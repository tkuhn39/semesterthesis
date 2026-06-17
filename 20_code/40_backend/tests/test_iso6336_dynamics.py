"""
@module: tests.test_iso6336_dynamics
@context: Domain-layer tests — the native ISO 6336-1 dynamic / load factors.
@role: The mesh stiffness c_γα, reduced mass m_red, resonance ratio N and the
       branch selection are determinable and locked; the assembled K_v / K_Hα land
       in the helical reference band (the grade and c_γ the reference used are not
       reported, so an exact match is not attainable — ADR-011).
"""

import math

import pytest

from app.io.ste import Pair
from app.services.capacity.iso6336_dynamics import (
    DynamicConditions,
    RunningInGroup,
    basic_rack_factor,
    compute_dynamic_factors,
    dynamic_factor,
    face_load_factor_flank,
    face_load_factor_root,
    mesh_stiffness_alpha,
    reduced_mass,
    running_in_allowance_alpha,
    single_stiffness,
    theoretical_single_stiffness,
    transverse_load_factor,
)

# Helical DIN 3990 example (memory din3990-helical-reference): z=25/40, m_n=2, β=20°.
_ZN = Pair(29.669, 47.471)  # virtual teeth z_n (from the tooth-root virtual spur gear)


def test_basic_rack_factor_matches_reference() -> None:
    """C_B = [1 + 0.5(1.2 − h_fP*)]·[1 − 0.02(20 − α_n)] = 0.95 for the helical (h_fP*=1.3)."""
    assert basic_rack_factor(Pair(1.3, 1.3), 20.0) == pytest.approx(0.95, abs=1e-9)
    assert basic_rack_factor(Pair(1.25, 1.25), 20.0) == pytest.approx(0.975, abs=1e-9)


def test_theoretical_single_stiffness_helical() -> None:
    """c′_th = 1/q′ ≈ 17.27 N/(mm·µm) for the helical virtual teeth, x = 0."""
    assert theoretical_single_stiffness(_ZN, Pair(0.0, 0.0)) == pytest.approx(17.27, abs=0.02)


def test_single_and_mesh_stiffness_helical() -> None:
    """c′ ≈ 12.33, c_γα ≈ 17.21 N/(mm·µm) (steel, C_B=0.95, C_M=0.8, cos20°)."""
    c_th = theoretical_single_stiffness(_ZN, Pair(0.0, 0.0))
    c_prime = single_stiffness(c_th, 0.95, 20.0, specific_load_n_mm=216.8)
    assert c_prime == pytest.approx(12.33, abs=0.02)
    assert mesh_stiffness_alpha(c_prime, 1.527) == pytest.approx(17.21, abs=0.02)


def test_reduced_mass_solid_steel_pair() -> None:
    """m_red ≈ 0.0074 kg/mm for the solid steel helical pair (eq. 30–32)."""
    m_red = reduced_mass(
        Pair(53.628, 85.277),  # d_m = (d_a + d_f)/2
        Pair(49.617, 79.387),  # d_b
        Pair(7800.0, 7800.0),
        1.6,  # u
    )
    assert m_red == pytest.approx(0.0074, abs=5e-5)


def test_running_in_allowance_velocity_cap() -> None:
    """y_α = (160/σ_Hlim)·f_pb for steel, capped at f_pb = 40 µm above 10 m/s."""
    # below 5 m/s: no cap
    assert running_in_allowance_alpha(RunningInGroup.THROUGH_HARDENED, 7.7, 1500.0, 3.0) == (
        pytest.approx(160.0 / 1500.0 * 7.7)
    )
    # above 10 m/s with a large deviation: capped to the 40 µm value
    capped = running_in_allowance_alpha(RunningInGroup.THROUGH_HARDENED, 120.0, 1500.0, 15.0)
    assert capped == pytest.approx(160.0 / 1500.0 * 40.0)
    # cast iron / surface hardened use fixed coefficients
    assert running_in_allowance_alpha(RunningInGroup.CAST_IRON, 10.0, 1500.0, 3.0) == (
        pytest.approx(2.75)
    )
    assert running_in_allowance_alpha(RunningInGroup.SURFACE_HARDENED, 10.0, 1500.0, 3.0) == (
        pytest.approx(0.75)
    )


def test_dynamic_factor_branch_selection() -> None:
    """K_v picks the sub-critical, resonance and super-critical branches (eq. 13–22)."""
    common = {"b_p": 0.4, "b_f": 0.3, "b_k": 0.28, "total_contact_ratio": 1.6}
    sub = dynamic_factor(0.16, specific_load_n_mm=216.8, **common)
    reson = dynamic_factor(1.0, specific_load_n_mm=80.0, **common)  # N_s = 0.85
    sup = dynamic_factor(2.0, specific_load_n_mm=216.8, **common)
    assert 1.0 < sub < 1.1  # small dynamic increment when far sub-critical
    assert reson > sub  # the resonance range amplifies
    cv7 = 0.125 * math.sin(math.pi * (1.6 - 2.0)) + 0.875  # 1.5 < ε_γ ≤ 2.5
    assert sup == pytest.approx(0.47 * 0.4 + 0.47 * 0.3 + cv7, abs=1e-6)  # C_v5/C_v6/C_v7


def test_face_load_factor_root_below_flank() -> None:
    """K_Fβ = K_Hβ^N_F < K_Hβ (exponent < 1); equals 1 when K_Hβ = 1."""
    assert face_load_factor_root(1.5, 5.0) < 1.5
    assert face_load_factor_root(1.0, 5.0) == pytest.approx(1.0)


def test_face_load_factor_flank_misalignment() -> None:
    """K_Hβ rises above 1 with misalignment and switches to the √ branch past 2."""
    assert face_load_factor_flank(14.6, 0.0, 224.0) == pytest.approx(1.0)
    small = face_load_factor_flank(14.6, 10.0, 224.0)
    assert 1.0 < small < 2.0
    big = face_load_factor_flank(14.6, 80.0, 224.0)
    assert big == pytest.approx(math.sqrt(2.0 * 80.0 * 14.6 / 224.0))


def test_transverse_load_factor_floor_and_cap() -> None:
    """K_Hα floors at 1 (tiny deviation) and caps at ε_γ/(ε_α Z_ε²)."""
    floor = transverse_load_factor(
        17.2,
        0.5,
        0.4,
        5000.0,
        total_contact_ratio=2.94,
        transverse_contact_ratio=1.527,
        contact_ratio_factor=0.809,
        for_root=False,
    )
    assert floor == pytest.approx(1.0)
    cap = transverse_load_factor(
        17.2,
        200.0,
        0.4,
        50.0,
        total_contact_ratio=2.94,
        transverse_contact_ratio=1.527,
        contact_ratio_factor=0.809,
        for_root=False,
    )
    assert cap == pytest.approx(2.94 / (1.527 * 0.809**2), abs=1e-6)


def test_helical_dynamics_components_and_reference_band() -> None:
    """Full assembly: components locked; K_v / K_Hα land in the helical reference band."""
    cond = DynamicConditions(
        pinion_speed_min1=3000.0,
        base_pitch_deviation_um=Pair(7.7, 7.7),  # representative grade (not reported)
        profile_form_deviation_um=Pair(6.0, 6.0),
        tip_relief_um=Pair(12.6, 17.7),  # SIGG tip relief from the reference
        sigma_hlim_mpa=Pair(1500.0, 1500.0),
    )
    f = compute_dynamic_factors(
        cond,
        pinion_teeth=25,
        virtual_teeth=_ZN,
        profile_shift=Pair(0.0, 0.0),
        helix_angle_deg=20.0,
        normal_pressure_angle_deg=20.0,
        transverse_contact_ratio=1.527,
        overlap_ratio=1.4153,
        tip_diameter_mm=Pair(57.209, 89.134),
        root_diameter_mm=Pair(50.047, 81.420),
        base_diameter_mm=Pair(49.617, 79.387),
        basic_rack_dedendum_factor=Pair(1.3, 1.3),
        elastic_modulus=Pair(206000.0, 206000.0),
        tangential_force_n=5638.0,
        face_width_mm=26.0,
        application_factor=1.0,
        flank_contact_ratio_factor=0.809,
        width_to_height_ratio=26.0 / ((57.209 - 50.047) / 2.0),
    )
    # determinable components — locked
    assert f.mesh_stiffness_alpha == pytest.approx(17.21, abs=0.03)
    assert f.reduced_mass == pytest.approx(0.0074, abs=5e-5)
    assert f.resonance_speed == pytest.approx(18419.0, abs=50.0)
    assert f.resonance_ratio == pytest.approx(0.163, abs=2e-3)  # sub-critical
    # assembled factors — within the reference band (ref K_v 1.05, K_Hα 1.18)
    assert f.dynamic_factor == pytest.approx(1.034, abs=3e-3)
    assert 1.02 < f.dynamic_factor < 1.06
    assert f.transverse_factor_flank == pytest.approx(1.143, abs=3e-3)
    assert 1.10 < f.transverse_factor_flank < 1.20
    # well-aligned (F_βx = 0) → no face concentration
    assert f.face_load_factor_flank == pytest.approx(1.0)
    assert f.face_load_factor_root == pytest.approx(1.0)
