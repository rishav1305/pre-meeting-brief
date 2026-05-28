"""firm_config table for per-firm thesis parameterization.

Single-row default seeds Renegade for the POC. Production multi-tenancy
partitions canonical entities by firm_id; this migration is the seam.
"""
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_firm_config"
down_revision: str | None = "0002_etl_run_log_progress"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_RENEGADE_THESIS_DESCRIPTION = (
    "Markets That Matter — workflow-critical sectors in defense, dual-use, "
    "vertical infrastructure, and industries underserved by SaaS."
)

_RENEGADE_FIT_RUBRIC = (
    "5/5 = core thesis (defense, dual-use, workflow-critical vertical infra). "
    "4/5 = strong adjacent (industrial automation, deep-tech infra). "
    "3/5 = AI infra or compute substrate enabling thesis sectors. "
    "2/5 = horizontal SaaS in non-thesis sectors. "
    "1/5 = off-thesis or commodity."
)


def upgrade() -> None:
    op.create_table(
        "firm_config",
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("thesis_label", sa.String(128), nullable=False),
        sa.Column("thesis_description", sa.String, nullable=False),
        sa.Column("fit_rubric", sa.String, nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Partial unique index: only one default firm.
    op.create_index(
        "firm_config_one_default",
        "firm_config",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default = true"),
    )

    # Seed Renegade as the default firm.
    firm_id = uuid4()
    op.execute(
        sa.text(
            "INSERT INTO firm_config "
            "(firm_id, name, thesis_label, thesis_description, fit_rubric, is_default) "
            "VALUES (:firm_id, :name, :thesis_label, :thesis_description, :fit_rubric, true)"
        ).bindparams(
            firm_id=str(firm_id),
            name="Renegade Capital",
            thesis_label="Markets That Matter",
            thesis_description=_RENEGADE_THESIS_DESCRIPTION,
            fit_rubric=_RENEGADE_FIT_RUBRIC,
        )
    )


def downgrade() -> None:
    op.drop_index("firm_config_one_default", table_name="firm_config")
    op.drop_table("firm_config")
