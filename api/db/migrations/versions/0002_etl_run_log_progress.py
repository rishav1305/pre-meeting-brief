"""Phase 3 polish: real-time per-node progress on etl_run_log.

Adds:
  - current_node TEXT    — name of the node currently running, or last
                            completed if status is terminal
  - node_history JSONB   — array of {node, status, started_at,
                            completed_at, duration_ms, message} records;
                            updated by the pipeline as each node runs.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_etl_run_log_progress"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "etl_run_log",
        sa.Column("current_node", sa.String(64), nullable=True),
    )
    op.add_column(
        "etl_run_log",
        sa.Column("node_history", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("etl_run_log", "node_history")
    op.drop_column("etl_run_log", "current_node")
