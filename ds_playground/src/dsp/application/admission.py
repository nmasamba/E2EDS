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
from dsp.contracts.canonical import pin
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.domain import admission as rules
from dsp.domain import jobs as machine
from dsp.ports import Ledger

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
    ctx: TrustedContext, key: str, operation: str, task: dict[str, Any], ledger: Ledger
) -> dict[str, Any] | None:
    """The job already admitted for this idempotency key, if its payload is the same (D05)."""
    for job in ledger.current(ctx, "Job"):
        if job["idempotency_key"] != key:
            continue
        ref = job["request_ref"]
        request = ledger.get(ctx, "ExecutionRequest", ref["id"], ref["revision"])
        if (request["operation"], job["task"]) == (operation, task):
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
    clock: Callable[[], str],
    new_id: Callable[[], str],
) -> dict[str, Any]:
    """Admit the request and return the queued job, or record the rejection and raise.

    A caller without the submit scope is refused before anything is read or written. Any other
    refusal is recorded as a rejected ExecutionRequest with its reason; no job and no reservation
    exist for it.
    """
    if not SUBMIT & ctx.scopes:
        raise DspError(ErrorCode.FORBIDDEN, "this context may not submit work")
    if existing := _same_request(ctx, idempotency_key, operation, task, ledger):
        return existing
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
            plan = propose_plan(ctx, ledger=ledger, new_id=new_id)
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
            "conversation_ref": None,
            "assistant_model_binding_ref": None,
            "source_code_task_ref": pin(
                {"id": "code-task-test-worker", "revision": "1.0.0", **task}
            ),
            "requirement_revision": workload["revision"],
            "workflow_plan_ref": pin(plan) if plan else None,
        }
        refused = rules.refusal(operation, workload, binding, snapshot, _held(ledger, ctx))
        if refused:
            code, reason = refused
            request["state"] = "rejected"
            validate("ExecutionRequest", request)
            rejected = {"request": request["id"], "operation": operation, "code": code}
            rejected |= {"reason": reason, "plan_rechecked": stale}
            aggregate = f"request:{request['id']}"
            ledger.commit(
                ctx,
                aggregate,
                0,
                f"{request['id']}:rejected",
                "admission.rejected",
                rejected,
                [request],
            )
            raise DspError(code, reason, {"request": request["id"]})
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
            task=task,
            request_ref=pin(request),
            reservation=reservation["id"],
            workload_ref=pin(workload),
            idempotency_key=idempotency_key,
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
        objects.append(("WorkloadSpec", workload))
        try:
            ledger.commit(ctx, AGGREGATE, seq, f"{job['id']}:admitted", kind or "", body, objects)
        except DspError as error:
            if error.code is ErrorCode.REVISION_CONFLICT:
                continue
            raise
        return job
    raise DspError(ErrorCode.REVISION_CONFLICT, "admission raced three times; try again")


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
