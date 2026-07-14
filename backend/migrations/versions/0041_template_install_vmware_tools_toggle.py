"""add deployment_templates.install_vmware_tools toggle

Explicitly requested: a per-template (and per-deployment, via the
"Customize installation" override) checkbox to skip installing VMware
Tools entirely. Previously this step always ran unconditionally.
Defaults to true, preserving existing behavior for every template that
already exists.

Revision ID: 0041
Revises: 0040
Create Date: 2026-07-15

"""
from alembic import op
import sqlalchemy as sa

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "deployment_templates",
        sa.Column("install_vmware_tools", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("deployment_templates", "install_vmware_tools")
