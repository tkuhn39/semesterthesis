"""
@module: app.services.capacity.iso6336_root_strength
@context: Domain layer — ISO 6336-3:2019 tooth-root permissible-stress sub-factors.
@role: The factors that turn the root basic strength σ_FE into the permissible
       root stress σ_FP, so the root safety S_F = σ_FP/σ_F falls out *natively* from
       material + roughness + notch geometry inputs (no fed-in product): the
       relative surface factor Y_RrelT (§14.3, eq. 87–90), the relative notch
       sensitivity factor Y_δrelT (§11, eq. 75–77 with the slip-layer ρ′ of Table 4),
       and the size factor Y_X (§15). The life factor Y_NT (§10) stays an input — it
       depends on the material S-N curve (an operating/material datum, not a tool
       output).

Validated against both complete references: kst-E (spur, DIN 3990 via STplus) and
the helical ISO 6336 case ([[din3990-helical-reference]]): Y_RrelT 0.957 / 0.915,
Y_δrelT 1.001 / 0.996, and σ_FP 823 / 714.1 → S_F 4.571 / 2.275.
"""

import math
from enum import StrEnum


class RootMaterialGroup(StrEnum):
    """ISO 6336-3 material group for ρ′ (Table 4) and the Y_RrelT formula (eq. 87–89)."""

    CASE_HARDENED = "case_hardened"  # Eh, IF (case/surface hardened)
    THROUGH_HARDENED = "through_hardened"  # V, GTS, GGG (perl., bai.)
    NORMALIZED = "normalized"  # St (normalized steel)
    NITRIDED = "nitrided"  # NT, NV (nitrided)
    CAST_IRON = "cast_iron"  # GG, GGG (ferr.)


# Slip-layer thickness ρ′ [mm] (ISO 6336-3 Table 4); a representative value per group
# (interpolatable by σ_S/σ_0.2 within a group — refined when material strength is known).
_SLIP_LAYER_MM: dict[RootMaterialGroup, float] = {
    RootMaterialGroup.CASE_HARDENED: 0.0030,
    RootMaterialGroup.THROUGH_HARDENED: 0.0064,
    RootMaterialGroup.NORMALIZED: 0.0445,
    RootMaterialGroup.NITRIDED: 0.1005,
    RootMaterialGroup.CAST_IRON: 0.3095,
}

_REFERENCE_NOTCH_PARAMETER = 2.5  # q_sT of the standard reference test gear


def relative_surface_factor(roughness_rz_um: float, group: RootMaterialGroup) -> float:
    """Relative surface factor Y_RrelT (ISO 6336-3 eq. 87–89, 1 µm ≤ R_z ≤ 40 µm)."""
    rz = min(40.0, max(1.0, roughness_rz_um))
    if group in (RootMaterialGroup.CASE_HARDENED, RootMaterialGroup.THROUGH_HARDENED):
        return 1.674 - 0.529 * (rz + 1.0) ** 0.1
    if group is RootMaterialGroup.NORMALIZED:
        return 5.306 - 4.203 * (rz + 1.0) ** 0.01
    return 4.299 - 3.259 * (rz + 1.0) ** 0.005


def relative_notch_sensitivity_factor(notch_parameter_qs: float, group: RootMaterialGroup) -> float:
    """Relative notch sensitivity factor Y_δrelT (ISO 6336-3 eq. 75–77)."""
    slip_layer = _SLIP_LAYER_MM[group]
    gradient = (1.0 + 2.0 * notch_parameter_qs) / 5.0  # χ* (eq. 76–77)
    gradient_ref = (1.0 + 2.0 * _REFERENCE_NOTCH_PARAMETER) / 5.0  # χ*_T (= 1.2)
    return (1.0 + math.sqrt(slip_layer * gradient)) / (1.0 + math.sqrt(slip_layer * gradient_ref))


def size_factor(normal_module_mm: float, group: RootMaterialGroup) -> float:
    """Size factor Y_X for the tooth root (ISO 6336-3 §15); 1.0 for m_n ≤ 5 mm."""
    if normal_module_mm <= 5.0:
        return 1.0
    if group in (
        RootMaterialGroup.CASE_HARDENED,
        RootMaterialGroup.THROUGH_HARDENED,
        RootMaterialGroup.NITRIDED,
    ):
        return max(0.85, 1.03 - 0.006 * normal_module_mm)
    if group is RootMaterialGroup.NORMALIZED:
        return max(0.85, 1.05 - 0.010 * normal_module_mm)
    return max(0.85, 1.075 - 0.015 * normal_module_mm)


def permissible_root_stress(
    basic_root_strength_mpa: float,
    *,
    notch_parameter_qs: float,
    roughness_rz_um: float,
    normal_module_mm: float,
    group: RootMaterialGroup,
    life_factor: float = 1.0,
) -> float:
    """Permissible root stress σ_FP = σ_FE · Y_NT · Y_δrelT · Y_RrelT · Y_X (ISO 6336-3).

    ``life_factor`` is Y_NT (the material S-N life factor); the surface, notch and
    size factors are computed natively here, so S_F = σ_FP / σ_F is native.
    """
    return (
        basic_root_strength_mpa
        * life_factor
        * relative_notch_sensitivity_factor(notch_parameter_qs, group)
        * relative_surface_factor(roughness_rz_um, group)
        * size_factor(normal_module_mm, group)
    )
