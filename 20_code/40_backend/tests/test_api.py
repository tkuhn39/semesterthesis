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


def test_capacity_native_khb_active_and_dynamics_parity() -> None:
    """V-02: with an accuracy grade, K_Hβ > 1 falls out natively on the default (kst-E)
    stage; GAP-01: /api/dynamics with the same inputs returns the same K-factors."""
    client = TestClient(create_app())
    shared = {
        "pinion_torque_nm": 7.85,
        "pinion_speed_min1": 1000.0,
        "application_factor": 1.0,
        "accuracy_grade": 7,
    }
    cap = client.post("/api/capacity", json=shared)
    assert cap.status_code == 200
    factors = cap.json()["factors"]
    assert factors["face_load_factor"] > 1.0  # was inert 1.000 before the F_βx estimate
    assert factors["face_load_factor_root"] > 1.0
    dyn = client.post("/api/dynamics", json=shared)
    assert dyn.status_code == 200
    d = dyn.json()
    assert d["dynamic_factor"] == factors["dynamic_factor"]
    assert d["transverse_factor_flank"] == factors["transverse_factor"]
    assert d["face_load_factor_flank"] == factors["face_load_factor"]
    assert d["face_load_factor_root"] == factors["face_load_factor_root"]
    # an explicit F_βx override wins over the native estimate
    override = client.post("/api/dynamics", json={**shared, "mesh_misalignment_um": 80.0})
    assert override.status_code == 200
    assert override.json()["face_load_factor_flank"] > d["face_load_factor_flank"]


def test_geometry_report_supports_helical() -> None:
    """The SSOT report computes helical stages (DIN 21773 helical forms, NRM-01 closed):
    transverse quantities, W_k, ball measures and ε_β all come back — only the
    contour-based effective root stays None (the 2-D contour chain is spur-only)."""
    client = TestClient(create_app())
    res = client.post(
        "/api/geometry/report",
        json={
            "stage": {"use_example": False, "helix_angle_deg": 15.0},
            "fillet_gear1": {"kind": "elliptic"},
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["pair"]["helix_angle_deg"] == 15.0
    assert 0.0 < body["pair"]["base_helix_angle_deg"] < 15.0
    assert body["pair"]["overlap_ratio"] > 0.0
    assert body["pair"]["transverse_module_mm"] > body["pair"]["normal_module_mm"]
    assert body["gear1"]["span_measurement_mm"] is not None
    assert body["gear1"]["two_ball_measure_mm"] is not None
    # spur-only contour chain: no effective root for helical stages, even with a fillet
    assert body["gear1"]["effective_root_diameter_mm"] is None


def test_profile_routes_reject_helical_with_422() -> None:
    """NRM-02 follow-up (verify pass): every profile-consuming route answers a helical
    stage with 422, never a raw 500."""
    client = TestClient(create_app())
    helical_stage = {"use_example": False, "helix_angle_deg": 15.0}
    for route, payload in (
        ("/api/tooth-profile", helical_stage),
        ("/api/mesh/preview", {"stage": helical_stage}),
        ("/api/mesh/deck", {"stage": helical_stage}),
        ("/api/mesh/pair", {"stage": helical_stage}),
    ):
        res = client.post(route, json=payload)
        assert res.status_code == 422, f"{route} -> {res.status_code}"
