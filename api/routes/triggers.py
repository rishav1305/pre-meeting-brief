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

from datetime import date
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.config import settings
from api.db.models import EtlRunLog, PreMeetingBrief
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
            recent_tool_calls=[],
        )
