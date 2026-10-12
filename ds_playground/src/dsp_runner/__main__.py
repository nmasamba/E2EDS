"""The runner: ``python -m dsp_runner <attempt>/task.json`` runs one CodeTask inside the sandbox.

The sandbox adapter lays the attempt directory out before the runner starts: ``task.json`` (the
CodeTask), ``source``, the declared inputs under ``inputs/`` and an empty ``scratch/``, where the
code runs. Before any task code runs, the runner checks the source and inputs against their
digests and lowers its own CPU-time and open-file limits, which an unprivileged process cannot
raise again. It then runs the Python, or the DuckDB SQL against the inputs loaded as tables, and
writes ``result.json`` and, on success, the declared outputs to standard output as one tar stream:
the only result channel. Everything on it is untrusted: the adapter validates the result against
its schema and bounds, checks and hashes the outputs, so the runner validates nothing itself.

An audit hook records every open outside the declaration, so such a task fails even when its code
swallows the refusal. It is a detector, never the boundary: the OS sandbox is the boundary.
"""

import csv
import errno
import io
import json
import os
import resource
import stat
import sys
import tarfile
from pathlib import Path
from typing import Any

import duckdb

from dsp.contracts.canonical import canonical_json, file_digest

MESSAGE = 500  # characters of a failure message the result keeps
WRITES = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
LOCKED = (
    "SET enable_external_access = false",
    "SET autoinstall_known_extensions = false",
    "SET autoload_known_extensions = false",
    "SET lock_configuration = true",
)


def run(task: dict[str, Any], work: Path) -> dict[str, str] | None:
    """Run the task in ``work/scratch``; return why it failed, or None when it succeeded."""
    scratch, source = work / "scratch", work / "source"
    checked = [(source, task["source_sha256"])]
    checked += [(work / "inputs" / item["name"], item["sha256"]) for item in task["inputs"]]
    for path, expected in checked:
        if file_digest(path) != expected:
            return {"kind": "digest_mismatch", "message": f"{path.name} differs from its digest"}
    limits = task["limits"]
    resource.setrlimit(resource.RLIMIT_CPU, (limits["cpu_seconds"], limits["cpu_seconds"] + 1))
    resource.setrlimit(resource.RLIMIT_NOFILE, (limits["open_files"], limits["open_files"]))
    code = source.read_text()
    os.chdir(scratch)
    readable = {Path(prefix).resolve() for prefix in (sys.prefix, sys.base_prefix)}
    readable.add(work.resolve())
    writable, refused = scratch.resolve(), []

    def audit(event: str, args: tuple[Any, ...]) -> None:
        if event != "open" or not isinstance(args[0], str | bytes):
            return
        target = Path(os.fsdecode(args[0])).resolve()
        if (args[2] or 0) & WRITES:
            if not target.is_relative_to(writable):
                refused.append("undeclared_write")
        elif not any(target.is_relative_to(root) for root in readable):
            refused.append("undeclared_read")

    sys.addaudithook(audit)
    raised: BaseException | None = None
    try:
        if task["language"] == "python":
            exec(compile(code, "task.py", "exec"), {"__name__": "__main__"})
        else:
            query(task, work, code)
    except SystemExit as stop:
        raised = stop if stop.code not in (None, 0) else None
    except duckdb.PermissionException as error:
        return {"kind": "undeclared_access", "message": str(error)[:MESSAGE]}
    except BaseException as error:  # the task's own failure, whatever it raised
        raised = error
    if refused:
        return {"kind": refused[0], "message": f"{len(refused)} open(s) outside the declaration"}
    if raised is not None:
        kind = "crash"
        if isinstance(raised, MemoryError):
            kind = "memory_limit"
        elif isinstance(raised, OSError) and raised.errno in (errno.ENOSPC, errno.EDQUOT):
            kind = "scratch_limit"
        said = f"{type(raised).__name__}: {raised}".replace(str(work), "<attempt>")
        return {"kind": kind, "message": said[:MESSAGE]}
    for name in task["outputs"]:
        if not (scratch / name).is_file() or (scratch / name).is_symlink():
            return {"kind": "missing_output", "message": f"{name} was not written"}
    return None


def query(task: dict[str, Any], work: Path, sql: str) -> None:
    """Load the inputs as tables named as declared, lock DuckDB down, run the SQL, write its rows.

    Once the inputs are loaded, DuckDB may read no file, load no extension and change no setting:
    defence in depth behind the sandbox, as C18 asks of SQL.
    """
    con = duckdb.connect()
    for item in task["inputs"]:
        path = str(work / "inputs" / item["name"])
        con.execute(f'CREATE TABLE "{item["name"]}" AS SELECT * FROM read_csv(?)', [path])
    for setting in LOCKED:
        con.execute(setting)
    rows = con.execute(sql).fetchall()
    if con.description is None:
        raise ValueError("the last statement returns no table")
    with open(task["outputs"][0], "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(column[0] for column in con.description)
        writer.writerows(rows)


def main(path: Path) -> int:
    """Run the task and send its result on the channel; nothing the task prints reaches it."""
    channel = os.fdopen(os.dup(1), "wb")
    quiet = os.open(os.devnull, os.O_WRONLY)
    os.dup2(quiet, 1)
    os.dup2(quiet, 2)
    task = json.loads(path.read_text())
    failure = run(task, path.parent)
    result = {"schema_version": "0.1.0", "type": "RunnerResult", "failure": failure}
    sent = canonical_json(result)

    def entry(name: str, size: int) -> tarfile.TarInfo:
        info = tarfile.TarInfo(name)
        info.size, info.mode = size, stat.S_IRUSR
        return info

    with channel, tarfile.open(fileobj=channel, mode="w|") as tar:  # closed here, not at exit
        tar.addfile(entry("result.json", len(sent)), io.BytesIO(sent))
        for name in task["outputs"] if failure is None else []:
            with open(name, "rb") as handle:
                tar.addfile(entry(name, os.fstat(handle.fileno()).st_size), handle)
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
