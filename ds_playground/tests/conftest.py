import contextlib
import fcntl
import json
import os
import signal
import sys
import time
from collections.abc import Callable, Iterator
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


@pytest.fixture
def evidence() -> Callable[..., None]:
    """Write an acceptance scenario's evidence record when the run asks for one (`make sat`)."""

    def write(
        scenario: str, slug: str, fixture: str, expected: str, actual: str, *limits: str
    ) -> None:
        if folder := os.environ.get("DSP_EVIDENCE"):
            platform = f"{sys.platform}-{os.uname().machine}"
            record = {
                "id": scenario,
                "sprint": 2,
                "os": platform,
                "fixture": fixture,
                "commit": os.environ.get("DSP_COMMIT", "unrecorded"),
                "expected": expected,
                "actual": actual,
                "outcome": "PASS",
                "limits": list(limits),
            }
            Path(folder).mkdir(parents=True, exist_ok=True)
            path = Path(folder) / f"{scenario}-{slug}-{platform}.json"
            path.write_text(json.dumps(record, indent=2) + "\n")

    return write


@pytest.fixture
def harness_stopped() -> Callable[[Path], bool]:
    """Wait up to ten seconds for the harness on a profile to exit and free its instance lock."""

    def check(profile: Path) -> bool:
        for _ in range(100):
            with (profile / "harness.lock").open("a") as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    time.sleep(0.1)
                else:
                    return True
        return False

    return check
