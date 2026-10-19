"""Strict loopback application; routes never perform provider requests."""

import asyncio
import mimetypes
import secrets
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from time import monotonic
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from fantasy_gm.web.data import synthetic_view


class BrowserSession:
    """One capability and whitelisted payload, never a token or on-disk cache."""

    def __init__(
        self, *, private: bool = False, clock: Callable[[], float] = monotonic
    ) -> None:
        self.private = private
        self.clock = clock
        self.capability = secrets.token_urlsafe(32) if private else ""
        self.expires = clock() + 1200
        self.view: dict[str, Any] | None = None if private else synthetic_view()
        self.yahoo = "disconnected"
        self.schedule = "unavailable" if private else "synthetic"

    def load(self, view: dict[str, Any]) -> None:
        self.view = view
        self.yahoo = "loaded"
        self.schedule = "observed" if view.get("schedule") else "unavailable"
        self.expires = self.clock() + 1200

    def clear(self, *, expired: bool = False) -> None:
        self.view = None
        self.capability = ""
        self.yahoo = "expired" if expired else "disconnected"
        self.schedule = "unavailable"

    def expire(self) -> None:
        if self.private and self.capability and self.clock() >= self.expires:
            self.clear(expired=True)

    def authorized(self, request: Request) -> bool:
        self.expire()
        supplied = request.headers.get("authorization", "")
        expected = "Bearer " + self.capability
        return (
            bool(self.capability)
            and supplied.isascii()
            and secrets.compare_digest(supplied, expected)
        )


class _Boundary:
    def __init__(self, app: ASGIApp, *, origin: str) -> None:
        self.app = app
        self.origin = origin
        self.host = origin.removeprefix("http://")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        headers = scope.get("headers", [])
        names = [key.lower() for key, _ in headers]
        request = Request(scope)
        invalid = (
            names.count(b"host") != 1
            or names.count(b"origin") > 1
            or names.count(b"authorization") > 1
            or names.count(b"sec-fetch-site") > 1
            or request.headers.get("host") != self.host
            or request.headers.get("origin", self.origin) != self.origin
            or request.headers.get("sec-fetch-site", "none")
            not in ("none", "same-origin")
        )
        response: Response | None = None
        if invalid:
            response = JSONResponse({"error": "Request denied"}, status_code=403)
        elif scope.get("query_string"):
            response = JSONResponse(
                {"error": "Queries are unsupported"}, status_code=400
            )

        async def safe_send(message: Any) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend(
                    [
                        (b"cache-control", b"no-store"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"cross-origin-resource-policy", b"same-origin"),
                        (b"cross-origin-opener-policy", b"same-origin"),
                        (
                            b"content-security-policy",
                            (
                                b"default-src 'self'; connect-src 'self'; "
                                b"img-src 'self' data:; "
                                b"style-src 'self' 'unsafe-inline'; script-src 'self'; "
                                b"font-src 'self'; object-src 'none'; base-uri 'none'; "
                                b"frame-ancestors 'none'; form-action 'none'"
                            ),
                        ),
                    ]
                )
            await send(message)

        if response is not None:
            await response(scope, receive, safe_send)
        else:
            await self.app(scope, receive, safe_send)


def create_app(
    *,
    port: int = 8765,
    session: BrowserSession | None = None,
    static_root: Path | None = None,
) -> ASGIApp:
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("Invalid port")
    state = session or BrowserSession()
    origin = f"http://127.0.0.1:{port}"
    root = static_root or Path(__file__).resolve().parents[3] / "frontend" / "dist"

    async def cleanup() -> None:
        while True:
            await asyncio.sleep(1)
            state.expire()

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        task = asyncio.create_task(cleanup())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            state.clear()

    async def status(request: Request) -> Response:
        state.expire()
        return JSONResponse(
            {
                "mode": "private" if state.private else "synthetic",
                "yahoo": state.yahoo,
                "schedule": state.schedule,
            }
        )

    async def view(request: Request) -> Response:
        if state.private and (not state.authorized(request) or state.view is None):
            return JSONResponse({"error": "Session unavailable"}, status_code=401)
        return JSONResponse(state.view)

    async def disconnect(request: Request) -> Response:
        if request.headers.get("origin") != origin:
            return JSONResponse({"error": "Request denied"}, status_code=403)
        if not state.private or not state.authorized(request):
            return JSONResponse({"error": "Session unavailable"}, status_code=401)
        state.clear()
        return JSONResponse({"disconnected": True})

    async def static(request: Request) -> Response:
        path = request.path_params["path"]
        parts = path.split("/") if path else ["index.html"]
        if any(
            part in ("", ".", "..")
            or "\\" in part
            or ":" in part
            or part.startswith(".")
            for part in parts
        ):
            return Response(status_code=404)
        candidate = root.joinpath(*parts)
        # Reject symlink/reparse escapes at every component before reading bytes.
        chain = [root, *candidate.parents]
        if any(p.is_symlink() or p.is_junction() for p in chain):
            return Response(status_code=404)
        if candidate.is_symlink() or candidate.is_junction():
            return Response(status_code=404)
        if not candidate.resolve().is_relative_to(root.resolve()):
            return Response(status_code=404)
        if (
            candidate.suffix.lower()
            not in {
                ".html",
                ".js",
                ".css",
                ".svg",
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
                ".woff",
                ".woff2",
                ".ico",
                ".avif",
            }
            or not candidate.is_file()
        ):
            return Response(status_code=404)
        try:
            content = candidate.read_bytes()
        except OSError:
            return Response(status_code=404)
        return Response(content, media_type=mimetypes.guess_type(candidate)[0])

    async def failure(request: Request, error: Exception) -> Response:
        return JSONResponse({"error": "Request unavailable"}, status_code=500)

    app = Starlette(
        routes=[
            Route("/api/status", status),
            Route("/api/view", view),
            Route("/api/disconnect", disconnect, methods=["POST"]),
            Route("/{path:path}", static),
        ],
        lifespan=lifespan,
        exception_handlers={Exception: failure},
    )
    return _Boundary(app, origin=origin)
