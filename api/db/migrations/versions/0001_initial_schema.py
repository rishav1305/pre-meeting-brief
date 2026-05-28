"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-28 09:10:28.683199

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'company',
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('domain_aliases', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('specter_id', sa.String(length=64), nullable=True),
        sa.Column('cb_uuid', sa.String(length=64), nullable=True),
        sa.Column('pb_id', sa.String(length=64), nullable=True),
        sa.Column('linkedin_url', sa.String(length=512), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('operating_status', sa.String(length=16), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('customer_focus', sa.String(length=16), nullable=True),
        sa.Column('customer_profile', sa.String(), nullable=True),
        sa.Column('founded_year', sa.SmallInteger(), nullable=True),
        sa.Column('hq_city', sa.String(length=128), nullable=True),
        sa.Column('hq_country', sa.String(length=2), nullable=True),
        sa.Column('hq_region', sa.String(length=64), nullable=True),
        sa.Column('certifications', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('traction_highlights', sa.String(), nullable=True),
        sa.Column('technologies', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('total_raised_usd', sa.BigInteger(), nullable=True),
        sa.Column('last_round_type', sa.String(length=32), nullable=True),
        sa.Column('last_round_date', sa.DateTime(), nullable=True),
        sa.Column('last_round_usd', sa.BigInteger(), nullable=True),
        sa.Column('post_money_valuation_usd', sa.BigInteger(), nullable=True),
        sa.Column('round_count', sa.SmallInteger(), nullable=True),
        sa.Column('growth_stage', sa.String(length=32), nullable=True),
        sa.Column('investors', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('revenue_estimate_usd', sa.BigInteger(), nullable=True),
        sa.Column('audit', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "customer_focus IS NULL OR customer_focus IN ('b2b','b2c','b2b_b2c','b2c_b2b')",
            name='company_customer_focus_check',
        ),
        sa.CheckConstraint(
            "growth_stage IS NULL OR growth_stage IN ('bootstrapped','seed_stage','early_stage','growth_stage','late_stage','exit_stage')",
            name='company_growth_stage_check',
        ),
        sa.CheckConstraint(
            "operating_status IN ('active','acquired','closed','ipo')",
            name='company_operating_status_check',
        ),
        sa.PrimaryKeyConstraint('company_id'),
    )
    op.create_index(op.f('ix_company_domain'), 'company', ['domain'], unique=True)

    op.create_table(
        'people',
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('founders', postgresql.JSONB(), nullable=True),
        sa.Column('key_executives', postgresql.JSONB(), nullable=True),
        sa.Column('board_members', postgresql.JSONB(), nullable=True),
        sa.Column('employee_count', sa.Integer(), nullable=True),
        sa.Column('employee_range', sa.String(length=16), nullable=True),
        sa.Column('headcount_trend', postgresql.JSONB(), nullable=True),
        sa.Column('hiring_signals', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('open_role_count', sa.Integer(), nullable=True),
        sa.Column('org_rank', sa.Integer(), nullable=True),
        sa.Column('audit', postgresql.JSONB(), nullable=True),
        sa.CheckConstraint(
            "employee_range IS NULL OR employee_range IN ('1-10','11-50','51-200','201-500','501-1000','1001-5000','5001-10000','10001+')",
            name='people_employee_range_check',
        ),
        sa.ForeignKeyConstraint(['company_id'], ['company.company_id']),
        sa.PrimaryKeyConstraint('company_id'),
    )

    op.create_table(
        'traction_metrics',
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('highlights', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('new_highlights', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('web_visits_latest', sa.BigInteger(), nullable=True),
        sa.Column('web_visits_trend', postgresql.JSONB(), nullable=True),
        sa.Column('web_popularity_rank', sa.Integer(), nullable=True),
        sa.Column('bounce_rate', sa.Float(), nullable=True),
        sa.Column('top_traffic_country', sa.String(length=64), nullable=True),
        sa.Column('traffic_sources', sa.String(), nullable=True),
        sa.Column('linkedin_followers', sa.Integer(), nullable=True),
        sa.Column('linkedin_trend', postgresql.JSONB(), nullable=True),
        sa.Column('g2_rating', sa.Float(), nullable=True),
        sa.Column('g2_review_count', sa.Integer(), nullable=True),
        sa.Column('trustpilot_rating', sa.Float(), nullable=True),
        sa.Column('awards', postgresql.JSONB(), nullable=True),
        sa.Column('patents', sa.SmallInteger(), nullable=True),
        sa.Column('reported_clients', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('it_spend_usd', sa.Integer(), nullable=True),
        sa.Column('news', postgresql.JSONB(), nullable=True),
        sa.Column('audit', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['company.company_id']),
        sa.PrimaryKeyConstraint('company_id'),
    )

    op.create_table(
        'etl_run_log',
        sa.Column('run_id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running','merged','complete','failed')",
            name='etl_run_log_status_check',
        ),
        sa.ForeignKeyConstraint(['company_id'], ['company.company_id']),
        sa.PrimaryKeyConstraint('run_id'),
    )

    op.create_table(
        'data_quality_flags',
        sa.Column('flag_id', sa.Uuid(), nullable=False),
        sa.Column('run_id', sa.Uuid(), nullable=True),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('field', sa.String(length=64), nullable=False),
        sa.Column('issue', sa.String(length=128), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False),
        sa.Column('source_a', sa.String(length=32), nullable=True),
        sa.Column('value_a', sa.String(), nullable=True),
        sa.Column('source_b', sa.String(length=32), nullable=True),
        sa.Column('value_b', sa.String(), nullable=True),
        sa.Column('flagged_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['company.company_id']),
        sa.PrimaryKeyConstraint('flag_id'),
    )

    op.create_table(
        'calendar_events',
        sa.Column('event_id', sa.Uuid(), nullable=False),
        sa.Column('partner', sa.String(length=64), nullable=False),
        sa.Column('company_domain', sa.String(length=255), nullable=False),
        sa.Column('meeting_date', sa.Date(), nullable=False),
        sa.Column('attendees', postgresql.JSONB(), nullable=True),
        sa.Column('source', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('event_id'),
    )
    op.create_index(
        op.f('ix_calendar_events_company_domain'),
        'calendar_events',
        ['company_domain'],
        unique=False,
    )

    op.create_table(
        'pre_meeting_brief',
        sa.Column('brief_id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('run_id', sa.Uuid(), nullable=True),
        sa.Column('partner', sa.String(length=64), nullable=False),
        sa.Column('meeting_date', sa.Date(), nullable=False),
        sa.Column('thesis_fit', postgresql.JSONB(), nullable=True),
        sa.Column('industry_deepdive', sa.String(), nullable=True),
        sa.Column('market_deepdive', sa.String(), nullable=True),
        sa.Column('key_engagement_questions', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('podcast_mentions', postgresql.JSONB(), nullable=True),
        sa.Column('prior_interactions', postgresql.JSONB(), nullable=True),
        sa.Column('pre_meeting_brief', sa.String(), nullable=False),
        sa.Column('pre_meeting_brief_link', sa.String(length=512), nullable=False),
        sa.Column('google_drive_link', sa.String(length=512), nullable=False),
        sa.Column('attio_company_link', sa.String(length=512), nullable=False),
        sa.Column('audit_company', postgresql.JSONB(), nullable=True),
        sa.Column('audit_people', postgresql.JSONB(), nullable=True),
        sa.Column('audit_traction_metrics', postgresql.JSONB(), nullable=True),
        sa.Column('generated_ts', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['company.company_id']),
        sa.PrimaryKeyConstraint('brief_id'),
    )

    op.create_table(
        'source_payloads',
        sa.Column('payload_id', sa.Uuid(), nullable=False),
        sa.Column('company_id', sa.Uuid(), nullable=False),
        sa.Column('source', sa.String(length=32), nullable=False),
        sa.Column('raw', postgresql.JSONB(), nullable=False),
        sa.Column('pulled_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['company.company_id']),
        sa.PrimaryKeyConstraint('payload_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('source_payloads')
    op.drop_table('pre_meeting_brief')
    op.drop_index(op.f('ix_calendar_events_company_domain'), table_name='calendar_events')
    op.drop_table('calendar_events')
    op.drop_table('data_quality_flags')
    op.drop_table('etl_run_log')
    op.drop_table('traction_metrics')
    op.drop_table('people')
    op.drop_index(op.f('ix_company_domain'), table_name='company')
    op.drop_table('company')
