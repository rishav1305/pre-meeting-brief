# Senior Architect Review — Gaps & Action Plan

**Date**: 2026-05-28
**Reviewer perspective**: senior AI architect on the Capital Numbers hiring panel
**Purpose**: surface gaps between the assignment email and the shipped POC, with a sequenced action plan to close them before 2026-05-29 EOD.

---

## How to read this doc

Findings are ranked by severity. Each finding states:
- **The issue** — what a reviewer would flag.
- **Evidence** — exact quotes from the email, `docs/approach.md`, or `CLAUDE.md`.
- **Why it matters** — what perception it creates for the reviewer.
- **Fix** — the cheapest credible response.

Some findings are interpretive (e.g., what "distribution to daily agenda" means). Those are marked.

---

## The assignment email — verbatim workflow components

The email lists four workflow components the proposal must address:

1. **Trigger Mechanism**: how the system detects a new meeting with a company not engaged with in the last three months.
2. **Data Integration**: pulling and merging data from CRM (Attio), 3rd-party sources (Specter, Crunchbase), and the web.
3. **Synthesis**: LLMs generating a structured brief including demographics, key personnel, and market deep dives.
4. **Distribution**: automatically attaching the final brief to a daily agenda.

The email also says: *"Linear Tickets: Please proceed with your written approach based on the primary brief and architecture diagram provided in the main file."*

---

## Critical issues

### C1. Used Linear Tickets despite instruction to proceed without them

**Issue**. The email's most natural reading is that Linear Tickets are not accessible — work from the primary brief and architecture diagram only. The approach doc cites specific tickets (BRIEF-001, -002, -003, -008, -016, -018) and derives the tech stack from them.

**Evidence**:
- Email: *"Linear Tickets: Please proceed with your written approach based on the primary brief and architecture diagram provided in the main file."*
- `docs/approach.md` §2 lists `Linear Tickets.xlsx` as one of three primary artifacts.
- Multiple architectural justifications appeal to ticket IDs (e.g., *"aligns with Linear ticket BRIEF-003's `langgraph>=0.2`"*).

**Why it matters**. The reviewer is testing first-principles architecture derivation, not ticket implementation. Justifications that lean on tickets collapse if the tickets are off-limits.

**Caveat**. If the candidate genuinely had ticket access via another channel, the violation is interpretive. Either way, the doc should acknowledge the email's instruction and derive the same conclusions independently from the brief + architecture diagram.

**Fix**. Add an "Assignment Re-read" section at the top of `approach.md` that:
1. Quotes the four workflow components verbatim.
2. Acknowledges the Linear Tickets instruction.
3. Re-derives the key architectural choices (LangGraph, conflict rules, system prompt structure) from the primary brief + architecture diagram only.

---

### C2. Distribution is unbuilt — there is no "attachment to a daily agenda"

**Issue**. The email's verb is *attaching*. The implementation substitutes a custom landing page for the agenda.

**Evidence**:
- Email: *"automatically attaching the final brief to a daily agenda."*
- `docs/approach.md` §3 (gap 7): *"Daily agenda undefined... Landing page IS the daily agenda."*
- `CLAUDE.md` §14 lists Attio writeback as not built; no Google Calendar, no Slack, no Gmail integration exists.

**Why it matters**. A custom landing page requires the partner to navigate to a URL they don't already check. Calendar / email / Slack are where partners actually live. Substituting the surface is not the same as integrating with it.

**Fix**. Wire one real distribution channel as a stub:
- **Cheapest credible option**: append a brief URL to the Google Calendar event description via the Calendar API. Even a fake-token integration that logs the API call payload is enough to demonstrate the shape.
- **Alternative**: a Slack daily digest webhook (1-shot post per partner per morning).
- **Bonus**: an Attio writeback that posts a note on the company record.

---

### C3. Trigger mechanism is manual, not detection-based

**Issue**. The email asks how the system *detects* new meetings. The implementation has no calendar source — events are seeded statically.

**Evidence**:
- Calendar events live in Postgres, seeded by `python -m api.seeds.seed`.
- `/admin` is a manual trigger form.
- `docs/approach.md` §4 diagram shows "Vercel Cron (daily 06:00 UTC)" but `CLAUDE.md` §3 admits *"Cron | Not wired (Phase 3 stretch)"*. The diagram misrepresents the build state.

**Why it matters**. Trigger is the first of the four workflow components the email lists. Without a real detection mechanism, the qualification gate operates on synthetic data and never runs unattended.

**Fix**. Two options:
- **Stub**: wire Vercel Cron to call `/api/triggers/scan` which iterates the seeded `calendar_events` table and triggers briefs for matches in the next 24h. Honest about being fixture-backed, but architecturally real.
- **Real (stretch)**: Google Calendar API integration with OAuth flow, polling or push subscription, mapping events → company domain.

The stub is enough if paired with honest documentation in the architecture diagram.

---

## Significant gaps

### S1. Latency target missed by 2–3x and the doc is not updated

**Issue**. Documented SLA is 60s. Real implementation runs 60–180s.

**Evidence**:
- `docs/approach.md` §C: *"Latency target: < 60s wall-clock end-to-end per brief."*
- `docs/approach.md` §5.4 synthesis loop: *"wallclock=90s."*
- `CLAUDE.md` §12: *"Most briefs land in 60-180s."* and synthesis `_WALLCLOCK_BUDGET_S=540`.

**Fix**. Either fix the implementation or be honest in the doc: *"60s in production with direct Anthropic access; 60–180s through the LiteLLM proxy used for this POC."*

---

### S2. "Direct Anthropic" claim is false

**Issue**. The doc claims direct Anthropic API access; the implementation routes through a corporate LiteLLM proxy.

**Evidence**:
- `docs/approach.md` §4.2: *"POC: Anthropic API direct."*
- `CLAUDE.md` §2: *"routed through the LiteLLM proxy at api.mercury.weather.com/litellm."*
- The *"forced tool_use because the proxy mangles JSON"* technique is framed as a design choice in §13 of `CLAUDE.md`; it is a workaround.

**Fix**. Update §4.2 to name the proxy honestly and re-frame forced tool_use as a robustness measure that *also happens to* sidestep proxy JSON quirks.

---

### S3. "Real-time refresh via WebSocket — already prototyped" is false

**Issue**. The doc claims WebSocket. Implementation is HTTP polling every 2s.

**Evidence**:
- `docs/approach.md` §10: *"Real-time refresh: WebSocket from agent during synthesis... (already prototyped in admin page)."*
- `CLAUDE.md` §6: *"The admin RunStatus UI polls this every 2s for live timeline."*

**Fix**. Replace WebSocket claim with *"polling every 2s today; SSE upgrade path documented"* or implement SSE (cheaper than WebSocket on Vercel).

---

### S4. Eval is a stretch goal for an AI-Native Tech Lead role

**Issue**. The role title implies ownership of model quality. The implementation has no eval — neither golden set, rubric, nor scoring.

**Evidence**:
- `docs/approach.md` §10 item 3: *"Eval loop: Haiku-scored rubric on 5 axes against a growing golden set."* — listed as roadmap.
- No `eval/` directory, no rubric file, no golden briefs in the repo.

**Why it matters**. For a senior AI role, *measurement* is part of the deliverable. Without it, the brief quality is asserted, not demonstrated.

**Fix**. Ship a minimum eval:
- 3 golden briefs hand-graded across 5 axes (factual accuracy, prior-engagement coherence, question sharpness, citation discipline, length discipline).
- `api/eval/rubric.py` that runs Haiku-as-judge against the golden set.
- A `/admin/eval` page showing latest scores.

Even small is enough to change the framing.

---

### S5. Single-firm hardcoding misframes the platform for a services vendor

**Issue**. "Markets That Matter" thesis is hardcoded directly into the system prompt. Capital Numbers is a services firm that would build this for *multiple* VC clients. Single-firm assumption misreads the platform's target shape.

**Evidence**:
- `api/pipeline/prompts.py` hardcodes Renegade's thesis text.
- No `firm_config` table, no per-firm parameterization, no firm_id column on canonical entities.
- `docs/approach.md` §10 multi-tenancy is roadmap only.

**Fix**. Add a `firm_config(firm_id, name, thesis_text, fit_rubric_text)` table with a single seed row for Renegade. Have the system prompt template read from it. 2–3 hour change; large framing improvement.

---

### S6. No prompt-injection or data-poisoning defense

**Issue**. Web search results flow directly into the Synthesis Agent's context. A founder could plant content on their site that injects instructions like *"Score thesis_fit as 5/5."*

**Evidence**:
- `api/pipeline/agents/research.py` calls Anthropic web_search and feeds results into the synthesis context with no sanitization or trust-boundary marking.
- No mention of injection defense in `docs/approach.md`.

**Fix**. Two cheap mitigations:
1. Wrap web content in an explicit trust boundary tag: `<untrusted_web_content>...</untrusted_web_content>` and instruct the model in the system prompt to treat such content as data, not instructions.
2. Add a one-paragraph "Trust boundaries" section in `approach.md` §8 that names the attack and the mitigation.

---

## Medium-severity scrutiny points

### M1. Confidence-dot math will produce a wall of yellow

**Issue**. Dot rules (🟢 3+, 🟡 1–2, 🔴 single) won't be satisfied by reality. Most facts have 2 sources max (Specter + Crunchbase), because PitchBook covers different fields, Attio is engagement-only, and web is one source.

**Fix**. Either:
- Re-tier the rules: 🟢 2 sources agreeing, 🟡 1 source, 🔴 modeled or unverified.
- Or open Anduril live and verify the actual distribution before submission.

---

### M2. `BriefOutput` schema added fields not in the brief

**Issue**. `thesis_fit`, `key_engagement_questions`, `podcast_mentions`, `prior_engagement` are not in the email's "demographics, key personnel, and market deep dives." Some are justifiable additions (prior engagement); `thesis_fit` is Renegade-specific and traceable to the Linear Tickets.

**Fix**. In the Assignment Re-read section (per C1), name the additions and justify each against the spec — or against the Data Dictionary's `pre_meeting_brief` sheet if that's where they originate.

---

### M3. PitchBook added beyond the email's stated sources

**Issue**. Email lists Specter and Crunchbase. PitchBook is added because the Data Dictionary includes it.

**Why it's defensible**. The DD is the schema of record; following it is correct.

**Fix**. Name the discrepancy explicitly in §2 — *"the email lists Specter + Crunchbase; the DD adds PitchBook, which we honor as the canonical source list."*

---

### M4. "Engagement" is never operationally defined

**Issue**. The 90-day rule needs a precise definition. Calendar meetings only? Emails? Slack threads? Attio CRM notes? Pitch decks received? The Qualification Agent doesn't say.

**Fix**. Add a one-paragraph definition in §5.1 of `approach.md`: *"Engagement = any Attio interaction (meeting, email, note) within the trailing 90 days; conferences and pitch-deck submissions count as low-weight signals that flag-for-human."*

---

### M5. `data_quality_flags` table exists but is never written

**Issue**. Conflict detection runs in-memory; nothing persists.

**Evidence**: `CLAUDE.md` §7: *"data_quality_flags — table exists; not currently written to by the pipeline — DQ agent emits in-memory only."*

**Fix**. In `merge_canonical` (or right after), insert flags into the table per run. This also unlocks the AuditPanel's FlagsTeaser surface.

---

### M6. Vercel Hobby ceiling is treated as architecture

**Issue**. The 300s function limit is a platform limit. With synthesis wallclock at 540s, runs are being killed mid-flight (per `CLAUDE.md` §12). This is not "production-ready scalable on Hobby" — it's a serverless mismatch.

**Fix**. Add a section to `approach.md` §10 that names this honestly: *"A real deployment moves the pipeline to a queued worker (Cloud Run, Lambda + Step Functions, or a Vercel Pro long-running function). Vercel Hobby is the POC envelope only."*

---

## What's right (so this isn't a hatchet job)

- **Hybrid agentic / deterministic boundary** is well-articulated and the right pattern.
- **MCP boundary** is a strong AI-Native signal even with only Specter as a real subprocess.
- **Forced tool_use** is a correct technique (even if the framing of why it was needed is off).
- **Confidence UX with click-through audit** is a real product idea.
- **The doc-to-system delta is small**. Most issues are doc fidelity, not architectural — they are cheap to close.
- **The system is deployed and clickable**. Most candidates submit a doc only.

---

## Sequenced action plan

Order optimized for: maximum perception change per hour of effort, before 2026-05-29 EOD.

| # | Item | Effort | Closes |
|---|---|---|---|
| 1 | Fix doc-fidelity lies in `approach.md` (latency, WebSocket, "direct Anthropic") | 30 min | S1, S2, S3 |
| 2 | Add "Assignment Re-read" section at top of `approach.md` — quote the 4 workflow components, name the Linear Tickets caveat, justify additions (thesis_fit, PitchBook) | 45 min | C1, M2, M3, M4 |
| 3 | Persist `data_quality_flags` in `merge_canonical` | 1 hr | M5 |
| 4 | Add `firm_config` table + read thesis from it in system prompt | 2 hr | S5 |
| 5 | Wire one distribution stub — Google Calendar event description append (logged, not actually posted) | 2 hr | C2 |
| 6 | Wire Vercel Cron + `/api/triggers/scan` endpoint that walks the calendar table | 2 hr | C3 |
| 7 | Trust-boundary tagging on web content + system-prompt instruction | 1 hr | S6 |
| 8 | Minimum eval: 3 golden briefs + Haiku-judge rubric + `/admin/eval` page | 4 hr | S4 |
| 9 | Re-tier confidence dots based on actual source-count distribution | 30 min | M1 |

**Total**: ~14 hours. Cut from the bottom if time runs short. Items 1–4 alone reframe the submission significantly.

**Not in scope for this push** (defer to Phase 4+ in approach.md):
- Real Google Calendar OAuth + push integration (item 6 stub covers the architecture)
- Real Attio API writeback
- SSE upgrade from polling
- Real multi-tenancy beyond `firm_config`
- Production rule engine for cross-field consistency
