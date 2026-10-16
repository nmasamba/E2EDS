"""The OpenAI-compatible binding against llama-server itself (5.6, D4 = B; live_model).

llama-server is an OpenAI-compatible server on this machine: the remote adapter reaches it through
its models, chat and tokenize routes with the key the session's server was started with, held in a
test-only secret store under the binding's account. No key of the owner's, no spend, nothing leaves
the machine; the local binding is never tried in its place.
"""

import json
import sys
import time
from functools import partial
from pathlib import Path
from typing import Any

import httpx
import pytest

from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.adapters.openai_compatible import OpenAICompatible
from dsp.application.assistant import Assistant, remote_binding
from dsp.contracts.errors import TrustedContext
from tests.conftest import Clock
from tests.integration.test_assistant_loop import ended, ready
from tests.integration.test_controls import say
from tests.integration.test_jobs import until
from tests.integration.test_remote_harness import kinds, shown
from tests.unit.test_llama_server import Memory
from tests.unit.test_remote_binding import ACCOUNT, record

pytestmark = pytest.mark.live_model
CTX = TrustedContext.local()
Harness = tuple[httpx.Client, Clock]
SPENT = {
    "price_per_million_tokens_minor": 10**9,
    "approved_by": "owner",
    "approved_at": "2026-10-16T00:00:00Z",
}


def binding(model_server: Any, **changes: Any) -> dict[str, Any]:
    """The remote record for the session's llama-server: TCP on macOS, its socket on Linux."""
    base = (
        "http://127.0.0.1:8081/v1" if sys.platform == "darwin" else f"unix://{model_server.socket}"
    )
    listed = model_server.client.get("/v1/models", headers=model_server.headers()).json()
    provider = {"name": "llama.cpp", "model": str(listed["data"][0]["id"])}
    endpoint = {"base_url": base, "api_key_ref": f"secret://local/{ACCOUNT}"}
    return record(**({"endpoint": endpoint, "provider": provider} | changes))


@pytest.fixture
def assistant(model_server: Any, state_dir: Path, request: pytest.FixtureRequest) -> Assistant:
    """A harness assistant on the remote adapter; a test may change the record or the key."""
    options: dict[str, Any] = getattr(request, "param", {})
    rec = binding(model_server, **options.get("changes", {}))
    store = Memory()
    store.put(ACCOUNT, options.get("key", model_server.key))
    clock = Clock()
    return Assistant(
        CTX,
        OpenAICompatible(rec, secrets=store),
        ledger=lambda: SqliteLedger(state_dir / "ledger.sqlite", clock),
        clock=clock,
        describe=partial(remote_binding, rec),
    )


def test_r17_the_remote_binding_is_ready_with_its_policy_shown_and_answers_from_llama_server(
    harness: Harness, assistant: Assistant, model_server: Any
) -> None:
    """Ready after the probe; placement, policy and spend are in the ready event; it answers."""
    client, _ = harness
    ready(client, 120)
    events = client.get("/v1/events").json()["events"]
    (up,) = [e["body"] for e in events if e["type"] == "assistant.ready"]
    assert up["profile"] == "assistant-remote-v1"
    assert up["placement"] == {"host": "127.0.0.1", "leaves_machine": False}
    assert up["data_policy"]["allowed"] == "synthetic_fixtures_only"
    assert (up["spend"]["price_per_million_tokens_minor"], up["spend_limit_minor"]) == (0, 0)
    seen = shown(client)["binding"]
    assert (seen["id"], seen["planning_only"]) == ("assistant-remote-qwen", False)
    assert seen["observed"]["model"] == assistant.binding["provider"]["model"]
    sample = "the quick brown fox jumps over the lazy dog"
    assert assistant.server is not None
    assert assistant.server.count(sample) == model_server.count(sample)  # the server's tokenizer
    answer = say(client, "What is 7 times 8? Answer with the number only.")
    assert answer["state"] == "accepted", answer
    assert ended(client, answer["job"]["id"], 120)["state"] == "succeeded"
    events = client.get("/v1/events").json()["events"]
    (said,) = [e["body"]["text"] for e in events if e["type"] == "assistant.answered"]
    assert "56" in said, said
    assert "assistant-local-qwen" not in json.dumps(events)  # the local binding is never tried


@pytest.mark.parametrize(
    ("assistant", "reason"),
    [
        (
            {"changes": {"provider": {"name": "llama.cpp", "model": "nope"}}},
            "model nope is not served (served: ",
        ),
        ({"key": "not-the-key"}, f"the endpoint refused the key for account {ACCOUNT}"),
        ({"changes": {"spend": SPENT}}, "the spend limit of GBP 0.00 would be exceeded"),
    ],
    indirect=["assistant"],
)
def test_r17_a_wrong_model_a_refused_key_or_an_unaffordable_probe_is_final_and_tries_nothing_else(
    harness: Harness, reason: str
) -> None:
    """Each ends in assistant_unavailable with its reason, once; the local binding is not tried."""
    client, _ = harness
    until(lambda: shown(client)["state"] == "unavailable", 120)
    assert shown(client)["reason"].startswith(reason), shown(client)["reason"]
    assert say(client, "summarise the data")["because"] == shown(client)["reason"]
    time.sleep(2.5)  # two ticks: final, no restart
    seen = kinds(client)
    assert (seen.count("assistant.unavailable"), seen.count("assistant.ready")) == (1, 0)
    assert shown(client)["binding"]["id"] == "assistant-remote-qwen"
