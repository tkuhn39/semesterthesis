"""
@module: app.services.capacity.iso6336_dynamics
@context: Domain layer — the internal dynamic / load factors of ISO 6336-1:2019.
@role: Compute the dynamic factor K_v (Method B), the transverse load factors
       K_Hα/K_Fα and the face load factors K_Hβ/K_Fβ (Method C) **natively**, so
       the capacity factors fall out of geometry + operating data rather than
       being fed in. Built on the native mesh stiffness c′/c_γα/c_γβ (§9) and the
       reduced mass m_red (§6.5.9).

Method B for K_v resolves the running speed against the gear-pair main resonance:

    n_E1 = (30000 / (π z₁)) · √(c_γα / m_red)        (eq. 6)   resonance speed
    N    = n₁ / n_E1                                 (eq. 9)   resonance ratio

and selects the sub-critical / resonance / super-critical branch (eq. 13–22) with
the load-parameter K = C_v1·B_p + C_v2·B_f + C_v3·B_k built from the effective
pitch/profile deviations and tip relief (eq. 15–18, Table 8).

Standards basis & validation rule: ADR-011/013 (current standards; the norm wins).
The references report only the *result* K_v/K_Hα/K_Hβ, not the gear-accuracy grade
or the mesh stiffness they used, so K_v cannot be reproduced to the last digit from
them (the spur kst-E even overrides c_γ). The components that *are* determinable —
c_γα, m_red, n_E1, N and the branch selection — are validated, and the helical
example lands at K_v ≈ 1.04 (ref. 1.05) for its representative grade and reported
tip relief; see ``tests/test_iso6336_dynamics.py``.
"""

import math
from enum import StrEnum

from pydantic import BaseModel

from app.io.ste import Pair

# Table 11 — coefficients of the theoretical single stiffness q′ (eq. 84).
_Q_C1 = 0.04723
_Q_C2 = 0.15551
_Q_C3 = 0.25791
_Q_C4 = -0.00635
_Q_C5 = -0.11654
_Q_C6 = -0.00193
_Q_C7 = -0.24188
_Q_C8 = 0.00529
_Q_C9 = 0.00182

_C_M = 0.8  # theoretical-correction factor C_M (eq. 85), solid disc gears
_STEEL_E_MPA = 206000.0  # E_st reference modulus for the c′ material correction (eq. 90/91)
_STEEL_E_PAIR = Pair(_STEEL_E_MPA, _STEEL_E_MPA)  # default steel/steel pair (B008-safe)
_ZERO_PAIR = Pair(0.0, 0.0)  # solid-disc / no-relief default (B008-safe)


class RunningInGroup(StrEnum):
    """Material group for the running-in allowances y_α / y_β (ISO 6336-1 §7.5.3/§7.6.3)."""

    THROUGH_HARDENED = "through_hardened"  # St, V, GGG (perl), GTS (perl)
    CAST_IRON = "cast_iron"  # GG, GGG (ferr)
    SURFACE_HARDENED = "surface_hardened"  # Eh, IF, NT (nitr), NV (nitrocar)


# ---------------------------------------------------------------------------
# Mesh stiffness  c′, c_γα, c_γβ  (ISO 6336-1, clause 9)
# ---------------------------------------------------------------------------
def theoretical_single_stiffness(virtual_teeth: Pair[float], profile_shift: Pair[float]) -> float:
    """Theoretical single stiffness c′_th = 1/q′ in N/(mm·µm) (eq. 83–84, Table 11).

    q′ uses the *virtual* (normal-section) tooth numbers z_n1, z_n2 and the profile
    shifts x1, x2 (helical gears are handled through the virtual spur gear).
    """
    zn1, zn2 = virtual_teeth
    x1, x2 = profile_shift
    q_prime = (
        _Q_C1
        + _Q_C2 / zn1
        + _Q_C3 / zn2
        + _Q_C4 * x1
        + _Q_C5 * x1 / zn1
        + _Q_C6 * x2
        + _Q_C7 * x2 / zn2
        + _Q_C8 * x1**2
        + _Q_C9 * x2**2
    )
    return 1.0 / q_prime


def basic_rack_factor(
    basic_rack_dedendum_factor: Pair[float], normal_pressure_angle_deg: float
) -> float:
    """Basic rack factor C_B (eq. 88–89), averaged over the pair when h_fP* differs.

    ``basic_rack_dedendum_factor`` is the generated gear's dedendum h_fP*/m_n (the
    tool addendum h_aP0*/m_n plus the tip clearance). C_B = [1 + 0.5(1.2 − h_fP*/m_n)]
    · [1 − 0.02(20° − α_Pn)].
    """
    alpha_n = normal_pressure_angle_deg

    def _cb(h_fp: float) -> float:
        return (1.0 + 0.5 * (1.2 - h_fp)) * (1.0 - 0.02 * (20.0 - alpha_n))

    return 0.5 * (_cb(basic_rack_dedendum_factor[0]) + _cb(basic_rack_dedendum_factor[1]))


def single_stiffness(
    c_theoretical: float,
    basic_rack: float,
    helix_angle_deg: float,
    *,
    elastic_modulus: Pair[float] = _STEEL_E_PAIR,
    blank_factor: float = 1.0,
    specific_load_n_mm: float | None = None,
) -> float:
    """Single tooth-pair stiffness c′ in N/(mm·µm) (eq. 82, with eq. 90–92).

    c′ = c′_th · C_M · C_R · C_B · cos β, scaled by the material factor E/E_st
    (eq. 90–91; = 1 for steel/steel) and, below 100 N/mm specific load, by the
    low-load reduction (load/100)^0.25 (eq. 92). C_R = 1 for solid disc gears.
    """
    e_pair = (
        2.0 * elastic_modulus[0] * elastic_modulus[1] / (elastic_modulus[0] + elastic_modulus[1])
    )
    material_factor = e_pair / _STEEL_E_MPA
    c_prime = (
        c_theoretical
        * _C_M
        * blank_factor
        * basic_rack
        * math.cos(math.radians(helix_angle_deg))
        * material_factor
    )
    if specific_load_n_mm is not None and specific_load_n_mm < 100.0:
        c_prime *= (specific_load_n_mm / 100.0) ** 0.25
    return c_prime


def mesh_stiffness_alpha(single: float, transverse_contact_ratio: float) -> float:
    """Mean mesh stiffness c_γα = c′·(0.75 ε_α + 0.25) in N/(mm·µm) (eq. 93)."""
    return single * (0.75 * transverse_contact_ratio + 0.25)


def mesh_stiffness_beta(mesh_alpha: float) -> float:
    """Mesh stiffness for the face load factor c_γβ = 0.85 c_γα (eq. 94)."""
    return 0.85 * mesh_alpha


# ---------------------------------------------------------------------------
# Reduced mass and resonance speed  (ISO 6336-1 §6.5.9 / §6.5.3)
# ---------------------------------------------------------------------------
def reduced_mass(
    mean_diameter_mm: Pair[float],
    base_diameter_mm: Pair[float],
    density_kg_m3: Pair[float],
    gear_ratio: float,
    *,
    bore_diameter_mm: Pair[float] = _ZERO_PAIR,
) -> float:
    """Reduced mass per unit face width m_red in kg/mm (eq. 30–32, external pair).

    m_red = (π/8)(d_m1/d_b1)² · d_m1² / [ 1/((1−q1⁴)ρ1) + 1/((1−q2⁴)ρ2 u²) ],
    with d_m = (d_a + d_f)/2 and q = d_i/d_m (q = 0 for a solid disc). Web and hub
    are neglected (their inertia is negligible). Density in kg/mm³ internally.
    """
    dm1, _dm2 = mean_diameter_mm
    db1, _db2 = base_diameter_mm
    rho1 = density_kg_m3[0] * 1.0e-9  # kg/m³ → kg/mm³
    rho2 = density_kg_m3[1] * 1.0e-9
    q1 = bore_diameter_mm[0] / mean_diameter_mm[0]
    q2 = bore_diameter_mm[1] / mean_diameter_mm[1]
    denom = 1.0 / ((1.0 - q1**4) * rho1) + 1.0 / ((1.0 - q2**4) * rho2 * gear_ratio**2)
    return (math.pi / 8.0) * (dm1 / db1) ** 2 * dm1**2 / denom


def resonance_speed(pinion_teeth: int, mesh_alpha: float, reduced: float) -> float:
    """Pinion resonance running speed n_E1 in min⁻¹ (eq. 6).

    c_γα in N/(mm·µm), m_red in kg/mm.
    """
    return (30000.0 / (math.pi * pinion_teeth)) * math.sqrt(mesh_alpha / reduced)


# ---------------------------------------------------------------------------
# Running-in allowances  (ISO 6336-1 §7.5.3 y_β, §7.6.3 y_α; running-in tip relief)
# ---------------------------------------------------------------------------
def _velocity_cap_um(
    value_um: float, deviation_um: float, velocity_ms: float, coeff: float
) -> float:
    """Apply the running-in velocity cap (deviation ≤ 80 µm for 5–10 m/s, ≤ 40 above)."""
    if velocity_ms <= 5.0:
        return value_um
    cap_dev = 80.0 if velocity_ms <= 10.0 else 40.0
    return min(value_um, coeff * cap_dev)


def running_in_allowance_alpha(
    group: RunningInGroup, base_pitch_deviation_um: float, sigma_hlim_mpa: float, velocity_ms: float
) -> float:
    """Running-in allowance y_α in µm (eq. 77–79) for the transverse load factor."""
    if group is RunningInGroup.THROUGH_HARDENED:
        coeff = 160.0 / sigma_hlim_mpa
    elif group is RunningInGroup.CAST_IRON:
        coeff = 0.275
    else:
        coeff = 0.075
    return _velocity_cap_um(
        coeff * base_pitch_deviation_um, base_pitch_deviation_um, velocity_ms, coeff
    )


def running_in_factor_beta(group: RunningInGroup, sigma_hlim_mpa: float) -> float:
    """Running-in factor χ_β = F_βy/F_βx (eq. 47/49/51): 1−320/σ_Hlim, 0.45 or 0.85."""
    if group is RunningInGroup.THROUGH_HARDENED:
        return max(0.0, 1.0 - 320.0 / sigma_hlim_mpa)
    if group is RunningInGroup.CAST_IRON:
        return 0.45
    return 0.85


def running_in_tip_relief(sigma_hlim_mpa: float) -> float:
    """Running-in tip relief C_ay in µm for *unmodified* gears (ISO 6336-1)."""
    return (1.0 / 18.0) * (sigma_hlim_mpa / 97.0 - 18.45) ** 2 + 1.5


# ---------------------------------------------------------------------------
# Dynamic factor K_v  (Method B, ISO 6336-1 §6.5)
# ---------------------------------------------------------------------------
def _cv_coefficients(total_contact_ratio: float) -> tuple[float, ...]:
    """C_v1…C_v7 of Table 8 as a function of the total contact ratio ε_γ."""
    eg = total_contact_ratio
    cv1 = 0.32
    if eg <= 2.0:
        cv2, cv3, cv4, cv6 = 0.34, 0.23, 0.90, 0.47
    else:
        cv2 = 0.57 / (eg - 0.3)
        cv3 = 0.096 / (eg - 1.56)
        cv4 = (0.57 - 0.05 * eg) / (eg - 1.44)
        cv6 = 0.12 / (eg - 1.74)
    cv5 = 0.47
    if eg <= 1.5:
        cv7 = 0.75
    elif eg <= 2.5:
        cv7 = 0.125 * math.sin(math.pi * (eg - 2.0)) + 0.875
    else:
        cv7 = 1.0
    return cv1, cv2, cv3, cv4, cv5, cv6, cv7


def dynamic_factor(
    resonance_ratio: float,
    *,
    specific_load_n_mm: float,
    b_p: float,
    b_f: float,
    b_k: float,
    total_contact_ratio: float,
) -> float:
    """Dynamic factor K_v (Method B, eq. 13–22) over the resonance ranges.

    ``specific_load_n_mm`` is K_A·F_t/b (determines the lower resonance bound N_S).
    B_p/B_f/B_k are the dimensionless deviation/tip-relief parameters (eq. 15–17).
    """
    cv1, cv2, cv3, cv4, cv5, cv6, cv7 = _cv_coefficients(total_contact_ratio)
    n = resonance_ratio
    n_s = (
        0.5 + 0.35 * math.sqrt(specific_load_n_mm / 100.0) if specific_load_n_mm >= 100.0 else 0.85
    )

    def _kv_resonance() -> float:  # eq. 20, at N = 1.15
        return cv1 * b_p + cv2 * b_f + cv4 * b_k + 1.0

    def _kv_supercritical() -> float:  # eq. 21, at N = 1.5
        return cv5 * b_p + cv6 * b_f + cv7

    if n <= n_s:  # sub-critical (eq. 13–14)
        return n * (cv1 * b_p + cv2 * b_f + cv3 * b_k) + 1.0
    if n <= 1.15:  # main resonance (eq. 20)
        return _kv_resonance()
    if n >= 1.5:  # super-critical (eq. 21)
        return _kv_supercritical()
    # intermediate 1.15 < N < 1.5 — linear interpolation (eq. 22)
    return _kv_supercritical() + (_kv_resonance() - _kv_supercritical()) * (1.5 - n) / 0.35


# ---------------------------------------------------------------------------
# Transverse load factor  K_Hα / K_Fα  (ISO 6336-1 §7.6)
# ---------------------------------------------------------------------------
def transverse_load_factor(
    mesh_alpha: float,
    base_pitch_deviation_um: float,
    running_in_alpha_um: float,
    determinant_load_n_mm: float,
    *,
    total_contact_ratio: float,
    transverse_contact_ratio: float,
    contact_ratio_factor: float,
    for_root: bool,
) -> float:
    """Transverse load factor K_Hα (flank) or K_Fα (root) (eq. 73–76).

    ``determinant_load_n_mm`` is F_tH/b = (F_t/b)·K_A·K_v·K_Hβ. ``contact_ratio_factor``
    is Z_ε for the flank limit and Y_ε for the root limit (eq. 75/76).
    """
    base = mesh_alpha * (base_pitch_deviation_um - running_in_alpha_um) / determinant_load_n_mm
    if total_contact_ratio <= 2.0:
        k = 0.5 * total_contact_ratio * (0.9 + 0.4 * base)
    else:
        k = 0.9 + 0.4 * math.sqrt(2.0 * (total_contact_ratio - 1.0) / total_contact_ratio) * base
    if for_root:
        upper = total_contact_ratio / (transverse_contact_ratio * contact_ratio_factor)
    else:
        upper = total_contact_ratio / (transverse_contact_ratio * contact_ratio_factor**2)
    if upper >= 1.0:
        k = min(k, upper)
    return max(1.0, k)


# ---------------------------------------------------------------------------
# Face load factor  K_Hβ / K_Fβ  (Method C, ISO 6336-1 §7.4)
# ---------------------------------------------------------------------------
def face_load_factor_flank(
    mesh_beta: float, effective_misalignment_um: float, mean_load_n_mm: float
) -> float:
    """Face load factor K_Hβ (Method C, eq. 41–42).

    ``mean_load_n_mm`` is F_m/b = (F_t/b)·K_A·K_v. ``effective_misalignment_um`` is
    F_βy = χ_β·F_βx (after running-in). K_Hβ = 1 + F_βy·c_γβ/(2 F_m/b), or
    √(2 F_βy·c_γβ/(F_m/b)) once that exceeds 2.
    """
    linear = 1.0 + effective_misalignment_um * mesh_beta / (2.0 * mean_load_n_mm)
    if linear < 2.0:
        return linear
    return math.sqrt(2.0 * effective_misalignment_um * mesh_beta / mean_load_n_mm)


def face_load_factor_root(face_load_factor_h: float, width_to_height: float) -> float:
    """Face load factor for the root K_Fβ = K_Hβ^N_F (eq. 39–40).

    N_F = (b/h)²/(1 + b/h + (b/h)²), with b/h not taken below 3.
    """
    ratio = max(width_to_height, 3.0)
    exponent = ratio**2 / (1.0 + ratio + ratio**2)
    return face_load_factor_h**exponent


class DynamicFactors(BaseModel):
    """The native ISO 6336-1 load factors plus the resonance diagnostics."""

    dynamic_factor: float  # K_v
    transverse_factor_flank: float  # K_Hα
    transverse_factor_root: float  # K_Fα
    face_load_factor_flank: float  # K_Hβ
    face_load_factor_root: float  # K_Fβ
    mesh_stiffness_alpha: float  # c_γα  [N/(mm·µm)]
    reduced_mass: float  # m_red  [kg/mm]
    resonance_speed: float  # n_E1   [min⁻¹]
    resonance_ratio: float  # N


class DynamicConditions(BaseModel):
    """Operating + accuracy data needed to compute the native dynamic/load factors.

    The gear-accuracy deviations (f_pb base pitch, f_fα profile form) come from the
    tolerance grade (ISO 1328); the tip/root relief from the micro-geometry. The
    initial mesh misalignment F_βx (for K_Hβ Method C) is a shaft/mounting quantity —
    it comes from the shaft analysis (RIKOR) and defaults to a well-aligned 0 here.
    """

    pinion_speed_min1: float  # n₁
    density_kg_m3: Pair[float] = Pair(7800.0, 7800.0)
    base_pitch_deviation_um: Pair[float]  # f_pb (per gear; larger one governs)
    profile_form_deviation_um: Pair[float]  # f_fα (per gear; larger one governs)
    tip_relief_um: Pair[float] = Pair(0.0, 0.0)  # C_a (0 → running-in C_ay)
    root_relief_um: Pair[float] = Pair(0.0, 0.0)  # C_f
    running_in_group: Pair[RunningInGroup] = Pair(
        RunningInGroup.THROUGH_HARDENED, RunningInGroup.THROUGH_HARDENED
    )
    sigma_hlim_mpa: Pair[float] = Pair(1500.0, 1500.0)  # for the running-in allowances
    initial_mesh_misalignment_um: float = 0.0  # F_βx (from shaft / RIKOR)
    bore_diameter_mm: Pair[float] = Pair(0.0, 0.0)  # d_i (0 → solid disc)


def compute_dynamic_factors(
    conditions: DynamicConditions,
    *,
    pinion_teeth: int,
    virtual_teeth: Pair[float],
    profile_shift: Pair[float],
    helix_angle_deg: float,
    normal_pressure_angle_deg: float,
    transverse_contact_ratio: float,
    overlap_ratio: float,
    tip_diameter_mm: Pair[float],
    root_diameter_mm: Pair[float],
    base_diameter_mm: Pair[float],
    basic_rack_dedendum_factor: Pair[float],
    elastic_modulus: Pair[float],
    tangential_force_n: float,
    face_width_mm: float,
    application_factor: float,
    flank_contact_ratio_factor: float,  # Z_ε
    width_to_height_ratio: float,  # b/h for K_Fβ
) -> DynamicFactors:
    """Assemble K_v, K_Hα/K_Fα and K_Hβ/K_Fβ natively (ISO 6336-1, Methods B/C)."""
    total_contact_ratio = transverse_contact_ratio + overlap_ratio
    specific_load = application_factor * tangential_force_n / face_width_mm

    # --- mesh stiffness ---
    c_th = theoretical_single_stiffness(virtual_teeth, profile_shift)
    c_b = basic_rack_factor(basic_rack_dedendum_factor, normal_pressure_angle_deg)
    c_prime = single_stiffness(
        c_th,
        c_b,
        helix_angle_deg,
        elastic_modulus=elastic_modulus,
        specific_load_n_mm=specific_load,
    )
    c_ga = mesh_stiffness_alpha(c_prime, transverse_contact_ratio)
    c_gb = mesh_stiffness_beta(c_ga)

    # --- reduced mass, resonance ---
    mean_diameter = Pair(
        0.5 * (tip_diameter_mm[0] + root_diameter_mm[0]),
        0.5 * (tip_diameter_mm[1] + root_diameter_mm[1]),
    )
    gear_ratio = virtual_teeth[1] / virtual_teeth[0]
    m_red = reduced_mass(
        mean_diameter,
        base_diameter_mm,
        conditions.density_kg_m3,
        gear_ratio,
        bore_diameter_mm=conditions.bore_diameter_mm,
    )
    n_e1 = resonance_speed(pinion_teeth, c_ga, m_red)
    resonance_n = conditions.pinion_speed_min1 / n_e1

    # --- effective deviations / tip relief (the worse gear governs) ---
    f_pb = max(conditions.base_pitch_deviation_um)
    f_fa = max(conditions.profile_form_deviation_um)
    velocity = math.pi * mean_diameter[0] * conditions.pinion_speed_min1 / 60000.0
    group = conditions.running_in_group[0]
    sigma_hlim = min(conditions.sigma_hlim_mpa)
    y_p = running_in_allowance_alpha(group, f_pb, sigma_hlim, velocity)
    y_f = running_in_allowance_alpha(group, f_fa, sigma_hlim, velocity)
    tip = tuple(
        c if c > 0.0 else running_in_tip_relief(conditions.sigma_hlim_mpa[i])
        for i, c in enumerate(conditions.tip_relief_um)
    )
    relief = min(tip[0] + conditions.root_relief_um[1], tip[1] + conditions.root_relief_um[0])
    b_p = c_prime * (f_pb - y_p) / specific_load
    b_f = c_prime * (f_fa - y_f) / specific_load
    b_k = abs(1.0 - c_prime * relief / specific_load)

    k_v = dynamic_factor(
        resonance_n,
        specific_load_n_mm=specific_load,
        b_p=b_p,
        b_f=b_f,
        b_k=b_k,
        total_contact_ratio=total_contact_ratio,
    )

    # --- face load factor (Method C) ---
    chi_beta = running_in_factor_beta(group, sigma_hlim)
    f_by = chi_beta * conditions.initial_mesh_misalignment_um
    mean_load = specific_load * k_v
    k_hb = face_load_factor_flank(c_gb, f_by, mean_load)
    k_fb = face_load_factor_root(k_hb, width_to_height_ratio)

    # --- transverse load factor ---
    determinant_load = mean_load * k_hb
    y_eps = 0.25 + 0.75 / transverse_contact_ratio
    k_ha = transverse_load_factor(
        c_ga,
        f_pb,
        y_p,
        determinant_load,
        total_contact_ratio=total_contact_ratio,
        transverse_contact_ratio=transverse_contact_ratio,
        contact_ratio_factor=flank_contact_ratio_factor,
        for_root=False,
    )
    k_fa = transverse_load_factor(
        c_ga,
        f_pb,
        y_p,
        determinant_load,
        total_contact_ratio=total_contact_ratio,
        transverse_contact_ratio=transverse_contact_ratio,
        contact_ratio_factor=y_eps,
        for_root=True,
    )

    return DynamicFactors(
        dynamic_factor=k_v,
        transverse_factor_flank=k_ha,
        transverse_factor_root=k_fa,
        face_load_factor_flank=k_hb,
        face_load_factor_root=k_fb,
        mesh_stiffness_alpha=c_ga,
        reduced_mass=m_red,
        resonance_speed=n_e1,
        resonance_ratio=resonance_n,
    )
