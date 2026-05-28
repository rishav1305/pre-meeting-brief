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
