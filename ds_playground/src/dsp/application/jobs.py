"""The job coordinator: submit, lease, heartbeat, report and control.

Each operation loads the job, reconciles an expired lease, applies the pure state machine and
commits the successor and its event in one ledger transaction under compare-and-swap. A
concurrent transition that wins the race is retried from the reloaded job; a worker's stale
report is recorded as rejected and refused.
"""

from collections.abc import Callable
from typing import Any

from dsp.contracts.canonical import canonical_json, digest
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.domain import jobs as machine
from dsp.ports import Ledger

OUTCOMES = {"succeeded": "succeed", "failed": "fail", "stopped": "stop"}


class _RacedError(Exception):
    """Another transition won the compare-and-swap: reload and try again."""


def _commit(
    ctx: TrustedContext, ledger: Ledger, before: str, job: dict[str, Any], kind: str, body: Any
) -> None:
    objects = [job] if job["revision"] != before else []
    if objects:
        validate("Job", job)
    aggregate = f"job:{job['id']}"
    seq = ledger.seq(ctx, aggregate)
    event_id = f"{job['id']}:{seq + 1}:{digest(canonical_json(body))[7:19]}"
    try:
        ledger.commit(ctx, aggregate, seq, event_id, kind, body, objects)
    except DspError as error:
        if error.code is ErrorCode.REVISION_CONFLICT:
            raise _RacedError from error
        raise


def _load(ctx: TrustedContext, job_id: str, ledger: Ledger) -> dict[str, Any]:
    job = ledger.latest(ctx, "Job", job_id)
    if job is None:
        raise DspError(ErrorCode.NOT_FOUND, "no such job")
    return job


def _apply(
    ctx: TrustedContext,
    job_id: str,
    action: str,
    *,
    ledger: Ledger,
    clock: Callable[[], str],
    **given: Any,
) -> tuple[dict[str, Any], bool]:
    """Reconcile, apply and commit one action; return the job and whether anything changed."""
    for _ in range(3):
        at = clock()
        job = _load(ctx, job_id, ledger)
        try:
            if machine.due(job, at):
                expired, kind, body = machine.advance(job, "expire", at)
                _commit(ctx, ledger, job["revision"], expired, kind or "", body)
                job = expired
            after, kind, body = machine.advance(job, action, at, **given)
            if kind:
                _commit(ctx, ledger, job["revision"], after, kind, body)
            return after, kind is not None
        except _RacedError:
            continue
    raise DspError(
        ErrorCode.REVISION_CONFLICT, "the job changed under this request", {"retry": True}
    )


def submit(
    ctx: TrustedContext,
    task: dict[str, Any],
    *,
    ledger: Ledger,
    clock: Callable[[], str],
    new_id: Callable[[], str],
) -> dict[str, Any]:
    """Queue a job for the one workload that exists, the test worker's task, and return it."""
    job, kind, body = machine.new(f"job-{new_id()}", task, clock())
    _commit(ctx, ledger, "", job, kind or "", body)
    return job


def inspect(
    ctx: TrustedContext, job_id: str, *, ledger: Ledger, clock: Callable[[], str]
) -> dict[str, Any]:
    """Return the job as it is now, after reconciling a lease that has run out."""
    return _apply(ctx, job_id, "touch", ledger=ledger, clock=clock)[0]


def lease(
    ctx: TrustedContext, job_id: str, worker: str, *, ledger: Ledger, clock: Callable[[], str]
) -> dict[str, Any]:
    """Lease the next attempt to a worker: a 60 s lease to heartbeat every 15 s (D03)."""
    job, _ = _apply(ctx, job_id, "lease", ledger=ledger, clock=clock, worker=worker)
    return {
        "attempt": job["lease"]["attempt"],
        "fence": job["fence"],
        "expires_at": job["lease"]["expires_at"],
        "heartbeat_seconds": machine.HEARTBEAT_SECONDS,
        "task": job["task"],
    }


def heartbeat(
    ctx: TrustedContext,
    job_id: str,
    attempt: int,
    fence: int,
    *,
    ledger: Ledger,
    clock: Callable[[], str],
) -> dict[str, Any]:
    """Extend the live attempt's lease and tell the worker whether it has been asked to stop."""
    job, _ = _apply(
        ctx, job_id, "heartbeat", ledger=ledger, clock=clock, attempt=attempt, fence=fence
    )
    return {"state": job["state"], "expires_at": job["lease"]["expires_at"]}


def report(
    ctx: TrustedContext,
    job_id: str,
    attempt: int,
    fence: int,
    outcome: str,
    *,
    ledger: Ledger,
    clock: Callable[[], str],
    **fields: Any,
) -> dict[str, Any]:
    """Commit the worker's one report: succeeded with a result key and digest, failed, or stopped.

    A retry of a committed result key returns the committed result (A03). Anything the fence or
    the state refuses is recorded on the job as a rejected report, then refused (A04).
    """
    try:
        if outcome == "succeeded":
            job = _load(ctx, job_id, ledger)
            if machine.committed(job, fields["key"], fields["sha256"]):
                return {"state": job["state"], "committed": False}
        job, _ = _apply(
            ctx,
            job_id,
            OUTCOMES[outcome],
            ledger=ledger,
            clock=clock,
            attempt=attempt,
            fence=fence,
            **fields,
        )
    except DspError as error:
        if error.code is not ErrorCode.NOT_FOUND and not error.details.get("retry"):
            rejected = {
                "attempt": attempt,
                "fence": fence,
                "outcome": outcome,
                "because": error.code,
            }
            _apply(ctx, job_id, "reject", ledger=ledger, clock=clock, **rejected)
        raise
    return {"state": job["state"], "committed": True}


def control(
    ctx: TrustedContext, job_id: str, action: str, *, ledger: Ledger, clock: Callable[[], str]
) -> dict[str, Any]:
    """Apply an explicit control and say what it changed; a finished job is left as it is."""
    job, changed = _apply(ctx, job_id, action, ledger=ledger, clock=clock)
    return {"job": job, "changed": changed}
