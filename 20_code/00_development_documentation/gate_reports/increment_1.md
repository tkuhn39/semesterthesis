# Adversarial gate — increment 1 (involute and basic rack) — 2026-09-29

Reviewer: read-only agent per `adversarial_gate.md` (probes: pytest, ruff, mypy, Poppler renderings of
the norm pages, Python snippets with 45- to 70-digit references, in-memory mutations). A checksum
manifest of 193 files and `git status` were identical before and after the review.
Baseline reviewed: 454 tests, ruff and mypy clean.

**Result: passed.** P0 = 0. P1 = 15 (all resolved). P2 = 21 (all resolved). P3 = 9 (four resolved,
two resolved in part, three accepted with documentation). Deferrals: `known_limits.md`.
State after the fixes: 621 tests, 3 notebooks executed, ruff and mypy --strict (src, scripts) clean.
Regression tests: `tests/test_adv_1.py` and the files named in its docstring.

No formula, no table transcription and no equation citation of `involute.py` was wrong. The findings
concern missing guards, untyped errors, two citation errors, one undocumented table deviation, loose
tolerances and overstated documentation.

## P1

| ID | Finding (short) | Resolution |
|---|---|---|
| ADV1-01 | negative tooth thickness or space width at the reference cylinder returned silently for \|x\| > π / (4 tan α_n) | **resolved differently from the proposal.** An error would reject feasible gears (z = 100, α_n = 30°, x = −1,5: tip thickness 0,40·m, root circle above the base circle, reference cylinder above the tip). The equations return signed values (documented), `BasicGearGeometry.warnings` names the case |
| ADV1-02 | `OverflowError` for integers beyond the float range | `finite_input` checks the magnitude before converting; `integer_input` limits integers to 2^53 |
| ADV1-03 | `inf` returned for huge inputs | `finite_result` on every product and quotient that can overflow → `InputRangeError` |
| ADV1-04 | `root_form_height_factor` guarded the angle only | both factors checked; a form height ≤ 0 is `GeometryInfeasibleError` |
| ADV1-05 | orchestrator converted to radians before any guard (`bool` accepted as 1°, `str` → `TypeError`) | inputs are checked first, against the verified ranges |
| ADV1-06 | `din867_basic_rack` did not check the fillet radius factor (raw `ValueError` possible) | `finite_input` and range [0, 1] |
| ADV1-07 | negative "maximum fillet radius" for c_P < 0 or h_fP ≤ 0 | `InputRangeError` |
| ADV1-08 | exact float membership: `check_module(0.07 * 100)` said "module 7 is not listed" | tabulated modules are matched with a relative tolerance of 1e-9; messages print the full value |
| ADV1-09 | non-positive module accepted as "not standardised" | `InputRangeError` |
| ADV1-10 | `check_module` cited ISO 54 Table 1 on p. 1 | Table 1 → p. 2; clause 3 (preference, module 6,5) → p. 1 as a second reference |
| ADV1-11 | symbol map named DIN ISO 21771 Bild 35 as a location of ρ_aP0; the figure letters r_aP0 | survey of the current norms after the user's feedback: the equations of DIN ISO 21771:2014-08 (Eq. (128) in the normative Anhang NB, Eq. (130)) and ISO/TR 6336-30:2022 write ρ_aP0, only the lettering of Bild 35 shows r_aP0; ISO 6336-3:2019 and VDI 2736 Blatt 2 write ρ_a0. ρ_aP0 is kept, the location now names the equations (symbol map, norm map, notebook) |
| ADV1-12 | DIN 867 table prints 0,25 for c_P = 0,17 where Eq. (7) gives 0,2584; hidden by a tolerance of 0,01 | pinned like the DIN 3972 cells; all other values checked to half a printed digit; listed in the norm map |
| ADV1-13 | Eq. (12) and Eq. (17) used different tolerances at the base circle | one criterion `d_b / d_y ≤ 1 + EPS` for both |
| ADV1-14 | `ZAEHNEZAHL = 1e400` → `OverflowError` in the `.ste` import | number tokens beyond the float range are `ParseError` |
| ADV1-15 | parity compared β_b by magnitude; a sign error was invisible | signed comparison against the interface file (magnitude only for the listing, which prints one); mutation tests |

## P2

| ID | Finding (short) | Resolution |
|---|---|---|
| ADV1-16 | fillet slack 0.005 accepted user racks above the bound | no slack; only the two value pairs printed by the norms are admitted and reported |
| ADV1-17 | arithmetic tolerance 2⁻²² relative not derived from the evidence | two binary32 steps at the printed value (largest deviation observed: 1.5 steps); detection limit stated (ADV1-46) |
| ADV1-18 | input tolerance added even where x is an input | x of `input.ste` is used where STplus uses it; tolerance only for derived x, with the sensitivity of each quantity. New finding: STplus overrides a given x₂ when the centre distance is given |
| ADV1-19 | "listing prints three decimals" stated in five places | corrected: three for lengths, five for angles and m_t, four for x |
| ADV1-20 | `printed_decimals` miscounted exponent tokens | fixed-point tokens only, else `ParseError` |
| ADV1-21 | precision guard bypassable; docs said "enforces" | scan extended (type codes, aliases, format-and-parse, floor division), self-tests with 19 violating and 6 harmless snippets, wording corrected |
| ADV1-22 | ISO 53 type D clearance 0.3999999999999999 | printed table values stored |
| ADV1-23 | hard error for c_P outside 0,1 … 0,4 attributed to DIN 867 | soft finding (`check_basic_rack`); the norm says "im allgemeinen" |
| ADV1-24 | machining allowance validated the angle for III/IV only | validated first |
| ADV1-25 | `max(0.0, psi_y)` untested; Eq. (38) accepted a negative ψ_y | explicit boundary with test; Eq. (38) rejects a negative ψ_y |
| ADV1-26 | orchestrator and result contract unbounded | verified ranges shared by input contracts, orchestrator and result contract |
| ADV1-27 | notebook cell with `math.pi * m_t`; guard inspected functions only | guard covers cell level; notebook uses `printed_tolerance` and package functions |
| ADV1-28 | notebook gave the allowance formula without restriction | restricted to profiles III and IV; example of the norm added |
| ADV1-29 | tolerances far above what is achieved | a few ulp, or the conditioning bound |
| ADV1-30 | tautological tests | printed pitches of DIN 3972 (28 values), DIN 867 Eq. (8) as reference for the ISO 53 form, decimal references |
| ADV1-31 | new contracts missing in the metadata test | added; `ParityRow` carries its unit as a field |
| ADV1-32 | property tests avoided the difficult regions | properties for error paths, the base circle, the pointed tooth and arbitrary inputs |
| ADV1-33 | mutable public tables | `MappingProxyType` |
| ADV1-34 | builtin exception and path traversal in the data loaders | names are checked against the packaged data → `InputRangeError` |
| ADV1-35 | meaning of α_P0 paraphrased | transcribed: "Profilwinkel des Bezugserzeugungsprofils" (§3.1, p. 15) |
| ADV1-36 | ISO 53 Eq. (3) cited without its range | note on the reference; DIN 867 Eq. (8) covers type D |

## P3

| ID | Finding (short) | Resolution |
|---|---|---|
| ADV1-37 | cancellation of inv for tiny angles | accepted, documented (known_limits) |
| ADV1-38 | cancellation in ρ_y near the base circle | evaluated as √((d_y − d_b)(d_y + d_b)) / 2 |
| ADV1-39 | `inv_inverse` not strictly monotonic within its bound | accepted, documented (known_limits) |
| ADV1-40 | bisection fallback unreachable | accepted as a safety net (known_limits) |
| ADV1-41 | names built with six digits | full value |
| ADV1-42 | numpy integers rejected, duplicated guards, negative zero | `integer_input`, `positive_input` in `_safe`; −0.0 → 0.0 |
| ADV1-43 | `finite_input` untested; mypy on tests | direct tests; mypy on tests deferred (ADV1-43b) |
| ADV1-44 | three references tested by file-name fallback only; fixture unconfirmed; `slack` key | markers added, `slack` removed; confirmation and hand of helix open (ADV1-44b) |
| ADV1-45 | 63 of 99 probed values trivial; counts not pinned | ADR-106 states the share of the helical runs; counts pinned |

## Unverified suspicions of the reviewer

| Suspicion | Outcome |
|---|---|
| numpy's binary32 functions differ by CPU, the evidence test could fail elsewhere | the chain now rounds binary64 results to binary32 after every operation; deterministic |
| root `pytest.ini` not exercised | exercised: a collection at the repository root finds the package tests only |
| notebook not executed via nbmake | executed (3 notebooks pass) |

## Verified as correct by the reviewer

DIN ISO 21771:2014-08 Eq. (1), (2), (5)–(8), (12), (14)–(20), (38)–(51) against code and notebook, all 26
section and page references of `involute.py` (printed page numbers throughout); DIN 867:1986-02 Eq. (2),
(4), (5), (7)–(9) and the table of p. 3; ISO 53:1998 Table 2, Table A.1, Eq. (2), (3); ISO 54:1996 both
series; DIN 3972:1952-02 all 28 rows and the explanations; exactly 6 of 152 cells of DIN 3972 deviate
from the formulas; every value of the worked example fixture against the printed pages; nine values
recomputed by hand with 45 digits (gearcore deviates by 0.02 to 5.4 ulp); the inverse involute on
829 068 values without non-convergence and on 10⁶ random angles within its bound; the counts of
ADR-106.

## Incident during the increment

A test run started at the repository root by mistake collected the archived legacy workbench, whose
tests created an empty folder `80_output` and a hypothesis cache at the root (both removed; creation
time of the folder = time of the run; the archive itself was not modified). Guard: root `pytest.ini`.

## Registry review after the feedback round (2026-09-29)

The quantity registry (`data/quantities.yaml`, ADR-108) was written after the gate above and had not
been checked by anyone but its author. Three read-only reviewers compared it with the rendered pages
and with the STplus fixtures; `git status` was identical before and after. The implementer looked
up every finding on the page or in the fixture before correcting it.

| Reviewer | Scope | Checked |
|---|---|---|
| A | DIN ISO 21771:2014-08, DIN 867:1986-02, ISO 53:1998: symbol, designation, unit, location | 66 entries, 10 `also` items |
| B | ISO 6336-1:2019, ISO 6336-3:2019, ISO/TR 6336-30:2022, VDI 2736 Blatt 2: English designations, other current symbols | 52 designations, 27 `also` items, 10 entries |
| C | DIN 3960:1987-03, DIN 3972:1952-02, STplus listing, input, interface file and manual | 69 `replaced` items, 40 STplus blocks, 11 notes |

**Result.** Symbol, unit and location of the governing norm were right in all 66 entries; two
designations were shortened. The errors were in the translations: 3 findings P1, 5 P2, 2 P3, all
resolved; three items deferred (`known_limits.md`). State after the corrections: 657 tests, 3
notebooks, ruff and mypy --strict clean. Regression tests: `tests/test_quantities.py`
(`test_review_*`).

| ID | Sev. | Finding | Resolution |
|---|---|---|---|
| REG1-01 | P1 | The `replaced` symbols of twelve quantities were taken from the list §2.1 of DIN 3960, which omits the index of the section (s, e, s_y, e_y, p_b, p_e, alpha_y). For the normal section this named the wrong quantity (s is the transverse thickness of a spur gear); for the transverse section it suggested a symbol change that never happened. alpha_yn was missing | the clauses of DIN 3960 are cited (s_t, s_n, e_t, e_n, s_yt, s_yn, e_yt, e_yn, p_bt, p_et, alpha_yt, alpha_yn; §3.3.3, §3.3.4, §3.4.5.1, §3.4.6.1, §3.5.8.1 to §3.5.8.6). Symbols that did change since DIN 3960: a → a_w, rho_a0 → rho_aP0, alpha_K → alpha_KP (pending) |
| REG1-02 | P1 | English designation of `tool_tip_radius` was the row rho_aP0 of ISO/TR 6336-30 Table 2, a dimensionless coefficient of a pinion cutter | 'tool tip corner rounding' (ISO 6336-3:2019 Table 2, p. 7); the two senses of rho_aP0 in ISO/TR 6336-30 are recorded in the note |
| REG1-03 | P1 | STplus has two inputs for the machining allowance: `BEARBEITUNGSZUGABE` (q, geometry data) in addition to `BEARB_ZUGABE_WKZ` (tool-internal); the listing prints the total. The registry named only the second one without saying so | recorded in the note; the importer reports `BEARBEITUNGSZUGABE` as unmapped key; implemented with increment 3 (REG1-03b) |
| REG1-04 | P2 | `rotation_speed`: the documents print n_1,2 and n_1; ISO 6336-1 lists n 'rotational speed' in a row of its own | printed forms recorded |
| REG1-05 | P2 | STplus names missing: listing row of the gear ratio (z2/z1), interface keys `GEMEINSAME_BREITE` and `FUSSKREISDURCHM` | added |
| REG1-06 | P2 | STplus 'Bezugspr.-Kopfhoehenfaktor (Istw.)' is an actual value, (d_a − d) / (2 m_n) − x, not the addendum of the basic rack | note; `test_review_stplus_addendum_factor_is_an_actual_value` checks it on all interface files |
| REG1-07 | P2 | Designations not verbatim: c_P and rho_fP of DIN 867 shortened; h_kw, h_fr of DIN 3972 paraphrased; DIN 3972 prints no designation for t_0; r1 instead of r_1 | corrected, also in `sources.yaml`, `rack.py`, project rule 3a |
| REG1-08 | P2 | Note of eta_b ('negative when the root circle lies above the base circle') does not hold: z = 50, x = 0 has d_f > d_b and eta_b > 0 | corrected in the registry and in the docstring of `involute.py`; sign change between z = 105 and 106 tested |
| REG1-09 | P3 | Notes: 'seven words' (eight); centre distance note incomplete (a_w also in g_alpha, a in d_Nf); the rule behind the parentheses of x_1 not cited (ISO/TR 6336-30 4.2.18, p. 9); subscripts of the gear ratio; header sentence on units | corrected |
| REG1-10 | P3 | Designations of other current documents missing (ISO 6336-1, ISO 6336-3, DIN 867 §2, VDI 2736 Blatt 2, ISO/TR 6336-30 Table 13) | added where the implementer read them on the page |

**Verified as correct by the reviewers.** All 63 items of DIN 3960 §2.1 are printed as cited
(wording and page); all 39 pairs of STplus symbol and label are verbatim in all 15 listings; all 38
interface keys occur in all 11 interface files with the value of the listing row; 49 of 52 English
designations; no mix-up of transverse and normal, reference and working, basic rack and tool, tip
and root in the entries of the governing norms.
