"""The assistant in the harness: the workspace opens without the model and says so (R18)."""

import sys
import time
from pathlib import Path

import httpx
import pytest

from tests.conftest import Clock
from tests.integration.test_controls import say

Harness = tuple[httpx.Client, Clock]


def test_r18_the_workspace_opens_with_the_model_absent_and_shows_assistant_unavailable(
    harness: Harness,
) -> None:
    """R18, A30: no model, so the assistant is unavailable with the reason; everything else works.

    The state names the binding it would use (no secret, no path), the trail carries the
    unavailable event, an instruction is rejected as ASSISTANT_UNAVAILABLE with that reason, and
    a control phrase still answers on the fast path.
    """
    client, _ = harness
    for _ in range(100):
        shown = client.get("/v1/assistant").json()
        if shown["state"] == "unavailable" and shown["reason"] == "model missing":
            break
        time.sleep(0.05)
    assert (shown["state"], shown["reason"]) == ("unavailable", "model missing")
    assert shown["binding"]["id"] == "assistant-local-qwen"
    assert shown["binding"]["endpoint"]["api_key_ref"] == "secret://local/assistant-api-key"
    assert "/" not in shown["binding"]["model"]["local_path_ref"].split("://")[1]
    events = client.get("/v1/events").json()["events"]
    (unavailable,) = [e for e in events if e["type"] == "assistant.unavailable"]
    assert unavailable["body"]["reason"] == "model missing"
    assert not [e for e in events if e["type"] == "assistant.ready"]
    assert client.post("/v1/hardware").status_code == 200  # admission would otherwise refuse first
    told = say(client, "summarise the data")
    assert (told["operation"], told["state"], told["because"]) == (
        "instruction",
        "rejected",
        "model missing",
    )
    assert client.get("/v1/events").json()["events"][-1]["body"]["reason"] == "model missing"
    assert not [j for j in client.get("/v1/events").json()["events"] if j["type"] == "job.queued"]
    assert say(client, "status")["because"] == "no job is live"


@pytest.mark.slow
def test_r18_a_corrupt_or_absent_model_server_leaves_the_conversation_and_controls_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state_dir: Path, assistant: None
) -> None:
    """R18, A30: a right-sized file with other bytes is refused by its hash; a missing binary too.

    Each start says why, no server process exists, an instruction is rejected with that reason, a
    control phrase still answers, and no other model is tried (the binding stays the one).
    """
    import socket
    import threading

    import uvicorn

    from dsp.application.assistant import MODEL_BYTES
    from dsp.harness import workspace
    from dsp.harness.app import create_app

    models = tmp_path / "models"
    models.mkdir()
    with (models / "Qwen3-8B-Q4_K_M.gguf").open("wb") as sparse:
        sparse.truncate(MODEL_BYTES)
    for number, (binary, reason) in enumerate(
        (
            (tmp_path / "no-such-binary", "model server binary missing"),
            (Path(sys.executable), "model hash mismatch"),  # any file passes the binary check
        )
    ):
        monkeypatch.setenv("DSP_MODEL_DIR", str(models))
        monkeypatch.setenv("DSP_LLAMA_SERVER", str(binary))
        home = tmp_path / f"home-{number}"
        home.mkdir()
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        app = create_app("token", port)
        server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
        workspace.mount(app, home, server, Clock())
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            client = httpx.Client(
                base_url=f"http://127.0.0.1:{port}",
                headers={"Authorization": "Bearer token"},
                timeout=30,
            )
            for _ in range(600):
                try:
                    if client.get("/v1/assistant").json()["state"] == "unavailable":
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
            shown = client.get("/v1/assistant").json()
            assert (shown["state"], shown["reason"]) == ("unavailable", reason)
            assert shown["binding"]["id"] == "assistant-local-qwen"
            assert not (home / "assistant" / "server.pid").exists()
            assert client.post("/v1/hardware").status_code == 200
            told = say(client, "summarise the data")
            assert (told["state"], told["because"]) == ("rejected", reason)
            assert say(client, "status")["because"] == "no job is live"
            kinds = [e["type"] for e in client.get("/v1/events").json()["events"]]
            assert kinds.count("assistant.unavailable") == 1
            assert "assistant.ready" not in kinds
            time.sleep(2.5)  # two ticks: a verification failure is final, never started again
            kinds = [e["type"] for e in client.get("/v1/events").json()["events"]]
            assert kinds.count("assistant.unavailable") == 1
        finally:
            server.should_exit = True  # on a failed assertion too: live threads would hold pytest
            thread.join(30)


def test_r16_a_restart_of_the_harness_never_redispatches_a_committed_tool(
    state_dir: Path, tmp_path: Path
) -> None:
    """R16, A03: a harness dies mid-generation; the next one never redispatches the committed call.

    The next harness, on the same ledger, expires the lease and replays the committed call.

    Two real harnesses in this process on one state directory: the first's loop is held inside
    its second generation (the model "hangs"); the second runs attempt 2 on a clock 61 s later.
    """
    import socket
    import threading

    import uvicorn

    from dsp.adapters.ledger_sqlite import SqliteLedger
    from dsp.application.assistant import Assistant
    from dsp.contracts.errors import TrustedContext
    from dsp.harness import workspace
    from dsp.harness.app import create_app
    from tests.integration.test_assistant_loop import Scripted, call, calls, ended, text
    from tests.integration.test_jobs import until

    ctx = TrustedContext.local()
    stuck = threading.Event()

    started: list[uvicorn.Server] = []

    def serve(
        clock: Clock, gateway: Scripted
    ) -> tuple[httpx.Client, uvicorn.Server, threading.Thread]:
        assistant = Assistant(
            ctx,
            gateway,
            ledger=lambda: SqliteLedger(state_dir / "ledger.sqlite", clock),
            clock=clock,
        )
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        app = create_app("token", port)
        server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
        started.append(server)
        workspace.mount(app, state_dir, server, clock, assistant)
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        client = httpx.Client(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": "Bearer token"},
            timeout=30,
        )
        until(lambda: client.get("/v1/assistant").json()["state"] == "ready", 30)
        return client, server, thread

    first_clock = Clock()
    source = "open('out.json', 'w').write('1')"
    script_a = [
        call("write_code_artifact", language="python", source=source, repairs=None),
        call("request_trial", trial="never"),
    ]
    gateway_a = Scripted(script_a, lambda n: stuck.wait(120) if n == 2 else None)
    try:
        client_a, server_a, thread_a = serve(first_clock, gateway_a)
        assert client_a.post("/v1/hardware").status_code == 200
        answer = say(client_a, "write some code")
        job = answer["job"]["id"]
        until(
            lambda: (
                len(calls(state_dir, job)) == 1 and calls(state_dir, job)[0]["state"] == "committed"
            ),
            30,
        )
        until(
            lambda: len(gateway_a.shown) == 2, 30
        )  # the second generation is in progress and stuck
        server_a.should_exit = True  # the first harness is gone, mid-generation, lease held
        second_clock = Clock()
        second_clock.advance(61)
        gateway_b = Scripted([text("Done; one artifact was stored.")])
        client_b, server_b, thread_b = serve(second_clock, gateway_b)
        done = ended(client_b, job, 60)
        assert (done["state"], done["attempts"]) == ("succeeded", 2)
        recorded = calls(state_dir, job)
        assert [(c["n"], c["attempt"], c["tool"], c["state"]) for c in recorded] == [
            (1, 1, "write_code_artifact", "committed"),
            (2, 2, "answer", "committed"),
        ]
        dispatched = [
            e
            for e in client_b.get("/v1/events").json()["events"]
            if e["type"] == "assistant.call_dispatched"
        ]
        assert [(e["body"]["n"], e["body"]["tool"]) for e in dispatched] == [
            (1, "write_code_artifact")
        ]
        replayed = gateway_b.shown[0]
        assert [m["role"] for m in replayed] == ["system", "user", "assistant", "tool"]
        stored = {p.name for p in (state_dir / "store" / "cas" / "tenant-local").iterdir()}
        assert recorded[0]["result"]["artifact"].removeprefix("sha256:") in stored
        before = {p.name for p in (state_dir / "store" / "cas" / "tenant-local").iterdir()}
        stuck.set()  # the first harness's loop wakes: fenced out, it dispatches nothing
        time.sleep(1)
        dispatched = [
            e
            for e in client_b.get("/v1/events").json()["events"]
            if e["type"] == "assistant.call_dispatched"
        ]
        assert [(e["body"]["n"], e["body"]["tool"]) for e in dispatched] == [
            (1, "write_code_artifact")
        ]
        assert {p.name for p in (state_dir / "store" / "cas" / "tenant-local").iterdir()} == before
        server_b.should_exit = True
        thread_a.join(30)
        thread_b.join(30)
    finally:
        stuck.set()
        for server in started:
            server.should_exit = True  # on a failed assertion too: live threads would hold pytest
