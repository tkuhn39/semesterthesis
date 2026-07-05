"""
@module: tests.test_line_of_action
@context: Domain-layer tests — the transverse line of action T1/A/B/C/D/E.
@role: The point construction reproduces the FVA Gesamtsystemreport reference plot
       (kst-E, 3000_16_lin) after the frame transform (FVA: gear 2 on +y at (0, a);
       ours: gear 2 on +x at (a, 0) → (x, y) = (y_fva, −x_fva)), and the internal
       relations hold: |E−A| = g_α (ISO 21771 eq. 77), |B−E| = |D−A| = p_et,
       |O₁T₁| = r_b1, |O₂T₂| = r_b2, C on the centre line at r_w1.
"""

import math
from pathlib import Path

import pytest

from app.io.ste import gear_stage_from_ste, load_ste
from app.services.geometry.gear import GearStage, line_of_action_points

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)

# FVA Gesamtsystemreport 3000_16_lin, diagram "Zahneingriff" (points_x/points_y),
# transformed into our frame: (x, y) = (y_fva, −x_fva)
_FVA_POINTS = {
    "t1": (22.30056840284508, 8.767545179757299),
    "t2": (29.26213754694489, -8.939457830340777),
    "a": (25.149086815978347, 1.5222355273466341),
    "b": (25.31542730195159, 1.0991424825370806),
    "c": (25.747558949923622, 0.0),
    "d": (26.229245856242745, -1.2251880752123765),
    "e": (26.39558634221599, -1.6482811200219296),
}


@pytest.fixture(scope="module")
def stage() -> GearStage:
    if not _REF_STE.exists():
        pytest.skip("kst-E reference .ste not present")
    return GearStage.from_ste(gear_stage_from_ste(load_ste(_REF_STE)))


def test_points_match_fva_reference(stage: GearStage) -> None:
    loa = line_of_action_points(stage)
    assert loa is not None
    for name, (x_ref, y_ref) in _FVA_POINTS.items():
        px, py = getattr(loa, name)
        assert px == pytest.approx(x_ref, abs=2e-3), name
        assert py == pytest.approx(y_ref, abs=2e-3), name


def test_internal_relations(stage: GearStage) -> None:
    loa = line_of_action_points(stage)
    assert loa is not None
    # tangent points sit on the base circles (T1 from O1, T2 from O2)
    a_w = stage.working_center_distance_mm
    assert math.hypot(*loa.t1) == pytest.approx(stage.base_diameter_mm[0] / 2.0, abs=1e-6)
    assert math.hypot(loa.t2[0] - a_w, loa.t2[1]) == pytest.approx(
        stage.base_diameter_mm[1] / 2.0, abs=1e-6
    )
    # pitch point on the centre line at the working pitch radius
    assert loa.c == (pytest.approx(stage.working_pitch_diameter_mm[0] / 2.0), 0.0)
    # |E−A| is exactly the ISO 21771 path of contact, B/E and A/D one base pitch apart
    g = math.hypot(loa.e[0] - loa.a[0], loa.e[1] - loa.a[1])
    assert g == pytest.approx(stage.path_of_contact_mm, abs=1e-9)
    assert math.hypot(loa.b[0] - loa.e[0], loa.b[1] - loa.e[1]) == pytest.approx(
        stage.transverse_base_pitch_mm, abs=1e-9
    )
    assert math.hypot(loa.d[0] - loa.a[0], loa.d[1] - loa.a[1]) == pytest.approx(
        stage.transverse_base_pitch_mm, abs=1e-9
    )
    # A and E lie between the tangent points (active path inside T1–T2)
    t = [
        (p[0] - loa.t1[0]) * (loa.t2[0] - loa.t1[0]) + (p[1] - loa.t1[1]) * (loa.t2[1] - loa.t1[1])
        for p in (loa.a, loa.e)
    ]
    span = (loa.t2[0] - loa.t1[0]) ** 2 + (loa.t2[1] - loa.t1[1]) ** 2
    assert all(0.0 < ti < span for ti in t)


def test_api_tooth_profile_carries_line_of_action() -> None:
    if not _REF_STE.exists():
        pytest.skip("kst-E reference .ste not present")
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    res = client.post("/api/tooth-profile", json={"use_example": True})
    assert res.status_code == 200
    loa = res.json()["line_of_action"]
    assert loa is not None
    assert loa["c"][0] == pytest.approx(25.7476, abs=1e-3)
    assert loa["path_of_contact_mm"] == pytest.approx(3.4067, abs=2e-3)
