# `10_verifiers`

Python scripts used purely for verification and testing — analytical
cross-checks (DIN 3990 / VDI 2736), comparison against FE results, and unit
tests collected by `pytest`.

Naming: `test_*.py` for pytest cases, `*_verifier.py` for standalone checks
(both are discovered by the pytest config in `../pyproject.toml`).

## Scripts

- `make_reference_template.py` — regenerates the committed ADR-019 sector template from the
  reference deck and prints the pinned topology metrics.
- `compare_generated_vs_reference.py` — generates the kst-E wheel sector and overlays it on
  the parsed reference (plots to `40_backend/80_output/`).
- `checkpoint2_plots.py` — review plots: tooth congruence/symmetry, density levels,
  convergence curves, fillet strategies.

Run from `20_code/` with the `semesterthesis_3-12` env.
