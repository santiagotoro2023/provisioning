"""deployment_templates.local_admin_username

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-09

"""
import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "deployment_templates",
        sa.Column("local_admin_username", sa.String(64), nullable=False, server_default="svcadmin"),
    )


def downgrade() -> None:
    op.drop_column("deployment_templates", "local_admin_username")
