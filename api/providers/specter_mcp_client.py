"""SpecterMcpClient — DataProvider that wraps the standalone specter-mcp server.

This is the "real MCP demo" path. For each :meth:`fetch` call we subprocess-launch
``python -m mcp_servers.specter_mcp.server``, open an MCP stdio session, and
invoke the ``fetch_company`` tool. The returned :class:`ProviderResult` matches
the in-process :class:`SpecterProvider` envelope so the orchestrator can swap
implementations without caring about the transport.

If anything in the MCP path goes sideways — subprocess fails to launch, the
tool returns an error, the response is malformed, the call times out — we fall
back to the in-process :class:`SpecterProvider`. The result's ``normalized``
dict is tagged with ``_via: "mcp"`` or ``_via: "in_process_fallback"`` so the
audit panel can show which path served the data.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from api.providers.base import ProviderResult
from api.providers.specter import SpecterProvider

logger = logging.getLogger(__name__)


class SpecterMcpClient:
    """DataProvider wrapper around the standalone specter-mcp server.

    Parameters
    ----------
    fixtures_dir:
        Forwarded to the fallback :class:`SpecterProvider` so that if the
        subprocess path fails we can still serve the brief from local fixtures.
    server_module:
        The python ``-m`` target for the MCP server. Defaults to the in-repo
        ``mcp_servers.specter_mcp.server``.
    timeout_s:
        Soft deadline for the entire MCP roundtrip (initialize + call_tool).
        Exceeding it triggers the fallback path.
    """

    def __init__(
        self,
        fixtures_dir: Path,
        *,
        server_module: str = "mcp_servers.specter_mcp.server",
        timeout_s: float = 10.0,
    ) -> None:
        self.fixtures_dir = fixtures_dir
        self.server_module = server_module
        self.timeout_s = timeout_s
        # Composition over inheritance: the in-process provider owns the
        # fixture-reading + normalization logic. We reuse `_normalize` here and
        # delegate to `fetch` on fallback.
        self._fallback = SpecterProvider(fixtures_dir=fixtures_dir)

    async def fetch(self, domain: str, hints: dict) -> ProviderResult | None:
        try:
            payload = await asyncio.wait_for(
                self._call_mcp_tool(domain), timeout=self.timeout_s
            )
        except Exception as exc:  # noqa: BLE001 — any failure routes to fallback
            logger.warning(
                "specter-mcp transport failed for %s (%s); falling back to in-process",
                domain,
                exc,
            )
            return await self._fallback_with_marker(domain, hints)

        if payload is None:
            # The tool responded but the domain isn't in coverage. That's a
            # legitimate "no data" — surface as None, no fallback.
            return None

        normalized = self._fallback._normalize(payload, domain)
        normalized["_via"] = "mcp"
        return ProviderResult(source="specter", raw=payload, normalized=normalized)

    async def _call_mcp_tool(self, domain: str) -> dict | None:
        """Open an MCP stdio session and call ``fetch_company``.

        Returns the tool's JSON payload as a dict, or ``None`` if the server
        reported the domain wasn't found. Raises on any transport / protocol
        error so :meth:`fetch` can route to the fallback.
        """
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", self.server_module],
            env=None,
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "fetch_company", arguments={"domain": domain}
                )

        if getattr(result, "isError", False):
            raise McpToolError(f"specter-mcp fetch_company({domain!r}) returned isError")

        return _extract_payload(result)

    async def _fallback_with_marker(
        self, domain: str, hints: dict
    ) -> ProviderResult | None:
        """Delegate to the in-process provider and tag the result."""
        result = await self._fallback.fetch(domain, hints)
        if result is None:
            return None
        # ProviderResult is a pydantic model — mutate the normalized dict in
        # place; pydantic will keep the reference.
        result.normalized["_via"] = "in_process_fallback"
        return result


class McpToolError(RuntimeError):
    """Raised when the MCP tool call returns ``isError=True``."""


def _extract_payload(result: Any) -> dict | None:
    """Pull the JSON dict (or ``None``) out of a CallToolResult.

    FastMCP 1.27 wraps a bare-dict return value two ways at once:
      * ``structuredContent = {"result": <the dict>}`` (newer transport)
      * ``content = [TextContent(text=<json-encoded dict>)]``

    For ``None`` returns FastMCP emits ``structuredContent={"result": None}``
    and ``content=[]``. We prefer ``structuredContent`` when present and fall
    back to parsing the first text block.
    """
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict) and "result" in structured:
        value = structured["result"]
        if value is None or isinstance(value, dict):
            return value
        # Unexpected shape — punt to text parsing.

    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if not text:
            continue
        parsed = json.loads(text)
        if parsed is None or isinstance(parsed, dict):
            return parsed
        raise McpToolError(
            f"specter-mcp fetch_company returned non-dict JSON: {type(parsed).__name__}"
        )

    # No structured payload and no text content => treat as "no data".
    return None
