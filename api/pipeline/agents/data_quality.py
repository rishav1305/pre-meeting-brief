"""Data Quality Agent — Phase 2 Task 2.6.

Takes the raw ``state.data_quality_flags`` emitted by ``merge_canonical``
and produces a ranked list ``state.dq_ranked`` for the brief audit panel.

Hybrid design:

1. **Rule-based ranking** (always):
   - Sort by severity (high > medium > low). Stable.
   - Within each severity, critical fields first (per ``_FIELD_PRIORITY``),
     then alphabetical by ``field`` for deterministic tie-break.

2. **LLM tie-break** (Haiku, optional):
   - Only invoked when the rule-based pass leaves a genuinely ambiguous
     bucket: >5 flags sharing the same severity AND the same field-priority
     bucket, AND the overall flag count exceeds 8.
   - The LLM proposes an ordering for that bucket only. If it fails, errors,
     or returns malformed JSON, the rule-based order stands. ``state.error``
     stays None — DQ ranking is never load-bearing on pipeline success.

A ``ToolCall`` row is appended if and only if the LLM was invoked.
``state.timings["data_quality"]`` is always recorded.
"""
from __future__ import annotations

import json
import time
from typing import Final

from api.llm import CHEAP_MODEL, get_client
from api.pipeline.state import BriefState, DQFlag, ToolCall


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# Severity → numeric rank. Lower number = higher priority (sorted ascending).
_SEVERITY_RANK: Final[dict[str, int]] = {"high": 0, "medium": 1, "low": 2}

# Field → priority within a severity bucket. Lower number = surfaced first.
# Critical fields (operating_status, total_raised_usd, last_round_date,
# founded_year, hq_country, employee_count) get explicit slots. All other
# fields fall through to the catch-all priority of 999.
_FIELD_PRIORITY: Final[dict[str, int]] = {
    "operating_status": 0,
    "total_raised_usd": 1,
    "last_round_date": 2,
    "founded_year": 3,
    "hq_country": 4,
    "employee_count": 5,
}
_DEFAULT_FIELD_PRIORITY: Final[int] = 999

# LLM tie-break only fires when both thresholds are crossed.
_AMBIGUOUS_BUCKET_MIN: Final[int] = 6   # >5 means at least 6
_TOTAL_FLAGS_MIN: Final[int] = 9         # >8 means at least 9


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _field_priority(field: str) -> int:
    return _FIELD_PRIORITY.get(field, _DEFAULT_FIELD_PRIORITY)


def _rule_based_sort_key(flag: DQFlag) -> tuple[int, int, str]:
    return (
        _SEVERITY_RANK.get(flag.severity, 99),
        _field_priority(flag.field),
        flag.field,
    )


def _find_ambiguous_bucket(flags: list[DQFlag]) -> list[DQFlag] | None:
    """Return the largest bucket of flags sharing the same severity AND
    field-priority bucket, IFF that bucket has >5 members. Otherwise None.
    """
    buckets: dict[tuple[str, int], list[DQFlag]] = {}
    for f in flags:
        key = (f.severity, _field_priority(f.field))
        buckets.setdefault(key, []).append(f)
    largest = max(buckets.values(), key=len, default=[])
    if len(largest) >= _AMBIGUOUS_BUCKET_MIN:
        return largest
    return None


def _build_prompt(bucket: list[DQFlag]) -> str:
    flag_lines = "\n".join(
        f"- field={f.field!r} severity={f.severity!r} issue={f.issue!r}"
        for f in bucket
    )
    return (
        "You are ranking data-quality flags for a VC partner's pre-meeting brief.\n"
        "All flags below share the same severity and field-priority bucket. "
        "Re-order them so the most material flags (the ones a partner most needs to see) "
        "come first.\n\n"
        f"Flags:\n{flag_lines}\n\n"
        "Respond with strict JSON only: "
        '{"order": ["<field_1>", "<field_2>", ...]} '
        "— exactly the same set of field names, in your preferred order. "
        "No prose, no markdown."
    )


def _parse_llm_order(text: str, bucket: list[DQFlag]) -> list[DQFlag] | None:
    """Parse the LLM JSON response and reorder ``bucket`` accordingly.

    Returns None on any parse/validation failure — caller falls back to the
    rule-based order.
    """
    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        return None
    order = payload.get("order") if isinstance(payload, dict) else None
    if not isinstance(order, list) or not all(isinstance(x, str) for x in order):
        return None
    bucket_by_field = {f.field: f for f in bucket}
    if set(order) != set(bucket_by_field.keys()):
        return None
    return [bucket_by_field[name] for name in order]


# ─────────────────────────────────────────────────────────────────────────────
# Public entrypoint
# ─────────────────────────────────────────────────────────────────────────────


async def data_quality_agent(state: BriefState) -> BriefState:
    """Ranks ``state.data_quality_flags`` by surface-priority.

    Sets ``state.dq_ranked``. Empty input → empty output, no LLM call.
    """
    started = time.perf_counter()

    flags = list(state.data_quality_flags)
    if not flags:
        state.dq_ranked = []
        state.timings["data_quality"] = time.perf_counter() - started
        return state

    # Step 1: deterministic rule-based ranking.
    ranked = sorted(flags, key=_rule_based_sort_key)

    # Step 2: LLM tie-break only when genuinely ambiguous.
    ambiguous = _find_ambiguous_bucket(ranked)
    if ambiguous is not None and len(flags) >= _TOTAL_FLAGS_MIN:
        ranked = _apply_llm_tiebreak(state, ranked, ambiguous)

    state.dq_ranked = ranked
    state.timings["data_quality"] = time.perf_counter() - started
    return state


def _apply_llm_tiebreak(
    state: BriefState,
    ranked: list[DQFlag],
    bucket: list[DQFlag],
) -> list[DQFlag]:
    """Ask Haiku for a preferred ordering of ``bucket``. On any failure,
    return ``ranked`` unchanged. Always appends a ToolCall record.
    """
    prompt = _build_prompt(bucket)
    call_started = time.perf_counter()
    error_str: str | None = None
    response_text = ""
    try:
        client = get_client()
        response = client.messages.create(
            model=CHEAP_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = response.content[0].text if response.content else ""
        reordered = _parse_llm_order(response_text, bucket)
        if reordered is None:
            error_str = "llm returned unparseable or mismatched order"
        else:
            # Swap the bucket portion of ranked with the LLM ordering.
            # Find the contiguous slice in ranked corresponding to bucket.
            bucket_fields = {f.field for f in bucket}
            slice_indices = [
                i for i, f in enumerate(ranked) if f.field in bucket_fields
            ]
            # The rule-based sort guarantees the bucket is contiguous.
            for idx, flag in zip(slice_indices, reordered):
                ranked[idx] = flag
    except Exception as exc:
        error_str = f"{type(exc).__name__}: {exc}"

    duration_ms = int((time.perf_counter() - call_started) * 1000)
    state.tool_calls.append(
        ToolCall(
            agent="data_quality",
            tool=f"anthropic.messages.create({CHEAP_MODEL})",
            input_summary=f"{len(bucket)} ambiguous flags",
            output_summary=(response_text[:200] if response_text else ""),
            duration_ms=duration_ms,
            error=error_str,
        )
    )
    return ranked
