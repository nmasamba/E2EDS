"""The job coordinator: submit, lease, heartbeat, report and control.

Each operation loads the job, reconciles an expired lease, applies the pure state machine and
commits the successor and its event in one ledger transaction under compare-and-swap. A
concurrent transition that wins the race is retried from the reloaded job; a worker's stale
report is recorded as rejected and refused.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dsp.application.admission import readmit, released
from dsp.contracts.canonical import canonical_json, digest
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.domain import jobs as machine
from dsp.ports import Ledger, Runner, Store

OUTCOMES = {"succeeded": "succeed", "failed": "fail", "stopped": "stop"}
WORKER = "runner-local"  # the harness's own worker, which runs sandboxed attempts


class _RacedError(Exception):
    """Another transition won the compare-and-swap: reload and try again."""


def _commit(
    ctx: TrustedContext, ledger: Ledger, before: str, job: dict[str, Any], kind: str, body: Any
) -> None:
    objects = [job] if job["revision"] != before else []
    if objects:
        validate("Job", job)
        if job["state"] in machine.RELEASES:
            objects += released(ctx, job, body["at"], ledger)
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
        if error.code is ErrorCode.NOT_FOUND or error.details.get("retry"):
            raise
        if (
            outcome == "succeeded"
            and error.code is not ErrorCode.IDEMPOTENCY_CONFLICT
            and machine.committed(_load(ctx, job_id, ledger), fields["key"], fields["sha256"])
        ):
            return {"state": "succeeded", "committed": False}  # a retry that raced its own commit
        rejected = {"attempt": attempt, "fence": fence, "outcome": outcome, "because": error.code}
        _apply(ctx, job_id, "reject", ledger=ledger, clock=clock, **rejected)
        raise
    return {"state": job["state"], "committed": True}


def checkpoint(
    ctx: TrustedContext,
    job_id: str,
    attempt: int,
    fence: int,
    sha256: str,
    *,
    ledger: Ledger,
    clock: Callable[[], str],
) -> dict[str, Any]:
    """Record the live attempt's durable checkpoint; accepted while draining for a pause (A25)."""
    given = {"attempt": attempt, "fence": fence, "sha256": sha256}
    job, _ = _apply(ctx, job_id, "checkpoint", ledger=ledger, clock=clock, **given)
    return {"state": job["state"], "checkpoint": job["checkpoint"]}


def control(
    ctx: TrustedContext,
    job_id: str,
    action: str,
    *,
    ledger: Ledger,
    clock: Callable[[], str],
    new_id: Callable[[], str],
    workload: dict[str, Any],
    binding: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Apply an explicit control on the fast path and return the job and whether it changed.

    Pause and cancel advance the fence at once; resume is a fresh admission under the current
    workload revision; status reads. A finished job is left as it is.
    """
    if action == "resume":
        return readmit(
            ctx,
            job_id,
            workload=workload,
            binding=binding,
            ledger=ledger,
            clock=clock,
            new_id=new_id,
        )
    if action == "status":
        return inspect(ctx, job_id, ledger=ledger, clock=clock), False
    return _apply(ctx, job_id, action, ledger=ledger, clock=clock)


def reconcile(ctx: TrustedContext, *, ledger: Ledger, clock: Callable[[], str]) -> None:
    """The reconcile tick (D03): expire every lease that has run out, with nobody touching its job.

    The harness runs it every second, so a dead worker's attempt is expired, its fence advanced and
    a retry queued within one lease of its last heartbeat, whether or not anyone reads the job.
    """
    for job in ledger.current(ctx, "Job"):
        if machine.due(job, clock()):
            inspect(ctx, job["id"], ledger=ledger, clock=clock)


def execute(
    ctx: TrustedContext,
    job_id: str,
    *,
    ledger: Ledger,
    store: Store,
    runner: Runner,
    clock: Callable[[], str],
    timer: Callable[[], float],
) -> dict[str, Any]:
    """Run one attempt of a sandboxed job and commit what it produced under the attempt's fence.

    The attempt is leased to the harness's own worker and heartbeats every 15 s while the task
    runs; a pause or cancel request, or a lease that is no longer this attempt's (it expired and
    the fence moved), stops the task within a quarter of a second. The outputs stay in the
    attempt's staging folder until the result that names them (a RunRecord, by digest) is
    committed as the job's result; only then do they move into the content store. A task that
    fails has failed for good (a repair is a new task); a result the fence refuses leaves
    nothing behind.
    """
    granted = lease(ctx, job_id, WORKER, ledger=ledger, clock=clock)
    attempt, fence = granted["attempt"], granted["fence"]
    pinned = _load(ctx, job_id, ledger)["request_ref"]
    request = ledger.get(ctx, "ExecutionRequest", pinned["id"], pinned["revision"])
    ref = request["source_code_task_ref"]
    code = ledger.get(ctx, "CodeTask", ref["id"], ref["revision"])
    work = store.staging(f"{job_id}.{attempt}")
    due, asked = {"beat": timer() + machine.HEARTBEAT_SECONDS, "look": 0.0}, {"stop": False}

    def proceed() -> bool:
        now = timer()
        if now < due["look"]:
            return True
        due["look"] = now + 0.25
        try:
            if now >= due["beat"]:
                due["beat"] = now + machine.HEARTBEAT_SECONDS
                heartbeat(ctx, job_id, attempt, fence, ledger=ledger, clock=clock)
            job = _load(ctx, job_id, ledger)
        except DspError:
            return False  # fenced out: another attempt may run now
        asked["stop"] = job["state"] in ("pause_requested", "cancel_requested")
        lease = job["lease"] or {}
        return not asked["stop"] and (lease.get("attempt"), lease.get("fence")) == (attempt, fence)

    inputs = {item["name"]: store.path(ctx, item["sha256"]) for item in code["inputs"]}
    result = runner.run(code, store.path(ctx, code["source_sha256"]), inputs, work, proceed)
    outcome: dict[str, Any] = {}
    if result["outcome"] == "succeeded":
        record = {
            "schema_version": "0.1.0",
            "type": "RunRecord",
            "job": job_id,
            "attempt": attempt,
            "fence": fence,
            "code_task_ref": ref,
            "compute_binding_ref": request["compute_binding_ref"],
            "assurance": "os_sandbox_single_user",
            "outputs": result["outputs"],
        }
        validate("RunRecord", record)
        (work / "run.json").write_bytes(canonical_json(record))
        outcome = {"outcome": "succeeded", "key": work.name}
        outcome["sha256"] = digest(canonical_json(record))
    elif result["failure"]["kind"] != "stopped":
        reason = f"{result['failure']['kind']}: {result['failure']['message']}"
        outcome = {"outcome": "failed", "transient": False, "reason": reason[:200]}
    elif asked["stop"]:
        outcome = {"outcome": "stopped"}
    committed = False
    try:
        if outcome:
            answer = report(ctx, job_id, attempt, fence, ledger=ledger, clock=clock, **outcome)
            committed = answer["committed"] and outcome["outcome"] == "succeeded"
    except DspError:
        pass  # refused, and recorded on the job as a rejected result
    if committed:
        _promote(ctx, store, work)  # a failure here leaves the folder for tidy to finish
    else:
        store.discard(work)
    return _load(ctx, job_id, ledger)


def tidy(ctx: TrustedContext, *, ledger: Ledger, store: Store, runner: Runner) -> None:
    """Finish or clear what a crash left in staging, between runs (never during one).

    A committed result whose outputs are still staged is moved into the content store; every
    other attempt's folder is released (a mounted scratch volume, say) and deleted.
    """
    for work in store.attempts():
        job_id, _, number = work.name.rpartition(".")
        job = ledger.latest(ctx, "Job", job_id) if number.isdigit() else None
        if job is None:
            continue
        result = job["result"]
        if (
            job["state"] == "succeeded"
            and result["key"] == work.name
            and work.joinpath("run.json").exists()
        ):
            _promote(ctx, store, work)
        else:
            runner.release(work)
            store.discard(work)


def _promote(ctx: TrustedContext, store: Store, work: Path) -> None:
    """Move a committed attempt's outputs and RunRecord into the content store; clear the rest."""
    record = json.loads((work / "run.json").read_bytes())
    for output in record["outputs"]:
        if store.commit(ctx, work / "out" / output["name"]) != output["sha256"]:
            raise DspError(ErrorCode.INTERNAL_ERROR, "a staged output changed after it was hashed")
    store.commit(ctx, work / "run.json")
    store.discard(work)
