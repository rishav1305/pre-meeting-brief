"""One-shot seed script.

Run via:
    make seed
    # or
    python -m api.seeds.seed

Idempotent — each `_ensure_*` helper checks for an existing row and skips if present.
Safe to re-run: row counts stay the same after the first run.

Uses a synchronous SQLAlchemy engine with psycopg (psycopg3). This is intentional:
- One-shot script, no concurrency benefit from async.
- psycopg3 supports the `channel_binding` libpq query param that Vercel Postgres /
  Neon append to POSTGRES_URL; asyncpg does not.
- Uses POSTGRES_URL_NON_POOLING (direct connection) so a long-running transaction
  doesn't fight the pooler.
"""
import json
import os
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from api.db.models import (
    CalendarEvent,
    Company,
    People,
    PreMeetingBrief,
    TractionMetrics,
)

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"

DOMAINS = ["anduril.com", "hadrian.co", "modal.com", "ramp.com", "glean.com", "mercury.com"]
PARTNER = "Devon"


def _engine_url() -> str:
    """Convert Vercel's POSTGRES_URL_NON_POOLING to a SQLAlchemy psycopg3 URL."""
    url = os.environ.get("POSTGRES_URL_NON_POOLING") or os.environ.get("POSTGRES_URL", "")
    if not url:
        raise RuntimeError(
            "POSTGRES_URL_NON_POOLING / POSTGRES_URL not set. "
            "Run with `set -a && source .env.local && set +a` first."
        )
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _ensure_company(session: Session, domain: str) -> Company:
    existing = session.scalar(select(Company).where(Company.domain == domain))
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
    session.flush()
    return company


def _ensure_people(session: Session, company: Company) -> None:
    existing = session.get(People, company.company_id)
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


def _ensure_traction(session: Session, company: Company) -> None:
    existing = session.get(TractionMetrics, company.company_id)
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


def _ensure_calendar(session: Session, company: Company, days_ahead: int) -> None:
    meeting_date = date.today() + timedelta(days=days_ahead)
    existing = session.scalar(
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


def _ensure_anduril_brief(session: Session, company: Company) -> None:
    existing = session.scalar(
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


def main() -> None:
    engine = create_engine(_engine_url(), pool_pre_ping=True)
    SessionMaker = sessionmaker(engine, expire_on_commit=False)
    with SessionMaker() as session:
        with session.begin():
            for i, domain in enumerate(DOMAINS):
                company = _ensure_company(session, domain)
                _ensure_people(session, company)
                _ensure_traction(session, company)
                _ensure_calendar(session, company, days_ahead=i + 1)
                if domain == "anduril.com":
                    _ensure_anduril_brief(session, company)
    print(f"Seeded {len(DOMAINS)} companies + calendar events + 1 polished brief.")


if __name__ == "__main__":
    main()
