import hashlib
import json
from pathlib import Path


def canonical_json(value: object) -> bytes:
    """Return the canonical bytes that identify a JSON value: sorted keys, no whitespace, UTF-8."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()


def digest(data: bytes) -> str:
    """Return the ``sha256:<hex>`` digest of bytes."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    """Return the ``sha256:<hex>`` digest of a file without loading it whole."""
    with path.open("rb") as handle:
        return "sha256:" + hashlib.file_digest(handle, "sha256").hexdigest()


def pin(obj: dict[str, object]) -> dict[str, object]:
    """Return the typed reference that pins one object revision by its canonical digest."""
    return {"id": obj["id"], "revision": obj["revision"], "sha256": digest(canonical_json(obj))}
