import json
import logging
import os
import sys
import threading
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import uuid4

import uvicorn
from fastapi import Body, Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse

from dsp.adapters import export_fs, sandbox, secrets
from dsp.adapters.discovery import host, probes
from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.adapters.llama_server import LlamaServer
from dsp.adapters.store_fs import ContentStore
from dsp.application import admission, controls, conversation, jobs
from dsp.application.assistant import LAUNCH, MODEL_BYTES, Assistant
from dsp.application.assistant import local_binding as assistant_binding
from dsp.application.discovery import discover
from dsp.application.grants import grant_folder, resolve, revoke, summary
from dsp.application.packs import export_profile, submit_profile
from dsp.application.planning import local_binding, propose_plan
from dsp.application.workloads import current_workload
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext

STATUS = (
    {
        ErrorCode.INPUT_INVALID: 400,
        ErrorCode.FORBIDDEN: 403,
        ErrorCode.NOT_FOUND: 404,
    }
    | dict.fromkeys(
        (
            ErrorCode.IDEMPOTENCY_CONFLICT,
            ErrorCode.REVISION_CONFLICT,
            ErrorCode.PAUSED,
            ErrorCode.PAUSE_REQUESTED,
            ErrorCode.CANCEL_REQUESTED,
            ErrorCode.CANCELLED,
        ),
        409,
    )
    | {
        ErrorCode.QUOTA_EXCEEDED: 429,
        ErrorCode.DEPENDENCY_UNAVAILABLE: 503,
        ErrorCode.ASSISTANT_UNAVAILABLE: 503,
        ErrorCode.REQUIRES_CONFIRMATION: 409,
    }
)

MESSAGE_FIELDS = {"client_message_id", "text", "expected_revision"}
MAX_SOURCE = 2**20  # a task's source text
ENDED = ("succeeded", "failed", "cancelled")
MODELS = Path.home() / ".local" / "share" / "dsp" / "models"
LLAMA = Path.home() / ".local" / "share" / "dsp" / "llama.cpp" / "build" / "bin" / "llama-server"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _id() -> str:
    return uuid4().hex


def mount(
    app: FastAPI,
    state_dir: Path,
    server: uvicorn.Server | None = None,
    clock: Callable[[], str] = _now,
    assistant: Assistant | None = None,
) -> None:
    """Add the workspace routes: grants, profiling, discovery, planning, events and jobs.

    Every caller is the local owner, established by the token the guard has already checked;
    nothing in a request body is treated as authority. ``server`` is the running server, whose
    shutdown ends open event streams and the background work, the reconcile tick every second and
    the dispatcher, which runs queued sandboxed jobs one at a time; a quit lets a job already
    running finish (D24). ``clock`` is the one source
    of time for the ledger and the job coordinator. The runner environment is ``DSP_RUNNER_ENV``,
    or ``.runner-env`` beside the source when the harness runs from source (a frozen harness has
    only the variable); without it, or without the OS's sandbox, sandboxed work is refused, never
    run another way. The assistant's model server (``DSP_LLAMA_SERVER``) and model
    (``DSP_MODEL_DIR``) default to ``~/.local/share/dsp``; the assistant starts after the
    workspace is up and stops with the harness, and the workspace opens whether or not the model
    is there (R18). A test may pass a started ``assistant``.
    """
    ctx = TrustedContext.local()
    binding = local_binding(ctx, *host())
    if assistant is None:
        model = Path(os.environ.get("DSP_MODEL_DIR") or MODELS) / "Qwen3-8B-Q4_K_M.gguf"
        llama = LlamaServer(
            assistant_binding(ctx, threads=LAUNCH["threads"]),
            model=model,
            model_bytes=MODEL_BYTES,
            server=Path(os.environ.get("DSP_LLAMA_SERVER") or LLAMA),
            state=state_dir,
            secrets=secrets.local(state_dir),
            threads=LAUNCH["threads"],
            gpu_layers=LAUNCH["gpu_layers"],
        )
        assistant = Assistant(ctx, llama, ledger=lambda: ledger(), clock=clock)
    beside = None if getattr(sys, "frozen", False) else Path(__file__).parents[3] / ".runner-env"
    named = os.environ.get("DSP_RUNNER_ENV")
    environment = Path(named) if named else beside  # a frozen harness has no source beside it
    runner: sandbox.Confined | None = None
    lock, unavailable = None, "the runner environment is not built (make runner-env)"
    if environment and (environment / "bin" / "python").exists():
        try:
            runner, lock = sandbox.local(environment), sandbox.lock(environment)
        except DspError as error:
            unavailable = error.message
    executing = threading.Lock()  # one sandboxed attempt at a time, as the binding allows

    def ledger() -> SqliteLedger:
        return SqliteLedger(state_dir / "ledger.sqlite", clock)

    def sandboxed() -> sandbox.Confined:
        if runner is None:
            raise DspError(ErrorCode.DEPENDENCY_UNAVAILABLE, unavailable)
        return runner

    def running() -> bool:
        return not (server and server.should_exit)

    def execute(job_id: str) -> dict[str, Any]:
        """Run one queued sandboxed job here, or wait for whoever leased it first to finish it."""
        with executing:
            store = ledger()
            try:
                return jobs.execute(
                    ctx,
                    job_id,
                    ledger=store,
                    store=ContentStore(state_dir / "store"),
                    runner=sandboxed(),
                    clock=clock,
                    timer=time.monotonic,
                )
            except DspError as error:
                if error.code is not ErrorCode.REVISION_CONFLICT:
                    raise
            job = jobs.inspect(ctx, job_id, ledger=store, clock=clock)
        while job["state"] not in ENDED:
            time.sleep(0.1)
            job = jobs.inspect(ctx, job_id, ledger=ledger(), clock=clock)
        return job

    def dispatch() -> None:
        """Finish or clear what a crash left, then run the oldest queued sandboxed job."""
        store = ledger()
        with executing:
            jobs.tidy(
                ctx, ledger=store, store=ContentStore(state_dir / "store"), runner=sandboxed()
            )
        queued = [job for job in store.current(ctx, "Job") if job["state"] == "queued"]
        queued = [job for job in queued if job["task"] is None]
        if queued:
            execute(min(queued, key=lambda job: str(job["submitted_at"]))["id"])

    def every(seconds: float, work: Callable[[], object]) -> None:
        """Run ``work`` every ``seconds`` while the server runs; a failure is logged, not fatal."""

        def loop() -> None:
            while running():
                try:
                    work()
                except Exception as error:
                    name = getattr(work, "__name__", "work")
                    logging.getLogger(__name__).error("%s failed: %s", name, type(error).__name__)
                time.sleep(seconds)

        threading.Thread(target=loop).start()  # not a daemon: a quit drains what it is doing

    def supervise() -> None:
        """Start the assistant once the workspace is up; watch it; stop it with the harness."""
        assistant.start(running)
        while running():
            assistant.watch()
            time.sleep(1)
        assistant.stop()

    if server is not None:
        every(1.0, lambda: jobs.reconcile(ctx, ledger=ledger(), clock=clock))
        if runner is not None:
            every(0.25, dispatch)
        threading.Thread(target=supervise).start()  # not a daemon: a quit stops the model server

    def native(request: Request) -> None:
        """A lease, a heartbeat or a report comes from a worker process, never from the window."""
        if "origin" in request.headers:
            raise DspError(ErrorCode.FORBIDDEN, "accepted from the shell, the CLI or a worker only")

    @app.exception_handler(DspError)
    async def refused(request: Request, error: DspError) -> JSONResponse:
        body = {"code": error.code, "message": error.message}
        return JSONResponse(body, STATUS.get(error.code, 500))

    @app.exception_handler(RequestValidationError)
    async def malformed(request: Request, error: RequestValidationError) -> JSONResponse:
        body = {"code": ErrorCode.INPUT_INVALID, "message": "the request body is not valid"}
        return JSONResponse(body, 400)

    @app.post("/v1/grants")
    def create_grant(
        request: Request, purpose: Annotated[str, Body()], path: Annotated[str, Body()]
    ) -> dict[str, str]:
        if "origin" in request.headers:
            raise DspError(ErrorCode.FORBIDDEN, "a path is accepted from the shell or CLI only")
        granted = grant_folder(ctx, Path(path), purpose, ledger=ledger(), clock=_now, new_id=_id)
        return summary(granted)

    @app.get("/v1/grants")
    def list_grants() -> dict[str, list[dict[str, str]]]:
        grants = ledger().current(ctx, "FolderGrant")
        return {"grants": [summary(grant) for grant in grants if grant["state"] == "active"]}

    @app.post("/v1/grants/{handle}/revoke")
    def revoke_grant(handle: str) -> dict[str, str]:
        return summary(revoke(ctx, handle, ledger=ledger()))

    @app.post("/v1/hardware")
    def discover_hardware() -> dict[str, Any]:
        snapshot = discover(
            ctx, probes(state_dir), ledger=ledger(), clock=_now, new_id=_id, timer=time.monotonic
        )
        propose_plan(ctx, binding=binding, ledger=ledger(), new_id=_id)
        return snapshot

    @app.get("/v1/hardware")
    def latest_hardware() -> dict[str, Any]:
        snapshots = ledger().current(ctx, "HardwareSnapshot")
        if not snapshots:
            raise DspError(ErrorCode.NOT_FOUND, "nothing has been discovered yet")
        return snapshots[-1]

    @app.post("/v1/plan")
    def create_plan() -> dict[str, Any]:
        return propose_plan(ctx, binding=binding, ledger=ledger(), new_id=_id)

    @app.get("/v1/plan")
    def latest_plan() -> dict[str, Any]:
        plans = ledger().current(ctx, "WorkflowPlan")
        if not plans:
            raise DspError(ErrorCode.NOT_FOUND, "no plan has been proposed yet")
        return plans[-1]

    def changes(after: int) -> dict[str, Any]:
        """Events after a cursor; a cursor this ledger never issued gets the whole history."""
        fresh, reset = ledger().events(ctx, after), False
        if after and not fresh:
            history = ledger().events(ctx)
            if not history or history[-1]["seq"] < after:
                fresh, reset = history, True
        shown = [
            {key: event[key] for key in ("seq", "event_id", "type", "recorded_at", "body")}
            for event in fresh
        ]
        cursor = fresh[-1]["seq"] if fresh else 0 if reset else after
        return {"events": shown, "cursor": cursor, "reset": reset}

    @app.get("/v1/events")
    def poll_events(after: Annotated[int, Query(ge=0)] = 0) -> dict[str, Any]:
        return changes(after)

    @app.get("/v1/events/stream")
    def stream_events(after: Annotated[int, Query(ge=0)] = 0) -> StreamingResponse:
        def frames() -> Iterator[str]:
            cursor, quiet = after, 0.0
            while not (server and server.should_exit):
                batch = changes(cursor)
                cursor = batch["cursor"]
                if batch["reset"]:
                    yield "event: stream.resynchronised\ndata: {}\n\n"
                for event in batch["events"]:
                    data = json.dumps(event)
                    yield f"id: {event['seq']}\nevent: {event['type']}\ndata: {data}\n\n"
                if not batch["events"]:
                    time.sleep(0.25)
                    quiet += 0.25
                if quiet >= 5:
                    quiet = 0.0
                    yield ": keep-alive\n\n"

        return StreamingResponse(frames(), media_type="text/event-stream")

    @app.post("/v1/shutdown")
    def shutdown(request: Request) -> dict[str, str]:
        """Stop the harness once the requests already in progress have finished (explicit Quit)."""
        if "origin" in request.headers or server is None:
            raise DspError(ErrorCode.FORBIDDEN, "only the shell or the CLI may stop the harness")
        server.should_exit = True
        return {"status": "stopping"}

    @app.post("/v1/profiles")
    def create_profile(
        source_handle: Annotated[str, Body()],
        relative_path: Annotated[str, Body()],
        output_handle: Annotated[str, Body()],
    ) -> dict[str, Any]:
        """Profile a granted CSV as a sandboxed job the trail follows, then export its pack."""
        store, content = ledger(), ContentStore(state_dir / "store")
        sandboxed()
        resolve(ctx, output_handle, ".", "output_root", ledger=store)  # before any capture
        if not store.current(ctx, "HardwareSnapshot"):
            discover_hardware()  # nothing is admitted blind; a first profile observes first
        job, data = submit_profile(
            ctx,
            source_handle,
            relative_path,
            ledger=store,
            store=content,
            workload=current_workload(ctx, store),
            binding=binding,
            environment=lock,
            clock=clock,
            new_id=_id,
        )
        job = execute(job["id"])
        if job["state"] != "succeeded":
            raise DspError(ErrorCode.INPUT_INVALID, str(job["reason"] or f"the job {job['state']}"))
        receipt = export_profile(
            ctx,
            job,
            data,
            output_handle,
            ledger=store,
            store=content,
            exporter=export_fs,
            clock=_now,
            new_id=_id,
        )
        return {"version": receipt["version"], "files": len(receipt["files"])}

    @app.post("/v1/sources", dependencies=[Depends(native)])
    def store_source(
        text: Annotated[str, Body(embed=True, max_length=MAX_SOURCE)],
    ) -> dict[str, str]:
        """Keep a task's source text in the content store; a job names it by digest."""
        content = ContentStore(state_dir / "store")
        work = content.staging(_id())
        (work / "source").write_text(text)
        stored = content.commit(ctx, work / "source")
        content.discard(work)
        return {"sha256": stored}

    @app.post("/v1/jobs")
    def submit_job(
        operation: Annotated[
            Literal["train", "evaluate", "optimise", "simulate", "infer", "prepare", "analyse"],
            Body(),
        ],
        idempotency_key: Annotated[str, Body(min_length=1, max_length=160)],
        task: Annotated[dict[str, Any], Body()],
    ) -> dict[str, Any]:
        store = ledger()
        if "language" in task:
            sandboxed()
        return admission.admit(
            ctx,
            operation,
            idempotency_key,
            task,
            workload=current_workload(ctx, store),
            binding=binding,
            ledger=store,
            store=ContentStore(state_dir / "store"),
            clock=clock,
            new_id=_id,
            environment=lock,
        )

    @app.get("/v1/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, Any]:
        return jobs.inspect(ctx, job_id, ledger=ledger(), clock=clock)

    @app.post("/v1/jobs/{job_id}/lease", dependencies=[Depends(native)])
    def lease_job(job_id: str, worker: Annotated[str, Body(embed=True)]) -> dict[str, Any]:
        if jobs.inspect(ctx, job_id, ledger=ledger(), clock=clock)["task"] is None:
            raise DspError(
                ErrorCode.FORBIDDEN, "a sandboxed job runs only in the harness's sandbox"
            )
        return jobs.lease(ctx, job_id, worker, ledger=ledger(), clock=clock)

    @app.post("/v1/jobs/{job_id}/heartbeat", dependencies=[Depends(native)])
    def heartbeat(
        job_id: str, attempt: Annotated[int, Body()], fence: Annotated[int, Body()]
    ) -> dict[str, Any]:
        return jobs.heartbeat(ctx, job_id, attempt, fence, ledger=ledger(), clock=clock)

    @app.post("/v1/jobs/{job_id}/report", dependencies=[Depends(native)])
    def report(
        job_id: str,
        attempt: Annotated[int, Body()],
        fence: Annotated[int, Body()],
        outcome: Annotated[Literal["succeeded", "failed", "stopped"], Body()],
        charge_minor: Annotated[int, Body(ge=0)] = 0,
        key: Annotated[str | None, Body()] = None,
        sha256: Annotated[str | None, Body()] = None,
        transient: Annotated[bool, Body()] = False,
        reason: Annotated[str, Body(max_length=200)] = "",
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {"charge_minor": charge_minor}
        if outcome == "succeeded":
            fields |= {"key": key, "sha256": sha256}
        if outcome == "failed":
            fields |= {"transient": transient, "reason": reason}
        return jobs.report(
            ctx, job_id, attempt, fence, outcome, ledger=ledger(), clock=clock, **fields
        )

    @app.get("/v1/workload")
    def latest_workload() -> dict[str, Any]:
        return current_workload(ctx, ledger())

    @app.get("/v1/assistant")
    def assistant_state() -> dict[str, Any]:
        """Whether the assistant is ready, and its binding; never a secret or a path."""
        return assistant.shown()

    @app.post("/v1/conversations/{conversation_id}/messages")
    async def post_message(conversation_id: str, request: Request) -> dict[str, Any]:
        """D18: the body is bounded in bytes as it arrives, before parsing; three fields only."""
        too_large = DspError(ErrorCode.INPUT_INVALID, "the message is larger than 16 KiB")
        if int(request.headers.get("content-length") or 0) > conversation.MAX_BYTES:
            raise too_large
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > conversation.MAX_BYTES:
                raise too_large
        try:
            fields = json.loads(raw)
        except ValueError:
            raise DspError(ErrorCode.INPUT_INVALID, "the request body is not JSON") from None
        if not isinstance(fields, dict) or set(fields) != MESSAGE_FIELDS:
            raise DspError(
                ErrorCode.INPUT_INVALID, "a message is its ID, text and expected revision"
            )
        if not all(isinstance(value, str) for value in fields.values()):
            raise DspError(ErrorCode.INPUT_INVALID, "message fields are strings")
        return commanded(conversation_id, None, **fields)

    def commanded(
        conversation_id: str,
        job_id: str | None,
        client_message_id: str,
        text: str,
        expected_revision: str,
    ) -> dict[str, Any]:
        store = ledger()
        return controls.command(
            ctx,
            conversation_id,
            client_message_id,
            text,
            expected_revision,
            job_id=job_id,
            ledger=store,
            clock=clock,
            new_id=_id,
            workload=current_workload(ctx, store),
            binding=binding,
        )

    def controlled(job_id: str | None, command_id: str, action: str) -> dict[str, Any]:
        revision = current_workload(ctx, ledger())["revision"]
        return commanded(
            controls.CONVERSATION, job_id, command_id, controls.PHRASES[action], revision
        )

    @app.post("/v1/jobs/{job_id}/control")
    def control_job(
        job_id: str,
        command_id: Annotated[str, Body(min_length=1, max_length=160)],
        action: Annotated[Literal["pause", "resume", "cancel", "status"], Body()],
    ) -> dict[str, Any]:
        return controlled(job_id, command_id, action)

    @app.post("/v1/control")
    def control_live(
        command_id: Annotated[str, Body(min_length=1, max_length=160)],
        action: Annotated[Literal["pause", "resume", "cancel", "status"], Body()],
    ) -> dict[str, Any]:
        """The native menu's door: the same control on whichever job is live."""
        return controlled(None, command_id, action)

    @app.post("/v1/jobs/{job_id}/checkpoint", dependencies=[Depends(native)])
    def checkpoint(
        job_id: str,
        attempt: Annotated[int, Body()],
        fence: Annotated[int, Body()],
        sha256: Annotated[str, Body(pattern="^sha256:[a-f0-9]{64}$")],
    ) -> dict[str, Any]:
        return jobs.checkpoint(ctx, job_id, attempt, fence, sha256, ledger=ledger(), clock=clock)
