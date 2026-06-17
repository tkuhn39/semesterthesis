"""
@module: app.services.capacity.vdi2736
@context: Domain layer — plastic gear load capacity (VDI 2736 Blatt 2, 2014).
@role: The capacity checks that matter for a thermoplastic gear and that ISO 6336
       does not cover: tooth-root and flank stress with the **tip-load** form
       factors Y_Fa/Y_Sa, the local **tooth temperature** (frictional heat raises it
       and lowers the strength), the **wear** (dry running) and the (large) tooth
       **deformation**. Shares the geometry (`geometry.tooth_root`, the tip-load
       Y_Fa) and the mutual flank factors (Z_E/Z_H/Z_ε) with the ISO 6336 path.

The steel gear of a steel–plastic pair is evaluated with ISO 6336 (`iso6336`); the
plastic gear with this module. Validated against the FVA-Workbench VDI-2736 report
(`31_FVA/Tragfaehigkeit_VDI-2736_Workbench.pdf`), which is the **kst-E** pair
(z 51/52, m_n 1, steel 20MnCr5 pinion + plastic wheel): exact on σ_H = 79.893,
ϑ = 107.767 °C, λ = 0.0377 mm, H_V = 0.0626, l_Fl = 1.330 mm and the pinion tip
form factors Y_Fa = 2.693 / Y_Sa = 1.759. Standards basis: ADR-011 (the norm wins).
"""

import math

from pydantic import BaseModel

from app.io.ste import Pair
from app.services.capacity.iso6336 import (
    elasticity_factor,
    flank_contact_ratio_factor,
    zone_factor,
)
from app.services.geometry.gear import GearStage
from app.services.geometry.tooth_root import ToothRootGeometry
from app.services.materials import Material


# ---------------------------------------------------------------------------
# Geometry helpers (loss factor, partial contact ratios, active flank length)
# ---------------------------------------------------------------------------
def partial_contact_ratios(stage: GearStage) -> Pair[float]:
    """Partial contact ratios ε_1 (pinion), ε_2 (wheel); ε_1 + ε_2 = ε_α.

    ε_i = z_i/(2π)·(tan α_aNi − tan α_wt), with α_aNi at the usable tip d_Na.
    """
    if stage.usable_tip_diameter_mm is None:
        raise ValueError("partial contact ratios need the usable tip diameters (tool/tip data)")
    alpha_wt = math.radians(stage.working_pressure_angle_deg)
    base = stage.base_diameter_mm
    tip = stage.usable_tip_diameter_mm
    out = []
    for i in range(2):
        alpha_a = math.acos(base[i] / tip[i])
        out.append(stage.teeth[i] / (2.0 * math.pi) * (math.tan(alpha_a) - math.tan(alpha_wt)))
    return Pair(out[0], out[1])


def loss_factor(stage: GearStage) -> float:
    """Gear loss factor H_V after Wimmer (VDI 2736 eq. 8).

    H_V = π(u+1)/(z_2 cos β_b)·(1 − ε_1 − ε_2 + ε_1² + ε_2²).
    """
    eps1, eps2 = partial_contact_ratios(stage)
    u = stage.teeth[1] / stage.teeth[0]
    beta = math.radians(stage.helix_angle_deg)
    alpha_n = math.radians(stage.normal_pressure_angle_deg)
    base_helix = math.asin(math.sin(beta) * math.cos(alpha_n))
    return (
        math.pi
        * (u + 1.0)
        / (stage.teeth[1] * math.cos(base_helix))
        * (1.0 - eps1 - eps2 + eps1**2 + eps2**2)
    )


def active_flank_length_mm(stage: GearStage, index: int) -> float:
    """Profile line length of the active flank l_Fl (VDI 2736 eq. 20).

    l_Fl = (d_Na² − d_Nf²)/(4 d_b), the involute arc between the lower active root
    circle d_Nf and the usable tip d_Na. d_Nf is the *usable* root from the path of
    contact (set by the mating gear's tip), ξ_Nf = a_w·sin α_wt − ξ_Na,mate.
    """
    if stage.usable_tip_diameter_mm is None:
        raise ValueError("active flank length needs the usable tip diameters (tool/tip data)")
    tip = stage.usable_tip_diameter_mm
    base = stage.base_diameter_mm
    alpha_wt = math.radians(stage.working_pressure_angle_deg)
    mate = 1 - index
    xi_mate_tip = math.sqrt((tip[mate] / 2.0) ** 2 - (base[mate] / 2.0) ** 2)
    xi_root = stage.working_center_distance_mm * math.sin(alpha_wt) - xi_mate_tip
    d_nf = 2.0 * math.hypot(base[index] / 2.0, xi_root)
    return (tip[index] ** 2 - d_nf**2) / (4.0 * base[index])


# ---------------------------------------------------------------------------
# Tooth temperature  (VDI 2736 eq. 9)
# ---------------------------------------------------------------------------
def tooth_temperature(
    *,
    ambient_temperature_c: float,
    power_w: float,
    friction_coefficient: float,
    loss_factor_hv: float,
    heat_transfer_coefficient: float,  # k_ϑ  [K·(m/s)^0.75·mm^1.75/W]
    face_width_mm: float,
    pinion_teeth: int,
    pitch_velocity_ms: float,
    normal_module_mm: float,
    housing_resistance_k_m2_w: float,  # R_λ,G
    housing_surface_m2: float,  # A_G
    duty_cycle: float = 1.0,  # relative ED (1.0 = continuous)
) -> float:
    """Local tooth (flank or root) temperature ϑ in °C (VDI 2736 eq. 9).

    ϑ = ϑ_0 + P·μ·H_V·( k_ϑ/(b·z_1·(v_t·m_n)^0.75) + R_λG/A_G )·ED^0.64.
    Use the flank or root ``heat_transfer_coefficient`` for ϑ_Fla or ϑ_Fuß.
    """
    conduction = heat_transfer_coefficient / (
        face_width_mm * pinion_teeth * (pitch_velocity_ms * normal_module_mm) ** 0.75
    )
    convection = housing_resistance_k_m2_w / housing_surface_m2
    rise = (
        power_w
        * friction_coefficient
        * loss_factor_hv
        * (conduction + convection)
        * duty_cycle**0.64
    )
    return ambient_temperature_c + rise


# ---------------------------------------------------------------------------
# Wear and deformation  (VDI 2736 eq. 19, 22)
# ---------------------------------------------------------------------------
def linear_wear_um(
    *,
    torque_nm: float,
    load_cycles: float,
    loss_factor_hv: float,
    wear_coefficient_mm3_nm: float,  # k_w  [mm³/(N·m)]
    face_width_mm: float,
    teeth: int,
    active_flank_length_mm: float,
) -> float:
    """Mean linear wear W_m in µm (VDI 2736 eq. 19).

    W_m = T_d·2π·N_L·H_V·k_w/(b_w·z·l_Fl). Compare against W_zul = 0.1·m_n.
    """
    wear_mm = (
        torque_nm * 2.0 * math.pi * load_cycles * loss_factor_hv * wear_coefficient_mm3_nm
    ) / (face_width_mm * teeth * active_flank_length_mm)
    return wear_mm * 1000.0


def tooth_deformation_mm(
    *,
    tangential_force_n: float,
    face_width_mm: float,
    helix_angle_deg: float,
    elastic_modulus: Pair[float],
) -> float:
    """Tooth deformation λ in mm (VDI 2736 eq. 22).

    λ = 7.5·F_t/(b·cos β)·(1/E_1 + 1/E_2) — large for plastics (low E).
    """
    return (
        7.5
        * tangential_force_n
        / (face_width_mm * math.cos(math.radians(helix_angle_deg)))
        * (1.0 / elastic_modulus[0] + 1.0 / elastic_modulus[1])
    )


# ---------------------------------------------------------------------------
# Root and flank stress  (VDI 2736 eq. 10, 15-17)
# ---------------------------------------------------------------------------
def root_contact_ratio_factor(transverse_contact_ratio: float) -> float:
    """Root contact ratio factor Y_ε = 0.25 + 0.75/ε_α (VDI 2736)."""
    return 0.25 + 0.75 / transverse_contact_ratio


def root_stress(
    *,
    tangential_force_n: float,
    face_width_mm: float,
    normal_module_mm: float,
    form_factor_tip: float,  # Y_Fa
    stress_correction_tip: float,  # Y_Sa
    contact_ratio_factor: float,  # Y_ε
    helix_factor: float = 1.0,  # Y_β
    load_factor_kf: float = 1.0,  # K_F = K_A·K_v·K_Fα·K_Fβ
) -> float:
    """Tooth-root stress σ_F (VDI 2736 eq. 10), with the tip-load form factors."""
    return (
        load_factor_kf
        * form_factor_tip
        * stress_correction_tip
        * contact_ratio_factor
        * helix_factor
        * tangential_force_n
        / (face_width_mm * normal_module_mm)
    )


def flank_stress(
    stage: GearStage,
    materials: Pair[Material],
    *,
    tangential_force_n: float,
    face_width_mm: float,
    pinion_reference_diameter_mm: float,
    gear_ratio: float,
    zone: float | None = None,
    helix_factor: float = 1.0,  # Z_β (1 for spur)
    load_factor_kh: float = 1.0,  # K_H = K_A·K_v·K_Hα·K_Hβ
) -> float:
    """Flank (contact) stress σ_H (VDI 2736 eq. 15-17; same form as ISO 6336)."""
    z_e = elasticity_factor(materials[0], materials[1])
    z_h = zone_factor(stage) if zone is None else zone
    z_eps = flank_contact_ratio_factor(stage.transverse_contact_ratio, stage.overlap_ratio)
    return (
        z_e
        * z_h
        * z_eps
        * helix_factor
        * math.sqrt(
            tangential_force_n
            / (pinion_reference_diameter_mm * face_width_mm)
            * (gear_ratio + 1.0)
            / gear_ratio
        )
        * math.sqrt(load_factor_kh)
    )


def permissible_root_stress(fatigue_strength_mpa: float, *, minimum_safety: float = 2.0) -> float:
    """Permissible root stress σ_FP = σ_Flim,N(ϑ, N_L)/S_Fmin (VDI 2736)."""
    return fatigue_strength_mpa / minimum_safety


def permissible_flank_stress(
    fatigue_strength_mpa: float, *, roughness_factor: float = 1.0, minimum_safety: float = 1.4
) -> float:
    """Permissible flank stress σ_HP = σ_Hlim,N(ϑ, N_L)·Z_R/S_Hmin (VDI 2736 eq. 17)."""
    return fatigue_strength_mpa * roughness_factor / minimum_safety


class Vdi2736Conditions(BaseModel):
    """Operating + thermal/wear data for the plastic-gear VDI 2736 checks."""

    power_w: float  # P (rolling power)
    torque_nm: Pair[float]  # T_d per gear
    pitch_velocity_ms: float  # v_t
    ambient_temperature_c: float = 20.0  # ϑ_0
    friction_coefficient: float = 0.04  # μ (Table 1/2)
    flank_heat_coefficient: float = 0.0  # k_ϑ,Fla (Table 3; 0 if material-undefined)
    root_heat_coefficient: float = 0.0  # k_ϑ,Fuß
    housing_resistance_k_m2_w: float = 0.060  # R_λ,G (Table 4; closed housing)
    housing_surface_m2: float = 0.010  # A_G
    duty_cycle: float = 1.0  # ED
    load_cycles: Pair[float]  # N_L per gear
    wear_coefficient_mm3_nm: float = 1.0e-6  # k_w (Table 6)
    root_minimum_safety: float = 2.0  # S_Fmin
    flank_minimum_safety: float = 1.4  # S_Hmin
    flank_roughness_factor: float = 1.0  # Z_R
    load_factor_root: float = 1.0  # K_F
    load_factor_flank: float = 1.0  # K_H


class Vdi2736GearResult(BaseModel):
    """Per-gear (root) plus the shared mesh results of a VDI 2736 plastic evaluation."""

    root_stress_mpa: float  # σ_F
    flank_stress_mpa: float  # σ_H (shared mesh value)
    root_temperature_c: float  # ϑ_Fuß
    flank_temperature_c: float  # ϑ_Fla
    loss_factor: float  # H_V
    linear_wear_um: float  # W_m
    allowable_wear_um: float  # W_zul = 0.1·m_n
    deformation_mm: float  # λ
    root_safety: float | None = None  # S_F
    flank_safety: float | None = None  # S_H


def evaluate_vdi2736(
    stage: GearStage,
    roots: Pair[ToothRootGeometry],
    materials: Pair[Material],
    conditions: Vdi2736Conditions,
    *,
    root_face_width_mm: Pair[float],
    common_face_width_mm: float,
) -> Pair[Vdi2736GearResult]:
    """Evaluate the VDI 2736 plastic-gear capacity (root, flank, temperature, wear, deformation).

    Strength limits are read per gear from the material's ``root_strength_at`` /
    ``flank_strength_at`` (temperature- and cycle-dependent); when absent the safety
    is left ``None`` (graceful, ADR-013).
    """
    h_v = loss_factor(stage)
    u = stage.teeth[1] / stage.teeth[0]
    f_t = 2000.0 * conditions.torque_nm[0] / stage.reference_diameter_mm[0]
    sigma_h = flank_stress(
        stage,
        materials,
        tangential_force_n=f_t,
        face_width_mm=common_face_width_mm,
        pinion_reference_diameter_mm=stage.reference_diameter_mm[0],
        gear_ratio=u,
        load_factor_kh=conditions.load_factor_flank,
    )
    y_eps = root_contact_ratio_factor(stage.transverse_contact_ratio)
    deformation = tooth_deformation_mm(
        tangential_force_n=f_t,
        face_width_mm=root_face_width_mm[1],
        helix_angle_deg=stage.helix_angle_deg,
        elastic_modulus=Pair(materials[0].elastic_modulus_mpa, materials[1].elastic_modulus_mpa),
    )

    results: list[Vdi2736GearResult] = []
    for index in range(2):
        material = materials[index]
        root = roots[index]
        theta_root = tooth_temperature(
            ambient_temperature_c=conditions.ambient_temperature_c,
            power_w=conditions.power_w,
            friction_coefficient=conditions.friction_coefficient,
            loss_factor_hv=h_v,
            heat_transfer_coefficient=conditions.root_heat_coefficient,
            face_width_mm=common_face_width_mm,
            pinion_teeth=stage.teeth[0],
            pitch_velocity_ms=conditions.pitch_velocity_ms,
            normal_module_mm=stage.normal_module_mm,
            housing_resistance_k_m2_w=conditions.housing_resistance_k_m2_w,
            housing_surface_m2=conditions.housing_surface_m2,
            duty_cycle=conditions.duty_cycle,
        )
        theta_flank = tooth_temperature(
            ambient_temperature_c=conditions.ambient_temperature_c,
            power_w=conditions.power_w,
            friction_coefficient=conditions.friction_coefficient,
            loss_factor_hv=h_v,
            heat_transfer_coefficient=conditions.flank_heat_coefficient,
            face_width_mm=common_face_width_mm,
            pinion_teeth=stage.teeth[0],
            pitch_velocity_ms=conditions.pitch_velocity_ms,
            normal_module_mm=stage.normal_module_mm,
            housing_resistance_k_m2_w=conditions.housing_resistance_k_m2_w,
            housing_surface_m2=conditions.housing_surface_m2,
            duty_cycle=conditions.duty_cycle,
        )
        sigma_f = root_stress(
            tangential_force_n=f_t,
            face_width_mm=root_face_width_mm[index],
            normal_module_mm=stage.normal_module_mm,
            form_factor_tip=root.form_factor_tip,
            stress_correction_tip=root.stress_correction_factor_tip,
            contact_ratio_factor=y_eps,
            load_factor_kf=conditions.load_factor_root,
        )
        wear = linear_wear_um(
            torque_nm=conditions.torque_nm[index],
            load_cycles=conditions.load_cycles[index],
            loss_factor_hv=h_v,
            wear_coefficient_mm3_nm=conditions.wear_coefficient_mm3_nm,
            face_width_mm=common_face_width_mm,
            teeth=stage.teeth[index],
            active_flank_length_mm=active_flank_length_mm(stage, index),
        )

        root_strength = material.root_strength_at(theta_root, conditions.load_cycles[index])
        flank_strength = material.flank_strength_at(theta_flank, conditions.load_cycles[index])
        sigma_fp = (
            permissible_root_stress(root_strength, minimum_safety=conditions.root_minimum_safety)
            if root_strength is not None
            else None
        )
        sigma_hp = (
            permissible_flank_stress(
                flank_strength,
                roughness_factor=conditions.flank_roughness_factor,
                minimum_safety=conditions.flank_minimum_safety,
            )
            if flank_strength is not None
            else None
        )
        results.append(
            Vdi2736GearResult(
                root_stress_mpa=sigma_f,
                flank_stress_mpa=sigma_h,
                root_temperature_c=theta_root,
                flank_temperature_c=theta_flank,
                loss_factor=h_v,
                linear_wear_um=wear,
                allowable_wear_um=0.1 * stage.normal_module_mm * 1000.0,
                deformation_mm=deformation,
                root_safety=sigma_fp / sigma_f if sigma_fp is not None else None,
                flank_safety=sigma_hp / sigma_h if sigma_hp is not None else None,
            )
        )
    return Pair(results[0], results[1])
