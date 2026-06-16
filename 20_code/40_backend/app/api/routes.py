"""
@module: app.api.routes
@context: FastAPI backend.
@role: Declares the versioned API routes. Provides liveness/readiness/info
       endpoints (HA-friendly probes) as a scaffold; gear-analysis endpoints
       will be added here.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__
from app.config import get_settings
from app.database import get_database
from app.storage import get_storage

router = APIRouter(prefix="/api", tags=["meta"])


class HealthResponse(BaseModel):
    """Liveness payload."""

    status: str
    version: str


class ReadyResponse(BaseModel):
    """Readiness payload (dependencies reachable)."""

    ready: bool
    database: bool
    storage: bool


class InfoResponse(BaseModel):
    """Non-secret runtime information."""

    version: str
    app_env: str
    node_name: str
    storage_backend: str
    database_backend: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness: the process is up. Does not touch external dependencies."""
    return HealthResponse(status="ok", version=__version__)


@router.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    """Readiness: configured storage and database backends are usable.

    Raises (-> HTTP 500) if a backend cannot be built, which a load balancer
    reads as "not ready" — correct behaviour for a multi-node deployment.
    """
    database_ok = get_database().health_check()
    get_storage()  # constructible == storage configured correctly
    return ReadyResponse(ready=database_ok, database=database_ok, storage=True)


@router.get("/info", response_model=InfoResponse)
def info() -> InfoResponse:
    """Report non-secret configuration (selected backends, node, environment)."""
    summary = get_settings().public_summary()
    return InfoResponse(version=__version__, **summary)
