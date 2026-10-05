"""Desktop end to end against the bundle `make desktop-build` produced. Run by `make e2e`."""

import json
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from importlib.metadata import version
from pathlib import Path

import httpx
import pytest

from dsp.application.packs import verify_pack
from fixtures.operations import write_orders

pytestmark = pytest.mark.desktop

BUNDLE = Path(__file__).parents[2] / "desktop/src-tauri/target/release/bundle"
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
