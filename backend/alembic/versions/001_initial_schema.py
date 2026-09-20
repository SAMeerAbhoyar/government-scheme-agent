"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-19 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Users Table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), server_default='user', nullable=False),
        sa.Column('consent_given_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 3. Profiles Table
    op.create_table(
        'profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
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
        sa.Column('annual_income', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('family_size', sa.Integer(), nullable=True),
        sa.Column('social_category', sa.String(length=50), nullable=True),
        sa.Column('disability', sa.Boolean(), nullable=True),
        sa.Column('minority', sa.Boolean(), nullable=True),
        sa.Column('bpl_card', sa.Boolean(), nullable=True),
        sa.Column('domicile_state', sa.String(length=100), nullable=True),
        sa.Column('marital_status', sa.String(length=50), nullable=True),
        sa.Column('land_holding_acres', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('other_attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # 4. Schemes Table
    op.create_table(
        'schemes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('benefits', sa.Text(), nullable=True),
        sa.Column('eligibility_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('documents', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('application_process', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('application_url', sa.String(length=500), nullable=True),
        sa.Column('deadline_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='active', nullable=False),
        sa.Column('last_verified', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extraction_confidence', sa.Float(), nullable=True),
    )

    # 5. Scheme Versions Table
    op.create_table(
        'scheme_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scheme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('schemes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('extracted_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 6. Scheme Chunks Table (Vector + TSVector)
    op.create_table(
        'scheme_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scheme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('schemes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('section', sa.String(length=50), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('embedding', Vector(768), nullable=True),
        sa.Column('tsv', postgresql.TSVECTOR(), nullable=True),
    )
    op.create_index('idx_scheme_chunks_tsv', 'scheme_chunks', ['tsv'], postgresql_using='gin')

    # 7. Saved Schemes Table
    op.create_table(
        'saved_schemes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scheme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('schemes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('saved_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 8. Search History Table
    op.create_table(
        'search_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mode', sa.String(length=50), nullable=False),
        sa.Column('query', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 9. Recommendations Table
    op.create_table(
        'recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scheme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('schemes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('match_status', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 10. Source Records Table
    op.create_table(
        'source_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scheme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('schemes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('verification_status', sa.String(length=50), server_default='pending', nullable=False),
    )

    # 11. Feedback Table
    op.create_table(
        'feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recommendation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('recommendations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('useful', sa.Boolean(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

def downgrade() -> None:
    op.drop_table('feedback')
    op.drop_table('source_records')
    op.drop_table('recommendations')
    op.drop_table('search_history')
    op.drop_table('saved_schemes')
    op.drop_index('idx_scheme_chunks_tsv', table_name='scheme_chunks')
    op.drop_table('scheme_chunks')
    op.drop_table('scheme_versions')
    op.drop_table('schemes')
    op.drop_table('profiles')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.execute("DROP EXTENSION IF EXISTS vector;")
