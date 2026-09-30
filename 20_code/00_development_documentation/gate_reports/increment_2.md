# Adversarial gate — increment 2 (pair geometry) — 2026-09-30

Reviewers: two read-only agents per `adversarial_gate.md`, in parallel. `git status` was identical
before and after both reviews; neither ran STplus.

| Reviewer | Scope | Probes |
|---|---|---|
| A | `pair.py`: citations and formula bodies against the rendered pages, guards, boundaries, tests | independent recomputation of every float field of `PairGeometry` for 10 pairs (plain `math`, own inverse involute), 1 728 corner cases and 30 000 random cases of the orchestrators, single-function sweep with 35 bad values per argument, coverage |
| B | comparison with STplus, `.ste` importer, quantity registry, notebook 02, documentation | counts and tolerances recomputed per field, twelve own mutations of the formulas in memory, registry entries against the rendered pages of DIN ISO 21771, DIN 3960, ISO 6336-1, ISO/TS 6336-21, importer probes with own texts |

Baseline reviewed: 759 tests passed, 10 skipped; ruff and mypy clean; `pair.py` 98 % line coverage.

**Result: passed after two rounds of fixes.** Gate: P0 = 1 (resolved). P1 = 7 (six resolved, one
needs no action). P2 = 17 (all resolved, G2B-06 in part). P3 = 17 (all resolved). A third read-only
reviewer then re-ran the original repros against the fixes (section "Verification review" below): the
first fix of the singular mesh (G2A-02, G2B-14) did not hold; in total the review produced 17
findings (3 P1, 6 P2, 8 P3), which were resolved in a second round. Deferrals: `known_limits.md`
(PAIR-06 to PAIR-11). State after the second round, its re-check and the review by the user: 896 tests passed, 10 skipped (six modules of
later increments, four supplied listings without interface file), 4 notebooks executed, ruff and
mypy --strict (src, scripts) clean, `pair.py` 100 % line coverage, 18 STplus cases. Regression tests:
`tests/test_adv_2.py`.

No citation and no formula body of `pair.py` was wrong: reviewer A read every equation cited at the
time on the rendered pages, and the independent recomputation agrees with `compute_pair_geometry` to
2.4e-13 relative (range extremes) and 7e-15 otherwise. Eq. (83), (84), which became traced functions
through G2A-14, were read on p. 46 by the implementer. The counts of the comparison with STplus were reproduced by reviewer
B, and all of his mutations were detected. The defects were a missing guard (P0), the handling of
the singular mesh, untyped errors for inputs that bypassed the contract, untested branches, registry
translations, two importer behaviours and overstated documentation.

## P0

| ID | Finding (short) | Resolution |
|---|---|---|
| G2A-01 | `GearKind.INTERNAL` was read nowhere: a pair declared as internal was computed as an external pair without error or warning | the three orchestrators raise `NotSupportedError` for a gear that is not external; test over all three |

## P1

| ID | Finding (short) | Resolution |
|---|---|---|
| G2A-02, G2B-14 | a start of the active profile on the base circle was rejected only when a denominator fell below an absolute 1e-12 mm: a large gear returned ζ_f = −1.4e14, a wheel tip 1e-13 (relative) beyond the tangent point returned ζ_f = +6.0e11 with the wrong sign | first round: a relative criterion on the radius of curvature (≤ EPS · T_1T_2). The verification review showed that it caught exact zeros only (G2V-01, G2V-02). Second round: the criterion is the diameter the result reports, d_Nf ≤ d_b · (1 + EPS) → `GeometryInfeasibleError`, and the radius of curvature at the root is evaluated from the circle that is given instead of through a diameter round trip. The single functions of Eq. (114), (115) keep their own relative guard against a division by zero. Tested at m_n = 0,05, 2 and 100, with the original repros of both reviewers, with a scan of the centre distance and by a property test of the orchestrator |
| G2B-01 | registry: the note of Σx said that the symbol list §3.1 does not list it; p. 17 lists it | location "§3.1 symbol list, p. 17; §5.3 Eq. (62), p. 41", sentence removed |
| G2B-02 | registry: the tip alteration coefficient was mapped to DIN 3960 "k Kopfhöhenänderung", which is a length; the factor is k* (§4.3.6 Eq. (4.3.08), p. 32) | `replaced` is k* "Kopfhöhenänderungsfaktor"; the note names k as the length. The difference table now lists k* → k as a changed symbol |
| G2B-03 | registry, norm map and two tests stated a changed symbol g_αa → g_a; the clause of DIN 3960 writes g_a itself (Eq. (4.4.13), p. 35), g_αa stands only in the list §2.1 and in the STplus listing | `replaced` cites the clause; g_αa is recorded as the symbol of the list and of STplus; norm map and both tests corrected. Same error pattern as REG1-01 (ADR-108) |
| G2B-04 | the importer read `ACHSABSTAND` as a per-gear key: `ACHSABSTAND = % 60.5` gave no centre distance silently, a second value was ignored | read as a pair key: a placeholder in front of a value is a `ParseError`, two values are `NotSupportedError` |
| G2B-05 | a file with a and no x, or without a and with one x, left the importer as a raw `pydantic.ValidationError`; ADR-107 promised `NotSupportedError`, and the branch in `resolve_profile_shift` was unreachable | the importer checks determinacy: a without x and without span → `NotSupportedError` (distribution of the sum), no a and one x → `ParseError`; the unreachable branch is removed and ADR-107 corrected. "Whatever the contract rejects is a `ParseError`" held for `PairInput` only in the first round (G2V-03); since the second round it holds for every model the importer builds |
| G2B-24 | ADR-105 cites DIN 3972 with the edition 1952; not compared with the title page by this reviewer | no action: `sources.yaml` and the norm map use 1952-02, the title page was read in the gate of increment 1 |

## P2

| ID | Finding (short) | Resolution |
|---|---|---|
| G2A-03 | inputs that bypassed the contract (`model_copy`, `model_construct`) raised `TypeError`/`AttributeError` from the mathematics | the orchestrators apply `PairInput` again in strict mode before any computation and raise `InputRangeError`; optional `Pair` arguments are type-checked. Since the second round they also compute with the validated pair and return it as `inputs` (G2V-04) |
| G2A-04 | Eq. (67), (69), the case "both gears limited", d_Ff equal to the start of the active profile and the tolerance bands were never executed; one branch was hidden by a regex alternative | decimal references D (both gears limited) and E (wheel limited) from the generator in `scripts/`; direct tests of every branch; `pair.py` at 100 % line coverage |
| G2A-05, G2B-06 | span measurements: ADR-107 said a gear with a span counts as "x given", the contract did not apply that, and a_w + x_2 + W_k1 (the data of ISO/TR 6336-30 Table A.1) raised `NotSupportedError` although x_1 follows from a_w and x_2. The norm example shows that a span yields x_E1 = 0,117 79, not the nominal x_1 = 0,145 22 | spans are not evaluated in increment 2: a span is reported (`span_measurement_not_used`); `NotSupportedError` only where x is otherwise undetermined. The worked example now passes the spans on. The implementer's rule "a span never stands in for the nominal x" was not confirmed by the user: how a span determines the profile shift is left open until increments 4 and 5 (section "Review by the user", PAIR-06) |
| G2A-06 | second implementation of Eq. (17) in `pair.py` | `involute.radius_of_curvature` is the only one |
| G2A-07 | values inside a tolerance band were accepted but not folded onto the boundary: d_Nf below d_b, d_Na above d_a in 97 of 30 000 random cases; two different criteria for "mate beyond the tangent point" | d_Ff within EPS below d_b is d_b, d_Fa within EPS above d_a is d_a, and the result echoes the root form diameters it used; one relative EPS for all boundaries, listed in the module docstring. A start of the active profile within EPS of the base circle is rejected (see G2A-02), so no result reports d_Nf ≤ d_b |
| G2A-08 | hypothesis wrote `.hypothesis/` into the package directory | no example database, and the storage directory of hypothesis (it also caches constants and Unicode data) is a temporary directory outside the repository |
| G2A-09 | `resolve_profile_shift` and `with_nominal_tip_diameters` returned a derived x of 14,9 and did not validate their arguments when both tip diameters were given | the verified range of x is enforced where the coefficient is derived; arguments are validated unconditionally |
| G2B-07 | "missing `EINGRIFFSWINKEL` is a `ParseError`" was pinned by no test | tested, also for a placeholder |
| G2B-08 | roadmap said "28 traced functions"; there were 26 | recounted after the fixes: 28 functions carry 37 references to 36 equations |
| G2B-09 | detection limits measured on one case and stated generally | `parity.detection_limits` computes the largest tolerance relative to the value per field and STplus output over all cases; ADR-110 and PAIR-05 quote it; pinned by a test |
| G2B-10 | 145 of 693 rows compare a value that equals an input of the comparison; Eq. (127) with h_K > 0, a helical pair with b_1 ≠ b_2 and a_w with x_2 only were never compared | `parity.rows_repeating_an_input` counts them (now 173 of 855, pinned, shown in notebook 02); three own STplus runs added: `chamfer_hk_z20_34`, `helix15_b_unequal`, `a_x2_only_z18_45` |
| G2B-11 | registry: `english` of d_Na empty although ISO 6336-1:2019 prints a designation; ISO/TS 6336-21 prints another | "active tip diameter of pinion or wheel" (ISO 6336-1:2019 Table 2, p. 4); "Effective tip diameter" (ISO/TS 6336-21:2022 Table 2, p. 2) under `also` |
| G2B-12 | all eight `replaced` items cited only the list §2.1 of DIN 3960 | the defining clause is cited first (§4.2.6, §4.3.3/4.3.4, §4.3.6, §4.4.3, §4.4.5.2, §4.5.2, §4.5.3) |
| G2B-13 | registry: STplus input key of Σx missing | `PR.VERSCH.SUMME` |
| G2B-15 | "no silent defaults" contradicted the default of 20° in `PairInput` | default removed: the normal pressure angle is a required input in the contract and in the importer |

## P3

| ID | Finding (short) | Resolution |
|---|---|---|
| G2A-10 | a root form diameter equal to the computed start of the active profile produced the "limited" warning although nothing changes | the norm limits only "wenn d_Ff größer ist" (p. 43): traced function `root_form_circle_limits_active_profile` (Eq. (66), (67)); "larger" means by more than EPS (relative), so that neither equality nor one unit in the last place limits (G2V-12) |
| G2A-11 | negative sliding factor possible and not documented; u < 1 and negative radii of curvature accepted | documented as signed like g_a; u ≥ 1 and ρ ≥ 0 are guarded |
| G2A-12 | Eq. (62) did not guard α_n and took α_t, unlike its inverse Eq. (55) | takes β like Eq. (55) and guards α_n. The argument `sum_of_profile_shift_coefficients` of Eq. (55) keeps the registry name although it shadows the function inside that one function |
| G2A-13 | wrong or misleading texts: "never negative" for c_F, "follows from the centre distance" for a given x, an error about α_wt = 90° for a huge centre distance, Eq. (62) cited for a value that is x_1 + x_2 | corrected; a huge centre distance is named in the error; c_F is listed as not in the result (ADR-110) |
| G2A-14 | Eq. (66)/(67), (83)/(84), (116)/(117) carried no `@eq` | traced functions added |
| G2A-15 | a given tip form diameter together with a chamfer input ignored the chamfer silently; a face width beyond the contract was computed; z_1 > z_2 passed the contract | warning `tip_chamfer_input_not_used`; the contract is applied again (G2A-03); `PairInput` requires z_1 ≤ z_2 (§5.1.3) |
| G2A-16 | `assert` in library code; guards duplicated between `involute.py` and `pair.py` | removed; shared guards in `_guards.py` |
| G2A-17 | loose tolerances; the generator of the decimal references was not in the repository | tolerances at what the arithmetic achieves (measured on 200 000 random pairs); `scripts/decimal_reference_pair.py` is part of the repository and checked against the tables of the tests |
| G2A-18 | Anhang NB prints the middle term of the corrected Eq. (56), (57) as cos α_t / cos α_wt without d_1, d_2 | confirmed on the page and recorded in ADR-110; no effect on the code, which uses the last form |
| G2B-16 | `norm_differences.md` is described as generated; neither the file nor a script exists | documents say "generated with increment 6" (PAIR-08) |
| G2B-17 | CHANGELOG: "one traced function per equation"; §7.6 missing | reworded |
| G2B-18 | the notebook column of `traceability.md` is a name match | the generated file says how the column comes about |
| G2B-19 | `expected_differences.yaml`: "within the print tolerance"; h_* not mentioned | reworded; evidence now covers a chamfer given as an input on both gears as well |
| G2B-20 | `sources.yaml`: title of DIN 58412 wrote "DIN 58400"; the page prints "DIN 58 400" | first copied as printed; the user then set the title to DIN 58400 (the title page only groups the digits) |
| G2B-21 | a third value on a per-gear key was ignored silently | `ParseError`; note of the dropped x_2 reworded |
| G2B-22 | norm map: conditions of DIN 21773 Eq. (26) and (28) omitted | added (helical gears; α_n = 20° with the chart of Bild 8) |
| G2B-23 | no oracle test for Eq. (76); tip clearance tested on interface files only | both tested against all 14 interface files and all 18 listings |

## Verification review of the fixes (2026-09-30)

A third read-only reviewer re-ran the original repros of both reports against the fixed code, swept
40 000 random pairs over the full ranges against an own recomputation (29 504 results, agreement to
4.5e-13, no untyped error, no violated invariant), tried 36 in-memory mutations of `pair.py` and
recomputed every number the documents quote. `git status` and a checksum manifest of 260 files were
identical before and after. All quoted counts reproduced. The formulas were right; "all resolved"
was not.

| ID | Sev. | Finding (short) | Resolution (second round) |
|---|---|---|---|
| G2V-01 | P1 | G2B-14 not resolved: `undercut_z12_x0` with d_Ff1 = d_b1 still returned ζ_f1 = −2,6e6 without a warning; a wheel tip shortly before the tangent point returned d_Nf1 = d_b1 together with ζ_f1 = −1,2e11 | criterion on the reported diameter: d_Nf ≤ d_b · (1 + EPS) → `GeometryInfeasibleError`; tests with both fixtures and with tips 1e-10 to 1e-6 mm short of the tangent point |
| G2V-02 | P1 | G2A-02 (c) not resolved: a centre distance just above the sum of the base radii with d_Ff = d_b returned a result with both starts on the base circles for about 15 % of the values, differently per module | same criterion; scan of 48 centre distances at each of three modules. In addition the radius at the root is taken from the given circle (Eq. (17) at d_Nf where the root form circle limits); that is a choice of conditioning without measurable effect (≤ 3e-8 in ζ_f in the second pass of the review), not what resolved the finding |
| G2V-03 | P1 | importer: values rejected by `GearInput`, `SpanMeasurement` or `ToolProfile` left as raw `ValidationError` | every model built while reading a file is covered (`GearInput`, `SpanMeasurement`, `ToolProfile`, `MaterialRecord`, `PairInput`), also through the public `tool_from_section` and `material_from_section`; tests for nine fields of the first three models and for the material block |
| G2V-04 | P2 | the second validation checked a dump but the computation read the original object: a nested dict raised `AttributeError` | the validated pair is computed and returned as `inputs` |
| G2V-05 | P2 | the tolerance at the base circle was one-sided: d_Ff one unit in the last place above d_b returned ζ_f = −2,7e7 | the band is symmetric (criterion of G2V-01) |
| G2V-06 | P2 | g_α = 0 within rounding noise gave a result at m_n = 0,05 and 100 and an error at m_n = 2 | first: g_α ≤ EPS · T_1T_2 is no mesh; replaced in the second pass by the criterion on the reported diameters (G2W-03) |
| G2V-07 | P2 | eight of 36 mutations survived; no property test called the orchestrator | property test of `compute_pair_geometry` over the verified ranges of z, m_n, α_n, β and x (order of the diameters, g_a1 + g_a2 = g_α, mating of d_Nf and d_Na, JSON round trip, only typed errors); boundaries pinned; two survivors were dead code and are removed (the `min` around Eq. (68), (69), the fold in the rest to the tangent point) |
| G2V-08 | P2 | documents claimed "all resolved", "the contract holds for every call", "folded before any radius is formed" | corrected in this report, ADR-110, roadmap, CHANGELOG, notebook 02 |
| G2V-09 | P2 | four texts said different things about spans and about "a_w without x" | one statement (ADR-107): no span is evaluated in increment 2; a pair with spans only is read but not computed; how a span determines the profile shift is open (user, increments 4 and 5) |
| G2V-10 | P3 | a derived x of 2,0000000000000044 was rejected although the same pair with x = 2 given is valid | within EPS beyond the range the limit is taken |
| G2V-11 | P3 | a root form circle above the tip gave a message about the mating gear | explicit check d_Ff < d_Fa with its own message; neutral wording of the interference message |
| G2V-12 | P3 | d_Ff one unit in the last place above the computed start flipped to "limited" | limit only beyond EPS |
| G2V-13 | P3 | the result echoed a root form diameter below d_b | the result carries the values used |
| G2V-14 | P3 | a third name on `WERKZEUG_VORVERZ.` or `ABMASS_TOL_REIHE` was ignored; zero defaults without note | `ParseError`; the zero defaults were put to the user, who made the four fields required (ADR-111) |
| G2V-15 | P3 | the basic comparison treated x_2 of a file with a_w and x_2 as derived | same rule as the pair comparison (basic comparison now 549 rows) |
| G2V-16 | P3 | PAIR-05 omitted Σx; "ein bis zwei Größenordnungen" too general; "committed generator" | reworded |
| G2V-17 | P3 | the singular criterion existed twice; `assert` in `parity.py` and `ste.py`; unvalidated content in `PairGeometry.inputs` | one criterion in the orchestrator; asserts replaced by typed errors; see G2V-04 |

Mutations: 28 of 36 detected in the first round. Survivors: the fold in the rest to the tangent
point and the `min` around Eq. (68), (69) (both without effect, removed), an absolute EPS in the
orchestrator's singular check (check replaced), the unfolded root form diameter (now visible in the
result and tested), `g_alpha < 0`, `d_Fa < d_b` and a wider band of d_Fa (boundaries now tested).

### Second pass of the verification review

The same reviewer re-ran all 17 findings, two random sweeps of 40 000 pairs each (56 605 results,
agreement with the own recomputation to 4.7e-13, no untyped error, no violated invariant, no result
with d_Nf ≤ d_b · (1 + 1e-12), no false rejection beyond the band) and 57 mutations (50 detected).
Verdict: the code holds; all three P1 are resolved. Eight further items (3 P2, 5 P3), resolved:

| ID | Sev. | Finding (short) | Resolution |
|---|---|---|---|
| G2W-01 | P2 | ADR-110 and PAIR-03 said that a specific sliding beyond roughly −1e5 is not returned; the code returns up to −1,3e7 | the bound is stated as it is: about T_1T_2 / (7e-7 · d_b1) at the wheel, divided by u at the pinion |
| G2W-02 | P2 | the wheel side of the singular criterion was pinned by no test | mirrored tests (pinion tip at T_2; root form circle of the wheel on its base circle) |
| G2W-03 | P2 | a_w and both root form circles 1e-6 above their limits: result with d_Nf > d_Na at m_n = 2, error at m_n = 0,05 | an active profile without length, d_Nf ≥ d_Na · (1 − EPS), is no mesh; it replaces the check of g_α, which it implies; tested at three modules |
| G2W-04 | P3 | the band of the limit decision is wide in roll length close to the base circle; c_F can be negative by rounding noise | documented (module docstring, ADR-110, PAIR-03); docstring of Eq. (76) corrected |
| G2W-05 | P3 | ADR-107 item 5, norm map and CHANGELOG still differed on "a_w without x" and on the increment | aligned: rejected only without span; open decision for increments 4 and 5 |
| G2W-06 | P3 | `material_from_section` raised a raw `ValidationError`; a third name on `WERKSTOFF` was ignored | `ParseError` in both cases |
| G2W-07 | P3 | docstring of `PairGeometry` said the root form diameters echo the input; ADR-110 item 7 overstated what the strict validation rejects | corrected; lax mode of the constructors recorded as PAIR-11 |
| G2W-08 | P3 | the property test did not cover the whole ranges; "one test per model and field"; the radius change credited with the fix | strategy widened to the verified ranges; texts corrected |

Surviving mutations of the second pass: `>=` instead of `>` inside the band of the limit decision
(equivalent), the radius at the root taken from the mating tip although limited (numerically
equivalent), the singular check for the pinion only (now tested), and an inner importer wrapper
that the outer one made redundant (removed).

## Review by the user (2026-09-30)

| Point | Decision of the user | Done |
|---|---|---|
| Span measurements (G2A-05, G2B-06, G2V-09) | not decided now. A span determines the profile shift and vice versa; how a span of an input is treated, and how STplus handles it, is researched in increments 4 and 5 and confirmed then | the implementer's rule "a span never stands in for the nominal x" is withdrawn; ADR-107 lists the sources (DIN 21773 Eq. (14), p. 13; DIN ISO 21771 §7.4, p. 67; ISO/TR 6336-30 p. 43, 45) and the behaviour of increment 2 (no span is evaluated); PAIR-06 |
| Zero defaults (G2V-14, PAIR-10) | helix angle, tip chamfer, protuberance and machining allowance are required inputs; a blanket zero only together with a note | ADR-111: the four fields have no default; the importer states each zero in its notes; `meta.json` of all fixtures refreshed |
| Common tooth depth (the eleven `different` rows of the comparison) | compute it with the tip form circles like STplus and document this deliberately: on the tip chamfer the tooth does not carry | ADR-112: Eq. (59) is evaluated with d_Fa; the result names the value of the tip circles in a warning; recorded under `deviations_from_the_norm`; the comparison has no `different` row any more (786 identical, 69 within the accuracy of STplus) |
| Title of DIN 58412 in `sources.yaml` (G2B-20) | the norm is DIN 58400 without a space; the title page only groups the digits | title corrected by the user; note aligned |

## Found while resolving the findings

- **STplus with a_w and x_2 only** derives x_1 from the centre distance, as gearcore does (own run
  `a_x2_only_z18_45`: x_1 = 0,42842, identical). This was an unverified suspicion of reviewer B.
- **The difference of the common tooth depth** (since resolved by the user's decision, ADR-112) also occurs for a tip chamfer given as an input
  (`chamfer_hk_z20_34`: 4,02249 mm by both norms, 3,52249 mm printed by STplus).
- **Single precision is visible in a spur run as well:** d_b2 = 126,858504 mm is printed as
  126,85851 (`a_x2_only_z18_45`). ADR-106 said that only helical runs show it; corrected there and
  in notebook 01. Evidence now: 14 own runs, 126 values, 117 reproduced by binary64, 126 by the
  binary32 chain.
- **STplus prints the form over-dimension c_F under the symbol c_n** in the listing.
- The comparison took x_1 from the STplus output whenever the file gave none, also where the file
  gave a_w and x_2; it now uses the two values of the file.

## Changes of contracts and signatures by the fixes

- `PairInput.normal_pressure_angle_deg` has no default (was 20°).
- `PairInput` rejects z_1 > z_2.
- `sum_of_profile_shift_coefficients(z_1, z_2, alpha_n_rad, beta_rad, alpha_wt_rad)` takes β instead of α_t.
- New warnings `span_measurement_not_used` and `tip_chamfer_input_not_used`.
- `PairGeometry.inputs` is the pair as the contract validated it; `root_form_diameter_mm` of the
  result holds the values the mesh was computed with.
- `compute_pair_geometry` raises for a start of the active profile with d_Nf ≤ d_b · (1 + 1e-12)
  and for an active profile without length, d_Nf ≥ d_Na · (1 − 1e-12).

## Unverified suspicions of the reviewers

| Suspicion | Outcome |
|---|---|
| the decimal reference table of `test_pair.py` has no visible origin | generator committed; a test compares every value |
| sign convention "left hand = negative β" not checked against the norm | open (ADV1-44b); all pair results are invariant under ±β, the convention matters from the contour on (increment 3) |
| what STplus does with a_w and x_2 only | answered by an own run (above) |
| what STplus does with `ACHSABSTAND = % …` | not run; gearcore rejects such a file (PAIR-07) |
| "tip alteration coefficient" as the wording of ISO 21771:2007 | the English edition is not in the repository; `english` stays empty (PAIR-09) |
| `helix20_z25_65` has a tool with an edge break angle but prints d_Fa = d_a | not examined; belongs to the generation (PAIR-07, increment 3) |
| STplus forms the printed nominal x_1 of kst-B from W_1 and the upper allowance of the preset series | reviewer's own calculation, not verified by the implementer (PAIR-06, increment 4) |

## Verified as correct by the reviewers

DIN ISO 21771:2014-08 Eq. (23), (24), (28), (30), (33), (52), (54) to (57) with Anhang NB, (59), (60),
(62), (64) to (69), (76), (77), (79), (80), (87), (90), (93), (97), (112) to (117), (127): number,
clause, printed page and formula body; "(61) does not exist"; b versus b_w in Eq. (93) and (91). The
printed results of ISO/TR 6336-30:2022 Annex A example 1 (p. 45, 46) against the fixture. Bit-identical
results under ±β (3 787 pairs); continuity at β → 0; JSON round trip; only typed errors in all sweeps
of validated inputs. The counts of the comparison (693 rows at the time); the documented difference
recomputed from printed values only, and that it is not the overlap of the active tip circles; all 15
fixtures import; the notes of kst-E; the title pages of DIN 3992 and DIN 58412; DIN 21773 p. 18;
manual Bild 4.12, p. 25. Notebook 02: formulas, clauses, pages, upright subscripts, no formula outside
the plot helpers.
