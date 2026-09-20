"""Encrypt profile columns at rest

Revision ID: 003_encrypt_profile_columns
Revises: 002_phase4_schema
Create Date: 2026-09-20 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sqla
from sqlalchemy.sql import text
from app.core.crypto import encrypt_value

revision = '003_encrypt_profile_columns'
down_revision = '002_phase4_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Alter column types in profiles table to Text to store Fernet ciphertext tokens
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        op.alter_column('profiles', 'social_category', type_=sqla.Text(), postgresql_using='social_category::text')
        op.alter_column('profiles', 'disability', type_=sqla.Text(), postgresql_using='disability::text')
        op.alter_column('profiles', 'minority', type_=sqla.Text(), postgresql_using='minority::text')
        op.alter_column('profiles', 'bpl_card', type_=sqla.Text(), postgresql_using='bpl_card::text')
        op.alter_column('profiles', 'annual_income', type_=sqla.Text(), postgresql_using='annual_income::text')
    else:
        # SQLite or other dialects: batch alter
        with op.batch_alter_table('profiles') as batch_op:
            batch_op.alter_column('social_category', type_=sqla.Text())
            batch_op.alter_column('disability', type_=sqla.Text())
            batch_op.alter_column('minority', type_=sqla.Text())
            batch_op.alter_column('bpl_card', type_=sqla.Text())
            batch_op.alter_column('annual_income', type_=sqla.Text())

    # 2. Re-encrypt existing unencrypted rows
    rows = bind.execute(text("SELECT id, social_category, disability, minority, bpl_card, annual_income FROM profiles")).fetchall()
    for row in rows:
        pid, cat, dis, min_c, bpl, inc = row[0], row[1], row[2], row[3], row[4], row[5]

        # Encrypt each column if present and not already Fernet encrypted
        enc_cat = encrypt_value(cat) if cat is not None and not str(cat).startswith("gAAAAA") else cat
        enc_dis = encrypt_value(dis) if dis is not None and not str(dis).startswith("gAAAAA") else dis
        enc_min = encrypt_value(min_c) if min_c is not None and not str(min_c).startswith("gAAAAA") else min_c
        enc_bpl = encrypt_value(bpl) if bpl is not None and not str(bpl).startswith("gAAAAA") else bpl
        enc_inc = encrypt_value(inc) if inc is not None and not str(inc).startswith("gAAAAA") else inc

        bind.execute(
            text("""
                UPDATE profiles 
                SET social_category = :cat, disability = :dis, minority = :min, bpl_card = :bpl, annual_income = :inc
                WHERE id = :id
            """),
            {"id": pid, "cat": enc_cat, "dis": enc_dis, "min": enc_min, "bpl": enc_bpl, "inc": enc_inc}
        )

def downgrade() -> None:
    # Downgrade alters columns back (data remains string/text in downgrade)
    with op.batch_alter_table('profiles') as batch_op:
        batch_op.alter_column('social_category', type_=sqla.String(length=50))
        batch_op.alter_column('disability', type_=sqla.Boolean())
        batch_op.alter_column('minority', type_=sqla.Boolean())
        batch_op.alter_column('bpl_card', type_=sqla.Boolean())
        batch_op.alter_column('annual_income', type_=sqla.Numeric(precision=14, scale=2))
