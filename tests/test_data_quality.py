"""Tests for the Data Quality Agent (Phase 2, Task 2.6).

Rule-based ranking handles the common case (severity desc, then critical
field bucket, then alphabetical). LLM (Haiku) tie-break is reserved for
ambiguous cases — only invoked when >5 flags share the same severity AND
field-priority bucket AND total flags > 8. All LLM calls are mocked.
"""
import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from api.pipeline.agents.data_quality import data_quality_agent
from api.pipeline.state import BriefState, DQFlag


def _state(flags: list[DQFlag] | None = None) -> BriefState:
    return BriefState(
        company_name="Acme Robotics",
        domain="acme.com",
        meeting_date=date(2026, 6, 1),
        partner="rishav",
        data_quality_flags=flags or [],
    )


def _mock_anthropic_response(payload: dict | list) -> MagicMock:
    """Build a fake Anthropic Messages response whose .content[0].text is the
    JSON payload — mirrors the real SDK shape."""
    fake = MagicMock()
    fake.content = [MagicMock(text=json.dumps(payload))]
    return fake


async def test_dq_agent_empty_input():
    """Empty input → empty output, no LLM call, no tool_call appended."""
    state = _state(flags=[])

    with patch("api.pipeline.agents.data_quality.get_client") as mock_get_client:
        out = await data_quality_agent(state)

    assert out.dq_ranked == []
    assert mock_get_client.call_count == 0
    assert out.tool_calls == []
    assert "data_quality" in out.timings


async def test_dq_agent_sorts_by_severity():
    """3 flags of varying severity → ordered high, medium, low."""
    flags = [
        DQFlag(field="x_field", issue="low issue", severity="low"),
        DQFlag(field="y_field", issue="high issue", severity="high"),
        DQFlag(field="z_field", issue="medium issue", severity="medium"),
    ]
    state = _state(flags=flags)

    with patch("api.pipeline.agents.data_quality.get_client") as mock_get_client:
        out = await data_quality_agent(state)

    assert [f.severity for f in out.dq_ranked] == ["high", "medium", "low"]
    assert mock_get_client.call_count == 0


async def test_dq_agent_critical_fields_first_within_severity():
    """Within same severity: operating_status (priority 0) before hq_country
    (priority 4) before random_field (priority 999)."""
    flags = [
        DQFlag(field="random_field", issue="random", severity="high"),
        DQFlag(field="operating_status", issue="status", severity="high"),
        DQFlag(field="hq_country", issue="country", severity="high"),
    ]
    state = _state(flags=flags)

    with patch("api.pipeline.agents.data_quality.get_client") as mock_get_client:
        out = await data_quality_agent(state)

    assert [f.field for f in out.dq_ranked] == [
        "operating_status",
        "hq_country",
        "random_field",
    ]
    assert mock_get_client.call_count == 0


async def test_dq_agent_stable_alphabetical_tiebreak():
    """Same severity + same field-priority bucket (both non-critical) →
    alphabetical by field name. aaa_field before bbb_field."""
    flags = [
        DQFlag(field="bbb_field", issue="b", severity="medium"),
        DQFlag(field="aaa_field", issue="a", severity="medium"),
    ]
    state = _state(flags=flags)

    with patch("api.pipeline.agents.data_quality.get_client") as mock_get_client:
        out = await data_quality_agent(state)

    assert [f.field for f in out.dq_ranked] == ["aaa_field", "bbb_field"]
    assert mock_get_client.call_count == 0


async def test_dq_agent_skips_llm_tiebreak_when_small():
    """3 flags total → well below the ambiguity threshold; LLM never called."""
    flags = [
        DQFlag(field="founded_year", issue="y", severity="medium"),
        DQFlag(field="employee_count", issue="e", severity="medium"),
        DQFlag(field="random_field", issue="r", severity="medium"),
    ]
    state = _state(flags=flags)

    with patch("api.pipeline.agents.data_quality.get_client") as mock_get_client:
        out = await data_quality_agent(state)

    assert mock_get_client.call_count == 0
    assert len(out.dq_ranked) == 3


async def test_dq_agent_invokes_llm_tiebreak_when_ambiguous():
    """9 flags, 6 sharing same severity + same field-priority bucket
    (all non-critical medium) → LLM tie-break fires; LLM returns a
    reordering that gets applied to that bucket."""
    flags = [
        # 3 high-severity (not in the ambiguous bucket)
        DQFlag(field="operating_status", issue="h1", severity="high"),
        DQFlag(field="hq_country", issue="h2", severity="high"),
        DQFlag(field="last_round_date", issue="h3", severity="high"),
        # 6 medium-severity, all NON-critical → same field-priority bucket
        DQFlag(field="aaa_field", issue="m1", severity="medium"),
        DQFlag(field="bbb_field", issue="m2", severity="medium"),
        DQFlag(field="ccc_field", issue="m3", severity="medium"),
        DQFlag(field="ddd_field", issue="m4", severity="medium"),
        DQFlag(field="eee_field", issue="m5", severity="medium"),
        DQFlag(field="fff_field", issue="m6", severity="medium"),
    ]
    state = _state(flags=flags)

    # LLM proposes reverse-alphabetical ordering for the ambiguous bucket.
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_anthropic_response(
        {"order": ["fff_field", "eee_field", "ddd_field", "ccc_field", "bbb_field", "aaa_field"]}
    )

    with patch("api.pipeline.agents.data_quality.get_client", return_value=fake_client):
        out = await data_quality_agent(state)

    assert fake_client.messages.create.call_count == 1
    # High-severity bucket stays in critical-field order at top
    assert [f.severity for f in out.dq_ranked[:3]] == ["high", "high", "high"]
    # Medium bucket reordered per LLM
    assert [f.field for f in out.dq_ranked[3:]] == [
        "fff_field", "eee_field", "ddd_field", "ccc_field", "bbb_field", "aaa_field",
    ]


async def test_dq_agent_records_tool_call_when_llm_invoked():
    """When the LLM is consulted, a ToolCall record must be appended with
    agent='data_quality'."""
    flags = [
        DQFlag(field="aaa_field", issue="m1", severity="medium"),
        DQFlag(field="bbb_field", issue="m2", severity="medium"),
        DQFlag(field="ccc_field", issue="m3", severity="medium"),
        DQFlag(field="ddd_field", issue="m4", severity="medium"),
        DQFlag(field="eee_field", issue="m5", severity="medium"),
        DQFlag(field="fff_field", issue="m6", severity="medium"),
        DQFlag(field="ggg_field", issue="m7", severity="medium"),
        DQFlag(field="hhh_field", issue="m8", severity="medium"),
        DQFlag(field="iii_field", issue="m9", severity="medium"),
    ]
    state = _state(flags=flags)

    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_anthropic_response(
        {"order": [f.field for f in flags]}  # identity reorder
    )

    with patch("api.pipeline.agents.data_quality.get_client", return_value=fake_client):
        out = await data_quality_agent(state)

    assert len(out.tool_calls) == 1
    assert out.tool_calls[0].agent == "data_quality"
    assert out.tool_calls[0].error is None


async def test_dq_agent_llm_failure_keeps_rule_based_order():
    """LLM raising must NOT block the pipeline — falls back to rule-based
    deterministic order; state.error stays None."""
    flags = [
        DQFlag(field="aaa_field", issue="m1", severity="medium"),
        DQFlag(field="bbb_field", issue="m2", severity="medium"),
        DQFlag(field="ccc_field", issue="m3", severity="medium"),
        DQFlag(field="ddd_field", issue="m4", severity="medium"),
        DQFlag(field="eee_field", issue="m5", severity="medium"),
        DQFlag(field="fff_field", issue="m6", severity="medium"),
        DQFlag(field="ggg_field", issue="m7", severity="medium"),
        DQFlag(field="hhh_field", issue="m8", severity="medium"),
        DQFlag(field="iii_field", issue="m9", severity="medium"),
    ]
    state = _state(flags=flags)

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = RuntimeError("API timeout")

    with patch("api.pipeline.agents.data_quality.get_client", return_value=fake_client):
        out = await data_quality_agent(state)

    # Falls back to alphabetical (rule-based) order for the bucket
    assert [f.field for f in out.dq_ranked] == [
        "aaa_field", "bbb_field", "ccc_field", "ddd_field", "eee_field",
        "fff_field", "ggg_field", "hhh_field", "iii_field",
    ]
    assert out.error is None
    # ToolCall records the failure
    assert len(out.tool_calls) == 1
    assert out.tool_calls[0].agent == "data_quality"
    assert out.tool_calls[0].error is not None
