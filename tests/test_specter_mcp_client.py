"""Tests for SpecterMcpClient — the DataProvider wrapper around the standalone
specter-mcp server.

Unit tests patch the mcp stdio transport so they don't actually spawn a
subprocess. The integration test (opt-in via env var ``PMB_RUN_INTEGRATION=1``)
spawns the real server and verifies an end-to-end roundtrip — kept off the
default suite because it's slow and forks a Python process.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.providers.base import DataProvider
from api.providers.specter_mcp_client import SpecterMcpClient

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

_RUN_INTEGRATION = os.environ.get("PMB_RUN_INTEGRATION") == "1"


# ---------------------------------------------------------------------------
# Helpers — build a fake (read, write) stdio_client async context manager and
# a fake ClientSession whose .initialize / .call_tool methods we control.
# ---------------------------------------------------------------------------


def _make_call_tool_result(*, is_error: bool = False, text: str | None = None) -> SimpleNamespace:
    """Stand-in for mcp.types.CallToolResult — we only access .isError + .content."""
    content: list = []
    if text is not None:
        content.append(SimpleNamespace(type="text", text=text))
    return SimpleNamespace(isError=is_error, content=content, structuredContent=None)


def _stdio_client_cm(session_factory):
    """Build a fake stdio_client async-context-manager.

    Calling stdio_client(params) returns this object; entering yields
    (read, write); ClientSession(read, write) yields the supplied session.
    """

    class _StdioCM:
        async def __aenter__(self):
            return (MagicMock(name="read"), MagicMock(name="write"))

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _SessionCM:
        def __init__(self, *args, **kwargs):
            self._session = session_factory()

        async def __aenter__(self):
            return self._session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    return _StdioCM(), _SessionCM


def test_specter_mcp_client_satisfies_protocol() -> None:
    """SpecterMcpClient must be a structural DataProvider."""
    client = SpecterMcpClient(fixtures_dir=FIXTURES_DIR)
    assert isinstance(client, DataProvider)


@pytest.mark.asyncio
async def test_mcp_happy_path_returns_provider_result(monkeypatch) -> None:
    """When the MCP tool returns a JSON payload, we get a ProviderResult with _via=mcp."""
    payload = json.loads((FIXTURES_DIR / "anduril.com" / "specter.json").read_text())

    fake_session = SimpleNamespace(
        initialize=AsyncMock(return_value=None),
        call_tool=AsyncMock(
            return_value=_make_call_tool_result(text=json.dumps(payload))
        ),
    )

    stdio_cm, session_cls = _stdio_client_cm(lambda: fake_session)

    with patch("api.providers.specter_mcp_client.stdio_client", return_value=stdio_cm), patch(
        "api.providers.specter_mcp_client.ClientSession", session_cls
    ):
        client = SpecterMcpClient(fixtures_dir=FIXTURES_DIR)
        result = await client.fetch("anduril.com", hints={})

    assert result is not None
    assert result.source == "specter"
    assert result.raw["organization_name"] == "Anduril Industries"
    assert result.normalized["domain"] == "anduril.com"
    assert result.normalized["founded_year"] == 2017
    assert result.normalized["_via"] == "mcp"
    fake_session.call_tool.assert_awaited_once()


@pytest.mark.asyncio
async def test_subprocess_failure_falls_back_to_in_process(monkeypatch) -> None:
    """If stdio_client raises (subprocess launch fail), fall back to in-process SpecterProvider."""

    def boom(*_args, **_kwargs):
        raise RuntimeError("subprocess launch failed")

    with patch("api.providers.specter_mcp_client.stdio_client", side_effect=boom):
        client = SpecterMcpClient(fixtures_dir=FIXTURES_DIR)
        result = await client.fetch("anduril.com", hints={})

    assert result is not None
    assert result.source == "specter"
    # In-process path produced this result, but the wrapper labelled it.
    assert result.normalized["_via"] == "in_process_fallback"
    assert result.normalized["domain"] == "anduril.com"
    assert result.normalized["founded_year"] == 2017


@pytest.mark.asyncio
async def test_missing_fixture_returns_none_via_fallback(monkeypatch) -> None:
    """A domain that's not in fixtures returns None; client surfaces None (not an error)."""

    def boom(*_args, **_kwargs):
        # Force the fallback to fire; the in-process SpecterProvider returns
        # None for missing fixtures.
        raise RuntimeError("simulated subprocess failure")

    with patch("api.providers.specter_mcp_client.stdio_client", side_effect=boom):
        client = SpecterMcpClient(fixtures_dir=FIXTURES_DIR)
        result = await client.fetch("notinfixtures.com", hints={})

    assert result is None


@pytest.mark.skipif(
    not _RUN_INTEGRATION,
    reason="set PMB_RUN_INTEGRATION=1 to spawn the real specter-mcp subprocess",
)
@pytest.mark.asyncio
async def test_live_mcp_roundtrip_against_real_server() -> None:
    """Opt-in: actually spawn the standalone server and call fetch_company."""
    client = SpecterMcpClient(fixtures_dir=FIXTURES_DIR)
    result = await client.fetch("anduril.com", hints={})

    assert result is not None
    assert result.source == "specter"
    assert result.raw["organization_name"] == "Anduril Industries"
    assert result.normalized["_via"] == "mcp"
