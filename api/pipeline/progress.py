"""Progress tracker that writes per-node events to etl_run_log.node_history.

The Phase 2 pipeline only persisted state.tool_calls at the end. This
adds incremental writes — every node calls record_node_start() on entry
and record_node_complete() / record_node_failed() on exit. The admin UI
polls etl_run_log and renders the live node_history as a real timeline.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from api.db.models import EtlRunLog
from api.db.session import SessionLocal


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def record_node_start(run_id: UUID | None, node: str, message: str = "") -> None:
    """Append a 'running' entry for the node. Idempotent on already-running."""
    if run_id is None:
        return
    async with SessionLocal() as session:
        row = await session.get(EtlRunLog, run_id)
        if row is None:
            return
        history = list(row.node_history or [])
        # Avoid duplicate consecutive 'running' entries for the same node
        if history and history[-1].get("node") == node and history[-1].get("status") == "running":
            return
        history.append({
            "node": node,
            "status": "running",
            "started_at": _utcnow_iso(),
            "completed_at": None,
            "duration_ms": None,
            "message": message,
        })
        row.node_history = history
        row.current_node = node
        await session.commit()


async def record_node_complete(run_id: UUID | None, node: str, message: str = "") -> None:
    """Mark the most recent matching 'running' entry as 'complete'."""
    if run_id is None:
        return
    async with SessionLocal() as session:
        row = await session.get(EtlRunLog, run_id)
        if row is None:
            return
        # Deep copy so SQLAlchemy sees a brand-new list+dicts and flushes the
        # JSONB column. Without this, in-place mutation of returned-dict-refs
        # is invisible to the change-detection layer (no MutableList tracking).
        history = copy.deepcopy(list(row.node_history or []))
        for entry in reversed(history):
            if entry.get("node") == node and entry.get("status") == "running":
                started = entry.get("started_at")
                completed = _utcnow_iso()
                entry["status"] = "complete"
                entry["completed_at"] = completed
                if started:
                    try:
                        d = datetime.fromisoformat(completed) - datetime.fromisoformat(started)
                        entry["duration_ms"] = int(d.total_seconds() * 1000)
                    except Exception:
                        entry["duration_ms"] = None
                if message:
                    entry["message"] = message
                break
        row.node_history = history
        row.current_node = node
        await session.commit()


async def record_node_failed(run_id: UUID | None, node: str, error: str) -> None:
    if run_id is None:
        return
    async with SessionLocal() as session:
        row = await session.get(EtlRunLog, run_id)
        if row is None:
            return
        # Deep copy — see record_node_complete for the why.
        history = copy.deepcopy(list(row.node_history or []))
        for entry in reversed(history):
            if entry.get("node") == node and entry.get("status") == "running":
                entry["status"] = "failed"
                entry["completed_at"] = _utcnow_iso()
                entry["message"] = f"FAILED: {error[:200]}"
                break
        row.node_history = history
        row.current_node = node
        await session.commit()


# Per-node message templates — used by graph.py's wrapper. Each function takes
# the BriefState and returns a human-readable string summarizing what just
# happened. Called when recording the 'complete' event.
def message_for(node: str, state: Any) -> str:
    if node == "resolve_company":
        return f"Normalized domain → company_id {str(state.company_id or '')[:8]}…, opened run log"
    if node == "qualification":
        return f"Decision: {state.qualification or '?'} — {(state.qualification_reason or '')[:80]}"
    if node == "fetch_all":
        sources_ok = []
        for src in ("specter", "crunchbase", "pitchbook", "attio"):
            raw = getattr(state, f"{src}_raw", None)
            sources_ok.append(f"{src}{'✓' if raw else '✗'}")
        return f"Concurrent fetch: {', '.join(sources_ok)}"
    if node == "research":
        n_cites = len(state.web_citations or [])
        n_chars = len(state.web_raw or "")
        return f"Web research: {n_cites} citations, {n_chars} chars of summary"
    if node == "merge":
        n_flags = len(state.data_quality_flags or [])
        return f"Deterministic merge → {n_flags} DQ flag(s) emitted"
    if node == "data_quality":
        n_ranked = len(state.dq_ranked or [])
        return f"Ranked {n_ranked} flag(s) by severity"
    if node == "synthesise":
        score = (state.brief_json or {}).get("thesis_fit", {}).get("score") if state.brief_json else None
        return f"Claude tool_use synthesis → thesis_fit score={score or '?'}/5"
    if node == "render_persist":
        return f"Persisted brief_id {str(state.brief_id or '')[:8]}…"
    if node == "distribute":
        if state.brief_id is None:
            return "Distribution skipped — no brief to attach"
        return f"Calendar writeback queued for {state.partner}'s {state.meeting_date} event"
    return ""
