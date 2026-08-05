"""
@module: tests.test_geometry_report
@context: Domain-layer tests — the SSOT geometry report (DIN ISO 21771 / DIN 21773 /
          DIN 3967 / DIN 3964).
@role: Full kst-E parity for the inspection/backlash/sliding block against the STplus
       reference output (Blatt 6–8) — transcribed literals, computed on CURRENT norms.
       Documented deviations from STplus (ADR-011 "the norm wins"): the chordal thickness
       uses the DIN 21773 §5 measurement cylinder d_y = d_a − 2·m_n (STplus uses its own
       caliper-contact cylinder), and the tip tooth thickness is the as-cut value at d_Na.
"""

import math
from pathlib import Path

import pytest

from app.io.ste import Pair, gear_stage_from_ste, load_ste
from app.services.geometry.gear import GearStage
from app.services.geometry.report import compute_geometry_report

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)

pytestmark = pytest.mark.skipif(not _REF_STE.exists(), reason="STplus reference .ste not present")


@pytest.fixture(scope="module")
def report():
    data = gear_stage_from_ste(load_ste(_REF_STE))
    stage = GearStage.from_ste(data)
    up = data.tooth_width_allowance_upper_um
    low = data.tooth_width_allowance_lower_um
    return compute_geometry_report(
        stage,
        ball_diameter_mm=Pair(1.75, 1.75),
        span_allowance_upper_mm=Pair(up[0] / 1000.0, up[1] / 1000.0),
        span_allowance_lower_mm=Pair(low[0] / 1000.0, low[1] / 1000.0),
        center_distance_allowance_mm=0.015,  # DIN 3964 js7 for the kst-E case
    )


# (attribute, expected gear1, expected gear2, abs tolerance) — kst-E-ausgabe.sta Blatt 6–8
_GEAR_EXPECTED = [
    ("tooth_thickness_normal_mm", 1.719, 1.800, 1e-3),
    ("space_width_normal_mm", 1.423, 1.342, 1e-3),
    ("span_teeth", 6, 6, 0),
    ("span_measurement_mm", 17.090, 17.180, 1e-3),
    ("span_contact_diameter_mm", 50.788, 51.728, 1e-3),
    ("two_ball_measure_mm", 53.846, 55.064, 1e-3),
    ("two_roller_measure_mm", 53.846, 55.064, 1e-3),
    ("ball_contact_diameter_mm", 50.779, 52.146, 1e-3),
    ("thickness_allowance_upper_mm", -0.296, -0.220, 5e-4),
    ("ball_allowance_factor", 2.489, 2.415, 1e-3),
    ("usable_root_diameter_mm", 50.391, 51.315, 1e-3),
    ("form_reserve_mm", 0.655, 0.578, 1.5e-3),
    ("tooth_height_mm", 2.250, 2.249, 1e-3),
    ("addendum_mm", 0.947, 1.011, 1e-3),
    ("addendum_factor_actual", 0.744, 0.697, 1e-3),
    ("tip_clearance_mm", 0.791, 0.792, 1e-3),
    ("tip_path_of_contact_mm", 1.771, 1.635, 1e-3),
    ("sliding_factor_tip", 0.136, 0.126, 5e-4),
    ("specific_sliding_tip", 0.313, 0.294, 5e-4),
    ("specific_sliding_root", -0.416, -0.457, 1e-3),
    ("rest_tip_thickness_mm", 0.672, 0.634, 1e-3),
    ("generation_profile_shift", -0.2030, 0.0117, 5e-4),
]


@pytest.mark.parametrize(("attr", "e1", "e2", "tol"), _GEAR_EXPECTED, ids=lambda v: str(v))
def test_gear_values_match_reference(report, attr, e1, e2, tol) -> None:
    v1, v2 = getattr(report.gear1, attr), getattr(report.gear2, attr)
    if tol == 0:
        assert (v1, v2) == (e1, e2)
    else:
        assert v1 == pytest.approx(e1, abs=tol)
        assert v2 == pytest.approx(e2, abs=tol)


def test_pair_values_match_reference(report) -> None:
    p = report.pair
    assert p.common_tooth_height_mm == pytest.approx(1.341, abs=1e-3)
    assert p.common_height_factor == pytest.approx(1.341, abs=1e-3)
    assert p.backlash_circumferential_mm == pytest.approx(0.521, abs=1e-3)
    assert p.backlash_normal_mm == pytest.approx(0.485, abs=1e-3)
    assert p.transverse_pitch_mm == pytest.approx(3.142, abs=1e-3)
    assert p.normal_pitch_mm == pytest.approx(3.142, abs=1e-3)
    assert p.normal_base_pitch_mm == pytest.approx(2.952, abs=1e-3)
    assert p.transverse_base_pitch_mm == pytest.approx(2.952, abs=1e-3)
    assert p.backlash_delta_upper_mm == pytest.approx((0.012, 0.011), abs=5e-4)
    assert p.backlash_delta_lower_mm == pytest.approx((-0.012, -0.011), abs=5e-4)
    assert p.gear_ratio == pytest.approx(52.0 / 51.0, abs=1e-9)


def test_chordal_thickness_is_norm_conform(report) -> None:
    """DIN 21773 §5 with d_y = d_a − 2·m_n (the norm's suggested measurement cylinder).

    STplus prints 1.723/1.808 on ITS caliper-contact cylinder — a tool convention, not the
    norm's; per ADR-011 the norm value is reported. Sanity: the chord is close to (and
    consistent with) the arc thickness at d_y, and the chordal height stays near 1·m_n.
    """
    for gear, d_a in ((report.gear1, 52.894), (report.gear2, 54.022)):
        assert gear.chordal_thickness_mm == pytest.approx(gear.tooth_thickness_normal_mm, abs=0.06)
        assert 0.9 < gear.chordal_height_mm < 1.1
        assert gear.chordal_height_mm < (d_a - 47.0) / 2.0  # sane band


def test_undercut_check_present(report) -> None:
    assert report.gear1.has_undercut is False
    assert report.gear2.has_undercut is False
    assert report.gear1.undercut_min_shift is not None


def test_effective_root_diameter_passthrough() -> None:
    data = gear_stage_from_ste(load_ste(_REF_STE))
    stage = GearStage.from_ste(data)
    rep = compute_geometry_report(stage, fillet_contour_min_radius_mm=Pair(23.852, 24.476))
    assert rep.gear1.effective_root_diameter_mm == pytest.approx(47.704, abs=1e-6)
    assert rep.gear2.effective_root_diameter_mm == pytest.approx(48.952, abs=1e-6)
    # Frühe digs below the tool root circle — the report carries both values side by side
    assert rep.gear1.effective_root_diameter_mm < rep.gear1.root_diameter_mm


def test_report_without_allowances_has_no_backlash() -> None:
    data = gear_stage_from_ste(load_ste(_REF_STE))
    stage = GearStage.from_ste(data)
    rep = compute_geometry_report(stage)
    assert rep.pair.backlash_normal_mm is None
    assert rep.gear1.thickness_allowance_upper_mm is None
    assert rep.gear1.span_measurement_mm is not None  # nominal measures still computed
    assert rep.gear1.two_ball_measure_mm is not None
    assert math.isclose(rep.gear1.ball_diameter_mm, 1.75, abs_tol=1e-9)  # 1.75·m_n default
