"""Tests for the Research Agent — Claude `web_search_20250305` loop.

All tests mock the Anthropic client. The optional integration test guarded by
PMB_RUN_INTEGRATION=1 hits live Claude via the LiteLLM proxy.
"""
import os
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from api.pipeline.agents.research import research_agent
from api.pipeline.state import BriefState


# ─────────────────────────────────────────────────────────────────────────────
# Fake response builders
# ─────────────────────────────────────────────────────────────────────────────


class FakeBlock:
    """Mimics an Anthropic content block. Attributes set from kwargs."""

    def __init__(self, type: str, **attrs):
        self.type = type
        for k, v in attrs.items():
            setattr(self, k, v)


class FakeResponse:
    def __init__(self, content, stop_reason: str = "end_turn"):
        self.content = content
        self.stop_reason = stop_reason
        self.model = "claude-sonnet-4-6"


def _state() -> BriefState:
    return BriefState(
        company_name="Anduril Industries",
        domain="anduril.com",
        meeting_date=date(2026, 5, 29),
        partner="Devon",
    )


def _happy_response() -> FakeResponse:
    """1 text + 1 server_tool_use + 1 web_search_tool_result (2 citations)."""
    return FakeResponse(
        [
            FakeBlock(
                "text",
                text="**Summary**\nAnduril raised $1.5B Series F in Aug 2025.",
            ),
            FakeBlock(
                "server_tool_use",
                id="srv_1",
                name="web_search",
                input={"query": "anduril series f 2025"},
            ),
            FakeBlock(
                "web_search_tool_result",
                tool_use_id="srv_1",
                content=[
                    {
                        "type": "web_search_result",
                        "url": "https://techcrunch.com/anduril-series-f",
                        "title": "Anduril Closes $1.5B Series F",
                        "encrypted_content": "enc1",
                    },
                    {
                        "type": "web_search_result",
                        "url": "https://reuters.com/anduril-defense",
                        "title": "Defense unicorn doubles valuation",
                        "encrypted_content": "enc2",
                    },
                ],
            ),
        ]
    )


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests (mocked)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_research_happy_path():
    fake = _happy_response()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = fake
    with patch("api.pipeline.agents.research.get_client", return_value=mock_client):
        state = await research_agent(_state())

    assert state.web_raw, "web_raw should be populated"
    assert "Anduril" in state.web_raw
    assert "$1.5B" in state.web_raw
    assert len(state.web_citations) == 2
    urls = {c["url"] for c in state.web_citations}
    assert "https://techcrunch.com/anduril-series-f" in urls
    assert "https://reuters.com/anduril-defense" in urls
    for c in state.web_citations:
        assert "url" in c and "title" in c


@pytest.mark.asyncio
async def test_research_no_results():
    fake = FakeResponse([FakeBlock("text", text="(no results found)")])
    mock_client = MagicMock()
    mock_client.messages.create.return_value = fake
    with patch("api.pipeline.agents.research.get_client", return_value=mock_client):
        state = await research_agent(_state())

    assert state.web_raw == "(no results found)"
    assert state.web_citations == []
    assert state.error is None  # not an error path


@pytest.mark.asyncio
async def test_research_exception_fallback():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = ConnectionError("proxy down")
    with patch("api.pipeline.agents.research.get_client", return_value=mock_client):
        state = await research_agent(_state())

    assert state.web_raw is not None
    assert state.web_raw.startswith("(web research unavailable")
    assert state.web_citations == []
    # error captured on a tool_call entry, not raised
    assert len(state.tool_calls) >= 1
    err_calls = [c for c in state.tool_calls if c.error]
    assert len(err_calls) >= 1
    assert "proxy down" in err_calls[0].error


@pytest.mark.asyncio
async def test_research_records_timing():
    fake = _happy_response()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = fake
    with patch("api.pipeline.agents.research.get_client", return_value=mock_client):
        state = await research_agent(_state())

    assert "research" in state.timings
    assert state.timings["research"] >= 0


@pytest.mark.asyncio
async def test_research_appends_tool_call():
    fake = _happy_response()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = fake
    with patch("api.pipeline.agents.research.get_client", return_value=mock_client):
        state = await research_agent(_state())

    assert len(state.tool_calls) >= 1
    research_calls = [c for c in state.tool_calls if c.agent == "research"]
    assert len(research_calls) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Optional integration (live LiteLLM proxy)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("PMB_RUN_INTEGRATION") != "1",
    reason="Live integration test — set PMB_RUN_INTEGRATION=1 to run",
)
@pytest.mark.asyncio
async def test_research_live_anduril():
    """Live call to Claude with web_search. Verifies raw + ≥1 citation."""
    state = BriefState(
        company_name="Anduril Industries",
        domain="anduril.com",
        meeting_date=date(2026, 5, 29),
        partner="Devon",
    )
    state = await research_agent(state)
    assert state.web_raw
    assert len(state.web_raw) > 100
    assert len(state.web_citations) >= 1
    for c in state.web_citations:
        assert c.get("url", "").startswith("http")
