"""Admin trigger + status endpoints — Phase 2 Task 2.10.

Two endpoints:

  POST /api/triggers/manual
      Kicks off a pipeline run for a domain. Body validated by
      :class:`TriggerBody`; password gated by the ``X-Admin-Password`` header
      against ``settings.admin_password``. Returns 202 + run_id immediately
      and runs the pipeline in the background via FastAPI's BackgroundTasks.

  GET  /api/triggers/runs/{run_id}
      Polling endpoint for the admin UI. Returns the etl_run_log row plus a
      pointer to the produced PreMeetingBrief (if any).

Both routes live under the same prefixes as the rest of /api/* (see
:mod:`api.index`). The trigger endpoint pre-creates the ``etl_run_log`` row
*here* so the HTTP response can include the run_id before the pipeline
finishes. ``run_pipeline`` is called with that run_id; ``resolve_company``
reuses the row instead of opening a new one.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, select

from api.config import settings
from api.db.models import CalendarEvent, Company, EtlRunLog, PreMeetingBrief
from api.db.session import SessionLocal
from api.pipeline.graph import run_pipeline


router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────────────────


def require_admin(x_admin_password: str | None) -> None:
    """Validate the X-Admin-Password header against settings.admin_password.

    Raises:
        HTTPException 503 if admin auth is not configured (empty setting).
        HTTPException 401 if the header is missing or wrong.
    """
    if not settings.admin_password:
        raise HTTPException(status_code=503, detail="admin auth not configured")
    if x_admin_password != settings.admin_password:
        raise HTTPException(status_code=401, detail="invalid admin password")


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/triggers/manual
# ─────────────────────────────────────────────────────────────────────────────


class TriggerBody(BaseModel):
    """Body for POST /api/triggers/manual."""
    domain: str = Field(..., min_length=1)
    company_name: str = Field(..., min_length=1)
    partner: str = Field(..., min_length=1)
    meeting_date: date


class TriggerResponse(BaseModel):
    run_id: UUID
    status_url: str


@router.post("/triggers/manual", status_code=202, response_model=TriggerResponse)
async def trigger_manual(
    body: TriggerBody,
    background_tasks: BackgroundTasks,
    x_admin_password: str | None = Header(default=None, alias="X-Admin-Password"),
) -> TriggerResponse:
    """Pre-create an etl_run_log row, kick off the pipeline in the background.

    The endpoint returns 202 immediately with the run_id and a polling URL.
    The actual pipeline runs via FastAPI's BackgroundTasks — fire-and-forget
    from the request's perspective.
    """
    require_admin(x_admin_password)

    # Pre-create the etl_run_log row so we can return the run_id up front.
    # We do NOT link a company_id here — resolve_company will backfill it
    # once the canonical row exists (matches the surgical edit in nodes.py).
    async with SessionLocal() as session:
        run = EtlRunLog(company_id=None, status="running")
        session.add(run)
        await session.flush()
        run_id = run.run_id
        await session.commit()

    # Kick off the pipeline as a fire-and-forget background task.
    background_tasks.add_task(
        run_pipeline,
        company_name=body.company_name,
        domain=body.domain,
        meeting_date=body.meeting_date,
        partner=body.partner,
        run_id=run_id,
    )

    return TriggerResponse(
        run_id=run_id,
        status_url=f"/api/triggers/runs/{run_id}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/triggers/scan — Vercel Cron entry point
# ─────────────────────────────────────────────────────────────────────────────


class ScanEvent(BaseModel):
    event_id: UUID
    partner: str
    company_domain: str
    meeting_date: date
    action: str  # one of: "triggered" | "skipped_existing_brief" | "skipped_recent_engagement"
    run_id: UUID | None = None
    reason: str | None = None


class ScanResponse(BaseModel):
    scanned_at: str
    horizon_days: int
    candidates: int
    triggered: int
    skipped: int
    events: list[ScanEvent]


def _company_name_from_domain(domain: str) -> str:
    """Cheap derivation for the trigger payload — the pipeline normalizes
    domain on resolve_company anyway, but the run_pipeline signature wants
    a name. Production replaces this with an Attio lookup or a lookup table.
    """
    base = domain.split(".")[0]
    return base[:1].upper() + base[1:]


@router.get("/triggers/scan", response_model=ScanResponse)
async def scan_calendar(
    background_tasks: BackgroundTasks,
    horizon_days: int = Query(1, ge=1, le=14, description="how many days ahead to scan"),
    dry_run: bool = Query(False, description="if true, report candidates without triggering"),
) -> ScanResponse:
    """Calendar-driven trigger detection — daily cron entry point.

    Walks ``canonical.calendar_events`` for events in the next ``horizon_days``,
    and for each event:
      1. Skips if a ``pre_meeting_brief`` already exists for
         ``(partner, meeting_date)`` matching the event's company_domain —
         idempotent re-runs.
      2. Otherwise kicks off ``run_pipeline`` via FastAPI BackgroundTasks.
         The pipeline's own Qualification Agent applies the 3-month rule;
         this endpoint stops short of duplicating that logic so the agent
         remains the source of truth.

    The Vercel Cron config in ``vercel.json`` invokes this at 06:00 UTC daily.
    The endpoint is intentionally unauthenticated — Vercel Cron does not pass
    the admin password header, and the call surface is read-mostly: the only
    side effect is triggering pipeline runs for events that pass the
    qualification gate, which is the entire point of the daily sweep.
    """
    today = date.today()
    end_window = today + timedelta(days=horizon_days)
    scanned_events: list[ScanEvent] = []
    triggered_count = 0
    skipped_count = 0

    async with SessionLocal() as session:
        rows = await session.scalars(
            select(CalendarEvent).where(
                and_(
                    CalendarEvent.meeting_date >= today,
                    CalendarEvent.meeting_date <= end_window,
                )
            )
        )
        events = rows.all()

        for ev in events:
            company = await session.scalar(
                select(Company).where(Company.domain == ev.company_domain)
            )
            existing_brief = None
            if company is not None:
                existing_brief = await session.scalar(
                    select(PreMeetingBrief).where(
                        and_(
                            PreMeetingBrief.company_id == company.company_id,
                            PreMeetingBrief.partner == ev.partner,
                            PreMeetingBrief.meeting_date == ev.meeting_date,
                        )
                    )
                )
            if existing_brief is not None:
                scanned_events.append(
                    ScanEvent(
                        event_id=ev.event_id,
                        partner=ev.partner,
                        company_domain=ev.company_domain,
                        meeting_date=ev.meeting_date,
                        action="skipped_existing_brief",
                        reason=f"brief {str(existing_brief.brief_id)[:8]}… already exists",
                    )
                )
                skipped_count += 1
                continue

            if dry_run:
                scanned_events.append(
                    ScanEvent(
                        event_id=ev.event_id,
                        partner=ev.partner,
                        company_domain=ev.company_domain,
                        meeting_date=ev.meeting_date,
                        action="triggered",
                        reason="dry_run — would have triggered",
                    )
                )
                continue

            # Pre-create the run log so we can return the run_id in the scan
            # response (identical pattern to /triggers/manual).
            run = EtlRunLog(company_id=None, status="running")
            session.add(run)
            await session.flush()
            run_id_local = run.run_id
            await session.commit()

            # Fire-and-forget via BackgroundTasks — same pattern as
            # /triggers/manual. Vercel Cron requests run inside a normal
            # request scope, so BackgroundTasks honors them.
            background_tasks.add_task(
                run_pipeline,
                company_name=_company_name_from_domain(ev.company_domain),
                domain=ev.company_domain,
                meeting_date=ev.meeting_date,
                partner=ev.partner,
                run_id=run_id_local,
            )

            scanned_events.append(
                ScanEvent(
                    event_id=ev.event_id,
                    partner=ev.partner,
                    company_domain=ev.company_domain,
                    meeting_date=ev.meeting_date,
                    action="triggered",
                    run_id=run_id_local,
                    reason="no existing brief; qualification agent will gate downstream",
                )
            )
            triggered_count += 1

    return ScanResponse(
        scanned_at=datetime.utcnow().isoformat() + "Z",
        horizon_days=horizon_days,
        candidates=len(scanned_events),
        triggered=triggered_count,
        skipped=skipped_count,
        events=scanned_events,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/triggers/runs/{run_id}
# ─────────────────────────────────────────────────────────────────────────────


class RunStatusResponse(BaseModel):
    run_id: UUID
    status: str
    started_at: str | None
    completed_at: str | None
    error_message: str | None
    company_id: UUID | None
    brief_id: UUID | None
    # Phase 3: per-node progress written incrementally by api.pipeline.progress
    current_node: str | None = None
    node_history: list[dict] = Field(default_factory=list)
    # TODO: Phase 3 will wire tool_calls table; for now we return [].
    recent_tool_calls: list[dict] = Field(default_factory=list)


@router.get("/triggers/runs/{run_id}", response_model=RunStatusResponse)
async def get_run_status(run_id: UUID) -> RunStatusResponse:
    """Return current status for a pipeline run.

    Returns 404 if the run_id is unknown.
    """
    async with SessionLocal() as session:
        run = await session.get(EtlRunLog, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")

        # Look up a brief produced by this run, if any (1 row at most by
        # construction — pre_meeting_brief.run_id is unique per pipeline
        # invocation in practice; if multiple exist we take the newest).
        brief = await session.scalar(
            select(PreMeetingBrief)
            .where(PreMeetingBrief.run_id == run_id)
            .order_by(PreMeetingBrief.generated_ts.desc())
        )

        return RunStatusResponse(
            run_id=run.run_id,
            status=run.status,
            started_at=run.started_at.isoformat() if run.started_at else None,
            completed_at=run.completed_at.isoformat() if run.completed_at else None,
            error_message=run.error_message,
            company_id=run.company_id,
            brief_id=brief.brief_id if brief else None,
            current_node=run.current_node,
            node_history=list(run.node_history or []),
            recent_tool_calls=[],
        )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/triggers/runs — list recent runs across all partners
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/triggers/runs")
async def list_runs(limit: int = Query(10, ge=1, le=50)) -> dict:
    """Return the most recent N pipeline runs across all partners.

    Joined LEFT-OUTER to company (for company_domain) and pre_meeting_brief
    (for brief_id + partner). Runs that haven't resolved a company or
    produced a brief still show — the joined columns simply come back null.

    Used by the Recent Runs panel on /admin so reviewers can see what
    happened without knowing specific run_ids up front. No auth — the panel
    is rendered only after the password gate, and the data is non-sensitive
    (run ids, statuses, domains, partner names).
    """
    async with SessionLocal() as session:
        rows = await session.execute(
            select(
                EtlRunLog.run_id,
                EtlRunLog.started_at,
                EtlRunLog.completed_at,
                EtlRunLog.status,
                EtlRunLog.current_node,
                Company.domain.label("company_domain"),
                PreMeetingBrief.brief_id,
                PreMeetingBrief.partner,
            )
            .join(Company, Company.company_id == EtlRunLog.company_id, isouter=True)
            .join(
                PreMeetingBrief,
                PreMeetingBrief.run_id == EtlRunLog.run_id,
                isouter=True,
            )
            .order_by(EtlRunLog.started_at.desc())
            .limit(limit)
        )

        items: list[dict] = []
        for r in rows:
            duration_ms: int | None = None
            if r.completed_at and r.started_at:
                duration_ms = int(
                    (r.completed_at - r.started_at).total_seconds() * 1000
                )
            items.append(
                {
                    "run_id": str(r.run_id),
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "completed_at": (
                        r.completed_at.isoformat() if r.completed_at else None
                    ),
                    "status": r.status,
                    "duration_ms": duration_ms,
                    "partner": r.partner,
                    "company_domain": r.company_domain,
                    "brief_id": str(r.brief_id) if r.brief_id else None,
                    "current_node": r.current_node,
                }
            )
        return {"items": items}
