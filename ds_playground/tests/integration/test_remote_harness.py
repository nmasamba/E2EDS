"""The remote binding in the harness without any model: opt-in, key, policy, spend (5.6, D4 = B).

The harness itself stands in for an endpoint that is not OpenAI-compatible (404 on every route)
and for one that refuses a key (401): real HTTP, no key of the owner's, nothing sent anywhere.
"""

import json
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

from dsp.adapters.openai_compatible import OpenAICompatible
from dsp.contracts.errors import DspError, ErrorCode
from tests.conftest import Clock
from tests.integration.test_controls import say
from tests.integration.test_jobs import until
from tests.unit.test_llama_server import Memory
from tests.unit.test_remote_binding import ACCOUNT, record

Harness = tuple[httpx.Client, Clock]
STORED = "no key stored for account dsp-test-remote: `security add-generic-password"


def shown(client: httpx.Client) -> dict[str, Any]:
    """What the harness shows of its assistant."""
    found: dict[str, Any] = client.get("/v1/assistant").json()
    return found


def kinds(client: httpx.Client) -> list[str]:
    """Every event's type, in commit order."""
    return [str(e["type"]) for e in client.get("/v1/events").json()["events"]]


@pytest.fixture
def opted(state_dir: Path) -> dict[str, Any]:
    """The owner's opt-in: a remote binding record under the profile, before the harness starts."""
    (state_dir / "assistant").mkdir()
    (state_dir / "assistant" / "binding.json").write_text(json.dumps(record()))
    return record()


def test_r18_the_opted_in_remote_binding_needs_its_key_and_is_the_only_binding_tried(
    opted: dict[str, Any], harness: Harness, state_dir: Path
) -> None:
    """No key under the account: unavailable, with how to store one; final; no local model."""
    client, _ = harness
    until(lambda: shown(client)["state"] == "unavailable", 20)
    seen = shown(client)
    assert seen["reason"].startswith(STORED), seen["reason"]
    assert seen["binding"]["id"] == opted["id"]
    assert say(client, "summarise the data")["because"] == seen["reason"]
    assert say(client, "status")["because"] == "no job is live"
    time.sleep(2.5)  # two ticks: a missing key is not retried, and the local model is never tried
    assert kinds(client).count("assistant.unavailable") == 1
    assert "assistant.ready" not in kinds(client)
    assert not (state_dir / "assistant" / "server.pid").exists()


@pytest.fixture
def invalid(state_dir: Path) -> None:
    """An opt-in record that is not a binding."""
    (state_dir / "assistant").mkdir()
    (state_dir / "assistant" / "binding.json").write_text(json.dumps({"schema_version": "0.4.0"}))


def test_r18_an_invalid_record_leaves_the_assistant_unavailable_with_its_first_error(
    invalid: None, harness: Harness
) -> None:
    """The workspace opens; the record's first schema error is the reason; nothing else is tried."""
    client, _ = harness
    until(lambda: "assistant.unavailable" in kinds(client), 20)
    reason = shown(client)["reason"]
    assert reason.startswith("the remote binding in binding.json is not valid: INPUT_INVALID"), (
        reason
    )
    assert say(client, "summarise the data")["because"] == reason


def adapter(client: httpx.Client, key: str, **changes: Any) -> OpenAICompatible:
    """The adapter on the harness's own address, with ``key`` stored under the binding's account."""
    store = Memory()
    store.put(ACCOUNT, key)
    endpoint = {"base_url": f"{client.base_url}/v1", "api_key_ref": f"secret://local/{ACCOUNT}"}
    return OpenAICompatible(record(endpoint=endpoint, **changes), secrets=store)


def test_r17_the_policy_the_key_and_the_endpoint_are_checked_in_that_order(
    harness: Harness,
) -> None:
    """Nothing leaves: a 'none' policy stops before the key; a refused key and a 404 say which."""
    client, _ = harness
    token = client.headers["Authorization"].removeprefix("Bearer ")
    closed = adapter(
        client, token, data_policy={"allowed": "none", "sealed_data": False, "secrets": False}
    )
    with pytest.raises(DspError) as refused:
        closed.start()
    assert refused.value.message == "the project's data policy lets nothing leave the machine"
    with pytest.raises(DspError) as refused:
        OpenAICompatible(record(), secrets=Memory()).start()
    assert refused.value.message.startswith(STORED)
    with pytest.raises(DspError) as refused:
        adapter(client, "not-the-token").start()
    assert refused.value.message == f"the endpoint refused the key for account {ACCOUNT}"
    with pytest.raises(DspError) as refused:
        adapter(client, token).start()
    assert refused.value.message == "the endpoint answered 404"
    assert refused.value.code == ErrorCode.ASSISTANT_UNAVAILABLE


def test_r17_a_charge_the_limit_cannot_cover_is_refused_before_anything_is_sent(
    harness: Harness,
) -> None:
    """With no tokenizer the count is a high bound; the projected charge is checked first."""
    client, _ = harness
    token = client.headers["Authorization"].removeprefix("Bearer ")
    spend = {
        "price_per_million_tokens_minor": 10**9,
        "approved_by": "owner",
        "approved_at": "2026-10-16T00:00:00Z",
    }
    priced = adapter(client, token, spend=spend)
    priced.key, priced.ready = token, True  # as a passed start leaves it
    text = "hello world"
    assert priced.count(text) == len(text.encode()) // 2 + 1  # the harness has no /tokenize
    messages = [{"role": "user", "content": "x" * 100}]
    with pytest.raises(DspError) as refused:
        priced.complete(messages, [], max_tokens=10, deadline=5, seed=1, temperature=0)
    assert refused.value.message.startswith(
        "the spend limit of GBP 0.00 would be exceeded: GBP 0.00 spent"
    )
    assert priced.alive()  # a refused charge is not a dead endpoint: the owner can raise the limit
    free = adapter(client, token)
    free.key, free.ready = token, True
    with pytest.raises(DspError) as refused:
        free.complete(messages, [], max_tokens=10, deadline=5, seed=1, temperature=0)
    assert refused.value.message == "the endpoint answered 404"
    assert not free.alive()
