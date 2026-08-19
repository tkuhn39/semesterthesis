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


def test_fillet_spec_kind_approach_schema() -> None:
    """kind+approach schema: legacy payloads keep working (family default), the Frühe tilted
    ellipse is selectable and digs below the standard root circle, invalid combos and
    not-yet-implemented approaches are rejected with 422."""
    res = client.post(
        "/api/mesh/contour",
        json={
            "stage": _FREE_STAGE,
            "gear": 2,
            "fillet": {"kind": "elliptic", "approach": "fruehe", "tilt_deg": 30.0, "aspect": 3.0},
        },
    )
    assert res.status_code == 200
    body = res.json()
    pts = body["boundary_xy"]
    r_min = min(math.hypot(pts[i], pts[i + 1]) for i in range(0, len(pts), 2))
    assert r_min < body["root_diameter_mm"] / 2.0  # root diameter is a RESULT of the fit
    res = client.post(
        "/api/mesh/contour",
        json={"stage": _FREE_STAGE, "gear": 2, "fillet": {"kind": "elliptic", "approach": "landi"}},
    )
    assert res.status_code == 200  # Landi default: D1 = d_Ff, D2 = gap centreline on d_f
    res = client.post(
        "/api/mesh/contour",
        json={"stage": _FREE_STAGE, "gear": 2, "fillet": {"kind": "bezier", "approach": "dong"}},
    )
    assert res.status_code == 200
    assert res.json()["fillet_approach"] == "dong"
    res = client.post(
        "/api/mesh/fillet-cao",
        json={"stage": _FREE_STAGE, "gear": 2, "cao_iterations": 2},
    )
    assert res.status_code == 200
    body = res.json()
    # diagnostics only since 2026-08-18 (audit COV-15): histories + converged; the
    # contour/clearance echo lives in /api/mesh/contour (interference still 422s here)
    assert set(body) == {"gear", "converged", "sigma_history_mpa", "uniformity_history"}
    assert 1 <= len(body["sigma_history_mpa"]) <= 2
    for bad in (
        {"kind": "bezier", "approach": "kassem"},  # wrong family
        {"kind": "trochoid", "approach": "kassem"},  # trochoid takes no approach
        {"kind": "standard", "approach": "kassem"},  # standard takes no approach
    ):
        res = client.post("/api/mesh/contour", json={"gear": 2, "fillet": bad})
        assert res.status_code == 422, bad


def test_deck_download_with_steel_shell() -> None:
    """ADR-021 slot semantics: gear 1 = steel pinion (z51, at the origin/left, rigid under
    the shell rule), gear 2 = plastic wheel (z52, at the centre distance/right, deformable,
    angle-driven), axial offsets parametric per input slot."""
    res = client.post(
        "/api/mesh/deck",
        json={
            "steel_shell": True,
            "face_layers": 2,
            "n_roll_positions": 4,
            "axial_offset_gear2_mm": 1.0,
        },
    )
    assert res.status_code == 200
    deck = res.text
    assert "*PART, NAME=Part_Rad_Vz_1" in deck
    assert "Gear 1: z=51" in deck and "Gear 2: z=52" in deck  # STE order, header table
    assert "axis at (0, 0)" in deck.split("Gear 2")[0]  # gear 1 at the origin (rig: left)
    assert "ELSET=Rad_Vz_1.ALL_ELEMENTS_Part_Rad_Vz_1" in deck  # rigid steel pinion
    assert "TIE NSET=Fesselung_Rad2" in deck  # plastic wheel stays deformable
    assert "mid-plane z=1 mm" in deck  # gear-2 axial offset lands in the header table
    assert "Rot_Node_Rad2, 6, 6" in deck  # the plastic side (gear 2) is angle-driven


def test_mesh_fineness_per_gear() -> None:
    """FVA mesh-fineness dialog (user point 7): thickness factor splits the tip-land band,
    the preview reports the effective per-tooth counts, and the deck honours *_gear2."""
    res = client.post("/api/mesh/preview", json={"gear": 2})
    assert res.status_code == 200
    base = res.json()
    assert base["elements_flank"] > 10 and base["elements_root"] > 20
    res = client.post("/api/mesh/preview", json={"gear": 2, "refine_thickness": 2})
    assert res.status_code == 200
    body = res.json()
    assert body["cells_below_035"] == 0  # land-only seeding keeps the chamfer cells intact
    assert body["elements_thickness"] > 1.5 * base["elements_thickness"]
    assert body["elements_flank"] == base["elements_flank"]  # bands are independent
    # per-gear deck fineness: only gear 2 grows
    r1 = client.post(
        "/api/mesh/pair",
        json={"face_layers": 2, "n_roll_positions": 3, "refine_flank_gear2": 2},
    )
    assert r1.status_code == 200
    b1 = r1.json()
    r0 = client.post("/api/mesh/pair", json={"face_layers": 2, "n_roll_positions": 3})
    b0 = r0.json()
    assert b1["gear1"]["n_elements"] == b0["gear1"]["n_elements"]
    assert b1["gear2"]["n_elements"] > b0["gear2"]["n_elements"]


def test_pair_assembly_is_the_deck_positioning() -> None:
    """/api/mesh/pair serves THE deck assembly (SSOT): closing rotation baked in, edge-start
    angle schedule with kinematic coupling, rigid shell on the steel slot."""
    res = client.post(
        "/api/mesh/pair",
        json={"face_layers": 2, "n_roll_positions": 5, "steel_shell": True},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["driven_gear"] == 2  # plastic side (kst-E: gear 2) is angle-driven
    assert abs(body["center_distance_mm"] - 52.0) < 1e-6
    assert body["closing_rad"] != 0.0  # single-flank contact alignment applied
    assert len(body["contact_pairs"]) == 7  # sweep-union reference pairs
    g1, g2 = body["gear1"], body["gear2"]
    assert g1["rigid_shell"] is True and g2["rigid_shell"] is False
    assert g1["center"] == [0.0, 0.0] and g2["center"][0] > 50.0
    # schedule: driven gear from −roll/2 in steps of roll/(n−1); gear 1 counter-rotates by z2/z1
    roll = 3.0 * 2.0 * math.pi / 52.0
    assert abs(body["roll_angle_rad"] - roll) < 1e-12
    assert abs(g2["start_angle_rad"] + roll / 2.0) < 1e-12
    assert abs(g2["step_angle_rad"] - roll / 4.0) < 1e-12
    assert abs(g1["start_angle_rad"] - roll / 2.0 * 52.0 / 51.0) < 1e-12
    assert abs(g1["step_angle_rad"] + roll / 4.0 * 52.0 / 51.0) < 1e-12
    # payload consistency: quad indices address the vertex list
    for g in (g1, g2):
        assert len(g["faces"]) % 4 == 0 and len(g["vertices"]) % 3 == 0
        assert max(g["faces"]) < len(g["vertices"]) // 3
    assert len(g1["vertices"]) < len(g2["vertices"])  # R3D4 shell ≪ solid hull? (lateral only)


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
        # per-gear tools survive the import (kst-E: h_aP0* 1.1/1.25, edge break wheel-only)
        assert params["tool_addendum_factor"] == 1.1
        assert params["tool_addendum_factor_gear2"] == 1.25
        assert params["tool_edge_break_angle_deg"] is None
        assert params["tool_edge_break_angle_deg_gear2"] == 45.0
        assert params["tool_root_form_height_factor_gear2"] == 0.8456


def test_per_gear_tool_fields_change_only_their_gear() -> None:
    """A deeper gear-2 tool (h_aP0*↑) cuts a smaller gear-2 root; gear 1 is untouched."""

    def roots(stage: dict[str, object]) -> tuple[float, float]:
        out = []
        for gear in (1, 2):
            res = client.post("/api/mesh/contour", json={"stage": stage, "gear": gear})
            assert res.status_code == 200
            out.append(res.json()["root_diameter_mm"])
        return out[0], out[1]

    base: dict[str, object] = dict(_FREE_STAGE, tool_addendum_factor=1.1)
    r1_base, r2_base = roots(base)
    r1_deep, r2_deep = roots(dict(base, tool_addendum_factor_gear2=1.3))
    assert r1_deep == r1_base  # gear-1 tool unchanged
    assert r2_deep < r2_base - 0.1  # deeper wheel tool cuts a smaller root circle


def test_tip_relief_enters_the_fe_contour() -> None:
    """Kopfrücknahme C_αa (symmetric flanks) narrows the contour near the tip only —
    the FE mesh boundary shows the modification like the FVA transient FEM."""
    relief = {"tip_relief_um": 30.0, "tip_relief_start_diameter_mm": 86.0}
    stage: dict[str, object] = dict(
        _FREE_STAGE, modifications_wheel={"left": relief, "right": relief}
    )
    plain = client.post("/api/mesh/contour", json={"stage": _FREE_STAGE, "gear": 2}).json()
    modified = client.post("/api/mesh/contour", json={"stage": stage, "gear": 2}).json()
    assert modified["usable_tip_diameter_mm"] == plain["usable_tip_diameter_mm"]  # d_Na keeps
    bx_p, bx_m = plain["boundary_xy"][0::2], modified["boundary_xy"][0::2]
    by = plain["boundary_xy"][1::2]
    radii = [2.0 * math.hypot(x, y) for x, y in zip(bx_p, by, strict=True)]
    moved = [abs(xm - xp) for xp, xm, d in zip(bx_p, bx_m, radii, strict=True) if d > 86.0 + 0.05]
    untouched = [
        abs(xm - xp) for xp, xm, d in zip(bx_p, bx_m, radii, strict=True) if d < 86.0 - 0.05
    ]
    assert max(untouched) < 1e-6  # below d_Ca nothing changes
    assert max(moved) > 0.02  # at the tip ~C_αa/cos α (30 µm+) is removed


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


def test_variation_sample_count_sobol_rounds_lhs_exact() -> None:
    """sample_count is user-controlled; Sobol rounds up to a power of two with a warning,
    LHS uses the exact count."""
    base = {
        "z1": {"vary": True, "value": 24, "min": 20, "max": 28, "steps": 5},
        "x1": {"vary": True, "value": 0.0, "min": -0.3, "max": 0.6, "steps": 5},
    }
    res = client.post("/api/variation", json={**base, "method": "sobol", "sample_count": 100})
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 128
    assert any("power of two" in w for w in body["warnings"])

    res = client.post("/api/variation", json={**base, "method": "lhs", "sample_count": 100})
    assert res.status_code == 200
    assert res.json()["count"] == 100


def test_variation_per_gear_reference_profile_rows() -> None:
    """The per-gear rows sweep for real now: varying rho_fp2 changes only gear 2's
    root safety; the point payload carries the per-gear values."""
    res = client.post(
        "/api/variation",
        json={
            "rho_fp2": {"vary": True, "value": 0.38, "min": 0.25, "max": 0.45, "steps": 3},
            "z1": {"vary": False, "value": 24, "min": 20, "max": 28},
            "x1": {"vary": False, "value": 0.0, "min": -0.3, "max": 0.6},
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 3
    pts = body["points"]
    assert {p["rho_fp2"] for p in pts} == {0.25, 0.35, 0.45}
    assert len({p["root_safety_wheel"] for p in pts}) == 3  # gear 2 responds
    assert len({p["root_safety_pinion"] for p in pts}) == 1  # gear 1 constant
    # no more "not separable" warning for the reference-profile rows
    assert not any("h_fP" in w for w in body["warnings"])
