"""
@module: app.services.variation.kernel
@context: Domain layer — the vectorized macro-geometry + capacity kernel of the
       plastic-capable Stufenvariation (ADR-013).
@role: Evaluate **many** gear-pair variants at once as numpy arrays — the geometry
       (working pressure angle, contact ratios), the tooth-root tip-load form
       factors Y_Fa/Y_Sa (ISO 6336-3, the ϑ fixed-point iterated in lockstep) and
       the capacity (σ_F/σ_H, S_F/S_H) — with per-gear material dispatch
       (steel → ISO 6336, plastic → VDI 2736) over the shared mesh.

This is the performance core: the two iterative steps (inv α_wt, the root angle ϑ)
become **fixed-iteration vectorized Newton / fixed-point** so a whole batch of
variants is solved in a handful of numpy operations instead of a Python loop over
the scalar pydantic models. The kernel reproduces the scalar
``geometry``/``capacity`` results variant-by-variant (validated against kst-E); the
sweep/sampling/Pareto layers sit on top in ``sweep.py``.

All angle inputs are in **radians**; arrays broadcast against each other, so a scalar
(a fixed design choice, e.g. the tool profile) and an array (a swept parameter) mix
freely. Lengths in mm, stresses in N/mm².
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
_ONE: Array = np.asarray(1.0, dtype=np.float64)  # 0-d default (B008-safe, type-clean)


def involute(angle: Array) -> Array:
    """Involute function inv α = tan α − α (element-wise)."""
    return np.tan(angle) - angle


def inverse_involute(value: Array, *, iterations: int = 30) -> Array:
    """Solve inv α = value for α by vectorized Newton (d/dα inv α = tan²α)."""
    alpha = np.cbrt(3.0 * np.asarray(value, dtype=float)) + 1e-6  # good involute seed
    for _ in range(iterations):
        f = np.tan(alpha) - alpha - value
        alpha = alpha - f / np.tan(alpha) ** 2
    return alpha


def working_pressure_angle(
    transverse_pressure_angle: Array,
    teeth_pinion: Array,
    teeth_wheel: Array,
    profile_shift_pinion: Array,
    profile_shift_wheel: Array,
    normal_pressure_angle: Array,
) -> Array:
    """Working transverse pressure angle α_wt from the profile-shift sum (vectorized)."""
    inv_awt = involute(transverse_pressure_angle) + 2.0 * (
        profile_shift_pinion + profile_shift_wheel
    ) / (teeth_pinion + teeth_wheel) * np.tan(normal_pressure_angle)
    return inverse_involute(inv_awt)


@dataclass(frozen=True)
class ToothRootFormFactors:
    """Vectorized tooth-root geometry and tip-load bending factors per gear."""

    critical_root_chord_mn: Array  # s_Fn / m_n
    root_fillet_radius_mn: Array  # ρ_F / m_n
    notch_parameter: Array  # q_s
    form_factor_tip: Array  # Y_Fa
    stress_correction_tip: Array  # Y_Sa


def tip_form_factors(
    *,
    normal_module_mm: Array,
    teeth: Array,
    normal_pressure_angle: Array,
    helix_angle: Array,
    generation_profile_shift: Array,  # x_E
    tool_addendum_factor: Array,  # h_aP0*
    tool_tip_radius_factor: Array,  # ρ_aP0*
    tip_diameter_mm: Array,  # d_Na (usable tip; with chamfer if any)
    theta_iterations: int = 80,
) -> ToothRootFormFactors:
    """Tip-load tooth-root factors Y_Fa/Y_Sa (ISO 6336-3 / VDI 2736), vectorized.

    Mirrors ``geometry.tooth_root`` through the virtual spur gear z_n; the 30°-tangent
    angle ϑ is solved by the same fixed-point iteration across the whole batch.
    """
    alpha_n = normal_pressure_angle
    base_helix = np.arcsin(np.sin(helix_angle) * np.cos(alpha_n))
    zn = teeth / (np.cos(base_helix) ** 2 * np.cos(helix_angle))
    g_aux = tool_tip_radius_factor - tool_addendum_factor + generation_profile_shift
    e_aux = (
        np.pi / 4.0
        - tool_addendum_factor * np.tan(alpha_n)
        - (1.0 - np.sin(alpha_n)) * tool_tip_radius_factor / np.cos(alpha_n)
    )
    h_aux = (2.0 / zn) * (np.pi / 2.0 - e_aux) - np.pi / 3.0
    theta = np.full_like(zn, np.pi / 6.0)
    for _ in range(theta_iterations):
        theta = (2.0 * g_aux / zn) * np.tan(theta) - h_aux

    s_fn = zn * np.sin(np.pi / 3.0 - theta) + np.sqrt(3.0) * (
        g_aux / np.cos(theta) - tool_tip_radius_factor
    )
    rho_f = tool_tip_radius_factor + 2.0 * g_aux**2 / (
        np.cos(theta) * (zn * np.cos(theta) ** 2 - 2.0 * g_aux)
    )

    reference_n = normal_module_mm * zn
    base_n = reference_n * np.cos(alpha_n)
    transverse_reference = normal_module_mm / np.cos(helix_angle) * teeth
    tip_n = reference_n + (tip_diameter_mm - transverse_reference)

    load_angle = np.arccos(base_n / tip_n)
    gamma = (
        (np.pi / 2.0 + 2.0 * generation_profile_shift * np.tan(alpha_n)) / zn
        + involute(alpha_n)
        - involute(load_angle)
    )
    alpha_fa = load_angle - gamma
    load_term = (np.cos(gamma) - np.sin(gamma) * np.tan(alpha_fa)) * (tip_n / normal_module_mm)
    root_term = zn * np.cos(np.pi / 3.0 - theta) + (g_aux / np.cos(theta) - tool_tip_radius_factor)
    h_fa = 0.5 * (load_term - root_term)

    y_fa = 6.0 * h_fa * np.cos(alpha_fa) / (s_fn**2 * np.cos(alpha_n))
    lever_ratio = s_fn / h_fa
    q_s = s_fn / (2.0 * rho_f)
    y_sa = (1.2 + 0.13 * lever_ratio) * q_s ** (1.0 / (1.21 + 2.3 / lever_ratio))
    return ToothRootFormFactors(s_fn, rho_f, q_s, y_fa, y_sa)


def transverse_contact_ratio(
    *,
    base_diameter_pinion: Array,
    base_diameter_wheel: Array,
    tip_diameter_pinion: Array,
    tip_diameter_wheel: Array,
    working_center_distance_mm: Array,
    working_pressure_angle: Array,
    transverse_base_pitch_mm: Array,
) -> Array:
    """Transverse contact ratio ε_α from the path of contact (vectorized)."""
    path = (
        0.5 * np.sqrt(tip_diameter_pinion**2 - base_diameter_pinion**2)
        + 0.5 * np.sqrt(tip_diameter_wheel**2 - base_diameter_wheel**2)
        - working_center_distance_mm * np.sin(working_pressure_angle)
    )
    return path / transverse_base_pitch_mm


@dataclass(frozen=True)
class MeshGeometry:
    """Vectorized macro-geometry of a batch of gear-pair variants."""

    transverse_pressure_angle: Array
    working_pressure_angle: Array
    reference_diameter: tuple[Array, Array]
    base_diameter: tuple[Array, Array]
    tip_diameter: tuple[Array, Array]
    working_center_distance_mm: Array
    transverse_contact_ratio: Array
    overlap_ratio: Array
    total_contact_ratio: Array


def mesh_geometry(
    *,
    normal_module_mm: Array,
    teeth_pinion: Array,
    teeth_wheel: Array,
    profile_shift_pinion: Array,
    profile_shift_wheel: Array,
    normal_pressure_angle: Array,
    helix_angle: Array,
    face_width_mm: Array,
    addendum_factor: Array = _ONE,
) -> MeshGeometry:
    """Build the vectorized macro-geometry from the swept parameters.

    Tip diameters use the running addendum d_a = d + 2 m_n (h_aP* + x) (no chamfer —
    a small correction for a macro pre-design); the working centre distance follows
    the profile-shift sum.
    """
    cos_beta = np.cos(helix_angle)
    transverse_module = normal_module_mm / cos_beta
    alpha_t = np.arctan(np.tan(normal_pressure_angle) / cos_beta)
    ref_p = transverse_module * teeth_pinion
    ref_w = transverse_module * teeth_wheel
    base_p = ref_p * np.cos(alpha_t)
    base_w = ref_w * np.cos(alpha_t)
    tip_p = ref_p + 2.0 * normal_module_mm * (addendum_factor + profile_shift_pinion)
    tip_w = ref_w + 2.0 * normal_module_mm * (addendum_factor + profile_shift_wheel)

    alpha_wt = working_pressure_angle(
        alpha_t,
        teeth_pinion,
        teeth_wheel,
        profile_shift_pinion,
        profile_shift_wheel,
        normal_pressure_angle,
    )
    ref_center = 0.5 * (ref_p + ref_w)
    working_center = ref_center * np.cos(alpha_t) / np.cos(alpha_wt)
    base_pitch = np.pi * transverse_module * np.cos(alpha_t)

    eps_a = transverse_contact_ratio(
        base_diameter_pinion=base_p,
        base_diameter_wheel=base_w,
        tip_diameter_pinion=tip_p,
        tip_diameter_wheel=tip_w,
        working_center_distance_mm=working_center,
        working_pressure_angle=alpha_wt,
        transverse_base_pitch_mm=base_pitch,
    )
    eps_b = face_width_mm * np.abs(np.sin(helix_angle)) / (np.pi * normal_module_mm)
    return MeshGeometry(
        transverse_pressure_angle=alpha_t,
        working_pressure_angle=alpha_wt,
        reference_diameter=(ref_p, ref_w),
        base_diameter=(base_p, base_w),
        tip_diameter=(tip_p, tip_w),
        working_center_distance_mm=working_center,
        transverse_contact_ratio=eps_a,
        overlap_ratio=eps_b,
        total_contact_ratio=eps_a + eps_b,
    )


# ---------------------------------------------------------------------------
# Capacity  (stresses; vectorized; the same forms as the scalar capacity modules)
# ---------------------------------------------------------------------------
def elasticity_factor(
    modulus_pinion: Array, poisson_pinion: Array, modulus_wheel: Array, poisson_wheel: Array
) -> Array:
    """Elasticity factor Z_E = √(1/(π·Σ(1−ν²)/E)) (vectorized; steel–plastic aware)."""
    compliance = (1.0 - poisson_pinion**2) / modulus_pinion + (
        1.0 - poisson_wheel**2
    ) / modulus_wheel
    return np.sqrt(1.0 / (np.pi * compliance))


def zone_factor(
    transverse_pressure_angle: Array, working_pressure_angle: Array, base_helix_angle: Array
) -> Array:
    """Zone factor Z_H = √(2 cos β_b cos α_wt/(cos²α_t sin α_wt)) (vectorized)."""
    return np.sqrt(
        2.0
        * np.cos(base_helix_angle)
        * np.cos(working_pressure_angle)
        / (np.cos(transverse_pressure_angle) ** 2 * np.sin(working_pressure_angle))
    )


def flank_contact_ratio_factor(transverse_contact_ratio: Array, overlap_ratio: Array) -> Array:
    """Contact ratio factor Z_ε (vectorized; spur and helical branches)."""
    helical = np.sqrt(np.clip(1.0 / transverse_contact_ratio, 0.0, None))
    spur = np.sqrt(
        np.clip(
            (4.0 - transverse_contact_ratio) / 3.0 * (1.0 - overlap_ratio)
            + overlap_ratio / transverse_contact_ratio,
            0.0,
            None,
        )
    )
    return np.where(overlap_ratio >= 1.0, helical, spur)


def flank_stress(
    *,
    elasticity: Array,
    zone: Array,
    contact_ratio_factor: Array,
    helix_factor: Array,
    tangential_force_n: Array,
    pinion_reference_diameter_mm: Array,
    face_width_mm: Array,
    gear_ratio: Array,
    load_factor_kh: Array = _ONE,
) -> Array:
    """Flank (contact) stress σ_H (vectorized; ISO 6336-2 / VDI 2736 form)."""
    return (
        elasticity
        * zone
        * contact_ratio_factor
        * helix_factor
        * np.sqrt(
            tangential_force_n
            / (pinion_reference_diameter_mm * face_width_mm)
            * (gear_ratio + 1.0)
            / gear_ratio
        )
        * np.sqrt(load_factor_kh)
    )


def root_stress(
    *,
    tangential_force_n: Array,
    face_width_mm: Array,
    normal_module_mm: Array,
    form_factor_tip: Array,
    stress_correction_tip: Array,
    transverse_contact_ratio: Array,
    helix_factor: Array = _ONE,
    load_factor_kf: Array = _ONE,
) -> Array:
    """Tooth-root stress σ_F (vectorized; tip-load form, Y_ε = 0.25 + 0.75/ε_α)."""
    y_eps = 0.25 + 0.75 / transverse_contact_ratio
    return (
        load_factor_kf
        * form_factor_tip
        * stress_correction_tip
        * y_eps
        * helix_factor
        * tangential_force_n
        / (face_width_mm * normal_module_mm)
    )


def validity_mask(
    geometry: MeshGeometry,
    roots: tuple[ToothRootFormFactors, ToothRootFormFactors],
    *,
    minimum_total_contact_ratio: float = 1.0,
    minimum_notch_parameter: float = 1.0,
    maximum_notch_parameter: float = 8.0,
) -> BoolArray:
    """Boolean mask of geometrically usable variants (early pruning, ADR-013).

    Drops variants with ε_γ below the target, a non-physical (NaN) form factor
    (pointed tip / undercut so the tooth-root construction degenerates) or a notch
    parameter q_s outside the 1…8 validity range of the stress correction factor.
    """
    ok = geometry.total_contact_ratio >= minimum_total_contact_ratio
    for root in roots:
        ok = ok & np.isfinite(root.form_factor_tip) & np.isfinite(root.critical_root_chord_mn)
        ok = ok & (root.notch_parameter >= minimum_notch_parameter)
        ok = ok & (root.notch_parameter <= maximum_notch_parameter)
    return ok
