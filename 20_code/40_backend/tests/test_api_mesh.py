"""
@module: tests.test_api_mesh
@context: API-layer tests — mesh preview/3D/convergence/fillet/deck + design endpoints (M4–M6).
@role: The mesh router serves the transplant sector (2-D preview + 3-D hull), the density
       convergence quick check, the fillet ranking/sweep and the implicit deck download with
       the rigid-shell rule — all from the shared StageParams (kst-E example or free
       parameters); the design router provides presets and the STplus text import.
"""

import math
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())

_FREE_STAGE = {
    "use_example": False,
    "normal_module_mm": 2.0,
    "teeth_pinion": 20,
    "teeth_wheel": 41,
    "profile_shift_pinion": 0.3,
    "profile_shift_wheel": 0.1,
    "face_width_pinion_mm": 20.0,
    "face_width_wheel_mm": 20.0,
}


def test_mesh_preview_reference_topology() -> None:
    res = client.post("/api/mesh/preview", json={"gear": 2})
    assert res.status_code == 200
    body = res.json()
    assert body["n_quads"] == 3024  # reference sector signature at density 1
    assert body["min_scaled_jacobian"] >= 0.35
    assert body["cells_below_035"] == 0
    assert len(body["nodes_xy"]) == 2 * body["n_nodes"]
    assert len(body["quads"]) == 4 * body["n_quads"]


def test_mesh_preview_free_stage_and_fillet() -> None:
    res = client.post(
        "/api/mesh/preview",
        json={"stage": _FREE_STAGE, "gear": 2, "fillet": {"kind": "bezier", "be": 0.57}},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["n_quads"] == 3024
    assert body["cells_below_035"] == 0


def test_mesh_3d_hull() -> None:
    res = client.post("/api/mesh/3d?layers=2", json={"gear": 2})
    assert res.status_code == 200
    body = res.json()
    assert body["n_hexes"] == 3024 * 2
    assert len(body["faces"]) % 4 == 0
    assert len(body["face_quality"]) == len(body["faces"]) // 4
    assert max(body["faces"]) < len(body["vertices"]) // 3
    assert body["face_width_mm"] > 0.0


def test_mesh_convergence_endpoint() -> None:
    res = client.post("/api/mesh/convergence", json={"gear": 2, "target": "root", "levels": [1, 2]})
    assert res.status_code == 200
    body = res.json()
    assert body["converged_level"] == 1
    assert len(body["sigma_mpa"]) == 2


def test_fillet_sweep_recommends_feasible_optimum() -> None:
    res = client.post("/api/mesh/fillet-sweep", json={"gear": 2, "kind": "bezier", "points": 3})
    assert res.status_code == 200
    body = res.json()
    assert body["parameter"] == "be"
    assert len(body["values"]) == 3
    assert body["best_value"] is not None
    assert body["best_sigma_mpa"] < body["standard_sigma_mpa"]  # Bézier beats the ρ_F arc


def test_tooth_contour_example_and_variant() -> None:
    res = client.post("/api/mesh/contour", json={"gear": 2})
    assert res.status_code == 200
    body = res.json()
    assert body["teeth"] == 52
    assert body["clearance_mm"] is None
    # the drawn envelope is completed across the root land: the boundary starts on the
    # gap centreline (half-pitch off the tooth centre), not at the fillet tangent point
    x0, y0 = body["boundary_xy"][0], body["boundary_xy"][1]
    gap_angle = math.pi / 2.0 - math.pi / body["teeth"]  # right gap centre, tooth centre = +y
    assert math.isclose(math.atan2(y0, x0), gap_angle, abs_tol=1e-6)
    assert math.isclose(math.hypot(x0, y0), body["root_diameter_mm"] / 2.0, rel_tol=1e-6)
    # free variant with an optimized fillet reports its clearance
    res = client.post(
        "/api/mesh/contour",
        json={"stage": _FREE_STAGE, "gear": 2, "fillet": {"kind": "elliptic", "e_f": -0.1}},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["teeth"] == 41
    assert body["clearance_mm"] is not None and body["clearance_mm"] > 0.0
    # the exact DIN 3960 trochoid is a first-class strategy
    res = client.post("/api/mesh/contour", json={"gear": 2, "fillet": {"kind": "trochoid"}})
    assert res.status_code == 200
    assert res.json()["fillet_kind"] == "trochoid"


def test_deck_download_with_steel_shell() -> None:
    """ADR-021 numbering: gear 1 = steel pinion (z51, rigid under the shell rule),
    gear 2 = plastic wheel (z52, deformable, angle-driven), axial offsets parametric."""
    res = client.post(
        "/api/mesh/deck",
        json={
            "steel_shell": True,
            "face_layers": 2,
            "n_roll_positions": 4,
            "axial_offset_wheel_mm": 1.0,
        },
    )
    assert res.status_code == 200
    deck = res.text
    assert "*PART, NAME=Part_Rad_Vz_1" in deck
    assert "Gear 1: z=51" in deck and "Gear 2: z=52" in deck  # STE order, header table
    assert "ELSET=Rad_Vz_1.ALL_ELEMENTS_Part_Rad_Vz_1" in deck  # rigid steel pinion
    assert "TIE NSET=Fesselung_Rad2" in deck  # plastic wheel stays deformable
    assert "mid-plane z=1 mm" in deck  # wheel axial offset lands in the header table
    assert "Rot_Node_Rad2, 6, 6" in deck  # the wheel is the angle-driven gear


def test_presets_and_ste_import() -> None:
    res = client.get("/api/presets")
    assert res.status_code == 200
    body = res.json()
    assert body["presets"][0]["id"] == "kst-e"
    assert body["presets"][0]["params"]["teeth_wheel"] == 52
    assert "din3972-i" in body["tools"]

    ste = (
        Path(__file__).resolve().parents[3]
        / "30_references_and_examples"
        / "33_STplus"
        / "kst-E_eingabe.ste"
    )
    if ste.exists():
        res = client.post("/api/import/ste", json={"content": ste.read_text(encoding="latin-1")})
        assert res.status_code == 200
        params = res.json()["params"]
        assert params["teeth_pinion"] == 51 and params["teeth_wheel"] == 52
        assert params["use_example"] is False


def test_variation_material_matrix() -> None:
    """Material matrix: steel/steel runs through the same kernel (per-gear dispatch)."""
    res = client.post(
        "/api/variation",
        json={
            "pinion_material": "steel",
            "wheel_material": "steel",
            "z1": {"vary": True, "value": 24, "min": 20, "max": 26, "steps": 4},
        },
    )
    assert res.status_code == 200
    assert res.json()["count"] >= 4


def test_micro_geometry_symmetry_policy() -> None:
    """Asymmetric per-flank micro-geometry data drops mirror symmetry (teeth stay congruent)."""
    stage: dict[str, object] = dict(_FREE_STAGE)
    stage["modifications_wheel"] = {
        "left": {"tip_relief_um": 20.0},
        "right": {"tip_relief_um": 0.0},
    }
    res = client.post("/api/mesh/preview", json={"stage": stage, "gear": 2})
    assert res.status_code == 200
    assert res.json()["cells_below_035"] == 0
