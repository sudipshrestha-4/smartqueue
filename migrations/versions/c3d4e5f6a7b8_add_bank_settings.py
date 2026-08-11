"""Add bank operating hours settings table

Revision ID: c3d4e5f6a7b8
Revises: 9c1d2e3f4a5b
Create Date: 2026-08-11 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = 'c3d4e5f6a7b8'
down_revision = '9c1d2e3f4a5b'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = inspect(conn)

    if 'bank_settings' not in insp.get_table_names():
        op.create_table(
            'bank_settings',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('open_time', sa.Time(), nullable=False),
            sa.Column('close_time', sa.Time(), nullable=False),
            sa.Column('manual_override', sa.String(length=10), nullable=True),
        )
        op.execute(
            "INSERT INTO bank_settings (id, open_time, close_time, manual_override) "
            "VALUES (1, '09:00:00', '17:00:00', NULL)"
        )


def downgrade():
    op.drop_table('bank_settings')
