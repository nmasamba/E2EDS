"""The assistant's tools: the eight typed calls the application owns, validates and dispatches.

The list is the assistant-gateway skill's and nothing else: inspect an approved schema, propose a
typed requirement patch, write a code artifact, submit a validated code task, inspect redacted
results, request a permitted trial, assemble an evidence report, propose a release. There is no
shell, no grant and no sealed-data tool. A call is checked in order, schema, principal, revision,
scope, budget, fence, before anything runs (the loop does the budget and the fence); the model's
arguments never reach a process as a command string. Everything a tool returns enters the model's
context as quoted data.
"""

import json
from collections.abc import Callable
from typing import Any

from jsonschema import Draft202012Validator

from dsp.application.workloads import current_workload, revise
from dsp.contracts.canonical import canonical_json
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
        "description": "Propose typed changes to the requirements (a JSON patch on the"
        " WorkloadSpec) with where in the instruction each came from, or ask one question"
        " when an ambiguity changes material work.",
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
                "question": {"type": ["string", "null"], "maxLength": 500},
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
        "description": "See a job this task submitted: its state, why it failed, and its outputs.",
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


def quoted_failure(reason: str | None) -> str | None:
    """A task's failure message, bounded: it is text the task chose and never an instruction."""
    return None if reason is None else reason[:FAILURE_CHARS]


class Dispatcher:
    """Runs one checked call for one assistant job; every result is data the loop quotes."""

    def __init__(
        self,
        ctx: TrustedContext,
        job: dict[str, Any],
        *,
        ledger: Ledger,
        store: Store,
        admit: Callable[[dict[str, Any], str, str], dict[str, Any]],
        run_job: Callable[[str], dict[str, Any]],
        profile: Callable[[str, str, str], dict[str, Any]],
        clock: Callable[[], str],
    ) -> None:
        self.ctx, self.job, self.ledger, self.store = ctx, job, ledger, store
        self.admit, self.run_job, self.profile, self.clock = admit, run_job, profile, clock

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
                if arguments["question"]:
                    return {"asked": arguments["question"], "applied": False}
                command = self.job["task"]["command"]  # revise refuses the owner's paths itself
                successor, impact = revise(
                    self.ctx,
                    arguments["patch"],
                    arguments["expected_revision"],
                    command,
                    canonical_json(arguments["provenance"]).decode(),
                    ledger=self.ledger,
                    clock=self.clock,
                )
                return {"applied": True, "revision": successor["revision"], "impact": impact}
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
                return self.outcome(seen or {})
            case _:
                raise DspError(ErrorCode.DEPENDENCY_UNAVAILABLE, NOT_YET)

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
