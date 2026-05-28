# Pre-Meeting Brief Platform

**Take-home submission** · [Capital Numbers](https://www.capitalnumbers.com/) · **AI-Native Tech Lead** role (Gurgaon).

An agentic pre-meeting brief platform designed around **Renegade Capital** (the example VC client in the assignment materials). Triggered on first meetings with a company in a rolling 3-month window. Pulls data from CRM (Attio), third-party sources (Specter, Crunchbase, PitchBook), and live web. Synthesises a tiered dashboard brief tuned to Renegade's "Markets That Matter" thesis via an agentic workflow.

**Approach document**: [`docs/approach.md`](docs/approach.md) — full architecture, data model, agentic workflow design, MCP server design, phase plan, and production roadmap.

**Live**: https://rishavchatterjee.com/pre-meeting-brief

**Status**: Phase 0 + Phase 1 + Phase 2 live. End-to-end agentic pipeline (LangGraph orchestrator + 4 agents — Qualification, Research with Claude web_search, Data Quality, Synthesis with forced tool_use for guaranteed valid JSON) runs in ~60s on Vercel. Reviewer can visit `/admin`, type any domain, and watch a brief generate live.

## Development

```bash
make install          # install npm + pip deps
cp .env.example .env  # fill in POSTGRES_URL after Vercel Postgres provisioning
make migrate          # run Alembic migrations
make seed             # seed calendar_events + sample briefs
make dev              # next dev server on :3000
make test             # pytest suite
```

## Structure

- `app/` — Next.js App Router (`basePath: /pre-meeting-brief`)
- `api/` — Python FastAPI serverless function
- `mcp_servers/` — Standalone MCP servers (Phase 1+)
- `fixtures/` — Synthetic JSON fixtures per company domain
- `docs/approach.md` — submission deliverable
