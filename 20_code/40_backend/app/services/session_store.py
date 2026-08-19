"""
@module: app.services.session_store
@context: Domain layer — saved workbench sessions (persisted, recallable).
@role: CRUD for named session snapshots (user requirement 2026-08-19: "Sitzung als
       File speichern … alle eingestellten Parameter und eventuelle Berichte … in
       der Seitenleiste erneut abrufen"). A session is the frontend's FULL input
       state as an opaque JSON document plus metadata; optionally the rendered HTML
       system report is stored alongside so it can be reopened without recomputing.

Persistence mirrors the user material library (ADR-030): one object per session
under ``sessions/<slug>.json`` via app.storage (local or S3-compatible; per-record
objects keep concurrent nodes race-free, §18), the report under
``sessions/<slug>.report.html``. The state payload is versioned by the frontend
(``schema_version``) and treated as opaque here — the store never interprets it.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.storage import get_storage

logger = logging.getLogger(__name__)

__all__ = [
    "SessionMeta",
    "SessionRecord",
    "delete_session",
    "get_session",
    "list_sessions",
    "load_report_html",
    "save_report_html",
    "save_session",
]

_PREFIX = "sessions/"
_SLUG_STRIP = re.compile(r"[^A-Za-z0-9._-]+")


class SessionRecord(BaseModel):
    """One saved session: metadata + the opaque frontend state document."""

    name: str = Field(min_length=1, max_length=80)
    saved_at: str  # ISO 8601 (UTC)
    schema_version: int = 1
    state: dict[str, Any]


class SessionMeta(BaseModel):
    """Listing entry (the state stays on disk until the session is opened)."""

    name: str
    saved_at: str
    schema_version: int
    has_report: bool


def _slug(name: str) -> str:
    slug = _SLUG_STRIP.sub("_", name.strip()).strip("._")
    if not slug:
        raise ValueError(f"session name {name!r} has no storable characters")
    return slug


def _key(name: str) -> str:
    return f"{_PREFIX}{_slug(name)}.json"


def _report_key(name: str) -> str:
    return f"{_PREFIX}{_slug(name)}.report.html"


def save_session(name: str, state: dict[str, Any], schema_version: int) -> SessionRecord:
    """Create or update a named session (upsert by name; slug collisions rejected)."""
    storage = get_storage()
    key = _key(name)
    if storage.exists(key):
        existing = SessionRecord.model_validate_json(storage.load_bytes(key))
        if existing.name != name.strip():
            raise ValueError(
                f"session name {name!r} collides with existing entry "
                f"{existing.name!r} (same storage slug)"
            )
    record = SessionRecord(
        name=name.strip(),
        saved_at=datetime.now(UTC).isoformat(timespec="seconds"),
        schema_version=schema_version,
        state=state,
    )
    storage.save_bytes(key, record.model_dump_json().encode("utf-8"))
    return record


def list_sessions() -> list[SessionMeta]:
    """All saved sessions (newest first); unreadable records are skipped with a warning."""
    storage = get_storage()
    sessions: list[SessionMeta] = []
    for key in storage.list_keys(_PREFIX):
        if not key.endswith(".json"):
            continue
        try:
            record = SessionRecord.model_validate_json(storage.load_bytes(key))
        except (KeyError, ValueError) as exc:
            logger.warning("skipping unreadable session %r: %s", key, exc)
            continue
        sessions.append(
            SessionMeta(
                name=record.name,
                saved_at=record.saved_at,
                schema_version=record.schema_version,
                has_report=storage.exists(_report_key(record.name)),
            )
        )
    return sorted(sessions, key=lambda s: s.saved_at, reverse=True)


def get_session(name: str) -> SessionRecord | None:
    storage = get_storage()
    key = _key(name)
    if not storage.exists(key):
        return None
    return SessionRecord.model_validate_json(storage.load_bytes(key))


def delete_session(name: str) -> bool:
    """Remove a session AND its stored report; ``False`` if it does not exist."""
    storage = get_storage()
    key = _key(name)
    if not storage.exists(key):
        return False
    storage.delete(key)
    storage.delete(_report_key(name))
    return True


def save_report_html(name: str, html: str) -> None:
    get_storage().save_bytes(_report_key(name), html.encode("utf-8"))


def load_report_html(name: str) -> str | None:
    storage = get_storage()
    key = _report_key(name)
    if not storage.exists(key):
        return None
    return storage.load_bytes(key).decode("utf-8")
