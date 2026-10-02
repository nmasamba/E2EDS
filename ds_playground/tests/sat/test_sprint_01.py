import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dsp.interfaces.cli import app
from fixtures.operations import write_orders


def test_sprint_1_profile_and_export_the_orders_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R11, D20, D23: the 2,000-order fixture is profiled in full and exported as a verified v1."""
    monkeypatch.setenv("DSP_HOME", str(tmp_path / "home"))
    source, out = tmp_path / "orders.csv", tmp_path / "out"
    out.mkdir()
    write_orders(source)
    runner = CliRunner()
    assert runner.invoke(app, ["profile", str(source), "--out", str(out)]).exit_code == 0
    assert runner.invoke(app, ["verify", str(out / "v1")]).output.strip() == "verified"
    profile = json.loads((out / "v1" / "profile.json").read_text())
    accounts = next(c for c in profile["columns"] if c["name"] == "account_num")
    assert (profile["rows"], profile["rows_rejected"]) == (2000, 0)
    assert (accounts["distinct"], accounts["min"], accounts["max"]) == (400, "000000", "000399")
