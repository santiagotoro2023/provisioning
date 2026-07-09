import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.template import DiskProvisioning, DomainJoinTiming, NetworkAdapterType
from app.schemas.disk_layout import DiskLayoutJson

# Windows reserves these local account names (the built-in Administrator
# and Guest accounts, plus the two accounts newer Windows 10/11 SKUs also
# ship); DeployCore actively disables the built-in Administrator, so a
# custom admin account named "Administrator" would collide with the very
# account being renamed away from.
_RESERVED_LOCAL_ACCOUNT_NAMES = {"administrator", "guest", "defaultaccount", "wdagutilityaccount"}


def _check_local_admin_username(cls, value: str) -> str:
    """Shared by both Create (required field) and Update (optional field,
    which wraps this itself and skips the call for None) below, matching
    Pydantic v2's documented pattern for reusing one validator function
    across models: https://docs.pydantic.dev/latest/concepts/validators/#reusable-validators"""
    if value.strip().lower() in _RESERVED_LOCAL_ACCOUNT_NAMES:
        raise ValueError(f'"{value}" is a reserved Windows account name, choose a different local admin username')
    if not value.strip():
        raise ValueError("local admin username cannot be blank")
    return value


class PostInstallScript(BaseModel):
    name: str
    script_text: str


class DeploymentTemplateCreate(BaseModel):
    name: str
    iso_asset_id: uuid.UUID | None = None
    disk_layout_id: uuid.UUID
    cpu_count: int
    cores_per_socket: int = 1
    ram_mb: int
    disk_size_gb: int
    disk_provisioning: DiskProvisioning = DiskProvisioning.THIN
    network_name: str
    network_adapter_type: NetworkAdapterType = NetworkAdapterType.VMXNET3
    vlan_id: int | None = None
    locale: str = "de-DE"
    timezone: str = "W. Europe Standard Time"
    keyboard_layout: str = "de-CH"
    local_admin_username: str = "svcadmin"
    local_admin_password: str
    domain_join_enabled: bool = False
    domain_fqdn: str | None = None
    domain_join_account: str | None = None
    domain_join_credential: str | None = None
    domain_target_ou: str | None = None
    domain_join_timing: DomainJoinTiming = DomainJoinTiming.ANSWER_FILE
    windows_features: list[str] = []
    post_install_scripts: list[PostInstallScript] = []

    _validate_local_admin_username = field_validator("local_admin_username")(_check_local_admin_username)


class DeploymentTemplateUpdate(BaseModel):
    name: str | None = None
    iso_asset_id: uuid.UUID | None = None
    disk_layout_id: uuid.UUID | None = None
    cpu_count: int | None = None
    cores_per_socket: int | None = None
    ram_mb: int | None = None
    disk_size_gb: int | None = None
    disk_provisioning: DiskProvisioning | None = None
    network_name: str | None = None
    network_adapter_type: NetworkAdapterType | None = None
    vlan_id: int | None = None
    locale: str | None = None
    timezone: str | None = None
    keyboard_layout: str | None = None
    local_admin_username: str | None = None
    local_admin_password: str | None = None
    domain_join_enabled: bool | None = None
    domain_fqdn: str | None = None
    domain_join_account: str | None = None
    domain_join_credential: str | None = None
    domain_target_ou: str | None = None
    domain_join_timing: DomainJoinTiming | None = None
    windows_features: list[str] | None = None
    post_install_scripts: list[PostInstallScript] | None = None

    @field_validator("local_admin_username")
    @classmethod
    def _validate_local_admin_username(cls, value: str | None) -> str | None:
        return value if value is None else _check_local_admin_username(cls, value)


class DeploymentTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID | None
    name: str
    iso_asset_id: uuid.UUID | None
    disk_layout_id: uuid.UUID
    cpu_count: int
    cores_per_socket: int
    ram_mb: int
    disk_size_gb: int
    disk_provisioning: DiskProvisioning
    network_name: str
    network_adapter_type: NetworkAdapterType
    vlan_id: int | None
    locale: str
    timezone: str
    keyboard_layout: str
    local_admin_username: str
    domain_join_enabled: bool
    domain_fqdn: str | None
    domain_join_account: str | None
    domain_target_ou: str | None
    domain_join_timing: DomainJoinTiming
    windows_features: list[str]
    post_install_scripts: list[PostInstallScript]


class TemplateExportDiskLayout(BaseModel):
    name: str
    layout: DiskLayoutJson


class TemplateExportIsoHint(BaseModel):
    filename: str
    kind: str


class DeploymentTemplateExport(BaseModel):
    """Credentials are deliberately omitted, an import always starts with
    a random placeholder password that must be replaced before the
    template is deployable. iso_hint is informational only: the ISO
    itself isn't portable, so import never sets iso_asset_id."""

    name: str
    disk_layout: TemplateExportDiskLayout
    iso_hint: TemplateExportIsoHint | None
    cpu_count: int
    cores_per_socket: int
    ram_mb: int
    disk_size_gb: int
    disk_provisioning: DiskProvisioning
    network_name: str
    network_adapter_type: NetworkAdapterType
    vlan_id: int | None
    locale: str
    timezone: str
    keyboard_layout: str
    local_admin_username: str
    domain_join_enabled: bool
    domain_fqdn: str | None
    domain_join_account: str | None
    domain_target_ou: str | None
    domain_join_timing: DomainJoinTiming
    windows_features: list[str]
    post_install_scripts: list[PostInstallScript]


class DeploymentTemplateImport(BaseModel):
    name: str
    disk_layout: TemplateExportDiskLayout
    cpu_count: int
    cores_per_socket: int = 1
    ram_mb: int
    disk_size_gb: int
    disk_provisioning: DiskProvisioning = DiskProvisioning.THIN
    network_name: str
    network_adapter_type: NetworkAdapterType = NetworkAdapterType.VMXNET3
    vlan_id: int | None = None
    locale: str = "de-DE"
    timezone: str = "W. Europe Standard Time"
    keyboard_layout: str = "de-CH"
    local_admin_username: str = "svcadmin"
    domain_join_enabled: bool = False
    domain_fqdn: str | None = None
    domain_join_account: str | None = None
    domain_target_ou: str | None = None
    domain_join_timing: DomainJoinTiming = DomainJoinTiming.ANSWER_FILE
    windows_features: list[str] = []
    post_install_scripts: list[PostInstallScript] = []

    _validate_local_admin_username = field_validator("local_admin_username")(_check_local_admin_username)
