"""Starting the runner and reading what it returns: the part of the sandbox both OSes share.

The OS adapters confine the process; this module lays out the attempt directory, starts the
runner from the locked runner environment with a fixed argument vector and a scrubbed
environment, stops it at the wall-clock limit and reads its one result channel, bounded, because
everything the runner sends is untrusted: only regular files with declared names are taken,
within the output cap, and hashed here.
"""

import contextlib
import json
import os
import shutil
import signal
import tarfile
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from dsp.contracts.canonical import canonical_json, file_digest
from dsp.contracts.errors import DspError
from dsp.contracts.schemas import validate

FRAMING = 64 * 1024  # the result file and the tar headers, beyond the outputs' own bytes


def failed(kind: str, message: str) -> dict[str, Any]:
    """A run that produced no result: partial output is never one."""
    return {"outcome": "failed", "failure": {"kind": kind, "message": message}, "outputs": []}


def run(
    task: dict[str, Any],
    source: Path,
    inputs: Mapping[str, Path],
    work: Path,
    environment: Path,
) -> dict[str, Any]:
    """Run the task with ``python -m dsp_runner`` from ``environment`` and read its result."""
    scratch, limits = work / "scratch", task["limits"]
    (work / "inputs").mkdir(parents=True)
    scratch.mkdir()
    shutil.copyfile(source, work / "source")
    for name, path in inputs.items():
        shutil.copyfile(path, work / "inputs" / name)
    (work / "task.json").write_bytes(canonical_json(task))
    python = str(environment / "bin" / "python")
    argv = [python, "-I", "-B", "-X", "utf8", "-m", "dsp_runner", str(work / "task.json")]
    read, write = os.pipe()
    pid = os.posix_spawn(
        python,
        argv,
        {"HOME": str(scratch), "TMPDIR": str(scratch)},
        file_actions=[
            (os.POSIX_SPAWN_OPEN, 0, os.devnull, os.O_RDONLY, 0),
            (os.POSIX_SPAWN_DUP2, write, 1),
            (os.POSIX_SPAWN_OPEN, 2, os.devnull, os.O_WRONLY, 0),
        ],
        setsid=True,
    )
    os.close(write)
    cap, channel, over = limits["output_bytes"] + FRAMING, work / "channel.tar", threading.Event()

    def stop() -> None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(pid, signal.SIGKILL)

    def drain() -> None:
        with os.fdopen(read, "rb") as pipe, channel.open("wb") as sink:
            while chunk := pipe.read(65536):
                if sink.tell() + len(chunk) > cap:
                    over.set()
                    stop()
                    return
                sink.write(chunk)

    reader = threading.Thread(target=drain)
    reader.start()
    deadline, late = time.monotonic() + limits["wall_seconds"], False
    while not (reaped := os.waitpid(pid, os.WNOHANG))[0]:
        if late := time.monotonic() >= deadline:
            stop()
            reaped = os.waitpid(pid, 0)
            break
        time.sleep(0.05)
    stop()  # a group outlives its reaped leader under the same ID: nothing the task started stays
    code = os.waitstatus_to_exitcode(reaped[1])
    reader.join()
    if late:
        return failed("timeout", f"stopped at the {limits['wall_seconds']} s wall-clock limit")
    if over.is_set():
        return failed("output_limit", f"the result exceeded {limits['output_bytes']} bytes")
    if code == -signal.SIGXCPU:
        return failed("cpu_limit", f"stopped at the {limits['cpu_seconds']} s CPU-time limit")
    if code == -signal.SIGKILL:
        return failed("killed", "stopped by SIGKILL")
    if code:
        return failed("crash", f"the runner ended with status {code}")
    return _received(task, channel, work / "out")


def _received(task: dict[str, Any], channel: Path, out: Path) -> dict[str, Any]:
    """The result the runner sent: its failure, or every declared output within the cap."""
    declared, sizes, result = set(task["outputs"]), {}, None
    out.mkdir()
    try:
        with tarfile.open(channel, "r:") as tar:
            for member in tar:
                taken = result is not None if member.name == "result.json" else member.name in sizes
                known = member.name in declared | {"result.json"} and not taken
                if not (known and member.isreg() and (content := tar.extractfile(member))):
                    return failed("result_invalid", "the channel held an undeclared entry")
                if member.name == "result.json":
                    result = json.loads(content.read(FRAMING))
                    validate("RunnerResult", result)
                    continue
                sizes[member.name] = member.size
                if sum(sizes.values()) > task["limits"]["output_bytes"]:
                    limit = task["limits"]["output_bytes"]
                    return failed("output_limit", f"the outputs exceed {limit} bytes")
                with (out / member.name).open("wb") as sink:
                    shutil.copyfileobj(content, sink)
    except (tarfile.TarError, ValueError, DspError):
        return failed("result_invalid", "the channel held no readable result")
    if result is None:
        return failed("result_invalid", "the channel held no result")
    if result["failure"]:
        return {"outcome": "failed", "failure": result["failure"], "outputs": []}
    if set(sizes) != declared:
        return failed("result_invalid", "the result is missing a declared output")
    outputs = [
        {"name": name, "sha256": file_digest(out / name), "bytes": sizes[name]}
        for name in task["outputs"]
    ]
    return {"outcome": "succeeded", "failure": None, "outputs": outputs}
