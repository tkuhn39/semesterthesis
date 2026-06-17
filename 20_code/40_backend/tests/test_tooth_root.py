"""
@module: tests.test_tooth_root
@context: Domain-layer tests — tooth-root geometry & form factors.
@role: The 30°-tangent root geometry (s_Fn, ρ_F), the load application at the outer
       single contact point (α_Fen, h_Fe) and the form/stress-correction factors
       (Y_F, Y_S) reproduce STplus exactly for the project gear (kst-E).
"""

from pathlib import Path

import pytest

from app.io.ste import gear_stage_from_ste, load_ste
from app.services.geometry.gear import GearStage
from app.services.geometry.tooth_root import ToothRootGeometry

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)


@pytest.mark.skipif(not _REF_STE.exists(), reason="STplus reference .ste not present")
def test_tooth_root_matches_stplus() -> None:
    """Root chord, fillet radius, lever, load angle and Y_F / Y_S match STplus."""
    stage = GearStage.from_ste(gear_stage_from_ste(load_ste(_REF_STE)))
    pinion = ToothRootGeometry.from_stage(stage, 0)
    wheel = ToothRootGeometry.from_stage(stage, 1)

    assert pinion.critical_root_chord_mn == pytest.approx(2.068, abs=2e-3)
    assert pinion.root_fillet_radius_mn == pytest.approx(0.404, abs=2e-3)
    assert pinion.load_application_angle_deg == pytest.approx(23.222, abs=0.02)
    assert pinion.bending_lever_mn == pytest.approx(1.762, abs=2e-3)
    assert pinion.form_factor == pytest.approx(2.417, abs=3e-3)
    assert pinion.stress_correction_factor == pytest.approx(1.819, abs=3e-3)

    assert wheel.critical_root_chord_mn == pytest.approx(2.197, abs=2e-3)
    assert wheel.root_fillet_radius_mn == pytest.approx(0.381, abs=2e-3)
    assert wheel.load_application_angle_deg == pytest.approx(22.702, abs=0.02)
    assert wheel.bending_lever_mn == pytest.approx(1.614, abs=2e-3)
    assert wheel.form_factor == pytest.approx(1.970, abs=3e-3)
    assert wheel.stress_correction_factor == pytest.approx(1.984, abs=3e-3)
    assert wheel.notch_parameter == pytest.approx(2.88, abs=0.02)
