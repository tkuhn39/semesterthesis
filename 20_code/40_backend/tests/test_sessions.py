"""
@module: tests.test_sessions
@context: Domain + API tests — saved workbench sessions (app.services.session_store).
@role: Save/list/load/delete roundtrip on isolated storage, the optional stored HTML
       report, and the API error paths (404, slug collision).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import session_store


@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    from app.storage.local import LocalStorageBackend

    backend = LocalStorageBackend(tmp_path / "storage")
    monkeypatch.setattr(session_store, "get_storage", lambda: backend)
    return backend


def test_session_roundtrip(isolated_storage) -> None:
    """Save → list → get → delete; metadata carries a UTC timestamp and version."""
    assert session_store.list_sessions() == []
    record = session_store.save_session("Auslegung A", {"stage": {"teeth_pinion": 30}}, 1)
    assert record.saved_at.endswith("+00:00")
    metas = session_store.list_sessions()
    assert [m.name for m in metas] == ["Auslegung A"]
    assert metas[0].has_report is False
    loaded = session_store.get_session("Auslegung A")
    assert loaded is not None
    assert loaded.state == {"stage": {"teeth_pinion": 30}}
    assert session_store.delete_session("Auslegung A") is True
    assert session_store.delete_session("Auslegung A") is False


def test_session_slug_collision(isolated_storage) -> None:
    session_store.save_session("Lauf 1", {"a": 1}, 1)
    with pytest.raises(ValueError, match="collides"):
        session_store.save_session("Lauf_1", {"a": 2}, 1)


def test_sessions_api_with_stored_report(isolated_storage) -> None:
    """POST with a report request stores the rendered HTML for later recall."""
    client = TestClient(create_app())
    res = client.post(
        "/api/sessions",
        json={"name": "kst-E Referenz", "state": {"label": "kst-E"}, "report": {}},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["report_error"] is None
    assert body["meta"]["has_report"] is True
    # listing + stored report recall
    metas = client.get("/api/sessions").json()
    assert metas[0]["name"] == "kst-E Referenz"
    assert metas[0]["has_report"] is True
    rep = client.get("/api/sessions/kst-E Referenz/report")
    assert rep.status_code == 200
    assert "<!doctype html>" in rep.text.lower()
    # full state recall
    got = client.get("/api/sessions/kst-E Referenz").json()
    assert got["state"] == {"label": "kst-E"}
    # a re-save WITHOUT report keeps the stored report available
    res = client.post("/api/sessions", json={"name": "kst-E Referenz", "state": {"label": "x"}})
    assert res.json()["meta"]["has_report"] is True
    # delete removes state AND report
    assert client.delete("/api/sessions/kst-E Referenz").status_code == 204
    assert client.get("/api/sessions/kst-E Referenz").status_code == 404
    assert client.get("/api/sessions/kst-E Referenz/report").status_code == 404
    assert client.delete("/api/sessions/kst-E Referenz").status_code == 404
