"""
@module: tests.test_iso6336_root_strength
@context: Domain-layer tests — ISO 6336-3 root permissible-stress sub-factors.
@role: The relative surface (Y_RrelT) and notch sensitivity (Y_δrelT) factors and
       the permissible root stress σ_FP match BOTH complete references — kst-E
       (spur, DIN 3990 via STplus) and the helical ISO 6336 case — so the root
       safety S_F is now native (de-circularised), not a fed-in product.
"""

import pytest

from app.services.capacity.iso6336_root_strength import (
    RootMaterialGroup,
    permissible_root_stress,
    relative_notch_sensitivity_factor,
    relative_surface_factor,
    size_factor,
)

_EH = RootMaterialGroup.CASE_HARDENED  # both reference gears are case-hardened


def test_relative_surface_factor_matches_both_references() -> None:
    """Y_RrelT (ISO 6336-3 eq. 87) vs kst-E (Rz=20) and helical (Rz=36)."""
    assert relative_surface_factor(20.0, _EH) == pytest.approx(0.957, abs=1e-3)
    assert relative_surface_factor(36.0, _EH) == pytest.approx(0.915, abs=1e-3)


def test_relative_notch_sensitivity_matches_both_references() -> None:
    """Y_δrelT (ISO 6336-3 eq. 75–77, ρ′=0.003) vs kst-E (q_s=2.56) and helical (q_s≈2.07)."""
    assert relative_notch_sensitivity_factor(2.56, _EH) == pytest.approx(1.001, abs=1e-3)
    assert relative_notch_sensitivity_factor(2.072, _EH) == pytest.approx(0.996, abs=1e-3)


def test_permissible_root_stress_de_circularises_safety() -> None:
    """σ_FP and S_F = σ_FP/σ_F fall out natively for both references."""
    # kst-E steel pinion: σ_FE=860, q_s=2.56, Rz=20, m_n=1, Y_NT=1.0
    kst_e = permissible_root_stress(
        860.0, notch_parameter_qs=2.56, roughness_rz_um=20.0, normal_module_mm=1.0, group=_EH
    )
    assert kst_e == pytest.approx(823.2, abs=2.0)
    assert kst_e / 180.1 == pytest.approx(4.571, abs=0.03)

    # helical pinion: σ_FE=2·σ_Flim=922, q_s≈2.07, Rz=36, m_n=2, Y_NT=0.85
    helical = permissible_root_stress(
        922.0,
        notch_parameter_qs=2.072,
        roughness_rz_um=36.0,
        normal_module_mm=2.0,
        group=_EH,
        life_factor=0.85,
    )
    assert helical == pytest.approx(714.1, abs=2.0)
    assert helical / 313.9 == pytest.approx(2.275, abs=0.02)


def test_size_factor_table5_groups() -> None:
    """Y_X per ISO 6336-3:2019 Table 5 (audit NRM-05): slopes and floors per group."""
    for group in RootMaterialGroup:
        assert size_factor(5.0, group) == 1.0  # m_n ≤ 5 → 1.0 for every group
    # St, V (through-hardened/normalized): 1.03 − 0.006·m_n, floor 0.85
    assert size_factor(10.0, RootMaterialGroup.THROUGH_HARDENED) == pytest.approx(0.97)
    assert size_factor(45.0, RootMaterialGroup.NORMALIZED) == pytest.approx(0.85)
    # Eh, IF, NT, NV: 1.05 − 0.01·m_n, floor 0.80
    assert size_factor(10.0, RootMaterialGroup.CASE_HARDENED) == pytest.approx(0.95)
    assert size_factor(30.0, RootMaterialGroup.NITRIDED) == pytest.approx(0.80)
    # GG, GGG (ferr.): 1.075 − 0.015·m_n, floor 0.70
    assert size_factor(10.0, RootMaterialGroup.CAST_IRON) == pytest.approx(0.925)
    assert size_factor(30.0, RootMaterialGroup.CAST_IRON) == pytest.approx(0.70)
