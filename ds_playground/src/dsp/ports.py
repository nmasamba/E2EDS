from collections.abc import Callable, Mapping, Sequence
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
        objects: Sequence[dict[str, Any] | tuple[str, dict[str, Any]]] = (),
    ) -> None:
        """Append one event and its immutable objects atomically, or raise.

        An object is stored under its ``type``; a suite object that has none is given as
        ``(kind, object)``.
        """

    def get(self, ctx: TrustedContext, kind: str, object_id: str, revision: str) -> dict[str, Any]:
        """Return one immutable object revision, or raise NOT_FOUND."""

    def current(self, ctx: TrustedContext, kind: str) -> list[dict[str, Any]]:
        """Return the latest revision of every object of one kind in this tenant."""

    def latest(self, ctx: TrustedContext, kind: str, object_id: str) -> dict[str, Any] | None:
        """Return the newest revision of one object, or None when the tenant has none."""

    def seq(self, ctx: TrustedContext, aggregate: str) -> int:
        """Return an aggregate's current sequence: what ``commit`` must be told to expect."""


class Store(Protocol):
    """Content-addressed artifact storage with attempt-scoped staging."""

    def staging(self, attempt: str) -> Path:
        """Return a fresh staging directory for one attempt."""

    def commit(self, ctx: TrustedContext, path: Path) -> str:
        """Move a staged file into the store and return its digest."""

    def path(self, ctx: TrustedContext, digest: str) -> Path:
        """Return the stored file for a digest."""

    def attempts(self) -> list[Path]:
        """Return the staging directories that exist now."""

    def discard(self, staging: Path) -> None:
        """Delete one staging directory and everything left in it."""


class Runner(Protocol):
    """Runs one CodeTask confined by the OS sandbox and reports what happened (B26)."""

    def run(
        self,
        task: dict[str, Any],
        source: Path,
        inputs: Mapping[str, Path],
        work: Path,
        proceed: Callable[[], bool] = lambda: True,
    ) -> dict[str, Any]:
        """Run the task on its source and declared inputs in the fresh attempt directory ``work``.

        ``proceed`` is asked as the task runs; False stops it (failure kind ``stopped``). Return
        the outcome, the failure's kind and message, and the declared outputs, each staged under
        ``work/out`` with the digest and size taken here: nothing the task wrote is trusted.
        """

    def release(self, work: Path) -> None:
        """Release what a run set up in ``work`` and may have left behind, as after a crash."""


class Exporter(Protocol):
    """Staged, verified export into a new version directory (D23)."""

    def stage(self, root: Path, files: Mapping[str, Path], staging_id: str) -> Path:
        """Copy files into a labelled staging area under the destination."""

    def commit_staged(self, root: Path, staging: Path, digests: Mapping[str, str]) -> str:
        """Verify the staged files and publish them as a new version; return its name."""


class SecretStore(Protocol):
    """The OS secret store behind ``secret://local/<account>``: never a file in the repo or argv."""

    def get(self, account: str) -> str | None:
        """Return the secret stored under this account, or None when there is none."""

    def put(self, account: str, value: str) -> None:
        """Store the secret under this account, replacing any earlier value."""


class ModelGateway(Protocol):
    """The one door to a model (B24): a bounded chat completion whose tools are typed schemas.

    Nothing that comes back is trusted: the caller validates every tool call before it acts.
    """

    def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int,
        deadline: float,
        seed: int,
        temperature: float,
    ) -> dict[str, Any]:
        """Return the model's next message (text or tool calls) and its token usage, or raise.

        ``deadline`` is seconds for this one call (D17: 300 s); past it the generation is
        stopped and ASSISTANT_UNAVAILABLE is raised.
        """

    def count(self, text: str) -> int:
        """Return how many tokens the text is for this model, to bound the input (D17)."""


class ModelServer(ModelGateway, Protocol):
    """A supervised local model server: verified, confined, started, watched and stopped."""

    def start(self, proceed: Callable[[], bool] = lambda: True) -> dict[str, Any]:
        """Verify the model, start the server confined and wait for readiness; raise if not.

        ``proceed`` is asked while the model loads; False gives up (the harness is quitting).

        Return what was observed: the model's and binary's digests, the chat template's
        digest and the seconds the load took. Readiness is the health endpoint plus a typed
        tool-response probe; an endpoint answering HTTP is not readiness.
        """

    def stop(self) -> None:
        """Stop the server and release what ``start`` set up."""

    def alive(self) -> bool:
        """True while the server process runs and is within its memory limit."""
