from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Body, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from dsp.adapters import export_fs
from dsp.adapters.duckdb_profile import profile_csv
from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.adapters.store_fs import ContentStore
from dsp.application.grants import grant_folder, revoke, summary
from dsp.application.packs import profile_granted
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext

STATUS = {ErrorCode.INPUT_INVALID: 400, ErrorCode.FORBIDDEN: 403, ErrorCode.NOT_FOUND: 404}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _id() -> str:
    return uuid4().hex


def mount(app: FastAPI, state_dir: Path) -> None:
    """Add the workspace routes: folder grants, and profiling through them, on one ledger.

    Every caller is the local owner, established by the token the guard has already checked;
    nothing in a request body is treated as authority.
    """
    ctx = TrustedContext.local()

    def ledger() -> SqliteLedger:
        return SqliteLedger(state_dir / "ledger.sqlite", _now)

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
