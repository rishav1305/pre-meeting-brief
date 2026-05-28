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
