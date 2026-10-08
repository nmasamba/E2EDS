"""Fast controls (../conversational_control.md "Fast controls and races").

An exact control phrase, the window's button and the native menu item all become the same
ConversationCommand and the same coordinator transition. The path touches the ledger only: no
model, no worker, nothing that a hung generation or a saturated task could hold up (D18, A24).
"""

from collections.abc import Callable
from typing import Any

from dsp.application import jobs
from dsp.application.conversation import receipt, receive, settle
from dsp.application.workloads import patch_for, revise
from dsp.contracts.canonical import pin
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.ports import Ledger

CONVERSATION = "conversation-local"
ACTIONS = {"pause", "resume", "cancel", "status"}
PHRASES = {"pause": "pause", "resume": "resume", "cancel": "cancel this run", "status": "status"}
ENDED = {"succeeded", "failed", "cancelled"}


def live_jobs(ctx: TrustedContext, ledger: Ledger) -> list[dict[str, Any]]:
    """The jobs that have not ended; a paused job is live, it can resume."""
    return [job for job in ledger.current(ctx, "Job") if job["state"] not in ENDED]


def command(
    ctx: TrustedContext,
    conversation_id: str,
    client_message_id: str,
    text: str,
    expected_revision: str,
    *,
    job_id: str | None,
    ledger: Ledger,
    clock: Callable[[], str],
    new_id: Callable[[], str],
    workload: dict[str, Any],
    binding: dict[str, Any],
) -> dict[str, Any]:
    """Receive the message; if it is a control, apply it to the job (the live one by default).

    The receipt is durable before the control runs. The command ends ``applied`` when the job
    changed, ``superseded`` when the job had already settled it (cancel after success), or
    ``rejected`` with the code when the job's state refuses it; a phrase with no live job is
    rejected and one with several live jobs needs clarification, since a phrase names no job; a
    repeated client message ID is not applied twice. The answer carries the job's actual state.
    """
    received = receive(
        ctx,
        conversation_id,
        client_message_id,
        text,
        expected_revision,
        ledger=ledger,
        clock=clock,
        new_id=new_id,
    )
    answer = receipt(received)
    if received["state"] == "received" and received["operation"] == "change_requirements":
        return answer | change(
            ctx,
            received,
            ledger=ledger,
            clock=clock,
            new_id=new_id,
            workload=workload,
            binding=binding,
        )
    if received["state"] != "received" or received["operation"] not in ACTIONS:
        effect = received["effect_ref"]
        shown = jobs.inspect(ctx, effect["id"], ledger=ledger, clock=clock) if effect else None
        return answer | {"job": shown, "changed": False}
    live = [] if job_id else live_jobs(ctx, ledger)
    if not job_id and len(live) != 1:
        state = "rejected" if not live else "needs_clarification"
        because = "no job is live" if not live else f"{len(live)} jobs are live; name the job"
        settled = settle(ctx, received, state, because=because, ledger=ledger, clock=clock)
        return receipt(settled) | {"job": None, "changed": False, "because": because}
    target = job_id or live[0]["id"]
    try:
        job, changed = jobs.control(
            ctx,
            target,
            received["operation"],
            ledger=ledger,
            clock=clock,
            new_id=new_id,
            workload=workload,
            binding=binding,
        )
    except DspError as error:
        settled = settle(ctx, received, "rejected", because=error.code, ledger=ledger, clock=clock)
        shown = None
        if error.code is not ErrorCode.NOT_FOUND:
            shown = jobs.inspect(ctx, target, ledger=ledger, clock=clock)
        return receipt(settled) | {"job": shown, "changed": False, "because": error.message}
    state = "applied" if changed or received["operation"] == "status" else "superseded"
    settled = settle(ctx, received, state, effect=pin(job), ledger=ledger, clock=clock)
    return receipt(settled) | {"job": job, "changed": changed}


def change(
    ctx: TrustedContext,
    received: dict[str, Any],
    *,
    ledger: Ledger,
    clock: Callable[[], str],
    new_id: Callable[[], str],
    workload: dict[str, Any],
    binding: dict[str, Any],
) -> dict[str, Any]:
    """Apply a change instruction as a new requirement revision and hold the work it affects.

    The patch is typed before anything else; a budget or evaluation change, an unknown field or a
    stale expected revision ends the command ``rejected`` with its code and no new revision. Live
    jobs on the old revision are paused, so an explicit resume readmits them under the new one.
    """
    text, expected = received["text"], received["expected_requirement_revision"]
    patch: list[dict[str, Any]] = []
    try:
        patch = patch_for(text, workload)
        successor, impact = revise(
            ctx, patch, expected, received["client_message_id"], text, ledger=ledger, clock=clock
        )
    except DspError as error:
        rejected = settle(
            ctx, received, "rejected", because=error.code, patch=patch, ledger=ledger, clock=clock
        )
        return receipt(rejected) | {"job": None, "changed": False, "because": error.message}
    for job_id in impact["holds"]:
        jobs.control(
            ctx,
            job_id,
            "pause",
            ledger=ledger,
            clock=clock,
            new_id=new_id,
            workload=workload,
            binding=binding,
        )
    applied = settle(
        ctx, received, "applied", effect=pin(successor), patch=patch, ledger=ledger, clock=clock
    )
    return receipt(applied) | {
        "job": None,
        "changed": True,
        "workload": {"id": successor["id"], "revision": successor["revision"]},
        "impact": impact,
    }
