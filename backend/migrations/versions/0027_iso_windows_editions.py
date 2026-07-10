"""iso_assets.windows_editions, deployment_templates.image_index

Revision ID: 0027
Revises: 0026
Create Date: 2026-07-09

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "iso_assets",
        sa.Column("windows_editions", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    # Default 1 preserves exactly today's behavior (hardcoded index 1,
    # typically Server Core on Microsoft's standard multi-edition media)
    # for every existing template; nothing changes until an operator
    # explicitly picks a different edition.
    op.add_column(
        "deployment_templates",
        sa.Column("image_index", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("deployment_templates", "image_index")
    op.drop_column("iso_assets", "windows_editions")
