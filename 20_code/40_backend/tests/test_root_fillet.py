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
    DongToolBezierFillet,
    EllipticFillet,
    FilletStrategy,
    FruheEllipticFillet,
    LandiEllipticFillet,
    _to_gap,
    fillet_boundary,
    junction_radius_mm,
    mating_tip_clearance,
    rack_tip_envelope,
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

Profiles = tuple[ToothProfile, ToothProfile]

_STRATEGIES = [
    EllipticFillet(e_f=-0.2),
    FruheEllipticFillet(),
    LandiEllipticFillet(),
    BezierFillet(be=0.57),
    DongToolBezierFillet(),
    BionicFillet(),
]


@pytest.fixture(scope="module")
def pair() -> tuple[ToothProfile, ToothProfile]:
    stage = GearStage.from_ste(gear_stage_from_ste(load_ste(_REF_STE)))
    return ToothProfile.from_stage(stage, 1), ToothProfile.from_stage(stage, 0)


@pytest.mark.parametrize("strategy", _STRATEGIES, ids=lambda s: type(s).__name__)
def test_fillet_attaches_at_junction(pair: Profiles, strategy: FilletStrategy) -> None:
    """Curve runs gap centre → d_Ff junction; elliptic/Bézier meet the involute G1 (< 2° kink),
    the bionic form deliberately attaches with the tension-triangle wedge angle (bounded kink
    below the active flank, per Voith/Kassem)."""
    wheel, _ = pair
    boundary = np.array([(p[0], p[1]) for p in fillet_boundary(wheel, strategy)])
    radii = np.hypot(boundary[:, 0], boundary[:, 1])
    n_fillet = len(strategy.right_half(wheel))
    assert radii[n_fillet - 1] == pytest.approx(junction_radius_mm(strategy, wheel), abs=1e-3)
    a = boundary[n_fillet - 1] - boundary[n_fillet - 2]  # last fillet segment
    b = boundary[n_fillet] - boundary[n_fillet - 1]  # first flank segment
    cos = float(a @ b / (np.hypot(*a) * np.hypot(*b)))
    kink_deg = math.degrees(math.acos(min(1.0, max(-1.0, cos))))
    assert kink_deg < (25.0 if isinstance(strategy, BionicFillet) else 2.0)


@pytest.mark.parametrize("strategy", _STRATEGIES, ids=lambda s: type(s).__name__)
def test_mating_clearance_positive(pair: Profiles, strategy: FilletStrategy) -> None:
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


def test_fruehe_reaches_centreline_perpendicular(pair: Profiles) -> None:
    """Frühe: the curve starts ON the gap centreline with a horizontal tangent (the mirrored
    ellipses of the facing flanks meet G1 there) and the resulting root lies BELOW the
    standard root circle — the root diameter is a result of the fit (Diss. §5.4, Abb. 41)."""
    wheel, _ = pair
    pts = FruheEllipticFillet().right_half(wheel)
    u0, v0 = _to_gap(wheel, pts[0][0], pts[0][1])
    assert abs(u0) < 1e-9
    u1, v1 = _to_gap(wheel, pts[1][0], pts[1][1])
    assert abs(v1 - v0) < 0.05 * abs(u1 - u0)  # first segment ⊥ centreline
    r_eff = math.hypot(pts[0][0], pts[0][1])
    r_f = wheel.root_diameter_mm / 2.0
    assert r_eff < r_f
    assert r_f - r_eff < 0.5 * wheel.mn  # kst-E: ≈ 0.35·m_n deeper than the ρ_F root


def test_landi_double_tangency_and_raised_junction(pair: Profiles) -> None:
    """Landi: default D2 sits on the root circle AT the gap centreline (tangent ⊥ radial);
    raising ra_f moves D1 up the involute and the flank continues from there seamlessly."""
    wheel, _ = pair
    pts = LandiEllipticFillet().right_half(wheel)
    r_f = wheel.root_diameter_mm / 2.0
    u0, v0 = _to_gap(wheel, pts[0][0], pts[0][1])
    assert abs(u0) < 1e-9  # D2 on the gap centreline …
    assert v0 == pytest.approx(r_f, abs=1e-6)  # … on the root circle
    u1, v1 = _to_gap(wheel, pts[1][0], pts[1][1])
    assert abs(v1 - v0) < 0.05 * abs(u1 - u0)  # tangent to the root circle (⊥ centreline)
    raised = LandiEllipticFillet(ra_f=0.3)
    r_j = junction_radius_mm(raised, wheel)
    assert r_j == pytest.approx(wheel.d_Ff / 2.0 + 0.3 * wheel.mn, abs=1e-9)
    boundary = np.array([(p[0], p[1]) for p in fillet_boundary(wheel, raised)])
    radii = np.hypot(boundary[:, 0], boundary[:, 1])
    n_fillet = len(raised.right_half(wheel))
    assert radii[n_fillet - 1] == pytest.approx(r_j, abs=1e-3)  # fillet ends at the raised D1
    assert radii[n_fillet] >= r_j - 1e-6  # flank continues from D1, no gap back to d_Ff


def test_rack_tip_envelope_reproduces_trochoid(pair: Profiles) -> None:
    """The generic rack-tip envelope with an ARC tool tip reproduces root_fillet_points —
    validates the meshing condition + rolling map. Nearest-neighbour metric (the trochoid's
    double branch near d_Ff breaks naive radius interpolation, ADR-017)."""
    wheel, _ = pair
    m, alpha = wheel.mn, wheel.alpha
    v_tip = (wheel.h_aP0 - wheel.x_e) * m
    rho = wheel.rho_aP0 * m
    v_c = v_tip - rho
    u_c = wheel._as_cut_tooth_thickness_mm / 2.0 + v_c * math.tan(alpha) - rho / math.cos(alpha)  # noqa: SLF001
    theta = np.linspace(0.0, math.pi / 2.0 + alpha, 2000)
    pts = np.stack([u_c + rho * np.sin(theta), v_c + rho * np.cos(theta)], axis=1)
    tangents = np.stack([np.cos(theta), -np.sin(theta)], axis=1)
    env = np.array(rack_tip_envelope(wheel, pts, tangents, r_hi=wheel.d_Ff / 2.0, count=150))
    troch = np.array(wheel.root_fillet_points(2000))
    dists = np.sqrt(((env[:, None, :] - troch[None, :, :]) ** 2).sum(-1)).min(axis=1)
    assert float(dists.max()) < 5e-3  # < 5 µm from the reference trochoid


def test_dong_junction_above_dff_and_root_land(pair: Profiles) -> None:
    """Dong: the generated junction lies ABOVE d_Ff (P0 higher than the arc tangency) and
    the fillet starts on the root circle (root land like the trochoid)."""
    wheel, _ = pair
    f = DongToolBezierFillet()
    r_j = junction_radius_mm(f, wheel)
    assert r_j > wheel.d_Ff / 2.0
    pts = f.right_half(wheel)
    assert math.hypot(pts[0][0], pts[0][1]) == pytest.approx(wheel.root_diameter_mm / 2.0, abs=1e-3)
    assert math.hypot(pts[-1][0], pts[-1][1]) == pytest.approx(r_j, abs=1e-3)


def test_optimized_fillets_reduce_root_stress(pair: Profiles) -> None:
    """Deep ellipse and Bézier cut the quick-FE root stress vs the standard fillet (gates hold)."""
    wheel, _ = pair
    bore = float(load_reference_template().meta["bore_radius_mm"])
    sigma: dict[str, float] = {}
    for name, strategy in (
        ("standard", None),
        ("elliptic", EllipticFillet(e_f=-0.2)),
        ("fruehe", FruheEllipticFillet()),
        ("landi", LandiEllipticFillet(ra_f=0.3)),
        ("bezier", BezierFillet(be=0.57)),
        ("dong", DongToolBezierFillet()),
    ):
        mesh = generate_sector_2d(wheel, bore_radius_mm=bore, fillet=strategy)
        sj = scaled_jacobians(mesh.coords, mesh.quads)
        assert float(sj.min()) >= 0.35, name
        limit = None if strategy is None else junction_radius_mm(strategy, wheel)
        sigma[name] = root_tensile_stress(mesh, wheel, fillet_limit_radius_mm=limit).sigma_max_mpa
    # measured on kst-E (2026-08-05): elliptic 90.1 %, fruehe 79.1 %, landi(ra_f=.3) 79.5 %,
    # bezier 77.9 %, dong(dv1=1) 81.0 % of the standard ρ_F arc — thresholds keep ~6 pp margin
    assert sigma["elliptic"] < 0.95 * sigma["standard"]
    assert sigma["fruehe"] < 0.85 * sigma["standard"]
    assert sigma["landi"] < 0.88 * sigma["standard"]
    assert sigma["bezier"] < 0.85 * sigma["standard"]
    assert sigma["dong"] < 0.88 * sigma["standard"]
