"""
@module: tests.test_fem_results
@context: API layer — the FEM results upload + path-of-contact transformation (phase G).
@role: ``POST /api/fem/results`` unwraps the Abaqus dump's flank radii onto the line of
       action (ξ relative to C, gear-signed) using THE GearStage quantities, and returns
       the A…E markers plus the extended d_Nf…d_Na range — verified against the analytic
       line-of-action helper on the kst-E stage.
"""

import math

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def _dump(frames: list[dict]) -> dict:
    return {"schema": "zahnfuss.fem_results/1", "mode": "position_series", "frames": frames}


def _node(r: float, z: float, mises: float = 10.0, cpress: float = 5.0) -> dict:
    return {
        "id": 1,
        "r": r,
        "z": z,
        "s_mises": mises,
        "s_maxp": mises,
        "s_minp": -1.0,
        "e_mises": 0.001,
        "e_maxp": 0.001,
        "cpress": cpress,
        "u": 0.01,
    }


def test_fem_results_unwraps_onto_the_line_of_action() -> None:
    """ξ(r) matches the analytic A/E terms: a gear-1 node at d_Na1/2 lands exactly on E,
    a gear-2 node at d_Na2/2 exactly on A; the pitch radii land on C (ξ = 0)."""
    # kst-E analytics (from /api/tooth-profile's line of action, ISO 21771 eq. 77 terms)
    geo = client.post("/api/tooth-profile", json={}).json()
    loa = geo["line_of_action"]
    r_na1 = geo["pinion"]["tip_radius_mm"]  # gear 1: no chamfer → d_Na = d_a
    d_na2 = 2.0 * geo["wheel"]["tip_radius_mm"] - 2.0 * 0.117  # wheel chamfer h_K
    rw1 = loa["working_pitch_radius_mm"][0]
    rw2 = loa["working_pitch_radius_mm"][1]

    frames = [
        {
            "index": 1,
            "phi_driven_rad": -0.18,
            "flanks": {
                "G1T002F2": [_node(r_na1, -2.0), _node(rw1, -2.0), _node(rw1, 2.0)],
                "G2T004F2": [_node(0.5 * d_na2, 0.0, mises=42.0, cpress=77.0), _node(rw2, 0.0)],
            },
        }
    ]
    res = client.post("/api/fem/results", json={"results": _dump(frames)})
    assert res.status_code == 200
    body = res.json()
    assert body["n_frames"] == 1
    assert body["flank_tags"] == ["G1T002F2", "G2T004F2"]

    markers = body["markers"]
    # A/E from the same terms as the verified line-of-action helper
    xi_e = math.dist(loa["e"], loa["c"])
    xi_a = -math.dist(loa["a"], loa["c"])
    assert abs(markers["e"] - xi_e) < 5e-3
    assert abs(markers["a"] - xi_a) < 5e-3
    assert markers["c"] == 0.0
    assert markers["xi_min"] <= markers["a"] and markers["xi_max"] >= markers["e"]
    assert abs((markers["d"] - markers["a"]) - markers["transverse_base_pitch_mm"]) < 1e-6

    flank1 = body["frames"][0]["flanks"]["G1T002F2"]
    assert abs(flank1["xi"][0] - xi_e) < 5e-3  # gear-1 tip node lands on E
    assert abs(flank1["xi"][1]) < 5e-3  # pitch radius lands on C
    assert flank1["n_z"] == 2  # two z planes → grid hint
    flank2 = body["frames"][0]["flanks"]["G2T004F2"]
    assert abs(flank2["xi"][0] - xi_a) < 5e-3  # gear-2 tip node lands on A (negative side)
    assert flank2["max_mises"] == 42.0 and flank2["max_cpress"] == 77.0


def test_fem_results_rejects_foreign_json() -> None:
    res = client.post("/api/fem/results", json={"results": {"schema": "other/1"}})
    assert res.status_code == 422
    res = client.post("/api/fem/results", json={"results": _dump([])})
    assert res.status_code == 422
