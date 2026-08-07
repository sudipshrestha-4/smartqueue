"""Add per-service daily token counters, reset audit log, and relax token_number uniqueness

Revision ID: 9c1d2e3f4a5b
Revises: f6a5d7c8b9e0
Create Date: 2026-08-02 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '9c1d2e3f4a5b'
down_revision = 'f6a5d7c8b9e0'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = inspect(conn)

    service_cols = {c['name'] for c in insp.get_columns('services')}
    if 'daily_token_counter' not in service_cols:
        op.add_column(
            'services',
            sa.Column('daily_token_counter', sa.Integer(), nullable=False, server_default='0')
        )
    if 'counter_reset_date' not in service_cols:
        op.add_column('services', sa.Column('counter_reset_date', sa.Date(), nullable=True))

    op.execute("ALTER TABLE queue_entries DROP CONSTRAINT IF EXISTS queue_entries_token_number_key")

    queue_indexes = {idx['name'] for idx in insp.get_indexes('queue_entries')}
    if 'ix_queue_entries_token_number' not in queue_indexes:
        op.create_index('ix_queue_entries_token_number', 'queue_entries', ['token_number'])

    if 'token_reset_logs' not in insp.get_table_names():
        op.create_table(
            'token_reset_logs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('admin_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('admin_name', sa.String(length=100), nullable=False),
            sa.Column('reset_at', sa.DateTime(), nullable=False),
            sa.Column('counters_reset', sa.Integer(), nullable=False, server_default='0'),
        )


def downgrade():
    op.drop_table('token_reset_logs')
    op.drop_index('ix_queue_entries_token_number', table_name='queue_entries')
    op.create_unique_constraint('queue_entries_token_number_key', 'queue_entries', ['token_number'])
    op.drop_column('services', 'counter_reset_date')
    op.drop_column('services', 'daily_token_counter')
