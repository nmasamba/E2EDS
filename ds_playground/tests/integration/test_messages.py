"""Messages and receipts (A27, D18) against the harness, including a dropped acknowledgement."""

import json
import socket
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.application.conversation import classify, receive
from dsp.application.workloads import base_workload
from dsp.contracts.canonical import pin
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.harness import workspace
from dsp.harness.app import SHELL_ORIGIN, create_app
from tests.conftest import Clock

CTX = TrustedContext.local()
WINDOW = {"Authorization": "Bearer secret", "Origin": SHELL_ORIGIN}
ROUTE = "/v1/conversations/conversation-local/messages"
NOW = "2026-10-08T10:00:00+00:00"


def message(text: str, mid: str = "m1", revision: str = "1.0.0") -> dict[str, str]:
    """The three fields the inbound API accepts."""
    return {"client_message_id": mid, "text": text, "expected_revision": revision}


@pytest.fixture
def api(tmp_path: Path) -> TestClient:
    """The harness API in-process, as served on port 4100 with credential ``secret``."""
    (tmp_path / "home").mkdir()
    app = create_app("secret", 4100)
    workspace.mount(app, tmp_path / "home")
    return TestClient(app, base_url="http://127.0.0.1:4100")


def kinds(api: TestClient, after: int = 0) -> list[tuple[int, str, str]]:
    """(seq, type, client message ID) of every event after the cursor, in order."""
    events = api.get(f"/v1/events?after={after}", headers=WINDOW).json()["events"]
    return [(e["seq"], e["type"], e["body"].get("client_message_id", "")) for e in events]


def test_a27_the_same_message_id_is_one_command_and_other_text_under_it_conflicts(
    api: TestClient, tmp_path: Path
) -> None:
    """A27, D05, D06: the same message ID is one command; other text under it conflicts.

    A retried ID returns the same receipt and writes nothing; the command and its conversation
    validate against their schemas and pin each other by digest.
    """
    first = api.post(ROUTE, headers=WINDOW, json=message("status"))
    assert first.status_code == 200, first.text
    again = api.post(ROUTE, headers=WINDOW, json=message("status"))
    stable = ("command", "revision", "operation", "state", "receipt")
    assert {key: again.json()[key] for key in stable} == {key: first.json()[key] for key in stable}
    assert (first.json()["operation"], first.json()["state"]) == ("status", "rejected")
    assert first.json()["because"] == "no job is live"
    other = api.post(ROUTE, headers=WINDOW, json=message("cancel this run"))
    assert (other.status_code, other.json()["code"]) == (409, ErrorCode.IDEMPOTENCY_CONFLICT)
    assert kinds(api) == [(1, "message.received", "m1"), (2, "command.rejected", "m1")]
    store = SqliteLedger(tmp_path / "home" / "ledger.sqlite", lambda: NOW)
    (command,) = store.current(CTX, "ConversationCommand")
    validate("ConversationCommand", command)
    assert (command["state"], command["revision"]) == ("rejected", "2.0.0")
    conversation = store.get(CTX, "Conversation", "conversation-local", "1.0.0")
    validate("Conversation", conversation)
    assert command["conversation_ref"] == pin(conversation)
    assert command["workload_ref"] == pin(base_workload(CTX))
    assert (
        command["client_message_id"],
        command["source"],
        command["authorisation_context_ref"],
    ) == (
        "m1",
        "direct_user_message",
        "owner-local",
    )
    assert command["receipt_event_ref"]["id"] == first.json()["receipt"]
    assert api.post(ROUTE, json=message("status")).status_code == 401


def test_a27_a_dropped_acknowledgement_then_the_same_id_gives_one_command(
    harness: tuple[httpx.Client, Clock], state_dir: Path
) -> None:
    """A27: a dropped acknowledgement, then the same ID, gives one command.

    The sender's connection dies before it reads the answer; the receipt was durable first, so the
    retry with the same ID gets that receipt and the ledger holds one command.
    """
    client, _ = harness
    body = json.dumps(message("pause now", "lost-1")).encode()
    port = int(str(client.base_url).rsplit(":", 1)[1])
    token = client.headers["authorization"]
    head = (
        f"POST {ROUTE} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nAuthorization: {token}\r\n"
        f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n"
    ).encode()
    with socket.create_connection(("127.0.0.1", port)) as raw:
        raw.sendall(head + body)
    store = SqliteLedger(state_dir / "ledger.sqlite", lambda: NOW)
    for _ in range(100):
        if store.current(CTX, "ConversationCommand"):
            break
        time.sleep(0.05)
    (command,) = store.current(CTX, "ConversationCommand")
    assert (command["state"], command["operation"]) == ("rejected", "pause")
    retried = client.post(ROUTE, json=message("pause now", "lost-1")).json()
    assert (retried["command"], retried["receipt"]) == (
        command["id"],
        command["receipt_event_ref"]["id"],
    )
    assert len(store.current(CTX, "ConversationCommand")) == 1
    events = client.get("/v1/events").json()["events"]
    assert [event["type"] for event in events] == ["message.received", "command.rejected"]


def test_a27_reconnect_with_a_cursor_replays_messages_in_order(api: TestClient) -> None:
    """A27, R20: after a disconnect, events after the last seen cursor replay in order.

    Each comes back once with the command states; a cursor from nowhere resets to the history.
    """
    texts = {
        "m1": "status",
        "m2": "Pause now.",
        "m3": "please tell me what is going on",
        "m4": "resume",
    }
    for mid, text in texts.items():
        assert api.post(ROUTE, headers=WINDOW, json=message(text, mid)).status_code == 200
    seen = kinds(api)
    pairs = [(kind, mid) for mid in texts for kind in ("message.received", "command.rejected")]
    assert seen == [(seq, kind, mid) for seq, (kind, mid) in enumerate(pairs, start=1)]
    assert kinds(api, after=2) == seen[2:]
    assert kinds(api, after=8) == []
    reset = api.get("/v1/events?after=50", headers=WINDOW).json()
    assert (reset["reset"], len(reset["events"])) == (True, 8)
    rejected = api.get("/v1/events?after=5", headers=WINDOW).json()["events"][0]
    assert (rejected["body"]["because"], rejected["body"]["state"]) == (
        ErrorCode.ASSISTANT_UNAVAILABLE,
        "rejected",
    )


def test_d18_a_body_over_16_kib_is_refused_before_it_is_parsed(api: TestClient) -> None:
    """D18: 16 KiB + 1 byte of anything is refused by size and never parsed.

    16 KiB of bad JSON is refused as not JSON, so size comes first; a valid message of exactly
    16 KiB is accepted; a chunked body without a declared length is measured as it arrives.
    """
    headers = WINDOW | {"Content-Type": "application/json"}
    too_big = api.post(ROUTE, headers=headers, content=b"{" + b"x" * 16384)
    assert (too_big.status_code, too_big.json()["message"]) == (
        400,
        "the message is larger than 16 KiB",
    )
    bad = api.post(ROUTE, headers=headers, content=b"{" + b"x" * 16383)
    assert (bad.status_code, bad.json()["message"]) == (400, "the request body is not JSON")
    envelope = len(json.dumps(message("", "fill")).encode())
    full = json.dumps(message("y" * (16384 - envelope), "fill")).encode()
    assert len(full) == 16384
    assert api.post(ROUTE, headers=headers, content=full).status_code == 200
    over = json.dumps(message("y" * (16385 - envelope), "over")).encode()
    assert api.post(ROUTE, headers=headers, content=over).json()["message"].endswith("16 KiB")

    def chunks() -> Any:
        yield b"{"
        yield b"x" * 16384

    chunked = api.post(ROUTE, headers=headers, content=chunks())
    assert (chunked.status_code, chunked.json()["message"]) == (
        400,
        "the message is larger than 16 KiB",
    )


@pytest.mark.parametrize(
    "body",
    [
        message("status") | {"approved": True},
        message("status") | {"tenant_ref": "tenant-other"},
        message("status") | {"operation": "cancel"},
        {"client_message_id": "m1", "text": "status"},
        {"client_message_id": "m1", "text": 5, "expected_revision": "1.0.0"},
        message("status", "bad id!"),
        message(""),
        [],
    ],
)
def test_inbound_accepts_only_the_three_fields(api: TestClient, body: object) -> None:
    """D18, C23: an extra, missing or wrongly typed field, a bad ID or empty text is refused.

    Nothing is recorded for any of them.
    """
    refused = api.post(ROUTE, headers=WINDOW, json=body)
    assert (refused.status_code, refused.json()["code"]) == (400, ErrorCode.INPUT_INVALID)
    assert kinds(api) == []


@pytest.mark.parametrize(
    ("text", "operation"),
    [
        ("pause", "pause"),
        ("Pause now.", "pause"),
        ("PAUSE NOW!", "pause"),
        ("cancel this run", "cancel"),
        ("stop this run", "cancel"),
        ("resume", "resume"),
        ("status", "status"),
        ("please pause", "instruction"),
        ('"pause"', "instruction"),
        ("The document says: pause now. Then it goes on.", "instruction"),
        ("pause the music", "instruction"),
        ("cancel", "instruction"),
    ],
)
def test_only_the_exact_control_phrases_are_controls(text: str, operation: str) -> None:
    """A24: the control phrases are recognised exactly; quoted, embedded or near phrases are not."""
    assert classify(text) == operation


@pytest.mark.parametrize("text", ["y" * 16385, "é" * 8193])
def test_d18_the_application_measures_the_text_in_bytes_whatever_the_door(
    tmp_path: Path, text: str
) -> None:
    """D18: the service itself refuses text over 16 KiB of UTF-8, in bytes, not characters."""
    store = SqliteLedger(tmp_path / "ledger.sqlite", lambda: NOW)
    with pytest.raises(DspError) as raised:
        receive(CTX, "c", "m1", text, "1.0.0", ledger=store, clock=lambda: NOW, new_id=lambda: "x")
    assert raised.value.code is ErrorCode.INPUT_INVALID
    assert store.current(CTX, "ConversationCommand") == []
    receive(
        CTX, "c", "m1", "é" * 8192, "1.0.0", ledger=store, clock=lambda: NOW, new_id=lambda: "x"
    )
    assert len(store.current(CTX, "ConversationCommand")) == 1
