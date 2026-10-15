"""The assistant behind one explicit AssistantModelBinding, and whether it is ready (R16, R18).

The workspace opens before any model loads; the assistant starts in the background and the
window shows ``assistant_unavailable`` with the reason until the server passed readiness. A
failure (model missing, hash mismatch, a crash, out of memory, a hang, a deadline) leaves the
conversation and the controls as they are and tries no other model: the binding is the only
one, selected explicitly, and a change of model is a new binding the owner selects.
"""

import logging
import threading
from collections.abc import Callable
from typing import Any

from dsp.application.grants import PROJECT
from dsp.contracts.canonical import pin
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.ports import Ledger, ModelGateway, ModelServer

BINDING_ID = "assistant-local-qwen"
MODEL_BYTES = 5_027_783_488
MODEL_SHA256 = "sha256:d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785"
LAUNCH = {"threads": 2, "gpu_layers": 99}  # the owner's D3 pick (2026-10-15): Metal full offload
AGGREGATE = "assistant:local"
RESTARTS = 3  # after a crash, a hang or a limit; never after a verification failure


def local_binding(
    ctx: TrustedContext, *, threads: int = 2, observed: dict[str, Any] | None = None
) -> dict[str, Any]:
    """The local open model's AssistantModelBinding 0.3.0 (the suite's schema and pins).

    A planning record until the server passed readiness; ``observed`` then carries the digests
    the supervisor measured (model, binary, chat template), and the record is stored.
    """
    seen = observed or {}
    profile = "assistant-local-metal-v1" if LAUNCH["gpu_layers"] else "assistant-local-cpu-v1"
    binding = {
        "schema_version": "0.3.0",
        "planning_only": not seen,
        "id": BINDING_ID,
        "revision": "1.0.0",
        "tenant_ref": ctx.tenant,
        "project_ref": PROJECT,
        "state": "proposed",
        "mode": "local_supervised",
        "profile_id": profile,
        "runtime": {
            "name": "llama.cpp",
            "release": "b11104",
            "source_revision": "217f81c266a7b7c986ee3d2c58e1cccee05a0744",
            "release_status": "prerelease_candidate",
            "observed_licence": "MIT",
            "revision_licence_status": "capture_pending",
            "binary_sha256": seen.get("binary_sha256"),
        },
        "model": {
            "repository": "Qwen/Qwen3-8B-GGUF",
            "revision": "7c41481f57cb95916b40956ab2f0b139b296d974",
            "filename": "Qwen3-8B-Q4_K_M.gguf",
            "quantisation": "Q4_K_M",
            "upstream_expected_sha256": MODEL_SHA256,
            "locally_verified_sha256": seen.get("model_sha256"),
            "observed_licence": "Apache-2.0",
            "revision_licence_status": "capture_pending",
            "local_path_ref": "local-model://qwen3-8b-q4-k-m",
        },
        "endpoint": {
            "host": "127.0.0.1",
            "port": 8081,
            "api_key_ref": "secret://local/assistant-api-key",
        },
        "template": {
            "sha256": seen.get("template_sha256"),
            "enable_thinking": False,
            "source": "pinned_model_metadata_or_reviewed_override",
        },
        "limits": {
            "context_tokens": 8192,
            "max_input_tokens": 6144,
            "max_output_tokens": 2048,
            "concurrent_generations": 1,
            "cpu_threads": threads,
            "model_memory_gib": 12,
            "generation_deadline_seconds": 300,
            "max_model_calls_per_task": 20,
            "max_code_repairs_per_task": 2,
            "max_generation_seconds_per_task": 1800,
            "max_external_charge_minor": 0,
            "currency": "GBP",
        },
        "decoding": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0},
        "privacy": {
            "network": "loopback_only",
            "prompt_content_logging": False,
            "automatic_downloads": False,
            "remote_fallback": False,
            "built_in_model_server_tools": False,
        },
        "operator_ref": ctx.principal,
        "payer_ref": ctx.principal,
        "qualification": {"status": "planned", "report_ref": None, "observed_hardware_ref": None},
    }
    validate("AssistantModelBinding", binding)
    return binding


class Assistant:
    """What the harness knows about its assistant: starting, ready, or unavailable and why."""

    def __init__(
        self,
        ctx: TrustedContext,
        server: ModelServer | None,
        *,
        ledger: Callable[[], Ledger],
        clock: Callable[[], str],
    ) -> None:
        self.ctx, self.server, self.ledger, self.clock = ctx, server, ledger, clock
        self.state = "unavailable"
        self.reason = "the assistant has not started" if server else "no model server is configured"
        self.binding = local_binding(ctx, threads=LAUNCH["threads"])
        self.failures = 0
        self.lock = threading.Lock()

    def start(self, proceed: Callable[[], bool] = lambda: True) -> None:
        """Start the server and record the outcome; never raises, the state says what happened."""
        with self.lock:
            if self.server is None:
                return
            self.state = "starting"
            try:
                observed = self.server.start(proceed)
            except DspError as error:
                self.state, self.reason = "unavailable", error.message
                verification = error.message.startswith(("model ", "model_"))
                self.failures = RESTARTS if verification else self.failures + 1
                self._record("assistant.unavailable", {"reason": error.message})
                return
            self.binding = local_binding(self.ctx, threads=LAUNCH["threads"], observed=observed)
            self.state, self.reason, self.failures = "ready", "", 0
            body = {"binding": pin(self.binding), "profile": self.binding["profile_id"]}
            body |= {key: observed[key] for key in ("model_sha256", "load_seconds")}
            self._record("assistant.ready", body, [("AssistantModelBinding", self.binding)])

    def _record(self, kind: str, body: dict[str, Any], objects: Any = ()) -> None:
        store = self.ledger()
        body |= {"at": self.clock()}
        seq = store.seq(self.ctx, AGGREGATE)
        try:
            store.commit(self.ctx, AGGREGATE, seq, f"assistant:{seq + 1}", kind, body, objects)
        except DspError as error:
            logging.getLogger(__name__).error("assistant event not recorded: %s", error.code)

    def watch(self) -> None:
        """The tick: a dead server (crash, limit, hang) is restarted a bounded number of times."""
        if self.state != "ready" or self.server is None or self.server.alive():
            return
        self.state, self.reason = "unavailable", "the model server stopped"
        self._record("assistant.unavailable", {"reason": self.reason})
        if self.failures < RESTARTS:
            self.failures += 1
            self.start()

    def gateway(self) -> ModelGateway:
        """The model, if the assistant is ready; otherwise ASSISTANT_UNAVAILABLE with the reason."""
        if self.state != "ready" or self.server is None:
            raise DspError(
                ErrorCode.ASSISTANT_UNAVAILABLE, self.reason or "the assistant is starting"
            )
        return self.server

    def shown(self) -> dict[str, Any]:
        """The state the window and the CLI show: no secret, no path."""
        return {"state": self.state, "reason": self.reason, "binding": self.binding}

    def stop(self) -> None:
        """Stop the server with the harness."""
        if self.server is not None:
            self.server.stop()
