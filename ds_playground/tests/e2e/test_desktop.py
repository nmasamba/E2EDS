"""Desktop end to end against the bundle `make desktop-build` produced. Run by `make e2e`."""

import json
import os
import re
import signal
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Iterator
from importlib.metadata import version
from pathlib import Path

import httpx
import pytest

from dsp.application.packs import verify_pack
from fixtures.operations import write_orders

pytestmark = pytest.mark.desktop

ROOT = Path(__file__).parents[2]
BUNDLE = ROOT / "desktop/src-tauri/target/release/bundle"
LINUX = sys.platform != "darwin"


def eventually[T](probe: Callable[[], T]) -> T:
    """Return the first result ``probe`` gives without failing; give up after a minute."""
    deadline = time.monotonic() + 60
    while True:
        try:
            return probe()
        except (OSError, ValueError, KeyError, AssertionError, httpx.HTTPError):
            if time.monotonic() > deadline:
                raise
            time.sleep(0.2)


def harness(state_dir: Path) -> httpx.Client:
    """Return a client, with the owner's token, for the harness that answers on ``state_dir``."""
    state = json.loads((state_dir / "harness.json").read_text())
    client = httpx.Client(
        base_url=f"http://127.0.0.1:{state['port']}",
        headers={"Authorization": f"Bearer {state['token']}"},
        timeout=60,
    )
    client.get("/v1/status").raise_for_status()
    return client


def xdotool(*arguments: str) -> str:
    """Run one xdotool command against the virtual display and return what it printed."""
    done = subprocess.run(
        ["xdotool", *arguments], check=True, capture_output=True, text=True, timeout=60
    )
    return done.stdout


@pytest.fixture(scope="module")
def binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The built app's executable: inside the .app on macOS, unpacked from the deb on Linux."""
    if not LINUX:
        (found,) = BUNDLE.glob("macos/*.app/Contents/MacOS/dsp-desktop")
        return found
    (deb,) = BUNDLE.glob("deb/*.deb")
    installed = tmp_path_factory.mktemp("deb")
    subprocess.run(["dpkg-deb", "--extract", deb, installed], check=True)
    return installed / "usr/bin/dsp-desktop"


@pytest.fixture
def launch(binary: Path, state_dir: Path) -> Iterator[Callable[[], subprocess.Popen[bytes]]]:
    """Start the built app on the temporary profile; every app started is stopped afterwards."""
    started: list[subprocess.Popen[bytes]] = []

    def start() -> subprocess.Popen[bytes]:
        app = subprocess.Popen([binary], env={**os.environ, "DSP_HOME": str(state_dir)})
        started.append(app)
        return app

    yield start
    for app in started:
        app.kill()
        app.wait(10)


def press(keys: str) -> None:
    """Send a key combination to the app's main window through the window manager."""
    window = xdotool("search", "--sync", "--onlyvisible", "--name", "^DS Playground$")
    xdotool("windowactivate", "--sync", window.split()[-1], "key", keys)


def kinds(client: httpx.Client) -> list[str]:
    """The types of every event in the ledger, in commit order."""
    return [event["type"] for event in client.get("/v1/events").json()["events"]]


CLICK_ADD_SOURCE = (
    "[...document.querySelectorAll('button')]"
    ".find((button) => button.textContent.startsWith('Add source folder')).click()"
)
CLICK = (
    "[...document.querySelectorAll('button')]"
    ".find((button) => button.textContent.trim() === '{name}').click()"
)
CALL_UNGRANTED_COMMAND = (
    "const done = arguments[arguments.length - 1];"
    "window.__TAURI_INTERNALS__.invoke('plugin:app|version')"
    ".then(() => done('allowed'), (error) => done(String(error)))"
)


def inspect_window(binary: Path, state_dir: Path) -> None:
    """Drive the real window through WebDriver (Linux only: macOS has none for its webview).

    It must show "connected", the work trail and the observed environment, refuse a command its
    capability does not grant, and open the real native folder dialog and grant nothing when that
    is cancelled. Choosing a folder in the dialog is not automated.
    """
    options = {"tauri:options": {"application": str(binary)}}
    driver = subprocess.Popen(["tauri-driver"], env={**os.environ, "DSP_HOME": str(state_dir)})
    try:
        with httpx.Client(base_url="http://127.0.0.1:4444", timeout=60) as web:
            eventually(lambda: web.get("/status").raise_for_status())
            created = web.post("/session", json={"capabilities": {"alwaysMatch": options}})
            session = created.raise_for_status().json()["value"]["sessionId"]

            def run(script: str, mode: str = "sync") -> str:
                reply = web.post(
                    f"/session/{session}/execute/{mode}", json={"script": script, "args": []}
                )
                value: str = reply.raise_for_status().json()["value"]
                return value

            def shown(expected: str) -> str:
                text = run("return document.body.innerText")
                assert expected in text, text
                return text

            try:
                eventually(lambda: shown("Harness connected"))
                text = eventually(lambda: shown("Waiting for you · INSUFFICIENT_EVIDENCE"))
                answer = harness(state_dir).get("/v1/status").json()
                assert f"version {answer['version']} · process {answer['pid']}" in text
                assert "Environment and context\n● Completed" in text
                assert "Outcome: INSUFFICIENT_EVIDENCE. local-native-draft is unqualified" in text
                snapshot = harness(state_dir).get("/v1/hardware").json()
                assert f"{snapshot['cpu']['visible_logical_processors']} visible" in text
                denied = run(CALL_UNGRANTED_COMMAND, "async")
                assert "not allowed" in denied, denied
                run(CLICK_ADD_SOURCE)
                visible = ("--onlyvisible", "--name", "Choose a source folder")
                dialog = xdotool("search", "--sync", *visible).split()[-1]
                xdotool("windowactivate", "--sync", dialog, "key", "Escape")

                def dismissed() -> str:
                    found = ["xdotool", "search", *visible]
                    still_open = subprocess.run(found, capture_output=True)
                    assert still_open.returncode, "the folder dialog is still open"
                    return shown("No folders granted yet.")

                assert "Could not update folders" not in eventually(dismissed)
            finally:
                web.delete(f"/session/{session}")  # quits the app
    finally:
        driver.terminate()
        driver.wait(10)
    assert harness(state_dir).get("/v1/grants").json() == {"grants": []}


def test_the_built_app_works_and_survives_close_kill_crash_and_a_second_instance(
    binary: Path,
    launch: Callable[[], subprocess.Popen[bytes]],
    state_dir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    evidence: Callable[..., None],
    harness_stopped: Callable[[Path], bool],
) -> None:
    """A44, R26, R20, D24: the built app, with no terminal or uv, on a fresh profile.

    Its own window makes the first discovery, which shows the real webview reached the bundled
    harness. One harness then serves the profile across a second instance, a killed shell, a
    reopen and a harness crash. On Linux the window is also inspected through WebDriver and the
    real Quit shortcut and a real window close are pressed with xdotool; on macOS none of those
    can be scripted, so Quit is exercised only as the request the shell sends.
    """
    if LINUX:
        inspect_window(binary, state_dir)
    first = launch()
    bundled = eventually(lambda: harness(state_dir))
    owner = bundled.get("/v1/status").json()
    assert owner | {"pid": 0} == {"status": "ok", "pid": 0, "version": version("dsp")}

    def opened() -> None:
        assert kinds(bundled) == ["discovery.finished", "plan.proposed"]

    eventually(opened)
    assert bundled.get("/v1/hardware").json()["evidence_source"] == "observed"

    work = tmp_path_factory.mktemp("work")
    write_orders(work / "orders.csv", orders=50, accounts=10)
    (work / "out").mkdir()
    handles = [
        bundled.post("/v1/grants", json={"purpose": purpose, "path": str(work / name)}).json()
        for purpose, name in (("source_root", "orders.csv"), ("output_root", "out"))
    ]
    request = {
        "source_handle": handles[0]["handle"],
        "relative_path": ".",
        "output_handle": handles[1]["handle"],
    }
    assert bundled.post("/v1/profiles", json=request).json() == {"version": "v1", "files": 3}
    assert verify_pack(work / "out" / "v1") == []
    escape = bundled.post("/v1/profiles", json=request | {"relative_path": "../out"})
    assert (escape.status_code, sorted(p.name for p in (work / "out").iterdir())) == (403, ["v1"])
    history = kinds(bundled)

    second = launch()  # a second instance attaches to the same harness
    time.sleep(3)
    assert (first.poll(), second.poll()) == (None, None)
    assert harness(state_dir).get("/v1/status").json()["pid"] == owner["pid"]

    first.kill()  # the shell dies; the harness and its state do not
    second.terminate()
    first.wait(10)
    second.wait(10)
    assert bundled.get("/v1/status").json()["pid"] == owner["pid"]

    third = launch()  # reopen: same harness, same history, nothing done twice
    time.sleep(3)
    assert third.poll() is None
    assert harness(state_dir).get("/v1/status").json()["pid"] == owner["pid"]
    assert kinds(bundled) == history

    os.kill(owner["pid"], signal.SIGKILL)  # the harness crashes; the next launch starts another
    third.terminate()
    third.wait(10)
    fourth = launch()
    replaced = eventually(lambda: harness(state_dir))
    successor = replaced.get("/v1/status").json()["pid"]
    assert successor != owner["pid"]
    assert kinds(replaced) == history

    if LINUX:
        # A real window close, asked of the window manager, only detaches: the app ends and the
        # harness it started keeps running.
        xdotool("search", "--sync", "--onlyvisible", "--name", "^DS Playground$")
        subprocess.run(["wmctrl", "-F", "-c", "DS Playground"], check=True, timeout=60)
        assert fourth.wait(20) == 0
        assert replaced.get("/v1/status").json()["pid"] == successor
        fifth = launch()
        press("ctrl+q")  # a real Quit from a shell that did not start the harness leaves it too
        assert fifth.wait(20) == 0
        assert replaced.get("/v1/status").json()["pid"] == successor
    assert replaced.post("/v1/shutdown").json() == {"status": "stopping"}
    assert harness_stopped(state_dir)
    (state_dir / "harness.json").unlink()

    if LINUX:
        owning = launch()  # a shell that started its own harness stops it on a real Quit
        eventually(lambda: harness(state_dir))
        press("ctrl+q")
        assert owning.wait(20) == 0
        assert harness_stopped(state_dir)
        (state_dir / "harness.json").unlink()
    seen = (
        "the window's own first discovery reached the bundled harness; a second instance "
        "attached to the same harness; the harness outlived a killed shell; reopen replayed the "
        "same history without repeating discovery; a crashed harness was replaced with the "
        "history intact; the stop request ended the harness"
    )
    if LINUX:
        seen += "; a real window close detached and a real Quit stopped the owned harness"
    evidence(
        "A44",
        "desktop-lifecycle",
        "INSUFFICIENT_EVIDENCE",
        "built desktop bundle on a temporary profile",
        "launch without model or terminal, select scoped folders, inspect the graph by keyboard, "
        "pause during busy work, close, quit, crash, sleep and reopen; one authenticated harness, "
        "history preserved, workers reconciled, renderer confined",
        seen,
        "everything exercised passed, but jobs, pause, workers and the relationship graph do not "
        "exist until later sprints, and sleep and wake were not exercised",
        "choosing a folder in the native dialog was checked by the owner by hand, not by this run",
        *([] if LINUX else ["the Quit menu item and window close are not scripted on macOS"]),
    )


def hung_job(client: httpx.Client) -> str:
    """Admit the hung test job with the request the window's Run button sends."""
    body = {"operation": "analyse", "idempotency_key": uuid.uuid4().hex}
    body["task"] = {"cues": ["hang"], "seconds": 0}
    return str(client.post("/v1/jobs", json=body).raise_for_status().json()["id"])


def worker(state_dir: Path, job: str) -> subprocess.Popen[bytes]:
    """The test worker on the app's profile, heartbeating every 200 ms."""
    command = [sys.executable, "-m", "fixtures.worker", "--job", job, "--heartbeat-seconds", "0.2"]
    return subprocess.Popen(command, cwd=ROOT, env={**os.environ, "DSP_HOME": str(state_dir)})


def shows(client: httpx.Client, job: str, state: str) -> None:
    """Fail unless the coordinator holds the job in ``state`` now."""
    assert client.get(f"/v1/jobs/{job}").json()["state"] == state


def kinds_without_heartbeats(client: httpx.Client) -> list[str]:
    """The event types in commit order, heartbeats left out."""
    return [kind for kind in kinds(client) if kind != "job.heartbeat"]


def drive_controls(binary: Path, state_dir: Path) -> None:
    """Linux: start the hung job from the window, pause and cancel with the real shortcuts.

    The trail is read through WebDriver at each step, and read again from a second launch.
    """
    options = {"tauri:options": {"application": str(binary)}}
    driver = subprocess.Popen(["tauri-driver"], env={**os.environ, "DSP_HOME": str(state_dir)})
    workers: list[subprocess.Popen[bytes]] = []
    try:
        with httpx.Client(base_url="http://127.0.0.1:4444", timeout=60) as web:
            eventually(lambda: web.get("/status").raise_for_status())

            def session() -> str:
                created = web.post("/session", json={"capabilities": {"alwaysMatch": options}})
                return str(created.raise_for_status().json()["value"]["sessionId"])

            def run(session_id: str, script: str) -> str:
                reply = web.post(
                    f"/session/{session_id}/execute/sync", json={"script": script, "args": []}
                )
                return str(reply.raise_for_status().json()["value"])

            def shown(session_id: str, expected: str) -> str:
                text = run(session_id, "return document.body.innerText")
                assert expected in text, text
                return text

            first = session()
            try:
                eventually(lambda: shown(first, "Harness connected"))
                eventually(lambda: shown(first, "Environment and context\n● Completed"))
                run(first, CLICK.format(name="Start the hung test job"))
                text = eventually(lambda: shown(first, "queued, waiting for a worker"))
                job = re.search(r"Queued (job-[0-9a-f]+)", text).group(1)  # type: ignore[union-attr]
                workers.append(worker(state_dir, job))
                eventually(lambda: shown(first, "◐ Running"))
                press("ctrl+p")  # the real Pause shortcut
                eventually(lambda: shown(first, "◆ Waiting for you · paused"))
                assert workers[-1].wait(30) == 0
                run(first, CLICK.format(name="Resume"))
                eventually(lambda: shown(first, "queued, waiting for a worker"))
                workers.append(worker(state_dir, job))
                eventually(lambda: shown(first, "running (attempt 2, fence 1)"))
                press("ctrl+period")  # the real Cancel shortcut
                eventually(lambda: shown(first, "◇ Inconclusive · cancelled"))
                assert workers[-1].wait(30) == 0
                shown(first, f"Job {job[-6:]}: cancelled (attempt 2, fence 2)")
            finally:
                web.delete(f"/session/{first}")
            second = session()
            try:
                eventually(lambda: shown(second, "◇ Inconclusive · cancelled"))
                shown(second, "pause requested (attempt 1, fence 1)")
                shown(second, "cancelled (attempt 2, fence 2)")
            finally:
                web.delete(f"/session/{second}")
    finally:
        driver.terminate()
        driver.wait(10)
        for process in workers:
            process.kill()


def test_the_built_app_starts_pauses_and_cancels_the_hung_test_job(
    binary: Path,
    launch: Callable[[], subprocess.Popen[bytes]],
    state_dir: Path,
    harness_stopped: Callable[[Path], bool],
) -> None:
    """A24, A25, R15: the built app runs the sprint's acceptance line and the trail survives.

    On Linux the window starts the hung job, the real Pause and Cancel shortcuts act on it and
    the trail is read through WebDriver, again after a second launch. On macOS, which has no
    WebDriver for its webview, the same requests the window and the menu send are made against
    the bundled harness while the app is open, and the states are read back after a relaunch.
    """
    if LINUX:
        drive_controls(binary, state_dir)
        bundled = eventually(lambda: harness(state_dir))
    else:
        app = launch()
        bundled = eventually(lambda: harness(state_dir))
        eventually(lambda: kinds(bundled).index("plan.proposed"))
        job = hung_job(bundled)
        first = worker(state_dir, job)
        eventually(lambda: shows(bundled, job, "running"))
        pause = {"command_id": uuid.uuid4().hex, "action": "pause"}
        assert bundled.post("/v1/control", json=pause).json()["job"]["state"] == "pause_requested"
        assert first.wait(30) == 0
        eventually(lambda: shows(bundled, job, "paused"))
        resume = {"command_id": uuid.uuid4().hex, "action": "resume"}
        assert (
            bundled.post(f"/v1/jobs/{job}/control", json=resume).json()["job"]["state"] == "queued"
        )
        second = worker(state_dir, job)
        eventually(lambda: shows(bundled, job, "running"))
        cancel = {"command_id": uuid.uuid4().hex, "action": "cancel"}
        assert bundled.post("/v1/control", json=cancel).json()["job"]["state"] == "cancel_requested"
        assert second.wait(30) == 0
        eventually(lambda: shows(bundled, job, "cancelled"))
        app.terminate()
        app.wait(10)
        launch()
        time.sleep(3)
    expected = [
        "job.queued",
        "job.started",
        "job.pause_requested",
        "job.paused",
        "job.resumed",
        "job.started",
        "job.cancel_requested",
        "job.cancelled",
    ]
    assert [k for k in kinds_without_heartbeats(bundled) if k.startswith("job.")] == expected
    assert bundled.get("/v1/status").json()["status"] == "ok"
    assert bundled.post("/v1/shutdown").json() == {"status": "stopping"}
    assert harness_stopped(state_dir)
    (state_dir / "harness.json").unlink()
