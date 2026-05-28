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
    Boolean,
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


from sqlalchemy import Date
from datetime import date as date_type


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
    current_node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    node_history: Mapped[list | None] = mapped_column(CrossJSON(), nullable=True)


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

    # Append-only log of distribution attempts. One record per channel
    # (calendar / slack / attio / gmail) per attempt: {channel, target,
    # status, payload, attempted_at, error}. POC mocks the Google Calendar
    # call; the payload is the same one a real API call would carry.
    distribution_log: Mapped[list | None] = mapped_column(CrossJSON(), nullable=True)

    generated_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FirmConfig(Base):
    """Per-firm configuration for thesis-aware brief synthesis.

    A single-row default seeds Renegade for the POC. Production multi-tenancy
    (see approach.md §10) partitions all canonical entities by firm_id and
    reads the synthesis system prompt from this row by firm_id.
    """
    __tablename__ = "firm_config"

    firm_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    thesis_label: Mapped[str] = mapped_column(String(128), nullable=False)
    thesis_description: Mapped[str] = mapped_column(String, nullable=False)
    fit_rubric: Mapped[str] = mapped_column(String, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
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
