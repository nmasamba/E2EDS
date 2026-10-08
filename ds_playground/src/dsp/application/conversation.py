"""Durable messages: a ConversationCommand and its receipt are committed before anything answers.

../conversational_control.md "Transport and durable records": the inbound API accepts a client
message ID, bounded text and the expected requirement revision; tenancy, the operation and the
command's state are derived here. The exact control phrases are recognised deterministically; any
other text is an instruction, and with no assistant bound an instruction is rejected as such.
"""

from collections.abc import Callable
from typing import Any

from dsp.application.grants import PROJECT
from dsp.application.workloads import current_workload
from dsp.contracts.canonical import canonical_json, digest, pin
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.ports import Ledger

MAX_BYTES = 16 * 1024  # D18
CONTROLS = {
    "pause": "pause",
    "pause now": "pause",
    "cancel this run": "cancel",
    "stop this run": "cancel",
    "resume": "resume",
    "status": "status",
}


def classify(text: str) -> str:
    """The operation the text asks for: an exact control phrase, or else an instruction."""
    return CONTROLS.get(text.strip().lower().rstrip(".!"), "instruction")


def receipt(command: dict[str, Any]) -> dict[str, Any]:
    """What a sender is told: the command, its operation and state, and the receipt event."""
    return {
        "command": command["id"],
        "revision": command["revision"],
        "operation": command["operation"],
        "state": command["state"],
        "receipt": command["receipt_event_ref"]["id"],
    }


def _record(
    ctx: TrustedContext,
    command: dict[str, Any],
    kind: str,
    body: dict[str, Any],
    objects: list[dict[str, Any]],
    ledger: Ledger,
) -> None:
    aggregate = f"conversation:{command['conversation_ref']['id']}"
    for _ in range(3):
        try:
            seq = ledger.seq(ctx, aggregate)
            ledger.commit(ctx, aggregate, seq, body["event"], kind, body, objects)
            return
        except DspError as error:
            if error.code is not ErrorCode.REVISION_CONFLICT:
                raise
    raise DspError(ErrorCode.REVISION_CONFLICT, "the conversation changed under this message")


def receive(
    ctx: TrustedContext,
    conversation_id: str,
    client_message_id: str,
    text: str,
    expected_revision: str,
    *,
    ledger: Ledger,
    clock: Callable[[], str],
    new_id: Callable[[], str],
) -> dict[str, Any]:
    """Persist the message as a received ConversationCommand with its receipt event, then answer.

    The same client message ID again returns the same receipt (A27: a lost acknowledgement); the
    same ID with other text is an IDEMPOTENCY_CONFLICT. The first message of a conversation creates
    it. An instruction is then rejected, honestly, because no assistant is bound yet.
    """
    if len(text.encode()) > MAX_BYTES:
        raise DspError(ErrorCode.INPUT_INVALID, "the message is larger than 16 KiB")
    for earlier in ledger.current(ctx, "ConversationCommand"):
        if (earlier["conversation_ref"]["id"], earlier["client_message_id"]) == (
            conversation_id,
            client_message_id,
        ):
            if earlier["text"] != text:
                raise DspError(ErrorCode.IDEMPOTENCY_CONFLICT, "this message ID carried other text")
            return receipt(earlier)
    objects: list[dict[str, Any]] = []
    conversation = ledger.latest(ctx, "Conversation", conversation_id)
    if conversation is None:
        conversation = {
            "schema_version": "0.1.0",
            "type": "Conversation",
            "id": conversation_id,
            "revision": "1.0.0",
            "project_ref": PROJECT,
            "workload_id": current_workload(ctx, ledger)["id"],
            "created_at": clock(),
        }
        validate("Conversation", conversation)
        objects.append(conversation)
    command: dict[str, Any] = {
        "schema_version": "0.3.0",
        "planning_only": False,
        "id": f"command-{new_id()}",
        "revision": "1.0.0",
        "tenant_ref": ctx.tenant,
        "project_ref": PROJECT,
        "type": "ConversationCommand",
        "conversation_ref": pin(conversation),
        "client_message_id": client_message_id,
        "source": "direct_user_message",
        "text": text,
        "operation": classify(text),
        "workload_ref": pin(current_workload(ctx, ledger)),
        "expected_requirement_revision": expected_revision,
        "proposed_patch": [],
        "state": "received",
        "authorisation_context_ref": ctx.principal,
        "receipt_event_ref": None,
        "effect_ref": None,
    }
    body = {
        "event": f"{command['id']}:received",
        "conversation": conversation_id,
        "command": command["id"],
        "client_message_id": client_message_id,
        "operation": command["operation"],
        "state": "received",
        "text": text,
        "expected_revision": expected_revision,
        "at": clock(),
    }
    command["receipt_event_ref"] = {
        "id": body["event"],
        "revision": "1.0.0",
        "sha256": digest(canonical_json(body)),
    }
    validate("ConversationCommand", command)
    _record(ctx, command, "message.received", body, [*objects, command], ledger)
    if command["operation"] == "instruction":
        command = settle(
            ctx,
            command,
            "rejected",
            because=ErrorCode.ASSISTANT_UNAVAILABLE,
            ledger=ledger,
            clock=clock,
        )
    return receipt(command)


def settle(
    ctx: TrustedContext,
    command: dict[str, Any],
    state: str,
    *,
    ledger: Ledger,
    clock: Callable[[], str],
    effect: dict[str, Any] | None = None,
    because: str | None = None,
) -> dict[str, Any]:
    """Record the command's next state as a new revision with a `command.<state>` event."""
    settled = command | {
        "revision": f"{int(command['revision'].split('.')[0]) + 1}.0.0",
        "state": state,
        "effect_ref": effect,
    }
    validate("ConversationCommand", settled)
    body = {
        "event": f"{command['id']}:{settled['revision']}:{state}",
        "conversation": command["conversation_ref"]["id"],
        "command": command["id"],
        "client_message_id": command["client_message_id"],
        "operation": command["operation"],
        "state": state,
        "because": because,
        "effect": effect,
        "at": clock(),
    }
    _record(ctx, settled, f"command.{state}", body, [settled], ledger)
    return settled
