"""The remote, OpenAI-compatible binding (0.4.0) and the adapter's arithmetic (5.6, D4 = B)."""

from typing import Any

import pytest

from dsp.adapters.openai_compatible import OpenAICompatible
from dsp.application.assistant import remote_binding
from dsp.application.grants import PROJECT
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from tests.unit.test_llama_server import Memory

CTX = TrustedContext.local()
ACCOUNT = "dsp-test-remote"  # an account no owner stores: the key path is the test's own


def record(**changes: Any) -> dict[str, Any]:
    """A valid remote binding record for an endpoint on this machine; ``changes`` are top-level."""
    found: dict[str, Any] = {
        "schema_version": "0.4.0",
        "planning_only": True,
        "id": "assistant-remote-qwen",
        "revision": "1.0.0",
        "tenant_ref": CTX.tenant,
        "project_ref": PROJECT,
        "state": "proposed",
        "mode": "remote_openai_compatible",
        "profile_id": "assistant-remote-v1",
        "provider": {"name": "llama.cpp", "model": "qwen3-8b"},
        "endpoint": {
            "base_url": "http://127.0.0.1:8081/v1",
            "api_key_ref": f"secret://local/{ACCOUNT}",
        },
        "placement": {"host": "127.0.0.1", "leaves_machine": False},
        "data_policy": {
            "allowed": "synthetic_fixtures_only",
            "sealed_data": False,
            "secrets": False,
        },
        "spend": {
            "price_per_million_tokens_minor": 0,
            "approved_by": "owner",
            "approved_at": "2026-10-16T00:00:00Z",
        },
        "limits": {
            "context_tokens": 8192,
            "max_input_tokens": 6144,
            "max_output_tokens": 2048,
            "concurrent_generations": 1,
            "generation_deadline_seconds": 300,
            "max_model_calls_per_task": 20,
            "max_code_repairs_per_task": 2,
            "max_generation_seconds_per_task": 1800,
            "max_external_charge_minor": 0,
            "currency": "GBP",
        },
        "decoding": {"temperature": 0, "top_p": 0.8},
        "privacy": {"remote_fallback": False, "automatic_downloads": False},
        "observed": None,
        "operator_ref": CTX.principal,
        "payer_ref": CTX.principal,
        "qualification": {"status": "planned", "report_ref": None, "observed_hardware_ref": None},
    }
    return found | changes


def test_a_remote_binding_is_planning_until_observed_and_every_policy_field_is_required() -> None:
    """0.4.0 is the remote mode only: the policy, the spend and the placement cannot be left out."""
    planning = remote_binding(record())
    assert (planning["planning_only"], planning["observed"]) == (True, None)
    seen = {"model": "qwen3-8b", "probe_seconds": 1.25, "placement": {"host": "127.0.0.1"}}
    observed = remote_binding(record(), seen)
    assert (observed["planning_only"], observed["observed"]) == (
        False,
        {"model": "qwen3-8b", "probe_seconds": 1.25},
    )
    refused = [
        {k: v for k, v in record().items() if k != "data_policy"},
        record(mode="local_supervised"),
        record(
            data_policy={
                "allowed": "synthetic_fixtures_only",
                "sealed_data": True,
                "secrets": False,
            }
        ),
        record(data_policy={"allowed": "everything", "sealed_data": False, "secrets": False}),
        record(spend={"price_per_million_tokens_minor": 0, "approved_by": "assistant"}),
        record(endpoint={"base_url": "ftp://x", "api_key_ref": "secret://local/a"}),
        record(endpoint={"base_url": "http://x/v1", "api_key_ref": "/etc/key"}),
        record(privacy={"remote_fallback": True, "automatic_downloads": False}),
        record(schema_version="0.3.0"),
    ]
    for wrong in refused:
        with pytest.raises(DspError) as error:
            remote_binding(wrong)
        assert error.value.code == ErrorCode.INPUT_INVALID, wrong


def test_the_charge_is_the_price_rounded_up_and_a_free_endpoint_charges_nothing() -> None:
    """Minor units per million tokens; any fraction of a minor unit counts as one."""
    priced = record(
        spend={
            "price_per_million_tokens_minor": 1000,
            "approved_by": "owner",
            "approved_at": "2026-10-16T00:00:00Z",
        }
    )
    adapter = OpenAICompatible(priced, secrets=Memory())
    assert [adapter.charge(n) for n in (0, 1, 999, 1_000_000, 1_000_001)] == [0, 1, 1, 1000, 1001]
    assert OpenAICompatible(record(), secrets=Memory()).charge(10**9) == 0


def test_the_account_and_a_socket_endpoint_come_from_the_record() -> None:
    """The key's account is the reference's last part; a unix:// base URL is a socket client."""
    adapter = OpenAICompatible(record(), secrets=Memory())
    assert (adapter.account, str(adapter.client.base_url)) == (ACCOUNT, "http://127.0.0.1:8081")
    socket = record(
        endpoint={"base_url": "unix:///tmp/llama.sock", "api_key_ref": "secret://local/a"}
    )
    assert str(OpenAICompatible(socket, secrets=Memory()).client.base_url) == "http://remote"
