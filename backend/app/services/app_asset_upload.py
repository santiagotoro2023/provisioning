import hashlib
import shutil
import uuid
from pathlib import Path

from app.config import get_settings

# Same chunked-upload approach as iso_upload.py (see its docstring): the
# client sends 8 MB chunks sequentially, the server appends them, and a
# finalize call assembles the file and checksums it. No ISO-remastering
# equivalent step here, an installer's silent-install behavior is
# controlled entirely by the install_args a template passes it, not
# anything DeployCore rewrites in the file itself.


def _temp_path(app_id: uuid.UUID) -> Path:
    return Path(get_settings().app_asset_build_tmp) / f"upload-{app_id}.part"


def append_chunk(app_id: uuid.UUID, chunk: bytes) -> None:
    path = _temp_path(app_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as fh:
        fh.write(chunk)


def finalize(app_id: uuid.UUID, filename: str) -> tuple[str, str, int]:
    """Moves the assembled temp upload into permanent app asset storage.
    Returns (storage_path, checksum_sha256, size_bytes)."""
    src = _temp_path(app_id)
    dest_dir = Path(get_settings().app_asset_storage_path)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{app_id}-{filename}"
    shutil.move(str(src), str(dest))

    sha256 = hashlib.sha256()
    with open(dest, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            sha256.update(block)
    size_bytes = dest.stat().st_size
    return str(dest), sha256.hexdigest(), size_bytes
