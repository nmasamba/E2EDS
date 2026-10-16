"""Generate, run, repair against the real local model (5.4, A28 part; live_model).

The instruction of the sprint's acceptance line on the synthetic orders fixture; the committed table
must equal an independent DuckDB query on the same file. The model's prose is never read.
"""

import csv
import io
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import duckdb
import httpx
import pytest

from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.application.assistant import BINDING_ID, Assistant
from dsp.contracts.errors import TrustedContext
from fixtures.operations import write_orders
from tests.conftest import Clock
from tests.integration.conftest import Shared
from tests.integration.test_admission import fixed_probes
from tests.integration.test_assistant_loop import calls, ended, ready
from tests.integration.test_controls import say

pytestmark = [pytest.mark.live_model, pytest.mark.sandbox]
CTX = TrustedContext.local()
Harness = tuple[httpx.Client, Clock]
INSTRUCTION = "load this CSV and show transit hours by service level"


@pytest.fixture
def assistant(model_server: Any, state_dir: Path) -> Assistant:
    """A harness's assistant on the session's real server."""
    clock = Clock()
    return Assistant(
        CTX,
        Shared(model_server),
        ledger=lambda: SqliteLedger(state_dir / "ledger.sqlite", clock),
        clock=clock,
    )


def matching_column(
    rows: list[dict[str, str]], expected: dict[str, dict[str, float]]
) -> tuple[str, str] | None:
    """The (level column, value column) whose values equal one of the expected means per level."""
    if not rows:
        return None
    for level_column in rows[0]:
        levels = {r[level_column] for r in rows}
        if levels != set(next(iter(expected.values()))):
            continue
        for value_column in rows[0]:
            if value_column == level_column:
                continue
            for measure, by_level in expected.items():
                try:
                    if all(
                        abs(float(r[value_column]) - by_level[r[level_column]]) < 0.011
                        for r in rows
                    ):
                        return level_column, f"{value_column} = mean {measure}"
                except ValueError:
                    break
    return None


def own_grouping(rows: list[dict[str, str]], data: Path) -> str:
    """Whether the table's numbers are DuckDB's means for the grouping the model chose itself."""
    columns = list(rows[0])
    numeric = [c for c in columns if all(_is_number(r[c]) for r in rows)]
    keys = [c for c in columns if c not in numeric]
    if not keys or not numeric:
        return f"columns {columns}: no grouping and measure to check"
    outcomes = []
    for measure in ("actual_transit_hours", "quoted_transit_hours"):
        expected = {
            tuple(str(v) for v in row[:-1]): float(row[-1])
            for row in duckdb.sql(
                f"SELECT {', '.join(keys)}, avg({measure}) FROM read_csv('{data}') GROUP BY ALL"
            ).fetchall()
        }
        for value in numeric:
            close = all(
                abs(float(r[value]) - expected.get(tuple(r[k] for k in keys), 1e9)) < 0.011
                for r in rows
            )
            if close and len(rows) == len(expected):
                outcomes.append(f"{value} per {keys} equals DuckDB's mean {measure}")
    return "; ".join(outcomes) or f"grouped by {keys} with {numeric}: not DuckDB's means for that"


def _is_number(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True


def test_a28_the_acceptance_instruction_yields_a_committed_table_equal_to_duckdb(
    harness: Harness,
    state_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runner_env: Path,
    evidence: Callable[..., None],
) -> None:
    """R22, A28, B26, D17: model-generated code runs in the sandbox; its table is the right table.

    The record states what ran, how many repairs, and which transit column the model chose; the
    outcome is PASS only when a committed CSV output has one row per service level whose values
    equal DuckDB's mean of the actual or the quoted transit hours on the same file.
    """
    from dsp.harness import workspace

    monkeypatch.setattr(workspace, "probes", lambda state: fixed_probes(cpus=8, memory_gib=32))
    client, _ = harness
    ready(client)
    data = tmp_path / "orders.csv"
    write_orders(data, orders=500, accounts=50)
    granted = client.post("/v1/grants", json={"purpose": "source_root", "path": str(data)}).json()
    assert granted["purpose"] == "source_root"
    expected = {
        measure: {
            level: float(value)
            for level, value in duckdb.sql(
                f"SELECT service_level, avg({measure}) FROM read_csv('{data}') GROUP BY 1"
            ).fetchall()
        }
        for measure in ("actual_transit_hours", "quoted_transit_hours")
    }
    started = time.monotonic()
    answer = say(client, INSTRUCTION)
    assert answer["state"] == "accepted", answer
    job = answer["job"]["id"]
    done = ended(client, job, 900)
    elapsed = time.monotonic() - started
    recorded = calls(state_dir, job)
    submitted = [
        c for c in recorded if c["tool"] == "submit_code_task" and c["state"] == "committed"
    ]
    repairs = sum(1 for c in recorded if c["repair"] and c["state"] == "committed")
    found: tuple[str, str] | None = None
    table: dict[str, Any] = {}
    own = ""
    for call in reversed(submitted):
        if call["result"]["state"] != "succeeded":
            continue
        for output in call["result"]["outputs"]:
            if not output["name"].endswith(".csv"):
                continue
            text = client.get(f"/v1/artifacts/{output['sha256']}").content.decode()
            rows = list(csv.DictReader(io.StringIO(text)))
            found = matching_column(rows, expected)
            table = {
                "job": call["result"]["job"],
                "output": output["name"],
                "sha256": output["sha256"],
                "rows": rows,
            }
            if not found and rows:
                own = own_grouping(rows, data)
            if found:
                break
        if found:
            break
    steps = " | ".join(
        f"{c['n']} {c['tool']} -> {c['state']}"
        + (f" {json.dumps(c['result'])[:300]}" if c["tool"] == "answer" else "")
        + (f" {json.dumps(c['result'])[:400]}" if c["tool"] == "inspect_schema" else "")
        + (
            " "
            + json.dumps(
                {k: v for k, v in (c["result"] or c["refusal"] or {}).items() if k != "outputs"}
            )[:300]
            if c["tool"] in ("submit_code_task", "propose_requirement_patch")
            else ""
        )
        + (
            f" inputs {[i['name'] for i in c['arguments'].get('inputs', [])]}"
            if c["tool"] == "submit_code_task"
            else ""
        )
        + (
            f" source {json.dumps(c['arguments'].get('source', ''))[:200]}"
            if c["tool"] == "write_code_artifact"
            else ""
        )
        for c in recorded
    )
    actual = (
        f"job {done['state']} ({done['reason']}) in {elapsed:.0f} s, {len(recorded)} generations, "
        f"{len(submitted)} task(s) submitted, {repairs} repair(s); "
        + (
            f"committed {table['output']} {table['sha256'][:19]}… of job {table['job'][-6:]} has "
            f"{len(table['rows'])} rows and its {found[1]} per {found[0]} equals DuckDB's"
            if found
            else "no committed CSV output matched DuckDB's means per service level"
            + (
                f"; the committed {table['output']} has {len(table['rows'])} rows: {own}"
                if table
                else ""
            )
        )
        + f"; steps: {steps}"
    )
    evidence(
        "A28",
        f"generated-code-live-{BINDING_ID}",
        "PASS" if found else "FAIL",
        f"the orders fixture (500 rows, seed 0) granted as a source; binding {BINDING_ID}, seed 1, "
        "temperature 0; the instruction of the sprint's acceptance line",
        "model-generated code runs only in the sandboxed runner through admission, the assistant "
        "sees redacted results and repairs at most twice, and the committed table artifact equals "
        "an independent query on the same fixture",
        actual,
        "OS-sandbox assurance for one local user, not VM isolation; one model, one seed, one "
        "instruction, not the qualification suite",
        sprint=5,
        assurance="os_sandbox_single_user",
    )
    assert found, actual
    assert repairs <= 2
    assert done["state"] == "succeeded"
    Path(tmp_path / "facts.json").write_text(
        json.dumps({"seconds": round(elapsed, 1), "generations": len(recorded), "repairs": repairs})
    )
