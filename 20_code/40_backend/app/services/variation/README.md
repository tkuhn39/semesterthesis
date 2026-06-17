# `app.services.variation` — plastic-capable Stufenvariation

The macro-geometry parameter sweep that runs *before* the FE rolling model: scan
gear-pair macro geometry (module, teeth, profile shifts, helix, width) and read off
the contact ratios and safety factors, then optimize. It replaces the FVA-Workbench
Stufenvariation, which **cannot run with a plastic gear** (DIN-3990-only) and is slow
at high variable counts. Standards & strategy: **ADR-013**.

## Modules

- **`kernel.py`** — the vectorized core. Evaluates a whole **batch** of variants as
  numpy arrays: the macro-geometry (`mesh_geometry`: α_wt via vectorized Newton on
  the involute, ε_α/ε_β/ε_γ), the tooth-root **tip-load** form factors Y_Fa/Y_Sa
  (`tip_form_factors`, the 30°-tangent angle ϑ iterated in lockstep), the capacity
  (`flank_stress`/`root_stress`, `elasticity_factor`/`zone_factor`/`flank_contact_ratio_factor`)
  and the early-pruning `validity_mask`. Reproduces the scalar
  `geometry`/`capacity` models bit-for-bit (validated against kst-E).
- **`sweep.py`** — the orchestration. `build_grid` (cartesian product) and
  `build_sample` (Sobol / Latin-Hypercube via `scipy.stats.qmc`) build the batch;
  `evaluate` runs it through the kernel with **per-gear material dispatch** (each
  gear's permissible stress from its own material — steel ISO 6336 limits, plastic
  VDI 2736 limits) over the shared mesh; `pareto_front` selects the non-dominated
  macro-geometries over several objectives (max S_F, max S_H, target ε_γ, …).

## Performance (the point)

A **5-DOF grid of 98 000 variants evaluates in ~165 ms (~6·10⁵ variants/s)** on one
core — the whole geometry + capacity chain vectorized, no per-variant Python loop.
Layered strategy (ADR-013): ① vectorized batch, ② early validity pruning (drop
undercut / ε_γ<1 / pointed-tip before the costly capacity), ③ Sobol/LHS sampling for
high-dimensional spaces where the full grid explodes, ④ Pareto optimization.

## Graceful degradation

A missing **non-essential** input (e.g. a gear without σ_Flim) yields a *warning* and
skips only that sub-result (its S_F is `NaN`); the sweep keeps running, never locking —
unlike the Workbench. The material pairings steel–steel, plastic–plastic and
steel–plastic all run through the same batched pass (the dispatch is a per-gear
material lookup over the shared mesh).

```python
from app.services.variation import VariationSpec, Varied, build_grid, evaluate, pareto_front

spec = VariationSpec(materials=(steel, plastic), torque_nm=15.0,
    varied={"z1": Varied(values=(18, 24, 30)), "x1": Varied(bounds=(-0.3, 0.6))},
    fixed={"m_n": 2.0, "z2": 60, "x2": 0.0, "b": 20.0})
res = evaluate(spec, build_grid(spec))
best = pareto_front([res.root_safety[1], res.total_contact_ratio], maximize=[True, True])
```
