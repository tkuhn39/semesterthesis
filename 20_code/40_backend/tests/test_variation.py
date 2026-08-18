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


@pytest.mark.skipif(not _REF_STE.exists(), reason="kst-E reference .ste not present")
def test_kernel_single_contact_factors_match_scalar() -> None:
    """Y_F/Y_S at d_en (ISO Method B, steel branch of the per-kind dispatch) reproduce
    the scalar tooth-root model (kst-E) when ε_α is passed."""
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
        transverse_contact_ratio=np.array(
            [stage.transverse_contact_ratio, stage.transverse_contact_ratio]
        ),
    )
    assert ff.form_factor_single is not None and ff.stress_correction_single is not None
    for i in range(2):
        assert ff.form_factor_single[i] == pytest.approx(roots_scalar[i].form_factor, abs=1e-4)
        assert ff.stress_correction_single[i] == pytest.approx(
            roots_scalar[i].stress_correction_factor, abs=1e-4
        )


def test_per_gear_norm_dispatch_branches() -> None:
    """The sweep NEVER mixes the norm branches (user requirement 2026-08-18): the
    steel slot's σ_F uses the ISO Method-B form (Y_F·Y_S, no Y_ε), the plastic slot's
    the VDI tip-load form (Y_Fa·Y_Sa·Y_ε) — swapping the kinds swaps the numbers."""
    fixed = {"m_n": 2.0, "z1": 24.0, "z2": 60.0, "x1": 0.1, "x2": 0.0, "b": 20.0}
    mixed = VariationSpec(materials=(_STEEL, _PLASTIC), torque_nm=10.0, fixed=dict(fixed))
    swapped = VariationSpec(materials=(_PLASTIC, _STEEL), torque_nm=10.0, fixed=dict(fixed))
    res_m = evaluate(mixed, build_grid(mixed))
    res_s = evaluate(swapped, build_grid(swapped))
    # same geometry, same widths → gear 1's stress form follows ITS kind: the steel
    # form (Y_F·Y_S at d_en, no Y_ε) differs from the plastic form (Y_Fa·Y_Sa·Y_ε)
    assert float(res_m.root_stress_mpa[0]) != pytest.approx(
        float(res_s.root_stress_mpa[0]), rel=1e-3
    )
    # dispatch consistency across orientations: gear 1 steel ≡ gear... the same slot
    # evaluated as steel must give the same σ_F form regardless of the mate's kind
    both_steel = VariationSpec(materials=(_STEEL, _STEEL), torque_nm=10.0, fixed=dict(fixed))
    res_ss = evaluate(both_steel, build_grid(both_steel))
    assert float(res_ss.root_stress_mpa[0]) == pytest.approx(
        float(res_m.root_stress_mpa[0]), rel=1e-12
    )
    # spur case: both Z_β conventions are 1 → per-gear flank stresses coincide
    assert float(res_m.flank_stress_mpa[0]) == pytest.approx(
        float(res_m.flank_stress_mpa[1]), rel=1e-12
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
    # only the permanent pre-design honesty note — no data warnings for this spec
    assert all("pre-design" in w for w in res.warnings)
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


def test_per_gear_rows_match_scalar_path_when_equal() -> None:
    """Regression: per-gear batch entries equal to the spec scalars reproduce the old
    scalar path bit-identically (b2=b, h_ap=addendum, h_fp/rho_fp=tool factors)."""
    fixed_old = {"m_n": 2.0, "z1": 24.0, "z2": 60.0, "x1": 0.1, "x2": 0.0, "b": 20.0}
    spec_old = VariationSpec(
        materials=(_STEEL, _PLASTIC),
        torque_nm=10.0,
        varied={"z1": Varied(values=(20.0, 24.0, 28.0))},
        fixed={k: v for k, v in fixed_old.items() if k != "z1"},
    )
    res_old = evaluate(spec_old, build_grid(spec_old))
    spec_new = VariationSpec(
        materials=(_STEEL, _PLASTIC),
        torque_nm=10.0,
        varied={"z1": Varied(values=(20.0, 24.0, 28.0))},
        fixed={
            **{k: v for k, v in fixed_old.items() if k != "z1"},
            "b2": 20.0,
            "h_ap1": 1.0,
            "h_ap2": 1.0,
            "h_fp1": 1.25,
            "h_fp2": 1.25,
            "rho_fp1": 0.38,
            "rho_fp2": 0.38,
        },
    )
    res_new = evaluate(spec_new, build_grid(spec_new))
    for old, new in (
        (res_old.root_stress_mpa[0], res_new.root_stress_mpa[0]),
        (res_old.root_stress_mpa[1], res_new.root_stress_mpa[1]),
        (res_old.flank_stress_mpa, res_new.flank_stress_mpa),
        (res_old.total_contact_ratio, res_new.total_contact_ratio),
    ):
        assert np.array_equal(old, new)


def test_h_fp_variation_affects_only_its_gear() -> None:
    """Varying the gear-1 tool dedendum changes only gear 1's root stress."""
    spec = VariationSpec(
        materials=(_STEEL, _PLASTIC),
        torque_nm=10.0,
        varied={"h_fp1": Varied(values=(1.1, 1.25, 1.4))},
        fixed={"m_n": 2.0, "z1": 24.0, "z2": 60.0, "x1": 0.1, "x2": 0.0, "b": 20.0},
    )
    res = evaluate(spec, build_grid(spec))
    assert np.unique(np.round(res.root_stress_mpa[0], 9)).size == 3  # gear 1 responds
    assert np.unique(np.round(res.root_stress_mpa[1], 9)).size == 1  # gear 2 constant


def test_b2_drives_wheel_root_and_common_flank_width() -> None:
    """b2 loads gear 2's root with its own width; the flank uses min(b, b2)."""
    spec = VariationSpec(
        materials=(_STEEL, _PLASTIC),
        torque_nm=10.0,
        varied={"b2": Varied(values=(10.0, 20.0, 30.0))},
        fixed={"m_n": 2.0, "z1": 24.0, "z2": 60.0, "x1": 0.1, "x2": 0.0, "b": 20.0},
    )
    res = evaluate(spec, build_grid(spec))
    sigma2 = res.root_stress_mpa[1]
    assert sigma2[0] > sigma2[1] > sigma2[2]  # wider wheel → lower root stress
    sigma1 = res.root_stress_mpa[0]
    assert sigma1[0] == sigma1[1] == sigma1[2]  # gear 1 root keeps its own b
    # flank: min(b, b2) → 10/20/20 → first variant is more stressed, last two equal
    # (σ_H is per gear since the per-kind norm dispatch — check the wheel's)
    sh = res.flank_stress_mpa[1]
    assert sh[0] > sh[1]
    assert np.isclose(sh[1], sh[2])
