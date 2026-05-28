# Pre-Meeting Brief — Project Memory & Handoff

> **Session-handoff doc.** If you're picking this up on a different device or a new Claude Code session, read this top to bottom. Everything you need to continue is here.

---

## 1. The submission (one paragraph)

This is a take-home submission to **Capital Numbers** for the **AI-Native Tech Lead** role (Gurgaon). The assignment uses **Renegade Capital** as the example VC client — so the platform is designed around Renegade's thesis ("Markets That Matter"), data dictionary, and Linear tickets. The deliverable is the architecture + a working POC for Capital Numbers to evaluate.

**Framing rule:** when docs / code / UI refer to "the firm", "Renegade", or "Renegade Capital", that's the demo client. The hiring entity is **Capital Numbers**. The top-bar nav and footer both surface this — keep that distinction visible.

**Deadline:** 2026-05-29 EOD.

---

## 2. Live URLs & credentials

| Resource | URL |
|---|---|
| Live demo | https://rishavchatterjee.com/pre-meeting-brief |
| GitHub repo | https://github.com/rishav1305/pre-meeting-brief |
| Approach doc (rendered) | https://rishavchatterjee.com/pre-meeting-brief/approach |
| Pipeline architecture | https://rishavchatterjee.com/pre-meeting-brief/pipeline |
| Admin (trigger brief) | https://rishavchatterjee.com/pre-meeting-brief/admin |
| Vercel project | `rishav1305s-projects/pre-meeting-brief` |
| Postgres | Vercel Postgres / Neon (auto-provisioned) |

**Admin password to share with reviewer:** `rdSaGl_zcV7dfkZklglshlWsZHYAWZOP` (32 chars, set on Vercel env as `ADMIN_PASSWORD`).

**Anthropic API:** routed through the LiteLLM proxy at `api.mercury.weather.com/litellm` (the user's corporate proxy). Both `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` set on Vercel. The proxy supports `claude-sonnet-4-6` and the `web_search_20250305` tool — both verified working.

---

## 3. Phase status (all shipped, tagged)

| Tag | What it ships | Commit |
|---|---|---|
| `phase-0` | Scaffold + deploy: Next.js basePath, FastAPI shell, Vercel project + Postgres provisioned, subpath rewrite | — |
| `phase-1` | Schema (DD-mirror), 6 company fixtures, 4 providers, standalone specter-mcp server, seed script, agenda + brief reader, /approach renderer | — |
| `phase-2` | LangGraph orchestrator + 4 real agents (Qualification/Research/DQ/Synthesis), real Anthropic web_search, forced tool_use synthesis, admin trigger + UI | — |
| `phase-3` | Live per-node progress tracking, partner switcher, calendar-view agenda with non-uniform density, nested TOC + scroll-spy, interactive /pipeline (4 tabs), rebuilt audit panel, recent-runs panel on /admin | `phase-3` HEAD |
| `phase-4` (in-progress) | Senior-architect review pass: closed reviewer-flagged gaps before submission — `firm_config` parameterization, `data_quality_flags` persistence, Vercel Cron + `/api/triggers/scan` trigger detection, Google Calendar distribution stub via `pre_meeting_brief.distribution_log`, trust-boundary tagging on web content, `eval/` rubric + golden criteria for 3 companies, confidence-dot tier re-alignment, full doc-fidelity sweep on `docs/approach.md`. See `docs/review-gaps.md` for the gap log driving this. | uncommitted |

Total commits on master: ~50+. See `git log --oneline` for the full sequence.

---

## 4. Architecture (one screen)

```
                              ┌── Vercel project: pre-meeting-brief ──┐
                              │                                       │
   rishavchatterjee.com/  ──► │  Next.js (app/, basePath /pre-…)      │
   pre-meeting-brief/*        │  ├─ /                Calendar agenda  │
   (proxied via               │  ├─ /briefs/[id]     Dashboard reader │
   portfolio_app rewrite)     │  ├─ /admin           Trigger form     │
                              │  ├─ /approach        Rendered doc     │
                              │  └─ /pipeline        Architecture     │
                              │                                       │
                              │  Python FastAPI (api/index.py)        │
                              │  ├─ /api/agenda                       │
                              │  ├─ /api/briefs/{id}                  │
                              │  ├─ /api/triggers/manual  (gated)     │
                              │  ├─ /api/triggers/runs                │
                              │  └─ /api/triggers/runs/{run_id}       │
                              │                                       │
                              │  LangGraph pipeline (api/pipeline/)   │
                              │   ↓                                   │
                              │   resolve_company   [deterministic]   │
                              │   qualification_agent  [Haiku]        │
                              │   fetch_all  (4 providers concurrent) │
                              │   research_agent  [Sonnet + web_search]│
                              │   merge_canonical  [deterministic]    │
                              │   data_quality_agent  [rule + Haiku]  │
                              │   synthesise_brief  [Sonnet tool_use] │
                              │   render_and_persist  [deterministic] │
                              │                                       │
                              │  Vercel Postgres (Neon)               │
                              │   ├─ canonical.company, .people,      │
                              │   │  .traction_metrics                │
                              │   ├─ canonical.pre_meeting_brief      │
                              │   ├─ canonical.calendar_events        │
                              │   ├─ canonical.etl_run_log            │
                              │   │   (+ current_node, node_history)  │
                              │   ├─ canonical.data_quality_flags     │
                              │   └─ raw.source_payloads              │
                              │                                       │
                              │  Standalone MCP servers (mcp_servers/)│
                              │   └─ specter_mcp  (FastMCP 1.27)      │
                              │      launched as subprocess per fetch │
                              │      via stdio transport              │
                              └───────────────────────────────────────┘

                              External:
                              ├─ Anthropic (Claude Sonnet 4.6, Haiku 4.5)
                              │   via LiteLLM proxy at
                              │   api.mercury.weather.com/litellm
                              └─ portfolio_app on Vercel
                                  (handles rishavchatterjee.com,
                                   rewrites /pre-meeting-brief/* here)
```

Read `docs/approach.md` §4 for the v2 architecture diagram with all the cross-cutting layers.

---

## 5. Tech stack & key decisions

| Layer | Choice | Notes |
|---|---|---|
| Framework (UI) | **Next.js 16** (App Router, TypeScript) | basePath `/pre-meeting-brief` |
| CSS | **Tailwind v4** (postcss-only, NO `tailwind.config.ts`) | typography plugin loaded via `@plugin` directive in `app/globals.css` |
| Framework (API) | **FastAPI** on Vercel Python serverless | Function in `api/index.py`, ALL /api/* requests go to this one function via catch-all rewrite in `vercel.json` |
| Orchestrator | **LangGraph 0.2+** | aligns with Linear ticket spec |
| LLM | **Claude Sonnet 4.6** (synthesis, research), **Haiku 4.5** (qualification, DQ tie-break) via Anthropic SDK | All calls go through the LiteLLM proxy |
| LLM JSON output | **Forced `tool_use` with `submit_brief` schema** | The LiteLLM proxy occasionally produces JSON with unescaped quotes that breaks `json.loads`. Forced tool_use bypasses parsing entirely — the SDK validates the schema at the API boundary. |
| DB driver | **psycopg3** (`postgresql+psycopg`) | NOT asyncpg — Neon's URLs include `channel_binding=require` which asyncpg rejects. psycopg3 supports both sync and async. |
| Migrations | **Alembic** | `api/db/migrations/versions/` |
| MCP | **`mcp` package 1.27**, FastMCP server | `mcp_servers/specter_mcp/server.py` launched via stdio transport per fetch |
| Hosting | **Vercel** Hobby plan | `maxDuration: 300` (Hobby ceiling — required for the ~60-180s pipeline) |
| Cron | Not wired (Phase 3 stretch) | Manual trigger only via /admin |

---

## 6. The 8-stage pipeline (the centerpiece)

Each stage has its own card on `/pipeline` with full contract (reads/writes/bounds/model). The reviewer-facing description lives in `components/PipelineStageCard.tsx`.

| # | Stage | Type | Function | Model | Notes |
|---|---|---|---|---|---|
| 1 | `resolve_company` | Deterministic | `api/pipeline/nodes.py` | — | Normalizes domain, upserts canonical.company, opens etl_run_log |
| 2 | `qualification_agent` | Agentic | `api/pipeline/agents/qualification.py` | Haiku 4.5 | Hybrid: deterministic 90-day prefilter + LLM judgment for edge cases. Graceful default to "proceed" on LLM failure. |
| 3 | `fetch_all` | Deterministic + MCP | `api/pipeline/nodes.py` | — | `asyncio.gather(return_exceptions=True)` across 4 providers. **specter-mcp runs as subprocess** (`SpecterMcpClient` in `api/providers/specter_mcp_client.py`); crunchbase/pitchbook/attio are in-process. Failures emit DQ flags, never raise. |
| 4 | `research_agent` | Agentic | `api/pipeline/agents/research.py` | Sonnet 4.6 + `web_search_20250305` | Loop up to 5 searches, 60s wallclock. |
| 5 | `merge_canonical` | Deterministic | `api/pipeline/merge.py` | — | DD's source-priority chains (COALESCE) + 6 conflict detectors. Pure Python. |
| 6 | `data_quality_agent` | Agentic | `api/pipeline/agents/data_quality.py` | Haiku 4.5 (only when ambiguous) | Severity-ranks DQ flags. Rule-based first, LLM tie-break only when ≥6 same-severity flags AND total >8. |
| 7 | `synthesise_brief` | Agentic | `api/pipeline/agents/synthesis.py` | Sonnet 4.6 with **forced tool_use** | Draft → critique → revise. `_DRAFT_MAX_TOKENS=8000`, `_PER_CALL_TIMEOUT_S=240`, `_WALLCLOCK_BUDGET_S=540`. THE CENTERPIECE. |
| 8 | `render_and_persist` | Deterministic | `api/pipeline/nodes.py` | — | Writes `canonical.pre_meeting_brief`, closes etl_run_log. |

**Progress tracking (Phase 3):** every node is wrapped by `_wrap_node` in `api/pipeline/graph.py` which calls `api.pipeline.progress.record_node_start/complete/failed`. These write to `etl_run_log.current_node` and `.node_history` (JSONB array). The admin RunStatus UI polls this every 2s for live timeline.

**Per-node messages** are templated in `api/pipeline/progress.py::message_for()`. Examples:
- `qualification`: "Decision: proceed — no prior interactions in 90 days"
- `fetch_all`: "Concurrent fetch: specter✓, crunchbase✓, pitchbook✓, attio✓"
- `synthesise`: "Claude tool_use synthesis → thesis_fit score=5/5"

---

## 7. Database schema (mirrors the Data Dictionary)

Tables in `canonical.*` (no actual schema prefix — flat in Postgres):

- **`company`** — 30+ fields, audit JSONB, mirrors DD sheet 1
- **`people`** — founders/key_executives/board_members (JSONB arrays), audit
- **`traction_metrics`** — highlights, new_highlights, web_visits, linkedin, g2, news, audit
- **`pre_meeting_brief`** — output table; thesis_fit + 4 prose fields + 3 audit columns (audit_company, audit_people, audit_traction_metrics) — frozen at brief-gen time
- **`calendar_events`** — partner, company_domain, meeting_date, attendees
- **`etl_run_log`** — run_id, company_id, status (running|complete|failed|merged), started_at, completed_at, error_message, **current_node**, **node_history (JSONB)** ← Phase 3 added
- **`data_quality_flags`** — flag rows from merge. **Phase 4: now persisted** by `render_and_persist` for every detected conflict; brief reader's FlagsTeaser surfaces them.
- **`source_payloads`** — raw layer (company_id, source, raw, pulled_at) — combined for all 4 sources
- **`firm_config`** ← Phase 4 added — `firm_id, name, thesis_label, thesis_description, fit_rubric, is_default`. Seeded with Renegade as the default; `api.pipeline.prompts.load_firm_context()` reads from it to parameterize the synthesis system prompt.
- **`pre_meeting_brief.distribution_log`** ← Phase 4 added (JSONB on existing table) — append-only log of distribution attempts (channel, target, status, payload, attempted_at).

Migrations:
- `0001_initial_schema.py` — all 8 tables
- `0002_etl_run_log_progress.py` — adds `current_node` + `node_history`
- `0003_firm_config.py` — adds `firm_config` table + seeds Renegade
- `0004_brief_distribution.py` — adds `distribution_log` JSONB column to `pre_meeting_brief`

---

## 8. The 6 demo companies & seeded calendar

**Companies** (all in `fixtures/<domain>/{specter,crunchbase,pitchbook,attio}.json`):

| Domain | Thesis fit (Renegade) | Why |
|---|---|---|
| anduril.com | **5/5** | Defense + workflow-critical — core thesis |
| hadrian.co | **5/5** | Industrial mfg automation, dual-use |
| modal.com | **3/5** | AI infra — adjacent thesis |
| ramp.com | **2/5** | Horizontal corporate spend SaaS |
| glean.com | **2/5** | Enterprise search SaaS |
| mercury.com | **2/5** | Horizontal banking SaaS |

**Calendar (12 events, 1-3-4-3-1 non-uniform density):**

```
Thu May 28 (1)  Devon × Anduril
Fri May 29 (3)  Devon × Modal · Joe × Anduril · Sara × Hadrian
Mon Jun 1  (4)  Sara × Anduril · Joe × Hadrian · Joe × Modal · Devon × Ramp
Tue Jun 2  (3)  Devon × Glean · Sara × Mercury · Joe × Glean
Wed Jun 3  (1)  Devon × Mercury
```

Cross-partner company overlap: Anduril 3×, Hadrian 2×, Modal 2×, Glean 2× (same-day Devon+Joe), Mercury 2×.

Per-partner: Devon 5, Sara 3, Joe 4.

To re-seed: `python -m api.seeds.seed` (Devon's portion only); the Sara/Joe events were added via a one-off Python script that the chat history has (see the calendar-redesign moment). If you need to re-create them, easiest is to run the python in `chat-history` or just re-paste the calendar INSERT SQL.

---

## 9. Important file paths

```
pre-meeting-brief/
├── CLAUDE.md                              ← YOU ARE HERE
├── README.md                              ← Short project summary
├── docs/
│   ├── approach.md                        ← THE submission deliverable (12 pages)
│   ├── review-gaps.md                     ← Phase 4: senior-architect critique + action plan
│   └── superpowers/plans/
│       ├── 2026-05-28-pmb-foundation.md   ← Phase 0 + 1 plan
│       └── 2026-05-28-pmb-phase-2.md      ← Phase 2 plan
├── app/                                   ← Next.js App Router
│   ├── layout.tsx                         ← TopBar + SiteFooter wrap
│   ├── page.tsx                           ← Calendar agenda
│   ├── briefs/[id]/page.tsx               ← Brief reader (dashboard)
│   ├── admin/page.tsx                     ← Password gate + form + recent runs
│   ├── approach/page.tsx                  ← Renders docs/approach.md
│   ├── pipeline/page.tsx                  ← 4-tab interactive pipeline
│   └── globals.css                        ← Tailwind v4 + scroll-margin
├── components/
│   ├── TopBar.tsx, SiteFooter.tsx         ← Site-wide nav
│   ├── CalendarDay.tsx, CalendarEventCard ← Date-grouped cards (color-coded)
│   ├── BriefCard.tsx                      ← (legacy from list view; still imported in places)
│   ├── ThesisFitBadge.tsx
│   ├── AuditPanel.tsx                     ← Rebuilt Phase 3 — 3 sub-tables
│   ├── HowAssembled.tsx                   ← Thin shim re-exporting AuditPanel
│   ├── DashboardSection.tsx, ConfidenceDot.tsx
│   ├── ArchitectureSvg.tsx                ← Hand-authored 294-line SVG
│   ├── PipelineStageCard.tsx              ← Expandable stage cards
│   ├── SampleRunTrace.tsx                 ← Replays a real completed run
│   ├── AdminForm.tsx                      ← Password-aware trigger form
│   ├── RunStatus.tsx                      ← Live per-node timeline
│   ├── RecentRuns.tsx                     ← Last 10 runs, refresh every 10s
│   └── TocSidebar.tsx                     ← Nested TOC + scroll-spy
├── lib/
│   ├── api.ts                             ← fetchAgenda, fetchBrief; SSR-safe resolveApiBase
│   └── types.ts                           ← AgendaItem, BriefResponse, etc.
├── api/
│   ├── index.py                           ← FastAPI ASGI entry; mounts all routers
│   ├── config.py                          ← pydantic-settings (POSTGRES_URL, ANTHROPIC_*, etc.)
│   ├── llm.py                             ← Anthropic client factory (base_url-aware)
│   ├── routes/
│   │   ├── health.py
│   │   ├── agenda.py
│   │   ├── briefs.py
│   │   └── triggers.py                    ← POST manual + GET runs + GET runs/{id}
│   ├── db/
│   │   ├── session.py                     ← async psycopg3
│   │   ├── models.py                      ← All 8 SQLAlchemy models
│   │   └── migrations/versions/
│   ├── providers/
│   │   ├── base.py                        ← DataProvider Protocol + ProviderResult
│   │   ├── specter.py, crunchbase.py, pitchbook.py, attio.py
│   │   └── specter_mcp_client.py          ← Subprocess-launches the MCP server
│   ├── pipeline/
│   │   ├── state.py                       ← BriefState pydantic model
│   │   ├── nodes.py                       ← resolve_company, fetch_all, render_and_persist
│   │   ├── merge.py                       ← Priority chains + 6 conflict detectors
│   │   ├── graph.py                       ← LangGraph StateGraph + _wrap_node
│   │   ├── progress.py                    ← record_node_start/complete/failed
│   │   ├── prompts.py                     ← SYSTEM_PROMPT, build_brief_prompt
│   │   └── agents/
│   │       ├── qualification.py
│   │       ├── research.py
│   │       ├── data_quality.py
│   │       └── synthesis.py
│   ├── seeds/seed.py                      ← One-shot DB seed (companies + Devon's calendar + Anduril brief)
│   └── distribution/
│       ├── __init__.py
│       └── calendar_writeback.py          ← Phase 4: Google Calendar payload builder + log-only stub
├── eval/                                  ← Phase 4: brief-quality eval
│   ├── golden/criteria.json               ← Hand-curated criteria for Anduril, Hadrian, Mercury
│   ├── rubric.py                          ← Haiku-as-judge with forced tool_use submit_eval_scores
│   └── runner.py                          ← CLI: `python -m eval.runner [--company X]`
├── mcp_servers/
│   └── specter_mcp/
│       ├── server.py                      ← FastMCP with fetch_company tool
│       └── README.md                      ← How to run + connect to Claude Desktop
├── fixtures/
│   ├── anduril.com/  hadrian.co/  modal.com/  ramp.com/  glean.com/  mercury.com/
│   └── (each has specter.json, crunchbase.json, pitchbook.json, attio.json)
├── tests/                                 ← pytest, ~84 passing
├── vercel.json                            ← maxDuration: 300, rewrites
├── alembic.ini
├── pyproject.toml                         ← Python deps including langgraph, mcp, anthropic
├── requirements.txt                       ← Same deps for Vercel build
├── package.json                           ← Next, react-markdown, recharts, etc.
└── .env.local                             ← REAL secrets — gitignored! Pull via `vercel env pull`
```

---

## 10. Environment variables

Set on Vercel (production + development) and pulled to `.env.local` via `vercel env pull`:

| Var | Purpose |
|---|---|
| `POSTGRES_URL` | Pooled URL for runtime queries |
| `POSTGRES_URL_NON_POOLING` | Direct URL for Alembic migrations |
| `ANTHROPIC_API_KEY` | LiteLLM proxy key (NOT a direct Anthropic key) |
| `ANTHROPIC_BASE_URL` | `https://api.mercury.weather.com/litellm` |
| `ADMIN_PASSWORD` | `rdSaGl_zcV7dfkZklglshlWsZHYAWZOP` (gates /admin) |

Plus a bunch of auto-bound Neon vars (`PGHOST`, `PGUSER`, etc.) that we don't use directly.

**Never** commit `.env.local`. It's in `.gitignore`.

---

## 11. Common commands

```bash
# Setup (one-time, on new machine)
git clone git@github.com:rishav1305/pre-meeting-brief.git
cd pre-meeting-brief
npm install
pip3 install --user --break-system-packages -r requirements.txt

# Vercel CLI (if not installed)
npm config set prefix ~/.npm-global
npm install -g vercel
~/.npm-global/bin/vercel login              # interactive browser OAuth

# Pull env vars locally
~/.npm-global/bin/vercel env pull .env.local

# Run local dev (rare — most work is against the live deploy)
npm run dev                                  # Next.js on :3000
set -a && source .env.local && set +a && uvicorn api.index:app --port 8000

# Tests
set -a && source .env.local && set +a && python3 -m pytest tests/ -q

# Generate a brief via the live admin API
ADMIN_PW=$(grep '^ADMIN_PASSWORD=' .env.local | cut -d'"' -f2)
curl -X POST -H "X-Admin-Password: $ADMIN_PW" -H "Content-Type: application/json" \
  -d '{"domain":"hadrian.co","company_name":"Hadrian","partner":"Devon","meeting_date":"2026-06-08"}' \
  https://rishavchatterjee.com/pre-meeting-brief/api/triggers/manual

# Deploy (auto-deploy from GitHub is NOT wired; deploy manually)
~/.npm-global/bin/vercel deploy --prod --yes

# Migrate (against live DB — production side-effect)
set -a && source .env.local && set +a && alembic upgrade head

# Tail recent runs
curl -sS "https://rishavchatterjee.com/pre-meeting-brief/api/triggers/runs?limit=5" | python3 -m json.tool
```

---

## 12. Known issues, gotchas, and their fixes

These all bit me at some point — documented here so future-you doesn't re-discover them.

| Issue | Fix |
|---|---|
| Neon Postgres URL has `?channel_binding=require` which asyncpg rejects | Use psycopg3 (`postgresql+psycopg://`). Already in `api/db/session.py`. |
| Vercel function `maxDuration` ceiling on Hobby plan is 300s | Set to 300 in `vercel.json`. Pipeline tuned to fit within this. |
| LiteLLM proxy ~36 tok/sec is slower than direct Anthropic (~80) | Synthesis tuned to `_PER_CALL_TIMEOUT_S=240`, `_WALLCLOCK_BUDGET_S=540`. Most briefs land in 60-180s. |
| Claude wraps JSON in ` ```json … ``` ` markdown fences → naive `json.loads` fails | Switched synthesis to **forced `tool_use`** with `submit_brief` schema. SDK validates structured output. Other agents (qualification, DQ) use fence-tolerant parser in `_parse_llm_json`. |
| Long-running parallel briefs sometimes leave etl_run_log rows as `running` after Vercel kills the function | Manually mark failed via SQL. Eventually need a sweeper job. |
| Next.js 16 build sometimes Bus-errors in WSL/sandboxed envs | Build on Vercel. Local dev with `npm run dev` is fine. |
| SQLAlchemy doesn't auto-flush in-place mutations of JSONB lists | In `api/pipeline/progress.py`, use `copy.deepcopy` before mutating `row.node_history`. |
| Server components can't use relative URLs for `fetch()` | `lib/api.ts::resolveApiBase()` uses `VERCEL_PROJECT_PRODUCTION_URL` env var (NOT `VERCEL_URL` — that one has deployment protection on Hobby). |
| portfolio_app's auto-deploy from GitHub failed when Supabase DB was paused | Unpause Supabase and re-trigger deploy. |
| GitHub auto-deploy on `pre-meeting-brief` Vercel project is NOT wired | Deploy via CLI: `vercel deploy --prod --yes`. |

---

## 13. The framing decisions (don't change these)

These came up in conversation and got locked in — important for not re-litigating:

- **Agentic where judgment helps, deterministic where consistency matters.** Merge stays deterministic (priority chains from DD). Agents only at qualification, research, DQ, synthesis.
- **Forced `tool_use` for structured output.** Don't go back to parsing markdown JSON — the proxy produces enough quirks that parsing is brittle.
- **`specter-mcp` runs as a real subprocess.** Not in-process. This is the "real MCP demo." Other providers (CB, PB, Attio) stay in-process per the spec.
- **No Vercel Cron yet.** Manual trigger only. Cron is a Phase 3+ stretch.
- **Single-tenant single-firm.** Multi-tenancy is a production roadmap item (§10 of approach doc), not built.
- **Reseed strategy.** Calendar reseeds are idempotent-by-wipe. We do `DELETE FROM calendar_events; INSERT INTO calendar_events (...)`. Briefs are NOT wiped — their meeting_date gets updated to match the new schedule per (partner, company).
- **Submission file is `docs/approach.md`.** ~5,700 words, 12 pages. Rendered at `/pre-meeting-brief/approach` with sticky nested TOC sidebar.

---

## 14. What's NOT built (Phase 4+ candidates)

| Item | Why deferred |
|---|---|
| ~~Vercel Cron daily 06:00 UTC trigger~~ | **Built in Phase 4** — `/api/triggers/scan` + cron config in `vercel.json` |
| ~~`data_quality_flags` table actually populated by the pipeline~~ | **Built in Phase 4** — `render_and_persist` writes rows; brief API returns them; FlagsTeaser surfaces them |
| Full multi-tenancy (`firm_id` partitioning on all canonical tables + row-level security) | Phase 4 added `firm_config` table + parameterized system prompt — the framing seam is in place. `firm_id` column on canonical entities + RLS is still production roadmap |
| Brief feedback loop (thumbs up/down → `brief_feedback` table) | Schema exists in plan; UI not built |
| ~~Eval rubric (Haiku-scored on 5 axes against golden set)~~ | **Built in Phase 4** — `eval/` with Haiku-as-judge, golden criteria for 3 companies, CLI runner |
| Real Google Calendar OAuth dispatch | Phase 4 wired the payload-building + log-only stub on `pre_meeting_brief.distribution_log`. Production flip = OAuth + flip `_LOG_ONLY=False` in `api/distribution/calendar_writeback.py` |
| PDF / Google Doc export | Spec'd as cuttable in Phase 1; HTML print stylesheet is the substitute |
| Attio CRM writeback (folder link on company record) | Stub link in DB; no API call. Same architectural pattern as the calendar writeback — add `api/distribution/attio_writeback.py` |
| Live tool_call streaming via SSE | Polling every 2s is good enough for 60-180s pipelines |
| GitHub auto-deploy from pre-meeting-brief repo to Vercel | Vercel GitHub app installation never succeeded; manual `vercel deploy` works fine |
| Real prompt-injection HTML sanitization + output-side regex guard | Phase 4 added trust-boundary tagging at the prompt level; production also needs input sanitization before tagging and output-side red-team eval |

If the reviewer asks "what's next?", point them at the **Production roadmap** section of `docs/approach.md` §10 — that's the canonical answer.

---

## 15. Conventions (keep using these)

- **Commit messages**: conventional commits with phase tag, e.g. `feat(phase-3): add recent runs panel`. Use `fix(phase-X): ...` for fixes within a phase. Use `chore: ...` for non-feature stuff like gitignore tweaks.
- **Co-author trailer**: every commit Claude makes ends with `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
- **Tests**: pytest + pytest-asyncio. Mock external calls (Anthropic SDK, Postgres) for unit tests. Integration tests gated by `PMB_RUN_INTEGRATION=1` env var.
- **Branch**: everything on `master`. No feature branches (POC). Direct commits authorized.
- **Push cadence**: each subagent commits but does NOT push — the controller (Claude or human) handles `git push`.
- **Subagent dispatch**: prefer `shuri` over `general-purpose` for code work — better quality reports, sharper deviations. Disjoint-file parallel dispatch is safe; same-file parallel is not (skill rule).
- **No secrets in commits, ever.** `.env*` is gitignored; `.env.example` has placeholders only.

---

## 16. If you're picking this up fresh — start here

1. `cd ~/pre-meeting-brief` (or clone fresh: `git clone git@github.com:rishav1305/pre-meeting-brief.git`)
2. `git log --oneline -20` — see the last 20 commits to orient on what just happened
3. Read **this file** (CLAUDE.md) end-to-end
4. Skim `docs/approach.md` — the submission doc
5. Visit https://rishavchatterjee.com/pre-meeting-brief and click around to see the current live state
6. If you need to generate a brief, use `/admin` with the password above
7. If you need to debug a stuck run, query Postgres directly: `SELECT * FROM etl_run_log ORDER BY started_at DESC LIMIT 5;` via `psql "$POSTGRES_URL_NON_POOLING"`
8. If the user asks for "the next thing" without specifics, the candidates are in §14 (Phase 4+) — propose one or two and let them pick

---

*Last updated 2026-05-28 by Claude. Phase 4 session closed senior-architect-review gaps before the 2026-05-29 submission: doc fidelity, Assignment Re-read, firm_config parameterization, data_quality_flags persistence, Vercel Cron + scan endpoint, Google Calendar distribution stub, trust-boundary tagging, eval rubric, confidence-dot re-alignment. Migrations `0003_firm_config.py` and `0004_brief_distribution.py` need `alembic upgrade head` against the live DB; deploy via `vercel deploy --prod --yes` to ship.*
