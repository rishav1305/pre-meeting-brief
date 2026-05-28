"""System prompts + builders for the Synthesis Agent.

Captures the full prompt per docs/approach.md §8.1 — Renegade thesis
articulation, BriefOutput JSON output schema, calibration rules, citation
rules. The text below is the exact prompt from the approach doc with the
{{partner}}, {{company.name}}, and {{meeting_date}} placeholders left
in so we can `.format(partner=…, company_name=…, meeting_date=…)` at
call time.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.pipeline.state import BriefState


SYSTEM_PROMPT = """You are a senior associate at Renegade Capital preparing a pre-meeting
brief for partner {partner}, meeting {company_name} on {meeting_date}.

Renegade thesis: Markets That Matter — workflow-critical sectors in defense,
dual-use, vertical infrastructure, and industries underserved by SaaS.
Score thesis_fit on this basis: 5/5 = core thesis, 1/5 = adjacent or off.

The partner already has some context about this company (intro email,
deck review, conference encounter — see prior_interactions). Your job is
to REFRESH their memory and surface what's NEW since last contact,
not introduce from zero.

Brief structure (return as JSON per BriefOutput schema):
1. snapshot     — 60-word hook lead with new_highlights from Specter
2. thesis_fit   — { score: 1-5, reasoning, bear_case }
3. funding      — table of rounds + 1-paragraph funding story
4. team         — founder/exec cards + 1-paragraph team thesis
5. traction     — signal cards + 1-paragraph narrative pulse
6. prior_engagement — synthesised summary from Attio interaction history
7. industry_deepdive — 1 paragraph: TAM, dynamics, comparables
8. market_deepdive   — 1 paragraph: timing, tailwinds, threats
9. key_engagement_questions — 3-5 sharp questions
10. podcast_mentions  — list of podcast appearances
11. news — recent items with date and source

Citation rules:
- Funding facts: cite source ("[PB+CB]", "[S modeled]")
- Web facts: inline URL citation
- Engagement facts: cite Attio interaction date

Calibrate your language:
- "Revenue est. ~$300M ARR, Specter modeled" not "Revenue is $300M"
- "Founders have prior exit at X" not "Founders are world-class"
- "TAM estimated at $80B per Bessemer 2024 memo" not "Massive market"

Output: strict JSON. No markdown outside JSON. No commentary."""


CRITIQUE_PROMPT = """Review the brief draft below. Critique on:
- Where is a claim insufficiently cited?
- What questions can't the partner answer from this brief?
- Where is language uncalibrated (e.g., "world-class" instead of specific evidence)?
- Did the synthesis lead with new_highlights or bury them?
- Is the thesis_fit reasoning specific to Renegade's Markets That Matter thesis, or generic?

Return JSON: { "weaknesses": [..., ...], "specific_revisions": [..., ...] }
Be concise: 3-5 weaknesses, 3-5 actionable revisions. No fluff."""


def _json_block(value, indent: int = 2) -> str:
    """JSON-encode with default=str to handle datetime/UUID etc."""
    return json.dumps(value, indent=indent, default=str)


def build_brief_prompt(state: "BriefState") -> str:
    """Build the user message that gives Claude the merged canonical context
    plus web research. Returned string is passed as the user message in
    `messages=[{"role": "user", "content": <this>}]`.
    """
    parts: list[str] = [f"# Company: {state.company_name} ({state.domain})"]
    parts.append(
        f"## Meeting context\n"
        f"Partner: {state.partner}\n"
        f"Date: {state.meeting_date}\n"
    )

    if state.company_profile:
        parts.append(
            "## Canonical company profile\n"
            f"```json\n{_json_block(state.company_profile)}\n```\n"
        )
    if state.funding_history:
        parts.append(
            "## Funding history\n"
            f"```json\n{_json_block(state.funding_history)}\n```\n"
        )
    if state.team_people:
        parts.append(
            "## Team\n"
            f"```json\n{_json_block(state.team_people)}\n```\n"
        )
    if state.traction_signals:
        parts.append(
            "## Traction signals\n"
            f"```json\n{_json_block(state.traction_signals)}\n```\n"
        )
    if state.attio_raw:
        engagement = state.attio_raw.get("interactions") or state.attio_raw
        parts.append(
            "## Prior engagement (Attio history)\n"
            f"```json\n{_json_block(engagement)}\n```\n"
        )
    if state.web_raw:
        parts.append(f"## Recent web research\n{state.web_raw}\n")
        if state.web_citations:
            citations_md = "\n".join(
                f"- [{c.get('title', '(no title)')}]({c.get('url', '')})"
                for c in state.web_citations
            )
            parts.append(f"### Citations\n{citations_md}")
    if state.dq_ranked:
        flags = [f.model_dump() for f in state.dq_ranked[:5]]
        parts.append(
            "## Data quality flags (ranked)\n"
            "The following inconsistencies were detected during merge. Note "
            "them in your brief where they affect claims, but proceed with "
            "the highest-priority source's value:\n"
            f"```json\n{_json_block(flags)}\n```\n"
        )

    parts.append("\nGenerate the brief now. Return strict JSON only.")
    return "\n\n".join(parts)
