import json
import shutil
from collections.abc import Callable
from html import escape
from pathlib import Path
from typing import Any

from dsp.application.admission import admit
from dsp.application.grants import resolve
from dsp.contracts.canonical import canonical_json, file_digest
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.ports import Exporter, Ledger, Store

MAX_FILE_BYTES = 50 * 1024**2  # D20
RECIPE_SOURCE = Path(__file__).parents[1] / "recipes" / "profile_csv.py"  # source, never imported
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
        f"<p>{profile['rows']:d} rows read, {profile['rows_rejected']:d} rows rejected by the "
        f"parser. Produced by a reviewed built-in recipe, run in the sandbox; no generated code "
        f"was run.</p>"
        f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></html>"
    )


def submit_profile(
    ctx: TrustedContext,
    source_handle: str,
    relative_path: str,
    *,
    ledger: Ledger,
    store: Store,
    workload: dict[str, Any],
    binding: dict[str, Any],
    environment: str | None,
    clock: Callable[[], str],
    new_id: Callable[[], str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Capture a CSV named under a source grant and queue the profiling recipe on it (R11, D20).

    The grant is checked now, at use; a file outside the D20 size bound is refused before anything
    is captured. The capture is recorded as a DataManifest, the recipe's source is stored, and the
    recipe is admitted as a sandboxed Python task with the capture as its one input. Return the
    queued job and the DataManifest.
    """
    source = resolve(ctx, source_handle, relative_path, "source_root", ledger=ledger)
    if not source.is_file():
        raise DspError(ErrorCode.NOT_FOUND, "no such file under the granted folder")
    size = source.stat().st_size
    if size == 0 or size > MAX_FILE_BYTES:
        raise DspError(
            ErrorCode.INPUT_INVALID,
            f"file is {size} bytes; it must be between 1 and {MAX_FILE_BYTES}",
            {"limit": "D20"},
        )
    work = store.staging(new_id())
    raw = store.commit(ctx, Path(shutil.copyfile(source, work / "raw")))
    (work / "recipe.py").write_bytes(RECIPE_SOURCE.read_bytes())
    recipe = store.commit(ctx, work / "recipe.py")
    store.discard(work)
    data = {
        "schema_version": "0.1.0",
        "type": "DataManifest",
        "id": f"data-{new_id()}",
        "revision": "1.0.0",
        "source_name": source.name,
        "sha256": raw,
        "bytes": size,
        "captured_at": clock(),
        "rights": "owner_supplied_unreviewed",
    }
    validate("DataManifest", data)
    captured = {"data": data["id"], "bytes": size}
    ledger.commit(
        ctx, f"data:{data['id']}", 0, f"{data['id']}:captured", "data.captured", captured, [data]
    )
    task: dict[str, Any] = {"language": "python", "source_sha256": recipe}
    task["outputs"] = ["profile.json"]
    task["inputs"] = [{"name": "data.csv", "sha256": raw}]
    job = admit(
        ctx,
        "analyse",
        f"profile-{data['id']}",
        task,
        workload=workload,
        binding=binding,
        ledger=ledger,
        store=store,
        clock=clock,
        new_id=new_id,
        environment=environment,
    )
    return job, data


def export_profile(
    ctx: TrustedContext,
    job: dict[str, Any],
    data: dict[str, Any],
    output_handle: str,
    *,
    ledger: Ledger,
    store: Store,
    exporter: Exporter,
    clock: Callable[[], str],
    new_id: Callable[[], str],
) -> dict[str, Any]:
    """Export a succeeded profiling job's pack to a new version in an output grant (D23).

    The job's RunRecord names the profile by digest; the profile is untrusted until it validates,
    and the report is rendered here from it with every value escaped. Files reach the output folder
    through staging and a hash check, and the receipt names the folder by its grant handle only.
    """
    out_root = resolve(ctx, output_handle, ".", "output_root", ledger=ledger)
    record = json.loads(store.path(ctx, job["result"]["sha256"]).read_bytes())
    validate("RunRecord", record)
    (made,) = record["outputs"]
    profile = json.loads(store.path(ctx, made["sha256"]).read_bytes())
    validate("Profile", profile)
    work = store.staging(new_id())
    report = render_report(data["source_name"], profile).encode()
    (work / "report.html").write_bytes(report)
    files = [
        {
            "path": "profile.json",
            "role": "profile",
            "sha256": made["sha256"],
            "bytes": made["bytes"],
        },
        {
            "path": "report.html",
            "role": "report",
            "sha256": store.commit(ctx, work / "report.html"),
        },
    ]
    files[1]["bytes"] = len(report)
    source = {"name": data["source_name"], "sha256": data["sha256"], "bytes": data["bytes"]}
    manifest: dict[str, Any] = {"schema_version": "0.1.0", "type": "PackManifest"}
    manifest["kind"] = "profile_pack"
    manifest |= {"recipe": RECIPE, "source": source, "files": files}
    validate("PackManifest", manifest)
    (work / "manifest.json").write_bytes(canonical_json(manifest))
    digests = {"manifest.json": store.commit(ctx, work / "manifest.json")}
    digests |= {entry["path"]: entry["sha256"] for entry in files}
    store.discard(work)
    staged = exporter.stage(
        out_root, {name: store.path(ctx, sha) for name, sha in digests.items()}, new_id()
    )
    version = exporter.commit_staged(out_root, staged, digests)
    receipt = {
        "schema_version": "0.1.0",
        "type": "ExportReceipt",
        "id": f"export-{new_id()}",
        "revision": "1.0.0",
        "output_sha256": digests["manifest.json"],
        "destination": output_handle,
        "version": version,
        "files": [
            {"path": name, "sha256": sha, "bytes": store.path(ctx, sha).stat().st_size}
            for name, sha in digests.items()
        ],
        "result": "committed",
        "committed_at": clock(),
    }
    validate("ExportReceipt", receipt)
    event = f"{receipt['id']}:committed"
    ledger.commit(ctx, f"export:{receipt['id']}", 0, event, "export.committed", receipt, [receipt])
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
