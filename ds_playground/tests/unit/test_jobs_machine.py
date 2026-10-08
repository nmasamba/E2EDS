from datetime import datetime, timedelta
from typing import Any

import pytest

from dsp.contracts.errors import DspError, ErrorCode
from dsp.contracts.schemas import validate
from dsp.domain import jobs as machine

T0 = "2026-10-08T10:00:00+00:00"
SHA = "sha256:" + "b" * 64


def at(seconds: float) -> str:
    """A time ``seconds`` after T0."""
    return (datetime.fromisoformat(T0) + timedelta(seconds=seconds)).isoformat()


def step(job: dict[str, Any], action: str, when: float, **given: Any) -> dict[str, Any]:
    """Advance, check the successor against the schema and return it."""
    successor, kind, body = machine.advance(job, action, at(when), **given)
    validate("Job", successor)
    assert (body == {}) is (kind is None) or action == "reject"
    return successor


def refused(job: dict[str, Any], action: str, when: float, **given: Any) -> DspError:
    """The error the machine raises for an action its state forbids."""
    with pytest.raises(DspError) as raised:
        machine.advance(job, action, at(when), **given)
    return raised.value


@pytest.fixture
def running() -> dict[str, Any]:
    """A job leased to its first attempt at T0 + 1 s."""
    job, kind, body = machine.new("job-1", {"cues": ["sleep"], "seconds": 1}, T0)
    assert (kind, body["state"], job["revision"]) == ("job.queued", "queued", "1.0.0")
    validate("Job", job)
    return step(job, "lease", 1, worker="w1")


def test_d03_a_lease_lasts_60_seconds_and_a_heartbeat_extends_it(running: dict[str, Any]) -> None:
    """D03: the lease ends 60 s after it was taken or last heartbeat; it is due at that second."""
    assert running["lease"] == {"attempt": 1, "fence": 0, "worker": "w1", "expires_at": at(61)}
    assert (running["state"], running["attempts"], running["revision"]) == ("running", 1, "2.0.0")
    assert not machine.due(running, at(60.999))
    assert machine.due(running, at(61))
    beat = step(running, "heartbeat", 30, attempt=1, fence=0)
    assert (beat["lease"]["expires_at"], beat["state"]) == (at(90), "running")
    assert not machine.due(beat, at(61))
    assert refused(running, "heartbeat", 30, attempt=2, fence=0).code is ErrorCode.REVISION_CONFLICT
    assert refused(running, "heartbeat", 30, attempt=1, fence=1).code is ErrorCode.REVISION_CONFLICT


def test_a04_expiry_advances_the_fence_and_the_fenced_attempt_cannot_commit(
    running: dict[str, Any],
) -> None:
    """A04: expiry fences the attempt; a replacement is leased; the old result is refused."""
    expired = step(running, "expire", 61)
    assert (expired["state"], expired["fence"], expired["failures"], expired["lease"]) == (
        "queued",
        1,
        1,
        None,
    )
    assert expired["reason"] == "the lease expired without a heartbeat"
    replacement = step(expired, "lease", 62, worker="w2")
    assert replacement["lease"] == {"attempt": 2, "fence": 1, "worker": "w2", "expires_at": at(122)}
    stale = refused(replacement, "succeed", 70, attempt=1, fence=0, key="k1", sha256=SHA)
    assert stale.code is ErrorCode.REVISION_CONFLICT
    assert stale.details == {"state": "running", "fence": 1}
    done = step(
        replacement, "succeed", 70, attempt=2, fence=1, key="k2", sha256=SHA, charge_minor=3
    )
    assert done["result"] == {"key": "k2", "sha256": SHA, "attempt": 2, "at": at(70)}
    assert (done["state"], done["lease"], done["charged_minor"]) == ("succeeded", None, 3)
    assert refused(done, "lease", 71, worker="w3").message == "the job is succeeded"


def test_d03_the_third_transient_failure_is_final(running: dict[str, Any]) -> None:
    """D03: two automatic retries after the first attempt; a final failure ends the job at once."""
    job = running
    for attempt in (1, 2):
        job = step(job, "fail", 10 * attempt, attempt=attempt, fence=0, transient=True, reason="io")
        assert (job["state"], job["failures"]) == ("queued", attempt)
        job = step(job, "lease", 10 * attempt + 1, worker=f"w{attempt + 1}")
    job = step(job, "fail", 30, attempt=3, fence=0, transient=True, reason="io")
    assert (job["state"], job["attempts"], job["failures"], job["reason"]) == ("failed", 3, 3, "io")
    assert refused(job, "lease", 31, worker="w4").code is ErrorCode.REVISION_CONFLICT
    final = step(running, "fail", 2, attempt=1, fence=0, transient=False, reason="bad input")
    assert (final["state"], final["attempts"]) == ("failed", 1)
    with pytest.raises(DspError) as unknown:
        machine.advance(running, "launch", at(3))
    assert unknown.value.code is ErrorCode.INPUT_INVALID


def test_a07_cancel_in_every_state_records_acknowledge_and_stop(running: dict[str, Any]) -> None:
    """A07: queued cancels at once; running is requested, fenced, stopped; done is untouched."""
    queued, _, _ = machine.new("job-2", {"cues": ["sleep"], "seconds": 1}, T0)
    cancelled = step(queued, "cancel", 5)
    assert (cancelled["state"], cancelled["acknowledged_at"], cancelled["stopped_at"]) == (
        "cancelled",
        at(5),
        at(5),
    )
    assert machine.advance(cancelled, "cancel", 6) == (cancelled, None, {})
    assert refused(cancelled, "lease", 7, worker="w").code is ErrorCode.CANCELLED

    requested = step(running, "cancel", 10)
    assert (requested["state"], requested["fence"], requested["acknowledged_at"]) == (
        "cancel_requested",
        1,
        at(10),
    )
    assert requested["stopped_at"] is None
    assert refused(requested, "lease", 11, worker="w2").code is ErrorCode.CANCEL_REQUESTED
    late = refused(requested, "succeed", 12, attempt=1, fence=0, key="k", sha256=SHA)
    assert late.code is ErrorCode.CANCEL_REQUESTED
    held = refused(requested, "checkpoint", 12, attempt=1, fence=0, sha256=SHA)
    assert held.code is ErrorCode.CANCEL_REQUESTED
    draining = step(requested, "heartbeat", 12, attempt=1, fence=0)
    assert draining["state"] == "cancel_requested"
    assert refused(draining, "stop", 13, attempt=1, fence=1).code is ErrorCode.CANCEL_REQUESTED
    stopped = step(draining, "stop", 13, attempt=1, fence=0, charge_minor=2)
    assert (
        stopped["state"],
        stopped["stopped_at"],
        stopped["lease"],
        stopped["charged_minor"],
    ) == (
        "cancelled",
        at(13),
        None,
        2,
    )
    assert machine.advance(stopped, "cancel", 14) == (stopped, None, {})
    assert refused(stopped, "stop", 14, attempt=1, fence=0).code is ErrorCode.CANCELLED

    done = step(running, "succeed", 20, attempt=1, fence=0, key="k", sha256=SHA)
    assert machine.advance(done, "cancel", 21) == (done, None, {})
    assert refused(done, "stop", 22, attempt=1, fence=0).code is ErrorCode.REVISION_CONFLICT


def test_a07_a_cancel_nobody_answers_is_reconciled_at_lease_expiry(running: dict[str, Any]) -> None:
    """A07, D03: a cancel request the worker never answers ends in cancelled at lease expiry."""
    requested = step(running, "cancel", 10)
    reconciled = step(requested, "expire", 61)
    assert (reconciled["state"], reconciled["fence"]) == ("cancelled", 2)
    assert reconciled["stopped_at"] == at(61)
    assert reconciled["reason"] == "reconciled after the lease expired"
    assert refused(reconciled, "expire", 62).code is ErrorCode.CANCELLED


def test_a25_a_checkpoint_is_recorded_and_the_result_still_needs_the_current_fence(
    running: dict[str, Any],
) -> None:
    """A25: a durable checkpoint moves running to checkpointed; the fence rule is unchanged."""
    checkpointed = step(running, "checkpoint", 5, attempt=1, fence=0, sha256=SHA)
    assert checkpointed["state"] == "checkpointed"
    assert checkpointed["checkpoint"] == {"attempt": 1, "sha256": SHA, "at": at(5)}
    again = step(checkpointed, "checkpoint", 6, attempt=1, fence=0, sha256=SHA)
    assert again["state"] == "checkpointed"
    stale = refused(checkpointed, "checkpoint", 7, attempt=1, fence=1, sha256=SHA)
    assert stale.code is ErrorCode.REVISION_CONFLICT
    done = step(checkpointed, "succeed", 8, attempt=1, fence=0, key="k", sha256=SHA)
    assert done["state"] == "succeeded"
    expired = step(checkpointed, "expire", 65)
    assert (expired["state"], expired["checkpoint"]["attempt"]) == ("queued", 1)


def test_a03_a_committed_result_key_is_recognised_and_other_bytes_under_it_conflict(
    running: dict[str, Any],
) -> None:
    """A03, D05: the same key with the same digest is the committed result; other bytes conflict."""
    assert not machine.committed(running, "k", SHA)
    done = step(running, "succeed", 8, attempt=1, fence=0, key="k", sha256=SHA)
    assert machine.committed(done, "k", SHA)
    assert not machine.committed(done, "other", SHA)
    with pytest.raises(DspError) as raised:
        machine.committed(done, "k", "sha256:" + "c" * 64)
    assert raised.value.code is ErrorCode.IDEMPOTENCY_CONFLICT


def test_every_transition_is_a_new_revision_with_a_replayable_event(
    running: dict[str, Any],
) -> None:
    """ADR02: revisions advance by one, a rejection records without a revision, bodies replay."""
    job, kind, body = machine.advance(running, "heartbeat", at(2), attempt=1, fence=0)
    assert (job["revision"], kind) == ("3.0.0", "job.heartbeat")
    assert body == {
        "job": "job-1",
        "action": "heartbeat",
        "at": at(2),
        "input": {"attempt": 1, "fence": 0},
        "state": "running",
        "attempt": 1,
        "fence": 0,
    }
    assert machine.advance(running, body["action"], body["at"], **body["input"])[0] == job
    same, kind, noted = machine.advance(job, "reject", at(3), attempt=9, fence=9, outcome="x")
    assert (same is job, kind) == (True, "job.result_rejected")
    assert noted["input"] == {"attempt": 9, "fence": 9, "outcome": "x"}
    assert machine.advance(job, "touch", at(4)) == (job, None, {})
