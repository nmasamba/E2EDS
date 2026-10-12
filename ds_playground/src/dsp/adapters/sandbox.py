"""Starting the runner and reading what it returns: the part of the sandbox both OSes share.

An OS adapter confines the process it starts; ``Confined.run`` does the rest the same way on both:
it lays out the attempt directory, gives the adapter a fixed argument vector and a scrubbed
environment, stops the process at the wall-clock limit, and reads its one result channel, bounded,
because everything the runner sends is untrusted: only regular files with declared names are
taken, within the output cap, and hashed here.
"""

import contextlib
import json
import os
import shutil
import signal
import sys
import tarfile
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from dsp.contracts.canonical import canonical_json, file_digest
from dsp.contracts.errors import DspError, ErrorCode
from dsp.contracts.schemas import validate

FRAMING = 64 * 1024  # the result file and the tar headers, beyond the outputs' own bytes
FLAGS = ["-I", "-B", "-X", "utf8"]  # isolated, no bytecode written, UTF-8 whatever the locale


def failed(kind: str, message: str) -> dict[str, Any]:
    """A run that produced no result: partial output is never one."""
    return {"outcome": "failed", "failure": {"kind": kind, "message": message}, "outputs": []}


class Confined(ABC):
    """The runner confined by one OS: the steps both OSes share, around the ones they do not.

    A subclass starts the confined process, may stop it on a limit its OS measures but does not
    enforce (``exceeded``), names a kill it cannot otherwise explain (``killed``) and releases what
    it set up (``end``).
    """

    killed = "killed"

    def __init__(self, environment: Path) -> None:
        self.environment = environment

    @abstractmethod
    def start(self, task: dict[str, Any], work: Path, channel: int) -> int:
        """Start ``python -m dsp_runner work/task.json`` confined, writing to ``channel``.

        Standard input and error are ``/dev/null``; the process leads a new session; its
        environment is ``scrubbed(work)``. Return its process ID.
        """

    def exceeded(self, pid: int, task: dict[str, Any]) -> bool:
        """True when the running process is past a limit its OS does not stop it at."""
        return False

    def end(self, work: Path) -> None:
        """Release whatever ``start`` set up for this attempt."""
        return None

    def run(
        self, task: dict[str, Any], source: Path, inputs: Mapping[str, Path], work: Path
    ) -> dict[str, Any]:
        """Run the task on its source and declared inputs; see ``ports.Runner``."""
        work, limits = work.resolve(), task["limits"]
        (work / "inputs").mkdir(parents=True)
        (work / "scratch").mkdir()
        shutil.copyfile(source, work / "source")
        for name, path in inputs.items():
            shutil.copyfile(path, work / "inputs" / name)
        (work / "task.json").write_bytes(canonical_json(task))
        read, write = os.pipe()
        try:
            pid = self.start(task, work, write)
        except BaseException:
            os.close(read)
            self.end(work)
            raise
        finally:
            os.close(write)
        cap, channel, over = (
            limits["output_bytes"] + FRAMING,
            work / "channel.tar",
            threading.Event(),
        )

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
        deadline, late, spent = time.monotonic() + limits["wall_seconds"], False, False
        try:
            while not (reaped := os.wait4(pid, os.WNOHANG))[0]:
                late = time.monotonic() >= deadline
                if late or (spent := self.exceeded(pid, task)):
                    stop()
                    reaped = os.wait4(pid, 0)
                    break
                time.sleep(0.05)
            stop()  # a group outlives its reaped leader under the same ID: nothing it began stays
            reader.join()
        finally:
            self.end(work)
        code, usage = os.waitstatus_to_exitcode(reaped[1]), reaped[2]
        cpu = usage.ru_utime + usage.ru_stime
        if late:
            return failed("timeout", f"stopped at the {limits['wall_seconds']} s wall-clock limit")
        if over.is_set():
            return failed("output_limit", f"the result exceeded {limits['output_bytes']} bytes")
        if (
            spent
            or code == -signal.SIGXCPU
            or (code == -signal.SIGKILL and cpu >= limits["cpu_seconds"])
        ):
            return failed("cpu_limit", f"stopped at the {limits['cpu_seconds']} s CPU-time limit")
        if code == -signal.SIGKILL:
            return failed(self.killed, "stopped by SIGKILL")
        if code:
            return failed("crash", f"the runner ended with status {code}")
        return _received(task, channel, work / "out")


def local(environment: Path) -> Confined:
    """The runner confined by this host's OS; the one place the OS chooses the adapter."""
    if sys.platform == "darwin":
        from dsp.adapters.seatbelt import Seatbelt  # it loads libSystem as it starts

        return Seatbelt(environment)
    raise DspError(ErrorCode.DEPENDENCY_UNAVAILABLE, f"no sandbox for {sys.platform} yet")


def scrubbed(work: Path) -> dict[str, str]:
    """The task's whole environment: its home and temporary folder are its scratch, nothing else."""
    return {"HOME": str(work / "scratch"), "TMPDIR": str(work / "scratch")}


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
