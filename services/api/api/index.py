"""Serverless entrypoint.

Vercel's Python runtime discovers an ASGI application exported as ``app`` from
this conventional path. The package lives under ``src/``, which is not
installed by ``pip install -r requirements.txt``, so the source directory is
placed on the path explicitly rather than relying on an editable install.

Every request is rewritten here by ``vercel.json`` from its real URL to
``/api/index``. Whether the platform hands the function the original path or
the rewritten one decides whether any route matches at all, so the path the
function actually receives is reported on a response header. It costs nothing
and turns "the whole API returns 404" into a one-request diagnosis.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, MutableMapping

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from vmf_api.main import app as fastapi_app  # noqa: E402  (path setup must run first)

Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]

#: Headers carrying the request's real path, in the order they are trusted.
#: Platforms differ, and an absent header simply falls through to the next.
ORIGINAL_PATH_HEADERS = (
    b"x-vercel-original-path",
    b"x-forwarded-path",
    b"x-original-uri",
    b"x-vercel-original-pathname",
)

REWRITE_TARGET = "/api/index"


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers") or ():
        if key.lower() == name:
            return value.decode("latin-1")
    return None


def _original_path(scope: Scope) -> str | None:
    """Recover the path the visitor asked for, if the platform still has it."""

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
