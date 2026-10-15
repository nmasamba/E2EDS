"""The assistant in the harness: the workspace opens without the model and says so (R18)."""

import time

import httpx

from tests.conftest import Clock
from tests.integration.test_controls import say

Harness = tuple[httpx.Client, Clock]


def test_r18_the_workspace_opens_with_the_model_absent_and_shows_assistant_unavailable(
    harness: Harness,
) -> None:
    """R18, A30: no model, so the assistant is unavailable with the reason; everything else works.

    The state names the binding it would use (no secret, no path), the trail carries the
    unavailable event, an instruction is rejected as ASSISTANT_UNAVAILABLE with that reason, and
    a control phrase still answers on the fast path.
    """
    client, _ = harness
    for _ in range(100):
        shown = client.get("/v1/assistant").json()
        if shown["state"] == "unavailable" and shown["reason"] == "model missing":
            break
        time.sleep(0.05)
    assert (shown["state"], shown["reason"]) == ("unavailable", "model missing")
    assert shown["binding"]["id"] == "assistant-local-qwen"
    assert shown["binding"]["endpoint"]["api_key_ref"] == "secret://local/assistant-api-key"
    assert "/" not in shown["binding"]["model"]["local_path_ref"].split("://")[1]
    events = client.get("/v1/events").json()["events"]
    (unavailable,) = [e for e in events if e["type"] == "assistant.unavailable"]
    assert unavailable["body"]["reason"] == "model missing"
    assert not [e for e in events if e["type"] == "assistant.ready"]
    told = say(client, "summarise the data")
    assert (told["operation"], told["state"]) == ("instruction", "rejected")
    assert say(client, "status")["because"] == "no job is live"
