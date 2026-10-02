import json
from itertools import count
from pathlib import Path
from typing import Any

import pytest

from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.application.grants import grant_folder, resolve, revoke, summary
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate

CTX = TrustedContext.local()
OTHER = TrustedContext("someone", "tenant-other", frozenset())
NOW = "2026-10-02T00:00:00+00:00"


@pytest.fixture
def ledger(tmp_path: Path) -> SqliteLedger:
    """A real ledger file beside the folders under test."""
    return SqliteLedger(tmp_path / "ledger.sqlite", lambda: NOW)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A folder to grant, holding one file and one nested file, with a secret beside it."""
    folder = tmp_path / "granted"
    (folder / "nested").mkdir(parents=True)
    (folder / "data.csv").write_text("a\n1\n")
    (folder / "nested" / "deep.csv").write_text("a\n2\n")
    (tmp_path / "secret.csv").write_text("a\n3\n")
    return folder


def grant(ledger: SqliteLedger, folder: Path, purpose: str = "source_root") -> dict[str, Any]:
    """Grant ``folder`` as the local owner, with a predictable new handle."""
    ids = count(len(ledger.events(CTX)))
    return grant_folder(
        CTX, folder, purpose, ledger=ledger, clock=lambda: NOW, new_id=lambda: f"n{next(ids)}"
    )


def refusal(ledger: SqliteLedger, handle: str, relative: str, purpose: str = "source_root") -> str:
    """Return the error code with which using ``relative`` under ``handle`` is refused."""
    with pytest.raises(DspError) as raised:
        resolve(CTX, handle, relative, purpose, ledger=ledger)
    return raised.value.code


def test_a_grant_is_an_opaque_handle_with_no_path(ledger: SqliteLedger, root: Path) -> None:
    """R26: granting a folder yields a handle and a label; the path stays in the grant record."""
    granted = grant(ledger, root)
    validate("FolderGrant", granted)
    assert summary(granted) == {
        "handle": granted["id"],
        "purpose": "source_root",
        "label": "granted",
        "state": "active",
    }
    assert str(root.parent) not in json.dumps([summary(granted), ledger.events(CTX)])
    assert [event["type"] for event in ledger.events(CTX)] == ["grant.created"]


def test_paths_inside_the_granted_folder_resolve(ledger: SqliteLedger, root: Path) -> None:
    """R26: the root itself, a file and a nested file are all reachable through the handle."""
    handle = grant(ledger, root)["id"]
    resolved = [resolve(CTX, handle, r, "source_root", ledger=ledger) for r in (".", "data.csv")]
    assert resolved == [root.resolve(), root.resolve() / "data.csv"]
    nested = resolve(CTX, handle, "nested/deep.csv", "source_root", ledger=ledger)
    assert nested.read_text() == "a\n2\n"


@pytest.mark.parametrize("relative", ["../secret.csv", "nested/../../secret.csv", "/etc/hosts"])
def test_traversal_is_denied_at_use_time(ledger: SqliteLedger, root: Path, relative: str) -> None:
    """C23: a relative path that climbs out, or an absolute path, is refused when it is used."""
    handle = grant(ledger, root)["id"]
    assert refusal(ledger, handle, relative) == ErrorCode.FORBIDDEN
    absolute = str(root.parent / "secret.csv")
    assert refusal(ledger, handle, absolute) == ErrorCode.FORBIDDEN


def test_a_symlink_that_escapes_is_denied_at_use_time(ledger: SqliteLedger, root: Path) -> None:
    """C23: a link planted inside the folder after the grant cannot reach outside it."""
    handle = grant(ledger, root)["id"]
    (root / "link.csv").symlink_to(root.parent / "secret.csv")
    (root / "linkdir").symlink_to(root.parent)
    (root / "inside.csv").symlink_to(root / "data.csv")
    assert refusal(ledger, handle, "link.csv") == ErrorCode.FORBIDDEN
    assert refusal(ledger, handle, "linkdir/secret.csv") == ErrorCode.FORBIDDEN
    inside = resolve(CTX, handle, "inside.csv", "source_root", ledger=ledger)
    assert inside == root.resolve() / "data.csv"


def test_a_root_swapped_for_a_symlink_is_denied(ledger: SqliteLedger, root: Path) -> None:
    """C23: replacing the granted folder itself with a link elsewhere does not move the grant."""
    handle = grant(ledger, root)["id"]
    root.rename(root.parent / "moved")
    root.symlink_to(root.parent)
    assert refusal(ledger, handle, "secret.csv") == ErrorCode.FORBIDDEN


def test_a_revoked_handle_is_refused(ledger: SqliteLedger, root: Path) -> None:
    """C23: after revocation the handle resolves nothing, and revoking twice changes nothing."""
    handle = grant(ledger, root)["id"]
    assert summary(revoke(CTX, handle, ledger=ledger))["state"] == "revoked"
    assert refusal(ledger, handle, "data.csv") == ErrorCode.FORBIDDEN
    revoke(CTX, handle, ledger=ledger)
    assert [event["type"] for event in ledger.events(CTX)] == ["grant.created", "grant.revoked"]
    assert ledger.get(CTX, "FolderGrant", handle, "1.0.0")["state"] == "active"  # history is kept


def test_unknown_foreign_and_wrong_purpose_handles_are_refused(
    ledger: SqliteLedger, root: Path
) -> None:
    """C23: a made-up handle, a raw path, another tenant, or the wrong purpose grants nothing."""
    handle = grant(ledger, root)["id"]
    assert refusal(ledger, "grant-made-up", "data.csv") == ErrorCode.NOT_FOUND
    assert refusal(ledger, str(root), "data.csv") == ErrorCode.NOT_FOUND
    assert refusal(ledger, handle, "data.csv", "output_root") == ErrorCode.FORBIDDEN
    with pytest.raises(DspError) as foreign:
        resolve(OTHER, handle, "data.csv", "source_root", ledger=ledger)
    assert foreign.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(DspError) as unknown:
        revoke(CTX, "grant-made-up", ledger=ledger)
    assert unknown.value.code is ErrorCode.NOT_FOUND


def test_granting_the_same_folder_again_reuses_the_handle(ledger: SqliteLedger, root: Path) -> None:
    """R26: one active grant per folder and purpose; a revoked one is replaced by a new handle."""
    first = grant(ledger, root)
    assert grant(ledger, root / "nested" / "..")["id"] == first["id"]
    assert len(ledger.events(CTX)) == 1
    assert grant(ledger, root, "output_root")["id"] != first["id"]
    revoke(CTX, first["id"], ledger=ledger)
    assert grant(ledger, root)["id"] != first["id"]
    assert [g["state"] for g in ledger.current(CTX, "FolderGrant")] == [
        "active",
        "revoked",
        "active",
    ]


@pytest.mark.parametrize(
    ("folder", "purpose", "code"),
    [
        ("absent", "source_root", ErrorCode.NOT_FOUND),
        ("granted/data.csv", "output_root", ErrorCode.NOT_FOUND),
        ("granted", "everything", ErrorCode.INPUT_INVALID),
        ("", "source_root", ErrorCode.INPUT_INVALID),
    ],
)
def test_bad_grants_are_refused_and_record_nothing(
    ledger: SqliteLedger, root: Path, folder: str, purpose: str, code: ErrorCode
) -> None:
    """R26: a missing folder, a file as an output folder, an unknown purpose or a relative path."""
    with pytest.raises(DspError) as raised:
        grant(ledger, root.parent / folder if folder else Path("relative/folder"), purpose)
    assert raised.value.code is code
    assert str(root.parent) not in raised.value.message
    assert ledger.events(CTX) == []


def test_a_single_file_can_be_granted_as_a_source(ledger: SqliteLedger, root: Path) -> None:
    """R26: naming one file grants that file only, not the folder around it."""
    handle = grant(ledger, root / "data.csv")["id"]
    assert resolve(CTX, handle, ".", "source_root", ledger=ledger) == root.resolve() / "data.csv"
    assert refusal(ledger, handle, "../nested/deep.csv") == ErrorCode.FORBIDDEN


def test_an_output_grant_proposes_an_output_binding(ledger: SqliteLedger, root: Path) -> None:
    """R26, D23: an output folder grant records a schema-valid, path-free proposed OutputBinding."""
    granted = grant(ledger, root, "output_root")
    binding = ledger.get(CTX, "OutputBinding", f"binding-{granted['id']}", "1.0.0")
    validate("OutputBinding", binding)
    assert (binding["root_handle"], binding["state"], binding["planning_only"]) == (
        granted["id"],
        "proposed",
        True,
    )
    assert str(root.parent) not in json.dumps(binding)
    assert ledger.current(CTX, "OutputBinding") == [binding]
    grant(ledger, root / "nested")
    assert len(ledger.current(CTX, "OutputBinding")) == 1  # a source grant proposes no binding
