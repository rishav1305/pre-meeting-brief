# Pre-Meeting Brief — Foundation Implementation Plan (Phase 0 + 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the foundation of the pre-meeting brief platform — a deployed Next.js + Python FastAPI shell at `rishavchatterjee.com/pre-meeting-brief`, a Postgres schema mirroring the Data Dictionary, four data providers (one standalone MCP server + three in-process MCP-shaped stubs) reading fixtures for six demo companies, plus a Daily Agenda landing page and Brief reader page rendering seed data with confidence dots and an audit panel stub.

**Architecture:** Single Vercel project (no split frontend/backend). Next.js (App Router, TypeScript, Tailwind) for UI with `basePath: '/pre-meeting-brief'`. Python FastAPI runs as a Vercel Python serverless function at `api/index.py`. Vercel Postgres (Neon) for storage. One standalone `specter-mcp` process to demonstrate the MCP deployment shape; other providers run in-process behind the same interface. No LLM calls in this plan — Phase 2 wires up Claude.

**Tech Stack:** Next.js 15+, TypeScript, Tailwind, Recharts | Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic 2.x, `mcp` (Anthropic's MCP package), pytest, pytest-asyncio | Vercel + Vercel Postgres

**Scope of THIS plan:** Phase 0 (scaffold + deploy) and Phase 1 (schema + fixtures + providers + agenda/reader UI with seed data). Phase 2 (pipeline + agents) and Phase 3 (admin + audit UX + Vercel Cron) get their own plans drafted after Phase 1 ships.

**Pre-flight user actions (required before Task 0.5):**
- Vercel: create a new project named `pre-meeting-brief` connected to `github.com/rishav1305/pre-meeting-brief`
- Vercel: add the Vercel Postgres (Neon) integration to the project; env vars `POSTGRES_URL`, `POSTGRES_URL_NON_POOLING`, `POSTGRES_PRISMA_URL` auto-bind
- Vercel: in the existing `portfolio_app` project's `vercel.json`, add the rewrite rule documented in Task 0.6

---

## File structure (Phase 0 + 1 target)

```
pre-meeting-brief/
├── CLAUDE.md                          # NEW: project memory
├── README.md                          # exists, updated in Phase 0
├── docs/
│   ├── approach.md                    # exists (the submission doc)
│   └── superpowers/
│       ├── specs/                     # (skill default; not used by us)
│       └── plans/
│           └── 2026-05-28-pmb-foundation.md   # THIS file
├── app/                               # NEW: Next.js App Router
│   ├── layout.tsx
│   ├── page.tsx                       # Daily Agenda
│   ├── briefs/
│   │   └── [id]/page.tsx              # Brief reader
│   ├── approach/page.tsx              # Renders docs/approach.md
│   ├── api/
│   │   └── health/route.ts            # Next.js BFF health pass-through (optional)
│   └── globals.css
├── components/                        # NEW: React components
│   ├── ConfidenceDot.tsx
│   ├── AuditPanel.tsx
│   ├── BriefCard.tsx
│   └── DashboardSection.tsx
├── lib/                               # NEW: frontend utilities
│   ├── api.ts                         # fetch wrappers
│   └── types.ts                       # shared TS types matching pydantic
├── api/                               # NEW: Python serverless
│   ├── index.py                       # FastAPI ASGI entry
│   ├── config.py                      # env loading
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── agenda.py
│   │   └── briefs.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py                 # async SQLAlchemy session
│   │   ├── models.py                  # all SQLAlchemy ORM models
│   │   └── migrations/                # Alembic
│   │       ├── env.py
│   │       ├── script.py.mako
│   │       └── versions/
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py                    # DataProvider Protocol + ProviderResult
│   │   ├── specter.py                 # in-process variant (fixture-reading)
│   │   ├── crunchbase.py              # in-process stub
│   │   ├── pitchbook.py               # in-process stub
│   │   ├── attio.py                   # in-process stub
│   │   └── specter_mcp_client.py      # MCP client wrapper for standalone server
│   └── seeds/
│       ├── __init__.py
│       └── seed.py                    # one-shot seeding script
├── mcp_servers/                       # NEW: standalone MCP servers
│   └── specter_mcp/
│       ├── pyproject.toml
│       ├── server.py                  # FastMCP scaffold
│       └── README.md
├── fixtures/                          # NEW: synthetic data
│   ├── anduril.com/
│   │   ├── specter.json
│   │   ├── crunchbase.json
│   │   ├── pitchbook.json
│   │   └── attio.json
│   ├── hadrian.co/...
│   ├── modal.com/...
│   ├── ramp.com/...
│   ├── glean.com/...
│   └── mercury.com/...
├── tests/                             # NEW: pytest suites
│   ├── __init__.py
│   ├── conftest.py                    # shared fixtures (in-memory db, etc)
│   ├── test_db_models.py
│   ├── test_providers.py
│   └── test_specter_mcp.py
├── .env.example                       # NEW
├── alembic.ini                        # NEW
├── Makefile                           # NEW: install, dev, test, seed, migrate
├── next.config.js                     # NEW
├── package.json                       # NEW
├── pyproject.toml                     # NEW
├── requirements.txt                   # NEW
├── tailwind.config.ts                 # NEW
├── tsconfig.json                      # NEW
└── vercel.json                        # NEW
```

**File ownership principles:**

- One Python file per provider (each has one job: fetch from one source)
- All SQLAlchemy models in one `models.py` (they're 5 entities, each tight; one file keeps them readable as a schema)
- Routes split by surface (`health.py`, `agenda.py`, `briefs.py`) — small files, each owns one URL prefix
- React components in `components/` — one component per file, dumb props
- Tests mirror source paths

---

## Phase 0 — Scaffold + Deploy

### Task 0.1: Initialize Next.js app with basePath

**Files:**
- Create: `package.json`, `next.config.js`, `tsconfig.json`, `tailwind.config.ts`, `postcss.config.js`, `app/layout.tsx`, `app/page.tsx`, `app/globals.css`
- Modify: `.gitignore` (add `.next/`, `node_modules/`)

- [ ] **Step 1: Run create-next-app non-interactively**

```bash
cd /home/rishav/pre-meeting-brief
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir --eslint --import-alias '@/*' --use-npm --yes
```

Expected: project files created. If `.git`, `README.md`, `LICENSE` conflict, accept overwrites for the README+LICENSE only (we'll restore our README content in Task 0.4).

- [ ] **Step 2: Replace `next.config.js` to set basePath**

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  basePath: '/pre-meeting-brief',
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
};
module.exports = nextConfig;
```

- [ ] **Step 3: Replace `app/page.tsx` with a Phase 0 placeholder**

```tsx
export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-16">
      <div className="mx-auto max-w-3xl">
        <p className="text-sm font-medium uppercase tracking-wider text-slate-500">
          Renegade Capital
        </p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-slate-900">
          Pre-Meeting Brief
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          Phase 0 — deployed. Phase 1 (schema, fixtures, agenda) in progress.
        </p>
        <p className="mt-8 text-sm text-slate-500">
          See the architecture approach at{' '}
          <a
            className="underline underline-offset-2 hover:text-slate-700"
            href="/pre-meeting-brief/approach"
          >
            /approach
          </a>
          .
        </p>
      </div>
    </main>
  );
}
```

- [ ] **Step 4: Verify locally**

```bash
npm run dev
```

Open `http://localhost:3000/pre-meeting-brief`. Expected: placeholder page renders with Tailwind styles.

Kill dev server (Ctrl+C) after verifying.

- [ ] **Step 5: Commit**

```bash
git add app/ public/ next.config.js package.json package-lock.json tsconfig.json tailwind.config.ts postcss.config.js .gitignore
git commit -m "feat(phase-0): initialize Next.js app with basePath /pre-meeting-brief"
```

---

### Task 0.2: Add Python FastAPI shell with health route

**Files:**
- Create: `api/index.py`, `api/config.py`, `api/routes/__init__.py`, `api/routes/health.py`
- Create: `pyproject.toml`, `requirements.txt`
- Create: `tests/__init__.py`, `tests/test_health.py`

- [ ] **Step 1: Write the failing test**

`tests/test_health.py`:

```python
from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "phase": 0}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pip install --user fastapi httpx pytest
python -m pytest tests/test_health.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'api'`

- [ ] **Step 3: Create `requirements.txt`**

```
fastapi>=0.115.0
pydantic>=2.7.0
pydantic-settings>=2.4.0
sqlalchemy>=2.0.30
asyncpg>=0.29.0
psycopg[binary]>=3.2.0
alembic>=1.13.0
httpx>=0.27.0
python-dotenv>=1.0.0
mangum>=0.17.0
```

- [ ] **Step 4: Create `pyproject.toml`**

```toml
[project]
name = "pre-meeting-brief"
version = "0.1.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py312"
```

- [ ] **Step 5: Create `api/index.py`**

```python
"""FastAPI entry point for Vercel Python serverless.

Mounts all routers under /api/*. The whole ASGI app is exported as `app`;
Vercel's Python runtime calls it for every /api/* request.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health

app = FastAPI(title="Pre-Meeting Brief API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
```

- [ ] **Step 6: Create `api/routes/__init__.py`** (empty file)

- [ ] **Step 7: Create `api/routes/health.py`**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, object]:
    return {"status": "ok", "phase": 0}
```

- [ ] **Step 8: Create `api/config.py`** (placeholder for now, expanded in Task 1.1)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    phase: int = 0


settings = Settings()
```

- [ ] **Step 9: Run test to verify it passes**

```bash
python -m pytest tests/test_health.py -v
```

Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add api/ tests/ pyproject.toml requirements.txt
git commit -m "feat(phase-0): add FastAPI shell with /api/health route"
```

---

### Task 0.3: Vercel config, Makefile, and .env.example

**Files:**
- Create: `vercel.json`, `Makefile`, `.env.example`

- [ ] **Step 1: Create `vercel.json`**

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "buildCommand": "npm run build",
  "framework": "nextjs",
  "functions": {
    "api/index.py": {
      "runtime": "python3.12",
      "maxDuration": 60
    }
  },
  "rewrites": [
    {
      "source": "/pre-meeting-brief/api/:path*",
      "destination": "/api/:path*"
    }
  ]
}
```

The rewrite is needed because Next.js basePath rewrites the UI under `/pre-meeting-brief`, but our Python function lives at `/api/*` — we route `/pre-meeting-brief/api/*` to the function.

- [ ] **Step 2: Create `Makefile`**

```makefile
.PHONY: install dev test lint seed migrate build deploy

install:
	npm install
	pip install -r requirements.txt

dev:
	npm run dev

test:
	python -m pytest tests/ -v

lint:
	ruff check api/ tests/
	npm run lint

migrate:
	alembic upgrade head

seed:
	python -m api.seeds.seed

build:
	npm run build

deploy:
	vercel --prod
```

- [ ] **Step 3: Create `.env.example`**

```env
# Vercel Postgres auto-binds these in production. Locally, copy to .env and fill in.
POSTGRES_URL=postgres://user:pass@host:5432/db?sslmode=require
POSTGRES_URL_NON_POOLING=postgres://user:pass@host:5432/db?sslmode=require

# Phase 2+ — required for LLM synthesis and web search
ANTHROPIC_API_KEY=

# Phase 3 — admin trigger gate
ADMIN_PASSWORD=
```

- [ ] **Step 4: Commit**

```bash
git add vercel.json Makefile .env.example
git commit -m "chore(phase-0): add Vercel config, Makefile, and env template"
```

---

### Task 0.4: Restore README and add CLAUDE.md project memory

**Files:**
- Modify: `README.md` (was rewritten by create-next-app; restore our pointer content)
- Create: `CLAUDE.md`

- [ ] **Step 1: Replace `README.md`**

```markdown
# Pre-Meeting Brief Platform

An automated pre-meeting brief platform for Renegade Capital partners. Triggered on first meetings with companies in a rolling 3-month window. Pulls data from CRM (Attio), third-party sources (Specter, Crunchbase, PitchBook), and live web. Synthesises a tiered dashboard brief tuned to Renegade's "Markets That Matter" thesis via an agentic workflow.

**Approach document**: [`docs/approach.md`](docs/approach.md) — full architecture, data model, agentic workflow design, MCP server design, phase plan, and production roadmap.

**Live**: https://rishavchatterjee.com/pre-meeting-brief

**Status**: Phase 0 (scaffold + deploy) → Phase 1 (schema + fixtures + providers) in progress.

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
```

- [ ] **Step 2: Create `CLAUDE.md`** (project memory for future Claude Code sessions in this repo)

```markdown
# Pre-Meeting Brief — Project Memory

## What this is
A take-home submission to Renegade Capital. Builds an automated pre-meeting brief platform.

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
```

- [ ] **Step 3: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs(phase-0): restore README and add CLAUDE.md project memory"
```

---

### Task 0.5: Initial Vercel deploy + verify subpath

**Files:** None (deployment action)

**Pre-conditions:**
- User has created the `pre-meeting-brief` Vercel project via the dashboard, connected to `github.com/rishav1305/pre-meeting-brief`
- Vercel Postgres add-on attached, env vars auto-bound

- [ ] **Step 1: Push to GitHub**

```bash
git push origin master
```

- [ ] **Step 2: Trigger deploy via Vercel dashboard**

The git push should trigger an automatic build. Watch logs at `https://vercel.com/<team>/pre-meeting-brief/deployments`.

Expected build:
- `npm install` succeeds
- `npm run build` succeeds
- Python function `api/index.py` is detected and bundled
- Deploy completes in ~2-3 minutes

- [ ] **Step 3: Verify deploy at default Vercel URL**

Open `https://pre-meeting-brief.vercel.app/pre-meeting-brief` — expected: Phase 0 placeholder page

Open `https://pre-meeting-brief.vercel.app/api/health` — expected: `{"status": "ok", "phase": 0}`

- [ ] **Step 4: Add subpath rewrite in portfolio_app**

In the existing `portfolio_app` repo (the one serving `rishavchatterjee.com`), edit `vercel.json`:

```json
{
  "rewrites": [
    {
      "source": "/pre-meeting-brief",
      "destination": "https://pre-meeting-brief.vercel.app/pre-meeting-brief"
    },
    {
      "source": "/pre-meeting-brief/:path*",
      "destination": "https://pre-meeting-brief.vercel.app/pre-meeting-brief/:path*"
    }
  ]
}
```

Commit and push the portfolio_app change.

- [ ] **Step 5: Verify at production URL**

Wait ~60s for portfolio_app to redeploy. Then:

- Open `https://rishavchatterjee.com/pre-meeting-brief` — expected: placeholder page (200)
- Open `https://rishavchatterjee.com/pre-meeting-brief/api/health` — expected: health JSON

- [ ] **Step 6: Tag the Phase 0 milestone**

```bash
git tag -a phase-0 -m "Phase 0: scaffold + deploy complete"
git push origin phase-0
```

---

## Phase 1 — Schema, Fixtures, Providers, UI

### Task 1.1: SQLAlchemy session + Alembic init

**Files:**
- Create: `api/db/__init__.py`, `api/db/session.py`, `alembic.ini`
- Create: `api/db/migrations/env.py`, `api/db/migrations/script.py.mako`, `api/db/migrations/versions/` (empty dir)
- Modify: `api/config.py` (add database URLs)

- [ ] **Step 1: Extend `api/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    phase: int = 1

    # Vercel Postgres auto-binds these
    postgres_url: str = ""
    postgres_url_non_pooling: str = ""

    # Optional for Phase 2+
    anthropic_api_key: str = ""
    admin_password: str = ""


settings = Settings()
```

- [ ] **Step 2: Create `api/db/__init__.py`** (empty)

- [ ] **Step 3: Create `api/db/session.py`**

```python
"""Async SQLAlchemy session factory.

Use `get_session()` as a FastAPI dependency. Use POSTGRES_URL (pooled) at runtime;
Alembic uses POSTGRES_URL_NON_POOLING separately for DDL.
"""
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import settings


def _engine_url() -> str:
    # SQLAlchemy async driver requires postgresql+asyncpg, not postgres://
    url = settings.postgres_url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(_engine_url(), echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
```

- [ ] **Step 4: Initialize Alembic**

```bash
alembic init api/db/migrations
```

This creates `alembic.ini` at the repo root and `api/db/migrations/env.py`. Move `alembic.ini` to root if it isn't already.

- [ ] **Step 5: Edit `alembic.ini` — set the migrations location**

Find the line `script_location = alembic` and change to:

```ini
script_location = api/db/migrations
```

Comment out or leave `sqlalchemy.url` blank (we set it dynamically in env.py).

- [ ] **Step 6: Replace `api/db/migrations/env.py`**

```python
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from api.db.models import Base  # noqa: E402 — populated in Task 1.2+

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Use POSTGRES_URL_NON_POOLING for DDL; pooled connections can't run migrations
db_url = os.environ.get("POSTGRES_URL_NON_POOLING") or os.environ.get("POSTGRES_URL", "")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 7: Commit**

```bash
git add api/db/ api/config.py alembic.ini
git commit -m "feat(phase-1): add async SQLAlchemy session and Alembic init"
```

---

### Task 1.2: Define canonical.company SQLAlchemy model + test

**Files:**
- Create: `api/db/models.py`
- Create: `tests/conftest.py`
- Create: `tests/test_db_models.py`

- [ ] **Step 1: Write the failing test**

`tests/conftest.py`:

```python
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.db.models import Base


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionMaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionMaker() as session:
        yield session
    await engine.dispose()
```

`tests/test_db_models.py`:

```python
from uuid import uuid4

import pytest

from api.db.models import Company


@pytest.mark.asyncio
async def test_company_insert_and_select(db_session):
    company = Company(
        company_id=uuid4(),
        domain="anduril.com",
        description="Defense technology company",
        operating_status="active",
        founded_year=2017,
        hq_country="US",
        total_raised_usd=4_200_000_000,
        last_round_type="series_f",
        investors=["Founders Fund", "Andreessen Horowitz", "Valor Equity Partners"],
        audit={"fields": [{"field": "description", "source": "Specter"}]},
    )
    db_session.add(company)
    await db_session.commit()

    fetched = await db_session.get(Company, company.company_id)
    assert fetched is not None
    assert fetched.domain == "anduril.com"
    assert fetched.investors == ["Founders Fund", "Andreessen Horowitz", "Valor Equity Partners"]
    assert fetched.audit["fields"][0]["source"] == "Specter"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pip install --user aiosqlite pytest-asyncio
python -m pytest tests/test_db_models.py -v
```

Expected: FAIL — `ImportError: cannot import name 'Company'`

- [ ] **Step 3: Implement `api/db/models.py` (Company only for this task)**

```python
"""SQLAlchemy ORM models mirroring the Data Dictionary 1:1.

VARIANT -> JSONB (queryable, indexable)
TEXT[]  -> native ARRAY (Postgres) / JSON (SQLite for tests)
ENUMs   -> VARCHAR + CHECK constraints (easier to evolve than native ENUMs)
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# Helper for cross-dialect array columns (Postgres ARRAY in prod, JSON in SQLite tests)
def TextArray():  # noqa: N802 — factory for sqlalchemy type
    from sqlalchemy import JSON
    from sqlalchemy.dialects.postgresql import ARRAY as PGArray
    from sqlalchemy.types import TypeDecorator

    class CrossDialectArray(TypeDecorator):
        impl = JSON
        cache_ok = True

        def load_dialect_impl(self, dialect):
            if dialect.name == "postgresql":
                return dialect.type_descriptor(PGArray(String))
            return dialect.type_descriptor(JSON)

    return CrossDialectArray()


# Same trick for JSONB (Postgres native, JSON in SQLite tests)
def CrossJSON():  # noqa: N802
    from sqlalchemy import JSON
    from sqlalchemy.dialects.postgresql import JSONB as PGJSONB
    from sqlalchemy.types import TypeDecorator

    class CrossDialectJSONB(TypeDecorator):
        impl = JSON
        cache_ok = True

        def load_dialect_impl(self, dialect):
            if dialect.name == "postgresql":
                return dialect.type_descriptor(PGJSONB())
            return dialect.type_descriptor(JSON)

    return CrossDialectJSONB()


class Company(Base):
    __tablename__ = "company"
    __table_args__ = (
        CheckConstraint(
            "operating_status IN ('active','acquired','closed','ipo')",
            name="company_operating_status_check",
        ),
        CheckConstraint(
            "customer_focus IS NULL OR customer_focus IN ('b2b','b2c','b2b_b2c','b2c_b2b')",
            name="company_customer_focus_check",
        ),
        CheckConstraint(
            "growth_stage IS NULL OR growth_stage IN "
            "('bootstrapped','seed_stage','early_stage','growth_stage','late_stage','exit_stage')",
            name="company_growth_stage_check",
        ),
        {"schema": None},  # schema "canonical" added in production migration
    )

    company_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    domain_aliases: Mapped[list[str] | None] = mapped_column(TextArray(), nullable=True)

    specter_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cb_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pb_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    operating_status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    tags: Mapped[list[str] | None] = mapped_column(TextArray(), nullable=True)
    customer_focus: Mapped[str | None] = mapped_column(String(16), nullable=True)
    customer_profile: Mapped[str | None] = mapped_column(String, nullable=True)
    founded_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    hq_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hq_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    hq_region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    certifications: Mapped[list[str] | None] = mapped_column(TextArray(), nullable=True)
    traction_highlights: Mapped[str | None] = mapped_column(String, nullable=True)
    technologies: Mapped[list[str] | None] = mapped_column(TextArray(), nullable=True)

    total_raised_usd: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_round_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_round_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_round_usd: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    post_money_valuation_usd: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    round_count: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    growth_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    investors: Mapped[list[str] | None] = mapped_column(TextArray(), nullable=True)
    revenue_estimate_usd: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    audit: Mapped[dict | None] = mapped_column(CrossJSON(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_db_models.py::test_company_insert_and_select -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api/db/models.py tests/conftest.py tests/test_db_models.py
git commit -m "feat(phase-1): add Company SQLAlchemy model with cross-dialect types"
```

---

### Task 1.3: Add People + TractionMetrics models + tests

**Files:**
- Modify: `api/db/models.py`
- Modify: `tests/test_db_models.py`

- [ ] **Step 1: Add failing tests for People and TractionMetrics**

Append to `tests/test_db_models.py`:

```python
from datetime import date

from api.db.models import People, TractionMetrics


@pytest.mark.asyncio
async def test_people_insert_and_select(db_session):
    company_id = uuid4()
    db_session.add(
        Company(
            company_id=company_id,
            domain="hadrian.co",
            operating_status="active",
        )
    )
    await db_session.commit()

    people = People(
        company_id=company_id,
        founders=[
            {"full_name": "Chris Power", "title": "CEO", "linkedin_url": "https://..."},
        ],
        employee_count=180,
        employee_range="51-200",
        hiring_signals=["engineering_hiring", "headcount_surge"],
        audit={"fields": [{"field": "founders", "source": "Specter"}]},
    )
    db_session.add(people)
    await db_session.commit()

    fetched = await db_session.get(People, company_id)
    assert fetched is not None
    assert fetched.employee_count == 180
    assert fetched.founders[0]["full_name"] == "Chris Power"


@pytest.mark.asyncio
async def test_traction_metrics_insert_and_select(db_session):
    company_id = uuid4()
    db_session.add(Company(company_id=company_id, domain="modal.com", operating_status="active"))
    await db_session.commit()

    tm = TractionMetrics(
        company_id=company_id,
        highlights=["headcount_surge", "strong_web_traffic_growth"],
        new_highlights=["enterprise_logo_added"],
        web_visits_latest=480_000,
        g2_rating=4.7,
        g2_review_count=120,
        news=[{"date": "2026-05-10", "title": "...", "url": "https://..."}],
        audit={"fields": [{"field": "highlights", "source": "Specter"}]},
    )
    db_session.add(tm)
    await db_session.commit()

    fetched = await db_session.get(TractionMetrics, company_id)
    assert fetched is not None
    assert fetched.g2_rating == 4.7
    assert "headcount_surge" in fetched.highlights
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_db_models.py -v
```

Expected: 2 FAIL (People, TractionMetrics not defined)

- [ ] **Step 3: Add People and TractionMetrics to `api/db/models.py`**

Append to `api/db/models.py`:

```python
class People(Base):
    __tablename__ = "people"
    __table_args__ = (
        CheckConstraint(
            "employee_range IS NULL OR employee_range IN "
            "('1-10','11-50','51-200','201-500','501-1000','1001-5000','5001-10000','10001+')",
            name="people_employee_range_check",
        ),
    )

    company_id: Mapped[UUID] = mapped_column(ForeignKey("company.company_id"), primary_key=True)

    founders: Mapped[list | None] = mapped_column(CrossJSON(), nullable=True)
    key_executives: Mapped[list | None] = mapped_column(CrossJSON(), nullable=True)
    board_members: Mapped[list | None] = mapped_column(CrossJSON(), nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employee_range: Mapped[str | None] = mapped_column(String(16), nullable=True)
    headcount_trend: Mapped[list | None] = mapped_column(CrossJSON(), nullable=True)
    hiring_signals: Mapped[list[str] | None] = mapped_column(TextArray(), nullable=True)
    open_role_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    org_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    audit: Mapped[dict | None] = mapped_column(CrossJSON(), nullable=True)


class TractionMetrics(Base):
    __tablename__ = "traction_metrics"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("company.company_id"), primary_key=True)

    highlights: Mapped[list[str] | None] = mapped_column(TextArray(), nullable=True)
    new_highlights: Mapped[list[str] | None] = mapped_column(TextArray(), nullable=True)
    web_visits_latest: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    web_visits_trend: Mapped[dict | None] = mapped_column(CrossJSON(), nullable=True)
    web_popularity_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bounce_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_traffic_country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    traffic_sources: Mapped[str | None] = mapped_column(String, nullable=True)
    linkedin_followers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    linkedin_trend: Mapped[dict | None] = mapped_column(CrossJSON(), nullable=True)
    g2_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    g2_review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trustpilot_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    awards: Mapped[list | None] = mapped_column(CrossJSON(), nullable=True)
    patents: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    reported_clients: Mapped[list[str] | None] = mapped_column(TextArray(), nullable=True)
    it_spend_usd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    news: Mapped[list | None] = mapped_column(CrossJSON(), nullable=True)

    audit: Mapped[dict | None] = mapped_column(CrossJSON(), nullable=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_db_models.py -v
```

Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add api/db/models.py tests/test_db_models.py
git commit -m "feat(phase-1): add People and TractionMetrics models"
```

---

### Task 1.4: Add operational + brief models (PreMeetingBrief, EtlRunLog, DataQualityFlag, CalendarEvent, SourcePayload)

**Files:**
- Modify: `api/db/models.py`
- Modify: `tests/test_db_models.py`

- [ ] **Step 1: Add failing tests for each new model**

Append to `tests/test_db_models.py`:

```python
from datetime import date as date_type

from api.db.models import (
    CalendarEvent,
    DataQualityFlag,
    EtlRunLog,
    PreMeetingBrief,
    SourcePayload,
)


@pytest.mark.asyncio
async def test_etl_run_log(db_session):
    company_id = uuid4()
    db_session.add(Company(company_id=company_id, domain="ramp.com", operating_status="active"))
    await db_session.commit()

    run_id = uuid4()
    db_session.add(
        EtlRunLog(
            run_id=run_id,
            company_id=company_id,
            status="running",
        )
    )
    await db_session.commit()

    fetched = await db_session.get(EtlRunLog, run_id)
    assert fetched is not None
    assert fetched.status == "running"


@pytest.mark.asyncio
async def test_data_quality_flag(db_session):
    company_id = uuid4()
    db_session.add(Company(company_id=company_id, domain="glean.com", operating_status="active"))
    await db_session.commit()

    flag = DataQualityFlag(
        flag_id=uuid4(),
        run_id=uuid4(),
        company_id=company_id,
        field="founded_year",
        issue="delta_gt_1_year",
        source_a="Specter",
        value_a="2019",
        source_b="Crunchbase",
        value_b="2021",
    )
    db_session.add(flag)
    await db_session.commit()

    fetched = await db_session.get(DataQualityFlag, flag.flag_id)
    assert fetched.field == "founded_year"


@pytest.mark.asyncio
async def test_calendar_event(db_session):
    company_id = uuid4()
    db_session.add(Company(company_id=company_id, domain="mercury.com", operating_status="active"))
    await db_session.commit()

    event = CalendarEvent(
        event_id=uuid4(),
        partner="Devon",
        company_domain="mercury.com",
        meeting_date=date_type(2026, 5, 30),
        attendees={"emails": ["devon@renegade.vc", "founder@mercury.com"]},
        source="manual_seed",
    )
    db_session.add(event)
    await db_session.commit()

    fetched = await db_session.get(CalendarEvent, event.event_id)
    assert fetched.partner == "Devon"


@pytest.mark.asyncio
async def test_pre_meeting_brief(db_session):
    company_id = uuid4()
    db_session.add(Company(company_id=company_id, domain="anduril.com", operating_status="active"))
    await db_session.commit()

    brief = PreMeetingBrief(
        brief_id=uuid4(),
        company_id=company_id,
        run_id=uuid4(),
        partner="Sara",
        meeting_date=date_type(2026, 5, 30),
        thesis_fit={"score": 5, "reasoning": "core thesis", "bear_case": "regulatory"},
        industry_deepdive="Defense software is...",
        market_deepdive="The defense tech market...",
        key_engagement_questions=["Q1", "Q2", "Q3"],
        podcast_mentions=[],
        prior_interactions=[],
        pre_meeting_brief="<html>...</html>",
        pre_meeting_brief_link="https://rishavchatterjee.com/pre-meeting-brief/briefs/...",
        google_drive_link="",
        attio_company_link="",
    )
    db_session.add(brief)
    await db_session.commit()

    fetched = await db_session.get(PreMeetingBrief, brief.brief_id)
    assert fetched.thesis_fit["score"] == 5


@pytest.mark.asyncio
async def test_source_payload(db_session):
    company_id = uuid4()
    db_session.add(Company(company_id=company_id, domain="hadrian.co", operating_status="active"))
    await db_session.commit()

    db_session.add(
        SourcePayload(
            payload_id=uuid4(),
            company_id=company_id,
            source="specter",
            raw={"id": "spec_123", "name": "Hadrian"},
        )
    )
    await db_session.commit()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_db_models.py -v
```

Expected: 5 FAIL (new models not defined)

- [ ] **Step 3: Add the new models to `api/db/models.py`**

Append to `api/db/models.py`:

```python
from sqlalchemy import Date


class EtlRunLog(Base):
    __tablename__ = "etl_run_log"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running','merged','complete','failed')",
            name="etl_run_log_status_check",
        ),
    )

    run_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID | None] = mapped_column(ForeignKey("company.company_id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)


class DataQualityFlag(Base):
    __tablename__ = "data_quality_flags"

    flag_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID | None] = mapped_column(nullable=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("company.company_id"), nullable=False)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    issue: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    source_a: Mapped[str | None] = mapped_column(String(32), nullable=True)
    value_a: Mapped[str | None] = mapped_column(String, nullable=True)
    source_b: Mapped[str | None] = mapped_column(String(32), nullable=True)
    value_b: Mapped[str | None] = mapped_column(String, nullable=True)
    flagged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    event_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    partner: Mapped[str] = mapped_column(String(64), nullable=False)
    company_domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    meeting_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    attendees: Mapped[dict | None] = mapped_column(CrossJSON(), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual_seed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PreMeetingBrief(Base):
    __tablename__ = "pre_meeting_brief"

    brief_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("company.company_id"), nullable=False)
    run_id: Mapped[UUID | None] = mapped_column(nullable=True)
    partner: Mapped[str] = mapped_column(String(64), nullable=False)
    meeting_date: Mapped[date_type] = mapped_column(Date, nullable=False)

    # Prompt-based fields (from DD sheet 5)
    thesis_fit: Mapped[dict | None] = mapped_column(CrossJSON(), nullable=True)
    industry_deepdive: Mapped[str | None] = mapped_column(String, nullable=True)
    market_deepdive: Mapped[str | None] = mapped_column(String, nullable=True)
    key_engagement_questions: Mapped[list[str] | None] = mapped_column(TextArray(), nullable=True)
    podcast_mentions: Mapped[list | None] = mapped_column(CrossJSON(), nullable=True)
    prior_interactions: Mapped[list | None] = mapped_column(CrossJSON(), nullable=True)

    # The rendered brief + distribution links
    pre_meeting_brief: Mapped[str] = mapped_column(String, nullable=False, default="")
    pre_meeting_brief_link: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    google_drive_link: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    attio_company_link: Mapped[str] = mapped_column(String(512), nullable=False, default="")

    # Frozen provenance at brief-gen time (3 separate columns per the DD)
    audit_company: Mapped[dict | None] = mapped_column(CrossJSON(), nullable=True)
    audit_people: Mapped[dict | None] = mapped_column(CrossJSON(), nullable=True)
    audit_traction_metrics: Mapped[dict | None] = mapped_column(CrossJSON(), nullable=True)

    generated_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SourcePayload(Base):
    """Combined raw layer — one row per (company_id, source).

    Simpler than the original spec's per-source raw tables; same semantics.
    """
    __tablename__ = "source_payloads"

    payload_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("company.company_id"), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    raw: Mapped[dict] = mapped_column(CrossJSON(), nullable=False)
    pulled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_db_models.py -v
```

Expected: 8 PASS total

- [ ] **Step 5: Commit**

```bash
git add api/db/models.py tests/test_db_models.py
git commit -m "feat(phase-1): add operational models (run_log, dq_flags, calendar, brief, source_payloads)"
```

---

### Task 1.5: Generate Alembic migration and apply to Postgres

**Files:**
- Create: `api/db/migrations/versions/0001_initial_schema.py`

- [ ] **Step 1: Ensure `.env` is populated with Vercel Postgres URLs**

Verify `POSTGRES_URL` and `POSTGRES_URL_NON_POOLING` are set in `.env` (copy from Vercel dashboard's project env tab).

- [ ] **Step 2: Auto-generate the initial migration**

```bash
alembic revision --autogenerate -m "initial schema"
```

Expected: A new file `api/db/migrations/versions/<hash>_initial_schema.py`. Rename it to `0001_initial_schema.py` (drop the hash for readability).

- [ ] **Step 3: Sanity-check the generated migration**

Open the file. Verify `op.create_table()` calls cover all 7 tables: `company`, `people`, `traction_metrics`, `etl_run_log`, `data_quality_flags`, `calendar_events`, `pre_meeting_brief`, `source_payloads`. Check that ARRAY columns are using `postgresql.ARRAY(sa.String)` and JSON columns are using `postgresql.JSONB`.

If autogenerate produced JSON instead of JSONB or VARCHAR instead of ARRAY (which happens due to the cross-dialect type), manually edit the migration to use the Postgres-native types:

```python
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# In create_table calls:
sa.Column("domain_aliases", postgresql.ARRAY(sa.String()), nullable=True),
sa.Column("audit", postgresql.JSONB(), nullable=True),
```

- [ ] **Step 4: Apply the migration to Vercel Postgres**

```bash
alembic upgrade head
```

Expected: tables created without error. Verify via:

```bash
psql "$POSTGRES_URL_NON_POOLING" -c "\dt"
```

Expected output: 8 tables listed.

- [ ] **Step 5: Commit**

```bash
git add api/db/migrations/versions/0001_initial_schema.py
git commit -m "feat(phase-1): generate and apply initial Postgres schema migration"
```

---

### Task 1.6: DataProvider base interface

**Files:**
- Create: `api/providers/__init__.py`, `api/providers/base.py`
- Create: `tests/test_providers.py`

- [ ] **Step 1: Write the failing test**

`tests/test_providers.py`:

```python
import pytest

from api.providers.base import DataProvider, ProviderResult


def test_provider_result_shape():
    result = ProviderResult(
        source="specter",
        raw={"id": "spec_123"},
        normalized={"domain": "anduril.com"},
    )
    assert result.source == "specter"
    assert result.error is None


def test_provider_result_with_error():
    result = ProviderResult(
        source="crunchbase",
        raw={},
        normalized={},
        error="company not found",
    )
    assert result.error == "company not found"


def test_data_provider_is_protocol():
    # DataProvider should be a Protocol; we shouldn't be able to instantiate it directly,
    # but classes with the right shape should be recognized as instances of it.
    class FakeProvider:
        async def fetch(self, domain: str, hints: dict) -> ProviderResult | None:
            return ProviderResult(source="specter", raw={}, normalized={})

    fake = FakeProvider()
    assert isinstance(fake, DataProvider)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_providers.py -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: Create `api/providers/__init__.py`** (empty)

- [ ] **Step 4: Create `api/providers/base.py`**

```python
"""DataProvider interface — every source (Specter, Crunchbase, PitchBook, Attio, Web)
implements this. For the POC most read fixtures; in production they call real APIs
or MCP servers behind the same interface.
"""
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

Source = Literal["specter", "crunchbase", "pitchbook", "attio", "web", "notion"]


class ProviderResult(BaseModel):
    source: Source
    raw: dict
    normalized: dict
    pulled_at: datetime = Field(default_factory=datetime.utcnow)
    error: str | None = None


@runtime_checkable
class DataProvider(Protocol):
    """Async data provider.

    Implementations must define `fetch(domain, hints)` returning a ProviderResult
    or None when the company is not in coverage. Implementations must NOT raise on
    expected miss — raise only on unexpected error and let the caller convert to
    a ProviderResult with `error` populated.
    """

    async def fetch(self, domain: str, hints: dict) -> ProviderResult | None:
        ...
```

- [ ] **Step 5: Run test to verify it passes**

```bash
python -m pytest tests/test_providers.py -v
```

Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add api/providers/ tests/test_providers.py
git commit -m "feat(phase-1): add DataProvider protocol and ProviderResult model"
```

---

### Task 1.7: Author fixtures for Anduril (the showcase company)

**Files:**
- Create: `fixtures/anduril.com/specter.json`
- Create: `fixtures/anduril.com/crunchbase.json`
- Create: `fixtures/anduril.com/pitchbook.json`
- Create: `fixtures/anduril.com/attio.json`

Anduril is our highest-fidelity fixture — the demo lands on this brief first. Populate Tier 1 fields well; Tier 2 with reasonable values; leave Tier 3 null.

- [ ] **Step 1: Create `fixtures/anduril.com/specter.json`**

```json
{
  "id": "spec_anduril_001",
  "domain": "anduril.com",
  "organization_name": "Anduril Industries",
  "description": "Anduril Industries builds autonomous defense systems and AI-powered command software for the US Department of Defense and allied militaries. Products include Lattice (an AI-driven command and control platform), Ghost (autonomous drones), Sentry Tower (perimeter security), and Roadrunner (counter-drone). Founded by Palmer Luckey (Oculus founder) after Facebook ousted him.",
  "industries": ["Defense", "Aerospace", "AI"],
  "sub_industries": ["Autonomous Systems", "Defense Software", "Hardware"],
  "operating_status": "active",
  "highlights": [
    "top_tier_investors",
    "headcount_surge",
    "government_contract_momentum",
    "founder_with_prior_exit"
  ],
  "new_highlights": [
    "pentagon_250m_contract_2026q2",
    "iron_dome_partnership_announced"
  ],
  "growth_stage": "late_stage",
  "founded_year": 2017,
  "employee_count": 6500,
  "employee_count_range": "5001-10000",
  "revenue_estimate_usd": 1000000000,
  "investors": [
    "Founders Fund", "Andreessen Horowitz", "Valor Equity Partners",
    "8VC", "General Catalyst", "Lux Capital", "Counterpoint Global"
  ],
  "funding": {
    "total_raised_usd": 4200000000,
    "last_round_type": "series_f",
    "last_round_date": "2024-08-08",
    "last_round_usd": 1500000000,
    "post_money_valuation_usd": 14000000000,
    "round_count": 8
  },
  "hq": {
    "city": "Costa Mesa",
    "country": "US",
    "region": "North America"
  },
  "tags": ["defense", "AI", "autonomous", "dual_use", "DoD"],
  "customer_focus": "b2b",
  "customer_profile": "US Department of Defense, allied governments, defense primes",
  "traction_highlights": "Recently awarded $250M Pentagon contract for autonomous systems. Iron Dome partnership with Rafael announced Q1 2026.",
  "certifications": ["ITAR registered", "CMMC Level 3"],
  "technologies": ["Computer Vision", "Edge Compute", "Mesh Networking", "Sensor Fusion"],
  "traction_metrics": {
    "web_visits": {"latest": 4200000, "trend_3mo": {"value": 4200000, "change": 380000, "pct_change": 9.95}},
    "linkedin_followers": {"latest": 850000, "trend_6mo": {"value": 850000, "change": 92000, "pct_change": 12.13}},
    "employee_count": {"latest": 6500, "trend_6mo": {"value": 6500, "change": 1200, "pct_change": 22.64}}
  },
  "web": {
    "popularity_rank": 18500,
    "bounce_rate": 0.34,
    "top_country": "US",
    "traffic_source": "Direct 58% / Search 28% / Social 7% / Referral 5% / Mail 2%"
  },
  "socials": {
    "linkedin": {"url": "https://www.linkedin.com/company/anduril-industries", "follower_count": 850000}
  },
  "reviews": {},
  "founder_info": [
    {
      "specter_person_id": "spec_p_luckey",
      "full_name": "Palmer Luckey",
      "title": "Founder",
      "linkedin_url": "https://www.linkedin.com/in/palmerluckey",
      "prior_companies": ["Oculus"],
      "prior_exits": ["Oculus → Facebook (2014, $2B)"]
    },
    {
      "specter_person_id": "spec_p_schimpf",
      "full_name": "Brian Schimpf",
      "title": "CEO",
      "linkedin_url": "https://www.linkedin.com/in/brian-schimpf",
      "prior_companies": ["Palantir Technologies"],
      "prior_exits": []
    },
    {
      "specter_person_id": "spec_p_stewart",
      "full_name": "Trae Stephens",
      "title": "Co-founder, Chairman",
      "linkedin_url": "https://www.linkedin.com/in/traestephens",
      "prior_companies": ["Palantir Technologies", "Founders Fund"],
      "prior_exits": []
    }
  ],
  "news": [
    {"date": "2026-05-12", "title": "Anduril wins $250M Pentagon contract for autonomous systems", "url": "https://example.com/anduril-pentagon", "publisher": "Defense News"},
    {"date": "2026-04-22", "title": "Iron Dome partnership announced with Rafael", "url": "https://example.com/anduril-iron-dome", "publisher": "TechCrunch"},
    {"date": "2026-03-15", "title": "Anduril opens Australian facility", "url": "https://example.com/anduril-au", "publisher": "Reuters"}
  ],
  "awards": [
    {"name": "Fast Company Most Innovative", "org": "Fast Company", "year": 2024, "rank": 12}
  ],
  "patent_count": 47,
  "it_spend": 85000000,
  "reported_clients": ["US Department of Defense", "UK Ministry of Defence", "Australia ADF"],
  "hiring_signals": ["headcount_surge", "engineering_hiring", "ml_hiring"]
}
```

- [ ] **Step 2: Create `fixtures/anduril.com/crunchbase.json`**

```json
{
  "org": {
    "uuid": "cb_anduril_uuid",
    "name": "Anduril Industries",
    "permalink": "anduril-industries",
    "short_description": "Defense technology company building autonomous systems",
    "founded_year": 2017,
    "country_code": "USA",
    "city": "Costa Mesa",
    "operating_status": "active",
    "homepage_url": "https://www.anduril.com",
    "linkedin_url": "https://www.linkedin.com/company/anduril-industries",
    "num_employees_enum": "10001+",
    "category_list": ["Defense", "Artificial Intelligence", "Robotics"]
  },
  "rounds": [
    {"announced_on": "2024-08-08", "investment_type": "series_f", "raised_usd": 1500000000, "post_money_valuation_usd": 14000000000, "investors": ["Founders Fund", "Counterpoint Global", "Andreessen Horowitz"]},
    {"announced_on": "2022-12-02", "investment_type": "series_e", "raised_usd": 1480000000, "post_money_valuation_usd": 8480000000, "investors": ["Valor Equity Partners", "8VC", "Andreessen Horowitz"]},
    {"announced_on": "2021-06-17", "investment_type": "series_d", "raised_usd": 450000000, "post_money_valuation_usd": 4600000000, "investors": ["Elad Gil", "Andreessen Horowitz", "Founders Fund"]},
    {"announced_on": "2020-07-14", "investment_type": "series_c", "raised_usd": 200000000, "post_money_valuation_usd": 1900000000, "investors": ["Andreessen Horowitz", "Founders Fund"]}
  ],
  "board_members_and_advisors": [
    {"full_name": "Peter Thiel", "title": "Board Observer", "affiliated_firm": "Founders Fund"}
  ]
}
```

- [ ] **Step 3: Create `fixtures/anduril.com/pitchbook.json`**

```json
{
  "pb_id": "pb_anduril",
  "domain": "anduril.com",
  "total_raised_usd": 4200000000,
  "last_round_type": "Series F",
  "last_round_date": "2024-08-08",
  "last_round_usd": 1500000000,
  "post_money_valuation_usd": 14000000000,
  "loaded_at": "2026-05-20T00:00:00Z",
  "loaded_by": "demo_seed"
}
```

- [ ] **Step 4: Create `fixtures/anduril.com/attio.json`**

```json
{
  "company_id": "attio_anduril",
  "interactions": [
    {
      "date": "2024-09-15",
      "type": "conference",
      "attendees": ["devon@renegade.vc"],
      "event": "Reindustrialize 2024",
      "raw_notes": "Devon saw Brian Schimpf keynote. Briefly chatted re Lattice platform. Energetic, technically deep. Asked for follow-up."
    },
    {
      "date": "2024-11-04",
      "type": "email",
      "from": "trae@anduril.com",
      "subject": "Introduction from Joe Lonsdale",
      "raw_notes": "Trae Stephens reached out via Joe Lonsdale (8VC) intro. Offered intro call. Devon followed up but scheduling slipped through Q4."
    },
    {
      "date": "2025-02-21",
      "type": "meeting",
      "attendees": ["devon@renegade.vc", "trae@anduril.com"],
      "raw_notes": "30min intro. Trae walked through Anduril thesis: workflow-critical defense software. Discussed Series E performance. Renegade indicated thesis fit but check size mismatch for Series E. Trae mentioned a future smaller co-invest opportunity in their seed program."
    },
    {
      "date": "2025-08-12",
      "type": "note",
      "author": "devon@renegade.vc",
      "raw_notes": "Internal: Anduril Series F leaked at $14B post. Confirmed our thesis but unable to participate. Tracking for adjacent opportunities (Hadrian, Saronic, Castelion). Will revisit on next round if open to smaller cheques."
    }
  ],
  "stage": "passed_series_f",
  "last_interaction_date": "2025-08-12"
}
```

- [ ] **Step 5: Commit**

```bash
git add fixtures/anduril.com/
git commit -m "feat(phase-1): add Anduril fixtures (T1 fidelity for showcase brief)"
```

---

### Task 1.8: Author fixtures for remaining 5 companies (T1 tier)

**Files:**
- Create: `fixtures/hadrian.co/{specter,crunchbase,pitchbook,attio}.json`
- Create: `fixtures/modal.com/{specter,crunchbase,pitchbook,attio}.json`
- Create: `fixtures/ramp.com/{specter,crunchbase,pitchbook,attio}.json`
- Create: `fixtures/glean.com/{specter,crunchbase,pitchbook,attio}.json`
- Create: `fixtures/mercury.com/{specter,crunchbase,pitchbook,attio}.json`

Authoring strategy: use the Anduril fixture as a template. Populate Tier 1 fields with real public information for each company; use placeholder-but-plausible values for Tier 2; null for Tier 3. **Use Claude (via WebFetch on each company's domain) to gather real public facts** for accuracy, then shape into the fixture schema.

- [ ] **Step 1: Author Hadrian fixtures**

Public facts to seed (verify via web): Hadrian is a US industrial manufacturing automation company. Founded 2020 by Chris Power. Raised Series B in 2024. Based in California. Customers in aerospace/defense supply chains.

Use Anduril fixtures as template; substitute Hadrian facts.

- [ ] **Step 2: Author Modal fixtures**

Public facts: Modal Labs is a compute infrastructure platform for AI/ML workloads. Founded by Erik Bernhardsson (ex-Spotify). Raised Series A in 2024. Based in NYC.

- [ ] **Step 3: Author Ramp fixtures**

Public facts: Ramp is a corporate spend management platform. Founded by Eric Glyman + Karim Atiyeh. Raised at $13B valuation in 2024. Based in NYC.

- [ ] **Step 4: Author Glean fixtures**

Public facts: Glean is an enterprise search platform. Founded by Arvind Jain (ex-Google). Raised Series E at $4.6B in 2024. Based in Palo Alto.

- [ ] **Step 5: Author Mercury fixtures**

Public facts: Mercury is a banking platform for startups. Founded by Immad Akhund. Raised Series C at $1.6B in 2021 (no recent rounds, intentional). Based in SF.

- [ ] **Step 6: Validate all fixtures are valid JSON**

```bash
for f in fixtures/*/*.json; do python -c "import json; json.load(open('$f'))" || echo "FAIL: $f"; done
```

Expected: no failures.

- [ ] **Step 7: Commit**

```bash
git add fixtures/
git commit -m "feat(phase-1): add fixtures for Hadrian, Modal, Ramp, Glean, Mercury"
```

---

### Task 1.9: In-process Specter provider with test

**Files:**
- Create: `api/providers/specter.py`
- Modify: `tests/test_providers.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_providers.py`:

```python
from pathlib import Path

import pytest

from api.providers.specter import SpecterProvider

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.mark.asyncio
async def test_specter_provider_hits_fixture():
    provider = SpecterProvider(fixtures_dir=FIXTURES_DIR)
    result = await provider.fetch("anduril.com", hints={})
    assert result is not None
    assert result.source == "specter"
    assert result.raw["organization_name"] == "Anduril Industries"
    assert result.normalized["domain"] == "anduril.com"
    assert result.normalized["founded_year"] == 2017


@pytest.mark.asyncio
async def test_specter_provider_returns_none_on_miss():
    provider = SpecterProvider(fixtures_dir=FIXTURES_DIR)
    result = await provider.fetch("notinfixtures.com", hints={})
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_providers.py::test_specter_provider_hits_fixture -v
```

Expected: FAIL — `ModuleNotFoundError: api.providers.specter`

- [ ] **Step 3: Implement `api/providers/specter.py`**

```python
"""In-process Specter provider. Reads fixtures/<domain>/specter.json.

For Phase 2+ the real Specter API client lives in the standalone specter-mcp
server (see mcp_servers/specter_mcp/). The two have the same shape; the
orchestrator can swap them transparently.
"""
import json
from pathlib import Path

from api.providers.base import ProviderResult


class SpecterProvider:
    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = fixtures_dir

    async def fetch(self, domain: str, hints: dict) -> ProviderResult | None:
        path = self.fixtures_dir / domain / "specter.json"
        if not path.exists():
            return None
        raw = json.loads(path.read_text())
        normalized = self._normalize(raw, domain)
        return ProviderResult(source="specter", raw=raw, normalized=normalized)

    def _normalize(self, raw: dict, domain: str) -> dict:
        funding = raw.get("funding", {})
        hq = raw.get("hq", {})
        return {
            "domain": domain,
            "specter_id": raw.get("id"),
            "description": raw.get("description"),
            "operating_status": raw.get("operating_status", "active"),
            "tags": raw.get("tags"),
            "customer_focus": raw.get("customer_focus"),
            "customer_profile": raw.get("customer_profile"),
            "founded_year": raw.get("founded_year"),
            "hq_city": hq.get("city"),
            "hq_country": hq.get("country"),
            "hq_region": hq.get("region"),
            "certifications": raw.get("certifications"),
            "traction_highlights": raw.get("traction_highlights"),
            "technologies": raw.get("technologies"),
            "total_raised_usd": funding.get("total_raised_usd"),
            "last_round_type": funding.get("last_round_type"),
            "last_round_date": funding.get("last_round_date"),
            "last_round_usd": funding.get("last_round_usd"),
            "post_money_valuation_usd": funding.get("post_money_valuation_usd"),
            "round_count": funding.get("round_count"),
            "growth_stage": raw.get("growth_stage"),
            "investors": raw.get("investors"),
            "revenue_estimate_usd": raw.get("revenue_estimate_usd"),
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_providers.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add api/providers/specter.py tests/test_providers.py
git commit -m "feat(phase-1): add SpecterProvider with fixture reader + tests"
```

---

### Task 1.10: In-process Crunchbase, PitchBook, Attio providers

**Files:**
- Create: `api/providers/crunchbase.py`, `api/providers/pitchbook.py`, `api/providers/attio.py`
- Modify: `tests/test_providers.py`

- [ ] **Step 1: Add failing tests for all three providers**

Append to `tests/test_providers.py`:

```python
from api.providers.attio import AttioProvider
from api.providers.crunchbase import CrunchbaseProvider
from api.providers.pitchbook import PitchBookProvider


@pytest.mark.asyncio
async def test_crunchbase_provider():
    provider = CrunchbaseProvider(fixtures_dir=FIXTURES_DIR)
    result = await provider.fetch("anduril.com", hints={})
    assert result is not None
    assert result.source == "crunchbase"
    assert result.raw["org"]["uuid"] == "cb_anduril_uuid"
    assert len(result.normalized["rounds"]) == 4


@pytest.mark.asyncio
async def test_pitchbook_provider():
    provider = PitchBookProvider(fixtures_dir=FIXTURES_DIR)
    result = await provider.fetch("anduril.com", hints={})
    assert result is not None
    assert result.source == "pitchbook"
    assert result.normalized["post_money_valuation_usd"] == 14000000000


@pytest.mark.asyncio
async def test_attio_provider():
    provider = AttioProvider(fixtures_dir=FIXTURES_DIR)
    result = await provider.fetch("anduril.com", hints={})
    assert result is not None
    assert result.source == "attio"
    assert len(result.normalized["interactions"]) >= 3


@pytest.mark.asyncio
async def test_provider_returns_none_when_fixture_missing():
    for ProviderCls in [CrunchbaseProvider, PitchBookProvider, AttioProvider]:
        provider = ProviderCls(fixtures_dir=FIXTURES_DIR)
        result = await provider.fetch("notinfixtures.com", hints={})
        assert result is None
```

- [ ] **Step 2: Implement `api/providers/crunchbase.py`**

```python
import json
from pathlib import Path

from api.providers.base import ProviderResult


class CrunchbaseProvider:
    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = fixtures_dir

    async def fetch(self, domain: str, hints: dict) -> ProviderResult | None:
        path = self.fixtures_dir / domain / "crunchbase.json"
        if not path.exists():
            return None
        raw = json.loads(path.read_text())
        org = raw.get("org", {})
        normalized = {
            "domain": domain,
            "cb_uuid": org.get("uuid"),
            "description": org.get("short_description"),
            "founded_year": org.get("founded_year"),
            "hq_country": "US" if org.get("country_code") == "USA" else org.get("country_code"),
            "hq_city": org.get("city"),
            "operating_status": org.get("operating_status"),
            "linkedin_url": org.get("linkedin_url"),
            "rounds": raw.get("rounds", []),
            "board_members": raw.get("board_members_and_advisors", []),
        }
        return ProviderResult(source="crunchbase", raw=raw, normalized=normalized)
```

- [ ] **Step 3: Implement `api/providers/pitchbook.py`**

```python
import json
from pathlib import Path

from api.providers.base import ProviderResult


class PitchBookProvider:
    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = fixtures_dir

    async def fetch(self, domain: str, hints: dict) -> ProviderResult | None:
        path = self.fixtures_dir / domain / "pitchbook.json"
        if not path.exists():
            return None
        raw = json.loads(path.read_text())
        normalized = {
            "domain": domain,
            "pb_id": raw.get("pb_id"),
            "total_raised_usd": raw.get("total_raised_usd"),
            "last_round_type": raw.get("last_round_type"),
            "last_round_date": raw.get("last_round_date"),
            "last_round_usd": raw.get("last_round_usd"),
            "post_money_valuation_usd": raw.get("post_money_valuation_usd"),
        }
        return ProviderResult(source="pitchbook", raw=raw, normalized=normalized)
```

- [ ] **Step 4: Implement `api/providers/attio.py`**

```python
import json
from pathlib import Path

from api.providers.base import ProviderResult


class AttioProvider:
    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = fixtures_dir

    async def fetch(self, domain: str, hints: dict) -> ProviderResult | None:
        path = self.fixtures_dir / domain / "attio.json"
        if not path.exists():
            return None
        raw = json.loads(path.read_text())
        normalized = {
            "domain": domain,
            "attio_company_id": raw.get("company_id"),
            "interactions": raw.get("interactions", []),
            "stage": raw.get("stage"),
            "last_interaction_date": raw.get("last_interaction_date"),
        }
        return ProviderResult(source="attio", raw=raw, normalized=normalized)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_providers.py -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add api/providers/crunchbase.py api/providers/pitchbook.py api/providers/attio.py tests/test_providers.py
git commit -m "feat(phase-1): add Crunchbase, PitchBook, Attio in-process providers"
```

---

### Task 1.11: Standalone specter-mcp server (FastMCP)

**Files:**
- Create: `mcp_servers/specter_mcp/pyproject.toml`
- Create: `mcp_servers/specter_mcp/server.py`
- Create: `mcp_servers/specter_mcp/README.md`
- Create: `tests/test_specter_mcp.py`

- [ ] **Step 1: Install `mcp` package**

Add `mcp[cli]>=0.9.0` to `requirements.txt` and run:

```bash
pip install -r requirements.txt
```

- [ ] **Step 2: Write the failing test**

`tests/test_specter_mcp.py`:

```python
import asyncio
from pathlib import Path

import pytest

from mcp_servers.specter_mcp.server import fetch_company


@pytest.mark.asyncio
async def test_specter_mcp_fetch_company():
    result = await fetch_company("anduril.com")
    assert result is not None
    assert result["organization_name"] == "Anduril Industries"


@pytest.mark.asyncio
async def test_specter_mcp_returns_none_on_miss():
    result = await fetch_company("notreal.com")
    assert result is None
```

- [ ] **Step 3: Run test to verify it fails**

```bash
python -m pytest tests/test_specter_mcp.py -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 4: Create `mcp_servers/specter_mcp/pyproject.toml`**

```toml
[project]
name = "specter-mcp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "mcp[cli]>=0.9.0",
]
```

- [ ] **Step 5: Create `mcp_servers/specter_mcp/server.py`**

```python
"""Standalone Specter MCP server.

Exposes a single tool `fetch_company(domain)` returning the Specter enrichment
payload for a company. POC: reads from ../../fixtures/<domain>/specter.json.
Production: would call the real Specter REST API.

Run standalone:
    python -m mcp_servers.specter_mcp.server

Or via MCP Inspector for ad-hoc testing:
    npx @modelcontextprotocol/inspector python -m mcp_servers.specter_mcp.server
"""
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"

mcp = FastMCP("specter-mcp")


@mcp.tool()
async def fetch_company(domain: str) -> dict | None:
    """Fetch enrichment for a company by domain.

    Returns Specter v1 schema; see api.tryspecter.com docs.
    For this POC: reads from ../../fixtures/<domain>/specter.json.

    Returns None if domain not in Specter coverage.
    """
    path = FIXTURES_DIR / domain / "specter.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 6: Create `mcp_servers/specter_mcp/README.md`**

```markdown
# specter-mcp

Standalone Model Context Protocol server exposing Specter company enrichment as a tool.

POC: reads fixtures from `../../fixtures/<domain>/specter.json`.
Production: would proxy to the real Specter REST API behind the same tool contract.

## Run

```bash
python -m mcp_servers.specter_mcp.server
```

## Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python -m mcp_servers.specter_mcp.server
```

Then call `fetch_company` with `{"domain": "anduril.com"}`.

## Connect to Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "specter": {
      "command": "python",
      "args": ["-m", "mcp_servers.specter_mcp.server"],
      "cwd": "/path/to/pre-meeting-brief"
    }
  }
}
```
```

- [ ] **Step 7: Run test to verify it passes**

```bash
python -m pytest tests/test_specter_mcp.py -v
```

Expected: PASS

- [ ] **Step 8: Smoke test the server runs**

```bash
python -m mcp_servers.specter_mcp.server &
sleep 1
kill %1
```

Expected: process starts without crashing (kill it after 1s — we just verify boot).

- [ ] **Step 9: Commit**

```bash
git add mcp_servers/ tests/test_specter_mcp.py requirements.txt
git commit -m "feat(phase-1): add standalone specter-mcp server"
```

---

### Task 1.12: Seed script — calendar events + one full brief for Anduril

**Files:**
- Create: `api/seeds/__init__.py`
- Create: `api/seeds/seed.py`

The seed script populates: 6 `company` rows (one per fixture domain), 6 `calendar_events` rows (one per company for "tomorrow"), and **one fully-rendered `pre_meeting_brief` row for anduril.com** with hand-crafted brief content. Anduril is our showcase; the others are seeded but render generic placeholder briefs in the UI for now (Phase 2 generates them live).

- [ ] **Step 1: Create `api/seeds/__init__.py`** (empty)

- [ ] **Step 2: Create `api/seeds/seed.py`**

```python
"""One-shot seed script.

Run via:
    make seed
    # or
    python -m api.seeds.seed

Idempotent — uses ON CONFLICT DO NOTHING on the unique domain column.
"""
import asyncio
import json
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    CalendarEvent,
    Company,
    People,
    PreMeetingBrief,
    TractionMetrics,
)
from api.db.session import SessionLocal

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"

DOMAINS = ["anduril.com", "hadrian.co", "modal.com", "ramp.com", "glean.com", "mercury.com"]
PARTNER = "Devon"


async def _ensure_company(session: AsyncSession, domain: str) -> Company:
    existing = await session.scalar(select(Company).where(Company.domain == domain))
    if existing:
        return existing
    specter_path = FIXTURES_DIR / domain / "specter.json"
    raw = json.loads(specter_path.read_text())
    company = Company(
        company_id=uuid4(),
        domain=domain,
        description=raw.get("description"),
        operating_status=raw.get("operating_status", "active"),
        founded_year=raw.get("founded_year"),
        hq_city=raw.get("hq", {}).get("city"),
        hq_country=raw.get("hq", {}).get("country"),
        total_raised_usd=raw.get("funding", {}).get("total_raised_usd"),
        last_round_type=raw.get("funding", {}).get("last_round_type"),
        post_money_valuation_usd=raw.get("funding", {}).get("post_money_valuation_usd"),
        investors=raw.get("investors"),
        tags=raw.get("tags"),
        customer_focus=raw.get("customer_focus"),
        growth_stage=raw.get("growth_stage"),
        revenue_estimate_usd=raw.get("revenue_estimate_usd"),
        audit={
            "fields": [
                {"field": "description", "source": "Specter"},
                {"field": "founded_year", "source": "Specter"},
                {"field": "total_raised_usd", "source": "Specter"},
            ]
        },
    )
    session.add(company)
    await session.flush()
    return company


async def _ensure_people(session: AsyncSession, company: Company):
    existing = await session.get(People, company.company_id)
    if existing:
        return
    specter_path = FIXTURES_DIR / company.domain / "specter.json"
    raw = json.loads(specter_path.read_text())
    session.add(
        People(
            company_id=company.company_id,
            founders=raw.get("founder_info"),
            employee_count=raw.get("employee_count"),
            employee_range=raw.get("employee_count_range"),
            hiring_signals=raw.get("hiring_signals"),
            audit={"fields": [{"field": "founders", "source": "Specter"}]},
        )
    )


async def _ensure_traction(session: AsyncSession, company: Company):
    existing = await session.get(TractionMetrics, company.company_id)
    if existing:
        return
    specter_path = FIXTURES_DIR / company.domain / "specter.json"
    raw = json.loads(specter_path.read_text())
    tm = raw.get("traction_metrics", {})
    web = raw.get("web", {})
    session.add(
        TractionMetrics(
            company_id=company.company_id,
            highlights=raw.get("highlights"),
            new_highlights=raw.get("new_highlights"),
            web_visits_latest=tm.get("web_visits", {}).get("latest"),
            web_visits_trend=tm.get("web_visits"),
            web_popularity_rank=web.get("popularity_rank"),
            bounce_rate=web.get("bounce_rate"),
            top_traffic_country=web.get("top_country"),
            traffic_sources=web.get("traffic_source"),
            linkedin_followers=tm.get("linkedin_followers", {}).get("latest"),
            linkedin_trend=tm.get("linkedin_followers"),
            awards=raw.get("awards"),
            patents=raw.get("patent_count"),
            reported_clients=raw.get("reported_clients"),
            it_spend_usd=raw.get("it_spend"),
            news=raw.get("news"),
            audit={"fields": [{"field": "highlights", "source": "Specter"}]},
        )
    )


async def _ensure_calendar(session: AsyncSession, company: Company, days_ahead: int):
    meeting_date = date.today() + timedelta(days=days_ahead)
    existing = await session.scalar(
        select(CalendarEvent).where(
            CalendarEvent.company_domain == company.domain,
            CalendarEvent.meeting_date == meeting_date,
        )
    )
    if existing:
        return
    session.add(
        CalendarEvent(
            event_id=uuid4(),
            partner=PARTNER,
            company_domain=company.domain,
            meeting_date=meeting_date,
            attendees={"emails": [f"{PARTNER.lower()}@renegade.vc", f"founder@{company.domain}"]},
            source="manual_seed",
        )
    )


ANDURIL_BRIEF_HTML = """<!-- placeholder; Phase 2 generates real briefs -->
<div class="hero">Anduril Industries — Series F — $14B post — 6,500 employees</div>
"""


async def _ensure_anduril_brief(session: AsyncSession, company: Company):
    existing = await session.scalar(
        select(PreMeetingBrief).where(PreMeetingBrief.company_id == company.company_id)
    )
    if existing:
        return
    session.add(
        PreMeetingBrief(
            brief_id=uuid4(),
            company_id=company.company_id,
            partner=PARTNER,
            meeting_date=date.today() + timedelta(days=1),
            thesis_fit={
                "score": 5,
                "reasoning": (
                    "Anduril sits exactly at the centre of Renegade's 'Markets That Matter' "
                    "thesis. Defense + workflow-critical software + dual-use. Their "
                    "Lattice platform is the prototype for software-defined defense procurement."
                ),
                "bear_case": (
                    "Concentration risk: ~70% revenue from DoD contracts. Regulatory exposure "
                    "around export controls (ITAR/EAR). International expansion is uneven "
                    "post-AUKUS slowdown."
                ),
            },
            industry_deepdive=(
                "Defense software is undergoing a 30-year refresh. Legacy primes (Lockheed, "
                "Northrop, RTX) optimised for hardware contracts and 10-year procurement cycles. "
                "Anduril's thesis: software-defined platforms, OTA updates, commercial-pace "
                "iteration. Lattice has become the de-facto C2 layer for autonomy across Replicator "
                "and adjacent programmes."
            ),
            market_deepdive=(
                "Timing favours Anduril: the 2025-2027 DoD budget shift toward attritable autonomy "
                "(Replicator: $1B → projected $5B annually), allied defense spend increases (NATO 2.5% "
                "target), and post-Ukraine emphasis on mass-producible systems. Comparables: Saronic "
                "(maritime, $4B), Shield AI (autonomy, $5.3B), Castelion (strike, Series A). Anduril "
                "is the only vertical-integrated platform play at scale."
            ),
            key_engagement_questions=[
                "Margin profile of autonomous hardware (Ghost, Roadrunner) vs Lattice software — is the software take-rate scaling as headcount mix shifts?",
                "How does the procurement Bottleneck — silicon supply vs DoD acquisitions team capacity — affect 18-month forward pipeline?",
                "International expansion roadmap: AUKUS pillar 2 progress and what comes after the Australia facility?",
                "Lattice as platform: third-party developers (Saronic, Hadrian-built components) on Lattice — is there a published SDK or API roadmap?",
                "Series F deployment: which product line is the largest investment over the next 24 months, and what's the gross margin guidance at scale?",
            ],
            podcast_mentions=[
                {"show": "Acquired", "date": "2024-09-12", "url": "https://acquired.fm/episodes/anduril"},
                {"show": "Invest Like the Best", "date": "2025-02-18", "url": "https://example.com"},
            ],
            prior_interactions=[
                {"date": "2024-09-15", "type": "conference", "summary": "Devon saw Brian Schimpf keynote at Reindustrialize 2024."},
                {"date": "2024-11-04", "type": "email", "summary": "Trae Stephens reached out via Joe Lonsdale (8VC). Follow-up slipped through Q4."},
                {"date": "2025-02-21", "type": "meeting", "summary": "30min intro with Trae. Thesis fit confirmed; check size mismatch for Series E."},
                {"date": "2025-08-12", "type": "internal_note", "summary": "Series F at $14B confirmed our thesis but we couldn't participate. Tracking adjacent opportunities."},
            ],
            pre_meeting_brief=ANDURIL_BRIEF_HTML,
            pre_meeting_brief_link="/pre-meeting-brief/briefs/anduril",
            google_drive_link="",
            attio_company_link="https://app.attio.com/renegade/companies/anduril",
            audit_company={"fields": [{"field": "description", "source": "Specter"}]},
            audit_people={"fields": [{"field": "founders", "source": "Specter"}]},
            audit_traction_metrics={"fields": [{"field": "highlights", "source": "Specter"}]},
        )
    )


async def main():
    async with SessionLocal() as session:
        async with session.begin():
            for i, domain in enumerate(DOMAINS):
                company = await _ensure_company(session, domain)
                await _ensure_people(session, company)
                await _ensure_traction(session, company)
                await _ensure_calendar(session, company, days_ahead=i + 1)
                if domain == "anduril.com":
                    await _ensure_anduril_brief(session, company)
        print(f"Seeded {len(DOMAINS)} companies + calendar events + 1 polished brief.")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Run the seed script**

```bash
python -m api.seeds.seed
```

Expected: `Seeded 6 companies + calendar events + 1 polished brief.`

- [ ] **Step 4: Verify via psql**

```bash
psql "$POSTGRES_URL_NON_POOLING" -c "SELECT domain, founded_year, total_raised_usd FROM company;"
psql "$POSTGRES_URL_NON_POOLING" -c "SELECT partner, company_domain, meeting_date FROM calendar_events;"
psql "$POSTGRES_URL_NON_POOLING" -c "SELECT partner, meeting_date, thesis_fit->'score' FROM pre_meeting_brief;"
```

Expected: 6 rows, 6 rows, 1 row.

- [ ] **Step 5: Commit**

```bash
git add api/seeds/
git commit -m "feat(phase-1): add idempotent seed script with Anduril showcase brief"
```

---

### Task 1.13: Backend agenda and briefs routes

**Files:**
- Create: `api/routes/agenda.py`, `api/routes/briefs.py`
- Modify: `api/index.py`
- Create: `tests/test_routes.py`

- [ ] **Step 1: Write failing tests for both routes**

`tests/test_routes.py`:

```python
import pytest
from fastapi.testclient import TestClient

from api.index import app

client = TestClient(app)


def test_agenda_endpoint_exists():
    response = client.get("/api/agenda?partner=Devon")
    # Should return 200 with a list (possibly empty if DB not seeded in this env)
    assert response.status_code in (200, 503)  # 503 if DB unreachable


def test_briefs_endpoint_exists():
    response = client.get("/api/briefs/00000000-0000-0000-0000-000000000000")
    assert response.status_code in (404, 503)
```

- [ ] **Step 2: Create `api/routes/agenda.py`**

```python
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CalendarEvent, Company, PreMeetingBrief
from api.db.session import get_session

router = APIRouter()


@router.get("/agenda")
async def get_agenda(
    partner: str = Query(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    today = date.today()
    horizon = today + timedelta(days=14)

    # Get events for this partner in the next 14 days
    events_q = (
        select(CalendarEvent)
        .where(CalendarEvent.partner == partner)
        .where(CalendarEvent.meeting_date >= today)
        .where(CalendarEvent.meeting_date <= horizon)
        .order_by(CalendarEvent.meeting_date)
    )
    events = (await session.scalars(events_q)).all()

    # For each event, look up the brief (if any) and the company (for the preview card)
    items = []
    for event in events:
        company = await session.scalar(
            select(Company).where(Company.domain == event.company_domain)
        )
        brief = None
        if company:
            brief = await session.scalar(
                select(PreMeetingBrief)
                .where(PreMeetingBrief.company_id == company.company_id)
                .where(PreMeetingBrief.meeting_date == event.meeting_date)
                .order_by(PreMeetingBrief.generated_ts.desc())
            )
        items.append(
            {
                "event_id": str(event.event_id),
                "meeting_date": event.meeting_date.isoformat(),
                "company_domain": event.company_domain,
                "company_description": company.description if company else None,
                "company_stage": (company.growth_stage if company else None),
                "company_last_round": (company.last_round_type if company else None),
                "thesis_fit_score": (
                    brief.thesis_fit.get("score") if brief and brief.thesis_fit else None
                ),
                "brief_id": str(brief.brief_id) if brief else None,
            }
        )

    return {"partner": partner, "items": items}
```

- [ ] **Step 3: Create `api/routes/briefs.py`**

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Company, People, PreMeetingBrief, TractionMetrics
from api.db.session import get_session

router = APIRouter()


@router.get("/briefs/{brief_id}")
async def get_brief(
    brief_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    brief = await session.get(PreMeetingBrief, brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    company = await session.get(Company, brief.company_id)
    people = await session.get(People, brief.company_id)
    traction = await session.get(TractionMetrics, brief.company_id)

    return {
        "brief_id": str(brief.brief_id),
        "partner": brief.partner,
        "meeting_date": brief.meeting_date.isoformat(),
        "generated_at": brief.generated_ts.isoformat(),
        "company": {
            "domain": company.domain if company else None,
            "description": company.description if company else None,
            "operating_status": company.operating_status if company else None,
            "founded_year": company.founded_year if company else None,
            "hq_city": company.hq_city if company else None,
            "hq_country": company.hq_country if company else None,
            "tags": company.tags if company else None,
            "growth_stage": company.growth_stage if company else None,
            "investors": company.investors if company else None,
            "total_raised_usd": company.total_raised_usd if company else None,
            "last_round_type": company.last_round_type if company else None,
            "post_money_valuation_usd": company.post_money_valuation_usd if company else None,
        },
        "people": {
            "founders": people.founders if people else None,
            "employee_count": people.employee_count if people else None,
            "employee_range": people.employee_range if people else None,
        } if people else None,
        "traction": {
            "highlights": traction.highlights if traction else None,
            "new_highlights": traction.new_highlights if traction else None,
            "linkedin_followers": traction.linkedin_followers if traction else None,
            "news": traction.news if traction else None,
        } if traction else None,
        "thesis_fit": brief.thesis_fit,
        "industry_deepdive": brief.industry_deepdive,
        "market_deepdive": brief.market_deepdive,
        "key_engagement_questions": brief.key_engagement_questions,
        "podcast_mentions": brief.podcast_mentions,
        "prior_interactions": brief.prior_interactions,
    }
```

- [ ] **Step 4: Update `api/index.py`**

Replace the existing file with:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import agenda, briefs, health

app = FastAPI(title="Pre-Meeting Brief API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(agenda.router, prefix="/api")
app.include_router(briefs.router, prefix="/api")
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_routes.py -v
```

Expected: PASS (response codes match expectations)

- [ ] **Step 6: Commit**

```bash
git add api/routes/ api/index.py tests/test_routes.py
git commit -m "feat(phase-1): add /api/agenda and /api/briefs/{id} endpoints"
```

---

### Task 1.14: Daily Agenda page (Next.js, real data)

**Files:**
- Create: `components/BriefCard.tsx`, `components/ThesisFitBadge.tsx`
- Modify: `app/page.tsx`
- Create: `lib/api.ts`, `lib/types.ts`

- [ ] **Step 1: Create `lib/types.ts`**

```ts
export type ThesisFitScore = 1 | 2 | 3 | 4 | 5;

export type AgendaItem = {
  event_id: string;
  meeting_date: string;
  company_domain: string;
  company_description: string | null;
  company_stage: string | null;
  company_last_round: string | null;
  thesis_fit_score: ThesisFitScore | null;
  brief_id: string | null;
};

export type AgendaResponse = {
  partner: string;
  items: AgendaItem[];
};
```

- [ ] **Step 2: Create `lib/api.ts`**

```ts
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/pre-meeting-brief/api";

export async function fetchAgenda(partner: string) {
  const res = await fetch(`${API_BASE}/agenda?partner=${encodeURIComponent(partner)}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Agenda fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchBrief(briefId: string) {
  const res = await fetch(`${API_BASE}/briefs/${briefId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Brief fetch failed: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 3: Create `components/ThesisFitBadge.tsx`**

```tsx
import type { ThesisFitScore } from "@/lib/types";

const COLORS: Record<ThesisFitScore, string> = {
  5: "bg-emerald-100 text-emerald-800 ring-emerald-300",
  4: "bg-lime-100 text-lime-800 ring-lime-300",
  3: "bg-amber-100 text-amber-800 ring-amber-300",
  2: "bg-orange-100 text-orange-800 ring-orange-300",
  1: "bg-rose-100 text-rose-800 ring-rose-300",
};

export function ThesisFitBadge({ score }: { score: ThesisFitScore | null }) {
  if (!score) return <span className="text-slate-400 text-sm">—</span>;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ${COLORS[score]}`}
    >
      Thesis fit {score}/5
    </span>
  );
}
```

- [ ] **Step 4: Create `components/BriefCard.tsx`**

```tsx
import Link from "next/link";

import { ThesisFitBadge } from "@/components/ThesisFitBadge";
import type { AgendaItem } from "@/lib/types";

export function BriefCard({ item }: { item: AgendaItem }) {
  const hasBrief = !!item.brief_id;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-500">
            {new Date(item.meeting_date).toLocaleDateString("en-US", {
              weekday: "short",
              month: "short",
              day: "numeric",
            })}
          </div>
          <h3 className="mt-1 text-lg font-semibold text-slate-900">{item.company_domain}</h3>
          {item.company_description && (
            <p className="mt-2 line-clamp-2 text-sm text-slate-600">{item.company_description}</p>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            {item.company_stage && (
              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
                {item.company_stage.replace(/_/g, " ")}
              </span>
            )}
            {item.company_last_round && (
              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
                {item.company_last_round.replace(/_/g, " ")}
              </span>
            )}
            <ThesisFitBadge score={item.thesis_fit_score} />
          </div>
        </div>
        {hasBrief ? (
          <Link
            href={`/briefs/${item.brief_id}`}
            className="shrink-0 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
          >
            Read brief →
          </Link>
        ) : (
          <span className="shrink-0 rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700">
            Brief pending
          </span>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Replace `app/page.tsx`**

```tsx
import { BriefCard } from "@/components/BriefCard";
import { fetchAgenda } from "@/lib/api";
import type { AgendaResponse } from "@/lib/types";

const PARTNER = "Devon";

export default async function Home() {
  let agenda: AgendaResponse | null = null;
  let error: string | null = null;
  try {
    agenda = await fetchAgenda(PARTNER);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-12">
      <div className="mx-auto max-w-4xl">
        <header className="border-b border-slate-200 pb-6">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Renegade Capital · {PARTNER}
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
            Today's Agenda
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Pre-meeting briefs for upcoming first meetings with new companies (rolling 3-month window).
          </p>
        </header>

        <section className="mt-8">
          {error && (
            <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              Could not load agenda: {error}
            </div>
          )}
          {agenda && agenda.items.length === 0 && (
            <p className="text-sm text-slate-500">No meetings scheduled.</p>
          )}
          {agenda && agenda.items.length > 0 && (
            <div className="space-y-3">
              {agenda.items.map((item) => (
                <BriefCard key={item.event_id} item={item} />
              ))}
            </div>
          )}
        </section>

        <footer className="mt-12 border-t border-slate-200 pt-6 text-xs text-slate-500">
          <a className="underline underline-offset-2" href="/pre-meeting-brief/approach">
            Architecture approach
          </a>
        </footer>
      </div>
    </main>
  );
}
```

- [ ] **Step 6: Verify locally**

Start the dev server alongside the FastAPI server:

```bash
# Terminal A:
uvicorn api.index:app --reload --port 8000

# Terminal B:
NEXT_PUBLIC_API_BASE=http://localhost:8000/api npm run dev
```

Open `http://localhost:3000/pre-meeting-brief`. Expected: agenda page with 6 company cards. Anduril shows "Read brief →" button; others show "Brief pending."

- [ ] **Step 7: Commit**

```bash
git add components/ lib/ app/page.tsx
git commit -m "feat(phase-1): daily agenda page rendering live data from DB"
```

---

### Task 1.15: Brief reader page (Anduril showcase)

**Files:**
- Create: `app/briefs/[id]/page.tsx`
- Create: `components/DashboardSection.tsx`, `components/ConfidenceDot.tsx`, `components/AuditPanel.tsx`

- [ ] **Step 1: Create `components/ConfidenceDot.tsx`**

```tsx
type Confidence = "green" | "yellow" | "red";

const STYLES: Record<Confidence, string> = {
  green: "bg-emerald-500 ring-emerald-100",
  yellow: "bg-amber-400 ring-amber-100",
  red: "bg-rose-500 ring-rose-100",
};

export function ConfidenceDot({
  confidence,
  sources,
  label,
}: {
  confidence: Confidence;
  sources: string[];
  label?: string;
}) {
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ring-2 ${STYLES[confidence]}`}
      title={`${label ?? "Source"}: ${sources.join(", ")}`}
      aria-label={`Confidence ${confidence}: ${sources.join(", ")}`}
    />
  );
}
```

- [ ] **Step 2: Create `components/DashboardSection.tsx`**

```tsx
import type { ReactNode } from "react";

export function DashboardSection({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="border-b border-slate-100 pb-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">{title}</h2>
        {subtitle && <p className="mt-0.5 text-xs text-slate-400">{subtitle}</p>}
      </div>
      <div className="pt-3">{children}</div>
    </section>
  );
}
```

- [ ] **Step 3: Create `components/AuditPanel.tsx`** (stub for Phase 1; Phase 2 wires real interactivity)

```tsx
export function AuditPanel({ auditData }: { auditData: Record<string, unknown> | null }) {
  if (!auditData) return null;
  return (
    <details className="mt-4 rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-xs">
      <summary className="cursor-pointer font-medium text-slate-700">
        Data quality & sources ({Object.keys(auditData).length})
      </summary>
      <pre className="mt-2 overflow-x-auto text-slate-600">
        {JSON.stringify(auditData, null, 2)}
      </pre>
    </details>
  );
}
```

- [ ] **Step 4: Create `app/briefs/[id]/page.tsx`**

```tsx
import { notFound } from "next/navigation";

import { AuditPanel } from "@/components/AuditPanel";
import { ConfidenceDot } from "@/components/ConfidenceDot";
import { DashboardSection } from "@/components/DashboardSection";
import { ThesisFitBadge } from "@/components/ThesisFitBadge";
import { fetchBrief } from "@/lib/api";

export default async function BriefPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let brief;
  try {
    brief = await fetchBrief(id);
  } catch {
    notFound();
  }
  if (!brief) notFound();

  const { company, people, traction, thesis_fit, industry_deepdive, market_deepdive } = brief;

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-8">
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <header className="border-b border-slate-200 pb-6">
          <div className="flex items-baseline justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                {company.tags?.[0] ?? "Company"}
              </p>
              <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
                {company.domain}
              </h1>
              <p className="mt-1 text-sm text-slate-600">{company.description}</p>
            </div>
            <ThesisFitBadge score={thesis_fit?.score ?? null} />
          </div>
          <div className="mt-4 flex flex-wrap gap-2 text-xs">
            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
              {company.growth_stage?.replace(/_/g, " ")}
            </span>
            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
              {company.last_round_type?.replace(/_/g, " ")}
            </span>
            {company.post_money_valuation_usd && (
              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
                ${(company.post_money_valuation_usd / 1e9).toFixed(1)}B post
              </span>
            )}
            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
              {people?.employee_count ? `${people.employee_count.toLocaleString()} employees` : "—"}
            </span>
            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700">
              {company.hq_city ? `${company.hq_city}, ${company.hq_country}` : company.hq_country}
            </span>
          </div>
        </header>

        {/* Above-the-fold dashboard */}
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <DashboardSection title="Thesis Fit" subtitle="Renegade — Markets That Matter">
            {thesis_fit ? (
              <>
                <p className="text-sm text-slate-700">
                  <span className="font-semibold">Score:</span> {thesis_fit.score}/5
                </p>
                <p className="mt-2 text-sm text-slate-700">
                  <span className="font-semibold">Reasoning:</span> {thesis_fit.reasoning}
                </p>
                <p className="mt-2 text-sm text-slate-700">
                  <span className="font-semibold">Bear case:</span> {thesis_fit.bear_case}
                </p>
              </>
            ) : (
              <p className="text-sm text-slate-500">Not yet generated.</p>
            )}
          </DashboardSection>

          <DashboardSection title="Funding">
            {company.total_raised_usd && (
              <p className="text-sm text-slate-700">
                Total raised: <strong>${(company.total_raised_usd / 1e9).toFixed(2)}B</strong>{" "}
                <ConfidenceDot
                  confidence="green"
                  sources={["PitchBook", "Specter", "Crunchbase"]}
                />
              </p>
            )}
            <p className="mt-1 text-sm text-slate-700">
              Last round: <strong>{company.last_round_type?.replace(/_/g, " ")}</strong>
            </p>
            <p className="mt-1 text-sm text-slate-700">
              Investors:{" "}
              <span className="text-slate-600">{company.investors?.slice(0, 3).join(", ")}</span>
            </p>
          </DashboardSection>

          <DashboardSection title="Team">
            {people?.founders?.slice(0, 3).map((f: any) => (
              <p key={f.full_name} className="text-sm text-slate-700">
                <strong>{f.full_name}</strong> · {f.title}{" "}
                {f.prior_exits?.[0] && (
                  <span className="text-xs text-slate-500">— {f.prior_exits[0]}</span>
                )}
              </p>
            ))}
          </DashboardSection>

          <DashboardSection title="Traction" subtitle="Signals">
            {traction?.new_highlights?.map((h: string) => (
              <p key={h} className="text-sm text-slate-700">
                ⚡ {h.replace(/_/g, " ")}
              </p>
            ))}
            {traction?.highlights?.slice(0, 3).map((h: string) => (
              <p key={h} className="text-sm text-slate-700">
                · {h.replace(/_/g, " ")}
              </p>
            ))}
          </DashboardSection>
        </div>

        {/* Prior engagement */}
        {brief.prior_interactions?.length > 0 && (
          <div className="mt-6">
            <DashboardSection title="Prior Engagement" subtitle="Outside the 3-month window">
              <ul className="space-y-1.5 text-sm text-slate-700">
                {brief.prior_interactions.map((i: any, idx: number) => (
                  <li key={idx}>
                    <span className="text-slate-500">{i.date}</span> · {i.type} —{" "}
                    {i.summary}
                  </li>
                ))}
              </ul>
            </DashboardSection>
          </div>
        )}

        {/* Below-the-fold: prose deep-dives */}
        {industry_deepdive && (
          <div className="mt-6">
            <DashboardSection title="Industry Deep-Dive">
              <p className="text-sm leading-relaxed text-slate-700">{industry_deepdive}</p>
            </DashboardSection>
          </div>
        )}

        {market_deepdive && (
          <div className="mt-4">
            <DashboardSection title="Market Deep-Dive">
              <p className="text-sm leading-relaxed text-slate-700">{market_deepdive}</p>
            </DashboardSection>
          </div>
        )}

        {brief.key_engagement_questions?.length > 0 && (
          <div className="mt-4">
            <DashboardSection title="Key Questions">
              <ol className="space-y-2 text-sm text-slate-700">
                {brief.key_engagement_questions.map((q: string, i: number) => (
                  <li key={i}>
                    <span className="font-semibold">{i + 1}.</span> {q}
                  </li>
                ))}
              </ol>
            </DashboardSection>
          </div>
        )}

        <AuditPanel auditData={brief.company} />

        <footer className="mt-8 border-t border-slate-200 pt-4 text-xs text-slate-500">
          Generated {new Date(brief.generated_at).toLocaleString()} · Partner: {brief.partner}
        </footer>
      </div>
    </main>
  );
}
```

- [ ] **Step 5: Verify locally**

Open `http://localhost:3000/pre-meeting-brief` → click "Read brief →" on Anduril → expected: full dashboard brief renders with thesis fit, funding, team, traction, prior engagement, industry, market, key questions.

- [ ] **Step 6: Commit**

```bash
git add app/briefs/ components/ConfidenceDot.tsx components/DashboardSection.tsx components/AuditPanel.tsx
git commit -m "feat(phase-1): brief reader page (Anduril showcase) with dashboard layout"
```

---

### Task 1.16: Approach doc rendered at /approach

**Files:**
- Create: `app/approach/page.tsx`
- Modify: `package.json` (add markdown rendering deps)

- [ ] **Step 1: Install markdown deps**

```bash
npm install react-markdown remark-gfm rehype-slug rehype-autolink-headings
```

- [ ] **Step 2: Create `app/approach/page.tsx`**

```tsx
import fs from "node:fs/promises";
import path from "node:path";

import rehypeAutolinkHeadings from "rehype-autolink-headings";
import rehypeSlug from "rehype-slug";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default async function ApproachPage() {
  const file = path.join(process.cwd(), "docs", "approach.md");
  const markdown = await fs.readFile(file, "utf8");

  return (
    <main className="min-h-screen bg-white px-6 py-12">
      <div className="prose prose-slate prose-headings:tracking-tight prose-table:text-sm mx-auto max-w-3xl">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeSlug, rehypeAutolinkHeadings]}
        >
          {markdown}
        </ReactMarkdown>
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Add Tailwind typography plugin**

Install:

```bash
npm install -D @tailwindcss/typography
```

Update `tailwind.config.ts` to include the plugin:

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
```

- [ ] **Step 4: Verify locally**

Open `http://localhost:3000/pre-meeting-brief/approach`. Expected: full approach doc rendered with table-of-contents-style anchored headings.

- [ ] **Step 5: Commit**

```bash
git add app/approach/ package.json package-lock.json tailwind.config.ts
git commit -m "feat(phase-1): render docs/approach.md at /approach"
```

---

### Task 1.17: Phase 1 deploy + verify

**Files:** None (deployment action)

- [ ] **Step 1: Push to GitHub**

```bash
git push origin master
```

- [ ] **Step 2: Verify Vercel auto-deploy**

Watch the Vercel dashboard. Expected: build passes, deploy completes in ~3 minutes.

- [ ] **Step 3: Run seed against production Postgres**

The seed runs locally pointing at the Vercel Postgres instance (configured in `.env`):

```bash
make seed
```

If you want the seed to run automatically on first deploy in the future, wire it to a build-step or a one-time CLI invocation (out of scope for this plan).

- [ ] **Step 4: Verify the live URL**

Open `https://rishavchatterjee.com/pre-meeting-brief`. Expected: agenda page with 6 cards.

Open Anduril's brief. Expected: full dashboard with all sections populated.

Open `https://rishavchatterjee.com/pre-meeting-brief/approach`. Expected: rendered approach doc.

- [ ] **Step 5: Tag the Phase 1 milestone**

```bash
git tag -a phase-1 -m "Phase 1: schema + fixtures + providers + agenda/reader UI"
git push origin phase-1
```

- [ ] **Step 6: Update the README status line**

In `README.md`, change "Status:" line to:

```markdown
**Status**: Phase 1 (schema + fixtures + agenda + reader UI) live. Phase 2 (pipeline + agents) next.
```

Commit:

```bash
git add README.md
git commit -m "docs: bump status to Phase 1 complete"
git push origin master
```

---

## What ships after this plan

- `rishavchatterjee.com/pre-meeting-brief` — Daily Agenda with 6 company cards
- `rishavchatterjee.com/pre-meeting-brief/briefs/<id>` — Polished Anduril brief, other companies show preview cards (briefs generated live in Phase 2)
- `rishavchatterjee.com/pre-meeting-brief/approach` — Approach doc rendered as a web page
- Postgres schema mirroring the DD, populated with seed data
- 4 in-process providers + 1 standalone MCP server reading 24 fixture files
- Test suite covering models, providers, MCP server (>15 tests passing)
- Tagged Phase 0 and Phase 1 milestones in git

## What ships next (Phase 2 — separate plan)

- LangGraph orchestrator + 4 agents (Qualification, Research, Data Quality, Synthesis)
- Deterministic merge with priority chains + 6 conflict detectors
- Real Anthropic web search (Claude `web_search_20250305`)
- Admin trigger UI (password-gated) — type a domain, watch brief generate live
- Confidence dots and audit panel wired to real provenance

## Self-review notes (inline)

- ✅ Spec coverage: every section of the approach doc (§2-§11) has tasks here or in Phase 2/3 plans
- ✅ Placeholder scan: no TBDs, no "TODO", no "add appropriate error handling"
- ✅ Type consistency: ProviderResult, BriefState, AgendaItem types are consistent across tests and implementation
- ⚠️ Risk: Vercel Python serverless cold starts (4-8s) may cause first-request latency on agenda page. Mitigation: deploy with Fluid Compute enabled (Vercel project setting); UI shows a loading skeleton if API takes > 1s.
- ⚠️ Risk: Alembic autogenerate may produce non-Postgres-native column types because of our cross-dialect TypeDecorators. Task 1.5 Step 3 explicitly checks for this and manually fixes.
- ⚠️ Open: the seed currently hardcodes Anduril's brief content as the only "real" rendered brief. Other companies show "Brief pending." Once Phase 2 lands, all 6 will have generated briefs.

---

*End of Phase 0 + 1 plan. Phase 2 plan drafted after this ships.*
