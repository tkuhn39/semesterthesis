# Changelog

All notable changes to this project's FE / analysis toolchain (under
[`20_code/`](20_code/)) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Dates are ISO 8601 (YYYY-MM-DD).

## [Unreleased]

### Changed (rolling deck load case — user feedback round 2026-07-06, phase A)
- **Per-position torque cycle** replaces the constant-torque staircase
  (`RollKinematics` + `_torque_cycle_pairs`): the angle-driven gear is HELD at each
  Wälzstellung while the torque gear ramps base→full (`ramp_up`), holds at full
  (`hold`, measurement at the END — Newton equilibrium each increment, STABILIZE
  energy decayed), ramps back to the **base fraction** (default 1 % of the powerflow
  torque — flanks stay seated, no free spin; the very first ramp starts at 0), and
  only then the angle sub-ramps to the next position (`move` increments). This is
  what the FVA reference deck does (its AMP-TORQUE alternates −78.5/−7846.2).
- **SMOOTH STEP amplitudes** (`*AMPLITUDE, DEFINITION=SMOOTH STEP`): zero slope at
  both ends of every ramp — gentle contact seating at low torque, no overshoot at
  full torque (addresses the user's convergence aborts at high torque).
- **Roll starts at an EDGE tooth** (`start_at_edge`, default on): the pair is
  pre-rotated ±roll/2 (kinematically coupled) so the sweep walks the contact across
  the sector and the MIDDLE teeth complete the full engagement boundary-free;
  `roll_pitches` default 3 (gear-1 tooth T1 has no working partner in the window).
- **Sweep-union contact pairing** (`_sweep_contact_pairs`): flank centroids are
  rotated through the whole coupled roll and every pairing found becomes a
  `*CONTACT PAIR` — reproduces exactly the reference deck's **7 pairs** (working
  F2 g1-i↔g2-(6−i), back F1 g1-i↔g2-(5−i)); proximity-at-t0 had found only 6.
- **Reference-parity outputs**: `*STATIC …, ALLSDTOL=0.0, CONTINUE=NO`;
  `*RESTART, WRITE`; `*TIME POINTS, NAME=MEASURE` (exact full-torque equilibrium
  instants, hit exactly by Standard) with the full per-flank-set payload (NODE
  CF/RF/U · CONTACT CFORCE/CSTRESS/CDISP · ELEMENT E/MISESMAX/…/S per
  `G{g}T{nnn}F{f}` set + MASTERKNOTEN + global U) plus a cheap all-increment
  animation request (U only); measure table also in the deck header.
- **Drehrichtung** (`rotation_sense` cw/ccw, from the Leistungsfluss "Drehrichtung
  Welle 1" dropdown — new schema row): mirrors roll sign, closing flank and start
  offset consistently.

### Added (position series — the new default deck mode)
- **`POST /api/mesh/deck-series`** (+ `build_position_series`): one INDEPENDENT
  static INP per Wälzstellung — legitimate because the model is path-independent
  (Marlow hyperelasticity + frictionless contact) — robust against convergence
  aborts (one failure costs one position) and trivially parallelisable. ZIP layout:
  `pair_common.inp` (shared mesh via `*INCLUDE`, positioned per file through
  `*INSTANCE` rotation lines — 252 kB instead of ~30 full decks), `pos_NNN.inp`,
  `manifest.json` (angles/torque/files for the postprocessing), `run_all.bat/.sh`.
  The Dyn-Abwälzen tab gets a "Berechnungsmodus" dropdown (series default); both
  frontend download paths share one payload.

### Added (rigid Außenhülle — phase B)
- **R3D4 lateral shell per gear** (`build_rigid_shell` + `rigid_shell_gear1/2`,
  schema row "Ideal steife Außenhülle" per gear): an ideally stiff gear is no longer
  a full solid declared rigid (the ANSA finding — every face constrained, zero
  element reduction) but its **lateral boundary surface only** — tooth contour, both
  radial cut planes and the bore swept over the width, axial end faces OPEN — as
  R3D4 rigid elements about the rotation node. Nodes renumbered to the boundary
  (kst-E: 3 042 vs 16 647 solid nodes at 4 layers), no section/material card, no
  Fesselung nset, contact surfaces uniformly `ELSET, SPOS` (outward by the CCW-edge
  orientation proof); ELEMENT/CONTACT measurement outputs skipped on the rigid side.
  The contact slave (plastic side) must stay deformable (422 otherwise); the legacy
  `steel_shell` shortcut maps onto the steel slot.

### Added (per-gear geometry — phase C, user points 5/6)
- **One tool reference profile per gear** (`StageParams.tool_*_gear2` overrides,
  None = same as gear 1): the free-parameter path now matches the .ste ground truth
  (kst-E: h_aP0* **1.1/1.25**, ρ_aP0* 0.2, 45° Kantenbrechwinkel ONLY on the wheel
  tool → h_K 0/0.117 mm). The .ste importer fills both tools, the Geometrie tab
  renders h_aP0*/ρ_fP*/h_fP0*/h_FfP0*/α_Kn0 per gear, the Stufenvariation
  "Übernehmen" writes h_fP*/ρ_fP* per gear, and the frontend kst-E snapshot carries
  the true per-gear values (was: a single 1.25/0.38 tool for both).
- **Kopfrücknahme C_αa in the FE contour** (like the FVA transient FEM, ADR-012
  amendment): `ToothProfile.from_stage(…, tip_relief_um, tip_relief_start_diameter_mm)`
  applies the relief as an angular reduction δ/(r·cos α_y) ramping linearly from d_Ca
  (default d_Na − m_n) to the tip — contour preview, Zahneingriff plot, mesher
  reprojection, deck assembly and collision alignment all inherit the SAME modified
  boundary (SSOT). Values flow from the Flankenmodifikation editor
  (`tip_relief_dca_mm` now sent as `tip_relief_start_diameter_mm`) via
  `StageParams.tip_relief()`; symmetric flanks only (asymmetric relief stays carried).
- **Root fillet per gear in the pair view**: full `FilletEditor` (strategy +
  parameters) for gear 1 AND gear 2 BEFORE "Paar erzeugen" — drives the preview mesh
  and the deck identically (`fillet_gear1/2`); gear 1 was hard-coded "standard".
- **Verifier tip-geometry checks** (user point 5c, measured not assumed): gear 1 cuts
  NO chamfer (d_Na = d_a — its look is the Kopfrücknahme), gear 2 h_K = 0.117 mm,
  both gears' mesh flank sets end at d_Na, and C_αa = 8 µm pulls the tip flank back
  by ≈ C_αa/cos α (8.83 µm measured).

### Added (viewport parity — phase D, user points 1–3)
- **`POST /api/mesh/pair`**: THE deck assembly for the viewport — runs the deck
  builders' own `assemble_centered_pair` (fillets, tip relief, rigid R3D4 shells,
  closing rotation, sweep contact pairing) and returns the outer hulls in absolute
  assembly coordinates plus the per-gear angle law (edge start + kinematic coupling)
  and the contact-pair list. The PairViewport's local positioning math (half-pitch
  heuristic, no closing rotation — the "gears don't touch" report) is deleted;
  preview and .inp share one payload builder in the panel.
- **Roll slider = real Wälzstellungen**: position k over the deck schedule
  (1 … n, measurement points marked, φ from the backend angle law) instead of a
  free ±15° angle.
- **Orthographic camera + CATIA mouse controls** (shared `CatiaControls`) in the
  pair AND mesh viewports: MMB drag = pan, MMB+LMB/RMB = quaternion free-tumble
  (full 360°, no polar clamp), wheel = ortho zoom; middle-click autoscroll
  suppressed. Rigid-shell gears render as semi-transparent open mantles.

### Added (mesh fineness per gear — phase E, user point 7)
- **New chord group "über Zahndicke"** (`refine_thickness`, ADR-019 mesher): conformal
  chord splits seeded ONLY at the flat tip land — those chords run tangentially down
  through the whole tooth, multiplying the elements over the tooth THICKNESS. Chamfer
  edges are deliberately excluded from the seeds (they cut the 45° corner cells into
  slivers — measured SJ 0.22 on kst-E gear 2; land-only seeding keeps min SJ ≈ 0.45,
  zero sub-gate cells at factors 1–3 on both gears).
- **Per-gear fineness in the deck** (`refine_gear1/2 = (root, flank, thickness)`
  through `assemble_centered_pair` and both deck builders; `DeckRequest` gains
  `refine_thickness` + `refine_{root,flank,thickness}_gear2` overrides — plain fields
  keep applying to both gears).
- **FVA mesh-fineness dialog in the pair view**: per-gear factor table (Elemente am
  Zahnfuß / über Zahnhöhe / über Zahndicke; Zahnbreite = shared layers) with the
  EFFECTIVE per-tooth element counts (counted on the final mesh: one gap rounding,
  one flank, the tip land — new `elements_root/flank/thickness` in
  `/api/mesh/preview`); FE-Mesh tab gets the thickness factor + effective row too.
- **2D quick-convergence preseed per gear**: one button per gear runs the native
  plane-FE convergence for root AND flank and preseeds the factors with the
  converged level.

### Changed (PairPanel SSOT + layout — phase F, user "Felder/Einheit verschluckt")
- **PairPanel fully on the store**: face layers, per-gear fineness factors
  (root/flank/thickness), roll positions, rigid-shell flag, axial offsets and both
  root fillets moved out of panel-local `useState` into `fem.*` — the Dyn-Abwälzen
  tab and the pair view now edit the SAME values. A new `lib/deck.ts` `deckPayload()`
  is THE single request builder; the SchemaTab action and the pair view both call it,
  so identical settings yield byte-identical decks (no more divergent deck paths).
- **Resizable split panes with a min-width lock** (`components/SplitPane.tsx`): the
  model tree, the Ergebnis-Schnellansicht and the viewport panels (PairPanel,
  MeshPanel) get a draggable divider that CLAMPS at the content minimum — the user's
  "Fenster verschieben, aber ein Block, dass man nicht mehr verkleinern kann".
- **Never clip values/units** (user report): `Section` bodies and the QuickView table
  wrappers switched from `overflow-hidden` to `overflow-x-auto` (content scrolls
  instead of being cut by the rounded-corner clip); the ×1/×2/×3 fineness dropdowns
  use a narrow `.sel-narrow` variant so the per-gear column pairs fit without pushing
  units out of the pane; the roll-slider caption moved above the track.
- Verified by own Playwright screenshots (`shot-pair.mjs`, `shot-femesh.mjs` +
  the 27-view `self-screenshots.mjs`): per-gear fineness table with ≙ effective
  counts, closed assembly in the viewport, no swallowed fields/units.

### Fixed
- Powerflow torque reset: entering **0** (not only clearing) now frees both shaft
  fields again (user report).
- PairPanel deck download no longer uses a panel-local M₂=20000: the torque comes
  from the Leistungsfluss (SSOT), incl. Drehrichtung/fasten/align flags.

## [0.7.0] - 2026-07-05

User-feedback round after v0.6.0: powerflow SSOT rebuild (one torque on either shaft,
exclusive load types, shaft-1/2 naming), per-gear variation parameters + controllable
sample count, mesh-zone zoom with the exact line of action (FVA-reference-verified),
and the interactive HTML system report. Gates: 189 backend tests, deck-parity verifier
incl. `--reference`, ruff, mypy, eslint, production build, 27 self-screenshot views.

### Added (interactive HTML system report — full scope)
- **`POST /api/report`** renders a self-contained, printable HTML Gesamtsystemreport
  (like the FVA reference, no external requests, < 300 KB): sidebar navigation,
  Getriebeeinheit (power-flow table in the shaft-1/2 convention), Stirnradstufe
  (ISO 21771 geometry with per-gear columns + colspan pairing rows, the ANIMATED
  Zahneingriff with the labelled line of action as inline SVG + ~30 lines vanilla JS,
  ISO 1328 tolerances per gear, K factors, dynamics/resonance) and — better than FVA
  (user decision) — **each gear only under its own norm**: a mixed pair gets two
  separate sections (ISO 6336 steel / VDI 2736 plastic incl. ϑ_Z, wear, deflection,
  peak load) instead of one table with "−" placeholder rows; a same-material pair
  shares one two-column table. Optional Stufenvariation section (summary, warnings,
  top-20 table, static parallel-coordinates SVG) from the store-persisted last run.
- The endpoint recomputes everything SERVER-SIDE from the input state (stage +
  capacity request + powerflow block) via the same functions the live tabs use —
  the frontend never ships computed values. Plain string templating (no jinja2
  dependency); `app/services/report/builder.py` + `app/api/report.py`.
- Frontend: "Report erzeugen" button in the header (collects the store state incl.
  `varUi` results); `buildCapacityRequest` extracted to `lib/capacityRequest.ts`
  (shared by CapacityPanel + report collector, no duplication).
- Tests (`tests/test_report.py`): mixed pair → plastic rows only in the VDI section,
  no placeholders in the ISO table; steel/steel → one shared ISO table; self-contained
  (no external URLs) with animated SVG + T1…E labels; variation section from real
  sweep points; EN locale.

### Changed (Zahneingriff: mesh-zone zoom with the exact line of action)
- **The Zahneingriff view zooms on the meshing zone** (user decision — no full-disc
  overview; a "Gesamtansicht" toggle keeps the old view) and draws the line of action
  as a static overlay behind the rotating as-cut contours: tangent line T1–T2 on both
  base circles, the active path A–E highlighted, single-contact points B/D, pitch
  point C with a grey crosshair, dashed base + working pitch circles, and the
  characteristics α_wt / g_α / ε_α in the footer.
- **Backend `line_of_action_points()`** (`app/services/geometry/gear.py`): T1/A/B/C/D/E
  in the tooth-profile frame from α_wt, r_b, r_w, d_Na and p_et — the same ISO 21771
  eq. 77 terms as `path_of_contact_mm`; served as `ToothProfileResponse.line_of_action`.
  Verified against the FVA Gesamtsystemreport reference coordinates (kst-E, all seven
  points within 2 µm; |E−A| ≡ g_α, |B−E| = |D−A| = p_et, tangent radii exact).

### Changed (Stufenvariation: per-gear reference-profile rows sweep for real)
- **b₂, h_aP*₁/₂, h_fP*₁/₂, ρ_fP*₁/₂ are real sweep parameters now** (previously greyed
  "Rad-1-Wert führt" rows): the vectorized kernel takes per-gear addendum factors
  (`mesh_geometry`), per-gear tool dedendum/tip-radius (`tip_form_factors` inputs) and
  per-gear face widths — shared-mesh quantities (ε, flank stress) use the common width
  min(b, b₂), each gear's root stress its own width, the weight each gear's own width.
  Only q/pr_P/α_prP stay fixed (protuberance is not in the kernel yet — honest warning).
- **sample_count is user-controlled** (was hardcoded 256): a number field appears next
  to the method select for Sobol/LHS; Sobol rounds UP to the next power of two (scipy
  balance) and says so in the warnings — LHS uses the exact count.
- Fixed: the request-level honesty warnings (`extra_warnings`) were built but never
  merged into `VariationResponse.warnings`; `evaluate()` now broadcasts all outputs to
  the batch shape (a sweep that only touches the tooth-root side — h_fP*, ρ_fP*, b₂ —
  used to collapse the geometry arrays to scalars).
- `VariationPoint` carries the per-gear values; **Übernehmen** writes b₂ and the gear-1
  tool factors into the shared stage; the step-4 contour overlay uses the variant's
  gear-2 reference profile. The sweep request is persisted in the store (`varUi.req`)
  for the upcoming report.

### Changed (powerflow rebuild: ONE torque on either shaft, exclusive load types)
- **One system torque, entered on either shaft** (user decision): the Leistungsfluss
  torque row has a Welle-1 and a Welle-2 field; entering one locks the other, which
  displays the loss-free converted value (T₁ = T₂·z₁/z₂). Clearing the entered field
  resets both to empty. The store keeps `{torque_nm, torque_shaft}` and always computes
  from the RAW entered value — never from the rounded display — so kst-E parity stays
  exact (8 N·m at shaft 2 → deck M₂ = 8000 N·mm, T₁ = 7.8462 N·m).
- **Antrieb/Abtrieb mutually exclusive**: flipping one load's type flips the other to
  the complement (store-level coupling, one setState patch). Both couplings are recorded
  as norm-referenced dependency rules in the schema/glossary.
- **Shaft-1/2 naming in the load tables** (user decision): the Leistungsfluss/Kräfte
  column headers and torque labels use the "Welle 1 / Welle 2" convention (1 = left,
  2 = right gear per ADR-021) instead of "Belastung [16]/[17]"; the model tree keeps its
  FVA instance IDs — the ID system stays in the store for later multi-stage systems.
- **Schema renderer honours dynamic locks**: `RowRef.locked_if` and the new per-column
  `AttributeDef.locked_ifs` are now evaluated (previously ignored); `nullable` number
  fields write null on empty (reset semantics). Downstream guards: capacity/dynamics/
  deck-download show "Kein Drehmoment gesetzt …" instead of sending NaN.
- **Torque SSOT closed in the last two panels**: Dynamikfaktoren and the Stufenvariation
  now read T₁/n₁ from the Leistungsfluss derived values (grey display rows) instead of
  panel-local 7.85/1000 copies; K_A and the deviations write back to the shared
  operating values.

## [0.6.0] - 2026-07-05

FVA-replica completion round: every editor tab field-checked against the 27 reference
screenshots via the Playwright self-screenshot loop; final pass all green (27 views without
errors, 176 backend tests, deck-parity verifier incl. `--reference`, ruff, eslint,
production build).

### Changed (i18n completion + one locale-aware number format)
- **One formatter for every user-visible number** (`fmtNum`/`fmtInt` in `lib/format`,
  bound to the active language via the `useFmt()` hook): German UI now shows comma
  decimals and dot thousands like the FVA Workbench (QuickView 51,495 · ε 1,154), English
  shows the inverse — the previous mix of `toFixed`, hardcoded `de-DE` and `en-US`
  formatting is gone. SVG path/transform coordinates deliberately keep raw `toFixed`
  (machine syntax, never localized).
- **DE/EN complete across the hand-built panels**: Stufenvariation flow, Ergebnis-
  Schnellansicht (ISO 21771 labels), Geometrie, Tragfähigkeits-/Lastfall-Karten,
  Dynamikfaktoren, Auslegung (incl. ISO 1328 rows, micro-geometry fields), Zahnform,
  Übersicht, Zahneingriff animation, 2D mesh caption, schema-table headers and the
  "FEM-Vernetzung durchführen" action — shared attribute names live under one `attr.*`
  key set (DE = exact FVA wording).
- **Tree material badges are data now**: Stahl/Steel and PA follow the Werkstoff
  selection (norm-dispatch source) instead of being hardcoded role strings; remaining
  hardcoded tab titles (Geometrie, Zahnform, Stufenvariation) localized.

### Added (Stufenvariation as the FVA guided 4-step flow)
- **Guided flow in the tree tab** (user decision): 1. Attribute → 2. Rechnung →
  3. Filterkriterien → 4. Ergebnisse with step chips, Zurück/Weiter and "Neue Variation";
  wording and table layout per the FVA screenshots (count line "n Varianten, m erfolgreich,
  k ohne gültige Geometrie", live "Es werden X Varianten angezeigt").
- **Persistent results in the workbench store** (`varUi` namespace): step, response,
  sorted rows, compare selection and filters survive tab switches and back-navigation —
  returning to step 3/4 NEVER recomputes; "Weiter (vorhandene Ergebnisse)" jumps straight
  back into the existing sweep from step 1.
- **Filterkriterien step**: min/max per result attribute (ε_γ, S_H/S_F per gear, a,
  weight) filtering the result set live; changing a filter drops the compare selection
  (indices would silently remap). Empty filter results render a plain note instead of
  degenerate −Infinity axes.
- **Übernehmen (SSOT)**: applying a variant writes it into THE shared stage
  (`setStage`) — Geometrie/Toleranzen/Tragfähigkeit/Schnellansicht/Zahneingriff/Deck all
  follow, and the always-visible stage badge (moved out of the scrollable tab strip into
  the node-title row) renames to "Variante z=… x₁=…".
- **Fußform & Werkstoff-Matrix as variation extensions**: root-fillet strategy
  (standard/trochoid/elliptic/Bézier/bionic) drives the step-4 contour overlays, and the
  per-gear material dropdowns dispatch norms strictly by material (steel → ISO 6336,
  plastic → VDI 2736).
- **Parallel coordinates selection behaviour** (user decision): the picked variant keeps
  its verdict colour and is drawn on top; all other lines turn grey instead of vanishing.
- Self-review script `scripts/shot-variation.mjs` walks the wizard end to end (run →
  filter → compare overlay → back-navigation persistence → tab-switch persistence →
  Übernehmen → Geometrie check) and screenshots every station.

### Added (2D mesh rendering + Zahneingriff animation)
- **2D-Schnitt view of the FE mesh** (`Mesh2DView`): the previously unrendered
  `/api/mesh/preview` now draws every quad as an SVG polygon with the scaled-Jacobian
  heatmap (grey ≥ 0.7, amber, red < 0.35 — same gates as the 3D viewport) plus a legend
  and min-J readout; selectable next to the 3D hull in the FE-Mesh tab (kst-E wheel:
  3 024 quads, min J 0.449, 0 cells below the gate — the ADR-019 reference topology is
  now visually checkable in the app, FVA "FEM-Vernetzer" style).
- **Zahneingriff animation** (`MeshEngagement`, Vorbild Gesamtsystemreport): both gears'
  REAL as-cut outlines (from `/api/tooth-profile`) rendered as SVG and rotated
  kinematically coupled (φ₂ = −φ₁·z₁/z₂) with play/pause + speed slider and pitch-circle
  construction geometry; embedded in the Geometrie tab. Fixed during self-review: the
  tooth outline walker now joins consecutive teeth at the root lands (the first version
  chained the tips and visually covered the gaps).

### Added (Ergebnis-Schnellansicht + Achsabstand-Modus rule + per-gear column headers)
- **Ergebnis-Schnellansicht** (FVA right panel): the ISO 21771 Hauptgeometrie and
  Durchmesser tables of the ACTIVE stage (incl. u, b_gem, ε-values and the derived working
  pitch diameters d_w = 2a·z_i/Σz — kst-E 51.495/52.505 like the FVA quick view),
  recomputed live on every stage change; shown for all component nodes on wide screens.
- **Achsabstand-Modus** (DIN 21771 lock rule): the Geometrie tab carries the FVA dropdown
  "Achsabstand definieren" — in "aus den Profilverschiebungen berechnen" mode the a field
  turns computed/grey and the effective stage sends a = null so the backend derives it
  from inv α_wt(Σx); in "definieren" mode a is the input.
- Schema tables now show the per-gear/per-load **column headers from the instance table**
  (Stahlritzel [8] / Kunststoffrad [9], Belastung [16] / [17]) instead of anonymous columns.

### Added (Flankenmodifikation [34] + Radkörper Stirnrad [40] tree nodes)
- **Flankenmodifikation** editor with the five FVA tabs (Allgemeine Angaben, Flankenlinie,
  Stirnprofil, Weitere Formen, Matrix): every modification as consider-checkbox + form
  dropdown + amount with FVA-style conditional rows (form/amount appear only while the
  modification is active). The amounts our ISO 21771 §6 micro-geometry model carries
  (C_Hβ, C_β, C_βI/II, C_α, C_αa, C_αf) merge into the EFFECTIVE stage; kst-E default:
  Kopfrücknahme C_αa = 8 µm from d_Ca = 51.946 mm active. Matrix editor honestly pending.
- **Radkörper Stirnrad** tab (Werkstoff = SSOT with the plastic wheel's material,
  Radkörpergestaltung with the validated "ohne Radkörper" reference variant as default,
  Einbaulage; the CAD tie-in steps section appears only for the CAD variant).
- Tree: both nodes hang under their gears (Stahlritzel [8] → Flankenmodifikation [34],
  Kunststoffrad [9] → Radkörper Stirnrad [40]) with instance-ID labels from the store.

### Added (Stirnradstufe editor tabs — Toleranzen/Tragfähigkeit/VDI 2736/Werkstoff/Schmierstoff/Lastverteilung)
- **Toleranzen** (screenshot parity): DIN 3967 Zahnweitenabmaße A_We/A_Wi per gear
  (kst-E −278/−207 µm) with the norm-active coupling — the MEAN allowance merges into the
  effective stage (x_E generation AND the rolling-deck backlash/closing rotation), DIN 3964
  centre-distance allowances, DIN 3962 quality grades (feed the dynamics deviations),
  tooth-plot checkboxes.
- **Tragfähigkeit** inputs per FVA sheet (Radkörper modes, Rauheiten R_a/R_z with
  auto-conversion switch, Kopfrücknahme C_a, c_γ mode, K_A) + the results block; the
  capacity request now derives ENTIRELY from the store (stage + Leistungsfluss load case
  with derived T₁/n₁/P/N_L = 60·|n₂|·L_H + operating + materials) — the panel-local
  DEFAULTS copy is gone.
- **VDI 2736 (2014)** tab: Schmierungsart, Zahntemperatur block (ϑ₀ = Öltemperatur-Modus,
  ED, Gehäuse, A_G, µ/k_ϑ/H_v modes with the µ-value row appearing only for
  "Nutzereingabe"), Fuß-/Flanken-Mindestsicherheiten, Verschleiß (W_zul = 0.1·m_n, k_W),
  Verformung, Spitzenlasten — all bound to the SAME operating store the capacity run uses.
- **Werkstoff** tab: catalog selection + Werkstoffart per gear (THE norm/deck dispatch),
  steel/plastic property blocks. **Schmierstoff** tab (ISO-VG-100 data, ν_40/ν_100, ρ15).
- **Lastverteilung (FEM, FVA 377)** tab (visible only while FVA 377 is selected):
  parameters, meshing with a working "FEM-Vernetzung durchführen" action (native
  transplant-mesher check reporting quads + min Jacobian), SHARED Fesselung switches with
  the rolling deck, expert section — solver honestly marked pending.
- Store: `operating`/`materials`/`tol`/`loaddist` namespaces + derived paths
  (`friction_is_user`, capacity load case, deck material kinds) and the effective-stage
  merge; deck action pulls materials from the Werkstoff selection.

### Added (Getriebeeinheit editor complete — Leistungsfluss/Kräfte und Momente/Steuerparameter)
- **Leistungsfluss** (screenshot parity, values match the FVA quick view): Schaltmatrix,
  shaft speeds with the derived n₂ = −n₁·z₁/z₂ (kst-E: 2250 → **−2206.73** min⁻¹, grey),
  load types (Antrieb/Abtrieb) with the norm-active lock rule — the Antrieb torque is THE
  system load case (kst-E M₂ = 8.0 N·m), Abtrieb torque (7.8462 N·m) and both powers
  (1.8487 kW) derive read-only. **SSOT chain**: the transient-FEM deck torque now derives
  from this Antrieb load (`fem.torque_gear2_nmm` is computed; the Abwälz tab has no own
  torque input — FVA behaviour; also fixes the M₂ semantics: 8000 N·mm at gear 2 → the
  deck's converted 7846.2 N·mm at the torque gear, the reference AMP level).
- **Kräfte und Momente**: per-load pair columns (u coordinate, switchability,
  Einzelkräfte/skalierbare Kräfte, Biegemomente) carried per screenshot.
- **Betriebsdaten** completed (Schwerkraft/Fliehkraft sections) and **Steuerparameter**
  (system-run switches, load-distribution block) with honest "FVA solver control — carried,
  computed natively" notes. Derived store paths power the grey fields (rule-engine start).

### Changed (self-review round 1 — own Playwright screenshots vs. the FVA dialogs)
- **Stufenvariation attribute matrix = the FVA dialog row set** (Stufenvariation_Ansicht-1):
  α_n/β/z/x/b per FVA naming plus the per-gear reference-profile rows (h_aP*, h_fP*, ρ_fP*,
  Bearbeitungszugabe q, Protuberanz pr_P/α_prP, Zahnbreite Rad 2) and the four dialog
  checkboxes; separate Wert/Minimum/Maximum/Schrittweite/Einh. columns (values were clipped
  by the old two-column layout); "Es werden N Varianten berechnet." footer. α_n is now
  sweepable end-to-end (`alpha_n_deg` in the sweep kernel); per-gear values the kernel
  cannot separate yet surface as explicit response warnings instead of silently averaging.
- **Tree instance IDs are data**: the `[n]` numbers come from the model-instance table in
  the store (kst-E defaults 1/3/4/6/8/9/…, FVA assigns them on insertion) — no hardcoded
  label strings.
- Dyn. Abwälzen (FEM) tab completed against its screenshot: FE-Löser-Ergebnisdatei switch,
  greyed odb/result path rows, Automatische Netzglättung, Expertenfunktion section.
- Fixes from the screenshot round: dropdowns no longer truncate their FVA phrases
  (select min-width), `/api/geometry` returns the REAL tip diameter d_a (kst-E wheel
  54.022, not the usable d_Na 53.788), Schmierstofftemperatur binding (showed 0 instead
  of 80 °C), dev CORS for localhost:3000 + `NEXT_PUBLIC_API_BASE_URL` in the shared .env.
- New tooling: `50_frontend/scripts/self-screenshots.mjs` (Playwright walk through every
  tree node/tab for the self-review loop).

## [0.5.0] - 2026-07-04

### Fixed (deck correctness — measured against the reference INP, user report)
- **Fesselung is now a coordinate predicate over ALL mesh nodes** — the reference deck's
  `Fesselung_Rad{1,2}` holds the bore surface PLUS both radial cut planes as *complete
  cross-sections* (every single node, bore → root circle, all face-width planes; measured:
  2 268/2 225 nodes per cut plane, no z side faces). The previous boundary-edge traversal
  could miss face nodes. The four FVA "Fesselung" checkboxes (Bohrung/Schnitt/oben/unten)
  are writer flags now (`DeckRequest.fasten_*`), defaults = reference parity.
- **Initial single-flank contact (the gears no longer "run in the air")**: the reference
  stands in single-flank contact at t=0 (~25 µm node gap on the −y flanks; AMP-TORQUE
  switches on while AMP-ANGLE dwells). The writer now computes the backlash-closing rotation
  of gear 2 by exact rotational collision detection on the 2-D boundary polylines
  (`align_contact=True`, 15 µm arc backoff) — kst-E: 243 µm centred backlash → **21.9 µm**
  on the −y flank, angle documented in the deck heading.
- New verifier `10_verifiers/verify_deck_parity.py`: Fesselung composition (bore + two
  complete cut planes to d_f/2), initial gap ≤ 35 µm on −y, torque-before-angle amplitudes,
  one `*STATIC` step, flank-wise contact pairs; `--reference` re-measures the FVA deck.
  ADR-021 second amendment records the measured ground truth.

### Changed (single source of truth — user requirement "eine aktive Geometrie überall")
- **`StageParams` moved to `app/api/stage_params.py`** and became THE shared request model:
  `/api/geometry`, `/api/capacity`, `/api/dynamics`, `/api/tooth-profile`, mesh/contour/deck
  all derive their `GearStage` from the same parameters (plus new fields: tooth-width
  allowances A_We, explicit tip diameters, tool dedendum, gear addendum factor).
  The duplicated `GeometryRequest`/`ToothProfileRequest`/`/api/evaluate` are gone;
  `/api/tooth-profile` now returns the REAL as-cut flanks (tip chamfer, root fillet).
- **Norm dispatch follows the MATERIAL, never the role**: steel → ISO 6336:2019, plastic →
  VDI 2736:2014, per gear (`CapacityRequest.pinion_material`/`wheel_material`) — steel/steel,
  plastic/plastic and mixed pairs all dispatch correctly.
- **Material catalog** (`app/services/materials.py::CATALOG`): 20MnCr5 + Stanyl TW200F6
  (PA46, cond. 80 °C, incl. the measured Marlow stress–strain curve, single copy) feed the
  analytic methods AND the FE deck (`materials_card.card_from_catalog`; FE Marlow keeps the
  reference deck's ν=0.30 while the analytic sheet uses ν=0.34).
- Frontend panels consume the shared stage store: Geometrie edits publish app-wide,
  Tragfähigkeit/Dynamik/Stufenvariation recompute from it (the Variation baseline is the
  active stage, no more hardcoded second gear pair); face width is a per-gear pair
  everywhere; input width cap 132→180 px (values were clipped); computed/locked field
  styling; missing SVG plot CSS tokens defined.

### Added (FVA replica foundation — user decision "Option 2": FVA as template, own logic)
- `20_antigravity_scripts/extract_fva_labels.py` mines the installed FVA Workbench's
  declarative UI (produktmodell_SI.xml + pm_messages DE/EN + pm_combo.xml, inheritance
  resolved) into `00_development_documentation/fva_label_reference.json` — a wording
  reference for 8 replicated components.
- **Own pydantic editor schema** `app/services/uimodel/` (AttributeDef/TabDef/
  DependencyRule/CalcMethod — every attribute with DE/EN label, symbol, unit, norm
  reference, store binding; doubles as the glossary source), served at **`/api/ui-schema`**.
- Frontend: workbench store (`lib/store.tsx`) with path-based bindings (stage/calc/fem/…),
  generic `SchemaTab` renderer, **Berechnungsauswahl** matrix (18 methods, unimplemented
  greyed out, ISO 6336 + VDI 2736 always-on), and the FVA-style shell: model tree
  (Getriebeeinheit → Stirnradstufe → Wellen → Räder) with an editor TAB BAR per node —
  the "Dynamisches Abwälzen (FEM)" tab exists only while FVA 892 is selected and downloads
  the corrected deck with the Fesselung checkboxes + contact alignment.

## [0.4.1] - 2026-07-04

### Changed (user review follow-up — Fesselung parity + rig-view slot convention)
- **Fesselung on reference parity**: `Fesselung_Rad{g}` now ties the bore surface AND both
  radial sector cut faces (bore → shoulder contour) to the rotation node — verified
  numerically against the reference deck's set (bore arc over the full sector + two complete
  radial node chains up to the root circle, all layers). Previously only the bore was tied.
- **Slot convention (ADR-021 amendment)**: every per-gear input follows the stage INPUT
  position through the whole chain (gear 1 = first .ste gear, gear 2 = second — never
  re-ordered by role or tooth count), and the assembly matches the Kleingetriebeprüfstand
  top view: **gear 1 at the origin (left), gear 2 at the working centre distance (right)** —
  in the deck and as the default 3D pair-view orientation. Deck request fields renamed
  accordingly (`gear1_material`/`gear2_material`, `axial_offset_gear(1|2)_mm`,
  `fillet_gear(1|2)`, `torque_gear2_nmm` = M₂, the torque expressed at gear 2). The
  angle/torque/slave roles follow the MATERIAL (plastic side angle-driven + contact slave,
  reference parity), independent of the slot.

## [0.4.0] - 2026-07-04

### Changed (user review of the generated pair — deck conventions, ADR-021)
- **Deck gear numbering now follows the stage input order**: gear 1 = pinion (kst-E: steel,
  z=51), gear 2 = wheel (plastic, z=52) — across parts, `G{g}T{nnn}F{f}` sets, surfaces,
  `Rot_Node_Rad{g}` and `Fesselung_Rad{g}`. Verified against the FVA reference deck that its
  own `Part_Rad_Vz_1` is the plastic z52 wheel (material cards + tip diameters), i.e. reversed
  relative to the .ste order — generated decks now carry a header comment table (z, b,
  material, axis, mid-plane, role per gear) documenting the mapping. The physical load case is
  unchanged (wheel at the origin angle-driven, pinion carrying the torque, plastic = contact
  slave); `wheel_torque_nmm` (M₂) is now converted to the applied pinion torque T₁ = M₂·z₁/z₂.
- **Mid-plane-centred extrusion (reference parity)**: each gear keeps its own face width and
  extrudes symmetric about z = 0, so the 15/17 mm kst-E pair rolls centred by default and both
  rotation nodes sit at their gear's mid-plane instead of on a side face; also applied to the
  single-gear `/api/mesh/3d` hull.

### Added
- **Legende & Parameter panel**: a dedicated, filterable glossary tab (75 entries, DE/EN) —
  symbol, full name, an understandable explanation of what each parameter does and which
  parameters it interacts with, norm badges (click to filter) and clickable cross-links;
  free-text search + category chips + norm dropdown.
- **Parametric axial offsets**: `axial_offset_(pinion|wheel)_mm` in the deck request displace
  each gear along its rotation axis; the pair panel exposes both (Δz₁/Δz₂) and the viewport
  mirrors them live.
- **Deck material matrix**: `pinion_material`/`wheel_material` (steel/plastic) in the deck
  request; the rigid-shell rule resolves to the steel side of a mixed pairing and the contact
  slave to the plastic side; `fillet_pinion` joins `fillet_wheel`.
- Tooth contours are drawn **continuously across the root land**: the plotted boundary is
  completed with the d_f arc from the fillet end to the gap centreline
  (`with_root_land`), so the standard/trochoid envelope no longer shows a gap at d_f.

### Fixed
- CI: `ruff check` over all of `20_code/` (unused variable in
  `10_verifiers/checkpoint2_plots.py`); local lint gate now runs from `20_code/`
  like the pipeline, not just `40_backend/`.
- mypy is now clean over the whole backend including tests (annotations added to the mesher,
  fillet and refine test modules).

## [0.3.0] - 2026-07-03

### Changed (2026-07-03 — frontend swap, ADR-020 completed)
- **`50_frontend/` is now the Next.js workbench** (old Vite SPA removed; `50_frontend_v2`
  renamed): new M6 panels — Auslegung (presets / `.ste` import / free parameters, DIN 3972
  tool presets, ISO 21771 §6 micro-geometry editor, ISO 1328-1 tolerances; publishes the stage
  app-wide), Tragfähigkeit (incl. accuracy grade + VDI 2736 static peak), Dynamikfaktoren, and
  the **pair viewport** with co-moving DOF triads at Rot_Node_Rad1/2 (locked DOFs 1–5 gray,
  free rotation green/amber) and a kinematically coupled roll slider. Mesh panel gains FVA
  density presets, the trochoid option, the manufacturability warning and the fillet-sweep UI;
  Stufenvariation gains the material-matrix selectors.
- **Docker** builds the Next static export (`out/` → `app/static`); the runtime image needs
  **no OpenGL**: gmsh became an optional import (the legacy mapped mesher guards its entry
  points; the deck path runs on the ADR-019 transplant mesher). Container smoke-tested:
  UI + `/api/health` + `/api/mesh/preview` green.

### Added (2026-07-03 — M6 backend: free design flow, fillet axis, presets/import, micro-geometry)
- **Design router** (`app/api/design.py`): shared `StageParams` (kst-E example OR fully free
  pair definition incl. tool reference profile) now feeds EVERY mesh/contour/deck endpoint —
  the kst-E lock is gone; `GET /api/presets` (kst-E + DIN 3972 tool-profile presets I–III /
  ISO 53 A) and `POST /api/import/ste` (STplus text import → editable parameters).
- **Fillet axis for the Stufenvariation**: `POST /api/mesh/fillet-sweep` sweeps one strategy's
  shape parameter (e_f / Be / b_f) with the quick-FE root stress as objective, enforcing the
  interference check and the det(J) gate per point, and recommends the feasible optimum.
- **TrochoidFillet** (`geometry/root_fillet.py`): the exact DIN 3960 tool trochoid as a
  first-class strategy (norm reference beside the ρ_F arc; ADR-017's high-fidelity option).
- **Micro-geometry data model** (`geometry/modifications.py`, ISO 21771 §6): per-flank
  Kopf-/Fußrücknahme, Profil-/Breitenballigkeit, Endrücknahme, f_Hβ per gear — carried through
  `StageParams`, drives the flank-symmetry policy (asymmetric data ⇒ mirror symmetry off,
  teeth stay rotation-congruent); mechanically active from the load-distribution step onward.
- **Variation material matrix**: `pinion_material`/`wheel_material` (steel|plastic) request
  fields — steel/steel, plastic/plastic and both mixed orientations dispatch per gear through
  the existing ADR-013 kernel; weight densities follow the material kind.

## [0.2.0] - 2026-07-03

### Added (2026-07-03 — mesh API, deck rewiring + rigid shell, workbench UI; ADR-019/020, M3–M5)
- **API — mesh router** (`app/api/mesh.py`): `/api/mesh/preview` (2-D sector + per-quad scaled
  Jacobian), `/api/mesh/3d` (outer hull of the extruded sector for the three.js viewer),
  `/api/mesh/convergence` (native root/flank density quick check), `/api/mesh/fillet-compare`
  (quick-FE ranking of the fillet strategies incl. clearances), `/api/mesh/contour` (real as-cut
  boundary — kst-E or free variant parameters, fillet-strategy-capable, with interference check)
  and `/api/mesh/deck` (implicit rolling deck download).
- **FE deck on the transplant mesher (M3):** `implicit_deck.build_gear_part` now meshes via
  ADR-019 (4 teeth + 2 shoulders, density factors, fillet strategy); the mixed-pairing material
  rule ships as `steel_shell`/`rigid_gears` (steel gear = ideally stiff rigid body about its
  rotation node, contact + frozen FVA set contract unchanged); `plastic_index` fixes the
  Workstream-C convention (Part_Rad_Vz_1 = plastic wheel, second `.ste` entry).
- **Geometry:** `ToothProfile.half_thickness_angle` (tip thickness via the edge-break involute);
  the mating-tip interference sweep now samples only MATERIAL tip points and rolls the correct
  direction (a half-pitch corner sweep produced false interference for u ≠ 1 pairs).
- **Frontend v2 (ADR-020):** Next.js workbench under `50_frontend_v2/` — model tree, condensed
  attribute-table editors (Geist, Tailwind), dark three.js FE-mesh viewport with Jacobian
  heatmap, convergence + fillet-ranking panels, deck download with rigid-shell toggle, real
  tooth-form panel (standard vs optimized fillet overlay + clearance), Stufenvariation with
  parallel coordinates, Pareto and the up-to-4-variant **real-contour overlay comparison**;
  DE/EN i18n keys from day one. Served as a static export by FastAPI (`app/static`, gitignored).

### Added (2026-07-03 — reference-topology transplant mesher, ADR-019)
- **FE model — reference miner** (`model/reference_slice.py` + committed template
  `model/data/reference_sector_rad_vz_1.json`, verifier `10_verifiers/make_reference_template.py`):
  the ANSA/FVA wheel slice is parsed with correct cyclic face ordering (rim hexes carry a rotated
  local axis — naive ordering creates bowtie quads) and pinned by tests: 3024 quads / 3329 nodes,
  interior valences {4: 2716, 5: 2, 6: 3} — **exactly one fan-convergence node per tooth gap**,
  rim grid 26×25, min scaled Jacobian 0.243 (24 tip cells < 0.35).
- **FE model — transplant mesher** (`model/template_mesher.py`): generates the reference-identical
  block-structured 2D sector for any spur gear by re-using the mined connectivity and deriving node
  positions from the target geometry (pitch scaling, radial feature map, exact foot-point
  projection onto the analytic contour incl. the ISO 21771 tip chamfer up to d_a, selective §11
  tip lift). kst-E wheel: topology-identical, min scaled Jacobian 0.45, **0 cells < 0.35**.
- **FE model — canonical symmetry**: sector symmetry orbits enforce **exact tooth-to-tooth
  congruence** (≤ 1e-14 mm) and, gated by the data-driven `ToothProfile.is_flank_symmetric()`
  (DIN 867 §4.2), exact in-tooth mirror symmetry; the tip lift is rolled out orbit-synchronously.
- **FE model — parametric density** (`model/refine.py`): conformal chord splits with separate
  FVA-style root/flank factors; structure, gates and congruence survive every level.
- **FE model — native quick solver** (`model/plane_fe.py`): vectorized plane-strain Q4 FE
  (< 0.1 s/solve) for root/flank density-convergence checks (separate searches) — confirms the
  mined reference density is already converged for the root stress (Δ < 0.1 %).
- **Geometry — optimized root fillets** (`geometry/root_fillet.py`, supervisor's topic):
  `EllipticFillet` / `BezierFillet` / `BionicFillet` per the literature synthesis
  (`00_development_documentation/root_fillet_strategies.md`), pluggable into the mesher, with the
  mandatory mating-tip clearance check and a DIN 3960 eq. 3.6.06 undercut warning. Quick-FE on
  kst-E: ellipse −9.9 %, Bézier −22.1 % root stress vs the standard ρ_F arc.
- **Geometry — tip chamfer boundary**: `transverse_right_boundary(to_tip_circle=True)` continues
  past d_Na along the edge-break involute to d_a (`generation.edge_break_flank_transverse`).
- **Docs:** norm audit (`norm_geometry_audit.md` — DIN 3960/867/3972 findings incl. tool-profile
  presets I–IV and protuberance parameters living in DIN 3960 Anhang A) and the root-fillet
  literature synthesis with measured results.

### Removed
- **FE model:** deleted the unstructured gmsh tooth/sector mesher
  (`model/gmsh_mesher.py`: `mesh_sector_3d`, `mesh_tooth_pitch`,
  `mesh_tooth_pitch_3d`). Its self-intersecting multi-tooth boundary could make
  gmsh's Frontal-Delaunay meshing run unbounded — a multi-hour hang at full CPU.
  The structured, deterministic transfinite `mapped_mesher` is now the single
  meshing path.

### Added
- **FE model:** reference-faithful implicit deck generator (`model/implicit_deck.py`)
  reproducing `32_Abaqus/implicit/…_ohne_Radkoerper.inp` — two `Part_Rad_Vz_{g}`
  sectors, bore `Fesselung` rigid-tied to a rotation node, frictionless hard contact
  as explicit meshing flank pairs (plastic = slave), and one quasi-static step driving
  gear 1 through a staircase angle while gear 2 carries the resisting torque. One-call
  entry `build_implicit_pair_from_stage(stage, …)`.
- **FE model:** reference per-tooth/flank tagging (`mesh_sets.tag_gear_reference`) emitting
  the exact `G{g}T{nnn}F{f}_NODESET/_ELEMENTSET` + `TOOTH-{g}-{nnn}F{f}` names the frozen
  FVA postprocessing requires, in 1-based 3-D ids.
- **FE model:** material cards (`model/materials_card.py`) — linear `*ELASTIC` (steel) and
  `*Hyperelastic, MARLOW` + `*Uniaxial Test Data` (plastic), with the kst-E PA curve embedded
  for validation.
- **FE model — geometry:** clean rounded root fillet (`tooth_form.transverse_right_boundary`): the
  ρ_F arc tangent to the involute flank (true d_Ff) and the root circle d_f → a monotone boundary
  with no pinch. Regression test guards monotonicity + flank/fillet continuity for both gears.
- **FE model — mesher:** the transfinite `mapped_mesher` now builds the tooth from that clean
  boundary, with a fine **surface boundary layer** (`flank_bias`, gmsh "Bump") and a radially graded
  **deep rim** to the real bore; Jacobi-Güte ≥ 0.9. Native fallback mesher
  `model/structured_mesher.py` (radius-arc tooth + rim) with a scaled-Jacobian check. (ADR-017)
- **FE model — body mesh (WIP):** building blocks toward the reference gear-body mesh —
  `mapped_mesher.tooth_section_2d` (transfinite tooth+fillet, no rim, + ordered d_f base interface),
  a validated **conformal all-quad 4→2 coarsening template** + graded ring (`structured_mesher.
  body_section_2d`), and Laplacian smoothing. The exact reference **O-grid "dome + run-out"** body
  (fine structure continued under the tooth, coarsening only outside the root) is the next step;
  the tooth/root itself is already reference-grade and (Saint-Venant) sets the root stress. (ADR-017)
- **FE model — reference ground truth + dome (WIP):** the reference deck `…_ohne_Radkoerper.inp` is
  now mined as the *meshed ground truth* (parse a z-slice → exact 2D topology, instead of guessing
  from screenshots): wheel 269 649 nodes, 81 z-levels (b=15, z-centered, Δz=0.1875), bore r=12.38,
  ~723 quads/pitch; structure = fine tooth → dome-cap fan → structured rim grid. New structured
  pieces toward it: optimization-based (quality-greedy) smoothing `structured_mesher._optimize_smooth`
  (+ `boundary_nodes`) and `assemble_pitch_2d` (merge tooth+body, hold only the outer contour, smooth
  the dome). Validated by overlay on the parsed reference; bad-cell count on the kst-E pitch fell from
  26 to 9 toward the reference dome. Dome-quality finish + sector/extrude next. (ADR-017)
- **FE model — body mesh matches the reference (kst-E):** the body is now built as a **root
  boundary layer** (fine surface-aligned arcs hugging the fillet, where the bending stress peaks)
  that runs out into a structured rim grid — the reason the reference is meshed this way. The
  reference itself is fully structured (all interior nodes valence 4; its only 6 cells < 0.35 sit at
  the tooth *tip*, min 0.243). The dome transition is lifted by the now **lexicographic**
  `_optimize_smooth` (maximise the worst incident scaled Jacobian, then the mean — the mean
  tie-breaker unlocks the plateau Laplacian/greedy-min got stuck at). Result on the kst-E wheel
  pitch: all-quad, **min Jacobian 0.736, 0 cells < 0.35** — exceeding the reference (0.243 / 6) with
  a reference-like structure. (ADR-017)
- **FE model — block-structured FVA mesher (`model/block_mesh.py`, WIP):** the reference-faithful
  multiblock route per `MESHING_SPEC.md`, built on the proven scaffold pipeline (TFI/Coons blocks +
  shared-node `NodeRegistry` for conformity, no tolerance merge, no paving/gmsh). Adds B3 fillet band
  (curve-seeded, densified to the 30°-tangent — not offset marching), B4 core, B1 rim, B2 deep 2:1
  quad templates, and the **section-11 finish** (optimization-based worst-first node relocation,
  frozen connectivity, fixed boundary/feature/cut nodes). On kst-E: registry conformity asserted,
  4-tooth + 2-toothless sector periodic to 5e-15 mm, B2 template det(J) **0.21 → 0.66** after the
  finish (0 cells < 0.35, 0 inverted). Element type **C3D8I** in the root. (ADR-018)
- **FE model:** `model/mesh3d.py` holding the pure-numpy `Mesh3D` container and
  the native `extrude_to_hex` (quad section → C3D8 hexahedra), free of gmsh.
- **FE model:** an element-count safety valve (`max_elements`, default
  4,000,000) on the mapped mesher — an over-budget request is rejected up front
  instead of being meshed, so the mesher can no longer hang the machine.

### Fixed
- **FE model:** the inverted / pinched tooth root ("Pokal" shape) is fixed — the root cause was
  `tooth_form.root_fillet_points` producing a non-monotonic, branch-mixed trochoid that did not even
  meet the involute at d_Ff; the `_monotone_fillet` band-aid is removed. (ADR-017)
- **FE model:** gmsh section quads are normalised to CCW winding before the face-width sweep, so the
  C3D8 hexahedra are positively oriented (Abaqus rejects negative-Jacobian elements).
- **FE model:** `tag_sector_surfaces` now reads the bore radius off the actual
  mesh (its quad-referenced nodes) instead of recomputing it from `rim_depth`,
  so the BORE / Fesselung node set can no longer come up empty when the mesher
  used a different rim depth.
- **Tooling:** cleared all outstanding ruff and mypy findings across the model
  layer and the test suite.
- **CI:** the workflow now installs the system OpenGL libs (`libglu1-mesa`, `libgl1`) the gmsh wheel
  links against, and runs `ruff format --check`; CI had been red since gmsh was introduced because
  importing it on the Linux runner failed with `libGLU.so.1: cannot open shared object file`, erroring
  out collection of every gmsh-importing test.

### Verified
- `ruff check .` clean, `mypy .` clean, `pytest` → 136 passed (full gold-standard
  validation active: kst-E, RIKOR, helical references present).
- FE geometry/mesh checked numerically + visually on kst-E (rounded root, deep rim, boundary layer,
  Jacobi 0.9); the all-quad 4→2 body-coarsening template validated standalone (|Jacobi| 1.0, ADR-017).
