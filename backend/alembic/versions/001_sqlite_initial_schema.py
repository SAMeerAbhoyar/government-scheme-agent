"""001_sqlite_initial_schema

Revision ID: 001_sqlite_initial_schema
Revises: 
Create Date: 2026-09-20 21:28:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_sqlite_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='user'),
        sa.Column('consent_given_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Profiles table
    op.create_table(
        'profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('gender', sa.String(length=50), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('rural_urban', sa.String(length=50), nullable=True),
        sa.Column('education_level', sa.String(length=100), nullable=True),
        sa.Column('course', sa.String(length=100), nullable=True),
        sa.Column('year', sa.String(length=50), nullable=True),
        sa.Column('occupation', sa.String(length=100), nullable=True),
        sa.Column('employment_status', sa.String(length=100), nullable=True),
        sa.Column('annual_income', sa.Text(), nullable=True),
        sa.Column('family_size', sa.Integer(), nullable=True),
        sa.Column('social_category', sa.Text(), nullable=True),
        sa.Column('disability', sa.Text(), nullable=True),
        sa.Column('minority', sa.Text(), nullable=True),
        sa.Column('bpl_card', sa.Text(), nullable=True),
        sa.Column('domicile_state', sa.String(length=100), nullable=True),
        sa.Column('marital_status', sa.String(length=50), nullable=True),
        sa.Column('land_holding_acres', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('other_attributes', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    # Schemes table
    op.create_table(
        'schemes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('benefits', sa.Text(), nullable=True),
        sa.Column('eligibility_rules', sa.JSON(), nullable=True),
        sa.Column('documents', sa.JSON(), nullable=True),
        sa.Column('application_process', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('application_url', sa.String(length=500), nullable=True),
        sa.Column('deadline_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('last_verified', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extraction_confidence', sa.Float(), nullable=True),
        sa.Column('consecutive_fetch_failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_fetched_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Scheme versions
    op.create_table(
        'scheme_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scheme_id', sa.UUID(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('extracted_json', sa.JSON(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scheme_id'], ['schemes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Scheme chunks
    op.create_table(
        'scheme_chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scheme_id', sa.UUID(), nullable=False),
        sa.Column('section', sa.String(length=50), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('embedding', sa.JSON(), nullable=True),
        sa.Column('tsv', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['scheme_id'], ['schemes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Scheme changes
    op.create_table(
        'scheme_changes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scheme_id', sa.UUID(), nullable=False),
        sa.Column('from_version', sa.String(length=100), nullable=True),
        sa.Column('to_version', sa.String(length=100), nullable=True),
        sa.Column('diff', sa.JSON(), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scheme_id'], ['schemes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Source records
    op.create_table(
        'source_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scheme_id', sa.UUID(), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.ForeignKeyConstraint(['scheme_id'], ['schemes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Ingestion runs
    op.create_table(
        'ingestion_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fetched', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('extracted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('flagged', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rejected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Saved schemes
    op.create_table(
        'saved_schemes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('scheme_id', sa.UUID(), nullable=False),
        sa.Column('saved_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scheme_id'], ['schemes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Search history
    op.create_table(
        'search_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('mode', sa.String(length=50), nullable=False),
        sa.Column('query', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Recommendations
    op.create_table(
        'recommendations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('scheme_id', sa.UUID(), nullable=False),
        sa.Column('match_status', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scheme_id'], ['schemes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Feedback
    op.create_table(
        'feedback',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('recommendation_id', sa.UUID(), nullable=False),
        sa.Column('useful', sa.Boolean(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('scheme_id', sa.UUID(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scheme_id'], ['schemes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # LLM Calls
    op.create_table(
        'llm_calls',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('purpose', sa.String(length=100), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('tokens_in', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_out', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_estimate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # FTS5 virtual table
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        try:
            op.execute("CREATE VIRTUAL TABLE IF NOT EXISTS scheme_chunks_fts USING fts5(chunk_id UNINDEXED, text, section);")
        except Exception:
            pass

def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        try:
            op.execute("DROP TABLE IF EXISTS scheme_chunks_fts;")
        except Exception:
            pass
    op.drop_table('llm_calls')
    op.drop_table('notifications')
    op.drop_table('feedback')
    op.drop_table('recommendations')
    op.drop_table('search_history')
    op.drop_table('saved_schemes')
    op.drop_table('ingestion_runs')
    op.drop_table('source_records')
    op.drop_table('scheme_changes')
    op.drop_table('scheme_chunks')
    op.drop_table('scheme_versions')
    op.drop_table('schemes')
    op.drop_table('profiles')
    op.drop_table('users')
