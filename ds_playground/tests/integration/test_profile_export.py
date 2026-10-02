import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from dsp.adapters import export_fs
from dsp.adapters.duckdb_profile import profile_csv
from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.adapters.store_fs import ContentStore
from dsp.application.packs import profile_and_export
from dsp.contracts.canonical import file_digest
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.interfaces.cli import app
from fixtures.operations import write_orders

CTX = TrustedContext.local()


@pytest.fixture
def out(tmp_path: Path, home: Path) -> Path:
    """An existing output folder, with DSP_HOME pointed at a temporary profile."""
    folder = tmp_path / "out"
    folder.mkdir()
    return folder


def _csv(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "data.csv"
    path.write_text(text)
    return path


def _run(*args: object) -> Any:
    return CliRunner().invoke(app, [str(arg) for arg in args])


def _columns(folder: Path) -> dict[str, dict[str, Any]]:
    profile = json.loads((folder / "profile.json").read_text())
    return {column["name"]: column for column in profile["columns"]}


def test_profile_exports_a_verified_pack(tmp_path: Path, out: Path) -> None:
    """R11, D23: a CSV becomes a new version folder whose files match the manifest digests."""
    source = tmp_path / "orders.csv"
    write_orders(source, orders=50, accounts=10)
    assert _run("profile", source, "--out", out).exit_code == 0
    assert sorted(p.name for p in (out / "v1").iterdir()) == [
        "manifest.json",
        "profile.json",
        "report.html",
    ]
    assert _run("verify", out / "v1").output.strip() == "verified"
    columns = _columns(out / "v1")
    assert columns["account_num"] | {"distinct": 10} == columns["account_num"]
    assert (columns["account_num"]["proposed_type"], columns["account_num"]["min"]) == (
        "string",
        "000000",
    )
    assert {
        name: columns[name]["proposed_type"]
        for name in ("item_count", "actual_transit_hours", "created_at")
    } == {
        "item_count": "integer",
        "actual_transit_hours": "number",
        "created_at": "timestamp",
    }
    assert "/" not in json.loads((out / "v1" / "manifest.json").read_text())["source"]["name"]
    assert str(tmp_path) not in (out / "v1" / "manifest.json").read_text()


def test_re_export_makes_a_new_version_and_keeps_the_old(tmp_path: Path, out: Path) -> None:
    """D23: exporting again never overwrites; the same source gives a byte-identical manifest."""
    source = tmp_path / "orders.csv"
    write_orders(source, orders=20, accounts=5)
    _run("profile", source, "--out", out)
    before = {p.name: file_digest(p) for p in (out / "v1").iterdir()}
    assert _run("profile", source, "--out", out).exit_code == 0
    assert {p.name: file_digest(p) for p in (out / "v1").iterdir()} == before
    assert file_digest(out / "v2" / "manifest.json") == before["manifest.json"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("id\n007\n010\n", "string"),
        ("id\n0\n-5\n12\n", "integer"),
        ("id\n0.5\n-2\n", "number"),
        ("id\n\n\n", "unknown"),
        ("id\nabc\n1\n", "string"),
    ],
)
def test_proposed_types_preserve_identifier_text(tmp_path: Path, text: str, expected: str) -> None:
    """R17: leading-zero values stay strings; a type is proposed only when every value fits it."""
    assert profile_csv(_csv(tmp_path, text))["columns"][0]["proposed_type"] == expected


def test_nulls_and_rejected_rows_are_counted_not_dropped(tmp_path: Path) -> None:
    """D20: empty values count as nulls; rows the parser cannot read are reported as rejected."""
    profile = profile_csv(_csv(tmp_path, "a,b\n1,x\n2,\n3,y,EXTRA,COLUMNS\n4,z\n"))
    assert (profile["rows"], profile["rows_rejected"]) == (3, 1)
    assert profile["columns"][1]["nulls"] == 1


def test_bounds_are_refused_without_truncation(tmp_path: Path, out: Path) -> None:
    """D20: 100,000 rows pass; 100,001 rows and 201 columns are refused and nothing is exported."""
    assert profile_csv(_csv(tmp_path, "n\n" + "1\n" * 100_000))["rows"] == 100_000
    too_wide = _csv(
        tmp_path, ",".join(f"c{i}" for i in range(201)) + "\n" + ",".join("1" * 201) + "\n"
    )
    with pytest.raises(DspError) as raised:
        profile_csv(too_wide)
    assert raised.value.details == {"limit": "D20"}
    result = _run("profile", _csv(tmp_path, "n\n" + "1\n" * 100_001), "--out", out)
    assert (result.exit_code, list(out.iterdir())) == (2, [])
    assert "INPUT_INVALID" in result.output
    events = SqliteLedger(Path(os.environ["DSP_HOME"]) / "ledger.sqlite", str).events(CTX)
    jobs = [event["type"] for event in events if event["aggregate"].startswith("job:")]
    assert jobs == ["job.started", "job.failed"]


def test_empty_and_unreadable_input_is_refused(tmp_path: Path, out: Path) -> None:
    """D20: an empty file is refused before any job starts and nothing is exported."""
    result = _run("profile", _csv(tmp_path, ""), "--out", out)
    assert (result.exit_code, list(out.iterdir())) == (2, [])
    assert "INPUT_INVALID" in result.output


def test_report_escapes_untrusted_text(tmp_path: Path, out: Path) -> None:
    """C17: a column name containing markup is rendered as text, never as active content."""
    _run("profile", _csv(tmp_path, "<script>alert(1)</script>\n1\n"), "--out", out)
    report = (out / "v1" / "report.html").read_text()
    assert "<script>" not in report
    assert "&lt;script&gt;" in report


def test_verify_detects_a_changed_file_and_a_missing_manifest(tmp_path: Path, out: Path) -> None:
    """A12: a single changed byte, or a folder without a manifest, fails verification."""
    _run("profile", _csv(tmp_path, "a\n1\n"), "--out", out)
    (out / "v1" / "profile.json").write_text("{}")
    tampered = _run("verify", out / "v1")
    assert (tampered.exit_code, "MISMATCH: profile.json" in tampered.output) == (2, True)
    missing = _run("verify", tmp_path)
    assert (missing.exit_code, "NOT_FOUND" in missing.output) == (2, True)


def _export(out: Path, tmp_path: Path, relative: str = "a.txt") -> tuple[Path, dict[str, str]]:
    source = tmp_path / "source.txt"
    source.write_text("content")
    return export_fs.stage(out, {relative: source}, "s1"), {relative: file_digest(source)}


def test_a_tampered_staged_file_is_never_published(tmp_path: Path, out: Path) -> None:
    """D23: bytes that change between staging and commit abort the export and leave it labelled."""
    staged, digests = _export(out, tmp_path)
    (staged / "a.txt").write_text("tampered")
    with pytest.raises(DspError) as raised:
        export_fs.commit_staged(out, staged, digests)
    assert raised.value.code is ErrorCode.INTERNAL_ERROR
    assert [p.name for p in out.iterdir()] == [".dsp-staging-s1"]


def test_versions_never_replace_existing_output(
    tmp_path: Path, out: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D23: the next version skips gaps; a version that appears mid-commit is not overwritten."""
    for name in ("v1", "v3"):
        (out / name).mkdir()
        (out / name / "keep").write_text(name)
    staged, digests = _export(out, tmp_path)
    real_rename = os.rename

    def racing_rename(source: Path, target: Path) -> None:
        if target.name == "v4":
            shutil.copytree(out / "v1", target)  # another export wins the race for v4
        real_rename(source, target)

    monkeypatch.setattr(export_fs.os, "rename", racing_rename)
    assert export_fs.commit_staged(out, staged, digests) == "v5"
    assert {name: (out / name / "keep").read_text() for name in ("v1", "v3", "v4")} == {
        "v1": "v1",
        "v3": "v3",
        "v4": "v1",
    }


def test_export_refuses_traversal_missing_roots_and_full_disks(
    tmp_path: Path, out: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D23, C24: a path that escapes, a missing folder and a full disk each stop the export."""
    with pytest.raises(DspError) as escaped:
        _export(out, tmp_path, "../outside.txt")
    assert escaped.value.code is ErrorCode.FORBIDDEN
    assert not (tmp_path / "outside.txt").exists()
    with pytest.raises(DspError) as missing:
        export_fs.stage(tmp_path / "absent", {}, "s2")
    assert missing.value.code is ErrorCode.NOT_FOUND
    monkeypatch.setattr(export_fs.shutil, "disk_usage", lambda _: shutil._ntuple_diskusage(1, 1, 0))
    with pytest.raises(DspError) as full:
        _export(out, tmp_path)
    assert full.value.code is ErrorCode.QUOTA_EXCEEDED


def test_a_crash_mid_job_leaves_no_success_and_no_output(tmp_path: Path, out: Path) -> None:
    """A03: if the recipe crashes, the ledger holds no succeeded job and no version is published."""
    ledger = SqliteLedger(tmp_path / "ledger.sqlite", lambda: "2026-10-01T00:00:00+00:00")

    def crash(_: Path) -> dict[str, Any]:
        raise RuntimeError("power cut")

    with pytest.raises(RuntimeError):
        profile_and_export(
            CTX,
            _csv(tmp_path, "a\n1\n"),
            out,
            destination="grant-out",
            ledger=ledger,
            store=ContentStore(tmp_path / "store"),
            exporter=export_fs,
            profiler=crash,
            clock=lambda: "2026-10-01T00:00:00+00:00",
            new_id=lambda: "job1",
        )
    assert [event["type"] for event in ledger.events(CTX)] == ["job.started"]
    assert list(out.iterdir()) == []
