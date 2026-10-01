import copy
import json
from pathlib import Path
from typing import Any

import pytest

from dsp.contracts import schemas
from dsp.contracts.canonical import file_digest
from dsp.contracts.errors import DspError, ErrorCode

SUITE = Path(__file__).parents[3]
VENDORED = schemas.ROOT / "suite"
NAMES = {path.name.removesuffix(".schema.json") for path in VENDORED.glob("*.json")}
TYPELESS = {
    "assistant_model_binding": "AssistantModelBinding",
    "compute_binding": "ComputeBinding",
    "data_analysis_workload": "WorkloadSpec",
    "workload_spec": "WorkloadSpec",
    "release_manifest": "ReleaseManifest",
    "service_spec": "ServiceSpec",
}


def _instances() -> list[Any]:
    """Every suite example object that claims a schema, including items inside wrapper arrays."""
    found = []
    for path in sorted((SUITE / "examples").glob("*.json")):
        document = json.loads(path.read_text())
        nested = [
            i for v in document.values() if isinstance(v, list) for i in v if isinstance(i, dict)
        ]
        for index, candidate in enumerate([document, *nested]):
            name = candidate.get("type") or TYPELESS.get(path.name.split(".")[0])
            if name in NAMES and "schema_version" in candidate:
                found.append(pytest.param(name, candidate, id=f"{path.stem}[{index}]"))
    return found


INSTANCES = _instances()


def test_vendored_schemas_match_the_suite_manifest() -> None:
    """Vendored schemas are byte-identical to the suite's, by SUITE_MANIFEST digest."""
    manifest = json.loads((SUITE / "SUITE_MANIFEST.json").read_text())
    expected = {
        Path(entry["path"]).name: "sha256:" + entry["sha256"]
        for entry in manifest["files"]
        if entry["path"].startswith("contracts/")
    }
    assert len(expected) == 16
    assert {name: file_digest(VENDORED / name) for name in expected} == expected


def test_every_suite_schema_has_an_example() -> None:
    """All sixteen schemas are exercised by at least one suite example."""
    assert {param.values[0] for param in INSTANCES} == NAMES


@pytest.mark.parametrize(("name", "instance"), INSTANCES)
def test_suite_example_conforms(name: str, instance: dict[str, Any]) -> None:
    """Every suite example validates against its schema with format assertion on."""
    schemas.validate(name, instance)


@pytest.mark.parametrize(("name", "instance"), INSTANCES)
def test_invalid_variants_are_rejected(name: str, instance: dict[str, Any]) -> None:
    """Unknown fields, a missing required field and a wrong schema version are each rejected."""
    extra = {**copy.deepcopy(instance), "unexpected_field": 1}
    missing = {k: v for k, v in instance.items() if k != "planning_only"}
    wrong_version = {**copy.deepcopy(instance), "schema_version": "9.9.9"}
    for variant in (extra, missing, wrong_version):
        with pytest.raises(DspError) as raised:
            schemas.validate(name, variant)
        assert raised.value.code is ErrorCode.INPUT_INVALID
