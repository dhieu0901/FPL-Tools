"""Vercel entrypoint, discovered under ``api/``.

The package lives under ``src/``, which is not installed by
``pip install -r requirements.txt``, so the source directory is placed on the
path explicitly rather than relying on an editable install. Past that, this
exports the same object as the root ``app.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from vmf_api.asgi import app  # noqa: E402  (path setup must run first)

__all__ = ["app"]
