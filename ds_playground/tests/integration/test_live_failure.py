"""Failure and independence against the real model (5.5; live_model).

These tests hang, starve and kill the session's model server, so they run after the other live
tests (the conftest orders them last) and each later test starts from the server it left.
"""

import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.application.assistant import Assistant
from dsp.contracts.canonical import pin
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from tests.conftest import Clock
from tests.integration.conftest import Lent
from tests.integration.test_assistant_loop import ended, ready
from tests.integration.test_controls import control, say
from tests.integration.test_jobs import job_of, submit, until
from tests.integration.test_live_gateway import make
from tests.sat.test_sprint_03 import p95

pytestmark = pytest.mark.live_model
CTX = TrustedContext.local()
Harness = tuple[httpx.Client, Clock]
Worker = Callable[..., subprocess.Popen[bytes]]
TRIALS = 20


@pytest.fixture
def assistant(model_server: Any, state_dir: Path) -> Assistant:
    """A harness's assistant on the session's server, lent with its real stop and restart."""
    clock = Clock()
    return Assistant(
        CTX,
        Lent(model_server),
        ledger=lambda: SqliteLedger(state_dir / "ledger.sqlite", clock),
        clock=clock,
    )


def reached(client: httpx.Client, job: str, state: str) -> Callable[[], bool]:
    """A probe that one job, bound here, is in a state."""
    return lambda: bool(job_of(client, job)["state"] == state)


LONG = (  # what the model is asked for: one of these keeps it generating for seconds
    "write a long essay about rivers, at least 600 words, as your answer",
    "list the integers from 1 to 400, one per line, as your answer",
    "describe each of the seven continents in a paragraph of its own, as your answer",
)


def hung_generation(client: httpx.Client, model_server: Any) -> tuple[str, int]:
    """An assistant job whose generation is in progress on a server now stopped with SIGSTOP.

    The model may answer a request briefly (it refused the essay once in a second), so the
    requests are tried in turn until one is still generating 1.5 s after the job began.
    """
    for text in LONG:
        job = str(say(client, text)["job"]["id"])
        until(reached(client, job, "running"), 60)
        time.sleep(1.5)
        pid = int(model_server.process.pid)
        if job_of(client, job)["state"] == "running":
            os.kill(pid, signal.SIGSTOP)
            if job_of(client, job)["state"] == "running":
                return job, pid
            os.kill(pid, signal.SIGCONT)
        ended(client, job, 300)
    raise AssertionError("no request kept the model generating for 1.5 s")


def events(client: httpx.Client) -> list[dict[str, Any]]:
    """Every event, in commit order."""
    found: list[dict[str, Any]] = client.get("/v1/events").json()["events"]
    return found


@pytest.mark.slow
def test_a24_pause_and_cancel_receipts_are_durable_within_two_seconds_under_a_hung_generation(
    harness: Harness, model_server: Any, worker: Worker, evidence: Callable[..., None]
) -> None:
    """A24, D18: receipts stay within 2 s at p95 with the model server stopped mid-generation.

    Every processor is busy too; a pause of the hung assistant job is durable and nothing it
    proposes afterwards is dispatched; the generation ends when the server resumes.
    """
    client, _ = harness
    ready(client, 300)  # the previous test's harness stopped the lent server: a real restart
    job, pid = hung_generation(client, model_server)  # a genuinely hung generation
    busy = [
        subprocess.Popen([sys.executable, "-c", "while True: pass"])
        for _ in range(os.cpu_count() or 2)
    ]
    pauses: list[float] = []
    cancels: list[float] = []
    try:
        for trial in range(TRIALS):
            hung = submit(client, "hang")
            draining = worker(hung, f"w{trial}", heartbeat=0.2)
            until(reached(client, hung, "running"), 60)
            started = time.perf_counter()
            paused = control(client, hung, "pause")
            pauses.append(time.perf_counter() - started)
            assert paused["job"]["state"] == "pause_requested"
            assert draining.wait(60) == 0
            until(reached(client, hung, "paused"), 60)
            assert control(client, hung, "resume")["job"]["state"] == "queued"
            second = worker(hung, f"w{trial}b", heartbeat=0.2)
            until(reached(client, hung, "running"), 60)
            started = time.perf_counter()
            cancelled = control(client, hung, "cancel")
            cancels.append(time.perf_counter() - started)
            assert cancelled["job"]["state"] == "cancel_requested"
            assert second.wait(60) == 0
            until(reached(client, hung, "cancelled"), 60)
        started = time.perf_counter()
        held = control(client, job, "pause")
        pauses.append(time.perf_counter() - started)
        assert held["job"]["state"] == "pause_requested"
    finally:
        for process in busy:
            process.kill()
        os.kill(pid, signal.SIGCONT)
    until(lambda: job_of(client, job)["state"] == "paused", 400)
    assert not [e for e in events(client) if e["type"] == "assistant.call_dispatched"]
    assert model_server.alive()
    pause_p95, cancel_p95 = p95(pauses), p95(cancels)
    actual = (
        f"the model server was stopped with SIGSTOP during a generation and {len(busy)} busy "
        f"processes held every processor; over {TRIALS} trials pause was durable in p95 "
        f"{pause_p95:.3f} s (max {max(pauses):.3f} s) and cancel in p95 {cancel_p95:.3f} s (max "
        f"{max(cancels):.3f} s); the hung assistant job's own pause was durable in "
        f"{pauses[-1]:.3f} s, it showed paused once the server resumed, and no call was dispatched"
    )
    evidence(
        "A24",
        "control-liveness-hung-generation",
        "PASS" if max(pause_p95, cancel_p95) <= 2 else "FAIL",
        f"the real model server (Metal) stopped mid-generation, {len(busy)} busy processes, "
        f"{TRIALS} pause and {TRIALS} cancel trials on hung test-worker jobs",
        "receipt persists within 2 s at p95 independent of model and task load; no new tool "
        "dispatch after an accepted pause; actual stopping shown",
        actual,
        "the generation itself ends only when the server resumes or the deadline kills it",
        sprint=5,
    )
    assert pause_p95 <= 2, actual
    assert cancel_p95 <= 2, actual
    assert control(client, job, "cancel")["job"]["state"] in ("cancel_requested", "cancelled")


def test_r16_a_hung_server_is_killed_at_the_deadline_and_the_assistant_recovers_on_the_same_binding(
    harness: Harness, model_server: Any, assistant: Assistant, state_dir: Path
) -> None:
    """R16, R18: past the deadline the hung server is killed and the same binding is restarted.

    The task fails, the command says so, the controls still answer, and no other model is tried.
    """
    client, _ = harness
    ready(client, 300)  # the previous test's harness stopped the lent server: a real restart
    assistant.binding["limits"]["generation_deadline_seconds"] = 5
    before = pin(assistant.binding)
    job, pid = hung_generation(client, model_server)
    done = ended(client, job, 120)
    assert (done["state"], done["reason"]) == (
        "failed",
        "no answer within the 5 s generation deadline",
    )
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)  # killed, not left stopped
    rejected = [e["body"] for e in events(client) if e["type"] == "command.rejected"]
    assert (rejected[-1]["because"], rejected[-1]["reason"]) == (
        ErrorCode.ASSISTANT_UNAVAILABLE,
        "no answer within the 5 s generation deadline",
    )
    assert say(client, "status")["because"] == "no job is live"
    until(lambda: [e["type"] for e in events(client)].count("assistant.ready") == 2, 300)
    assert client.get("/v1/assistant").json()["state"] == "ready"
    kinds = [e["type"] for e in events(client)]
    assert kinds.count("assistant.unavailable") == 1
    ready_events = [e["body"] for e in events(client) if e["type"] == "assistant.ready"]
    assert ready_events[-1]["binding"]["id"] == before["id"]  # the same binding, no other model
    assert model_server.process.pid != pid
    again = say(client, "What is 7 times 8? Answer with the number only.")
    assert ended(client, again["job"]["id"], 120)["state"] == "succeeded"


def test_r16_out_of_memory_ends_in_unavailable_and_no_server_remains(
    model_server: Any, tmp_path: Path
) -> None:
    """R16, D16: a model that does not fit its memory limit never becomes ready; nothing stays.

    Inadequate hardware is said truthfully, before any answer, with the limit the binding declares.
    """
    model_server.stop()  # one server at a time fits the Linux container
    adapter = make(tmp_path / "home")
    adapter.binding["limits"]["model_memory_gib"] = 0.5
    started = time.monotonic()
    try:
        with pytest.raises(DspError) as refused:
            adapter.start()
    finally:
        adapter.stop()  # a server a failed check left behind would hold the port for every run
    seconds = time.monotonic() - started
    message = refused.value.message
    assert "memory_limit" in message or "exited with status" in message, message
    assert adapter.process is not None
    assert adapter.process.poll() is not None
    assert not (adapter.state / "api-key").exists()
    assert seconds < 300
