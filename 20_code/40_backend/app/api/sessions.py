"""
@module: app.api.sessions
@context: API layer — saved workbench sessions (save/list/load/delete + stored report).
@role: The sidebar's session recall (user requirement 2026-08-19). POST saves the
       frontend's full input state (opaque, versioned) and can render + store the HTML
       system report in the same call — the stored report reopens later WITHOUT
       recomputation, everything else is regenerable from the state. The state schema
       belongs to the frontend; this layer only persists it (app.services.session_store).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.api.report import ReportRequest, report
from app.services.session_store import (
    SessionMeta,
    SessionRecord,
    delete_session,
    get_session,
    list_sessions,
    load_report_html,
    save_report_html,
    save_session,
)

router = APIRouter(prefix="/api", tags=["sessions"])


class SessionSaveRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    schema_version: int = 1
    state: dict[str, Any]
    # when set, the report is rendered server-side (the same POST /api/report chain)
    # and stored next to the session for later recall without recomputation
    report: ReportRequest | None = None


class SessionSaveResponse(BaseModel):
    meta: SessionMeta
    # report rendering is best-effort: the session save must not fail because a
    # capacity input is currently incomplete — the error is surfaced instead
    report_error: str | None = None


@router.get("/sessions", response_model=list[SessionMeta])
def sessions_list() -> list[SessionMeta]:
    """All saved sessions, newest first."""
    return list_sessions()


@router.post("/sessions", response_model=SessionSaveResponse)
def sessions_save(req: SessionSaveRequest) -> SessionSaveResponse:
    """Save (upsert) a named session; optionally render + store its HTML report."""
    try:
        record = save_session(req.name, req.state, req.schema_version)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    report_error: str | None = None
    has_report = False
    if req.report is not None:
        try:
            html = report(req.report).body
            save_report_html(record.name, bytes(html).decode("utf-8"))
            has_report = True
        except Exception as exc:  # surfaced, never fatal for the save itself
            report_error = str(exc)
    else:
        has_report = load_report_html(record.name) is not None  # keep an earlier report
    return SessionSaveResponse(
        meta=SessionMeta(
            name=record.name,
            saved_at=record.saved_at,
            schema_version=record.schema_version,
            has_report=has_report,
        ),
        report_error=report_error,
    )


@router.get("/sessions/{name}", response_model=SessionRecord)
def sessions_get(name: str) -> SessionRecord:
    """The full saved state document for recall."""
    record = get_session(name)
    if record is None:
        raise HTTPException(status_code=404, detail=f"session not found: {name}")
    return record


@router.get("/sessions/{name}/report", response_class=HTMLResponse)
def sessions_report(name: str) -> HTMLResponse:
    """The stored HTML system report of a session (404 when none was stored)."""
    html = load_report_html(name)
    if html is None:
        raise HTTPException(status_code=404, detail=f"session has no stored report: {name}")
    return HTMLResponse(html)


@router.delete("/sessions/{name}", status_code=204)
def sessions_delete(name: str) -> None:
    """Remove a session and its stored report."""
    if not delete_session(name):
        raise HTTPException(status_code=404, detail=f"session not found: {name}")
