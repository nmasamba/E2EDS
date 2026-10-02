from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from dsp.contracts.errors import TrustedContext


class Ledger(Protocol):
    """The authoritative, append-only record of objects and events."""

    def commit(
        self,
        ctx: TrustedContext,
        aggregate: str,
        expected_seq: int,
        event_id: str,
        event_type: str,
        body: dict[str, Any],
        objects: Sequence[dict[str, Any]] = (),
    ) -> None:
        """Append one event and its immutable objects atomically, or raise."""

    def current(self, ctx: TrustedContext, kind: str) -> list[dict[str, Any]]:
        """Return the latest revision of every object of one kind in this tenant."""


class Store(Protocol):
    """Content-addressed artifact storage with attempt-scoped staging."""

    def staging(self, attempt: str) -> Path:
        """Return a fresh staging directory for one attempt."""

    def commit(self, ctx: TrustedContext, path: Path) -> str:
        """Move a staged file into the store and return its digest."""

    def path(self, ctx: TrustedContext, digest: str) -> Path:
        """Return the stored file for a digest."""


class Exporter(Protocol):
    """Staged, verified export into a new version directory (D23)."""

    def stage(self, root: Path, files: Mapping[str, Path], staging_id: str) -> Path:
        """Copy files into a labelled staging area under the destination."""

    def commit_staged(self, root: Path, staging: Path, digests: Mapping[str, str]) -> str:
        """Verify the staged files and publish them as a new version; return its name."""
