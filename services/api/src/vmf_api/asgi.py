"""The ASGI application every deployment target serves.

There is one application object and one place that wraps it. Two entrypoint
files used to build their own, which is how the deployed API ended up serving
a different app from the one under test.

The wrapper reports the path the platform actually delivered on a response
header. A serverless platform may hand the function the visitor's path or a
rewritten one, and the difference is invisible until every route returns 404
at once - which is exactly what it cost to find out the first time.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, MutableMapping

from vmf_api.main import app as fastapi_app

Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]

#: Headers carrying the request's real path, in the order they are trusted.
#: Platforms differ, and an absent header falls through to the next.
ORIGINAL_PATH_HEADERS = (
    b"x-vercel-original-path",
    b"x-forwarded-path",
    b"x-original-uri",
    b"x-vercel-original-pathname",
)

#: The path a catch-all rewrite would collapse every request onto.
REWRITE_TARGET = "/api/index"


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers") or ():
        if key.lower() == name:
            return value.decode("latin-1")
    return None


def _original_path(scope: Scope) -> str | None:
    for name in ORIGINAL_PATH_HEADERS:
        value = _header(scope, name)
        if value:
            return value.split("?", 1)[0]
    return None


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] != "http":
        await fastapi_app(scope, receive, send)
        return

    received = scope.get("path", "")
    # A request that arrives already rewritten matches no route, so the real
    # path is put back before FastAPI ever sees it.
    if received == REWRITE_TARGET or received.startswith(f"{REWRITE_TARGET}/"):
        recovered = _original_path(scope)
        if recovered:
            scope = dict(scope)
            scope["path"] = recovered
            scope["raw_path"] = recovered.encode("utf-8")

    async def send_with_diagnosis(message: MutableMapping[str, Any]) -> None:
        if message["type"] == "http.response.start":
            message = dict(message)
            headers = list(message.get("headers") or [])
            headers.append((b"x-vmf-received-path", received.encode("latin-1")))
            headers.append((b"x-vmf-routed-path", str(scope.get("path", "")).encode("latin-1")))
            message["headers"] = headers
        await send(message)

    await fastapi_app(scope, receive, send_with_diagnosis)


__all__ = ["app"]
