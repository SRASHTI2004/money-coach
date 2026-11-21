"""FastAPI app: JSON API under /api (routers in app/api), React build served from the same service."""
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import db, gemini, guardrails
from .api import coach_api, data, insights, plan

log = logging.getLogger("money-coach")
app = FastAPI(title="Money Coach", docs_url=None, redoc_url=None)
db.init()
gemini.preload()

for module in (data, plan, insights, coach_api):
    app.include_router(module.router)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": ("default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                                "connect-src 'self'; frame-ancestors 'none'"),
}


@app.middleware("http")
async def security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Add basic hardening headers to every response."""
    response = await call_next(request)
    for k, v in SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    return response


def _error(status: int, message: str) -> JSONResponse:
    """All API errors share one shape: {"detail": "<human readable message>"}."""
    return JSONResponse(status_code=status, content={"detail": message})


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Normalise HTTP errors."""
    return _error(exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Turn pydantic validation errors into one readable sentence."""
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(p) for p in first.get("loc", ()) if p != "body")
    return _error(422, f"Invalid input{f' ({where})' if where else ''}: {first.get('msg', 'please check your values')}.")


@app.exception_handler(Exception)
async def unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    """Never leak internals; log the exception type only (no request bodies, no secrets)."""
    log.error("unhandled %s", type(exc).__name__)
    return _error(500, "Something went wrong on our side. Please try again.")


@app.api_route("/api/health", methods=["GET", "HEAD"])
def health() -> dict[str, Any]:
    """Lightweight liveness + AI status for uptime pings, Render and the UI badge (no database or AI call)."""
    return {"ok": True, "ai_enabled": gemini.enabled(), "ai": gemini.status, "disclaimer": guardrails.DISCLAIMER}


# ---- frontend (built by Vite into frontend/dist)
DIST = os.path.abspath(os.environ.get("FRONTEND_DIST", os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")))
if os.path.isdir(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        """Serve built files; unknown paths fall back to index.html (single-page app). Path traversal safe."""
        f = os.path.abspath(os.path.join(DIST, path))
        if path and f.startswith(DIST + os.sep) and os.path.isfile(f):
            return FileResponse(f)
        return FileResponse(os.path.join(DIST, "index.html"))
