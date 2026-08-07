"""Drop the one-active-token-per-customer partial unique index

Revision ID: f6a5d7c8b9e0
Revises: b2c3d4e5f6a7
Create Date: 2026-08-02 00:00:00.000000

"""

from alembic import op


revision = 'f6a5d7c8b9e0'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP INDEX IF EXISTS uq_one_active_token_per_customer")


def downgrade():
    op.execute(
        """
        CREATE UNIQUE INDEX uq_one_active_token_per_customer
        ON queue_entries (customer_id)
        WHERE status IN ('waiting', 'called', 'in_service')
        """
    )
