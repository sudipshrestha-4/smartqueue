"""Add service_id to counters

Revision ID: 87226543e415
Revises:
Create Date: 2026-07-12 09:14:32.743200
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '87226543e415'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Get existing columns in counters table
    columns = {
        column["name"]
        for column in inspector.get_columns("counters")
    }

    # Add service_id only if it does not already exist
    if "service_id" not in columns:
        op.add_column(
            "counters",
            sa.Column("service_id", sa.Integer(), nullable=True)
        )

    # Check existing foreign keys
    foreign_keys = inspector.get_foreign_keys("counters")

    service_fk_exists = any(
        "service_id" in (fk.get("constrained_columns") or [])
        and fk.get("referred_table") == "services"
        for fk in foreign_keys
    )

    # Create foreign key only if it does not already exist
    if not service_fk_exists:
        op.create_foreign_key(
            "fk_counters_service_id_services",
            "counters",
            "services",
            ["service_id"],
            ["id"]
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("counters")
    }

    foreign_keys = inspector.get_foreign_keys("counters")

    service_fk = next(
        (
            fk for fk in foreign_keys
            if "service_id" in (fk.get("constrained_columns") or [])
            and fk.get("referred_table") == "services"
        ),
        None
    )

    if service_fk:
        if service_fk.get("name"):
            op.drop_constraint(
                service_fk["name"],
                "counters",
                type_="foreignkey"
            )

    if "service_id" in columns:
        op.drop_column("counters", "service_id")