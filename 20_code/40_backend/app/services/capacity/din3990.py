"""
@module: app.services.capacity.din3990
@context: Domain layer — steel gear load capacity (DIN 3990 Teil 1–3, Dec 1987).
@role: Flank (pitting) and tooth-root (bending) stress and the resulting safety
       factors. The geometry-derived factors (elasticity Z_E, zone Z_H, contact
       ratio Z_ε; form Y_F and stress-correction Y_S from the tooth-root module)
       are computed exactly; the load/dynamic/face/transverse factors (K_A, K_v,
       K_Hβ, K_Fβ, K_Hα, K_Fα), the single-contact factors (Z_B, Z_D) and the
       permissible-stress life/sub factors are typed inputs with neutral defaults,
       so a partly specified case still evaluates (graceful — a missing factor
       defaults to 1.0 rather than blocking).

Stresses validated exactly against STplus (kst-E): σ_H0 = 72.4, σ_H = 99.6/99.5,
σ_F0 = 99.5/100.2, σ_F = 180.1/181.4 (with K_A=1, K_v=1.56, K_Hβ=1.19, K_Fβ=1.16).
"""

import math

from pydantic import BaseModel

from app.io.ste import Pair
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


class Din3990LoadCase(BaseModel):
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
    single_contact_factor: Pair[float] = Pair(1.0, 1.0)  # Z_B (pinion), Z_D (wheel)
    helix_factor_root: float = 1.0  # Y_β


class Din3990GearResult(BaseModel):
    """Per-gear DIN 3990 result: flank and root stress and (when limits known) safety."""

    flank_stress_mpa: float  # σ_H
    nominal_flank_stress_mpa: float  # σ_H0
    root_stress_mpa: float  # σ_F
    nominal_root_stress_mpa: float  # σ_F0
    flank_safety: float | None = None  # S_H
    root_safety: float | None = None  # S_F


def _gear_result(
    *,
    sigma_h0: float,
    single_contact: float,
    load: Din3990LoadCase,
    nominal_root: float,
    material: Material,
    flank_strength_product: float,
    root_strength_product: float,
) -> Din3990GearResult:
    sigma_h = (
        single_contact
        * sigma_h0
        * math.sqrt(
            load.application_factor
            * load.dynamic_factor
            * load.face_load_factor_flank
            * load.transverse_factor_flank
        )
    )
    sigma_f = nominal_root * (
        load.application_factor
        * load.dynamic_factor
        * load.face_load_factor_root
        * load.transverse_factor_root
    )
    flank_safety: float | None = None
    if material.sigma_hlim_mpa is not None:
        flank_safety = material.sigma_hlim_mpa * flank_strength_product / sigma_h
    root_safety: float | None = None
    root_basic = material.sigma_fe_mpa
    if root_basic is None and material.sigma_flim_mpa is not None:
        root_basic = 2.0 * material.sigma_flim_mpa  # σ_FE = σ_Flim · Y_ST, Y_ST = 2
    if root_basic is not None:
        root_safety = root_basic * root_strength_product / sigma_f
    return Din3990GearResult(
        flank_stress_mpa=sigma_h,
        nominal_flank_stress_mpa=sigma_h0,
        root_stress_mpa=sigma_f,
        nominal_root_stress_mpa=nominal_root,
        flank_safety=flank_safety,
        root_safety=root_safety,
    )


_UNIT_PAIR: Pair[float] = Pair(1.0, 1.0)


def evaluate_din3990(
    stage: GearStage,
    roots: Pair[ToothRootGeometry],
    materials: Pair[Material],
    load: Din3990LoadCase,
    *,
    flank_strength_product: Pair[float] = _UNIT_PAIR,
    root_strength_product: Pair[float] = _UNIT_PAIR,
) -> Pair[Din3990GearResult]:
    """Evaluate DIN 3990 flank and root capacity for both gears.

    ``*_strength_product`` are the per-gear products of the permissible-stress life
    and sub factors (flank: Z_NT·Z_L·Z_R·Z_V·Z_W·Z_X; root: Y_NT·Y_δrelT·Y_RrelT·Y_X);
    default 1.0. With the raw endurance limits this yields the static safety.
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
    results: list[Din3990GearResult] = []
    for index in range(2):
        root = roots[index]
        nominal_root = (
            load.tangential_force_n
            / (load.root_face_width_mm[index] * stage.normal_module_mm)
            * root.form_factor
            * root.stress_correction_factor
            * load.helix_factor_root
        )
        results.append(
            _gear_result(
                sigma_h0=sigma_h0,
                single_contact=load.single_contact_factor[index],
                load=load,
                nominal_root=nominal_root,
                material=materials[index],
                flank_strength_product=flank_strength_product[index],
                root_strength_product=root_strength_product[index],
            )
        )
    return Pair(results[0], results[1])
