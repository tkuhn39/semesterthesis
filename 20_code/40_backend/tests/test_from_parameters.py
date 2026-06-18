"""
@module: tests.test_from_parameters
@context: Domain-layer tests — free gear definition (GearStage.from_parameters).
@role: Building a stage from raw design parameters + the rack-tool reference profile
       reproduces the parsed-`.ste` kst-E geometry exactly (contact ratio, tip form
       circle incl. chamfer, tooth-root form factors), so the capacity runs for any
       gear, not only a `.ste`.
"""

from pathlib import Path

import pytest

from app.io.ste import Pair, gear_stage_from_ste, load_ste
from app.services.geometry.gear import GearStage
from app.services.geometry.tooth_root import ToothRootGeometry

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)


@pytest.mark.skipif(not _REF_STE.exists(), reason="kst-E reference .ste not present")
def test_from_parameters_reproduces_kst_e() -> None:
    """Raw kst-E inputs + tool profile → identical geometry and tooth-root factors."""
    ref = GearStage.from_ste(gear_stage_from_ste(load_ste(_REF_STE)))
    assert ref.generation is not None
    g0, g1 = ref.generation

    built = GearStage.from_parameters(
        normal_module_mm=1.0,
        teeth=Pair(51, 52),
        profile_shift=Pair(0.2034, 0.3143),
        face_width_mm=Pair(17.0, 15.0),
        tool=Pair(g0.tool, g1.tool),
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=0.0,
        center_distance_mm=52.0,
        tip_diameter_mm=Pair(52.894, 54.022),
        tooth_width_allowance_mm=Pair(g0.tooth_width_allowance_mm, g1.tooth_width_allowance_mm),
        span_teeth=Pair(6, 6),
    )

    assert built.transverse_contact_ratio == pytest.approx(ref.transverse_contact_ratio, abs=1e-4)
    assert built.working_pressure_angle_deg == pytest.approx(
        ref.working_pressure_angle_deg, abs=1e-3
    )
    ref_tip = ref.usable_tip_diameter_mm
    built_tip = built.usable_tip_diameter_mm
    assert ref_tip is not None and built_tip is not None
    for i in range(2):  # tip form circle d_Fa (carries the wheel tip chamfer)
        assert built_tip[i] == pytest.approx(ref_tip[i], abs=2e-3)
    for i in range(2):
        rb = ToothRootGeometry.from_stage(built, i)
        rr = ToothRootGeometry.from_stage(ref, i)
        assert rb.form_factor == pytest.approx(rr.form_factor, abs=1e-3)
        assert rb.critical_root_chord_mn == pytest.approx(rr.critical_root_chord_mn, abs=1e-3)


def test_from_parameters_running_addendum_when_no_tip_given() -> None:
    """Without measured tips, d_a follows the running addendum d = m_t·z + 2 m_n(h_aP*+x)."""
    from app.services.geometry.gear import ToolReferenceProfile

    tool = ToolReferenceProfile(addendum_factor=1.25, tip_radius_factor=0.38)
    stage = GearStage.from_parameters(
        normal_module_mm=2.0,
        teeth=Pair(24, 60),
        profile_shift=Pair(0.3, 0.1),
        face_width_mm=Pair(20.0, 20.0),
        tool=Pair(tool, tool),
        gear_addendum_factor=1.0,
    )
    assert stage.generation is not None
    # pinion d = 48, d_a = 48 + 2·2·(1.0 + 0.3) = 53.2
    assert stage.generation[0].tip_diameter_mm == pytest.approx(53.2)
    assert stage.transverse_contact_ratio > 1.0
