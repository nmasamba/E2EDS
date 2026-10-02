import os
import secrets
from collections.abc import Awaitable, Callable
from importlib.metadata import version

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from dsp.contracts.errors import ErrorCode


def _refuse(code: ErrorCode, status: int, message: str) -> JSONResponse:
    return JSONResponse({"code": code, "message": message}, status)


def create_app(token: str, port: int) -> FastAPI:
    """Build the local harness API: loopback hosts only, no browser origins, bearer token."""
    app = FastAPI(title="DS Playground harness", docs_url=None, redoc_url=None, openapi_url=None)
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    @app.middleware("http")
    async def guard(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.headers.get("host") not in hosts or "origin" in request.headers:
            return _refuse(ErrorCode.FORBIDDEN, 403, "host or origin not allowed")
        supplied = request.headers.get("authorization", "")
        if not secrets.compare_digest(supplied.encode(), f"Bearer {token}".encode()):
            return _refuse(ErrorCode.UNAUTHENTICATED, 401, "missing or wrong credential")
        return await call_next(request)

    @app.get("/v1/status")
    def status() -> dict[str, object]:
        return {"status": "ok", "pid": os.getpid(), "version": version("dsp")}

    return app
