from pathlib import Path
from runpy import run_path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient

from vmf_api.db.schema import SCHEMA_REVISION
from vmf_api.main import app


def test_vercel_entrypoint_exports_application() -> None:
    entrypoint = Path(__file__).parents[1] / "app.py"

    assert run_path(str(entrypoint))["app"] is app


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
