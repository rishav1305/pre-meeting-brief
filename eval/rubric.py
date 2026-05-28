"""Haiku-as-judge scoring rubric.

Given (golden_criteria, candidate_brief) — return a per-axis score dict.

The model is asked to return strict JSON via forced tool_use (same pattern
as the Synthesis Agent). Scores are 0-5 per axis. Total = sum across 5
axes (max 25).

Importantly: the judge sees the golden's expected criteria, not a reference
brief. We score against "did the brief satisfy the criteria" rather than
"does it match a reference verbatim" — the former is more forgiving of
legitimate variation between runs.
"""
from __future__ import annotations

import json
import time
from typing import Any

from api.llm import get_client

JUDGE_MODEL = "claude-haiku-4-5-20251001"

_JUDGE_TOOL = {
    "name": "submit_eval_scores",
    "description": (
        "Submit the per-axis scores and rationale for the candidate brief "
        "against the golden criteria."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "factual_accuracy": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "minimum": 0, "maximum": 5},
                    "rationale": {"type": "string"},
                },
                "required": ["score", "rationale"],
            },
            "prior_engagement_coherence": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "minimum": 0, "maximum": 5},
                    "rationale": {"type": "string"},
                },
                "required": ["score", "rationale"],
            },
            "question_sharpness": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "minimum": 0, "maximum": 5},
                    "rationale": {"type": "string"},
                },
                "required": ["score", "rationale"],
            },
            "citation_discipline": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "minimum": 0, "maximum": 5},
                    "rationale": {"type": "string"},
                },
                "required": ["score", "rationale"],
            },
            "language_calibration": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "minimum": 0, "maximum": 5},
                    "rationale": {"type": "string"},
                },
                "required": ["score", "rationale"],
            },
            "overall_notes": {"type": "string"},
        },
        "required": [
            "factual_accuracy",
            "prior_engagement_coherence",
            "question_sharpness",
            "citation_discipline",
            "language_calibration",
            "overall_notes",
        ],
    },
}


_JUDGE_SYSTEM = """You are a rigorous eval judge for VC pre-meeting briefs.

You score a candidate brief on 5 axes (each 0-5):

1. factual_accuracy — Are hard facts consistent with the canonical sources?
2. prior_engagement_coherence — Does the brief surface what's NEW and lead
   with new_highlights? Penalize introducing from zero when prior context exists.
3. question_sharpness — Are key_engagement_questions specific and tied to
   the company's actual business — not generic VC fluff?
4. citation_discipline — Are non-obvious claims attributed to a source?
5. language_calibration — Hedged where appropriate? Penalize founder
   hagiography and unhedged estimates.

For each axis:
- 5 = exceeds expectations
- 4 = meets expectations cleanly
- 3 = meets with minor issues
- 2 = partial — multiple issues
- 1 = below expectations
- 0 = absent or wrong

Be specific in rationales. Cite exact quotes from the brief when penalizing.

Call submit_eval_scores to return your decision."""


def _build_user_message(criteria: dict[str, Any], brief: dict[str, Any]) -> str:
    return (
        "# Golden criteria\n"
        f"```json\n{json.dumps(criteria, indent=2)}\n```\n\n"
        "# Candidate brief\n"
        f"```json\n{json.dumps(brief, indent=2, default=str)}\n```\n\n"
        "Score the brief now. Be specific."
    )


def judge_brief(criteria: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    """Score one brief against one set of criteria. Returns the parsed tool input.

    Raises if the API call fails — eval is allowed to fail loud, unlike the
    synthesis loop which is best-effort. The CLI runner catches and aggregates.
    """
    client = get_client()
    started = time.perf_counter()
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=2048,
        system=_JUDGE_SYSTEM,
        messages=[{"role": "user", "content": _build_user_message(criteria, brief)}],
        tools=[_JUDGE_TOOL],
        tool_choice={"type": "tool", "name": "submit_eval_scores"},
    )
    duration_ms = int((time.perf_counter() - started) * 1000)

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "submit_eval_scores":
            scores = block.input
            scores["_meta"] = {
                "model": JUDGE_MODEL,
                "duration_ms": duration_ms,
            }
            return scores

    raise RuntimeError("Judge did not return a tool_use block")


def total_score(scores: dict[str, Any]) -> int:
    """Sum the per-axis scores; max 25."""
    return sum(
        scores.get(axis, {}).get("score", 0)
        for axis in (
            "factual_accuracy",
            "prior_engagement_coherence",
            "question_sharpness",
            "citation_discipline",
            "language_calibration",
        )
    )
