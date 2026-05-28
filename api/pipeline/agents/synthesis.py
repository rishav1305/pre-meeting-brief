"""Synthesis Agent — the centerpiece of the pipeline.

Three-stage loop:
  1. Draft  — Claude Sonnet 4.6 produces an initial BriefOutput JSON.
  2. Critique — a separate Claude call reads the draft and lists weaknesses.
  3. Revise — a third call incorporates the critique into a final brief.

Bounds: max 3 stages (with 1 automatic retry on stage-1 JSON parse failure),
540s wallclock budget across the whole loop, and 240s timeout per individual
call. Every call appends a ToolCall record for the audit UI.

Failure semantics — be conservative:
  - Draft parse fails twice: bail with state.error.
  - Critique fails (call or parse): keep the draft as final, don't raise.
  - Revise fails (call or parse): keep the draft as final, don't raise.

Sets state.brief_json (dict, BriefOutput-shaped) and state.brief_html
(basic HTML snippet for the audit field — the Next.js reader does the rich
rendering on its own).
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from html import escape
from typing import Any

from api.llm import DEFAULT_MODEL, get_client
from api.pipeline.prompts import (
    CRITIQUE_PROMPT,
    SYSTEM_PROMPT,
    build_brief_prompt,
)
from api.pipeline.state import BriefState, ToolCall


# ── Tuning constants ───────────────────────────────────────────────────────
_DRAFT_MAX_TOKENS = 8000
_CRITIQUE_MAX_TOKENS = 800
_REVISE_MAX_TOKENS = 8000
_PER_CALL_TIMEOUT_S = 240.0
_WALLCLOCK_BUDGET_S = 540.0
_INPUT_SUMMARY_CAP = 240
_OUTPUT_SUMMARY_CAP = 240


# ── Helpers ────────────────────────────────────────────────────────────────


def _truncate(s: str, cap: int) -> str:
    return s if len(s) <= cap else s[: cap - 1] + "…"


def _parse_llm_json(raw_text: str) -> dict:
    """Tolerantly extract a JSON object from the LLM's text response.

    Mirrors api.pipeline.agents.qualification._parse_llm_json: strips
    optional markdown fences, then falls back to a substring slice on
    the first/last brace pair if direct json.loads still fails.
    """
    text = (raw_text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]  # drop opening fence + any language tag
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


def _call_anthropic(
    *,
    system: str | None,
    user_content: str,
    max_tokens: int,
) -> tuple[str, str | None]:
    """Single Anthropic Messages call.

    Returns (raw_text, error). Never raises — converts every exception
    into an `error` string so the caller can decide whether to fall back.
    """
    try:
        client = get_client()
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=max_tokens,
            timeout=_PER_CALL_TIMEOUT_S,
            system=system if system else None,
            messages=[{"role": "user", "content": user_content}],
        )
        raw_text = ""
        if response.content:
            block = response.content[0]
            raw_text = getattr(block, "text", "") or ""
        return raw_text, None
    except Exception as exc:  # noqa: BLE001 — every failure is non-blocking
        return "", f"{type(exc).__name__}: {exc}"


def _record_tool_call(
    state: BriefState,
    *,
    tool: str,
    input_summary: str,
    output_summary: str,
    duration_ms: int,
    error: str | None,
) -> None:
    state.tool_calls.append(
        ToolCall(
            agent="synthesis",
            tool=tool,
            input_summary=_truncate(input_summary, _INPUT_SUMMARY_CAP),
            output_summary=_truncate(output_summary or (error or ""), _OUTPUT_SUMMARY_CAP),
            duration_ms=duration_ms,
            timestamp=datetime.utcnow(),
            error=error,
        )
    )


def _render_brief_html(brief: dict, company_name: str) -> str:
    """Render a minimal HTML snippet for the audit field. The Next.js
    reader does the rich rendering — this is just for /runs and the
    persisted brief_html column.
    """
    snapshot = brief.get("snapshot") or {}
    hook = escape(str(snapshot.get("hook") or ""))
    thesis = brief.get("thesis_fit") or {}
    score = escape(str(thesis.get("score") or "?"))
    reasoning = escape(str(thesis.get("reasoning") or ""))
    bear = escape(str(thesis.get("bear_case") or ""))
    questions = brief.get("key_engagement_questions") or []
    questions_html = "".join(f"<li>{escape(str(q))}</li>" for q in questions)
    return (
        f"<article class=\"brief\">"
        f"<header><h1>{escape(company_name)}</h1>"
        f"<p class=\"hook\">{hook}</p></header>"
        f"<section class=\"thesis-fit\">"
        f"<h2>Thesis fit: {score}/5</h2>"
        f"<p>{reasoning}</p>"
        f"<p class=\"bear\"><strong>Bear case:</strong> {bear}</p>"
        f"</section>"
        f"<section class=\"questions\"><h2>Key questions</h2>"
        f"<ol>{questions_html}</ol></section>"
        f"</article>"
    )


# ── Main entry point ───────────────────────────────────────────────────────


async def synthesise_brief(state: BriefState) -> BriefState:
    """Draft → critique → revise. Mutates and returns the same state object.

    Sets state.brief_json (dict) and state.brief_html (string).
    On unrecoverable draft failure, sets state.error and leaves brief_json None.
    """
    started = time.perf_counter()
    user_message = build_brief_prompt(state)
    # SYSTEM_PROMPT contains literal braces in the JSON schema description
    # (e.g. "{ score: 1-5, reasoning, bear_case }"), so we use targeted
    # string replacement rather than str.format.
    system_prompt = (
        SYSTEM_PROMPT
        .replace("{partner}", state.partner)
        .replace("{company_name}", state.company_name)
        .replace("{meeting_date}", state.meeting_date.isoformat())
    )

    def _budget_exhausted() -> bool:
        return (time.perf_counter() - started) > _WALLCLOCK_BUDGET_S

    # ── Stage 1: DRAFT (with one parse-retry) ─────────────────────────────
    draft: dict | None = None
    draft_user = user_message

    for attempt in range(2):  # initial + 1 retry
        if _budget_exhausted():
            break
        call_started = time.perf_counter()
        raw_text, error = _call_anthropic(
            system=system_prompt,
            user_content=draft_user,
            max_tokens=_DRAFT_MAX_TOKENS,
        )
        duration_ms = int((time.perf_counter() - call_started) * 1000)

        parse_error: str | None = None
        if error is None:
            try:
                draft = _parse_llm_json(raw_text)
            except (json.JSONDecodeError, ValueError) as exc:
                parse_error = f"json_parse: {exc}"

        tool_name = (
            f"anthropic.messages.create:{DEFAULT_MODEL}"
            f"#draft{'_retry' if attempt > 0 else ''}"
        )
        _record_tool_call(
            state,
            tool=tool_name,
            input_summary=f"draft attempt={attempt} company={state.company_name}",
            output_summary=_truncate(raw_text, _OUTPUT_SUMMARY_CAP),
            duration_ms=duration_ms,
            error=error or parse_error,
        )

        if draft is not None:
            break

        # Retry hint for round 2.
        draft_user = (
            user_message
            + "\n\nYour previous response wasn't valid JSON. Return strict "
            "JSON only — no prose, no markdown fences."
        )

    if draft is None:
        state.error = "synthesis JSON parse failed"
        state.timings["synthesis"] = time.perf_counter() - started
        return state

    # ── Stage 2: CRITIQUE (best-effort; skip on failure) ──────────────────
    critique: dict | None = None
    if not _budget_exhausted():
        critique_user = CRITIQUE_PROMPT + "\n\nDRAFT:\n" + json.dumps(draft)
        call_started = time.perf_counter()
        raw_text, error = _call_anthropic(
            system=None,
            user_content=critique_user,
            max_tokens=_CRITIQUE_MAX_TOKENS,
        )
        duration_ms = int((time.perf_counter() - call_started) * 1000)

        parse_error: str | None = None
        if error is None:
            try:
                critique = _parse_llm_json(raw_text)
            except (json.JSONDecodeError, ValueError) as exc:
                parse_error = f"json_parse: {exc}"

        _record_tool_call(
            state,
            tool=f"anthropic.messages.create:{DEFAULT_MODEL}#critique",
            input_summary=f"critique draft.score={draft.get('thesis_fit', {}).get('score')}",
            output_summary=_truncate(raw_text, _OUTPUT_SUMMARY_CAP),
            duration_ms=duration_ms,
            error=error or parse_error,
        )

    # ── Stage 3: REVISE (only if critique succeeded; fall back to draft) ──
    final: dict[str, Any] = draft
    if critique is not None and not _budget_exhausted():
        revise_user = (
            user_message
            + "\n\nCritique from review:\n"
            + json.dumps(critique)
            + "\n\nProduce the REVISED brief incorporating these revisions. "
            "Return strict JSON only."
        )
        call_started = time.perf_counter()
        raw_text, error = _call_anthropic(
            system=system_prompt,
            user_content=revise_user,
            max_tokens=_REVISE_MAX_TOKENS,
        )
        duration_ms = int((time.perf_counter() - call_started) * 1000)

        revised: dict | None = None
        parse_error: str | None = None
        if error is None:
            try:
                revised = _parse_llm_json(raw_text)
            except (json.JSONDecodeError, ValueError) as exc:
                parse_error = f"json_parse: {exc}"

        _record_tool_call(
            state,
            tool=f"anthropic.messages.create:{DEFAULT_MODEL}#revise",
            input_summary=(
                f"revise weaknesses="
                f"{len((critique or {}).get('weaknesses') or [])}"
            ),
            output_summary=_truncate(raw_text, _OUTPUT_SUMMARY_CAP),
            duration_ms=duration_ms,
            error=error or parse_error,
        )

        if revised is not None:
            final = revised
        # else: fall back to draft (already assigned to `final`)

    state.brief_json = final
    state.brief_html = _render_brief_html(final, state.company_name)
    state.timings["synthesis"] = time.perf_counter() - started
    return state
