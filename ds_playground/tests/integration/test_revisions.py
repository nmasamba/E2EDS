"""Requirement revisions driven for real: typed patches, impact, stale marks and conflicts (A26)."""

import subprocess
import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.application.workloads import base_workload, impact_of, patch_for
from dsp.contracts.canonical import pin
from dsp.contracts.errors import ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from tests.conftest import Clock
from tests.integration.test_controls import control, say
from tests.integration.test_jobs import job_of, submit, until

Harness = tuple[httpx.Client, Clock]
Worker = Callable[..., subprocess.Popen[bytes]]
CTX = TrustedContext.local()
NOW = "2026-10-08T10:00:00+00:00"
MESSAGES = "/v1/conversations/conversation-local/messages"


def change(client: httpx.Client, text: str, expected: str = "1.0.0", mid: str = "") -> Any:
    """A change instruction against an expected revision, as the composer sends it."""
    body = {
        "client_message_id": mid or uuid.uuid4().hex,
        "text": text,
        "expected_revision": expected,
    }
    answer = client.post(MESSAGES, json=body)
    assert answer.status_code == 200, answer.text
    return answer.json()


def test_a26_excluding_a_field_mid_run_revises_holds_and_leaves_old_results_where_they_were(
    harness: Harness, worker: Worker, state_dir: Path
) -> None:
    """A26: a field is excluded while work runs.

    The diff, impact, new immutable revision and stale marks are recorded; the finished job's
    result stays on the old revision; the running job is held and an explicit resume readmits it
    under the new revision; the next admission pins a plan for the new revision.
    """
    client, _ = harness
    done = submit(client, "sleep", seconds=0.1)
    assert worker(done).wait(20) == 0
    hung = submit(client, "hang")
    draining = worker(hung, heartbeat=0.2)
    until(lambda: job_of(client, hung)["state"] == "running")
    before = job_of(client, done)

    answer = change(client, "exclude field region")
    assert (answer["state"], answer["operation"]) == ("applied", "change_requirements")
    assert answer["workload"] == {"id": "workload-test-job", "revision": "2.0.0"}
    impact = answer["impact"]
    assert impact["changed"] == [
        "/intent_constraints/features/allowed_fields",
        "/intent_constraints/features/excluded_fields",
    ]
    assert impact["invalidates"] == ["checkpoint", "result"]
    assert impact["stale"] == [
        {"job": done, "kind": "result", "sha256": before["result"]["sha256"]}
    ]
    assert impact["holds"] == [hung]

    current = client.get("/v1/workload").json()
    validate("WorkloadSpec", current)
    assert current["revision"] == "2.0.0"
    assert current["intent_constraints"]["features"] == base_workload(CTX)["intent_constraints"][
        "features"
    ] | {
        "allowed_fields": ["item_count"],
        "excluded_fields": ["order_id", "region"],
    }
    provenance = current["field_provenance"][-1]
    assert (provenance["source_kind"], provenance["source_span"], provenance["confirmed_by"]) == (
        "direct_user_message",
        "exclude field region",
        "owner-local",
    )
    store = SqliteLedger(state_dir / "ledger.sqlite", lambda: NOW)
    assert store.get(CTX, "WorkloadSpec", "workload-test-job", "1.0.0") == base_workload(CTX)
    assert job_of(client, done) == before
    assert before["workload_ref"]["revision"] == "1.0.0"
    revised = [
        e for e in client.get("/v1/events").json()["events"] if e["type"] == "workload.revised"
    ]
    assert len(revised) == 1
    assert (revised[0]["body"]["from"], revised[0]["body"]["to"]) == ("1.0.0", "2.0.0")
    assert revised[0]["body"]["patch"] == patch_for("exclude field region", base_workload(CTX))
    applied = [
        e for e in client.get("/v1/events").json()["events"] if e["type"] == "command.applied"
    ]
    assert applied[-1]["body"]["patch"] == revised[0]["body"]["patch"]
    assert applied[-1]["body"]["effect"] == pin(current)

    assert draining.wait(20) == 0
    until(lambda: job_of(client, hung)["state"] == "paused")
    assert job_of(client, hung)["workload_ref"]["revision"] == "1.0.0"
    resumed = control(client, hung, "resume")
    assert (resumed["job"]["state"], resumed["job"]["workload_ref"]["revision"]) == (
        "queued",
        "2.0.0",
    )
    later = submit(client, "hang")
    request_ref = job_of(client, later)["request_ref"]
    request = store.get(CTX, "ExecutionRequest", request_ref["id"], request_ref["revision"])
    plan = store.get(CTX, "WorkflowPlan", request["workflow_plan_ref"]["id"], "1.0.0")
    assert (request["requirement_revision"], plan["workload_ref"]["revision"]) == ("2.0.0", "2.0.0")


def test_a26_two_concurrent_edits_conflict_predictably(harness: Harness) -> None:
    """A26: two edits against the same expected revision conflict predictably.

    Exactly one applies and the other is REVISION_CONFLICT; a later edit with the stale revision
    conflicts; one with the current revision applies.
    """
    client, _ = harness
    outcomes: list[Any] = []
    ready = threading.Barrier(2)

    def edit(text: str, done: list[Any] = outcomes, go: threading.Barrier = ready) -> None:
        go.wait()
        done.append(change(client, text))

    racers = [
        threading.Thread(target=edit, args=(t,))
        for t in ("exclude field region", "exclude field item_count")
    ]
    for racer in racers:
        racer.start()
    for racer in racers:
        racer.join()
    assert sorted(o["state"] for o in outcomes) == ["applied", "rejected"]
    assert client.get("/v1/workload").json()["revision"] == "2.0.0"
    (left,) = client.get("/v1/workload").json()["intent_constraints"]["features"]["allowed_fields"]
    stale = change(client, f"exclude field {left}", expected="1.0.0")
    assert (stale["state"], stale["because"]) == (
        "rejected",
        "the requirements are at 2.0.0, not 1.0.0",
    )
    assert client.get("/v1/workload").json()["revision"] == "2.0.0"
    fresh = change(client, f"exclude field {left}", expected="2.0.0")
    assert (fresh["state"], fresh["workload"]["revision"]) == ("applied", "3.0.0")
    events = [
        e for e in client.get("/v1/events").json()["events"] if e["type"] == "command.rejected"
    ]
    assert [e["body"]["because"] for e in events] == [ErrorCode.REVISION_CONFLICT] * 2


def test_a26_budget_and_evaluation_changes_need_the_owner_and_unknown_fields_are_refused(
    harness: Harness,
) -> None:
    """A26: budget and evaluation changes need the owner; unknown fields are refused.

    A budget or evaluation change is typed, recorded and refused without the owner's action; an
    unknown, non-predictor or already excluded field is refused; nothing is revised.
    """
    client, _ = harness
    budget = change(client, "set budget to 500")
    assert (budget["state"], budget["operation"]) == ("rejected", "change_requirements")
    assert budget["because"].startswith(
        "a budget change (/requested_resources/max_external_charge_minor)"
    )
    evaluation = change(client, "Change the evaluation to accuracy.")
    assert "evaluation change (/evaluation_contract_ref)" in evaluation["because"]
    for text in ("exclude field colour", "exclude field order_id", "exclude the field Region"):
        refused = change(client, text)
        assert (refused["state"], "not an allowed predictor field" in refused["because"]) == (
            "rejected",
            True,
        ), text
    assert client.get("/v1/workload").json()["revision"] == "1.0.0"
    rejected = [
        e for e in client.get("/v1/events").json()["events"] if e["type"] == "command.rejected"
    ]
    assert [e["body"]["because"] for e in rejected] == [
        ErrorCode.REQUIRES_CONFIRMATION,
        ErrorCode.REQUIRES_CONFIRMATION,
        ErrorCode.INPUT_INVALID,
        ErrorCode.INPUT_INVALID,
        ErrorCode.INPUT_INVALID,
    ]
    assert rejected[0]["body"]["patch"] == [
        {"op": "replace", "path": "/requested_resources/max_external_charge_minor", "value": 500}
    ]
    assert rejected[2]["body"]["patch"] == []
    assert say(client, "exclude field region and set budget to 5")["operation"] == "instruction"


def test_the_dependency_graph_marks_only_what_depends_on_the_change(tmp_path: Path) -> None:
    """A26: the impact names only what depends on the change.

    The changed paths, the evidence kinds that depend on them and the stale items of jobs on this
    revision; a job on another revision is untouched.
    """
    store = SqliteLedger(tmp_path / "ledger.sqlite", lambda: NOW)
    base = base_workload(CTX)
    patch = patch_for("exclude field item_count", base)
    assert impact_of(CTX, patch, base, store) == {
        "changed": [
            "/intent_constraints/features/allowed_fields",
            "/intent_constraints/features/excluded_fields",
        ],
        "invalidates": ["checkpoint", "result"],
        "stale": [],
        "holds": [],
    }
    assert (
        impact_of(CTX, [{"op": "replace", "path": "/purpose/task", "value": "x"}], base, store)[
            "invalidates"
        ]
        == []
    )
