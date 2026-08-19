"""
@module: tests.test_material_store
@context: Domain + API tests — the user material library (persisted via app.storage).
@role: CRUD roundtrip on an isolated local storage, built-in immutability, the served
       catalog merging built-ins + user records, and the per-request mat_name options
       of /api/ui-schema following the library.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import material_store
from app.services.materials import CATALOG, Material, MaterialKind
from app.storage.local import LocalStorageBackend


@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    """Point the material store at a throwaway local storage root."""
    backend = LocalStorageBackend(tmp_path / "storage")
    monkeypatch.setattr(material_store, "get_storage", lambda: backend)
    return backend


def _pa66() -> Material:
    return Material(
        name="PA66-GF30 eigen",
        kind=MaterialKind.PLASTIC,
        elastic_modulus_mpa=5200.0,
        poisson_ratio=0.38,
        density_kg_m3=1360.0,
        sigma_hlim_mpa=52.0,
        sigma_flim_mpa=28.0,
        allowable_temperature_c=120.0,
    )


def test_user_material_roundtrip(isolated_storage) -> None:
    """Save → list → merge → delete; the record survives with source='user'."""
    assert material_store.list_user_materials() == []
    saved = material_store.save_user_material(_pa66())
    assert saved.source == "user"
    listed = material_store.list_user_materials()
    assert [m.name for m in listed] == ["PA66-GF30 eigen"]
    assert listed[0].elastic_modulus_mpa == pytest.approx(5200.0)
    merged = material_store.all_materials()
    assert set(CATALOG) <= set(merged)  # built-ins always present, user record appended
    assert "PA66-GF30 eigen" in merged
    assert material_store.delete_user_material("PA66-GF30 eigen") is True
    assert material_store.delete_user_material("PA66-GF30 eigen") is False
    assert "PA66-GF30 eigen" not in material_store.all_materials()


def test_builtin_names_are_immutable(isolated_storage) -> None:
    """Built-in catalog entries can be neither overwritten nor deleted."""
    clash = _pa66().model_copy(update={"name": "20MnCr5"})
    with pytest.raises(ValueError, match="built-in"):
        material_store.save_user_material(clash)
    with pytest.raises(ValueError, match="built-in"):
        material_store.delete_user_material("20MnCr5")


def test_slug_collision_rejected(isolated_storage) -> None:
    """Two names mapping to one storage slug must not silently share a record."""
    material_store.save_user_material(_pa66().model_copy(update={"name": "PA66 eigen"}))
    other = _pa66().model_copy(update={"name": "PA66_eigen"})  # same slug PA66_eigen
    with pytest.raises(ValueError, match="collides"):
        material_store.save_user_material(other)


def test_material_api_crud_and_catalog(isolated_storage) -> None:
    """PUT/DELETE /api/materials/user + the merged catalog + dynamic schema options."""
    client = TestClient(create_app())
    body = {
        "name": "S355 eigen",
        "kind": "steel",
        "elastic_modulus_mpa": 205000.0,
        "poisson_ratio": 0.3,
        "density_kg_dm3": 7.85,
        "sigma_hlim_mpa": 900.0,
        "sigma_flim_mpa": 300.0,
    }
    res = client.put("/api/materials/user", json=body)
    assert res.status_code == 200
    out = res.json()
    assert out["builtin"] is False
    assert out["kind"] == "steel"
    assert out["density_kg_dm3"] == pytest.approx(7.85)
    # merged catalog: built-ins flagged, the user record appended
    cat = client.get("/api/materials/catalog").json()
    by_name = {m["name"]: m for m in cat}
    assert by_name["20MnCr5"]["builtin"] is True
    assert by_name["S355 eigen"]["builtin"] is False
    assert by_name["S355 eigen"]["is_default_for_kind"] is False
    # /api/ui-schema serves the CURRENT names as mat_name options
    schema = client.get("/api/ui-schema").json()
    options = [o["value"] for o in schema["attributes"]["mat_name"]["options"]]
    assert "S355 eigen" in options
    assert set(CATALOG) <= set(options)
    # upsert: a second PUT with changed values updates in place
    res = client.put("/api/materials/user", json={**body, "sigma_flim_mpa": 320.0})
    assert res.status_code == 200
    cat = client.get("/api/materials/catalog").json()
    assert next(m for m in cat if m["name"] == "S355 eigen")["sigma_flim_mpa"] == 320.0
    # built-in guard + delete + 404
    assert client.put("/api/materials/user", json={**body, "name": "20MnCr5"}).status_code == 422
    assert client.delete("/api/materials/user/20MnCr5").status_code == 422
    assert client.delete("/api/materials/user/S355 eigen").status_code == 204
    assert client.delete("/api/materials/user/S355 eigen").status_code == 404
    options = [
        o["value"] for o in client.get("/api/ui-schema").json()["attributes"]["mat_name"]["options"]
    ]
    assert "S355 eigen" not in options
