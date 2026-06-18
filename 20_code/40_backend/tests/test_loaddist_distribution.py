"""
@module: tests.test_loaddist_distribution
@context: Domain-layer tests — RIKOR (FVA 30) LTCA load distribution (R3 scaffolding).
@role: The contact solver behaves (uniform compliance → uniform load; contact loss);
       the assembled δ^W LTCA reproduces the mean line load exactly and a physical,
       end-loaded distribution for standard test 001. The absolute K_Hβ still
       over-predicts until the gear-body cross-influence δ^Z (Weber-Banaschek / FVA
       T309) is added — that gap is asserted as a documented bound, not exactness.
"""

from pathlib import Path

import numpy as np
import pytest

from app.io.rie import RikorInput
from app.services.loaddist.distribution import evaluate_load_distribution, solve_contact

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


def test_solve_contact_uniform_compliance_gives_uniform_load() -> None:
    """A uniform diagonal compliance with no misalignment → equal support forces."""
    n = 8
    delta = np.eye(n) * 1e-4
    forces = solve_contact(delta, np.zeros(n), total_force_n=800.0)
    assert forces == pytest.approx(np.full(n, 100.0))


def test_solve_contact_releases_lifted_supports() -> None:
    """A strong one-sided misalignment lifts the far supports (non-negative forces, Σ=F)."""
    n = 6
    delta = np.eye(n) * 1e-4
    misalignment = np.linspace(0.0, 0.05, n)  # mm, rising to one side
    forces = solve_contact(delta, misalignment, total_force_n=500.0)
    assert np.all(forces >= -1e-9)
    assert forces.sum() == pytest.approx(500.0)
    assert forces[0] > forces[-1]  # the low-gap side carries more
    assert forces[-1] == pytest.approx(0.0, abs=1e-6)  # the lifted side drops out


@pytest.mark.skipif(not _EX001.exists(), reason="RIKOR example 001 not present")
def test_load_distribution_mean_and_shape_001() -> None:
    """LTCA on test 001: exact mean line load, end-loaded w(b), K_Hβ in the bound."""
    result = evaluate_load_distribution(RikorInput.load(_EX001), points=40)
    assert result.mean_line_load_n_per_mm == pytest.approx(1319.34, rel=1e-4)
    w = np.array(result.line_load_n_per_mm)
    # physical shape: most load near the (drive-side) end, least in the span
    assert w[0] > w[len(w) // 2]
    assert result.face_load_factor_flank > 1.0
    # without δ^Z the factor over-predicts the RIKOR 1.36; keep a documented upper bound
    assert 1.3 < result.face_load_factor_flank < 1.7
