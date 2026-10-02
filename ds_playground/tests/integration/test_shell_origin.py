import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dsp.contracts.errors import ErrorCode
from dsp.harness.app import DEV_ORIGIN, SHELL_ORIGIN, create_app
from dsp.harness.instance import connect

AUTH = {"Authorization": "Bearer secret"}
PREFLIGHT = {
    "Access-Control-Request-Method": "GET",
    "Access-Control-Request-Headers": "authorization",
}
ALLOW = "access-control-allow-origin"


def api(dev: bool = False) -> TestClient:
    """The harness API in-process, as served on port 4100 with credential ``secret``."""
    return TestClient(create_app("secret", 4100, dev=dev), base_url="http://127.0.0.1:4100")


def test_the_shell_origin_with_a_valid_credential_is_accepted() -> None:
    """C23: the desktop shell's own origin reaches the harness and may read the answer."""
    response = api().get("/v1/status", headers=AUTH | {"Origin": SHELL_ORIGIN})
    assert (response.status_code, response.headers[ALLOW]) == (200, SHELL_ORIGIN)
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize(
    "origin",
    [
        "http://evil.example",
        "null",
        "",
        "tauri://localhost.evil.example",
        "tauri://localhost:1420",
        "https://tauri.localhost",
        "http://127.0.0.1:4100",
        DEV_ORIGIN,
    ],
)
@pytest.mark.parametrize("extra", [{}, PREFLIGHT])
def test_any_other_origin_is_forbidden(origin: str, extra: dict[str, str]) -> None:
    """C23: no other origin gets an answer or a CORS grant, as a request or as a preflight."""
    method = "OPTIONS" if extra else "GET"
    response = api().request(method, "/v1/status", headers=AUTH | {"Origin": origin} | extra)
    assert (response.status_code, response.json()["code"]) == (403, ErrorCode.FORBIDDEN)
    assert ALLOW not in response.headers


def test_preflight_from_the_shell_origin_is_answered_without_a_credential() -> None:
    """C23: the browser's preflight carries no token, so it is answered before the token check."""
    response = api().options("/v1/status", headers={"Origin": SHELL_ORIGIN} | PREFLIGHT)
    assert (response.status_code, response.content) == (204, b"")
    assert response.headers[ALLOW] == SHELL_ORIGIN
    assert response.headers["access-control-allow-headers"] == "authorization"


@pytest.mark.parametrize(
    ("method", "headers"),
    [("GET", {}), ("GET", {"Authorization": "Bearer wrong"}), ("OPTIONS", {}), ("POST", PREFLIGHT)],
)
def test_the_shell_origin_is_not_a_credential(method: str, headers: dict[str, str]) -> None:
    """C23: only a true preflight skips the token; every real request from the shell needs it."""
    response = api().request(method, "/v1/status", headers={"Origin": SHELL_ORIGIN} | headers)
    assert (response.status_code, response.json()["code"]) == (401, ErrorCode.UNAUTHENTICATED)
    assert response.headers[ALLOW] == SHELL_ORIGIN  # the shell may read why it was refused


def test_the_dev_origin_is_accepted_when_the_app_is_built_with_the_dev_flag() -> None:
    """C23: the `tauri dev` origin is allowed only in a harness created for development."""
    dev = api(dev=True)
    assert dev.get("/v1/status", headers=AUTH | {"Origin": DEV_ORIGIN}).status_code == 200
    assert dev.options("/v1/status", headers={"Origin": DEV_ORIGIN} | PREFLIGHT).status_code == 204
    assert dev.get("/v1/status", headers=AUTH | {"Origin": SHELL_ORIGIN}).status_code == 200
    assert (
        dev.get("/v1/status", headers=AUTH | {"Origin": "http://localhost:5173"}).status_code == 403
    )


def test_a_harness_spawned_without_the_dev_flag_refuses_the_dev_origin(state_dir: Path) -> None:
    """C23: a real harness started the ordinary way admits the shell origin and not the dev one."""
    client = connect(state_dir)
    assert client.get("/v1/status", headers={"Origin": SHELL_ORIGIN}).status_code == 200
    assert client.get("/v1/status", headers={"Origin": DEV_ORIGIN}).status_code == 403


@pytest.mark.parametrize(("arguments", "expected"), [(["--dev"], 200), (["--dev", "x"], 403)])
def test_only_the_dev_flag_at_spawn_admits_the_dev_origin(
    tmp_path: Path, arguments: list[str], expected: int
) -> None:
    """C23: the dev origin is admitted only when the harness process is spawned with `--dev`."""
    environment = {**os.environ, "DSP_HOME": str(tmp_path)}
    process = subprocess.Popen([sys.executable, "-m", "dsp.harness", *arguments], env=environment)
    try:
        for _ in range(100):
            if (tmp_path / "harness.json").exists():
                break
            time.sleep(0.1)
        assert json.loads((tmp_path / "harness.json").read_text())["pid"] == process.pid
        response = connect(tmp_path).get("/v1/status", headers={"Origin": DEV_ORIGIN})
        assert response.status_code == expected
    finally:
        process.terminate()
        process.wait()
