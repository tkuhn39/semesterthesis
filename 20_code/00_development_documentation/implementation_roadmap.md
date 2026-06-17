# Implementation status & roadmap — to completion of post-processing

This document is the single place to **follow and supervise** the implementation.
It records what is done and validated, and lays out every remaining step up to and
including the own post-processing, so work can be paused and reviewed at any point.

It complements, and does not replace:
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — the system design (config, storage, HA).
- [`architecture_decisions.md`](architecture_decisions.md) — the ADRs (why).
- The master plan in plan mode — the FE-modelling vision and trade-offs.

_Last updated: 2026-06-17 — Step 1 (native STplus geometry) complete and exact vs STplus._

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
| 1b | **Tool generation (Verzahnen)** `generation.py`: x_E (§7.4), root form circle d_Ff, tip chamfer h_K & tip form circle d_Fa via the two-involute construction (usable ∩ edge-break involute) | ISO 21771 §5/§6/§7 involute primitives (cross-checked vs DIN 3960 A.3.1) | exact vs kst-E: x_E, d_Ff, d_Fa=53.788, h_K=0.117, s_aK | ✅ |
| 1c | **Meshing geometry:** d_Na, p_et, g_α, ε_α/ε_β/ε_γ, W_k; input-validity checks | ISO 21771 (77,90,93,97), DIN 21773 (14), ISO 1328-1 ranges | exact vs kst-E (table §5) | ✅ |
| 1d | **Materials** `materials.py`: steel (DIN 3990) + plastic (VDI 2736), graceful on missing optional fields; **nonlinear x–y measured curves** + Matscape card import (Matscape later) — also used by RIKOR/STplus/FE | — | loads kst-E PA66 / 16MnCr5 | ✅ (linear); curves/Matscape ⬜ |

Step 1 (native STplus geometry) is **complete and exact vs STplus** for the project
gear: the tip chamfer h_K (Kopfkantenbruch) is generated from the tool edge-break
flank, so d_Na carries it and ε_α = 1.154 matches STplus (without the chamfer it
would be ~1.25, ~8 % off). All computation rests on current-standard ISO 21771
primitives; DIN 3960 was used only to cross-check the construction (not as a basis).
Remaining for full coverage: helical/internal cases, more standard-test inputs.

### Step 1.5 — Capacity & plastic-capable Stufenvariation (macro pre-design)
The analytical macro-geometry layer *before* the FE work, and a clear advantage over
the FVA-Workbench (whose Stufenvariation fails for plastic gears). Decision & full
performance strategy: **ADR-013**; current-standards rule: **ADR-011**.

| Sub-step | Scope | Method / standard | Validation | Status |
|---|---|---|---|---|
| C1 | Tooth-root geometry `tooth_root.py`: 30°-tangent s_Fn, ρ_F, h_Fe, α_Fen + form factors Y_F, Y_S | DIN 3990 T3 / ISO 6336-3 (generation trochoid, x_E) | exact vs kst-E: s_Fn* 2.068/2.197, ρ_F* 0.404/0.381, Y_F 2.417/1.970, Y_S 1.819/1.984 | ✅ |
| C2 | Capacity **stress core** `capacity/` (→ rename `iso6336.py`): σ_H/σ_F, Z_E/Z_H/Z_ε exact; K- and life-factors still **fed** (so σ_H/σ_F validate the assembly, not yet the factor *computation*) | ISO 6336:2019 / DIN 3990:1987 | stresses exact vs kst-E (σ_H 99.6, σ_F 180.1) | ✅ (stresses) |
| C2b | **End-to-end**: native K_v, K_Hα, K_Hβ (C/D), Z_B/Z_D, and the permissible-stress life/sub factors (Z_NT, Y_NT, Y_RrelT, Y_δrelT, Y_X, Z_X, Z_W) → σ_HP/σ_FP and **S_H/S_F native** (de-circularised); helical (z_n, β_b, Z_β, Y_β) | ISO 6336-1/-2/-3/-5 (2019) | **helical** ISO-6336 ref (S_H=1.044, S_F=2.275/2.309, Z_NT=0.85, Y_RrelT=0.915) **and** kst-E (S_F=4.571) | ✅ |
| C2b-dyn | Native dynamics `iso6336_dynamics.py` (ADR-014): mesh stiffness c′/c_γα (E-corrected for plastic), m_red, resonance ratio N, **K_v Method B**, K_Hα/K_Fα, **K_Hβ/K_Fβ Method C** (F_βx from RIKOR) | ISO 6336-1 (2019) | helical components locked (C_B 0.95, c_γα 17.21, N 0.163); K_v 1.034 (ref 1.05), K_Hα 1.143 (ref 1.18) in-band — grade not reported (ADR-011) | ✅ |
| C3 | **VDI 2736** capacity (plastic) `vdi2736.py`: σ_H/σ_F (tip-load Y_Fa/Y_Sa), tooth temperature ϑ, wear W_m, deformation λ, loss factor H_V | VDI 2736 Bl. 2 (2014) | VDI-2736 Workbench report (= kst-E pair), near-exact: σ_H 79.9, σ_F 77.8, ϑ 107.77, W_m 40.16 µm, λ 0.0378 — ADR-015 | ✅ |
| C4 | **Stufenvariation engine** `variation/kernel.py` — vectorized grid (macro-geometry, tip-load Y_Fa/Y_Sa, capacity) + early pruning; per-gear material dispatch (steel↔plastic) over the shared mesh (ADR-013) | numpy batch | bit-exact vs scalar (kst-E); **98k variants / 165 ms** | ✅ |
| C5 | `variation/sweep.py` — Sobol/LHS sampling (scipy.qmc) + Pareto front + graceful warnings | ADR-013 | grid=cartesian, samples in-bounds, Pareto/pruning/graceful tested | ✅ (NSGA-II evolutionary search = outlook) |

Validation philosophy (ADR-011): implement **strictly per ISO 6336:2019** (the current
standard; DIN 3990:1987 is the equivalent cross-check, what STplus uses). Two complete
references: **kst-E** (spur, DIN 3990 via STplus) and the **helical ISO-6336 case**
(`31_FVA/Helical_…_Gesamt.pdf`, see memory [[din3990-helical-reference]]). Where a
reference tool deviates from a norm-correct result, the norm wins.

**Outlook (recorded, not yet built):** (a) **i18n** — switch the tool/reports to English at a
button press (domain identifiers are already English; ISO 6336 EN is the vocabulary).
(b) **Material pairings** in the Stufenvariation — steel/steel, plastic/plastic and
steel/plastic, via the per-gear capacity-method dispatch over a shared mesh (ADR-013).

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
| d_Fa | 52.894 | **53.788** | ✅ (native, `generation.py`) |
| h_K (tip chamfer, radial) | 0.000 | **0.117** | ✅ (native) |
| x_E (generation profile shift) | −0.2030 | 0.0117 | ✅ |
| d_Ff (root form) | 49.081 | 50.158 | ✅ |
| rest tip thickness s_aK | 0.672 | 0.634 | ✅ |
| g_α (path of contact) | 3.406 | — | ✅ |
| p_et | 2.952 | — | ✅ |
| **ε_α** | **1.154** | — | ✅ (with d_Na) |
| W_k (k=6) | 17.090 | 17.180 | ✅ |

---

## 6. Key technical findings & open decisions

- **Tip chamfer h_K (Kopfkantenbruch) — SOLVED.** It is **tool-generated** from the
  wheel tool edge-break flank (α_K0 = 45°), not given in the `.ste`. d_Fa is the
  intersection of the usable involute and the **edge-break (Kantenbruch) involute**
  (base d·cos α_tK); solved by iteration. This is pure involute geometry built from
  ISO 21771 primitives (§5/§6/§7) — cross-checked against the DIN 3960 A.3.1 worked
  form (withdrawn → understanding only, **not** a computational basis, per the
  current-standards requirement). Reproduces STplus exactly (h_K=0.117, d_Fa=53.788).
- **Standards constraint:** computation must rest only on current standards (ISO
  21771 / 21773 / 1328-1/-2); withdrawn norms (DIN 3960, 21772) are cross-checks only.
- **Tip diameter d_a:** given in kst-E; when absent STplus computes it from the tool.
  Not yet implemented natively (all our `.ste` inputs give KOPFKREISDM) — add to
  `generation.py` when an input without d_a appears.
- **Generation profile shift x_E:** `x_E = x + A_sn/(2·m_n·tan α_n)`, A_sn = A_We/cos α_n
  from the `.ste` span allowances — drives the as-cut tooth thickness and the form
  circles. Validated exact (−0.2030 / 0.0117).
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
Current state: ruff clean, mypy clean, 49 tests pass.
