"""The assistant in the harness: the workspace opens without the model and says so (R18)."""

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
    for number, (variable, reason) in enumerate(
        (("DSP_LLAMA_SERVER", "model server binary missing"), ("", "model hash mismatch"))
    ):
        monkeypatch.setenv("DSP_MODEL_DIR", str(models))
        if variable:
            monkeypatch.setenv(variable, str(tmp_path / "no-such-binary"))
        else:
            monkeypatch.delenv("DSP_LLAMA_SERVER", raising=False)
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
        server.should_exit = True
        thread.join(30)
