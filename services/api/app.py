"""Vercel entrypoint, discovered at the project root.

Both this file and ``api/index.py`` export the same object from
``vmf_api.asgi``. Which one the platform picks is its business; what matters
is that it cannot pick a different application from the one under test.
"""

from vmf_api.asgi import app

__all__ = ["app"]
