# Adversarial gate — increment 4 (inspection dimensions of the tooth thickness) — 2026-10-04

Reviewers: three read-only agents per `adversarial_gate.md`, in parallel, and one verification
reviewer for the fixes. Every agent carried the guard sentence and wrote scratch files only under
the system temp directory; `git status` after the reviews showed the files of the implementer
only (the implementer wrote notebook 04 and the documentation while the reviews ran; the reviewed
sources were unchanged until the reviewers of their scope had finished).

| Reviewer | Scope | Probes |
|---|---|---|
| A | `inspection.py`: every `@eq` against the rendered pages of DIN 21773, DIN 3977, DIN 3960 and DIN ISO 21771; `din3977_table_1.yaml`; the 34 registry entries of the increment | 91 tool runs; worked numbers of DIN 3977 Bild 1 and Bild 2, ISO/TR 6336-30 A.6; a ball on a three-dimensional involute helicoid; numeric derivatives of the allowance factors |
| B | resolution of the tooth thickness, contracts, orchestrator, `.ste` importer, rules of STplus, comparison | 62 tool runs; 3600 combinations of {x, kind, allowance} against an independent count; 9520 round trips; about 4900 random gears |
| C | increment 3: sixth round (G3Y-01 to G3Y-10), causes of the deviations, controls of the tool limits (user decision 2026-10-04: these rounds had been checked by the implementer only) | 62 tool runs; 12 evidence scripts; 16 mutations; rendered manual pages 223 to 229 |

Baseline reviewed: 1470 tests passed, 7 skipped; ruff, format and mypy --strict clean.

**Result: passed after one round of fixes.** P0 = 0. P1 = 2 (both resolved). P2 = 12 (8 resolved, 4
deferred as known limits). P3 = 14 (11 resolved, 3 accepted or deferred). Regression tests:
`tests/test_adv_4.py`. Report of reviewer C: section "Independent review …" of
`increment_3.md`.

## Reviewer A — equations against the norm pages

No P0, no P1. Verified as printed: DIN 21773 Eq. (1) to (9), (12), (13) (first forms), (14) to
(17), (26), (27), (29) to (37), (40), (43) to (45), (48) to (63); DIN ISO 21771 Eq. (29), (32),
(38), (46), (48), (123), (124); DIN 3960 Eq. (3.8.13), (3.8.15), (3.8.18); DIN 3977 Tabelle 1
(55 of 55 values), section 6, Anhang A Eq. (3); all 34 registry entries. Numbers reproduced: D_M*
= 1,8506 (norm 1,85); usable range 1,7296 to 2,5389 m_n (norm 1,73 / 2,54); x_E of ISO/TR 6336-30
0,117 785 / −0,027 479.

| ID | Sev. | Finding | Resolution |
|---|---|---|---|
| G4A-01 | P2 | The constant chord was reported where its end points lie above the tip circle (z 20, d_a 40,8: h_cc = −0,105 mm, no warning) | constant chord only where its end points lie on the usable flank, else `None` and warning `constant_chord_outside_usable_flank` |
| G4A-02 | P3 | The allowance factor of Eq. (60), (61) was described for balls and rollers; rollers on an odd helical gear have twice E_MrK* | docstring and registry say so |
| G4A-03 | P3 | Eq. (35), (36) cited as §11, p. 22 for rollers; they are printed in §10, p. 21 | citation corrected |
| G4A-04 | P3 | Eq. (48) "1 on the reference cylinder" without the condition z > 12 of the norm | docstring and registry carry the condition (limits do not use the factor) |
| G4A-05 | P3 | `chordal_height` lacked the half-angle guard of the chord | guard added |
| G4A-06 | P3 | DIN 3977 Bild 2 names a 6 mm ball as usable that its own limit (6,055 mm) excludes | `norm_map.md`; gearcore follows the limits of section 6 |
| G4A-07 | P3 | English designation of the ball measuring circle stood on the span measuring circle | moved |
| G4A-08 | P3 | Eq. (15) compares b_F (face width less the edge breaks); gearcore compares b | warning says so; INS-10 |

Suspicion of the reviewer: `MIN_TEETH_SPANNED = 2` is stricter than Eq. (9), (14) — INS-09.

## Reviewer B — resolution, contracts, importer, rules of STplus, comparison

Attacked without success: determinacy (3600 combinations, no silent resolution, every value
right), round trips of all four kinds (8e-16 relative), ordering of the limits, odd z on a
helical wheel (2e-14 against an independent calculation), NaN / inf / huge integers / `model_copy`
bypass (typed errors), JSON round trips, about 1900 random extreme gears (no untyped error), x
and upper allowances of the probes.

| ID | Sev. | Finding | Resolution |
|---|---|---|---|
| G4B-01 | P1 | Warnings of the resolution (e.g. lower allowance set equal to the upper one) were missing in `InspectionResult` | the result carries the warnings of the generation |
| G4B-02 | P1 | A span over an impossible number of teeth (k = 40 on 20 teeth) determined x without a word; a given k far outside the flank only warned while a ball raised | the generation rejects an input dimension that does not touch the involute between the form circles; a given k outside the usable range is `GeometryInfeasibleError`, as a ball |
| G4B-03 | P2 | No ball of DIN 3977 Tabelle 1 (m_n 28: ideal 52,3 mm) raised with a number the user never gave, and the span was lost | typed error names the remedy; that span and chords are not returned then: INS-07 |
| G4B-04 | P2 | No backlash at the upper allowances was reported with a given centre distance only | reported in both cases; that STplus rejects such a pair: INS-03 (accepted) |
| G4B-05 | P2 | `MESSZAEHNEZAHL` without `ZAHNWEITE` and `MESSTUECKDM_KUGEL` without `DIAMETRALES_MASS` were dropped without a note | notes |
| G4B-06 | P2 | The importer did not say that the lower allowance of a gear whose upper one follows from a dimension is set equal to it (STplus: tolerance of its series) | note; the series comes with increment 5 |
| G4B-07 | P2 | A file without `KOPFKREISDM` whose x follows from a dimension gets no preset tip circle; stale note | note corrected; INS-08 |
| G4B-08 | P2 | `with_stplus_inspection_choices` did not validate its choices (`IndexError`); the docstring promised the dimensions of the listing for every gear | validated; docstring says where a choice of STplus is no measurement |
| G4B-09 | P3 | Four messages named a cause that did not apply | reworded |
| G4B-10 | P3 | A missing value of a shifted run would have become a tolerance (latent); the chord cylinder allows 7 µm | raises; INS-06 (accepted) |
| G4B-11 | P3 | Booleans are accepted as floats (contract-wide lax mode) | PAIR-11 |

## Reviewer C — the last rounds of increment 3

No P0, no P1; five P2, four P3 (G3Z-01 to G3Z-09): three importer defects fixed and tested, two
stated causes narrowed to what is established, GEN-17 and GEN-18 opened. Details and the
confirmed items: `increment_3.md`.

## Found while resolving the findings

- Notebook 02 used `SpanMeasurement` without `kind` (contract change of the increment): adapted;
  all six notebooks execute.
- The comparison of the chord allowed 7 µm although chord and height themselves do not depend on
  the accuracy of the form circles: they are compared on the printed cylinder now (before the
  gate).
- The rules of STplus for k and D_M were found during the increment (ADR-115); the comparison no
  longer takes k and D_M from the listing.
- A property test demanded nominal ≥ upper without the rounding slack the contract allows; relaxed.

## State after the fixes

1485 tests passed, 7 skipped (three modules of later increments, four supplied listings without
interface file); 6 notebooks executed (index, template, NB 01 to 04); ruff and format (package,
tests, scripts, notebooks) and mypy --strict (src, scripts) clean; 18 STplus cases: 876
comparisons of the inspection dimensions (675 identical, 201 within the accuracy of STplus, none
different), pair geometry and generation unchanged; 88 probes; 142 quantities (5 pending); 540
gears of evidence for the choices of STplus.

## Verification review of the fixes (2026-10-04)

One read-only reviewer (33 tool runs). Every fix is confirmed by its original repro; the six
mutations of G4A-01, G4B-01, G4B-02 (three variants), G4B-04 and G3Z-05 are detected by
`tests/test_adv_4.py`. The new check of the generation rejected none of 1980 inputs built from
results of the inspection (all four kinds, z 9 to 80, x -0,4 to 1,0, beta 0 / 12 / 30 degrees,
with and without chamfer), and kst-A, kst-B and kst-C pass with an allowance of the pinion. No
warning is duplicated in the result. No P0, P1 or P2.

| ID | Sev. | Finding | Resolution |
|---|---|---|---|
| G4V-01 | P3 | The generation checks an input dimension at the upper allowance of the gear; for a dimension given as mean or lower limit the message said the measurement does not touch the flank although it does at its own state (k = 4 with a usable range 1 to 4 at the lower limit, 1 to 3 at the upper one) | the messages name the state of the check |

Suspicions of the reviewer, not reproduced: the contact of a span or ball at the lower allowance
and the limits of the constant chord are not checked against the flank separately (the orchestrator
checks the ball at both limits where it chooses it; a given k is checked at the upper allowance).

