"""Desktop end to end against the bundle `make desktop-build` produced. Run by `make e2e`."""

import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path

import httpx
import pytest

from dsp.application.packs import verify_pack
from fixtures.operations import write_orders

pytestmark = pytest.mark.desktop

BUNDLE = Path(__file__).parents[2] / "desktop/src-tauri/target/release/bundle"


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


CLICK_ADD_SOURCE = (
    "[...document.querySelectorAll('button')]"
    ".find((button) => button.textContent.startsWith('Add source folder')).click()"
)
CALL_UNGRANTED_COMMAND = (
    "const done = arguments[arguments.length - 1];"
    "window.__TAURI_INTERNALS__.invoke('plugin:app|version')"
    ".then(() => done('allowed'), (error) => done(String(error)))"
)


def test_the_built_app_starts_its_bundled_harness_and_connects(
    state_dir: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """R26, C23: launched on a fresh profile with no terminal or uv, the app works end to end.

    On Linux the window is driven through WebDriver: it must show "connected", refuse a command
    its capability does not grant, and turn a folder chosen in the real native dialog (typed in
    with xdotool) into a grant shown by name. macOS has no WebDriver for its webview and its
    dialog cannot be scripted here, so there only the harness the app started is checked. On both,
    the bundled harness then profiles a real file through grants and refuses a path outside them.
    """
    environment = {**os.environ, "DSP_HOME": str(state_dir)}
    if sys.platform == "darwin":
        (binary,) = BUNDLE.glob("macos/*.app/Contents/MacOS/dsp-desktop")
        app = subprocess.Popen([binary], env=environment)
        try:
            bundled = eventually(lambda: harness(state_dir))
            assert app.poll() is None
        finally:
            app.terminate()
            app.wait(10)
    else:
        (deb,) = BUNDLE.glob("deb/*.deb")
        installed = tmp_path_factory.mktemp("deb")
        subprocess.run(["dpkg-deb", "--extract", deb, installed], check=True)
        options = {"tauri:options": {"application": str(installed / "usr/bin/dsp-desktop")}}
        picked = tmp_path_factory.mktemp("picked") / "orders 2026"
        picked.mkdir()
        driver = subprocess.Popen(["tauri-driver"], env=environment)
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
                    text = eventually(lambda: shown("Harness connected"))
                    denied = run(CALL_UNGRANTED_COMMAND, "async")
                    assert "not allowed" in denied, denied
                    run(CLICK_ADD_SOURCE)
                    search = ["xdotool", "search", "--sync", "--name", "Choose a source folder"]
                    found = subprocess.run(
                        search, check=True, capture_output=True, text=True, timeout=60
                    )
                    dialog = found.stdout.split()[0]
                    typing = ["key", "ctrl+l", "type", "--delay", "20", f"{picked}\n"]
                    subprocess.run(
                        ["xdotool", "windowfocus", "--sync", dialog, *typing],
                        check=True,
                        timeout=60,
                    )
                    listed = eventually(lambda: shown("Source folder: orders 2026"))
                    assert str(picked.parent) not in listed
                finally:
                    web.delete(f"/session/{session}")  # quits the app
        finally:
            driver.terminate()
            driver.wait(10)
        bundled = harness(state_dir)
        grants = bundled.get("/v1/grants").json()["grants"]
        assert [(grant["purpose"], grant["label"]) for grant in grants] == [
            ("source_root", "orders 2026")
        ]
        answer = bundled.get("/v1/status").json()
        assert f"version {answer['version']} · process {answer['pid']}" in text
    assert bundled.get("/v1/status").json() | {"pid": 0} == {
        "status": "ok",
        "pid": 0,
        "version": version("dsp"),
    }

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
