"""
@module: tests.test_errors
@context: FastAPI backend tests.
@role: The central AppError handler returns a uniform JSON error envelope with
       the carried status code and machine-readable code.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import AppError, register_error_handlers


def test_app_error_returns_uniform_envelope() -> None:
    """A raised AppError is rendered as {"error": {"code", "message"}}."""
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise AppError("not allowed", status_code=418, code="teapot")

    response = TestClient(app).get("/boom")
    assert response.status_code == 418
    assert response.json() == {"error": {"code": "teapot", "message": "not allowed"}}
