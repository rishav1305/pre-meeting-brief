"""BriefState — the shared state flowing through every pipeline node.

See docs/approach.md §5.6 and the Phase 2 plan for the role of this object.
Stateful graph orchestration: each node reads from and writes to this
pydantic model. Type-safe at every node boundary; serializable for
inspection and the /runs page.
"""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


Qualification = Literal["proceed", "skip", "flag_for_human"]
Severity = Literal["low", "medium", "high"]


class DQFlag(BaseModel):
    """A data-quality flag emitted by merge_canonical or the DQ Agent."""
    field: str
    issue: str
    severity: Severity = "medium"
    source_a: str | None = None
    value_a: str | None = None
    source_b: str | None = None
    value_b: str | None = None


class ToolCall(BaseModel):
    """One agent tool invocation, captured for audit + UI."""
    agent: str           # e.g. "research", "synthesis"
    tool: str            # e.g. "web_search", "specter_mcp.fetch_company"
    input_summary: str   # truncated repr
    output_summary: str  # truncated repr
    duration_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: str | None = None


class BriefState(BaseModel):
    """Shared state passed between every node in the pipeline graph."""

    # ───── Input ─────
    company_name: str
    domain: str
    meeting_date: date
    partner: str

    # ───── Populated by resolve_company ─────
    company_id: UUID | None = None
    run_id: UUID | None = None
    started_at: datetime | None = None

    # ───── Populated by qualification_agent ─────
    qualification: Qualification | None = None
    qualification_reason: str | None = None

    # ───── Populated by fetch_all (and research_agent) ─────
    specter_raw: dict | None = None
    crunchbase_raw: dict | None = None
    pitchbook_raw: dict | None = None
    attio_raw: dict | None = None
    web_raw: str | None = None         # ephemeral, NOT persisted
    web_citations: list[dict] = Field(default_factory=list)

    # ───── Populated by merge_canonical ─────
    company_profile: dict | None = None    # merged canonical.company shape
    funding_history: dict | None = None
    team_people: dict | None = None        # merged canonical.people shape
    traction_signals: dict | None = None   # merged canonical.traction_metrics shape
    data_quality_flags: list[DQFlag] = Field(default_factory=list)

    # ───── Populated by data_quality_agent ─────
    dq_ranked: list[DQFlag] = Field(default_factory=list)

    # ───── Populated by synthesise_brief ─────
    brief_id: UUID | None = None
    brief_html: str | None = None
    brief_json: dict | None = None

    # ───── Diagnostics (observable on /runs and admin) ─────
    timings: dict[str, float] = Field(default_factory=dict)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    error: str | None = None
