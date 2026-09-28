# Implementation roadmap (restart 2026-09-28)

Legacy roadmap: `30_references_and_examples/38_legacy_workbench/00_development_documentation/implementation_roadmap.md`.

## Stage 1 — verified 2D geometry chain (plan `ber-die-vergangenen-monate-whimsical-charm.md`)

| # | Increment | Status | Gate |
|---|---|---|---|
| 0 | Move + foundation: archive legacy, package skeleton, contracts, `@eq`, sources registry, `.ste`/`.sta`/contour/interface parsers, STplus oracle, 15 fixture cases (kst-A/B/C/E supplied + re-runs, FZG-C, six adversarial variants), notebook template/index, scripts (traceability, source verification, schema export) | done 2026-09-28 — 165+ tests incl. property-based and gate regressions (`tests/test_adv_0.py`), mypy strict (src + scripts), ruff clean | **passed 2026-09-28**: 0 P0, 7 P1 (ADV0-01…07) all fixed, 18 P2 (14 fixed, ADV0-23b deferred → known_limits), 12 P3 (most fixed; ADV0-29/35/36/37 accepted/deferred → known_limits) |
| 1 | Involute + basic rack (DIN ISO 21771 §4, DIN 867, ISO 53, DIN 3972) — NB 01 | open | – |
| 2 | Pair geometry (DIN ISO 21771 §5 + Annex NB) — NB 02 | open | – |
| 3 | Tool-based generation + trochoid + transverse contour, spur and helical (DIN ISO 21771 §7, DIN 3960 §3.6/Annex A, Linke 2010, FVA 604 I) — NB 03 | open | – |
| 4 | Inspection dimensions (DIN 21773) — NB 04 | open | – |
| 5 | Allowances and tolerances (DIN 3967, DIN 3964, DIN ISO 1328-1/-2) — NB 05 | open | – |
| 6 | Synthesis: norm map, norm differences, traceability, schema export — NB 06 | open | – |

## Later stages (to be planned after the stage-1 gate)
2. Load capacity (ISO 6336-1/-2/-3/-5/-6:2019, ISO/TS 6336-20/-21/-22; DIN 3990 as cross-check; VDI 2736)
   + material database (steel per ISO 6336-5; plastics per VDI 2736 tables + CAMPUS datasheets), dispatch on
   `MaterialKind`.
3. Alternative root fillets (elliptic: Frühe, Kassem, Landi, Sanders; Bézier: Roth/Opferkuch, Dong; bionic:
   patents DE 10 2008 045 318 B3 / DE 10 2013 004 861 B3, Kassem CAO) with the verified source registry.
4. Parameter studies, separately for steel and plastic pairs.
5. 3D model + Abaqus `.inp` rolling simulation deck (reference contract from the legacy work).
6. Python post-processing; API, UI, Docker.
