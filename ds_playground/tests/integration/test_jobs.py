"""The job coordinator driven for real: a harness on a movable clock and worker processes."""

import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.contracts.errors import ErrorCode, TrustedContext
from dsp.domain import jobs as machine
from dsp.harness import workspace
from dsp.harness.app import SHELL_ORIGIN, create_app
from tests.conftest import Clock

Harness = tuple[httpx.Client, Clock]
Worker = Callable[..., subprocess.Popen[bytes]]
SHA = "sha256:" + "a" * 64
KILLED = -9


def submit(client: httpx.Client, *cues: str, seconds: float = 0.0) -> str:
    """Queue a job for the test worker and return its ID."""
    answer = client.post("/v1/jobs", json={"task": {"cues": list(cues), "seconds": seconds}})
    assert answer.status_code == 200, answer.text
    return str(answer.json()["id"])


def job_of(client: httpx.Client, job_id: str) -> Any:
    """The job as the coordinator holds it now."""
    return client.get(f"/v1/jobs/{job_id}").json()


def events_of(client: httpx.Client, job_id: str) -> list[dict[str, Any]]:
    """This job's events in commit order, as the window replays them."""
    everything = client.get("/v1/events").json()["events"]
    return [event for event in everything if event["body"].get("job") == job_id]


def kinds_of(client: httpx.Client, job_id: str) -> list[str]:
    """The job's event types in commit order, heartbeats left out."""
    return [e["type"] for e in events_of(client, job_id) if e["type"] != "job.heartbeat"]


def until(condition: Callable[[], bool], seconds: float = 20) -> None:
    """Poll a condition for up to ``seconds``; fail if it never holds."""
    deadline = time.monotonic() + seconds
    while not condition():
        assert time.monotonic() < deadline, "the condition did not come true in time"
        time.sleep(0.05)


def control(client: httpx.Client, job_id: str, action: str) -> Any:
    """An explicit control sent the way the window sends it."""
    return client.post(f"/v1/jobs/{job_id}/control", json={"action": action}).json()


def replays_to(client: httpx.Client, job_id: str) -> None:
    """ADR02: folding the state machine over the job's events gives the job the ledger holds."""
    stored = job_of(client, job_id)
    first, *rest = events_of(client, job_id)
    job, _, _ = machine.new(job_id, first["body"]["input"]["task"], first["body"]["at"])
    for event in rest:
        body = event["body"]
        job, _, _ = machine.advance(job, body["action"], body["at"], **body["input"])
    assert job == stored


def test_a03_a_worker_killed_before_its_commit_is_retried_once_and_commits_one_result(
    harness: Harness, worker: Worker
) -> None:
    """A03: an attempt that dies before its commit is retried once; one result is committed.

    The first attempt dies holding its lease; after the lease expires a second attempt is leased
    and commits. Every attempt is visible, the result is committed exactly once, and a retry of
    the committed result key returns that result and writes nothing.
    """
    client, clock = harness
    job = submit(client, "crash_before_commit", "sleep", seconds=0.2)
    assert worker(job, "first").wait(20) == KILLED
    assert job_of(client, job)["state"] == "running"  # it leased, then died with the lease held
    held = client.post(f"/v1/jobs/{job}/lease", json={"worker": "eager"})
    assert (held.status_code, held.json()["code"]) == (409, ErrorCode.REVISION_CONFLICT)
    assert "attempt 1 holds the lease" in held.json()["message"]

    clock.advance(61)
    assert worker(job, "second").wait(20) == 0
    final = job_of(client, job)
    assert (final["state"], final["attempts"], final["failures"], final["fence"]) == (
        "succeeded",
        2,
        1,
        1,
    )
    assert final["result"]["attempt"] == 2
    kinds = kinds_of(client, job)
    assert kinds == ["job.queued", "job.started", "job.expired", "job.started", "job.succeeded"]
    started = [
        event["body"]["input"]["worker"]
        for event in events_of(client, job)
        if event["type"] == "job.started"
    ]
    assert started == ["first", "second"]

    committed = next(event for event in events_of(client, job) if event["type"] == "job.succeeded")
    retry = client.post(
        f"/v1/jobs/{job}/report", json=committed["body"]["input"] | {"outcome": "succeeded"}
    )
    assert retry.json() == {"state": "succeeded", "committed": False}
    assert kinds_of(client, job) == kinds
    replays_to(client, job)


def test_a03_a_worker_killed_after_its_commit_gets_that_result_on_retry_and_never_a_second(
    harness: Harness, worker: Worker
) -> None:
    """A03, D05: an attempt that dies after its commit gets that result on retry, never a second.

    The same key with other bytes, a new key and a new lease are all refused and the refusals
    are recorded; one result stays committed.
    """
    client, _ = harness
    job = submit(client, "crash_after_commit", seconds=0.1)
    assert worker(job).wait(20) == KILLED
    assert job_of(client, job)["state"] == "succeeded"
    committed = next(event for event in events_of(client, job) if event["type"] == "job.succeeded")
    report = f"/v1/jobs/{job}/report"
    same = committed["body"]["input"] | {"outcome": "succeeded"}
    assert client.post(report, json=same).json() == {"state": "succeeded", "committed": False}
    other_bytes = client.post(report, json=same | {"sha256": SHA})
    assert (other_bytes.status_code, other_bytes.json()["code"]) == (
        409,
        ErrorCode.IDEMPOTENCY_CONFLICT,
    )
    other_key = client.post(report, json=same | {"key": "another"})
    assert (other_key.status_code, other_key.json()["code"]) == (409, ErrorCode.REVISION_CONFLICT)
    again = client.post(f"/v1/jobs/{job}/lease", json={"worker": "late"})
    assert (again.status_code, again.json()["message"]) == (409, "the job is succeeded")
    kinds = kinds_of(client, job)
    assert kinds == [
        "job.queued",
        "job.started",
        "job.succeeded",
        "job.result_rejected",
        "job.result_rejected",
    ]
    rejected = [
        event["body"]["input"]["because"]
        for event in events_of(client, job)
        if event["type"] == "job.result_rejected"
    ]
    assert rejected == [ErrorCode.IDEMPOTENCY_CONFLICT, ErrorCode.REVISION_CONFLICT]
    final = job_of(client, job)
    assert (final["result"]["key"], final["result"]["attempt"], final["attempts"]) == (
        f"{job}:1",
        1,
        1,
    )
    replays_to(client, job)


@pytest.mark.slow
def test_a04_an_expired_lease_fences_the_old_worker_whose_late_commit_is_rejected(
    harness: Harness, worker: Worker
) -> None:
    """A04: an expired lease fences the old worker, whose late commit is rejected.

    The worker goes silent; its lease expires; a replacement is leased under a new fence; the old
    worker returns with its result and the fence rejects it; the replacement's result commits.
    """
    client, clock = harness
    job = submit(client, "sleep", seconds=4)
    old = worker(job, "old", heartbeat=0)
    until(lambda: job_of(client, job)["state"] == "running")
    assert job_of(client, job)["lease"]["attempt"] == 1
    clock.advance(61)
    new = worker(job, "new", heartbeat=0)
    until(lambda: job_of(client, job)["attempts"] == 2)
    assert (job_of(client, job)["fence"], job_of(client, job)["lease"]["worker"]) == (1, "new")
    assert old.wait(20) == 3
    assert new.wait(20) == 0
    final = job_of(client, job)
    assert (final["state"], final["result"]["attempt"], final["result"]["key"]) == (
        "succeeded",
        2,
        f"{job}:2",
    )
    kinds = kinds_of(client, job)
    assert kinds.count("job.succeeded") == 1
    assert kinds.count("job.result_rejected") == 1
    rejected = next(
        event for event in events_of(client, job) if event["type"] == "job.result_rejected"
    )
    assert rejected["body"]["input"] == {
        "attempt": 1,
        "fence": 0,
        "outcome": "succeeded",
        "because": ErrorCode.REVISION_CONFLICT,
    }
    assert kinds[:4] == ["job.queued", "job.started", "job.expired", "job.started"]
    replays_to(client, job)


def test_a07_cancel_while_queued_running_and_after_success(
    harness: Harness, worker: Worker
) -> None:
    """A07: cancel while queued, running and after success, with acknowledge and stop times.

    A queued job cancels at once with equal times; a running job is acknowledged, fenced and
    stopped by its worker; a finished job is left as it is and the answer says so.
    """
    client, _ = harness
    queued = submit(client, "sleep")
    answer = control(client, queued, "cancel")
    assert (answer["changed"], answer["job"]["state"]) == (True, "cancelled")
    assert answer["job"]["acknowledged_at"] == answer["job"]["stopped_at"] is not None
    assert control(client, queued, "cancel") == {"job": answer["job"], "changed": False}
    refused = client.post(f"/v1/jobs/{queued}/lease", json={"worker": "w"})
    assert (refused.status_code, refused.json()["code"]) == (409, ErrorCode.CANCELLED)

    hung = submit(client, "hang")
    draining = worker(hung, heartbeat=0.2)
    until(lambda: job_of(client, hung)["state"] == "running")
    acknowledged = control(client, hung, "cancel")["job"]
    assert (acknowledged["state"], acknowledged["fence"], acknowledged["stopped_at"]) == (
        "cancel_requested",
        1,
        None,
    )
    assert acknowledged["acknowledged_at"] is not None
    assert draining.wait(20) == 0
    stopped = job_of(client, hung)
    assert (stopped["state"], stopped["lease"]) == ("cancelled", None)
    assert stopped["stopped_at"] >= stopped["acknowledged_at"] == acknowledged["acknowledged_at"]
    late = client.post(
        f"/v1/jobs/{hung}/report",
        json={"attempt": 1, "fence": 0, "outcome": "succeeded", "key": "k", "sha256": SHA},
    )
    assert (late.status_code, late.json()["code"]) == (409, ErrorCode.CANCELLED)
    kinds = kinds_of(client, hung)
    assert kinds == [
        "job.queued",
        "job.started",
        "job.cancel_requested",
        "job.cancelled",
        "job.result_rejected",
    ]

    done = submit(client, "sleep", seconds=0.1)
    assert worker(done).wait(20) == 0
    before = events_of(client, done)
    assert control(client, done, "cancel") == {"job": job_of(client, done), "changed": False}
    assert job_of(client, done)["state"] == "succeeded"
    assert events_of(client, done) == before
    for job in (queued, hung, done):
        replays_to(client, job)


def test_a07_a_cancel_the_worker_never_answers_is_reconciled_when_its_lease_expires(
    harness: Harness, worker: Worker
) -> None:
    """A07, D03: a cancel the worker never answers is reconciled when its lease expires.

    Nothing claims the job stopped until then; it is then cancelled with the reason and a second
    fence.
    """
    client, clock = harness
    job = submit(client, "hang")
    silent = worker(job, heartbeat=0)
    until(lambda: job_of(client, job)["state"] == "running")
    assert control(client, job, "cancel")["job"]["state"] == "cancel_requested"
    time.sleep(0.5)
    assert (job_of(client, job)["state"], silent.poll()) == ("cancel_requested", None)
    clock.advance(61)
    reconciled = job_of(client, job)
    assert (reconciled["state"], reconciled["fence"], reconciled["reason"]) == (
        "cancelled",
        2,
        "reconciled after the lease expired",
    )
    assert reconciled["stopped_at"] is not None
    assert kinds_of(client, job)[-1] == "job.expired"
    replays_to(client, job)


def test_d03_the_third_transient_failure_is_final_and_a_final_failure_ends_at_once(
    harness: Harness, worker: Worker
) -> None:
    """D03: two automatic retries, then failed; a final failure ends the job at once.

    A fourth worker gets no lease.
    """
    client, _ = harness
    job = submit(client, "fail_transient")
    for attempt in (1, 2, 3):
        assert worker(job, f"w{attempt}").wait(20) == 0
        assert job_of(client, job)["state"] == ("failed" if attempt == 3 else "queued")
    assert worker(job, "w4").wait(20) == 3
    final = job_of(client, job)
    assert (final["attempts"], final["failures"], final["reason"]) == (3, 3, "fail_transient")
    kinds = kinds_of(client, job)
    assert kinds == [
        "job.queued",
        "job.started",
        "job.requeued",
        "job.started",
        "job.requeued",
        "job.started",
        "job.failed",
    ]
    fatal = submit(client, "fail_final")
    assert worker(fatal).wait(20) == 0
    assert (job_of(client, fatal)["state"], job_of(client, fatal)["attempts"]) == ("failed", 1)
    replays_to(client, job)


def test_a03_a_failure_inside_the_result_transaction_commits_neither_the_result_nor_its_event(
    tmp_path: Path,
) -> None:
    """A03: a failure inside the result transaction commits neither the result nor its event.

    The job stays at its previous revision and the retried commit lands exactly once.
    """
    ctx, broken = TrustedContext.local(), False

    def clock() -> str:
        if broken:
            raise RuntimeError("crash mid-transaction")
        return "2026-10-08T10:00:00+00:00"

    ledger = SqliteLedger(tmp_path / "ledger.sqlite", clock)
    job, kind, body = machine.new("job-1", {"cues": ["sleep"], "seconds": 1}, clock())
    ledger.commit(ctx, "job:job-1", 0, "e1", kind or "", body, [job])
    leased, kind, body = machine.advance(job, "lease", clock(), worker="w")
    ledger.commit(ctx, "job:job-1", 1, "e2", kind or "", body, [leased])
    done, kind, body = machine.advance(
        leased, "succeed", "2026-10-08T10:00:01+00:00", attempt=1, fence=0, key="k", sha256=SHA
    )
    broken = True
    with pytest.raises(RuntimeError):
        ledger.commit(ctx, "job:job-1", 2, "e3", kind or "", body, [done])
    assert ledger.latest(ctx, "Job", "job-1") == leased
    assert [event["type"] for event in ledger.events(ctx)] == ["job.queued", "job.started"]
    broken = False
    ledger.commit(ctx, "job:job-1", 2, "e3", kind or "", body, [done])
    assert ledger.latest(ctx, "Job", "job-1") == done
    assert ledger.seq(ctx, "job:job-1") == 3


NATIVE = {"Authorization": "Bearer secret"}
WINDOW = NATIVE | {"Origin": SHELL_ORIGIN}
WORKER_ROUTES = ("lease", "heartbeat", "report")


@pytest.fixture
def api(tmp_path: Path) -> TestClient:
    """The harness API in-process, as served on port 4100 with credential ``secret``."""
    (tmp_path / "home").mkdir()
    app = create_app("secret", 4100)
    workspace.mount(app, tmp_path / "home")
    return TestClient(app, base_url="http://127.0.0.1:4100")


def test_the_window_may_submit_and_cancel_but_is_not_a_worker(api: TestClient) -> None:
    """C23: the window may queue and control jobs but is not a worker.

    Leases, heartbeats and reports are refused with an Origin; every job route needs the token;
    a malformed task and an unknown job are refused.
    """
    queued = api.post("/v1/jobs", headers=WINDOW, json={"task": {"cues": ["hang"], "seconds": 0}})
    assert queued.status_code == 200, queued.text
    job = queued.json()["id"]
    for route in WORKER_ROUTES:
        refused = api.post(
            f"/v1/jobs/{job}/{route}",
            headers=WINDOW,
            json={"worker": "w", "attempt": 1, "fence": 0, "outcome": "stopped"},
        )
        assert (refused.status_code, refused.json()["code"]) == (403, ErrorCode.FORBIDDEN), route
        assert api.post(f"/v1/jobs/{job}/{route}", json={}).status_code == 401
    assert api.post("/v1/jobs", json={}).status_code == 401
    assert api.get(f"/v1/jobs/{job}").status_code == 401
    assert api.post(f"/v1/jobs/{job}/control", json={}).status_code == 401
    assert api.post(f"/v1/jobs/{job}/control", headers=WINDOW, json={"action": "cancel"}).json()[
        "changed"
    ]
    assert api.get("/v1/jobs/job-absent", headers=WINDOW).status_code == 404
    bad = api.post("/v1/jobs", headers=NATIVE, json={"task": {"cues": [], "seconds": 0}})
    assert (bad.status_code, bad.json()["code"]) == (400, ErrorCode.INPUT_INVALID)
    assert (
        api.post(
            "/v1/jobs", headers=NATIVE, json={"task": {"cues": ["nap"], "seconds": 0}}
        ).status_code
        == 400
    )
    assert (
        api.post(f"/v1/jobs/{job}/control", headers=NATIVE, json={"action": "pause"}).status_code
        == 400
    )
    assert (
        api.post(
            "/v1/jobs",
            headers=NATIVE,
            json={"task": {"cues": ["hang"], "seconds": 0, "path": "/x"}},
        ).status_code
        == 400
    )
