import json
import os
import signal
from collections.abc import Iterator
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]


@pytest.fixture
def state_dir(tmp_path: Path) -> Iterator[Path]:
    """A profile directory whose harness, if one was started, is stopped afterwards."""
    yield tmp_path
    state = tmp_path / "harness.json"
    pid = json.loads(state.read_text()).get("pid") if state.exists() else None
    if pid:
        os.kill(pid, signal.SIGTERM)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Fail the run on any skipped or xfailed test: a skip looks like a pass (AGENTS.md §6)."""
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    hidden = [kind for kind in ("skipped", "xfailed", "xpassed") if reporter.stats.get(kind)]
    if hidden and exitstatus == 0:
        reporter.write_line(
            f"FAILED: tests were {', '.join(hidden)}; skips are not allowed", red=True
        )
        session.exitstatus = 1
