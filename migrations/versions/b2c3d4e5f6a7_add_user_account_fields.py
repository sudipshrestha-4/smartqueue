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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Get existing columns in users table
    existing_columns = {
        column['name']
        for column in inspector.get_columns('users')
    }

    # Add only columns that don't already exist
    with op.batch_alter_table('users', schema=None) as batch_op:

        if 'last_login' not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    'last_login',
                    sa.DateTime(),
                    nullable=True
                )
            )

        if 'profile_photo' not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    'profile_photo',
                    sa.String(length=255),
                    nullable=True
                )
            )

        if 'reset_token' not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    'reset_token',
                    sa.String(length=128),
                    nullable=True
                )
            )

        if 'reset_token_expires' not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    'reset_token_expires',
                    sa.DateTime(),
                    nullable=True
                )
            )

    # Check whether the reset_token index already exists
    existing_indexes = {
        index['name']
        for index in inspector.get_indexes('users')
    }

    if 'ix_users_reset_token' not in existing_indexes:
        op.create_index(
            'ix_users_reset_token',
            'users',
            ['reset_token'],
            unique=False
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_columns = {
        column['name']
        for column in inspector.get_columns('users')
    }

    existing_indexes = {
        index['name']
        for index in inspector.get_indexes('users')
    }

    if 'ix_users_reset_token' in existing_indexes:
        op.drop_index(
            'ix_users_reset_token',
            table_name='users'
        )

    with op.batch_alter_table('users', schema=None) as batch_op:

        if 'reset_token_expires' in existing_columns:
            batch_op.drop_column('reset_token_expires')

        if 'reset_token' in existing_columns:
            batch_op.drop_column('reset_token')

        if 'profile_photo' in existing_columns:
            batch_op.drop_column('profile_photo')

        if 'last_login' in existing_columns:
            batch_op.drop_column('last_login')