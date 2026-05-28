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
