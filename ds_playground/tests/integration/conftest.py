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
