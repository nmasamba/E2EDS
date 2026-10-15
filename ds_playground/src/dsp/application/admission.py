"""Admission: a request becomes an admitted ExecutionRequest, a held Reservation and a queued Job.

Authority is the trusted context, never a request field. The workload and binding revisions are
pinned by digest, the latest plan is used only if it is as new as its inputs (otherwise a fresh
one is proposed: the recheck of A33), capacity is judged against the latest HardwareSnapshot less
what live jobs hold, and the three records are committed in one transaction under the admission
aggregate's compare-and-swap, so two requests racing for the last reservation cannot both win.
"""

from collections.abc import Callable
from typing import Any

from dsp.application.planning import propose_plan
from dsp.contracts.canonical import canonical_json, digest, pin
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.domain import admission as rules
from dsp.domain import jobs as machine
from dsp.ports import Ledger, Store

AGGREGATE = "admission:host-local"
DOMAIN = "host-local"
SUBMIT = {"*", "job:submit"}


def _held(ledger: Ledger, ctx: TrustedContext) -> dict[str, float]:
    held = {"cpu_cores": 0.0, "memory_gib": 0.0, "scratch_gib": 0.0}
    for reservation in ledger.current(ctx, "Reservation"):
        if reservation["state"] == "held":
            for unit in held:
                held[unit] += reservation[unit]
    return held


def _same_request(
    ctx: TrustedContext, key: str, operation: str, payload: str, ledger: Ledger
) -> dict[str, Any] | None:
    """The job already admitted for this idempotency key, if its payload is the same (D05).

    A Sprint 3 job carries no payload digest; its payload was its test-worker task.
    """
    for job in ledger.current(ctx, "Job"):
        if job["idempotency_key"] != key:
            continue
        ref = job["request_ref"]
        request = ledger.get(ctx, "ExecutionRequest", ref["id"], ref["revision"])
        earlier = job.get("payload_sha256") or digest(canonical_json(job["task"]))
        if (request["operation"], earlier) == (operation, payload):
            return job
        raise DspError(ErrorCode.IDEMPOTENCY_CONFLICT, f"key {key} was used for another request")
    return None


def admit(
    ctx: TrustedContext,
    operation: str,
    idempotency_key: str,
    task: dict[str, Any],
    *,
    workload: dict[str, Any],
    binding: dict[str, Any],
    ledger: Ledger,
    store: Store,
    clock: Callable[[], str],
    new_id: Callable[[], str],
    environment: str | None = None,
    parent: str | None = None,
    conversation: dict[str, Any] | None = None,
    assistant_binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Admit the request and return the queued job, or record the rejection and raise.

    A caller without the submit scope, or a task that is not a well-formed declaration, is refused
    before anything is read or written. Any other refusal is recorded as a rejected
    ExecutionRequest, pinning the CodeTask it declared, with its reason; no job and no reservation
    exist for it. Every input must be data captured through a grant, and the source must be in
    the content store. ``environment`` is the runner environment's lock digest, recorded on a
    Python or SQL CodeTask. A job the assistant submits names its ``parent`` job; the request
    of an assistant job, or of its children, pins the ``conversation`` and the assistant binding.
    """
    if not SUBMIT & ctx.scopes:
        raise DspError(ErrorCode.FORBIDDEN, "this context may not submit work")
    payload = digest(canonical_json(task))
    if existing := _same_request(ctx, idempotency_key, operation, payload, ledger):
        return existing
    code = rules.code_task(task, workload, environment)
    validate("CodeTask", code)
    cues = None if "language" in task else task
    captured = {manifest["sha256"] for manifest in ledger.current(ctx, "DataManifest")}
    names = [item["name"] for item in code["inputs"]]
    unknown = [item["name"] for item in code["inputs"] if item["sha256"] not in captured]
    unresolved: tuple[ErrorCode, str] | None = None
    if len(set(names)) < len(names):
        unresolved = ErrorCode.INPUT_INVALID, "two inputs share a name"
    elif unknown:
        unresolved = ErrorCode.INPUT_INVALID, f"input {unknown[0]} was not captured through a grant"
    elif cues is None:
        try:
            store.path(ctx, code["source_sha256"])
        except DspError:
            unresolved = ErrorCode.INPUT_INVALID, "the task's source is not in the store"
    for _ in range(3):
        seq, at = ledger.seq(ctx, AGGREGATE), clock()
        snapshots = ledger.current(ctx, "HardwareSnapshot")
        snapshot = snapshots[-1] if snapshots else None
        plans = ledger.current(ctx, "WorkflowPlan")
        plan = plans[-1] if plans else None
        stale = plan is None or plan["workload_ref"]["revision"] != workload["revision"]
        if snapshot is not None and plan is not None:
            stale = stale or plan["hardware_snapshot_refs"][-1]["id"] != snapshot["id"]
        if stale and snapshot is not None:
            plan = propose_plan(ctx, binding=binding, ledger=ledger, new_id=new_id)
        request: dict[str, Any] = {
            "schema_version": "0.5.0",
            "planning_only": False,
            "id": f"request-{new_id()}",
            "revision": "1.0.0",
            "type": "ExecutionRequest",
            "tenant_ref": ctx.tenant,
            "project_ref": workload["project_ref"],
            "workload_ref": pin(workload),
            "compute_binding_ref": pin(binding),
            "operation": operation,
            "data_access": rules.DATA_ACCESS.get(operation, "train_tune_only"),
            "idempotency_key": idempotency_key,
            "authorisation_context_ref": ctx.principal,
            "state": "admitted",
            "conversation_ref": pin(conversation) if conversation else None,
            "assistant_model_binding_ref": pin(assistant_binding) if assistant_binding else None,
            "source_code_task_ref": pin(code),
            "requirement_revision": workload["revision"],
            "workflow_plan_ref": pin(plan) if plan else None,
        }
        refused = unresolved or rules.refusal(
            operation, cues, code, workload, binding, snapshot, _held(ledger, ctx)
        )
        if refused:
            refusing, reason = refused
            request["state"] = "rejected"
            validate("ExecutionRequest", request)
            rejected = {"request": request["id"], "operation": operation, "code": refusing}
            rejected |= {"reason": reason, "plan_rechecked": stale}
            aggregate = f"request:{request['id']}"
            ledger.commit(
                ctx,
                aggregate,
                0,
                f"{request['id']}:rejected",
                "admission.rejected",
                rejected,
                [request, code],
            )
            raise DspError(refusing, reason, {"request": request["id"]})
        validate("ExecutionRequest", request)
        reservation = {
            "schema_version": "0.1.0",
            "type": "Reservation",
            "id": f"reservation-{new_id()}",
            "revision": "1.0.0",
            "job_ref": "",
            "request_ref": request["id"],
            "domain": DOMAIN,
            **rules.reservation(workload, binding),
            "state": "held",
            "held_at": at,
            "released_at": None,
        }
        job, kind, body = machine.new(
            f"job-{new_id()}",
            at,
            task=cues,
            payload_sha256=payload,
            request_ref=pin(request),
            reservation=reservation["id"],
            workload_ref=pin(workload),
            idempotency_key=idempotency_key,
            parent=parent,
        )
        reservation["job_ref"] = job["id"]
        validate("Reservation", reservation)
        validate("Job", job)
        body |= {
            "request": request["id"],
            "reservation": reservation["id"],
            "plan_rechecked": stale,
        }
        objects: list[dict[str, Any] | tuple[str, dict[str, Any]]] = [request, reservation, job]
        objects += [code, ("WorkloadSpec", workload), ("ComputeBinding", binding)]
        try:
            ledger.commit(ctx, AGGREGATE, seq, f"{job['id']}:admitted", kind or "", body, objects)
        except DspError as error:
            if error.code is ErrorCode.REVISION_CONFLICT:
                continue
            raise
        return job
    raise DspError(ErrorCode.REVISION_CONFLICT, "admission raced three times; try again")


def readmit(
    ctx: TrustedContext,
    job_id: str,
    *,
    workload: dict[str, Any],
    binding: dict[str, Any],
    ledger: Ledger,
    clock: Callable[[], str],
    new_id: Callable[[], str],
) -> tuple[dict[str, Any], bool]:
    """Resume a paused job: admit its remaining work again under the current revision.

    Capacity is rechecked against the latest observation and a new reservation is held; a refusal
    is recorded and leaves the job paused. The commit rides the admission aggregate, so a race for
    capacity is serialised, and the job revision's immutability refuses a transition that raced it.
    """
    if not SUBMIT & ctx.scopes:
        raise DspError(ErrorCode.FORBIDDEN, "this context may not resume work")
    for _ in range(3):
        seq, at = ledger.seq(ctx, AGGREGATE), clock()
        job = ledger.latest(ctx, "Job", job_id)
        if job is None:
            raise DspError(ErrorCode.NOT_FOUND, "no such job")
        reservation = {
            "schema_version": "0.1.0",
            "type": "Reservation",
            "id": f"reservation-{new_id()}",
            "revision": "1.0.0",
            "job_ref": job_id,
            "request_ref": job["request_ref"]["id"],
            "domain": DOMAIN,
            **rules.reservation(workload, binding),
            "state": "held",
            "held_at": at,
            "released_at": None,
        }
        resumed, kind, body = machine.advance(
            job, "resume", at, reservation=reservation["id"], workload_ref=pin(workload)
        )
        request = ledger.get(ctx, "ExecutionRequest", job["request_ref"]["id"], "1.0.0")
        snapshots = ledger.current(ctx, "HardwareSnapshot")
        snapshot = snapshots[-1] if snapshots else None
        ref = request["source_code_task_ref"]
        code = (
            rules.code_task(job["task"], workload)
            if job["task"] is not None
            else ledger.get(ctx, "CodeTask", ref["id"], ref["revision"])
        )
        refused = rules.refusal(
            request["operation"],
            job["task"],
            code,
            workload,
            binding,
            snapshot,
            _held(ledger, ctx),
        )
        if refused:
            refusing, reason = refused
            rejected = {"job": job_id, "request": request["id"], "code": refusing, "reason": reason}
            event_id = f"{job_id}:resume:{new_id()}"
            ledger.commit(
                ctx,
                f"request:{request['id']}",
                ledger.seq(ctx, f"request:{request['id']}"),
                event_id,
                "admission.rejected",
                rejected,
                [],
            )
            raise DspError(refusing, reason, {"job": job_id})
        validate("Reservation", reservation)
        validate("Job", resumed)
        body |= {"reservation": reservation["id"], "requirement_revision": workload["revision"]}
        try:
            ledger.commit(
                ctx,
                AGGREGATE,
                seq,
                f"{job_id}:resumed:{resumed['revision']}",
                kind or "",
                body,
                [reservation, resumed],
            )
        except DspError as error:
            if error.code is ErrorCode.REVISION_CONFLICT:
                continue
            raise
        return resumed, True
    raise DspError(ErrorCode.REVISION_CONFLICT, "the job changed under this resume; try again")


def released(
    ctx: TrustedContext, job: dict[str, Any], at: str, ledger: Ledger
) -> list[dict[str, Any]]:
    """The successor that releases the job's reservation, to commit with the job's transition."""
    held = ledger.latest(ctx, "Reservation", job["reservation"]) if job["reservation"] else None
    if not held or held["state"] != "held":
        return []
    free = held | {"revision": "2.0.0", "state": "released", "released_at": at}
    validate("Reservation", free)
    return [free]
