"""
@module: tests.test_health
@context: FastAPI backend tests.
@role: Smoke-tests the health endpoint and the application factory.
"""

from fastapi.testclient import TestClient

from app import __version__
from app.main import create_app


def test_health_endpoint() -> None:
    """The /api/health endpoint returns status ok and the current version."""
    client = TestClient(create_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}
