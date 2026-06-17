"""
@module: tests.test_tooth_form
@context: Domain-layer tests — full tooth profile coordinates.
@role: The generated tooth profile spans the root circle d_f to the usable tip
       d_Na, with the root fillet trochoid joining the involute flank continuously
       at d_Ff — consistent with the STplus form circles for the project gear.
"""

import math
from pathlib import Path

import pytest

from app.io.ste import gear_stage_from_ste, load_ste
from app.services.geometry.gear import GearStage
from app.services.geometry.tooth_form import ToothProfile

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)


def _radius(point: tuple[float, float]) -> float:
    return math.hypot(point[0], point[1])


@pytest.mark.skipif(not _REF_STE.exists(), reason="STplus reference .ste not present")
def test_tooth_profile_spans_root_to_tip() -> None:
    """Pinion profile: fillet bottom = d_f, flank d_Ff … d_Na, continuous at d_Ff."""
    stage = GearStage.from_ste(gear_stage_from_ste(load_ste(_REF_STE)))
    profile = ToothProfile.from_stage(stage, 0)

    assert profile.root_diameter_mm == pytest.approx(48.394, abs=2e-3)

    fillet = profile.root_fillet_points()
    flank = profile.flank_points()
    # Root fillet bottom reaches d_f; its top meets the involute near d_Ff.
    assert 2.0 * _radius(fillet[0]) == pytest.approx(48.394, abs=1e-2)
    assert 2.0 * _radius(fillet[-1]) == pytest.approx(49.081, abs=0.1)
    # Involute flank runs from d_Ff to d_Na.
    assert 2.0 * _radius(flank[0]) == pytest.approx(49.081, abs=2e-3)
    assert 2.0 * _radius(flank[-1]) == pytest.approx(52.894, abs=2e-3)

    # The full right flank is radius-monotonic from root to tip.
    radii = [_radius(p) for p in profile.right_flank_profile()]
    assert radii == sorted(radii)
    assert all(point[0] >= -1e-9 for point in profile.right_flank_profile())
