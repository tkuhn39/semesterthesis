"""
@module: tests.test_vdi2736
@context: Domain-layer tests — plastic gear capacity (VDI 2736 Blatt 2).
@role: The full plastic capacity (root, flank, tooth temperature, wear, deformation)
       reproduces the FVA-Workbench VDI-2736 report, which is the kst-E steel–plastic
       pair (z 51/52, m_n 1). All inputs are known, so the match is near-exact.
"""

from pathlib import Path

import pytest

from app.io.ste import Pair, gear_stage_from_ste, load_ste
from app.services.capacity.vdi2736 import (
    Vdi2736Conditions,
    active_flank_length_mm,
    evaluate_vdi2736,
    loss_factor,
    partial_contact_ratios,
    permissible_peak_stress,
    tooth_deformation_mm,
)
from app.services.geometry.gear import GearStage
from app.services.geometry.tooth_root import ToothRootGeometry
from app.services.materials import Material, MaterialKind

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)


def _case() -> tuple[GearStage, Pair[ToothRootGeometry], Pair[Material], Vdi2736Conditions]:
    stage = GearStage.from_ste(gear_stage_from_ste(load_ste(_REF_STE)))
    roots = Pair(ToothRootGeometry.from_stage(stage, 0), ToothRootGeometry.from_stage(stage, 1))
    materials = Pair(
        Material(
            name="20MnCr5",
            kind=MaterialKind.STEEL,
            elastic_modulus_mpa=210000.0,
            poisson_ratio=0.30,
        ),
        Material(
            name="Kunststoff",
            kind=MaterialKind.PLASTIC,
            elastic_modulus_mpa=4156.0,
            poisson_ratio=0.34,
        ),
    )
    conditions = Vdi2736Conditions(
        power_w=1848.706,
        torque_nm=Pair(7.85, 8.00),
        pitch_velocity_ms=6.067,
        ambient_temperature_c=80.0,
        friction_coefficient=0.04,
        housing_resistance_k_m2_w=0.060,
        housing_surface_m2=0.010,
        duty_cycle=1.0,
        load_cycles=Pair(1.350e7, 1.324e7),
        wear_coefficient_mm3_nm=1.0e-6,
    )
    return stage, roots, materials, conditions


def test_tooth_deformation_matches_report() -> None:
    """λ = 7.5·F_t/(b·cos β)·(1/E1 + 1/E2) = 0.0378 mm (ref 0.038)."""
    lam = tooth_deformation_mm(
        tangential_force_n=307.7,
        face_width_mm=15.0,
        helix_angle_deg=0.0,
        elastic_modulus=Pair(210000.0, 4156.0),
    )
    assert lam == pytest.approx(0.038, abs=5e-4)


@pytest.mark.skipif(not _REF_STE.exists(), reason="kst-E reference .ste not present")
def test_loss_factor_and_partial_contact_ratios() -> None:
    """H_V (Wimmer) = 0.0626 and ε_1/ε_2 = 0.600/0.554 (ref)."""
    stage, *_ = _case()
    eps1, eps2 = partial_contact_ratios(stage)
    assert eps1 == pytest.approx(0.600, abs=2e-3)
    assert eps2 == pytest.approx(0.554, abs=2e-3)
    assert loss_factor(stage) == pytest.approx(0.063, abs=1e-3)


@pytest.mark.skipif(not _REF_STE.exists(), reason="kst-E reference .ste not present")
def test_active_flank_length_matches_report() -> None:
    """l_Fl = (d_Na² − d_Nf²)/(4 d_b) = 1.349/1.330 mm (ref)."""
    stage, *_ = _case()
    assert active_flank_length_mm(stage, 0) == pytest.approx(1.349, abs=2e-3)
    assert active_flank_length_mm(stage, 1) == pytest.approx(1.330, abs=2e-3)


@pytest.mark.skipif(not _REF_STE.exists(), reason="kst-E reference .ste not present")
def test_vdi2736_full_capacity_matches_report() -> None:
    """Root, flank, temperature, wear and deformation reproduce the VDI-2736 report."""
    stage, roots, materials, conditions = _case()
    pinion, wheel = evaluate_vdi2736(
        stage,
        roots,
        materials,
        conditions,
        root_face_width_mm=Pair(17.0, 15.0),
        common_face_width_mm=15.0,
    )
    # flank (shared mesh): Z_E (steel–plastic) drives σ_H
    assert wheel.flank_stress_mpa == pytest.approx(79.893, abs=0.1)
    # root: the plastic wheel governs (its displayed Y_Fa is a Workbench artefact;
    # the native Y_Fa reproduces the report's σ_F — ADR-011)
    assert wheel.root_stress_mpa == pytest.approx(77.896, rel=3e-3)
    # tooth temperature (frictional rise over the 80 °C ambient)
    assert wheel.root_temperature_c == pytest.approx(107.767, abs=0.05)
    assert wheel.flank_temperature_c == pytest.approx(107.767, abs=0.05)
    # wear and deformation
    assert wheel.linear_wear_um == pytest.approx(40.151, abs=0.2)
    assert wheel.allowable_wear_um == pytest.approx(100.0)
    assert wheel.deformation_mm == pytest.approx(0.038, abs=5e-4)
    assert wheel.loss_factor == pytest.approx(0.063, abs=1e-3)


def test_permissible_peak_stress() -> None:
    """Static peak permissible σ_FP = 2·σ_S/S_Smin (VDI 2736 §3.3 eq. 24)."""
    assert permissible_peak_stress(70.0, minimum_safety=1.5) == pytest.approx(2.0 * 70.0 / 1.5)


@pytest.mark.skipif(not _REF_STE.exists(), reason="kst-E reference .ste not present")
def test_static_peak_load() -> None:
    """σ_F,P = σ_F0·K_A,stat and S_static = (2·σ_S/S_Smin)/σ_F,P for the plastic wheel."""
    stage, roots, _materials, base = _case()
    materials = Pair(
        _materials[0],
        _materials[1].model_copy(update={"yield_strength_mpa": 70.0}),
    )
    k_stat = 2.0
    conditions = base.model_copy(
        update={"static_overload_factor": k_stat, "static_minimum_safety": 1.5}
    )
    _pin, wheel = evaluate_vdi2736(
        stage,
        roots,
        materials,
        conditions,
        root_face_width_mm=Pair(17.0, 15.0),
        common_face_width_mm=15.0,
    )
    # nominal σ_F (K_F = load_factor_root = 1 by default here) → peak = σ_F·k_stat
    assert wheel.peak_root_stress_mpa == pytest.approx(wheel.root_stress_mpa * k_stat, rel=1e-6)
    assert wheel.peak_root_safety == pytest.approx(
        (2.0 * 70.0 / 1.5) / wheel.peak_root_stress_mpa, rel=1e-6
    )


def test_strength_lookup_temperature_and_cycles() -> None:
    """The material strength lookup interpolates a VDI-2736 Table-5-style grid."""
    from app.services.materials import StrengthPoint

    curve = [
        StrengthPoint(temperature_c=20.0, cycles=1e5, stress_mpa=50.0),
        StrengthPoint(temperature_c=20.0, cycles=1e7, stress_mpa=40.0),
        StrengthPoint(temperature_c=100.0, cycles=1e5, stress_mpa=25.0),
        StrengthPoint(temperature_c=100.0, cycles=1e7, stress_mpa=20.0),
    ]
    mat = Material(
        name="POM",
        kind=MaterialKind.PLASTIC,
        elastic_modulus_mpa=4000.0,
        poisson_ratio=0.34,
        root_strength_curve=curve,
    )
    # corner points exact
    assert mat.root_strength_at(20.0, 1e5) == pytest.approx(50.0)
    assert mat.root_strength_at(100.0, 1e7) == pytest.approx(20.0)
    # interpolated centre (60 °C, 1e6): bilinear over temp and log10(cycles)
    assert mat.root_strength_at(60.0, 1e6) == pytest.approx(33.75, abs=1e-6)
    # absent curve → graceful None
    assert (
        Material(
            name="x", kind=MaterialKind.PLASTIC, elastic_modulus_mpa=4000.0, poisson_ratio=0.34
        ).root_strength_at(60.0, 1e6)
        is None
    )
