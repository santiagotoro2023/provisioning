import logging
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger(__name__)

# A Windows Server install ISO's install.wim (or, less commonly for
# volume-license media, install.esd) holds several editions in one file,
# e.g. Server Core and Desktop Experience for both Standard and
# Datacenter, each addressed by a numeric /IMAGE/INDEX in the answer
# file. autounattend_base.xml.j2 used to hardcode index 1, which on the
# standard Microsoft image ordering is Server Core, not what most people
# mean by "install Windows Server" by default. Detecting the real list
# once at upload time (rather than guessing a fixed index that varies by
# ISO) lets template creation offer an actual dropdown instead.
_INSTALL_IMAGE_GLOB = "[iI][nN][sS][tT][aA][lL][lL].[wW][iI][mM]"
_INSTALL_ESD_GLOB = "[iI][nN][sS][tT][aA][lL][lL].[eE][sS][dD]"


def _run(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{args[0]} failed: {result.stderr[-2000:]}")
    return result.stdout


def _find_path(iso_path: Path, name_glob: str) -> str | None:
    stdout = _run(["xorriso", "-indev", str(iso_path), "-find", "/", "-name", name_glob])
    for line in stdout.splitlines():
        line = line.strip().strip("'")
        if line.startswith("/"):
            return line
    return None


def detect_editions(iso_path: Path) -> list[dict]:
    """Best-effort: returns [] on anything unexpected (no install.wim/.esd
    found, wimlib-imagex missing or fails, XML doesn't parse, ...) rather
    than raising, an ISO that isn't laid out the way Microsoft's own
    Windows Server media is just doesn't get a dropdown, the template form
    falls back to a plain index field instead of losing the upload."""
    try:
        wim_path = _find_path(iso_path, _INSTALL_IMAGE_GLOB) or _find_path(iso_path, _INSTALL_ESD_GLOB)
        if wim_path is None:
            logger.info("windows_edition_detect: no install.wim/install.esd found in %s", iso_path)
            return []

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            local_wim = tmp_dir / "install.wim"
            # osirrox extraction, read-only against the ISO, never touches
            # it: unrelated to iso_remaster.py's in-place boot-prompt patch.
            _run(["xorriso", "-osirrox", "on", "-indev", str(iso_path), "-extract", wim_path, str(local_wim)])

            xml_path = tmp_dir / "images.xml"
            _run(["wimlib-imagex", "info", str(local_wim), "--extract-xml", str(xml_path)])
            # WIM's embedded metadata XML is UTF-16 (with a BOM), not UTF-8.
            root = ET.fromstring(xml_path.read_bytes().decode("utf-16"))

        editions = []
        for image in root.findall("IMAGE"):
            index = image.get("INDEX")
            if index is None:
                continue
            editions.append({
                "index": int(index),
                "name": image.findtext("NAME") or "",
                "description": image.findtext("DESCRIPTION") or "",
            })
        return editions
    except Exception:  # noqa: BLE001 - best-effort, see docstring
        logger.exception("windows_edition_detect: failed to detect editions in %s", iso_path)
        return []
