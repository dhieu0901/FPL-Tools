"""Run a command's coroutine on an event loop psycopg can use.

Windows defaults to the proactor loop, which psycopg refuses to run against in
async mode. The API itself never meets this because it is served on Linux, but
the administration commands are run by hand from an operator's machine, so
they select the loop explicitly rather than failing at the first query.
"""

from __future__ import annotations

import asyncio
import selectors
import sys
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


def configure_console() -> None:
    """Let the console print any name FPL returns.

    Team names are free text and regularly contain characters outside the
    Windows console's default code page. Without this a report crashes partway
    through on a name it cannot encode, which looks like a failed import.
    """

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            # A redirected or already-closed stream keeps its own encoding.
            continue


def _selector_loop() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


def run(coroutine: Coroutine[Any, Any, T]) -> T:
    """Execute ``coroutine`` to completion, closing the loop afterwards."""

    if sys.platform == "win32":
        return asyncio.run(coroutine, loop_factory=_selector_loop)
    return asyncio.run(coroutine)
