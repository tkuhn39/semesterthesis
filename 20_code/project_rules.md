# Project Rules (binding for humans and AI agents)

Successor of the legacy rules (archived in `30_references_and_examples/38_legacy_workbench/project_rules.md`).
Rules are numbered so ADRs and reviews can cite them.

## A. Sources and traceability
1. **Primary sources only.** Every formula comes from a norm, patent, FVA report, textbook or paper that
   exists as a PDF in `00_literatur/` (or is provided by the user). Nothing is implemented from memory or
   from the web. Missing source → ask the user.
2. **Full references.** Every computational function carries `@eq(source, eq, section, page)` where
   `source` is a key of `data/sources.yaml` naming norm **and edition** (`ISO21771:2014`). Bare equation
   numbers are never used; they are only unique within one document.
3. **Current norm wins.** Withdrawn norms (DIN 3960:1987, DIN 3961–63:1978, ISO/TR 13989 …) are never the
   computational basis. STplus is a numeric oracle only. Every deviation from it is recorded in
   `data/stplus/expected_differences.yaml` (old source/eq, new source/eq, reason, numeric example, effect)
   and rendered to `norm_differences.md` for the thesis.
3a. **Current notation in the tool, original notation in quotations — never mixed.** Code, contracts,
   notebooks and the later program use the symbols of the currently valid norms (e.g. `h_aP0`,
   DIN ISO 21771:2014-08 §7.1). When an older document is quoted (DIN 3972:1952 `h_kw`, `r_1`; DIN 3960;
   STplus listings), its own symbols are kept and the mapping to the current symbol is stated
   explicitly. Where current documents differ, the equations and the symbol list of the newest
   geometry norm decide (figure lettering can differ from them); the other documents are recorded.
3b. **One source of truth for names, symbols and designations** (user decision 2026-09-29, ADR-108):
   `data/quantities.yaml`. Every quantity is entered there **before** it is used, with the symbol
   and the designation of the governing norm (verbatim, with location), the English designation of
   an ISO document, what other current documents print, what STplus prints (listing symbol and
   label, input key, interface key) and what the replaced norms printed. Every text is read on the
   rendered page. Contracts declare their fields with `Q(<quantity>)`; fixtures, the comparison
   with STplus, notebooks and the generated table `quantities.md` refer to the registry. Nothing
   else defines a symbol.
   - **Program names** render the designation of the governing norm in English, using the wording
     of an ISO document in the repository where one exists; they are shortened only where the
     designation has more than four words. A contract field is the program name without the
     context prefix of its model, plus `_factor` for a module factor, plus the unit suffix.
     Arguments of single-equation functions are the symbol plus the unit suffix (`m_n_mm`).
     Names are ASCII only: the unit µm has the suffix `_um`, Greek letters are spelled out
     (`alpha_n`). Python normalises the micro sign in an identifier to the Greek letter mu, so a
     key typed as `..._µm` in JSON or YAML would no longer match the field. The unit itself is
     written "µm" wherever it is a value (`unit`, `printed`, tables, plots).
   - **Fixtures of norm examples** hold the complete table of the norm in its order; every entry
     carries the label of the norm verbatim, the symbol, the unit and the printed text, and the
     tests require the stored number to equal the printed one.
   - **Typography:** the symbol is italic, every subscript upright, letters as well as digits
     (`\mathrm{...}`; `gearcore.quantities.latex` renders the symbols of the registry).
   - A quantity whose designation is not yet verified has `status: pending`; no computation,
     fixture or notebook may use it.
4. **Citations are verified**, not assumed: DOI via Crossref, ISBN checksum, URN via nbn-resolving, norm
   edition from the PDF header, patent number from the DPMA front page. A source may be cited from code
   (`@eq`) only after the user has checked the entry against the PDF and set `confirmed_by_user: true`
   in `sources.yaml`; `test_trace.py` fails otherwise (user decision 2026-09-28).
5. **Licence hygiene.** No norm text is reproduced verbatim; formulas are transcribed in own LaTeX with a
   reference. The STplus executable and its manual never enter git, CI or containers.
5a. **Nothing of STplus gets lost** (user decision 2026-09-30, ADR-109). What STplus ships and
   presets — tool databases, the register of input keys, defaults — is kept under
   `data/stplus_program/` as written, labelled with program version and release and with its
   evidence (page of the manual, probe run). It is no norm and is never applied silently: a
   caller asks for a record or a default by name. A value that is not entered is either a named
   value of a norm table or missing; falling back on an old STplus default is an explicit choice.

## B. Code
6. **One equation = one function**; models are data, computations are module-level functions. No
   `@property` cascades, no duplicated helpers (a second inverse involute is a P0 finding).
7. **Typed errors, never silent values.** Unsupported or infeasible inputs raise `NotSupportedError`,
   `GeometryInfeasibleError`, `InputRangeError`, `SolverError`, `ParseError`. Functions never return `None`
   or a placeholder for "could not compute". No `try/except` around mathematics; domain checks go through
   `gearcore._safe`, which raises instead of clamping.
8. **Frozen, validated contracts.** All inputs and results are pydantic models (`FrozenModel`:
   `frozen`, `extra="forbid"`, `allow_inf_nan=False`) with `symbol`/`unit`/`source` metadata; units are
   part of field names (`_mm`, `_deg`, `_um`). Results round-trip through JSON.
8a. **Double precision everywhere, no rounding in the chain** (user decision 2026-09-29, ADR-106).
   Every computation runs in IEEE 754 binary64 (Python `float`, numpy `float64`); reduced-precision
   types (`float32` …) are forbidden in `src/gearcore`. Values are handed over between functions,
   models, JSON and later the API with all their digits; rounding happens only where a number is
   displayed or printed. Inputs that were rounded by someone else (a printed STplus value, a norm
   table) carry their rounding as an explicit tolerance, never as a silent assumption.
   `test_numeric_precision.py` guards the usual violations (syntax scan and behavioural tests); it
   cannot prove their absence, so reviews check the rule as well.
9. **Steel and plastic are never mixed.** `MaterialKind` is a required field without default; every
   material-dependent branch dispatches on it explicitly.
10. **Helical is first class.** Every closed-form quantity accepts β ≠ 0; the transverse section is the
    working plane for contours.
11. **No legacy imports.** `app` (the archived workbench) is a banned import (ruff TID). Copying a
    formula from it counts as implementing from a secondary source — re-derive from the primary source.
12. **Domain library, not an application.** `gearcore` has no globals, no process state, no I/O side
    effects besides the explicit parsers in `gearcore.io`. The later API and UI wrap it; notebooks import it.
13. **English identifiers, comments, docstrings, commits.** German is reserved for the thesis and the
    norm-facing documents (`norm_map.md`, `norm_differences.md`, notebook prose).
14. **Forward slashes** in paths everywhere except when writing Windows config files for STplus.

## C. Verification
15. **Every increment ships with tests, a notebook section and an adversarial gate**
    (`00_development_documentation/adversarial_gate.md`). Next increment only after P0 = 0 and every P1
    fixed or entered in `known_limits.md` with a reason.
16. **Fixtures carry provenance** (source, page/sheet, printed decimals → tolerance, transcriber, trust).
    STplus fixtures from unconfirmed reference pairs only warn.
17. **Property-based tests** (hypothesis) cover round trips, invariants and error types for every module.
18. **Notebooks are documentation.** They call `gearcore`; they never define formulas
    (`test_notebooks_are_documentation.py` enforces it). Outputs are stripped before commit.

## D. Repository hygiene
19. **Doc chain on every commit:** CHANGELOG (root), ADRs, roadmap, and — when the norm map or a
    deviation changes — `norm_map.md` / `expected_differences.yaml`.
20. **Git-ignore traps:** `30_references_and_examples/`, `*.sta`, `*.dat`, `*.inp`, `*.log`, `lib/`,
    `build/`, `dist/` are ignored repo-wide. Name fixtures accordingly (`report.sta.txt`).
21. Accumulative documentation files (`architecture_decisions.md`, `known_limits.md`, CHANGELOG) are
    never rewritten wholesale; entries are appended.
