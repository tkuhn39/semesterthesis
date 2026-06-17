"""
@module: app.services.capacity.iso6336
@context: Domain layer — metal gear load capacity (ISO 6336:2019, the current
       standard; numerically equivalent to DIN 3990:1987, which STplus computes).
@role: Flank (pitting) and tooth-root (bending) stress and the resulting safety
       factors. Computed natively: the geometry factors (Z_E, Z_H, Z_ε; Y_F, Y_S
       from the tooth-root module; Z_B, Z_D), the stresses σ_H/σ_F, and the
       permissible stresses σ_HP/σ_FP (via the ISO 6336-2/-3 strength factor
       modules and the operating ``Iso6336Conditions``). So S_H = σ_HP/σ_H and
       S_F = σ_FP/σ_F fall out of inputs; only K_v/K_Hβ/K_Hα (dynamics, in the load
       case) and Z_NT/Y_NT (life, in the conditions) remain inputs.

Validated against two complete references: kst-E (spur, DIN 3990 via STplus) —
σ_H 99.6, σ_F 180.1, S_F 4.571 — and the helical ISO 6336 case (S_H 1.044,
S_F 2.275/2.309). The plastic gear of a pair is handled by ``capacity.vdi2736``.
"""

import math

from pydantic import BaseModel

from app.io.ste import Pair
from app.services.capacity.iso6336_flank_strength import (
    lubricant_factor,
    permissible_flank_stress,
    relative_radius_of_curvature_mm,
    roughness_factor,
    size_factor,
    velocity_factor,
    work_hardening_factor,
)
from app.services.capacity.iso6336_root_strength import (
    RootMaterialGroup,
    permissible_root_stress,
)
from app.services.geometry.gear import GearStage
from app.services.geometry.tooth_root import ToothRootGeometry
from app.services.materials import Material


def elasticity_factor(pinion: Material, wheel: Material) -> float:
    """Elasticity factor Z_E = √(1 / (π · Σ (1−ν²)/E)) (DIN 3990-2), in √(N/mm²)."""
    pair_compliance = (1.0 - pinion.poisson_ratio**2) / pinion.elastic_modulus_mpa + (
        1.0 - wheel.poisson_ratio**2
    ) / wheel.elastic_modulus_mpa
    return math.sqrt(1.0 / (math.pi * pair_compliance))


def zone_factor(stage: GearStage) -> float:
    """Zone factor Z_H = √(2 cos β_b cos α_wt / (cos²α_t sin α_wt)) (DIN 3990-2; β_b=0 spur)."""
    alpha_t = math.radians(stage.transverse_pressure_angle_deg)
    alpha_wt = math.radians(stage.working_pressure_angle_deg)
    beta_b = 0.0  # spur; helical base helix angle added with the helical validation
    return math.sqrt(
        2.0 * math.cos(beta_b) * math.cos(alpha_wt) / (math.cos(alpha_t) ** 2 * math.sin(alpha_wt))
    )


def flank_contact_ratio_factor(eps_alpha: float, eps_beta: float) -> float:
    """Contact ratio factor Z_ε (DIN 3990-2)."""
    if eps_beta >= 1.0:
        return math.sqrt(1.0 / eps_alpha)
    spur_part = (4.0 - eps_alpha) / 3.0
    return math.sqrt(spur_part * (1.0 - eps_beta) + eps_beta / eps_alpha)


def single_contact_factors(stage: GearStage) -> Pair[float]:
    """Single pair tooth contact factors Z_B (pinion), Z_D (wheel) (ISO 6336-2 §9).

    For an overlap ratio ε_β ≥ 1 they are 1.0; for spur gears (ε_β = 0) they are the
    auxiliaries M_1, M_2 (not below 1); in between they are interpolated. Uses the
    usable tip diameter d_Na (= d_Fa, carrying the tip chamfer), valid for 1 < ε_α ≤ 2.
    """
    eps_beta = stage.overlap_ratio
    if eps_beta >= 1.0:
        return Pair(1.0, 1.0)
    usable = stage.usable_tip_diameter_mm
    if usable is None:
        raise ValueError("single contact factors need the usable tip diameters (tool/tip data)")
    db1, db2 = stage.base_diameter_mm
    z1, z2 = stage.teeth
    eps_alpha = stage.transverse_contact_ratio
    tan_awt = math.tan(math.radians(stage.working_pressure_angle_deg))
    tip_1 = math.sqrt(usable[0] ** 2 / db1**2 - 1.0)
    tip_2 = math.sqrt(usable[1] ** 2 / db2**2 - 1.0)
    two_pi = 2.0 * math.pi
    m_1 = tan_awt / math.sqrt((tip_1 - two_pi / z1) * (tip_2 - (eps_alpha - 1.0) * two_pi / z2))
    m_2 = tan_awt / math.sqrt((tip_2 - two_pi / z2) * (tip_1 - (eps_alpha - 1.0) * two_pi / z1))
    z_b = max(1.0, m_1 - eps_beta * (m_1 - 1.0))
    z_d = max(1.0, m_2 - eps_beta * (m_2 - 1.0))
    return Pair(z_b, z_d)


class Iso6336LoadCase(BaseModel):
    """Operating load and the load/dynamic factors (neutral defaults = 1.0)."""

    tangential_force_n: float  # F_t at the reference circle
    common_face_width_mm: float  # b (the load-carrying flank width)
    root_face_width_mm: Pair[float]  # per-gear width for the root stress
    gear_ratio: float  # u = z2/z1
    pinion_reference_diameter_mm: float  # d1
    application_factor: float = 1.0  # K_A
    dynamic_factor: float = 1.0  # K_v
    face_load_factor_flank: float = 1.0  # K_Hβ
    face_load_factor_root: float = 1.0  # K_Fβ
    transverse_factor_flank: float = 1.0  # K_Hα
    transverse_factor_root: float = 1.0  # K_Fα
    helix_factor_root: float = 1.0  # Y_β


class Iso6336Conditions(BaseModel):
    """Operating + material-classification data for the permissible stresses.

    Feeds the native ISO 6336-2/-3 permissible-stress factors so S_H/S_F fall out
    of inputs. The life factors (Z_NT flank, Y_NT root) stay here as the material
    S-N datum.
    """

    pitch_line_velocity_ms: float  # v (for Z_v)
    lubricant_viscosity_40_mm2s: float  # ν40 (for Z_L)
    flank_roughness_rz_um: float  # mean flank Rz (for Z_R)
    root_roughness_rz_um: Pair[float]  # per-gear root fillet Rz (for Y_RrelT)
    material_group: Pair[RootMaterialGroup]  # ISO 6336 group (ρ′, Y_RrelT, Z_R curves)
    flank_life_factor: Pair[float] = Pair(1.0, 1.0)  # Z_NT
    root_life_factor: Pair[float] = Pair(1.0, 1.0)  # Y_NT
    softer_gear_hardness_hb: float | None = None  # for Z_W (paired with a soft gear)


class Iso6336GearResult(BaseModel):
    """Per-gear DIN 3990 result: flank and root stress and (when limits known) safety."""

    flank_stress_mpa: float  # σ_H
    nominal_flank_stress_mpa: float  # σ_H0
    root_stress_mpa: float  # σ_F
    nominal_root_stress_mpa: float  # σ_F0
    flank_safety: float | None = None  # S_H
    root_safety: float | None = None  # S_F


def _safety(strength_mpa: float | None, stress_mpa: float) -> float | None:
    return strength_mpa / stress_mpa if strength_mpa is not None else None


def _basic_root_strength(material: Material) -> float | None:
    """σ_FE (basic root strength); derive from σ_Flim·Y_ST (Y_ST = 2) when absent."""
    if material.sigma_fe_mpa is not None:
        return material.sigma_fe_mpa
    if material.sigma_flim_mpa is not None:
        return 2.0 * material.sigma_flim_mpa
    return None


def evaluate_iso6336(
    stage: GearStage,
    roots: Pair[ToothRootGeometry],
    materials: Pair[Material],
    load: Iso6336LoadCase,
    conditions: Iso6336Conditions,
) -> Pair[Iso6336GearResult]:
    """Evaluate ISO 6336 / DIN 3990 flank and root capacity for both gears.

    The stresses *and* the permissible stresses are computed natively (geometry +
    ISO 6336-2/-3 strength factors); only K_v/K_Hβ/K_Hα (dynamics, in ``load``) and
    Z_NT/Y_NT (life, in ``conditions``) remain inputs. S_H = σ_HP/σ_H, S_F = σ_FP/σ_F.
    """
    z_e = elasticity_factor(materials[0], materials[1])
    z_h = zone_factor(stage)
    z_eps = flank_contact_ratio_factor(stage.transverse_contact_ratio, stage.overlap_ratio)
    sigma_h0 = (
        z_h
        * z_e
        * z_eps
        * math.sqrt(
            load.tangential_force_n
            / (load.pinion_reference_diameter_mm * load.common_face_width_mm)
            * (load.gear_ratio + 1.0)
            / load.gear_ratio
        )
    )
    single_bd = single_contact_factors(stage)  # Z_B, Z_D (native, from the geometry)
    base_diameter = stage.base_diameter_mm
    rho_red = relative_radius_of_curvature_mm(
        base_diameter[0], base_diameter[1], stage.working_pressure_angle_deg
    )
    k_flank = math.sqrt(
        load.application_factor
        * load.dynamic_factor
        * load.face_load_factor_flank
        * load.transverse_factor_flank
    )
    k_root = (
        load.application_factor
        * load.dynamic_factor
        * load.face_load_factor_root
        * load.transverse_factor_root
    )
    results: list[Iso6336GearResult] = []
    for index in range(2):
        material = materials[index]
        root = roots[index]
        sigma_h = single_bd[index] * sigma_h0 * k_flank
        sigma_f0 = (
            load.tangential_force_n
            / (load.root_face_width_mm[index] * stage.normal_module_mm)
            * root.form_factor
            * root.stress_correction_factor
            * load.helix_factor_root
        )
        sigma_f = sigma_f0 * k_root

        sigma_hp: float | None = None
        if material.sigma_hlim_mpa is not None:
            sigma_hp = permissible_flank_stress(
                material.sigma_hlim_mpa,
                life_factor=conditions.flank_life_factor[index],
                lubricant=lubricant_factor(
                    conditions.lubricant_viscosity_40_mm2s, material.sigma_hlim_mpa
                ),
                velocity=velocity_factor(
                    conditions.pitch_line_velocity_ms, material.sigma_hlim_mpa
                ),
                roughness=roughness_factor(
                    conditions.flank_roughness_rz_um, rho_red, material.sigma_hlim_mpa
                ),
                work_hardening=work_hardening_factor(conditions.softer_gear_hardness_hb),
                size=size_factor(),
            )

        sigma_fp: float | None = None
        basic_root = _basic_root_strength(material)
        if basic_root is not None:
            sigma_fp = permissible_root_stress(
                basic_root,
                notch_parameter_qs=root.notch_parameter,
                roughness_rz_um=conditions.root_roughness_rz_um[index],
                normal_module_mm=stage.normal_module_mm,
                group=conditions.material_group[index],
                life_factor=conditions.root_life_factor[index],
            )

        results.append(
            Iso6336GearResult(
                flank_stress_mpa=sigma_h,
                nominal_flank_stress_mpa=sigma_h0,
                root_stress_mpa=sigma_f,
                nominal_root_stress_mpa=sigma_f0,
                flank_safety=_safety(sigma_hp, sigma_h),
                root_safety=_safety(sigma_fp, sigma_f),
            )
        )
    return Pair(results[0], results[1])
