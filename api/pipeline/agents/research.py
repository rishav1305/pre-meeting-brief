"""Research Agent — Claude `web_search_20250305` tool loop.

Asks Claude Sonnet 4.6 to research a target company for an investor brief.
Claude iterates up to 5 web searches autonomously via the server-side tool;
we parse the multi-block response to collect text + citations.

Failure mode: any exception is captured on `state.tool_calls` and the agent
returns gracefully with a fallback `web_raw` message. The orchestrator never
sees an exception from this node.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from api.llm import DEFAULT_MODEL, get_client
from api.pipeline.state import BriefState, ToolCall


PROMPT_TEMPLATE = """Research the company {company_name} (domain: {domain}) for an investor pre-meeting brief.

Focus on the past 6 months:
- Funding announcements (rounds, valuations, lead investors)
- Product launches, major partnerships, or platform changes
- Notable negative news, regulatory issues, or analyst commentary
- Customer review signals (G2, Trustpilot, app store)
- Executive changes (CEO, CTO, head of product/sales)

Iterate web searches up to 5 times. If you find a high-signal item (e.g., a Series F announcement), search deeper on that specific item. Don't stop at the first page of results.

Return a concise markdown summary (<= 1000 words) with inline citations as you go. Reference URLs the search returned; do not invent."""


MAX_TOOL_USES = 5
MAX_OUTPUT_TOKENS = 1500
WALLCLOCK_SECS = 60.0


def _truncate(s: str, n: int = 200) -> str:
    return s if len(s) <= n else s[:n] + "…"


def _block_attr(block: Any, name: str, default: Any = None) -> Any:
    """Safely read an attribute that may be missing on a content block."""
    return getattr(block, name, default)


def _extract_text(content: list[Any]) -> str:
    parts: list[str] = []
    for block in content:
        if _block_attr(block, "type") == "text":
            t = _block_attr(block, "text", "")
            if t:
                parts.append(t)
    return "\n\n".join(parts).strip()


def _extract_citations(content: list[Any]) -> list[dict]:
    """Pull citations from `web_search_tool_result` blocks.

    Each result block carries a `.content` list of dicts shaped like
    {"type": "web_search_result", "url": ..., "title": ..., "encrypted_content": ...}.
    We normalize to {"title", "url", "snippet"}.
    """
    citations: list[dict] = []
    seen: set[str] = set()
    for block in content:
        if _block_attr(block, "type") != "web_search_tool_result":
            continue
        results = _block_attr(block, "content", []) or []
        for r in results:
            # `r` may be a dict (mock) or an SDK object (live)
            if isinstance(r, dict):
                url = r.get("url", "")
                title = r.get("title", "")
                snippet = r.get("snippet") or r.get("page_age") or ""
            else:
                url = getattr(r, "url", "") or ""
                title = getattr(r, "title", "") or ""
                snippet = getattr(r, "snippet", "") or getattr(r, "page_age", "") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            citations.append({"title": title, "url": url, "snippet": snippet})
    return citations


def _count_tool_uses(content: list[Any]) -> int:
    return sum(1 for b in content if _block_attr(b, "type") == "server_tool_use")


def _run_claude_sync(company_name: str, domain: str) -> Any:
    """Blocking Anthropic call. Wrapped in asyncio.to_thread by the caller."""
    client = get_client()
    return client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=MAX_OUTPUT_TOKENS,
        messages=[
            {
                "role": "user",
                "content": PROMPT_TEMPLATE.format(
                    company_name=company_name, domain=domain
                ),
            }
        ],
        tools=[
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": MAX_TOOL_USES,
            }
        ],
    )


async def research_agent(state: BriefState) -> BriefState:
    """Researches the target company via Claude's web_search tool.

    Sets state.web_raw (markdown summary) and state.web_citations (list of dicts).
    Records timing and tool-call audit entries. Never raises.
    """
    started = time.monotonic()
    input_summary = _truncate(
        f"research {state.company_name} ({state.domain}) for investor brief"
    )

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(_run_claude_sync, state.company_name, state.domain),
            timeout=WALLCLOCK_SECS,
        )
        content = getattr(response, "content", []) or []
        web_raw = _extract_text(content)
        citations = _extract_citations(content)
        tool_uses = _count_tool_uses(content)

        state.web_raw = web_raw or "(no results found)"
        state.web_citations = citations

        duration_ms = int((time.monotonic() - started) * 1000)
        state.tool_calls.append(
            ToolCall(
                agent="research",
                tool="claude.web_search",
                input_summary=input_summary,
                output_summary=_truncate(
                    f"{tool_uses} searches, {len(citations)} citations, "
                    f"{len(state.web_raw or '')} chars"
                ),
                duration_ms=duration_ms,
            )
        )
    except Exception as exc:  # pragma: no cover - exercised via tests
        reason = str(exc) or exc.__class__.__name__
        state.web_raw = f"(web research unavailable: {reason})"
        state.web_citations = []
        duration_ms = int((time.monotonic() - started) * 1000)
        state.tool_calls.append(
            ToolCall(
                agent="research",
                tool="claude.web_search",
                input_summary=input_summary,
                output_summary="error",
                duration_ms=duration_ms,
                error=reason,
            )
        )

    state.timings["research"] = time.monotonic() - started
    return state
