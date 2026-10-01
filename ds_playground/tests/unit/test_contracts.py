import pytest

from dsp.contracts import schemas
from dsp.contracts.canonical import canonical_json, digest
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext

SHA = "sha256:" + "a" * 64


def _pack(path: str) -> dict[str, object]:
    return {
        "schema_version": "0.1.0",
        "type": "PackManifest",
        "kind": "profile_pack",
        "recipe": {"id": "profile-csv", "revision": "1.0.0", "execution": "signed_recipe"},
        "source": {"name": "orders.csv", "sha256": SHA, "bytes": 1},
        "files": [{"path": path, "role": "profile", "sha256": SHA, "bytes": 1}],
    }


def test_canonical_bytes_ignore_key_order_and_whitespace() -> None:
    """Equal JSON values give equal bytes and digests whatever the key order."""
    assert canonical_json({"b": 1, "a": [2, "é"]}) == canonical_json({"a": [2, "é"], "b": 1})
    assert canonical_json({"a": 1}) == b'{"a":1}'
    assert digest(b"") == "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_canonical_json_rejects_nan() -> None:
    """NaN has no canonical JSON form, so it cannot enter a hashed object."""
    with pytest.raises(ValueError, match="Out of range"):
        canonical_json({"x": float("nan")})


@pytest.mark.parametrize("path", ["/etc/passwd", "../up.json", "a/../../b", "a/./b", ""])
def test_pack_manifest_rejects_paths_that_escape(path: str) -> None:
    """D23: a portable manifest holds relative paths only, with no traversal."""
    with pytest.raises(DspError) as raised:
        schemas.validate("PackManifest", _pack(path))
    assert raised.value.code is ErrorCode.INPUT_INVALID
    assert raised.value.details["field"] == "/files/0/path"


def test_pack_manifest_accepts_a_nested_relative_path() -> None:
    """D23: nested relative paths are allowed."""
    schemas.validate("PackManifest", _pack("reports/report.html"))


def test_format_assertion_is_enforced() -> None:
    """A malformed date-time is rejected: draft 2020-12 formats are asserted, not just annotated."""
    receipt = {
        "schema_version": "0.1.0",
        "type": "ExportReceipt",
        "id": "export-1",
        "revision": "1.0.0",
        "output_sha256": SHA,
        "destination": "/tmp/out",
        "version": "v1",
        "files": [{"path": "manifest.json", "sha256": SHA, "bytes": 1}],
        "result": "committed",
        "committed_at": "yesterday",
    }
    with pytest.raises(DspError):
        schemas.validate("ExportReceipt", receipt)
    schemas.validate("ExportReceipt", {**receipt, "committed_at": "2026-10-01T12:00:00+00:00"})
    with pytest.raises(DspError):
        schemas.validate("ExportReceipt", {**receipt, "version": "v0"})


def test_local_context_is_a_single_owner_tenant() -> None:
    """The local build has one tenant and one owner who holds every role."""
    context = TrustedContext.local()
    assert (context.tenant, context.principal) == ("tenant-local", "owner-local")
    assert str(DspError(ErrorCode.FORBIDDEN, "no")) == "FORBIDDEN: no"
