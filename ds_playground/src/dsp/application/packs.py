import json
import shutil
from collections.abc import Callable
from html import escape
from pathlib import Path
from typing import Any

from dsp.contracts.canonical import canonical_json, file_digest
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.ports import Exporter, Ledger, Store

MAX_FILE_BYTES = 50 * 1024**2  # D20
RECIPE = {"id": "profile-csv", "revision": "1.0.0", "execution": "signed_recipe"}
FIELDS = ("name", "proposed_type", "non_null", "nulls", "distinct", "min", "max")


def render_report(source_name: str, profile: dict[str, Any]) -> str:
    """Render the profile as self-contained HTML; every value is escaped profile data."""
    head = "".join(f"<th>{field}</th>" for field in FIELDS)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{escape('' if (v := col[f]) is None else str(v))}</td>" for f in FIELDS)
        + "</tr>"
        for col in profile["columns"]
    )
    return (
        f'<!doctype html><html lang="en"><meta charset="utf-8">'
        f"<title>Profile of {escape(source_name)}</title><h1>Profile of {escape(source_name)}</h1>"
        f"<p>{profile['rows']} rows read, {profile['rows_rejected']} rows rejected by the parser. "
        f"Produced by a reviewed built-in recipe; no generated code was run.</p>"
        f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></html>"
    )


def profile_and_export(
    ctx: TrustedContext,
    source: Path,
    out_root: Path,
    *,
    ledger: Ledger,
    store: Store,
    exporter: Exporter,
    profiler: Callable[[Path], dict[str, Any]],
    clock: Callable[[], str],
    new_id: Callable[[], str],
) -> dict[str, Any]:
    """Capture a CSV, profile it, and export a verified pack to a new version directory.

    Each step is recorded in the ledger. Artifacts are committed to the store before the job is
    recorded as succeeded, and the export is recorded only after its bytes are verified in place.
    """
    size = source.stat().st_size
    if size == 0 or size > MAX_FILE_BYTES:
        raise DspError(
            ErrorCode.INPUT_INVALID,
            f"file is {size} bytes; it must be between 1 and {MAX_FILE_BYTES}",
            {"limit": "D20"},
        )
    job = new_id()
    aggregate = f"job:{job}"
    work = store.staging(job)
    raw = store.commit(ctx, Path(shutil.copyfile(source, work / "raw")))
    data_manifest = {
        "schema_version": "0.1.0",
        "type": "DataManifest",
        "id": f"data-{job}",
        "revision": "1.0.0",
        "source_name": source.name,
        "sha256": raw,
        "bytes": size,
        "captured_at": clock(),
        "rights": "owner_supplied_unreviewed",
    }
    validate("DataManifest", data_manifest)
    started = {"recipe": RECIPE, "source": raw}
    ledger.commit(ctx, aggregate, 0, f"{job}:started", "job.started", started, [data_manifest])
    try:
        profile = profiler(store.path(ctx, raw))
    except DspError as error:
        ledger.commit(ctx, aggregate, 1, f"{job}:failed", "job.failed", {"code": error.code})
        raise

    outputs = {
        "profile.json": ("profile", canonical_json(profile)),
        "report.html": ("report", render_report(source.name, profile).encode()),
    }
    files: list[dict[str, Any]] = []
    for name, (role, content) in outputs.items():
        (work / name).write_bytes(content)
        identity = store.commit(ctx, work / name)
        files.append({"path": name, "role": role, "sha256": identity, "bytes": len(content)})
    manifest = {
        "schema_version": "0.1.0",
        "type": "PackManifest",
        "kind": "profile_pack",
        "recipe": RECIPE,
        "source": {"name": source.name, "sha256": raw, "bytes": size},
        "files": files,
    }
    validate("PackManifest", manifest)
    (work / "manifest.json").write_bytes(canonical_json(manifest))
    manifest_digest = store.commit(ctx, work / "manifest.json")
    digests = {"manifest.json": manifest_digest} | {f["path"]: f["sha256"] for f in files}
    ledger.commit(ctx, aggregate, 1, f"{job}:succeeded", "job.succeeded", {"artifacts": digests})

    staged = exporter.stage(out_root, {n: store.path(ctx, d) for n, d in digests.items()}, job)
    version = exporter.commit_staged(out_root, staged, digests)
    receipt = {
        "schema_version": "0.1.0",
        "type": "ExportReceipt",
        "id": f"export-{job}",
        "revision": "1.0.0",
        "output_sha256": manifest_digest,
        "destination": str(out_root),
        "version": version,
        "files": [
            {"path": n, "sha256": d, "bytes": store.path(ctx, d).stat().st_size}
            for n, d in digests.items()
        ],
        "result": "committed",
        "committed_at": clock(),
    }
    validate("ExportReceipt", receipt)
    ledger.commit(ctx, aggregate, 2, f"{job}:exported", "export.committed", receipt, [receipt])
    return receipt


def verify_pack(directory: Path) -> list[str]:
    """Return the files in an exported pack that are missing or differ from the manifest."""
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        raise DspError(ErrorCode.NOT_FOUND, "no manifest.json in this folder")
    manifest = json.loads(manifest_path.read_text())
    validate("PackManifest", manifest)
    return [
        entry["path"]
        for entry in manifest["files"]
        if not (directory / entry["path"]).is_file()
        or file_digest(directory / entry["path"]) != entry["sha256"]
    ]
