"""The secret store (SecretPort) on this OS, on a throwaway keychain or an owner-only file."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from dsp.adapters import secrets
from dsp.contracts.errors import DspError, ErrorCode


def store(tmp_path: Path) -> secrets.Keychain | secrets.SecretService:
    """The OS's adapter on a store that is not the owner's: a keychain file made here, or a file."""
    if sys.platform != "darwin":
        return secrets.SecretService(tmp_path / "secrets")
    keychain = tmp_path / "test.keychain-db"
    subprocess.run(
        ["/usr/bin/security", "create-keychain", "-p", "test-password", str(keychain)], check=True
    )
    return secrets.Keychain(keychain, "test-password")


def test_r16_a_secret_is_stored_read_back_replaced_and_absent_when_never_stored(
    tmp_path: Path,
) -> None:
    """R16, C23: get, put, replace and a missing account, through the OS's own store."""
    adapter = store(tmp_path)
    assert adapter.get("assistant-api-key") is None
    adapter.put("assistant-api-key", "first-value")
    assert adapter.get("assistant-api-key") == "first-value"
    adapter.put("assistant-api-key", "second-value")
    assert adapter.get("assistant-api-key") == "second-value"
    assert adapter.get("huggingface") is None
    assert "first-value" not in str(tmp_path.glob("*"))


def test_r16_without_a_secret_service_the_fallback_is_an_owner_only_file(tmp_path: Path) -> None:
    """R16: with no secret-tool the value lives in a 0600 file under a 0700 folder."""
    adapter = secrets.SecretService(tmp_path / "secrets")
    adapter.tool = None
    adapter.put("anthropic", "value")
    path = tmp_path / "secrets" / "anthropic"
    assert path.read_text() == "value"
    assert (path.stat().st_mode & 0o777, path.parent.stat().st_mode & 0o777) == (0o600, 0o700)
    assert adapter.get("anthropic") == "value"
    os.chmod(path.parent, 0o755)
    with pytest.raises(DspError) as refused:
        adapter.get("anthropic")
    assert refused.value.code is ErrorCode.FORBIDDEN


def test_r16_the_local_store_is_the_os_s_own() -> None:
    """R16: the one place the OS chooses the adapter."""
    chosen = secrets.local(Path("/nowhere"))
    expected = secrets.Keychain if sys.platform == "darwin" else secrets.SecretService
    assert isinstance(chosen, expected)
