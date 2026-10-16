"""The OS secret store (SecretPort): the macOS keychain, or Linux Secret Service with a file.

The service name is fixed (``dev.dsp.assistant``); the account is the last part of a
``secret://local/<account>`` reference. No secret ever passes through a child's arguments or
environment: the keychain is read through the Security framework in this process, and
``secret-tool`` reads the value from its standard input. Where Linux has no Secret Service (a
container, CI), the value lives in an owner-only file under the state directory.
"""

import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dsp.contracts.errors import DspError, ErrorCode

SERVICE = "dev.dsp.assistant"
NOT_FOUND, DUPLICATE = -25300, -25299  # errSecItemNotFound, errSecDuplicateItem


class Keychain:
    """macOS: generic passwords in the login keychain, or in the keychain file a test created."""

    def __init__(self, path: Path | None = None, password: str | None = None) -> None:
        self.security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
        self.keychain = ctypes.c_void_p()
        if path is not None:
            if self.security.SecKeychainOpen(bytes(path), ctypes.byref(self.keychain)):
                raise DspError(ErrorCode.DEPENDENCY_UNAVAILABLE, "the keychain could not be opened")
            if password is not None:
                secret = password.encode()
                self.security.SecKeychainUnlock(self.keychain, len(secret), secret, True)

    def _find(self, account: str) -> tuple[int, bytes, ctypes.c_void_p]:
        length, data, item = ctypes.c_uint32(), ctypes.c_void_p(), ctypes.c_void_p()
        name = account.encode()
        status: int = self.security.SecKeychainFindGenericPassword(
            self.keychain,
            len(SERVICE),
            SERVICE.encode(),
            len(name),
            name,
            ctypes.byref(length),
            ctypes.byref(data),
            ctypes.byref(item),
        )
        found = ctypes.string_at(data, length.value) if status == 0 else b""
        if status == 0:
            self.security.SecKeychainItemFreeContent(None, data)
        return status, found, item

    def get(self, account: str) -> str | None:
        """Return the stored secret, or None; any other keychain answer is a refusal."""
        status, found, item = self._find(account)
        if status == NOT_FOUND:
            return None
        if status:
            raise DspError(ErrorCode.DEPENDENCY_UNAVAILABLE, f"the keychain answered {status}")
        self.security.CFRelease(item)
        return found.decode()

    def put(self, account: str, value: str) -> None:
        """Add the secret, or replace the one stored under this account."""
        name, secret = account.encode(), value.encode()
        status: int = self.security.SecKeychainAddGenericPassword(
            self.keychain,
            len(SERVICE),
            SERVICE.encode(),
            len(name),
            name,
            len(secret),
            secret,
            None,
        )
        if status == DUPLICATE:
            status, _, item = self._find(account)
            if status == 0:
                status = self.security.SecKeychainItemModifyAttributesAndData(
                    item, None, len(secret), secret
                )
                self.security.CFRelease(item)
        if status:
            raise DspError(ErrorCode.DEPENDENCY_UNAVAILABLE, f"the keychain answered {status}")


class SecretService:
    """Linux: ``secret-tool`` (the Secret Service), else an owner-only file under the state dir."""

    def __init__(self, fallback: Path) -> None:
        self.tool = shutil.which("secret-tool")
        self.fallback = fallback

    def _file(self, account: str) -> Path:
        self.fallback.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.fallback.stat().st_mode & 0o077:
            raise DspError(ErrorCode.FORBIDDEN, "the secrets folder is not the owner's alone")
        return self.fallback / account

    def get(self, account: str) -> str | None:
        """Return the stored secret, or None when neither store has it."""
        if self.tool:
            found = subprocess.run(
                [self.tool, "lookup", "service", SERVICE, "account", account],
                capture_output=True,
                check=False,
                timeout=30,
            )
            if found.returncode == 0:
                return found.stdout.decode()
            if found.returncode == 1 and not found.stderr:  # the service answered: no such item
                return None
        path = self._file(account)
        return path.read_text() if path.is_file() else None

    def put(self, account: str, value: str) -> None:
        """Store the secret in the Secret Service, else in the owner-only file."""
        if self.tool:
            stored = subprocess.run(
                [self.tool, "store", "--label=dsp", "service", SERVICE, "account", account],
                input=value.encode(),
                capture_output=True,
                check=False,
                timeout=30,
            )
            if stored.returncode == 0:
                return
        path = self._file(account)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            handle.write(value)


def local(state_dir: Path) -> Keychain | SecretService:
    """The owner's secret store on this OS; the one place the OS chooses the adapter."""
    if sys.platform == "darwin":
        return Keychain()
    return SecretService(state_dir / "secrets")
