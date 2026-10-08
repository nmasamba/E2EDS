"""Admission driven for real: refusals before any work, the reservation race and the stale plan."""

import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.application import admission, jobs
from dsp.application.discovery import discover
from dsp.application.planning import LOCAL_DRAFT, propose_plan
from dsp.application.workloads import base_workload
from dsp.contracts.canonical import pin
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.harness import workspace
from dsp.harness.app import SHELL_ORIGIN, create_app
from tests.conftest import Clock

CTX = TrustedContext.local()
NOW = "2026-10-08T10:00:00+00:00"
TASK = {"cues": ["hang"], "seconds": 0}
REQUEST = {"operation": "analyse", "idempotency_key": "key-1", "task": TASK}
WINDOW = {"Authorization": "Bearer secret", "Origin": SHELL_ORIGIN}
Probes = dict[str, Callable[[], dict[str, Any]]]


def fixed_probes(cpus: int, memory_gib: float, free_gib: float = 100.0) -> Probes:
    """Probes that report a chosen machine, in the shapes the real probes return."""
    return {
        "system": lambda: {"system": {"os": "linux", "architecture": "x86_64", "cpu_features": []}},
        "cpu": lambda: {
            "cpu": {
                "visible_logical_processors": cpus,
                "effective_cpu_quota": cpus,
                "available_to_plan_cpus": None,
            }
        },
        "memory": lambda: {
            "memory": {
                "total_gib": memory_gib,
                "available_gib": memory_gib,
                "effective_limit_gib": memory_gib,
            }
        },
        "storage": lambda: {
            "storage": [
                {
                    "role": "combined",
                    "domain_id": "state-volume",
                    "available_gib": free_gib,
                    "effective_quota_gib": None,
                }
            ]
        },
    }


def new_id() -> str:
    """A fresh opaque ID."""
    return uuid.uuid4().hex


def ledger(tmp_path: Path) -> SqliteLedger:
    """A ledger on a fixed clock."""
    return SqliteLedger(tmp_path / "ledger.sqlite", lambda: NOW)


def observed(store: SqliteLedger, cpus: int = 4, memory_gib: float = 16.0) -> dict[str, Any]:
    """Record one observation of a chosen machine and return the snapshot."""
    probes = fixed_probes(cpus, memory_gib)
    return discover(
        CTX, probes, ledger=store, clock=lambda: NOW, new_id=new_id, timer=time.monotonic
    )


def attempt(store: SqliteLedger, **choices: Any) -> dict[str, Any]:
    """One admission with the owner's context and the test job unless a choice says otherwise."""
    return admission.admit(
        choices.get("ctx", CTX),
        choices.get("operation", "analyse"),
        choices.get("key", new_id()),
        choices.get("task", TASK),
        workload=choices.get("workload", base_workload(CTX)),
        binding=LOCAL_DRAFT,
        ledger=store,
        clock=lambda: NOW,
        new_id=new_id,
    )


def written(store: SqliteLedger) -> dict[str, int]:
    """How many jobs, reservations and requests the ledger holds."""
    return {
        kind: len(store.current(CTX, kind)) for kind in ("Job", "Reservation", "ExecutionRequest")
    }


def refused_by(store: SqliteLedger, **choices: Any) -> DspError:
    """The error one admission raises."""
    with pytest.raises(DspError) as raised:
        attempt(store, **choices)
    return raised.value


def test_a18_role_operation_accelerator_and_charge_are_refused_before_any_work(
    tmp_path: Path,
) -> None:
    """A18, R05: role, operation, accelerator and charge are each refused before any work.

    A context without the scope, an operation nothing declares, an accelerator on a CPU option and
    a nonzero charge without a spend grant: no job or reservation exists for any of them, and every
    refusal but the authority one is recorded as a rejected request.
    """
    store = ledger(tmp_path)
    observed(store)
    base = base_workload(CTX)
    viewer = TrustedContext("viewer", CTX.tenant, frozenset({"workload:read"}))
    broad = base | {
        "execution_requirements": base["execution_requirements"]
        | {"required_operations": ["analyse", "prepare"]}
    }
    with_gpu = base | {"requested_resources": base["requested_resources"] | {"gpu_count": 1}}
    paid = base | {
        "requested_resources": base["requested_resources"] | {"max_external_charge_minor": 500},
        "execution_requirements": base["execution_requirements"]
        | {"no_external_charge_only": False},
    }
    for workload in (broad, with_gpu, paid):
        validate("WorkloadSpec", workload)
    cases = [
        ({"ctx": viewer}, ErrorCode.FORBIDDEN, "may not submit"),
        ({"operation": "train"}, ErrorCode.INPUT_INVALID, "not declared by the workload"),
        (
            {"operation": "prepare", "workload": broad},
            ErrorCode.INPUT_INVALID,
            "does not offer prepare",
        ),
        ({"workload": with_gpu}, ErrorCode.QUOTA_EXCEEDED, "accelerator"),
        ({"workload": paid}, ErrorCode.FORBIDDEN, "spend grant"),
    ]
    for choices, code, text in cases:
        error = refused_by(store, **choices)
        assert (error.code, text in error.message) == (code, True), choices
    assert written(store) == {"Job": 0, "Reservation": 0, "ExecutionRequest": 4}
    requests = store.current(CTX, "ExecutionRequest")
    for request in requests:
        validate("ExecutionRequest", request)
        assert (request["state"], request["authorisation_context_ref"]) == (
            "rejected",
            "owner-local",
        )
    rejections = [event for event in store.events(CTX) if event["type"] == "admission.rejected"]
    assert [event["body"]["code"] for event in rejections] == [
        ErrorCode.INPUT_INVALID,
        ErrorCode.INPUT_INVALID,
        ErrorCode.QUOTA_EXCEEDED,
        ErrorCode.FORBIDDEN,
    ]


def test_d05_an_admitted_job_holds_its_reservation_until_it_ends_and_its_key_is_idempotent(
    tmp_path: Path,
) -> None:
    """D05, D02: an admitted job holds its reservation until it ends; its key is idempotent.

    Admission pins the workload, binding and plan by digest, reserves at zero external charge and
    stores the workload; the same key with the same payload is the same job and with another
    payload a conflict; the terminal transition releases the reservation in its own commit.
    """
    store = ledger(tmp_path)
    snapshot = observed(store)
    job = attempt(store, key="k1")
    assert (job["state"], job["idempotency_key"], job["workload_ref"]) == (
        "queued",
        "k1",
        pin(base_workload(CTX)),
    )
    reservation = store.latest(CTX, "Reservation", job["reservation"])
    assert reservation is not None
    assert {
        key: reservation[key]
        for key in (
            "state",
            "job_ref",
            "cpu_cores",
            "memory_gib",
            "scratch_gib",
            "external_charge_minor",
            "currency",
        )
    } == {
        "state": "held",
        "job_ref": job["id"],
        "cpu_cores": 1,
        "memory_gib": 1,
        "scratch_gib": 1,
        "external_charge_minor": 0,
        "currency": "GBP",
    }
    request = store.get(CTX, "ExecutionRequest", job["request_ref"]["id"], "1.0.0")
    validate("ExecutionRequest", request)
    assert (request["state"], request["operation"], request["data_access"]) == (
        "admitted",
        "analyse",
        "permitted_snapshot",
    )
    assert (request["compute_binding_ref"], request["authorisation_context_ref"]) == (
        pin(LOCAL_DRAFT),
        "owner-local",
    )
    assert request["workload_ref"] == job["workload_ref"]
    assert request["requirement_revision"] == "1.0.0"
    plan = store.get(CTX, "WorkflowPlan", request["workflow_plan_ref"]["id"], "1.0.0")
    assert plan["hardware_snapshot_refs"][-1]["id"] == snapshot["id"]
    assert store.get(CTX, "WorkloadSpec", "workload-test-job", "1.0.0") == base_workload(CTX)
    assert LOCAL_DRAFT["capabilities"]["external_billing_possible"] is False

    assert attempt(store, key="k1") == job
    with pytest.raises(DspError) as raised:
        attempt(store, key="k1", task={"cues": ["sleep"], "seconds": 1})
    assert raised.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert written(store) == {"Job": 1, "Reservation": 1, "ExecutionRequest": 1}

    ended, _ = jobs.control(
        CTX,
        job["id"],
        "cancel",
        ledger=store,
        clock=lambda: NOW,
        new_id=new_id,
        workload=base_workload(CTX),
        binding=LOCAL_DRAFT,
    )
    released = store.latest(CTX, "Reservation", job["reservation"])
    assert ended["state"] == "cancelled"
    assert released is not None
    assert (released["state"], released["revision"], released["released_at"]) == (
        "released",
        "2.0.0",
        NOW,
    )
    assert [event["type"] for event in store.events(CTX)][-2:] == ["job.queued", "job.cancelled"]


def test_a33_a_plan_older_than_its_snapshot_is_rechecked_and_refused_when_capacity_fell(
    tmp_path: Path,
) -> None:
    """A33, D19: a plan older than its snapshot is rechecked and refused when capacity fell.

    Admission does not trust the stale plan: it proposes a fresh one from the current observation
    and refuses; when capacity is back the next admission pins a plan made from the current
    snapshot, and a current plan is reused rather than proposed again.
    """
    store = ledger(tmp_path)
    observed(store)
    first = propose_plan(CTX, ledger=store, new_id=new_id)
    small = observed(
        store, memory_gib=2.5
    )  # the 2 GiB host reserve leaves 0.5 GiB for 1 GiB needed
    error = refused_by(store)
    assert (error.code, "GiB memory" in error.message) == (ErrorCode.QUOTA_EXCEEDED, True)
    rejected = store.current(CTX, "ExecutionRequest")[-1]
    rechecked = store.get(CTX, "WorkflowPlan", rejected["workflow_plan_ref"]["id"], "1.0.0")
    assert rechecked["id"] != first["id"]
    assert rechecked["hardware_snapshot_refs"][-1]["id"] == small["id"]
    assert rechecked["supersedes_ref"]["id"] == first["id"]
    assert rechecked["feasibility_outcome"] == "FAIL"
    rejection = [event for event in store.events(CTX) if event["type"] == "admission.rejected"][-1]
    assert rejection["body"]["plan_rechecked"] is True
    assert written(store)["Job"] == 0

    big = observed(store)
    job = attempt(store)
    request = store.get(CTX, "ExecutionRequest", job["request_ref"]["id"], "1.0.0")
    fresh = store.get(CTX, "WorkflowPlan", request["workflow_plan_ref"]["id"], "1.0.0")
    assert fresh["hardware_snapshot_refs"][-1]["id"] == big["id"]
    assert fresh["id"] not in (first["id"], rechecked["id"])
    plans = len(store.current(CTX, "WorkflowPlan"))
    again = attempt(store)
    assert (
        store.get(CTX, "ExecutionRequest", again["request_ref"]["id"], "1.0.0")["workflow_plan_ref"]
        == request["workflow_plan_ref"]
    )
    assert len(store.current(CTX, "WorkflowPlan")) == plans


def test_a08_two_admissions_racing_for_the_last_reservation_never_exceed_the_cap(
    harness: tuple[httpx.Client, Clock], state_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A08, A33: two admissions racing for the last reservation never exceed the cap.

    With room for one more job, two requests race through the real harness five times over; each
    time exactly one is admitted and the other refused for capacity, what is held never exceeds
    the cap, and cancelling the winner gives the room back.
    """
    client, _ = harness
    monkeypatch.setattr(workspace, "probes", lambda state: fixed_probes(cpus=2, memory_gib=16))
    assert client.post("/v1/hardware").status_code == 200
    store = SqliteLedger(state_dir / "ledger.sqlite", lambda: NOW)

    def held() -> list[dict[str, Any]]:
        return [r for r in store.current(CTX, "Reservation") if r["state"] == "held"]

    for round_number in range(5):
        outcomes: list[httpx.Response] = []
        ready = threading.Barrier(2)

        def race(
            name: str,
            key: str = str(round_number),
            go: threading.Barrier = ready,
            done: list[httpx.Response] = outcomes,
        ) -> None:
            own = httpx.Client(base_url=client.base_url, headers=client.headers, timeout=30)
            body = {"operation": "analyse", "idempotency_key": f"{key}-{name}", "task": TASK}
            go.wait()
            done.append(own.post("/v1/jobs", json=body))

        racers = [threading.Thread(target=race, args=(name,)) for name in ("a", "b")]
        for racer in racers:
            racer.start()
        for racer in racers:
            racer.join()
        assert sorted(r.status_code for r in outcomes) == [200, 429], [r.text for r in outcomes]
        loser = next(r for r in outcomes if r.status_code == 429)
        assert loser.json()["code"] == ErrorCode.QUOTA_EXCEEDED
        assert [r["cpu_cores"] for r in held()] == [1]
        winner = next(r for r in outcomes if r.status_code == 200).json()["id"]
        assert client.post(
            f"/v1/jobs/{winner}/control", json={"command_id": winner, "action": "cancel"}
        ).json()["changed"]
        assert held() == []
    kinds = [event["type"] for event in client.get("/v1/events").json()["events"]]
    assert (kinds.count("job.queued"), kinds.count("admission.rejected")) == (5, 5)


@pytest.fixture
def api(tmp_path: Path) -> TestClient:
    """The harness API in-process, as served on port 4100 with credential ``secret``."""
    (tmp_path / "home").mkdir()
    app = create_app("secret", 4100)
    workspace.mount(app, tmp_path / "home")
    return TestClient(app, base_url="http://127.0.0.1:4100")


def test_admission_needs_an_observation_and_the_window_may_submit(api: TestClient) -> None:
    """D19: admission needs an observation; the window may submit once there is one.

    With nothing observed the window's request is refused and recorded; after discovery the same
    request is admitted; the plan now plans for the test job's WorkloadSpec.
    """
    validate("WorkloadSpec", base_workload(CTX))
    refused = api.post("/v1/jobs", headers=WINDOW, json=REQUEST)
    assert (refused.status_code, refused.json()["code"]) == (503, ErrorCode.DEPENDENCY_UNAVAILABLE)
    assert api.post("/v1/hardware", headers=WINDOW).status_code == 200
    plan = api.get("/v1/plan", headers=WINDOW).json()
    assert plan["workload_ref"] == {"id": "workload-test-job", "revision": "1.0.0", "sha256": None}
    assert plan["operating_bounds"]["max_task_seconds"] == 600
    admitted = api.post("/v1/jobs", headers=WINDOW, json=REQUEST)
    assert (admitted.status_code, admitted.json()["state"]) == (200, "queued")
    kinds = [event["type"] for event in api.get("/v1/events", headers=WINDOW).json()["events"]]
    assert kinds == ["admission.rejected", "discovery.finished", "plan.proposed", "job.queued"]
    assert (
        api.post("/v1/jobs", headers=WINDOW, json=REQUEST | {"operation": "launch"}).status_code
        == 400
    )
    assert api.post("/v1/jobs", headers=WINDOW, json={"task": TASK}).status_code == 400
