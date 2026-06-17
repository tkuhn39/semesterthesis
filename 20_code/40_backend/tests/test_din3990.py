"""
@module: tests.test_din3990
@context: Domain-layer tests — DIN 3990 tooth capacity.
@role: The flank and root stresses, the geometry factors (Z_E, Z_H) and the safety
       factors reproduce the STplus DIN 3990 output for the project gear (kst-E).
"""

from pathlib import Path

import pytest

from app.io.ste import Pair, gear_stage_from_ste, load_ste
from app.services.capacity import (
    Din3990LoadCase,
    Iso6336Conditions,
    RootMaterialGroup,
    elasticity_factor,
    evaluate_din3990,
    single_contact_factors,
    zone_factor,
)
from app.services.geometry.gear import GearStage
from app.services.geometry.tooth_root import ToothRootGeometry
from app.services.materials import material_from_ste

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)


@pytest.mark.skipif(not _REF_STE.exists(), reason="STplus reference .ste not present")
def test_din3990_matches_stplus() -> None:
    """Flank/root stresses, Z_E/Z_H and safety reproduce the STplus DIN 3990 output."""
    ste = load_ste(_REF_STE)
    stage = GearStage.from_ste(gear_stage_from_ste(ste))
    roots = Pair(ToothRootGeometry.from_stage(stage, 0), ToothRootGeometry.from_stage(stage, 1))
    materials = Pair(material_from_ste(ste, "16MnCr5"), material_from_ste(ste, "WST_PA66"))

    assert elasticity_factor(materials[0], materials[1]) == pytest.approx(31.0, abs=0.1)
    assert zone_factor(stage) == pytest.approx(2.400, abs=2e-3)

    load = Din3990LoadCase(
        tangential_force_n=384.6,
        common_face_width_mm=15.0,
        root_face_width_mm=Pair(17.0, 15.0),
        gear_ratio=52.0 / 51.0,
        pinion_reference_diameter_mm=51.0,
        application_factor=1.0,
        dynamic_factor=1.56,
        face_load_factor_flank=1.19,
        face_load_factor_root=1.16,
    )
    conditions = Iso6336Conditions(
        pitch_line_velocity_ms=2.696,
        lubricant_viscosity_40_mm2s=100.0,
        flank_roughness_rz_um=5.0,
        root_roughness_rz_um=Pair(20.0, 20.0),
        material_group=Pair(RootMaterialGroup.CASE_HARDENED, RootMaterialGroup.CASE_HARDENED),
        flank_life_factor=Pair(1.172, 1.0),  # Z_NT (material S-N)
        root_life_factor=Pair(1.0, 1.0),  # Y_NT
    )
    pinion, wheel = evaluate_din3990(stage, roots, materials, load, conditions)

    # Stresses — exact vs STplus.
    assert pinion.nominal_root_stress_mpa == pytest.approx(99.5, abs=0.3)
    assert wheel.nominal_root_stress_mpa == pytest.approx(100.2, abs=0.3)
    assert pinion.root_stress_mpa == pytest.approx(180.1, abs=0.6)
    assert wheel.root_stress_mpa == pytest.approx(181.4, abs=0.6)
    assert pinion.flank_stress_mpa == pytest.approx(99.6, abs=0.5)
    assert wheel.flank_stress_mpa == pytest.approx(99.5, abs=0.5)

    # Root safety — native σ_FP matches STplus for the steel pinion.
    assert pinion.root_safety == pytest.approx(4.571, abs=0.05)
    # Flank safety — native ISO 6336 lubricant factors (Z_L·Z_v·Z_R ≈ 0.88) give
    # S_H ≈ 15.1; STplus reports 17.184 using Z_L=Z_v=Z_R=1.0 (a DIN 3990 convention,
    # ADR-011). The native flank is validated exactly against the helical ISO 6336
    # case (S_H = 1.044) in test_iso6336_flank_strength.
    assert pinion.flank_safety is not None
    assert pinion.flank_safety == pytest.approx(15.1, abs=0.5)


@pytest.mark.skipif(not _REF_STE.exists(), reason="STplus reference .ste not present")
def test_single_contact_factors_spur() -> None:
    """Z_B/Z_D use the usable tip d_Na; match STplus for the (spur) project gear."""
    stage = GearStage.from_ste(gear_stage_from_ste(load_ste(_REF_STE)))
    z_b, z_d = single_contact_factors(stage)
    assert z_b == pytest.approx(1.009, abs=1e-3)
    assert z_d == pytest.approx(1.008, abs=1e-3)


def test_single_contact_factors_helical_overlap() -> None:
    """For a helical stage with overlap ratio ε_β ≥ 1, Z_B = Z_D = 1.0 (ISO 6336-2)."""
    helical = GearStage(
        normal_module_mm=2.0,
        teeth=Pair(25, 40),
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=20.0,
        face_width_mm=Pair(26.0, 26.0),
        center_distance_mm=69.172,
    )
    assert helical.overlap_ratio >= 1.0
    assert single_contact_factors(helical) == pytest.approx((1.0, 1.0))
