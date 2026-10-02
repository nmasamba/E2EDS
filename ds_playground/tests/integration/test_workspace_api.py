import json
import os
import signal
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.application.packs import verify_pack
from dsp.contracts.errors import ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.harness import workspace
from dsp.harness.app import DEV_ORIGIN, SHELL_ORIGIN, create_app
from dsp.harness.instance import connect
from dsp.interfaces.cli import app as cli
from fixtures.operations import write_orders

NATIVE = {"Authorization": "Bearer secret"}  # the shell's Rust side and the CLI send no Origin
WINDOW = NATIVE | {"Origin": SHELL_ORIGIN}  # the renderer always does


def client(state: Path, dev: bool = False) -> TestClient:
    """The harness API with the workspace routes, in-process, on a profile directory."""
    state.mkdir(exist_ok=True)
    app = create_app("secret", 4100, dev=dev)
    workspace.mount(app, state)
    return TestClient(app, base_url="http://127.0.0.1:4100")


@pytest.fixture
def api(tmp_path: Path) -> TestClient:
    """A harness on a fresh profile beside the folders under test."""
    return client(tmp_path / "home")


@pytest.fixture
def folders(tmp_path: Path) -> dict[str, Path]:
    """A data folder with an orders file, an empty output folder, and a secret outside both."""
    data, out = tmp_path / "data", tmp_path / "out"
    data.mkdir()
    out.mkdir()
    write_orders(data / "orders.csv", orders=30, accounts=6)
    (tmp_path / "secret.csv").write_text("a\n1\n")
    return {"data": data, "out": out, "secret": tmp_path / "secret.csv"}


def granted(api: TestClient, folder: Path, purpose: str) -> str:
    """Grant a folder the way the native shell or the CLI does and return its handle."""
    response = api.post(
        "/v1/grants", headers=NATIVE, json={"purpose": purpose, "path": str(folder)}
    )
    assert response.status_code == 200, response.text
    handle: str = response.json()["handle"]
    return handle


def profiled(api: TestClient, source: str, relative: str, output: str) -> Any:
    """Ask, as the CLI does, for a profile of ``relative`` under one grant into another."""
    body = {"source_handle": source, "relative_path": relative, "output_handle": output}
    return api.post("/v1/profiles", headers=NATIVE, json=body)


def test_a_native_grant_is_listed_to_the_window_without_its_path(
    api: TestClient, folders: dict[str, Path], tmp_path: Path
) -> None:
    """R26: the shell or CLI grants by path; every answer carries the handle and label only."""
    created = api.post(
        "/v1/grants", headers=NATIVE, json={"purpose": "source_root", "path": str(folders["data"])}
    )
    listed = api.get("/v1/grants", headers=WINDOW)
    assert created.status_code == listed.status_code == 200
    assert listed.json() == {"grants": [created.json()]}
    assert created.json() | {"handle": ""} == {
        "handle": "",
        "purpose": "source_root",
        "label": "data",
        "state": "active",
    }
    assert str(tmp_path) not in created.text + listed.text


@pytest.mark.parametrize("dev", [False, True])
def test_the_window_cannot_grant_a_path(
    tmp_path: Path, folders: dict[str, Path], dev: bool
) -> None:
    """C23: a request with a browser origin, even the shell's own, cannot grant a path."""
    api = client(tmp_path / "home", dev=dev)
    body = {"purpose": "source_root", "path": str(folders["data"])}
    origin = DEV_ORIGIN if dev else SHELL_ORIGIN
    refused = api.post("/v1/grants", headers=NATIVE | {"Origin": origin}, json=body)
    assert (refused.status_code, refused.json()["code"]) == (403, ErrorCode.FORBIDDEN)
    assert api.get("/v1/grants", headers=WINDOW).json() == {"grants": []}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/v1/grants"),
        ("GET", "/v1/grants"),
        ("POST", "/v1/grants/grant-x/revoke"),
        ("POST", "/v1/profiles"),
    ],
)
def test_every_workspace_route_needs_the_token(api: TestClient, method: str, path: str) -> None:
    """C23: no workspace route answers without the owner credential."""
    response = api.request(method, path, json={})
    assert (response.status_code, response.json()["code"]) == (401, ErrorCode.UNAUTHENTICATED)


def test_a_profile_through_grants_exports_a_verified_pack(
    api: TestClient, folders: dict[str, Path], tmp_path: Path
) -> None:
    """R11, D23: a file named by handle and relative path is exported as a verified pack."""
    source = granted(api, folders["data"], "source_root")
    output = granted(api, folders["out"], "output_root")
    first = profiled(api, source, "orders.csv", output)
    assert (first.status_code, first.json()) == (200, {"version": "v1", "files": 3})
    assert verify_pack(folders["out"] / "v1") == []
    assert profiled(api, source, "orders.csv", output).json()["version"] == "v2"
    events = SqliteLedger(tmp_path / "home" / "ledger.sqlite", str).events(TrustedContext.local())
    assert events[-1]["body"]["destination"] == output
    assert str(tmp_path) not in first.text + json.dumps(events)


def test_grants_are_enforced_when_a_profile_uses_them(
    api: TestClient, folders: dict[str, Path]
) -> None:
    """C23: traversal, an escaping link, a raw path, a misused or revoked handle export nothing."""
    source = granted(api, folders["data"], "source_root")
    output = granted(api, folders["out"], "output_root")
    (folders["data"] / "link.csv").symlink_to(folders["secret"])
    attempts = {
        (source, "../secret.csv", output): 403,
        (source, str(folders["secret"]), output): 403,
        (source, "link.csv", output): 403,
        (str(folders["data"]), "orders.csv", output): 404,
        (source, "orders.csv", str(folders["out"])): 404,
        (output, "orders.csv", output): 403,
        (source, "orders.csv", source): 403,
        (source, "absent.csv", output): 404,
        (source, ".", output): 404,
    }
    for attempt, status in attempts.items():
        assert profiled(api, *attempt).status_code == status, attempt
    assert api.post(f"/v1/grants/{source}/revoke", headers=WINDOW).json()["state"] == "revoked"
    revoked = profiled(api, source, "orders.csv", output)
    assert (revoked.status_code, revoked.json()["code"]) == (403, ErrorCode.FORBIDDEN)
    assert list(folders["out"].iterdir()) == []


def test_the_window_can_revoke_and_the_list_follows(
    api: TestClient, folders: dict[str, Path]
) -> None:
    """R26: revoking is an explicit owner action from any door; unknown handles are NOT_FOUND."""
    source = granted(api, folders["data"], "source_root")
    output = granted(api, folders["out"], "output_root")
    assert api.post(f"/v1/grants/{output}/revoke", headers=WINDOW).status_code == 200
    assert [g["handle"] for g in api.get("/v1/grants", headers=WINDOW).json()["grants"]] == [source]
    unknown = api.post("/v1/grants/grant-made-up/revoke", headers=WINDOW)
    assert (unknown.status_code, unknown.json()["code"]) == (404, ErrorCode.NOT_FOUND)


def test_grants_survive_a_harness_restart(tmp_path: Path, folders: dict[str, Path]) -> None:
    """A44: a new harness on the same profile shows the same grants, read from the ledger."""
    first = client(tmp_path / "home")
    handle = granted(first, folders["data"], "source_root")
    reopened = client(tmp_path / "home").get("/v1/grants", headers=WINDOW).json()["grants"]
    assert [grant["handle"] for grant in reopened] == [handle]


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"purpose": "source_root"},
        {"purpose": "source_root", "path": 7},
        {"purpose": "everything", "path": "/"},
        {"purpose": "source_root", "path": "relative/folder"},
    ],
)
def test_a_malformed_grant_request_is_input_invalid(api: TestClient, body: dict[str, Any]) -> None:
    """R26: a bad request body gets the shared error shape and grants nothing."""
    response = api.post("/v1/grants", headers=NATIVE, json=body)
    assert (response.status_code, response.json()["code"]) == (400, ErrorCode.INPUT_INVALID)
    assert api.get("/v1/grants", headers=NATIVE).json() == {"grants": []}


def test_a_failed_profile_is_recorded_and_exports_nothing(
    api: TestClient, folders: dict[str, Path], tmp_path: Path
) -> None:
    """D20: a file over the column bound is refused and the job is recorded as failed."""
    wide = ",".join(f"c{i}" for i in range(201))
    (folders["data"] / "wide.csv").write_text(wide + "\n" + ",".join("1" * 201) + "\n")
    source = granted(api, folders["data"], "source_root")
    output = granted(api, folders["out"], "output_root")
    refused = profiled(api, source, "wide.csv", output)
    assert (refused.status_code, refused.json()["code"]) == (400, ErrorCode.INPUT_INVALID)
    events = SqliteLedger(tmp_path / "home" / "ledger.sqlite", str).events(TrustedContext.local())
    assert [event["type"] for event in events][-2:] == ["job.started", "job.failed"]
    assert list(folders["out"].iterdir()) == []


def test_an_unexpected_failure_is_a_structured_error_without_detail(
    api: TestClient, folders: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """C23: a crash inside a request answers INTERNAL_ERROR, readable by the window, no detail."""

    def crash(*arguments: object, **services: object) -> dict[str, Any]:
        raise RuntimeError(f"cannot handle {arguments}")

    source = granted(api, folders["data"], "source_root")
    monkeypatch.setattr(workspace, "revoke", crash)
    response = api.post(f"/v1/grants/{source}/revoke", headers=WINDOW)
    assert response.status_code == 500
    assert response.json() == {"code": ErrorCode.INTERNAL_ERROR, "message": "internal error"}
    assert response.headers["access-control-allow-origin"] == SHELL_ORIGIN


def test_discovery_runs_from_the_window_and_the_latest_snapshot_is_served(api: TestClient) -> None:
    """R19, A31: the window can ask for discovery before any model exists and read the result."""
    missing = api.get("/v1/hardware", headers=WINDOW)
    assert (missing.status_code, missing.json()["code"]) == (404, ErrorCode.NOT_FOUND)
    first = api.post("/v1/hardware", headers=WINDOW)
    second = api.post("/v1/hardware", headers=WINDOW)
    assert (first.status_code, first.json()["evidence_source"]) == (200, "observed")
    assert api.get("/v1/hardware", headers=WINDOW).json() == second.json() != first.json()
    assert api.post("/v1/hardware").status_code == 401


def test_the_workspace_stays_usable_when_discovery_finds_nothing(
    api: TestClient, folders: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A31: with every probe denied the snapshot is unknown and grants and status still work."""

    def denied() -> dict[str, Any]:
        raise PermissionError

    monkeypatch.setattr(workspace, "probes", lambda state: {"cpu": denied, "accelerators": denied})
    snapshot = api.post("/v1/hardware", headers=WINDOW).json()
    assert (snapshot["evidence_source"], snapshot["accelerators"]["inventory_status"]) == (
        "unknown",
        "unknown",
    )
    assert api.get("/v1/status", headers=WINDOW).json()["status"] == "ok"
    assert granted(api, folders["data"], "source_root").startswith("grant-")


def test_a_provisional_plan_follows_discovery_and_supersedes_the_last(
    api: TestClient, tmp_path: Path
) -> None:
    """R19, A32: the window gets a schema-valid plan that authorises nothing and names its gaps."""
    early = api.post("/v1/plan", headers=WINDOW)
    assert (early.status_code, early.json()["code"]) == (400, ErrorCode.INPUT_INVALID)
    assert api.get("/v1/plan", headers=WINDOW).status_code == 404
    snapshot = api.post("/v1/hardware", headers=WINDOW).json()
    first = api.get("/v1/plan", headers=WINDOW).json()  # proposed with the discovery
    second = api.post("/v1/plan", headers=WINDOW).json()
    validate("WorkflowPlan", second)
    assert (first["feasibility_outcome"], first["authorises_execution"]) == (
        "INSUFFICIENT_EVIDENCE",
        False,
    )
    assert first["recommendation"] == (
        "local-native-draft is unqualified: this compute profile has not been qualified."
    )
    assert first["hardware_snapshot_refs"][0]["id"] == snapshot["id"]
    assert (first["supersedes_ref"], second["supersedes_ref"]["id"]) == (None, first["id"])
    assert api.get("/v1/plan", headers=WINDOW).json() == second
    events = SqliteLedger(tmp_path / "home" / "ledger.sqlite", str).events(TrustedContext.local())
    assert [event["type"] for event in events] == [
        "discovery.finished",
        "plan.proposed",
        "plan.proposed",
    ]
    assert api.post("/v1/plan").status_code == 401


def test_polling_replays_from_a_cursor_and_resets_an_unknown_one(
    api: TestClient, folders: dict[str, Path], tmp_path: Path
) -> None:
    """R20: events come in commit order after a cursor; a cursor from elsewhere gets everything."""
    assert api.get("/v1/events", headers=WINDOW).json() == {
        "events": [],
        "cursor": 0,
        "reset": False,
    }
    stale = api.get("/v1/events?after=7", headers=WINDOW).json()
    assert stale == {"events": [], "cursor": 0, "reset": True}
    handle = granted(api, folders["data"], "source_root")
    api.post("/v1/hardware", headers=WINDOW)
    everything = api.get("/v1/events", headers=WINDOW).json()
    kinds = [event["type"] for event in everything["events"]]
    assert kinds == ["grant.created", "discovery.finished", "plan.proposed"]
    assert everything["events"][0]["body"] == {
        "handle": handle,
        "purpose": "source_root",
        "label": "data",
    }
    assert set(everything["events"][0]) == {"seq", "event_id", "type", "recorded_at", "body"}
    later = api.get("/v1/events?after=1", headers=WINDOW).json()
    assert ([event["type"] for event in later["events"]], later["reset"]) == (kinds[1:], False)
    current = api.get(f"/v1/events?after={everything['cursor']}", headers=WINDOW).json()
    assert current == {"events": [], "cursor": everything["cursor"], "reset": False}
    beyond = api.get("/v1/events?after=99", headers=WINDOW).json()
    assert (beyond["reset"], beyond["events"], beyond["cursor"]) == (
        True,
        everything["events"],
        everything["cursor"],
    )
    assert api.get("/v1/events?after=-1", headers=WINDOW).status_code == 400
    assert api.get("/v1/events").status_code == 401
    assert str(tmp_path) not in json.dumps(everything)


def frames(lines: Iterator[str], count: int) -> list[tuple[str, dict[str, Any]]]:
    """Read ``count`` server-sent events from a response as (event name, data) pairs."""
    seen: list[tuple[str, dict[str, Any]]] = []
    name = ""
    for line in lines:
        if line.startswith("event: "):
            name = line.removeprefix("event: ")
        elif line.startswith("data: "):
            seen.append((name, json.loads(line.removeprefix("data: "))))
            if len(seen) == count:
                break
    return seen


def test_the_stream_replays_then_follows_and_equals_polling(state_dir: Path) -> None:
    """R20: a real stream replays from its cursor, delivers new events live and matches polling."""
    client = connect(state_dir)
    client.post("/v1/hardware")
    with client.stream("GET", "/v1/events/stream", timeout=30) as live:
        lines = live.iter_lines()
        replayed = frames(lines, 2)
        client.post("/v1/plan")
        (followed,) = frames(lines, 1)
        assert live.headers["content-type"].startswith("text/event-stream")
    polled = client.get("/v1/events").json()["events"]
    assert [data for _, data in [*replayed, followed]] == polled
    assert [name for name, _ in [*replayed, followed]] == [
        "discovery.finished",
        "plan.proposed",
        "plan.proposed",
    ]
    with client.stream("GET", f"/v1/events/stream?after={polled[1]['seq']}", timeout=30) as live:
        assert frames(live.iter_lines(), 1) == [("plan.proposed", polled[2])]
    with client.stream("GET", "/v1/events/stream?after=999", timeout=30) as live:
        resynchronised = frames(live.iter_lines(), 4)
    assert resynchronised[0] == ("stream.resynchronised", {})
    assert [data for _, data in resynchronised[1:]] == polled
    assert client.get("/v1/status").json()["status"] == "ok"


def test_an_open_stream_does_not_keep_a_stopping_harness_alive(state_dir: Path) -> None:
    """A44: asked to stop while a client is streaming, the harness ends the stream and exits."""
    client = connect(state_dir)
    pid = client.get("/v1/status").json()["pid"]
    with client.stream("GET", "/v1/events/stream", timeout=30) as live:
        os.kill(pid, signal.SIGTERM)
        assert list(live.iter_lines()) == []
    for _ in range(50):
        if subprocess.run(["ps", "-p", str(pid)], capture_output=True).returncode:
            break
        time.sleep(0.1)
    else:
        pytest.fail("the harness is still running")
    (state_dir / "harness.json").unlink()


def test_a_plan_from_unobserved_hardware_says_unknown(
    api: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A31, A32: with every probe denied the plan is still proposed and its option is unknown."""

    def denied() -> dict[str, Any]:
        raise PermissionError

    monkeypatch.setattr(workspace, "probes", lambda state: {"memory": denied})
    api.post("/v1/hardware", headers=WINDOW)
    proposed = api.post("/v1/plan", headers=WINDOW).json()
    assert proposed["recommendation"] == (
        "local-native-draft is unknown: its hardware has not been observed."
    )
    assert proposed["feasibility_outcome"] == "INSUFFICIENT_EVIDENCE"


def run(*arguments: object) -> Any:
    """Invoke the CLI in-process; it talks to a real harness on the temporary profile."""
    return CliRunner().invoke(cli, [str(argument) for argument in arguments])


def test_the_cli_grants_lists_and_revokes(home: Path, folders: dict[str, Path]) -> None:
    """R26: `dsp grant`, `dsp grants` and `dsp revoke` go through the harness and print no path."""
    made = run("grant", folders["out"], "--purpose", "output_root")
    handle = made.output.split()[0]
    assert (made.exit_code, made.output.split()[1:]) == (0, ["output_root", "out"])
    assert run("grant", folders["out"], "--purpose", "output_root").output == made.output
    assert run("grants").output == made.output
    assert run("revoke", handle).exit_code == 0
    assert run("grants").output == ""
    again = run("revoke", "grant-made-up")
    assert (again.exit_code, "NOT_FOUND" in again.output) == (2, True)
    bad = run("grant", folders["out"], "--purpose", "everything")
    assert (bad.exit_code, "INPUT_INVALID" in bad.output) == (2, True)
    stored = json.dumps(SqliteLedger(home / "ledger.sqlite", str).events(TrustedContext.local()))
    assert str(folders["out"].parent) not in stored


def test_cli_profile_grants_only_what_it_names(home: Path, folders: dict[str, Path]) -> None:
    """R26: `dsp profile FILE --out FOLDER` grants that file and that folder, visible afterwards."""
    result = run("profile", folders["data"] / "orders.csv", "--out", folders["out"])
    assert (result.exit_code, verify_pack(folders["out"] / "v1")) == (0, [])
    listed = [line.split()[1:] for line in run("grants").output.splitlines()]
    assert listed == [["source_root", "orders.csv"], ["output_root", "out"]]


def test_the_cli_reports_observed_hardware(home: Path) -> None:
    """R19: `dsp hardware` observes this machine through the harness and prints what it found."""
    result = run("hardware")
    first, second = result.output.splitlines()[:2]
    assert result.exit_code == 0
    assert "processors" in first
    assert "GiB memory" in first
    assert "unknown" not in first
    assert second.startswith("accelerators ")


def test_the_cli_reports_a_provisional_plan(home: Path) -> None:
    """R19: `dsp plan` needs discovery first, then prints the outcome, the reason and the gaps."""
    early = run("plan")
    assert (early.exit_code, "INPUT_INVALID" in early.output) == (2, True)
    assert run("hardware").exit_code == 0
    lines = run("plan").output.splitlines()
    assert lines[0].startswith("INSUFFICIENT_EVIDENCE: local-native-draft is unqualified")
    assert (
        lines[1]
        == "needs: Recheck capacity and reserve it at dispatch; this plan authorises nothing."
    )
