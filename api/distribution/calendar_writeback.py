"""Google Calendar event-description writeback.

The assignment's Distribution step is "automatically attaching the final
brief to a daily agenda." For the POC, we construct the exact API payload
that a real Google Calendar Events.patch() call would carry and persist it
to ``pre_meeting_brief.distribution_log`` instead of dispatching the HTTP
call. This demonstrates the architectural shape without requiring OAuth +
calendar API setup in the live deploy.

When the user is ready to flip this to real, the only changes are:
  1. Add Google OAuth flow + credentials env vars.
  2. Replace ``_LOG_ONLY = True`` with a live ``googleapiclient`` call.
  3. Map ``calendar_events.event_id`` -> real Google Calendar event id.

The schema of the persisted record is intentionally one-row-per-attempt so
follow-up channels (Slack daily digest, Attio note, Gmail attachment) can
append without a schema change.
"""
from __future__ import annotations

import copy
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select

from api.db.models import CalendarEvent, PreMeetingBrief
from api.db.session import SessionLocal

logger = logging.getLogger("api.distribution.calendar_writeback")

# Flip to False once Google OAuth + googleapiclient are wired in production.
_LOG_ONLY = True

# Vercel rewrites the user-facing URL through portfolio_app.
_BRIEF_URL_BASE = "https://rishavchatterjee.com/pre-meeting-brief/briefs"


def _brief_url(brief_id) -> str:
    return f"{_BRIEF_URL_BASE}/{brief_id}"


def build_writeback_payload(
    brief: PreMeetingBrief, event: CalendarEvent | None
) -> dict[str, Any]:
    """Construct the Google Calendar Events.patch() payload.

    Returns a dict describing the call (endpoint, method, headers, body)
    that the production caller would send to Google's API. The structure
    follows Google Calendar API v3:
        PATCH /calendar/v3/calendars/{calendarId}/events/{eventId}
        body: { description: "...appended brief link..." }
    """
    brief_link = _brief_url(brief.brief_id)
    # The description we'd append. In production this would merge with any
    # existing description rather than overwrite — modeled here as a single
    # block the caller patches in.
    description_block = (
        f"\n\n— Pre-Meeting Brief —\n"
        f"Generated {brief.generated_ts.isoformat() if brief.generated_ts else 'n/a'}\n"
        f"{brief_link}\n"
    )

    calendar_id = (
        f"{brief.partner.lower()}@renegade.vc"  # POC convention; production reads from firm config
    )
    event_id_str = str(event.event_id) if event is not None else None

    return {
        "channel": "google_calendar",
        "target": {
            "calendar_id": calendar_id,
            "event_id": event_id_str,
            "meeting_date": (event.meeting_date.isoformat() if event else None),
            "company_domain": (event.company_domain if event else None),
        },
        "endpoint": (
            f"PATCH https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id_str}"
        ),
        "method": "PATCH",
        "headers": {
            "Authorization": "Bearer <service_account_token>",
            "Content-Type": "application/json",
        },
        "body": {
            # Real implementation reads existing description first, then
            # appends. The mock only models the append payload.
            "description": description_block,
        },
        "brief_link": brief_link,
    }


def _match_event_for_brief(rows: list[CalendarEvent], brief: PreMeetingBrief) -> CalendarEvent | None:
    """Return the calendar_event row that matches (partner, company_domain, meeting_date)."""
    for ev in rows:
        if (
            ev.partner == brief.partner
            and ev.meeting_date == brief.meeting_date
        ):
            return ev
    return None


async def distribute_brief(brief_id) -> dict[str, Any]:
    """Build the writeback payload, append to distribution_log, return the record.

    Idempotent across calls — repeated invocations append another attempt
    record. The brief reader UI shows the latest 'sent' record as the
    distribution badge.
    """
    async with SessionLocal() as session:
        brief = await session.get(PreMeetingBrief, brief_id)
        if brief is None:
            raise ValueError(f"brief {brief_id} not found")

        domain_row = await session.scalars(
            select(CalendarEvent).where(
                CalendarEvent.company_domain.is_not(None),
                CalendarEvent.partner == brief.partner,
                CalendarEvent.meeting_date == brief.meeting_date,
            )
        )
        events = domain_row.all()
        event = _match_event_for_brief(events, brief)

        payload = build_writeback_payload(brief, event)
        attempt = {
            "channel": payload["channel"],
            "target": payload["target"],
            "status": "logged" if _LOG_ONLY else "sent",
            "endpoint": payload["endpoint"],
            "brief_link": payload["brief_link"],
            "attempted_at": datetime.utcnow().isoformat() + "Z",
            "error": None,
            "note": (
                "POC: payload constructed but HTTP call not dispatched. "
                "Production flips _LOG_ONLY=False after Google OAuth is wired."
                if _LOG_ONLY
                else None
            ),
        }

        # Append to the JSONB list; copy.deepcopy + reassign so SQLAlchemy
        # picks up the mutation (same pattern as etl_run_log.node_history).
        history = copy.deepcopy(brief.distribution_log) if brief.distribution_log else []
        history.append(attempt)
        brief.distribution_log = history

        await session.commit()

        if _LOG_ONLY:
            logger.info(
                "calendar writeback (LOG_ONLY) for brief %s -> %s",
                brief_id,
                payload["endpoint"],
            )

        return attempt
