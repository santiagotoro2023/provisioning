import uuid

from pydantic import BaseModel, ConfigDict

from app.models.app_asset import AppKind
from app.models.iso_asset import UploadStatus


class AppAssetCreate(BaseModel):
    name: str
    filename: str
    kind: AppKind
    default_install_args: str = ""


class AppAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID | None
    kind: AppKind
    name: str
    filename: str
    checksum_sha256: str | None
    size_bytes: int
    default_install_args: str
    upload_status: UploadStatus
