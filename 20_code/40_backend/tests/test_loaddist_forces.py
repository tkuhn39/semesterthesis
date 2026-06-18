"""
@module: tests.test_loaddist_forces
@context: Domain-layer tests — RIKOR (FVA 30) step R1: nominal mesh forces + stiffness.
@role: For the RIKOR standard test 001 (single helical stage) the nominal forces and
       the ISO 6336-1 mesh stiffness reproduce the RIKOR report exactly (to its
       rounding): F_bt, F_bt/b, F_bn, F_bx and c_γ.
"""

from pathlib import Path

import pytest

from app.io.rie import RikorInput
from app.services.loaddist import evaluate_mesh

_EX001 = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "35_Rikor"
    / "RIKOR_exec"
    / "work"
    / "Beispiele"
    / "001_eine_stufe"
    / "1_Eingabe"
    / "rikor.rie"
)


@pytest.mark.skipif(not _EX001.exists(), reason="RIKOR example 001 not present")
def test_mesh_forces_and_stiffness_match_rikor_001() -> None:
    """Forces and mesh stiffness reproduce RIKOR test 001 (to the report's rounding)."""
    mesh = evaluate_mesh(RikorInput.load(_EX001))

    # design torque = K_A · T_nom = 1.5 · 5975 = 8962.5 Nm
    assert mesh.design_torque_nm == pytest.approx(8962.5)

    f = mesh.forces
    assert f.tangential_force_n == pytest.approx(167555.8, rel=1e-4)  # F_bt
    assert f.line_load_n_per_mm == pytest.approx(1319.34, rel=1e-4)  # F_bt/b
    assert f.normal_force_n == pytest.approx(170316.0, rel=1e-4)  # F_bn
    assert f.axial_force_n == pytest.approx(30538.0, rel=1e-4)  # F_bx
    assert f.common_face_width_mm == 127.0

    s = mesh.stiffness
    assert s.theoretical_single == pytest.approx(18.44, abs=0.1)  # c_sth
    assert s.basic_rack_factor == pytest.approx(0.87, abs=0.01)  # C_B
    assert s.mesh_alpha == pytest.approx(16.70, abs=0.1)  # c_γ


@pytest.mark.skipif(not _EX001.exists(), reason="RIKOR example 001 not present")
def test_drive_gear_is_the_pinion() -> None:
    """The drive gear (torque shaft) is ordered first and is the pinion (z=14)."""
    mesh = evaluate_mesh(RikorInput.load(_EX001))
    assert mesh.stage.teeth[0] == 14
    assert mesh.stage.teeth[1] == 59
