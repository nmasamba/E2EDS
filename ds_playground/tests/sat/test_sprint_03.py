"""Sprint 3 acceptance: jobs, admission, conversation and control, with evidence records."""

import json
import math
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.contracts.errors import ErrorCode, TrustedContext
from dsp.harness import workspace
from tests.conftest import Clock
from tests.integration.test_admission import attempt, fixed_probes, ledger, observed, refused_by
from tests.integration.test_controls import control, say
from tests.integration.test_jobs import (
    KILLED,
    events_of,
    job_of,
    kinds_of,
    replays_to,
    submit,
    until,
)
from tests.integration.test_revisions import change

Harness = tuple[httpx.Client, Clock]
Worker = Callable[..., subprocess.Popen[bytes]]
CTX = TrustedContext.local()
TRIALS = 20
MESSAGES = "/v1/conversations/conversation-local/messages"
SHA = "sha256:" + "d" * 64
FIXTURE = "the deterministic test worker (fixtures/worker.py) on a harness with a movable clock"


def p95(samples: list[float]) -> float:
    """The 95th percentile by nearest rank."""
    return sorted(samples)[math.ceil(0.95 * len(samples)) - 1]


@pytest.mark.slow
def test_a24_pause_and_cancel_receipts_are_durable_within_two_seconds_under_load(
    harness: Harness, worker: Worker, state_dir: Path, evidence: Callable[..., None]
) -> None:
    """A24, D18: pause and cancel receipts are durable within 2 s at p95 under load.

    With the hung test worker heartbeating and every processor saturated, the authenticated
    phrases "pause now" and "cancel this run" are each accepted, durably, within 2 s at p95 over
    20 trials; no new attempt is leased while paused; the actual stop is shown when the worker
    drains; a quoted phrase in document text has no authority.
    """
    client, _ = harness
    store = SqliteLedger(state_dir / "ledger.sqlite", lambda: "2026-10-08T10:00:00+00:00")
    busy = [
        subprocess.Popen([sys.executable, "-c", "while True: pass"])
        for _ in range(os.cpu_count() or 2)
    ]
    pauses: list[float] = []
    cancels: list[float] = []

    def shows(job_id: str, state: str) -> None:
        until(lambda: job_of(client, job_id)["state"] == state, 60)

    try:
        for trial in range(TRIALS):
            job = submit(client, "hang")
            draining = worker(job, f"w{trial}", heartbeat=0.2)
            shows(job, "running")
            if trial == 0:
                quoted = {"client_message_id": "doc", "expected_revision": "1.0.0"}
                quoted["text"] = 'From the uploaded document: "pause now" and "cancel this run".'
                assert client.post(MESSAGES, json=quoted).json()["state"] == "rejected"
                assert job_of(client, job)["state"] == "running"
            body = {"client_message_id": f"pause-{trial}", "text": "pause now"}
            started = time.perf_counter()
            answer = client.post(MESSAGES, json=body | {"expected_revision": "1.0.0"}).json()
            pauses.append(time.perf_counter() - started)
            assert (answer["state"], answer["job"]["state"]) == ("applied", "pause_requested")
            durable = store.latest(CTX, "Job", job)
            assert durable is not None
            assert durable["state"] in ("pause_requested", "paused")  # the worker may have drained
            refused = client.post(f"/v1/jobs/{job}/lease", json={"worker": "eager"})
            assert refused.json()["code"] in (ErrorCode.PAUSE_REQUESTED, ErrorCode.PAUSED)
            assert draining.wait(60) == 0
            shows(job, "paused")
            command = {"command_id": uuid.uuid4().hex, "action": "resume"}
            resumed = client.post(f"/v1/jobs/{job}/control", json=command)
            assert resumed.json()["job"]["state"] == "queued"
            second = worker(job, f"w{trial}b", heartbeat=0.2)
            shows(job, "running")
            body = {"client_message_id": f"cancel-{trial}", "text": "cancel this run"}
            started = time.perf_counter()
            answer = client.post(MESSAGES, json=body | {"expected_revision": "1.0.0"}).json()
            cancels.append(time.perf_counter() - started)
            assert (answer["state"], answer["job"]["state"]) == ("applied", "cancel_requested")
            durable = store.latest(CTX, "Job", job)
            assert durable is not None
            assert durable["state"] in ("cancel_requested", "cancelled")
            assert second.wait(60) == 0
            shows(job, "cancelled")
            final = job_of(client, job)
            assert final["stopped_at"] >= final["acknowledged_at"]
            assert final["charged_minor"] == 0
    finally:
        for process in busy:
            process.kill()
    pause_p95, cancel_p95 = p95(pauses), p95(cancels)
    actual = (
        f"{len(busy)} processors saturated, each trial's hung worker heartbeating; over {TRIALS} "
        f"trials each, 'pause now' was durable in p95 {pause_p95:.3f} s (max {max(pauses):.3f} s) "
        f"and 'cancel this run' in p95 {cancel_p95:.3f} s (max {max(cancels):.3f} s); no lease was "
        "granted while paused; each job showed paused or cancelled only after its worker stopped; "
        "incurred charge 0 shown; the quoted phrases in document text were rejected"
    )
    evidence(
        "A24",
        "control-liveness",
        "PASS" if max(pause_p95, cancel_p95) <= 2 else "FAIL",
        f"hung test worker, {len(busy)} busy processes, {TRIALS} pause and {TRIALS} cancel trials",
        "receipt persists within 2 s at p95 independent of model and task load; no new tool "
        "dispatch; actual stopping and cost shown; untrusted document instructions have no "
        "control authority",
        actual,
        "the fake generation is the hung test worker: no assistant model is bound until Sprint 5",
        sprint=3,
    )
    assert pause_p95 <= 2, actual
    assert cancel_p95 <= 2, actual


def test_a03_crash_and_lost_acknowledgement(
    harness: Harness, worker: Worker, evidence: Callable[..., None]
) -> None:
    """A03: a worker killed before its commit and one killed after; the same result key retried.

    Exactly one committed result per job, every attempt visible with its cost, no unbounded re-run.
    """
    client, clock = harness
    early = submit(client, "crash_before_commit", "sleep", seconds=0.2)
    assert worker(early, "first").wait(20) == KILLED
    clock.advance(61)
    assert worker(early, "second").wait(20) == 0
    late = submit(client, "crash_after_commit", seconds=0.1)
    assert worker(late, "third").wait(20) == KILLED
    committed = next(e for e in events_of(client, late) if e["type"] == "job.succeeded")
    body = committed["body"]["input"] | {"outcome": "succeeded"}
    assert client.post(f"/v1/jobs/{late}/report", json=body).json() == {
        "state": "succeeded",
        "committed": False,
    }
    early_kinds, late_kinds = kinds_of(client, early), kinds_of(client, late)
    assert (early_kinds.count("job.succeeded"), late_kinds.count("job.succeeded")) == (1, 1)
    assert early_kinds.count("job.started") == 2
    assert client.post(f"/v1/jobs/{early}/lease", json={"worker": "fourth"}).status_code == 409
    for job in (early, late):
        replays_to(client, job)
    evidence(
        "A03",
        "crash-and-lost-acknowledgement",
        "PASS",
        FIXTURE,
        "kill worker before and after commit; retry same result key; exactly one committed logical "
        "result, multiple attempts and costs visible, no unbounded re-run",
        f"attempt 1 of the first job died holding its lease and attempt 2 committed after expiry "
        f"({early_kinds}); the second job's worker committed then died and the retried key "
        "returned "
        f"the committed result without a new event ({late_kinds}); each job has one succeeded "
        "event, "
        f"attempts and charged_minor {job_of(client, early)['charged_minor']} are on the job; a "
        "further lease is refused; the events replay to the stored jobs",
        "the cost visible is what the test worker reports, which is zero",
        sprint=3,
    )


@pytest.mark.slow
def test_a04_stale_worker_is_fenced(
    harness: Harness, worker: Worker, evidence: Callable[..., None]
) -> None:
    """A04: the lease expires, a replacement is admitted, the old worker returns and is refused."""
    client, clock = harness
    job = submit(client, "sleep", seconds=4)
    old = worker(job, "old", heartbeat=0)
    until(lambda: job_of(client, job)["state"] == "running")
    clock.advance(61)
    new = worker(job, "new", heartbeat=0)
    until(lambda: job_of(client, job)["attempts"] == 2)
    assert (old.wait(20), new.wait(20)) == (3, 0)
    final = job_of(client, job)
    kinds = kinds_of(client, job)
    assert (final["state"], final["result"]["attempt"], kinds.count("job.succeeded")) == (
        "succeeded",
        2,
        1,
    )
    rejected = next(e for e in events_of(client, job) if e["type"] == "job.result_rejected")
    assert rejected["body"]["input"]["attempt"] == 1
    evidence(
        "A04",
        "stale-worker-fencing",
        "INSUFFICIENT_EVIDENCE",
        FIXTURE,
        "expire lease, admit permitted replacement, let old worker return: old commit rejected; no "
        "corrupted release pointer; orphan cost reconciled",
        f"the silent worker's lease expired, the fence advanced to {final['fence']}, the "
        "replacement "
        "leased attempt 2 and committed; the old worker's result was recorded as rejected and "
        "refused "
        f"({kinds}); one result stands",
        "no release pointer exists until Sprint 8 and no provider cost exists to reconcile, so "
        "those "
        "parts of the scenario were not exercised; the fencing itself held",
        sprint=3,
    )


def test_a07_cancellation(harness: Harness, worker: Worker, evidence: Callable[..., None]) -> None:
    """A07: cancel while queued, running with a checkpoint, and after success; a silent worker."""
    client, clock = harness
    queued = submit(client, "sleep")
    at_once = control(client, queued, "cancel")["job"]
    assert at_once["acknowledged_at"] == at_once["stopped_at"] is not None
    hung = submit(client, "hang")
    draining = worker(hung, heartbeat=0.2)
    until(lambda: job_of(client, hung)["state"] == "running")
    checkpoint = {"attempt": 1, "fence": 0, "sha256": SHA}
    assert client.post(f"/v1/jobs/{hung}/checkpoint", json=checkpoint).status_code == 200
    acknowledged = control(client, hung, "cancel")["job"]
    assert draining.wait(20) == 0
    until(lambda: job_of(client, hung)["state"] == "cancelled")
    stopped = job_of(client, hung)
    assert stopped["stopped_at"] >= acknowledged["acknowledged_at"]
    assert stopped["checkpoint"]["sha256"] == SHA
    assert control(client, hung, "resume")["state"] == "rejected"
    done = submit(client, "sleep", seconds=0.1)
    assert worker(done).wait(20) == 0
    assert control(client, done, "cancel")["state"] == "superseded"
    silent = submit(client, "hang")
    worker(silent, heartbeat=0)
    until(lambda: job_of(client, silent)["state"] == "running")
    control(client, silent, "cancel")
    clock.advance(61)
    reconciled = job_of(client, silent)
    assert (reconciled["state"], reconciled["reason"]) == (
        "cancelled",
        "reconciled after the lease expired",
    )
    evidence(
        "A07",
        "cancellation",
        "INSUFFICIENT_EVIDENCE",
        FIXTURE,
        "cancel queued, running and checkpointed jobs; record acknowledge and stop timestamps, "
        "checkpoint validity and incurred cost; simulate provider that continues charging; no "
        "false "
        "guarantee of cancellation",
        "queued cancelled at once with equal acknowledge and stop times; the running job with a "
        "checkpoint was acknowledged, fenced and stopped by its worker, keeping the checkpoint and "
        f"charged_minor {stopped['charged_minor']}, and cannot resume; a finished job stayed "
        "succeeded "
        "and the command was superseded; a silent worker's cancel was reconciled only when its "
        "lease "
        "expired, never claimed earlier",
        "no provider exists to keep charging, so that part was not exercised; cost is what the "
        "test "
        "worker reports",
        sprint=3,
    )


def test_a08_budget_race(
    harness: Harness,
    state_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    evidence: Callable[..., None],
) -> None:
    """A08: two admissions race for the last reservation, three times; the cap never breaks."""
    client, _ = harness
    monkeypatch.setattr(workspace, "probes", lambda state: fixed_probes(cpus=2, memory_gib=16))
    assert client.post("/v1/hardware").status_code == 200
    store = SqliteLedger(state_dir / "ledger.sqlite", lambda: "2026-10-08T10:00:00+00:00")
    outcomes: list[list[int]] = []
    for round_number in range(3):
        answers: list[httpx.Response] = []
        ready = threading.Barrier(2)

        def race(
            name: str,
            key: str = str(round_number),
            go: threading.Barrier = ready,
            done: list[httpx.Response] = answers,
        ) -> None:
            own = httpx.Client(base_url=client.base_url, headers=client.headers, timeout=30)
            body = {
                "operation": "analyse",
                "idempotency_key": f"{key}-{name}",
                "task": {"cues": ["hang"], "seconds": 0},
            }
            go.wait()
            done.append(own.post("/v1/jobs", json=body))

        racers = [threading.Thread(target=race, args=(name,)) for name in ("a", "b")]
        for racer in racers:
            racer.start()
        for racer in racers:
            racer.join()
        outcomes.append(sorted(r.status_code for r in answers))
        held = [r for r in store.current(CTX, "Reservation") if r["state"] == "held"]
        assert len(held) == 1
        winner = next(r for r in answers if r.status_code == 200).json()["id"]
        control(client, winner, "cancel")
    assert outcomes == [[200, 429]] * 3
    evidence(
        "A08",
        "budget-race",
        "INSUFFICIENT_EVIDENCE",
        "two threads racing POST /v1/jobs through the real harness on a two-processor observation",
        "two workers concurrently request last reservation; total granted envelope never exceeds "
        "approved cap; no new paid call after exhaustion; late receipts remain unsettled until "
        "reconciled",
        f"three rounds gave {outcomes}: one admitted, one refused QUOTA_EXCEEDED, one reservation "
        "held each time, released by the cancel",
        "no paid call or provider receipt exists yet, so exhaustion of spend and late receipts "
        "were "
        "not exercised; the external charge is zero by construction",
        sprint=3,
    )


def test_a25_pause_checkpoint_commit_race(
    harness: Harness, worker: Worker, evidence: Callable[..., None]
) -> None:
    """A25: queued, mid-run, draining with a checkpoint and completed work, paused and cancelled."""
    client, _ = harness
    queued = submit(client, "hang")
    assert control(client, queued, "pause")["job"]["state"] == "paused"
    assert control(client, queued, "resume")["job"]["state"] == "queued"
    control(client, queued, "cancel")
    job = submit(client, "hang")
    draining = worker(job, heartbeat=0.2)
    until(lambda: job_of(client, job)["state"] == "running")
    answers: dict[str, Any] = {}
    ready = threading.Barrier(2)

    def checkpoint() -> None:
        ready.wait()
        body = {"attempt": 1, "fence": 0, "sha256": SHA}
        answers["checkpoint"] = client.post(f"/v1/jobs/{job}/checkpoint", json=body).status_code

    def pause() -> None:
        ready.wait()
        answers["pause"] = control(client, job, "pause")["job"]["state"]

    racers = [threading.Thread(target=checkpoint), threading.Thread(target=pause)]
    for racer in racers:
        racer.start()
    for racer in racers:
        racer.join()
    assert answers == {"checkpoint": 200, "pause": "pause_requested"}
    until(lambda: job_of(client, job)["state"] == "paused")
    assert draining.wait(20) == 0
    late = {"attempt": 1, "fence": 0, "outcome": "succeeded", "key": "k", "sha256": SHA}
    assert client.post(f"/v1/jobs/{job}/report", json=late).status_code == 409
    paused = job_of(client, job)
    assert (paused["result"], paused["checkpoint"]["sha256"]) == (None, SHA)
    resumed = control(client, job, "resume")["job"]
    assert (resumed["state"], resumed["fence"]) == ("queued", 1)
    second = worker(job, heartbeat=0.2)
    until(lambda: job_of(client, job)["state"] == "running")
    control(client, job, "cancel")
    assert second.wait(20) == 0
    until(lambda: job_of(client, job)["state"] == "cancelled")
    assert "cancelled" in control(client, job, "resume")["because"]
    done = submit(client, "sleep", seconds=0.1)
    assert worker(done).wait(20) == 0
    assert control(client, done, "pause")["state"] == "rejected"
    evidence(
        "A25",
        "pause-checkpoint-commit-race",
        "INSUFFICIENT_EVIDENCE",
        FIXTURE,
        "exercise queued, mid-fit, checkpoint drain and already-completed work; fences reject "
        "stale "
        "success; authorised checkpoint receipts cannot promote; explicit resume uses compatible "
        "current revision/grant; cancelled jobs cannot resume",
        "a queued job paused and resumed; a checkpoint and a pause raced and both were recorded; "
        "the "
        "fenced attempt's success was refused after the pause; the checkpoint was kept across "
        "resume, "
        "which readmitted under the current revision with a new reservation and the advanced "
        "fence; "
        "the cancelled job could not resume; a finished job refused a pause",
        "nothing promotes until Sprint 8, so a checkpoint receipt had nothing to promote; the test "
        "worker is not a fit",
        sprint=3,
    )


def test_a26_mid_run_requirement_revision(
    harness: Harness, worker: Worker, monkeypatch: pytest.MonkeyPatch, evidence: Callable[..., None]
) -> None:
    """A26: exclude a field while work runs; diff, impact, new revision, invalidation, conflicts."""
    client, _ = harness
    monkeypatch.setattr(workspace, "probes", lambda state: fixed_probes(cpus=8, memory_gib=16))
    done = submit(client, "sleep", seconds=0.1)
    assert worker(done).wait(20) == 0
    hung = submit(client, "hang")
    draining = worker(hung, heartbeat=0.2)
    until(lambda: job_of(client, hung)["state"] == "running")
    before = job_of(client, done)
    applied = change(client, "exclude field region")
    assert (applied["state"], applied["workload"]["revision"]) == ("applied", "2.0.0")
    assert applied["impact"]["stale"] == [
        {"job": done, "kind": "result", "sha256": before["result"]["sha256"]}
    ]
    assert draining.wait(20) == 0
    until(lambda: job_of(client, hung)["state"] == "paused")
    assert job_of(client, done) == before
    conflicting = change(client, "exclude field item_count", expected="1.0.0")
    assert conflicting["because"] == "the requirements are at 2.0.0, not 1.0.0"
    assert change(client, "set budget to 500", expected="2.0.0")["state"] == "rejected"
    resumed = control(client, hung, "resume")["job"]
    assert resumed["workload_ref"]["revision"] == "2.0.0"
    control(client, hung, "cancel")
    evidence(
        "A26",
        "mid-run-requirement-revision",
        "INSUFFICIENT_EVIDENCE",
        FIXTURE + ", the test job's WorkloadSpec at revision 1.0.0",
        "exclude a feature/change search while work runs; record diff, impact, new version and "
        "invalidation; old results stay under old revision; simultaneous edits conflict "
        "predictably; "
        "changed final criteria/test exposure return to EO; production stays unchanged",
        "the exclusion became a typed patch, an impact naming the finished job's result as "
        "stale, and "
        "revision 2.0.0; the finished job's record and result were unchanged on 1.0.0; the "
        "running job "
        "was held and resumed under 2.0.0; an edit against the old revision was "
        "REVISION_CONFLICT; a "
        "budget change was refused for the owner's action",
        "no evaluation owner and no production exist yet, so the return to EO and an unchanged "
        "production were not exercised; the search space of this workload is empty",
        sprint=3,
    )


def test_a27_reconnect_and_command_replay(
    harness: Harness, worker: Worker, state_dir: Path, evidence: Callable[..., None]
) -> None:
    """A27: dropped acknowledgement, same-ID retry, conflict, cursor replay, a lost observer."""
    client, _ = harness
    job = submit(client, "hang")
    hung = worker(job, heartbeat=0.2)
    until(lambda: job_of(client, job)["state"] == "running")
    store = SqliteLedger(state_dir / "ledger.sqlite", lambda: "2026-10-08T10:00:00+00:00")
    body = json.dumps({"client_message_id": "m1", "text": "status", "expected_revision": "1.0.0"})
    port = int(str(client.base_url).rsplit(":", 1)[1])
    head = (
        f"POST {MESSAGES} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
        f"Authorization: {client.headers['authorization']}\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n\r\n"
    ).encode()
    with socket.create_connection(("127.0.0.1", port)) as raw:
        raw.sendall(head + body.encode())  # and leave without reading the answer
    until(lambda: bool(store.current(CTX, "ConversationCommand")))
    (dropped,) = store.current(CTX, "ConversationCommand")
    first = say(client, "status", "m1")
    assert first["command"] == dropped["id"]
    assert len(store.current(CTX, "ConversationCommand")) == 1
    conflict = client.post(
        MESSAGES,
        json={"client_message_id": "m1", "text": "pause now", "expected_revision": "1.0.0"},
    )
    assert (conflict.status_code, conflict.json()["code"]) == (409, ErrorCode.IDEMPOTENCY_CONFLICT)
    with client.stream("GET", "/v1/events/stream", timeout=30) as live:
        next(live.iter_lines())
    assert job_of(client, job)["state"] == "running"
    cursor = client.get("/v1/events").json()["cursor"]
    say(client, "pause now", "m2")
    replayed = client.get(f"/v1/events?after={cursor}").json()
    kinds = [e["type"] for e in replayed["events"] if e["type"] != "job.heartbeat"]
    assert kinds[:3] == ["message.received", "job.pause_requested", "command.applied"]
    assert [event["seq"] for event in replayed["events"]] == sorted(
        event["seq"] for event in replayed["events"]
    )
    reset = client.get("/v1/events?after=100000").json()
    assert (reset["reset"], len(reset["events"]) > 0) == (True, True)
    assert hung.wait(20) == 0
    evidence(
        "A27",
        "reconnect-and-command-replay",
        "PASS",
        FIXTURE,
        "drop message acknowledgement/SSE, retry same ID, reconnect with cursor; exactly one "
        "logical "
        "command, ordered replay and correct snapshot; same ID/different payload conflicts; lost "
        "GUI "
        "connection does not cancel job; expired history is explicit",
        "the first message went over a raw socket that closed before any answer; the retry with "
        "the same ID returned that command's receipt and one command exists; other text under it "
        "was IDEMPOTENCY_CONFLICT; an event stream opened and dropped left the job running; events "
        f"after the cursor replayed in sequence order ({kinds[:3]}); a cursor beyond the history "
        "was "
        "answered with an explicit reset and the full history",
        "no retention window exists yet, so nothing expires; an unknown cursor gets the whole "
        "history "
        "with the reset flag, which is the explicit answer",
        sprint=3,
    )


def test_a33_capacity_freshness(tmp_path: Path, evidence: Callable[..., None]) -> None:
    """A33: capacity changes after the plan; admission rechecks and refuses; later it admits."""
    store = ledger(tmp_path)
    observed(store, memory_gib=16)
    first = attempt(store)
    small = observed(store, memory_gib=2.5)
    error = refused_by(store)
    assert error.code is ErrorCode.QUOTA_EXCEEDED
    plans = store.current(CTX, "WorkflowPlan")
    assert plans[-1]["hardware_snapshot_refs"][-1]["id"] == small["id"]
    observed(store, memory_gib=16)
    second = attempt(store)
    assert second["id"] != first["id"]
    evidence(
        "A33",
        "capacity-freshness",
        "INSUFFICIENT_EVIDENCE",
        "fixed probes recording 16 GiB, then 2.5 GiB, then 16 GiB of memory on a four-processor "
        "host",
        "change available RAM/disk/binding after plan creation; race two admissions; resume after "
        "inventory expiry; fresh reservations prevent admitted overcommit; stale plan is "
        "rechecked; "
        "external memory pressure produces truthful failure/checkpoint state, never an unapproved "
        "model/provider switch",
        "after the plan, memory fell and admission re-proposed the plan from the new observation "
        "and "
        "refused QUOTA_EXCEEDED; when memory was back the next admission was admitted with a plan "
        "made from the latest observation; the race is A08 and resume rechecks are the A25 tests",
        "no model or provider exists to switch and no external memory pressure was applied; the "
        "truthful failure under pressure is not shown",
        sprint=3,
    )
