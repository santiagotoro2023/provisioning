import uuid

from pydantic import BaseModel, ConfigDict

from app.models.iso_asset import IsoKind, UploadStatus


class IsoAssetCreate(BaseModel):
    filename: str
    kind: IsoKind


class WindowsEditionInfo(BaseModel):
    index: int
    name: str
    description: str
    # Derived from the WIM's own FLAGS metadata (falls back to scanning
    # name/description for "core" if FLAGS is missing): True for Desktop
    # Experience editions (has a GUI), False for Server Core ones.
    has_gui: bool


class IsoAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID | None
    kind: IsoKind
    filename: str
    checksum_sha256: str | None
    size_bytes: int
    upload_status: UploadStatus
    windows_editions: list[WindowsEditionInfo]
