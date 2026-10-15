"""The local open model's server: llama.cpp's llama-server, verified, confined and supervised (B24).

The launch contract of ../local_model_runtime.md mapped to this build's flags (b11104, 0.4.1-dev,
each proven by a run): ``-c`` context, ``-np 1`` one slot, ``-t`` threads, ``-ngl`` GPU layers,
``--offline`` (no download), ``--no-webui``, ``--no-agent`` and no ``--tools`` (no built-in agent),
``--no-slots`` (the slots endpoint shows prompt content), ``--log-disable`` (no prompt logging),
``--reasoning off`` (thinking off), ``--jinja`` (tool calls), ``--api-key-file`` (a 0600 file: the
key is never in a child's arguments or environment, which any process of the owner's can read).

The server is its own process, confined by the OS, with egress denied by the OS and not by the
flag: on macOS a deny-by-default Seatbelt profile applied by ``sandbox-exec`` (read-only binary,
libraries and model; the loopback listener alone; no outbound network), on Linux bubblewrap with
every namespace new, so the listener is a UNIX socket in the state directory (a logged deviation
from ``127.0.0.1:8081``). Memory is bounded by ``prlimit`` on Linux and by polling the kernel's
footprint account on macOS (an exec drops a jetsam limit). Readiness is the health endpoint plus
a typed tool-response probe. A deadline passed, a dead process or a limit reached ends in
ASSISTANT_UNAVAILABLE; nothing else is tried.
"""

import contextlib
import ctypes
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx
from jsonschema import Draft202012Validator

from dsp.adapters.sandbox import chain
from dsp.contracts.canonical import digest
from dsp.contracts.errors import DspError, ErrorCode
from dsp.ports import SecretStore

ACCOUNT = "assistant-api-key"  # secret://local/assistant-api-key
LOAD_SECONDS = 300
PROBE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "report_ready",
        "description": "Report that you are ready and which model you are.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"ready": {"type": "boolean"}, "model": {"type": "string"}},
            "required": ["ready", "model"],
        },
    },
}
PROBE_MESSAGES: list[dict[str, str]] = [
    {"role": "system", "content": "You are a tool-calling assistant. Call the tool."},
    {"role": "user", "content": "Report that you are ready; the model is 'qwen3-8b'."},
]
SYSCTLS = (  # read by libSystem, Foundation, ggml and the server at start (measured by denial log)
    "hw.cpufamily",
    "hw.ephemeral_storage",
    "hw.logicalcpu",
    "hw.machine",
    "hw.memsize",
    "hw.ncpu",
    "hw.nperflevels",
    "hw.optional.AdvSIMD_HPFPCvt",
    "hw.optional.arm.FEAT_BF16",
    "hw.optional.arm.FEAT_DotProd",
    "hw.optional.arm.FEAT_FHM",
    "hw.optional.arm.FEAT_FP16",
    "hw.optional.arm.FEAT_I8MM",
    "hw.optional.arm.FEAT_SME",
    "hw.optional.arm.FEAT_SME2",
    "hw.optional.arm.FEAT_SVE",
    "hw.optional.armv8_2_sha3",
    "hw.optional.armv8_2_sha512",
    "hw.pagesize",
    "hw.pagesize_compat",
    "hw.perflevel0.logicalcpu",
    "hw.perflevel0.physicalcpu",
    "hw.perflevel1.logicalcpu",
    "hw.perflevel1.physicalcpu",
    "hw.physicalcpu",
    "kern.bootargs",
    "kern.hostname",
    "kern.osrelease",
    "kern.ostype",
    "kern.osvariant_status",
    "kern.osversion",
    "kern.version",
    "machdep.cpu.brand_string",
    "machdep.ptrauth_enabled",
    "security.mac.lockdown_mode_state",
    "sysctl.proc_translated",
)
SYSV = (
    "SYS_shmsys SYS_shmget SYS_shmat SYS_shmctl SYS_shmdt SYS_msgsys SYS_msgget SYS_msgsnd "
    "SYS_msgsnd_nocancel SYS_msgrcv SYS_msgrcv_nocancel SYS_msgctl SYS_semsys SYS_semget SYS_semop "
    "SYS_semctl"
)
LINUX_SYSTEM = [Path(p) for p in ("/usr/lib", "/usr/lib64", "/lib", "/lib64", "/etc/ld.so.cache")]


def _sb(kind: str, paths: Sequence[Path]) -> str:
    return " ".join(f"({kind} {json.dumps(str(p), ensure_ascii=False)})" for p in paths)


class LlamaServer:
    """Supervises one llama-server for one AssistantModelBinding and is its gateway."""

    def __init__(
        self,
        binding: Mapping[str, Any],
        *,
        model: Path,
        model_bytes: int,
        server: Path,
        state: Path,
        secrets: SecretStore,
        threads: int,
        gpu_layers: int,
    ) -> None:
        self.binding, self.model, self.server = dict(binding), model, server
        self.model_bytes = model_bytes
        self.state, self.secrets = state / "assistant", secrets
        self.threads, self.gpu_layers = threads, gpu_layers
        self.process: subprocess.Popen[bytes] | None = None
        self.failure: str | None = None
        self.key = ""
        endpoint = binding["endpoint"]
        self.socket = self.state / "llama.sock"
        if sys.platform == "darwin":
            self.client = httpx.Client(
                base_url=f"http://{endpoint['host']}:{endpoint['port']}", timeout=30
            )
        else:
            transport = httpx.HTTPTransport(uds=str(self.socket))
            self.client = httpx.Client(base_url="http://llama", transport=transport, timeout=30)

    def verify(self) -> tuple[str, str]:
        """Check the model's size and SHA-256 and hash the binary; raise before any load."""
        expected = self.binding["model"]["upstream_expected_sha256"]
        if not self.model.is_file():
            raise DspError(ErrorCode.ASSISTANT_UNAVAILABLE, "model missing")
        if not self.server.is_file():
            raise DspError(ErrorCode.ASSISTANT_UNAVAILABLE, "model server binary missing")
        size = self.model.stat().st_size
        if size != self.model_bytes:
            raise DspError(
                ErrorCode.ASSISTANT_UNAVAILABLE,
                f"model size mismatch: {size} bytes, {self.model_bytes} expected",
            )
        with self.model.open("rb") as handle:
            found = "sha256:" + hashlib.file_digest(handle, "sha256").hexdigest()
        if found != expected:
            raise DspError(ErrorCode.ASSISTANT_UNAVAILABLE, "model hash mismatch")
        with self.server.open("rb") as handle:
            binary = "sha256:" + hashlib.file_digest(handle, "sha256").hexdigest()
        return found, binary

    def argv(self) -> list[str]:
        """The launch contract as this build's flags; the key is a 0600 file, never an argument."""
        limits, endpoint = self.binding["limits"], self.binding["endpoint"]
        listen = ["--host", endpoint["host"], "--port", str(endpoint["port"])]
        if sys.platform != "darwin":
            listen = ["--host", str(self.socket)]
        return [
            str(self.server),
            "-m",
            str(self.model),
            *listen,
            "-c",
            str(limits["context_tokens"]),
            "-np",
            str(limits["concurrent_generations"]),
            "-t",
            str(self.threads),
            "-ngl",
            str(self.gpu_layers),
            "--offline",
            "--no-webui",
            "--no-agent",
            "--no-slots",
            "--log-disable",
            "--reasoning",
            "off",
            "--jinja",
            "--api-key-file",
            str(self.state / "api-key"),
        ]

    def libraries(self) -> list[Path]:
        """Every shared library the binary links outside the system and its own folder (otool)."""
        found = subprocess.run(
            ["/usr/bin/otool", "-L", str(self.server)], capture_output=True, text=True, check=True
        )
        paths = [line.split()[0] for line in found.stdout.splitlines()[1:] if line.strip()]
        outside = [Path(p) for p in paths if p.startswith("/") and not p.startswith("/usr/lib")]
        return [p for p in outside if not p.is_relative_to("/System")]

    def profile(self) -> str:
        """The macOS Seatbelt profile: deny by default; reads, the loopback listener, Metal."""
        endpoint = self.binding["endpoint"]
        reads = [self.server.parent.resolve(), Path("/usr/lib"), Path("/System/Library")]
        files = [self.model.resolve(), self.state / "api-key"]
        links = [link for lib in self.libraries() for link in chain(lib)]
        files += [link for link in links if not link.is_dir()]
        reads += [link for link in links if link.is_dir()]
        ancestors = {p for path in [*reads, *files] for p in path.parents}
        ancestors |= {Path("/var"), Path("/private/var"), Path("/System/Cryptexes/OS")}
        sysctls = " ".join(f"(sysctl-name {json.dumps(name)})" for name in SYSCTLS)
        return "\n".join(
            [
                "(version 1)",
                "(deny default)",
                f"(allow file-read* {_sb('subpath', reads)} {_sb('literal', files)})",
                '(allow file-read-data (literal "/"))',
                f"(allow file-read-metadata {_sb('literal', sorted(ancestors))})",
                '(allow file-read* file-write* (literal "/dev/null"))',
                f"(allow process-exec {_sb('literal', [self.server.resolve()])})",
                "(deny process-info*)",
                "(allow process-info* (target self))",
                f'(allow network-bind network-inbound (local ip "localhost:{endpoint["port"]}"))',
                f"(allow sysctl-read {sysctls})",
                f"(deny syscall-unix (syscall-number {SYSV}))",
                '(allow iokit-open (iokit-user-client-class "IOSurfaceRootUserClient")'
                ' (iokit-user-client-class "AGXDeviceUserClient"))',
                '(allow mach-lookup (global-name "com.apple.MTLCompilerService"))',
            ]
        )

    def confined(self) -> list[str]:
        """The fixed argument vector that starts the server confined on this OS."""
        argv = self.argv()
        if sys.platform == "darwin":
            (self.state / "profile.sb").write_text(self.profile())
            return ["/usr/bin/sandbox-exec", "-f", str(self.state / "profile.sb"), *argv]
        prlimit, bwrap = shutil.which("prlimit"), shutil.which("bwrap")
        if not (prlimit and bwrap):
            raise DspError(ErrorCode.ASSISTANT_UNAVAILABLE, "bubblewrap or prlimit is missing")
        limit = int(self.binding["limits"]["model_memory_gib"] * 2**30)
        wrapped = [prlimit, f"--as={limit}", "--", bwrap, "--unshare-all", "--die-with-parent"]
        wrapped += ["--new-session"]
        for path in LINUX_SYSTEM:
            if path.is_symlink():
                wrapped += ["--symlink", os.readlink(path), str(path)]
            elif path.exists():
                wrapped += ["--ro-bind", str(path), str(path)]
        binary = self.server.parent.resolve()
        for path in (binary, self.model.resolve()):
            wrapped += ["--ro-bind", str(path), str(path)]
        wrapped += ["--ro-bind", str(self.state / "api-key"), str(self.state / "api-key")]
        wrapped += ["--bind", str(self.state / "socket"), str(self.state / "socket")]
        wrapped += [
            "--dev",
            "/dev",
            "--remount-ro",
            "/",
            "--",
        ]  # no /proc: Docker forbids a fresh one
        return [*wrapped, *argv]

    def start(self, proceed: Callable[[], bool] = lambda: True) -> dict[str, Any]:
        """Verify, confine, start, wait for health and pass the typed probe; see ``ModelServer``."""
        self.failure = None
        model_sha, binary_sha = self.verify()
        self.state.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.stale()
        key = self.secrets.get(ACCOUNT)
        if key is None:
            key = secrets.token_urlsafe(32)
            self.secrets.put(ACCOUNT, key)
        self.key = key
        descriptor = os.open(self.state / "api-key", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            handle.write(key + "\n")
        if sys.platform != "darwin":
            self.socket = self.state / "socket" / "llama.sock"
            self.socket.parent.mkdir(mode=0o700, exist_ok=True)
            self.socket.unlink(missing_ok=True)
            transport = httpx.HTTPTransport(uds=str(self.socket))
            self.client = httpx.Client(base_url="http://llama", transport=transport, timeout=30)
        if sys.platform == "darwin":
            with contextlib.suppress(httpx.HTTPError):
                self.client.get("/health", timeout=2)
                endpoint = self.binding["endpoint"]
                raise DspError(
                    ErrorCode.ASSISTANT_UNAVAILABLE,
                    f"{endpoint['host']}:{endpoint['port']} is held by another process",
                )
        started = time.monotonic()
        self.process = subprocess.Popen(
            self.confined(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={},
            start_new_session=True,
        )
        (self.state / "server.pid").write_text(str(self.process.pid))
        while True:
            if not self.alive():
                self.stop()
                raise DspError(ErrorCode.ASSISTANT_UNAVAILABLE, self.failure or "server exited")
            if time.monotonic() - started > LOAD_SECONDS or not proceed():
                self.stop()
                raise DspError(ErrorCode.ASSISTANT_UNAVAILABLE, "the model did not load in time")
            try:
                if self.client.get("/health", timeout=5).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        load = time.monotonic() - started
        try:
            answer, template = self.probe()
        except DspError:
            self.stop()  # health answered, readiness did not: nothing of this server stays
            raise
        return {
            "model_sha256": model_sha,
            "binary_sha256": binary_sha,
            "template_sha256": digest(str(template).encode()) if template else None,
            "load_seconds": round(load, 1),
            "probe_usage": answer["usage"],
        }

    def probe(self) -> tuple[dict[str, Any], str | None]:
        """The typed tool-response probe and the chat template; raise unless both are right."""
        props = self.client.get("/props", headers=self.headers())
        if props.status_code != 200:
            raise DspError(
                ErrorCode.ASSISTANT_UNAVAILABLE, f"the server answered {props.status_code}"
            )
        template = props.json().get("chat_template")
        deadline = self.binding["limits"]["generation_deadline_seconds"]
        answer = self.complete(
            PROBE_MESSAGES, [PROBE_TOOL], max_tokens=128, deadline=deadline, seed=1, temperature=0
        )
        calls: list[dict[str, Any]] = answer["message"].get("tool_calls") or [{}]
        call = calls[0].get("function", {})
        schema = Draft202012Validator(PROBE_TOOL["function"]["parameters"])
        try:
            arguments = json.loads(call.get("arguments", ""))
        except ValueError:
            arguments = None
        if call.get("name") != "report_ready" or not schema.is_valid(arguments):
            raise DspError(ErrorCode.ASSISTANT_UNAVAILABLE, "the typed tool-response probe failed")
        if "reasoning_content" in answer["message"]:
            raise DspError(ErrorCode.ASSISTANT_UNAVAILABLE, "thinking is on; the binding says off")
        return answer, template

    def stale(self) -> None:
        """Kill a server a crashed harness left behind, by the pid file and only if it is ours."""
        pid_file = self.state / "server.pid"
        if not pid_file.is_file():
            return
        pid = pid_file.read_text().strip()
        if pid.isdigit():
            shown = subprocess.run(
                ["ps", "-ww", "-o", "command=", "-p", pid],
                capture_output=True,
                text=True,
                check=False,
            )
            if str(self.server) in shown.stdout and str(self.model) in shown.stdout:
                os.killpg(int(pid), 9) if sys.platform == "darwin" else os.kill(int(pid), 9)
                time.sleep(0.5)
        pid_file.unlink()

    def headers(self) -> dict[str, str]:
        """The key, held in this process's memory only."""
        return {"Authorization": f"Bearer {self.key}"}

    def alive(self) -> bool:
        """True while the process runs; on macOS also while its footprint is within the limit."""
        if self.process is None or self.process.poll() is not None:
            if self.process is not None and self.failure is None:
                self.failure = f"the model server exited with status {self.process.returncode}"
            return False
        if sys.platform == "darwin":
            from dsp.adapters.seatbelt import _Usage  # loads libSystem; macOS only

            usage = _Usage()
            system = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
            if system.proc_pid_rusage(self.process.pid, 0, ctypes.byref(usage)) == 0:
                limit = self.binding["limits"]["model_memory_gib"] * 2**30
                if usage.footprint > limit:
                    self.failure = "memory_limit: the model server exceeded its memory limit"
                    self.stop()
                    return False
        return True

    def stop(self) -> None:
        """Stop the server and its session; delete the key file."""
        if self.process is not None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(self.process.pid, 9)
            self.process.wait(30)
        (self.state / "api-key").unlink(missing_ok=True)
        (self.state / "server.pid").unlink(missing_ok=True)

    def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int,
        deadline: float,
        seed: int,
        temperature: float,
        stop: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        """One streamed chat completion within the deadline; past it the server is stopped (hung).

        The stream is read token by token so ``stop`` can end the generation between chunks
        (closing the stream cancels it on the server); a stop during prompt processing takes
        effect at the first chunk.
        """
        decoding = self.binding["decoding"]
        body: dict[str, Any] = {
            "messages": list(messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "seed": seed,
            "top_p": decoding["top_p"],
            "top_k": decoding["top_k"],
            "min_p": decoding["min_p"],
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            body["tools"] = list(tools)
        if not self.alive():
            raise DspError(ErrorCode.ASSISTANT_UNAVAILABLE, self.failure or "server not running")
        content, reasoning, finish, halted = "", False, None, False
        calls: dict[int, dict[str, Any]] = {}
        usage: dict[str, Any] = {}
        timings: dict[str, Any] = {}
        try:
            with self.client.stream(
                "POST", "/v1/chat/completions", json=body, headers=self.headers(), timeout=deadline
            ) as answer:
                if answer.status_code != 200:
                    raise DspError(
                        ErrorCode.ASSISTANT_UNAVAILABLE,
                        f"the model server answered {answer.status_code}",
                    )
                for line in answer.iter_lines():
                    if stop is not None and stop():
                        halted = True
                        break
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    chunk = json.loads(line[6:])
                    usage = chunk.get("usage") or usage
                    timings = chunk.get("timings") or timings
                    for choice in chunk.get("choices", []):
                        delta = choice.get("delta", {})
                        content += delta.get("content") or ""
                        reasoning = reasoning or "reasoning_content" in delta
                        for part in delta.get("tool_calls") or []:
                            slot = calls.setdefault(
                                part.get("index", 0),
                                {"id": "", "type": "function", "function": {}},
                            )
                            slot["id"] = part.get("id") or slot["id"]
                            function = slot["function"]
                            for key in ("name", "arguments"):
                                function[key] = function.get(key, "") + (
                                    part.get("function", {}).get(key) or ""
                                )
                        finish = choice.get("finish_reason") or finish
        except httpx.TimeoutException:
            self.failure = f"no answer within the {deadline:g} s generation deadline"
            self.stop()
            raise DspError(ErrorCode.ASSISTANT_UNAVAILABLE, self.failure) from None
        except httpx.HTTPError as error:
            raise DspError(
                ErrorCode.ASSISTANT_UNAVAILABLE,
                f"the model server did not answer ({type(error).__name__})",
            ) from None
        message: dict[str, Any] = {"role": "assistant", "content": content}
        if calls:
            message["tool_calls"] = [calls[index] for index in sorted(calls)]
        if reasoning:
            message["reasoning_content"] = ""  # its presence is what the probe refuses
        return {
            "message": message,
            "finish_reason": finish,
            "usage": usage,
            "timings": timings,
            "stopped": halted,
        }

    def count(self, text: str) -> int:
        """How many tokens the text is, by the server's own tokenizer."""
        answer = self.client.post("/tokenize", json={"content": text}, headers=self.headers())
        if answer.status_code != 200:
            raise DspError(ErrorCode.ASSISTANT_UNAVAILABLE, "the tokenizer did not answer")
        return len(answer.json()["tokens"])
