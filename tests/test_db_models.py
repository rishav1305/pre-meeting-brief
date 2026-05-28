from uuid import uuid4

import pytest

from api.db.models import Company


@pytest.mark.asyncio
async def test_company_insert_and_select(db_session):
    company = Company(
        company_id=uuid4(),
        domain="anduril.com",
        description="Defense technology company",
        operating_status="active",
        founded_year=2017,
        hq_country="US",
        total_raised_usd=4_200_000_000,
        last_round_type="series_f",
        investors=["Founders Fund", "Andreessen Horowitz", "Valor Equity Partners"],
        audit={"fields": [{"field": "description", "source": "Specter"}]},
    )
    db_session.add(company)
    await db_session.commit()

    fetched = await db_session.get(Company, company.company_id)
    assert fetched is not None
    assert fetched.domain == "anduril.com"
    assert fetched.investors == ["Founders Fund", "Andreessen Horowitz", "Valor Equity Partners"]
    assert fetched.audit["fields"][0]["source"] == "Specter"


from datetime import date

from api.db.models import People, TractionMetrics


@pytest.mark.asyncio
async def test_people_insert_and_select(db_session):
    company_id = uuid4()
    db_session.add(
        Company(
            company_id=company_id,
            domain="hadrian.co",
            operating_status="active",
        )
    )
    await db_session.commit()

    people = People(
        company_id=company_id,
        founders=[
            {"full_name": "Chris Power", "title": "CEO", "linkedin_url": "https://..."},
        ],
        employee_count=180,
        employee_range="51-200",
        hiring_signals=["engineering_hiring", "headcount_surge"],
        audit={"fields": [{"field": "founders", "source": "Specter"}]},
    )
    db_session.add(people)
    await db_session.commit()

    fetched = await db_session.get(People, company_id)
    assert fetched is not None
    assert fetched.employee_count == 180
    assert fetched.founders[0]["full_name"] == "Chris Power"


@pytest.mark.asyncio
async def test_traction_metrics_insert_and_select(db_session):
    company_id = uuid4()
    db_session.add(Company(company_id=company_id, domain="modal.com", operating_status="active"))
    await db_session.commit()

    tm = TractionMetrics(
        company_id=company_id,
        highlights=["headcount_surge", "strong_web_traffic_growth"],
        new_highlights=["enterprise_logo_added"],
        web_visits_latest=480_000,
        g2_rating=4.7,
        g2_review_count=120,
        news=[{"date": "2026-05-10", "title": "...", "url": "https://..."}],
        audit={"fields": [{"field": "highlights", "source": "Specter"}]},
    )
    db_session.add(tm)
    await db_session.commit()

    fetched = await db_session.get(TractionMetrics, company_id)
    assert fetched is not None
    assert fetched.g2_rating == 4.7
    assert "headcount_surge" in fetched.highlights


from datetime import date as date_type

from api.db.models import (
    CalendarEvent,
    DataQualityFlag,
    EtlRunLog,
    PreMeetingBrief,
    SourcePayload,
)


@pytest.mark.asyncio
async def test_etl_run_log(db_session):
    company_id = uuid4()
    db_session.add(Company(company_id=company_id, domain="ramp.com", operating_status="active"))
    await db_session.commit()

    run_id = uuid4()
    db_session.add(
        EtlRunLog(
            run_id=run_id,
            company_id=company_id,
            status="running",
        )
    )
    await db_session.commit()

    fetched = await db_session.get(EtlRunLog, run_id)
    assert fetched is not None
    assert fetched.status == "running"


@pytest.mark.asyncio
async def test_data_quality_flag(db_session):
    company_id = uuid4()
    db_session.add(Company(company_id=company_id, domain="glean.com", operating_status="active"))
    await db_session.commit()

    flag = DataQualityFlag(
        flag_id=uuid4(),
        run_id=uuid4(),
        company_id=company_id,
        field="founded_year",
        issue="delta_gt_1_year",
        source_a="Specter",
        value_a="2019",
        source_b="Crunchbase",
        value_b="2021",
    )
    db_session.add(flag)
    await db_session.commit()

    fetched = await db_session.get(DataQualityFlag, flag.flag_id)
    assert fetched.field == "founded_year"


@pytest.mark.asyncio
async def test_calendar_event(db_session):
    company_id = uuid4()
    db_session.add(Company(company_id=company_id, domain="mercury.com", operating_status="active"))
    await db_session.commit()

    event = CalendarEvent(
        event_id=uuid4(),
        partner="Devon",
        company_domain="mercury.com",
        meeting_date=date_type(2026, 5, 30),
        attendees={"emails": ["devon@renegade.vc", "founder@mercury.com"]},
        source="manual_seed",
    )
    db_session.add(event)
    await db_session.commit()

    fetched = await db_session.get(CalendarEvent, event.event_id)
    assert fetched.partner == "Devon"


@pytest.mark.asyncio
async def test_pre_meeting_brief(db_session):
    company_id = uuid4()
    db_session.add(Company(company_id=company_id, domain="anduril.com", operating_status="active"))
    await db_session.commit()

    brief = PreMeetingBrief(
        brief_id=uuid4(),
        company_id=company_id,
        run_id=uuid4(),
        partner="Sara",
        meeting_date=date_type(2026, 5, 30),
        thesis_fit={"score": 5, "reasoning": "core thesis", "bear_case": "regulatory"},
        industry_deepdive="Defense software is...",
        market_deepdive="The defense tech market...",
        key_engagement_questions=["Q1", "Q2", "Q3"],
        podcast_mentions=[],
        prior_interactions=[],
        pre_meeting_brief="<html>...</html>",
        pre_meeting_brief_link="https://rishavchatterjee.com/pre-meeting-brief/briefs/...",
        google_drive_link="",
        attio_company_link="",
    )
    db_session.add(brief)
    await db_session.commit()

    fetched = await db_session.get(PreMeetingBrief, brief.brief_id)
    assert fetched.thesis_fit["score"] == 5


@pytest.mark.asyncio
async def test_source_payload(db_session):
    company_id = uuid4()
    db_session.add(Company(company_id=company_id, domain="hadrian.co", operating_status="active"))
    await db_session.commit()

    db_session.add(
        SourcePayload(
            payload_id=uuid4(),
            company_id=company_id,
            source="specter",
            raw={"id": "spec_123", "name": "Hadrian"},
        )
    )
    await db_session.commit()
