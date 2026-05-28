"""Tests for the Qualification Agent (Phase 2, Task 2.4).

Hybrid logic: deterministic prefilter on the attio interactions list +
LLM judgment fallback for the edge cases the heuristic can't cleanly
classify. All LLM calls are mocked — no network in unit tests.
"""
import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from api.pipeline.agents.qualification import qualification_agent
from api.pipeline.state import BriefState


def _state(meeting_date: date = date(2026, 6, 1), attio_raw: dict | None = None) -> BriefState:
    return BriefState(
        company_name="Acme Robotics",
        domain="acme.com",
        meeting_date=meeting_date,
        partner="rishav",
        attio_raw=attio_raw,
    )


def _mock_anthropic_response(payload: dict) -> MagicMock:
    """Build a fake Anthropic Messages response whose .content[0].text is the
    JSON payload — mirrors the real SDK shape."""
    fake = MagicMock()
    fake.content = [MagicMock(text=json.dumps(payload))]
    return fake


async def test_qualification_skip_recent_interaction():
    """Deterministic prefilter must skip when any interaction is within 90d
    of the meeting. The LLM must NOT be invoked — it would burn cost on a
    clear-cut case."""
    meeting = date(2026, 6, 1)
    state = _state(
        meeting_date=meeting,
        attio_raw={
            "interactions": [
                {"date": (meeting - timedelta(days=30)).isoformat(), "type": "email"},
                {"date": (meeting - timedelta(days=400)).isoformat(), "type": "intro"},
            ]
        },
    )

    with patch("api.pipeline.agents.qualification.get_client") as mock_get_client:
        out = await qualification_agent(state)

    assert out.qualification == "skip"
    assert "recent interaction" in (out.qualification_reason or "").lower()
    # most-recent interaction date is the 30d-ago one
    assert (meeting - timedelta(days=30)).isoformat() in (out.qualification_reason or "")
    assert mock_get_client.call_count == 0
    assert "qualification" in out.timings
    assert out.tool_calls == []


async def test_qualification_proceed_old_interactions():
    """All interactions older than 90d → LLM is consulted; agent returns
    whatever the LLM decides (proceed here)."""
    meeting = date(2026, 6, 1)
    state = _state(
        meeting_date=meeting,
        attio_raw={
            "interactions": [
                {"date": (meeting - timedelta(days=180)).isoformat(), "type": "conference"},
                {"date": (meeting - timedelta(days=400)).isoformat(), "type": "intro"},
            ]
        },
    )

    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_anthropic_response(
        {"decision": "proceed", "reason": "stale conference handshake — fresh meeting"}
    )

    with patch("api.pipeline.agents.qualification.get_client", return_value=fake_client):
        out = await qualification_agent(state)

    assert out.qualification == "proceed"
    assert "stale conference" in (out.qualification_reason or "")
    assert fake_client.messages.create.call_count == 1


async def test_qualification_no_interactions():
    """Empty/None interactions list → LLM is consulted (no recent activity
    is itself an edge case worth a cheap LLM check)."""
    state_empty = _state(attio_raw={"interactions": []})
    state_none = _state(attio_raw=None)

    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_anthropic_response(
        {"decision": "proceed", "reason": "no prior engagement on file"}
    )

    with patch("api.pipeline.agents.qualification.get_client", return_value=fake_client):
        out_empty = await qualification_agent(state_empty)
        out_none = await qualification_agent(state_none)

    assert out_empty.qualification == "proceed"
    assert out_none.qualification == "proceed"
    assert fake_client.messages.create.call_count == 2


async def test_qualification_flag_for_human():
    """LLM returning flag_for_human flows through verbatim."""
    meeting = date(2026, 6, 1)
    state = _state(
        meeting_date=meeting,
        attio_raw={
            "interactions": [
                {"date": (meeting - timedelta(days=200)).isoformat(), "type": "note",
                 "body": "passed on Series E"},
            ]
        },
    )

    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_anthropic_response(
        {"decision": "flag_for_human", "reason": "closed loop — previously passed on Series E"}
    )

    with patch("api.pipeline.agents.qualification.get_client", return_value=fake_client):
        out = await qualification_agent(state)

    assert out.qualification == "flag_for_human"
    assert "closed loop" in (out.qualification_reason or "")


async def test_qualification_llm_failure_defaults_to_proceed():
    """LLM raising must NOT block the pipeline — default to proceed and
    explain the fallback in qualification_reason. state.error stays None
    because this failure is non-blocking."""
    meeting = date(2026, 6, 1)
    state = _state(
        meeting_date=meeting,
        attio_raw={"interactions": [
            {"date": (meeting - timedelta(days=180)).isoformat(), "type": "email"},
        ]},
    )

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = RuntimeError("API timeout")

    with patch("api.pipeline.agents.qualification.get_client", return_value=fake_client):
        out = await qualification_agent(state)

    assert out.qualification == "proceed"
    assert "fail" in (out.qualification_reason or "").lower()
    assert out.error is None


async def test_qualification_records_tool_call_when_llm_invoked():
    """When the LLM is consulted, a ToolCall record must be appended with
    agent='qualification'."""
    meeting = date(2026, 6, 1)
    state = _state(
        meeting_date=meeting,
        attio_raw={"interactions": [
            {"date": (meeting - timedelta(days=200)).isoformat(), "type": "intro"},
        ]},
    )

    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_anthropic_response(
        {"decision": "proceed", "reason": "old intro, fresh meeting"}
    )

    with patch("api.pipeline.agents.qualification.get_client", return_value=fake_client):
        out = await qualification_agent(state)

    assert len(out.tool_calls) == 1
    assert out.tool_calls[0].agent == "qualification"
    assert out.tool_calls[0].error is None
