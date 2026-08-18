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
from app.services.capacity.iso6336_dynamics import (
    DynamicConditions,
    DynamicFactors,
    compute_dynamic_factors,
)
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
    relative_notch_sensitivity_factor,
    relative_surface_factor,
)
from app.services.capacity.iso6336_root_strength import size_factor as root_size_factor
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
    """Zone factor Z_H = √(2 cos β_b cos α_wt / (cos²α_t sin α_wt)) (ISO 6336-2:2019 §6).

    β_b = asin(sin β · cos α_n) is the base helix angle (ISO 21771); it reduces to 0 for
    spur gears. Fixed 2026-08-18 (audit NRM-03): β_b was hardcoded 0 before.
    """
    alpha_t = math.radians(stage.transverse_pressure_angle_deg)
    alpha_wt = math.radians(stage.working_pressure_angle_deg)
    alpha_n = math.radians(stage.normal_pressure_angle_deg)
    beta = math.radians(stage.helix_angle_deg)
    beta_b = math.asin(math.sin(beta) * math.cos(alpha_n))
    return math.sqrt(
        2.0 * math.cos(beta_b) * math.cos(alpha_wt) / (math.cos(alpha_t) ** 2 * math.sin(alpha_wt))
    )


def helix_angle_factor_flank(helix_angle_deg: float) -> float:
    """Helix angle factor Z_β = √(1/cos β) (ISO 6336-2:2019 Eq. 41, β = reference helix)."""
    return math.sqrt(1.0 / math.cos(math.radians(helix_angle_deg)))


def helix_angle_factor_root(eps_beta: float, helix_angle_deg: float) -> float:
    """Helix angle factor Y_β = (1 − ε_β·β/120°)·1/cos³β (ISO 6336-3:2019 Eq. 66/67).

    β is the REFERENCE helix angle in degrees; ε_β is substituted by 1.0 when ε_β > 1 and
    β by 30° when β > 30° (the 2019 edition's 1/cos³β term lets Y_β exceed 1, Figure 8).
    """
    eps = min(eps_beta, 1.0)
    beta = min(abs(helix_angle_deg), 30.0)
    return (1.0 - eps * beta / 120.0) / math.cos(math.radians(beta)) ** 3


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
    """Per-gear DIN 3990 result: flank and root stress and (when limits known) safety.

    The permissible stresses AND their individual sub-factors are carried explicitly so
    the API/report can print the full ISO 6336-2/-3 factor chain (user requirement
    2026-08-18) instead of only the folded σ_HP/σ_FP products.
    """

    flank_stress_mpa: float  # σ_H
    nominal_flank_stress_mpa: float  # σ_H0
    root_stress_mpa: float  # σ_F
    nominal_root_stress_mpa: float  # σ_F0
    flank_safety: float | None = None  # S_H
    root_safety: float | None = None  # S_F
    permissible_flank_stress_mpa: float | None = None  # σ_HP (native product below)
    permissible_root_stress_mpa: float | None = None  # σ_FP
    # flank sub-factors (ISO 6336-2): σ_HP = σ_Hlim·Z_NT·Z_L·Z_v·Z_R·Z_W·Z_X
    lubricant_factor: float | None = None  # Z_L
    velocity_factor: float | None = None  # Z_v
    roughness_factor: float | None = None  # Z_R
    work_hardening_factor: float | None = None  # Z_W
    size_factor_flank: float | None = None  # Z_X
    life_factor_flank: float | None = None  # Z_NT (echoed input)
    # root sub-factors (ISO 6336-3): σ_FP = σ_FE·Y_NT·Y_δrelT·Y_RrelT·Y_X
    notch_sensitivity_factor: float | None = None  # Y_δrelT
    surface_factor: float | None = None  # Y_RrelT
    size_factor_root: float | None = None  # Y_X
    life_factor_root: float | None = None  # Y_NT (echoed input)


def _safety(strength_mpa: float | None, stress_mpa: float) -> float | None:
    return strength_mpa / stress_mpa if strength_mpa is not None else None


def _basic_root_strength(material: Material) -> float | None:
    """σ_FE (basic root strength); derive from σ_Flim·Y_ST (Y_ST = 2) when absent."""
    if material.sigma_fe_mpa is not None:
        return material.sigma_fe_mpa
    if material.sigma_flim_mpa is not None:
        return 2.0 * material.sigma_flim_mpa
    return None


def native_dynamic_factors(
    stage: GearStage,
    roots: Pair[ToothRootGeometry],
    materials: Pair[Material],
    load: Iso6336LoadCase,
    dynamics: DynamicConditions,
) -> DynamicFactors:
    """Compute K_v / K_Hα / K_Hβ natively (ISO 6336-1) from the geometry + operating data.

    Needs the per-gear rack-tool generation (tip/root diameters, basic-rack dedendum).
    """
    if stage.generation is None:
        raise ValueError("native dynamics need the rack-tool generation (tool + tip data)")
    gen = stage.generation
    z_eps = flank_contact_ratio_factor(stage.transverse_contact_ratio, stage.overlap_ratio)
    tip = Pair(gen[0].tip_diameter_mm, gen[1].tip_diameter_mm)
    root = Pair(gen[0].root_form_diameter_mm, gen[1].root_form_diameter_mm)
    tooth_height = 0.5 * (tip[0] - root[0])  # pinion tooth height for b/h
    dedendum = Pair(
        gen[0].tool.dedendum_factor or gen[0].tool.addendum_factor,
        gen[1].tool.dedendum_factor or gen[1].tool.addendum_factor,
    )
    # per-gear material data (audit NRM-08: densities and σ_Hlim follow the materials —
    # a plastic wheel is ~5.6× lighter than the former steel default)
    if dynamics.density_kg_m3 == Pair(7800.0, 7800.0):
        dynamics = dynamics.model_copy(
            update={
                "density_kg_m3": Pair(
                    materials[0].density_kg_m3 or 7800.0, materials[1].density_kg_m3 or 7800.0
                ),
                "sigma_hlim_mpa": Pair(
                    materials[0].sigma_hlim_mpa or 1500.0, materials[1].sigma_hlim_mpa or 1500.0
                ),
            }
        )
    return compute_dynamic_factors(
        dynamics,
        pinion_teeth=stage.teeth[0],
        virtual_teeth=Pair(roots[0].virtual_teeth, roots[1].virtual_teeth),
        profile_shift=stage.profile_shift,
        helix_angle_deg=stage.helix_angle_deg,
        normal_pressure_angle_deg=stage.normal_pressure_angle_deg,
        transverse_contact_ratio=stage.transverse_contact_ratio,
        overlap_ratio=stage.overlap_ratio,
        tip_diameter_mm=tip,
        root_diameter_mm=root,
        base_diameter_mm=stage.base_diameter_mm,
        basic_rack_dedendum_factor=dedendum,
        elastic_modulus=Pair(materials[0].elastic_modulus_mpa, materials[1].elastic_modulus_mpa),
        tangential_force_n=load.tangential_force_n,
        face_width_mm=load.common_face_width_mm,
        application_factor=load.application_factor,
        flank_contact_ratio_factor=z_eps,
        width_to_height_ratio=load.common_face_width_mm / tooth_height,
        pinion_reference_diameter_mm=stage.reference_diameter_mm[0],
    )


def evaluate_iso6336(
    stage: GearStage,
    roots: Pair[ToothRootGeometry],
    materials: Pair[Material],
    load: Iso6336LoadCase,
    conditions: Iso6336Conditions,
    dynamics: DynamicConditions | None = None,
) -> Pair[Iso6336GearResult]:
    """Evaluate ISO 6336 / DIN 3990 flank and root capacity for both gears.

    The stresses *and* the permissible stresses are computed natively (geometry +
    ISO 6336-2/-3 strength factors); Z_NT/Y_NT (life, in ``conditions``) stay inputs.
    When ``dynamics`` is given, K_v/K_Hα/K_Hβ (and K_Fα/K_Fβ) are computed natively
    (ISO 6336-1) and override the scalar factors in ``load``; otherwise the ``load``
    factors are used. S_H = σ_HP/σ_H, S_F = σ_FP/σ_F.
    """
    if dynamics is not None:
        factors = native_dynamic_factors(stage, roots, materials, load, dynamics)
        load = load.model_copy(
            update={
                "dynamic_factor": factors.dynamic_factor,
                "face_load_factor_flank": factors.face_load_factor_flank,
                "face_load_factor_root": factors.face_load_factor_root,
                "transverse_factor_flank": factors.transverse_factor_flank,
                "transverse_factor_root": factors.transverse_factor_root,
            }
        )
    z_e = elasticity_factor(materials[0], materials[1])
    z_h = zone_factor(stage)
    z_eps = flank_contact_ratio_factor(stage.transverse_contact_ratio, stage.overlap_ratio)
    z_beta = helix_angle_factor_flank(stage.helix_angle_deg)  # 1.0 for spur
    # Y_β natively from the stage (fixed 2026-08-18, audit NRM-03: the former load-case
    # field defaulted to 1.0 and no caller ever set it — helical root stress was too high)
    y_beta = helix_angle_factor_root(stage.overlap_ratio, stage.helix_angle_deg)
    sigma_h0 = (
        z_h
        * z_e
        * z_eps
        * z_beta
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
            * y_beta
        )
        sigma_f = sigma_f0 * k_root

        sigma_hp: float | None = None
        z_l = z_v = z_r = None
        z_w = z_x = None
        if material.sigma_hlim_mpa is not None:
            z_l = lubricant_factor(conditions.lubricant_viscosity_40_mm2s, material.sigma_hlim_mpa)
            z_v = velocity_factor(conditions.pitch_line_velocity_ms, material.sigma_hlim_mpa)
            z_r = roughness_factor(
                conditions.flank_roughness_rz_um, rho_red, material.sigma_hlim_mpa
            )
            z_w = work_hardening_factor(conditions.softer_gear_hardness_hb)
            z_x = size_factor()
            sigma_hp = permissible_flank_stress(
                material.sigma_hlim_mpa,
                life_factor=conditions.flank_life_factor[index],
                lubricant=z_l,
                velocity=z_v,
                roughness=z_r,
                work_hardening=z_w,
                size=z_x,
            )

        sigma_fp: float | None = None
        y_drel = y_rrel = y_x = None
        basic_root = _basic_root_strength(material)
        if basic_root is not None:
            group = conditions.material_group[index]
            y_drel = relative_notch_sensitivity_factor(root.notch_parameter, group)
            y_rrel = relative_surface_factor(conditions.root_roughness_rz_um[index], group)
            y_x = root_size_factor(stage.normal_module_mm, group)
            sigma_fp = permissible_root_stress(
                basic_root,
                notch_parameter_qs=root.notch_parameter,
                roughness_rz_um=conditions.root_roughness_rz_um[index],
                normal_module_mm=stage.normal_module_mm,
                group=group,
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
                permissible_flank_stress_mpa=sigma_hp,
                permissible_root_stress_mpa=sigma_fp,
                lubricant_factor=z_l,
                velocity_factor=z_v,
                roughness_factor=z_r,
                work_hardening_factor=z_w,
                size_factor_flank=z_x,
                life_factor_flank=(
                    conditions.flank_life_factor[index] if sigma_hp is not None else None
                ),
                notch_sensitivity_factor=y_drel,
                surface_factor=y_rrel,
                size_factor_root=y_x,
                life_factor_root=(
                    conditions.root_life_factor[index] if sigma_fp is not None else None
                ),
            )
        )
    return Pair(results[0], results[1])
