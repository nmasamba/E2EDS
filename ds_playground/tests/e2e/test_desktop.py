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


def status(state_dir: Path) -> dict[str, object]:
    """Answer of the harness that published its port and token in ``state_dir``."""
    state = json.loads((state_dir / "harness.json").read_text())
    response = httpx.get(
        f"http://127.0.0.1:{state['port']}/v1/status",
        headers={"Authorization": f"Bearer {state['token']}"},
    )
    answer: dict[str, object] = response.raise_for_status().json()
    return answer


def test_the_built_app_starts_its_bundled_harness_and_connects(
    state_dir: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """R26: launched on a fresh profile with no terminal or uv, the app brings up its own harness.

    On Linux the window is driven through WebDriver and must show "connected". macOS has no
    WebDriver for its webview, so there only the harness the app started is checked.
    """
    environment = {**os.environ, "DSP_HOME": str(state_dir)}
    if sys.platform == "darwin":
        (binary,) = BUNDLE.glob("macos/*.app/Contents/MacOS/dsp-desktop")
        app = subprocess.Popen([binary], env=environment)
        try:
            answer = eventually(lambda: status(state_dir))
            assert app.poll() is None
        finally:
            app.terminate()
            app.wait(10)
    else:
        (deb,) = BUNDLE.glob("deb/*.deb")
        installed = tmp_path_factory.mktemp("deb")
        subprocess.run(["dpkg-deb", "--extract", deb, installed], check=True)
        options = {"tauri:options": {"application": str(installed / "usr/bin/dsp-desktop")}}
        driver = subprocess.Popen(["tauri-driver"], env=environment)
        try:
            with httpx.Client(base_url="http://127.0.0.1:4444", timeout=60) as web:
                eventually(lambda: web.get("/status").raise_for_status())
                created = web.post("/session", json={"capabilities": {"alwaysMatch": options}})
                session = created.raise_for_status().json()["value"]["sessionId"]

                def shown() -> str:
                    script = {"script": "return document.body.innerText", "args": []}
                    reply = web.post(f"/session/{session}/execute/sync", json=script)
                    text: str = reply.raise_for_status().json()["value"]
                    assert "Harness connected" in text, text
                    return text

                try:
                    text = eventually(shown)
                finally:
                    web.delete(f"/session/{session}")  # quits the app
        finally:
            driver.terminate()
            driver.wait(10)
        answer = status(state_dir)
        assert f"version {answer['version']} · process {answer['pid']}" in text
    assert (answer["status"], answer["version"]) == ("ok", version("dsp"))
