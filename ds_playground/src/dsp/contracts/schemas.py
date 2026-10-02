import json
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from dsp.contracts.errors import DspError, ErrorCode

ROOT = Path(__file__).parent / "schemas"


@cache
def _validator(name: str) -> Draft202012Validator:
    (path,) = ROOT.glob(f"*/{name}.schema.json")
    return Draft202012Validator(
        json.loads(path.read_text()), format_checker=Draft202012Validator.FORMAT_CHECKER
    )


def validate(name: str, instance: Any) -> None:
    """Raise INPUT_INVALID unless ``instance`` conforms to the named schema, formats included."""
    error = next(iter(_validator(name).iter_errors(instance)), None)
    if error:
        pointer = "/" + "/".join(str(part) for part in error.absolute_path)
        raise DspError(ErrorCode.INPUT_INVALID, f"{name}: {error.message}", {"field": pointer})
