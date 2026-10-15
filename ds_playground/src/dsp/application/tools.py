"""The assistant's tools: the eight typed calls the application owns, validates and dispatches.

The list is the assistant-gateway skill's and nothing else: inspect an approved schema, propose a
typed requirement patch, write a code artifact, submit a validated code task, inspect redacted
results, request a permitted trial, assemble an evidence report, propose a release. There is no
shell, no grant and no sealed-data tool. A call is checked in order, schema, principal, revision,
scope, budget, fence, before anything runs (the loop does the budget and the fence); the model's
arguments never reach a process as a command string. Everything a tool returns enters the model's
context as quoted data.
"""

import csv
import io
import json
from collections.abc import Callable
from typing import Any

from jsonschema import Draft202012Validator

from dsp.application.workloads import apply_patch, complete, current_workload, describe, revise
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.ports import Ledger, Store

MAX_SOURCE = 64 * 1024
FAILURE_CHARS = 200  # a task's failure message is text the task chose: bounded and quoted
NOT_YET = "nothing of that kind exists yet: trials, evaluations and releases come in later sprints"
HANDLE = {
    "type": "string",
    "minLength": 1,
    "maxLength": 160,
    "pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]*$",
}
DIGEST = {"type": "string", "pattern": "^sha256:[a-f0-9]{64}$"}
NAME = {
    "type": "string",
    "minLength": 1,
    "maxLength": 100,
    "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]*$",
}
TOOLS: dict[str, dict[str, Any]] = {
    "inspect_schema": {
        "description": "Profile one CSV the owner granted (columns, proposed types, counts, ranges)"
        " by running the reviewed profiling recipe in the sandbox. Returns the data's id to"
        " name as a task input.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "source": HANDLE | {"description": "a granted source folder's handle"},
                "path": {"type": "string", "minLength": 1, "maxLength": 300},
            },
            "required": ["source", "path"],
        },
    },
    "propose_requirement_patch": {
        "description": "Propose typed changes to the requirements as a JSON patch on the"
        " WorkloadSpec shown in the workspace state (/intent_constraints/field_roles, a list of"
        " {field, role: row_id|entity_id|split_group|predictor|target, data_type:"
        " string|number|integer|boolean, nullable, public_output:"
        " excluded|authorised_join_only|task_output}; /intent_constraints/features"
        " {allowed_fields, excluded_fields, count_basis: source_fields|transformed_features,"
        " hard_max_count, soft_objective: none|minimise_count_among_feasible};"
        " /intent_constraints/split_group_fields; /intent_constraints/output_transforms, a list"
        " of {operation: round_to_increment, output_field, increment, units, ties:"
        " away_from_zero|to_even, raw_value_public: false, privacy_claim: precision_only};"
        " /intent_constraints/privacy_status: not_requested|requires_review;"
        " /requested_resources/max_external_charge_minor, which only the owner may change)."
        " Every patched path needs a provenance entry quoting the exact words of the instruction"
        " it comes from, with your extraction confidence and how material the change is. When"
        " an ambiguity would change material work, ask one question instead of patching.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "expected_revision": {"type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"},
                "patch": {
                    "type": "array",
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "op": {"enum": ["add", "replace", "remove"]},
                            "path": {"type": "string", "pattern": "^/"},
                            "value": {},
                        },
                        "required": ["op", "path", "value"],
                    },
                },
                "provenance": {
                    "type": "array",
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "field": {"type": "string", "pattern": "^/"},
                            "span": {"type": "string", "minLength": 1, "maxLength": 500},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "materiality": {"enum": ["low", "medium", "high"]},
                        },
                        "required": ["field", "span", "confidence", "materiality"],
                    },
                },
                "question": {
                    "type": ["string", "null"],
                    "maxLength": 500,
                    "description": "Set this when an ambiguity changes material work: the owner"
                    " is asked it; a patch in the same call applies first (the unambiguous part).",
                },
            },
            "required": ["expected_revision", "patch", "provenance", "question"],
        },
    },
    "write_code_artifact": {
        "description": "Store Python or SQL source as an immutable artifact; name the artifact it"
        " repairs, if any (at most two repairs per task). Python reads inputs from"
        " ../inputs/<name> and writes outputs beside itself; SQL sees each input as a table"
        " named like its input and its last statement's rows are its one output.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "language": {"enum": ["python", "sql"]},
                "source": {"type": "string", "minLength": 1, "maxLength": MAX_SOURCE},
                "repairs": {"anyOf": [DIGEST, {"type": "null"}]},
            },
            "required": ["language", "source", "repairs"],
        },
    },
    "submit_code_task": {
        "description": "Run a stored artifact in the sandbox as a job on named inputs (data ids"
        " from inspect_schema) producing named outputs; returns the job's outcome once it ended.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "artifact": DIGEST,
                "language": {"enum": ["python", "sql"]},
                "inputs": {
                    "type": "array",
                    "maxItems": 16,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {"name": NAME, "data": HANDLE},
                        "required": ["name", "data"],
                    },
                },
                "outputs": {"type": "array", "minItems": 1, "maxItems": 16, "items": NAME},
            },
            "required": ["artifact", "language", "inputs", "outputs"],
        },
    },
    "inspect_results": {
        "description": "See a job this task submitted: its state, why it failed, its outputs, and,"
        " for the output you name, a bounded preview (a CSV's header and first 20 rows, or the"
        " first 2,000 characters of a JSON or text file).",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"job": HANDLE, "output": {"anyOf": [NAME, {"type": "null"}]}},
            "required": ["job", "output"],
        },
    },
    "request_trial": {
        "description": "Request one permitted optimisation trial.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"trial": {"type": "string", "minLength": 1, "maxLength": 200}},
            "required": ["trial"],
        },
    },
    "assemble_evidence_report": {
        "description": "Assemble the evidence report from committed artifacts.",
        "parameters": {"type": "object", "additionalProperties": False, "properties": {}},
    },
    "propose_release": {
        "description": "Propose a release of the committed results.",
        "parameters": {"type": "object", "additionalProperties": False, "properties": {}},
    },
}
NEEDS = {  # the scope a principal must hold to make the call (checked after the schema)
    "propose_requirement_patch": "workload:interact",
    "submit_code_task": "job:submit",
    "inspect_schema": "job:submit",
    "request_trial": "job:submit",
    "propose_release": "job:submit",
}
VALIDATORS = {name: Draft202012Validator(tool["parameters"]) for name, tool in TOOLS.items()}


def catalogue() -> list[dict[str, Any]]:
    """The tools as the model sees them: name, description and parameter schema."""
    return [
        {"type": "function", "function": {"name": name, **tool}} for name, tool in TOOLS.items()
    ]


def check(ctx: TrustedContext, name: str, arguments: Any) -> dict[str, Any]:
    """Schema, then principal: the typed arguments of a call this principal may make, or raise."""
    if name not in TOOLS:
        raise DspError(ErrorCode.INPUT_INVALID, f"no tool named {name[:80]!r}")
    error = next(iter(VALIDATORS[name].iter_errors(arguments)), None)
    if error is not None:
        pointer = "/" + "/".join(str(part) for part in error.absolute_path)
        raise DspError(
            ErrorCode.INPUT_INVALID, f"{name} arguments: {error.message[:200]}", {"field": pointer}
        )
    needed = NEEDS.get(name)
    if needed and not {"*", needed} & ctx.scopes:
        raise DspError(ErrorCode.FORBIDDEN, f"this context may not {name}")
    return dict(arguments)


PREVIEW_ROWS, PREVIEW_CELL, PREVIEW_CHARS = 20, 200, 2000


def preview(name: str, content: bytes) -> dict[str, Any]:
    """The bounded view of one committed output the model may see (decisions, 2026-10-15)."""
    if name.endswith(".csv"):
        rows = list(csv.reader(io.StringIO(content.decode("utf-8", "replace"))))
        shown = [[cell[:PREVIEW_CELL] for cell in row] for row in rows[: PREVIEW_ROWS + 1]]
        return {"kind": "csv", "rows": max(len(rows) - 1, 0), "header_and_first_rows": shown}
    if name.endswith((".json", ".txt", ".md")):
        return {
            "kind": "text",
            "chars": len(content),
            "head": content.decode("utf-8", "replace")[:PREVIEW_CHARS],
        }
    return {"kind": "other", "bytes": len(content)}


def quoted_failure(reason: str | None) -> str | None:
    """A task's failure message, bounded: it is text the task chose and never an instruction."""
    return None if reason is None else reason[:FAILURE_CHARS]


class Dispatcher:
    """Runs one checked call for one assistant job; every result is data the loop quotes."""

    def __init__(
        self,
        ctx: TrustedContext,
        job: dict[str, Any],
        command: dict[str, Any],
        *,
        ledger: Ledger,
        store: Store,
        admit: Callable[[dict[str, Any], str, str], dict[str, Any]],
        run_job: Callable[[str], dict[str, Any]],
        profile: Callable[[str, str, str], dict[str, Any]],
        clock: Callable[[], str],
    ) -> None:
        self.ctx, self.job, self.command = ctx, job, command
        self.ledger, self.store, self.clock = ledger, store, clock
        self.admit, self.run_job, self.profile = admit, run_job, profile

    def revision_check(self, name: str, arguments: dict[str, Any]) -> None:
        """Revision: a patch names the current one; work stops on a revision the job predates."""
        current = current_workload(self.ctx, self.ledger)["revision"]
        if name == "propose_requirement_patch" and arguments["expected_revision"] != current:
            raise DspError(
                ErrorCode.REVISION_CONFLICT,
                f"the requirements are at {current}, not {arguments['expected_revision']}",
            )
        if name == "submit_code_task" and self.job["workload_ref"]["revision"] != current:
            raise DspError(
                ErrorCode.REVISION_CONFLICT,
                f"this task was admitted at {self.job['workload_ref']['revision']}; "
                f"the requirements are at {current} now",
            )

    def scope_check(self, name: str, arguments: dict[str, Any]) -> None:
        """Scope: a call names only what this task and its conversation own or were granted."""
        if name == "inspect_results":
            child = self.ledger.latest(self.ctx, "Job", arguments["job"])
            if child is None or child.get("parent") != self.job["id"]:
                raise DspError(ErrorCode.FORBIDDEN, "not a job this task submitted")
        if name == "submit_code_task":
            captured = {m["id"]: m for m in self.ledger.current(self.ctx, "DataManifest")}
            for item in arguments["inputs"]:
                if item["data"] not in captured:
                    raise DspError(ErrorCode.FORBIDDEN, f"{item['data']} is not captured data")
            try:
                self.store.path(self.ctx, arguments["artifact"])
            except DspError:
                raise DspError(ErrorCode.FORBIDDEN, "no such artifact") from None

    def run(self, name: str, arguments: dict[str, Any], call_id: str) -> dict[str, Any]:
        """Dispatch a checked call; the answer is quoted data for the model, never authority."""
        match name:
            case "inspect_schema":
                return self.profile(arguments["source"], arguments["path"], call_id)
            case "propose_requirement_patch":
                asked = {"asked": arguments["question"]} if arguments["question"] else {}
                proposed = arguments["patch"]
                if asked and not proposed:
                    return asked | {"applied": False}
                current = current_workload(self.ctx, self.ledger)
                self.grounded(proposed, current)
                whole = complete(current, proposed)
                derived = [
                    {
                        "field": operation["path"],
                        "source_kind": "trusted_observation",
                        "message_id": None,
                        "source_span": None,
                        "extraction_confidence": None,
                        "materiality": "medium",
                        "confirmation_status": "proposed",
                        "confirmed_by": None,
                    }
                    for operation in whole[len(proposed) :]
                ]
                successor, impact = revise(  # revise refuses the owner's paths itself
                    self.ctx,
                    whole,
                    arguments["expected_revision"],
                    self.command["client_message_id"],
                    self.command["text"],
                    ledger=self.ledger,
                    clock=self.clock,
                    provenance=[*self.provenance(proposed, arguments["provenance"]), *derived],
                )
                return asked | {  # the unambiguous part applies; the question still ends the task
                    "applied": True,
                    "revision": successor["revision"],
                    "readback": describe(whole),
                    "diff": whole,
                    "impact": impact,
                }
            case "write_code_artifact":
                work = self.store.staging(f"artifact-{call_id}")
                (work / "source").write_text(arguments["source"])
                stored = self.store.commit(self.ctx, work / "source")
                self.store.discard(work)
                return {"artifact": stored, "repairs": arguments["repairs"]}
            case "submit_code_task":
                captured = {
                    m["id"]: m["sha256"] for m in self.ledger.current(self.ctx, "DataManifest")
                }
                task = {
                    "language": arguments["language"],
                    "source_sha256": arguments["artifact"],
                    "inputs": [
                        {"name": i["name"], "sha256": captured[i["data"]]}
                        for i in arguments["inputs"]
                    ],
                    "outputs": arguments["outputs"],
                }
                child = self.admit(task, call_id, self.job["id"])
                ended = self.run_job(child["id"])
                return self.outcome(ended)
            case "inspect_results":
                seen = self.ledger.latest(self.ctx, "Job", arguments["job"])
                shown = self.outcome(seen or {})
                named = [o for o in shown["outputs"] if o["name"] == arguments["output"]]
                if named:
                    shown["preview"] = preview(
                        named[0]["name"], self.store.path(self.ctx, named[0]["sha256"]).read_bytes()
                    )
                return shown
            case _:
                raise DspError(ErrorCode.DEPENDENCY_UNAVAILABLE, NOT_YET)

    def grounded(self, patch: list[dict[str, Any]], current: dict[str, Any]) -> None:
        """A proposal says only what the instruction said: no invented number, no unnamed drop.

        Under the intent constraints every number in a value must appear in the instruction (a
        hard maximum or an increment the owner never gave is an invention); a field role may be
        removed only when the instruction names that field; a patch that changes nothing is
        refused, so the model asks instead of pretending.
        """
        text = self.command["text"]
        if not patch:
            raise DspError(ErrorCode.INPUT_INVALID, "the patch is empty: ask a question instead")

        def numbers(value: Any) -> list[int | float]:
            if isinstance(value, bool):
                return []
            if isinstance(value, int | float):
                return [value]
            if isinstance(value, dict):
                return [n for item in value.values() for n in numbers(item)]
            if isinstance(value, list):
                return [n for item in value for n in numbers(item)]
            return []

        roles = current["intent_constraints"]["field_roles"]
        for operation in patch:
            path = operation["path"]
            if path.startswith("/intent_constraints"):
                for number in numbers(operation["value"]):
                    if f"{number:g}" not in text:
                        raise DspError(
                            ErrorCode.INPUT_INVALID,
                            f"the number {number:g} is not in the instruction",
                        )
            if operation["op"] == "remove" and path.startswith("/intent_constraints/field_roles/"):
                index = path.rsplit("/", 1)[1]
                named = (
                    roles[int(index)]["field"]
                    if index.isdigit() and int(index) < len(roles)
                    else ""
                )
                if named and named not in text:
                    raise DspError(
                        ErrorCode.INPUT_INVALID,
                        f"{named} is not named in the instruction, so its role stays: propose "
                        "the patch again without the operation that removes it",
                    )
        if apply_patch(current, patch) == current:
            raise DspError(
                ErrorCode.INPUT_INVALID, "the patch changes nothing: ask a question instead"
            )

    def provenance(
        self, patch: list[dict[str, Any]], given: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """The typed, proposed provenance of a patch: every path covered, every span verbatim.

        A span must be the instruction's own words, so a reader can find it; a field must be a
        path the patch changes (or a prefix of one); an uncovered change is refused. Nothing here
        is confirmed: the owner's own action does that.
        """
        paths = [operation["path"] for operation in patch]
        for entry in given:
            if entry["span"] not in self.command["text"]:
                raise DspError(
                    ErrorCode.INPUT_INVALID, "a provenance span is not in the instruction"
                )
            if not any(path.startswith(entry["field"]) for path in paths):
                raise DspError(
                    ErrorCode.INPUT_INVALID,
                    f"provenance names {entry['field']}, which is not patched",
                )
        for path in paths:
            if not any(path.startswith(entry["field"]) for entry in given):
                raise DspError(ErrorCode.INPUT_INVALID, f"no provenance for the change at {path}")
        return [
            {
                "field": entry["field"],
                "source_kind": "direct_user_message",
                "message_id": self.command["client_message_id"],
                "source_span": entry["span"],
                "extraction_confidence": entry["confidence"],
                "materiality": entry["materiality"],
                "confirmation_status": "proposed",
                "confirmed_by": None,
            }
            for entry in given
        ]

    def outcome(self, job: dict[str, Any]) -> dict[str, Any]:
        """A job's redacted outcome: state, bounded failure text, outputs by name, size, digest."""
        outputs: list[dict[str, Any]] = []
        if job.get("state") == "succeeded":
            record = json.loads(self.store.path(self.ctx, job["result"]["sha256"]).read_bytes())
            validate("RunRecord", record)
            outputs = record["outputs"]
        return {
            "job": job.get("id"),
            "state": job.get("state"),
            "failure": quoted_failure(job.get("reason")),
            "outputs": outputs,
        }
