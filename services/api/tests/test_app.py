from fastapi.testclient import TestClient

from vmf_api.main import app


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
        assert "/api/admin/violations" in schema["paths"]
