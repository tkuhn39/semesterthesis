"""
@module: tests.test_cao_fillet
@context: Model-layer tests — CAO root-fillet growth loop (Kassem et al. 2023).
@role: The direct-method growth rule reduces the quick-FE fillet stress monotonically-ish,
       never moves the reference (junction) node, converges on the uniformity criterion,
       memoizes per profile+parameters, and passes the mesh gates as a strategy.
"""

import math
from pathlib import Path

import numpy as np
import pytest

from app.io.ste import gear_stage_from_ste, load_ste
from app.services.geometry.gear import GearStage
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.cao_fillet import CaoFillet, optimize_cao_fillet
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


@pytest.fixture(scope="module")
def wheel() -> ToothProfile:
    stage = GearStage.from_ste(gear_stage_from_ste(load_ste(_REF_STE)))
    return ToothProfile.from_stage(stage, 1)


def test_cao_growth_reduces_stress_and_fixes_junction(wheel: ToothProfile) -> None:
    res = optimize_cao_fillet(wheel, iterations=5, tol=1e-6, points=48)
    assert res.iterations_run >= 2
    assert res.sigma_history_mpa[-1] < res.sigma_history_mpa[0]  # growth relieves the notch
    # the reference node between involute and fillet never moves (Kassem, Fig. 6)
    start = wheel.transverse_right_boundary(fillet_points=48, flank_points=8)
    r_limit = wheel.d_Ff / 2.0 + 1e-6
    r_start_junction = max(
        math.hypot(p[0], p[1]) for p in start if math.hypot(p[0], p[1]) <= r_limit
    )
    r_end_junction = math.hypot(res.points[-1][0], res.points[-1][1])
    assert r_end_junction == pytest.approx(r_start_junction, abs=1e-9)
    # memoized: identical parameters return the identical object
    assert optimize_cao_fillet(wheel, iterations=5, tol=1e-6, points=48) is res


def test_cao_strategy_through_mesh_pipeline(wheel: ToothProfile) -> None:
    strategy = CaoFillet(cao_iterations=3, cao_tol=1e-6, points=48)
    bore = float(load_reference_template().meta["bore_radius_mm"])
    mesh = generate_sector_2d(wheel, bore_radius_mm=bore, fillet=strategy)
    sj = scaled_jacobians(mesh.coords, mesh.quads)
    assert float(sj.min()) >= 0.35
    sigma = root_tensile_stress(
        mesh, wheel, fillet_limit_radius_mm=strategy.junction_radius_mm(wheel)
    ).sigma_max_mpa
    std = root_tensile_stress(generate_sector_2d(wheel, bore_radius_mm=bore), wheel).sigma_max_mpa
    assert sigma < std  # already better than the ρ_F arc after a 3-iteration budget


def test_cao_polyline_shape(wheel: ToothProfile) -> None:
    res = optimize_cao_fillet(wheel, iterations=5, tol=1e-6, points=48)
    pts = np.asarray(res.points)
    radii = np.hypot(pts[:, 0], pts[:, 1])
    assert radii[-1] == pytest.approx(wheel.d_Ff / 2.0, abs=0.05)  # junction near d_Ff
    assert radii.min() > 0.9 * wheel.root_diameter_mm / 2.0  # sane root band
    assert len(pts) == 48
