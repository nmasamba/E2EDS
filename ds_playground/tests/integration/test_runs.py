"""Sandboxed CodeTasks as fenced jobs, run for real by the harness's dispatcher and tick."""

import json
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from dsp.adapters import sandbox
from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.adapters.store_fs import ContentStore
from dsp.application import admission, jobs
from dsp.application.workloads import base_workload
from dsp.contracts.canonical import canonical_json, digest
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.harness import workspace
from dsp.harness.app import create_app
from tests.conftest import Clock
from tests.integration.test_admission import BINDING, new_id, observed
from tests.integration.test_jobs import control, job_of, kinds_of, replays_to, submit, until

pytestmark = pytest.mark.sandbox
CTX = TrustedContext.local()
ENDED = ("succeeded", "failed", "cancelled")
WRITE = "open('out.json', 'w').write('{\"n\": 1}')\n"
Harness = tuple[httpx.Client, Clock]


def queued(client: httpx.Client, code: str, **limits: int) -> str:
    """Queue ``code`` as a sandboxed Python job writing out.json, as `dsp run-task` would."""
    if client.get("/v1/hardware").status_code == 404:
        assert client.post("/v1/hardware").status_code == 200
    source = client.post("/v1/sources", json={"text": code}).json()["sha256"]
    task: dict[str, Any] = {"language": "python", "source_sha256": source, "outputs": ["out.json"]}
    task |= {"limits": limits} if limits else {}
    request = {"operation": "analyse", "idempotency_key": uuid.uuid4().hex, "task": task}
    answer = client.post("/v1/jobs", json=request)
    assert answer.status_code == 200, answer.text
    return str(answer.json()["id"])


def ended(client: httpx.Client, job: str) -> Any:
    """The job once it has ended."""
    until(lambda: job_of(client, job)["state"] in ENDED, 60)
    return job_of(client, job)


def stored(folder: Path) -> set[str]:
    """Every digest in the content store under ``folder``."""
    return {path.name for path in (folder / "store" / "cas").rglob("*") if path.is_file()}


def staged(folder: Path) -> list[str]:
    """Every attempt's staging folder that still exists under ``folder``."""
    return [path.name for path in (folder / "store" / "staging").glob("job-*")]


def admitted(store: SqliteLedger, content: ContentStore, clock: Clock, code: str) -> str:
    """Admit ``code`` as a sandboxed task straight through the application; return the job."""
    work = content.staging(new_id())
    (work / "source").write_text(code)
    task = {"language": "python", "source_sha256": content.commit(CTX, work / "source")}
    task["outputs"] = ["out.json"]
    job = admission.admit(
        CTX,
        "analyse",
        new_id(),
        task,
        workload=base_workload(CTX),
        binding=BINDING,
        ledger=store,
        store=content,
        clock=clock,
        new_id=new_id,
    )
    return str(job["id"])


def test_b26_a_sandboxed_task_is_a_fenced_job_whose_result_names_its_outputs(
    harness: Harness, state_dir: Path
) -> None:
    """B26, A28, D05: the dispatcher leases, runs and commits; the RunRecord names every output.

    The outputs reach the content store only with the committed result, the attempt's staging
    is gone, and the job's events replay to the stored job.
    """
    client, _ = harness
    job = ended(client, queued(client, WRITE))
    assert (job["state"], job["attempts"], job["reason"]) == ("succeeded", 1, None)
    cas = state_dir / "store" / "cas" / "tenant-local"
    record = json.loads((cas / job["result"]["sha256"].removeprefix("sha256:")).read_bytes())
    validate("RunRecord", record)
    assert digest(canonical_json(record)) == job["result"]["sha256"]
    (output,) = record["outputs"]
    assert (cas / output["sha256"].removeprefix("sha256:")).read_bytes() == b'{"n": 1}'
    assert (record["assurance"], record["attempt"]) == ("os_sandbox_single_user", 1)
    assert staged(state_dir) == []
    assert kinds_of(client, job["id"]) == ["job.queued", "job.started", "job.succeeded"]
    replays_to(client, job["id"])


def test_d21_a_result_over_the_size_cap_fails_the_job_and_nothing_is_ingested(
    harness: Harness, state_dir: Path
) -> None:
    """D21, D20: an output over the cap fails the job for good; no byte of it is stored."""
    client, _ = harness
    before = stored(state_dir)
    job = ended(
        client, queued(client, "open('out.json', 'wb').write(b'x' * 8192)\n", output_bytes=4096)
    )
    assert (job["state"], job["attempts"]) == ("failed", 1)
    assert job["reason"] == "output_limit: the outputs exceed 4096 bytes"
    assert len(stored(state_dir) - before) == 1  # the task's source; nothing it wrote
    assert staged(state_dir) == []


def test_a04_a_result_that_arrives_after_its_fence_moved_is_refused_and_leaves_nothing(
    tmp_path: Path, runner_env: Path
) -> None:
    """A04, A03: a run whose lease ran out before it reported cannot commit; nothing is kept.

    The run is real; only the interleaving is arranged: the lease runs out as the task finishes,
    so the reconcile tick fences the attempt before its result arrives.
    """
    clock = Clock()
    store, content = (
        SqliteLedger(tmp_path / "ledger.sqlite", clock),
        ContentStore(tmp_path / "store"),
    )
    observed(store)
    job_id = admitted(store, content, clock, WRITE)

    class Late(type(sandbox.local(runner_env))):
        """The real runner, after which the lease runs out before the result is reported."""

        def run(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            result: dict[str, Any] = super().run(*args, **kwargs)
            assert result["outcome"] == "succeeded"
            clock.advance(61)
            jobs.reconcile(CTX, ledger=store, clock=clock)
            return result

    before = stored(tmp_path)
    after = jobs.execute(
        CTX,
        job_id,
        ledger=store,
        store=content,
        runner=Late(runner_env),
        clock=clock,
        timer=time.monotonic,
    )
    assert (after["state"], after["fence"], after["result"]) == ("queued", 1, None)
    kinds = [event["type"] for event in store.events(CTX) if event["body"].get("job") == job_id]
    assert kinds[-2:] == ["job.expired", "job.result_rejected"]
    assert stored(tmp_path) == before
    assert staged(tmp_path) == []


def test_a07_a_task_cancelled_mid_run_is_killed_and_leaves_no_success_and_no_artifact(
    harness: Harness, state_dir: Path
) -> None:
    """A07, A03: cancel stops the sandboxed process within a heartbeat's look; what it wrote dies.

    The task has already written its output when it is killed: nothing reaches the store, the
    job ends cancelled with its stop recorded, and no staging is left.
    """
    client, _ = harness
    before = stored(state_dir)
    job = queued(client, WRITE + "import time\ntime.sleep(60)\n")
    until(lambda: job_of(client, job)["state"] == "running", 30)
    time.sleep(1)  # the output is written; the task sleeps
    asked = time.monotonic()
    control(client, job, "cancel")
    stopped = ended(client, job)
    assert time.monotonic() - asked < 10
    assert (stopped["state"], stopped["result"]) == ("cancelled", None)
    assert kinds_of(client, job)[-2:] == ["job.cancel_requested", "job.cancelled"]
    assert len(stored(state_dir) - before) == 1  # the task's source only
    assert staged(state_dir) == []
    replays_to(client, job)


@pytest.mark.slow
def test_d03_the_reconcile_tick_expires_a_dead_attempt_without_anything_touching_its_job(
    harness: Harness, worker: Any
) -> None:
    """D03, A04: a worker that died holding its lease is expired by the tick within one lease.

    Nothing reads the job between its lease running out and the expiry: only the event log is
    read, which reconciles nothing.
    """
    client, clock = harness
    job = submit(client, "hang")
    process = worker(job, "doomed", heartbeat=0)
    until(lambda: "job.started" in kinds_of(client, job))
    process.kill()
    process.wait(10)
    clock.advance(61)
    until(lambda: "job.expired" in kinds_of(client, job), 5)
    assert kinds_of(client, job) == ["job.queued", "job.started", "job.expired"]


def test_a03_a_crash_between_commit_and_promotion_is_finished_by_tidy(
    tmp_path: Path, runner_env: Path
) -> None:
    """A03: a crash after a result's commit and part-way through its storage is finished by tidy.

    The output had moved and the record had not: tidy counts the stored output as moved, stores
    the record, and clears a dead attempt's folder.
    """
    clock = Clock()
    store, content = (
        SqliteLedger(tmp_path / "ledger.sqlite", clock),
        ContentStore(tmp_path / "store"),
    )
    observed(store)
    job_id = admitted(store, content, clock, WRITE)

    class Crashing(ContentStore):
        """A store that fails once the outputs moved and before the record did: a power cut."""

        def commit(self, ctx: TrustedContext, path: Path) -> str:
            if path.name == "run.json":
                raise OSError("power cut")
            return super().commit(ctx, path)

    runner = sandbox.local(runner_env)
    with pytest.raises(OSError, match="power cut"):
        jobs.execute(
            CTX,
            job_id,
            ledger=store,
            store=Crashing(tmp_path / "store"),
            runner=runner,
            clock=clock,
            timer=time.monotonic,
        )
    job = store.latest(CTX, "Job", job_id)
    assert job is not None
    assert job["state"] == "succeeded"
    with pytest.raises(DspError):
        content.path(CTX, job["result"]["sha256"])  # committed, but not yet stored
    dead = content.staging(f"{job_id}.9")  # an attempt that never ran to the end
    jobs.tidy(CTX, ledger=store, store=content, runner=runner)
    record = json.loads(content.path(CTX, job["result"]["sha256"]).read_bytes())
    assert content.path(CTX, record["outputs"][0]["sha256"]).read_bytes() == b'{"n": 1}'
    assert not dead.exists()
    assert staged(tmp_path) == []


@pytest.mark.slow
def test_a04_an_attempt_fenced_mid_run_is_stopped_and_the_next_attempt_commits(
    harness: Harness, state_dir: Path
) -> None:
    """A04, D03: a lease that runs out mid-run stops the sandboxed task; a new attempt commits.

    The first attempt never reports: its fence moved, so it is stopped within a quarter of a
    second, and the dispatcher runs the job again under the new fence.
    """
    client, clock = harness
    job = queued(client, "import time\ntime.sleep(4)\n" + WRITE)
    until(lambda: job_of(client, job)["state"] == "running", 30)
    clock.advance(61)  # the tick expires the lease: the attempt is fenced while it sleeps
    final = ended(client, job)
    assert (final["state"], final["attempts"], final["fence"]) == ("succeeded", 2, 1)
    assert final["result"]["attempt"] == 2
    assert kinds_of(client, job) == [
        "job.queued",
        "job.started",
        "job.expired",
        "job.started",
        "job.succeeded",
    ]
    assert staged(state_dir) == []
    replays_to(client, job)


def test_b26_without_a_runner_environment_sandboxed_work_is_refused_not_run_otherwise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B26, R16: no runner environment means no Python or SQL task and no profile; nothing else.

    The refusal names what is missing; the test worker's jobs are still admitted.
    """
    monkeypatch.setenv("DSP_RUNNER_ENV", str(tmp_path / "absent"))
    app = create_app("secret", 4100)
    workspace.mount(app, tmp_path)
    api = TestClient(app, base_url="http://127.0.0.1:4100")
    headers = {"Authorization": "Bearer secret"}
    api.post("/v1/hardware", headers=headers)
    task = {"language": "python", "source_sha256": "sha256:" + "a" * 64, "outputs": ["out.json"]}
    request = {"operation": "analyse", "idempotency_key": "k1", "task": task}
    refused = api.post("/v1/jobs", headers=headers, json=request)
    assert (refused.status_code, refused.json()["code"]) == (503, "DEPENDENCY_UNAVAILABLE")
    assert "make runner-env" in refused.json()["message"]
    worker = request | {"idempotency_key": "k2", "task": {"cues": ["hang"], "seconds": 0}}
    assert api.post("/v1/jobs", headers=headers, json=worker).status_code == 200


def test_a03_an_output_changed_between_its_hash_and_its_storage_is_never_stored(
    tmp_path: Path, runner_env: Path
) -> None:
    """A03, D23: the bytes stored are the bytes hashed; staging changed after the run is refused.

    Tidy then sets the folder aside once instead of failing on it at every tick.
    """
    clock = Clock()
    store, content = (
        SqliteLedger(tmp_path / "ledger.sqlite", clock),
        ContentStore(tmp_path / "store"),
    )
    observed(store)
    job_id = admitted(store, content, clock, WRITE)

    class Tampered(type(sandbox.local(runner_env))):
        """The real runner, after which the staged output is changed."""

        def run(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            result: dict[str, Any] = super().run(*args, **kwargs)
            (args[3] / "out" / "out.json").write_text("tampered")
            return result

    before = stored(tmp_path)
    with pytest.raises(DspError) as raised:
        jobs.execute(
            CTX,
            job_id,
            ledger=store,
            store=content,
            runner=Tampered(runner_env),
            clock=clock,
            timer=time.monotonic,
        )
    assert raised.value.code is ErrorCode.INTERNAL_ERROR
    assert stored(tmp_path) == before  # neither the tampered bytes nor the record
    jobs.tidy(CTX, ledger=store, store=content, runner=sandbox.local(runner_env))
    jobs.tidy(CTX, ledger=store, store=content, runner=sandbox.local(runner_env))  # nothing left
    assert [p.name for p in (tmp_path / "store" / "staging").glob("job-*")] == [f"{job_id}.1.held"]
    assert stored(tmp_path) == before


def test_b26_a_runner_environment_others_could_write_or_a_frozen_guess_is_refused(
    tmp_path: Path, runner_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B26, C14: only an environment the owner alone can write runs tasks; frozen, none is guessed.

    A folder another user could write into would choose every task's interpreter; a frozen harness's
    source folder is a temporary unpack folder, so it uses only `DSP_RUNNER_ENV`.
    """
    shared = tmp_path / "shared-env"
    shutil.copytree(runner_env, shared, symlinks=True)
    shared.chmod(0o777)
    with pytest.raises(DspError) as raised:
        sandbox.local(shared)
    assert raised.value.message == "the runner environment is not the owner's alone"
    shared.chmod(0o755)
    sandbox.local(shared)  # the same environment, the owner's alone, is accepted

    monkeypatch.delenv("DSP_RUNNER_ENV", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    app = create_app("secret", 4100)
    (tmp_path / "home").mkdir()
    workspace.mount(app, tmp_path / "home")
    api = TestClient(app, base_url="http://127.0.0.1:4100")
    task = {"language": "python", "source_sha256": "sha256:" + "a" * 64, "outputs": ["out.json"]}
    request = {"operation": "analyse", "idempotency_key": "k1", "task": task}
    refused = api.post("/v1/jobs", headers={"Authorization": "Bearer secret"}, json=request)
    assert (refused.status_code, refused.json()["code"]) == (503, "DEPENDENCY_UNAVAILABLE")


def test_a04_no_outside_worker_can_lease_a_sandboxed_job(tmp_path: Path, runner_env: Path) -> None:
    """A04, B26: a sandboxed job runs only in the harness's sandbox; an outside worker is refused.

    Otherwise a process holding the token could lease it and report a success no sandbox ran.
    """
    app = create_app("secret", 4100)
    workspace.mount(app, tmp_path)  # no server, so no dispatcher: the job stays queued
    api = TestClient(app, base_url="http://127.0.0.1:4100")
    headers = {"Authorization": "Bearer secret"}
    api.post("/v1/hardware", headers=headers)
    source = api.post("/v1/sources", headers=headers, json={"text": WRITE}).json()["sha256"]
    task = {"language": "python", "source_sha256": source, "outputs": ["out.json"]}
    request = {"operation": "analyse", "idempotency_key": "k1", "task": task}
    job = api.post("/v1/jobs", headers=headers, json=request).json()["id"]
    leased = api.post(f"/v1/jobs/{job}/lease", headers=headers, json={"worker": "outsider"})
    assert (leased.status_code, leased.json()["code"]) == (403, "FORBIDDEN")
    assert api.get(f"/v1/jobs/{job}", headers=headers).json()["state"] == "queued"
