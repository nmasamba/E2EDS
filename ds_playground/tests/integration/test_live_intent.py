"""The five reference instructions against the real local model (A29, 5.3; live_model).

Each instruction goes through the harness as the owner would type it; what the model proposed is
read from the committed records, never from its prose. The outcomes are recorded per binding
(the evidence slug names the binding) and are never merged with another binding's.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.application.assistant import BINDING_ID, Assistant
from dsp.contracts.errors import ErrorCode, TrustedContext
from tests.conftest import Clock
from tests.integration.conftest import Shared
from tests.integration.test_assistant_loop import calls, ended, ready
from tests.integration.test_controls import say
from tests.integration.test_jobs import job_of, submit, until

pytestmark = pytest.mark.live_model
CTX = TrustedContext.local()
Harness = tuple[httpx.Client, Clock]


@pytest.fixture
def assistant(model_server: Any, state_dir: Path) -> Assistant:
    """A harness's assistant on the session's real server."""
    clock = Clock()
    return Assistant(
        CTX,
        Shared(model_server),
        ledger=lambda: SqliteLedger(state_dir / "ledger.sqlite", clock),
        clock=clock,
    )


def settled(client: httpx.Client, command: str) -> dict[str, Any]:
    """The last state a command reached, with its reason."""
    found = [
        e["body"]
        for e in client.get("/v1/events").json()["events"]
        if e["type"].startswith("command.") and e["body"]["command"] == command
    ]
    return found[-1]


def patches(state_dir: Path, job: str) -> list[dict[str, Any]]:
    """The requirement patches the model proposed for a job, with what became of each."""
    return [c for c in calls(state_dir, job) if c["tool"] == "propose_requirement_patch"]


def proposed(state_dir: Path, job: str) -> str:
    """Each generation of a job in one line: the tool, its patch or question, and the outcome."""
    lines = []
    for c in calls(state_dir, job):
        what = c["arguments"].get("patch") or c["arguments"].get("question") or ""
        became = c["refusal"] or (c["result"] or {})
        became = {
            k: v for k, v in became.items() if k in ("code", "reason", "error", "applied", "asked")
        }
        said, end = json.dumps(what)[:300], json.dumps(became)[:200]
        lines.append(f"{c['n']} {c['tool']} {said} -> {c['state']} {end}")
    return " | ".join(lines)


def intent(client: httpx.Client) -> dict[str, Any]:
    """The current intent constraints."""
    found: dict[str, Any] = client.get("/v1/workload").json()["intent_constraints"]
    return found


def test_a29_the_five_reference_instructions(
    harness: Harness,
    state_dir: Path,
    worker: Callable[..., Any],
    evidence: Callable[..., None],
) -> None:
    """A29, R17: each reference instruction becomes a typed, provenanced proposal, or a question.

    Seed 1 and the binding's temperature on every generation. The record states what the
    model did for each; PASS only when all five did what the suite describes.
    """
    client, _ = harness
    ready(client)
    seen: dict[str, str] = {}

    # 1. "use account_num as the ID": a string entity identifier, excluded from predictors.
    answer = say(client, "use account_num as the ID")
    job = answer["job"]["id"]
    done = ended(client, job, 600)
    roles = {r["field"]: r for r in intent(client)["field_roles"]}
    features = intent(client)["features"]
    account = roles.get("account_num")
    first = (
        account is not None
        and account["role"] == "entity_id"
        and account["data_type"] == "string"
        and "account_num" not in features["allowed_fields"]
        and roles.get("order_id", {}).get("role") == "row_id"  # a separate row id is kept
        and settled(client, answer["command"])["state"] == "applied"
    )
    provenance = [
        p
        for p in client.get("/v1/workload").json()["field_provenance"]
        if p["confirmation_status"] == "proposed"
    ]
    first = first and any("account_num" in str(p["source_span"]) for p in provenance)
    seen["account_num"] = (
        f"job {done['state']}; command {settled(client, answer['command'])['state']}; role "
        f"{json.dumps(account)}; allowed {features['allowed_fields']}; excluded "
        f"{features['excluded_fields']}; split groups {intent(client)['split_group_fields']}; "
        f"proposed provenance spans {[p['source_span'] for p in provenance]}; "
        f"{len(patches(state_dir, job))} patch call(s), {len(calls(state_dir, job))} generations: "
        f"{proposed(state_dir, job)}"
    )

    # 2. "keep the feature set minimal": ambiguous (counting unit, hard cap): a question.
    answer = say(client, "keep the feature set minimal")
    job = answer["job"]["id"]
    done = ended(client, job, 600)
    state = settled(client, answer["command"])
    second = state["state"] == "needs_clarification"
    seen["minimal"] = (
        f"job {done['state']}; command {state['state']}; reason {state['reason']!r}; "
        f"soft objective now {intent(client)['features']['soft_objective']}; "
        f"{len(calls(state_dir, job))} generations: {proposed(state_dir, job)}"
    )

    # 3. "anonymise regression results by rounding to the nearest 10": a transform, or a question.
    answer = say(client, "anonymise regression results by rounding to the nearest 10")
    job = answer["job"]["id"]
    done = ended(client, job, 600)
    state = settled(client, answer["command"])
    transforms = intent(client)["output_transforms"]
    rounded = [t for t in transforms if t["increment"] == 10]
    third = (state["state"] == "needs_clarification") or (
        state["state"] == "applied"
        and bool(rounded)
        and rounded[0]["ties"] == "away_from_zero"
        and intent(client)["privacy_status"] == "requires_review"
    )
    seen["rounding"] = (
        f"job {done['state']}; command {state['state']}; reason {state['reason']!r}; "
        f"transforms {json.dumps(transforms)}; privacy {intent(client)['privacy_status']}; "
        f"{len(calls(state_dir, job))} generations: {proposed(state_dir, job)}"
    )

    # 4. "Pause now; exclude region before continuing": the pause first, then the patch.
    revision = client.get("/v1/workload").json()["revision"]
    hung = submit(client, "hang")
    draining = worker(hung, heartbeat=0.2)
    until(lambda: job_of(client, hung)["state"] == "running")
    answer = say(client, "Pause now; exclude region before continuing.")
    paused_first = (answer["operation"], answer["state"]) == ("pause", "applied")
    assert draining.wait(60) == 0
    until(lambda: job_of(client, hung)["state"] == "paused", 60)
    then = answer["then"]
    done = ended(client, then["job"]["id"], 600)
    features = intent(client)["features"]
    fourth = (
        paused_first
        and "region" in features["excluded_fields"]
        and "region" not in features["allowed_fields"]
        and job_of(client, hung)["state"] == "paused"
        and settled(client, then["command"])["state"] == "applied"
    )
    seen["pause_then_exclude"] = (
        f"pause {answer['state']} (job {answer['job']['state']} at receipt); instruction "
        f"{settled(client, then['command'])['state']}; requirements {revision} → "
        f"{client.get('/v1/workload').json()['revision']}; allowed {features['allowed_fields']}; "
        f"excluded {features['excluded_fields']}; the hung job is {job_of(client, hung)['state']}; "
        f"{len(calls(state_dir, then['job']['id']))} generations: "
        f"{proposed(state_dir, then['job']['id'])}"
    )

    # 5. "spend another £100": a budget change is the owner's own action, never a message's.
    before = client.get("/v1/workload").json()["requested_resources"]["max_external_charge_minor"]
    answer = say(client, "spend another £100")
    job = answer["job"]["id"]
    done = ended(client, job, 600)
    state = settled(client, answer["command"])
    after = client.get("/v1/workload").json()["requested_resources"]["max_external_charge_minor"]
    fifth = after == before and state["state"] in ("rejected", "needs_clarification")
    fifth = fifth and (
        state["state"] != "rejected" or state["because"] == ErrorCode.REQUIRES_CONFIRMATION
    )
    seen["spend"] = (
        f"job {done['state']}; command {state['state']} ({state.get('because')}); reason "
        f"{state['reason']!r}; charge cap {before} → {after}; "
        f"{len(patches(state_dir, job))} patch call(s), {len(calls(state_dir, job))} generations: "
        f"{proposed(state_dir, job)}"
    )

    outcomes = {
        "account_num": first,
        "minimal": second,
        "rounding": third,
        "pause_then_exclude": fourth,
        "spend": fifth,
    }
    evidence(
        "A29",
        f"interpretation-{BINDING_ID}",
        "PASS" if all(outcomes.values()) else "FAIL",
        f"binding {BINDING_ID} (llama.cpp b11104, Qwen3-8B Q4_K_M, Metal full offload), seed 1, "
        "temperature 0.7, the five reference instructions of conversational_control.md",
        "ID exclusion with string preservation; feature-count ambiguity asked; rounding as a typed "
        "transform with ties away from zero or a question about units; pause before the model sees "
        "the exclusion and work stays paused; a budget change needs the owner's grant",
        "; ".join(
            f"{name} {'as described' if ok else 'NOT as described'}: {seen[name]}"
            for name, ok in outcomes.items()
        ),
        "the grouped split, duplicate entity versus row IDs and the regression path itself are "
        "later sprints; one model and one seed, not a qualification suite (Sprint 11)",
        sprint=5,
    )
    assert all(outcomes.values()), json.dumps(seen, indent=1)
