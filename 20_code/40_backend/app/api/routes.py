"""
@module: app.api.routes
@context: FastAPI backend.
@role: Declares the versioned API routes. Currently exposes health/meta
       endpoints as a scaffold; gear-analysis endpoints will be added here.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__

router = APIRouter(prefix="/api", tags=["meta"])


class HealthResponse(BaseModel):
    """Liveness payload."""

    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report service liveness and version."""
    return HealthResponse(status="ok", version=__version__)
