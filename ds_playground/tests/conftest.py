import contextlib
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
    profile = tmp_path / "home"
    profile.mkdir()
    yield profile
    state = profile / "harness.json"
    pid = json.loads(state.read_text()).get("pid") if state.exists() else None
    if pid:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGTERM)


@pytest.fixture
def home(state_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """``DSP_HOME`` pointed at a temporary profile, so the CLI starts its harness there."""
    monkeypatch.setenv("DSP_HOME", str(state_dir))
    return state_dir


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Fail the run on any skipped or xfailed test: a skip looks like a pass (AGENTS.md §6)."""
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    hidden = [kind for kind in ("skipped", "xfailed", "xpassed") if reporter.stats.get(kind)]
    if hidden and exitstatus == 0:
        reporter.write_line(
            f"FAILED: tests were {', '.join(hidden)}; skips are not allowed", red=True
        )
        session.exitstatus = 1
