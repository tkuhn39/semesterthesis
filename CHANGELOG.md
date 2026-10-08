# Changelog

All notable changes to this project's code (under [`20_code/`](20_code/)) are
documented in this file. Entries before 2026-09-28 refer to the legacy workbench,
now archived read-only under `30_references_and_examples/38_legacy_workbench/`
(git tag `legacy-workbench-final`).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Dates are ISO 8601 (YYYY-MM-DD).

## [Unreleased]

### Changed (restart of the workbench, 2026-09-28, ADR-101)
User decision: the legacy FastAPI/Next.js workbench (22k LOC backend, 65 open
adversarial findings) is retired; the toolchain is rebuilt from the ground up in
small, adversarially gated increments.
- **Legacy code archived**: `20_code/` moved to
  `30_references_and_examples/38_legacy_workbench/` (git-ignored, read-only, never
  imported); history preserved under tag `legacy-workbench-final` (= 4af1d2b).
- **New code tree** `20_code/`: `10_gearcore/` — pydantic domain package `gearcore`
  (src layout, one norm equation = one traced function), `00_development_documentation/`
  (new ADR series 101+, norm map, adversarial-gate protocol, extension points).
- **Notebooks** in `40_jupyter-notebooks/` are executable norm documentation that
  import `gearcore` and run in CI (nbmake); they never implement formulas.
- CI rebuilt for the new package; Docker job removed until the API/UI stage.

### Added (increment 0 - foundation of the geometry chain, 2026-09-28, ADR-102...105)
- `gearcore` package skeleton: typed errors, domain-checked math (`_safe`), `@eq` traceability
  registry + verified `sources.yaml` (ADR-103), frozen pydantic contracts (`ToolProfile`,
  `GearInput`, `PairInput`, `MaterialRecord` with steel/plastic layers), STplus parsers
  (`.ste` incl. multi-pair lines and interface-file keys, `.sta` report grammar with explicit
  symbol registry, contour export).
- STplus oracle (`scripts/stplus_oracle.py`, ADR-102): batch runs of the local 11.1F
  installation with contour export and interface file, import of supplied listings with trust
  levels. 15 packaged fixture cases (kst-A/B/C/E supplied + 11.1F re-runs, FZG-C, six adversarial
  variants incl. undercut, helix 20/30 deg, m_n 0.5, x = -0.8).
- Test harness: hypothesis profiles, fixture-parametrised parser tests, traceability guards
  (unknown source keys, missing `@eq`, ISBN checksums). mypy --strict clean.
- Notebook template and index (`40_jupyter-notebooks/`), executed in CI via nbmake; scripts for
  the traceability table, source verification (Crossref/ISBN) and JSON schema export.
- **Adversarial gate 0 passed** (read-only reviewer, 37 findings, 0 P0): tool pressure angle /
  module now inherit the gear values (`None`), `AUFTEILUNG_X1X2 != 0` and `PR.VERSCH.SUMME` raise
  `NotSupportedError`, STplus number grammar enforced (no silent `int()` truncation, malformed
  tokens are `ParseError`), per-gear single-value semantics per manual §3.2, `MESSZAEHNEZAHL_K` no
  longer stands in for the span tooth count, DIN/ISO quality systems kept apart (`QualitySystem`),
  duplicate keys/blocks rejected, `.sta` series letters vs single-letter symbols disambiguated,
  `p_x` and two-token units (`Grad C`) parsed, bare `Pair` rejects NaN, fixture hashes and case
  counts tested, pre-commit no longer rewrites fixtures, property-based tests for contracts and
  the `.ste` parser, oracle never adopts foreign contour files from `bin/`.
- **Source registry hardened** (user decision 2026-09-28): Roth/Opferkuch 2017 now carries its DOI
  (10.51202/9783181022948-719, Crossref-checked), Frühe 2012 its URN (nbn-resolving redirect
  checked); `test_trace.py` fails when code cites a source that is not `confirmed_by_user: true`;
  URNs accepted as thesis identifiers.
- **Registry audit 2026-09-29** (user check + machine comparison with the PDF title pages): titles of
  DIN ISO 1328-2 and VDI 2736 Blatt 3 corrected, author names corrected (Roth, Kassem, Dong et al.),
  patent designations and holders added, DIN 3972 note rewritten in the norm's own symbols
  (h_kw, r1, r2; rounding tabulated) with the mapping to current notation, VDI 2736 Blatt 1-4 now
  point to the final editions (Blatt 1: 2016-07, key `VDI2736-1:2016`); draft editions may not be
  cited from code. New rule 3a: current notation in the tool, original notation in quotations.

### Added (increment 1 - involute and basic rack, 2026-09-29, ADR-106)
- `gearcore.involute`: single-gear quantities of DIN ISO 21771:2014-08 §4.2, §4.3, §4.7 (reference and
  base diameter, transverse pressure angle, base helix angle, involute function, tooth thickness and
  space width in the transverse and normal section), one traced function per equation, spur and
  helical. Exactly one inverse involute (bracketed Newton with bisection fallback) that terminates
  at the rounding level of the residual and raises typed errors outside its domain.
- `gearcore.rack`: basic racks per DIN 867:1986-02 and ISO 53:1998 (types A-D) with the fillet radius
  bounds, tool reference profiles I-IV per DIN 3972:1952-02 (tabulated tip rounding, machining
  allowance), module check against ISO 54:1996 (soft finding, never an error).
- `gearcore.parity` and contract `ParityRow`: value-by-value comparison with the STplus fixtures that
  reports print, arithmetic and input tolerance separately and the verdict `identical`,
  `oracle_accuracy` or `different`. State: 15 cases, 443 comparisons, 431 identical, 12 within the
  accuracy of STplus, 0 different. Finding: with a centre distance given STplus derives x2 from it
  and overrides a given x2 (kst-E).
- **Double precision everywhere** (user decision 2026-09-29, ADR-106, project rule 8a): STplus
  computes in single precision (all 99 probed interface values are reproduced by a 32-bit
  evaluation of the same formulas, 93 by the 64-bit result); gearcore computes in binary64 and
  never rounds inside the chain. `test_numeric_precision.py` guards against reduced-precision
  types, rounding calls and format-and-parse in the package.
- Norm finding: 6 of 152 table values of DIN 3972:1952-02 deviate from the formulas printed in the
  same norm by more than half a unit of the last digit (largest: module 4.5, profile IV, printed
  6,60, formula 6,6156). The formulas are implemented, the six cells are pinned in the test.
- Worked example ISO/TR 6336-30:2022 Annex A example 1 as packaged fixture (geometry values of later
  increments pinned as pending), translation old notation -> current notation (since the
  feedback round part of the quantity registry, see below), notebook `01_involute_bezugsprofil`.
- Root `pytest.ini`: a bare `pytest` at the repository root collects only the package tests, never
  the archived legacy workbench.
- **Adversarial gate 1 passed** (read-only reviewer, 45 findings, 0 P0; no formula, table or
  equation citation of the involute chain was wrong): every result is finite or a typed error
  (huge integers, overflow, strings, `bool`), the orchestrator enforces the verified input ranges,
  tooth thickness and space width at the reference cylinder are signed values with a warning
  instead of silent negatives, one tolerance at the base circle for Eq. (12) and (17), tabulated
  modules are matched with a relative tolerance (0.07 * 100 is module 7), norm tables are
  immutable, the fillet bound has no slack except for the two value pairs the norms print, the
  bottom clearance outside 0.1 ... 0.4 is a soft finding (DIN 867 says "im allgemeinen"), parity
  compares the base helix angle with its sign and uses two binary32 steps as arithmetic
  tolerance, packaged data is addressed by name only, citation of ISO 54 corrected, symbols
  corrected (alpha_P0; rho_aP0 located in the equations of DIN ISO 21771, whose Bild 35 letters
  r_aP0), DIN 867 table deviation pinned,
  test tolerances tightened to a few ulp with references from 45-digit decimal arithmetic,
  notebooks must not contain formulas at cell level either.
- JSON schemas exported for `BasicGearGeometry`, `BasicRackProfile`, `ParityRow`.

### Changed (feedback round on increment 1, 2026-09-29, ADR-107)
- **Notation** (user rule: always the newest symbols, with a translation from STplus): survey of
  the tool tip rounding symbol over the current norms (rho_aP0 in DIN ISO 21771:2014-08 Eq. (128)
  of the normative Anhang NB and in ISO/TR 6336-30:2022; rho_a0 in ISO 6336-3:2019 and VDI 2736
  Blatt 2); every current symbol cites the newest geometry norm, the STplus listing symbols and
  tool keys used in increment 1 are translated (quantity registry, see below).
- **Centre distance** (user decision, ADR-107): a given centre distance is fixed, the profile
  shift follows it; implemented with increment 2. The worked example of ISO/TR 6336-30 gives the
  centre distance and x_2 = 0 and prints the resulting x_1 in parentheses.
- **Worked example fixture** (user review): ISO/TR 6336-30:2022 Annex A example 1 now holds all 19
  rows of Table A.1 and all 25 results of A.6 (p. 45 and 46) in the order of the norm, each with
  the label of the norm, its symbol, its unit and the printed text (five rows and the results of
  p. 46 were missing, labels were program names, symbols were absent). The basic rack dedendum and
  fillet radius hold for both gears (11,2 mm and 3,12 mm), x_1 is marked as derived from x_2 and
  the centre distance, formulas are written with abs() and atan(). `printed_number` parses the
  printed text; the tests require the stored number and the printed decimals to equal it.
- **Quantity registry** (user decision, ADR-108, project rule 3b): `data/quantities.yaml` is the
  single source of truth for program names, symbols and designations, with the STplus names and
  the symbols of the replaced norms per quantity (85 quantities, 9 pending). Contracts declare
  their fields with `Q(<quantity>)`; `symbol_map.yaml` is merged into the registry; the table
  `quantities.md` is generated.
- **Program names follow the norm designations**: `number_of_teeth`, `profile_shift_coefficient`,
  `normal_pressure_angle_deg`, `profile_angle_deg` (basic rack, tool), `centre_distance_mm`,
  `span_measurement_mm`, `number_of_teeth_spanned`, `bottom_clearance_factor`,
  `transverse_profile_angle_at`, `normal_profile_angle_at`. Symbol of the centre distance: a_w.
- **Typography**: subscripts are set upright in every formula of the notebooks;
  `gearcore.quantities.latex` renders the registry symbols. Names are ASCII (`_um` for µm):
  Python normalises the micro sign of an identifier to the Greek letter mu, a key typed with
  the micro sign would not match the field.
- **Registry review** (three read-only reviewers against the rendered pages and the STplus
  fixtures, findings REG1-01 to REG1-10 in `gate_reports/increment_1.md`): symbol, unit and
  location of the governing norms held in all 66 entries. Corrected: the older symbols of twelve
  quantities (DIN 3960 printed s_t, s_n, e_t, p_bt, alpha_yt ... as today, only its list §2.1
  omits the index), the English designation of the tool tip radius, the two STplus inputs of
  the machining allowance, missing STplus names, designations of DIN 867 and DIN 3972 that were
  not verbatim (r_1 instead of r1), the note on the sign of eta_b. The worked example was
  confirmed by the user.
- **Table of differences** (user request): `quantities.md` starts with the symbols and
  designations that differ from the current norm (older norms, STplus, other current
  documents), generated by `gearcore.quantities.symbol_differences` and
  `designation_differences`.
- **Inventory of tabulated values and defaults** (`norm_map.md`): what STplus presets, what the
  current norms tabulate, what gearcore holds so far and which increment adds the rest.

### Added (STplus heritage, 2026-09-30, ADR-109)
User decision: nothing STplus offered may get lost; tool databases and defaults are kept and
labelled with the program version.
- `data/stplus_program/`: tool databases of the installation (`wkz.dat` with 12 tools,
  `WKZ_GLOB.DAT` with 2), the register of input keys (`DEFAULT.STY`), `provenance.yaml` (STplus
  11.1F, Freigabe 01.12.2025, hashes), `defaults.yaml` (24 defaults with the sentence of the
  manual and the evidence of a probe run) and five probe runs.
- `gearcore.stplus_program`: `tool_database`, `stplus_tool`, `stplus_defaults`,
  `stplus_default_tool`, `input_key_register`, `probe_listing`; every record carries the label
  of program, version and release. Nothing is applied silently: six contradicting tool records
  and two without tip rounding are kept as written and rejected as contracts.
- Findings: the default pressure angle of 20° exists in the user interface only (a batch input
  without it is rejected); the default hob has h_aP0* = 1,25, rho_aP0* = 0,25, h_fP0* = 1,3;
  STplus computes a contradicting tool record with the factor and reduces tip rounding and
  dedendum silently.
- Project rule 5a; `scripts/import_stplus_program.py` reproduces import and probes.

### Added (increment 3 - tool-based generation and transverse tooth contour, 2026-09-30, ADR-113)
- `generation.py`: what a rack-type tool generates on an external gear (DIN ISO 21771:2014-08
  §7, §4.6, §4.7, §7.9): tooth thickness limits (118), (119), generating profile shift
  coefficient at the upper and the lower allowance (123), (124), pre-machining shift (120), (121),
  straight part of the tool addendum h_FaP0 (bracket of (128) NB; FVA 604 I (4.36), (4.37)),
  generated root diameter (125), root form diameter (128) in the corrected form of Anhang NB and
  (129)/(130) as printed as a cross-check, undercut limit (135), tip chamfer height (127), tooth
  depth, addendum, dedendum (35)-(37) with d_fE, tip tooth thickness (38)/(48) with x_E, and the
  tip form circle of an edge break flank of the tool with the residual tip thickness (DIN 3960
  Anhang A.3.1 Eq. (A.3.03), (A.3.05), (A.3.06), which the current norm lacks). Orchestrator
  `compute_generation`: both gears at x_Es, the pair geometry with the generated form circles,
  tip clearance (60) and form over-dimension (76) per gear; typed errors for protuberance tools,
  machining allowance, deviating tool module or angle; warnings for undercut, a missing allowance,
  an edge break flank that does not reach the tip, a chamfer without its shape, a topping tool.
- `trochoid.py`: the tool rolls on the gear by the law of gearing (Linke 2010 §1.3, FVA 604 I
  §3.1); the envelope of the tool tip rounding, an ellipse in the transverse section of a helical
  gear (FVA 604 I p. 29), is the fillet; the straight flank reproduces the involute and the tip
  line the root circle (tests); the root form circle of an undercut gear is the intersection of
  fillet and involute, found with `brentq`.
- `contour.py`: transverse tooth contour (fillet, involute, edge break involute or chamfer, tip
  circle), whole-gear polygon, `compare` (normal distance per region), STplus export loader.
  On the 14 own STplus runs (28 gears, four with undercut, beta up to 30 deg) the export lies
  within 0,6 um (fillet), 0,25 um (involute), 0,01 um (tip) of the gearcore contour (gate of the
  plan: 10 and 5 um).
- Contracts `GearGeneration`, `GenerationResult`, `ToothContour`, `ContourDiff`;
  `GearInput.residual_tip_thickness_mm` (a chamfer given by h_K and s_aK, DIN ISO 21771 §6.1.2).
- Comparison with STplus of the generation (`parity.compare_generation`): 537 comparisons over
  the 18 cases, 368 identical, 169 within the accuracy of STplus, none different. Findings: STplus
  prints the transverse allowance A_ste = E_sns / cos beta; its root form diameter is the numerical
  junction of its curves (doubled contour vertex), accuracy measured up to 6,4 um, allowed as
  `FORM_CIRCLE_ACCURACY_MM` = 0,007 mm; its residual thickness of a chamfer given by h_K follows
  the rule 0,7 h_K (labelled program rule `stplus_program.stplus_residual_tip_thickness`).
- Quantity registry: 13 quantities (h_FaP0, x_Es, x_Ei, x_Emin, d_fEi, c, c_F, h, h_a, h_f, s_at,
  s_an, s_aK) added, `tool_root_form_height`, `tool_edge_break_angle` (alpha_kP as Bild 36 a)
  letters it) and `tooth_thickness_allowance` verified; with the two entries of the gate (s_ns/s_ni,
  x_EsV/x_EiV) 108 quantities, 6 pending.
- `.ste` importer: a tool with `KANTENBRECHWINKEL` and without `FUSSFORMHOEHENFAKTOR` gets the
  STplus default h_FfP0* = 1,3 with a note (helix20_z25_65 lists it).
- Decimal reference generator `scripts/decimal_reference_generation.py` (45-digit arithmetic;
  the helical example 1 of ISO/TR 6336-30 gives d_Ff1 = 132,248 mm with Eq. (128) NB and
  132,243 mm with Eq. (130) as printed). Worked example: d_fE and d_Ff of example 1 reproduced
  from the printed x_E.
- Notebook `03_werkzeug_erzeugung_zahnkontur.ipynb` (23 cells, 26 after the fourth round): equations, fillet plots, contour
  overlays and deviation plots against STplus, whole gear, parity tables, limits.
- **Adversarial gate 3 passed** (two read-only reviewers, one round of fixes, verification review;
  `gate_reports/increment_3.md`, regression tests `tests/test_adv_3.py`): the numerical intersection
  of fillet and involute now covers the band just below the undercut limit (P0: the base circle is
  the root form circle where the cut is below resolution, `undercut_expected`), a pointed tooth at
  the tip circle is a typed error, tool feasibility (straight flank exists, roundings do not
  overlap) is checked on every path, a sharp tool corner (rho_aP0 = 0) rolls as the limit of the
  rounding, the dedendum is signed like Eq. (37) admits, the tool root rounding is a named extension
  point, one page number and the old-norm symbol x_Ee corrected, `contour.distances` public and
  junction points no longer doubled, `tooth_contour(generation, role)`, `tool_from_section` requires
  its notes list and raises a dedendum below the default root form height as STplus does, the
  fixture records refreshed (`refresh-import`), the STplus allowance for numerically found form
  circles reported as `ParityRow.solver_tolerance` and rows that echo inputs or cannot fail named
  (`rows_without_evidence`; 537 comparisons, 368 identical, 169 within the accuracy of STplus), the
  circle approximation of FVA 604 I measured reproducibly (`scripts/circle_approximation_fva604.py`:
  176 µm at β = 30°), two undetected mutations now detected, registry entries for s_ns/s_ni and
  x_EsV/x_EiV (108 quantities). The verification review (third read-only agent) confirmed the 29
  resolutions and named eight further items (G3V-01 to G3V-08), resolved in a second round: the
  fillet of the band below the undercut limit ends on the base circle itself and contour elements
  are joined with a tolerance relative to the size of the gear (`contour.JOIN_TOLERANCE`; no
  zero-length segment at any module), `fillet_curve`, `gear_polygon` and `tool_from_section` raise
  typed errors for the remaining wrong argument types, an equal dedendum is not reported as raised,
  the three mutations no test detected (resolution of a shallow cut, unit of `distances`, tolerance
  of the tangent end) are detected, known limit GEN-12 (root form circle on the base circle and the
  band of the pair module). A second verification review confirmed these eight and named eight
  more (G3W-01 to G3W-08), resolved in a third round: a hypothesis test that failed in 3 of 180
  runs draws feasible tools only; `root_form_diameter_by_intersection` checks a caller's
  `undercut_expected` against the fillet (it must end on the mirrored branch of the involute, else
  `SolverError`) instead of returning the base circle for a gear free of undercut; numbers and
  arrays of the rolling functions, the `TipRounding`, the reference contour and the `.ste` section
  are validated (`InputRangeError`, 36 untyped paths closed); `fillet_curve` takes numpy integers;
  `gear_polygon` handles a full-radius tool (no root arc, shared point placed once, no crowded arc
  points); the join tolerance is pinned from both sides. 1125 tests.

### Changed (increment 3, fourth round - reading a file as STplus computes it, 2026-10-03, ADR-114)
Review by the user after a talk with his supervisor at the FZG: the complete STplus manual was
studied (ch. 1 to 3, 4.1, 4.2, 4.14 to 4.17, 5 to 8, 10) and unclear behaviour probed with the
program (34 new probes). User decisions: the `.ste` importer reads a file as STplus computes it;
a tip circle above the root line of the tool is cut with a warning; where manual and program
disagree (known at the FZG), the program is followed and both are documented.
- `gearcore.stplus_program`: the labelled rules of STplus 11.1F: `stplus_tool_factors` (presets
  1,25 / 0,25 / 1,3 / 1,3; a dedendum below the root form height is set equal to it; edge break
  angle alpha_n0 + 10 deg for the flank between root form height and dedendum; limits of
  addendum, tip rounding, root form height and dedendum, `stplus_max_tool_*`),
  `stplus_helix_angle_deg` (helix angle from centre distance and sum of the profile shift
  coefficients), `stplus_tip_chamfer_height` (limit 0,20 m_n),
  `stplus_residual_tip_thickness` (now in the normal section, at least 0,2 s_an) and
  `stplus_transverse_residual_tip_thickness`.
- `io.ste`: an incomplete file is completed as STplus does and every step is recorded in
  `SteImport.notes`: default hob for a gear without tool, tool factors, absolute tool heights,
  helix angle, the second profile shift coefficient from `PR.VERSCH.SUMME`, tip diameters
  (`SteImport.preset_tip_diameters`), lower span allowance, residual thickness of a chamfer
  given by h_K. Typed errors for what is not translated (controls that move the tool limits,
  tools dimensioned from a measuring line, protuberance heights).
- `generation.compute_generation`: a tip circle above the root line of the tool is cut to
  d + 2 (x_E m_n + h_fP0) (warning `tip_circle_cut_by_tool`); the pair geometry is computed with
  the generated tip diameters; a tool has an edge break flank only where its dedendum lies above
  its root form height (warning `edge_break_angle_without_flank` otherwise); a tooth pointed by
  the edge break flanks is `GeometryInfeasibleError`.
- `data/stplus_program`: 58 defaults (24 before) with the controls and limits of manual §4.17.2
  and the four places where manual and program disagree; 39 probes (5 before); the tool records
  are read as STplus computes with them.
- Evidence: `tests/test_stplus_reading.py` (tool factors of the probes the importer reads and
  of the 18 cases equal the listings in three decimals; cut tip circles, chamfers, residual thicknesses, helix
  angle; example 1 of the manual reproduced: d_Fa 144,535 against 144,536 printed). The
  comparison of the generation is unchanged (537 / 368 / 169 / 0). Notebook 03: new section on
  how STplus reads an incomplete input. Known limits GEN-05 and GEN-07 resolved, GEN-06, GEN-10
  and GEN-11 revised, GEN-13 to GEN-15 added. 1231 tests.

### Fixed (increment 3, fifth round - verification review of the fourth round, 2026-10-03)
A read-only verification review confirmed the rules of STplus against every listing (110 tools,
110 tip circles) and found twelve items around them (G3X-01 to G3X-12: 1 P0, 4 P1, 5 P2, 2 P3).
- `contour.tooth_contour` drew an edge break involute for a tool that states an edge break
  angle but has no flank (dedendum = root form height) where the gear has a given chamfer (P0):
  `GearGeneration.tool_edge_break_angle_deg` is now the angle of the flank the tool has, `None`
  otherwise. The comparison with STplus loses four rows that echoed an input: 533 comparisons,
  364 identical, 169 within the accuracy of STplus, none different.
- `stplus_tool_factors`: the limits apply to presets as to given values (default hob at 28 and
  30 degrees), the rule requires the pressure angle, an edge break angle of 90 degrees is a tool
  without flank, every value is a finite number or an `InputRangeError`; a module or an angle
  of zero is a typed error instead of a `ZeroDivisionError`.
- `io.ste`: the five other definitions of the tip circle (`BEZ_KOPFDICKE`, `DA_DURCH_WKZ`,
  `DA_NACH_DIN3960`, `KOPFSPIELFAKTOR`, `K_HOEHENF_VERZ_BEZ_PR`) are `NotSupportedError` for a
  gear without `KOPFKREISDM`; a control of `$ KONFIGURATIONSDATEN` is one value for the stage,
  its use is recorded, controls not evaluated are named, `ABSCHALTEN_KORRGLIED = 1` is refused;
  with centre distance and helix angle given `PR.VERSCH.SUMME` is not used (as STplus).
- `stplus_tool(name, normal_module_mm=..., normal_pressure_angle_deg=..., notes=...)` completes a
  record of the tool databases with the data of the gear; ten of the fourteen records are
  contracts by themselves, two need the pressure angle of the gear, two exceed the contract.
- Twelve further probes (51 in all), 60 defaults, import records of all probes current
  (`import_stplus_program.py refresh-import`), known limit GEN-16 (a preset tip circle that
  STplus shortens for the tip thickness or the mating gear). 79 further tests, 39 mutations of
  the corrected code detected. 1310 tests.

### Fixed (increment 3, sixth round - second verification review, 2026-10-03)
The verification review of the fifth round confirmed its resolutions and named ten items at the
edges of the new code (G3Y-01 to G3Y-10: 2 P1, 5 P2, 3 P3).
- Edge break angle of a tool as STplus reads it: below the profile angle it is replaced by
  alpha_n0 + 10 deg, equal to it or 90 deg it is a tool without flank; STplus computes 85 deg and
  aborts at 88 deg, so the importer refuses an angle in between (`NotSupportedError`). The
  generation refuses a flank steeper than 89,9 deg (`InputRangeError`): beyond it DIN 3960
  (A.3.05) is not resolved numerically (values wrong by micrometres, then by metres).
- `rack.has_edge_break_flank`: one predicate for generation, contour, comparison and pair
  geometry (the pair geometry announced a flank for every tool that states an angle).
- `io.ste`: the placeholder `%` is "not given" for every key; keys of a tool block that are not
  read and further values of a line are named in notes, junk tokens are `ParseError`; a tool name
  must point to a tool block; `MINDESTKOPFSPIEL` and `ABSCHALTEN_KORRGLIED` follow the rules of a
  control; a control outside its range keeps the preset with a note (as STplus, before:
  `ParseError`); tip circle keys beside `KOPFKREISDM` of both gears are named as without effect.
- Eight further probes (59 in all), 62 defaults; the limit functions return finite values or
  typed errors. 26 further tests, 36 mutations of the corrected code detected. 1336 tests.

### Documented (increment 3 - causes of the deviations from STplus, 2026-10-03)
Question of the user: are the deviations stated as "not known" errors of gearcore? They are
not; the causes lie in STplus and are shown by experiment (four further probes, 63 in all).
- Helix angle iterated by STplus where the file gives none: its iteration ends when the centre
  distance is met within about 0,5 um (18 pairs), so its angle is up to 0,002 deg too small
  (16,25980 for arccos(60 / 62,5) = 16,26020 deg); no documented control changes that.
- Form circles: the root form diameter STplus prints for the undercut pinion of fzg_c moves
  onto gearcore's intersection as BOGENDIFFERENZ is tightened (6,4 / 2,6 / 0,7 um at 10 000 /
  20 000 / 50 000): the accuracy the comparison allows is that of this iteration (GEN-06).
- Residual thickness at an 85 deg edge break flank (0,0200 against 0,0205 mm): single precision
  of STplus; gearcore's value is confirmed by the envelope of the rolling tool flank.
- Gate report: every deviation of the comparison by cause (pair geometry 786 / 25 / 44 / 0,
  generation 364 / 71 / 5 / 93 / 0). 13 further tests. 1349 tests.

### Changed (increment 3 - controls of the tool limits, 2026-10-03)
Question of the user: how do the presets 0,2 and 0,4 the manual names relate to the limits
0,120 and 0,110 the listings show? They do not: the program has other presets.
- With `MIN_WKZ_ZAHNKOPFDICKE*`, `MIN_LUECKENWEITE_EFF0*` and `MIN_LUECKENWEITE_EF0*` varied in
  STplus the limits follow the controls exactly (tip land = s_a0*, tool space = e_Ff0*, root
  space = 2 e_f0* tan alpha_n); the program presets 0,12, 0,11 and e_f0* = 0,03 where the manual
  says 0,2, 0,4 and 0,06. The limits of gearcore are no fit any more (GEN-11).
- The importer reads the three controls (before: `NotSupportedError`); `stplus_max_tool_*` and
  `stplus_tool_factors` take them as keyword arguments.
- Fixed: the range of a control is an open interval in STplus (the ends are not accepted);
  importer and rule functions took the ends as valid.
- Seven further probes (70 in all), 16 further tests, 12 mutations detected. 1365 tests.

### Added (increment 4 - inspection dimensions, 2026-10-04, ADR-115)
User decisions of 2026-10-04: an inspection dimension of an input states which dimension it is;
the core demands the split of the sum of the allowances; k and D_M by the norm, the choices of
STplus as named functions; DIN 3977:1981-02 is still valid.
- **`gearcore.inspection`** (new): DIN 21773:2014-08 as traced functions - chordal tooth thickness
  and constant chord (Eq. (1) to (8)), span measurement with its usable range and measuring
  circle (Eq. (9), (12) to (17)), ball and roller dimensions (Eq. (26), (27), (29) to (37)),
  overcut tip diameter (Eq. (40)), allowances and allowance factors (Eq. (43) to (63)); DIN
  3977:1981-02 Tabelle 1 (`data/din3977_table_1.yaml`) and section 6. `compute_inspection`
  returns `InspectionResult` with nominal dimension and upper, mean and lower limit
  (`DimensionLimits`, computed as §4 says), the choices made and warnings.
- **Contracts**: `DimensionKind`, `SpanMeasurement.kind` (required; breaking), `BallMeasurement`,
  `GearInput.ball_dimension` / `measuring_ball_diameter_mm`, `GearInspection`, `InspectionResult`;
  `GearGeneration.tooth_thickness_allowance_um`.
- **Resolution** (`pair.resolve_tooth_thickness`): per gear two of {x, inspection dimension,
  allowances}, per pair two of {a_w, x_1, x_2}; over- and under-determination are
  `InputRangeError`. The generation rejects an input dimension that does not touch the involute
  it determines.
- **`.ste` importer**: `ZAHNWEITE` / `DIAMETRALES_MASS` read as the upper limit of the finished
  gear, as STplus reads them; `MESSTUECKDM_D_M`, `MESSZAEHNEZAHL_K`; pair-level rules of STplus
  as typed errors or notes. 18 new probes (88 in all).
- **How STplus chooses k and D_M** (found by experiment): `stplus_number_of_teeth_spanned`,
  `stplus_measuring_ball_diameter` (table of the program, 44 values, not DIN 3977 Tabelle 1),
  `stplus_inspection_choices`, `with_stplus_inspection_choices`; evidence
  `data/stplus_program/inspection_choices.json` (540 gears), `scripts/stplus_inspection_choices.py`.
- **Comparison** (`parity.compare_inspection`): 876 rows over the 18 cases, 675 identical, 201
  within the accuracy of STplus, none different; k and D_M computed by the rules of STplus, chord
  on the printed cylinder.
- **Findings**: DIN 21773 Eq. (10) and the second forms of Eq. (12), (13) are smaller by 0,5
  inside INT than Eq. (9); DIN 3977 Bild 2 names a 6 mm ball its own limit excludes
  (`norm_map.md`).
- Notebook `04_pruefmasse_din21773`; notebook 02 adapted (a span states its kind). Registry: 142
  quantities (34 new). Gate: `gate_reports/increment_4.md` (three reviewers, no P0; includes the
  independent review of the last rounds of increment 3: nine findings, causes of two deviations
  reworded, GEN-17 and GEN-18 opened).

### Added (finite element model, steps S2 to S4 - position of the pair, wheel mesh, rigid surface, 2026-10-05, ADR-116)
User decisions of 2026-10-05: one static analysis per mesh position instead of a rolling
simulation; the steel gear of a steel-plastic pair is a rigid tooth surface; the working flanks
touch in the start position; the wheel mesh keeps the reference topology; this stage comes
before increment 5.
- `gearcore.fe.placement`: position of a spur gear pair from one number, the radius of curvature
  of the pinion flank at the contact point of the followed tooth pair; distance of any two
  facing flanks, distance of the back flanks, the same relative position with the wheel at rest,
  working flank and torque sign for the sense of rotation of the driving pinion. kst-E: working
  flanks 1e-14 mm apart, back flanks 0,4850 mm (STplus prints j_n = 0,485, j_t = 0,521).
- `gearcore.fe.sector_template`, `data/fe/sector_template.json`, `scripts/build_fe_template.py`:
  one tooth block and one shoulder block derived from the mid slice of the FVA reference mesh of
  the kst-E wheel, the tooth block exactly mirror symmetric, with the regular grid of the tooth
  and the points that divide the contour.
- `gearcore.fe.sector_mesh`: transverse mesh of any number of teeth between two toothless
  shoulder pitches with a selectable number of rim rings; surface nodes placed piece by piece on
  the generated contour, interior by harmonic continuation, tip region smoothed; depths scale
  with the module; a mesh below the quality limit raises `GeometryInfeasibleError`.
- `gearcore.fe.solid`: sweep along the face width, and the sets (halves, first layer, surface
  parts, root per tooth space, head per tooth, fixed nodes).
- `gearcore.fe.rigid_surface`: the swept tooth surface of the steel gear as R3D4, no volume and
  no end faces; z-levels of the mating gear plus the overhang.
- `gearcore.fe.abaqus`: text of the mesh file and of the surface file (keywords valid inside a
  part and in a file without parts).
- `scripts/build_fe_decks.py`: commands `preview`, `mesh`, `surface`; output and pictures in
  `80_output/fe/` (git-ignored), a list of the sets read back from the written file.
- Tests `test_fe_placement.py`, `test_fe_mesh.py`, `test_fe_rigid_surface.py` (50 tests);
  19 mutations of the new code, 18 detected, the remaining one is equivalent for a mirror
  symmetric tooth and exposed a doubled edge weight that is fixed.
- ADR-116, roadmap (stage 5 pulled forward), known limits FE-01 to FE-08.

### Added (finite element model, step S4a - mesh parameters and convergence study, 2026-10-06, ADR-116 amendment)
- `gearcore.fe.refine`: the parameters of the FVA mesh dialog as integer factors on the
  density of the template (elements over the tooth height, along the rounding of the tooth
  root, over the tooth thickness; a uniform factor for convergence series), as conformal chord
  splits that keep the teeth congruent and move new surface nodes onto the contour; effective
  counts in the words of the dialog. `build_fe_decks.py mesh --height --root --thickness
  --uniform`, folder suffix and the counts in the report.
- `gearcore.fe.plane_solver`: plane strain solver with the four-node element in two
  formulations, as Abaqus formulates CPE4 and C3D8 (volumetric strain at the centroid) and with
  incompatible modes (counterpart of CPE4I and C3D8I, condensed per element); stresses at the
  Gauss points and averaged at the nodes, principal and von Mises stresses, strain energy.
- `gearcore.fe.convergence`: load case of point B of the wheel (Hertz pressure patch of the
  line load, Fesselung), evaluation (surface stress of the loaded fillet, tip displacement,
  strain energy), Richardson extrapolation.
- `scripts/fe_mesh_convergence.py study` (series uniform, height, root, thickness;
  sensitivities; tables, extrapolation, pictures in `80_output/fe/<case>/convergence/`, per
  formulation), `verify` (one-tooth sector in the Abaqus Learning Edition with CPE4, CPE4R,
  CPE4I; `.dat` parsing; agreement with the own solver to 7e-5 for CPE4 and 1e-5 for CPE4I),
  `decks` (plane decks of five levels and three element types plus solid decks with 20, 40 and
  80 layers for the full licence, batch file, manifest, instructions) and `compare` (reads the
  `.dat` files back, Richardson over the Abaqus series, layers over the width).
- Study text for the thesis (German): `00_development_documentation/fe_mesh_convergence.md`.
  Result for kst-E: tip displacement converged at the template density; root surface stress
  15 % low with C3D8, 23 % with C3D8R, 4,7 % with C3D8I and 0,7 % with C3D8I at thickness
  factor 2; decision of the user pending (FE-10).
- `gearcore.fe.resample` (step S4b): the numbers of elements of the FVA dialog as absolute
  values (`MeshCounts`: over the tooth height, at the tip edge break, at the tooth root, over
  the tooth thickness, root layers, rim rings, shoulder columns) by reading the block structure
  of the template and rebuilding every block as a grid of the requested size with the
  template's node distributions; `sector_mesh(..., counts=)`; `build_fe_decks.py mesh` takes
  the numbers and `--bore-radius`. With the template's numbers the template results exactly.
- `fe_mesh_convergence.py recommend`: ladder of thickness and root layers, least-squares
  extrapolation (`convergence.richardson_fit`), coarsest mesh within the tolerances and a node
  budget, then the other numbers coarsened one at a time with a contact floor for the flank;
  the element type is named (kst-E at 2 % / 1 %: height 18 + 1, root 60, thickness 14, root
  layers 4, rim rings 4, shoulder columns 2, C3D8I, 3 890 nodes per layer).
- `convergence.hertz_line_contact` with `@eq` on Maschinenelemente 1 (Tab. 13.1, Eq. (13.5),
  (13.6)) and VDI 2736 Blatt 2 Eq. (15). `sources.yaml`: Maschinenelemente 1 (Niemann, Winter,
  Höhn, Stahl, 5th ed. 2019) and the book of Stommel, Stojek, Korte (2nd ed. 2018), confirmed by
  the user; registered with confirmation pending: Bathe, Finite Element Procedures (1996) for
  the a priori error order, Dahmen and Reusken, Numerik für Ingenieure und
  Naturwissenschaftler (3rd ed. 2022) for the extrapolation (both cited with `@eq` on
  `richardson` and `richardson_fit`), Erhard and Strickle, Maschinenelemente aus
  thermoplastischen Kunststoffen, Band 2 (1978) for the Hertz pressure of plastic gears
  (FE-12, FE-13).
- Tests `test_fe_convergence.py` (26 tests: conformality, counts, contour, congruence, patch
  test of both formulations, cantilevers, load case, evaluation, Richardson, least-squares
  fit) and `test_fe_resample.py` (7 tests: counts, patches of the template, reproduction of
  the template, other counts, bore and rings). Known limits FE-04 revised, FE-09 to FE-12.

### Added (finite element model, step S5 - position files, manifest, runner, Learning Edition tests, 2026-10-06, ADR-116 amendment)
- `gearcore.fe.deck`: one position file per mesh position with parts and instances (wheel
  part with mesh include and section, pinion part with the rigid surface, placed instances,
  reference points, rigid bodies, contact pair, material steps W1 to W4, seating step and one
  static step per torque with `*BOUNDARY, OP=NEW`, output requests); reader of the isotropic
  row of a CONVERSE material card; splitter of an orientation file into part and model pieces
  (and the piece without plasticity for W3).
- `gearcore.fe.placement.single_contact_points`: points B and D of the path of contact
  (DIN ISO 21771:2014-08, 5.4.3).
- `build_fe_decks.py decks` (grid of positions with A to E, `pilot`, or named points; manifest
  with positions, torques, card, mesh counts and fillet node chains; `run_all.ps1`; README) and
  `le-tests` (coarse pair and orientation test in the Learning Edition, with `--run`).
- Steps geometrically linear by default (`PositionDeck.nlgeom`): the first pilot and the
  coarse Learning Edition model broke off under NLGEOM=YES with negative eigenvalues, the
  linear steps run through (FE-14). `*PREPRINT` keeps the model printout out of the .dat;
  RF, RM, UR of both reference points and CSTRESS of the flank nodes are printed per step;
  `run_all.ps1` logs the outcome of each job from its .sta. The support moment at the wheel
  deviates from T_2 because the contact force is turned by Δψ against the line of action
  while staying tangent to the pinion base circle, a_2 = a·cos(α_wt + Δψ) − r_b1 (FE-15);
  `build_fe_decks.py report` evaluates a position folder (Δψ, lever arms, contact).
- Solver and contact options of the position file (`nlgeom`, `contact`, `smoothing`,
  `enforcement`, `line_search`) and `decks --variants` for the six diagnosis variants of a
  broken-off run; pilot 2 (linear steps) broke off at 16 Nm by a contact oscillation
  (FE-14), the variant folder goes to the full licence; the Learning Edition ran all six on
  the coarse pair. Largest contact pressure against Hertz: FE-16.
- Tests `test_fe_deck.py` (5 tests) and the point test in `test_fe_placement.py`. Known limits
  FE-14, FE-15.

### Changed (finite element model, step S6 - variant run and element test, 2026-10-07, ADR-116 amendment)
- The six variants of `pilot_20layers_variants` ran on the full licence (2026-10-06): only
  node-to-surface with NLGEOM=NO completes all steps; every NLGEOM=YES file breaks off in the
  12 Nm step with negative eigenvalues of the system matrix from the first load increment on,
  before any contact change and alike for all contact formulations. The element test in the
  Learning Edition (coarse model, node-to-surface, otherwise identical) isolates the cause:
  C3D8I with NLGEOM=YES alone; C3D8 and C3D8R run geometrically nonlinear without a warning
  (FE-14, FE-10).
- `PositionDeck.contact` defaults to `node_to_surface` with SMOOTH 0,2: the contact force
  stays normal to the rigid flank (a_1 = r_b1), the support moment at the wheel lies 1,1 to
  1,4 % below z_2/z_1·T_1 by the lever arm a_2 = a·cos(α_wt + Δψ) − r_b1 (FE-15), the largest
  contact pressure lies below the Hertz value (59,0 / 67,8 / 74,9 against 60,6 / 74,5 /
  85,7 MPa) instead of 34 % above it (FE-16). Every entry of `VARIANTS` names its contact
  formulation itself; the README of a deck folder points to the `** steps` heading line.
- W1 stays geometrically linear (NLGEOM=YES changes moment, rotation and pressure by at most
  0,6 % at 8 Nm); the elastic-plastic steps are to be computed with NLGEOM=YES on a mesh
  without C3D8I (Stommel, Stojek, Korte 2018, p. 2, 52, 474). Confirmation folder
  `pilot_20layers_c3d8_variants` (pilot mesh with C3D8, linear and nonlinear) for the full
  licence; the element type and density of the frozen mesh stay the user's decision (FE-10:
  the C3D8 ladder of `recommend --formulation selectively_reduced` reaches −4,9 % at 286 000
  nodes only).
- Confirmation on the fine mesh (`pilot_20layers_c3d8_variants`, full licence, 2026-10-07):
  with C3D8 the linear and the NLGEOM=YES file complete all steps without a negative
  eigenvalue (140 s / 161 s); NLGEOM changes moment, rotation and contact pressure by at
  most 0,7 %, C3D8 against C3D8I by less than 1 %.
- Rule per material step in `gearcore.fe.deck` (`NLGEOM_OF_STEP`, `ELEMENT_TYPE_OF_STEP`):
  W1 and W3 geometrically linear with C3D8I, W2 and W4 nonlinear with C3D8 on the same mesh;
  `decks` presets the element type and the nonlinearity from the step (`--element-type`
  overrides), the manifest records `nlgeom` and `contact`, the README states the rule. The
  four pilot folders (20, 40, 80 layers, deep bore) are rewritten with it (FE-10, FE-14).
- `test_fe_deck.py`: the variant test checks the node-to-surface default and the
  surface-to-surface option; a test guards the rule per material step (7 tests).
- Variants `n2s_smooth0` and `n2s_smooth0p01` (node-to-surface without or with the smallest
  smoothing): SMOOTH 0 aborts inside Abaqus 2025, SMOOTH 0,01 runs through with the results
  of SMOOTH 0,2, so the surface-to-surface break-off comes from that formulation itself, not
  from the facet kinks of the rigid surface (FE-14); the keyword reference confirms that
  SMOOTH affects node-to-surface only.

### Added (finite element model, steps S6a and S6b - evaluation over the path of contact, mesh freeze, resolution study, 2026-10-07, ADR-116 amendment)
- `scripts/fe_odb_extract.py`: extraction of one position from its `.odb` under the Python of
  Abaqus (reference points, closed contact nodes with radius, width coordinate, tooth half,
  pressure and normal force, nodal averaged principal stresses of every root fillet surface,
  head displacements) into `<job>_fields.json`; copied into every deck folder as
  `extract_odb.py` and called by `run_all.ps1` after each job; `build_fe_decks.py extract
  --folder` for folders computed before (the Learning Edition's Python reads the full
  licence's databases). `CFORCE` added to the field output request.
- `gearcore.fe.evaluation`: reader of the fields files, maxima per tooth half and fillet,
  curves over the path of contact, nested sub-grids of a position grid, resolution table
  (location refined by the parabola through the three highest points, value the measured
  maximum); `report` prints the maxima per step and writes `path_<step>.png` and
  `path_report.md`; the manifest records the grid (positions per pitch, margin, base pitch).
- Mesh freeze (user): 20 layers, bore 33 mm (inner diameter of the plastic region, steel
  insert as the fixed Fesselung), recommended density, `frozen_mesh_20layers_bore33` for the
  CONVERSE mapping; pilots at 40 and 80 layers, deep bore and positions A to E all complete
  (FE-08, FE-14). Resolution study `study_20layers_bore33_60perpitch` (133 positions) written
  and started. Findings: location of the contact maxima (FE-16), edge loading of the sharp
  pinion tip at B and E (FE-17, model unchanged).
- Mesh file header names the effective number of rim rings; `scripts/fe_mesh_convergence.py`
  typed (mypy clean).
- Tests `test_fe_evaluation.py` (3 tests); suite 1 600 tests.

### Added (finite element model, step S6c - wheel body with pockets after the drawing, 2026-10-07, ADR-116 amendment)
- `data/fe/body_sections.yaml`: the half section of the kst-E wheel body transcribed from the
  user's drawing (hub of full width, pockets open to both faces with walls at 93°, web 4 mm,
  rim, corner radii R 0,5), the drawing as the source; `data.load_body_sections`.
- `gearcore.fe.body`: `BodySection` (wall radii at any depth, pocket volume), `BodyCounts`
  (rings hub / pocket / rim, layers over the web and per pocket), `rim_ring_index`,
  `body_levels`, `body_mesh` (rings of the rim on the stations of the drawing level by level
  with the draft, sweep with levels on the floors and the mid plane, pocket elements removed,
  compact renumbering, sets carried over, `WHEEL_BODY_HUB`, `WHEEL_BODY_WEB`,
  `WHEEL_BODY_RIM`, `WHEEL_POCKET_SURF` with its node set).
- `gearcore.fe.solid`: `extrude_to_levels`, `hex_volumes` (2 x 2 x 2 Gauss),
  `remove_elements` (maps of nodes and elements, sets and surfaces filtered), `FACE_NODES`.
- `build_fe_decks.py mesh` and `decks`: `--body ring|pocket`, `--hub-rings`,
  `--pocket-rings`, `--web-layers` (`--rings` then counts the rings between the rim wall and
  the fan ring, the rest of `--layers` goes to the pockets); `mesh` returns the built mesh to
  the deck writer; manifest block `wheel_mesh.body`, README paragraph on the body, picture
  `mesh_body.png` (meridional section through the middle tooth with the drawing in red);
  `le-tests` with the third model `pair_coarse_pocket` (ran through in the Learning Edition,
  all steps, support moment −7890 / −11830 / −15773 N mm). Folder
  `frozen_mesh_20layers_bore33_pocket` (mesh file `wheel-pocket_mesh.inp`, the naming of the
  user for a pocket body; 83 650 nodes, 72 932 C3D8I, 1 428 pocket elements removed,
  position C) for the new CONVERSE mapping (delivered by the user the same evening as
  `91_Converse/wheel-pocket_mesh_{QS,DY1,DY2}.cof`) and the pilot ring against pocket.
- Both body shapes stay as variants (user): the ring body is investigated completely as
  well. FE-17 closed (the real pinion has no edge break), FE-18 (corner radii not meshed).
- Tests `test_fe_body.py` (10 tests).

### Added (finite element model, step S6d - strain rates as a variant axis, orientation check, 2026-10-07, ADR-116 amendment)
- `build_fe_decks.py decks --material W1 W3 ... --cof <file per rate> --rates QS DY1 DY2`:
  one position file per position, material step and rate (`pos_NNN_<step>_<rate>.inp`),
  orientation pieces per rate, the mesh once per element type needed (`<mesh>_C3D8.inp` for
  the nonlinear steps, same numbering), manifest with `material_steps`, `rates` (file, card,
  E, ν, strain rate from `data/fe/converse_rates.yaml`, the user's message of 2026-10-07)
  and per file step / rate / element type / NLGEOM; README names the rates; `report` labels
  by step and rate and draws the curves over the path of contact per series.
- `gearcore.fe.deck`: `split_orientation_file` rewrites the ELSET of the CONVERSE section to
  the wheel's element set (the file names `CONVERSE_AUTO_SOLID`, which nothing defines);
  `read_distribution`, `read_field_variables`; the steps W3 and W4 request the predefined
  field variables `FV` in the element output (an integration point variable, Abaqus 2025
  output variable identifiers); `PositionDeck.rate` in the heading line.
- `scripts/fe_odb_extract.py`: per step the local material directions of up to 300 sampled
  elements of the rim and of the head of the middle tooth (rows of the local coordinate
  system of the stress), their nodes and FV1/FV2 at their centroids. `gearcore.fe.evaluation`:
  `orientation_check` (directions of the database against the CONVERSE distribution turned
  by the rotation of the wheel instance; the angle against the file not turned as the
  discriminating number), `field_variable_check`, `format_orientation`, series of a folder
  (`series_of`, `series_names`, `path_points(..., series)`).
- `le-tests`: fourth model `pair_coarse_w3` with a synthetic orientation file
  (`synthetic_orientation_text`: +x in the part, field variables 0,6 / 0,1, the material
  tables of the reference card), extracted and checked after the run: all steps complete,
  108 sampled elements, instance turned by 91,53°, deviation from the turned file 0,0000°,
  field variables within 3,6e-8 (the orientation turns with the instance, the values are
  those of the file).
- Tests: `test_fe_deck.py` +3 (ELSET rewrite, readers, FV output), `test_fe_evaluation.py`
  +2 (orientation and field variable checks, series).

### Added (finite element model, step S6d - simulation diary, 2026-10-07, ADR-116 amendment)
- `build_fe_decks.py log`: `00_development_documentation/fe_simulation_log.md` generated from
  every output folder (manifest, `.sta`, `.msg`, `run_log.txt`, fields files): per folder the
  curated note of `fe_simulation_notes.yaml` (purpose, outcome, machine, findings), mesh and
  settings, per position file status, increments, wall-clock time, negative-eigenvalue
  warnings and the key numbers of the last load step (support moment deviation, pinion
  rotation, largest contact pressure with place, largest root stress with fillet, place and
  tangent angle, most compressive root stress, head displacement); files not run are counted.
- `gearcore.fe.evaluation.tangent_angle_deg`: angle between the fillet surface at a point
  and the centre line of the tooth the point lies on (from the mid-width contour of the
  fillet); test added.
- First diary: 38 folders, 66 complete, 11 broken-off, 1 open run, 183 files not run.

### Added (increment 2 - pair geometry, 2026-09-30, ADR-107, ADR-110)
- `gearcore.pair`: mating quantities of an external gear pair per DIN ISO 21771:2014-08 §4.4, §4.5,
  §5.2 to §5.4, §5.6 and Eq. (127) of §7.6 (pitches, tip and tip form diameter, working pressure
  angle, centre distance, sum of the profile shift coefficients, working pitch diameters, working
  depth, tip clearance, start of the active profile and its limit by the root form circle, active
  tip diameter, form over-dimension, path of contact, contact ratios, sliding factor, specific
  sliding): 28 traced functions for 36 equations; contract `PairGeometry`.
- **Two of a_w, x_1, x_2** (user decision 2026-09-30, ADR-107): all three together are an input
  error; a given centre distance is fixed and the missing coefficient follows. The `.ste` importer
  translates the silent behaviour of STplus (keeps x_1, derives x_2) and names the dropped value.
  Span measurements are not evaluated yet: a span is reported as not used, and a pair that gives
  spans in place of a missing x is read but not computed (`NotSupportedError`). How a span
  determines the profile shift (DIN 21773 Eq. (14): x or x_E) and how STplus handles it is left
  open by the user until increments 4 and 5 (ADR-107).
- Nothing is assumed silently: tip diameters are an input (`with_nominal_tip_diameters` applies
  Eq. (33) as an explicit choice), root form and tip form diameters are optional results of the
  generation with a warning when absent, the normal pressure angle has no default in the contract,
  and a `.ste` file without pressure angle is rejected as STplus does.
- The contract holds for every call: the orchestrators apply `PairInput` again (strict) to the
  pair they receive and compute with the validated pair; `PairInput` requires z_1 <= z_2; a gear
  declared as internal raises `NotSupportedError`. A mesh whose active profile starts on the
  base circle (d_Nf <= d_b (1 + 1e-12)) is rejected with `GeometryInfeasibleError` because the
  specific sliding is unbounded there; all boundaries use the same relative tolerance.
- `compare_pair_geometry` with a tolerance from first-order error propagation of the single
  precision of STplus: 18 cases, 855 comparisons, 786 identical, 69 within the accuracy of STplus,
  none different. `parity.detection_limits` and `parity.rows_repeating_an_input` state what the
  comparison can show (173 rows repeat an input; limits per quantity in ADR-110).
- **Common tooth depth with the tip form circles** (user decision 2026-09-30, ADR-112): the
  comparison showed that STplus evaluates h_w with the tip form diameters, while DIN ISO 21771
  Eq. (59) and DIN 3960 Eq. (4.2.08) define it with the tip circles (0,117 to 0,500 mm, 8 to 12 %,
  with a tip chamfer). gearcore follows the tip form circles as a deliberate, documented deviation
  from the letter of the norm (on the chamfer the tooth does not carry); the result names the
  value of the tip circles in a warning, and the new `data/stplus/expected_differences.yaml`
  records the decision under `deviations_from_the_norm`.
- Three further STplus runs (fixtures): tip chamfer given as an input (`chamfer_hk_z20_34`),
  helical pair with different face widths (`helix15_b_unequal`), centre distance with x_2 only
  (`a_x2_only_z18_45`: STplus derives x_1 as gearcore does). The evidence for the single precision
  of STplus now covers 14 runs and 126 values (ADR-106, update); one spur value shows it as well.
- Worked example ISO/TR 6336-30:2022 Annex A example 1: twelve further results reproduced, and
  the x_1 the norm prints in parentheses follows from the centre distance and x_2, with the span
  measurements of the table passed on.
- Decimal references for the pair equations, including the limited mesh (both gears, wheel only),
  from the generator `scripts/decimal_reference_pair.py`, which is part of the repository now.
- Eight quantities added to the registry (sum of the profile shift coefficients, tip alteration
  coefficient, tip form diameter, active tip diameter, common tooth depth, length of the addendum
  path of contact, sliding factor at the tip, specific sliding at the end points).
- DIN 3992:1964-03 and DIN 58412:1987-11 (both withdrawn; supplied and confirmed by the user)
  registered in `sources.yaml`; notebook `02_paarungsgeometrie_iso21771`.
- Adversarial gate with two reviewers (1 P0, 7 P1, 17 P2, 17 P3) and a verification review of the
  fixes in two passes (3 P1, 6 P2, 8 P3; then 3 P2, 5 P3), resolved (`gate_reports/increment_2.md`, regression
  tests `tests/test_adv_2.py` incl. a property test of the orchestrator); `pair.py` at 100 % line
  coverage. Shared input guards moved to `gearcore._guards`. The `.ste` importer turns every
  rejection by a contract into a `ParseError`.

### Changed (increment 2)
- `PairInput.normal_pressure_angle_deg` is required (the default of 20° is removed).
- **Zero is stated, never assumed** (user decision 2026-09-30, ADR-111): `helix_angle_deg`,
  `tip_chamfer_radial_mm`, `protuberance_mm` and `machining_allowance_mm` are required fields.
  The `.ste` importer sets a zero for an absent key only together with a note; the fixtures
  record these notes (`stplus_oracle.py refresh-import`).
- Test runs write nothing into the repository: hypothesis keeps no example database and its
  storage directory is a temporary directory.
- Notebook 01 and ADR-106 state the evidence for the single precision of STplus for the 14 runs.

### Fixed (pre-commit configuration, 2026-09-30)
- The whitespace hooks no longer touch reference material (`30_references_and_examples/`, frozen
  FVA post-processing) or the packaged STplus data; the ruff hooks use the configuration of the
  package as CI does (notebooks were formatted with ruff's default line length otherwise);
  nbstripout keeps cell ids. `pre-commit run --all-files` is clean.

### Added (session save/load + sidebar recall, 2026-08-19, ADR-031)
User requirement: "Sitzung als File speichern … alle eingestellten Parameter und
eventuelle Berichte … in der Seitenleiste erneut abrufen".
- **Saved sessions** (`app/services/session_store.py` + `app/api/sessions.py`): a
  session is the frontend's FULL input state (all editable namespaces + label) as a
  versioned, opaque JSON document — one object per session under
  `sessions/<slug>.json` via app.storage. `POST /api/sessions` upserts and can render
  + store the HTML system report in the same call (`sessions/<slug>.report.html`,
  best-effort: a report error never blocks the save); `GET /api/sessions` lists
  newest-first with a has_report flag; `GET /api/sessions/{name}` recalls the state;
  `GET /api/sessions/{name}/report` reopens the stored report WITHOUT recomputation;
  DELETE removes both.
- **Sidebar "Sitzungen"**: save row (name + "mit Bericht" toggle), session list with
  Laden / Bericht (new tab) / delete, and **export/import as a plain JSON file**.
- **Store hydrate**: recalling merges each saved namespace over its defaults
  (`SESSION_SCHEMA_VERSION`), so files from older app versions keep loading after
  fields are added; transient state (Meldungen, served material catalog) is excluded
  from persistence. The persisted Stufenvariation results recall with the session.

### Added (user material database, 2026-08-19, ADR-030)
User requirement: "eine verwendbare Datenbank an Materialien … für das jeweilige
Zahnrad wählen … im Frontend Anpassungen machen, ohne dass diese zurück in die
Materialdatenbank geschrieben werden".
- **User material library** (`app/services/material_store.py`): persistent, definable
  materials next to the built-in catalog — one JSON object per record under
  `materials/user/<slug>.json` via app.storage (works on local AND S3-compatible
  backends; per-record objects keep concurrent nodes race-free). Built-in names are
  immutable (neither overwritable nor deletable); slug collisions are rejected.
- **API**: `GET /api/materials/catalog` now serves built-ins + user records (with
  `builtin` flag and the full property set incl. R_p0.2/ϑ_zul);
  `PUT /api/materials/user` upserts, `DELETE /api/materials/user/{name}` removes
  (404 unknown, 422 built-in). `/api/ui-schema` refreshes the `mat_name` options per
  request from the live library.
- **Frontend**: the served catalog replaces the static name→kind mirror
  (`CATALOG_SEED` remains as the offline seed, drift-guard test re-anchored);
  selecting a material for a gear snaps the kind (ADR-026 coupling) AND **loads the
  library values into the editable Werkstoff fields** — edits there stay
  session-local, never written back. New Werkstoffdatenbank section in the Werkstoff
  tab: record list with kind badges and per-gear apply buttons, create/edit form
  (prefillable from the current session values), delete with automatic re-selection
  of the kind default; saving reloads the schema so the dropdown follows the library.
- Known limitation (recorded): the property fields are per KIND, so a same-kind pair
  (steel/steel) shares one working property set; and the FE deck's Marlow curve stays
  the built-in catalog data (user plastics run linear-elastic in the deck).

### Added (helical geometry report — analytics only, 2026-08-19, ADR-029)
User-approved package: the Workbench Geometrie tab and the HTML report now compute
helical stages ("nur die richtige Geometrieanzeige … noch nicht in Richtung FEM").
- **SSOT geometry service is helical** (`compute_geometry_report`): every inspection
  block carries its DIN 21773:2014 helical form, verified page-by-page against the
  norm PDF — chordal thicknesses per Eqs. (1)–(8) (normal-section chord with β_y),
  measuring tooth count per Eqs. (10)/(12)/(13) (base-tangent lengths ÷ cos β_b),
  W_k per Eq. (14) (unchanged shared helper — already transverse), ball measures per
  Eqs. (30)–(36) using z·m_n·cos α_n = d_b·cos β_b, roller measures per §11 (on a
  helical gear with ODD teeth the rollers sit diametrically opposite: M_dR = 2·M_rK,
  a normative discontinuity pinned in the tests), allowance factors per §14 (E*_W =
  cos α_n holds exactly for helical), backlash per ISO 21771 Eqs. (102)/(103)
  (j_wt = j_bn/(cos α_wt·cos β_b)) and the span measurability limit b_Fmin per
  Eqs. (15)/(16) — too-narrow face widths surface as a note in the Meldungen strip.
- **Auto measuring tooth count now norm-native**: Eq. (10) replaces the previous
  roll-angle approximation (identical k = 6 for the kst-E reference; Eq. (9) was
  rejected — its "+1" bracket rounds half a pitch higher and would flip kst-E to 7).
- **ToothProfile removed from the report path**: its four contributions (d_f, d_Ff,
  s_a at d_Na, undercut x_E,min) are computed by their closed transverse-plane forms
  (helical-exact; spur values bit-compatible — all 27 kst-E literals unchanged). The
  2-D contour/fillet/FE chain stays spur-only (NRM-02 guards untouched, user decision);
  helical stages report tool root values without contour-effective overrides.
- **NRM-01 closed**: `/api/geometry/report` no longer 422s helical stages; the HTML
  report renders every table for helical and replaces the 2-D mesh SVG with a note.
- Tests: +8 helical (transverse/overlap hand values, backlash chain, W_k/M_dK
  regression literals for the z=25/40 β=20° reference pair, §11 roller jump,
  β→0 continuity, b_Fmin note); spur kst-E parity block untouched and green.

### Fixed (audit round P4 — polish, display + LOW cleanups, 2026-08-18)
The audit's final block; with it every P1–P4 finding is fixed, declared intentional, or
explicitly deferred with rationale (banner in the audit file).
- **Display (V-01/03/05/06/07/08)**: the Tragfähigkeit gear cards stack below ~1900 px
  (the value columns were clipped/invisible at 1720 px); the Zahnform left pane widened
  340→400 px (approach select/units clipped); the quick-view min width is 390 px (wheel
  column was cut); pair values in the HTML report centre across both gear columns
  (they read as gear-2 values); DE label "(as cut)" → "(wie gefertigt)".
- **Fillet UX (FIL-03…09, V-04)**: Voith's γ_b/b_f no longer show for CAO (dead inputs);
  the contour legend derives entirely from the response (raw i18n keys could leak);
  MeshPanel results reset on gear/stage switch (a pinion mesh was presented as the
  wheel's); the ranking gained the opt-in "incl. CAO" checkbox; the Dong sweep combos
  now mirror the backend; the Vernetzung quick check uses the ACTIVE fillets + per-gear
  densities (it hardcoded standard); the Variation fillet editor shows the
  manufacturability note + a CAO cost hint.
- **Wiring LOWs (GAP-09…14)**: the ISO 1328 quick check computes BOTH gears at
  d = m_n·z/cos β with labelled columns (was wheel-only at the spur d); measuring-ball
  Ø D_M per gear is a Toleranzen input reaching M_dK/M_dR (was locked to 1.75·m_n);
  the Meldungen strip is live (geometry notes + request errors via the store); the
  dynamics regime is a locale token translated in UI and report (raw English leaked
  into German); the FE pair header shows the WORKING centre distance (reference a was
  shown in "from x" mode); the Übersicht cards actually navigate to their targets
  (STR-14 — all three landed on the stage node).
- **Contract/consistency (COV-14/15/16, STR-08/09, FEM-06/07)**: the engagement plot
  draws the root circles and takes ε_α from the served contact ratio; the CAO response
  is diagnostics-only (the contour echo duplicated /contour) and GearCapacity lost its
  redundant label echo; the overview shows α_n/β/α_wt/ε_β; `effectiveStage` is memoized
  on its actual inputs (any store change used to hand every stage-keyed effect a fresh
  object — spurious refetches and Variation step-1 reseeds); the CAO cache fingerprint
  includes the tip-chamfer parameters; the deck mesher receives the per-gear
  flank-symmetry flag the preview already used (latent preview↔deck divergence).
- **Deferred with rationale** (audit banner): STR-05/06 (unreachable schema geometry
  tab + unconsumed rules engine — architecture cleanup, not polish), STR-07 quick-view
  fetch cache, STR-15 dead i18n keys, FEM-09 sweep-UI 2D-FE marker, GAP-10 remaining
  unconsumed diagnostic fields.

### Added/Fixed (per-gear Flankenmodifikation + audit round P3 visibility, 2026-08-18, ADR-028)
- **Wheel-side Flankenmodifikation node [41]** (user requirement: each gear edits its
  micro-geometry independently in the FULL editor): its own `correction2` store state,
  rendered by the SAME backend gear_correction schema via a new SchemaTab binding-remap
  (`correction.*` → `correction2.*`); `effectiveStage` derives `modifications_wheel`
  from it. The Auslegung micro table is now a pure read-only mirror of BOTH nodes.
- **C_a reaches K_v** (GAP-05): per-gear tip relief from THE stage micro-geometry feeds
  `DynamicConditions.tip_relief_um` in /capacity and /dynamics (it never arrived before
  — K_v always used the running-in C_ay); the Tragfähigkeit tab's disconnected
  `tip_relief_ca_um` second state is gone, replaced by a computed per-gear mirror row.
- **Ra→Rz coupling live** (GAP-05): with "automatisch umrechnen" on, editing R_a sets
  R_z = 6·R_a (ISO 6336-2:2019: Ra ≈ Rz/6, verified in the norm text).
- **ϑ₀ user mode live** (GAP-03): ambient "Nutzereingabe" reads the Betriebsdaten field
  (was hardcoded 20 °C); **K_A,stat input row** added (GAP-04: "Nutzereingabe" silently
  used 2.0 with no field).
- **Übersicht follows the active stage** (GAP-07): live /api/geometry + materials store
  instead of the frozen kst-E example; example/free mode labelled.
- **FEM-results provenance** (GAP-06): the dump's solver mode is shown plus an explicit
  "unwrapped with the CURRENT stage/fillet" note.
- **Visibility round (COV-03…09/12)**: Geometrie tab + HTML report gained the pair rows
  m_t/α_t/β_b/u/a_d/Σx/b_gem, k_min/k_max, has_undercut (✓/✗ + report verdict), h_fP0*
  and d_f,eff (report, now fillet-aware); DesignPanel + report show the full ISO 1328-1
  set incl. f_HαT/f_HβT/f_fβT; GearCard shows W_zul (pass/fail tone on W_m) and λ; the
  report's factor table carries K_Fα/K_Fβ/Z_ε/Z_B/Z_D/F_t/v/w_t/z_n and the per-gear
  sections σ_H0/σ_F0, s_Fn*/ρ_F*, q_s/h_Fe*, α_Fen, H_V, ϑ_Fla (tab↔report symmetric);
  the Stufenvariation summary names the ACTUALLY varied parameters + kernel time.
  W_k has ONE implementation (`gear.span_over_k_mm`, COV-12).

### Fixed (audit round P2 — state consistency + material SSOT completion, 2026-08-18)
Verification first (user question: "is the material really defined in ONE place and read
by every consumer?"): all frontend reads/writes go through the one `materials` store
slice (Werkstoff tab bindings + coupled mirrors) — with ONE residual violation, fixed
here. Then the audit's P2 block:
- **F4/FEM-03 — deck material parity**: the FE deck endpoints built their material cards
  from the raw catalog, silently diverging from the analytics the moment E/ν/ρ was
  edited. `DeckRequest` now carries the Werkstoff-tab overrides and `deckPayload` sends
  them; the plastic Marlow CURVE stays catalog data (a scalar E edit cannot regenerate a
  measured stress–strain curve — documented).
- **Catalog served + drift guard (F2 root)**: `GET /api/materials/catalog` serves THE
  catalog (names, kinds, core properties); a test pins backend CATALOG ↔ Werkstoff-tab
  `mat_name` options ↔ frontend name→kind mirror in sync.
- **F12 — .ste kind heuristic guarded**: `material_from_ste` logs an explicit warning
  whenever it INFERS the kind from the 20 GPa modulus line (the only inference in the
  system; the toggle must confirm imported materials before a norm branch runs).
- **COV-01/FEM-05 — allowance band lives**: the Geometrie tab and the HTML report now
  send the FULL A_We/A_Wi band per gear (plus the DIN 3964 A_a half-band), so
  E_sns/E_sni display distinct values and backlash uses the band, not a mean; editing
  Abmaße leaves the frozen kst-E example mode (free parameters reproduce kst-E exactly),
  so series/edits are never silently inert. `ReportRequest` gained the `geometry`
  context (fillets + band) instead of rebuilding with None.
- **STR-02 — ONE accuracy grade**: the Toleranzen grades drive `operating.accuracy_grade`
  (worse grade governs) and the Auslegung tab's ISO 1328 display reads/writes the same
  source — the triple state (7/7/8) is gone.
- **STR-03/FEM-02/FIL-01 — ONE fillet + density state**: Zahnform and Netz tabs bind to
  `fem.fillet_gear{n}` and `fem.refine_*` (per gear) instead of panel-local copies, so
  what those tabs show is EXACTLY what deck, pair view and geometry report use; the
  cached standard-contour overlay resets on gear/stage switch (no stale comparisons).
- **FIL-02 — variation fillet reaches the deck**: Übernehmen writes the compared Fußform
  into `fem.fillet_gear2`; the tooltip now says exactly that.
- **STR-01 — one micro-geometry source**: the DesignPanel draft seeds from the RAW stage
  (tab-owned merges are no longer baked back in), and its pinion micro rows are a locked
  read-only mirror of the Flankenmodifikation [34] tab (they were dead controls the
  effective stage always overrode); wheel rows stay editable.
- **FEM-04 — junction-aware FE classification**: set/surface tagging, rigid-shell flank
  sets, the root/flank refine-band split and the FEM-results ξ-range markers follow the
  ACTIVE fillet's junction radius instead of the standard d_Ff (a raised Landi junction
  had put fillet arc into the contact/measurement sets and the wrong density band);
  `/api/fem/results` accepts the active FilletSpecs.

### Fixed (material dispatch separation + glossary maintenance, 2026-08-18, ADR-026)
User directive: the steel and plastic calculation branches must NEVER mix, the material
kind must be an explicit input, and the glossary must carry every symbol with current
norm references and cross-links. A 3-agent trace (backend dispatch / frontend mask /
glossary inventory) found and this round fixed:
- **Stufenvariation per-gear norm dispatch** (MAT-01/02, HIGH): the sweep evaluated
  BOTH gears with one hybrid VDI-form chain. Now each gear's stress follows ITS norm —
  plastic → VDI 2736-2 tip-load form (Y_Fa·Y_Sa·Y_ε, Y_β Eq. 12, Z_β = √cos β), steel →
  ISO 6336-3:2019 Method B (new vectorized Y_F/Y_S at d_en in the kernel, no Y_ε, Y_β
  Eq. 66/67, Z_β = √(1/cos β)); σ_H/S_H are per gear under its convention. Y_F/Y_S
  parity vs the scalar tooth-root model is test-pinned; a permanent honesty warning
  states which strength sub-factors the pre-design sweep still omits (MAT-04).
- **Stufenvariation reads the Werkstoff mask** (VAR-01/02, HIGH): the panel sent NO
  material kinds (backend fell back to role defaults) and hardcoded σ-limits; now every
  sweep request merges the live materials/operating store (kinds, E, σ_Hlim/σ_Flim,
  densities, S_min) at call time, the panel's kind dropdowns WRITE THROUGH to the one
  Werkstoffart toggle, and the backend defaults were aligned with the catalog
  (206000/2800 → 210000/4156, MAT-03).
- **Werkstoffname ↔ Werkstoffart coupling** (frontend store): picking a catalog material
  snaps the kind, switching the kind snaps a mismatching name to the kind's default,
  catalog-foreign names are rejected — name and norm branch can no longer contradict.
  The Radkörper tab's material select became a locked mirror (it could flip gear 2's
  dispatch as a side channel), and the schema rule referencing a non-existent store path
  was repaired.
- **VDI 2736 Eq. 7/9 uses the PLASTIC gear's tooth count** (MAT-15): the temperature
  model fed z₁ for both gears — per the norm's symbol list ("Zähnezahl des
  Kunststoffrads"); invisible on kst-E (z 51/52), ~u-fold wrong for the norm example's
  22/73.
- **Density inputs live** (MAT-10/11): steel/plastic density are MaterialParams fields
  piped into m_red (the Werkstoff-tab rows were dead); the no-data fallback is
  kind-aware (plastic 1400 kg/m³, not steel's 7800). Also repaired: an agent edit had
  broken the NRM-08 per-material fill via a stale sentinel comparison.
- **Catalog-first kind branching** (MAT-09): property overrides branch on the resolved
  material's kind, not the request string — safe once catalog names join the API.
- Deck roles for same-kind pairs (foreign-agent fix, reviewed & kept): a steel/steel
  pair with gear 2 as rigid shell was wrongly 422'd as "the plastic side".
- Report labels the VDI branch's form factors Y_Fa/Y_Sa (MAT-13).
- **Glossary maintenance** (user request): now ~200 entries — all existing entries
  refreshed to current-norm references with edition years (DIN 3960 → DIN ISO
  21771:2014 etc.), renames to the printed symbols (K_v, f_ptT/F_pT/F_αT/F_βT,
  E_sns/E_sni, chamfer k → h_K), the c collision split (Kopfspiel vs Freigang c_F), a
  new "inspection" category, and 70+110 new entries covering the full computed set:
  geometry report (pitches, paths, heights, chords, x_E, ζ_a/ζ_f, d_f,eff …),
  inspection/allowances (W_k, M_dK/M_dR, E_sns/T_sn, DIN 3967 series, A_a, backlash),
  the complete ISO K/Z/Y factor chains, VDI thermal/wear set, native dynamics
  (F_βx/F_βy/χ_β/c′/c_γα/m_red/n_E1/N), and the seven fillet approaches with their
  parameters — each with DE/EN description and related-symbol links.
Known remaining (P2): the variation panel still re-seeds its sweep matrix on unrelated
store edits (VAR-03); same-kind pairs share one property set per kind (MAT-05, blocks
free pairing); the FE deck uses catalog material cards, ignoring property overrides
(MAT-06); sweep permissible sides stay sub-factor-free by design (warned).

### Fixed (audit round P1 — analytical correctness, 2026-08-18, ADR-025)
All P1 findings of `20_code/00_development_documentation/consistency_audit_2026-08-18.md`,
every formula re-verified against the repo's norm PDFs (primary sources):
- **NRM-03 — helical capacity factors live**: Z_H now uses the real base helix angle
  β_b = asin(sin β·cos α_n); σ_H0 carries Z_β = √(1/cos β) (ISO 6336-2:2019 eq. 41);
  σ_F0 carries Y_β = (1 − min(ε_β,1)·min(β,30°)/120°)/cos³β (ISO 6336-3:2019 eq. 66/67),
  computed natively inside `evaluate_iso6336` (the never-set load-case field is gone).
- **NRM-04 — Stufenvariation helix factors**: the sweep's Y_β fed the *pressure angle in
  radians* instead of the helix angle in degrees (plus a non-norm clip) — now VDI 2736-2
  eq. 12; the sweep's Z_β switched from the ISO-2019 form to DIN 3990-2 eq. 6.01
  (√cos β), consistent with its VDI-form tip-load stress chain.
- **NRM-05 — Y_X Table 5 un-scrambled** (ISO 6336-3:2019): St/V → 1.03 − 0.006·m_n
  (floor 0.85), Eh/IF/NT/NV → 1.05 − 0.01·m_n (floor 0.80), GG/GGG ferr. → 1.075 −
  0.015·m_n (floor 0.70); m_n ≤ 5 → 1.0. Test-pinned per group.
- **NRM-06 — VDI 2736 TRUE safeties**: S_F = σ_Flim,N/σ_F, S_H = σ_Hlim,N·Z_R/σ_H and
  S_stat = 2·σ_S/σ_F,P (the old values were σ_P/σ = S/S_min and were compared against
  S_min AGAIN downstream); the norm's permissible stresses σ_FP/σ_HP/2σ_S/S_Smin
  (eq. 13/17/24, carrying S_min) are now explicit result fields, and the API maps them
  directly instead of reconstructing safety×stress. The Stufenvariation safeties are
  true safeties too, so the S ≥ S_min verdicts in the UI/report are now correct. VDI
  helix factors wired: Y_β per eq. 12, Z_β = √cos β (DIN 3990-2 — VDI's convention).
- **V-02 — native K_Hβ activated**: F_βx is estimated per ISO 6336-1:2019 §7.5
  (eq. 54/58/59/61/66: f_sh from f_Hβ1 or the full pinion-shaft formula with K′, f_ma =
  √(f_Hβ1²+f_Hβ2²), floor max(0.005·F_m/b, 0.5·f_Hβ)) whenever f_Hβ is known — from the
  accuracy grade (`dynamics_deviations` now returns f_Hβ too) or a direct µm input; an
  explicit `mesh_misalignment_um` override (shaft analysis/RIKOR) wins. Running-in now
  follows eq. 52/53: per-gear y_α/χ_β averaged for mixed materials (min(σ_Hlim) had
  frozen χ_β = 0 for steel–plastic, keeping K_Hβ inert). kst-E @ Q7 now yields
  K_Hβ ≈ 1.12 natively (reference 1.19 with the 1987 estimation model).
- **GAP-01 — Dynamikfaktoren ≡ Tragfähigkeit**: `/api/dynamics` accepts the same
  accuracy grade + material overrides as `/api/capacity` (shared `MaterialParams`
  request base), the tab sends the shared store values, and the HTML report's dynamics
  block uses the capacity context; K_Fβ is now in the response. API-parity test-pinned.
- **NRM-07 — material group + Z_W inputs**: ISO 6336-3 material group per gear and the
  softer gear's HB (Z_W) are request fields (store + Werkstoff tab rows) instead of a
  hardcoded CASE_HARDENED pair.
- **NRM-08 — per-material dynamics data**: m_red/running-in use each gear's density and
  σ_Hlim from the material slots (a plastic wheel is ~5.6× lighter than the former
  steel default).
- **NRM-01/NRM-02 — helical guards**: `compute_geometry_report` and
  `ToothProfile.from_stage` now REFUSE β ≠ 0 (422 on the endpoints) instead of silently
  returning spur-formula numbers for helical input.
- **NRM-09 — ISO 1328-1 eq. 7**: f_HαT gained the missing 0.001·d term (grade-5
  reference values re-pinned).
- **FEM-01 — deck interference check**: `/api/mesh/deck`, `/deck-series` and `/pair`
  route both gears' fillets through the mating-tip interference check (422 on
  interference) instead of instantiating the strategies unchecked.
- Pre-existing E501 long lines in `api/report.py` (from the sub-factor round) cleaned up.
- **Adversarial verify pass over the P1 diff** (5 independent agents against the norm
  PDFs) caught and fixed four more defects before commit:
  - **Missing Y_St ≈ 2.0** in the VDI root check (Eq. 13: σ_FG = Y_St·σ_FlimN — the
    norm's worked example A1 pins σ_FlimN 30 → σ_FP 30 N/mm², and the FVA reference
    prints Y_St 2.000): `root_safety`/`permissible_root_stress_mpa` were a factor 2 too
    small (systematically conservative, opposite pass/fail verdict vs the norm). Same
    in the Stufenvariation `_root_limit` (now 2·σ_Flim — Y_St for plastics, Y_ST for
    steel).
  - VDI Eq. 12 caps **β at 30°** too (only ε_β was capped); same in the sweep.
  - `y_α` running-in cap for surface-hardened groups (Eh/IF/NT/NV) is **3 µm at ALL
    velocities** (ISO 6336-1 eq. 79), not only in the >5 m/s bands.
  - The new helical guards could 500 instead of 422 on `/api/tooth-profile`, the mesh
    preview/deck endpoints and the FEM postprocessing route — all profile-consuming
    routes now return 422 for β ≠ 0.
  - The NRM-07 Werkstoff rows (`mat_root_group`, `mat_softer_hb`) were declared but
    referenced by no section — now rendered in the Werkstoff tab (HB field nullable).

### Added (explicit strength sub-factors + DIN 3967 series, 2026-08-18)
- **ISO 6336-2/-3 strength sub-factors are explicit** end to end:
  `Iso6336GearResult` now carries Z_L, Z_v, Z_R, Z_W, Z_X, Z_NT and Y_δrelT, Y_RrelT, Y_X,
  Y_NT plus the native σ_HP/σ_FP (the API no longer back-computes them from safety×stress);
  self-consistency of the exposed chains is test-pinned (σ_FP ≡ σ_FE·Y_NT·Y_δrelT·Y_RrelT·Y_X,
  σ_HP ≡ σ_Hlim·Z_NT·Z_L·Z_v·Z_R·Z_W·Z_X; kst-E: Y_RrelT 0.957, Y_δrelT 1.001). Rendered in
  the Tragfähigkeit gear cards and the HTML report's per-gear norm sections.
- **DIN 3967:1978 allowance tables complete** (`services/geometry/din3967.py`): Tables 1
  (upper allowances E_sns, series a…h) and 2 (tolerances T_sn, series 21…30) over all eleven
  diameter ranges, pinned against the norm's own example (27cd @ d=100 → −70/−170 µm).
  Selectable per gear on `/api/geometry/report` (priority: direct µm input > DIN 3967
  series > example STE > StageParams mean) and via a Geometrie-tab picker that FILLS the
  existing SSOT span-allowance inputs (tol.awe/awi) so x_E, deck, backlash and report all
  follow one source.

### Documented (2026-08-18)
- The two deliberate norm-over-STplus deviations (chordal-measure cylinder d_a − 2·m_n per
  DIN 21773 §5; as-cut tip thickness at d_Na) and the DEFERRED scuffing implementation
  (ISO/TS 6336-20/-21, sources in repo) now have their own sections in
  `norm_geometry_audit.md`.

### Added (full geometry output on current norms — backend SSOT, 2026-08-05, ADR-024)
- **`compute_geometry_report` (services/geometry/report.py)** — ONE service computes every
  macro-geometry, tooth-thickness, inspection, sliding and backlash quantity per
  **DIN ISO 21771:2014** (incl. national Annex NB corrections), **DIN 21773:2014** (§5–§14:
  chordal measures, span W_k with AUTO measuring tooth count k_min/k/k_max, single/two-ball
  and roller measures with exact allowance differences, allowance conversion §14) and the
  still-valid **DIN 3967/3964** (E_sn = A_W/cos α_n; j_bn/j_t/j_n; Δj from the centre
  allowance A_a). Fillet-aware: the selected root-fillet strategy's effective root diameter
  is reported next to the tool d_f. **kst-E parity test-pinned** (27 checks transcribed from
  .sta Blatt 6–8: W_k 17.090/17.180 with k=6, M_dK 53.846/55.064, allowance factor
  2.489/2.415, contact circles 50.788/50.779, ζ_a/ζ_f, K_ga, j_t/j_n 0.521/0.485 …).
  Documented norm-over-tool deviations (ADR-011): chordal thickness on the DIN 21773 §5
  cylinder d_a − 2·m_n; tip thickness as cut at d_Na.
- `POST /api/geometry/report` + the Geometrie tab now renders the FULL report as grouped
  sections (Teilungen/Eingriff, Durchmesser, Zahnhöhen & Gleiten, Zahndicken & Abmaße,
  Prüfmaße, Flankenspiele, Werkzeug) — fillet-reactive via the shared store; the HTML
  report's geometry section carries the same rows.
- `POST /api/capacity` exposes the previously computed-but-dropped values: K_Fα, K_Fβ,
  Z_ε, Z_B/Z_D, F_t, v, line load, z_n (factors) and σ_H0/σ_F0, s_Fn*, ρ_F*, q_s, h_Fe*,
  α_Fen per gear (+ VDI: H_V, ϑ_Fla); the Tragfähigkeit tab renders σ_HP/σ_FP/Y_F/Y_S and
  the new factor/critical-section rows.

### Fixed (capacity)
- **K_Hβ/K_Fβ were computed natively (ISO 6336-1 Method C) and silently discarded** —
  `/api/capacity` always used the request default 1.0. `face_load_factor: null` now means
  "use the native value" (kst-E: ≈1.19/1.16 like the reference); an explicit number stays
  an override, so legacy payloads are unchanged. The frontend sends null for the untouched
  default.

### Added (all seven literature root-fillet approaches, 2026-08-05, ADR-023)
- **`FilletSpec(kind, approach)` two-level schema** (backward compatible: payloads without
  `approach` normalize to the family default and stay bit-identical, pinned by test):
  elliptic → `kassem | fruehe | landi`, bezier → `roth | dong`, bionic → `voith | cao`.
  Every new approach implemented from its PRIMARY source (pdftotext/pdftoppm — the built-in
  PDF reader mislabels the Nautos norm/paper PDFs as password-protected).
- **`FruheEllipticFillet`** (supervisor priority): Frühe's tilted ellipse in closed form
  (Diss. Eqs. 89–100, no solver) — G1 at d_Ff AND at the gap centreline, the root diameter
  is a RESULT of the fit (kst-E: −0.35·m_n). Quick-FE: **−20.9 %** σ vs the ρ_F arc.
- **`LandiEllipticFillet`**: the paper's double-tangent axis-aligned ellipse (4-unknown
  fsolve with normals'-intersection start + multi-start); parameters `ra_f` (D1 towards the
  limit contact diameter — the paper default; −20.5 % at 0.3) and `d2_frac` (D2 on d_f up to
  the gap centreline).
- **`DongToolBezierFillet`** + generic **`rack_tip_envelope`** hobbing-envelope generator
  (arc input reproduces the trochoid < 5 µm, test-pinned): degree-4 hob-tip Bézier per Dong
  Eqs. 2–9, dv0–dv4; default dv1 = 1.0 documented against the paper example (−19.0 % vs
  +12 % with the paper's endpoint constraint on the kst-E ρ* = 0.2 tool). Hob-manufacturable
  → neutral manufacturing note in the UI.
- **`CaoFillet`** (Kassem 2023 biological growth, `services/model/cao_fillet.py`): direct
  growth rule d_i = s·(σ_i−σ_ref)·n_i (σ_ref = fixed junction node, d_per = 0.025·m_n) on
  the quick-2D-FE surface stress (`fillet_surface_stress`); converges on kst-E in 5
  iterations (274.9 → 236.2 MPa, −14.1 %); in-process memo cache; `POST /api/mesh/fillet-cao`
  returns the convergence history (also shown in the Zahnform panel).
- **Junction plumbing**: strategies own their junction radius (Landi/Dong above d_Ff — the
  involute flank continues from `junction_radius_mm`), `junction_offset_mm` = literature
  interference fallback, quick-FE band follows the junction (`fillet_limit_radius_mm`).
- `/api/mesh/fillet-compare` ranks eight named `kind-approach` rows (`include_cao` opt-in);
  `/api/mesh/fillet-sweep` sweeps per (kind, approach, parameter) — including the previously
  missing bionic `gamma_deg` axis; contour responses report `fillet_approach` and
  `effective_root_diameter_mm`; ContourPlot draws d_f/d_Ff reference circles.

### Fixed
- **Stufenvariation dropped the fillet parameters** (`VariationPanel` forwarded only the
  kind): the store now carries the full `FilletSpec` and the step-1 flow mounts the shared
  `FilletEditor`.

### Changed
- Voith `BionicFillet` defaults confirmed by a γ×b_f grid sweep on kst-E (best −3.0 % vs
  default −3.1 % → kept); the tension-triangle closed form is inherently limited on this
  geometry — CAO is the recommended bionic approach (documented in
  `root_fillet_strategies.md`).

## [0.8.0] - 2026-07-07

User-feedback round v0.8 — the rolling INP made physically correct end-to-end plus the
result pipeline. Seven committed phases: (A) per-position torque cycle with SMOOTH-STEP
ramps, edge-tooth start, position-series default deck mode, Drehrichtung, powerflow fixes;
(B) rigid Außenhülle per gear as an R3D4 lateral shell (open end faces); (C) per-gear tools,
Kopfrücknahme C_αa in the FE contour, per-gear root fillet, chamfer verifier; (D)
backend-served pair assembly (`/api/mesh/pair`) + orthographic camera with CATIA controls +
schedule slider; (E) Zahndicke mesh-fineness group, per-gear factors, effective counts, 2D
convergence preseed; (F) PairPanel store-SSOT + one deck payload + resizable panes (never
clip); (G) own Abaqus postprocessing + path-of-contact 3-D stress/strain viewer (ADR-022).
Gates each phase: 201 backend tests, deck-parity verifier incl. `--reference`, ruff, mypy,
eslint, production build, own Playwright screenshots. New ADRs/amendments: ADR-012 (per-gear
tools + C_αa), ADR-019 (Zahndicke group), ADR-020 (backend pair assembly + ortho/CATIA),
ADR-021 (third amendment: load cycle/edge start/series), ADR-022 (postprocessing pipeline).

### Changed (rolling deck load case — user feedback round 2026-07-06, phase A)
- **Per-position torque cycle** replaces the constant-torque staircase
  (`RollKinematics` + `_torque_cycle_pairs`): the angle-driven gear is HELD at each
  Wälzstellung while the torque gear ramps base→full (`ramp_up`), holds at full
  (`hold`, measurement at the END — Newton equilibrium each increment, STABILIZE
  energy decayed), ramps back to the **base fraction** (default 1 % of the powerflow
  torque — flanks stay seated, no free spin; the very first ramp starts at 0), and
  only then the angle sub-ramps to the next position (`move` increments). This is
  what the FVA reference deck does (its AMP-TORQUE alternates −78.5/−7846.2).
- **SMOOTH STEP amplitudes** (`*AMPLITUDE, DEFINITION=SMOOTH STEP`): zero slope at
  both ends of every ramp — gentle contact seating at low torque, no overshoot at
  full torque (addresses the user's convergence aborts at high torque).
- **Roll starts at an EDGE tooth** (`start_at_edge`, default on): the pair is
  pre-rotated ±roll/2 (kinematically coupled) so the sweep walks the contact across
  the sector and the MIDDLE teeth complete the full engagement boundary-free;
  `roll_pitches` default 3 (gear-1 tooth T1 has no working partner in the window).
- **Sweep-union contact pairing** (`_sweep_contact_pairs`): flank centroids are
  rotated through the whole coupled roll and every pairing found becomes a
  `*CONTACT PAIR` — reproduces exactly the reference deck's **7 pairs** (working
  F2 g1-i↔g2-(6−i), back F1 g1-i↔g2-(5−i)); proximity-at-t0 had found only 6.
- **Reference-parity outputs**: `*STATIC …, ALLSDTOL=0.0, CONTINUE=NO`;
  `*RESTART, WRITE`; `*TIME POINTS, NAME=MEASURE` (exact full-torque equilibrium
  instants, hit exactly by Standard) with the full per-flank-set payload (NODE
  CF/RF/U · CONTACT CFORCE/CSTRESS/CDISP · ELEMENT E/MISESMAX/…/S per
  `G{g}T{nnn}F{f}` set + MASTERKNOTEN + global U) plus a cheap all-increment
  animation request (U only); measure table also in the deck header.
- **Drehrichtung** (`rotation_sense` cw/ccw, from the Leistungsfluss "Drehrichtung
  Welle 1" dropdown — new schema row): mirrors roll sign, closing flank and start
  offset consistently.

### Added (position series — the new default deck mode)
- **`POST /api/mesh/deck-series`** (+ `build_position_series`): one INDEPENDENT
  static INP per Wälzstellung — legitimate because the model is path-independent
  (Marlow hyperelasticity + frictionless contact) — robust against convergence
  aborts (one failure costs one position) and trivially parallelisable. ZIP layout:
  `pair_common.inp` (shared mesh via `*INCLUDE`, positioned per file through
  `*INSTANCE` rotation lines — 252 kB instead of ~30 full decks), `pos_NNN.inp`,
  `manifest.json` (angles/torque/files for the postprocessing), `run_all.bat/.sh`.
  The Dyn-Abwälzen tab gets a "Berechnungsmodus" dropdown (series default); both
  frontend download paths share one payload.

### Added (rigid Außenhülle — phase B)
- **R3D4 lateral shell per gear** (`build_rigid_shell` + `rigid_shell_gear1/2`,
  schema row "Ideal steife Außenhülle" per gear): an ideally stiff gear is no longer
  a full solid declared rigid (the ANSA finding — every face constrained, zero
  element reduction) but its **lateral boundary surface only** — tooth contour, both
  radial cut planes and the bore swept over the width, axial end faces OPEN — as
  R3D4 rigid elements about the rotation node. Nodes renumbered to the boundary
  (kst-E: 3 042 vs 16 647 solid nodes at 4 layers), no section/material card, no
  Fesselung nset, contact surfaces uniformly `ELSET, SPOS` (outward by the CCW-edge
  orientation proof); ELEMENT/CONTACT measurement outputs skipped on the rigid side.
  The contact slave (plastic side) must stay deformable (422 otherwise); the legacy
  `steel_shell` shortcut maps onto the steel slot.

### Added (per-gear geometry — phase C, user points 5/6)
- **One tool reference profile per gear** (`StageParams.tool_*_gear2` overrides,
  None = same as gear 1): the free-parameter path now matches the .ste ground truth
  (kst-E: h_aP0* **1.1/1.25**, ρ_aP0* 0.2, 45° Kantenbrechwinkel ONLY on the wheel
  tool → h_K 0/0.117 mm). The .ste importer fills both tools, the Geometrie tab
  renders h_aP0*/ρ_fP*/h_fP0*/h_FfP0*/α_Kn0 per gear, the Stufenvariation
  "Übernehmen" writes h_fP*/ρ_fP* per gear, and the frontend kst-E snapshot carries
  the true per-gear values (was: a single 1.25/0.38 tool for both).
- **Kopfrücknahme C_αa in the FE contour** (like the FVA transient FEM, ADR-012
  amendment): `ToothProfile.from_stage(…, tip_relief_um, tip_relief_start_diameter_mm)`
  applies the relief as an angular reduction δ/(r·cos α_y) ramping linearly from d_Ca
  (default d_Na − m_n) to the tip — contour preview, Zahneingriff plot, mesher
  reprojection, deck assembly and collision alignment all inherit the SAME modified
  boundary (SSOT). Values flow from the Flankenmodifikation editor
  (`tip_relief_dca_mm` now sent as `tip_relief_start_diameter_mm`) via
  `StageParams.tip_relief()`; symmetric flanks only (asymmetric relief stays carried).
- **Root fillet per gear in the pair view**: full `FilletEditor` (strategy +
  parameters) for gear 1 AND gear 2 BEFORE "Paar erzeugen" — drives the preview mesh
  and the deck identically (`fillet_gear1/2`); gear 1 was hard-coded "standard".
- **Verifier tip-geometry checks** (user point 5c, measured not assumed): gear 1 cuts
  NO chamfer (d_Na = d_a — its look is the Kopfrücknahme), gear 2 h_K = 0.117 mm,
  both gears' mesh flank sets end at d_Na, and C_αa = 8 µm pulls the tip flank back
  by ≈ C_αa/cos α (8.83 µm measured).

### Added (viewport parity — phase D, user points 1–3)
- **`POST /api/mesh/pair`**: THE deck assembly for the viewport — runs the deck
  builders' own `assemble_centered_pair` (fillets, tip relief, rigid R3D4 shells,
  closing rotation, sweep contact pairing) and returns the outer hulls in absolute
  assembly coordinates plus the per-gear angle law (edge start + kinematic coupling)
  and the contact-pair list. The PairViewport's local positioning math (half-pitch
  heuristic, no closing rotation — the "gears don't touch" report) is deleted;
  preview and .inp share one payload builder in the panel.
- **Roll slider = real Wälzstellungen**: position k over the deck schedule
  (1 … n, measurement points marked, φ from the backend angle law) instead of a
  free ±15° angle.
- **Orthographic camera + CATIA mouse controls** (shared `CatiaControls`) in the
  pair AND mesh viewports: MMB drag = pan, MMB+LMB/RMB = quaternion free-tumble
  (full 360°, no polar clamp), wheel = ortho zoom; middle-click autoscroll
  suppressed. Rigid-shell gears render as semi-transparent open mantles.

### Added (mesh fineness per gear — phase E, user point 7)
- **New chord group "über Zahndicke"** (`refine_thickness`, ADR-019 mesher): conformal
  chord splits seeded ONLY at the flat tip land — those chords run tangentially down
  through the whole tooth, multiplying the elements over the tooth THICKNESS. Chamfer
  edges are deliberately excluded from the seeds (they cut the 45° corner cells into
  slivers — measured SJ 0.22 on kst-E gear 2; land-only seeding keeps min SJ ≈ 0.45,
  zero sub-gate cells at factors 1–3 on both gears).
- **Per-gear fineness in the deck** (`refine_gear1/2 = (root, flank, thickness)`
  through `assemble_centered_pair` and both deck builders; `DeckRequest` gains
  `refine_thickness` + `refine_{root,flank,thickness}_gear2` overrides — plain fields
  keep applying to both gears).
- **FVA mesh-fineness dialog in the pair view**: per-gear factor table (Elemente am
  Zahnfuß / über Zahnhöhe / über Zahndicke; Zahnbreite = shared layers) with the
  EFFECTIVE per-tooth element counts (counted on the final mesh: one gap rounding,
  one flank, the tip land — new `elements_root/flank/thickness` in
  `/api/mesh/preview`); FE-Mesh tab gets the thickness factor + effective row too.
- **2D quick-convergence preseed per gear**: one button per gear runs the native
  plane-FE convergence for root AND flank and preseeds the factors with the
  converged level.

### Changed (PairPanel SSOT + layout — phase F, user "Felder/Einheit verschluckt")
- **PairPanel fully on the store**: face layers, per-gear fineness factors
  (root/flank/thickness), roll positions, rigid-shell flag, axial offsets and both
  root fillets moved out of panel-local `useState` into `fem.*` — the Dyn-Abwälzen
  tab and the pair view now edit the SAME values. A new `lib/deck.ts` `deckPayload()`
  is THE single request builder; the SchemaTab action and the pair view both call it,
  so identical settings yield byte-identical decks (no more divergent deck paths).
- **Resizable split panes with a min-width lock** (`components/SplitPane.tsx`): the
  model tree, the Ergebnis-Schnellansicht and the viewport panels (PairPanel,
  MeshPanel) get a draggable divider that CLAMPS at the content minimum — the user's
  "Fenster verschieben, aber ein Block, dass man nicht mehr verkleinern kann".
- **Never clip values/units** (user report): `Section` bodies and the QuickView table
  wrappers switched from `overflow-hidden` to `overflow-x-auto` (content scrolls
  instead of being cut by the rounded-corner clip); the ×1/×2/×3 fineness dropdowns
  use a narrow `.sel-narrow` variant so the per-gear column pairs fit without pushing
  units out of the pane; the roll-slider caption moved above the track.
- Verified by own Playwright screenshots (`shot-pair.mjs`, `shot-femesh.mjs` +
  the 27-view `self-screenshots.mjs`): per-gear fineness table with ≙ effective
  counts, closed assembly in the viewport, no swallowed fields/units.

### Added (FE postprocessing + 3-D result viewer — phase G, user goal, ADR-022)
- **Own Abaqus-Python postprocessing script**
  (`app/services/model/postprocessing/abaqus_fem_postprocessing.py`, shipped in the
  series ZIP and runnable on a single deck): works against OUR set naming
  (`G{g}T{ttt}F{f}`, `Rot_Node_Rad{g}`) — NOT the frozen FVA script's
  `REFERENCE_POINT_`/`Geometrieberechnung_E1` text files — and dumps a neutral
  `fem_results.json` (schema `zahnfuss.fem_results/1`): per measurement frame, per
  flank set, per surface node the radius, axial z, S/E von-Mises & principals
  (ELEMENT_NODAL-averaged), CPRESS and |U|. Measurement frames auto-detected (a frame
  carries the `S` field iff it is a `*TIME POINTS=MEASURE` hold), series roll angles
  from `manifest.json`. Kept Abaqus-Python (2.7/3.10) compatible and out of the py312
  ruff/mypy scope as a shipped resource.
- **`POST /api/fem/results`**: uploads the dump (client-side file read, like the .ste
  import) and does the path-of-contact unwrapping on the backend from THE GearStage
  (single source): `ξ(r) = ±(√(r²−r_b²) − r_w·sin α_wt)` relative to the pitch point C
  (gear 1 → E, gear 2 → A), returning structure-of-arrays viewer data plus the ISO
  21771 A/B/C/D/E markers and the extended d_Nf…d_Na range (pre-/post-engagement).
- **3-D stress/strain viewer** ("Ergebnisse (3D)" tab, `FemResultsPanel` +
  `FemResultsViewport`): per contact flank pair a three.js surface — axis 1 = path of
  contact ξ (beyond A/E to d_Nf…d_Na, A…E drawn as markers), axis 2 = face width,
  axis 3 + heat color = selectable σ_v/σ₁/σ₃/ε/CPRESS/|u| — with a position slider over
  the Wälzstellungen, a stable per-tag color scale, the frame maximum flagged, and the
  shared orthographic CATIA controls. Verified with own Playwright screenshots
  (`shot-femresults.mjs`): the contact stress peak travels along ξ with the roll
  position, as it must.

### Fixed
- Powerflow torque reset: entering **0** (not only clearing) now frees both shaft
  fields again (user report).
- PairPanel deck download no longer uses a panel-local M₂=20000: the torque comes
  from the Leistungsfluss (SSOT), incl. Drehrichtung/fasten/align flags.

## [0.7.0] - 2026-07-05

User-feedback round after v0.6.0: powerflow SSOT rebuild (one torque on either shaft,
exclusive load types, shaft-1/2 naming), per-gear variation parameters + controllable
sample count, mesh-zone zoom with the exact line of action (FVA-reference-verified),
and the interactive HTML system report. Gates: 189 backend tests, deck-parity verifier
incl. `--reference`, ruff, mypy, eslint, production build, 27 self-screenshot views.

### Added (interactive HTML system report — full scope)
- **`POST /api/report`** renders a self-contained, printable HTML Gesamtsystemreport
  (like the FVA reference, no external requests, < 300 KB): sidebar navigation,
  Getriebeeinheit (power-flow table in the shaft-1/2 convention), Stirnradstufe
  (ISO 21771 geometry with per-gear columns + colspan pairing rows, the ANIMATED
  Zahneingriff with the labelled line of action as inline SVG + ~30 lines vanilla JS,
  ISO 1328 tolerances per gear, K factors, dynamics/resonance) and — better than FVA
  (user decision) — **each gear only under its own norm**: a mixed pair gets two
  separate sections (ISO 6336 steel / VDI 2736 plastic incl. ϑ_Z, wear, deflection,
  peak load) instead of one table with "−" placeholder rows; a same-material pair
  shares one two-column table. Optional Stufenvariation section (summary, warnings,
  top-20 table, static parallel-coordinates SVG) from the store-persisted last run.
- The endpoint recomputes everything SERVER-SIDE from the input state (stage +
  capacity request + powerflow block) via the same functions the live tabs use —
  the frontend never ships computed values. Plain string templating (no jinja2
  dependency); `app/services/report/builder.py` + `app/api/report.py`.
- Frontend: "Report erzeugen" button in the header (collects the store state incl.
  `varUi` results); `buildCapacityRequest` extracted to `lib/capacityRequest.ts`
  (shared by CapacityPanel + report collector, no duplication).
- Tests (`tests/test_report.py`): mixed pair → plastic rows only in the VDI section,
  no placeholders in the ISO table; steel/steel → one shared ISO table; self-contained
  (no external URLs) with animated SVG + T1…E labels; variation section from real
  sweep points; EN locale.

### Changed (Zahneingriff: mesh-zone zoom with the exact line of action)
- **The Zahneingriff view zooms on the meshing zone** (user decision — no full-disc
  overview; a "Gesamtansicht" toggle keeps the old view) and draws the line of action
  as a static overlay behind the rotating as-cut contours: tangent line T1–T2 on both
  base circles, the active path A–E highlighted, single-contact points B/D, pitch
  point C with a grey crosshair, dashed base + working pitch circles, and the
  characteristics α_wt / g_α / ε_α in the footer.
- **Backend `line_of_action_points()`** (`app/services/geometry/gear.py`): T1/A/B/C/D/E
  in the tooth-profile frame from α_wt, r_b, r_w, d_Na and p_et — the same ISO 21771
  eq. 77 terms as `path_of_contact_mm`; served as `ToothProfileResponse.line_of_action`.
  Verified against the FVA Gesamtsystemreport reference coordinates (kst-E, all seven
  points within 2 µm; |E−A| ≡ g_α, |B−E| = |D−A| = p_et, tangent radii exact).

### Changed (Stufenvariation: per-gear reference-profile rows sweep for real)
- **b₂, h_aP*₁/₂, h_fP*₁/₂, ρ_fP*₁/₂ are real sweep parameters now** (previously greyed
  "Rad-1-Wert führt" rows): the vectorized kernel takes per-gear addendum factors
  (`mesh_geometry`), per-gear tool dedendum/tip-radius (`tip_form_factors` inputs) and
  per-gear face widths — shared-mesh quantities (ε, flank stress) use the common width
  min(b, b₂), each gear's root stress its own width, the weight each gear's own width.
  Only q/pr_P/α_prP stay fixed (protuberance is not in the kernel yet — honest warning).
- **sample_count is user-controlled** (was hardcoded 256): a number field appears next
  to the method select for Sobol/LHS; Sobol rounds UP to the next power of two (scipy
  balance) and says so in the warnings — LHS uses the exact count.
- Fixed: the request-level honesty warnings (`extra_warnings`) were built but never
  merged into `VariationResponse.warnings`; `evaluate()` now broadcasts all outputs to
  the batch shape (a sweep that only touches the tooth-root side — h_fP*, ρ_fP*, b₂ —
  used to collapse the geometry arrays to scalars).
- `VariationPoint` carries the per-gear values; **Übernehmen** writes b₂ and the gear-1
  tool factors into the shared stage; the step-4 contour overlay uses the variant's
  gear-2 reference profile. The sweep request is persisted in the store (`varUi.req`)
  for the upcoming report.

### Changed (powerflow rebuild: ONE torque on either shaft, exclusive load types)
- **One system torque, entered on either shaft** (user decision): the Leistungsfluss
  torque row has a Welle-1 and a Welle-2 field; entering one locks the other, which
  displays the loss-free converted value (T₁ = T₂·z₁/z₂). Clearing the entered field
  resets both to empty. The store keeps `{torque_nm, torque_shaft}` and always computes
  from the RAW entered value — never from the rounded display — so kst-E parity stays
  exact (8 N·m at shaft 2 → deck M₂ = 8000 N·mm, T₁ = 7.8462 N·m).
- **Antrieb/Abtrieb mutually exclusive**: flipping one load's type flips the other to
  the complement (store-level coupling, one setState patch). Both couplings are recorded
  as norm-referenced dependency rules in the schema/glossary.
- **Shaft-1/2 naming in the load tables** (user decision): the Leistungsfluss/Kräfte
  column headers and torque labels use the "Welle 1 / Welle 2" convention (1 = left,
  2 = right gear per ADR-021) instead of "Belastung [16]/[17]"; the model tree keeps its
  FVA instance IDs — the ID system stays in the store for later multi-stage systems.
- **Schema renderer honours dynamic locks**: `RowRef.locked_if` and the new per-column
  `AttributeDef.locked_ifs` are now evaluated (previously ignored); `nullable` number
  fields write null on empty (reset semantics). Downstream guards: capacity/dynamics/
  deck-download show "Kein Drehmoment gesetzt …" instead of sending NaN.
- **Torque SSOT closed in the last two panels**: Dynamikfaktoren and the Stufenvariation
  now read T₁/n₁ from the Leistungsfluss derived values (grey display rows) instead of
  panel-local 7.85/1000 copies; K_A and the deviations write back to the shared
  operating values.

## [0.6.0] - 2026-07-05

FVA-replica completion round: every editor tab field-checked against the 27 reference
screenshots via the Playwright self-screenshot loop; final pass all green (27 views without
errors, 176 backend tests, deck-parity verifier incl. `--reference`, ruff, eslint,
production build).

### Changed (i18n completion + one locale-aware number format)
- **One formatter for every user-visible number** (`fmtNum`/`fmtInt` in `lib/format`,
  bound to the active language via the `useFmt()` hook): German UI now shows comma
  decimals and dot thousands like the FVA Workbench (QuickView 51,495 · ε 1,154), English
  shows the inverse — the previous mix of `toFixed`, hardcoded `de-DE` and `en-US`
  formatting is gone. SVG path/transform coordinates deliberately keep raw `toFixed`
  (machine syntax, never localized).
- **DE/EN complete across the hand-built panels**: Stufenvariation flow, Ergebnis-
  Schnellansicht (ISO 21771 labels), Geometrie, Tragfähigkeits-/Lastfall-Karten,
  Dynamikfaktoren, Auslegung (incl. ISO 1328 rows, micro-geometry fields), Zahnform,
  Übersicht, Zahneingriff animation, 2D mesh caption, schema-table headers and the
  "FEM-Vernetzung durchführen" action — shared attribute names live under one `attr.*`
  key set (DE = exact FVA wording).
- **Tree material badges are data now**: Stahl/Steel and PA follow the Werkstoff
  selection (norm-dispatch source) instead of being hardcoded role strings; remaining
  hardcoded tab titles (Geometrie, Zahnform, Stufenvariation) localized.

### Added (Stufenvariation as the FVA guided 4-step flow)
- **Guided flow in the tree tab** (user decision): 1. Attribute → 2. Rechnung →
  3. Filterkriterien → 4. Ergebnisse with step chips, Zurück/Weiter and "Neue Variation";
  wording and table layout per the FVA screenshots (count line "n Varianten, m erfolgreich,
  k ohne gültige Geometrie", live "Es werden X Varianten angezeigt").
- **Persistent results in the workbench store** (`varUi` namespace): step, response,
  sorted rows, compare selection and filters survive tab switches and back-navigation —
  returning to step 3/4 NEVER recomputes; "Weiter (vorhandene Ergebnisse)" jumps straight
  back into the existing sweep from step 1.
- **Filterkriterien step**: min/max per result attribute (ε_γ, S_H/S_F per gear, a,
  weight) filtering the result set live; changing a filter drops the compare selection
  (indices would silently remap). Empty filter results render a plain note instead of
  degenerate −Infinity axes.
- **Übernehmen (SSOT)**: applying a variant writes it into THE shared stage
  (`setStage`) — Geometrie/Toleranzen/Tragfähigkeit/Schnellansicht/Zahneingriff/Deck all
  follow, and the always-visible stage badge (moved out of the scrollable tab strip into
  the node-title row) renames to "Variante z=… x₁=…".
- **Fußform & Werkstoff-Matrix as variation extensions**: root-fillet strategy
  (standard/trochoid/elliptic/Bézier/bionic) drives the step-4 contour overlays, and the
  per-gear material dropdowns dispatch norms strictly by material (steel → ISO 6336,
  plastic → VDI 2736).
- **Parallel coordinates selection behaviour** (user decision): the picked variant keeps
  its verdict colour and is drawn on top; all other lines turn grey instead of vanishing.
- Self-review script `scripts/shot-variation.mjs` walks the wizard end to end (run →
  filter → compare overlay → back-navigation persistence → tab-switch persistence →
  Übernehmen → Geometrie check) and screenshots every station.

### Added (2D mesh rendering + Zahneingriff animation)
- **2D-Schnitt view of the FE mesh** (`Mesh2DView`): the previously unrendered
  `/api/mesh/preview` now draws every quad as an SVG polygon with the scaled-Jacobian
  heatmap (grey ≥ 0.7, amber, red < 0.35 — same gates as the 3D viewport) plus a legend
  and min-J readout; selectable next to the 3D hull in the FE-Mesh tab (kst-E wheel:
  3 024 quads, min J 0.449, 0 cells below the gate — the ADR-019 reference topology is
  now visually checkable in the app, FVA "FEM-Vernetzer" style).
- **Zahneingriff animation** (`MeshEngagement`, Vorbild Gesamtsystemreport): both gears'
  REAL as-cut outlines (from `/api/tooth-profile`) rendered as SVG and rotated
  kinematically coupled (φ₂ = −φ₁·z₁/z₂) with play/pause + speed slider and pitch-circle
  construction geometry; embedded in the Geometrie tab. Fixed during self-review: the
  tooth outline walker now joins consecutive teeth at the root lands (the first version
  chained the tips and visually covered the gaps).

### Added (Ergebnis-Schnellansicht + Achsabstand-Modus rule + per-gear column headers)
- **Ergebnis-Schnellansicht** (FVA right panel): the ISO 21771 Hauptgeometrie and
  Durchmesser tables of the ACTIVE stage (incl. u, b_gem, ε-values and the derived working
  pitch diameters d_w = 2a·z_i/Σz — kst-E 51.495/52.505 like the FVA quick view),
  recomputed live on every stage change; shown for all component nodes on wide screens.
- **Achsabstand-Modus** (DIN 21771 lock rule): the Geometrie tab carries the FVA dropdown
  "Achsabstand definieren" — in "aus den Profilverschiebungen berechnen" mode the a field
  turns computed/grey and the effective stage sends a = null so the backend derives it
  from inv α_wt(Σx); in "definieren" mode a is the input.
- Schema tables now show the per-gear/per-load **column headers from the instance table**
  (Stahlritzel [8] / Kunststoffrad [9], Belastung [16] / [17]) instead of anonymous columns.

### Added (Flankenmodifikation [34] + Radkörper Stirnrad [40] tree nodes)
- **Flankenmodifikation** editor with the five FVA tabs (Allgemeine Angaben, Flankenlinie,
  Stirnprofil, Weitere Formen, Matrix): every modification as consider-checkbox + form
  dropdown + amount with FVA-style conditional rows (form/amount appear only while the
  modification is active). The amounts our ISO 21771 §6 micro-geometry model carries
  (C_Hβ, C_β, C_βI/II, C_α, C_αa, C_αf) merge into the EFFECTIVE stage; kst-E default:
  Kopfrücknahme C_αa = 8 µm from d_Ca = 51.946 mm active. Matrix editor honestly pending.
- **Radkörper Stirnrad** tab (Werkstoff = SSOT with the plastic wheel's material,
  Radkörpergestaltung with the validated "ohne Radkörper" reference variant as default,
  Einbaulage; the CAD tie-in steps section appears only for the CAD variant).
- Tree: both nodes hang under their gears (Stahlritzel [8] → Flankenmodifikation [34],
  Kunststoffrad [9] → Radkörper Stirnrad [40]) with instance-ID labels from the store.

### Added (Stirnradstufe editor tabs — Toleranzen/Tragfähigkeit/VDI 2736/Werkstoff/Schmierstoff/Lastverteilung)
- **Toleranzen** (screenshot parity): DIN 3967 Zahnweitenabmaße A_We/A_Wi per gear
  (kst-E −278/−207 µm) with the norm-active coupling — the MEAN allowance merges into the
  effective stage (x_E generation AND the rolling-deck backlash/closing rotation), DIN 3964
  centre-distance allowances, DIN 3962 quality grades (feed the dynamics deviations),
  tooth-plot checkboxes.
- **Tragfähigkeit** inputs per FVA sheet (Radkörper modes, Rauheiten R_a/R_z with
  auto-conversion switch, Kopfrücknahme C_a, c_γ mode, K_A) + the results block; the
  capacity request now derives ENTIRELY from the store (stage + Leistungsfluss load case
  with derived T₁/n₁/P/N_L = 60·|n₂|·L_H + operating + materials) — the panel-local
  DEFAULTS copy is gone.
- **VDI 2736 (2014)** tab: Schmierungsart, Zahntemperatur block (ϑ₀ = Öltemperatur-Modus,
  ED, Gehäuse, A_G, µ/k_ϑ/H_v modes with the µ-value row appearing only for
  "Nutzereingabe"), Fuß-/Flanken-Mindestsicherheiten, Verschleiß (W_zul = 0.1·m_n, k_W),
  Verformung, Spitzenlasten — all bound to the SAME operating store the capacity run uses.
- **Werkstoff** tab: catalog selection + Werkstoffart per gear (THE norm/deck dispatch),
  steel/plastic property blocks. **Schmierstoff** tab (ISO-VG-100 data, ν_40/ν_100, ρ15).
- **Lastverteilung (FEM, FVA 377)** tab (visible only while FVA 377 is selected):
  parameters, meshing with a working "FEM-Vernetzung durchführen" action (native
  transplant-mesher check reporting quads + min Jacobian), SHARED Fesselung switches with
  the rolling deck, expert section — solver honestly marked pending.
- Store: `operating`/`materials`/`tol`/`loaddist` namespaces + derived paths
  (`friction_is_user`, capacity load case, deck material kinds) and the effective-stage
  merge; deck action pulls materials from the Werkstoff selection.

### Added (Getriebeeinheit editor complete — Leistungsfluss/Kräfte und Momente/Steuerparameter)
- **Leistungsfluss** (screenshot parity, values match the FVA quick view): Schaltmatrix,
  shaft speeds with the derived n₂ = −n₁·z₁/z₂ (kst-E: 2250 → **−2206.73** min⁻¹, grey),
  load types (Antrieb/Abtrieb) with the norm-active lock rule — the Antrieb torque is THE
  system load case (kst-E M₂ = 8.0 N·m), Abtrieb torque (7.8462 N·m) and both powers
  (1.8487 kW) derive read-only. **SSOT chain**: the transient-FEM deck torque now derives
  from this Antrieb load (`fem.torque_gear2_nmm` is computed; the Abwälz tab has no own
  torque input — FVA behaviour; also fixes the M₂ semantics: 8000 N·mm at gear 2 → the
  deck's converted 7846.2 N·mm at the torque gear, the reference AMP level).
- **Kräfte und Momente**: per-load pair columns (u coordinate, switchability,
  Einzelkräfte/skalierbare Kräfte, Biegemomente) carried per screenshot.
- **Betriebsdaten** completed (Schwerkraft/Fliehkraft sections) and **Steuerparameter**
  (system-run switches, load-distribution block) with honest "FVA solver control — carried,
  computed natively" notes. Derived store paths power the grey fields (rule-engine start).

### Changed (self-review round 1 — own Playwright screenshots vs. the FVA dialogs)
- **Stufenvariation attribute matrix = the FVA dialog row set** (Stufenvariation_Ansicht-1):
  α_n/β/z/x/b per FVA naming plus the per-gear reference-profile rows (h_aP*, h_fP*, ρ_fP*,
  Bearbeitungszugabe q, Protuberanz pr_P/α_prP, Zahnbreite Rad 2) and the four dialog
  checkboxes; separate Wert/Minimum/Maximum/Schrittweite/Einh. columns (values were clipped
  by the old two-column layout); "Es werden N Varianten berechnet." footer. α_n is now
  sweepable end-to-end (`alpha_n_deg` in the sweep kernel); per-gear values the kernel
  cannot separate yet surface as explicit response warnings instead of silently averaging.
- **Tree instance IDs are data**: the `[n]` numbers come from the model-instance table in
  the store (kst-E defaults 1/3/4/6/8/9/…, FVA assigns them on insertion) — no hardcoded
  label strings.
- Dyn. Abwälzen (FEM) tab completed against its screenshot: FE-Löser-Ergebnisdatei switch,
  greyed odb/result path rows, Automatische Netzglättung, Expertenfunktion section.
- Fixes from the screenshot round: dropdowns no longer truncate their FVA phrases
  (select min-width), `/api/geometry` returns the REAL tip diameter d_a (kst-E wheel
  54.022, not the usable d_Na 53.788), Schmierstofftemperatur binding (showed 0 instead
  of 80 °C), dev CORS for localhost:3000 + `NEXT_PUBLIC_API_BASE_URL` in the shared .env.
- New tooling: `50_frontend/scripts/self-screenshots.mjs` (Playwright walk through every
  tree node/tab for the self-review loop).

## [0.5.0] - 2026-07-04

### Fixed (deck correctness — measured against the reference INP, user report)
- **Fesselung is now a coordinate predicate over ALL mesh nodes** — the reference deck's
  `Fesselung_Rad{1,2}` holds the bore surface PLUS both radial cut planes as *complete
  cross-sections* (every single node, bore → root circle, all face-width planes; measured:
  2 268/2 225 nodes per cut plane, no z side faces). The previous boundary-edge traversal
  could miss face nodes. The four FVA "Fesselung" checkboxes (Bohrung/Schnitt/oben/unten)
  are writer flags now (`DeckRequest.fasten_*`), defaults = reference parity.
- **Initial single-flank contact (the gears no longer "run in the air")**: the reference
  stands in single-flank contact at t=0 (~25 µm node gap on the −y flanks; AMP-TORQUE
  switches on while AMP-ANGLE dwells). The writer now computes the backlash-closing rotation
  of gear 2 by exact rotational collision detection on the 2-D boundary polylines
  (`align_contact=True`, 15 µm arc backoff) — kst-E: 243 µm centred backlash → **21.9 µm**
  on the −y flank, angle documented in the deck heading.
- New verifier `10_verifiers/verify_deck_parity.py`: Fesselung composition (bore + two
  complete cut planes to d_f/2), initial gap ≤ 35 µm on −y, torque-before-angle amplitudes,
  one `*STATIC` step, flank-wise contact pairs; `--reference` re-measures the FVA deck.
  ADR-021 second amendment records the measured ground truth.

### Changed (single source of truth — user requirement "eine aktive Geometrie überall")
- **`StageParams` moved to `app/api/stage_params.py`** and became THE shared request model:
  `/api/geometry`, `/api/capacity`, `/api/dynamics`, `/api/tooth-profile`, mesh/contour/deck
  all derive their `GearStage` from the same parameters (plus new fields: tooth-width
  allowances A_We, explicit tip diameters, tool dedendum, gear addendum factor).
  The duplicated `GeometryRequest`/`ToothProfileRequest`/`/api/evaluate` are gone;
  `/api/tooth-profile` now returns the REAL as-cut flanks (tip chamfer, root fillet).
- **Norm dispatch follows the MATERIAL, never the role**: steel → ISO 6336:2019, plastic →
  VDI 2736:2014, per gear (`CapacityRequest.pinion_material`/`wheel_material`) — steel/steel,
  plastic/plastic and mixed pairs all dispatch correctly.
- **Material catalog** (`app/services/materials.py::CATALOG`): 20MnCr5 + Stanyl TW200F6
  (PA46, cond. 80 °C, incl. the measured Marlow stress–strain curve, single copy) feed the
  analytic methods AND the FE deck (`materials_card.card_from_catalog`; FE Marlow keeps the
  reference deck's ν=0.30 while the analytic sheet uses ν=0.34).
- Frontend panels consume the shared stage store: Geometrie edits publish app-wide,
  Tragfähigkeit/Dynamik/Stufenvariation recompute from it (the Variation baseline is the
  active stage, no more hardcoded second gear pair); face width is a per-gear pair
  everywhere; input width cap 132→180 px (values were clipped); computed/locked field
  styling; missing SVG plot CSS tokens defined.

### Added (FVA replica foundation — user decision "Option 2": FVA as template, own logic)
- `20_antigravity_scripts/extract_fva_labels.py` mines the installed FVA Workbench's
  declarative UI (produktmodell_SI.xml + pm_messages DE/EN + pm_combo.xml, inheritance
  resolved) into `00_development_documentation/fva_label_reference.json` — a wording
  reference for 8 replicated components.
- **Own pydantic editor schema** `app/services/uimodel/` (AttributeDef/TabDef/
  DependencyRule/CalcMethod — every attribute with DE/EN label, symbol, unit, norm
  reference, store binding; doubles as the glossary source), served at **`/api/ui-schema`**.
- Frontend: workbench store (`lib/store.tsx`) with path-based bindings (stage/calc/fem/…),
  generic `SchemaTab` renderer, **Berechnungsauswahl** matrix (18 methods, unimplemented
  greyed out, ISO 6336 + VDI 2736 always-on), and the FVA-style shell: model tree
  (Getriebeeinheit → Stirnradstufe → Wellen → Räder) with an editor TAB BAR per node —
  the "Dynamisches Abwälzen (FEM)" tab exists only while FVA 892 is selected and downloads
  the corrected deck with the Fesselung checkboxes + contact alignment.

## [0.4.1] - 2026-07-04

### Changed (user review follow-up — Fesselung parity + rig-view slot convention)
- **Fesselung on reference parity**: `Fesselung_Rad{g}` now ties the bore surface AND both
  radial sector cut faces (bore → shoulder contour) to the rotation node — verified
  numerically against the reference deck's set (bore arc over the full sector + two complete
  radial node chains up to the root circle, all layers). Previously only the bore was tied.
- **Slot convention (ADR-021 amendment)**: every per-gear input follows the stage INPUT
  position through the whole chain (gear 1 = first .ste gear, gear 2 = second — never
  re-ordered by role or tooth count), and the assembly matches the Kleingetriebeprüfstand
  top view: **gear 1 at the origin (left), gear 2 at the working centre distance (right)** —
  in the deck and as the default 3D pair-view orientation. Deck request fields renamed
  accordingly (`gear1_material`/`gear2_material`, `axial_offset_gear(1|2)_mm`,
  `fillet_gear(1|2)`, `torque_gear2_nmm` = M₂, the torque expressed at gear 2). The
  angle/torque/slave roles follow the MATERIAL (plastic side angle-driven + contact slave,
  reference parity), independent of the slot.

## [0.4.0] - 2026-07-04

### Changed (user review of the generated pair — deck conventions, ADR-021)
- **Deck gear numbering now follows the stage input order**: gear 1 = pinion (kst-E: steel,
  z=51), gear 2 = wheel (plastic, z=52) — across parts, `G{g}T{nnn}F{f}` sets, surfaces,
  `Rot_Node_Rad{g}` and `Fesselung_Rad{g}`. Verified against the FVA reference deck that its
  own `Part_Rad_Vz_1` is the plastic z52 wheel (material cards + tip diameters), i.e. reversed
  relative to the .ste order — generated decks now carry a header comment table (z, b,
  material, axis, mid-plane, role per gear) documenting the mapping. The physical load case is
  unchanged (wheel at the origin angle-driven, pinion carrying the torque, plastic = contact
  slave); `wheel_torque_nmm` (M₂) is now converted to the applied pinion torque T₁ = M₂·z₁/z₂.
- **Mid-plane-centred extrusion (reference parity)**: each gear keeps its own face width and
  extrudes symmetric about z = 0, so the 15/17 mm kst-E pair rolls centred by default and both
  rotation nodes sit at their gear's mid-plane instead of on a side face; also applied to the
  single-gear `/api/mesh/3d` hull.

### Added
- **Legende & Parameter panel**: a dedicated, filterable glossary tab (75 entries, DE/EN) —
  symbol, full name, an understandable explanation of what each parameter does and which
  parameters it interacts with, norm badges (click to filter) and clickable cross-links;
  free-text search + category chips + norm dropdown.
- **Parametric axial offsets**: `axial_offset_(pinion|wheel)_mm` in the deck request displace
  each gear along its rotation axis; the pair panel exposes both (Δz₁/Δz₂) and the viewport
  mirrors them live.
- **Deck material matrix**: `pinion_material`/`wheel_material` (steel/plastic) in the deck
  request; the rigid-shell rule resolves to the steel side of a mixed pairing and the contact
  slave to the plastic side; `fillet_pinion` joins `fillet_wheel`.
- Tooth contours are drawn **continuously across the root land**: the plotted boundary is
  completed with the d_f arc from the fillet end to the gap centreline
  (`with_root_land`), so the standard/trochoid envelope no longer shows a gap at d_f.

### Fixed
- CI: `ruff check` over all of `20_code/` (unused variable in
  `10_verifiers/checkpoint2_plots.py`); local lint gate now runs from `20_code/`
  like the pipeline, not just `40_backend/`.
- mypy is now clean over the whole backend including tests (annotations added to the mesher,
  fillet and refine test modules).

## [0.3.0] - 2026-07-03

### Changed (2026-07-03 — frontend swap, ADR-020 completed)
- **`50_frontend/` is now the Next.js workbench** (old Vite SPA removed; `50_frontend_v2`
  renamed): new M6 panels — Auslegung (presets / `.ste` import / free parameters, DIN 3972
  tool presets, ISO 21771 §6 micro-geometry editor, ISO 1328-1 tolerances; publishes the stage
  app-wide), Tragfähigkeit (incl. accuracy grade + VDI 2736 static peak), Dynamikfaktoren, and
  the **pair viewport** with co-moving DOF triads at Rot_Node_Rad1/2 (locked DOFs 1–5 gray,
  free rotation green/amber) and a kinematically coupled roll slider. Mesh panel gains FVA
  density presets, the trochoid option, the manufacturability warning and the fillet-sweep UI;
  Stufenvariation gains the material-matrix selectors.
- **Docker** builds the Next static export (`out/` → `app/static`); the runtime image needs
  **no OpenGL**: gmsh became an optional import (the legacy mapped mesher guards its entry
  points; the deck path runs on the ADR-019 transplant mesher). Container smoke-tested:
  UI + `/api/health` + `/api/mesh/preview` green.

### Added (2026-07-03 — M6 backend: free design flow, fillet axis, presets/import, micro-geometry)
- **Design router** (`app/api/design.py`): shared `StageParams` (kst-E example OR fully free
  pair definition incl. tool reference profile) now feeds EVERY mesh/contour/deck endpoint —
  the kst-E lock is gone; `GET /api/presets` (kst-E + DIN 3972 tool-profile presets I–III /
  ISO 53 A) and `POST /api/import/ste` (STplus text import → editable parameters).
- **Fillet axis for the Stufenvariation**: `POST /api/mesh/fillet-sweep` sweeps one strategy's
  shape parameter (e_f / Be / b_f) with the quick-FE root stress as objective, enforcing the
  interference check and the det(J) gate per point, and recommends the feasible optimum.
- **TrochoidFillet** (`geometry/root_fillet.py`): the exact DIN 3960 tool trochoid as a
  first-class strategy (norm reference beside the ρ_F arc; ADR-017's high-fidelity option).
- **Micro-geometry data model** (`geometry/modifications.py`, ISO 21771 §6): per-flank
  Kopf-/Fußrücknahme, Profil-/Breitenballigkeit, Endrücknahme, f_Hβ per gear — carried through
  `StageParams`, drives the flank-symmetry policy (asymmetric data ⇒ mirror symmetry off,
  teeth stay rotation-congruent); mechanically active from the load-distribution step onward.
- **Variation material matrix**: `pinion_material`/`wheel_material` (steel|plastic) request
  fields — steel/steel, plastic/plastic and both mixed orientations dispatch per gear through
  the existing ADR-013 kernel; weight densities follow the material kind.

## [0.2.0] - 2026-07-03

### Added (2026-07-03 — mesh API, deck rewiring + rigid shell, workbench UI; ADR-019/020, M3–M5)
- **API — mesh router** (`app/api/mesh.py`): `/api/mesh/preview` (2-D sector + per-quad scaled
  Jacobian), `/api/mesh/3d` (outer hull of the extruded sector for the three.js viewer),
  `/api/mesh/convergence` (native root/flank density quick check), `/api/mesh/fillet-compare`
  (quick-FE ranking of the fillet strategies incl. clearances), `/api/mesh/contour` (real as-cut
  boundary — kst-E or free variant parameters, fillet-strategy-capable, with interference check)
  and `/api/mesh/deck` (implicit rolling deck download).
- **FE deck on the transplant mesher (M3):** `implicit_deck.build_gear_part` now meshes via
  ADR-019 (4 teeth + 2 shoulders, density factors, fillet strategy); the mixed-pairing material
  rule ships as `steel_shell`/`rigid_gears` (steel gear = ideally stiff rigid body about its
  rotation node, contact + frozen FVA set contract unchanged); `plastic_index` fixes the
  Workstream-C convention (Part_Rad_Vz_1 = plastic wheel, second `.ste` entry).
- **Geometry:** `ToothProfile.half_thickness_angle` (tip thickness via the edge-break involute);
  the mating-tip interference sweep now samples only MATERIAL tip points and rolls the correct
  direction (a half-pitch corner sweep produced false interference for u ≠ 1 pairs).
- **Frontend v2 (ADR-020):** Next.js workbench under `50_frontend_v2/` — model tree, condensed
  attribute-table editors (Geist, Tailwind), dark three.js FE-mesh viewport with Jacobian
  heatmap, convergence + fillet-ranking panels, deck download with rigid-shell toggle, real
  tooth-form panel (standard vs optimized fillet overlay + clearance), Stufenvariation with
  parallel coordinates, Pareto and the up-to-4-variant **real-contour overlay comparison**;
  DE/EN i18n keys from day one. Served as a static export by FastAPI (`app/static`, gitignored).

### Added (2026-07-03 — reference-topology transplant mesher, ADR-019)
- **FE model — reference miner** (`model/reference_slice.py` + committed template
  `model/data/reference_sector_rad_vz_1.json`, verifier `10_verifiers/make_reference_template.py`):
  the ANSA/FVA wheel slice is parsed with correct cyclic face ordering (rim hexes carry a rotated
  local axis — naive ordering creates bowtie quads) and pinned by tests: 3024 quads / 3329 nodes,
  interior valences {4: 2716, 5: 2, 6: 3} — **exactly one fan-convergence node per tooth gap**,
  rim grid 26×25, min scaled Jacobian 0.243 (24 tip cells < 0.35).
- **FE model — transplant mesher** (`model/template_mesher.py`): generates the reference-identical
  block-structured 2D sector for any spur gear by re-using the mined connectivity and deriving node
  positions from the target geometry (pitch scaling, radial feature map, exact foot-point
  projection onto the analytic contour incl. the ISO 21771 tip chamfer up to d_a, selective §11
  tip lift). kst-E wheel: topology-identical, min scaled Jacobian 0.45, **0 cells < 0.35**.
- **FE model — canonical symmetry**: sector symmetry orbits enforce **exact tooth-to-tooth
  congruence** (≤ 1e-14 mm) and, gated by the data-driven `ToothProfile.is_flank_symmetric()`
  (DIN 867 §4.2), exact in-tooth mirror symmetry; the tip lift is rolled out orbit-synchronously.
- **FE model — parametric density** (`model/refine.py`): conformal chord splits with separate
  FVA-style root/flank factors; structure, gates and congruence survive every level.
- **FE model — native quick solver** (`model/plane_fe.py`): vectorized plane-strain Q4 FE
  (< 0.1 s/solve) for root/flank density-convergence checks (separate searches) — confirms the
  mined reference density is already converged for the root stress (Δ < 0.1 %).
- **Geometry — optimized root fillets** (`geometry/root_fillet.py`, supervisor's topic):
  `EllipticFillet` / `BezierFillet` / `BionicFillet` per the literature synthesis
  (`00_development_documentation/root_fillet_strategies.md`), pluggable into the mesher, with the
  mandatory mating-tip clearance check and a DIN 3960 eq. 3.6.06 undercut warning. Quick-FE on
  kst-E: ellipse −9.9 %, Bézier −22.1 % root stress vs the standard ρ_F arc.
- **Geometry — tip chamfer boundary**: `transverse_right_boundary(to_tip_circle=True)` continues
  past d_Na along the edge-break involute to d_a (`generation.edge_break_flank_transverse`).
- **Docs:** norm audit (`norm_geometry_audit.md` — DIN 3960/867/3972 findings incl. tool-profile
  presets I–IV and protuberance parameters living in DIN 3960 Anhang A) and the root-fillet
  literature synthesis with measured results.

### Removed
- **FE model:** deleted the unstructured gmsh tooth/sector mesher
  (`model/gmsh_mesher.py`: `mesh_sector_3d`, `mesh_tooth_pitch`,
  `mesh_tooth_pitch_3d`). Its self-intersecting multi-tooth boundary could make
  gmsh's Frontal-Delaunay meshing run unbounded — a multi-hour hang at full CPU.
  The structured, deterministic transfinite `mapped_mesher` is now the single
  meshing path.

### Added
- **FE model:** reference-faithful implicit deck generator (`model/implicit_deck.py`)
  reproducing `32_Abaqus/implicit/…_ohne_Radkoerper.inp` — two `Part_Rad_Vz_{g}`
  sectors, bore `Fesselung` rigid-tied to a rotation node, frictionless hard contact
  as explicit meshing flank pairs (plastic = slave), and one quasi-static step driving
  gear 1 through a staircase angle while gear 2 carries the resisting torque. One-call
  entry `build_implicit_pair_from_stage(stage, …)`.
- **FE model:** reference per-tooth/flank tagging (`mesh_sets.tag_gear_reference`) emitting
  the exact `G{g}T{nnn}F{f}_NODESET/_ELEMENTSET` + `TOOTH-{g}-{nnn}F{f}` names the frozen
  FVA postprocessing requires, in 1-based 3-D ids.
- **FE model:** material cards (`model/materials_card.py`) — linear `*ELASTIC` (steel) and
  `*Hyperelastic, MARLOW` + `*Uniaxial Test Data` (plastic), with the kst-E PA curve embedded
  for validation.
- **FE model — geometry:** clean rounded root fillet (`tooth_form.transverse_right_boundary`): the
  ρ_F arc tangent to the involute flank (true d_Ff) and the root circle d_f → a monotone boundary
  with no pinch. Regression test guards monotonicity + flank/fillet continuity for both gears.
- **FE model — mesher:** the transfinite `mapped_mesher` now builds the tooth from that clean
  boundary, with a fine **surface boundary layer** (`flank_bias`, gmsh "Bump") and a radially graded
  **deep rim** to the real bore; Jacobi-Güte ≥ 0.9. Native fallback mesher
  `model/structured_mesher.py` (radius-arc tooth + rim) with a scaled-Jacobian check. (ADR-017)
- **FE model — body mesh (WIP):** building blocks toward the reference gear-body mesh —
  `mapped_mesher.tooth_section_2d` (transfinite tooth+fillet, no rim, + ordered d_f base interface),
  a validated **conformal all-quad 4→2 coarsening template** + graded ring (`structured_mesher.
  body_section_2d`), and Laplacian smoothing. The exact reference **O-grid "dome + run-out"** body
  (fine structure continued under the tooth, coarsening only outside the root) is the next step;
  the tooth/root itself is already reference-grade and (Saint-Venant) sets the root stress. (ADR-017)
- **FE model — reference ground truth + dome (WIP):** the reference deck `…_ohne_Radkoerper.inp` is
  now mined as the *meshed ground truth* (parse a z-slice → exact 2D topology, instead of guessing
  from screenshots): wheel 269 649 nodes, 81 z-levels (b=15, z-centered, Δz=0.1875), bore r=12.38,
  ~723 quads/pitch; structure = fine tooth → dome-cap fan → structured rim grid. New structured
  pieces toward it: optimization-based (quality-greedy) smoothing `structured_mesher._optimize_smooth`
  (+ `boundary_nodes`) and `assemble_pitch_2d` (merge tooth+body, hold only the outer contour, smooth
  the dome). Validated by overlay on the parsed reference; bad-cell count on the kst-E pitch fell from
  26 to 9 toward the reference dome. Dome-quality finish + sector/extrude next. (ADR-017)
- **FE model — body mesh matches the reference (kst-E):** the body is now built as a **root
  boundary layer** (fine surface-aligned arcs hugging the fillet, where the bending stress peaks)
  that runs out into a structured rim grid — the reason the reference is meshed this way. The
  reference itself is fully structured (all interior nodes valence 4; its only 6 cells < 0.35 sit at
  the tooth *tip*, min 0.243). The dome transition is lifted by the now **lexicographic**
  `_optimize_smooth` (maximise the worst incident scaled Jacobian, then the mean — the mean
  tie-breaker unlocks the plateau Laplacian/greedy-min got stuck at). Result on the kst-E wheel
  pitch: all-quad, **min Jacobian 0.736, 0 cells < 0.35** — exceeding the reference (0.243 / 6) with
  a reference-like structure. (ADR-017)
- **FE model — block-structured FVA mesher (`model/block_mesh.py`, WIP):** the reference-faithful
  multiblock route per `MESHING_SPEC.md`, built on the proven scaffold pipeline (TFI/Coons blocks +
  shared-node `NodeRegistry` for conformity, no tolerance merge, no paving/gmsh). Adds B3 fillet band
  (curve-seeded, densified to the 30°-tangent — not offset marching), B4 core, B1 rim, B2 deep 2:1
  quad templates, and the **section-11 finish** (optimization-based worst-first node relocation,
  frozen connectivity, fixed boundary/feature/cut nodes). On kst-E: registry conformity asserted,
  4-tooth + 2-toothless sector periodic to 5e-15 mm, B2 template det(J) **0.21 → 0.66** after the
  finish (0 cells < 0.35, 0 inverted). Element type **C3D8I** in the root. (ADR-018)
- **FE model:** `model/mesh3d.py` holding the pure-numpy `Mesh3D` container and
  the native `extrude_to_hex` (quad section → C3D8 hexahedra), free of gmsh.
- **FE model:** an element-count safety valve (`max_elements`, default
  4,000,000) on the mapped mesher — an over-budget request is rejected up front
  instead of being meshed, so the mesher can no longer hang the machine.

### Fixed
- **FE model:** the inverted / pinched tooth root ("Pokal" shape) is fixed — the root cause was
  `tooth_form.root_fillet_points` producing a non-monotonic, branch-mixed trochoid that did not even
  meet the involute at d_Ff; the `_monotone_fillet` band-aid is removed. (ADR-017)
- **FE model:** gmsh section quads are normalised to CCW winding before the face-width sweep, so the
  C3D8 hexahedra are positively oriented (Abaqus rejects negative-Jacobian elements).
- **FE model:** `tag_sector_surfaces` now reads the bore radius off the actual
  mesh (its quad-referenced nodes) instead of recomputing it from `rim_depth`,
  so the BORE / Fesselung node set can no longer come up empty when the mesher
  used a different rim depth.
- **Tooling:** cleared all outstanding ruff and mypy findings across the model
  layer and the test suite.
- **CI:** the workflow now installs the system OpenGL libs (`libglu1-mesa`, `libgl1`) the gmsh wheel
  links against, and runs `ruff format --check`; CI had been red since gmsh was introduced because
  importing it on the Linux runner failed with `libGLU.so.1: cannot open shared object file`, erroring
  out collection of every gmsh-importing test.

### Verified
- `ruff check .` clean, `mypy .` clean, `pytest` → 136 passed (full gold-standard
  validation active: kst-E, RIKOR, helical references present).
- FE geometry/mesh checked numerically + visually on kst-E (rounded root, deep rim, boundary layer,
  Jacobi 0.9); the all-quad 4→2 body-coarsening template validated standalone (|Jacobi| 1.0, ADR-017).
