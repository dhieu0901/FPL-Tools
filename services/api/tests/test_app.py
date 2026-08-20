from pathlib import Path
from runpy import run_path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient

from vmf_api.asgi import app as asgi_app
from vmf_api.db.schema import SCHEMA_REVISION
from vmf_api.main import app


def test_both_entrypoints_export_the_same_application() -> None:
    """The deployed API must be the application these tests exercise.

    Two entrypoint files each built their own, so the platform could serve one
    while every test covered the other. Every route returned 404 in production
    and nothing here noticed.
    """

    root = Path(__file__).parents[1]
    from_root = run_path(str(root / "app.py"))["app"]
    from_api_dir = run_path(str(root / "api" / "index.py"))["app"]

    assert from_root is asgi_app
    assert from_api_dir is asgi_app


def test_the_deployed_application_serves_the_real_routes() -> None:
    """A smoke test through the entrypoint, not around it."""

    with TestClient(asgi_app) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_readiness_expected_revision_matches_repository_head() -> None:
    project_root = Path(__file__).parents[1]
    config = Config(str(project_root / "alembic.ini"))

    assert ScriptDirectory.from_config(config).get_current_head() == SCHEMA_REVISION


def test_liveness_and_openapi() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["version"] == "0.1.0"

        schema = client.get("/openapi.json").json()
        assert "/api/managers" in schema["paths"]
        assert "/api/classic/standings" in schema["paths"]
        assert "/api/h2h/standings" in schema["paths"]
        assert "/api/cups" in schema["paths"]
        assert "/api/cron/fpl-probe" in schema["paths"]
        assert "/api/admin/violations" in schema["paths"]
