"""Add feedback and pending_services tables

Revision ID: a1b2c3d4e5f6
Revises: 87226543e415
Create Date: 2026-08-01 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '87226543e415'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Create feedbacks table only if it does not already exist
    if not inspector.has_table('feedbacks'):
        op.create_table(
            'feedbacks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('queue_entry_id', sa.Integer(), nullable=False),
            sa.Column('customer_id', sa.Integer(), nullable=False),
            sa.Column('rating', sa.Integer(), nullable=False),
            sa.Column('comment', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ['customer_id'],
                ['users.id']
            ),
            sa.ForeignKeyConstraint(
                ['queue_entry_id'],
                ['queue_entries.id']
            ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('queue_entry_id')
        )

    # Create pending_services table only if it does not already exist
    if not inspector.has_table('pending_services'):
        op.create_table(
            'pending_services',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('customer_id', sa.Integer(), nullable=False),
            sa.Column('service_id', sa.Integer(), nullable=False),
            sa.Column('priority_type', sa.String(length=20), nullable=True),
            sa.Column('sequence_order', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ['customer_id'],
                ['users.id']
            ),
            sa.ForeignKeyConstraint(
                ['service_id'],
                ['services.id']
            ),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('pending_services'):
        op.drop_table('pending_services')

    if inspector.has_table('feedbacks'):
        op.drop_table('feedbacks')