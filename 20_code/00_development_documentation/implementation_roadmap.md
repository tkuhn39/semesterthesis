# Implementation status & roadmap — to completion of post-processing

This document is the single place to **follow and supervise** the implementation.
It records what is done and validated, and lays out every remaining step up to and
including the own post-processing, so work can be paused and reviewed at any point.

It complements, and does not replace:
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — the system design (config, storage, HA).
- [`architecture_decisions.md`](architecture_decisions.md) — the ADRs (why).
- The master plan in plan mode — the FE-modelling vision and trade-offs.

_Last updated: 2026-06-17._

Status legend: ✅ done & validated · 🟦 in progress · ⬜ planned · ❓ open decision.

---

## 1. Guiding principles (do not violate)

1. **Reimplement from the documented method + standards, never by fitting I/O.**
   Every computed quantity must be variable in the inputs and traceable to a
   formula in a standard or a documented FVA method — not a value copied from an
   STplus/RIKOR printout. See ADR/notes and the standards captured below.
2. **Validate twice:** (a) against STplus/RIKOR I/O on varied inputs, and
   (b) against the shipped standard test cases / hand-checked standard formulas.
   "Exact is the gold standard" — no rounding-in of errors, because the tool may
   later be used with STplus or RIKOR alone.
3. **Cross-platform native runners** (no exe/host/Windows in between) so the
   whole pipeline ships in Docker (Linux/macOS/Windows). Wrappers around the
   original `.exe` exist only as an optional, non-default runner.
4. **English** everywhere in the code tree (code, comments, docs, Git); only the
   thesis under `../10_report/` is German.

---

## 2. Standards read and captured (basis for the native geometry)

All four DIN 3960-successor standards were read thoroughly; formulas were read
**visually from the rendered pages** (text extraction garbles math) and the
input-validity rules collected. Key results:

- **DIN ISO 21771:2014** — geometry chain (α_t, α_wt, d, d_b, d_w, a_w, form
  circles d_Fa/d_Ff, path of contact g_α, contact ratios ε_α/ε_β/ε_γ, tooth
  thickness, span). Tip chamfer: `d_Fa = d_a − 2·(z/|z|)·h_K` (eq. 127).
- **DIN ISO 1328-1:2018** — flank tolerances (pitch f_ptT/F_pT, profile
  f_Hα/f_fα/F_α, helix f_Hβ/f_fβ/F_β); grade step √2; rounding rules; the
  numeric **validity ranges** used as input checks.
- **DIN ISO 1328-2:2021** — double-flank composite (F_id/f_id); peripheral to us
  (a manufacturing QC method); runout F_r was removed from this edition.
- **DIN 21773:2014** — span measurement W_k over k teeth (eq. 14), the valid
  span-teeth range k_min ≤ k ≤ k_max, and the helical-feasibility check.

Contradictions/notes flagged: -1 and -2 use different grade-scaling laws (not
interchangeable); legacy runout F_r is no longer in ISO 1328; an STplus k must be
re-checked against k_min..k_max.

These are summarised for reuse in the agent memory files `iso21771-geometry-
formulas` and `iso1328-din21773-tolerances`.

---

## 3. Pipeline & remaining steps

The target pipeline (one lean app replacing the FVA-Workbench toolchain):

```
geometry (STplus) ─┐
                   ├─→ FE rolling model build ─→ Abaqus solve ─→ post-process ─→ evaluation/visualisation
load dist (RIKOR) ─┘            ▲ body sector (.stp), ≥30 roll positions, material modes (simple | cof)
```

### Step 0 — Base & I/O layer ✅
Repo, config (`.env`), storage/DB abstractions, HA layout, central logging/errors,
and the I/O layer: STplus `.ste` parser, REXS reader, Abaqus `.inp` keyword
editor — all pydantic-typed, tested. The native STplus geometry analysis and the
`.ste`/`.rexs` consistency check (ingest) are in place. Committed.

### Step 1 — STplus geometry, native (FVA 241 / ISO 21771 / DIN 21773)

| Sub-step | Scope | Method / standard | Validation | Status |
|---|---|---|---|---|
| 1a | `.ste` model: tool reference profiles, min tip clearance, tooth-width allowances, span teeth | parse documented keys | parser round-trip on kst-E | ✅ |
| 1b | **Tool generation (Verzahnen):** tip chamfer h_K from edge-break angle; tip/root form & usable circles d_Fa/d_Ff, d_Na/d_Nf; computed d_a when not given | ISO 21771 §7 generation + STplus tool construction | reproduce kst-E d_Fa=53.788, h_K=0.117, d_Nf | 🟦 |
| 1c | **Meshing geometry:** p_et, g_α, ε_α/ε_β/ε_γ, s_t/s_an, W_k; input-validity checks | ISO 21771 (62,77,90,93,97,38), DIN 21773 (14), ISO 1328-1 ranges | exact vs kst-E (table §5) + varied inputs through STplus | ⬜ |
| 1d | **Capacity (optional, later):** root/flank safety | DIN 3990 / VDI 2736 (plastics) | STplus standard tests | ⬜ |

The meshing chain (1c) is **hand-verified exact** already (see §5); it only needs
d_Na, i.e. h_K from 1b. Without the tip chamfer ε_α would be 1.248 instead of the
correct 1.154 (~8 % off) — so 1b is mandatory, not cosmetic.

### Step 2 — RIKOR load distribution, native (FVA 30) ⬜
Reimplement the face-/profile load distribution per the RIKOR Benutzeranleitung +
FVA 30 method (mesh stiffness, deflection, load sharing along the line of action),
output as REXS-compatible data. Validate against the RIKOR standard test cases and
varied inputs run through the original RIKOR. (REXS reader already exists.)
Done by the maintainer, not by sub-agents.

### Step 3 — FE rolling-model build ⬜ (released after Steps 1+2 are clean)
Build the quasi-static rolling Abaqus model in `model/` + `body/`:
- Rigid steel pinion as a **rigid surface** (+ reference node); plastic gear as a
  **symmetric sector** cut from the CAD `.stp`, coupled to the rim (per FVA 484).
- Whole pitches only: N pitches ⇒ N+1 complete teeth, rounded **up** (e.g. 3.6 → 4).
- **≥30 roll positions** covering A–E **including pre-/post-engagement** (deformation-
  extended contact, important for compliant plastic).
- Element-type convergence study (C3D8R vs C3D8I vs C3D20R) at one position.
- Material modes: **simple isotropic-nonlinear** (for model build) and
  **cof-mapped** (manual Converse hand-off; no Converse API yet).
- Implicit first; harden contact/initial increment/stabilisation; document a
  friction variant. Sub-agents may be used here **after explicit release**.

### Step 4 — Abaqus solve ⬜
Drive Abaqus 2025 via subprocess (`abq2025le`); odbAccess scripting runs in the
Abaqus Python 3.10 interpreter (not 2.7). Monitor energy balance (ALLSD/ALLIE/ALLAE).

### Step 5 — Own post-processing (decoupled, robust) ⬜  ← target of this roadmap
A standalone Abaqus-Python-3.10 extractor (template: `31_FVA/abaqus_postprocessing.py`),
**decoupled from FVA-Workbench names** so it does not break on every `.inp` change:
- Extract `S`/`LE` (maxPrincipal + mises), `CPRESS`, `U` → neutral **CSV/JSON** in `80_output`.
- Tooth-root tangent stress over the face width over A–E (**full field**, location not
  fixed a priori), tip deformation, flank pressures — per tooth, per roll position.
Acceptance: reproduces the FVA quantities on an unmodified WB run within tolerance,
**and** runs on a modified `.inp` without breaking.

### Step 6 — Evaluation & visualisation ⬜ (beyond this roadmap)
`evaluation/` derives the engineering results; `visualization/` + the modern
frontend (Anthropic-style, familiar to STplus/RIKOR users) present them.

---

## 4. Cross-cutting (already designed, applied as we go)
- One `.env` via `app.config`; files only via `app.storage`, data via `app.database`.
- Three independent analyses (`stplus | rikor | rolling`), each standalone, with
  pluggable runners (native default; exe/remote optional). See ADR-009/010.
- Stateless/multi-node assumptions; no node-local filesystem or in-process state.

---

## 5. kst-E gold-standard reference (regression target)

Project gear, STplus 11.0F output (`kst-E-ausgabe.sta`). Native geometry must
reproduce these exactly.

| Quantity | Pinion | Wheel | Native status |
|---|---|---|---|
| α_wt | 21.46251° | — | ✅ |
| d | 51.000 | 52.000 | ✅ |
| d_b | 47.924 | 48.864 | ✅ |
| d_w | 51.495 | 52.505 | ✅ |
| d_a (given) | 52.894 | 54.022 | ✅ |
| d_Fa | 52.894 | **53.788** | 🟦 (needs h_K, Step 1b) |
| h_K (tip chamfer, radial) | 0.000 | **0.117** | 🟦 (Step 1b) |
| g_α (path of contact) | 3.406 | — | ✅ hand-check (with d_Na) |
| p_et | 2.952 | — | ✅ |
| **ε_α** | **1.154** | — | ✅ hand-check (with d_Na) |
| s_t (nominal) | 1.719 | 1.800 | ✅ |
| W_k (k=6) | 17.090 | 17.180 | ✅ hand-check |

---

## 6. Key technical findings & open decisions

- **Tip chamfer h_K (Kopfkantenbruch) drives ε_α and is mandatory.** In kst-E it is
  **tool-generated** from the wheel tool's edge-break angle (α_K0 = 45°), not given
  as a number in the `.ste`. ISO 21771 treats h_K as a *given* radial modification
  (eq. 127) and does not provide a closed form from α_K0; STplus computes it in its
  tool-generation (Verzahnen) step. ❓ **Decision for Step 1b:** derive the exact
  STplus tool construction (render the STplus tool-reference-profile figures / the
  FVA 241 report) vs. accept a directly-specified h_K when available. Until 1b is
  exact, `from_ste` on a tool-chamfered gear yields the un-chamfered ε_α — so 1b is
  gating for full native exactness on such gears.
- **Tip diameter d_a:** given in kst-E; when absent STplus computes it from the tool
  (d_a = d + 2·m_n·(h_aP* + x), subject to tool/pairing compatibility). Same
  tool-generation module as 1b.
- **Tooth-thickness allowances:** STplus's s_an (0.777) and the span allowances
  include the tooth-width deviations (A_We/A_Wi). The nominal chain matches without
  them; the allowance refinement is part of 1c.
- **Converse cof:** no API → manual hand-off (load `.inp` material, map injection-
  moulding sim, export cof, embed into `.inp`). Modelled as a material **mode** in
  `model/`; automate later if an API appears.
- **Pinion/wheel safety:** the `(pinion, wheel)` `Pair` is now a named NamedTuple
  to prevent silent gear-1/gear-2 swaps while staying tuple-compatible.

---

## 7. How to run the checks (for review)

```bash
# Python lives in the Anaconda env (not on PATH):
PY="C:/Users/kuhnt/.conda/envs/semesterthesis_3-12/python.exe"
cd 20_code/40_backend
"$PY" -m ruff check . && "$PY" -m mypy . && PYTHONPATH=. "$PY" -m pytest -q
```
Current state: ruff clean, mypy clean, 42 tests pass.
