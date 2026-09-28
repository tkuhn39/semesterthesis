# Adversarial gate — increment 0 (foundation) — 2026-09-28

Reviewer: read-only agent per `adversarial_gate.md` (probes: pytest, ruff, mypy, nbmake, pdftotext,
python snippets; `git status` unchanged afterwards). Baseline reviewed: 106 tests, ruff/mypy clean.

**Result: passed.** P0 = 0. P1 = 7 (all fixed). P2 = 18 (14 fixed, ADV0-23b deferred).
P3 = 12 (fixed where cheap; ADV0-29/35/36/37 accepted or deferred). Deferrals: `known_limits.md`.
Regression tests: `tests/test_adv_0.py`, property tests: `tests/test_properties.py`.

| ID | Sev | Finding (short) | Resolution |
|---|---|---|---|
| ADV0-01 | P1 | `ToolProfile.pressure_angle_deg` defaulted to 20° instead of "gear angle" (manual §4.16.2) → imports with α_n ≠ 20 failed | `None` = gear value for module and angle; resolved in `_tool_modules_consistent` |
| ADV0-02 | P1 | `AUFTEILUNG_X1X2 ≠ 0` (x-distribution modes, manual Bild 4.12) silently accepted | `NotSupportedError`; also `PR.VERSCH.SUMME` |
| ADV0-03 | P1 | silent `int()` truncation (z = 51.5, k = 5.7, Q = 7.9); `nan`/`inf` escaped untyped | STplus number grammar; fractional z → `NotSupportedError`, k/Q → `ParseError` |
| ADV0-04 | P1 | lone value copied to gear 2 on per-gear keys (manual §3.2: gear 1 only) | ZAHNBREITE single → `ParseError`; KOPFKANTENBRUCH gear 2 → 0 with note; quality per gear |
| ADV0-05 | P1 | pre-commit hooks would rewrite fixtures (trailing whitespace / EOF) and invalidate `ste_sha256` | hooks exclude the fixture folder; `test_adv0_05` checks every hash |
| ADV0-06 | P1 | empty `case_dir` parameter set skips silently | `test_adv0_06`: packaged cases == `oracle_cases.yaml` |
| ADV0-07 | P1 | no property-based tests for contracts/parsers | `test_properties.py` (JSON round trip, hash, range rejection, `.ste` token stability) |
| ADV0-08 | P2 | m_n = 0.05 rejected (open bound) | `ge=0.05` |
| ADV0-09 | P2 | malformed tokens reported as absent | `ParseError` naming the token |
| ADV0-10 | P2 | `or 0.0` placeholders for missing width | `ParseError` |
| ADV0-11 | P2 | `MESSZAEHNEZAHL_K` used as span tooth count | `ParseError("ZAHNWEITE given without MESSZAEHNEZAHL")` |
| ADV0-12 | P2 | DIN 3967 series letters a/c/h masquerade as symbols | single-letter symbol only when numbers follow; 1–2 letter markers |
| ADV0-13 | P2 | `p_x` (axial pitch, helical) not registered | added |
| ADV0-14 | P2 | units `Grad C`, `W`, `HV`, … swallowed | `UNITS` extended; two-token `Grad C` |
| ADV0-15 | P2 | `report.json` overwrote third+ occurrences | counter suffix |
| ADV0-16 | P2 | bare `Pair` accepted NaN | finiteness validator |
| ADV0-17 | P2 | wrong citation for the base-pitch condition | cites DIN ISO 21771:2014-08 §4.4 (p_bn) + manual §4.16.2 as input admissibility |
| ADV0-18 | P2 | duplicate keys/blocks first-wins | `ParseError` (`get_all` for load spectra) |
| ADV0-19 | P2 | `str.splitlines()` splits on NEL/LS | split on `\r?\n` |
| ADV0-20 | P2 | oracle moved foreign contour files out of `bin/` | fails loudly if new files appear in `bin/` |
| ADV0-21 | P2 | contour test asserted only finiteness | `test_adv0_21`: r_min = d_f/2, r_max = d_a/2, start at root |
| ADV0-22 | P2 | extra contour columns ignored | exactly two columns |
| ADV0-23 | P2 | DIN/ISO quality merged | `QualitySystem` enum; both given → `ParseError`; grade bounds → known_limits (23b) |
| ADV0-24 | P2 | withdrawn source as sole `@eq` reference passes | `test_trace.py`: withdrawn sources need a current co-citation |
| ADV0-25 | P2 | ruff hook v0.13 vs ruff ≥ 0.15 | hook rev v0.15.0 |
| ADV0-26 | P3 | `Fall=Test` split into a key | multi-pair split requires ` KEY = ` |
| ADV0-27 | P3 | `prepare_ste` ignored `#` comments on block lines | stripped |
| ADV0-28 | P3 | `% 20` helix read as 0 | `ParseError` (placeholder for gear 1) |
| ADV0-29 | P3 | NUL byte in kst-E listing | accepted (known_limits) |
| ADV0-30 | P3 | mypy errors in scripts/tests, unused `noqa` | scripts type-checked in CI; noqa removed |
| ADV0-31 | P3 | dead `ci` hypothesis profile, unused marker | `HYPOTHESIS_PROFILE=ci` in CI; marker removed |
| ADV0-32 | P3 | lax coercion (`"24"`, `24.0`, blank names) | strict ints, stripped strings |
| ADV0-33 | P3 | key naming drift, duplicated ISBN helper, stale counts | roadmap updated; helper duplication tolerated in a test |
| ADV0-34 | P3 | `F("-", "-")` noise on name fields | plain `Field` for names |
| ADV0-35 | P3 | local `python3` kernelspec → other env | known_limits (environment) |
| ADV0-36 | P3 | page break inside a dashed title frame | known_limits (not observed) |
| ADV0-37 | P3 | plastic E/ν only in provenance note | known_limits (stage 2) |

Verified as correct by the reviewer: all 15 fixture hashes and typed imports, STplus versions
6.0.9/9.0F/11.0F/11.1F parsed, no fixture file git-ignored, contour radii = d_f/2 and d_a/2 within
8 µm, interface ↔ geometry consistency, manual §3.2 grammar assumptions, `prepare_ste` drops only
output-control keys, contract boundaries and validators, ISBN checksums, source editions vs PDF
headers, CI commands, `.gitignore` traps.
