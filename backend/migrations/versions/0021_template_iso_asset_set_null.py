"""deployment_templates.iso_asset_id: ON DELETE SET NULL

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-09

"""
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

_CONSTRAINT = "deployment_templates_iso_asset_id_fkey"


def upgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "deployment_templates", type_="foreignkey")
    op.create_foreign_key(
        _CONSTRAINT, "deployment_templates", "iso_assets", ["iso_asset_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "deployment_templates", type_="foreignkey")
    op.create_foreign_key(_CONSTRAINT, "deployment_templates", "iso_assets", ["iso_asset_id"], ["id"])
