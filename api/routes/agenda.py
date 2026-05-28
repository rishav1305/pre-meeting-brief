"""Agenda route — next-14-day calendar events for a partner with brief preview data."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CalendarEvent, Company, PreMeetingBrief
from api.db.session import get_session

router = APIRouter()


@router.get("/agenda")
async def get_agenda(
    partner: str = Query(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    today = date.today()
    horizon = today + timedelta(days=14)

    # Get events for this partner in the next 14 days
    events_q = (
        select(CalendarEvent)
        .where(CalendarEvent.partner == partner)
        .where(CalendarEvent.meeting_date >= today)
        .where(CalendarEvent.meeting_date <= horizon)
        .order_by(CalendarEvent.meeting_date)
    )
    events = (await session.scalars(events_q)).all()

    # For each event, look up the brief (if any) and the company (for the preview card)
    items = []
    for event in events:
        company = await session.scalar(
            select(Company).where(Company.domain == event.company_domain)
        )
        brief = None
        if company:
            brief = await session.scalar(
                select(PreMeetingBrief)
                .where(PreMeetingBrief.company_id == company.company_id)
                .where(PreMeetingBrief.meeting_date == event.meeting_date)
                .order_by(PreMeetingBrief.generated_ts.desc())
            )
        items.append(
            {
                "event_id": str(event.event_id),
                "meeting_date": event.meeting_date.isoformat(),
                "company_domain": event.company_domain,
                "company_description": company.description if company else None,
                "company_stage": (company.growth_stage if company else None),
                "company_last_round": (company.last_round_type if company else None),
                "thesis_fit_score": (
                    brief.thesis_fit.get("score") if brief and brief.thesis_fit else None
                ),
                "brief_id": str(brief.brief_id) if brief else None,
            }
        )

    return {"partner": partner, "items": items}
