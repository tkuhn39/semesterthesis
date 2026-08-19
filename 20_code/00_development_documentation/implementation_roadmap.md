# Implementation status & roadmap — to completion of post-processing

This document is the single place to **follow and supervise** the implementation.
It records what is done and validated, and lays out every remaining step up to and
including the own post-processing, so work can be paused and reviewed at any point.

It complements, and does not replace:
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — the system design (config, storage, HA).
- [`architecture_decisions.md`](architecture_decisions.md) — the ADRs (why).
- The master plan in plan mode — the FE-modelling vision and trade-offs.

_Last updated: 2026-07-07 (v0.8.0) — rolling INP made physically correct end-to-end (per-position torque cycle, edge-tooth start, position-series default, rigid R3D4 Außenhülle per gear, per-gear tools + Kopfrücknahme in the FE contour) + backend-served pair assembly with ortho/CATIA viewport + Zahndicke mesh fineness + PairPanel SSOT + own postprocessing with the path-of-contact 3-D result viewer (ADR-022). Previously v0.4.1: deck conventions finalized for the cluster run (ADR-021 + amendment: STE-order slot numbering with gear 1 left/origin, mid-plane centring, axial offsets, torque conversion, Fesselung = bore + cut faces) + glossary panel. Step 3: transplant mesher + deck + mesh API + Next.js workbench done (ADR-019/020). Earlier: reference-grade tooth/root geometry +
transfinite mesh (boundary layer, deep rim, Jacobi ≥ 0.9) and the validated all-quad body-coarsening
template (ADR-017); 136 tests green._

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
| C6 | **Accuracy tolerances** `geometry/tolerances.py` (ADR-016) — ISO 1328-1:2018 grade → flank deviations (f_ptT…F_βT); `dynamics_deviations` drives the native dynamics from the quality grade; §1 validity | ISO 1328-1:2018 (eq. 5–12) | hand-verified (mn2/d100/b20/Q5); grade step √2; rounding bands | ✅ |
| C7 | **Free geometry → capacity** `GearStage.from_parameters` + `/api/evaluate` — build any pair from raw inputs + tool reference profile (no `.ste`), then geometry + ISO 6336 (steel) / VDI 2736 (plastic) capacity | ISO 21771 generation | reproduces kst-E exactly (ε_α, d_Fa incl. chamfer, Y_F, s_Fn) | ✅ |
| C8 | **Static peak load** `vdi2736.permissible_peak_stress` + wiring — σ_F,P = σ_F0·K_A,stat ≤ 2·σ_S/S_Smin (yield σ_S at operating temp, S_Smin≈1.5); opt-in via `static_overload_factor` + plastic yield; `peak_root_stress_mpa`/`peak_root_safety` | VDI 2736 Blatt 2 §3.3 (eq. 23/24) | formula hand-checked; unit + kst-E test | ✅ |

**Material-dispatch round (2026-08-18, ADR-026):** kind is THE dispatch end-to-end —
name↔kind coupled in the mask, Stufenvariation reads the live Werkstoff store and
dispatches the stress FORM per gear (steel → ISO Method B vectorized Y_F/Y_S at d_en;
plastic → VDI tip-load), VDI ϑ-model uses the plastic gear's z (norm symbol list),
density inputs live, glossary grown to ~200 current-norm entries (new "inspection"
category). Open P2: per-gear material objects for same-kind pairs, deck cards from live
overrides, variation re-seed scope, served material catalog.

**Audit round P1 (2026-08-18, ADR-025):** all analytical-correctness findings of the
consistency audit fixed — helical factors live per norm branch (ISO 2019 vs VDI/DIN 3990
conventions), Y_X Table 5 un-scrambled, VDI safeties TRUE (σ_lim/σ, σ_P explicit),
**K_Hβ Method C native** (F_βx per ISO 6336-1 §7.5 from the quality grade or shaft data;
kst-E @ Q7 → K_Hβ ≈ 1.12), Dynamikfaktoren ≡ Tragfähigkeit (shared request base),
material group/HB/density per gear, spur-only paths guarded (422), f_HαT + 0.001·d,
deck fillet interference check. 256 backend tests.

**Audit rounds ADR-026/P2 (2026-08-18, ADR-026/ADR-027):** material kind is THE dispatch
end-to-end (per-gear norm branches in the sweep with vectorized ISO Y_F/Y_S at d_en,
coupled Werkstoffname↔art, glossary as vocabulary SSOT ~200 entries) and every
tab-visible input has ONE store home: deck material cards follow the Werkstoff tab
(Marlow curves stay catalog data), served catalog + three-way drift guard, ONE
fillet/density state (Zahnform/Netz/Deck/Report identical), ONE accuracy grade
(Toleranzen → capacity), one micro-geometry source (correction tab; Auslegung mirrors),
allowance BAND effective incl. example mode, FE sets/refine bands/ξ-markers
junction-aware (Landi). 260 backend tests.

**Audit round P3 + per-gear Flankenmodifikation (2026-08-18, ADR-028):** wheel-side
modification node [41] (full editor per gear via schema binding-remap), C_a live in the
K_v chain, Ra→Rz/ϑ₀/K_A,stat switches functional, Übersicht follows the active stage,
tab ↔ HTML report field parity (factors, norm rows, ISO 1328-1 components, pair rows,
W_zul/λ, undercut verdict), variation names its swept parameters, W_k single-sourced.
NOTE (audit COV-10/11): `services/loaddist` + `io/rexs`/`services/ingest` are
INTENTIONALLY unrouted — Step-2 (RIKOR) groundwork, not dead code.

**Audit round P4 (2026-08-18): the audit is fully worked off** — display clipping,
fillet UX, wiring LOWs (two-gear ISO 1328 check, D_M inputs, live Meldungen, regime
i18n, working-a header, routed overview cards) and contract hygiene (diagnostics-only
CAO response, memoized effectiveStage, chamfer-aware CAO cache, per-gear flank symmetry
into the deck). Deferred to a later architecture-cleanup round: STR-05/06/07, STR-15,
FEM-09, GAP-10 rest (see the audit banner). Next packages: **helical geometry report**
(pair rows already display-ready), scuffing (ISO/TS 6336-20/-21), catalog-served
uimodel options; twisted extrusion after the FE reference reproduction.

**Helical geometry report (2026-08-19, ADR-029):** the SSOT geometry service computes
helical stages natively — DIN 21773 helical forms in every inspection block (chordal
Eqs. 1–8, span count Eqs. 10/12/13, W_k Eq. 14, ball/roller measures Eqs. 30–36 + §11,
allowance factors §14, b_Fmin measurability note), backlash per ISO 21771 Eqs. 102/103;
ToothProfile removed from the report path (closed transverse-plane forms, kst-E spur
literals bit-compatible); NRM-01 closed (`/api/geometry/report` + HTML report render
helical; the 2-D mesh SVG degrades to a note). FE/contour chain stays spur-only per the
user's scope cut ("noch nicht in Richtung FEM"). 268 backend tests. Next (user-approved
order): **material database** (definable materials, per-gear selection, session-local
edits), **session save/load** (export/import + sidebar recall); then scuffing /
architecture cleanup / FE helical as separate packages.

**User material database (2026-08-19, ADR-030):** persistent user-definable materials
via app.storage (one JSON per record, built-ins immutable), CRUD API + served catalog
as the one SSOT, per-request `mat_name` schema options, frontend Werkstoffdatenbank
section (create/edit/delete/apply per gear); selecting a material loads its values into
the session-local Werkstoff fields — edits never write back. Known follow-ups: per-gear
property objects for same-kind pairs; measured curves on library records for the FE
deck. 272 backend tests. Next: **session save/load** (export/import + sidebar recall).

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

### Step 3 — FE rolling-model build 🟦 (in progress — reference reproduction, `ohne_Radkoerper`)
**Progress (2026-07-03, ADR-019):** the 2D sector mesh is **solved** — the reference topology is
mined from the deck (committed template + pin tests) and transplanted onto our validated geometry:
topology-identical to ANSA (one fan node per gap, 3024 quads/sector), min scaled Jacobian 0.45 with
0 cells < 0.35 (reference: 0.243/24), teeth exactly rotation-congruent, mirror symmetry gated by
`is_flank_symmetric`. Parametric density (root/flank chord splits) + native 2D quick solver for
convergence checks (reference density already converged, Δ < 0.1 %). Optimized root fillets
(elliptic/Bézier/bionic, supervisor topic) mesh through the same pipeline with interference check.
**Done (2026-08-05, ADR-023):** ALL SEVEN literature fillet approaches native
(`FilletSpec(kind, approach)`): elliptic kassem/**fruehe** (supervisor priority, closed-form
tilted ellipse, −20.9 % on kst-E)/landi, bezier roth/dong (true hobbing envelope
`rack_tip_envelope`), bionic voith/cao (Kassem 2023 growth loop on the quick-FE solver);
per-approach sweeps incl. the previously missing γ axis, Stufenvariation carries the full
FilletSpec, contour reports the effective root diameter.
**Done (2026-08-05, ADR-024):** full geometry output on CURRENT norms — the SSOT service
`compute_geometry_report` (DIN ISO 21771 + NB, DIN 21773 §5–§14 inspection measures with
auto span tooth count and exact ball-measure allowances, DIN 3967/3964 backlash chain),
`POST /api/geometry/report`, grouped result sections in the Geometrie tab (fillet-aware
effective root), extended capacity response (K_Fα/K_Fβ/Z_ε/Z_B/Z_D/F_t/v/z_n + σ_H0/σ_F0 +
30°-tangent section values) with the native-K_Hβ bugfix, HTML report carries the same rows;
kst-E parity pinned (27 .sta literals). **Open:** scuffing per ISO/TS 6336-20/-21 (sources
in repo), explicit Z_L/Z_v/Z_R/Z_W/Z_X + Y_relT sub-factor exposure, DIN 3967 series tables.
User-reviewed at checkpoints 1+2. **Done since (v0.2.0, checkpoints 3):** deck rewired onto the
transplant mesher (mapped_mesher retired from the deck path), rigid-shell material rule for mixed
pairings, Part_Rad_Vz_1 = plastic wheel convention, /api/mesh router (preview/3d/convergence/
fillet-compare/contour/deck) and the Next.js workbench UI (ADR-020) with the three.js mesh
viewport, tooth-form and variation-overlay panels. **Done (v0.3.0):** capacity/dynamics panels, FZG presets + STE
import + free StageParams across all mesh/deck endpoints, fillet-sweep axis (quick-FE
objective), trochoid strategy, micro-geometry data model (ISO 21771 §6), material matrix,
pair viewport with DOF triads, frontend swap (Next.js is `50_frontend`; Docker without
OpenGL). **Done (v0.4.0, ADR-021, user review of the pair):** deck gear numbering follows the
stage input order (gear 1 = steel pinion z51, gear 2 = plastic wheel z52; the FVA deck is the
reverse — header comment table documents the mapping), per-gear face widths with mid-plane-
centred extrusion (z = ±b/2) + parametric axial offsets, rotation nodes at mid-width, wheel
torque converted to the pinion (T₁ = M₂·z₁/z₂), deck material matrix (steel/plastic per gear),
contour completed across the root land, filterable parameter glossary panel (75 entries,
DE/EN). **Done (v0.4.1, ADR-021 amendment, user decisions):** Fesselung parity closed —
`Fesselung_Rad{g}` ties bore + both radial sector cut faces exactly like the reference deck
(verified numerically); rig-view slot convention — gear 1 (first .ste gear) at the origin/
LEFT, gear 2 at the centre distance/RIGHT in deck and 3D pair view, per-gear inputs strictly
keyed by input slot (never re-ordered by role/tooth count), deck request fields renamed to
gear1/gear2 names, angle/torque/slave roles follow the material (plastic side driven).
**Done (v0.5.0, ADR-021 second amendment, measured ground truth + user report):** the deck
starts in **single-flank contact** like the reference (backlash-closing rotation of gear 2 by
exact rotational collision detection; kst-E 243 µm centred backlash → 21.9 µm on the −y flank,
angle in the deck heading) and the **Fesselung is a coordinate predicate over ALL nodes**
(bore + both complete cut planes to d_f/2; FVA checkboxes as `fasten_*` writer flags);
`10_verifiers/verify_deck_parity.py` asserts both against the reference INP. Single source of
truth: shared `StageParams` (`app/api/stage_params.py`) behind every endpoint, material
catalog (20MnCr5 + Stanyl TW200F6 incl. Marlow curve) feeding analytics AND deck, norm
dispatch per gear by MATERIAL (steel → ISO 6336, plastic → VDI 2736). FVA-replica foundation:
label extraction from the installed Workbench, pydantic editor schema (`app/services/uimodel`)
at `/api/ui-schema`, FVA-style shell (tree → tab bar), Berechnungsauswahl matrix driving tab
visibility (FVA 892 → "Dynamisches Abwälzen (FEM)" tab with deck download).
**Done (v0.6.0, user review loop with self-screenshots):** FVA replica completed tab-by-tab
against the 27 reference screenshots — remaining Getriebeeinheit tabs (Leistungsfluss with
Antrieb/Abtrieb lock rules, Kräfte und Momente, Betriebsdaten, Steuerparameter), Stirnradstufe
tabs (Toleranzen DIN 3967/3962 with computed A_We/A_Wi, Tragfähigkeit FVA layout, VDI 2736,
Werkstoff, Schmierstoff, Lastverteilung (FEM)), Flankenmodifikation [34] (5 tabs) and
Radkörper Stirnrad [40], Ergebnis-Schnellansicht (ISO 21771, live d_w = FVA values), instance
IDs `[n]` as store data, Achsabstand-Modus lock rule (DIN 21771), 2D FE mesh rendering
(`/api/mesh/preview` as quality-coloured SVG), Zahneingriff animation (real as-cut contours,
kinematically coupled), Stufenvariation as the guided FVA 4-step flow (persistent results in
the store — back-navigation without recompute; Fußform + material matrix as variation
attributes; Übernehmen writes the variant into the shared stage; parallel-coordinates
selection keeps colour, rest greys out), and the i18n completion (DE = FVA wording, EN
complete; ONE locale-aware number format via `useFmt`).
**Done (v0.7.0, user-feedback round):** powerflow SSOT rebuild — ONE system torque entered
on either shaft (other side derived via z₁/z₂ and locked; clearing resets both; store
computes from the raw input so kst-E deck parity stays exact), Antrieb/Abtrieb mutually
exclusive, shaft-1/2 naming in the load tables (tree keeps FVA instance IDs for later
multi-stage systems — real IDs from the plant then, not from screenshots); Dynamik +
Stufenvariation read T₁/n₁ from the Leistungsfluss (last 7.85-copies removed).
Stufenvariation: b₂/h_aP*/h_fP*/ρ_fP* sweep per gear for real (kernel per-gear widths +
reference profiles, min(b,b₂) flank semantics), sample_count user-controlled (Sobol
rounds up to 2^n with warning). Zahneingriff: mesh-zone zoom with the exact line of
action T1–A–B–C–D–E–T2 (backend `line_of_action_points`, verified against the FVA
Gesamtsystemreport coordinates within 2 µm). Interactive HTML system report
(`POST /api/report`, self-contained + printable, animated mesh plot, per-gear norm
sections WITHOUT placeholder rows — better than FVA for mixed pairs, optional variation
section from the persisted run).
**Done (v0.8.0, user-feedback round — the rolling INP made physically correct + the result
pipeline):** the dynamic-rolling deck is now reference-faithful end-to-end. Load case: a
per-Wälzstellung torque cycle (angle side held, torque side SMOOTH-STEP base→full→base, first
ramp from 0, measurement at the full-torque hold; `ALLSDTOL=0`, `*RESTART`, `*TIME POINTS`
per-flank-set outputs), roll **starts at an edge tooth** so the middle teeth sweep the whole
engagement boundary-free, sweep-union contact pairing reproduces the reference's 7 pairs,
Drehrichtung from the Leistungsfluss. Default deck mode = **position series** (one independent
static INP per Wälzstellung; path-independent Marlow+frictionless ⇒ result-identical, robust,
parallelisable; shared `*INCLUDE` mesh + `manifest.json` + runners). Rigid **Außenhülle per
gear** = R3D4 lateral shell (tooth contour + cut faces + bore swept, axial end faces open,
massive element reduction). Geometry: **one tool per gear** (kst-E h_aP0* 1.1/1.25, wheel-only
45° Kantenbrechwinkel), **Kopfrücknahme C_αa in the FE contour** (like the FVA transient FEM),
per-gear root fillet before pairing, chamfer verifier (gear 1 no chamfer, gear 2 h_K=0.117).
Viewport: the pair assembly comes from the backend (`/api/mesh/pair`, exact deck positioning +
roll schedule), orthographic camera + CATIA mouse controls (free 360°). Mesh fineness: the FVA
quartet per gear (Zahnfuß/Zahnhöhe/**Zahndicke**/Zahnbreite) with effective per-tooth counts +
2D quick-convergence preseed. SSOT: PairPanel fully on the store, ONE `deckPayload()` builder,
resizable split panes that never clip. **Result pipeline (ADR-022):** own Abaqus-Python
postprocessing (against our sets, neutral `fem_results.json`), `POST /api/fem/results` unwraps
r→path-of-contact ξ from the GearStage, and the "Ergebnisse (3D)" tab renders per contact
flank pair a three.js surface (ξ × face width × σ/ε/CPRESS/|u|, A…E markers, Wälzstellungs-
slider, maxima flagged, range beyond A/E to d_Nf…d_Na). Step 5 (own postprocessing) now has
a native path; remaining is the live-cluster validation of the dump against a real solve.
**Still open:** DIN 3967/3964 tooth-thickness/centre-distance allowance system (full norm
tables), protuberance tool variant (DIN 3960 Anhang A), micro-geometry mechanics (load
distribution).

**Progress (2026-06-24, ADR-017):** Native STplus geometry → FE deck pipeline stands. Tooth/root
geometry is **reference-grade**: clean rounded ρ_F root fillet (`tooth_form.transverse_right_boundary`),
transfinite mesh fed that boundary with a fine **surface boundary layer** + radially graded **deep
rim** to the real bore, Jacobi-Güte ≥ 0.9, CCW winding fixed. The reference **all-quad 4→2 body
coarsening template** (the circumferential fan) is designed + validated standalone (|Jacobi| 1.0).
Deck generator (`implicit_deck.py`, `materials_card.py`, `mesh_sets.tag_gear_reference`) produces the
reference set/surface naming + Marlow/steel materials + single staircase step. **Still open (Workstream
C):** the `.ste` conventions in the deck (Part_Rad_Vz_1 = wheel z52/PA/b15, Vz_2 = pinion z51/steel/b17),
Fesselung = radial cut faces (lateral hold), z-centring, and the torque convention (M_wheel·z51/z52 on
the pinion). Live Abaqus solve runs on the user's cluster (locally node-limited).

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

### Step 5 — Own post-processing (decoupled, robust) 🟩 native path stands (v0.8.0, ADR-022)
A standalone Abaqus-Python extractor (`app/services/model/postprocessing/
abaqus_fem_postprocessing.py`, shipped with the deck), **decoupled from FVA-Workbench names**:
- Works against OUR sets (`G{g}T{ttt}F{f}`, `Rot_Node_Rad{g}`), NOT the frozen script's
  `REFERENCE_POINT_`/text files; auto-detects measurement frames (the `S`-carrying
  `*TIME POINTS=MEASURE` holds) and reads `manifest.json` for the series roll angles.
- Dumps a neutral **`fem_results.json`** (schema `zahnfuss.fem_results/1`): per frame, per
  flank set, per surface node the radius, axial z, S/E mises+principals, CPRESS, |U|.
- `POST /api/fem/results` unwraps r → path-of-contact ξ from THE GearStage (SSOT) with the
  A…E markers + extended d_Nf…d_Na range; the "Ergebnisse (3D)" tab renders the flank
  surface (ξ × face width × field) with a Wälzstellungs-slider and the maximum flagged.
Remaining (real solve): validate the dump against a live Abaqus run of the series on the
user's cluster and reproduce the FVA quantities within tolerance.

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
