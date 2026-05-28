"""Tests for api.pipeline.merge — deterministic canonical merge with priority chains.

Per Phase 2 Task 2.3. Validates:
- Source-priority chains for company / people / traction_metrics
- 6 conflict detectors (CONFLICT-1..6)
- ARRAY_UNION dedup semantics
- Audit JSONB shape: {field, source, pulled_at}
- Resilience to None inputs

Fixtures-as-data — no disk reads.
"""
from __future__ import annotations

from datetime import date

from api.pipeline.merge import merge_canonical
from api.pipeline.state import BriefState


# ─────────────────────────────────────────────────────────────────────────────
# Fixture builders
# ─────────────────────────────────────────────────────────────────────────────


def _base_state(**overrides) -> BriefState:
    """A BriefState pre-loaded with all 4 source raws populated, no conflicts."""
    specter = {
        "id": "spec_test",
        "domain": "anduril.com",
        "organization_name": "Anduril Industries",
        "description": "Defense autonomy.",
        "industries": ["Defense"],
        "operating_status": "active",
        "highlights": ["top_tier_investors", "headcount_surge", "engineering_hiring"],
        "new_highlights": ["pentagon_250m_contract_2026q2"],
        "growth_stage": "late_stage",
        "founded_year": 2017,
        "employee_count": 6500,
        "employee_count_range": "5001-10000",
        "revenue_estimate_usd": 1_000_000_000,
        "investors": ["Founders Fund", "Andreessen Horowitz"],
        "funding": {
            "total_raised_usd": 4_200_000_000,
            "last_round_type": "series_f",
            "last_round_date": "2024-08-08",
            "last_round_usd": 1_500_000_000,
            "post_money_valuation_usd": 14_000_000_000,
            "round_count": 8,
        },
        "hq": {"city": "Costa Mesa", "country": "US", "region": "North America"},
        "tags": ["defense", "AI"],
        "customer_focus": "b2b",
        "customer_profile": "DoD",
        "traction_metrics": {
            "web_visits": {"latest": 4_200_000, "trend_3mo": {"value": 4_200_000, "change": 380_000, "pct_change": 9.95}},
            "linkedin_followers": {"latest": 850_000, "trend_6mo": {"value": 850_000, "change": 92_000, "pct_change": 12.13}},
            "employee_count": {"latest": 6500, "trend_6mo": {"value": 6500, "change": 1200, "pct_change": 22.64}},
        },
        "web": {"popularity_rank": 18500, "bounce_rate": 0.34, "top_country": "US", "traffic_source": "Direct 58%"},
        "socials": {"linkedin": {"url": "https://linkedin.com/x", "follower_count": 850_000}},
        "founder_info": [
            {"specter_person_id": "p1", "full_name": "Palmer Luckey", "title": "Founder",
             "linkedin_url": "https://linkedin.com/in/palmerluckey"},
        ],
        "news": [
            {"date": "2026-05-12", "title": "Pentagon contract", "url": "https://ex.com/a", "publisher": "Defense News"},
        ],
        "awards": [{"name": "Fast Company", "org": "Fast Company", "year": 2024, "rank": 12}],
        "patent_count": 47,
        "it_spend": 85_000_000,
        "reported_clients": ["DoD"],
        "hiring_signals": ["headcount_surge", "engineering_hiring"],
        "key_people": [
            {"level": "Executive Level", "full_name": "Jane Doe", "title": "CFO"},
            {"level": "VP Level", "full_name": "Jim VP", "title": "VP Eng"},
        ],
        "open_role_count": 120,
        "org_rank": 88,
    }
    crunchbase = {
        "org": {
            "uuid": "cb_test",
            "name": "Anduril Industries",
            "permalink": "anduril-industries",
            "short_description": "Defense tech",
            "founded_year": 2017,
            "country_code": "USA",
            "city": "Costa Mesa",
            "operating_status": "active",
            "num_employees_enum": "5001-10000",
            "category_list": ["Defense"],
        },
        "rounds": [
            {"announced_on": "2024-08-08", "investment_type": "series_f", "raised_usd": 1_500_000_000,
             "post_money_valuation_usd": 14_000_000_000, "investors": ["Founders Fund"]},
        ],
        "board_members_and_advisors": [
            {"full_name": "Peter Thiel", "title": "Board Observer", "affiliated_firm": "Founders Fund"},
        ],
    }
    pitchbook = {
        "pb_id": "pb_test",
        "domain": "anduril.com",
        "total_raised_usd": 4_200_000_000,
        "last_round_type": "Series F",
        "last_round_date": "2024-08-08",
        "last_round_usd": 1_500_000_000,
        "post_money_valuation_usd": 14_000_000_000,
    }

    s = BriefState(
        company_name="Anduril Industries",
        domain="anduril.com",
        meeting_date=date(2026, 5, 29),
        partner="Devon",
        specter_raw=specter,
        crunchbase_raw=crunchbase,
        pitchbook_raw=pitchbook,
    )
    # Apply overrides on the source raws
    for key, val in overrides.items():
        setattr(s, key, val)
    return s


# ─────────────────────────────────────────────────────────────────────────────
# 1. Happy path
# ─────────────────────────────────────────────────────────────────────────────


def test_happy_path_no_conflicts_full_audit():
    state = _base_state()
    out = merge_canonical(state)

    cp = out.company_profile
    assert cp is not None
    assert cp["domain"] == "anduril.com"
    assert cp["operating_status"] == "active"
    assert cp["founded_year"] == 2017
    assert cp["hq_country"] == "US"
    assert cp["hq_city"] == "Costa Mesa"
    assert cp["total_raised_usd"] == 4_200_000_000
    assert cp["last_round_type"] == "series_f"
    assert cp["tags"] == ["defense", "AI"]
    assert cp["growth_stage"] == "late_stage"

    # Audit JSONB has many entries — every field touched logs one
    audit = cp["audit"]
    assert isinstance(audit, list)
    assert len(audit) >= 17  # company_profile has 17+ fields
    for entry in audit:
        assert set(entry.keys()) == {"field", "source", "pulled_at"}

    # No DQ flags on happy path
    assert out.data_quality_flags == []

    # Other entities also populated with their own audit
    assert out.team_people is not None
    assert "audit" in out.team_people
    assert out.traction_signals is not None
    assert "audit" in out.traction_signals


# ─────────────────────────────────────────────────────────────────────────────
# 2-6. Conflict detectors
# ─────────────────────────────────────────────────────────────────────────────


def test_conflict_1_operating_status_mismatch_high():
    state = _base_state()
    state.crunchbase_raw["org"]["operating_status"] = "closed"
    out = merge_canonical(state)
    flags = [f for f in out.data_quality_flags if f.field == "operating_status"]
    assert len(flags) == 1
    assert flags[0].severity == "high"
    # specter wins
    assert out.company_profile["operating_status"] == "active"


def test_conflict_2_founded_year_delta_gt_1_medium():
    state = _base_state()
    state.crunchbase_raw["org"]["founded_year"] = 2014  # delta=3
    out = merge_canonical(state)
    flags = [f for f in out.data_quality_flags if f.field == "founded_year"]
    assert len(flags) == 1
    assert flags[0].severity == "medium"


def test_conflict_3_hq_country_mismatch_high():
    state = _base_state()
    state.crunchbase_raw["org"]["country_code"] = "UK"
    out = merge_canonical(state)
    flags = [f for f in out.data_quality_flags if f.field == "hq_country"]
    assert len(flags) == 1
    assert flags[0].severity == "high"
    assert out.company_profile["hq_country"] == "US"  # specter wins


def test_conflict_4_last_round_date_delta_gt_30_days_high():
    state = _base_state()
    # pitchbook 2024-08-08, push crunchbase to 2024-10-08 (~61 days delta)
    state.crunchbase_raw["rounds"][0]["announced_on"] = "2024-10-08"
    out = merge_canonical(state)
    flags = [f for f in out.data_quality_flags if f.field == "last_round_date"]
    assert len(flags) == 1
    assert flags[0].severity == "high"


def test_conflict_5_employee_count_specter_gt_2x_crunchbase_midpoint_medium():
    state = _base_state()
    # crunchbase 11-50 -> midpoint ~30, specter 6500 (>> 2x 30)
    state.crunchbase_raw["org"]["num_employees_enum"] = "11-50"
    out = merge_canonical(state)
    flags = [f for f in out.data_quality_flags if f.field == "employee_count"]
    assert len(flags) == 1
    assert flags[0].severity == "medium"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Priority: PitchBook beats Specter on total_raised_usd
# ─────────────────────────────────────────────────────────────────────────────


def test_priority_pitchbook_beats_specter_on_total_raised():
    state = _base_state()
    state.pitchbook_raw["total_raised_usd"] = 9_999_999_999  # distinctive
    state.specter_raw["funding"]["total_raised_usd"] = 1_111_111_111
    out = merge_canonical(state)
    assert out.company_profile["total_raised_usd"] == 9_999_999_999
    # Audit names pitchbook as source
    field_audits = [e for e in out.company_profile["audit"] if e["field"] == "total_raised_usd"]
    assert field_audits and field_audits[0]["source"] == "pitchbook"


# ─────────────────────────────────────────────────────────────────────────────
# 8. ARRAY_UNION dedup
# ─────────────────────────────────────────────────────────────────────────────


def test_array_union_investors_dedup_case_insensitive_preserve_casing():
    state = _base_state()
    state.specter_raw["investors"] = ["Founders Fund", "Andreessen Horowitz"]
    state.crunchbase_raw["rounds"][0]["investors"] = ["founders fund", "Sequoia Capital"]
    out = merge_canonical(state)
    invs = out.company_profile["investors"]
    lowered = [i.lower() for i in invs]
    assert lowered == ["founders fund", "andreessen horowitz", "sequoia capital"]
    # Preserved original Specter casing for the duplicated one
    assert "Founders Fund" in invs


# ─────────────────────────────────────────────────────────────────────────────
# 9. Missing-source resilience
# ─────────────────────────────────────────────────────────────────────────────


def test_missing_source_resilience_specter_none_crunchbase_fills():
    state = _base_state()
    state.specter_raw = None
    out = merge_canonical(state)
    cp = out.company_profile
    # crunchbase backed: description, operating_status, founded_year, hq_country
    assert cp["description"] == "Defense tech"
    assert cp["operating_status"] == "active"
    assert cp["founded_year"] == 2017
    assert cp["hq_country"] == "US"  # USA normalized
    # specter-only fields → None + audit source="missing"
    assert cp["tags"] is None
    missing = [e for e in cp["audit"] if e["source"] == "missing"]
    assert len(missing) >= 1
    assert any(e["field"] == "tags" for e in missing)


# ─────────────────────────────────────────────────────────────────────────────
# 10. Founder dedup by name
# ─────────────────────────────────────────────────────────────────────────────


def test_founder_dedup_by_name_specter_wins_on_title():
    state = _base_state()
    state.specter_raw["founder_info"] = [
        {"specter_person_id": "p1", "full_name": "Palmer Luckey", "title": "Founder & CEO",
         "linkedin_url": "https://linkedin.com/in/palmerluckey"},
    ]
    # crunchbase doesn't have a separate founder list in the DD shape we ship,
    # but Phase-1 fixtures show founder info can also come from crunchbase.rounds[].investors
    # which isn't a founder. Per the spec, founders merge by full_name (case-insensitive),
    # so simulate a crunchbase founder list under a common key:
    state.crunchbase_raw["founders"] = [
        {"full_name": "palmer luckey", "title": "Co-founder", "linkedin_url": "https://x.test"},
        {"full_name": "Brian Schimpf", "title": "CEO"},
    ]
    out = merge_canonical(state)
    founders = out.team_people["founders"]
    # One Palmer (deduped, specter wins on title), one Brian
    palmers = [f for f in founders if f["full_name"].lower() == "palmer luckey"]
    assert len(palmers) == 1
    assert palmers[0]["title"] == "Founder & CEO"  # specter title
    assert palmers[0]["linkedin_url"] == "https://linkedin.com/in/palmerluckey"  # specter url
    # Brian filled from crunchbase
    brians = [f for f in founders if "brian" in f["full_name"].lower()]
    assert len(brians) == 1
