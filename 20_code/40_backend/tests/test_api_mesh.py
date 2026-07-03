"""
@module: tests.test_api_mesh
@context: API-layer tests — mesh preview/3D/convergence/deck endpoints (plan v2, M4).
@role: The mesh router serves the transplant sector (2-D preview + 3-D hull), the density
       convergence quick check, the fillet ranking, and the implicit deck download with the
       mixed-pairing rigid-shell rule — all stateless from the kst-E example stage.
"""

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_mesh_preview_reference_topology() -> None:
    res = client.post("/api/mesh/preview", json={"gear": 2})
    assert res.status_code == 200
    body = res.json()
    assert body["n_quads"] == 3024  # reference sector signature at density 1
    assert body["min_scaled_jacobian"] >= 0.35
    assert body["cells_below_035"] == 0
    assert len(body["nodes_xy"]) == 2 * body["n_nodes"]
    assert len(body["quads"]) == 4 * body["n_quads"]
    assert len(body["quality"]) == body["n_quads"]


def test_mesh_preview_refined_and_fillet() -> None:
    res = client.post(
        "/api/mesh/preview",
        json={"gear": 2, "refine_root": 2, "fillet": {"kind": "bezier", "be": 0.57}},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["n_quads"] > 3024
    assert body["cells_below_035"] == 0


def test_mesh_3d_hull() -> None:
    res = client.post("/api/mesh/3d?layers=2", json={"gear": 2})
    assert res.status_code == 200
    body = res.json()
    assert body["n_hexes"] == 3024 * 2
    assert len(body["faces"]) % 4 == 0
    assert len(body["face_quality"]) == len(body["faces"]) // 4
    assert len(body["vertices"]) % 3 == 0
    assert max(body["faces"]) < len(body["vertices"]) // 3


def test_mesh_convergence_endpoint() -> None:
    res = client.post("/api/mesh/convergence", json={"gear": 2, "target": "root", "levels": [1, 2]})
    assert res.status_code == 200
    body = res.json()
    assert body["converged_level"] == 1
    assert len(body["sigma_mpa"]) == 2


def test_deck_download_with_steel_shell() -> None:
    res = client.post(
        "/api/mesh/deck",
        json={"steel_shell": True, "face_layers": 2, "n_roll_positions": 4},
    )
    assert res.status_code == 200
    deck = res.text
    assert "*PART, NAME=Part_Rad_Vz_1" in deck
    assert "ELSET=Rad_Vz_2.ALL_ELEMENTS_Part_Rad_Vz_2" in deck  # rigid steel side
    assert "TIE NSET=Fesselung_Rad1" in deck  # plastic side stays deformable
    assert "attachment" in res.headers.get("content-disposition", "")


def test_tooth_contour_example_and_variant() -> None:
    # kst-E wheel, standard fillet
    res = client.post("/api/mesh/contour", json={"gear": 2})
    assert res.status_code == 200
    body = res.json()
    assert body["teeth"] == 52
    assert len(body["boundary_xy"]) >= 200
    assert body["clearance_mm"] is None
    # free variant with an optimized fillet reports its clearance
    res = client.post(
        "/api/mesh/contour",
        json={
            "gear": 2,
            "use_example": False,
            "normal_module_mm": 2.0,
            "teeth_pinion": 20,
            "teeth_wheel": 41,
            "profile_shift_pinion": 0.3,
            "profile_shift_wheel": 0.1,
            "fillet": {"kind": "elliptic", "e_f": -0.1},
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["teeth"] == 41
    assert body["fillet_kind"] == "elliptic"
    assert body["clearance_mm"] is not None and body["clearance_mm"] > 0.0
