import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PostInstallScript(BaseModel):
    name: str
    script_text: str


class ExtraVolume(BaseModel):
    label: str
    drive_letter: str
    size_mb: int


class FixedOsVolume(BaseModel):
    size_mb: int


class DiskLayoutJson(BaseModel):
    # 260 MB (not Microsoft's stated 100 MB absolute floor): a real
    # deployment failed Setup entirely at exactly 100 MB - "BCD: Failed
    # to add system store from file" while writing the boot
    # configuration store to the EFI System Partition, with zero
    # headroom to fall back on. Microsoft's own UEFI/GPT partitioning
    # guide already documents 100 MB as insufficient specifically on
    # Advanced Format 4K-native-sector drives ("the minimum size is
    # 260 MB, due to a limitation of the FAT32 file format"); this makes
    # that the hard floor for every layout instead of a UI-default
    # suggestion nothing actually enforced.
    efi_size_mb: int = Field(500, ge=260)
    msr_size_mb: int = Field(128, ge=16)
    # optional Windows RE tools partition placed between MSR and the OS
    # volume instead of at the end of the disk, so later expanding the OS
    # volume in a hypervisor is not blocked by a trailing recovery
    # partition. None omits it entirely (Windows Setup's own default
    # end-of-disk placement applies). 300 MB when set: Microsoft's own
    # documented floor for this partition type ("This partition must be
    # at least 300 MB").
    recovery_size_mb: int | None = Field(None, ge=300)
    os_volume: Literal["remaining"] | FixedOsVolume
    extra_volumes: list[ExtraVolume] = []


class DiskLayoutCreate(BaseModel):
    name: str
    layout: DiskLayoutJson
    post_install_scripts: list[PostInstallScript] = []


class DiskLayoutUpdate(BaseModel):
    name: str | None = None
    layout: DiskLayoutJson | None = None
    post_install_scripts: list[PostInstallScript] | None = None


class DiskLayoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID | None
    name: str
    layout_json: dict
    post_install_scripts: list[PostInstallScript]
