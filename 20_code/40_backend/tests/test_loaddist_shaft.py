"""
@module: tests.test_loaddist_shaft
@context: Domain-layer tests — RIKOR (FVA 30) step R2: shaft deflection → mesh gap.
@role: The beam FE solver matches closed-form beam deflection exactly; the assembled
       mesh gap reproduces RIKOR standard test 001's "Gesamtkorrektur" in shape and
       magnitude (bending + torsion + shear; peak ≈ 42 µm, vertex in the loaded face).
"""

from pathlib import Path

import numpy as np
import pytest

from app.io.rie import RikorInput
from app.services.loaddist.beam import BeamModel
from app.services.loaddist.shaft import mesh_gap

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


def _uniform_beam(ei: float, length: float, n: int = 41) -> tuple[np.ndarray, np.ndarray]:
    x = np.linspace(0.0, length, n)
    return x, np.full(n - 1, ei)


def test_beam_central_point_load_matches_analytic() -> None:
    """Simply supported beam, central point load: δ = PL³/(48 EI)."""
    ei, length, p = 6.44e10, 1000.0, 1000.0
    x, stiff = _uniform_beam(ei, length)
    beam = BeamModel(x, stiff)
    beam.add_support(0.0, 1e12)
    beam.add_support(length, 1e12)
    beam.add_point_load(length / 2, p)
    delta = beam.deflection_at(np.array([length / 2]))[0]
    assert delta == pytest.approx(p * length**3 / (48 * ei), rel=1e-4)


def test_beam_uniform_load_matches_analytic() -> None:
    """Simply supported beam, full uniform load: δ = 5wL⁴/(384 EI)."""
    ei, length, total = 6.44e10, 1000.0, 1000.0
    x, stiff = _uniform_beam(ei, length)
    beam = BeamModel(x, stiff)
    beam.add_support(0.0, 1e12)
    beam.add_support(length, 1e12)
    beam.add_distributed_load(0.0, length, total)
    delta = beam.deflection_at(np.array([length / 2]))[0]
    w = total / length
    assert delta == pytest.approx(5 * w * length**4 / (384 * ei), rel=1e-4)


def test_beam_shear_softens_deflection() -> None:
    """A Timoshenko (shear) beam deflects more than the Euler beam (stubby section)."""
    ei, length, p = 6.44e10, 200.0, 1000.0
    x, stiff = _uniform_beam(ei, length)
    ga = np.full(x.size - 1, 2.0e7)  # finite shear rigidity
    euler = BeamModel(x, stiff)
    timo = BeamModel(x, stiff, ga)
    for beam in (euler, timo):
        beam.add_support(0.0, 1e12)
        beam.add_support(length, 1e12)
        beam.add_point_load(length / 2, p)
    d_euler = euler.deflection_at(np.array([length / 2]))[0]
    d_timo = timo.deflection_at(np.array([length / 2]))[0]
    assert d_timo > d_euler


@pytest.mark.skipif(not _EX001.exists(), reason="RIKOR example 001 not present")
def test_mesh_gap_reproduces_rikor_001_gesamtkorrektur() -> None:
    """The face gap reproduces RIKOR 001's Gesamtkorrektur (shape + magnitude ~ ±15%)."""
    gap = mesh_gap(RikorInput.load(_EX001))
    correction = gap.correction_um
    # peak correction (RIKOR 41.82 µm at the unloaded end)
    assert correction.max() == pytest.approx(41.82, rel=0.15)
    # the vertex (point of max approach, ~zero correction) lies in the loaded face,
    # shifted off-centre by the torsion (RIKOR 77.76 mm of the 127 mm width)
    vertex = gap.face_mm[int(np.argmax(gap.gap_um))]
    assert 65.0 < vertex < 92.0
    # shape: large correction at the ends, ~zero near the vertex
    assert correction[0] > 30.0
    assert correction.min() < 2.0
    # equivalent linear misalignment f_βx is a positive, physical magnitude
    assert 10.0 < gap.equivalent_misalignment_um < 60.0


@pytest.mark.skipif(not _EX001.exists(), reason="RIKOR example 001 not present")
def test_mesh_gap_components_present() -> None:
    """Both bending+shear and torsion contribute to the gap."""
    gap = mesh_gap(RikorInput.load(_EX001))
    assert np.ptp(gap.bending_um) > 5.0
    assert np.ptp(gap.torsion_um) > 5.0
