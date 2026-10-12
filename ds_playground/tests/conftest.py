import contextlib
import fcntl
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import uvicorn

from dsp.harness import workspace
from dsp.harness.app import create_app

pytest_plugins = ["pytester"]
ROOT = Path(__file__).parents[1]


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
    """Write an acceptance scenario's evidence record when the run asks for one (`make sat`).

    ``outcome`` is PASS only when the run showed the whole scenario as the suite words it;
    a scenario with parts that cannot be exercised yet is INSUFFICIENT_EVIDENCE, with the reasons.
    """

    def write(
        scenario: str,
        slug: str,
        outcome: str,
        fixture: str,
        expected: str,
        actual: str,
        *limits: str,
        sprint: int = 2,
    ) -> None:
        if folder := os.environ.get("DSP_EVIDENCE"):
            platform = f"{sys.platform}-{os.uname().machine}"
            record = {
                "id": scenario,
                "sprint": sprint,
                "os": platform,
                "fixture": fixture,
                "commit": os.environ.get("DSP_COMMIT", "unrecorded"),
                "expected": expected,
                "actual": actual,
                "outcome": outcome,
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


class Clock:
    """The harness's clock in a test: real time plus an offset the test moves forward."""

    def __init__(self) -> None:
        self.offset = 0.0

    def __call__(self) -> str:
        """The harness's current time as RFC 3339."""
        return datetime.fromtimestamp(time.time() + self.offset, UTC).isoformat()

    def advance(self, seconds: float) -> None:
        """Move the harness's time forward, so leases run out without anyone waiting."""
        self.offset += seconds


@pytest.fixture
def harness(state_dir: Path) -> Iterator[tuple[httpx.Client, Clock]]:
    """A real harness served from this process on a loopback socket, on a clock the test moves.

    Worker processes find it through ``harness.json`` like any harness; the client it yields is
    the CLI's position (owner token, no Origin).
    """
    clock = Clock()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port, token = listener.getsockname()[1], secrets.token_urlsafe(16)
    (state_dir / "harness.json").write_text(json.dumps({"port": port, "token": token, "pid": 0}))
    app = create_app(token, port)
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    workspace.mount(app, state_dir, server, clock)
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    client = httpx.Client(
        base_url=f"http://127.0.0.1:{port}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    for _ in range(100):
        try:
            client.get("/v1/status").raise_for_status()
            break
        except httpx.HTTPError:
            time.sleep(0.05)
    yield client, clock
    server.should_exit = True
    thread.join(10)
    (state_dir / "harness.json").unlink()


@pytest.fixture
def worker(state_dir: Path) -> Iterator[Callable[..., subprocess.Popen[bytes]]]:
    """Start the test worker as a real process on the profile; every worker is reaped afterwards."""
    started: list[subprocess.Popen[bytes]] = []

    def start(job: str, name: str = "worker", heartbeat: float = 0.3) -> subprocess.Popen[bytes]:
        command = [sys.executable, "-m", "fixtures.worker", "--job", job, "--worker", name]
        command += ["--heartbeat-seconds", str(heartbeat)]
        process = subprocess.Popen(
            command, cwd=ROOT, env={**os.environ, "DSP_HOME": str(state_dir)}
        )
        started.append(process)
        return process

    yield start
    for process in started:
        process.kill()
        process.wait(10)
