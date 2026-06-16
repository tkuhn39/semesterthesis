"""
@module: tests.test_api
@context: FastAPI backend tests.
@role: Exercises the readiness and info endpoints with default settings
       (local storage, no database).
"""

from fastapi.testclient import TestClient

from app import __version__
from app.main import create_app


def test_ready_endpoint() -> None:
    """With defaults the service reports ready (null DB, local storage)."""
    client = TestClient(create_app())
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json() == {"ready": True, "database": True, "storage": True}


def test_info_endpoint() -> None:
    """Info exposes selected backends without leaking secrets."""
    client = TestClient(create_app())
    response = client.get("/api/info")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == __version__
    assert body["storage_backend"] == "local"
    assert body["database_backend"] == "none"
