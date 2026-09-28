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
4. **Citations are verified**, not assumed: DOI via Crossref, ISBN checksum, norm edition from the PDF
   header, patent number from the DPMA front page. Unverified entries are flagged, never silently used.
5. **Licence hygiene.** No norm text is reproduced verbatim; formulas are transcribed in own LaTeX with a
   reference. STplus exe, databases and manual never enter git, CI or containers.

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
