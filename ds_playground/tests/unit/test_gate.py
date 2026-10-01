from pathlib import Path

import check_boundaries
import pytest
import trace_ids

ROOT = Path(__file__).parents[2]


def test_boundary_check_flags_forbidden_imports(tmp_path: Path) -> None:
    """AGENTS.md §4: contracts may not import adapters, and application may not start processes."""
    for layer, source in {
        "contracts": "from dsp.adapters import store_fs\n",
        "application": "import subprocess\nfrom dsp.contracts import errors\n",
        "adapters": "import subprocess\nfrom dsp.contracts import errors\n",
    }.items():
        (tmp_path / "dsp" / layer).mkdir(parents=True)
        (tmp_path / "dsp" / layer / "m.py").write_text(source)
    found = check_boundaries.violations(tmp_path)
    assert len(found) == 2
    assert "contracts may not import dsp.adapters" in found[1]
    assert "application may not import subprocess" in found[0]


def test_the_real_tree_respects_boundaries() -> None:
    """AGENTS.md §4: the shipped source has no forbidden import."""
    assert check_boundaries.violations(ROOT / "src") == []


def test_a_skipped_test_fails_the_run(pytester: pytest.Pytester) -> None:
    """AGENTS.md §6: a skipped test turns a green run red."""
    pytester.makeconftest((ROOT / "tests" / "conftest.py").read_text())
    pytester.makepyfile("import pytest\n\n@pytest.mark.skip\ndef test_hidden():\n    pass\n")
    assert pytester.runpytest().ret == pytest.ExitCode.TESTS_FAILED


def test_sprint_scope_expands_ranges() -> None:
    """The ID trace reads a sprint heading, expands ranges and ignores backlog (B) items."""
    prompts = "## Sprint 3 — M1: x (B25, B05; A03, A24–A27; R05; D03, ADR19)\n"
    expected = {"A03", "A24", "A25", "A26", "A27", "R05", "D03", "ADR19"}
    assert trace_ids.scope(prompts, 3) == expected
    with pytest.raises(SystemExit):
        trace_ids.scope(prompts, 4)
