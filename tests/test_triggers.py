"""Tests for the admin trigger endpoint — Phase 2 Task 2.10.

The tests patch ``api.routes.triggers.run_pipeline`` so we never actually
invoke the agents or the real DB-coupled orchestrator. They also override
``api.routes.triggers.SessionLocal`` to point at the in-memory sqlite test
session so the endpoint's pre-create + status queries work end-to-end.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.db.models import Base, Company, EtlRunLog, PreMeetingBrief
from api.index import app
from api.routes import triggers as triggers_module


ADMIN_PW = "test-admin-pw"


@pytest_asyncio.fixture
async def test_session_factory():
    """Spin up an in-memory sqlite engine and override the route's session.

    The triggers route does its own ``async with SessionLocal()`` calls
    (for the pre-create + the status read), so we swap the module-level
    SessionLocal binding rather than relying on FastAPI's Depends pattern.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionMaker = async_sessionmaker(engine, expire_on_commit=False)

    original = triggers_module.SessionLocal
    triggers_module.SessionLocal = SessionMaker
    try:
        yield SessionMaker
    finally:
        triggers_module.SessionLocal = original
        await engine.dispose()


@pytest.fixture
def admin_pw():
    """Patch settings.admin_password for the duration of one test."""
    with patch.object(triggers_module.settings, "admin_password", ADMIN_PW):
        yield ADMIN_PW


@pytest.fixture
def stub_run_pipeline():
    """Replace run_pipeline with a no-op async function.

    The endpoint kicks off ``run_pipeline`` as a BackgroundTask; we don't
    want the agents to actually fire during tests.
    """
    async def _noop(*args, **kwargs):
        return None

    with patch.object(triggers_module, "run_pipeline", new=_noop) as p:
        yield p


@pytest.fixture
def client():
    return TestClient(app)


VALID_BODY = {
    "domain": "hadrian.co",
    "company_name": "Hadrian",
    "partner": "Devon",
    "meeting_date": "2026-05-30",
}


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/triggers/manual
# ─────────────────────────────────────────────────────────────────────────────


def test_trigger_missing_password_401(client, admin_pw, test_session_factory, stub_run_pipeline):
    response = client.post("/api/triggers/manual", json=VALID_BODY)
    assert response.status_code == 401


def test_trigger_wrong_password_401(client, admin_pw, test_session_factory, stub_run_pipeline):
    response = client.post(
        "/api/triggers/manual",
        json=VALID_BODY,
        headers={"X-Admin-Password": "wrong"},
    )
    assert response.status_code == 401


async def test_trigger_correct_password_202(
    client, admin_pw, test_session_factory, stub_run_pipeline
):
    response = client.post(
        "/api/triggers/manual",
        json=VALID_BODY,
        headers={"X-Admin-Password": ADMIN_PW},
    )
    assert response.status_code == 202
    body = response.json()
    assert "run_id" in body
    assert "status_url" in body
    run_id = UUID(body["run_id"])
    assert body["status_url"].endswith(str(run_id))

    # Verify the pre-create happened: there should be exactly one running row
    async with test_session_factory() as session:
        run = await session.get(EtlRunLog, run_id)
        assert run is not None
        assert run.status == "running"


def test_trigger_validates_body(client, admin_pw, test_session_factory, stub_run_pipeline):
    # Missing domain
    bad1 = {k: v for k, v in VALID_BODY.items() if k != "domain"}
    r1 = client.post("/api/triggers/manual", json=bad1, headers={"X-Admin-Password": ADMIN_PW})
    assert r1.status_code == 422

    # Missing partner
    bad2 = {k: v for k, v in VALID_BODY.items() if k != "partner"}
    r2 = client.post("/api/triggers/manual", json=bad2, headers={"X-Admin-Password": ADMIN_PW})
    assert r2.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/triggers/runs/{run_id}
# ─────────────────────────────────────────────────────────────────────────────


def test_status_unknown_run_404(client, admin_pw, test_session_factory, stub_run_pipeline):
    unknown = uuid4()
    response = client.get(f"/api/triggers/runs/{unknown}")
    assert response.status_code == 404


async def test_status_running_returns_running(
    client, admin_pw, test_session_factory, stub_run_pipeline
):
    # Seed a company + a running etl_run_log
    async with test_session_factory() as session:
        company = Company(domain="hadrian.co", operating_status="active")
        session.add(company)
        await session.flush()
        run = EtlRunLog(company_id=company.company_id, status="running")
        session.add(run)
        await session.flush()
        run_id = run.run_id
        company_id = company.company_id
        await session.commit()

    response = client.get(f"/api/triggers/runs/{run_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == str(run_id)
    assert body["status"] == "running"
    assert body["company_id"] == str(company_id)
    assert body["brief_id"] is None
    assert body["completed_at"] is None
    assert body["error_message"] is None
    assert body["recent_tool_calls"] == []


async def test_status_complete_includes_brief_id(
    client, admin_pw, test_session_factory, stub_run_pipeline
):
    from datetime import date as date_type

    async with test_session_factory() as session:
        company = Company(domain="hadrian.co", operating_status="active")
        session.add(company)
        await session.flush()

        run = EtlRunLog(
            company_id=company.company_id,
            status="complete",
            completed_at=datetime.utcnow(),
        )
        session.add(run)
        await session.flush()

        brief = PreMeetingBrief(
            company_id=company.company_id,
            run_id=run.run_id,
            partner="Devon",
            meeting_date=date_type(2026, 5, 30),
            pre_meeting_brief="<article>x</article>",
        )
        session.add(brief)
        await session.flush()

        run_id = run.run_id
        brief_id = brief.brief_id
        await session.commit()

    response = client.get(f"/api/triggers/runs/{run_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert body["brief_id"] == str(brief_id)
    assert body["completed_at"] is not None
