"""Qualification Agent — decides whether a calendar event qualifies as a
"first meeting with company in rolling 3-month window."

Hybrid design (see docs/superpowers/plans/2026-05-28-pmb-phase-2.md §2.4):

  1. Deterministic prefilter (no LLM cost): if any interaction in
     state.attio_raw["interactions"] falls within the last 90 days of
     the meeting, skip immediately. This is the overwhelmingly common
     case and the cheap path.

  2. LLM judgment (Haiku 4.5) for edge cases — empty interaction history
     or all interactions older than 90 days. The LLM gets the full
     interactions array as JSON and decides proceed / skip / flag.

  3. Failure mode: if the LLM call raises, default to "proceed" — never
     block the pipeline on a qualification hiccup. The reason field
     records the fallback so it surfaces in the audit UI.
"""
from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta
from typing import Any

from api.llm import CHEAP_MODEL, get_client
from api.pipeline.state import BriefState, ToolCall

_PREFILTER_WINDOW_DAYS = 90
_LLM_MAX_TOKENS = 256
_LLM_TIMEOUT_S = 30.0
_INPUT_SUMMARY_CAP = 240
_OUTPUT_SUMMARY_CAP = 240


def _parse_iso_date(value: Any) -> date | None:
    """Tolerant ISO-date parser. Accepts plain dates (YYYY-MM-DD) and
    datetime strings; returns None on anything unparseable."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _most_recent_interaction(interactions: list[dict]) -> date | None:
    """Return the most recent parseable interaction date, or None."""
    dates = [d for d in (_parse_iso_date(i.get("date")) for i in interactions) if d]
    return max(dates) if dates else None


def _build_prompt(company_name: str, meeting_date: date, interactions: list[dict]) -> str:
    return (
        "You are gating a VC's pre-meeting brief pipeline.\n\n"
        f"Company: {company_name}\n"
        f"Upcoming meeting date: {meeting_date.isoformat()}\n\n"
        "Recent interaction history (may be empty):\n"
        f"{json.dumps(interactions, default=str, indent=2)}\n\n"
        "Decide whether this qualifies as a first meeting (rolling 3-month window).\n"
        "Edge cases to think about:\n"
        "  - Old conference handshake (>90d) → usually proceed.\n"
        "  - Internal note saying we 'passed' on a previous round → flag_for_human.\n"
        "  - Co-investor intro email, no direct engagement → proceed.\n"
        "  - Founder spoke at our event, no 1-on-1 → borderline; lean proceed.\n\n"
        'Respond with ONLY a JSON object, no prose, no markdown fences:\n'
        '{"decision": "proceed" | "skip" | "flag_for_human", '
        '"reason": "<one sentence>"}\n'
    )


def _parse_llm_json(raw_text: str) -> dict:
    """Tolerantly extract the JSON object from the LLM's text response.
    Falls back to a substring slice if the model wrapped the JSON in
    prose or fences."""
    text = raw_text.strip()
    # Strip markdown code fences if present.
    if text.startswith("```"):
        lines = text.splitlines()
        # drop opening fence and any language tag
        lines = lines[1:]
        # drop closing fence if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _truncate(s: str, cap: int) -> str:
    return s if len(s) <= cap else s[: cap - 1] + "…"


async def qualification_agent(state: BriefState) -> BriefState:
    """Sets state.qualification and state.qualification_reason.

    Pure mutation — returns the same state object for chaining inside the
    LangGraph pipeline.
    """
    started = time.perf_counter()

    interactions: list[dict] = []
    if state.attio_raw and isinstance(state.attio_raw.get("interactions"), list):
        interactions = state.attio_raw["interactions"]

    # ── Step 1: deterministic prefilter ────────────────────────────────
    most_recent = _most_recent_interaction(interactions)
    if most_recent is not None:
        delta = state.meeting_date - most_recent
        if timedelta(days=0) <= delta <= timedelta(days=_PREFILTER_WINDOW_DAYS):
            state.qualification = "skip"
            state.qualification_reason = f"recent interaction on {most_recent.isoformat()}"
            state.timings["qualification"] = time.perf_counter() - started
            return state

    # ── Step 2: LLM judgment ───────────────────────────────────────────
    prompt = _build_prompt(state.company_name, state.meeting_date, interactions)
    llm_started = time.perf_counter()
    error: str | None = None
    output_summary = ""
    try:
        client = get_client()
        response = client.messages.create(
            model=CHEAP_MODEL,
            max_tokens=_LLM_MAX_TOKENS,
            timeout=_LLM_TIMEOUT_S,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text if response.content else ""
        output_summary = _truncate(raw_text, _OUTPUT_SUMMARY_CAP)
        payload = _parse_llm_json(raw_text)
        decision = payload.get("decision")
        reason = payload.get("reason") or ""
        if decision not in ("proceed", "skip", "flag_for_human"):
            raise ValueError(f"invalid decision from LLM: {decision!r}")
        state.qualification = decision  # type: ignore[assignment]
        state.qualification_reason = reason
    except Exception as exc:  # non-blocking — default to proceed
        error = f"{type(exc).__name__}: {exc}"
        state.qualification = "proceed"
        state.qualification_reason = (
            "qualification LLM failed — proceeding by default"
        )

    duration_ms = int((time.perf_counter() - llm_started) * 1000)
    state.tool_calls.append(
        ToolCall(
            agent="qualification",
            tool=f"anthropic.messages.create:{CHEAP_MODEL}",
            input_summary=_truncate(
                f"company={state.company_name} interactions={len(interactions)}",
                _INPUT_SUMMARY_CAP,
            ),
            output_summary=output_summary or (error or ""),
            duration_ms=duration_ms,
            timestamp=datetime.utcnow(),
            error=error,
        )
    )

    state.timings["qualification"] = time.perf_counter() - started
    return state
