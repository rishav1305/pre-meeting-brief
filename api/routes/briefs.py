"""Brief detail route — fetch one brief with company/people/traction context."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Company, People, PreMeetingBrief, TractionMetrics
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
    }
