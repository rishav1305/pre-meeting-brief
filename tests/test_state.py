from datetime import date
from uuid import uuid4
from api.pipeline.state import BriefState, DQFlag


def test_brief_state_minimal_construction():
    state = BriefState(
        company_name="Anduril Industries",
        domain="anduril.com",
        meeting_date=date(2026, 5, 29),
        partner="Devon",
    )
    assert state.domain == "anduril.com"
    assert state.qualification is None
    assert state.data_quality_flags == []
    assert state.timings == {}
    assert state.tool_calls == []
    assert state.error is None


def test_brief_state_qualification_literal():
    state = BriefState(
        company_name="X", domain="x.com", meeting_date=date(2026, 5, 29), partner="Devon",
        qualification="proceed", qualification_reason="No prior interactions in 90 days",
    )
    assert state.qualification == "proceed"


def test_brief_state_invalid_qualification_rejected():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        BriefState(
            company_name="X", domain="x.com", meeting_date=date(2026, 5, 29), partner="Devon",
            qualification="maybe",  # not in the Literal
        )


def test_dq_flag_construction():
    flag = DQFlag(
        field="founded_year",
        issue="delta_gt_1_year",
        severity="medium",
        source_a="Specter", value_a="2017",
        source_b="Crunchbase", value_b="2018",
    )
    assert flag.severity == "medium"
    assert flag.field == "founded_year"


def test_brief_state_serialization_roundtrip():
    state = BriefState(
        company_name="Anduril", domain="anduril.com",
        meeting_date=date(2026, 5, 29), partner="Devon",
        data_quality_flags=[
            DQFlag(field="founded_year", issue="delta", severity="medium"),
        ],
    )
    dumped = state.model_dump_json()
    reloaded = BriefState.model_validate_json(dumped)
    assert reloaded.domain == "anduril.com"
    assert len(reloaded.data_quality_flags) == 1
    assert reloaded.data_quality_flags[0].severity == "medium"


def test_brief_state_run_id_optional():
    state = BriefState(
        company_name="X", domain="x.com", meeting_date=date(2026, 5, 29), partner="Devon",
    )
    assert state.run_id is None
    state.run_id = uuid4()
    assert state.run_id is not None
