"""App-owned contracts: they meta-validate, what the code writes conforms, older versions read."""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from dsp.application.planning import local_binding
from dsp.application.workloads import base_workload
from dsp.contracts import schemas
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.domain import jobs as machine
from dsp.domain.admission import code_task, envelope

CTX = TrustedContext.local()
SHA = "sha256:" + "c" * 64
SUITE = Path(__file__).parents[3]
PYTHON: dict[str, Any] = {
    "language": "python",
    "source_sha256": SHA,
    "inputs": [{"name": "orders.csv", "sha256": SHA}],
    "outputs": ["summary.json"],
}


def refused(name: str, instance: Any) -> None:
    """Fail unless the instance is refused by its schema."""
    with pytest.raises(DspError) as raised:
        schemas.validate(name, instance)
    assert raised.value.code is ErrorCode.INPUT_INVALID


@pytest.mark.parametrize("path", sorted((schemas.ROOT / "app").glob("*.json")), ids=str)
def test_app_schemas_meta_validate_and_refuse_unknown_fields(path: Path) -> None:
    """B26: every app-owned schema is a valid draft 2020-12 schema that rejects unknown fields."""
    schema = json.loads(path.read_text())
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False


@pytest.mark.parametrize("os", ["darwin", "linux"])
def test_a28_the_local_binding_is_os_sandbox_single_user_assurance(os: str) -> None:
    """A28, D01: the local binding is ComputeBinding 0.6.0 at OS-sandbox, single-user assurance."""
    binding = local_binding(CTX, os, "arm64")
    schemas.validate("ComputeBinding", binding)
    assert binding["schema_version"] == "0.6.0"
    assert binding["resource_requirements"]["os"] == os
    assert (binding["generated_code_policy"], binding["assurance"]) == (
        "restricted_os_sandbox",
        "os_sandbox_single_user",
    )
    assert binding["isolation"] == {
        "trust_model": "customer_os_sandbox_single_user",
        "malicious_multitenant_approved": False,
    }
    assert "not VM isolation" in binding["limitations"][0]


def test_a28_a_policy_cannot_claim_an_assurance_it_does_not_give() -> None:
    """A28: OS-sandbox code needs OS-sandbox assurance and trust; each policy has its assurance."""
    binding = local_binding(CTX, "darwin", "arm64")
    vm_trust = {"trust_model": "customer_dedicated_vm", "malicious_multitenant_approved": False}
    for change in (
        {"assurance": "dedicated_vm"},
        {"assurance": "none"},
        {"isolation": vm_trust},
        {"generated_code_policy": "restricted_dedicated_vm"},
        {"generated_code_policy": "denied"},
        {"resource_requirements": binding["resource_requirements"] | {"os": "windows"}},
    ):
        refused("ComputeBinding", binding | change)
    schemas.validate(
        "ComputeBinding", binding | {"generated_code_policy": "denied", "assurance": "none"}
    )


def test_b26_prior_versions_still_read_under_their_own_schema() -> None:
    """B26: the suite's 0.5.0 binding and a Sprint 3 Job 0.1.0 still validate as they were."""
    example = json.loads((SUITE / "examples" / "compute_binding.local.json").read_text())
    schemas.validate("ComputeBinding", example)
    refused("ComputeBinding", example | {"schema_version": "0.6.0"})  # 0.6.0 needs an assurance
    job, _, _ = machine.new(
        "job-1",
        "2026-10-08T10:00:00+00:00",
        task={"cues": ["sleep"], "seconds": 1},
        request_ref={"id": "request-1", "revision": "1.0.0", "sha256": SHA},
        workload_ref={"id": "workload-test-job", "revision": "1.0.0", "sha256": SHA},
        reservation="reservation-1",
        idempotency_key="k",
    )
    sprint_3 = job | {"schema_version": "0.1.0"}
    schemas.validate("Job", sprint_3)
    refused("Job", sprint_3 | {"task": None})  # 0.1.0 always carried a test-worker task
    refused("Job", job)  # 0.2.0 needs the payload digest
    schemas.validate("Job", job | {"task": None, "payload_sha256": SHA})


def test_b26_code_tasks_conform_and_declare_their_outputs() -> None:
    """B26: Python and test-worker CodeTasks conform; Python must declare an output, plain names."""
    workload = base_workload(CTX)
    python = code_task(PYTHON, workload)
    schemas.validate("CodeTask", python)
    assert python == code_task(PYTHON, workload)  # the same declaration is the same CodeTask
    assert (python["requirement_revision"], python["limits"]) == ("1.0.0", envelope(workload))
    worker = code_task({"cues": ["sleep"], "seconds": 1}, workload)
    schemas.validate("CodeTask", worker)
    assert (worker["language"], worker["outputs"]) == ("test_worker", [])
    for bad in (
        PYTHON | {"outputs": []},
        PYTHON | {"outputs": ["../escape.json"]},
        PYTHON | {"inputs": [{"name": "a/b.csv", "sha256": SHA}]},
        PYTHON | {"limits": {"memory_mib": 0}},
        PYTHON | {"permissions": ["shell"]},
    ):
        refused("CodeTask", code_task(bad, workload))
    for caller_set in (
        PYTHON | {"requirement_revision": "9.9.9"},
        PYTHON | {"language": "test_worker"},
    ):
        with pytest.raises(DspError) as raised:
            code_task(caller_set, workload)
        assert raised.value.code is ErrorCode.INPUT_INVALID
