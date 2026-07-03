"""
@module: tests.test_root_fillet
@context: Domain-layer tests — optimized root-fillet strategies (plan v2 workstream C).
@role: Elliptic/Bézier/bionic fillets attach G1-tangentially at d_Ff, keep positive clearance
       to the mating tip path, mesh through the transplant pipeline within the quality gates,
       and reduce the quick-FE root stress in the direction the literature reports.
"""

import math
from pathlib import Path

import numpy as np
import pytest

from app.io.ste import gear_stage_from_ste, load_ste
from app.services.geometry.gear import GearStage
from app.services.geometry.root_fillet import (
    BezierFillet,
    BionicFillet,
    EllipticFillet,
    fillet_boundary,
    mating_tip_clearance,
)
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.plane_fe import root_tensile_stress
from app.services.model.reference_slice import load_reference_template
from app.services.model.template_mesher import generate_sector_2d, scaled_jacobians

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)

pytestmark = pytest.mark.skipif(not _REF_STE.exists(), reason="STplus reference .ste not present")

_STRATEGIES = [EllipticFillet(e_f=-0.2), BezierFillet(be=0.57), BionicFillet()]


@pytest.fixture(scope="module")
def pair() -> tuple[ToothProfile, ToothProfile]:
    stage = GearStage.from_ste(gear_stage_from_ste(load_ste(_REF_STE)))
    return ToothProfile.from_stage(stage, 1), ToothProfile.from_stage(stage, 0)


@pytest.mark.parametrize("strategy", _STRATEGIES, ids=lambda s: type(s).__name__)
def test_fillet_attaches_at_junction(pair, strategy) -> None:
    """Curve runs gap centre → d_Ff junction; elliptic/Bézier meet the involute G1 (< 2° kink),
    the bionic form deliberately attaches with the tension-triangle wedge angle (bounded kink
    below the active flank, per Voith/Kassem)."""
    wheel, _ = pair
    boundary = np.array([(p[0], p[1]) for p in fillet_boundary(wheel, strategy)])
    radii = np.hypot(boundary[:, 0], boundary[:, 1])
    n_fillet = len(strategy.right_half(wheel))
    assert radii[n_fillet - 1] == pytest.approx(wheel.d_Ff / 2.0, abs=1e-3)
    a = boundary[n_fillet - 1] - boundary[n_fillet - 2]  # last fillet segment
    b = boundary[n_fillet] - boundary[n_fillet - 1]  # first flank segment
    cos = float(a @ b / (np.hypot(*a) * np.hypot(*b)))
    kink_deg = math.degrees(math.acos(min(1.0, max(-1.0, cos))))
    assert kink_deg < (25.0 if isinstance(strategy, BionicFillet) else 2.0)


@pytest.mark.parametrize("strategy", _STRATEGIES, ids=lambda s: type(s).__name__)
def test_mating_clearance_positive(pair, strategy) -> None:
    """No interference with the mating tooth-tip path for the kst-E pair (a = 52 mm)."""
    wheel, pinion = pair
    fillet = np.array([(p[0], p[1]) for p in strategy.right_half(wheel)])
    clearance = mating_tip_clearance(
        wheel,
        fillet,
        mating_tip_radius_mm=(pinion.d_a or pinion.d_Na) / 2.0,
        mating_teeth=pinion.z,
        mating_half_tip_rad=pinion.half_thickness_angle((pinion.d_a or pinion.d_Na) / 2.0),
        centre_distance_mm=52.0,
    )
    assert clearance > 0.1


def test_optimized_fillets_reduce_root_stress(pair) -> None:
    """Deep ellipse and Bézier cut the quick-FE root stress vs the standard fillet (gates hold)."""
    wheel, _ = pair
    bore = float(load_reference_template().meta["bore_radius_mm"])
    sigma: dict[str, float] = {}
    for name, strategy in (
        ("standard", None),
        ("elliptic", EllipticFillet(e_f=-0.2)),
        ("bezier", BezierFillet(be=0.57)),
    ):
        mesh = generate_sector_2d(wheel, bore_radius_mm=bore, fillet=strategy)
        sj = scaled_jacobians(mesh.coords, mesh.quads)
        assert float(sj.min()) >= 0.35, name
        sigma[name] = root_tensile_stress(mesh, wheel).sigma_max_mpa
    assert sigma["elliptic"] < 0.95 * sigma["standard"]
    assert sigma["bezier"] < 0.85 * sigma["standard"]
