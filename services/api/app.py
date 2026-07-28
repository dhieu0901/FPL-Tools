"""Vercel-recognized FastAPI entrypoint.

Vercel installs this project from ``pyproject.toml``, including the ``src``
package, then discovers the exported application at this conventional path.
"""

from vmf_api.main import app

__all__ = ["app"]
