import fcntl
import ipaddress
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import uvicorn

from dsp.contracts.errors import DspError, ErrorCode
from dsp.harness.app import create_app
from dsp.harness.workspace import mount


def home() -> Path:
    """Return the per-user state directory (``DSP_HOME`` or ``~/.dsp``), creating it if needed."""
    path = Path(os.environ.get("DSP_HOME") or Path.home() / ".dsp")
    path.mkdir(parents=True, exist_ok=True)
    return path


def serve(state_dir: Path, host: str = "127.0.0.1", dev: bool = False) -> None:
    """Run the one harness for this profile; return at once if another instance already holds it.

    The port is chosen by the OS and published, with a fresh owner-only credential, in
    ``harness.json`` (mode 0600). Binding anywhere but loopback is refused. ``dev`` admits the
    `tauri dev` origin.
    """
    if not ipaddress.ip_address(host).is_loopback:
        raise DspError(ErrorCode.FORBIDDEN, "non-loopback binding needs remote authentication")
    lock = (state_dir / "harness.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    listener = socket.socket()
    listener.bind((host, 0))
    port, token = listener.getsockname()[1], secrets.token_urlsafe(32)
    descriptor = os.open(state_dir / "harness.json", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        json.dump({"port": port, "token": token, "pid": os.getpid()}, handle)
    app = create_app(token, port, dev)
    mount(app, state_dir)
    config = uvicorn.Config(app, log_level="warning")
    uvicorn.Server(config).run(sockets=[listener])


def connect(state_dir: Path) -> httpx.Client:
    """Return an authenticated client for the running harness, starting it if none answers."""
    for attempt in range(100):
        try:
            state = json.loads((state_dir / "harness.json").read_text())
            client = httpx.Client(
                base_url=f"http://127.0.0.1:{state['port']}",
                headers={"Authorization": f"Bearer {state['token']}"},
            )
            client.get("/v1/status").raise_for_status()
        except (OSError, ValueError, KeyError, httpx.HTTPError):
            if attempt == 0:
                subprocess.Popen(
                    [sys.executable, "-m", "dsp.harness"],
                    env={**os.environ, "DSP_HOME": str(state_dir)},
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            time.sleep(0.1)
        else:
            return client
    raise DspError(ErrorCode.DEPENDENCY_UNAVAILABLE, "the harness did not start")
