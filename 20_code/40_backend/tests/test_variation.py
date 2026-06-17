"""
@module: tests.test_variation
@context: Domain-layer tests — the plastic-capable Stufenvariation (ADR-013).
@role: The vectorized kernel reproduces the scalar geometry/tooth-root models
       bit-for-bit (kst-E); the sweep layer builds grids/samples, prunes invalid
       variants, dispatches per-gear materials gracefully and selects a Pareto front.
"""

from pathlib import Path

import numpy as np
import pytest

from app.io.ste import gear_stage_from_ste, load_ste
from app.services.geometry.gear import GearStage
from app.services.geometry.tooth_root import ToothRootGeometry
from app.services.materials import Material, MaterialKind
from app.services.variation import (
    VariationSpec,
    Varied,
    build_grid,
    build_sample,
    evaluate,
    kernel,
    pareto_front,
)

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)

_STEEL = Material(
    name="16MnCr5",
    kind=MaterialKind.STEEL,
    elastic_modulus_mpa=206000.0,
    poisson_ratio=0.30,
    sigma_flim_mpa=430.0,
    sigma_hlim_mpa=1500.0,
)
_PLASTIC = Material(
    name="POM",
    kind=MaterialKind.PLASTIC,
    elastic_modulus_mpa=2800.0,
    poisson_ratio=0.35,
    sigma_flim_mpa=35.0,
    sigma_hlim_mpa=60.0,
)


def test_inverse_involute_vectorized() -> None:
    """The vectorized inverse involute inverts inv α = tan α − α over a batch."""
    alpha = np.radians(np.array([15.0, 20.0, 25.0, 30.0]))
    recovered = kernel.inverse_involute(kernel.involute(alpha))
    assert np.allclose(recovered, alpha, atol=1e-9)


@pytest.mark.skipif(not _REF_STE.exists(), reason="kst-E reference .ste not present")
def test_kernel_form_factors_match_scalar() -> None:
    """The vectorized tip-load form factors reproduce the scalar tooth-root model (kst-E)."""
    stage = GearStage.from_ste(gear_stage_from_ste(load_ste(_REF_STE)))
    roots_scalar = [ToothRootGeometry.from_stage(stage, i) for i in range(2)]
    gen = stage.generation
    assert gen is not None
    ff = kernel.tip_form_factors(
        normal_module_mm=np.array([stage.normal_module_mm, stage.normal_module_mm]),
        teeth=np.array([float(stage.teeth[0]), float(stage.teeth[1])]),
        normal_pressure_angle=np.radians(np.array([20.0, 20.0])),
        helix_angle=np.array([0.0, 0.0]),
        generation_profile_shift=np.array(
            [gen[0].generation_profile_shift, gen[1].generation_profile_shift]
        ),
        tool_addendum_factor=np.array([gen[0].tool.addendum_factor, gen[1].tool.addendum_factor]),
        tool_tip_radius_factor=np.array(
            [gen[0].tool.tip_radius_factor, gen[1].tool.tip_radius_factor]
        ),
        tip_diameter_mm=np.array([gen[0].tip_form_diameter_mm, gen[1].tip_form_diameter_mm]),
    )
    for i in range(2):
        assert ff.form_factor_tip[i] == pytest.approx(roots_scalar[i].form_factor_tip, abs=1e-4)
        assert ff.stress_correction_tip[i] == pytest.approx(
            roots_scalar[i].stress_correction_factor_tip, abs=1e-4
        )
        assert ff.critical_root_chord_mn[i] == pytest.approx(
            roots_scalar[i].critical_root_chord_mn, abs=1e-4
        )


def test_grid_sweep_shapes_and_monotonicity() -> None:
    """A grid is the cartesian product; more teeth lower the root stress (more contact)."""
    spec = VariationSpec(
        materials=(_STEEL, _PLASTIC),
        torque_nm=10.0,
        varied={"z1": Varied(values=(18.0, 24.0, 30.0)), "x1": Varied(values=(0.0, 0.3))},
        fixed={"m_n": 2.0, "z2": 60.0, "x2": 0.0, "b": 20.0},
    )
    grid = build_grid(spec)
    assert grid["z1"].size == 6  # 3 × 2
    res = evaluate(spec, grid)
    assert res.total_contact_ratio.shape == (6,)
    assert np.all(res.warnings == ()) or res.warnings == ()
    # at fixed x1, raising z1 lowers σ_F of the pinion (longer lever shrinks, more teeth)
    z1 = res.parameters["z1"]
    x1 = res.parameters["x1"]
    sub = x1 == 0.0
    order = np.argsort(z1[sub])
    sigma = res.root_stress_mpa[0][sub][order]
    assert np.all(np.diff(sigma) < 0.0)


def test_pruning_drops_invalid_variants() -> None:
    """A too-small/pointed variant (ε_γ < 1 or degenerate root) is masked out."""
    spec = VariationSpec(
        materials=(_STEEL, _PLASTIC),
        torque_nm=10.0,
        varied={"z1": Varied(values=(6.0, 25.0))},  # z1=6 → undercut / low ε
        fixed={"m_n": 2.0, "z2": 60.0, "x1": 0.0, "x2": 0.0, "b": 20.0},
    )
    res = evaluate(spec, build_grid(spec))
    assert not bool(res.valid[0])  # z1 = 6 pruned
    assert bool(res.valid[1])  # z1 = 25 kept


def test_material_dispatch_graceful_on_missing_limit() -> None:
    """A plastic gear without σ_Flim warns and skips only its root safety (ADR-013)."""
    plastic_no_root = Material(
        name="x",
        kind=MaterialKind.PLASTIC,
        elastic_modulus_mpa=2800.0,
        poisson_ratio=0.35,
        sigma_hlim_mpa=60.0,
    )
    spec = VariationSpec(
        materials=(_STEEL, plastic_no_root),
        torque_nm=10.0,
        varied={"z1": Varied(values=(20.0, 25.0))},
        fixed={"m_n": 2.0, "z2": 60.0, "x1": 0.0, "x2": 0.0, "b": 20.0},
    )
    res = evaluate(spec, build_grid(spec))
    assert any("sigma_Flim" in w for w in res.warnings)
    assert np.all(np.isnan(res.root_safety[1]))  # plastic root skipped
    assert np.all(np.isfinite(res.flank_safety[1]))  # flank still evaluated


def test_pareto_front_selects_nondominated() -> None:
    """Pareto: a variant dominated on both objectives is excluded."""
    s_f = np.array([1.0, 2.0, 1.5])
    eps = np.array([2.0, 1.0, 1.4])
    front = pareto_front([s_f, eps], maximize=[True, True])
    assert front.tolist() == [True, True, True]  # the trade-off corners are all optimal
    dominated = pareto_front([np.array([1.0, 3.0]), np.array([1.0, 3.0])], maximize=[True, True])
    assert dominated.tolist() == [False, True]


def test_sobol_and_lhs_samples_within_bounds() -> None:
    """Sobol and Latin-Hypercube samples respect the parameter bounds."""
    spec = VariationSpec(
        materials=(_STEEL, _PLASTIC),
        torque_nm=10.0,
        varied={"x1": Varied(bounds=(-0.5, 0.7)), "x2": Varied(bounds=(-0.3, 0.5))},
        fixed={"m_n": 2.0, "z1": 24.0, "z2": 60.0, "b": 20.0},
    )
    for method in ("sobol", "lhs"):
        sample = build_sample(spec, 16, method=method, seed=1)
        assert sample["x1"].shape == (16,)
        assert np.all((sample["x1"] >= -0.5) & (sample["x1"] <= 0.7))
        assert np.all((sample["x2"] >= -0.3) & (sample["x2"] <= 0.5))
        res = evaluate(spec, sample)
        assert res.total_contact_ratio.shape == (16,)
