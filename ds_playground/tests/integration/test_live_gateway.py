"""The real model server, supervised and confined, from start to the typed probe (live_model)."""

import json
import os
import stat
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from dsp.adapters import secrets
from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.adapters.llama_server import LlamaServer
from dsp.application.assistant import LAUNCH, MODEL_BYTES, Assistant, local_binding
from dsp.contracts.canonical import pin
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from tests.conftest import Clock
from tests.integration.conftest import Shared
from tests.unit.test_llama_server import Memory

pytestmark = pytest.mark.live_model
CTX = TrustedContext.local()
MODELS = Path(os.environ.get("DSP_LIVE_MODEL_DIR") or Path.home() / ".local/share/dsp/models")
LLAMA = Path(
    os.environ.get("DSP_LLAMA_SERVER")
    or Path.home() / ".local/share/dsp/llama.cpp/build/bin/llama-server"
)


def make(state: Path, store: Any = None, **launch: int) -> LlamaServer:
    """The real adapter on the real model and binary, with its state under ``state``."""
    return LlamaServer(
        local_binding(CTX, threads=LAUNCH["threads"]),
        model=MODELS / "Qwen3-8B-Q4_K_M.gguf",
        model_bytes=MODEL_BYTES,
        server=LLAMA,
        state=state,
        secrets=store or Memory(),
        **(LAUNCH | launch),
    )


def unbound(adapter: LlamaServer) -> LlamaServer:
    """Point the adapter at a port nothing holds and at a server that exits at once."""
    adapter.verify = lambda: ("sha256:" + "a" * 64, "sha256:" + "b" * 64)
    adapter.confined = lambda: ["/usr/bin/false"]
    adapter.binding["endpoint"]["port"] = 8099
    adapter.client = httpx.Client(base_url="http://127.0.0.1:8099", timeout=5)
    return adapter


def test_r16_the_server_is_ready_only_after_health_and_the_typed_probe(
    model_server: LlamaServer,
) -> None:
    """R16, R18: readiness is health plus a schema-valid tool call; the binding is then observed.

    The chat template, the model and the binary are pinned by measured digests; thinking is
    off; the key is in a 0600 file and in no process's arguments or environment; the slots,
    metrics and web UI endpoints are off; the log is not written.
    """
    seen = model_server.observed
    assert seen["model_sha256"] == local_binding(CTX)["model"]["upstream_expected_sha256"]
    assert seen["template_sha256"].startswith("sha256:")
    binding = local_binding(CTX, threads=LAUNCH["threads"], observed=seen)
    validate("AssistantModelBinding", binding)
    assert binding["planning_only"] is False
    key_file = model_server.state / "api-key"
    assert stat.S_IMODE(key_file.stat().st_mode) == 0o600
    key = key_file.read_text().strip()
    assert model_server.process is not None
    shown = subprocess.run(
        ["ps", "-ww", "-o", "command=", "-p", str(model_server.process.pid)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "--api-key-file" in shown
    assert key not in shown
    if sys.platform == "darwin":
        environment = subprocess.run(
            ["ps", "-ww", "-E", "-o", "command=", "-p", str(model_server.process.pid)],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        assert key not in environment
    client, headers = model_server.client, model_server.headers()
    assert client.get("/v1/models").status_code == 401
    assert client.get("/v1/models", headers=headers).status_code == 200
    assert client.get("/slots", headers=headers).status_code == 501
    assert client.get("/metrics", headers=headers).status_code == 501
    assert client.get("/", headers=headers).status_code == 404
    answer = model_server.complete(
        [{"role": "user", "content": "What is 7 times 8? Answer with the number only."}],
        [],
        max_tokens=16,
        deadline=60,
        seed=1,
        temperature=0,
    )
    assert "reasoning_content" not in answer["message"]
    assert "<think>" not in answer["message"]["content"]
    assert answer["message"]["content"].strip() == "56"
    assert model_server.count("load this CSV and show transit hours by service level") == 10
    assert not list(model_server.state.glob("*.log"))


def test_r16_a_missing_or_corrupt_model_is_refused_before_any_load(tmp_path: Path) -> None:
    """R16: model missing, a wrong size and a right-sized file with other bytes each refuse."""
    missing = make(tmp_path / "a")
    missing.model = tmp_path / "absent.gguf"
    with pytest.raises(DspError, match="model missing"):
        missing.start()
    short = tmp_path / "short.gguf"
    short.write_bytes(b"gguf")
    wrong_size = make(tmp_path / "b")
    wrong_size.model = short
    with pytest.raises(DspError, match="model size mismatch: 4 bytes"):
        wrong_size.start()
    sparse = tmp_path / "sparse.gguf"
    with sparse.open("wb") as handle:
        handle.truncate(MODEL_BYTES)
    tampered = make(tmp_path / "c")
    tampered.model = sparse
    started = time.monotonic()
    with pytest.raises(DspError) as refused:
        tampered.start()
    assert (refused.value.code, refused.value.message) == (
        ErrorCode.ASSISTANT_UNAVAILABLE,
        "model hash mismatch",
    )
    assert time.monotonic() - started < 60  # the cost of hashing 5 GB, measured below 3 s
    assert tampered.process is None


def test_r16_the_key_comes_from_the_secret_store_and_is_made_once(tmp_path: Path) -> None:
    """R16, C23: a stored key is reused; a missing one is generated and stored, never logged."""
    store = Memory()
    store.put("assistant-api-key", "owner-stored-key")
    adapter = unbound(make(tmp_path, store))
    with pytest.raises(DspError, match="exited with status 1"):
        adapter.start()
    assert adapter.key == "owner-stored-key"
    fresh = Memory()
    second = unbound(make(tmp_path / "second", fresh))
    with pytest.raises(DspError, match="exited with status 1"):
        second.start()
    assert fresh.held["assistant-api-key"] == second.key
    assert len(second.key) >= 32
    assert not (second.state / "api-key").exists()  # removed with the server


def test_r16_the_os_keychain_holds_the_real_key_on_this_os(tmp_path: Path) -> None:
    """R16: the OS's own store (a throwaway keychain here) answers the adapter's get and put."""
    if sys.platform == "darwin":
        keychain = tmp_path / "live.keychain-db"
        subprocess.run(
            ["/usr/bin/security", "create-keychain", "-p", "pw", str(keychain)], check=True
        )
        store: Any = secrets.Keychain(keychain, "pw")
    else:
        store = secrets.SecretService(tmp_path / "secrets")
    adapter = unbound(make(tmp_path / "home", store))
    with pytest.raises(DspError, match="exited with status 1"):
        adapter.start()
    assert store.get("assistant-api-key") == adapter.key


def test_a30_the_server_cannot_reach_out_and_the_denial_is_the_os_s(
    model_server: LlamaServer, tmp_path: Path, evidence: Callable[..., None]
) -> None:
    """A30, C14: under the server's own confinement an outbound connect is refused by the OS.

    A process run under the very profile (macOS) or the same namespaces (Linux) that confine
    the server tries to connect to a listener on this host and to resolve a name; both fail,
    while the server's own loopback listener keeps answering.
    """
    import socket

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import socket, json\n"
        "out = {}\n"
        "try:\n"
        f"    socket.create_connection(('127.0.0.1', {port}), timeout=2); out['connect'] = 'ok'\n"
        "except OSError as e: out['connect'] = f'{type(e).__name__} {e.errno}'\n"
        "try:\n"
        "    socket.getaddrinfo('example.com', 80); out['resolve'] = 'ok'\n"
        "except OSError as e: out['resolve'] = f'{type(e).__name__} {e.errno}'\n"
        "print(json.dumps(out))\n"
    )
    python = Path(sys.executable).resolve()
    if sys.platform == "darwin":
        profile = (model_server.state / "profile.sb").read_text()
        profile += f'\n(allow file-read* (subpath "{python.parents[1]}") (subpath "{tmp_path}"))'
        profile += f'\n(allow process-exec (literal "{python}"))\n'
        profile += (
            f'(allow file-read-metadata (subpath "{tmp_path}") (subpath "{python.parents[1]}"))\n'
        )
        (tmp_path / "probe.sb").write_text(profile)
        command = ["/usr/bin/sandbox-exec", "-f", str(tmp_path / "probe.sb"), str(python)]
    else:
        confined = model_server.confined()
        mounts = confined.index("--remount-ro")  # new binds go before the root is made read-only
        extra = ["--ro-bind", str(python.parents[1]), str(python.parents[1])]
        extra += ["--ro-bind", str(tmp_path), str(tmp_path)]
        until = len(confined) - 1 - confined[::-1].index("--")  # up to bwrap's own --
        command = [*confined[:mounts], *extra, *confined[mounts:until], "--", str(python)]
    done = subprocess.run(
        [*command, "-I", str(probe)], capture_output=True, text=True, check=False, timeout=60
    )
    listener.close()
    assert done.stdout, done.stderr[-800:]
    found = json.loads(done.stdout)
    evidence(
        "A30",
        "offline-start",
        "PASS" if found["connect"] != "ok" and found["resolve"] != "ok" else "FAIL",
        "the real model server under its own confinement, a loopback listener on another port",
        "the assistant starts and answers with third-party network denied by the OS, not by a flag",
        f"under the server's profile a connect to this host answered {found['connect']} and a name "
        f"lookup {found['resolve']}; the server's own listener kept answering",
        "the export without the assistant (the rest of A30) is Sprint 10",
        sprint=5,
    )
    assert found["connect"] != "ok", found
    assert found["resolve"] != "ok", found
    assert model_server.client.get("/health").status_code == 200
    assert model_server.alive()


@pytest.fixture
def assistant(model_server: LlamaServer, state_dir: Path) -> Assistant:
    """A harness's assistant on the session's server."""
    return Assistant(
        CTX,
        Shared(model_server),
        ledger=lambda: SqliteLedger(state_dir / "ledger.sqlite", Clock()),
        clock=Clock(),
    )


def test_r18_the_harness_reports_the_assistant_ready_and_stores_its_observed_binding(
    harness: tuple[httpx.Client, Clock], state_dir: Path
) -> None:
    """R18, R16: ready after the probe; the event pins the stored, observed binding."""
    client, _ = harness
    for _ in range(600):
        shown = client.get("/v1/assistant").json()
        if shown["state"] == "ready":
            break
        time.sleep(0.1)
    assert (shown["state"], shown["reason"]) == ("ready", "")
    binding = shown["binding"]
    assert binding["planning_only"] is False
    assert (
        binding["model"]["locally_verified_sha256"] == binding["model"]["upstream_expected_sha256"]
    )
    store = SqliteLedger(state_dir / "ledger.sqlite", Clock())
    stored = store.latest(CTX, "AssistantModelBinding", "assistant-local-qwen")
    assert stored == binding
    events = client.get("/v1/events").json()["events"]
    (ready,) = [e for e in events if e["type"] == "assistant.ready"]
    assert ready["body"]["binding"]["sha256"] == pin(binding)["sha256"]
    assert ready["body"]["model_sha256"] == binding["model"]["locally_verified_sha256"]


def test_d24_quitting_the_harness_stops_the_model_server_it_started(
    model_server: LlamaServer, state_dir: Path
) -> None:
    """D24, A44: the model server ends with the harness's quit; the key file goes with it.

    The session's server is lent to this harness with its real ``stop``, so this is the last
    test: one server at a time is all the Linux container's memory holds (decisions, 2026-10-15).
    """
    import socket
    import threading

    import uvicorn

    from dsp.harness import workspace
    from dsp.harness.app import create_app

    class Lent(Shared):
        def stop(self) -> None:
            """The harness's quit stops the real server."""
            self.server.stop()

    assistant = Assistant(
        CTX,
        Lent(model_server),
        ledger=lambda: SqliteLedger(state_dir / "ledger.sqlite", Clock()),
        clock=Clock(),
    )
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    app = create_app("token", port)
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    workspace.mount(app, state_dir, server, Clock(), assistant)
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    client = httpx.Client(
        base_url=f"http://127.0.0.1:{port}", headers={"Authorization": "Bearer token"}, timeout=30
    )
    for _ in range(300):
        try:
            if client.get("/v1/assistant").json()["state"] == "ready":
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    assert client.get("/v1/assistant").json()["state"] == "ready"
    assert model_server.process is not None
    pid = model_server.process.pid
    assert model_server.alive()
    assert client.post("/v1/shutdown").json() == {"status": "stopping"}
    thread.join(30)
    for _ in range(100):
        if model_server.process.poll() is not None:
            break
        time.sleep(0.1)
    assert model_server.process.poll() is not None, f"the model server {pid} outlived the harness"
    assert not (model_server.state / "api-key").exists()
    (state_dir / "harness.json").unlink(missing_ok=True)
