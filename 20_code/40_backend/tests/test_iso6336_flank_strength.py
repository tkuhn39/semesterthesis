"""
@module: tests.test_iso6336_flank_strength
@context: Domain-layer tests — ISO 6336-2 flank permissible-stress sub-factors.
@role: The lubricant-film factors (Z_L, Z_v, Z_R), ρ_red and the permissible flank
       stress σ_HP reproduce the helical ISO 6336 reference, so the flank safety
       S_H = σ_HP/σ_H is native (de-circularised).
"""

import pytest

from app.services.capacity.iso6336_flank_strength import (
    lubricant_factor,
    permissible_flank_stress,
    relative_radius_of_curvature_mm,
    roughness_factor,
    velocity_factor,
    work_hardening_factor,
)

# helical ISO 6336 reference: σ_Hlim = 1500, db = 49.617/79.387, α_wt = 21.173°,
# Rz_flank = 18 µm, ν40 ≈ 318, v ≈ 8.33 m/s.
_SIGMA_HLIM = 1500.0


def test_relative_radius_and_roughness_factor() -> None:
    """ρ_red (eq. 51–52) and Z_R (eq. 53) match the helical reference exactly."""
    rho_red = relative_radius_of_curvature_mm(49.617, 79.387, 21.173)
    assert rho_red == pytest.approx(5.91, abs=0.02)
    assert roughness_factor(18.0, rho_red, _SIGMA_HLIM) == pytest.approx(0.854, abs=2e-3)


def test_lubricant_and_velocity_factor() -> None:
    """Z_L (eq. 42) and Z_v (eq. 47) reproduce the helical reference factors."""
    assert lubricant_factor(318.0, _SIGMA_HLIM) == pytest.approx(1.047, abs=2e-3)
    assert velocity_factor(8.33, _SIGMA_HLIM) == pytest.approx(0.995, abs=2e-3)
    assert work_hardening_factor() == 1.0


def test_permissible_flank_stress_de_circularises_safety() -> None:
    """σ_HP and S_H = σ_HP/σ_H fall out natively for the helical reference."""
    rho_red = relative_radius_of_curvature_mm(49.617, 79.387, 21.173)
    sigma_hp = permissible_flank_stress(
        _SIGMA_HLIM,
        life_factor=0.85,  # Z_NT
        lubricant=lubricant_factor(318.0, _SIGMA_HLIM),
        velocity=velocity_factor(8.33, _SIGMA_HLIM),
        roughness=roughness_factor(18.0, rho_red, _SIGMA_HLIM),
    )
    assert sigma_hp == pytest.approx(1135.4, abs=2.0)
    assert sigma_hp / 1087.2 == pytest.approx(1.044, abs=3e-3)
