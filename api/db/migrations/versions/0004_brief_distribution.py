"""Distribution log column on pre_meeting_brief.

Captures the payload of the distribution call (Google Calendar event-description
append today, eventually Slack/Attio webhooks) so the partner-facing brief reader
can show a "Distributed to calendar" badge with timestamp and target.

Schema is intentionally JSONB so future channels (Slack, Attio, Gmail) can be
added without a schema change — distribution_log is treated as an append-only
event log, one record per channel attempt.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_brief_distribution"
down_revision: str | None = "0003_firm_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pre_meeting_brief",
        sa.Column("distribution_log", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pre_meeting_brief", "distribution_log")
