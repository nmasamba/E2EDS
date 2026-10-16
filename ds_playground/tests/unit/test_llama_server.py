"""The llama-server adapter: the launch contract as flags, the confinement, the checks first."""

import sys
from collections.abc import Iterator
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest

from dsp.adapters import llama_server
from dsp.adapters.llama_server import LlamaServer
from dsp.application.assistant import MODEL_SHA256, local_binding
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext

CTX = TrustedContext.local()


class Memory:
    """A secret store in memory: the adapter's tests are about the server, not the keychain."""

    def __init__(self) -> None:
        self.held: dict[str, str] = {}

    def get(self, account: str) -> str | None:
        """The value held, or None."""
        return self.held.get(account)

    def put(self, account: str, value: str) -> None:
        """Hold the value."""
        self.held[account] = value


def server(tmp_path: Path, model_bytes: int = 4, **launch: int) -> LlamaServer:
    """An adapter on files under tmp: a four-byte model and an empty binary."""
    (tmp_path / "model.gguf").write_bytes(b"gguf")
    (tmp_path / "llama-server").write_bytes(b"")
    return LlamaServer(
        local_binding(CTX),
        model=tmp_path / "model.gguf",
        model_bytes=model_bytes,
        server=tmp_path / "llama-server",
        state=tmp_path / "home",
        secrets=Memory(),
        **({"threads": 2, "gpu_layers": 0} | launch),
    )


def test_r16_the_launch_contract_maps_to_this_builds_flags_and_the_key_is_a_file(
    tmp_path: Path,
) -> None:
    """R16, D17: every contract key is a real flag; the key is a 0600 file, never an argument."""
    argv = server(tmp_path, threads=2, gpu_layers=99).argv()
    assert argv[0] == str(tmp_path / "llama-server")
    pairs = {flag: value for flag, value in pairwise(argv) if value[0] != "-"}
    assert (pairs["-c"], pairs["-np"], pairs["-t"], pairs["-ngl"]) == ("8192", "1", "2", "99")
    assert pairs["--reasoning"] == "off"
    assert pairs["--api-key-file"] == str(tmp_path / "home" / "assistant" / "api-key")
    for flag in ("--offline", "--no-webui", "--no-agent", "--no-slots", "--log-disable", "--jinja"):
        assert flag in argv
    assert not {"--tools", "--api-key"} & set(argv)
    if sys.platform == "darwin":
        assert (pairs["--host"], pairs["--port"]) == ("127.0.0.1", "8081")
    else:
        assert (pairs["--host"].endswith("llama.sock"), "--port" in pairs) == (True, False)


def test_a30_the_macos_profile_denies_by_default_and_allows_only_the_loopback_listener(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A30, C14: deny default; model and binary read-only; no outbound network; named sysctls."""
    adapter = server(tmp_path)
    monkeypatch.setattr(adapter, "libraries", lambda: [Path("/opt/lib/libssl.3.dylib")])
    profile = adapter.profile()
    lines = profile.splitlines()
    assert lines[:2] == ["(version 1)", "(deny default)"]
    assert f'(literal "{tmp_path / "model.gguf"}")' in profile
    assert f'(subpath "{tmp_path}")' in profile  # the binary's folder, read-only
    for absent in ("network-outbound", "(allow network*", "(allow sysctl-read)", "kern.proc"):
        assert absent not in profile, absent
    assert '(allow network-bind network-inbound (local ip "localhost:8081"))' in profile
    assert '(sysctl-name "hw.ncpu")' in profile
    assert f'(allow process-exec (literal "{tmp_path / "llama-server"}"))' in profile
    assert "(deny process-info*)" in profile
    assert "(allow process-info* (target self))" in profile
    assert "file-write*" not in profile.replace('file-write* (literal "/dev/null")', "")
    assert '"/opt/lib/libssl.3.dylib"' in profile
    assert '(literal "/opt/lib")' in profile


def test_a30_the_linux_vector_unshares_every_namespace_and_listens_on_a_socket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A30, C14: bubblewrap with every namespace new, the model read-only, memory by prlimit."""
    monkeypatch.setattr(llama_server.sys, "platform", "linux")
    monkeypatch.setattr(llama_server.shutil, "which", lambda name: f"/usr/bin/{name}")
    adapter = server(tmp_path)
    (tmp_path / "home" / "assistant" / "socket").mkdir(parents=True)
    argv = adapter.confined()
    assert argv[:3] == ["/usr/bin/prlimit", f"--as={12 * 2**30}", "--"]
    assert argv[3:6] == ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent"]
    assert "--share-net" not in argv
    model = str(tmp_path / "model.gguf")
    assert argv[argv.index(model) - 1] == "--ro-bind"
    assert argv[argv.index("--host") + 1] == str(tmp_path / "home" / "assistant" / "llama.sock")
    assert "--port" not in argv


def test_r16_size_and_hash_are_checked_before_any_load(tmp_path: Path) -> None:
    """R16: a missing model, a wrong size and a wrong digest each refuse before loading (S0)."""
    adapter = server(tmp_path, model_bytes=5)
    with pytest.raises(DspError) as size:
        adapter.verify()
    assert size.value.code is ErrorCode.ASSISTANT_UNAVAILABLE
    assert size.value.message == "model size mismatch: 4 bytes, 5 expected"
    right_size = server(tmp_path, model_bytes=4)
    with pytest.raises(DspError) as mismatch:
        right_size.verify()
    assert mismatch.value.message == "model hash mismatch"
    (tmp_path / "model.gguf").unlink()
    with pytest.raises(DspError) as missing:
        right_size.verify()
    assert missing.value.message == "model missing"
    assert MODEL_SHA256.startswith("sha256:d98cdcbd")


def test_r18_the_binding_is_a_planning_record_until_the_server_was_observed() -> None:
    """R18: the local binding validates; digests are null until measured, then pinned."""
    planned = local_binding(CTX)
    assert planned["planning_only"] is True
    assert planned["model"]["locally_verified_sha256"] is None
    assert planned["endpoint"] == {
        "host": "127.0.0.1",
        "port": 8081,
        "api_key_ref": "secret://local/assistant-api-key",
    }
    assert (planned["template"]["enable_thinking"], planned["privacy"]["remote_fallback"]) == (
        False,
        False,
    )
    seen: dict[str, Any] = {
        "model_sha256": MODEL_SHA256,
        "binary_sha256": "sha256:" + "b" * 64,
        "template_sha256": "sha256:" + "c" * 64,
    }
    observed = local_binding(CTX, threads=2, observed=seen)
    assert observed["planning_only"] is False
    assert observed["model"]["locally_verified_sha256"] == MODEL_SHA256
    assert observed["runtime"]["binary_sha256"] == seen["binary_sha256"]


def test_r16_a_port_held_by_another_process_is_refused_before_spawning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R16: something answering on the endpoint's port is never mistaken for our server."""
    import socket

    import httpx

    monkeypatch.setattr(llama_server.sys, "platform", "darwin")
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    adapter = server(tmp_path)
    adapter.verify = lambda: ("sha256:" + "a" * 64, "sha256:" + "b" * 64)
    adapter.binding["endpoint"]["port"] = port
    adapter.client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5)
    spawned: list[str] = []
    adapter.confined = lambda: spawned.append("spawned") or ["/usr/bin/false"]
    import threading

    def answer() -> None:
        connection, _ = listener.accept()
        connection.recv(1024)
        connection.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")
        connection.close()

    threading.Thread(target=answer, daemon=True).start()
    with pytest.raises(DspError, match=f"127.0.0.1:{port} is held by another process"):
        adapter.start()
    listener.close()
    assert spawned == []


def test_r16_a_stale_server_is_killed_by_its_pid_file_only_when_the_command_line_is_ours(
    tmp_path: Path,
) -> None:
    """R16, C14: the pid file names a process; it is killed only if it runs our server and model."""
    import subprocess
    import time

    adapter = server(tmp_path)
    adapter.state.mkdir(parents=True)
    other = subprocess.Popen(["/bin/sleep", "30"])
    (adapter.state / "server.pid").write_text(str(other.pid))
    adapter.stale()
    time.sleep(0.2)
    assert other.poll() is None, "a process that is not our server was killed"
    assert not (adapter.state / "server.pid").exists()
    other.kill()
    other.wait()
    (adapter.state / "server.pid").write_text("not-a-pid")
    adapter.stale()
    assert not (adapter.state / "server.pid").exists()


def test_r16_a_server_that_answers_health_but_fails_readiness_is_stopped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R16, R18: health is not readiness; a server that fails the probe is stopped, not kept."""
    import socket
    import time

    import httpx

    monkeypatch.setattr(llama_server.sys, "platform", "darwin")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    adapter = server(tmp_path)
    adapter.verify = lambda: ("sha256:" + "a" * 64, "sha256:" + "b" * 64)
    adapter.binding["endpoint"]["port"] = port
    adapter.client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5)
    fake = (
        "import http.server\n"
        "class H(http.server.BaseHTTPRequestHandler):\n"
        "    def do_GET(self):\n"
        "        code = 200 if self.path == '/health' else 401\n"
        "        self.send_response(code); self.send_header('Content-Length', '2')\n"
        "        self.end_headers(); self.wfile.write(b'{}')\n"
        "    def log_message(self, *a): pass\n"
        f"http.server.HTTPServer(('127.0.0.1', {port}), H).serve_forever()\n"
    )
    adapter.confined = lambda: [sys.executable, "-c", fake]
    adapter.footprint = lambda pid: 0  # the macOS poll, which Linux has no library for
    with pytest.raises(DspError, match="the server answered 401"):
        adapter.start()
    assert adapter.process is not None
    for _ in range(50):
        if adapter.process.poll() is not None:
            break
        time.sleep(0.1)
    assert adapter.process.poll() is not None, "the server was left running"
    assert not (tmp_path / "home" / "assistant" / "api-key").exists()


def test_r16_a_generation_that_keeps_streaming_past_the_deadline_is_stopped_as_a_hang() -> None:
    """R16, D17: the deadline bounds the whole generation, not the wait for the next chunk."""
    import time

    def slow() -> Iterator[str]:
        for _ in range(50):
            time.sleep(0.01)
            yield 'data: {"choices": [{"delta": {"content": "x"}}]}'

    with pytest.raises(TimeoutError):
        llama_server.assemble(slow(), None, time.monotonic() + 0.1)
    whole = llama_server.assemble(slow(), None, time.monotonic() + 60)
    assert (whole["message"]["content"], whole["stopped"]) == ("x" * 50, False)


def test_r16_the_confinement_names_real_paths_so_a_symlinked_profile_folder_still_works(
    tmp_path: Path,
) -> None:
    """R16, B26: the sandbox matches the kernel's path, so a symlinked folder is resolved first."""
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "link").symlink_to(real)
    adapter = server(tmp_path / "link")
    assert adapter.state == real / "home" / "assistant"
    assert (adapter.model, adapter.server) == (real / "model.gguf", real / "llama-server")
    confinement = adapter.profile() if sys.platform == "darwin" else " ".join(adapter.confined())
    assert str(real / "home" / "assistant") in confinement
    assert str(tmp_path / "link") not in confinement
