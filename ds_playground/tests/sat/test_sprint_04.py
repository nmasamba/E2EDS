"""Sprint 4 acceptance: A28 containment, tried by real tasks through the job path.

Each part admits real Python as a CodeTask, which the harness's dispatcher runs in this host's OS
sandbox, and writes its part of the A28 evidence with what the run showed (`make sat`). Every record
is at OS-sandbox, single-user assurance, the owner's 2026-10-01 deviation from the suite's VM.
"""

import hashlib
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from dsp.interfaces.cli import app
from tests.conftest import Clock
from tests.integration.test_jobs import job_of, until

pytestmark = pytest.mark.sandbox
Harness = tuple[httpx.Client, Clock]
Evidence = Callable[..., None]
ASSURANCE = "os_sandbox_single_user"
LIMIT = (
    "OS-sandbox assurance for one local user (Seatbelt on macOS, bubblewrap and seccomp on "
    "Linux): not VM isolation, and not a boundary for hostile multi-tenant code"
)
HAND_WRITTEN = "the code is written by hand: no assistant generates code until Sprint 5"


def run(client: httpx.Client, code: str, **limits: int) -> dict[str, Any]:
    """Run ``code`` as a sandboxed job writing out.json, the way `dsp run-task` does; return it."""
    if client.get("/v1/hardware").status_code == 404:
        assert client.post("/v1/hardware").status_code == 200
    source = client.post("/v1/sources", json={"text": code}).json()["sha256"]
    task: dict[str, Any] = {"language": "python", "source_sha256": source, "outputs": ["out.json"]}
    task |= {"limits": limits} if limits else {}
    request = {"operation": "analyse", "idempotency_key": source + str(limits), "task": task}
    job = client.post("/v1/jobs", json=request).json()["id"]
    until(lambda: job_of(client, job)["state"] in ("succeeded", "failed", "cancelled"), 60)
    found: dict[str, Any] = job_of(client, job)
    return found


def told(job: dict[str, Any]) -> str:
    """How the job ended, as its record says it."""
    return f"{job['state']}: {job['reason']}"


def test_a28_a_host_secret_cannot_be_read(
    harness: Harness, tmp_path: Path, evidence: Evidence
) -> None:
    """A28, C14: real code reading a planted host secret or the home's .ssh is refused by the OS."""
    client, _ = harness
    secret = tmp_path / "planted-secret.txt"
    secret.write_text("never to be read")
    planted = run(client, f"open({str(secret)!r}).read()\n")
    ssh = run(client, f"open({str(Path.home() / '.ssh' / 'id_ed25519')!r}).read()\n")
    for job in (planted, ssh):
        assert job["state"] == "failed"
        assert job["reason"].startswith("undeclared_read: 1 open(s) outside the declaration")
    assert "the OS answered" in planted["reason"]
    evidence(
        "A28",
        "host-secret",
        "PASS",
        "planted-secret-and-home-ssh",
        "real code opening a planted host secret and a key under the home's .ssh is refused by "
        "the OS; the task fails and no result exists",
        f"planted secret: {told(planted)}; home .ssh: {told(ssh)}",
        LIMIT,
        HAND_WRITTEN,
        sprint=4,
        assurance=ASSURANCE,
    )


def test_a28_no_network_fetch_reaches_even_this_host(harness: Harness, evidence: Evidence) -> None:
    """A28, C18: an HTTP fetch from this host's own listener and a name lookup both fail."""
    client, _ = harness
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(0.5)
        url = f"http://127.0.0.1:{listener.getsockname()[1]}/simple/requests/"
        fetch = run(client, f"import urllib.request\nurllib.request.urlopen({url!r}, timeout=5)\n")
        lookup = run(client, "import socket\nsocket.getaddrinfo('pypi.org', 443)\n")
        with pytest.raises(TimeoutError):
            listener.accept()
    assert (fetch["state"], lookup["state"]) == ("failed", "failed")
    assert fetch["reason"].startswith("crash: URLError: [Errno ")
    evidence(
        "A28",
        "network-fetch",
        "PASS",
        "loopback-listener-and-lookup",
        "an HTTP fetch from a listener on this host's loopback and a name lookup both fail inside "
        "the sandbox; the listener receives nothing",
        f"fetch: {told(fetch)}; lookup: {told(lookup)}; the listener accepted nothing",
        LIMIT,
        HAND_WRITTEN,
        sprint=4,
        assurance=ASSURANCE,
    )


def test_a28_no_dependency_can_be_installed(
    harness: Harness, runner_env: Path, evidence: Evidence
) -> None:
    """A28: pip cannot be started, and nothing can be written into the runner's environment."""
    client, _ = harness
    site = next(runner_env.glob("lib/python3.12/site-packages"))
    pip = run(client, "import subprocess, sys\nsubprocess.run([sys.executable, '-m', 'pip'])\n")
    planted = run(client, f"open({str(site / 'injected.py')!r}, 'w').write('x')\n")
    assert pip["state"] == "failed"
    assert pip["reason"].startswith("crash: PermissionError: [Errno ")
    assert planted["reason"].startswith("undeclared_write: 1 open(s) outside the declaration")
    assert not (site / "injected.py").exists()
    evidence(
        "A28",
        "dependency-install",
        "PASS",
        "pip-process-and-site-packages-write",
        "starting pip is refused (no process may be created) and a module written into the "
        "runner environment is refused by the OS",
        f"pip: {told(pip)}; write into site-packages: {told(planted)}",
        LIMIT,
        HAND_WRITTEN,
        sprint=4,
        assurance=ASSURANCE,
    )


def test_a28_a_file_standing_for_the_final_partition_cannot_be_read(
    harness: Harness, state_dir: Path, evidence: Evidence
) -> None:
    """A28: a file in the harness's state folder, standing for a sealed partition, is unreadable."""
    client, _ = harness
    sealed = state_dir / "sealed" / "final.csv"
    sealed.parent.mkdir()
    sealed.write_text("label\n1\n")
    job = run(client, f"open({str(sealed)!r}).read()\n")
    assert job["state"] == "failed"
    assert job["reason"].startswith("undeclared_read: 1 open(s) outside the declaration")
    evidence(
        "A28",
        "final-set",
        "PASS",
        "state-folder-file",
        "a file in the harness's state folder, standing for a sealed final partition, is "
        "refused by the OS to task code",
        told(job),
        LIMIT,
        "sealed partitions and their evaluator arrive in Sprint 9: the stand-in is a plain file",
        sprint=4,
        assurance=ASSURANCE,
    )


def test_a28_the_ledger_and_the_task_declaration_cannot_be_changed(
    harness: Harness, state_dir: Path, evidence: Evidence
) -> None:
    """A28: real code writing the ledger or its own task file is refused; both stay intact."""
    client, _ = harness
    run(client, "open('out.json', 'w').write('{}')\n")  # something in the ledger first
    ledger = state_dir / "ledger.sqlite"
    ledger_write = run(client, f"open({str(ledger)!r}, 'r+b').write(b'corrupt')\n")
    task_write = run(client, "open('../task.json', 'w').write('{}')\n")
    for job in (ledger_write, task_write):
        assert job["state"] == "failed"
        assert job["reason"].startswith("undeclared_write: 1 open(s) outside the declaration")
    assert ledger.read_bytes().startswith(b"SQLite format 3\x00")
    assert client.get(f"/v1/jobs/{task_write['id']}").status_code == 200
    evidence(
        "A28",
        "metadata-mutation",
        "PASS",
        "ledger-and-task-file",
        "real code writing the ledger or its own task declaration is refused by the OS; the "
        "ledger stays a readable database holding the job",
        f"ledger: {told(ledger_write)}; task file: {told(task_write)}",
        LIMIT,
        HAND_WRITTEN,
        sprint=4,
        assurance=ASSURANCE,
    )


def test_a28_no_process_can_be_started_to_outlive_the_task(
    harness: Harness, evidence: Evidence
) -> None:
    """A28, C14: fork and a shell's spawn are refused, so nothing can outlive the task."""
    client, _ = harness
    fork = run(client, "import os\nos.fork()\n")
    shell = run(client, "import os\nos.posix_spawn('/bin/sh', ['sh', '-c', 'sleep 60'], {})\n")
    for job in (fork, shell):
        assert job["state"] == "failed"
        assert job["reason"].startswith("crash: ")
        assert "Error: [Errno " in job["reason"]
    evidence(
        "A28",
        "process",
        "PASS",
        "fork-and-shell",
        "fork and spawning a shell are refused, so no process the task starts can outlive it",
        f"fork: {told(fork)}; shell: {told(shell)}",
        LIMIT,
        HAND_WRITTEN,
        sprint=4,
        assurance=ASSURANCE,
    )


@pytest.mark.slow
def test_a28_cpu_memory_time_output_and_scratch_are_bounded(
    harness: Harness, evidence: Evidence
) -> None:
    """A28, D01, D21: each limit stops a task that passes it, with the limit named."""
    client, _ = harness
    busy = "import time\nstart = time.monotonic()\nwhile time.monotonic() - start < 30:\n    pass\n"
    fill = (
        "with open('fill', 'wb') as f:\n    while True:\n        f.write(b'x' * 2**20); f.flush()\n"
    )
    jobs = {
        "cpu": run(client, busy, cpu_seconds=1, wall_seconds=20),
        "memory": run(
            client, "import os\nchunks = [os.urandom(2**20) for _ in range(2048)]\n", memory_mib=256
        ),
        "time": run(client, "import time\ntime.sleep(60)\n", wall_seconds=3),
        "output": run(client, "open('out.json', 'wb').write(b'x' * 2**20)\n", output_bytes=4096),
        "scratch": run(client, fill, scratch_bytes=16 * 2**20),
    }
    kinds = {name: job["reason"].split(":")[0] for name, job in jobs.items()}
    assert kinds == {
        "cpu": "cpu_limit",
        "memory": "memory_limit",
        "time": "timeout",
        "output": "output_limit",
        "scratch": "scratch_limit",
    }
    assert all(job["state"] == "failed" for job in jobs.values())
    evidence(
        "A28",
        "bounds",
        "PASS",
        "cpu-1s-memory-256MiB-wall-3s-output-4KiB-scratch-16MiB",
        "a task past its CPU, memory, wall-clock, output or scratch limit is stopped and fails "
        "with that limit named; nothing it wrote is a result",
        "; ".join(f"{name}: {told(job)}" for name, job in jobs.items()),
        LIMIT,
        HAND_WRITTEN,
        sprint=4,
        assurance=ASSURANCE,
    )


def test_a28_code_and_attempts_are_kept(
    harness: Harness, state_dir: Path, evidence: Evidence
) -> None:
    """A28: every task's code is kept by digest with the CodeTask, and every attempt's events."""
    client, _ = harness
    code = "raise ValueError('a failed attempt is kept too')\n"
    job = run(client, code)
    request = client.get("/v1/events").json()["events"]
    started = [e for e in request if e["type"] == "job.started" and e["body"]["job"] == job["id"]]
    digest = "sha256:" + hashlib.sha256(code.encode()).hexdigest()
    stored = state_dir / "store" / "cas" / "tenant-local" / digest.removeprefix("sha256:")
    assert stored.read_text() == code
    assert (job["state"], job["attempts"], len(started)) == ("failed", 1, 1)
    evidence(
        "A28",
        "preserved",
        "PASS",
        "failed-attempt",
        "a task's source is kept in the content store under the digest its CodeTask records, and "
        "each attempt's start and end are events",
        f"{told(job)}; source stored by digest; {len(started)} attempt started and ended",
        LIMIT,
        "repairs (at most two per task, D17) need the assistant of Sprint 5",
        sprint=4,
        assurance=ASSURANCE,
    )


def test_a28_the_acceptance_line_read_secret_is_denied_by_the_os(
    home: Path, evidence: Evidence
) -> None:
    """A28, B26: `dsp run-task fixtures/tasks/read_secret.json` is refused by the OS (acceptance).

    The overall A28 record stays INSUFFICIENT_EVIDENCE: the scenario names model-generated code
    and at most two repairs, which need the assistant of Sprint 5, real sealed partitions (Sprint
    9), and VM isolation, which this build replaces with an OS sandbox by owner decision.
    """
    task = Path(__file__).parents[2] / "fixtures" / "tasks" / "read_secret.json"
    ran = CliRunner().invoke(app, ["run-task", str(task)])
    said = ran.output.strip().split(" ", 1)[1]
    assert ran.exit_code == 2, ran.output
    assert said.startswith("failed: undeclared_read: 1 open(s) outside the declaration; the OS")
    evidence(
        "A28",
        "acceptance-read-secret",
        "PASS",
        "fixtures/tasks/read_secret.json",
        "dsp run-task fixtures/tasks/read_secret.json, whose Python opens /etc/passwd, ends failed "
        "with the OS's refusal and exit status 2",
        f"exit status {ran.exit_code}; {said}",
        LIMIT,
        sprint=4,
        assurance=ASSURANCE,
    )
    evidence(
        "A28",
        "generated-code-containment",
        "INSUFFICIENT_EVIDENCE",
        "containment-v1: the A28 parts on this OS",
        "real generated Python attempting a host-secret read, a network fetch, a dependency "
        "install, final-set access and metadata mutation is denied at the enforced boundary; CPU, "
        "disk and output are bounded; code and attempts are preserved; at most two repairs",
        "every part exercised passed on this OS, through the job path and the OS sandbox: "
        "host-secret, network-fetch, dependency-install, final-set (a stand-in file), "
        "metadata-mutation, process, bounds (CPU, memory, wall time, output, scratch), preserved, "
        f"and the acceptance line ({said})",
        LIMIT,
        "the code was written by hand: model-generated code and its at most two repairs (D17) "
        "need the assistant of Sprint 5",
        "sealed final partitions do not exist until Sprint 9; a plain file stood for one",
        "the suite asks for a dedicated VM; this build runs an OS sandbox by owner decision "
        "(2026-10-01), so the assurance is os_sandbox_single_user",
        sprint=4,
        assurance=ASSURANCE,
    )
