# Pre-Meeting Brief — Project Memory

## What this is
A take-home submission **to Capital Numbers** for the **AI-Native Tech Lead** role (Gurgaon). The assignment uses **Renegade Capital** as the example VC client — so the platform is designed around Renegade's thesis, schema, and tickets, but the deliverable is the architecture + working POC for Capital Numbers to evaluate.

**Important framing**: when documents/code refer to "the firm" or "Renegade", that's the example/demo client baked into the take-home materials. The hiring entity is Capital Numbers.

## Deliverables (due 2026-05-29 EOD)
- Live URL: https://rishavchatterjee.com/pre-meeting-brief
- Repo: https://github.com/rishav1305/pre-meeting-brief
- Approach doc: docs/approach.md

## Architecture (one-screen summary)
- Single Vercel project. Next.js UI (basePath /pre-meeting-brief) + Python FastAPI at api/index.py
- Vercel Postgres for storage (mirrors the Data Dictionary 1:1)
- 4 data providers behind a DataProvider interface
  - specter-mcp = standalone MCP server (separate process)
  - crunchbase / pitchbook / attio = in-process providers, same interface
  - All read fixtures from disk for the POC
- Agentic synthesis (Phase 2): LangGraph orchestrator + 4 sub-agents (Qualification, Research, Data Quality, Synthesis) + real Anthropic web_search
- Deterministic core: domain normalize, merge with priority chains, DB writes, rendering

## Phase status
- Phase 0: scaffold + deploy → see plan at docs/superpowers/plans/2026-05-28-pmb-foundation.md
- Phase 1: schema + fixtures + providers + agenda/reader UI (this plan)
- Phase 2: pipeline + agents (next plan)
- Phase 3: admin + audit UX + cron (next plan after Phase 2)

## Key constants
- 6 demo companies: Anduril, Hadrian, Modal, Ramp, Glean, Mercury (thesis_fit varies 2-5)
- Postgres: Vercel-managed Neon; use POSTGRES_URL_NON_POOLING for Alembic, POSTGRES_URL for runtime
- Latency target: <60s end-to-end per brief
- Cost target: <$0.20 per brief
- Brief format: dashboard hybrid (above-fold cards + below-fold prose deep-dives)
- Confidence UX: inline dots + audit panel on click
- Thesis fit: surface above-the-fold with score + reasoning + bear case

## Conventions
- Commit messages: conventional commits with phase tag, e.g. `feat(phase-1): add specter provider`
- Tests: pytest, pytest-asyncio. Mock external calls; fixtures live in tests/ + fixtures/
- Provider interface: see api/providers/base.py
- Database: SQLAlchemy 2.x async, Alembic migrations in api/db/migrations/versions/
- Frontend: Next.js App Router, no client-side data fetching libraries (just fetch() in server components)
