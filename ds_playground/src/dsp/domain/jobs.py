"""The job state machine of ../architecture.md "Job state machine", as a pure function.

``advance`` maps a job, an action and the injected time to the successor revision and the event
that records it; the coordinator commits both in one ledger transaction under compare-and-swap.
Nothing here reads a clock, makes an ID or touches storage, so a job's events replay to its state.
"""

from datetime import datetime, timedelta
from typing import Any

from dsp.contracts.errors import DspError, ErrorCode

LEASE_SECONDS = 60  # D03
HEARTBEAT_SECONDS = 15  # D03
RETRIES = 2  # D03: automatic retries after the first attempt, for transient faults only
LIVE = frozenset({"running", "checkpointed", "pause_requested", "cancel_requested"})
RELEASES = frozenset({"succeeded", "failed", "cancelled"})  # states that give the reservation back
REFUSAL = {
    "paused": ErrorCode.PAUSED,
    "pause_requested": ErrorCode.PAUSE_REQUESTED,
    "cancel_requested": ErrorCode.CANCEL_REQUESTED,
    "cancelled": ErrorCode.CANCELLED,
}
Transition = tuple[dict[str, Any], str | None, dict[str, Any]]


def new(job_id: str, at: str, **fields: Any) -> Transition:
    """Return a queued job (revision 1.0.0, fence 0, no attempt yet) and its first event.

    ``fields`` are what admission settled: the task, the pinned request and workload, the
    reservation and the idempotency key.
    """
    job = {
        "schema_version": "0.1.0",
        "type": "Job",
        "id": job_id,
        "revision": "1.0.0",
        "state": "queued",
        **fields,
        "submitted_at": at,
        "attempts": 0,
        "fence": 0,
        "failures": 0,
        "lease": None,
        "checkpoint": None,
        "result": None,
        "charged_minor": 0,
        "acknowledged_at": None,
        "stopped_at": None,
        "reason": None,
    }
    return job, "job.queued", _body(job, "queue", at, fields)


def due(job: dict[str, Any], at: str) -> bool:
    """True when the live attempt's lease has run out, so the fence must advance first."""
    lease = job["lease"]
    return bool(lease) and datetime.fromisoformat(at) >= datetime.fromisoformat(lease["expires_at"])


def committed(job: dict[str, Any], key: str, sha256: str) -> bool:
    """True when this result key is already committed with these bytes (A03: a retried commit).

    The same key with other bytes is an IDEMPOTENCY_CONFLICT: quarantined, never merged.
    """
    result = job["result"]
    if not result or result["key"] != key:
        return False
    if result["sha256"] != sha256:
        raise DspError(
            ErrorCode.IDEMPOTENCY_CONFLICT, f"result {key} was committed with other bytes"
        )
    return True


def advance(job: dict[str, Any], action: str, at: str, **given: Any) -> Transition:
    """Apply one action and return the successor, the event type and the event body.

    A request that changes nothing (cancelling a finished job, a touch that finds nothing due)
    returns the job unchanged and no event; a request the state forbids raises with the code that
    names the state. ``attempt`` and ``fence`` identify the worker's attempt. Pause, cancel and
    lease expiry each advance the fence and take the job out of the states that accept a result,
    so the attempt they fenced can still report that it stopped but can never commit a result.
    """
    state, lease = job["state"], job["lease"]
    asked = (given.get("attempt"), given.get("fence"))
    mine = bool(lease) and (lease["attempt"], lease["fence"]) == asked
    charged = job["charged_minor"] + given.get("charge_minor", 0)
    change: dict[str, Any]
    kind: str | None
    match action:
        case "touch":
            return job, None, {}
        case "lease":
            if state != "queued":
                held = f"; attempt {lease['attempt']} holds the lease" if lease else ""
                raise _refusal(job, f"the job is {state}{held}")
            attempt = job["attempts"] + 1
            lease = {"attempt": attempt, "fence": job["fence"], "worker": given["worker"]}
            lease["expires_at"] = _later(at, LEASE_SECONDS)
            change = {"state": "running", "attempts": attempt, "lease": lease, "reason": None}
            kind = "job.started"
        case "heartbeat":
            if not mine or state not in LIVE:
                raise _refusal(job, "not the live attempt")
            change = {"lease": lease | {"expires_at": _later(at, LEASE_SECONDS)}}
            kind = "job.heartbeat"
        case "checkpoint":
            if not mine or state not in ("running", "checkpointed", "pause_requested"):
                raise _refusal(job, "no checkpoint is taken now")
            checkpoint = {"attempt": lease["attempt"], "sha256": given["sha256"], "at": at}
            change = {"state": "checkpointed" if state == "running" else state}
            change["checkpoint"] = checkpoint
            kind = "job.checkpointed"
        case "succeed":
            if not mine or state not in ("running", "checkpointed"):
                raise _refusal(job, "the fence rejects this result")
            result = {"key": given["key"], "sha256": given["sha256"], "attempt": lease["attempt"]}
            change = {"state": "succeeded", "lease": None, "charged_minor": charged}
            change["result"] = result | {"at": at}
            kind = "job.succeeded"
        case "fail":
            if not mine or state not in ("running", "checkpointed"):
                raise _refusal(job, "the fence rejects this report")
            change = _over(job, given["transient"], given["reason"]) | {"charged_minor": charged}
            kind = "job.failed" if change["state"] == "failed" else "job.requeued"
        case "expire":
            if not lease:
                raise _refusal(job, "no lease to expire")
            change = {"fence": job["fence"] + 1, "lease": None}
            if state == "cancel_requested":
                change |= {"state": "cancelled", "stopped_at": at}
                change["reason"] = "reconciled after the lease expired"
            elif state == "pause_requested":
                change |= {"state": "paused", "reason": "paused once the lease expired"}
            else:
                change |= _over(job, True, "the lease expired without a heartbeat")
            kind = "job.expired"
        case "cancel":
            if state in ("queued", "paused"):
                change = {"state": "cancelled", "acknowledged_at": at, "stopped_at": at}
                kind = "job.cancelled"
            elif state in ("running", "checkpointed", "pause_requested"):
                change = {"state": "cancel_requested", "fence": job["fence"] + 1}
                change["acknowledged_at"] = at
                kind = "job.cancel_requested"
            else:
                return job, None, {}
        case "stop":
            if not mine or state not in ("cancel_requested", "pause_requested"):
                raise _refusal(job, "no stop was requested of this attempt")
            stopped = "cancelled" if state == "cancel_requested" else "paused"
            change = {"state": stopped, "lease": None, "stopped_at": at, "charged_minor": charged}
            kind = f"job.{stopped}"
        case "reject":
            return job, "job.result_rejected", _body(job, action, at, given)
        case _:
            raise DspError(ErrorCode.INPUT_INVALID, f"unknown action {action}")
    successor = {**job, **change, "revision": f"{int(job['revision'].split('.')[0]) + 1}.0.0"}
    return successor, kind, _body(successor, action, at, given)


def _over(job: dict[str, Any], transient: bool, reason: str) -> dict[str, Any]:
    """The attempt is over without a result: queue a retry while D03 allows one, else fail."""
    retry = transient and job["attempts"] <= RETRIES
    state = "queued" if retry else "failed"
    return {"state": state, "lease": None, "failures": job["failures"] + 1, "reason": reason}


def _body(job: dict[str, Any], action: str, at: str, given: dict[str, Any]) -> dict[str, Any]:
    return {
        "job": job["id"],
        "action": action,
        "at": at,
        "input": given,
        "state": job["state"],
        "attempt": job["attempts"],
        "fence": job["fence"],
    }


def _later(at: str, seconds: int) -> str:
    return (datetime.fromisoformat(at) + timedelta(seconds=seconds)).isoformat()


def _refusal(job: dict[str, Any], message: str) -> DspError:
    code = REFUSAL.get(job["state"], ErrorCode.REVISION_CONFLICT)
    return DspError(code, message, {"state": job["state"], "fence": job["fence"]})
