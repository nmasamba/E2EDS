"""Fixtures the live model tests share: one real server per session, lent to each harness."""

from collections.abc import Iterator
from typing import Any

import pytest


def revive(server: Any) -> dict[str, Any]:
    """The session's server, started again for real if an earlier test stopped it (D24's quit)."""
    if server.process is not None and server.process.poll() is not None:
        server.observed = server.start()
    found: dict[str, Any] = dict(server.observed)
    return found


class Shared:
    """The session's started server lent to one harness: its lifecycle stays with the session."""

    def __init__(self, server: Any) -> None:
        self.server = server

    def start(self, proceed: Any = None) -> dict[str, Any]:
        """Already started: hand back what the session observed; revived first if it was stopped."""
        return revive(self.server)

    def stop(self) -> None:
        """The session stops it, not the harness."""

    def alive(self) -> bool:
        """As the real server is."""
        return bool(self.server.alive())

    def complete(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """The real server's completion."""
        found: dict[str, Any] = self.server.complete(*args, **kwargs)
        return found

    def count(self, text: str) -> int:
        """The real server's tokenizer."""
        return int(self.server.count(text))


@pytest.fixture(scope="session")
def model_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Any]:
    """One started real model server for the whole session: the load is measured once, here."""
    from tests.integration.test_live_gateway import make

    adapter = make(tmp_path_factory.mktemp("assistant-home"))
    adapter.observed = adapter.start()  # kept for the record
    yield adapter
    adapter.stop()


class Lent(Shared):
    """The session's server lent with its real stop too: a quit or a deadline really stops it."""

    def stop(self) -> None:
        """The harness's quit, or a deadline, stops the real server."""
        self.server.stop()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """The live failure tests end the session's server, so they run after the other live tests."""
    items.sort(key=lambda item: item.module.__name__.endswith("test_live_failure"))  # type: ignore[attr-defined]
