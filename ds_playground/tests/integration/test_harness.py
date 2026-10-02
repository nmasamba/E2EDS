import json
import os
import stat
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from dsp.contracts.errors import DspError, ErrorCode
from dsp.harness.app import create_app
from dsp.harness.instance import connect, serve
from dsp.interfaces.cli import app as cli

BASE = "http://127.0.0.1:4100"
AUTH = {"Authorization": "Bearer secret"}


@pytest.fixture
def api() -> TestClient:
    """The harness API in-process, as served on port 4100 with credential ``secret``."""
    return TestClient(create_app("secret", 4100), base_url=BASE)


def test_a_valid_credential_reaches_status(api: TestClient) -> None:
    """R26: the harness answers its owner."""
    assert api.get("/v1/status", headers=AUTH).json()["status"] == "ok"


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": "secret"}]
)
def test_a_missing_or_wrong_credential_is_unauthenticated(
    api: TestClient, headers: dict[str, str]
) -> None:
    """C23: loopback is not authorisation; every request needs the owner credential."""
    response = api.get("/v1/status", headers=headers)
    assert (response.status_code, response.json()["code"]) == (401, ErrorCode.UNAUTHENTICATED)


@pytest.mark.parametrize(
    "headers",
    [{"Host": "evil.example"}, {"Host": "127.0.0.1:9"}, {"Origin": "http://evil.example"}],
)
def test_foreign_hosts_and_origins_are_forbidden(api: TestClient, headers: dict[str, str]) -> None:
    """C23: a rebinding host or a foreign origin is refused even with the right credential."""
    response = api.get("/v1/status", headers=AUTH | headers)
    assert (response.status_code, response.json()["code"]) == (403, ErrorCode.FORBIDDEN)


def test_non_loopback_binding_is_refused(tmp_path: Path) -> None:
    """C23: the harness will not listen beyond loopback."""
    with pytest.raises(DspError) as raised:
        serve(tmp_path, host="0.0.0.0")
    assert raised.value.code is ErrorCode.FORBIDDEN
    assert not (tmp_path / "harness.json").exists()


def test_connect_starts_one_harness_and_then_reuses_it(state_dir: Path) -> None:
    """A44: a second client reconnects to the same instance; the credential file is owner-only."""
    first = connect(state_dir).get("/v1/status").json()
    second = connect(state_dir).get("/v1/status").json()
    assert first["pid"] == second["pid"] != os.getpid()
    assert stat.S_IMODE((state_dir / "harness.json").stat().st_mode) == 0o600
    serve(state_dir)  # a second instance returns at once: the profile lock is held
    port = json.loads((state_dir / "harness.json").read_text())["port"]
    assert httpx.get(f"http://127.0.0.1:{port}/v1/status").status_code == 401


def test_a_stale_state_file_is_replaced(state_dir: Path) -> None:
    """A44: after a crash leaves a dead port behind, connecting starts a fresh harness."""
    (state_dir / "harness.json").write_text(json.dumps({"port": 9, "token": "old"}))
    assert connect(state_dir).get("/v1/status").json()["status"] == "ok"


def test_status_command_reports_the_harness(
    state_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R26: `dsp status` starts or reconnects to the harness and reports it."""
    monkeypatch.setenv("DSP_HOME", str(state_dir))
    result = CliRunner().invoke(cli, ["status"])
    assert (result.exit_code, "harness running" in result.output) == (0, True)
