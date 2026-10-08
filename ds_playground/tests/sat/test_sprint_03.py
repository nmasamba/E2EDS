"""Sprint 3 acceptance: jobs, admission, conversation and control, with evidence records."""

import math
import os
import subprocess
import sys
import time
import uuid
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.contracts.errors import ErrorCode, TrustedContext
from tests.conftest import Clock
from tests.integration.test_jobs import job_of, submit, until

Harness = tuple[httpx.Client, Clock]
Worker = Callable[..., subprocess.Popen[bytes]]
CTX = TrustedContext.local()
TRIALS = 20
MESSAGES = "/v1/conversations/conversation-local/messages"


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
            assert durable["state"] == "pause_requested"
            refused = client.post(f"/v1/jobs/{job}/lease", json={"worker": "eager"})
            assert refused.json()["code"] == ErrorCode.PAUSE_REQUESTED
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
            assert durable["state"] == "cancel_requested"
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
