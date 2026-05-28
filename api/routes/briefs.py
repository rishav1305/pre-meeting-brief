"""Brief detail route — fetch one brief with company/people/traction context."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    Company,
    DataQualityFlag,
    People,
    PreMeetingBrief,
    TractionMetrics,
)
from api.db.session import get_session

router = APIRouter()


@router.get("/briefs/{brief_id}")
async def get_brief(
    brief_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    brief = await session.get(PreMeetingBrief, brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    company = await session.get(Company, brief.company_id)
    people = await session.get(People, brief.company_id)
    traction = await session.get(TractionMetrics, brief.company_id)

    # Pull DQ flags written by render_and_persist (matched on run_id, since
    # the brief itself is run-pinned and so are the flags). Severity ordering
    # is high → medium → low so the AuditPanel shows the worst first.
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    flag_rows = (
        await session.scalars(
            select(DataQualityFlag).where(DataQualityFlag.run_id == brief.run_id)
        )
    ).all() if brief.run_id else []
    flags_payload = [
        {
            "field": f.field,
            "issue": f.issue,
            "severity": f.severity,
            "source_a": f.source_a,
            "value_a": f.value_a,
            "source_b": f.source_b,
            "value_b": f.value_b,
        }
        for f in sorted(flag_rows, key=lambda r: severity_rank.get(r.severity, 99))
    ]

    return {
        "brief_id": str(brief.brief_id),
        "partner": brief.partner,
        "meeting_date": brief.meeting_date.isoformat(),
        "generated_at": brief.generated_ts.isoformat(),
        "company": {
            "domain": company.domain if company else None,
            "description": company.description if company else None,
            "operating_status": company.operating_status if company else None,
            "founded_year": company.founded_year if company else None,
            "hq_city": company.hq_city if company else None,
            "hq_country": company.hq_country if company else None,
            "tags": company.tags if company else None,
            "growth_stage": company.growth_stage if company else None,
            "investors": company.investors if company else None,
            "total_raised_usd": company.total_raised_usd if company else None,
            "last_round_type": company.last_round_type if company else None,
            "post_money_valuation_usd": company.post_money_valuation_usd if company else None,
        },
        "people": {
            "founders": people.founders if people else None,
            "employee_count": people.employee_count if people else None,
            "employee_range": people.employee_range if people else None,
        } if people else None,
        "traction": {
            "highlights": traction.highlights if traction else None,
            "new_highlights": traction.new_highlights if traction else None,
            "linkedin_followers": traction.linkedin_followers if traction else None,
            "news": traction.news if traction else None,
        } if traction else None,
        "thesis_fit": brief.thesis_fit,
        "industry_deepdive": brief.industry_deepdive,
        "market_deepdive": brief.market_deepdive,
        "key_engagement_questions": brief.key_engagement_questions,
        "podcast_mentions": brief.podcast_mentions,
        "prior_interactions": brief.prior_interactions,
        "audit_company": brief.audit_company,
        "audit_people": brief.audit_people,
        "audit_traction_metrics": brief.audit_traction_metrics,
        "data_quality_flags": flags_payload,
        "distribution_log": brief.distribution_log or [],
    }
