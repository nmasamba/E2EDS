import logging
import os
import secrets
from collections.abc import Awaitable, Callable
from importlib.metadata import version

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from dsp.contracts.errors import ErrorCode

SHELL_ORIGIN = "tauri://localhost"  # Tauri's custom-protocol origin on macOS and Linux
DEV_ORIGIN = "http://localhost:1420"  # the renderer's dev server under `tauri dev`
ALLOWED_HEADERS = ("authorization", "content-type")  # all a page may send; nothing else


def _refuse(code: ErrorCode, status: int, message: str) -> JSONResponse:
    return JSONResponse({"code": code, "message": message}, status)


def create_app(token: str, port: int, dev: bool = False) -> FastAPI:
    """Build the local harness API: loopback hosts, the desktop shell's origin only, bearer token.

    A request with no ``Origin`` (the CLI) or with the shell's origin passes the origin rule;
    ``dev`` also admits the `tauri dev` origin. Every other origin is refused. A preflight from an
    allowed origin is answered before the token check (a browser sends it without the token) and
    grants exactly the authorization and content-type headers.
    """
    app = FastAPI(title="DS Playground harness", docs_url=None, redoc_url=None, openapi_url=None)
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    origins = {None, SHELL_ORIGIN, DEV_ORIGIN} if dev else {None, SHELL_ORIGIN}

    @app.middleware("http")
    async def guard(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        origin = request.headers.get("origin")
        if request.headers.get("host") not in hosts or origin not in origins:
            return _refuse(ErrorCode.FORBIDDEN, 403, "host or origin not allowed")
        cors = {"Access-Control-Allow-Origin": origin} if origin else {}
        if (
            cors
            and request.method == "OPTIONS"
            and "access-control-request-method" in request.headers
        ):
            asked = request.headers.get("access-control-request-headers", "").lower().split(",")
            if not {name.strip() for name in asked if name.strip()} <= set(ALLOWED_HEADERS):
                return _refuse(ErrorCode.FORBIDDEN, 403, "request header not allowed")
            allowed = {"Access-Control-Allow-Headers": ", ".join(ALLOWED_HEADERS)}
            return Response(status_code=204, headers=cors | allowed)
        supplied = request.headers.get("authorization", "")
        if secrets.compare_digest(supplied.encode(), f"Bearer {token}".encode()):
            try:
                response = await call_next(request)
            except Exception as error:
                logging.getLogger(__name__).error("unhandled %s", type(error).__name__)
                response = _refuse(ErrorCode.INTERNAL_ERROR, 500, "internal error")
        else:
            response = _refuse(ErrorCode.UNAUTHENTICATED, 401, "missing or wrong credential")
        response.headers.update(cors)
        return response

    @app.get("/v1/status")
    def status() -> dict[str, object]:
        return {"status": "ok", "pid": os.getpid(), "version": version("dsp")}

    return app
