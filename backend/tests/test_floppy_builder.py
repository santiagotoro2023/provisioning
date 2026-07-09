import asyncio
import uuid
from pathlib import Path

import pytest

from app.config import get_settings
from app.services import floppy_builder


class _FakeDriver:
    def __init__(self):
        self.uploaded_from = None

    async def upload_iso_to_datastore(self, local_path: str, remote_name: str) -> str:
        # capture whether the local floppy image actually existed at upload time
        self.uploaded_from = local_path if Path(local_path).exists() else None
        return f"remote/{remote_name}"


class _FakeDeployment:
    def __init__(self):
        self.id = uuid.uuid4()


@pytest.fixture(autouse=True)
def _iso_build_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("ISO_BUILD_TMP", str(tmp_path))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _temp_dir(tmp_path: Path, deployment: _FakeDeployment) -> Path:
    return tmp_path / f"{deployment.id}-floppy"


async def test_temp_dir_removed_after_successful_build(tmp_path):
    driver = _FakeDriver()
    deployment = _FakeDeployment()

    remote_path = await floppy_builder.build_and_upload_answer_floppy(driver, deployment, "<unattend></unattend>")

    assert remote_path == f"remote/{deployment.id}-answer.flp"
    assert driver.uploaded_from is not None  # the floppy image existed locally when uploaded
    assert not _temp_dir(tmp_path, deployment).exists()


async def test_temp_dir_removed_after_mformat_failure(tmp_path, monkeypatch):
    class _FakeProcess:
        returncode = 1

        async def communicate(self):
            return b"", b"mformat: command failed"

    async def _fake_exec(*args, **kwargs):
        return _FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_exec)

    driver = _FakeDriver()
    deployment = _FakeDeployment()

    with pytest.raises(RuntimeError, match="mformat failed"):
        await floppy_builder.build_and_upload_answer_floppy(driver, deployment, "<unattend></unattend>")

    assert not _temp_dir(tmp_path, deployment).exists()


async def test_temp_dir_removed_after_mcopy_failure(tmp_path, monkeypatch):
    calls = []

    class _FakeProcess:
        def __init__(self, returncode, stderr):
            self.returncode = returncode
            self._stderr = stderr

        async def communicate(self):
            return b"", self._stderr

    async def _fake_exec(program, *args, **kwargs):
        calls.append(program)
        if program == "mformat":
            return _FakeProcess(0, b"")
        return _FakeProcess(1, b"mcopy: command failed")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _fake_exec)

    driver = _FakeDriver()
    deployment = _FakeDeployment()

    with pytest.raises(RuntimeError, match="mcopy failed"):
        await floppy_builder.build_and_upload_answer_floppy(driver, deployment, "<unattend></unattend>")

    assert calls == ["mformat", "mcopy"]
    assert not _temp_dir(tmp_path, deployment).exists()
