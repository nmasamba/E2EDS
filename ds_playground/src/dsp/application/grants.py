from collections.abc import Callable
from pathlib import Path
from typing import Any

from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.ports import Ledger

PROJECT = "project-local"
MAX_EXPORT_BYTES = 2**30


def summary(grant: dict[str, Any]) -> dict[str, str]:
    """Return the path-free view of a grant, the only form an interface shows or sends."""
    return {
        "handle": grant["id"],
        "purpose": grant["purpose"],
        "label": grant["label"],
        "state": grant["state"],
    }


def _find(ctx: TrustedContext, handle: str, ledger: Ledger) -> dict[str, Any]:
    for grant in ledger.current(ctx, "FolderGrant"):
        if grant["id"] == handle:
            return grant
    raise DspError(ErrorCode.NOT_FOUND, "no such grant")


def grant_folder(
    ctx: TrustedContext,
    folder: Path,
    purpose: str,
    *,
    ledger: Ledger,
    clock: Callable[[], str],
    new_id: Callable[[], str],
) -> dict[str, Any]:
    """Record the owner's grant of one folder, or of one source file, and return the grant.

    The caller must be a trusted picker or the CLI: this is the only place a path becomes
    authority. Granting a folder that already has an active grant for the purpose returns that
    grant. An output grant also proposes an OutputBinding that refers to the folder by handle.
    """
    if purpose not in ("source_root", "output_root") or not folder.is_absolute():
        raise DspError(
            ErrorCode.INPUT_INVALID, "a grant needs an absolute path and a known purpose"
        )
    if not (folder.exists() if purpose == "source_root" else folder.is_dir()):
        raise DspError(ErrorCode.NOT_FOUND, "no such folder")
    root = folder.resolve()
    for existing in ledger.current(ctx, "FolderGrant"):
        if (existing["root"], existing["purpose"], existing["state"]) == (
            str(root),
            purpose,
            "active",
        ):
            return existing
    handle = f"grant-{new_id()}"
    grant: dict[str, Any] = {
        "schema_version": "0.1.0",
        "type": "FolderGrant",
        "id": handle,
        "revision": "1.0.0",
        "purpose": purpose,
        "state": "active",
        "root": str(root),
        "label": root.name,
        "granted_by": ctx.principal,
        "granted_at": clock(),
    }
    validate("FolderGrant", grant)
    objects = [grant]
    if purpose == "output_root":
        binding: dict[str, Any] = {
            "schema_version": "0.6.0",
            "planning_only": True,
            "id": f"binding-{handle}",
            "revision": "1.0.0",
            "type": "OutputBinding",
            "tenant_ref": ctx.tenant,
            "project_ref": PROJECT,
            "owner_ref": ctx.principal,
            "state": "proposed",
            "mode": "filesystem",
            "output_ref": {"id": f"output-{handle}", "revision": "1.0.0", "sha256": None},
            "root_handle": handle,
            "relative_directory": ".",
            "conflict_policy": "new_version_or_fail",
            "commit_policy": "same_filesystem_atomic_rename_or_unsupported",
            "include_data": "only_with_export_rights",
            "max_export_bytes": MAX_EXPORT_BYTES,
            "secret_refs_in_bundle": False,
            "start_endpoint": False,
            "authorisation_context_ref": None,
            "receipt_ref": None,
            "operator_ref": ctx.principal,
            "payer_ref": ctx.principal,
        }
        validate("OutputBinding", binding)
        objects.append(binding)
    created = {"handle": handle, "purpose": purpose, "label": root.name}
    ledger.commit(ctx, f"grant:{handle}", 0, f"{handle}:created", "grant.created", created, objects)
    return grant


def revoke(ctx: TrustedContext, handle: str, *, ledger: Ledger) -> dict[str, Any]:
    """Revoke a grant by recording its revoked successor; revoking again changes nothing."""
    grant = _find(ctx, handle, ledger)
    if grant["state"] == "active":
        grant = grant | {"revision": "2.0.0", "state": "revoked"}
        event = f"{handle}:revoked"
        ledger.commit(
            ctx, f"grant:{handle}", 1, event, "grant.revoked", {"handle": handle}, [grant]
        )
    return grant


def resolve(
    ctx: TrustedContext, handle: str, relative: str, purpose: str, *, ledger: Ledger
) -> Path:
    """Return the real path for ``relative`` under a granted root, checked now, at use time.

    Refused: an unknown or another tenant's handle, a revoked grant, a grant for another purpose,
    and any path that ends outside the granted root once every symlink is followed. The root was
    stored fully resolved, so a root later replaced by a link elsewhere resolves outside it too.
    """
    grant = _find(ctx, handle, ledger)
    if (grant["state"], grant["purpose"]) != ("active", purpose):
        raise DspError(ErrorCode.FORBIDDEN, "the grant is revoked or is for another purpose")
    root = Path(grant["root"])
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise DspError(ErrorCode.FORBIDDEN, "the path is outside the granted folder")
    return target
