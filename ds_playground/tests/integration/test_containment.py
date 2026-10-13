"""The runner confined by this host's OS, tried for real: what the policy refuses and allows.

Each task is real code that attempts one thing and writes what the OS answered to its declared
output. Reads and writes go through libc, past the runner's audit hook, so the answer is the OS's
own. Limits are seen as the run's structured failure. Nothing here reads a secret's bytes: a probe
reports only whether an open succeeded and its errno.
"""

import contextlib
import ctypes
import errno
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest

from dsp.adapters import sandbox
from dsp.application.workloads import base_workload
from dsp.contracts.canonical import file_digest
from dsp.contracts.errors import TrustedContext
from dsp.domain.admission import code_task

pytestmark = pytest.mark.sandbox
CTX = TrustedContext.local()
LIBC = """
import ctypes, json, os
libc = ctypes.CDLL(None, use_errno=True)

def opened(path, write=False):
    fd = libc.creat(path.encode(), 0o600) if write else libc.open(path.encode(), os.O_RDONLY)
    if fd < 0:
        return ctypes.get_errno()
    libc.close(fd)
    return 0

def report(**seen):
    json.dump(seen, open("seen.json", "w"))
"""


def contained(folder: Path, env: Path, code: str, **limits: int) -> dict[str, Any]:
    """Run ``code`` under this OS's sandbox with orders.csv declared; return the run's result."""
    folder.mkdir()
    source, data = folder / "source", folder / "orders.csv"
    source.write_text(LIBC + code)
    data.write_bytes(b"order_id,amount\n000001,5\n")
    spec: dict[str, Any] = {"language": "python", "source_sha256": file_digest(source)}
    spec |= {"inputs": [{"name": "orders.csv", "sha256": file_digest(data)}]}
    spec |= {"outputs": ["seen.json"]} | ({"limits": limits} if limits else {})
    task = code_task(spec, base_workload(CTX))
    return sandbox.local(env).run(task, source, {"orders.csv": data}, folder / "attempt")


def seen(folder: Path, result: dict[str, Any]) -> Any:
    """What the task observed, from its declared output; the run must have succeeded."""
    assert result["outcome"] == "succeeded", result
    return json.loads((folder / "attempt" / "out" / "seen.json").read_text())


def test_b26_python_and_sql_tasks_run_under_the_sandbox(tmp_path: Path, runner_env: Path) -> None:
    """B26: the policy lets real work through: Python with a thread, and DuckDB SQL."""
    python = (
        "import csv, threading\n"
        "rows = []\n"
        "read = lambda: rows.extend(csv.DictReader(open('../inputs/orders.csv')))\n"
        "worker = threading.Thread(target=read)\n"
        "worker.start(); worker.join()\n"
        "report(rows=len(rows))\n"
    )
    assert seen(tmp_path / "py", contained(tmp_path / "py", runner_env, python)) == {"rows": 1}
    folder = tmp_path / "sql"
    folder.mkdir()
    source, data = folder / "source", folder / "orders.csv"
    source.write_text('SELECT count(*) AS orders, sum(amount) AS total FROM "orders.csv"')
    data.write_bytes(b"order_id,amount\n000001,5\n000002,7\n")
    spec = {"language": "sql", "source_sha256": file_digest(source), "outputs": ["totals.csv"]}
    spec["inputs"] = [{"name": "orders.csv", "sha256": file_digest(data)}]
    task = code_task(spec, base_workload(CTX))
    result = sandbox.local(runner_env).run(task, source, {"orders.csv": data}, folder / "attempt")
    assert result["outcome"] == "succeeded", result
    written = (folder / "attempt" / "out" / "totals.csv").read_bytes()
    assert written == b"orders,total\r\n2,12\r\n"


def test_c14_a_read_outside_the_allowlist_is_refused_and_a_declared_read_allowed(
    tmp_path: Path, runner_env: Path
) -> None:
    """C14, A28: a planted secret, the home directory's .ssh and the ledger are unreadable."""
    secret = tmp_path / "planted-secret.txt"
    secret.write_text("never to be read")
    probes = {"secret": secret, "ssh": Path.home() / ".ssh", "ledger": tmp_path / "ledger.sqlite"}
    (tmp_path / "ledger.sqlite").write_bytes(b"SQLite format 3\x00")
    code = (
        "def statted(path):\n"
        "    try:\n"
        "        os.stat(path); return 0\n"
        "    except OSError as error:\n"
        "        return error.errno\n"
    )
    code += "report(" + ", ".join(f"{k}=opened({str(p)!r})" for k, p in probes.items())
    code += f", stat=statted({str(secret)!r}), declared=opened('../inputs/orders.csv'))\n"
    observed = seen(tmp_path / "run", contained(tmp_path / "run", runner_env, code))
    assert observed.pop("declared") == 0
    assert all(observed.values()), observed  # even whether the secret exists is not told


def test_c14_a_write_outside_scratch_is_refused_and_a_scratch_write_allowed(
    tmp_path: Path, runner_env: Path
) -> None:
    """C14, A28: writes fail outside scratch: path, `..`, symlink, root, shared memory."""
    outside = tmp_path / "outside.txt"
    code = (
        f"os.symlink({str(outside)!r}, 'link')\n"
        f"report(path=opened({str(outside)!r}, True), dotdot=opened('../escaped.txt', True),\n"
        f"       inputs=opened('../inputs/orders.csv', True), link=opened('link', True),\n"
        f"       env=opened({str(runner_env / 'planted.py')!r}, True),\n"
        "       root=opened('/planted', True), shm=opened('/dev/shm/planted', True),\n"
        "       scratch=opened('mine.txt', True))\n"
    )
    observed = seen(tmp_path / "run", contained(tmp_path / "run", runner_env, code))
    assert observed.pop("scratch") == 0
    assert all(observed.values()), observed
    assert not outside.exists()
    assert not (tmp_path / "run" / "attempt" / "escaped.txt").exists()
    assert not (runner_env / "planted.py").exists()


def test_c14_no_socket_reaches_even_loopback_and_no_name_resolves(
    tmp_path: Path, runner_env: Path
) -> None:
    """C14, C18, A28: nothing reaches this host's listeners, internet or Unix; no name resolves.

    The Unix listeners are a path and, where the OS has them, an abstract name, which on Linux
    is scoped to the network namespace: what a shared namespace would expose.
    """
    listeners, targets = [], {}
    internet = socket.socket()
    internet.bind(("127.0.0.1", 0))
    listeners.append(internet)
    targets["loopback"] = ("AF_INET", ("127.0.0.1", internet.getsockname()[1]))
    folder = Path(tempfile.mkdtemp(prefix="dsp", dir="/tmp"))  # Unix socket paths are short
    named = socket.socket(socket.AF_UNIX)
    named.bind(str(folder / "s"))
    listeners.append(named)
    targets["unix_path"] = ("AF_UNIX", str(folder / "s"))
    abstract = socket.socket(socket.AF_UNIX)
    with contextlib.suppress(OSError):  # only Linux has the abstract namespace
        abstract.bind(f"\0dsp-{folder.name}")
        listeners.append(abstract)
        targets["unix_abstract"] = ("AF_UNIX", f"\0dsp-{folder.name}")
    for listener in listeners:
        listener.listen()
        listener.settimeout(0.5)
    code = (
        "import socket\n"
        "def connect(family, address):\n"
        "    try:\n"
        "        s = socket.socket(getattr(socket, family)); s.settimeout(2)\n"
        "        s.connect(tuple(address) if family == 'AF_INET' else address); return 0\n"
        "    except OSError as error:\n"
        "        return error.errno or -1\n"
        "def resolve():\n"
        "    try:\n"
        "        socket.getaddrinfo('localhost', 80); return 0\n"
        "    except OSError as error:\n"
        "        return error.errno or -1\n"
        f"targets = {targets!r}\n"
        "report(resolve=resolve(), **{k: connect(*v) for k, v in targets.items()})\n"
    )
    observed = seen(tmp_path / "run", contained(tmp_path / "run", runner_env, code))
    assert all(observed.values()), observed
    assert set(observed) == {"resolve", *targets}
    for listener in listeners:
        with pytest.raises(TimeoutError):
            listener.accept()
        listener.close()
    abstract.close()
    shutil.rmtree(folder)


def test_c14_the_task_sees_only_its_scrubbed_environment_and_standard_descriptors(
    tmp_path: Path, runner_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C14, A28: a secret in the harness's environment and its open files never reach the task."""
    monkeypatch.setenv("DSP_PLANTED_SECRET", "never to be seen")
    held = (tmp_path / "held.txt").open("w")  # an open file of the harness's, made inheritable
    os.set_inheritable(held.fileno(), True)  # as a library's descriptor without CLOEXEC would be
    code = (
        "import fcntl\n"
        "def held(fd):\n"
        "    try:\n"
        "        fcntl.fcntl(fd, fcntl.F_GETFD); return True\n"
        "    except OSError:\n"
        "        return False\n"
        "def parents():  # the harness's own arguments and environment, through the process table\n"
        "    if os.uname().sysname == 'Darwin':\n"
        "        mib = (ctypes.c_int * 3)(1, 49, os.getppid())  # CTL_KERN, KERN_PROCARGS2\n"
        "        size = ctypes.c_size_t(1 << 20)\n"
        "        found = ctypes.create_string_buffer(size.value)\n"
        "        if libc.sysctl(mib, 3, found, ctypes.byref(size), None, 0):\n"
        "            return False\n"
        "        return b'PATH=' in found.raw[: size.value]\n"
        "    fd = libc.open(f'/proc/{os.getppid()}/environ'.encode(), os.O_RDONLY)\n"
        "    if fd < 0:\n"
        "        return False\n"
        "    found = os.read(fd, 1 << 20)\n"
        "    os.close(fd)\n"
        "    return b'PATH=' in found\n"
        "fds = [fd for fd in range(1024) if held(fd)]\n"
        "report(env=dict(os.environ), fds=fds, parent=parents())\n"
    )
    observed = seen(tmp_path / "run", contained(tmp_path / "run", runner_env, code))
    leaked = held.fileno()
    held.close()
    scratch = str((tmp_path / "run" / "attempt" / "scratch").resolve())
    assert (observed["env"]["HOME"], observed["env"]["TMPDIR"]) == (scratch, scratch)
    assert "DSP_PLANTED_SECRET" not in observed["env"]
    assert observed["env"].get("PWD", scratch) == scratch  # bubblewrap sets it
    added_by_the_runtime = {"LC_CTYPE", "__CF_USER_TEXT_ENCODING", "PWD"}
    assert set(observed["env"]) <= {"HOME", "TMPDIR"} | added_by_the_runtime
    assert observed["parent"] is False  # the harness's own environment is out of reach too
    assert leaked not in observed["fds"]
    assert observed["fds"] == [0, 1, 2, 3, 4]  # standard three, the runner's channel, /dev/null


def test_c14_no_process_can_be_started_a_shell_or_otherwise(
    tmp_path: Path, runner_env: Path
) -> None:
    """C14, A28: fork, spawn and exec of a shell are refused, so nothing can outlive the task."""
    code = (
        "def tried(attempt):\n"
        "    try:\n"
        "        attempt(); return 0\n"
        "    except OSError as error:\n"
        "        return error.errno or -1\n"
        "def clone3():  # Linux's clone3 takes its flags in memory, where no filter can look\n"
        "    arguments = (ctypes.c_uint64 * 8)(0, 0, 0, 0, 17, 0, 0, 0)  # exit signal SIGCHLD\n"
        "    child = libc.syscall(435, ctypes.byref(arguments), 64)\n"
        "    if child == 0:\n"
        "        os._exit(0)\n"
        "    if child < 0:\n"
        "        raise OSError(ctypes.get_errno(), 'clone3')\n"
        "linux = {'clone3': tried(clone3)} if os.uname().sysname == 'Linux' else {}\n"
        "report(fork=tried(os.fork),\n"
        "       spawn=tried(lambda: os.posix_spawn('/bin/sh', ['sh', '-c', 'true'], {})),\n"
        "       exec=tried(lambda: os.execv('/bin/sh', ['sh', '-c', 'true'])), **linux)\n"
    )
    observed = seen(tmp_path / "run", contained(tmp_path / "run", runner_env, code))
    assert all(observed.values()), observed


def test_d21_memory_past_the_limit_stops_the_task_and_memory_within_it_is_allowed(
    tmp_path: Path, runner_env: Path
) -> None:
    """D21, A28: allocating past the memory limit stops a task; below it runs.

    Memory a task could hold without mapping it (shared memory, on Linux a memfd) cannot be made.
    """
    allocate = "chunks = [os.urandom(2**20) for _ in range({})]\nreport(mib=len(chunks))\n"
    within = contained(tmp_path / "within", runner_env, allocate.format(64), memory_mib=256)
    assert seen(tmp_path / "within", within) == {"mib": 64}
    over = contained(tmp_path / "over", runner_env, allocate.format(2048), memory_mib=256)
    assert (over["outcome"], over["failure"]["kind"]) == ("failed", "memory_limit")
    unmapped = (
        "from multiprocessing import shared_memory\n"
        "def tried(attempt):\n"
        "    try:\n"
        "        attempt(); return 0\n"
        "    except OSError as error:\n"
        "        return error.errno or -1\n"
        "def memfd():\n"
        "    fd = os.memfd_create('held')\n"
        "    os.write(fd, b'x' * 2**20)\n"
        "def sysv():\n"
        "    segment = libc.shmget(0, 2**20, 0o1600)  # IPC_PRIVATE, IPC_CREAT\n"
        "    if segment < 0:\n"
        "        raise OSError(ctypes.get_errno(), 'shmget')\n"
        "    seen['segment'] = segment  # macOS refuses IPC_RMID here; the test removes it\n"
        "seen = {'shared': tried(lambda: shared_memory.SharedMemory(create=True, size=2**30))}\n"
        "seen['sysv'] = tried(sysv)\n"
        "if hasattr(os, 'memfd_create'):\n"
        "    seen['memfd'] = tried(memfd)\n"
        "report(**seen)\n"
    )
    held = seen(tmp_path / "unmapped", contained(tmp_path / "unmapped", runner_env, unmapped))
    if (segment := held.pop("segment", -1)) >= 0:
        ctypes.CDLL(None).shmctl(segment, 0, None)  # IPC_RMID, from outside: never left behind
    assert all(held.values()), held  # memory held without being mapped cannot be made at all
    refusals = {errno.EPERM, errno.EACCES, errno.ENOSYS}
    assert held["sysv"] in refusals, held  # refused, not merely out of the system's quota


def test_d21_cpu_time_past_the_limit_stops_the_task_even_when_it_ignores_sigxcpu(
    tmp_path: Path, runner_env: Path
) -> None:
    """D21, A28: a busy task is stopped at its CPU-time limit, whether or not it ignores SIGXCPU."""
    busy = "import time\nstart = time.monotonic()\nwhile time.monotonic() - start < 30:\n    pass\n"
    plain = contained(tmp_path / "plain", runner_env, busy, cpu_seconds=1, wall_seconds=20)
    ignoring = "import signal\nsignal.signal(signal.SIGXCPU, signal.SIG_IGN)\n" + busy
    stubborn = contained(
        tmp_path / "stubborn", runner_env, ignoring, cpu_seconds=1, wall_seconds=20
    )
    for result in (plain, stubborn):
        assert (result["outcome"], result["failure"]["kind"]) == ("failed", "cpu_limit")


def test_d21_scratch_past_its_size_is_refused_by_the_filesystem(
    tmp_path: Path, runner_env: Path
) -> None:
    """D21, A28: scratch holds what the task may write and no more; the write fails there."""
    fill = (
        "written = 0\n"
        "try:\n"
        "    with open('fill', 'wb') as handle:\n"
        "        while written < 64 * 2**20:\n"
        "            handle.write(b'x' * 2**20); handle.flush(); written += 2**20\n"
        "    stopped = 0\n"
        "except OSError as error:\n"
        "    stopped = error.errno\n"
        "os.remove('fill')\n"
        "report(written=written, stopped=stopped)\n"
    )
    observed = seen(
        tmp_path / "run", contained(tmp_path / "run", runner_env, fill, scratch_bytes=16 * 2**20)
    )
    assert observed["stopped"] == 28  # ENOSPC
    assert observed["written"] <= 16 * 2**20
    attempt = tmp_path / "run" / "attempt"
    assert not os.path.ismount(attempt / "scratch")
    assert not list(attempt.glob("*.sparseimage"))


def test_d21_time_and_output_past_their_limits_stop_the_task(
    tmp_path: Path, runner_env: Path
) -> None:
    """D21, A28: the wall-clock limit and the output cap hold under the sandbox too."""
    began = time.monotonic()
    slow = contained(tmp_path / "slow", runner_env, "import time\ntime.sleep(60)\n", wall_seconds=3)
    assert (slow["outcome"], slow["failure"]["kind"]) == ("failed", "timeout")
    assert time.monotonic() - began < 15  # nothing confined outlived the kill to hold the channel
    flood = "open('seen.json', 'wb').write(os.urandom(2**20))\n"
    big = contained(tmp_path / "big", runner_env, flood, output_bytes=4096)
    assert (big["outcome"], big["failure"]["kind"]) == ("failed", "output_limit")


def test_c14_confinement_that_cannot_be_applied_runs_nothing(
    tmp_path: Path, runner_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C14: when the OS refuses the confinement, the process ends before any task code runs."""
    confined = sandbox.local(runner_env)
    if hasattr(confined, "profile"):  # Seatbelt: a profile that does not compile
        monkeypatch.setattr(confined, "profile", lambda work: "(version 1)(not a rule")
    else:  # bubblewrap: an option it refuses
        arguments = confined.arguments

        def refused(task: dict[str, Any], work: Path) -> list[str]:
            argv = arguments(task, work)
            return [*argv[:4], "--no-such-option", *argv[4:]]

        monkeypatch.setattr(confined, "arguments", refused)
    planted = tmp_path / "planted.txt"
    folder = tmp_path / "run"
    folder.mkdir()
    source = folder / "source"
    source.write_text(f"open({str(planted)!r}, 'w').write('ran')\nopen('seen.json', 'w')\n")
    spec = {"language": "python", "source_sha256": file_digest(source), "outputs": ["seen.json"]}
    task = code_task(spec, base_workload(CTX))
    result = confined.run(task, source, {}, folder / "attempt")
    assert (result["outcome"], result["failure"]["kind"]) == ("failed", "crash")
    assert not planted.exists()


SUPERVISOR = """
import sys
from pathlib import Path
from dsp.adapters import sandbox
from dsp.application.workloads import base_workload
from dsp.contracts.canonical import file_digest
from dsp.contracts.errors import TrustedContext
from dsp.domain.admission import code_task

env, folder = Path(sys.argv[1]), Path(sys.argv[2])
source = folder / "source"
source.write_text("import time\\ntime.sleep(60)\\n")
spec = {"language": "python", "source_sha256": file_digest(source), "outputs": ["out.json"]}
task = code_task(spec, base_workload(TrustedContext.local()))


class Told(type(sandbox.local(env))):
    def start(self, task, work, channel):
        pid = super().start(task, work, channel)
        (folder / "pid").write_text(str(pid))
        return pid


Told(env).run(task, source, {}, folder / "attempt")
"""


def alive(pid: int) -> bool:
    """Whether a process other than our child is still running (a zombie is not)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    stat = Path(f"/proc/{pid}/stat")  # where the OS has one, a zombie says so
    return not (stat.exists() and stat.read_text().rsplit(")", 1)[-1].split()[0] == "Z")


def test_d24_a_task_whose_harness_dies_ends_with_it(tmp_path: Path, runner_env: Path) -> None:
    """D24, C14: when the harness supervising a task is killed, the task ends within seconds.

    On Linux the kernel's parent-death signal ends it; on macOS a watcher in the task's own
    process does, since the harness's limits on wall and CPU time end with the harness.
    """
    root = Path(__file__).parents[2]
    command = [sys.executable, "-c", SUPERVISOR, str(runner_env), str(tmp_path)]
    harness = subprocess.Popen(command, cwd=root)
    for _ in range(300):
        if (tmp_path / "pid").exists() and (tmp_path / "pid").read_text():
            break
        time.sleep(0.05)
    task = int((tmp_path / "pid").read_text())
    time.sleep(1)
    assert alive(task)
    harness.kill()
    harness.wait(10)
    deadline = time.monotonic() + 10
    while alive(task) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not alive(task)
    sandbox.local(runner_env).release(tmp_path / "attempt")  # what the dead harness left
    assert not os.path.ismount(tmp_path / "attempt" / "scratch")
