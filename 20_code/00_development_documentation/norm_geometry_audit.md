# Norm audit: tool profile & root geometry (DIN 3960 / DIN 867 / DIN 3972)

Working document from the norm-extraction agent (2026-07-03). Feeds the parametric tool-profile
UI, the `tool_trochoid` fillet strategy, and validation warnings. Citations = (norm, clause, page).

## Key findings vs. the current implementation

1. **DIN 3960 has no closed-form trochoid.** The fillet is defined kinematically (tool tip
   rounding sweeps the root, §3.6.1/A.2.2); closed forms exist only for the root FORM circle
   d_Ff without undercut (eqs 3.6.08–3.6.10) — with undercut/protuberance the norm mandates
   iteration (refs Talke/Petri/Weck-Neupert). → Our `generation.py` d_Ff formula matches the
   3.6.08/3.6.10 family (rack tool, x_E, tip form height h_FaP0 = h_aP0 − ρ_aP0·(1−sin α_P0)) ✓.
   The exact `tool_trochoid` strategy implements the generation kinematics (as
   `tooth_form.root_fillet_points` already sketches) — norm-conform, validated numerically.
2. **x_E chain confirmed** (§3.6.3 eq 3.6.03): `x_E·m_n = x·m_n + A_s/(2·tan α_n) + q/sin α_n`;
   as-cut values follow by substituting x_E for x everywhere (§3.5.8). Our implementation uses
   exactly this with q=0 ✓. Open: pre-cut branches (q>0, x_Ev/x_Ew) if ever needed.
3. **Undercut warning missing** (§3.6.6 eq 3.6.06): `x_E,min = h*_FaP0 − z·sin²α_t/(2·cos β)`.
   → implement as a geometry validation warning (undercut changes d_Ff → iteration required,
   and undercut roots invalidate the no-undercut d_Ff closed form we use).
4. **DIN 867 basic rack** (defaults for the parametric tool UI): α_P=20°, h*_aP=1,
   h*_fP=1+c*_P (typ. 1.25), c*_P=0.1…0.4 (generally 0.25), ρ*_fP bounded by eq (7)
   `ρ_fP ≤ c_P/(1−sin α_P)`; ISO 53 point A default: c*_P=0.25, **ρ*_fP=0.38** (matches our
   test default 0.38 ✓). Max-ρ table: c*_P 0.17/0.25/0.3/0.4 → ρ*_fP,max 0.25/0.38/0.45/0.39.
   h_FfP = h_fP − ρ_fP·(1−sin α_P) (eq 9). Note: gear fillet curvature ≥ ρ_aP0 (ρ is a minimum,
   not the fillet radius itself).
5. **DIN 3972 tool profiles I–IV** (presets for the tool dropdown):
   I finishing h_k=1.167·m; II finishing h_k=1.25·m; III pre-cut h_k=1.25·m+0.25·∛m
   (allowance p=0.25·∛m·sin α_0); IV pre-cut h_k=1.25·m+0.6·∛m (p=0.6·∛m·sin α_0).
   Tool tip rounding r ≈ 0.2·m. **Protuberance is NOT in DIN 3972** (explicitly
   "Sonderausführung") — its parameters live in **DIN 3960 Anhang A.2.2**: pr_P0 (amount),
   α_prP0 (protuberance flank angle < α_P0), h_prP0 (height), FS (residual root relief,
   requires pr_P0 > q). → protuberance = later tool-side fillet variant with these names.
6. **Symmetry is norm-backed**: DIN 867 §4.2 — "Die beiden Flanken eines Zahnes sind
   spiegelbildlich zur Zahnmittellinie". DIN 3960 defines left/right flanks (§3.1.3) but builds
   all transverse tooth-thickness math symmetrically; asymmetry is admitted **only via helix**
   (β_R ≠ β_L, §3.5.1), not the transverse profile. → `is_flank_symmetric` default true for
   norm-standard gears; per-flank asymmetry stays an extension point (non-standard racks /
   micro-geometry per ISO 21771 §6).

## Citation index
- Fillet generation: DIN 3960 §3.6.1 (S.13–14), §A.2.2 (S.52), iteration refs (S.55)
- d_Fa/d_Ff: DIN 3960 §3.6.7 eqs 3.6.07–3.6.14 (S.16); d_fE eqs 3.6.04/05 (S.14)
- x_E ↔ A_s: eq 3.6.03 (S.14); substitute-x_E rule §3.5.8 (S.13); allowances §5.1/5.2 (S.39–40)
- Undercut: §3.6.6 eq 3.6.06 (S.14); practical limits §3.7.1–3.7.3 (S.17–19)
- Basic rack: DIN 867 §§3–4 eqs (1)–(9) (S.1–3); symmetry §4.2/§4.5
- Tool profiles: DIN 3972 table (S.1) + Erläuterungen (S.2); protuberance → DIN 3960 Anhang A
