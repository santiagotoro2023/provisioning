"""deployment_templates.app_installs, deployments.app_asset_access_token

Revision ID: 0025
Revises: 0024
Create Date: 2026-07-09

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "deployment_templates",
        sa.Column("app_installs", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "deployments",
        sa.Column("app_asset_access_token", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("deployments", "app_asset_access_token")
    op.drop_column("deployment_templates", "app_installs")
