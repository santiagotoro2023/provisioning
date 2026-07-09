"""deployment_templates: cores_per_socket, disk_provisioning, network_adapter_type

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-10

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

disk_provisioning_enum = postgresql.ENUM(
    "thin", "thick_lazy_zeroed", "thick_eager_zeroed", name="disk_provisioning", create_type=False
)
network_adapter_type_enum = postgresql.ENUM(
    "vmxnet3", "e1000", "e1000e", name="network_adapter_type", create_type=False
)


def upgrade() -> None:
    disk_provisioning_enum.create(op.get_bind(), checkfirst=True)
    network_adapter_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "deployment_templates",
        sa.Column("cores_per_socket", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "deployment_templates",
        sa.Column("disk_provisioning", disk_provisioning_enum, nullable=False, server_default="thin"),
    )
    op.add_column(
        "deployment_templates",
        sa.Column("network_adapter_type", network_adapter_type_enum, nullable=False, server_default="vmxnet3"),
    )


def downgrade() -> None:
    op.drop_column("deployment_templates", "network_adapter_type")
    op.drop_column("deployment_templates", "disk_provisioning")
    op.drop_column("deployment_templates", "cores_per_socket")
    network_adapter_type_enum.drop(op.get_bind(), checkfirst=True)
    disk_provisioning_enum.drop(op.get_bind(), checkfirst=True)
