"""Deterministic pipeline nodes — Phase 2 Task 2.9.

Three non-agent nodes that bracket the LLM work:

  - ``resolve_company``  — find/create the canonical.company row and open an
    etl_run_log entry. Runs FIRST.
  - ``fetch_all``        — concurrently pull from the 4 in-process / MCP
    providers (Specter via MCP first, with in-process fallback baked into the
    client; Crunchbase / PitchBook / Attio in-process). Failures degrade to
    a DQFlag on the state; the pipeline never raises out of fetch.
  - ``render_and_persist`` — write canonical.pre_meeting_brief, close the
    etl_run_log. Runs LAST. If synthesis didn't produce a brief, marks the run
    log as failed and exits cleanly.

These three are intentionally separate from the Wave D agents — they are pure
plumbing, no LLM, and they own the only side-effects in the pipeline
(database writes). Keeping them here keeps ``graph.py`` a thin wiring layer.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from api.db.models import Company, DataQualityFlag, EtlRunLog, PreMeetingBrief
from api.db.session import SessionLocal
from api.pipeline.state import BriefState, DQFlag, ToolCall
from api.providers.attio import AttioProvider
from api.providers.crunchbase import CrunchbaseProvider
from api.providers.pitchbook import PitchBookProvider
from api.providers.specter_mcp_client import SpecterMcpClient


# ─────────────────────────────────────────────────────────────────────────────
# resolve_company
# ─────────────────────────────────────────────────────────────────────────────


async def resolve_company(state: BriefState) -> BriefState:
    """Find or insert the canonical company row, open an etl_run_log row.

    Sets ``state.company_id``, ``state.run_id``, ``state.started_at`` and
    records timing under ``state.timings["resolve_company"]``.
    """
    started = time.monotonic()

    async with SessionLocal() as session:
        existing = await session.scalar(
            select(Company).where(Company.domain == state.domain)
        )
        if existing is not None:
            state.company_id = existing.company_id
        else:
            new_company = Company(
                domain=state.domain,
                operating_status="active",
            )
            session.add(new_company)
            await session.flush()
            state.company_id = new_company.company_id

        # If the caller (e.g. the admin trigger endpoint) pre-created the
        # etl_run_log row and seeded ``state.run_id``, keep using that row
        # so the status endpoint can poll the same run_id throughout the
        # pipeline. Backfill company_id on the existing row if it wasn't
        # known up front. Otherwise (cron / direct invocation) open a new
        # row here as before.
        if state.run_id is None:
            run = EtlRunLog(company_id=state.company_id, status="running")
            session.add(run)
            await session.flush()
            state.run_id = run.run_id
            state.started_at = run.started_at
        else:
            existing_run = await session.get(EtlRunLog, state.run_id)
            if existing_run is not None and existing_run.company_id is None:
                existing_run.company_id = state.company_id
            if existing_run is not None and state.started_at is None:
                state.started_at = existing_run.started_at
        await session.commit()

    state.timings["resolve_company"] = time.monotonic() - started
    return state


# ─────────────────────────────────────────────────────────────────────────────
# fetch_all
# ─────────────────────────────────────────────────────────────────────────────


def _fixtures_dir() -> Path:
    """Repo-rooted ``fixtures/`` directory.

    api/pipeline/nodes.py → ../../fixtures
    """
    return Path(__file__).resolve().parent.parent.parent / "fixtures"


# Order matters for the gathered-results unpack below. Keep aligned with
# `_RAW_STATE_FIELDS`.
_PROVIDERS_ORDER: tuple[str, ...] = ("specter", "crunchbase", "pitchbook", "attio")
_RAW_STATE_FIELDS: dict[str, str] = {
    "specter": "specter_raw",
    "crunchbase": "crunchbase_raw",
    "pitchbook": "pitchbook_raw",
    "attio": "attio_raw",
}


async def _fetch_one(
    name: str, provider: Any, domain: str, hints: dict
) -> tuple[str, Any, float, str | None]:
    """Run one provider.fetch, returning (name, result, duration, error_str).

    Catching here (instead of leaning on ``asyncio.gather(return_exceptions=True)``
    alone) lets us measure each provider's latency individually for the audit
    trail. Anything raised is converted to ``error_str`` and the caller decides
    what to do (in fetch_all: emit a DQFlag, leave the raw field None).
    """
    started = time.monotonic()
    try:
        result = await provider.fetch(domain, hints)
        return name, result, time.monotonic() - started, None
    except Exception as exc:  # noqa: BLE001 — fan-out: never raise upward
        return name, None, time.monotonic() - started, f"{type(exc).__name__}: {exc}"


async def fetch_all(state: BriefState) -> BriefState:
    """Concurrently fetch from the 4 providers; populate ``state.*_raw``.

    Failures degrade gracefully: the corresponding ``*_raw`` stays ``None``
    and a medium-severity DQFlag is appended. Each provider's latency is
    recorded as a ToolCall entry.
    """
    started = time.monotonic()

    fixtures = _fixtures_dir()
    providers = {
        "specter": SpecterMcpClient(fixtures_dir=fixtures),
        "crunchbase": CrunchbaseProvider(fixtures_dir=fixtures),
        "pitchbook": PitchBookProvider(fixtures_dir=fixtures),
        "attio": AttioProvider(fixtures_dir=fixtures),
    }
    hints = {"name": state.company_name}

    coros = [
        _fetch_one(name, providers[name], state.domain, hints)
        for name in _PROVIDERS_ORDER
    ]
    results = await asyncio.gather(*coros, return_exceptions=False)

    for name, result, duration_s, error in results:
        raw_field = _RAW_STATE_FIELDS[name]
        if error is not None or result is None:
            # `None` from a provider is a legitimate "not in coverage" — only
            # an *exception* is a DQFlag-worthy fetch failure.
            if error is not None:
                state.data_quality_flags.append(
                    DQFlag(
                        field=f"{name}_fetch",
                        issue=error,
                        severity="medium",
                        source_a=name,
                    )
                )
            setattr(state, raw_field, None)
            output_summary = "no_data" if error is None else "error"
        else:
            setattr(state, raw_field, result.raw)
            output_summary = (
                f"raw_keys={len(result.raw)} normalized_keys={len(result.normalized)}"
            )

        state.tool_calls.append(
            ToolCall(
                agent="fetch_all",
                tool=f"provider.{name}.fetch",
                input_summary=f"domain={state.domain}",
                output_summary=output_summary,
                duration_ms=int(duration_s * 1000),
                timestamp=datetime.utcnow(),
                error=error,
            )
        )

    state.timings["fetch_all"] = time.monotonic() - started
    return state


# ─────────────────────────────────────────────────────────────────────────────
# render_and_persist
# ─────────────────────────────────────────────────────────────────────────────


def _audit_fields(d: dict | None) -> dict:
    """Surface the per-field provenance dict the brief reader expects.

    The canonical entity dicts carry an ``audit`` list under the ``audit`` key
    (see merge._audit). We re-wrap it under ``fields`` so the brief reader and
    the audit panel can iterate uniformly. When merge didn't run (qualification
    skipped, or fetch_all returned nothing), we degrade to an empty list.
    """
    if not isinstance(d, dict):
        return {"fields": []}
    audit = d.get("audit")
    if isinstance(audit, list):
        return {"fields": audit}
    # Fall back to listing all keys with no source attribution.
    return {
        "fields": [
            {"field": k, "source": "merged"} for k in d.keys() if k != "audit"
        ]
    }


async def render_and_persist(state: BriefState) -> BriefState:
    """Persist the final brief + close the etl_run_log.

    If ``state.brief_json`` is None (synthesis failed), the run log is
    marked ``failed`` and no PreMeetingBrief row is written. This is a
    terminal node — never raises.
    """
    started = time.monotonic()

    # ── Failure path: synthesis produced nothing ──────────────────────────
    if state.brief_json is None:
        if state.run_id is not None:
            async with SessionLocal() as session:
                run = await session.get(EtlRunLog, state.run_id)
                if run is not None:
                    run.status = "failed"
                    run.completed_at = datetime.utcnow()
                    run.error_message = state.error or "synthesis produced no brief"
                    await session.commit()
        state.timings["render_and_persist"] = time.monotonic() - started
        return state

    # ── Happy path: persist the brief ─────────────────────────────────────
    brief_json = state.brief_json
    async with SessionLocal() as session:
        brief = PreMeetingBrief(
            company_id=state.company_id,
            run_id=state.run_id,
            partner=state.partner,
            meeting_date=state.meeting_date,
            thesis_fit=brief_json.get("thesis_fit"),
            industry_deepdive=brief_json.get("industry_deepdive") or "",
            market_deepdive=brief_json.get("market_deepdive") or "",
            key_engagement_questions=brief_json.get("key_engagement_questions") or [],
            podcast_mentions=brief_json.get("podcast_mentions") or [],
            prior_interactions=brief_json.get("prior_interactions") or [],
            pre_meeting_brief=state.brief_html or "",
            pre_meeting_brief_link="",  # filled in after we have the brief_id
            google_drive_link="",
            attio_company_link="",
            audit_company=_audit_fields(state.company_profile),
            audit_people=_audit_fields(state.team_people),
            audit_traction_metrics=_audit_fields(state.traction_signals),
        )
        session.add(brief)
        await session.flush()
        state.brief_id = brief.brief_id
        brief.pre_meeting_brief_link = (
            f"/pre-meeting-brief/briefs/{brief.brief_id}"
        )

        # Persist data-quality flags emitted by merge_canonical + DQ agent.
        # Flags are first-class observability artifacts (see approach.md §3, §7.5)
        # and power the AuditPanel's FlagsTeaser.
        for flag in state.data_quality_flags:
            session.add(DataQualityFlag(
                run_id=state.run_id,
                company_id=state.company_id,
                field=flag.field,
                issue=flag.issue,
                severity=flag.severity,
                source_a=flag.source_a,
                value_a=str(flag.value_a) if flag.value_a is not None else None,
                source_b=flag.source_b,
                value_b=str(flag.value_b) if flag.value_b is not None else None,
            ))

        if state.run_id is not None:
            run = await session.get(EtlRunLog, state.run_id)
            if run is not None:
                run.status = "complete"
                run.completed_at = datetime.utcnow()
        await session.commit()

    state.timings["render_and_persist"] = time.monotonic() - started
    return state
