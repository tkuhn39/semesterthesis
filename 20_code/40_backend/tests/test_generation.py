"""
@module: tests.test_generation
@context: Domain-layer tests — rack-tool gear generation (Verzahnen).
@role: The native generation reproduces the STplus generated circles exactly for
       the project gear (kst-E): generation profile shift x_E, root form circle
       d_Ff, tip form circle d_Fa, tip chamfer h_K and the rest tip thickness —
       for both the chamfered wheel and the un-chamfered pinion.
"""

from pathlib import Path

import pytest

from app.io.ste import gear_stage_from_ste, load_ste
from app.services.geometry.generation import GearGeneration, ToolReferenceProfile

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)

# kst-E wheel (gear 2): tool with a 45° edge-break flank → tip chamfer.
WHEEL = GearGeneration(
    normal_module_mm=1.0,
    teeth=52,
    normal_pressure_angle_deg=20.0,
    profile_shift=0.3143,
    tip_diameter_mm=54.022,
    tooth_width_allowance_mm=-0.207,
    tool=ToolReferenceProfile(
        addendum_factor=1.25,
        tip_radius_factor=0.2,
        dedendum_factor=1.0,
        root_form_height_factor=0.8456,
        normal_pressure_angle_deg=20.0,
        edge_break_angle_deg=45.0,
    ),
)

# kst-E pinion (gear 1): tool without an edge-break flank → no tip chamfer.
PINION = GearGeneration(
    normal_module_mm=1.0,
    teeth=51,
    normal_pressure_angle_deg=20.0,
    profile_shift=0.2034,
    tip_diameter_mm=52.894,
    tooth_width_allowance_mm=-0.278,
    tool=ToolReferenceProfile(
        addendum_factor=1.1,
        tip_radius_factor=0.2,
        dedendum_factor=1.0,
        normal_pressure_angle_deg=20.0,
    ),
)


def test_wheel_generation_matches_stplus() -> None:
    """Chamfered wheel: x_E, d_Ff, d_Fa, h_K and rest tip thickness match STplus."""
    assert WHEEL.generation_profile_shift == pytest.approx(0.0117, abs=5e-4)
    assert WHEEL.root_form_diameter_mm == pytest.approx(50.158, abs=2e-3)
    assert WHEEL.tip_form_diameter_mm == pytest.approx(53.788, abs=2e-3)
    assert WHEEL.tip_chamfer_radial_mm == pytest.approx(0.117, abs=1e-3)
    assert WHEEL.rest_tip_thickness_mm == pytest.approx(0.634, abs=2e-3)


def test_pinion_without_edge_break_has_no_chamfer() -> None:
    """Un-chamfered pinion: d_Fa == d_a, h_K == 0, x_E and d_Ff still match STplus."""
    assert PINION.tool.has_tip_chamfer is False
    assert PINION.generation_profile_shift == pytest.approx(-0.2030, abs=5e-4)
    assert PINION.root_form_diameter_mm == pytest.approx(49.081, abs=2e-3)
    assert PINION.tip_form_diameter_mm == pytest.approx(52.894)
    assert PINION.tip_chamfer_radial_mm == pytest.approx(0.0, abs=1e-9)
    assert PINION.rest_tip_thickness_mm == pytest.approx(0.672, abs=2e-3)


@pytest.mark.skipif(not _REF_STE.exists(), reason="STplus reference .ste not present")
def test_generation_from_ste_reference() -> None:
    """Building from the real STplus input reproduces the chamfer of the wheel."""
    stage = gear_stage_from_ste(load_ste(_REF_STE))
    pinion = GearGeneration.from_ste_gear(stage, 0)
    wheel = GearGeneration.from_ste_gear(stage, 1)
    assert pinion.tip_chamfer_radial_mm == pytest.approx(0.0, abs=1e-9)
    assert wheel.tip_form_diameter_mm == pytest.approx(53.788, abs=2e-3)
    assert wheel.tip_chamfer_radial_mm == pytest.approx(0.117, abs=1e-3)
