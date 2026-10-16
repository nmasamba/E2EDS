"""Fixtures the live model tests share: one real server per session, lent to each harness."""

from collections.abc import Iterator
from typing import Any

import pytest


class Shared:
    """The session's started server lent to one harness: its lifecycle stays with the session."""

    def __init__(self, server: Any) -> None:
        self.server = server

    def start(self, proceed: Any = None) -> dict[str, Any]:
        """Already started: hand back what the session observed."""
        return dict(self.server.observed)

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
    """The session's server lent with its real stop, and restarted for real once it is dead."""

    def start(self, proceed: Any = None) -> dict[str, Any]:
        """Already started: hand back what was observed; after a death, start it again for real."""
        if self.server.process is not None and self.server.process.poll() is not None:
            self.server.observed = self.server.start(proceed or (lambda: True))
        return dict(self.server.observed)

    def stop(self) -> None:
        """The harness's quit, or a deadline, stops the real server."""
        self.server.stop()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """The live failure tests end the session's server, so they run after the other live tests."""
    items.sort(key=lambda item: item.module.__name__.endswith("test_live_failure"))  # type: ignore[attr-defined]
