"""Tests for the Synthesis Agent (Phase 2, Task 2.7) — THE CENTERPIECE.

draft → critique → revise loop. All Anthropic calls mocked. Optional live
integration test guarded by PMB_RUN_INTEGRATION=1 — see bottom of file.
"""
import json
import os
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from api.pipeline.agents.synthesis import synthesise_brief
from api.pipeline.prompts import (
    CRITIQUE_PROMPT,
    SYSTEM_PROMPT,
    build_brief_prompt,
)
from api.pipeline.state import BriefState


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _draft_payload(score: int = 4) -> dict:
    """A minimally-valid BriefOutput-shaped dict — enough to exercise the loop."""
    return {
        "snapshot": {
            "hook": "Anduril keeps stacking DoD wins; the question is margin sustainability.",
            "new_highlights": ["Pentagon $250M deal", "EU expansion"],
        },
        "thesis_fit": {
            "score": score,
            "reasoning": "Defense + dual-use is core Renegade.",
            "bear_case": "Margin profile on autonomous platforms still unproven.",
        },
        "funding": {
            "total_raised_usd": 4_200_000_000,
            "rounds": [
                {"type": "Series F", "date": "2024-08-01", "amount_usd": 1_500_000_000,
                 "led_by": ["Founders Fund"], "co_invested": []}
            ],
            "story": "Stacked Series F at $14B post.",
            "sources_used": ["PB+CB"],
        },
        "team": {"founders": [], "executives": [], "thesis": "Founder-led."},
        "traction": {"highlights": [], "web_visits": {},
                     "headcount_trend": {}, "narrative": "HC +18%."},
        "prior_engagement": {"timeline": [], "summary": "Conf handshake 2024-Q3."},
        "industry_deepdive": "Defense primes are slow; Anduril fills the gap.",
        "market_deepdive": "Tailwinds: AUKUS, EU rearm.",
        "key_engagement_questions": [
            "Margin profile on autonomous platforms vs HW?",
            "Bottleneck: silicon supply or DoD procurement?",
            "International expansion roadmap post-AUKUS?",
        ],
        "podcast_mentions": [],
        "news": [],
        "citations": [],
    }


def _revised_payload() -> dict:
    """A revised version — slightly different to detect which version we end up with."""
    p = _draft_payload(score=5)
    p["snapshot"]["hook"] = "REVISED: Anduril is core thesis; the meeting is about leverage."
    return p


def _critique_payload() -> dict:
    return {
        "weaknesses": [
            "thesis_fit reasoning is too generic — name specific Markets That Matter sub-sector.",
            "funding.story lacks ARR estimate.",
            "engagement questions don't probe the prior pass.",
        ],
        "specific_revisions": [
            "Add 'dual-use defense + frontier compute' to thesis_fit.reasoning.",
            "Quote Specter modeled ARR with confidence band.",
            "Replace Q1 with one that probes the closed-loop pass.",
        ],
    }


def _mock_response(payload: dict | str) -> MagicMock:
    """Build an Anthropic-shaped response whose .content[0].text is the payload."""
    text = payload if isinstance(payload, str) else json.dumps(payload)
    fake = MagicMock()
    fake.content = [MagicMock(text=text)]
    fake.stop_reason = "end_turn"
    return fake


def _populated_state() -> BriefState:
    """A reasonably-populated state — exercises every branch of build_brief_prompt."""
    return BriefState(
        company_name="Anduril Industries",
        domain="anduril.com",
        meeting_date=date(2026, 5, 29),
        partner="Devon",
        company_profile={"name": "Anduril Industries", "hq": "Costa Mesa"},
        team_people={"founders": [{"name": "Palmer Luckey"}]},
        traction_signals={"headcount": {"trend": "+18% TTM"}},
        attio_raw={"interactions": [
            {"date": "2024-09-10", "type": "conference", "note": "handshake"},
        ]},
        web_raw="Anduril announced $250M Pentagon contract on 2026-05-20.",
        web_citations=[{"title": "DoD presser", "url": "https://defense.gov/x"}],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────


async def test_synthesis_happy_path():
    """3 successful calls — draft, critique, revise — yields revised JSON."""
    state = _populated_state()

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        _mock_response(_draft_payload()),
        _mock_response(_critique_payload()),
        _mock_response(_revised_payload()),
    ]

    with patch("api.pipeline.agents.synthesis.get_client", return_value=fake_client):
        out = await synthesise_brief(state)

    # Final JSON is the revised version
    assert out.brief_json is not None
    assert out.brief_json["snapshot"]["hook"].startswith("REVISED:")
    assert out.brief_json["thesis_fit"]["score"] == 5

    # All required top-level keys present
    for key in (
        "snapshot", "thesis_fit", "funding", "team", "traction",
        "prior_engagement", "industry_deepdive", "market_deepdive",
        "key_engagement_questions", "podcast_mentions", "news",
    ):
        assert key in out.brief_json, f"missing key: {key}"

    # 3 LLM calls → 3 tool_call entries
    assert len(out.tool_calls) == 3
    assert all(tc.agent == "synthesis" for tc in out.tool_calls)

    # brief_html populated
    assert out.brief_html
    assert "Anduril" in out.brief_html

    # No error
    assert out.error is None


async def test_synthesis_critique_failure_uses_draft():
    """Critique call raises → revise stage is skipped → final is the draft."""
    state = _populated_state()

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        _mock_response(_draft_payload(score=3)),
        RuntimeError("critique timeout"),
    ]

    with patch("api.pipeline.agents.synthesis.get_client", return_value=fake_client):
        out = await synthesise_brief(state)

    # Final JSON is the draft (not revised)
    assert out.brief_json is not None
    assert out.brief_json["thesis_fit"]["score"] == 3
    assert not out.brief_json["snapshot"]["hook"].startswith("REVISED:")

    # Only 2 calls actually invoked (draft + failed critique). At minimum, draft+critique
    # are recorded as tool_calls — revise must NOT have run.
    assert fake_client.messages.create.call_count == 2

    # The critique tool_call should record the error
    critique_calls = [tc for tc in out.tool_calls if "critique" in tc.tool]
    assert critique_calls, "critique tool call should still be recorded with error"
    assert critique_calls[0].error is not None

    # Error on critique is non-blocking
    assert out.error is None


async def test_synthesis_revise_invalid_json_falls_back_to_draft():
    """Revise returns malformed JSON → final is the draft."""
    state = _populated_state()

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        _mock_response(_draft_payload(score=2)),
        _mock_response(_critique_payload()),
        _mock_response("this is not json at all — sorry."),
    ]

    with patch("api.pipeline.agents.synthesis.get_client", return_value=fake_client):
        out = await synthesise_brief(state)

    assert out.brief_json is not None
    assert out.brief_json["thesis_fit"]["score"] == 2
    assert not out.brief_json["snapshot"]["hook"].startswith("REVISED:")
    assert out.error is None


async def test_synthesis_thesis_fit_score_range():
    """thesis_fit.score must be in 1-5 when synthesis succeeds (asserts our mocks
    + the loop preserve the field unchanged)."""
    state = _populated_state()

    for score in (1, 2, 3, 4, 5):
        fake_client = MagicMock()
        fake_client.messages.create.side_effect = [
            _mock_response(_draft_payload(score=score)),
            _mock_response(_critique_payload()),
            _mock_response(_draft_payload(score=score)),  # revise echoes
        ]

        with patch("api.pipeline.agents.synthesis.get_client", return_value=fake_client):
            out = await synthesise_brief(state)

        assert out.brief_json is not None
        assert 1 <= out.brief_json["thesis_fit"]["score"] <= 5


async def test_synthesis_draft_invalid_then_retry_then_valid():
    """First draft = bad JSON → automatic retry → valid → full loop continues.
    Total LLM calls: 1 (bad) + 1 (retry) + 1 (critique) + 1 (revise) = 4."""
    state = _populated_state()

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        _mock_response("oops not json"),
        _mock_response(_draft_payload()),
        _mock_response(_critique_payload()),
        _mock_response(_revised_payload()),
    ]

    with patch("api.pipeline.agents.synthesis.get_client", return_value=fake_client):
        out = await synthesise_brief(state)

    assert out.brief_json is not None
    assert out.brief_json["snapshot"]["hook"].startswith("REVISED:")
    # 4 LLM calls expected
    assert fake_client.messages.create.call_count == 4
    assert len(out.tool_calls) == 4


async def test_synthesis_records_timings():
    """state.timings['synthesis'] is populated."""
    state = _populated_state()

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        _mock_response(_draft_payload()),
        _mock_response(_critique_payload()),
        _mock_response(_revised_payload()),
    ]

    with patch("api.pipeline.agents.synthesis.get_client", return_value=fake_client):
        out = await synthesise_brief(state)

    assert "synthesis" in out.timings
    assert out.timings["synthesis"] > 0


def test_build_brief_prompt_includes_context():
    """Unit test for the prompt builder — every populated field should appear
    in the returned user message."""
    state = _populated_state()
    msg = build_brief_prompt(state)

    assert "Anduril Industries" in msg
    assert "anduril.com" in msg
    assert "Devon" in msg
    assert "2026-05-29" in msg
    assert "Costa Mesa" in msg
    assert "Palmer Luckey" in msg
    assert "+18% TTM" in msg
    assert "conference" in msg  # interaction type
    assert "Pentagon" in msg
    assert "defense.gov" in msg  # citation URL


# ─────────────────────────────────────────────────────────────────────────────
# Optional live integration test (LiteLLM proxy)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("PMB_RUN_INTEGRATION") != "1",
    reason="Live integration test — set PMB_RUN_INTEGRATION=1 to run",
)
async def test_synthesis_live_minimal_state():
    """Run synthesis end-to-end against live Claude with a fabricated tiny state.
    Asserts the JSON shape matches what the Anthropic API actually returns."""
    state = _populated_state()
    out = await synthesise_brief(state)

    assert out.brief_json is not None, f"synthesis failed: {out.error}"
    assert 1 <= out.brief_json["thesis_fit"]["score"] <= 5
    for key in (
        "snapshot", "thesis_fit", "funding", "team", "traction",
        "prior_engagement", "industry_deepdive", "market_deepdive",
        "key_engagement_questions",
    ):
        assert key in out.brief_json, f"missing key: {key}"
