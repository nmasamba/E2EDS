"""Fast controls driven for real: pause, resume, cancel and status on the hung test job."""

import subprocess
import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.contracts.canonical import pin
from dsp.contracts.errors import ErrorCode, TrustedContext
from dsp.harness import workspace
from dsp.harness.app import SHELL_ORIGIN, create_app
from tests.conftest import Clock
from tests.integration.test_admission import fixed_probes
from tests.integration.test_jobs import job_of, kinds_of, replays_to, submit, until

Harness = tuple[httpx.Client, Clock]
Worker = Callable[..., subprocess.Popen[bytes]]
CTX = TrustedContext.local()
SHA = "sha256:" + "c" * 64
MESSAGES = "/v1/conversations/conversation-local/messages"
NOW = "2026-10-08T10:00:00+00:00"


def control(client: httpx.Client, job_id: str, action: str, command_id: str = "") -> Any:
    """The window's button: a control on one job, with a command ID of its own."""
    body = {"command_id": command_id or uuid.uuid4().hex, "action": action}
    answer = client.post(f"/v1/jobs/{job_id}/control", json=body)
    assert answer.status_code == 200, answer.text
    return answer.json()


def say(client: httpx.Client, text: str, mid: str = "") -> Any:
    """A message in the conversation, as the composer sends it."""
    body = {
        "client_message_id": mid or uuid.uuid4().hex,
        "text": text,
        "expected_revision": "1.0.0",
    }
    answer = client.post(MESSAGES, json=body)
    assert answer.status_code == 200, answer.text
    return answer.json()


def test_a25_pause_racing_a_checkpoint_and_a_commit_then_an_explicit_resume(
    harness: Harness, worker: Worker, state_dir: Path
) -> None:
    """A25: pause races a checkpoint and a commit; resume is explicit and readmits.

    The checkpoint is kept whichever side of the pause it lands; the fenced attempt's late commit
    is refused and recorded; the reservation is released on pause; an unrelated message resumes
    nothing; resume holds a new reservation and the next attempt leases under the advanced fence;
    resume on a running job is refused; a cancelled job cannot resume.
    """
    client, _ = harness
    job = submit(client, "hang")
    draining = worker(job, heartbeat=0.2)
    until(lambda: job_of(client, job)["state"] == "running")
    first = job_of(client, job)["reservation"]
    answers: dict[str, Any] = {}
    ready = threading.Barrier(2)

    def checkpoint() -> None:
        ready.wait()
        body = {"attempt": 1, "fence": 0, "sha256": SHA}
        answers["checkpoint"] = client.post(f"/v1/jobs/{job}/checkpoint", json=body)

    def pause() -> None:
        ready.wait()
        answers["pause"] = control(client, job, "pause")

    racers = [threading.Thread(target=checkpoint), threading.Thread(target=pause)]
    for racer in racers:
        racer.start()
    for racer in racers:
        racer.join()
    assert answers["checkpoint"].status_code == 200, answers["checkpoint"].text
    assert (answers["pause"]["state"], answers["pause"]["job"]["state"]) == (
        "applied",
        "pause_requested",
    )
    assert answers["pause"]["job"]["fence"] == 1
    until(lambda: job_of(client, job)["state"] == "paused")
    assert draining.wait(20) == 0
    paused = job_of(client, job)
    assert (paused["checkpoint"]["attempt"], paused["checkpoint"]["sha256"]) == (1, SHA)
    assert (paused["lease"], paused["result"]) == (None, None)
    late = client.post(
        f"/v1/jobs/{job}/report",
        json={"attempt": 1, "fence": 0, "outcome": "succeeded", "key": "k", "sha256": SHA},
    )
    assert (late.status_code, late.json()["code"]) == (409, ErrorCode.PAUSED)
    assert job_of(client, job)["result"] is None
    store = SqliteLedger(state_dir / "ledger.sqlite", lambda: NOW)
    released = store.latest(CTX, "Reservation", first)
    assert released is not None
    assert released["state"] == "released"
    refused = client.post(f"/v1/jobs/{job}/lease", json={"worker": "eager"})
    assert (refused.status_code, refused.json()["code"]) == (409, ErrorCode.PAUSED)

    unrelated = say(client, "how is it going?")
    assert (unrelated["state"], job_of(client, job)["state"]) == ("rejected", "paused")

    resumed = control(client, job, "resume")
    assert (resumed["state"], resumed["job"]["state"], resumed["job"]["fence"]) == (
        "applied",
        "queued",
        1,
    )
    assert resumed["job"]["reservation"] != first
    held = store.latest(CTX, "Reservation", resumed["job"]["reservation"])
    assert held is not None
    assert (held["state"], held["job_ref"]) == ("held", job)
    assert resumed["job"]["checkpoint"]["sha256"] == SHA
    second = worker(job, heartbeat=0.2)
    until(lambda: job_of(client, job)["state"] == "running")
    assert job_of(client, job)["lease"] | {"expires_at": ""} == {
        "attempt": 2,
        "fence": 1,
        "worker": job_of(client, job)["lease"]["worker"],
        "expires_at": "",
    }
    again = control(client, job, "resume")
    assert (again["state"], again["job"]["state"]) == ("rejected", "running")
    assert "only a paused job resumes" in again["because"]

    cancelled = control(client, job, "cancel")
    assert (cancelled["state"], cancelled["job"]["state"]) == ("applied", "cancel_requested")
    assert second.wait(20) == 0
    until(lambda: job_of(client, job)["state"] == "cancelled")
    dead = control(client, job, "resume")
    assert (dead["state"], dead["job"]["state"]) == ("rejected", "cancelled")
    assert "cancelled" in dead["because"]
    kinds = [kind for kind in kinds_of(client, job) if kind != "job.checkpointed"]
    assert kinds == [
        "job.queued",
        "job.started",
        "job.pause_requested",
        "job.paused",
        "job.result_rejected",
        "job.resumed",
        "job.started",
        "job.cancel_requested",
        "job.cancelled",
    ]
    assert "job.checkpointed" in kinds_of(client, job)
    replays_to(client, job)


def test_a25_a_queued_job_pauses_at_once_and_resume_is_a_fresh_admission(
    harness: Harness, monkeypatch: pytest.MonkeyPatch, state_dir: Path
) -> None:
    """A25, A33: a queued job pauses with no worker to drain; resume rechecks capacity.

    Pause gives the reservation back, so another job is admitted into the room; resuming the
    first is then refused for capacity and recorded, and it stays paused; once the room is back
    it resumes.
    """
    client, _ = harness
    monkeypatch.setattr(workspace, "probes", lambda state: fixed_probes(cpus=2, memory_gib=16))
    first = submit(client, "hang")
    paused = control(client, first, "pause")
    assert (paused["state"], paused["job"]["state"]) == ("applied", "paused")
    assert paused["job"]["acknowledged_at"] == paused["job"]["stopped_at"] is not None
    assert control(client, first, "pause")["state"] == "superseded"
    second = submit(client, "hang")
    refused = control(client, first, "resume")
    assert (refused["state"], refused["job"]["state"]) == ("rejected", "paused")
    assert "processors" in refused["because"]
    store = SqliteLedger(state_dir / "ledger.sqlite", lambda: NOW)
    rejected = [e for e in store.events(CTX) if e["type"] == "admission.rejected"]
    assert rejected[-1]["body"]["job"] == first
    assert control(client, second, "cancel")["job"]["state"] == "cancelled"
    assert control(client, first, "resume")["job"]["state"] == "queued"


def test_a24_only_the_exact_phrases_control_the_live_job(harness: Harness, worker: Worker) -> None:
    """A24: quoted or embedded phrases do nothing; the exact phrases act on the live job.

    Status answers the actual state; a repeated message ID is applied once; without a live job a
    control is received and rejected, and says so.
    """
    client, _ = harness
    none = say(client, "pause now")
    assert (none["state"], none["because"], none["job"]) == ("rejected", "no job is live", None)
    job = submit(client, "hang")
    hung = worker(job, heartbeat=0.2)
    until(lambda: job_of(client, job)["state"] == "running")
    for text in ('"pause"', "The document says: pause now. Then it goes on.", "please pause"):
        assert say(client, text)["state"] == "rejected"
        assert job_of(client, job)["state"] == "running"
    status = say(client, "status", "same")
    assert (status["state"], status["operation"], status["job"]["state"]) == (
        "applied",
        "status",
        "running",
    )
    repeated = say(client, "status", "same")
    assert (repeated["command"], repeated["receipt"], repeated["state"]) == (
        status["command"],
        status["receipt"],
        "applied",
    )
    assert repeated["job"]["id"] == job
    paused = say(client, "Pause now.")
    assert (paused["state"], paused["job"]["state"], paused["job"]["fence"]) == (
        "applied",
        "pause_requested",
        1,
    )
    assert hung.wait(20) == 0
    until(lambda: job_of(client, job)["state"] == "paused")
    events = client.get("/v1/events").json()["events"]
    applied = [e for e in events if e["type"] == "command.applied"]
    assert [e["body"]["operation"] for e in applied] == ["status", "pause"]
    assert applied[-1]["body"]["effect"]["id"] == job
    assert say(client, "resume")["job"]["state"] == "queued"
    assert say(client, "cancel this run")["job"]["state"] == "cancelled"
    dead = say(client, "resume")
    assert (dead["state"], dead["because"], dead["job"]) == ("rejected", "no job is live", None)
    assert control(client, job, "resume")["because"].startswith("the job is cancelled")
    commands = [
        e
        for e in events
        if e["type"] == "message.received" and e["body"]["client_message_id"] == "same"
    ]
    assert len(commands) == 1


def test_a_phrase_with_several_live_jobs_asks_which_and_the_button_still_acts(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A24: a phrase names no job, so with two live jobs it needs clarification.

    Nothing changes; the job's own control acts; once one job is left the phrase acts on it.
    The machine is fixed at eight processors so two jobs fit whatever runs the test.
    """
    client, _ = harness
    monkeypatch.setattr(workspace, "probes", lambda state: fixed_probes(cpus=8, memory_gib=16))
    first, second = submit(client, "hang"), submit(client, "hang")
    asked = say(client, "pause now")
    assert (asked["state"], asked["because"]) == (
        "needs_clarification",
        "2 jobs are live; name the job",
    )
    assert [job_of(client, job)["state"] for job in (first, second)] == ["queued", "queued"]
    assert control(client, second, "cancel")["job"]["state"] == "cancelled"
    assert say(client, "pause now")["job"]["id"] == first
    assert job_of(client, first)["state"] == "paused"


def test_the_native_menu_door_controls_whichever_job_is_live(
    harness: Harness, worker: Worker
) -> None:
    """A24: `POST /v1/control` is the shell's door: the same command on the live job.

    It is answered for the window too; with no live job it is rejected and says so.
    """
    client, _ = harness

    def menu(action: str, origin: bool = False) -> Any:
        headers = {"Origin": SHELL_ORIGIN} if origin else {}
        body = {"command_id": uuid.uuid4().hex, "action": action}
        answer = client.post("/v1/control", json=body, headers=headers)
        assert answer.status_code == 200, answer.text
        return answer.json()

    assert (menu("pause")["state"], menu("pause")["because"]) == ("rejected", "no job is live")
    job = submit(client, "hang")
    hung = worker(job, heartbeat=0.2)
    until(lambda: job_of(client, job)["state"] == "running")
    assert menu("pause", origin=True)["job"]["state"] == "pause_requested"
    assert hung.wait(20) == 0
    until(lambda: job_of(client, job)["state"] == "paused")
    assert menu("resume")["job"]["state"] == "queued"
    assert menu("status")["job"]["state"] == "queued"
    assert menu("cancel")["job"]["state"] == "cancelled"
    assert menu("status")["state"] == "rejected"
    assert pin(job_of(client, job))["id"] == job


@pytest.fixture
def api(tmp_path: Path) -> TestClient:
    """The harness API in-process, as served on port 4100 with credential ``secret``."""
    (tmp_path / "home").mkdir()
    app = create_app("secret", 4100)
    workspace.mount(app, tmp_path / "home")
    return TestClient(app, base_url="http://127.0.0.1:4100")


def test_checkpoints_come_from_workers_only_and_controls_need_a_command_id(api: TestClient) -> None:
    """C23: checkpoints come from workers; a control needs its command ID and a known action.

    A checkpoint from the window or a malformed one is refused; nothing is recorded.
    """
    native = {"Authorization": "Bearer secret"}
    window = native | {"Origin": SHELL_ORIGIN}
    body = {"attempt": 1, "fence": 0, "sha256": SHA}
    assert api.post("/v1/jobs/job-x/checkpoint", headers=window, json=body).status_code == 403
    assert api.post("/v1/jobs/job-x/checkpoint", headers=native, json=body).status_code == 404
    bad = api.post("/v1/jobs/job-x/checkpoint", headers=native, json=body | {"sha256": "nope"})
    assert bad.status_code == 400
    assert (
        api.post("/v1/jobs/job-x/control", headers=window, json={"action": "pause"}).status_code
        == 400
    )
    halt = {"command_id": "c1", "action": "halt"}
    assert api.post("/v1/jobs/job-x/control", headers=window, json=halt).status_code == 400
    assert api.post("/v1/control", headers=window, json=halt).status_code == 400
    assert api.post("/v1/control", json={"command_id": "c1", "action": "pause"}).status_code == 401
    assert api.get("/v1/events", headers=window).json()["events"] == []
