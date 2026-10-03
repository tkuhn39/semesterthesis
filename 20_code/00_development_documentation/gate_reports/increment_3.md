# Adversarial gate — increment 3 (tool-based generation, trochoid, transverse contour) — 2026-09-30

Reviewers: two read-only agents per `adversarial_gate.md`, in parallel. `git status` was identical
before and after both reviews; neither ran STplus.

| Reviewer | Scope | Probes |
|---|---|---|
| A | `generation.py`, `trochoid.py`, contracts, tests, decimal script: every `@eq` against the rendered pages, boundary sweeps, invariants, three independent recomputations | own envelope of the tool tip rounding (four flank points mapped onto the involute to 1e-16 rad), own bisection of DIN 3960 (A.3.06), Eq. (128) NB and (130) as printed on the ISO/TR example, sweeps of z, x, β, m_n, tool factors, allowances, x_E around x_Emin |
| B | comparison with STplus, contour, importer, registry, notebook 03, documentation | counts reproduced, own point-to-polyline distances, 22 in-memory mutations against the five test files, registry entries against the rendered pages, DIN 3967 p. 7 rendered, fixture records against the importer |

Baseline reviewed: 1018 tests passed, 8 skipped; ruff, format and mypy --strict clean; notebooks 02 and
03 executed.

**Result: passed after six rounds of fixes. The first, second, fourth and fifth round were each
checked by a read-only verification review, the third and the sixth (both small) by the
implementer with the repro scripts and mutations of the review before them.** Gate: P0 = 1 (resolved). P1 = 8 (all resolved). P2 = 12 (all resolved). P3 = 9 (all
resolved, three accepted as limits). The first verification review confirmed the 29 resolutions,
two of them in part, and named eight further items (G3V-01 to G3V-08: 2 P2, 6 P3), resolved in the
second round. The second verification review confirmed those eight and named eight more (G3W-01 to
G3W-08: 3 P2, 5 P3), resolved in the third round (sections below). Mutations that no test detected
(2 of reviewer B, 3 of the first and 13 non-equivalent ones of the second verification review) are
detected now, except five variations of a tolerance inside the window the tests pin. Deferrals:
`known_limits.md` GEN-01 to GEN-12. Regression tests: `tests/test_adv_3.py`. State after the third
round: 1125 tests passed, 8 skipped (four modules of later increments, four supplied listings
without interface file), 5 notebooks executed (index, template, NB 01 to 03), ruff and format
(package, tests, scripts, notebooks) and mypy --strict (src, scripts) clean, 18 STplus cases, 537
comparisons of the generation (368 identical, 169 within the accuracy of STplus).

**Fourth round (2026-10-03).** A review by the user, who had discussed the increment with his
supervisor at the FZG, led to a study of the complete STplus manual and to a fourth round
(G3U-01 to G3U-10: 3 P1, 4 P2, 3 P3; ADR-114): the importer reads a file as STplus computes it,
and the generation cuts a tip circle above the root line of the tool. Known limits GEN-13 to
GEN-15 added, GEN-05 and GEN-07 resolved. State after the fourth round: 1231 tests passed, 8
skipped; the comparison of the generation unchanged (537 / 368 / 169 / 0). Section "Review by
the user" below.

**Fifth round (2026-10-03).** The verification review of the fourth round confirmed the rules of
STplus against every listing and named twelve items around them (G3X-01 to G3X-12: 1 P0, 4 P1,
5 P2, 2 P3), among them a contour that drew an edge break flank the tool does not have. All are
resolved, twelve further probes decided the cases that needed the program, GEN-16 added. State
after the fifth round: 1310 tests passed, 8 skipped; 533 comparisons of the generation (364
identical, 169 within the accuracy of STplus, none different). Section "Verification review of
the fourth round (2026-10-03) and fifth round" below.

**Sixth round (2026-10-03).** The verification review of the fifth round confirmed the twelve
resolutions (two in part) and named ten items at the edges of the new code (G3Y-01 to G3Y-10:
2 P1, 5 P2, 3 P3), none of them a wrong number for a tool of practice. All are resolved, eight
further probes decided the cases that needed the program. State after the sixth round: 1336
tests passed, 8 skipped; 59 probes, 62 defaults; the comparison of the generation unchanged
(533 / 364 / 169 / 0). Section "Second verification review (2026-10-03) of the fifth round, and
sixth round" below.

No citation of `generation.py` and `trochoid.py` was wrong except one page number (G3A-07); no formula
body was wrong: reviewer A read every equation on the rendered pages and his three recomputations agree
with gearcore to 4e-16 relative (undercut intersection, fzg_c pinion), 1.2e-16 (d_Fa of the kst-C wheel)
and 0 (ISO/TR example, both forms of d_Ff). Reviewer B reproduced every count and every contour
deviation to 1e-9 µm, confirmed the transverse allowance of STplus on all helical runs and the
numerical junction of the STplus form circles, and found the justification of the allowed accuracy
sound. The defects were a thin band below the undercut limit in which the numerical intersection was
not found (P0), tool feasibility checked on one path only, a raise where the norm admits the value
(dedendum), untyped errors, one wrong page, one wrong old-norm symbol, an unreproducible number in
three documents, an empty plot in the notebook, a stale fixture record, and rows of the comparison that
echo inputs.

## P0

| ID | Finding (short) | Resolution |
|---|---|---|
| G3A-01 | In a band of about 1e-3 below x_Emin (z 12 … 30, β 0 … 20°) `compute_generation` raised `GeometryInfeasibleError` ("the fillet does not cut into the involute" / "ends below the base circle" with a radius above r_b): the base-circle test used (1 + EPS), `GAP_TOLERANCE` = 1e-11 rad exceeded the physical cut, and the shipped hypothesis test skipped exactly this band | `trochoid.root_form_diameter_by_intersection`: a radius within EPS of the base circle counts as on it; `GAP_TOLERANCE` = 1e-13 rad (the rounding noise of the gap is 1e-16); the caller passes `undercut_expected` (x_E < x_Emin by Eq. (135)): where no crossing can be resolved the root form circle is the base circle and the fillet is cut where it reaches it, continuous with Eq. (128) at the limit; without that knowledge a fillet ending off the involute is a `SolverError` (inconsistent psi_b, the suspicion of reviewer A); the tangent end is recognised by `END_TOLERANCE`. Tests: five (z, β) pairs at six offsets down to −1e-9, hypothesis over the band, continuity at the limit, the contour of such a gear |

## P1

| ID | Finding (short) | Resolution |
|---|---|---|
| G3A-02 | A tip circle at the pointed tooth (Eq. (40) folds −EPS ≤ ψ_y < 0 to zero) escaped as a pydantic `ValidationError` of `GearGeneration` | `GeometryInfeasibleError` "pointed at the tip circle" before the contract; tested at d_pointed × (1, 1 + 1e-13, 1 + 2e-12, 1.01) |
| G3A-03 | Tool feasibility (roundings overlap, pointed tool tooth) was checked in `trochoid.tip_rounding` only, i.e. only for undercut gears; h_aP0* = 2.5 or ρ* = 0.6 with h* 1.25 generated silently on the other path | `_gear_generation` builds the tip rounding on every path; the message names both the addendum and the rounding and the height at which the tool tooth is pointed; tested for z 12, 20, 200 with four tools |
| G3A-04 | `dedendum` raised for d_fE ≥ d (x_E m_n ≥ h_aP0); Eq. (37) prints an absolute value and admits it, the gear is realisable | `dedendum` is signed like `addendum`; the `@eq` notes and the registry notes of h, h_a, h_f say that the first form is taken without its absolute value (G3A-09) |
| G3A-05 | ρ_aP0 = 0 (contract admits it) crashed the undercut path with `SolverError` (degenerate ellipse) | the pitch point position of the ellipse is evaluated in closed form, c = ξ − η cos β cot θ, whose slope does not depend on ρ; a sharp corner rolls as the limit ρ → 0 (`TipRounding.axis_ratio`); tested ρ* = 0, 1e-6, 1e-4, 1e-2 |
| G3A-06 | `tip_rounding` rejected ρ_aP0 > h_aP0 although the straight flank exists (h_aP0 > ρ (1 − sin α_n)); the two paths disagreed for h* 0.5 … 0.79 with ρ* 0.6 | the check is the existence of the straight flank, the same condition as `tool_tip_form_height`; tested h* 0.5, 0.7, 0.79 on both paths |
| G3A-07 | `generated_point` cited FVA 604 I Abbildung 4.7 on p. 29; it is on p. 30 | page corrected; `traceability.md` regenerated |
| G3B-01 | Notebook 03: the deviation plots were empty (NaN from the duplicated junction points, G3B-08) and the cell duplicated the distance formula of `contour` | `contour.distances` (per-point normal distances, µm) is public and the notebook plots it; junction points are no longer doubled |
| G3B-02 | A `.ste` tool with `KANTENBRECHWINKEL`, `FUSSHOEHENFAKTOR` ≤ 1,3 and no `FUSSFORMHOEHENFAKTOR` got the importer's default h_FfP0* = 1,3 and was then refused by the generation (dedendum ≤ root form height) | the importer raises the dedendum to the default as STplus does (kst-E lists h_fP0* = 1,3 for an input of 1,0) and records it in its notes; the generation admits a dedendum equal to the root form height (GEN-11) |

## P2

| ID | Finding (short) | Resolution |
|---|---|---|
| G3A-08 | Registry: DIN 3960 p. 14 writes x_Ee (index e as in A_se) for the upper limit, not x_Es | `replaced` entry corrected; `quantities.md` regenerated; test of the changed symbols updated |
| G3A-09 | Eq. (35)–(37) are printed with absolute values; the notes did not say that the absolute value is dropped | notes of the three functions and of the registry entries say "first form without the absolute value (signed)" |
| G3A-10 | `fillet_point(rounding, "a")` raised numpy's `ValueError`, NaN a misleading `InputRangeError` | `_parameter` validates the parameter (float, int, numeric array; finite; range) and raises `InputRangeError` naming it |
| G3A-11 | DIN 3960 (A.3.03) uses the x_E of the tool carrying the edge break flank (x_EV for q > 0); nowhere stated | docstring of `edge_break_transverse_tooth_thickness` |
| G3A-12 | h_FfP0 given without an angle, straight flank ending below the tip circle: `InputRangeError` although the input is valid (the tool root rounding ρ_fP0 is unmodelled) | `NotSupportedError`; `extension_points.md` row "Tool root rounding"; GEN-10 |
| G3B-03 | `meta.json` of helix20_z25_65 recorded the notes of the previous importer (no default note) | `scripts/stplus_oracle.py refresh-import` run; `test_g3b03_typed_import_of_the_fixture_is_current` compares every record with the importer |
| G3B-04 | `tooth_contour(pair, generation, role)`: the `pair` argument was dead (`generation.inputs` overrode it) | signature `tooth_contour(generation, role, *, points)`; a non-`GenerationResult` is an `InputRangeError` |
| G3B-05 | `tool_from_section(section, notes=None)` applied its defaults silently when no list was passed | `notes` is required |
| G3B-06 | "46 µm" for the circle approximation of FVA 604 I quoted in three documents and the notebook, not reproducible (the probe had used a third variant) | `scripts/circle_approximation_fva604.py` implements the approximation of FVA 604 I p. 29 (constant radius ρ/cos β about the rounding centre): 176 µm at β = 30°, 96 µm at 20°, 26,5 µm at 15° against the STplus exports, the ellipse 0,6 µm; documents and notebook quote these |
| G3B-07 | s_ns/s_ni (`tooth_thickness_limit`) and x_EsV/x_EiV (`pre_machining_generating_profile_shift_coefficient`) had no registry entry | entries `normal_tooth_thickness_limit` and `pre_machining_generating_profile_shift_coefficient` (108 quantities, 6 pending) |
| G3B-15 | Mutation "tip arc at 0,5 d_Fa instead of 0,5 d_a" passed all tests | `test_g3b15_tip_arc_of_a_chamfered_gear_lies_on_the_tip_circle` (kst-C wheel: every tip point at r_a, the flank from r_Fa to r_a) |
| GEN-06 (B) | `FORM_CIRCLE_ACCURACY_MM` is measured, not derived; its justification | sound per reviewer B (junction vertex, 0,23 µm / sin 4,14° = 6,37 µm reproduced); kept as GEN-06, now reported as a separate part of every row (G3B-09) |

## P3

| ID | Finding (short) | Resolution |
|---|---|---|
| G3A-13 | Messages: numpy repr in an error, a radius "below the base circle" that was above it, the overlap message blaming ρ alone | plain floats, corrected wording, both causes named |
| G3B-08 | Every junction point of `ToothContour.points` appeared twice (zero-length segments, hidden by a guard in `compare`) | `_joined` drops a point that repeats the last placed point; tested on the polyline and the gear polygon |
| G3B-09 | The allowance for the STplus form circles was folded into `arithmetic_tolerance` | `ParityRow.solver_tolerance` (fourth part, zero for closed formulas); `detection_limits` includes it |
| G3B-10 | Roadmap: "22 traced functions" of `generation.py` (there are 20) | corrected |
| G3B-11 | GEN-09: "spur: 0,1 µm" (spur fillets with undercut reach 0,33 µm) | corrected: 0,6 µm helical, 0,33 µm spur with undercut, 0,09 µm spur without |
| G3B-12 | Rows whose tolerance covers the value (c_F of a few µm) and rows echoing inputs (d_Fa = d_a) counted as identical | d_Fa is compared only where the tool has an edge break flank (537 rows); `parity.rows_without_evidence` names the four case/field pairs (seven rows: listing and interface) that can never fail (c_F of small_z8, neg_shift and undercut_z12, h_K = 0 of helix20); pinned |
| G3B-13 | Two STplus tip-circle points of an unchamfered gear fell into `tip` or `involute` by the seventh printed digit | `REGION_TOLERANCE` = 1e-6 relative; region counts pinned against the reference radii (G3B-16) |
| G3B-14 | Untyped errors: `tooth_contour` with a `PairInput`, `compare` with strings, `chamfer_flank` with r_a < r_Fa, a `ToothContour` whose segments exceed its points | all four typed (`InputRangeError`, `ValueError` of the contract validator) |
| G3B-16 | Mutation "fillet region widened by 2e-3" passed all tests | `test_g3b16_region_counts_follow_the_reference_radii` |

## Verification review of the fixes (2026-09-30) and second round (2026-10-01)

A third read-only agent re-ran the original repros of all 29 findings, the 22 mutations of reviewer
B and 24 new mutations of the fixed code, and reproduced the numbers of the documents (`git status`
identical before and after; STplus not run).

**Verdict of the reviewer.** The 29 findings are resolved as claimed, with two qualifications:
G3B-05 and G3B-08 in part (G3V-02, G3V-01). The P0 fix holds on 111 780 direct calls of
`root_form_diameter_by_intersection` (z 8 … 80, β −40 … 40°, ρ* 0,05 … 0,4, h* 1,0 … 1,4, 40
offsets −1e-10 … −5e-3 below x_Emin: no error, d_Ff ≥ d_b, monotone in the offset, continuous with
Eq. (128) at the limit) and on 1164 generations. All 22 mutations of reviewer B are detected; of
the 24 new ones 19 were detected, 2 are equivalent and 3 were not detected (G3V-06 to G3V-08).
Every number of the documents was reproduced except two (G3V-03 d, g).

| ID | Sev. | Finding (short) | Resolution (second round) |
|---|---|---|---|
| G3V-01 | P2 | In the band below x_Emin where the root form circle is the base circle, the fillet ended at r_b (1 − 0,5 EPS) and the involute started at r_b: a segment of 5e-13 r_b in every such contour (9,4e-12 mm at m_n 2, 4,7e-10 mm at m_n 100), above the absolute tolerance of `_joined` | `root_form_diameter_by_intersection` returns the parameter at which the fillet reaches the base circle itself (the band only keeps Eq. (12) defined at the root of the solver); `contour._joined` drops a repeated point by `JOIN_TOLERANCE` = 1e-10 relative to its radius. Sweep of 4986 contours in the band (z 8 … 40, since z 60 and 80 need a profile shift outside the contract; β 0/15/−30°, three roundings, three addenda, m_n 0,5/2/100, nine offsets): no step of the contour or of the gear polygon below 1e-9 d_b. Tests: `test_g3a01_generation_just_below_the_undercut_limit` (steps), `test_g3v01_no_zero_length_segment_at_any_size` |
| G3V-02 | P3 | Untyped errors: `fillet_curve(rounding, "a")` (numpy `ValueError`), `gear_polygon(pair)` and `tool_from_section(section, None)` / `(section, ())` (`AttributeError`) | `InputRangeError` in all three (end parameter and number of points validated; a `ToothContour` required; `notes` must be a list); tested |
| G3V-03 | P3 | Documents against code: (a) ADR-113 §5 "input error" for what is `NotSupportedError`; (b) CHANGELOG "106 quantities"; (c) "six modules of later increments" (four); (d) "four rows" without evidence (four case/field pairs, seven rows); (e) GEN-11 "does not exceed" (equal is admitted); (f) the root circle of the FVA circle approximation moves towards the gear centre, not outwards; (g) "0,05 µm (tip)" is a stale bound (measured 0,006 µm) | all seven corrected; the tip bound of `test_contour` and of the documents is 0,01 µm |
| G3V-04 | P3 | The importer noted "FUSSHOEHENFAKTOR = 1.3 raised to h_FfP0* = 1.3" for an equal value | the dedendum is raised, and the note written, only below the default; `test_g3v04_an_equal_dedendum_is_not_reported_as_raised` |
| G3V-05 | P3 (info) | With d_Ff = d_b (at x_Emin or in the band below it) a mate whose tip reaches the base circle triggers the pair module's "active profile starts on the base circle"; physically right, but the advice of the message cannot be followed in the generation | known limit GEN-12 (accepted) |
| G3V-06 | P2 | Mutation `GAP_TOLERANCE` 1e-13 → 1e-6 passed all tests: no test pinned a resolved crossing in the shallow band | `test_g3v06_shallow_crossings_are_resolved_not_folded` (z 12, 20, 40 at x_Emin − 0,005: d_Ff − d_b = 0,018 86 / 0,011 34 / 0,005 677 µm, a cut of 1,5e-9 / 3,3e-10 / 4,2e-11 rad half-way between base circle and crossing, the fillet end four times as far above the base circle); the generation test now asserts d_Ff = d_b down to −1e-4 and d_Ff > d_b from −1e-3 |
| G3V-07 | P3 | Mutation "`distances` in mm" passed: `distances` was asserted against zero only | `test_g3v07_distances_are_micrometres`: a radial shift of 2 µm gives 2 µm sin α_y on the involute, and maximum and rms equal those of `compare` (also on the STplus export of fzg_c) |
| G3V-08 | P3 | Mutation `END_TOLERANCE` 1e-9 → 1e-3 passed: the `SolverError` "ends off the involute" was exercised with ψ_b ± 0,01 only | ψ_b off by 1e-4, 1e-6, 1e-8 raises in both directions, ψ_b − 1e-11 is the tangent end |

Tests that passed for less than they name (reviewer's list) were tightened with these: the band
of `test_g3a01_generation_just_below_the_undercut_limit` is d_b … d_b (1 + 1e-5) with equality in
the fallback band (the mutation "`undercut_expected` ignored" now fails it, too);
`test_g3b03_typed_import_of_the_fixture_is_current` compares `unmapped_keys` as well. Left as
they are: `test_g3b16` (pins the consistency of `compare` with `REGION_TOLERANCE`; its value is
pinned by the tip bound of `test_contour`) and `test_g3a13` (pins the repr only).

**Check of the second round (2026-10-01, by the implementer, not by a reviewer).** The repros of
G3V-01, -02, -04 re-run as tests and as the sweep above; the three undetected mutations and two
more applied at run time (no file changed), against the seven test files of the reviewer:
`GAP_TOLERANCE` → 1e-6 fails 14 or 15 tests (one of them a hypothesis example), `distances` in mm
1, `END_TOLERANCE` → 1e-3 1, `undercut_expected` ignored 20 (before: 1; 21 with the wrapper used
here, which also swallowed a wrong type of the flag), `JOIN_TOLERANCE` → 0 28. 1111 tests passed,
8 skipped; ruff, format, mypy --strict clean. Found on the way: notebook 03 had seven lint findings
(three unused imports, three `zip` without `strict`, one line too long) that the CI lint of the
notebooks would have rejected; corrected in the notebook.

## Second verification review (2026-10-01) and third round

A further read-only agent re-ran the repros of G3V-01 to G3V-08 against the second round, swept
11 184 contours in the band (z 8 … 40, β 0/15/−30/40°, ρ* 0 … 0,38, h* 1,0 … 1,4, m_n 0,05/2/100,
ten offsets, 8 and 200 points per element) and 360 at and above the limit, recomputed the pinned
crossings of `test_g3v06` in 50-digit arithmetic with code of his own, applied 51 mutations in
memory and re-ran the stated state (`git status` and the hashes of all changed files identical
before and after; STplus not run).

**Verdict of the reviewer.** G3V-01 to G3V-08 are resolved in code and documents: no step below
1e-9 d_b in any contour or polygon of the sweep (smallest 3,75e-7 d_b), the fillet end and the
involute start coincide to 9,5e-14 r_b, θ reproduces d_Ff to 4,3e-16; the pins of `test_g3v06`
agree with the independent values 0,018 858 1 / 0,011 336 6 / 0,005 676 9 µm; the contour
deviations are 0,586 6 / 0,241 2 / 0,006 22 µm; 537 / 368 / 169, 108 / 6 and 1111 / 8 reproduced.
Three qualifications, all taken up below: the suite was not deterministic (G3W-01), a wrong d_Ff
came back silently from the direct API for a wrong flag (G3W-02), two mutation counts of this
report were off (G3W-08). Of his 46 own mutations 29 were detected, 4 are equivalent and 13 were
not detected.

| ID | Sev. | Finding (short) | Resolution (third round) |
|---|---|---|---|
| G3W-01 | P2 | `test_trochoid.test_undercut_limit_of_the_norm_agrees_with_the_fillet` failed in 3 of 180 runs without any mutation: its strategy box (ρ* ≤ 0,4, h* ≤ 1,4) holds tools whose tip roundings overlap (ρ* 0,4 above h* 1,388), which `tip_rounding` rejects outside the test's `try`. Present since the increment was written | the test assumes a feasible tool (h* < ρ* + (π/4 − ρ*/cos α_n)/tan α_n); the drawn example is pinned as a rejected tool (`test_g3w01`). Repetitions without a failure: see the check below |
| G3W-02 | P2 | `root_form_diameter_by_intersection(…, undercut_expected=True)` for a gear that is not undercut returned the base circle silently: z 60, x 0 (fillet starting above the base circle: 112,763 instead of 116,272), z 20, x 0,2 (37,588 instead of 37,734), and for ψ_b off by 1e-2 in the band. Not reachable through `compute_generation` | the expectation is checked against the fillet: the fillet of an undercut gear ends on the mirrored branch of the involute beyond T, 2 inv α from the flank, within `END_TOLERANCE`; else `SolverError` "undercut is expected, but …". A gear free of undercut passes that check only where its root form circle lies within 1e-6 of the base circle. The 111 780 direct calls of the first verification review and both band sweeps give the same results as before (83 241 on the base circle, no error). Tests: `test_g3w02_…` (three gears, ψ_b off by 1e-2 … 1e-8, ψ_b − 1e-11 accepted) |
| G3W-03 | P3 | 36 untyped errors on public functions for wrong argument types: `rounding` None / str / `PairInput` (`AttributeError`), `pitch_point_position` and `generated_point` with None, str, complex, string arrays, arrays of different length (`TypeError`, `ValueError`), `compare` / `distances` with a ragged list, `tool_from_section(None, [])`; complex arrays accepted with the imaginary part dropped | one validator for numbers and real arrays (`trochoid._real`: finite, real dtype), a shape check, a `TipRounding` check, a `SteSection` check, real dtype and ragged lists in `contour._reference`: `InputRangeError` throughout. The reviewer's script now shows 4 untyped results (before: 36), all four for objects built by hand past their contract (`TipRounding` with a field None, `ToothContour.model_copy(update={"points": None})`), accepted. `test_g3w03_wrong_argument_types_are_typed_errors` |
| G3W-04 | P3 | `fillet_curve` rejected a numpy integer for `n` (its neighbours accept one), carried a dead `bool` clause and repeated the range check of `_parameter` without its EPS slack | `integer_input` as elsewhere; the range of the end is checked once, by `fillet_point`. `test_g3w04` |
| G3W-05 | P3 | `JOIN_TOLERANCE` was pinned from below only: 1e-6, 1e-8, 1e-3, an absolute tolerance and "every first point dropped" passed all tests | `test_g3w05`: a first point 1e-11 of the radius away is dropped, one 1e-9 away is kept, at radius 1 and 1000; all seven mutations fail now |
| G3W-06 | P2 | Full-radius tool (ρ* = 0,471 91 at h* 1,25): `gear_polygon` raised "the fillets of neighbouring teeth overlap" exactly at the full radius (the check had no band) and crowded its eight arc points into a root arc of 2,5e-9 mm just below it (179 steps below 1e-9 d_b, exact duplicates at −1e-14). Older than the second round | the root arc is drawn with its points only where they lie more than `JOIN_TOLERANCE` apart; a shorter arc is one segment; where the fillets meet (within `JOIN_TOLERANCE`) the shared point is placed once; overlap is an error beyond that band. `test_g3w06` (ρ* full, −1e-14, −1e-9, −1e-6, −0,2): point counts and no step below `JOIN_TOLERANCE` r_f, closing step included |
| G3W-07 | P3 | GEN-12: the band width does not depend on the tool or the module but on z and β (1,1e-4 at z 8 … 1,5e-3 at z 80), and the pair module also raises up to 4,5e-6 above x_Emin | GEN-12 rewritten with these numbers |
| G3W-08 | P3 | This report: `GAP_TOLERANCE` → 1e-6 fails 14 or 15 tests, not always 15; "`undercut_expected` ignored" 20, the 21st an artefact of the wrapper; the sweep "z 8 … 80" yields contours for z ≤ 40; "a cut of the order of 1e-9 rad"; `JOIN_TOLERANCE` docstring "sampled points orders above" | corrected above and in the docstring (sampled points are never compared, whatever their spacing) |

Tests of the second round that passed for less than they name (reviewer's list): the join
tolerance of `test_g3v01` is now pinned by `test_g3w05`; `test_g3b05` also rejects a `deque`
(the list requirement was pinned against missing `append` only); the "independent look" of
`test_g3v06` uses gearcore's own `fillet_point` — its pins are confirmed by the reviewer's
independent computation, the test is left as it is. Not followed: a `list` subclass whose `append`
does nothing is accepted as `notes` (deliberate sabotage of the record, not an input error).

**Check of the third round (2026-10-01, by the implementer with the reviewer's scripts, not by a
reviewer).** The reviewer's repro scripts re-run unchanged: `g3w02_check.py` (typed errors with and
without the flag), `attack_types.py` (36 → 4 untyped), `sweep_band.py` (11 184 contours, on the
base circle 6651, zero-length 0, identical to his run), the first review's `g3a01_sweep.py`
(111 780 calls, 13 959 crossings, 83 241 on the base circle, 0 problems, identical). 23 mutations
in memory against the seven test files (521 passed unmutated): the eight non-equivalent ones of the
reviewer that concern the join tolerance and the `notes` check, and 15 of the third-round code
(mirrored-branch check removed / against the flank / tolerance 1e-3, the type and shape checks, the
three branches of the root arc, the dedendum comparison): all 23 fail at least one test. Not
re-run: five variations of a tolerance inside the window the tests pin (`REGION_TOLERANCE` 1e-5,
`GAP_TOLERANCE` 1e-12, `END_TOLERANCE` 3e-9 and 3e-11, solver xtol 1e-12), which the reviewer
judged as not mattering. The formerly flaky test (G3W-01; before: 3 failures in 180 runs): 136
separate pytest runs (dev and ci profile alternating; a planned 200 were cut by a time limit) and
400 calls in one process with fresh draws, none failed; on a grid of the strategy box (140 751
tools) `tip_rounding` rejects 44, none of which the test's assumption admits. 1125 tests passed, 8
skipped; ruff, format, mypy --strict clean; 5 notebooks executed.

## Review by the user (2026-10-03): study of the STplus manual and fourth round (ADR-114)

The user discussed the increment with his supervisor at the FZG and came back with two points.
First, STplus is older than the norm and has always computed the common tooth depth with the tip
form circles where a tip chamfer is given: ADR-112 is confirmed. Second, STplus documents in
chapters of its own what it presets where an input is missing or incomplete (above all §4.17), and
some of these presets carry meaning: a dedendum factor of the tool without a root form height
factor, for example, has no effect. He asked whether the complete manual had been studied for the
increments. It had not: §3.2, §4.2 (p. 15 to 25), p. 183 to 188, §6.2 and §6.4.2 had been read,
and rules of the program had been drawn from single listings.

**What was done (implementer, 2026-10-03).** Manual chapters 1 to 3, 4.1, 4.2, 4.14 to 4.17, 5 to
8 and 10 read; p. 186, p. 224 to 228 and the listing of example 1 (p. 254 to 259) read on the
rendered pages; 62 runs of STplus 11.1F with incomplete and contradicting inputs, 34 of them kept
as probes (`data/stplus_program/probes`, 39 in all). The findings were put to the user as three
questions; his decisions: the `.ste` importer reads a file as STplus computes it; a tip circle
above the root line of the tool is cut, with a warning, as the program does; where the manual and
the program disagree (known at the FZG), the program is followed and both are documented.

| ID | Sev. | Finding | Resolution (fourth round) |
|---|---|---|---|
| G3U-01 | P1 | A rule drawn from the kst-E listing was wrong: "STplus raises a tool dedendum whose root line would cut the tip circle" (input h_fP0* = 1,0, listing 1,300). The program presets root form height and dedendum with 1,3 each and sets a dedendum below the root form height equal to it; a tip circle above the root line of the tool is cut. `compute_generation` left such a tip circle untouched and warned (GEN-05) | `compute_generation` cuts the tip circle to d + 2 (x_E m_n + h_fP0), warning `tip_circle_cut_by_tool` (replaces `tool_root_line_below_tip_circle`); `GearGeneration.tip_diameter_mm` is the generated diameter and the pair geometry is computed with it. Probes `tip_circle_cut_by_tool`, `…_then_edge_break`, `…_helical`, `…_with_chamfer`: d_a of the listings reproduced |
| G3U-02 | P1 | A tool that gives a root form height without an edge break angle was taken as a tool with a root rounding gearcore cannot model (`NotSupportedError`, GEN-10) or reported (`edge_break_angle_not_given`). STplus replaces a tool root rounding by an edge break flank between root form height and dedendum and presets its angle with α_n0 + 10° (manual p. 186) | `stplus_tool_factors`: where the dedendum lies above the root form height, the angle is the given one, else α_n0 + 10°; a dedendum equal to the root form height is a sharp corner without flank (`_has_edge_break_flank`, warning `edge_break_angle_without_flank` where an angle is given nevertheless). DIN 3960 A.3.1 with the preset angle reproduces the probe `tool_root_both_heights` (46,3069 / 0,0466 / 0,4069 against 46,307 / 0,047 / 0,407) and example 1 of the manual (d_Fa 144,535 against 144,536 printed). The core keeps GEN-10 for a contract without the angle |
| G3U-03 | P1 | A file without `SCHRAEGUNGSWINKEL` was imported as a spur pair (zero with a note, ADR-111). STplus computes the angle from the centre distance and the sum of the profile shift coefficients (manual p. 16) or rejects the input | `stplus_helix_angle_deg` solves the centre distance equation for β (12,1322° where STplus, stopping at 1e-6, lists 12,1313°); without a centre distance `ParseError`. Probes `helix_angle_from_centre_distance`, `no_helix_angle_no_centre_distance` |
| G3U-04 | P2 | Incomplete tools were rejected (no tool block, no addendum, no tip rounding) or completed with one preset only (h_FfP0* = 1,3 where an angle was given); heights beyond the limits of STplus were passed on as written | `stplus_tool_factors` completes and limits a tool as the program does (presets 1,25 / 0,25 / 1,3 / 1,3, four limits, factor before absolute value); every step is a note. The factors of all probes and of the 18 cases equal the listed ones in three decimals. The limits of addendum, root form height and dedendum are fitted to listings, not derived (GEN-11) |
| G3U-05 | P2 | The rule of the residual thickness of a chamfer given by h_K was taken in the transverse section, without the floor 0,2 s_an and without the limit of h_K, and the importer did not apply it (GEN-07; open suspicion of reviewer B) | `stplus_residual_tip_thickness` works in the normal section (s_an − 1,4 h_K holds in five decimals of the interface file at β = 25°), floor and limit 0,20 m_n added, the controls `TANG_BETRAG_ZU_H_KGF` and `MAX_KOPFKANTENBRUCH` honoured; the importer sets s_aK and records it. Probes `tip_chamfer_default`, `…_tangential_given`, `…_limits`, `…_helical` |
| G3U-06 | P2 | A file without `KOPFKREISDM` was rejected. STplus computes d_a = d + 2 m_n (1 + x) without tip alteration and may shorten it afterwards | the importer sets that diameter with a note and marks it (`SteImport.preset_tip_diameters`); the comparison takes d_a of such a case from the output of STplus |
| G3U-07 | P3 | `PR.VERSCH.SUMME` together with one coefficient was `NotSupportedError`; a lone upper span allowance was not completed | the other coefficient follows from the sum; A_Wi = A_We (manual p. 20); a lower allowance alone is `ParseError`. Probes `profile_shift_sum`, `upper_span_allowance_only` |
| G3U-08 | P3 | Eight of the fourteen records of the tool databases were kept as "no contract" (six contradict themselves, two have no tip rounding) | read as STplus computes with them: twelve are tool contracts; two (α_n0 = 16°) exceed the bound 2,5 of the contract after the reduction and say so |
| G3U-09 | P3 | `defaults.yaml` did not cover the controls and limits of §4.17.2 (p. 223 to 230); the cause of the accuracy of the STplus form circles (GEN-06) was not documented | 58 defaults (24 before). The iteration limit of the form circles is documented (tooth thickness arcs equal within m_n / 10 000, p. 227); at the printed d_Ff of the four undercut pinions the arcs differ by 1,0 to 4,0 times that limit, which explains the order of `FORM_CIRCLE_ACCURACY_MM`, not its value |
| G3U-10 | P2 | Manual and program disagree in four places (preset of h_Ff0* 1,1 against 1,300; h_f0 < h_Ff0 → h_f0max against h_f0 = h_Ff0; largest chamfer factor 0,02 against 0,20 m_n; the presets of the controls s_a0* and e_Ff0* against the observed 0,120 and 0,110) | user decision: the program is followed; both are recorded in `defaults.yaml`, in ADR-114 and in `norm_map.md` ("Anleitung und Programm im Widerspruch") |

Not applied by the importer and stated as limits: the allowances STplus presets (series c25, js7)
need DIN 3967 and DIN 3964 (increment 5), so a pair imported from a file without allowances is
generated with the nominal tooth thickness (GEN-14); a tooth the edge break flanks make pointed
below the tip circle is a typed error where STplus cuts the tip (GEN-13); controls that move the
limits of the tool, a root form height beyond its limit together with a larger dedendum and tools
dimensioned in ways the importer does not translate are typed errors (GEN-15).

**State after the fourth round.** 1231 tests passed, 8 skipped (four modules of later increments, four supplied listings without interface file); ruff and format (package, tests, scripts, notebooks) and mypy --strict clean; 5 notebooks executed; 39 probes, 58 defaults, 18 STplus cases. The comparison with STplus is unchanged: 537
comparisons of the generation, 368 identical, 169 within the accuracy of STplus, none different.
New test module `tests/test_stplus_reading.py`; notebook 03 gained a section on how STplus reads
an incomplete input (26 cells).

## Verification review of the fourth round (2026-10-03) and fifth round

A read-only agent checked the fourth round (`git status` and the hashes of all changed files
identical before and after; STplus not run; report in the session scratchpad, `gate3_v4`). It
re-implemented the rules of STplus from the raw `input.ste` files and compared them with the raw
listings (110 tools and 110 tip circles in 55 listings), read the manual sentences of the new
defaults on the rendered pages, recomputed the quoted numbers with formulas of its own, swept
the new functions with wrong arguments (2166 calls), generated 1413 random pairs with and
without a tip cut, audited every difference between file and `PairInput` for a note (542
differences) and applied 75 mutations in memory.

**Verdict of the reviewer.** The rules agree with every listing in the repository: no tool
factor, no tip circle, no chamfer and no residual thickness contradicts them, the three fitted
constants are pinned by the listings to 0,11985 … 0,12011, 0,10985 … 0,11002 and 0,0595 … 0,0610,
every manual sentence is verbatim and on the page named, and nothing is applied without a note.
G3U-01, -03, -07, -08, -09, -10 resolved; G3U-02, -04, -05, -06 resolved in part. What was wrong
lay around the rules: 1 P0, 4 P1, 5 P2 and 2 P3 bundles (G3X-01 to G3X-12). Of the 75 mutations
60 were detected, 1 is equivalent and 14 were not detected.

Twelve further probes were run for the cases the reviewer could not judge without the program
(51 probes in all); each finding below names the probe that decided it.

| ID | Sev. | Finding (short) | Resolution (fifth round) |
|---|---|---|---|
| G3X-01 | P0 | `contour.tooth_contour` drew the edge break involute of the tool for a tool that states an angle but has no flank (dedendum = root form height, e.g. `KANTENBRECHWINKEL` alone) where the gear has a given chamfer: tip land 1,42 mm at s_aK = 0,218 mm and s_at = 0,498 mm. Reachable from a `.ste` file; 204 of 2826 gears of the random sweep | `GearGeneration.tool_edge_break_angle_deg` is the angle of the flank the tool has, `None` for such a tool; contour and comparison take the chamfer as the given one. The tip land equals the chord of s_aK, the contour is identical to that of the tool without angle, and without s_aK the contour asks for the shape (`test_g3x01`). The comparison loses four rows of helix20_z25_65 that echoed the input h_K = 0: 533 comparisons, 364 identical, 169 within the accuracy of STplus |
| G3X-02 | P1 | Raw `ZeroDivisionError` for `WKZ_EINGRIFFSWINKEL = 0`, `WKZ_NORMALMODUL = 0`, `EINGRIFFSWINKEL = 0` or `NORMALMODUL = 0` with a tool block, and from the limit functions at α = 0 | module and angle are checked before a rule divides by them: `ParseError` from a file, `InputRangeError` from the functions (`test_g3x02`) |
| G3X-03 | P1 | `stplus_tool_factors` passed NaN and ±inf through and raised `TypeError` for strings, lists, complex numbers (37 untyped errors and 24 non-finite results in 2166 calls) | every given value is a finite number or an `InputRangeError`, also the name and the range of the edge break angle; own sweep of all new functions and of a file with every value replaced: 937 calls, 841 typed errors, 96 finite results, none untyped (`test_g3x03`; one non-finite result of `stplus_max_tool_dedendum_factor` at 1e308 found by that sweep and closed) |
| G3X-04 | P1 | A preset was never limited although the stated rule limits it: the default hob at α_n = 28° kept ρ_aP0* = 0,25 beyond the full radius 0,201 (import "ok", generation infeasible); `KOPFHOEHENFAKTOR = 2.1` without rounding gave 1,993 / 0,25. No probe covered a preset beyond a limit | probes `default_hob_at_twenty_eight_degrees` (0,201), `default_hob_at_thirty_degrees` (0,110 and 1,265 / 1,265), `tool_addendum_limited_without_tip_rounding` (1,993 / 0,086): STplus limits presets as given values. `stplus_tool_factors` does the same and says so; the generation of both hobs is feasible (`test_g3x04`) |
| G3X-05 | P1 | A file without `KOPFKREISDM` got the preset tip circle and the note "the default of STplus" although it defined the tip circle by another key (`K_HOEHENF_VERZ_BEZ_PR`, `KOPFSPIELFAKTOR`, `DA_NACH_DIN3960`, `DA_DURCH_WKZ`, `BEZ_KOPFDICKE`; manual Bild 4.12) | such a file is `NotSupportedError` (`io.ste.TIP_CIRCLE_KEYS`; "nein" and the placeholder define nothing; with `KOPFKREISDM` of both gears the key stays in `unmapped_keys`). Probes `tip_circle_from_reference_profile_addendum` (46,000 / 84,400 and a tool dedendum of 1,430: the key moves more than the tip circle) and `tip_circle_per_din3960` (k m_n = −0,126 mm). GEN-15, extension point (`test_g3x05`) |
| G3X-06 | P2 | Controls: a second value was read as that of gear 2 (the manual prints `= % (%)`); `MAX_KOPFKANTENBRUCH` was honoured without probe and test; no note said that a control was used; other controls were dropped without a trace (`ABSCHALTEN_KORRGLIED = 1` switches the tool tip rounding to a circle) | probes `tip_chamfer_tangential_two_values` (1.0 0.5 → factor 1,0 for both gears), `tip_chamfer_limit_lowered` (0.1 0.4 → both limited to 0,10 m_n), `tip_chamfer_limit_raised`: a control is one value for the stage, `MAX_KOPFKANTENBRUCH` is the factor of the module. `_control` takes the first value, records its use and a second value; controls not evaluated are named in a note; `ABSCHALTEN_KORRGLIED = 1` is `NotSupportedError`; the rule functions keep the ranges of the manual (`test_g3x06`) |
| G3X-07 | P2 | `KANTENBRECHWINKEL = 90` was rejected although manual p. 186 documents it as the tool without edge break flank | probe `tool_edge_break_angle_ninety_degrees` (0,9 / 1,5 with 90° → 0,900 / 0,900, tip cut to 45,021): the dedendum is the root form height and no angle is passed on, with a note (`test_g3x07`) |
| G3X-08 | P2 | Mutations no test detected: contour, tooth depth, tip clearance of the wheel and normal tip thickness of a helical gear on the uncut circle; the importer storing the normal residual thickness in the transverse field; the notes of the edge break preset, of a reduced addendum and of a reduced tip rounding dropped; gear 2 without tool name getting the tool of gear 1; the band of the cut | `test_g3x08_…` (four tests: the cut helical probe against its interface file and its contour, the band of the cut from both sides, the transverse residual thickness at β = 25°, every correction of a tool in the notes) and the probe `tool_for_gear_one_only`. All 13 mutations fail now |
| G3X-09 | P2 | 29 of 39 probe records (`meta.json`) kept the import result of the importer before the fourth round; leftover texts in `extension_points.md`, three docstrings of `stplus_program.py`, a note of `defaults.yaml`, ADR-109, the changelog | `import_stplus_program.py refresh-import` and `test_g3x09_typed_import_of_the_probe_is_current` for all 51 probes; the texts corrected |
| G3X-10 | P2 | Without a profile angle the three limits were skipped without error and without note, against the docstring; it affected the two records of the global tool database | the rule requires the angle (`ParseError`); the two records are no contract by themselves and are completed with the data of the gear: `stplus_tool(name, normal_module_mm=…, normal_pressure_angle_deg=…, notes=…)` (hochverz2 at 25°: ρ_aP0* 0,135). Ten of fourteen records are contracts by themselves |
| G3X-11 | P3 | The `GeometryInfeasibleError` of `_gear_generation` for a tooth pointed by the edge break flanks was dead code: `residual_tip_thickness` raises first | the dead branch is removed; the message of `residual_tip_thickness` names the cause and the remedy and is pinned |
| G3X-12 | P3 | (a) ADR-114 quoted h_K 0,494 for 0,493; (b) 0,1099 for 0,1098 in `defaults.yaml`; (c) "STplus stops its iteration at 1e-6" stated as the cause of 12,1313°; (d) "the tool factors of every probe"; (e) the note of a preset tip circle did not say that STplus may shorten it; (f) the sum of the profile shift coefficients with centre distance and helix angle: wrong note, unprobed; (g) the floor 0,2 s_an evidenced at one thickness only; (h) notebook 03 listed three of four contradictions; (i) the chamfer functions accepted controls outside their ranges, no band at 45° | (a), (b), (d) corrected; (c) stated as not known (`defaults.yaml`, ADR-114, importer note, `norm_map.md`); (e) note extended, GEN-16; (f) probe `profile_shift_sum_with_centre_distance` (x_2 0,1298 from the centre distance, the sum is not used), the importer says so, the combination with gear 2 only is `NotSupportedError`; (g) probe `tip_chamfer_floor` (0,113 at 0,564); (h) fourth contradiction added; (i) ranges and band added (`test_g3x12_…`) |

**Check of the fifth round by the implementer (2026-10-03).** The reviewer's scripts re-run
against the corrected code: `repros.py` (G3X-01: tip land 0,217 921 = chord of s_aK; G3X-02 to -05
typed or as probed), `contour_bug.py` (tip land 0,600 000 for s_aK 0,6, deviation from the straight
chamfer 0,000 µm), `cut_sweep.py` (1413 pairs, 996 cut gears, no inconsistency), `silent_audit.py`
(60 files, 666 differences between file and `PairInput`, none without a note), `meta_check.py`
(18 + 51 records current). 39 mutations in memory against the whole suite: the 13 non-equivalent
ones the reviewer found undetected, adapted to the corrected source, and 26 of the code of this
round (limits on presets, the 90° rule, tip circle keys, controls, zero module and angle, guards,
the edge break angle of the result): all 39 fail at least one test.

**Not checked by the reviewer and still open.** How the documented limit of the helix angle
iteration (1e-6) enters the stop criterion of STplus (the residuals at 12,1313° are larger); that
the controls `VB_FUSS…` have no effect in situations other than the one probed; "1,0 to 4,0 times
m_n / 10 000" of GEN-06 was not recomputed by the reviewer; `parity.pair_data` takes a given
`KOPFKREISDM` as d_a also where STplus cut it (no fixture has a cut; the generation cuts it
itself).

**State after the fifth round.** 1310 tests passed, 8 skipped (four modules of later increments, four supplied listings without interface file); ruff and format (package, tests, scripts, notebooks) and mypy --strict clean; 5 notebooks executed; 51 probes, 60 defaults, 18 STplus cases; 533 comparisons of the generation, 364 identical, 169 within the accuracy of STplus, none different. The verification review of this round is the next section.

## Second verification review (2026-10-03) of the fifth round, and sixth round

A further read-only agent checked the fifth round (`git status` and the hashes of all changed
files identical before and after; STplus not run; report in the session scratchpad, `gate3_v5`).
It re-ran the repros of G3X-01 to G3X-12, recomputed the twelve new probes from the raw files
with code of its own (and all 134 tools of the 67 listings with tool rows), swept the corrected
contour over 3117 random pairs (6234 gears with and without flank, chamfer, cut, helix: no
inconsistency), attacked the new code with more than 12 000 calls and files (no untyped
exception) and applied 36 mutations of its own.

**Verdict of the reviewer.** G3X-01 (the P0), -02, -03, -04, -07 to -12 resolved; G3X-05 and
G3X-06 resolved in part. Every statement about the twelve probes in `defaults.yaml`, ADR-114,
`norm_map.md`, the known limits and this report is backed by the kept listings; the two new
manual quotes are verbatim; the counts of the fifth round are right except one (39 mutations, not
40; corrected above). New at the edges of the fifth-round code: G3Y-01 to G3Y-10 (2 P1, 5 P2,
3 P3 bundles). Of its 36 mutations 22 were detected, 2 are equivalent and 12 were not detected.

Eight further probes decided what needed the program (59 probes in all).

| ID | Sev. | Finding (short) | Resolution (sixth round) |
|---|---|---|---|
| G3Y-01 | P1 | A tip circle key was accepted beside `KOPFKREISDM` of both gears (only in `unmapped_keys`) although the kept listing shows that `K_HOEHENF_VERZ_BEZ_PR` moves the tool dedendum where it defines the tip circle; unprobed for all five keys | probe `tip_circle_given_with_other_definitions` (all five keys beside `KOPFKREISDM = 46.8 85.6`): the listing equals that of `tip_circle_cut_by_tool` in tip circles, tool factors, root circles, tip clearance and tip thickness. The keys have no effect there; the importer says so in a note (`test_g3y01`) |
| G3Y-02 | P1 | Just below the 90° rule the generation was numerically wrong: s_aK 0,36 µm low at 89,9999°, "pointed tooth" at 89,999999°, −83 450 mm at 89,99999999° (DIN 3960 (A.3.05) forms the difference of two involute functions next to 90°); band and range untested | probes: STplus computes a flank of 85° (`tool_edge_break_angle_eighty_five_degrees`) and aborts at 88° (`…_eighty_eight_degrees`). The importer refuses an angle above 85° and below 90° (`NotSupportedError`, `STPLUS_MAX_EDGE_BREAK_ANGLE_DEG`); the generation refuses a flank steeper than 89,9° (`InputRangeError`, `MAX_EDGE_BREAK_ANGLE_DEG`), up to which the residual thickness approaches its limit 0,06 m_n tan α_n d_a / d steadily (`test_g3y02_steep_edge_break_flanks`, which also pins the band of the 90° rule). At 85° gearcore reproduces d_a, d_Fa and h_K of STplus in five decimals; the residual thickness is 0,0200 against 0,0205 mm (GEN-06) |
| G3Y-03 | P2 | `pair._tip_form_diameters` still announced an edge break flank for any tool that states an angle | the predicate is one function, `rack.has_edge_break_flank`, used by generation and pair geometry; the warning `tip_form_diameter_not_generated` is raised for a tool with a flank and for an angle without the height at which a flank would start (`test_g3y03`) |
| G3Y-04 | P2 | The placeholder `%` was taken as a value: `MAX_KOPFKANTENBRUCH = %` was `ParseError`, `MIN_WKZ_ZAHNKOPFDICKE* = %` and `MASS_BZ0 = %` `NotSupportedError`, `KANTENBRECHWINKEL = %` `ParseError` | a key is given where it carries a value other than the placeholder (`io.ste._given`, manual §3.2); the first position of a tool key holds its value (`test_g3y04`, `test_g3y05_the_first_position…`) |
| G3Y-05 | P2 | Keys of a tool block the importer does not read, and further tokens of a line, vanished without a trace; `WERKZEUG_VORVERZ. = Ende Geometriedaten` was accepted | notes name the keys not read and further values; every token is a number or the placeholder (`ParseError`); a tool name that points to a block of the file structure or to a block without any tool key is `ParseError` (`test_g3y05`) |
| G3Y-06 | P2 | `MINDESTKOPFSPIEL` and `ABSCHALTEN_KORRGLIED` bypassed `_control`: second value dropped without note, no range, three values an error | both go through `_control` (`MIN_TIP_CLEARANCE_RANGE` 0,001 to 0,99, manual Bild 4.231) (`test_g3y06`) |
| G3Y-07 | P2 | Eleven mutations no test detected (the sum beside both coefficients, the sum with x_2 only and no helix angle, band and lower end of the 90° rule, bounds of the control ranges, `stplus_tool` letting a `ParseError` through, a non-numeric pressure angle of the gear, upper-case "NEIN", a control as placeholder, the preset tip circle with spans only) | `test_g3y07`, `test_g3y02`, `test_g3y04`; all eleven fail now |
| G3Y-08 | P3 | (a) Both control probes put the stricter value first; (b) "a control is one value for the stage" too general (`SPANDICKENVERHAELTNIS = % % (%)`); (c) a second token of a control was not parsed | (a) probe `controls_first_value_holds` (0.5 1.0 and 0.4 0.1: the first value holds); (b) rule reworded to the controls printed as `KEY = % (%)`; (c) parsed |
| G3Y-09 | P3 | Two limit functions returned inf for a subnormal angle; the dedendum limit returned a value below the root form height for a tool space that is closed at that height | `finite_result` in both; `GeometryInfeasibleError` for the closed space (`test_g3y09`) |
| G3Y-10 | P3 | (a) the note of the 90° rule did not say that a given dedendum is not used; (b) `MAX_KOPFKANTENBRUCH = -0.0` gave h_K = −0.0; (c) wrong reason in the ZAHNWEITE note where x follows from the sum; (d) an edge break angle not above the profile angle was completed "as STplus does" and then rejected by the generation; (e) GEN-15 incomplete; (f) ADR-114 and GEN-11 named different pressure angles; (g) docstring "[0, 45)"; (h) "40 mutations"; (i) a placeholder token left in this report | (a), (b), (c), (g), (h), (i) corrected; (d) probes `tool_edge_break_angle_below_pressure_angle` (15° at α_n = 20°: STplus computes with α_n0 + 10° = 30°) and `…_equal_to_pressure_angle` (20°: no flank, 0,900 / 0,900): the importer does the same with a note; a control outside its range is not accepted by STplus, which keeps the preset (probe `control_outside_its_range`, manual p. 223): the importer does the same with a note instead of a `ParseError`; (e), (f) GEN-11 and GEN-15 revised, ADR-114 amended |

**Check of the sixth round by the implementer (2026-10-03; not by a reviewer).** The reviewer's
`findings_repro.py` re-run: G3Y-01 with the note, G3Y-02 typed for every angle of the repro,
G3Y-03 without the warning, G3Y-04 imported, G3Y-05 `ParseError` for the junk token. The type
sweep of the fifth round repeated: 937 calls, none untyped, none non-finite. 36 mutations in
memory against the whole suite: the eleven of the reviewer, adapted to the corrected source, and
25 of the code of this round (the two angle bounds, the angle rules, the flank predicate in the
pair geometry, the placeholder, the notes and checks of tool blocks, the controls, the limits):
all 36 fail at least one test. This round is small (no P0, the two P1 are an evidence gap and a
numerical range without practical tools) and was not given a further review.

**Open after the sixth round** (stated, not resolved): where between 85° and 88° STplus stops
computing an edge break flank; why its residual thickness at 85° is 0,5 µm above gearcore's
(since clarified: single precision, see the section after this one);
what `K_HOEHENF_VERZ_BEZ_PR` does to the tool dedendum in general (one listing: 1,430 for 1,1);
the items the fifth round left open.

**State after the sixth round.** 1336 tests passed, 8 skipped (four modules of later increments,
four supplied listings without interface file); ruff and format (package, tests, scripts,
notebooks) and mypy --strict clean; 5 notebooks executed; 59 probes, 62 defaults, 18 STplus
cases; 533 comparisons of the generation, 364 identical, 169 within the accuracy of STplus, none
different.

## Causes of the deviations stated as "not known" (2026-10-03, question of the user)

The user asked whether the two items the sixth round left open hide errors of gearcore, and
whether more deviations exist than were reported. Both items and the accuracy of the form
circles (GEN-06) were examined with 56 exploratory runs of STplus (four kept as probes, 63 in
all) and three tests. None is an error of gearcore.

| Deviation | Size | Cause (evidence) |
|---|---|---|
| Helix angle where the file gives none (STplus iterates it from a and Σx) | STplus up to 0,002° below the solution | STplus ends its iteration when the centre distance is met within about 0,5 µm: for 18 pairs (m_n 1, 2, 4, 8; Σx 0,6 and 0) the centre distance of its angle is 0,05 to 0,43 µm short, never long, and the remainder appears in x_2 (Σx 0,60012 for 0,6). Without profile shift the solution is arccos(m_n (z_1 + z_2) / (2 a)) = 16,26020°, STplus lists 16,25980° (probe `helix_angle_without_profile_shift`). `GRENZE_BETA_ITERATION` at its lower bound, `BOGENDIFFERENZ`, `KREISDIFFERENZ` and `MAX_ITERATIONSSCHRITTE` do not change the listing. Cases with a given helix angle are not affected |
| Root form diameter of an undercut gear (93 of 533 comparisons need the accuracy allowed for the form circles) | up to 6,4 µm (fzg_c pinion) | iteration limit of STplus: with `BOGENDIFFERENZ` = 20 000 and 50 000 instead of the preset 10 000 its value moves from 6,4 µm to 2,6 µm and 0,7 µm above gearcore's intersection of fillet and involute (probes `form_circle_limit_*`) |
| Residual tip thickness of a chamfer cut by an 85° edge break flank | 0,0200 mm against 0,0205 mm | single precision of STplus: DIN 3960 (A.3.05) subtracts two numbers of the size 11 there; in binary32 the formula yields 0,01960 or 0,02051 mm depending on the last bit of the tip diameter, STplus prints the latter. gearcore's value is confirmed without the formula, by the envelope of the rolling tool flank (1e-9 mm). The limit `BOGENDIFFERENZ` does not change STplus's value |

**All deviations of the comparison over the 18 cases, by cause.** Pair geometry, 855
comparisons: 786 within the rounding of the printed digit, 25 within the rounding of inputs the
listing prints with three decimals (largest 0,7 µm), 44 within the single precision of STplus
(largest 0,04 µm), none beyond. Generation, 533 comparisons: 364 within the rounding of the
printed digit, 71 within the rounding of printed inputs (largest 1,8 µm, d_Fa of the kst-C wheel
from a listing with three decimals), 5 within single precision (largest 0,5 µm), 93 within the
accuracy of the form circle iteration of STplus (largest 6,4 µm), none beyond. What the
comparison does not cover is listed in `known_limits.md` (GEN-13 to GEN-16: a tooth pointed by
the edge break, the preset allowances c25 / js7, inputs that are typed errors, preset tip circles
STplus shortens).

State: 1349 tests passed, 8 skipped; 63 probes, 62 defaults; ruff, format and mypy --strict
clean; 5 notebooks executed.

**The controls of the tool limits (same day, second question of the user).** One relation was
still stated as not known: the manual presets the controls of the tool limits with 0,2 and 0,4,
the listings show 0,120 and 0,110. 65 further runs of STplus with the three controls varied and
8 on the ends of the ranges of the chamfer controls (seven kept as probes, 70 in all) settle it: the controls act as documented (tip land = s_a0*,
tool space at the root form height = e_Ff0*, in five decimals for 0,105 to 0,7 and 0,105 to
0,59), the program presets them with 0,12 and 0,11, not with the values of the manual; the
third control enters as a root space of 2 e_f0* tan α_n (0,15 to 0,59), with e_f0* = 0,03 where
it is not set, and has no effect up to 0,1. The limits of gearcore are thus the documented
mechanism with the presets of the program (GEN-11), and the importer reads the three controls
instead of refusing them. A defect of gearcore came out of these runs: the range of a control
is an open interval in STplus (0,3 and 1,5 of `TANG_BETRAG_ZU_H_KGF`, 0 and 0,5 of
`MAX_KOPFKANTENBRUCH`, 0,1 and 1,0 / 0,6 of the tool controls leave the preset), while
importer and rule functions accepted the ends. Corrected and pinned
(`test_the_range_of_a_control_is_an_open_interval`, probes
`controls_at_the_ends_of_their_ranges`, `tool_controls_at_the_ends_of_their_ranges`); 12
mutations of the new code against the whole suite, all detected. State: 1365 tests passed, 8
skipped; 70 probes, 62 defaults; ruff, format and mypy --strict clean; 5 notebooks executed;
the comparison of the generation unchanged (533 / 364 / 169 / 0).

## Found while resolving the findings

- The fillet of an undercut gear does not need a cusp: it crosses the involute and ends on the
  mirrored branch of the involute beyond T (the point Eq. (128) prints for a negative bracket). The
  docstrings said "turns back at a cusp"; corrected, and the test that asserted a cusp was replaced
  by the check that the fillet end lies outside the involute above the crossing.
- The STplus junction of fillet and involute is a doubled vertex on all 28 gears of the own runs
  (reviewer B: the two points 0,1–0,3 µm apart on undercut gears), which is how STplus marks d_Ff in
  its export.

## Changes of contracts and signatures by the fixes

- `contour.tooth_contour(generation, role, *, points)` (the `pair` argument is gone).
- `io.ste.tool_from_section(section, notes)`: `notes` is required.
- Fourth round: `io.ste.tool_from_section(section, notes, *, name, normal_module_mm,
  normal_pressure_angle_deg)` with `section` = `None` for the hob STplus presets;
  `SteImport.preset_tip_diameters` (new field);
  `stplus_program.stplus_residual_tip_thickness(s_an_mm, h_K_mm, *, tangential_factor)` takes
  the normal tip tooth thickness (before: the transverse one) and returns the normal residual
  thickness, `stplus_transverse_residual_tip_thickness` converts it; new
  `stplus_tool_factors`, `stplus_max_tool_*`, `stplus_helix_angle_deg`,
  `stplus_tip_chamfer_height`; `GearGeneration.tip_diameter_mm` is the generated tip diameter
  (cut by the tool where its root line lies below the given one), `GenerationResult.inputs`
  keeps the pair as given; warning `tool_root_line_below_tip_circle` replaced by
  `tip_circle_cut_by_tool`, new warning `edge_break_angle_without_flank`; a tooth pointed by
  the edge break flanks is the `GeometryInfeasibleError` of `residual_tip_thickness`.
- Fifth round: `GearGeneration.tool_edge_break_angle_deg` is `None` for a tool without edge
  break flank; `stplus_tool_factors` requires `alpha_n_deg` (a number in (0, 90)) and limits
  presets; `stplus_tool(name, *, normal_module_mm, normal_pressure_angle_deg, notes)`;
  `stplus_program.MAX_TIP_CHAMFER_RANGE`, `TANGENTIAL_AMOUNT_RANGE`; `io.ste.TIP_CIRCLE_KEYS`,
  `CONFIGURATION_KEYS_EVALUATED`; `PR.VERSCH.SUMME` is a mapped key;
  `import_stplus_program.py refresh-import`.
- Sixth round: `rack.has_edge_break_flank(tool)` (public; generation and pair geometry use it);
  `generation.MAX_EDGE_BREAK_ANGLE_DEG` (89,9) and `stplus_program.
  STPLUS_MAX_EDGE_BREAK_ANGLE_DEG` (85); `io.ste.STRUCTURAL_BLOCKS`, `MIN_TIP_CLEARANCE_RANGE`;
  a control outside its range is a note and the preset (before: `ParseError`); the placeholder
  `%` is "not given" for every key.
- Controls of the tool limits (2026-10-03): `stplus_max_tool_addendum_factor(…, *,
  min_tip_land_factor)`, `stplus_max_tool_root_form_height_factor(…, *, min_space_factor)`,
  `stplus_max_tool_dedendum_factor(…, *, min_root_space_factor)`, the same three keywords on
  `stplus_tool_factors`, `tool_from_section(…, limit_controls=…)`, `io.ste.TOOL_LIMIT_CONTROLS`
  (replaces `CONTROLS_NOT_SUPPORTED`); the default `min_tool_space_width_root` is 0,03 (e_f0*)
  instead of 0,06 (2 e_f0*); the ranges of the controls are open intervals.
- `trochoid.root_form_diameter_by_intersection(rounding, d_b_mm, psi_b_rad, *, undercut_expected=False)`.
- `trochoid.TipRounding.axis_ratio` (new field); `contour.distances`, `contour.REGION_TOLERANCE`
  and `contour.JOIN_TOLERANCE` (new); `parity.ParityRow.solver_tolerance` (new field, default 0);
  `parity.rows_without_evidence` (new); `generation.dedendum` signed.

## Unverified suspicions of the reviewers

- Whether STplus uses the transverse or the normal tip thickness for a helical gear with a chamfer
  given by h_K (no fixture; GEN-07). Settled 2026-10-03: the normal one (probe
  `tip_chamfer_helical`, G3U-05).
- The 0,6 µm deviation of the helical STplus fillets from the ellipse envelope (GEN-09).
- The series values −0,085 / −0,115 / −0,155 of DIN 3967 Table 1 (increment 5).
- Whether the STplus junction tolerance is a normal gap (the sqrt(2ε/Δκ) argument): the undercut
  junctions sit 0,24 µm (fzg_c) and 2,2 µm (small_z8) from the involute.
- `tip_clearance` uses d_fE at x_Es of the mate (conservative; Eq. (60) not re-read for which d_f).

## Verified as correct by the reviewers

- Every `@eq` of `generation.py` and `trochoid.py` on the rendered pages (DIN ISO 21771 pp. 6, 11–17,
  34, 35, 37, 63–70; DIN 3960 pp. 2–3, 14, 16, 51–53; FVA 604 I pp. 12–13, 28–30; Linke pp. 41–42,
  111–112), the registry entries (symbol, designation, location; α_kP with lower-case k at 600 dpi;
  DIN 3967 p. 7 for A_ste), the STplus names in the 18 listings, 14 interface files and `.ste` files.
- Recomputations: d_Ff1 of the ISO/TR example 132,248 24 (NB) and 132,242 71 ((130) as printed);
  kst-C wheel d_Fa 113,862 799, s_taK 1,930 806; fzg_c pinion undercut intersection 67,678 697.
- Counts of the comparison, the tolerance parts, the transverse allowance of STplus (all 12 helical
  rows identical with cos β, off by 0,004–0,006 without), the junction vertex and the 6,37 µm of the
  fzg_c pinion; contour deviations to 1e-9 µm with independent code; sagitta of the 200-point polyline
  ≤ 0,021 µm; polygon closed, monotone, no self-intersection, z copies to 1e-12.
- Invariants: ±β symmetry, continuity β → 0 (also with undercut), fillet end = Eq. (128) = numerical
  intersection free of undercut, (A.3.06) residual strictly decreasing (unique root), h = h_a + h_f,
  s_an = s_at cos β_a; 20 of 22 mutations detected before the fixes, 22 of 22 after.
