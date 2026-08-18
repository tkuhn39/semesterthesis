# Consistency audit: analytical chain + display (2026-08-18)

> **STATUS UPDATE (2026-08-18, ADR-025): the entire P1 block is FIXED** — NRM-01…NRM-09,
> V-02 (native K_Hβ incl. the eq. 52/53 running-in averaging that had frozen χ_β = 0 for
> mixed pairs), GAP-01 (shared `MaterialParams` request base + tab parity) and FEM-01
> (deck interference check). Details: CHANGELOG "Fixed (audit round P1)" + ADR-025. One
> deliberate deviation from a recommendation: NRM-04 uses VDI 2736-2 eq. 12 / DIN 3990-2
> eq. 6.01 in the sweep (per-norm fidelity — the sweep's stress chain is the VDI tip-load
> form), not the shared ISO helper. An adversarial verify pass over the fix diff caught
> four additional defects (missing Y_St ≈ 2 in the VDI root check incl. the sweep limit,
> the β ≤ 30° cap of VDI eq. 12, the all-velocity 3 µm y_α cap of eq. 79, and 500-instead-
> of-422 on the helical guards' remaining routes) — all fixed in the same round (ADR-025
> amendment). P2–P4 remain open. The findings below are kept as written (audit snapshot).

> **Read-only audit — no code was changed.** Deliverable requested by the user: full report
> first, decisions before fixes. Scope: the ANALYTICAL chain (geometry / norms / seven
> root-fillet approaches / capacity), its frontend display and the HTML report; the FEM/deck
> pipeline only at its interfaces. Audited state: commits `1b44547` (ADR-023, all seven
> fillet approaches), `0a38b36` (ADR-024, geometry SSOT), `e1e7e21` (explicit ISO 6336
> sub-factors + DIN 3967 tables).

**Method.** (1) An 11-agent workflow: five dimension auditors (A–E below), each finding
adversarially re-verified by an independent verifier agent (verdicts: confirmed / adjusted /
refuted — nothing was refuted), plus a completeness critic (F). 609 tool calls over the live
repo. (2) A live visual pass by the main session: backend + frontend started, 18 Playwright
screenshots across Geometrie/Tragfähigkeit/Zahnform (all seven fillet approaches exercised
end-to-end incl. the CAO convergence loop), EN locale, and the generated HTML report; plus a
direct API probe of the K_Hβ path.

**Verdict in one paragraph.** The analytical core is in good shape: every value pinned
against the kst-E reference (`.sta` Blatt 6–8, 27 literal checks) is correct on screen, all
seven fillet approaches work end-to-end in the UI with correct numbers, the HTML report
renders the full SSOT block, and there are zero console/page errors. The dominant defect
pattern is NOT wrong math on the validated path but (a) **silent spur-only/steel-only
assumptions** that produce plausible-looking wrong numbers the moment β ≠ 0, m_n > 5 or
non-default materials are used, (b) **state fragmentation** (four fillet stores, three
accuracy-grade states, an allowance band collapsing to its mean) so that what one tab
computes is not what another tab or the deck consumes, and (c) **computed-but-invisible
values**.

## What is verifiably sound today (positive inventory)

- **Geometry SSOT** (`services/geometry/report.py`): all 27 kst-E literals reproduced and
  correctly displayed (W_k with auto k = 6, M_dK/M_dR, allowance factors, contact circles,
  ζ_a/ζ_f, K_ga, j_t/j_n, d_Nf, c_n, heights, x_E, undercut limit) — on screen, in the API
  and in the HTML report; grouped sections render in DE and EN.
- **All seven fillet approaches** selectable and functional in the Zahnform tab: two-level
  selection, live contour overlay with d_f/d_Ff reference circles, effective root diameter
  (Frühe digging −0.35·m_n below d_f is visible), mating-tip clearance, CAO with its
  convergence table (274.9 → 236.2 MPa, "Konvergiert"). Measured quick-FE ranking on kst-E:
  Roth 77.9 %, Frühe 79.1 %, Landi (ra_f = 0.3) 79.5 %, Dong 81.0 %, CAO ≈ 85.9 %,
  Kassem 90.1 %, Voith 96.9 % of the standard ρ_F arc.
- **Capacity factor chains** explicit end-to-end (Z_L·Z_v·Z_R, Z_W·Z_X, Z_NT,
  Y_δrelT·Y_RrelT, Y_X, Y_NT) with test-pinned self-consistency; σ_HP/σ_FP native.
- **DIN 3967 tables** complete and pinned against the norm's own example; the series picker
  fills the SSOT allowance inputs.
- **HTML report**: full geometry block, mesh SVG, tolerances, factor sections, per-gear
  norm sections incl. the new sub-factor rows; renders cleanly.
- **Gates**: 246 backend tests, ruff, mypy (80 files), eslint, tsc, production build.

## Own visual/functional findings from the live pass (V-01 … V-10)

- **V-01 [HIGH] Tragfähigkeit gear cards clipped**: at 1720 px the ISO card's VALUE column
  is entirely invisible (labels truncated on the left, numbers cut off); the VDI card
  truncates values on the right. The extended cards no longer fit the two-column grid
  (`50_frontend/src/panels/CapacityPanel.tsx`, GearCard grid).
- **V-02 [HIGH] Native K_Hβ is inert**: `DynamicConditions.initial_mesh_misalignment_um`
  (F_βx) defaults to 0 and has NO estimation path and NO API input — Method C then returns
  K_Hβ = K_Fβ = 1.000 for every request (verified via `/api/dynamics` and `/api/capacity`).
  ISO 6336-1 Annex A (normative f_sh + f_ma estimation) is unimplemented; the kst-E
  reference prints K_Hβ = 1.19. The K_Hβ fix of commit `0a38b36` is correct wiring around an
  inert source. (`40_backend/app/services/capacity/iso6336_dynamics.py:375`)
- **V-03 [MEDIUM] FilletEditor input clipping**: in the 340 px pane the approach select
  truncates its label ("Frühe (geneigte El…"), numeric inputs clip their values and the
  unit column; same clipping in the Zahnform result table.
- **V-04 [MEDIUM] CAO shows Voith parameters**: with bionic/cao selected the editor still
  renders Keilwinkel γ_b and Bogenfaktor b_f (guard checks only `kind`), which CaoFillet
  ignores — misleading. (Found independently as FIL-07.)
- **V-05 [MEDIUM] Quick-view pane clipped right**: the wheel column of the
  Ergebnis-Schnellansicht is cut off at 1720 px (headers and values truncated).
- **V-06 [LOW] Input tables clip the unit column** (Hauptgeometrie editor shows "mm"/"°"
  fragments).
- **V-07 [LOW] Mixed-language label**: DE row "Zahndicke am Nutzkreis (as cut)".
- **V-08 [LOW] Report pairing rows**: single pair values right-align under the Rad-2 column
  and read as belonging to gear 2 (`services/report/builder.py` colspan alignment).
- **V-09 [INFO] Locale switch works** (header select DE/EN); the new sections are fully
  translated in EN.
- **V-10 [INFO] Zero console/page errors** across the full click-through incl. all seven
  fillet runs and the report.

## Priority reading guide

- **P1 — analytical correctness (fix first):** NRM-01…NRM-06 (silent spur-only SSOT report,
  unguarded helical profiles, dropped helical capacity factors, Stufenvariation Y_β bug,
  Y_X group mapping scrambled vs ISO 6336-3, VDI safety double-division), V-02 (inert
  K_Hβ), GAP-01 (Dynamikfaktoren tab vs capacity disagree), NRM-07/NRM-08 (hardcoded
  material group / density), FEM-01 (deck skips the interference check).
- **P2 — state consistency:** COV-01 (allowance band collapses to its mean; series
  invisible in example mode), STR-01…STR-04 (discarded pinion micro-geometry edits,
  accuracy-grade triple state, fillet spec split across four stores, Stufenvariation
  hardcoded materials), FIL-01/FIL-02, FEM-02…FEM-05.
- **P3 — visibility (computed but invisible):** the COV mediums, tolerance components,
  W_zul/λ, report/tab display asymmetries, GAP mediums.
- **P4 — polish:** the LOW entries and V-03…V-08.

The full findings follow, grouped by audit dimension, each with its adversarial-verification
verdict, exact files and a concrete recommendation.

## Dimension A — Backend→frontend value coverage

### COV-01 [HIGH] DIN 3967 allowance band collapses to a mean: E_sns/E_sni and A_We/A_Wi always display identical values, series apply invisible in example mode

*Verification: confirmed.*

Files: `20_code/50_frontend/src/panels/GeometryPanel.tsx`, `20_code/50_frontend/src/lib/store.tsx`, `20_code/40_backend/app/api/analysis.py`

The backend request fields GeometryReportRequest.span_allowance_upper_um / span_allowance_lower_um exist precisely to carry the distinct A_We/A_Wi pair, but no frontend code ever sends them (0 usages outside lib/api.ts). GeometryPanel.run() posts only {stage, fillet_gear1, fillet_gear2}; store.tsx (lines 673-674) folds tol.awe1_um/awi1_um into ONE mean tooth_width_allowance_*_mm. Consequences: (a) in free-parameter mode _report_allowances (analysis.py line 255-258) returns (mean, mean), so the Geometrie tab rows E_sns/E_sni and A_We/A_Wi always show the same number and the tolerance band T_sn from an applied DIN 3967 series (e.g. '27cd') is silently lost; backlash j_t/j_n is computed from the mean instead of the upper allowance; (b) in example mode (use_example=true) _report_allowances short-circuits to the kst-E STE values, so applying a DIN 3967 series in the Din3967Section changes nothing visible in the tab at all. The same collapse happens in the HTML report (api/report.py builds GeometryReportRequest with span_allowance_upper_um=None).

**Recommendation:** Have GeometryPanel (and lib/report.ts collectReportRequest) pass tol.awe1_um/awi1_um/awe2_um/awi2_um as span_allowance_upper_um/span_allowance_lower_um in the /api/geometry/report request, and make an applied series (or edited allowances) leave example mode or override the STE route.

### COV-02 [MEDIUM] DIN 3964 centre-distance allowance feature unreachable: backlash-delta row permanently shows dash

*Verification: confirmed.*

Files: `20_code/50_frontend/src/panels/GeometryPanel.tsx`, `20_code/40_backend/app/services/geometry/report.py`

GeometryReportRequest.center_distance_allowance_mm is never sent by any frontend code (0 usages outside lib/api.ts), so PairReport.center_distance_allowance_mm, backlash_delta_upper_mm and backlash_delta_lower_mm are always null. The Geometrie tab renders a dedicated row 'Delta j_t/Delta j_n' (GeometryPanel.tsx lines 456-462) that can therefore never show anything but '-'. backlash_delta_lower_mm is additionally never read even in TS (the row renders +/- of the upper tuple, which is legitimate since lower = -upper).

**Recommendation:** Add an A_a input (DIN 3964 js field) to the Geometrie or Toleranzen tab and send it in the report request; alternatively hide the delta row until a value exists. Consider dropping backlash_delta_lower_mm from the response (always the negation of upper).

### COV-03 [MEDIUM] GearReport fields computed but rendered nowhere: span_teeth_min/max, has_undercut, tool_dedendum_factor

*Verification: adjusted.* — *Two of three parts confirmed: span_teeth_min/max (report.py:350-352) and has_undercut (report.py:370) have zero frontend usages outside api.ts (440-441, 459) and no HTML-report row (report.py:664 prints only W_k(k)); GeometryPanel fmtCell's boolean branch (line 125) is indeed unreachable since no SEC_* row references a boolean field, and has_undercut is not surfaced via check_validity notes either (only a backend log in template_mesher.py:206-212). BUT the tool_dedendum_factor part overstates: h_fP0* is an EDITABLE input row in the schema-driven Profilerzeugung editor (uimodel components.py:415-422 bindings stage.tool_dedendum_factor/_gear2, referenced at line 1962), so the per-gear tool difference is user-visible as input - only the GearReport echo row in SEC_TOOL (GeometryPanel.tsx:88-93) and the report is missing. Keep medium for the first two, downgrade the tool_dedendum part to a completeness nit on the tool section.*

Files: `20_code/40_backend/app/services/geometry/report.py`, `20_code/50_frontend/src/panels/GeometryPanel.tsx`, `20_code/40_backend/app/api/report.py`

Four GearReport fields are computed in compute_geometry_report and shipped in every /api/geometry/report response but appear neither in any frontend panel nor in the HTML report: span_teeth_min and span_teeth_max (DIN 21773 eq. 12/13 k-range; the tab shows only the chosen k), has_undercut (the boolean the STA reference prints; GeometryPanel's fmtCell even has a boolean checkmark branch that is unreachable because no row uses a boolean field), and tool_dedendum_factor (SEC_TOOL renders only m_n0, alpha_n0, h_aP0*, rho_aP0*; h_fP0* is missing, so the kst-E per-gear tool difference is only partially visible).

**Recommendation:** Add k_min/k_max to the inspection section, a has_undercut row (checkmark) next to undercut_min_shift, and h_fP0* to the tool section; print at least has_undercut in the HTML report.

### COV-04 [MEDIUM] PairReport fields computed but rendered nowhere: transverse quantities, gear_ratio, reference centre distance, profile-shift sum, common face width

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/geometry/report.py`, `20_code/50_frontend/src/panels/GeometryPanel.tsx`

PairReport.transverse_module_mm, transverse_pressure_angle_deg, base_helix_angle_deg, gear_ratio, reference_center_distance_mm, profile_shift_sum and common_face_width_mm are computed and serialized on every geometry-report call but no panel row (SEC_PITCHES covers only pitches/heights) and no HTML-report row displays them. All of these appear in the STA reference geometry block (kst-E lines 293-434: m_t, alpha_t, beta_b, u, a_d, Summe x, b_gem). u and b_gem do reach the user, but only via QuickView's local recomputation from stage inputs, not from these fields.

**Recommendation:** Add the missing rows to the Geometrie tab pitch/pair section (m_t, alpha_t, beta_b, u, a_d, sum x, b_gem) and to the report's geometry table; they are spur-trivial today but become load-bearing the moment helix angles are used.

### COV-05 [MEDIUM] ISO 1328-1 tolerance components f_HalphaT, f_HbetaT, f_fbetaT computed but invisible everywhere

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/geometry/tolerances.py`, `20_code/50_frontend/src/panels/DesignPanel.tsx`, `20_code/40_backend/app/api/report.py`

FlankTolerances carries 8 deviation quantities (eq. 5-12) but both consumers show only 5: DesignPanel renders single_pitch, total_pitch, profile_form, profile_total, helix_total (+f_pb echo); the HTML report tol_rows renders the same 5. profile_slope (f_HalphaT), helix_slope (f_HbetaT) and helix_form (f_fbetaT) are computed, serialized in every /api/tolerances response, and rendered nowhere. ToleranceResponse.profile_form_deviation_um is likewise never displayed (pure echo of tolerances.profile_form).

**Recommendation:** Add the three missing slope/form rows to DesignPanel's tolerance table and to the report; drop or keep profile_form_deviation_um consciously (it is redundant with tolerances.profile_form).

### COV-06 [MEDIUM] VDI 2736 allowable wear W_zul and tooth deformation lambda invisible in the Tragfaehigkeit tab

*Verification: confirmed.*

Files: `20_code/50_frontend/src/panels/CapacityPanel.tsx`, `20_code/40_backend/app/api/analysis.py`

GearCapacity.allowable_wear_um and deformation_mm are computed by evaluate_vdi2736, present in every /api/capacity response (and printed in the HTML report via _norm_rows), but CapacityPanel's GearCard renders wear_um WITHOUT its limit allowable_wear_um and omits deformation_mm entirely (0 frontend usages outside lib/api.ts). The wear check is a pass/fail against W_zul = 0.1*m_n, so showing the measured wear without the limit makes the tab's wear row uninterpretable.

**Recommendation:** Add W_zul and lambda rows to GearCard's VDI branch (next to wear_um), ideally with a good/bad tone on wear_um <= allowable_wear_um.

### COV-07 [MEDIUM] HTML report and live tabs render asymmetric capacity field sets (each misses values the other shows)

*Verification: confirmed.*

Files: `20_code/40_backend/app/api/report.py`, `20_code/50_frontend/src/panels/CapacityPanel.tsx`

The report's per-gear norm sections (_norm_rows) omit response fields the CapacityPanel shows: nominal_flank_stress_mpa/nominal_root_stress_mpa (sigma_H0/sigma_F0), the critical-section geometry root_chord_mn/fillet_radius_mn/notch_parameter/bending_lever_mn/load_angle_deg (s_Fn*, rho_F*, q_s, h_Fe*, alpha_Fen), loss_factor (H_V) and flank_temperature_c (theta_Fla). The report's factor table prints only K_A, K_v, K_Halpha, K_Hbeta, Z_E, Z_H and omits transverse_factor_root (K_Falpha), face_load_factor_root (K_Fbeta), contact_ratio_factor (Z_eps), single_contact_b/d (Z_B/Z_D), tangential_force_n, pitch_velocity_ms, line_load_n_mm and virtual_teeth; the dynamics section omits reduced_mass. Conversely allowable_wear_um and deformation_mm appear only in the report (see separate finding). The STA reference prints all of these in its DIN-3990 block (lines 561-748).

**Recommendation:** Drive both renderers from one shared row list (field, symbol, digits, unit) per GearCapacity/CapacityFactors so tab and report cannot diverge.

### COV-08 [MEDIUM] HTML report is never fillet-aware: effective_root_diameter_mm cannot appear in it

*Verification: confirmed.*

Files: `20_code/40_backend/app/api/report.py`, `20_code/50_frontend/src/lib/report.ts`

ReportRequest has no fillet fields and api/report.py hard-codes GeometryReportRequest(fillet_gear1=None, fillet_gear2=None), so GearReport.effective_root_diameter_mm (d_f,eff, ADR-023/024 fillet-aware root) is always null in the report path even when the user has an optimized root fillet active in the store (wb.fem.fillet_gear1/2) and the Geometrie tab shows the d_f,eff row. The report also omits the row entirely, plus x_E-adjacent rows the tab has (addendum_mm, addendum_factor_actual, tip_path_of_contact_mm, span/ball allowance rows, rest_tip_thickness_mm, tool section).

**Recommendation:** Extend ReportRequest with fillet_gear1/fillet_gear2, pass wb.fem.fillet_* in collectReportRequest, and add a d_f,eff row (marked contour-based vs norm-based) to the report geometry table.

### COV-09 [MEDIUM] VariationResponse.eval_ms and varied, VariationPoint.transverse_contact_ratio and overlap_ratio never rendered

*Verification: confirmed.*

Files: `20_code/50_frontend/src/panels/VariationPanel.tsx`, `20_code/40_backend/app/api/analysis.py`

VariationResponse.eval_ms (kernel timing) and varied (human-readable list of swept parameters, built via _VAR_LABELS) are computed per run but have 0 frontend usages outside lib/api.ts and are absent from the report's variation section - the step-3/4 UI never tells the user WHICH parameters were actually varied (relevant after fix_center_distance silently locks z1/z2/x2). Per point, transverse_contact_ratio and overlap_ratio are serialized for every valid variant but only total_contact_ratio is shown in the table, PC dims, filters and report. The remaining per-point echoes (b, b2, h_ap*, h_fp*, rho_fp*, beta_deg) are consumed by applyVariant/buildOverlays, so they are fine.

**Recommendation:** Show 'varied: ...' (and optionally eval_ms) in the step-3 summary line; add eps_alpha/eps_beta as optional table columns or filter keys, or drop them from VariationPoint to slim the payload.

### COV-10 [MEDIUM] Native RIKOR load-distribution package (loaddist) fully unrouted - beyond the known forces.py: compliance, shaft, distribution and the .rie reader

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/loaddist/__init__.py`, `20_code/40_backend/app/services/loaddist/shaft.py`, `20_code/40_backend/app/services/loaddist/distribution.py`, `20_code/40_backend/app/services/loaddist/compliance.py`, `20_code/40_backend/app/io/rie.py`, `20_code/40_backend/app/services/capacity/iso6336_dynamics.py`

Not just forces.py: the entire loaddist package has no API route and no consumer outside itself - compliance.py (shaft_compliance, local_mesh_compliance), shaft.py (mesh_gap -> F_betax), distribution.py (solve_contact, evaluate_load_distribution -> K_Hbeta/K_Fbeta from the real w(b)), plus io/rie.py which only serves it. Its own docstring says the mesh misalignment F_betax 'feeds the existing ISO 6336-1 K_Hbeta (Method C), closing the last fed quantity' - but DynamicConditions.initial_mesh_misalignment_um is never set by any caller (defaults 0.0 in analysis.py), so every K_Hbeta the app reports is the well-aligned Method-C value and the computed R2/R3 capability is invisible. Also unrouted/unimported: services/analysis/stplus.py (known).

**Recommendation:** Either wire mesh_gap's F_betax into the capacity/dynamics requests (and expose the w(b) distribution via a route for a Breitenlastverteilung view), or mark the package experimental in the roadmap so the dead surface is intentional.

### COV-11 [MEDIUM] services/ingest.py (STE-REXS cross-check) and io/rexs.py have zero consumers

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/ingest.py`, `20_code/40_backend/app/io/rexs.py`

services/ingest.py (Discrepancy model, order-independent STE vs REXS consistency check) is imported by nothing in app/ - no route, no service consumer; io/rexs.py exists only for it (loaddist reads .rie, not .rexs). The import UI only offers .ste upload (designApi.importSte). Dead code on the import path.

**Recommendation:** Either add a /api/import/rexs (or combined validation) endpoint that surfaces the Discrepancy list in DesignPanel, or delete/park the module.

### COV-12 [MEDIUM] GearStage.span_measurement_mm duplicates the W_k computation in the geometry report

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/geometry/gear.py`, `20_code/40_backend/app/services/geometry/report.py`

GearStage.span_measurement_mm (gear.py line 272, DIN 21773 eq. 14) is consumed only by tests; the production path recomputes the identical W_k formula inline in compute_geometry_report (report.py line 282) with its own _auto_span_teeth k. Two implementations of the same norm quantity risk silent divergence (the report version additionally derives the allowance-corrected contact circle).

**Recommendation:** Make compute_geometry_report call the GearStage property (or move the property's formula into one shared helper) so W_k has a single implementation.

### COV-13 [LOW] DynamicsResponse omits K_Fbeta although the service computes it

*Verification: adjusted.* — *Core confirmed: DynamicFactors carries face_load_factor_root (used at analysis.py:567) but DynamicsResponse (analysis.py:738-747) omits it, and K_Fβ reaches the user only via CapacityFactors in the Tragfähigkeit tab (CapacityPanel.tsx:98-100). But the detail 'the Dynamics tab shows K_Halpha AND K_Falpha' is wrong: DynamicsPanel.tsx renders only K_v/K_Hα/K_Hβ stats (lines 97-101) plus the resonance table - transverse_factor_root IS in the response yet unrendered there too, so the asymmetry sits in the response model AND the panel (K_Fα is itself a serialized-but-invisible field of this tab). Severity low stands; the fix should add both K_Fα and K_Fβ rows (or drop the unused K_Fα from the response).*

Files: `20_code/40_backend/app/api/analysis.py`, `20_code/50_frontend/src/panels/DynamicsPanel.tsx`

DynamicFactors carries face_load_factor_root (K_Fbeta, ISO 6336-1 eq. 39-40) but DynamicsResponse maps only dynamic_factor, transverse_factor_flank/_root, face_load_factor_flank plus resonance data - the Dynamics tab shows K_Halpha AND K_Falpha but K_Hbeta without K_Fbeta. The value does reach the user through CapacityFactors.face_load_factor_root in the Tragfaehigkeit tab, so this is an inconsistency rather than total invisibility. The intermediate c_gammabeta (mesh_stiffness_beta) is likewise internal-only, matching c_gammaalpha being the only exposed stiffness.

**Recommendation:** Add face_load_factor_root to DynamicsResponse and a K_Fbeta row to DynamicsPanel for symmetry with the K_alpha pair.

### COV-14 [LOW] ToothGear.center_x_mm, reference_radius_mm, base_radius_mm, root_radius_mm never consumed

*Verification: confirmed.*

Files: `20_code/40_backend/app/api/analysis.py`, `20_code/50_frontend/src/components/MeshEngagement.tsx`, `20_code/40_backend/app/api/report.py`

Of ToothGear only teeth, tip_radius_mm and half_flank are used: MeshEngagement translates gear 2 by ToothProfileResponse.center_distance_mm (ignoring wheel.center_x_mm, which analysis.py explicitly model_copy's to a), and both the app plot and the report SVG draw base/pitch circles from LineOfAction.base_radius_mm/working_pitch_radius_mm, never from the per-gear reference_radius_mm, base_radius_mm or root_radius_mm. Four serialized fields per gear with zero consumers.

**Recommendation:** Either use them (e.g. draw the root circle in the engagement plot - visually useful) or drop them from ToothGear to keep the contract honest.

### COV-15 [LOW] Echo/duplicate response fields never consumed: ContourResponse.fillet_kind and teeth, FilletCaoResponse.iterations_run/boundary_xy/effective_root_diameter_mm/clearance_mm, GearCapacity.label

*Verification: confirmed.*

Files: `20_code/40_backend/app/api/mesh.py`, `20_code/50_frontend/src/panels/ToothFormPanel.tsx`, `20_code/50_frontend/src/panels/CapacityPanel.tsx`

ContourResponse.fillet_kind is never read (panels use their local FilletSpec state; fillet_approach IS read); ContourResponse.teeth is unused (ContourPlot replicates via pitch_deg). FilletCaoResponse duplicates the contour payload: ToothFormPanel uses only sigma_history_mpa, uniformity_history and converged - iterations_run (implicit in history length), boundary_xy, effective_root_diameter_mm and clearance_mm arrive a second time next to the /api/mesh/contour response for the same cao spec and are never consumed from this model. GearCapacity.label ('Ritzel (Stahl)' etc.) is rebuilt locally by both CapacityPanel and the report and never consumed. Otherwise the TS interfaces in lib/api.ts mirror the backend models field-for-field - no TS-only ghost fields were found in the listed response models.

**Recommendation:** Trim the duplicated FilletCao fields (keep the histories + converged), and either use fillet_kind/label for display or remove them.

### COV-16 [LOW] ExampleResponse alpha_n, beta, alpha_wt, eps_beta and ExampleGear.kind not shown in the Overview

*Verification: confirmed.*

Files: `20_code/50_frontend/src/panels/OverviewPanel.tsx`, `20_code/40_backend/app/api/analysis.py`

OverviewPanel renders a, m_n, eps_alpha, eps_gamma, gears table and notes, but omits normal_pressure_angle_deg, helix_angle_deg, working_pressure_angle_deg, overlap_ratio and the per-gear kind slug (role/material strings cover it in German only). These values are visible in other tabs, so this is partly a deliberate summary cut - but eps_beta next to eps_alpha/eps_gamma would cost nothing.

**Recommendation:** Add alpha_n/beta and eps_beta stats to the overview grid or consciously drop the unused fields from ExampleResponse.


## Dimension B — Frontend structure, duplication, dead weight

### STR-01 [HIGH] DesignPanel micro-geometry editor: pinion edits silently discarded by effectiveStage()

*Verification: confirmed.*

Files: `20_code/50_frontend/src/panels/DesignPanel.tsx`, `20_code/50_frontend/src/lib/store.tsx`

DesignPanel's MicroEditor (Auslegung tab) lets the user enter per-flank C_alpha-a/C_beta/C_beta-e on BOTH gears and 'Übernehmen' writes them into the raw stage. But store.tsx effectiveStage() unconditionally overwrites modifications_pinion with the flank object derived from the Flankenmodifikation [34] correction state (line 676: modifications_pinion: { left: flank, right: flank }), so every consumer sees the correction-tab values and the pinion rows of MicroEditor are dead controls — while the wheel rows DO take effect (effectiveStage leaves modifications_wheel alone). Two competing micro-geometry editors with different data models (per-flank left/right vs 'beide Flanken gleich') and asymmetric behavior per gear. Additionally the draft-follows-stage effect (setDraft(stage)) seeds the draft from the EFFECTIVE stage, so tolerance allowances and correction-derived pinion mods get silently baked into the draft and re-applied as raw values.

**Recommendation:** Make the correction store the one micro-geometry SSOT: drop the pinion rows from MicroEditor (or make them read-only mirrors of the correction tab), and either extend the correction component to gear 2 or route MicroEditor wheel edits through a wheel correction state. Seed the DesignPanel draft from the raw stage, not effectiveStage.

### STR-02 [HIGH] Accuracy-grade triple state: Toleranzen tab grades never reach the capacity calculation

*Verification: confirmed.*

Files: `20_code/50_frontend/src/lib/store.tsx`, `20_code/50_frontend/src/lib/capacityRequest.ts`, `20_code/50_frontend/src/panels/DesignPanel.tsx`

Three independent accuracy-grade states exist: (a) tol.grade1/tol.grade2 — editable in the rendered Toleranzen schema tab, consumed by NOTHING in the frontend; (b) operating.accuracy_grade — used by buildCapacityRequest for K_v/Z_R etc., but no schema attribute or panel binds it, so it is frozen at its default 7 (the store comment even claims it comes 'from the Toleranzen tab'); (c) DesignPanel's local useState grade defaulting to 8 for the ISO 1328 display. Changing DIN 3962 Qualität in the Toleranzen tab therefore has zero effect on the Tragfähigkeit results — misleading, since the FVA original couples them. The defaults only agree by coincidence (7 vs 7 vs 8).

**Recommendation:** Delete operating.accuracy_grade as an independent field and derive it (DERIVED entry) from tol.grade1/grade2 (e.g. max of both, or per-gear when the backend supports it); seed DesignPanel's ISO 1328 grade from the same source.

### STR-03 [HIGH] Root-fillet spec split across four states: Zahnform/FE-Mesh choices never reach deck or geometry report

*Verification: confirmed.*

Files: `20_code/50_frontend/src/panels/ToothFormPanel.tsx`, `20_code/50_frontend/src/panels/MeshPanel.tsx`, `20_code/50_frontend/src/lib/store.tsx`

The store SSOT for fillets is fem.fillet_gear1/fillet_gear2 (drives deckPayload, PairPanel, and the fillet-aware /api/geometry/report call in GeometryPanel). But ToothFormPanel (line 275) and MeshPanel (line 57) each keep their own useState<FilletSpec> starting at {kind:'standard'}, never synced with the store. A user who selects e.g. an elliptic Frühe fillet in the gear's own Zahnform or FE-Mesh tab gets a deck, pair view and Geometrie-tab report still built with the standard fillet (and vice versa: a PairPanel fillet choice is invisible in the Zahnform tab). varUi.fillet is a legitimate fourth spec (sweep-scoped, store-persisted by design). Related staleness bug from the local caching: ToothFormPanel's cached 'standard' comparison contour is only fetched once (if (f.kind !== 'standard' && !standard)) and is NOT invalidated when the stage changes, so after a geometry edit the overlay compares against the old gear's standard contour.

**Recommendation:** Bind ToothFormPanel and MeshPanel to fem.fillet_gearN via wb.setFem exactly like PairPanel does (FilletEditor already takes value/onChange), and reset the cached standard contour whenever stage or gear changes.

### STR-04 [HIGH] Stufenvariation ignores the Werkstoff/operating SSOT: material strengths, densities and min safeties hardcoded

*Verification: confirmed.*

Files: `20_code/50_frontend/src/panels/VariationPanel.tsx`

defaultsFromStage() (lines 135-142) hardcodes steel_sigma_hlim 1500 / sigma_flim 430, plastic 60/35, densities 7850/1410, root_minimum_safety 2.0 and flank_minimum_safety 1.0 instead of reading wb.materials and wb.operating (where flank_minimum_safety defaults to 1.4). The panel offers the material-KIND matrix (pinion_material/wheel_material selects, line 422) but strength values edited in the Werkstoff tab never flow into the sweep, so variation safeties S_F/S_H are computed with kst-E constants even after the user changes materials — wrong output relative to what the material matrix promises. The request's optional steel_modulus_mpa/plastic_modulus_mpa fields are never populated either. Torque, by contrast, is correctly derived from the Leistungsfluss.

**Recommendation:** Seed defaultsFromStage from wb.materials (sigma_hlim/flim, densities, moduli per kind) and wb.operating (root/flank_minimum_safety), and re-seed material kinds from materials.gear1_kind/gear2_kind.

### STR-05 [MEDIUM] Backend _geometry_tab() schema tab unreachable — shadowed by bespoke GeometryPanel, dragging dead store fields and lost inputs with it

*Verification: adjusted.* — *Core confirmed: _geometry_tab registered (components.py 1920-1968, 2896) but Workbench.tsx:250 hardcodes id 'geometry' → GeometryPanel; geometry.* computed bindings (374/387) resolve nowhere ('geometry' not in store namespaces or DERIVED → '–'); stage.tooth_end_chamfer_*_mm (265) exists in NEITHER frontend StageParams nor backend stage_params.py; shaft.* and geometryUi.profile_shift_mode/profile_generation_gear* have no other consumer. ONE detail wrong: tool_*_gear2 is NOT '.ste-import-only' — VariationPanel's h_fp2/rho_fp2 rows + applyVariant (lines 285-286) write tool_addendum_factor_gear2/tool_tip_radius_factor_gear2; only the dedendum/root-form-height/edge-break gear-2 overrides (and tip_diameter_*_mm) are truly unreachable in the UI.*

Files: `20_code/40_backend/app/services/uimodel/components.py`, `20_code/50_frontend/src/components/Workbench.tsx`, `20_code/50_frontend/src/lib/store.tsx`

components.py registers _geometry_tab() (id 'geometry', lines 1920-1968) on cylindrical_mesh, but Workbench.tsx hardcodes { id: 'geometry', render: <GeometryPanel/> } (line 250) and never calls schemaTab(s,'cylindrical_mesh','geometry') — the whole schema tab is unreachable. Consequences: (a) its computed bindings geometry.root_diameter_gear*_mm / geometry.tip_edge_break_gear*_mm reference a 'geometry' namespace that exists neither in store.tsx's namespace whitelist nor in DERIVED (documented in uimodel/schema.py as the contract) — they would render '–' forever even if mounted; (b) tooth_end_chamfer binds stage.tooth_end_chamfer_pinion_mm/_wheel_mm, fields that exist in NEITHER the frontend StageParams nor the backend model; (c) inputs only this tab offers are unreachable anywhere: tip-diameter overrides (stage.tip_diameter_*_mm), the per-gear tool overrides (tool_*_gear2 — currently reachable only via .ste import), profile_shift_mode/profile_generation modes; (d) shaft.u_coordinate_gear*_mm, shaft.rotation_negative_u_deg (whole ShaftUiState) and geometryUi.profile_shift_mode/profile_generation_gear* are store fields bound only here — dead weight.

**Recommendation:** Either render the schema geometry tab's sections that the bespoke panel does not cover (tool profile, tip diameter, shaft position) inside GeometryPanel via <SchemaTab/>, or delete _geometry_tab() plus the orphaned attributes/store fields; add DERIVED entries (or a geometry response cache in the store) for the computed geometry.* paths if kept.

### STR-06 [MEDIUM] UiSchema.rules served but never consumed; several rule paths reference nonexistent bindings

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/uimodel/components.py`, `20_code/40_backend/app/services/uimodel/schema.py`, `20_code/50_frontend/src/lib/uischema.ts`, `20_code/50_frontend/src/panels/GlossaryPanel.tsx`

schema.py documents that 'the frontend evaluates them [DependencyRules] to lock/compute fields' and that 'the glossary lists them' — but no frontend code reads schema.rules at all (grep: zero consumers). Every coupling is hand-reimplemented: DERIVED + set() write-throughs in store.tsx, row-level locked_if/locked_ifs/visible_if in SchemaTab, and VariationPanel's own fix_center_distance lock logic (lines 301/392). The GlossaryPanel renders the hardcoded lib/glossary.ts, not the schema attributes/rules, so labels/help texts exist in two sources that can drift. Several rules also target paths that exist nowhere: materials.gear_kind (when), capacity.method_gear1/2, fem.elements_tooth_height/root/thickness/width (the 'user' meshing-accuracy show rule — there are no such attributes or store fields), variation.fix_center_distance/z1/z2/x2 (store namespace is varUi and the flags live in panel-local state), tabs.cylindrical_mesh.transient_fem.

**Recommendation:** Either implement a rules evaluator (and render rules in the glossary as documented), or strip the rules list to documentation status and delete the ones pointing at nonexistent paths; long-term, generate the glossary's parameter entries from schema.attributes to remove the duplicate catalog.

### STR-07 [MEDIUM] QuickView recomputes u, d_w and b_gem client-side and double-fetches /api/geometry alongside GeometryPanel

*Verification: confirmed.*

Files: `20_code/50_frontend/src/components/QuickView.tsx`, `20_code/50_frontend/src/panels/GeometryPanel.tsx`

QuickView.tsx lines 43-50 compute u = z2/z1, d_w,i = 2a*z_i/(z1+z2) and b_gem = min(b1,b2) in TypeScript although the backend geometry-report SSOT (/api/geometry/report, ADR-024) serves pair.gear_ratio, gear.working_pitch_diameter_mm and pair.common_face_width_mm. The TS formulas duplicate DIN 21771 logic that can drift from the backend (e.g. if working pitch handling changes for helical/x-shifted cases). Additionally, when the stage node's Geometrie tab is open, QuickView and GeometryPanel each POST the identical stage to /api/geometry independently (GeometryPanel.run line 298; QuickView effect line 34) — duplicate fetch with no shared cache. The DISPLAY duplication of the Hauptgeometrie/Durchmesser tables in QuickView is intended (persistent summary), only the recomputation and double fetch are accidental.

**Recommendation:** Cache the last GeometryResponse/GeometryReportResponse in the store (one fetch per stage change) and have QuickView read gear_ratio/working_pitch_diameter_mm/common_face_width_mm from the report instead of recomputing.

### STR-08 [MEDIUM] MeshEngagement recomputes eps_alpha = g_alpha/p_et in TS instead of using the served transverse_contact_ratio

*Verification: confirmed.*

Files: `20_code/50_frontend/src/components/MeshEngagement.tsx`

Line 176: const epsAlpha = loa ? loa.path_of_contact_mm / loa.transverse_base_pitch_mm : null — a client-side recomputation of eps_alpha shown in the footer, although /api/geometry serves transverse_contact_ratio and the embedding GeometryPanel already holds it (res.transverse_contact_ratio is displayed 30 px above in the Stat row). If the backend eps ever accounts for usable tip diameters/tip chamfer differently from the drawn A-E path, the two eps values on the same tab diverge. alpha_wt is likewise shown twice on the tab from two different endpoints (report pair value and line_of_action value) — harmless today but the recomputed eps should come from the SSOT.

**Recommendation:** Pass eps_alpha (and alpha_wt) into MeshEngagement as props from the panel's GeometryResponse, or add them to the ToothProfileResponse line_of_action so the value is backend-computed.

### STR-09 [MEDIUM] effectiveStage() returns a new object identity on EVERY store change — identity-keyed effects refetch/reset spuriously

*Verification: confirmed.*

Files: `20_code/50_frontend/src/lib/store.tsx`, `20_code/50_frontend/src/components/QuickView.tsx`, `20_code/50_frontend/src/components/MeshEngagement.tsx`, `20_code/50_frontend/src/panels/VariationPanel.tsx`, `20_code/50_frontend/src/panels/ToothFormPanel.tsx`

The store memo (dep [state]) rebuilds stage: effectiveStage(state) as a fresh object whenever ANY namespace changes (a calc checkbox, a varUi step, an fem toggle). Panels whose useEffect deps are the stage OBJECT then re-run even though the stage content is unchanged: QuickView and MeshEngagement re-POST /api/geometry and /api/tooth-profile, GeometryPanel re-runs geometry+report, ToothFormPanel refetches contours. Worst case: VariationPanel's effect (line 183, deps [stage, torqueT1]) re-seeds the whole step-1 request with defaultsFromStage — so the panel's own setVar({step:2}) at run() start triggers a store change that resets the local request r; navigating back to step 1 shows re-seeded defaults instead of the persisted v.req the user configured. CapacityPanel and DynamicsPanel already defend with a JSON.stringify reqKey — the pattern is inconsistent across panels.

**Recommendation:** Memoize effectiveStage on the inputs it actually reads (stage, tol allowances, correction) or key the effects on a content hash like CapacityPanel does; bind VariationPanel step 1 to the persisted varUi.req instead of a local copy that gets re-seeded.

### STR-10 [MEDIUM] MeshPanel density/layers and results panel-local, duplicating and diverging from the fem.* deck settings; results lost on tab switch

*Verification: confirmed.*

Files: `20_code/50_frontend/src/panels/MeshPanel.tsx`, `20_code/50_frontend/src/panels/ToothFormPanel.tsx`, `20_code/50_frontend/src/panels/FemResultsPanel.tsx`

Contrary to the store-SSOT convention PairPanel follows (fem.refine_*, fem.face_layers, fem.fillet_gearN via wb.setFem), MeshPanel keeps refineRoot/refineFlank/refineThickness/layers/fillet in useState — the per-gear FE-Mesh tab therefore edits a parallel set of density values that never feed the deck, and its convergence check duplicates PairPanel's preseed but does not write the converged level back to fem.refine_*. Because Workbench renders only the active tab, all of MeshPanel's results (3D mesh, 2D preview, convergence, fillet ranking, sweep), ToothFormPanel's contours/CAO history and FemResultsPanel's parsed upload (a manual file import) are destroyed on every tab switch and must be regenerated — while varUi results were deliberately store-persisted for exactly this reason.

**Recommendation:** Move MeshPanel's density/fillet onto fem.* (per-gear fields already exist) and persist expensive results (at minimum the FemResultsPanel upload and MeshPanel mesh) in store slices keyed by gear, mirroring the varUi pattern.

### STR-11 [MEDIUM] Toleranzen Achsabstandsabmasse and tooth-plot options carried but never wired: backlash delta stays empty

*Verification: confirmed.*

Files: `20_code/50_frontend/src/panels/GeometryPanel.tsx`, `20_code/50_frontend/src/lib/store.tsx`, `20_code/50_frontend/src/lib/api.ts`

GeometryReportRequest supports center_distance_allowance_mm (plus ball_diameter_gear*_mm and span_allowance overrides), and the rendered Toleranzen tab edits tol.a_upper_um/a_lower_um (A_Ae/A_Ai) — but GeometryPanel's report call passes only stage + fillets, and the Din3967Section call passes only the series. So the user-editable Achsabstandsabmasse never reach the backend, and the report's backlash-delta row (Delta j_t/Delta j_n, GeometryPanel line 456) renders '–' permanently; pair.center_distance_allowance_mm stays null. tol.custom_diameter1/2 ('Anzeige benutzerdefinierter Durchmesser im Zahnplot'), tol.aw_factor_mode and tol.aw_selection are likewise bound checkboxes/dropdowns with no consumer anywhere (the A_We mean is always taken regardless of aw_selection).

**Recommendation:** Pass center_distance_allowance_mm: (tol.a_upper_um - tol.a_lower_um)/2/1000 (or upper/lower separately once the API takes both) into every geometryReport call; either implement the custom-diameter overlay in the tooth plot or drop the two checkboxes; honor aw_selection or remove the row.

### STR-12 [MEDIUM] Dead operating-store knobs sent in every capacity request but editable nowhere

*Verification: adjusted.* — *Core confirmed: of the listed fields only operating.static_mode has a binding (components.py 1204, rendered via RowRef 2176); compute_dynamics/dynamic_factor/face_load_factor/flank_life_factor/root_life_factor/static_minimum_safety/static_overload_factor have no schema row or panel writer, all travel in buildCapacityRequest, and 'Nutzereingabe' yields the fixed ?? 2.0 fallback (capacityRequest.ts 51-52) — half-wired as claimed. ONE detail wrong: flank/root_life_factor are NOT overrides made 'redundant with the native e1e7e21 sub-factors' — iso6336.py uses conditions.flank/root_life_factor directly as THE Z_NT/Y_NT in σ_HP/σ_FP (lines 309/331) and echoes them back as life_factor_flank/root (349-357); there is no separately computed native Z_NT, so deleting them (per the recommendation) would remove the only Z_NT/Y_NT source — they need a UI input or an N_L-based computation instead.*

Files: `20_code/50_frontend/src/lib/store.tsx`, `20_code/50_frontend/src/lib/capacityRequest.ts`

OperatingState fields that no schema attribute or panel binds (checked against every binding in components.py and all panels): compute_dynamics (always true), dynamic_factor (K_v override, frozen 1.0), face_load_factor (K_Hbeta override, frozen 1.0 — buildCapacityRequest maps 1.0 to 'native', so the override path is unreachable), flank_life_factor/root_life_factor (Z_NT/Y_NT overrides, frozen 1.0 — now redundant with the native e1e7e21 sub-factors), static_minimum_safety, and static_overload_factor: the Statik dropdown operating.static_mode IS rendered, but selecting 'Nutzereingabe' yields a fixed K_A,stat = 2.0 (capacityRequest.ts line 52 ?? 2.0) because no row binds the value — a half-wired flow. They all travel in every /api/capacity request, suggesting configurability that does not exist.

**Recommendation:** Add schema rows for the fields that should be user inputs (K_A,stat and S_Smin next to static_mode with visible_if, K_v/K_Hbeta overrides in the capacity tab), and delete the ones that should stay native (compute_dynamics, life-factor overrides) from the store and request builder.

### STR-13 [MEDIUM] CapacityResponse allowable_wear_um and deformation_mm served but displayed nowhere

*Verification: adjusted.* — *Panel claim confirmed: typed in api.ts 97-98, computed by vdi2736.py 419-420, and no frontend component reads either (grep); GearCard shows wear_um (CapacityPanel 281-285) without its W_zul counterpart. But 'displayed nowhere' overstates: the server-rendered HTML system report DOES output both (api/report.py 294-305, W_zul and λ rows), so the gap is the interactive panels only — keep as medium with the scope narrowed to CapacityPanel/UI.*

Files: `20_code/50_frontend/src/lib/api.ts`, `20_code/50_frontend/src/panels/CapacityPanel.tsx`

GearCapacity types allowable_wear_um (W_zul — the VDI 2736 wear limit the store even configures via operating.allowable_wear_mode '0.1_mn') and deformation_mm (tooth deformation lambda), both computed by the backend, but no panel renders them: CapacityPanel's GearCard shows wear_um without its permissible counterpart, so the wear check displays a value with no pass/fail context, and the deformation result is completely invisible in the UI.

**Recommendation:** Add W_zul (with a good/bad tone vs W_m, matching the safety rows) and the deformation row to GearCard's VDI branch.

### STR-14 [MEDIUM] Overview navigation cards discard their target — all three land on the stage node

*Verification: confirmed.*

Files: `20_code/50_frontend/src/panels/OverviewPanel.tsx`, `20_code/50_frontend/src/components/Workbench.tsx`

OverviewPanel's jump-off cards call props.onNavigate('wheel.mesh' | 'wheel.toothform' | 'variation'), but Workbench.tsx line 230 wires onNavigate={() => setActive('stage')} — the key parameter is ignored, so the 'FE-Mesh', 'Zahnform' and 'Stufenvariation' cards all open the Stirnradstufe node's Geometrie tab. 'variation' is even a valid NodeId that could be routed directly; the wheel.* keys need node+tab selection which the callback never attempts. The card labels promise navigation that does not happen.

**Recommendation:** Route the key: setActive('variation') for variation, and for 'wheel.*' set active='wheel' plus tabByNode.wheel to 'mesh'/'toothform'.

### STR-15 [LOW] 31 dead i18n keys; CalcSelectionPanel banner hardcoded, bypassing its own key

*Verification: confirmed.*

Files: `20_code/50_frontend/src/lib/i18n.tsx`, `20_code/50_frontend/src/panels/CalcSelectionPanel.tsx`

Static cross-reference of all 436 DICT keys against every t()/template usage finds 31 never referenced: the whole tree.* family (tree.model/stage/geometry/capacity/dynamics/pinion/wheel/toothform/mesh/calcs/deck/overview/design/pair/glossary — obsolete since the tree is built from model instances with instanceLabel()), quick.title/quick.empty (QuickView headers are now inline locale ternaries in Workbench), calc.banner (CalcSelectionPanel hardcodes the long DE/EN banner text inline via pick() instead of t('calc.banner')), cap.quality/cap.static/cap.materials, variation.overlay/variation.matrix, mesh.params/mesh.stats/mesh.preseedDone/mesh2d.caption, geo.mesh, attr.dbCircle, common.running/common.download. Dynamic-prefix families (gr.*, mesh.fillet.*, tf.*, fem.field.*, mesh.preset.*, mesh.convergence.*, pair.gear*) were excluded from the count.

**Recommendation:** Delete the dead keys; in CalcSelectionPanel replace the inline banner with the calc.banner key (or delete the key).

### STR-16 [LOW] Locale/format inconsistency: toFixed dot-decimals and MPa vs N/mm2 for the same quantities across panels

*Verification: confirmed.*

Files: `20_code/50_frontend/src/panels/MeshPanel.tsx`, `20_code/50_frontend/src/panels/PairPanel.tsx`, `20_code/50_frontend/src/components/SchemaTab.tsx`, `20_code/50_frontend/src/lib/format.ts`

format.ts declares 'ONE locale-aware formatter for every user-visible number' (comma decimals in DE), but user-visible values still use raw toFixed: MeshPanel sigma/delta/clearance/min-J (lines 241, 265, 293-298, 350-363), PairPanel center distance a (line 125), roll angle phi (283) and torque M2 (329), and SchemaTab's run_meshing result message (min J, lines 71-72). The identical quantities elsewhere go through fm.num — e.g. clearance_mm is fm.num(...,3) in ToothFormPanel but toFixed(2) in MeshPanel; a is fm.num in QuickView/GeometryPanel but toFixed in PairPanel — so DE users see mixed comma/dot decimals across adjacent tabs. Stress units are also labeled 'MPa' in the FE panels but 'N/mm²' in CapacityPanel for the same physical quantity.

**Recommendation:** Route the listed literals through useFmt() and pick one stress-unit label (N/mm² per the norm tabs, or document MPa as the FE convention).

### STR-17 [LOW] Schema binds correction.tri_tip_form / correction.tri_root_form — fields missing from CorrectionState

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/uimodel/components.py`, `20_code/50_frontend/src/lib/store.tsx`

The generated corr_{key}_form attributes exclude 'profile_slope', 'twist' and 'waviness' (components.py line 1385) but not 'tri_tip'/'tri_root', and _mod_block('tri_tip')/_mod_block('tri_root') render form rows in the Flankenmodifikation 'Weitere Formen' tab. CorrectionState has tri_tip_on/tri_tip_um and tri_root_on/tri_root_um but no *_form fields — the only rendered-tab bindings missing from the store (verified against every other binding in components.py). The enum select renders with no selection and a picked value lands as an undeclared ad-hoc key via set(), invisible to the typed interface and any consumer.

**Recommendation:** Add tri_tip_form/tri_root_form (default e.g. 'linear') to CorrectionState + defaults, or extend the form-suffix exclusion to tri_tip/tri_root.

### STR-18 [LOW] wheelBody.cut_diameter_mode dead store field

*Verification: confirmed.*

Files: `20_code/50_frontend/src/lib/store.tsx`, `20_code/40_backend/app/services/uimodel/components.py`

WheelBodyState.cut_diameter_mode (default 'user') exists in the store but no schema attribute binds it (the wheel-body tab binds only design_mode, angular_position_deg, cad_name, cut_diameter_mm, stiffness_mode and the derived design_is_cad) and no panel reads it — dead weight in the SSOT contract.

**Recommendation:** Either add the FVA cut-diameter-mode dropdown row to _wheel_body_tab() or remove the field.


## Dimension C — The seven fillet approaches in the UI

### FIL-01 [HIGH] ToothFormPanel keeps a stale 'standard' reference contour across gear/stage switches

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/panels/ToothFormPanel.tsx`

The standard-fillet overlay is fetched once and cached in `standard` state with the guard `if (f.kind !== "standard" && !standard)` (line 289), but `standard` is never invalidated. The component instance survives switching the tree node pinion->wheel (same component type at the same slot in Workbench.tsx, no key), and the useEffect on [props.gear, stage] refetches only `current`. Result: with a non-standard fillet selected, switching gear (z1=51 -> z2=52) or editing the stage overlays the NEW gear's optimized contour against the OLD gear's/old stage's standard contour - a wrong comparison plot including wrong dashed d_f/d_Ff reference circles (ContourPlot uses the first contour as ref).

**Recommendation:** Reset `standard` (and `current`/`cao`) when props.gear or stage change - e.g. setStandard(null) inside the useEffect before load(), or key the panel per gear in Workbench (`<ToothFormPanel key={gear} .../>`) and refetch standard together with current.

### FIL-02 [HIGH] Variation Fussform tooltip claims the fillet reaches the FE deck, but it never does

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/panels/VariationPanel.tsx`, `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/lib/i18n.tsx`, `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/lib/deck.ts`

i18n `var.fussformNote` (i18n.tsx:274-277) says "Fußform wirkt auf den Kontur-Vergleich (Schritt 4) und das FE-Deck", and the code comment at VariationPanel.tsx:436-437 repeats "carried into every variant contour/deck". In reality `varUi.fillet` is only used for the step-4 contour overlays (line 242); `applyVariant` (lines 269-290) writes only stage fields, never fem.fillet_gear1/2, and deckPayload reads exclusively fem.fillet_gear1/2. The backend VariationRequest (analysis.py:810) has no fillet field either. A user who picks an optimized Fußform in the Variation tab and downloads the deck gets a standard-fillet deck while the UI told them otherwise.

**Recommendation:** Either propagate v.fillet into fem.fillet_gear2 (and optionally gear 1) on 'Übernehmen', or correct the tooltip/comment to say the Fußform affects only the contour comparison.

### FIL-03 [MEDIUM] Dong sweep combos missing: frontend SWEEPABLE does not mirror backend _SWEEP_RANGES

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/panels/MeshPanel.tsx`, `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/api/mesh.py`

Backend _SWEEP_RANGES (mesh.py:552-564) includes ("bezier","dong") with four sweepable parameters (dv1, dv4, dv2, dv3). The frontend SWEEPABLE list (MeshPanel.tsx:34-47), whose comment claims it "mirrors the backend's _SWEEP_RANGES", omits Dong entirely, so the only hob-manufacturable optimized approach can never be swept from the UI. All other combos (kassem/e_f, fruehe/tilt+aspect, landi/ra_f+d2_frac, roth/be, voith/b_f+gamma_deg) are present and the i18n key mesh.fillet.bezier-dong exists.

**Recommendation:** Add the four (bezier, dong, dv*) entries to SWEEPABLE (at least the primary dv1) so the button row matches the backend ranges.

### FIL-04 [MEDIUM] fillet-compare include_cao is unreachable - the bionic-cao ranking row can never appear

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/lib/api.ts`, `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/panels/MeshPanel.tsx`, `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/api/mesh.py`

The backend FilletCompareRequest has include_cao (mesh.py:453, default False) that adds the "bionic-cao" row. meshApi.filletCompare (api.ts:744-745) posts only {stage, gear} and MeshPanel offers no toggle, so the comparison table always ranks 8 of the 9 strategies; the CAO row (and its prepared i18n label mesh.fillet.bionic-cao in the table path) is dead. The user cannot see how the self-optimizing CAO fillet ranks against the literature approaches.

**Recommendation:** Add an include_cao checkbox next to the 'Strategien vergleichen' button (with a note about the ~10 s FE growth loop) and pass it through meshApi.filletCompare.

### FIL-05 [MEDIUM] MeshPanel presents gear-1 results as the wheel's after a pinion->wheel node switch

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/panels/MeshPanel.tsx`, `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/components/Workbench.tsx`

MeshPanel holds mesh/preview/ranking/sweep/convergence results in local state and has no effect keyed on props.gear. Because Workbench renders `<MeshPanel gear={1}/>` and `<MeshPanel gear={2}/>` at the same tree position without a key (Workbench.tsx:283/295, render at line 421), React keeps the same instance when the user switches the tree node while staying on the FE-Mesh tab: all displayed results (fillet ranking, sweep table, 3D hull, convergence levels) still belong to gear 1 but now sit under the wheel node with no gear indicator. Conversely, the Workbench comment "hidden tabs keep their state" (line 7/307) is false for tab switches, which unmount the panel and drop the fillet selection and all results.

**Recommendation:** Key the per-gear panels by gear (`key={gear}`) or clear/refetch results in an effect on props.gear; optionally show response.gear next to the ranking/sweep tables. Fix or implement the 'hidden tabs keep their state' claim.

### FIL-06 [MEDIUM] Contour legend key mixes local kind with fetched approach - can render a raw i18n key

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/panels/ToothFormPanel.tsx`

ToothFormPanel.tsx:321-324 builds the legend key from the LOCAL editor state `fillet.kind` combined with the FETCHED `current.fillet_approach`. Between changing the kind dropdown and pressing Run these disagree: e.g. after running elliptic/kassem and switching the dropdown to bezier, the key becomes "mesh.fillet.bezier-kassem", which does not exist, and useT() falls back to the raw key string in the legend; switching to standard yields "mesh.fillet.standard-kassem". The response already carries the matching `fillet_kind`.

**Recommendation:** Derive the key entirely from the response: use `current.fillet_kind` instead of `fillet.kind` (key = current.fillet_approach ? `mesh.fillet.${current.fillet_kind}-${current.fillet_approach}` : `mesh.fillet.${current.fillet_kind}`).

### FIL-07 [MEDIUM] FilletEditor shows gamma_deg and b_f for bionic-cao although CaoFillet ignores them

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/panels/ToothFormPanel.tsx`, `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/services/model/cao_fillet.py`

The gamma_deg/b_f rows render for `f.kind === "bionic"` without an approach filter (ToothFormPanel.tsx:178-208), so with approach=cao the user can edit wedge angle and arc factor - but FilletSpec.strategy() builds CaoFillet(cao_step, cao_iterations, cao_tol) only (mesh.py:138-143; CaoFillet dataclass has no gamma/b_f), so the edits silently change nothing in contour, mesh, or deck. The analogous case junction_offset_mm is handled correctly (hidden for cao/landi/dong).

**Recommendation:** Gate the gamma_deg/b_f rows on `approach === "voith"`, exactly like the cao_* rows are gated on approach === "cao".

### FIL-08 [MEDIUM] Schema-tab meshing check hardcodes standard fillet, diverging from the deck it accompanies

*Verification: adjusted.* — *Core confirmed: SchemaTab.tsx:55-69 posts fillet {kind:"standard"} for both gears, so with fem.fillet_gear1/2 configured (the store SSOT the deck uses, deck.ts:37-38) the reported quad counts / min-J describe a mesh that is not the deck's — medium stands. Two details to correct: (a) the refine-level criticism is off — the level comes from loaddist.meshing_accuracy, the Lastverteilung tab's own FVA 'Vernetzungsgrad' attribute (components.py:1255-1266), replicated by design, so ignoring fem.refine_*_gear2 there is intended; (b) the action lives in the loaddist_fem tab, the deck download in transient_fem — 'the deck it accompanies' overstates proximity, though both should describe the same FE model. The fix should address only the fillet.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/components/SchemaTab.tsx`

The `loaddist.run_meshing` action (SchemaTab.tsx:51-75) posts /api/mesh/preview with `fillet: { kind: "standard" }` for both gears (and the shared refine level, ignoring the *_gear2 overrides), while the deck download in the same schema-driven tab family uses deckPayload with fem.fillet_gear1/2. With an optimized fillet configured, the reported quad counts and min scaled Jacobian describe a mesh that is not the one the deck will contain - the quality gate can pass here and fail in the deck (or vice versa).

**Recommendation:** Use wb.fem.fillet_gear1/fillet_gear2 (and the per-gear refine overrides) in the run_meshing previews so the quick check validates the actual deck mesh.

### FIL-09 [LOW] Variation fillet editor lacks the manufacturability note and any CAO cost/feedback

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/panels/VariationPanel.tsx`

VariationPanel mounts FilletEditor (line 438) without the ManufacturabilityNote shown at every other mount point, so the molded/WEDM-only warning for elliptic/bezier-roth/bionic is missing exactly where material pairing (plastic wheel) is being decided. Selecting bionic-cao there also makes each step-4 overlay run a full server-side CAO growth loop per variant geometry, sequentially awaited in buildOverlays (lines 216-250) with no busy indicator; the CAO convergence history itself is surfaced only in the Zahnform tab (which is a reasonable home for the diagnostics, but a non-converged budget stop is invisible here and in PairPanel/MeshPanel).

**Recommendation:** Render ManufacturabilityNote under the Variation FilletEditor and add a small busy/спinner state to buildOverlays; consider a hint that CAO overlays are expensive per variant.

### FIL-10 [LOW] Glossary covers only the pre-ADR-023 fillet parameters

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/lib/glossary.ts`

The glossary has entries for e_f, Be, gamma_b, b_f, rho_F, trochoid and Freigang, but nothing for the parameters introduced with the seven-approach set: Frühe tilt/aspect, Landi ra_f/d2_frac, Dong dv0-dv4, and the CAO cao_step/cao_iterations/cao_tol. Users meeting 'P2-Interpolation (x)' or 'Wachstumsfaktor' in the editors find no explanation in the Glossar tab.

**Recommendation:** Add glossary entries for the Frühe, Landi, Dong and CAO parameters (the FilletSpec field comments in api/mesh.py already contain the needed one-liners).

### FIL-11 [LOW] Untranslated hardcoded German strings in the fillet-compare/mesh controls

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/panels/MeshPanel.tsx`

The fillet ranking table header 'Strategie' (line 283), the 'Jacobi-Heatmap' checkbox label (line 222) and the view toggle options '3D-Ansicht'/'2D-Schnitt' (lines 229-230) are hardcoded German and bypass useT(), so the English locale shows German labels amid otherwise translated fillet UI.

**Recommendation:** Route these through i18n keys like the neighbouring labels.


## Dimension D — Norm currency & analytical correctness

### NRM-01 [HIGH] Helical input silently evaluated with spur-only inspection/backlash/sliding formulas in the geometry SSOT report

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/geometry/report.py`, `20_code/40_backend/app/api/analysis.py`, `20_code/50_frontend/src/panels/GeometryPanel.tsx`

compute_geometry_report() is documented as spur-scoped (docstring lines 15-16) but has NO guard for beta != 0: s_t = m_n-based ('spur: m_t = m_n', line 256), chordal s_c/h_c spur (lines 259-265), _auto_span_teeth k-selection uses d_v = z*m_n + 2x*m_n 'V-circle (spur)' (line 169), _ball_measure is 'spur external' with beta_b = 0 (line 190), M_dR = M_dK 'spur' (line 357), and j_t = j_bn/cos(alpha_wt) missing the cos(beta_b) division of ISO 21771 section 5.5. GearStage/StageParams accept any helix_angle_deg (frontend GeometryPanel.tsx line 368 and DesignPanel line 213 are free inputs), and /api/geometry/report serves the result without a warning or error - every inspection dimension (W_k, M_dK, s_cn), tooth thickness and backlash value is silently wrong for a helical stage. stage.check_validity() only flags beta > 45 deg.

**Recommendation:** Add an explicit guard in compute_geometry_report: raise (or append a prominent note and null the affected fields) when abs(helix_angle_deg) > ~1e-9, until the beta_b terms of DIN 21773/ISO 21771 are implemented. Do not return spur numbers unlabeled.

### NRM-02 [HIGH] ToothProfile and all root-fillet strategies are spur-only but accept helical stages without any guard

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/geometry/tooth_form.py`, `20_code/40_backend/app/services/geometry/root_fillet.py`, `20_code/40_backend/app/api/mesh.py`

ToothProfile mixes normal and transverse quantities under the spur assumption (reference_radius_mm = m_n*z/2 'spur: m_t = m_n' line 114, root_diameter_mm = m_n*z - ... line 123, psi_base built from alpha_n while base_diameter comes from the stage's transverse plane), yet from_stage() takes any GearStage without checking stage.helix_angle_deg. Every consumer inherits the error silently for beta != 0: /api/tooth-profile plots, the FE mesh contour (api/mesh.py), all seven fillet strategies (root_fillet.py builds junctions from profile._involute_half_angle), mating_tip_clearance, and the fillet-aware effective-root values in the geometry report. By contrast tooth_root.py handles helical correctly via the virtual gear - so the codebase looks helical-capable while the profile geometry is not.

**Recommendation:** Raise in ToothProfile.from_stage (and FilletSpec.strategy consumers) when helix_angle_deg != 0, or convert to the proper transverse-plane profile (m_t, alpha_t, x*tan(alpha_n) terms). A loud failure is required by the project's own spur-scope statement.

### NRM-03 [HIGH] evaluate_iso6336 silently drops all three helical capacity factors (Z_H with beta_b=0, Z_beta, Y_beta) despite roadmap claiming helical support

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/capacity/iso6336.py`, `20_code/40_backend/app/api/analysis.py`, `20_code/40_backend/app/services/capacity/vdi2736.py`

zone_factor() hardcodes beta_b = 0.0 ('spur; helical base helix angle added with the helical validation', iso6336.py line 61); sigma_H0 (line 254) has no Z_beta = 1/sqrt(cos beta) term (ISO 6336-2); Iso6336LoadCase.helix_factor_root (Y_beta, line 116) defaults to 1.0 and _run_capacity in api/analysis.py never sets it, so sigma_F misses Y_beta too. vdi2736.flank_stress reuses the same spur zone_factor. Meanwhile ToothRootGeometry, eps_beta, Z_eps and K_v ARE helical-aware, and the module docstring plus implementation_roadmap.md C2b ('helical (z_n, beta_b, Z_beta, Y_beta)' marked done) claim helical validation - the sub-factor modules were validated with hand-fed values, not end-to-end through evaluate_iso6336. A helical stage entered in the UI gets a numerically wrong sigma_H/sigma_F/S_H/S_F with no warning. The variation kernel (kernel.zone_factor with base_helix, sweep Z_beta) implements these correctly, so the two paths disagree for the same design.

**Recommendation:** Compute beta_b = asin(sin(beta)*cos(alpha_n)) in zone_factor, multiply sigma_H0 by Z_beta = 1/sqrt(cos beta), and set helix_factor_root from ISO 6336-3 eq. 66 (Y_beta = (1 - eps_beta*beta/120deg)/cos^3(beta), caps eps_beta<=1, beta<=30deg) in _run_capacity; or raise for beta != 0 until then.

### NRM-04 [HIGH] Stufenvariation Y_beta uses the pressure angle in radians instead of the helix angle in degrees (and the outdated pre-2019 formula)

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/variation/sweep.py`

sweep.py line 239: y_beta = 1.0 - geometry.overlap_ratio * np.radians(spec.normal_pressure_angle_deg) / 120.0. Verified against ISO 6336-3:2019 clause 8.3 eq. (66) (rendered page 26): Y_beta = (1 - eps_beta * beta/120deg) * 1/cos^3(beta), beta in DEGREES (reference HELIX angle), with eps_beta capped at 1.0 and beta capped at 30deg. The code (a) uses alpha_n instead of beta, (b) converts to radians before dividing by 120 (so the subtrahend is ~57x too small), (c) omits the 1/cos^3(beta) factor added in the 2019 edition (which can push Y_beta above 1), and (d) omits the eps_beta <= 1 cap. For a beta = 25 deg variant with eps_beta = 1.5 the code yields ~0.996 (clipped to [0.75, 1]) instead of ~1.045 - all helical variants' root stresses and S_F rankings in the Stufenvariation are wrong.

**Recommendation:** Replace with y_beta = (1 - np.minimum(geometry.overlap_ratio, 1.0) * np.minimum(np.degrees(beta), 30.0) / 120.0) / np.cos(beta)**3 and drop the 0.75..1.0 clip (the caps replace it).

### NRM-05 [HIGH] ISO 6336-3 root size factor Y_X: material-group-to-formula mapping is scrambled vs Table 5

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/capacity/iso6336_root_strength.py`

Verified against ISO 6336-3:2019 Table 5 (extracted text, page 43): St, V, GGG(perl/bai), GTS get Y_X = 1.03 - 0.006*m_n (floor 0.85); Eh, IF, NT, NV get Y_X = 1.05 - 0.01*m_n (floor 0.80); GG, GGG(ferr) get 1.075 - 0.015*m_n (floor 0.70). The code's size_factor() (lines 63-75) instead gives CASE_HARDENED + THROUGH_HARDENED + NITRIDED the (1.03 - 0.006, min 0.85) formula, NORMALIZED the (1.05 - 0.010, min 0.85) formula, and CAST_IRON floor 0.85: case-hardened and nitrided gears get the wrong (too mild) formula, normalized steel the wrong (too steep) one, and both the nitrided/case floor (0.80) and cast-iron floor (0.70) are wrong. Invisible in all current tests because kst-E has m_n = 1 (Y_X = 1 for m_n <= 5), but any gear with m_n > 5 mm gets a wrong sigma_FP/S_F.

**Recommendation:** Map NORMALIZED + THROUGH_HARDENED to max(0.85, 1.03 - 0.006*m_n); CASE_HARDENED + NITRIDED to max(0.80, 1.05 - 0.01*m_n); CAST_IRON to max(0.70, 1.075 - 0.015*m_n), and add a m_n > 5 test pinning Table 5.

### NRM-06 [HIGH] VDI 2736 'safety factors' already divide by S_min, then the UI/variation compare them against S_min again (double-counted minimum safety, mixed semantics with the ISO branch)

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/capacity/vdi2736.py`, `20_code/50_frontend/src/panels/CapacityPanel.tsx`, `20_code/40_backend/app/services/variation/sweep.py`, `20_code/40_backend/app/api/report.py`

vdi2736.permissible_root_stress = sigma_FlimN/S_Fmin and permissible_flank_stress = sigma_HlimN*Z_R/S_Hmin (VDI 2736 eq. 17 convention), and evaluate_vdi2736 reports root_safety = sigma_FP/sigma_F - i.e. S_F/S_Fmin, NOT the norm's S_F = sigma_FlimN/sigma_F >= S_Fmin. The frontend then labels this 'S_F'/'S_H' and colors it red when below req.root_minimum_safety (CapacityPanel.tsx lines 146-165: tone(g.root_safety, minRoot) with minRoot = S_Fmin = 2.0) - the minimum safety is applied twice: a plastic gear with true S_F = 3.0 displays 1.5 and shows red against the 2.0 threshold. The ISO branch in the same table reports the un-normalized S_F = sigma_FP/sigma_F compared against the same threshold, so the two columns have different semantics. The variation sweep (_permissible_root/_permissible_flank, sweep.py lines 293-311) and the report's Pareto coloring (api/report.py line 357: root_safety_wheel >= root_min) repeat the same double-count. peak_root_safety has the same normalized-by-S_Smin semantics under the label 'Statische Sicherheit'.

**Recommendation:** Make the VDI branch return the norm's S_F = sigma_FlimN/sigma_F and S_H = sigma_HlimN*Z_R/sigma_H (no S_min folded in) so all branches share one semantic, and keep the S_min values purely as UI thresholds; adjust sweep and report coloring accordingly.

### NRM-07 [MEDIUM] ISO 6336 material group hardcoded CASE_HARDENED for both gears (incl. the plastic slot); Z_W softer-gear hardness unreachable

*Verification: confirmed.*

Files: `20_code/40_backend/app/api/analysis.py`

analysis.py line 587: material_group=Pair(RootMaterialGroup.CASE_HARDENED, RootMaterialGroup.CASE_HARDENED) is hardcoded in _run_capacity; CapacityRequest has no field for it and the frontend exposes none. The group drives Y_deltarelT (slip layer rho' 0.003 vs 0.0064-0.31), Y_RrelT (eq. 87 vs 88/89) and Y_X, so a user modelling a through-hardened or nitrided steel (by editing sigma_Hlim/sigma_Flim, which IS exposed) silently gets case-hardened factors. Correct for the default 20MnCr5 but wrong for every other steel. Similarly conditions.softer_gear_hardness_hb (Z_W) is never settable from the request, so Z_W is always 1.0 while being printed as an explicit sub-factor.

**Recommendation:** Add a per-gear material-group (and optional softer-gear HB) field to CapacityRequest wired to Iso6336Conditions, defaulting from the catalog material's heat treatment; surface it next to the sigma limits in the capacity tab.

### NRM-08 [MEDIUM] Reduced mass m_red uses default steel density 7800 for BOTH gears - K_v resonance diagnostics wrong for the default steel-plastic pairing

*Verification: confirmed.*

Files: `20_code/40_backend/app/api/analysis.py`, `20_code/40_backend/app/services/capacity/iso6336_dynamics.py`

DynamicConditions.density_kg_m3 defaults to Pair(7800, 7800) (iso6336_dynamics.py line 366) and neither _run_capacity (analysis.py line 550) nor /api/dynamics (line 765) passes densities, although Material carries density_kg_m3 (7850 steel / 1410 plastic) and the elastic moduli ARE taken per material in the same call. For kst-E (plastic wheel, u ~ 1.02) m_red is ~3x too large, n_E1 ~1.7x too low, and the resonance ratio N / regime shown in the Dynamics tab and report shifts accordingly - K_v can land on the wrong branch (the .sta reference N = 1.258 sits right at the resonance boundary). Also the running-in allowances use only the pinion's group and Pair(1500,1500) sigma_Hlim for a plastic wheel.

**Recommendation:** Pass Pair(materials[0].density_kg_m3, materials[1].density_kg_m3) (with fallback) into DynamicConditions wherever native_dynamic_factors is called, mirroring how elastic_modulus is already wired.

### NRM-09 [MEDIUM] ISO 1328-1 eq. (7): profile slope tolerance f_HalphaT missing the 0.001*d term

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/geometry/tolerances.py`

Verified against DIN ISO 1328-1:2018-03 section 5.3.3.1 (rendered page 37): f_HalphaT = (0.4*m_n + 0.001*d + 4)*(sqrt2)^(A-5). tolerances.py line 74 computes f_halpha = (0.4*mn + 4.0)*g - the 0.001*d diameter term is dropped, which also skews the total F_alphaT (eq. 9, line 79). Negligible for kst-E (d ~ 51 mm -> 0.05 um) but grows to 1 um at d = 1000 and 15 um at the range limit d = 15000 - the tolerance tab and report print norm-nonconform values. All other eight equations (5, 6, 8, 10-12, rounding, grade step) match the norm exactly.

**Recommendation:** Change to f_halpha = (0.4*mn + 0.001*d + 4.0)*g and re-pin the affected test values.

### NRM-10 [MEDIUM] /api/report recomputes the dynamics block with raw default deviations and default materials, contradicting the capacity table in the same report

*Verification: confirmed.*

Files: `20_code/40_backend/app/api/report.py`

report() (lines 397-406) calls dynamics(DynamicsRequest(...)) forwarding only base_pitch_deviation_um/profile_form_deviation_um (defaults 6.0/5.0 um) - it ignores req.capacity.accuracy_grade, which the frontend always sets (store default grade 7), and which the capacity() call two lines above uses to derive f_pb/f_fa via dynamics_deviations(). It also leaves DynamicsRequest's pinion_material='steel'/wheel_material='plastic' defaults instead of the capacity request's actual kinds. Result: the report's 'Dynamik' table (c_gamma, n_E1, N, regime) is computed from different deviations and possibly different E-moduli than the K_v printed in the adjacent factors table - two inconsistent K_v chains in one document. Additionally line 409 uses a third width fallback (20.0, 20.0) where analysis.py uses Pair(17.0, 15.0).

**Recommendation:** Forward accuracy_grade (derive f_pb/f_fa the same way _run_capacity does) and the material kinds into the DynamicsRequest, or reuse the DynamicFactors already computed inside capacity() instead of a second divergent call.

### NRM-11 [MEDIUM] kst-E-specific face width fallback Pair(17.0, 15.0) hardcoded on the capacity/dynamics path

*Verification: adjusted.* — *The magic pair exists exactly where cited (analysis.py:519 and 755, design.py:63 and 110, report.py:409 with (20,20)). But the failure scenario is overstated: StageParams always carries widths (gt=0 with visible defaults 17/15, stage_params.py:69-70), so stage.face_width_mm is never None on any API route - the analysis.py/report.py fallbacks are effectively dead defensive code, and a .ste import without BREITE gets 17/15 written into the VISIBLE, editable StageParams fields (design.py:110-124), not invisibly substituted at stress time. Keep as medium under the 'dead code on the analytical path' rubric plus 'kst-E widths as universal defaults', but restate the scenario: the substitution is surfaced in the UI, not silent falsification of sigma_H/sigma_F.*

Files: `20_code/40_backend/app/api/analysis.py`

analysis.py lines 519 (_run_capacity) and 755 (/api/dynamics): width = stage.face_width_mm or Pair(17.0, 15.0) - the kst-E widths silently substitute for ANY stage that carries no width (e.g. a .ste import without BREITE). Stresses scale ~1/b, so a wrong silent default directly falsifies sigma_H/sigma_F. Same magic pair appears in example_kst_e (line 103, harmless there) and design.py lines 63/110; api/report.py uses a different (20, 20).

**Recommendation:** Fail with a 422 ('face width required') on the analytical path instead of substituting example-specific widths; keep cosmetic fallbacks only for display endpoints.

### NRM-12 [MEDIUM] Life factors Z_NT/Y_NT: one scalar for both gears, never derived from load cycles (STplus .sta Blatt 12/13 computes Z_N per gear)

*Verification: confirmed.*

Files: `20_code/40_backend/app/api/analysis.py`, `20_code/40_backend/app/services/capacity/iso6336.py`

CapacityRequest carries single scalars flank_life_factor/root_life_factor (default 1.0) applied to BOTH gears (analysis.py lines 588-589), while the kst-E reference derives per-gear time factors from the load cycles (Blatt 12: Z_N 1.172/1.000 'zeitfest' from N_L 6.118/6.000 Mio; Blatt 13: Y_N per gear). ISO 6336-2/-3 clause 10 gives Z_NT/Y_NT vs N_L tables that could close this: the request even has load_cycles (used only by VDI 2736), so the pinion's finite-life S_H can never reproduce the reference without the user hand-computing Z_NT - and the two gears (whose cycle counts differ by u) cannot get different values at all. Documented in docstrings as 'stays an input' but not listed as a deferred gap in the norm docs; roadmap C2b is marked complete.

**Recommendation:** At minimum make Z_NT/Y_NT per-gear request fields; better, add the ISO 6336-2/-3 clause-10 Method-B interpolation from N_L (per gear, using the material group) with the manual input as override, and document the current limitation in norm_geometry_audit.md.

### NRM-13 [LOW] VDI 2736 tooth-temperature conduction term always zero: heat-transfer coefficients k_theta not exposed

*Verification: confirmed.*

Files: `20_code/40_backend/app/api/analysis.py`, `20_code/40_backend/app/services/capacity/vdi2736.py`

Vdi2736Conditions has flank_heat_coefficient/root_heat_coefficient (VDI 2736 Table 3) but _run_capacity never sets them, and CapacityRequest has no fields - both default 0.0, so the k_theta/(b*z1*(v*m_n)^0.75) conduction term of eq. 9 is permanently dropped and only the housing term heats the tooth. This matches the kst-E FVA reference (validated theta = 107.767 C), but for any other material/housing configuration the tooth temperature - and through it the temperature-dependent strength sigma_FlimN - is silently underestimated with no way to enter the Table 3 values.

**Recommendation:** Expose k_theta,Fla / k_theta,Fuss in CapacityRequest (defaults from VDI 2736 Table 3 per pairing, 0 only when explicitly chosen) and pass them through.

### NRM-14 [LOW] Citation-only references to withdrawn DIN 3960 where DIN ISO 21771 covers the same content

*Verification: confirmed.*

Files: `20_code/40_backend/app/services/geometry/tooth_form.py`, `20_code/40_backend/app/services/geometry/root_fillet.py`, `20_code/40_backend/app/services/model/template_mesher.py`

tooth_form.py lines 226/237 cite 'DIN 3960 section 3.6.6 eq. 3.6.06' / 'section 3.6.7' for the undercut limit x_E,min and the with-undercut iteration mandate; DIN ISO 21771:2014 section 7.7 defines x_Emin (Unterschnittgrenze) and the geometry report already labels the same value 'ISO 21771 section 7.7' - the formulas are equivalent, so this is citation currency only. root_fillet.py line 558 (TrochoidFillet) dual-cites 'DIN 3960 section 3.6.1/A.2.2, ISO 21771 section 7' (acceptable but the DIN part should be marked historical per ADR-011), and template_mesher.py line 208 logs 'DIN 3960 3.6.06' in a user-facing warning. No legacy formula usage found anywhere else in services/geometry or services/capacity - all computation cites current standards.

**Recommendation:** Update the three docstrings/messages to cite DIN ISO 21771 section 7.7 primarily (keeping DIN 3960 as historical cross-check per the norm_geometry_audit convention).

### NRM-15 [LOW] Internal gears (negative z): .ste import crashes with an unhandled 500 and downstream geometry has only half-baked sign support

*Verification: adjusted.* — *Core confirmed: the StageParams(...) construction (design.py:114) sits OUTSIDE the try, StageParams enforces teeth ge=5 (stage_params.py:63-64), GearStage has no z>0 constraint, and shipped internal examples exist (stbsp05.ste ZAEHNEZAHL 24 -24, stbsp04.ste % -51) - an internal .ste that parses raises an uncaught pydantic ValidationError -> 500. Partial sign support also verified (gear.py:239 sign2, 307-311 abs()). One detail is wrong: the try (design.py:106-109) wraps the whole parse_ste -> gear_stage_from_ste -> GearStage.from_ste chain, not 'only parse_ste' - the uncovered statement is precisely the StageParams construction. Severity low stands (ge=5 validators block the other routes).*

Files: `20_code/40_backend/app/api/design.py`, `20_code/40_backend/app/services/geometry/report.py`, `20_code/40_backend/app/services/geometry/tooth_form.py`

import_ste (design.py lines 103-139) wraps only parse_ste in try/except; the subsequent StageParams(...) construction hits the teeth ge=5 validator for an internal-gear .ste (the repo ships internal STplus examples per test_ste.py line 86) and raises an uncaught pydantic ValidationError -> HTTP 500 instead of a clean 422. Beyond the API boundary, GearStage carries partial internal-gear support (sign2 in path_of_contact_mm line 239, abs(z)/abs(d) in check_validity) while compute_geometry_report (_ball_measure 'spur external' eq. 35/36, _auto_span_teeth, d_y = d_a - 2*m_n), ToothProfile and the fillet strategies (pi/z gap frame) are external-only with no z > 0 assertion - if negative z ever reaches them through a new caller, they emit nonsense rather than failing. Currently the ge=5 validators block all API routes, so this is exposure-limited.

**Recommendation:** Move the StageParams construction inside the try (or catch ValidationError -> 422 'internal gears not supported yet'), and add explicit z > 0 guards in compute_geometry_report/ToothProfile so the external-only scope fails loudly if ever bypassed.

### NRM-16 [LOW] Pitch-line velocity computed at the reference circle, not the working pitch circle

*Verification: confirmed.*

Files: `20_code/40_backend/app/api/analysis.py`

analysis.py line 521: v_t = pi * d1(reference) * n1/60000 feeds Iso6336Conditions.pitch_line_velocity_ms (Z_v) and the VDI 2736 temperature. ISO 6336 and the reference use the velocity at the working pitch circle (.sta Blatt 10: 'Nennumfangsgeschwindigkeit am Waelzkr. v 2.696' vs 2.670 m/s here, ~1% for kst-E; grows with |x-sum|). Same for the F_t basis: F_t is taken at the reference circle (matching the sigma_H0 formula's d1 convention, so the stress itself is consistent) but v for Z_v and the thermal model should be the pitch-line value.

**Recommendation:** Use v = pi * d_w1 * n1/60000 (stage.working_pitch_diameter_mm[0]) for Z_v and the VDI temperature; keep F_t at d1 for the stress formulas per ISO 6336 convention.

### NRM-17 [LOW] Quality-standard picker offers withdrawn DIN 3962 (1978) as default while the backend always computes DIN ISO 1328-1:2018 values

*Verification: adjusted.* — *Core confirmed: components.py:912-922 defines the enum (rendered via the Toleranzen editor layout, line 2003), store.tsx:554 defaults 'din_3962_1978', and a repo-wide grep shows quality_standard is stored but consumed by NO computation; tolerances.py implements only DIN ISO 1328-1:2018, and store.tsx:353 even annotates grade 7 as 'DIN 3962 Qualität 7'. One sub-claim is wrong and should be dropped: 'iso_1328_2013' does NOT mismatch the implementation - DIN ISO 1328-1:2018-03 is the German adoption of ISO 1328-1:2013 (identical formulas, verified eq. 5-12 in the repo PDF), so that option's label is consistent; only the DIN 3962 default and the dead selector remain the defect.*

Files: `20_code/40_backend/app/services/uimodel/components.py`, `20_code/50_frontend/src/lib/store.tsx`

components.py lines 912-934 define a 'Verzahnungsqualität' standard enum (din_3962_1978 / iso_1328_2013) and the frontend store defaults quality_standard to 'din_3962_1978' (store.tsx line 554), replicating the FVA dialog. The backend's tolerances.py implements only DIN ISO 1328-1:2018, and the selector has no effect on any computation - so with the default selection the UI advertises the withdrawn DIN 3962 grade semantics (whose Q-grade tolerance tables differ numerically from ISO 1328 classes) for values actually computed per ISO 1328-1:2018; the second option's label '(2013)' also mismatches the implemented 2018 edition. FVA-parity UI replication is a documented decision, but the label/value mismatch is a norm-currency defect.

**Recommendation:** Either implement the DIN 3962 tables behind the selector, or gray it out / relabel to 'DIN ISO 1328-1:2018' and note that grades are interpreted per the current standard regardless of the historical option.


## Dimension E — FEM/deck interface consistency

### FEM-01 [HIGH] Deck/pair endpoints skip the mandatory mating-tip interference check that contour/preview enforce

*Verification: adjusted.* — *Core confirmed at high: mesh.py 755-756, 848-849, 934-935 call req.fillet_gear{1,2}.strategy() directly, bypassing _checked_strategy (270-284), and implicit_deck.py/template_mesher.py only mention the clearance check in docstrings ('run ... first', implicit_deck.py 1012) — no downstream enforcement, so /deck and /deck-series (SchemaTab.tsx 31-49 downloads with no prior preview) yield a physically wrong .inp/ZIP with 422-rejected fillets. One detail is over-broad: the pair-VIEW symptom does not manifest in the shipped UI, because PairPanel's generate() (lines 69-83) runs meshApi.pair inside Promise.all with two meshApi.preview calls using the same fem.fillet_gear{1,2}; the preview's _checked_strategy 422 rejects the whole Promise.all, guard() shows the error and setPair never runs. The /pair ENDPOINT itself is still unguarded (direct API use, future consumers), but the interfering assembly is not reachable through the current PairPanel flow. Keep high severity for deck/deck-series; narrow the pair-view claim to API-level.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/api/mesh.py`, `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/services/model/implicit_deck.py`

api/mesh.py enforces the optimized-fillet interference check via _checked_strategy (lines 270-284, 'mandatory check', 422 on negative clearance) for /contour (line 699) and /preview//3d (line 289). But the three endpoints that build the REAL load case bypass it: build_deck (lines 755-756), build_deck_series (848-849) and pair_assembly (934-935) all call req.fillet_gear{1,2}.strategy() directly and pass the strategy into build_implicit_pair_from_stage / assemble_centered_pair, where no clearance check exists (implicit_deck.py only mentions it in a docstring: 'run the mating-tip clearance check first', line 1012). A fillet parameterization that the Zahnform/Netz tabs reject with 422 (e.g. deep elliptic e_f, wide Landi ra_f) still yields a downloadable .inp / position-series ZIP and a pair-view assembly with the mating tip cutting into the fillet, silently producing a physically wrong FE model (initial penetration mid-roll).

**Recommendation:** Route the deck/series/pair fillet resolution through _checked_strategy (both gears, each against its mating profile) so interference raises the same 422 there; keep the trochoid/standard bypass.

### FEM-02 [MEDIUM] Root-fillet spec (and mesh densities) live in three unsynced stores; Zahnform/Netz tabs can show a different fillet than the deck uses

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/panels/ToothFormPanel.tsx`, `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/panels/MeshPanel.tsx`, `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/lib/store.tsx`, `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/lib/deck.ts`, `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/panels/VariationPanel.tsx`

store.tsx declares fem.fillet_gear1/2 as the SSOT ('drives preview mesh AND deck identically', lines 56-58) and deck.ts (37-38) + PairPanel (234-244) consume it. But ToothFormPanel keeps its FilletSpec in local useState (line 275) and MeshPanel keeps fillet AND refine_root/flank/thickness/layers in local useState (lines 53-57) — none of it synced with fem.*. A user who tunes a Fruehe/CAO fillet in the Zahnform tab (contour, d_f,eff, clearance) or validates mesh quality/convergence in the Netz tab then downloads the deck from the Abwaelzen tab (whose backend ui-schema exposes no fillet rows at all) gets a deck built with whatever fem.fillet_gear1/2 holds — default 'standard' — with no indication of the mismatch. VariationPanel's 'Uebernehmen' (applyVariant, lines 269-290) likewise applies the variant stage but not the compared v.fillet to fem.*. The stage itself IS shared (useStage -> wb.stage = effectiveStage), so this divergence is specific to fillet + density inputs.

**Recommendation:** Bind ToothFormPanel and MeshPanel to fem.fillet_gear{1,2} (per selected gear) and MeshPanel's densities to fem.refine_*, or visibly mark the tab-local settings as exploratory and show the deck-active fillet; copy v.fillet into fem.fillet_gear2 on Uebernehmen.

### FEM-03 [MEDIUM] Deck material card ignores the Werkstoff tab's editable properties and material names — only the steel/plastic kind is transmitted

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/lib/deck.ts`, `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/api/mesh.py`, `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/services/materials.py`, `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/lib/capacityRequest.ts`

The analytical chain sends the store's editable material values (capacityRequest.ts: steel_modulus_mpa, plastic_modulus_mpa, poissons, sigma limits — schema-bound in the Werkstoff tab via materials.steel_*/plastic_* bindings). The deck payload sends only gear{1,2}_material: 'steel'|'plastic' (deck.ts 30-31); the backend _deck_roles (mesh.py 794-800) builds the card from catalog_material(kind) — the fixed catalog defaults 20MnCr5 / Stanyl_TW200F6_cond_80 (materials.py 231-280). Editing E or nu in the Werkstoff tab (or selecting a different catalog name via materials.gear1_name/gear2_name, which is never transmitted) changes ISO 6336 / VDI 2736 results but silently leaves the FE deck on the kst-E cards. Defaults coincide today (210000/0.3, 4156/0.34 with the documented fe_poisson 0.30 Marlow parity), so the divergence only appears after an edit — exactly when it is least expected. Partly a documented decision ('properties from THE material catalog, 2026-07-04'), but the UI exposes editable fields that one consumer honors and the other ignores.

**Recommendation:** Either transmit the material name + overridden elastic constants in DeckRequest and build the card from them (falling back to the catalog curve for Marlow), or lock the property fields to catalog values and make edits create a named catalog entry both consumers read.

### FEM-04 [MEDIUM] FE set/surface classification and refine bands assume the STANDARD d_Ff — wrong band assignment for Landi fillets with raised junction

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/services/model/mesh_sets.py`, `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/services/model/template_mesher.py`, `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/services/geometry/root_fillet.py`

tag_gear_reference, tag_sector_surfaces and build_rigid_shell classify contact/output flank surfaces purely by radius r_ff + tol < r < r_na - tol with r_ff = profile.d_Ff/2 (mesh_sets.py lines 74, 171, 261, 299-307), and template_mesher's refine bands + 'effektive Werte' counts split at r_split = d_Ff/2 + 0.02 (line 307). The junction_radius_mm plumbing (root_fillet.py 597-606) that the stress-evaluation calls already use is never passed here. For a Landi fillet the junction sits ABOVE d_Ff (d_Ff/2 + ra_f*m_n, ra_f up to 1.5), so the elliptical fillet portion between d_Ff and the junction is tagged into the TOOTH-g-tttFf contact surfaces and GgTtttFf_NODESET/_ELEMENTSET measurement sets, refine_flank (not refine_root) splits it, and the FVA-dialog effective element counts misattribute the bands. Fruehe/CAO fillets digging below d_f stay consistent (their extra depth lies below d_Ff and the mesher's radial map follows the actual contour bottom, template_mesher 220-224). fem_results.py line 121 likewise uses the standard d_Ff for the xi_min/xi_max path-of-contact markers regardless of the active fillet.

**Recommendation:** Pass the active strategy's junction_radius_mm into the set taggers (use it as the flank lower bound per gear) and into the refine-band split; derive the fem_results extended-range markers from the same junction radius.

### FEM-05 [MEDIUM] Toleranzen (A_We/A_Wi) edits are silently inert in the default kst-E example mode — for deck backlash AND analytics

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/api/stage_params.py`, `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/lib/store.tsx`

effectiveStage (store.tsx 652-678) merges the Toleranzen tab's A_We/A_Wi into tooth_width_allowance_*_mm on every API payload, and the comment (526-528) promises this 'drives x_E and the deck backlash'. But StageParams.stage() short-circuits to the frozen kst_e_stage() whenever use_example is true (stage_params.py 97-99), ignoring the transmitted allowance fields entirely — and set() clears use_example only for ns === 'stage' edits (store.tsx 830), never for tol.* edits. So in the default example mode a user editing the Abmasse sees the new values in the Toleranzen tab while every consumer — deck closing rotation/backlash, geometry report, capacity — keeps computing with the .ste values (which the defaults -278/-207 um happen to mirror). Deck and analytical chain stay mutually consistent (both ignore), but both silently diverge from what the tab shows until some unrelated stage field is touched.

**Recommendation:** Either apply the transmitted allowances (and modifications) on top of the example stage in StageParams.stage(), or flip use_example to false (with a visible mode indicator) when tol/correction values are edited.

### FEM-06 [LOW] CaoFillet cache fingerprint omits the tip-chamfer (edge_break) parameters

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/services/model/cao_fillet.py`

_fingerprint (cao_fillet.py 46-61) covers m_n, z, alpha, x_E (so allowances are covered), tool factors, d_b, d_Ff, d_Na, rho_F, d_a, C_aa and d_Ca (tip relief covered) — but not profile.edge_break (d_bK, psi_bK), although the chamfer involute shapes the sector contour the CAO FE growth loop meshes (tip_chamfer_points via transverse_right_boundary/to_tip_circle). The risk is largely theoretical: changing the tool edge-break angle or root-form height moves d_Fa = d_Na (generation.py tip_form_diameter_mm bisection), so the key changes indirectly; a stale hit needs a contrived compensating tool change that keeps d_Na and d_a identical while altering only the chamfer curve. All user-facing inputs that change the fillet-relevant contour are covered.

**Recommendation:** Add the edge_break tuple (or a hash of it) to _fingerprint for completeness — it is one line and removes the only contour input not in the key.

### FEM-07 [LOW] Deck mesh ignores the stage's flank-symmetry flag that the preview passes

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/services/model/implicit_deck.py`, `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/api/mesh.py`

/preview and /fillet-sweep pass mirror_symmetric=req.stage.mirror_symmetric(gear) into generate_sector_2d (mesh.py 298, 591), but build_gear_part (implicit_deck.py 243-250) omits the argument, so the deck mesher falls back to profile.is_flank_symmetric(), which is hardcoded True (tooth_form.py 240-250). Today unreachable (effectiveStage always writes both flanks equal), but the moment per-flank asymmetric micro-geometry lands, the preview would drop the in-tooth mirror while the deck silently keeps enforcing it — a latent preview-vs-deck mesh divergence on the exact policy the memory notes call data-driven.

**Recommendation:** Thread the same mirror_symmetric value (from StageParams.mirror_symmetric per gear) through build_gear_part/assemble_centered_pair so deck and preview stay coupled by construction.

### FEM-08 [LOW] Loaddist 'Vernetzung starten' quick check meshes with a hardcoded standard fillet and ignores the thickness factor

*Verification: adjusted.* — *Code claims verified: SchemaTab.tsx 51-75 builds both meshApi.preview calls with fillet: {kind:'standard'} hardcoded and no refine_thickness, with refine_root/flank from the coarse/medium/fine map of wb.loaddist.meshing_accuracy. Adjust the scope though: the refine level coming from loaddist.meshing_accuracy is the Lastverteilung module's OWN accuracy dropdown (FVA-replica semantics) — the user just set it in that very tab, so deriving the level from fem.refine_* as the recommendation suggests would break that module's control; that half is by design, not a defect. The genuine defect is narrower: there is no loaddist-side fillet (or thickness) setting, so the hardcoded standard fillet silently misdescribes mesh quality whenever an optimized fem.fillet_gear{1,2} is active. Keep low, limited to the fillet (and optionally thickness) mismatch.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/components/SchemaTab.tsx`

The loaddist.run_meshing action (SchemaTab.tsx 51-75) reports quad counts and min scaled Jacobian from meshApi.preview calls with fillet: {kind:'standard'} hardcoded and no refine_thickness, regardless of the active fem.fillet_gear1/2 and fem.refine_* the deck will use. When an optimized fillet or a thickness factor is active, the quoted quality numbers describe a mesh that is not the one any deck run will contain.

**Recommendation:** Build the two preview requests from fem.fillet_gear{1,2} and the fem refine values (like PairPanel does) so the quick check describes the deck's actual mesh.

### FEM-09 [LOW] Quick-FE (single tip load) vs deck rolling load case: well documented backend-side; only the sweep UI lacks the 2D-FE marker

*Verification: confirmed.*

Files: `C:/GitHub-tkuhn39/semesterthesis/20_code/40_backend/app/services/model/plane_fe.py`, `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/panels/MeshPanel.tsx`, `C:/GitHub-tkuhn39/semesterthesis/20_code/50_frontend/src/lib/i18n.tsx`

The objective difference is properly documented (plane_fe.py module docstring: 'convergence/ranking instrument, not the load-capacity result'; cao_fillet.py caveat vs Kassem's meshing-cycle objective), and the UI labels the ranking and CAO sections '(2D-FE)' (i18n 93, 530). Quick-FE sigma is nowhere shown side-by-side with deck FEM results as comparable. Remaining gap: the sweep section label 'Fusskurven-Optimierung (Sweep)' (i18n 197) and its table/recommendation (MeshPanel 306-367) show sigma_max [MPa] and 'Empfehlung' without the 2D-FE/single-tip-load qualifier, so the recommended optimum can be over-read as a load-capacity statement.

**Recommendation:** Add '(2D-FE)' to the sweep section title and a one-line footnote that sigma comes from the single static tip load, not the rolling deck load case.


## Dimension F — Completeness-critic additions (single-pass, not adversarially verified)

### GAP-01 [HIGH] Dynamikfaktoren tab and capacity compute different K_v/K_Ha/K_Hb for the same state (grade-vs-raw-deviation and material mismatch)

Files: `20_code/50_frontend/src/panels/DynamicsPanel.tsx`, `20_code/50_frontend/src/lib/capacityRequest.ts`, `20_code/40_backend/app/api/analysis.py`, `20_code/50_frontend/src/lib/store.tsx`

The capacity path always sends accuracy_grade = operating.accuracy_grade (hardwired 7, editable nowhere — no schema row or panel binds it), and _run_capacity (analysis.py:534-541) then derives f_pb/f_fa from the grade (grade 7, m_n=1, d=51 gives ~10.9/11.1 um), ignoring the editable base_pitch/profile_form deviation fields. The DynamicsPanel request (DynamicsPanel.tsx:22-31) has no accuracy-grade path at all and uses the raw store deviations (6.0/5.0 um), and it also omits pinion_material/wheel_material, so /api/dynamics (analysis.py:772-777) always evaluates the catalog kst-E steel/plastic pair regardless of the Werkstoff tab's kinds and modulus edits. Consequences: (a) the K_v/K_Ha/K_Hb stats shown in the Dynamikfaktoren tab contradict the ones in the Tragfaehigkeit tab for identical state; (b) the f_pb/f_fa inputs the Dynamics tab offers never influence any sigma/S result because the non-null grade takes precedence in the capacity path. This is distinct from the covered report-endpoint recompute and Toleranzen-grade-triple findings: it is a live-UI contradiction between two visible tabs.

**Recommendation:** Give DynamicsRequest the same accuracy_grade/material override inputs as CapacityRequest (or build its request via a shared builder), and make the grade-vs-raw-deviation precedence explicit and editable in one place; render a hint when an override is inert.

### GAP-02 [HIGH] Stufenvariation loses swept alpha_n and gear addendum h_aP*: not in VariationPoint, wrong contour overlay, dropped on Uebernehmen

Files: `20_code/40_backend/app/api/analysis.py`, `20_code/50_frontend/src/panels/VariationPanel.tsx`, `20_code/50_frontend/src/lib/api.ts`

alpha_n and h_ap1/h_ap2 are sweepable (VariationRequest rows, kernel uses them via mesh_geometry addendum_factor_pinion/wheel and the per-variant alpha column), but VariationPoint (analysis.py:868-892) carries neither alpha_n nor any addendum info. So: (1) the step-4 table/PC plot cannot show which alpha_n/h_aP a variant has; (2) buildOverlays (VariationPanel.tsx:222-243) rebuilds the variant contour with the BASELINE r.normal_pressure_angle_deg and without the variant's h_ap2 (no gear_addendum_factor/tip override), drawing a different tooth than was evaluated; (3) applyVariant (VariationPanel.tsx:269-290) writes neither normal_pressure_angle_deg nor gear addendum factors into the stage, so after Uebernehmen the model geometry silently differs from the selected variant whenever alpha_n or h_aP was swept (or even just set to a non-stage value in step 1). StageParams can express per-gear tips via tip_diameter_pinion/wheel_mm but only a single gear_addendum_factor, so the pipeline currently cannot round-trip per-gear h_aP at all.

**Recommendation:** Add alpha_n_deg (and h_ap1/h_ap2 or resulting tip diameters) to VariationPoint; use them in the overlay stage and in applyVariant (via normal_pressure_angle_deg + tip_diameter_*_mm); show alpha_n as a results column when varied.

### GAP-03 [MEDIUM] VDI 2736 ambient 'Nutzereingabe' mode pins theta_0 to hardcoded 20 C — the Betriebsdaten ambient field is inert

Files: `20_code/50_frontend/src/lib/store.tsx`, `20_code/40_backend/app/services/uimodel/components.py`

DERIVED 'operating.ambient_temperature_c' (store.tsx:640-641) returns oil temperature in 'equals_oil' mode, else a literal 20.0 — it never reads the editable operatingUi.ambient_temperature_c that the Betriebsdaten tab exposes (components.py:1896-1903). The VDI ambient-mode enum offers 'Nutzereingabe' (components.py:1067-1078), but selecting it ignores whatever the user typed and feeds 20 C into the tooth-temperature/wear/safety chain and the HTML report. The effective value is at least visible in the CapacityPanel load-case card, but it contradicts the Betriebsdaten entry.

**Recommendation:** In 'value' mode return s.operatingUi.ambient_temperature_c from the derived path (and grey/lock the field in equals_oil mode).

### GAP-04 [MEDIUM] Static peak-load 'Nutzereingabe' has no value input: K_A,stat silently hardcoded to 2.0 and never displayed

Files: `20_code/50_frontend/src/lib/capacityRequest.ts`, `20_code/40_backend/app/services/uimodel/components.py`, `20_code/50_frontend/src/lib/store.tsx`

vdi_static_overload (components.py:1194-1206) binds only the MODE enum (operating.static_mode); no schema row or panel binds operating.static_overload_factor (store default null). buildCapacityRequest (capacityRequest.ts:51-52) sends 'op.static_overload_factor ?? 2.0' when the mode is 'value', so enabling the static analysis always runs with an invisible, uneditable K_A,stat = 2.0. sigma_F,P and S_stat then appear in the CapacityPanel and HTML report without the factor they were computed with being shown anywhere.

**Recommendation:** Add a visible_if row for the K_A,stat value (bound to operating.static_overload_factor) and echo the used factor next to the static results.

### GAP-05 [MEDIUM] Tragfaehigkeit tab rows promise couplings that do not exist: roughness_auto never converts Ra->Rz, and C_a is a second disconnected tip-relief state

Files: `20_code/40_backend/app/services/uimodel/components.py`, `20_code/50_frontend/src/lib/store.tsx`, `20_code/50_frontend/src/lib/capacityRequest.ts`

(1) cap_roughness_auto (components.py:769-776) is a checked-by-default checkbox whose info text promises 'R_a <-> R_z Umrechnung (R_z ~ 6*R_a)', but operating.roughness_auto has no consumer anywhere — editing R_aH/R_aF changes nothing, while Z_R/Y_RrelT keep using the stale R_z fields. (2) cap_tip_relief binds operating.tip_relief_ca_um (default 8.0), which no request builder reads; the tip relief that actually reaches the tooth profile/FE contour is correction.tip_relief_um (Flankenmodifikation [34], also 8.0 by default) merged in effectiveStage(). The two values can diverge silently, and the Tragfaehigkeit C_a row (norm_ref 'ISO 6336-1 (K_v, Anregung)') never influences any calculation.

**Recommendation:** Either implement the Ra->Rz write-through and route C_a to the correction store (one tip-relief source), or mark both rows as computed/locked mirrors of the live values.

### GAP-06 [MEDIUM] FEM results upload has no stage-provenance check: dump is unwrapped with the CURRENT stage, and the dump's mode is never shown

Files: `20_code/40_backend/app/api/fem_results.py`, `20_code/50_frontend/src/panels/FemResultsPanel.tsx`

/api/fem/results (fem_results.py:93-133) computes xi(r), the A-E markers and the extended d_Nf-d_Na range from the ACTIVE StageParams; the fem_results.json schema carries no stage fingerprint and neither the deck download nor the postprocessing script embeds one, so nothing detects that the dump was produced for a different geometry. If the user edits the stage, imports an .ste or applies a variant between deck export and result upload, the viewer silently overlays foreign stresses on wrong path-of-contact coordinates/markers. Additionally FemResultsResponse.mode (quick-FE single tip load vs rolling series) is returned but never rendered, so the viewer cannot tell which load case it is looking at — the backend-side distinction auditor E noted as well documented is invisible here too.

**Recommendation:** Embed a stage hash (or the StageParams themselves) in the deck bundle/dump, verify it on upload with a clear warning, and show res.mode in the panel header.

### GAP-07 [MEDIUM] Uebersicht tab is permanently the static kst-E example — contradicts the active stage and Werkstoff selection after any edit

Files: `20_code/50_frontend/src/panels/OverviewPanel.tsx`, `20_code/40_backend/app/api/analysis.py`

OverviewPanel fetches GET /api/example/kst-e once and renders it regardless of the workbench state: after leaving example mode (free edit, .ste import, variant Uebernehmen) or switching the Werkstoff kinds, the top-level 'Uebersicht' still shows kst-E's a/m_n/eps, the kst-E gear table and the CATALOG material names (roles 'Ritzel (Stahl)'/'Rad (Kunststoff)' are also backend-hardcoded German), while the tree badges and every other tab follow the store. A user reading the Overview as a model summary gets stale, contradictory values. (Auditor A's Overview finding covers missing ExampleResponse fields, not this staleness.)

**Recommendation:** Drive the Overview from the live store/geometry (or clearly label it as the immutable kst-E reference example and show the active stage beside it).

### GAP-08 [MEDIUM] Glossary misses most displayed result symbols: whole flank chain, new ISO 6336-2/-3 sub-factors, VDI outputs, dynamics and inspection quantities

Files: `20_code/50_frontend/src/lib/glossary.ts`, `20_code/50_frontend/src/panels/GlossaryPanel.tsx`

The Glossar tab is pitched as 'explaining every symbol', but glossary.ts contains no entry for the entire flank-capacity chain (sigma_H, S_H, sigma_HP, Z_E, Z_H, Z_eps, Z_B/Z_D), none of the e1e7e21 sub-factors now rendered in the CapacityPanel and HTML report (Z_L, Z_v, Z_R, Z_W, Z_X, Z_NT, Y_drelT, Y_RrelT, Y_X, Y_NT), no K_Halpha/K_Hbeta (only K_Fbeta), none of the VDI 2736 outputs (theta_Z, theta_Fla, W_m, W_zul, lambda, H_V), none of the dynamics quantities (c_gamma_alpha, m_red, n_E1, N/regime), and none of the ADR-024 inspection/geometry-report symbols (W_k, M_dK, s_cn, h_c, K_ga, zeta_a/zeta_f, x_E, E_sns/E_sni, d_Nf usable root, c_n form reserve). Auditor C flagged only the fillet parameters.

**Recommendation:** Extend GLOSSARY to cover every symbol rendered by CapacityPanel, DynamicsPanel, the Geometrie report sections and the HTML report (the row lists in GeometryPanel.tsx and i18n gr./cap. keys are a ready checklist).

### GAP-09 [LOW] DesignPanel ISO 1328 quick check computes wheel-only at the spur reference diameter (m_n*z, no /cos beta)

Files: `20_code/50_frontend/src/panels/DesignPanel.tsx`

runTolerances (DesignPanel.tsx:84-103) requests tolerances only for the wheel (teeth_wheel, face_width_wheel_mm) with reference_diameter_mm = normal_module_mm * teeth_wheel — for a helical draft the correct d = m_n*z/cos(beta), so the diameter-dependent terms (f_pt, F_p, f_Hbeta, f_fbeta) are underestimated, and the ISO 1328 validity warnings are checked against the wrong d. The table is also labeled generically, not as wheel-only. (The panel-local grade state itself is covered by the accuracy-triple-state finding.)

**Recommendation:** Use m_n*z/cos(beta) (or the backend stage's reference_diameter_mm), compute both gears, and label the columns.

### GAP-10 [LOW] Additional response fields never consumed: kind_surface, convergence relative_change/reference_sigma, pair closing/roll metadata, per-flank maxima

Files: `20_code/50_frontend/src/lib/api.ts`, `20_code/50_frontend/src/panels/MeshPanel.tsx`, `20_code/50_frontend/src/components/PairViewport.tsx`, `20_code/50_frontend/src/panels/FemResultsPanel.tsx`

Beyond auditor A's unconsumed-field list: MeshPreviewResponse.kind_surface (surface-kind classification for the 2D view) is used nowhere; ConvergenceResponse.relative_change, reference_sigma_mpa and target are dropped (MeshPanel shows only sigma list + converged level, so the user never sees the convergence criterion values); Mesh3DResponse.face_width_mm is unused; PairAssemblyResponse.closing_rad, roll_angle_rad and contact_pairs are never surfaced (the closing rotation / contact-pair names would be useful deck diagnostics); FlankFrameData.max_mises/max_cpress are served but the FemResultsPanel recomputes frame maxima client-side from the raw arrays.

**Recommendation:** Either render these (convergence relative-change column, closing rotation in the PairPanel stats) or remove them from the response models.

### GAP-11 [LOW] Measuring-element diameter inputs (D_M) unreachable: two-ball/roller measures always use the default 1.75*m_n

Files: `20_code/50_frontend/src/lib/api.ts`, `20_code/50_frontend/src/panels/GeometryPanel.tsx`, `20_code/40_backend/app/api/analysis.py`

GeometryReportRequest.ball_diameter_gear1_mm/gear2_mm exist end-to-end in the backend (analysis.py:196-197, 286-290) but no UI ever passes them — GeometryPanel sends only stage+fillets and the Din3967Section only series — so M_dK/M_dR/E_Mds/E_Mdi are always computed for the default 1.75*m_n ball and a drawing's specified measuring-pin size cannot be reproduced. (Sibling of the covered unreachable DIN 3964 A_a, which shares the same request model.)

**Recommendation:** Add D_M per gear to the Toleranzen tab (or the DIN 3967 section) and pass it through to /api/geometry/report and the HTML report.

### GAP-12 [LOW] Meldungen strip is static decoration: warnings never reach it

Files: `20_code/50_frontend/src/components/Workbench.tsx`

The footer (Workbench.tsx:446-449) always renders t('msg.ready') ('Bereit.'). Geometry validity notes, ISO 1328 validity warnings, variation warnings and fetch errors appear only inside their respective panels (and are lost when the tab is not open); backend-offline shows only in the header. An FVA-style messages strip that permanently says 'ready' actively suggests there are no messages even when the active stage carries warnings (e.g. eps_gamma < 1).

**Recommendation:** Route panel warnings/errors (at least geometry notes and the last request error) into a small store-backed message list rendered by the strip.

### GAP-13 [LOW] Untranslated backend result strings: dynamics regime shown raw English in the German UI and German HTML report

Files: `20_code/40_backend/app/api/analysis.py`, `20_code/50_frontend/src/panels/DynamicsPanel.tsx`, `20_code/40_backend/app/api/report.py`

DynamicsResponse.regime is a hardcoded English string ('sub-critical' / 'main resonance' / 'super-critical', analysis.py:779-783) rendered verbatim in the DynamicsPanel 'Bereich' row and in the German HTML report's dynamics table (report.py:766). Distinct from auditor B's number/unit locale finding, this is a semantic result value with no i18n key or locale-aware rendering. GearCapacity.label ('Ritzel (Stahl)') is the mirror case, German-only, though currently unconsumed.

**Recommendation:** Return an enum token and translate it in the frontend/report renderer.

### GAP-14 [LOW] PairPanel header shows the reference centre distance instead of the working a in 'from x' mode

Files: `20_code/50_frontend/src/panels/PairPanel.tsx`

PairPanel.tsx:42 computes 'centerDistance = stage.center_distance_mm ?? m_n*(z1+z2)/2'. In the Geometrie tab's 'aus den Profilverschiebungen berechnen' mode, effectiveStage() sets center_distance_mm = null, so the FE-Abwaelzmodell header displays the REFERENCE centre distance while the assembly the backend builds (and every other tab) uses the working a from inv(alpha_wt)(sum x) — a visibly wrong label for shifted pairs (also dot-decimal toFixed, covered elsewhere).

**Recommendation:** Show pair.center_distance_mm from the last /api/mesh/pair response (or fetch the geometry a_w) instead of the raw stage field.


## Confirmed INTENDED duplications (by design — keep)

- **[COV] QuickView recomputes d_w, u and b_gem client-side instead of reading the backend SSOT fields** — QuickView is BY DESIGN a persistent duplicate of key geometry values (so the duplication itself is intended), but it derives d_w = 2a*z_i/(z1+z2), u = z2/z1 and b_gem = min(b1,b2) locally from stage inputs plus the light /api/geometry response, while the backend SSOT already serializes GearReport.working_pitch_diameter_mm, PairReport.gear_ratio and PairReport.common_face_width_mm (ADR-024). The fo

- **[STR] QuickView mirrors the Geometrie tab's Hauptgeometrie/Durchmesser tables (intended persistent summary)** — The right-hand Ergebnis-Schnellansicht shows alpha_n, m_n, z, u, a, x, b, eps values and the diameter table that also appear in the Geometrie tab and its report sections. This display duplication is BY DESIGN (FVA right panel, persistent across nodes) — recorded here so it is not mistaken for accidental duplication. Only its client-side recomputation and duplicate fetch are defects (reported separ

- **[STR] DynamicsPanel repeats K_v/K_Halpha/K_Hbeta shown in CapacityPanel (intended diagnostics extra)** — The bespoke Dynamikfaktoren tab fetches /api/dynamics and shows K_v/K_Halpha/K_Hbeta that CapacityPanel's factors block also displays (from /api/capacity). Both are backend-computed from the same kernel and the tab adds resonance diagnostics (c_gamma, m_red, n_E1, N, regime) not available elsewhere — a kept 'extra' per the Workbench design comment. Same-values-in-two-tabs is intended; the two endp

- **[STR] PairPanel and the Dyn-Abwälzen schema tab both edit fem.* and both offer the deck download (intended phase-F SSOT sharing)** — The transient_fem schema tab and PairPanel edit the SAME fem.* store fields and both build their deck request through the shared deckPayload() (byte-identical decks by design, phase F); the duplicated download button (SchemaTab useActions 'fem.download_deck' vs PairPanel downloadDeck) shares label, filename and payload logic. Recorded as intended so the duplicated download code path is not flagged

- **[FIL] Four independent fillet configurations by design; no path to carry a found optimum into the deck** — FilletEditor is mounted with four separate states: ToothFormPanel local, MeshPanel local, PairPanel bound to store fem.fillet_gear1/2 (the deck/geometry-report SSOT), VariationPanel bound to varUi.fillet. The exploration-vs-deck split looks intentional (exploratory tabs must not mutate the deck), hence intended_duplicate. The gap: after the sweep recommends best_value in MeshPanel or the user tune

