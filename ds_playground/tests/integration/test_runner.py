"""The runner and its result channel, run for real: Python and SQL tasks and every failure kind.

These tests start ``python -m dsp_runner`` from the locked runner environment through the shared
core with no confinement, so the runner's own behaviour is tested the same way on any OS; the OS
adapters' confinement is tested in ``test_containment.py``. Unconfined lives here, never in src.
"""

import json
import os
import socket
import time
from pathlib import Path
from typing import Any

import pytest

from dsp.adapters import sandbox
from dsp.application.workloads import base_workload
from dsp.contracts.canonical import file_digest
from dsp.contracts.errors import TrustedContext
from dsp.domain.admission import code_task

CTX = TrustedContext.local()
ORDERS = b"order_id,amount\n000001,5\n000002,7\n"
SUMMARY = """
import csv, json
with open("../inputs/orders.csv", newline="") as handle:
    rows = list(csv.DictReader(handle))
json.dump({"rows": len(rows), "total": sum(int(row["amount"]) for row in rows)},
          open("summary.json", "w"))
print("printed, and never on the channel")
"""


class Unconfined(sandbox.Confined):
    """The shared core with no confinement: a plain process from the runner environment."""

    def start(self, task: dict[str, Any], work: Path, channel: int) -> int:
        """Spawn the runner as a plain process, as the OS adapters do before confining it."""
        python = str(self.environment / "bin" / "python")
        argv = [python, *sandbox.FLAGS, "-m", "dsp_runner", str(work / "task.json")]
        return os.posix_spawn(
            python,
            argv,
            sandbox.scrubbed(work),
            file_actions=[
                (os.POSIX_SPAWN_OPEN, 0, os.devnull, os.O_RDONLY, 0),
                (os.POSIX_SPAWN_DUP2, channel, 1),
                (os.POSIX_SPAWN_OPEN, 2, os.devnull, os.O_WRONLY, 0),
            ],
            setsid=True,
        )


def ran(
    folder: Path,
    env: Path,
    code: str,
    language: str = "python",
    outputs: tuple[str, ...] = ("summary.json",),
    **limits: int,
) -> dict[str, Any]:
    """Declare ``code`` as admission would, reading orders.csv, run it, return the result."""
    folder.mkdir()
    source, data = folder / "source", folder / "orders.csv"
    source.write_text(code)
    data.write_bytes(ORDERS)
    spec: dict[str, Any] = {"language": language, "source_sha256": file_digest(source)}
    spec |= {"inputs": [{"name": "orders.csv", "sha256": file_digest(data)}]}
    spec |= {"outputs": list(outputs)} | ({"limits": limits} if limits else {})
    task = code_task(spec, base_workload(CTX))
    return Unconfined(env).run(task, source, {"orders.csv": data}, folder / "attempt")


def kind(result: dict[str, Any]) -> str:
    """The failure kind of a run that must have failed."""
    assert result["outcome"] == "failed", result
    return str(result["failure"]["kind"])


def test_b26_a_python_task_writes_its_declared_output_and_a_result(
    tmp_path: Path, runner_env: Path
) -> None:
    """B26: a Python task reads its declared input and writes its declared output, hashed here."""
    result = ran(tmp_path / "run", runner_env, SUMMARY)
    assert (result["outcome"], result["failure"]) == ("succeeded", None)
    written = tmp_path / "run" / "attempt" / "out" / "summary.json"
    assert json.loads(written.read_bytes()) == {"rows": 2, "total": 12}
    assert result["outputs"] == [
        {"name": "summary.json", "sha256": file_digest(written), "bytes": written.stat().st_size}
    ]


def test_b26_a_sql_task_runs_against_its_inputs_as_tables(tmp_path: Path, runner_env: Path) -> None:
    """B26, C18: DuckDB SQL reads the inputs as tables; its last statement is its one output."""
    sql = 'SELECT count(*) AS orders, sum(amount) AS total FROM "orders.csv"'
    result = ran(tmp_path / "run", runner_env, sql, "sql", ("totals.csv",))
    assert result["outcome"] == "succeeded", result
    written = tmp_path / "run" / "attempt" / "out" / "totals.csv"
    assert written.read_bytes() == b"orders,total\r\n2,12\r\n"
    install = ran(tmp_path / "install", runner_env, "INSTALL httpfs", "sql", ("x.csv",))
    assert kind(install) == "undeclared_access"
    assert "disabled" in install["failure"]["message"]


def test_c14_an_undeclared_read_fails_the_task_even_when_the_code_swallows_it(
    tmp_path: Path, runner_env: Path
) -> None:
    """C14, C18: reading outside the declaration fails the task in Python and in SQL.

    The runner's audit hook records a Python open, so code that catches the error still fails;
    DuckDB, locked down, refuses SQL's own file access. The sandbox (4.3, 4.4) refuses the read.
    """
    secret = tmp_path / "secret.txt"
    secret.write_text("not declared")
    plain = f"open({str(secret)!r}).read()\n"
    failing = f"open({str(tmp_path / 'absent.txt')!r})\n"  # the open raises, as a refusal would
    swallowed = f"try:\n    open({str(secret)!r}).read()\nexcept OSError:\n    pass\n"
    swallowed += "open('summary.json', 'w').write('{}')\n"
    sql = f"SELECT * FROM read_csv({str(secret)!r})"
    assert kind(ran(tmp_path / "plain", runner_env, plain)) == "undeclared_read"
    assert kind(ran(tmp_path / "failing", runner_env, failing)) == "undeclared_read"
    assert kind(ran(tmp_path / "swallowed", runner_env, swallowed)) == "undeclared_read"
    refused = ran(tmp_path / "sql", runner_env, sql, "sql", ("x.csv",))
    assert (kind(refused), "disabled" in refused["failure"]["message"]) == (
        "undeclared_access",
        True,
    )


def test_c14_a_write_outside_scratch_fails_the_task_by_path_dot_dot_and_symlink(
    tmp_path: Path, runner_env: Path
) -> None:
    """C14: a write anywhere but scratch fails the task: a path, the inputs by `..`, a symlink."""
    outside = tmp_path / "outside.txt"
    cases = {
        "path": f"open({str(outside)!r}, 'w').write('x')\n",
        "dotdot": "open('../inputs/orders.csv', 'a').write('x')\n",
        "symlink": f"import os\nos.symlink({str(outside)!r}, 'ln')\nopen('ln', 'w').write('x')\n",
    }
    for name, code in cases.items():
        assert kind(ran(tmp_path / name, runner_env, code)) == "undeclared_write", name


def test_d21_a_result_over_the_output_cap_is_refused_and_one_at_the_cap_accepted(
    tmp_path: Path, runner_env: Path
) -> None:
    """D21, D20: outputs over the cap are refused whole, at the channel or on reading it."""
    write = "open('summary.json', 'wb').write(b'x' * {})\n"
    at_cap = ran(tmp_path / "at", runner_env, write.format(1024), output_bytes=1024)
    assert at_cap["outcome"] == "succeeded"
    assert at_cap["outputs"][0]["bytes"] == 1024
    over = ran(tmp_path / "over", runner_env, write.format(1025), output_bytes=1024)
    assert kind(over) == "output_limit"
    flood = ran(tmp_path / "flood", runner_env, write.format(2**20), output_bytes=1024)
    assert kind(flood) == "output_limit"
    assert not list((tmp_path / "flood" / "attempt" / "out").glob("*"))


def test_b26_a_crash_a_missing_output_and_a_forged_channel_each_fail_with_their_kind(
    tmp_path: Path, runner_env: Path
) -> None:
    """B26: an exception, an exit status, a missing output, no result, a forged channel, a digest.

    The channel is untrusted: an entry the task forges on it is refused, not ingested.
    """
    forge = (
        "import io, os, tarfile\n"
        "with tarfile.open(fileobj=os.fdopen(3, 'wb'), mode='w|') as tar:\n"
        "    info = tarfile.TarInfo({name!r})\n"
        "    info.size = len({data!r})\n"
        "    tar.addfile(info, io.BytesIO({data!r}))\n"
        "os._exit(0)\n"
    )
    claim = {"schema_version": "0.1.0", "type": "RunnerResult", "failure": None}
    forgeries = {
        "undeclared": ("evil.sh", b"#!"),
        "succeeded_without_outputs": ("result.json", json.dumps(claim).encode()),
        "unknown_kind": (
            "result.json",
            json.dumps(claim | {"failure": {"kind": "none", "message": ""}}).encode(),
        ),
    }
    crashed = ran(tmp_path / "raise", runner_env, "raise ValueError('boom')\n")
    assert (kind(crashed), crashed["failure"]["message"]) == ("crash", "ValueError: boom")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]  # then nothing holds it: a connection is refused at once
    url = f"import urllib.request\nurllib.request.urlopen('http://127.0.0.1:{port}', timeout=5)\n"
    wrapped = ran(tmp_path / "wrapped", runner_env, url)
    assert kind(wrapped) == "crash"
    assert wrapped["failure"]["message"].startswith("URLError: [Errno ")  # the OS's own code
    assert kind(ran(tmp_path / "exit", runner_env, "import sys\nsys.exit(3)\n")) == "crash"
    assert kind(ran(tmp_path / "missing", runner_env, "x = 1\n")) == "missing_output"
    silent = ran(tmp_path / "silent", runner_env, "import os\nos._exit(0)\n")
    assert kind(silent) == "result_invalid"
    for name, (entry, data) in forgeries.items():
        forged = ran(tmp_path / name, runner_env, forge.format(name=entry, data=data))
        assert kind(forged) == "result_invalid", name
    assert not (tmp_path / "undeclared" / "attempt" / "out" / "evil.sh").exists()


def test_b26_a_source_that_differs_from_its_digest_is_never_run(
    tmp_path: Path, runner_env: Path
) -> None:
    """B26: the runner checks the source against the CodeTask's digest before running anything."""
    folder = tmp_path / "run"
    folder.mkdir()
    source, data = folder / "source", folder / "orders.csv"
    source.write_text("open('summary.json', 'w').write('{}')\n")
    data.write_bytes(ORDERS)
    spec = {"language": "python", "source_sha256": file_digest(source), "outputs": ["summary.json"]}
    spec["inputs"] = [{"name": "orders.csv", "sha256": file_digest(data)}]
    task = code_task(spec, base_workload(CTX))
    source.write_text("open('../../planted', 'w').write('ran')\n")
    result = Unconfined(runner_env).run(task, source, {"orders.csv": data}, folder / "attempt")
    assert kind(result) == "digest_mismatch"
    assert not (folder / "planted").exists()


@pytest.mark.slow
def test_d01_a_task_past_its_wall_time_is_stopped_with_what_it_started(
    tmp_path: Path, runner_env: Path
) -> None:
    """D01, D21: a task that outlasts its wall-clock limit is killed and reported as a timeout.

    A process it started in its own group is killed with it, before it can write anything.
    """
    late = tmp_path / "late.txt"
    code = (
        "import os, time\n"
        "if os.fork() == 0:\n"
        f"    time.sleep(3)\n    open({str(late)!r}, 'w').write('outlived')\n    os._exit(0)\n"
        "time.sleep(60)\n"
    )
    result = ran(tmp_path / "run", runner_env, code, wall_seconds=2)
    assert kind(result) == "timeout"
    assert result["failure"]["message"] == "stopped at the 2 s wall-clock limit"
    time.sleep(2)
    assert not late.exists()
