import asyncio
import shutil
from pathlib import Path

from app.config import get_settings
from app.hypervisors.base import HypervisorDriver
from app.models.deployment import Deployment

FLOPPY_SIZE_KB = 1440  # standard 1.44 MB, plenty for one XML file


async def build_and_upload_answer_floppy(
    driver: HypervisorDriver, deployment: Deployment, rendered_xml: str
) -> str:
    """Windows Setup's very first implicit answer-file scan (the one that
    decides whether to show the interactive language/time/keyboard
    screen) runs before its full driver stack is up, and empirically
    doesn't reliably see a second CD-ROM drive at that point, even though
    everything after it (disk partitioning, EULA, the rest of the
    windowsPE pass) does pick it up fine once the full environment
    loads. A floppy is checked earlier and with higher precedence
    (Microsoft's own implicit-search-order docs: read/write removable
    media before read-only removable media), which is why this, not a
    second CD-ROM, is what's used for the answer file, this is the
    traditional, most compatible way to deliver one.

    Builds a blank 1.44 MB FAT12 image with mtools (no loop-mount/root
    needed) containing just autounattend.xml at its root, uploads it to
    the hypervisor datastore, and always removes the local temp dir
    before returning or raising. The remote copy (which contains a
    plaintext local admin password) is the caller's responsibility to
    delete once the deployment finishes, success or fail.
    """
    temp_dir = Path(get_settings().iso_build_tmp) / f"{deployment.id}-floppy"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        xml_path = temp_dir / "autounattend.xml"
        xml_path.write_text(rendered_xml, encoding="utf-8")
        floppy_path = temp_dir / f"{deployment.id}-answer.flp"

        format_proc = await asyncio.create_subprocess_exec(
            "mformat", "-f", str(FLOPPY_SIZE_KB), "-C", "-i", str(floppy_path),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, format_stderr = await format_proc.communicate()
        if format_proc.returncode != 0:
            raise RuntimeError(f"mformat failed: {format_stderr.decode(errors='replace')}")

        copy_proc = await asyncio.create_subprocess_exec(
            "mcopy", "-i", str(floppy_path), str(xml_path), "::autounattend.xml",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, copy_stderr = await copy_proc.communicate()
        if copy_proc.returncode != 0:
            raise RuntimeError(f"mcopy failed: {copy_stderr.decode(errors='replace')}")

        remote_name = f"{deployment.id}-answer.flp"
        return await driver.upload_iso_to_datastore(str(floppy_path), remote_name)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
