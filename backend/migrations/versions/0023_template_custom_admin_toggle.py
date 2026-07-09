"""deployment_templates.custom_admin_enabled (off by default)

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-09

"""
import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "deployment_templates",
        sa.Column("custom_admin_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column(
        "deployment_templates", "local_admin_username", server_default="Administrator",
    )
    # 0022 gave every existing template "svcadmin" unconditionally; the
    # custom-admin pipeline is now opt-in and off by default, so revert
    # every row back to the built-in account it'll actually deploy with
    # unless an operator explicitly turns the toggle on.
    op.execute("UPDATE deployment_templates SET local_admin_username = 'Administrator'")


def downgrade() -> None:
    op.alter_column("deployment_templates", "local_admin_username", server_default="svcadmin")
    op.drop_column("deployment_templates", "custom_admin_enabled")
