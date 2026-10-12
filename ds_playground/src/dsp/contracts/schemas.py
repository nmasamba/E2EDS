import json
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from dsp.contracts.errors import DspError, ErrorCode

ROOT = Path(__file__).parent / "schemas"


@cache
def _validators(name: str) -> dict[str, Draft202012Validator]:
    """Every readable version of a contract, by its ``schema_version`` (``Name@x.y.z`` is older)."""
    paths = [*ROOT.glob(f"*/{name}.schema.json"), *ROOT.glob(f"*/{name}@*.schema.json")]
    schemas = [json.loads(path.read_text()) for path in paths]
    return {
        schema["properties"]["schema_version"]["const"]: Draft202012Validator(
            schema, format_checker=Draft202012Validator.FORMAT_CHECKER
        )
        for schema in schemas
    }


def validate(name: str, instance: Any) -> None:
    """Raise INPUT_INVALID unless ``instance`` conforms to the named schema, formats included.

    The version the instance names is the schema it is checked against; an unknown version is
    checked against the newest, so the error names the version it should have.
    """
    versions = _validators(name)
    version = str(instance.get("schema_version")) if isinstance(instance, dict) else ""
    newest = max(versions, key=lambda known: tuple(map(int, known.split("."))))
    validator = versions.get(version) or versions[newest]
    error = next(iter(validator.iter_errors(instance)), None)
    if error:
        pointer = "/" + "/".join(str(part) for part in error.absolute_path)
        raise DspError(ErrorCode.INPUT_INVALID, f"{name}: {error.message}", {"field": pointer})
