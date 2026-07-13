"""disk_layouts: bump undersized efi/msr partitions to the new safe minimums

Existing rows were seeded (or hand-created before validation existed) with
efi_size_mb as low as Microsoft's absolute floor of 100 MB, which has caused
real Windows Setup failures ("BCD: Failed to add system store") with no
headroom on 4K-native-sector drives. The schema now enforces a 260 MB floor
for new writes; this is a one-time data fix so already-provisioned
instances aren't stuck on the old unsafe values with no way to edit them.

Revision ID: 0035
Revises: 0034
Create Date: 2026-07-13

"""
import json

from alembic import op
from sqlalchemy import text

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None

EFI_FLOOR = 260
EFI_SAFE = 500
MSR_FLOOR = 16
MSR_SAFE = 128


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(text("SELECT id, layout_json FROM disk_layouts")).fetchall()
    for row_id, layout_json in rows:
        efi = layout_json.get("efi_size_mb")
        msr = layout_json.get("msr_size_mb")
        changed = False
        if efi is not None and efi < EFI_FLOOR:
            layout_json["efi_size_mb"] = EFI_SAFE
            changed = True
        if msr is not None and msr < MSR_FLOOR:
            layout_json["msr_size_mb"] = MSR_SAFE
            changed = True
        if changed:
            conn.execute(
                text("UPDATE disk_layouts SET layout_json = :layout_json::jsonb WHERE id = :id"),
                {"layout_json": json.dumps(layout_json), "id": row_id},
            )


def downgrade() -> None:
    pass
