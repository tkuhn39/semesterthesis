"""
@module: tests.test_geometry
@context: Domain-layer tests — gear geometry.
@role: Validate the involute gear-stage geometry against STplus / FVA-Workbench
       (ISO 21771) output for the project gear, plus the generated-center-distance
       path and the involute round-trip.
"""

import math
from pathlib import Path

import pytest

from app.io.ste import Pair, gear_stage_from_ste, load_ste
from app.services.geometry.gear import GearStage, inverse_involute, involute

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)

# Project gear; reference values are STplus / FVA-Workbench (ISO 21771) output.
KST_E = GearStage(
    normal_module_mm=1.0,
    teeth=Pair(51, 52),
    normal_pressure_angle_deg=20.0,
    helix_angle_deg=0.0,
    profile_shift=Pair(0.2034, 0.3143),
    center_distance_mm=52.0,
)


def test_kst_e_matches_stplus() -> None:
    """Core geometry reproduces the STplus/Workbench output exactly."""
    assert KST_E.reference_diameter_mm == pytest.approx((51.0, 52.0))
    assert KST_E.transverse_pressure_angle_deg == pytest.approx(20.0)
    assert KST_E.working_pressure_angle_deg == pytest.approx(21.46, abs=0.02)
    assert KST_E.working_center_distance_mm == pytest.approx(52.0)
    assert KST_E.working_pitch_diameter_mm == pytest.approx((51.495, 52.505), abs=0.005)
    assert KST_E.base_diameter_mm == pytest.approx((47.924, 48.864), abs=0.005)


def test_zero_profile_shift_generated_center_distance() -> None:
    """Without center distance and x=0: working angle == transverse angle and the
    generated center distance equals the reference center distance."""
    g = GearStage(normal_module_mm=2.0, teeth=Pair(20, 40))
    assert g.working_pressure_angle_deg == pytest.approx(20.0, abs=1e-6)
    assert g.working_center_distance_mm == pytest.approx(60.0, abs=1e-6)


def test_inverse_involute_roundtrip() -> None:
    """inverse_involute is the inverse of involute over the relevant range."""
    for deg in (15.0, 20.0, 25.0, 30.0):
        angle = math.radians(deg)
        assert inverse_involute(involute(angle)) == pytest.approx(angle, abs=1e-9)


@pytest.mark.skipif(not _REF_STE.exists(), reason="STplus reference .ste not present")
def test_from_ste_reference() -> None:
    """Building from the real STplus input reproduces the STplus geometry."""
    g = GearStage.from_ste(gear_stage_from_ste(load_ste(_REF_STE)))
    assert g.reference_diameter_mm == pytest.approx((51.0, 52.0))
    assert g.working_center_distance_mm == pytest.approx(52.0)
    assert g.working_pitch_diameter_mm == pytest.approx((51.495, 52.505), abs=0.005)


@pytest.mark.skipif(not _REF_STE.exists(), reason="STplus reference .ste not present")
def test_contact_ratio_from_ste() -> None:
    """The contact ratio uses d_Na = d_Fa (tip chamfer accounted for) and matches STplus."""
    g = GearStage.from_ste(gear_stage_from_ste(load_ste(_REF_STE)))
    assert g.usable_tip_diameter_mm == pytest.approx((52.894, 53.788), abs=2e-3)
    assert g.transverse_base_pitch_mm == pytest.approx(2.952, abs=2e-3)
    assert g.path_of_contact_mm == pytest.approx(3.406, abs=2e-3)
    assert g.transverse_contact_ratio == pytest.approx(1.154, abs=2e-3)
    assert g.overlap_ratio == pytest.approx(0.0)
    assert g.total_contact_ratio == pytest.approx(1.154, abs=2e-3)
