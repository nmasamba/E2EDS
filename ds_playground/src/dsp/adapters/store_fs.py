import os
from pathlib import Path

from dsp.contracts.canonical import file_digest
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext


class ContentStore:
    """Content-addressed files under a tenant namespace, with attempt-scoped staging beside them."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def staging(self, attempt: str) -> Path:
        """Return a fresh staging directory for one attempt; nothing in it is referenced yet."""
        path = self._root / "staging" / attempt
        path.mkdir(parents=True)
        return path

    def commit(self, ctx: TrustedContext, path: Path) -> str:
        """Move a staged file into the store atomically and return its digest."""
        identity = file_digest(path)
        target = self._target(ctx, identity)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(path, target)
        return identity

    def path(self, ctx: TrustedContext, digest: str) -> Path:
        """Return the stored file, or raise NOT_FOUND (also when it belongs to another tenant)."""
        target = self._target(ctx, digest)
        if not target.is_file():
            raise DspError(ErrorCode.NOT_FOUND, f"artifact {digest} not found")
        return target

    def _target(self, ctx: TrustedContext, digest: str) -> Path:
        return self._root / "cas" / ctx.tenant / digest.removeprefix("sha256:")
