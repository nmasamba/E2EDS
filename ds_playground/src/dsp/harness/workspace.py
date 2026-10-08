import json
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

from dsp.adapters import export_fs
from dsp.adapters.discovery import probes
from dsp.adapters.duckdb_profile import profile_csv
from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.adapters.store_fs import ContentStore
from dsp.application import admission, conversation, jobs
from dsp.application.discovery import discover
from dsp.application.grants import grant_folder, revoke, summary
from dsp.application.packs import profile_granted
from dsp.application.planning import LOCAL_DRAFT, propose_plan
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
    }
)

MESSAGE_FIELDS = {"client_message_id", "text", "expected_revision"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _id() -> str:
    return uuid4().hex


def mount(
    app: FastAPI,
    state_dir: Path,
    server: uvicorn.Server | None = None,
    clock: Callable[[], str] = _now,
) -> None:
    """Add the workspace routes: grants, profiling, discovery, planning, events and jobs.

    Every caller is the local owner, established by the token the guard has already checked;
    nothing in a request body is treated as authority. ``server`` is the running server, whose
    shutdown ends open event streams; ``clock`` is the one source of time for the ledger and the
    job coordinator.
    """
    ctx = TrustedContext.local()

    def ledger() -> SqliteLedger:
        return SqliteLedger(state_dir / "ledger.sqlite", clock)

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
        propose_plan(ctx, ledger=ledger(), new_id=_id)
        return snapshot

    @app.get("/v1/hardware")
    def latest_hardware() -> dict[str, Any]:
        snapshots = ledger().current(ctx, "HardwareSnapshot")
        if not snapshots:
            raise DspError(ErrorCode.NOT_FOUND, "nothing has been discovered yet")
        return snapshots[-1]

    @app.post("/v1/plan")
    def create_plan() -> dict[str, Any]:
        return propose_plan(ctx, ledger=ledger(), new_id=_id)

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
        receipt = profile_granted(
            ctx,
            source_handle,
            relative_path,
            output_handle,
            ledger=ledger(),
            store=ContentStore(state_dir / "store"),
            exporter=export_fs,
            profiler=profile_csv,
            clock=_now,
            new_id=_id,
        )
        return {"version": receipt["version"], "files": len(receipt["files"])}

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
        return admission.admit(
            ctx,
            operation,
            idempotency_key,
            task,
            workload=current_workload(ctx, store),
            binding=LOCAL_DRAFT,
            ledger=store,
            clock=clock,
            new_id=_id,
        )

    @app.get("/v1/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, Any]:
        return jobs.inspect(ctx, job_id, ledger=ledger(), clock=clock)

    @app.post("/v1/jobs/{job_id}/lease", dependencies=[Depends(native)])
    def lease_job(job_id: str, worker: Annotated[str, Body(embed=True)]) -> dict[str, Any]:
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

    @app.post("/v1/conversations/{conversation_id}/messages")
    async def post_message(conversation_id: str, request: Request) -> dict[str, Any]:
        """D18: the body is bounded in bytes before it is parsed; only three fields are accepted."""
        declared = int(request.headers.get("content-length") or 0)
        raw = b"" if declared > conversation.MAX_BYTES else await request.body()
        if max(declared, len(raw)) > conversation.MAX_BYTES:
            raise DspError(ErrorCode.INPUT_INVALID, "the message is larger than 16 KiB")
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
        return conversation.receive(
            ctx, conversation_id, **fields, ledger=ledger(), clock=clock, new_id=_id
        )

    @app.post("/v1/jobs/{job_id}/control")
    def control_job(
        job_id: str, action: Annotated[Literal["cancel"], Body(embed=True)]
    ) -> dict[str, Any]:
        return jobs.control(ctx, job_id, action, ledger=ledger(), clock=clock)
