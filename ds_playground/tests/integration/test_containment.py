"""The runner confined by this host's OS, tried for real: what the policy refuses and allows.

Each task is real code that attempts one thing and writes what the OS answered to its declared
output. Reads and writes go through libc, past the runner's audit hook, so the answer is the OS's
own. Limits are seen as the run's structured failure. Nothing here reads a secret's bytes: a probe
reports only whether an open succeeded and its errno.
"""

import json
import os
import socket
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
    """C14, A28: writes outside scratch fail by path, `..` and symlink; scratch takes writes."""
    outside = tmp_path / "outside.txt"
    code = (
        f"os.symlink({str(outside)!r}, 'link')\n"
        f"report(path=opened({str(outside)!r}, True), dotdot=opened('../escaped.txt', True),\n"
        f"       inputs=opened('../inputs/orders.csv', True), link=opened('link', True),\n"
        f"       env=opened({str(runner_env / 'planted.py')!r}, True),\n"
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
    """C14, C18, A28: a listener on this host's loopback gets nothing; no name resolves."""
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    listener.settimeout(0.5)
    port = listener.getsockname()[1]
    code = (
        "import socket\n"
        "def connect():\n"
        "    try:\n"
        "        s = socket.socket(); s.settimeout(2)\n"
        f"        s.connect(('127.0.0.1', {port})); return 0\n"
        "    except OSError as error:\n"
        "        return error.errno or -1\n"
        "def resolve():\n"
        "    try:\n"
        "        socket.getaddrinfo('localhost', 80); return 0\n"
        "    except OSError as error:\n"
        "        return error.errno or -1\n"
        "report(connect=connect(), resolve=resolve())\n"
    )
    observed = seen(tmp_path / "run", contained(tmp_path / "run", runner_env, code))
    assert observed["connect"] != 0
    assert observed["resolve"] != 0
    with pytest.raises(TimeoutError):
        listener.accept()
    listener.close()


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
        "report(env=dict(os.environ), fds=[fd for fd in range(1024) if held(fd)])\n"
    )
    observed = seen(tmp_path / "run", contained(tmp_path / "run", runner_env, code))
    leaked = held.fileno()
    held.close()
    scratch = str((tmp_path / "run" / "attempt" / "scratch").resolve())
    assert (observed["env"]["HOME"], observed["env"]["TMPDIR"]) == (scratch, scratch)
    assert "DSP_PLANTED_SECRET" not in observed["env"]
    added_by_the_runtime = {"LC_CTYPE", "__CF_USER_TEXT_ENCODING"}
    assert set(observed["env"]) <= {"HOME", "TMPDIR"} | added_by_the_runtime
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
        "report(fork=tried(os.fork),\n"
        "       spawn=tried(lambda: os.posix_spawn('/bin/sh', ['sh', '-c', 'true'], {})),\n"
        "       exec=tried(lambda: os.execv('/bin/sh', ['sh', '-c', 'true'])))\n"
    )
    observed = seen(tmp_path / "run", contained(tmp_path / "run", runner_env, code))
    assert all(observed.values()), observed


def test_d21_memory_past_the_limit_stops_the_task_and_memory_within_it_is_allowed(
    tmp_path: Path, runner_env: Path
) -> None:
    """D21, A28: allocating past the task's memory limit stops it; below the limit runs."""
    allocate = "chunks = [os.urandom(2**20) for _ in range({})]\nreport(mib=len(chunks))\n"
    within = contained(tmp_path / "within", runner_env, allocate.format(64), memory_mib=256)
    assert seen(tmp_path / "within", within) == {"mib": 64}
    over = contained(tmp_path / "over", runner_env, allocate.format(2048), memory_mib=256)
    assert (over["outcome"], over["failure"]["kind"]) == ("failed", "memory_limit")


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
    slow = contained(tmp_path / "slow", runner_env, "import time\ntime.sleep(60)\n", wall_seconds=3)
    assert (slow["outcome"], slow["failure"]["kind"]) == ("failed", "timeout")
    flood = "open('seen.json', 'wb').write(os.urandom(2**20))\n"
    big = contained(tmp_path / "big", runner_env, flood, output_bytes=4096)
    assert (big["outcome"], big["failure"]["kind"]) == ("failed", "output_limit")


def test_c14_confinement_that_cannot_be_applied_runs_nothing(
    tmp_path: Path, runner_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C14: when the OS refuses the confinement, the process ends before any task code runs."""
    confined = sandbox.local(runner_env)
    monkeypatch.setattr(confined, "profile", lambda work: "(version 1)(not a rule")
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
