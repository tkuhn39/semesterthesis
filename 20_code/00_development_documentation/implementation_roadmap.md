# Implementation roadmap (restart 2026-09-28)

Legacy roadmap: `30_references_and_examples/38_legacy_workbench/00_development_documentation/implementation_roadmap.md`.

## Stage 1 — verified 2D geometry chain (plan `ber-die-vergangenen-monate-whimsical-charm.md`)

| # | Increment | Status | Gate |
|---|---|---|---|
| 0 | Move + foundation: archive legacy, package skeleton, contracts, `@eq`, sources registry, `.ste`/`.sta`/contour/interface parsers, STplus oracle, 15 fixture cases (kst-A/B/C/E supplied + re-runs, FZG-C, six adversarial variants), notebook template/index, scripts (traceability, source verification, schema export) | done 2026-09-28 — 165+ tests incl. property-based and gate regressions (`tests/test_adv_0.py`), mypy strict (src + scripts), ruff clean | **passed 2026-09-28**: 0 P0, 7 P1 (ADV0-01…07) all fixed, 18 P2 (14 fixed, ADV0-23b deferred → known_limits), 12 P3 (most fixed; ADV0-29/35/36/37 accepted/deferred → known_limits) |
| 1 | Involute + basic rack (DIN ISO 21771 §4, DIN 867, ISO 53, DIN 3972) — NB 01. Note: DIN 3972 presets take the tool tip rounding from the norm's table (r₁ = r₂, tabulated per module), not from 0,2·m; modules outside the table get no preset. Delivered: `involute.py` (26 traced functions, one inverse involute), `rack.py` (DIN 867 / ISO 53 A–D basic racks, DIN 3972 I–IV tools, ISO 54 module check), `parity.py` (value-by-value comparison with STplus, ADR-106), contracts `BasicGearGeometry`, `BasicRackProfile`, `ParityRow`, worked example ISO/TR 6336-30:2022 Annex A example 1 (confirmed by the user), quantity registry `data/quantities.yaml` with the table of differences (ADR-108), STplus heritage `data/stplus_program/` (tool databases, defaults, probes; ADR-109), inventory of tabulated values and defaults (`norm_map.md`), NB 01. The transformation of the tool profile into the transverse section moved to increment 3 (it belongs to the generation) | done 2026-09-30 — 675 tests incl. property-based and gate regressions (`tests/test_adv_1.py`, `tests/test_quantities.py`, `tests/test_stplus_program.py`), mypy strict (src + scripts), ruff clean, NB 01 executed | **passed 2026-09-29**: 0 P0, 15 P1 (ADV1-01…15) all resolved, 21 P2 (all resolved), 9 P3 (ADV1-38/41/42/45 resolved, ADV1-43/44 resolved in part with ADV1-43b/44b open, ADV1-37/39/40 accepted with documentation → known_limits). ADV1-01 resolved differently from the reviewer's proposal (signed value with warning instead of an error, because feasible gears are affected). Registry review after the feedback round: REG1-01…10 resolved, REG1-03b/11/12 and STP-01/02 in known_limits. Report: `gate_reports/increment_1.md` |
| 2 | Pair geometry (DIN ISO 21771 §5 + Annex NB) — NB 02. A given centre distance is fixed and the profile shift follows it (ADR-107); the hand of helix of the worked example enters here (ADV1-44b). Also: enter the three norms the user supplies (DIN 3992, DIN 58412, the norm of the measuring ball diameters) into `sources.yaml` by the protocol (title page read on the rendered page, user confirmation) and extend the table of tabulated values | open | – |
| 3 | Tool-based generation + trochoid + transverse contour, spur and helical (DIN ISO 21771 §7, DIN 3960 §3.6/Annex A, Linke 2010, FVA 604 I) — NB 03 | open | – |
| 4 | Inspection dimensions (DIN 21773) — NB 04 | open | – |
| 5 | Allowances and tolerances (DIN 3967, DIN 3964, DIN ISO 1328-1/-2) — NB 05 | open | – |
| 6 | Synthesis: norm map, norm differences, quantity registry (names, symbols, designations, STplus and older symbols; extended by every increment in `data/quantities.yaml`, ADR-108), traceability, schema export — NB 06 | open | – |

Every increment enters the quantities it introduces into `data/quantities.yaml` before it uses them, reads symbol and designation on the rendered norm page, and regenerates `quantities.md`.
Every increment also inventories the tabulated values and defaults of its scope (what STplus presets, what the current norm tabulates, whether the values differ) and extends the table 'Tabellenwerte und Vorbelegungen' in `norm_map.md`; gearcore has no silent defaults.

## Later stages (to be planned after the stage-1 gate)
2. Load capacity (ISO 6336-1/-2/-3/-5/-6:2019, ISO/TS 6336-20/-21/-22; DIN 3990 as cross-check; VDI 2736)
   + material database (steel per ISO 6336-5; plastics per VDI 2736 tables + CAMPUS datasheets), dispatch on
   `MaterialKind`. STplus heritage of this stage (ADR-109): material and lubricant databases
   (`wst.dat`, `oel.dat`) and the defaults of the load capacity input, kept with program version.
3. Alternative root fillets (elliptic: Frühe, Kassem, Landi, Sanders; Bézier: Roth/Opferkuch, Dong; bionic:
   patents DE 10 2008 045 318 B3 / DE 10 2013 004 861 B3, Kassem CAO) with the verified source registry.
4. Parameter studies, separately for steel and plastic pairs.
5. 3D model + Abaqus `.inp` rolling simulation deck (reference contract from the legacy work).
6. Python post-processing; API, UI, Docker.
