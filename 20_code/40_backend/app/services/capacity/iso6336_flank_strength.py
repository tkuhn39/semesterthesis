"""
@module: app.services.capacity.iso6336_flank_strength
@context: Domain layer — ISO 6336-2:2019 flank permissible-stress sub-factors.
@role: The factors that turn the flank endurance limit σ_Hlim into the permissible
       flank stress σ_HP, so the flank safety S_H = σ_HP/σ_H is native — the lubricant
       film factors Z_L (eq. 42–45), Z_v (eq. 47–48) and Z_R (eq. 49–56, via the
       relative radius of curvature ρ_red), the work-hardening factor Z_W (clause 13)
       and the size factor Z_X (clause 14). The life factor Z_NT (clause 10) stays an
       input (a material S-N datum, like Y_NT for the root).

Validated against the helical ISO 6336 reference ([[din3990-helical-reference]]):
Z_R = 0.854 (R_z = 18, ρ_red ≈ 5.91, σ_Hlim = 1500), Z_L = 1.047, Z_v = 0.995,
Z_W = 1.000 → σ_HP = 1135.4, S_H = 1.044. (STplus reports Z_L=Z_v=Z_R=1.0 for kst-E,
a tool convention; the ISO 6336 values are used — ADR-011.)
"""

import math


def _c_zl(sigma_hlim_mpa: float) -> float:
    """Constant C_ZL for Z_L / Z_v (ISO 6336-2 eq. 43–45)."""
    if sigma_hlim_mpa < 850.0:
        return 0.83
    if sigma_hlim_mpa > 1200.0:
        return 0.91
    return sigma_hlim_mpa / 4375.0 + 0.6357


def lubricant_factor(nominal_viscosity_40_mm2s: float, sigma_hlim_mpa: float) -> float:
    """Lubricant factor Z_L (ISO 6336-2 eq. 42)."""
    c_zl = _c_zl(sigma_hlim_mpa)
    return c_zl + 4.0 * (1.0 - c_zl) / (1.2 + 134.0 / nominal_viscosity_40_mm2s) ** 2


def velocity_factor(pitch_line_velocity_ms: float, sigma_hlim_mpa: float) -> float:
    """Velocity factor Z_v (ISO 6336-2 eq. 47–48)."""
    c_zv = _c_zl(sigma_hlim_mpa) + 0.02
    return c_zv + 2.0 * (1.0 - c_zv) / math.sqrt(0.8 + 32.0 / pitch_line_velocity_ms)


def relative_radius_of_curvature_mm(
    base_diameter_pinion_mm: float, base_diameter_wheel_mm: float, working_pressure_angle_deg: float
) -> float:
    """Relative radius of curvature at the pitch point ρ_red (ISO 6336-2 eq. 51–52).

    db has a positive sign for external, negative for internal gears.
    """
    alpha_wt = math.radians(working_pressure_angle_deg)
    rho_1 = 0.5 * base_diameter_pinion_mm * math.tan(alpha_wt)
    rho_2 = 0.5 * base_diameter_wheel_mm * math.tan(alpha_wt)
    return rho_1 * rho_2 / (rho_1 + rho_2)


def _c_zr(sigma_hlim_mpa: float) -> float:
    """Constant C_ZR for Z_R (ISO 6336-2 eq. 54–56)."""
    if sigma_hlim_mpa < 850.0:
        return 0.15
    if sigma_hlim_mpa > 1200.0:
        return 0.08
    return 0.32 - 0.0002 * sigma_hlim_mpa


def roughness_factor(
    mean_roughness_rz_um: float, relative_radius_mm: float, sigma_hlim_mpa: float
) -> float:
    """Roughness factor Z_R (ISO 6336-2 eq. 50, 53). ``mean_roughness`` = (Rz1+Rz2)/2."""
    rz10 = mean_roughness_rz_um * (10.0 / relative_radius_mm) ** (1.0 / 3.0)
    return (3.0 / rz10) ** _c_zr(sigma_hlim_mpa)


def work_hardening_factor(softer_gear_hardness_hb: float | None = None) -> float:
    """Work-hardening factor Z_W (ISO 6336-2 clause 13); 1.0 unless paired with a soft gear."""
    if softer_gear_hardness_hb is None:
        return 1.0
    hardness = min(470.0, max(130.0, softer_gear_hardness_hb))
    return 1.2 - (hardness - 130.0) / 1700.0


def size_factor() -> float:
    """Size factor Z_X (ISO 6336-2 clause 14); 1.0 for surface durability."""
    return 1.0


def permissible_flank_stress(
    sigma_hlim_mpa: float,
    *,
    life_factor: float = 1.0,
    lubricant: float = 1.0,
    velocity: float = 1.0,
    roughness: float = 1.0,
    work_hardening: float = 1.0,
    size: float = 1.0,
) -> float:
    """Permissible flank stress σ_HP = σ_Hlim · Z_NT · Z_L · Z_v · Z_R · Z_W · Z_X (ISO 6336-2)."""
    return sigma_hlim_mpa * life_factor * lubricant * velocity * roughness * work_hardening * size
