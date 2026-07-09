"""app_assets

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-09

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

app_kind_enum = postgresql.ENUM("msi", "exe", name="app_kind", create_type=False)
# upload_status already exists (0004_iso_assets); reused as-is here, not
# created or dropped by this migration, iso_assets still depends on it.
upload_status_enum = postgresql.ENUM(
    "pending", "uploading", "complete", "failed", name="upload_status", create_type=False
)


def upgrade() -> None:
    app_kind_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "app_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("kind", app_kind_enum, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("default_install_args", sa.String(1024), nullable=False, server_default=""),
        sa.Column("upload_status", upload_status_enum, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_app_assets_org_id", "app_assets", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_app_assets_org_id", table_name="app_assets")
    op.drop_table("app_assets")
    app_kind_enum.drop(op.get_bind(), checkfirst=True)
