"""Add user account fields

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-01 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_login', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('profile_photo', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('reset_token', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('reset_token_expires', sa.DateTime(), nullable=True))
        batch_op.create_index('ix_users_reset_token', ['reset_token'], unique=False)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_reset_token')
        batch_op.drop_column('reset_token_expires')
        batch_op.drop_column('reset_token')
        batch_op.drop_column('profile_photo')
        batch_op.drop_column('last_login')
