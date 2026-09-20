"""Phase 4 Schema Expansion

Revision ID: 002_phase4_schema
Revises: 001_initial_schema
Create Date: 2026-09-20 10:40:00.000000

"""
from alembic import op
import sqlalchemy as sqla
from sqlalchemy.dialects import postgresql, sqlite

revision = '002_phase4_schema'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. New columns on schemes table
    op.add_column('schemes', sqla.Column('consecutive_fetch_failures', sqla.Integer(), nullable=True, server_default='0'))
    op.add_column('schemes', sqla.Column('last_fetched_at', sqla.DateTime(timezone=True), nullable=True))

    # 2. Table: scheme_changes
    op.create_table(
        'scheme_changes',
        sqla.Column('id', sqla.UUID(), nullable=False),
        sqla.Column('scheme_id', sqla.UUID(), nullable=False),
        sqla.Column('from_version', sqla.String(length=100), nullable=True),
        sqla.Column('to_version', sqla.String(length=100), nullable=True),
        sqla.Column('diff', sqla.JSON(), nullable=False),
        sqla.Column('detected_at', sqla.DateTime(timezone=True), nullable=False),
        sqla.ForeignKeyConstraint(['scheme_id'], ['schemes.id'], ondelete='CASCADE'),
        sqla.PrimaryKeyConstraint('id')
    )

    # 3. Table: notifications
    op.create_table(
        'notifications',
        sqla.Column('id', sqla.UUID(), nullable=False),
        sqla.Column('user_id', sqla.UUID(), nullable=False),
        sqla.Column('type', sqla.String(length=50), nullable=False),
        sqla.Column('scheme_id', sqla.UUID(), nullable=True),
        sqla.Column('message', sqla.Text(), nullable=False),
        sqla.Column('read', sqla.Boolean(), nullable=False, server_default='false'),
        sqla.Column('created_at', sqla.DateTime(timezone=True), nullable=False),
        sqla.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sqla.ForeignKeyConstraint(['scheme_id'], ['schemes.id'], ondelete='SET NULL'),
        sqla.PrimaryKeyConstraint('id')
    )

    # 4. Table: ingestion_runs
    op.create_table(
        'ingestion_runs',
        sqla.Column('id', sqla.UUID(), nullable=False),
        sqla.Column('source', sqla.String(length=255), nullable=False),
        sqla.Column('started_at', sqla.DateTime(timezone=True), nullable=False),
        sqla.Column('finished_at', sqla.DateTime(timezone=True), nullable=True),
        sqla.Column('fetched', sqla.Integer(), nullable=False, server_default='0'),
        sqla.Column('extracted', sqla.Integer(), nullable=False, server_default='0'),
        sqla.Column('flagged', sqla.Integer(), nullable=False, server_default='0'),
        sqla.Column('rejected', sqla.Integer(), nullable=False, server_default='0'),
        sqla.Column('errors', sqla.JSON(), nullable=True),
        sqla.PrimaryKeyConstraint('id')
    )

    # 5. Table: llm_calls
    op.create_table(
        'llm_calls',
        sqla.Column('id', sqla.UUID(), nullable=False),
        sqla.Column('purpose', sqla.String(length=100), nullable=False),
        sqla.Column('model', sqla.String(length=100), nullable=False),
        sqla.Column('tokens_in', sqla.Integer(), nullable=True),
        sqla.Column('tokens_out', sqla.Integer(), nullable=True),
        sqla.Column('latency_ms', sqla.Float(), nullable=True),
        sqla.Column('cost_estimate', sqla.Float(), nullable=True),
        sqla.Column('success', sqla.Boolean(), nullable=False, server_default='true'),
        sqla.Column('created_at', sqla.DateTime(timezone=True), nullable=False),
        sqla.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('llm_calls')
    op.drop_table('ingestion_runs')
    op.drop_table('notifications')
    op.drop_table('scheme_changes')
    op.drop_column('schemes', 'last_fetched_at')
    op.drop_column('schemes', 'consecutive_fetch_failures')
