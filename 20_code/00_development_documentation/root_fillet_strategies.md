# Root-fillet strategy design basis (literature synthesis)

> **Status 2026-08-05 — ALL SEVEN literature approaches implemented** (ADR-023), selected via
> `FilletSpec(kind, approach)`: elliptic → kassem | fruehe | landi, bezier → roth | dong,
> bionic → voith | cao. Each was verified against its primary source before coding
> (pdftotext/pdftoppm — the Read tool falsely reports the Nautos PDFs as password-protected).
> Quick-FE ranking on the kst-E wheel (native 2D plane-strain, 100 N tip load, identical mesh
> topology/gates, standard ρ_F arc = 274.9 MPa = 100 %):
>
> | approach | class | result | note |
> |---|---|---|---|
> | elliptic-kassem (e_f=−0.2) | `EllipticFillet` | 90.1 % | AGMA 22FTM13 axis-aligned |
> | elliptic-fruehe (γ=30°, a/b=3) | `FruheEllipticFillet` | **79.1 %** | closed form Eqs. 89–100; root diameter is a RESULT (kst-E: −0.35·m_n) |
> | elliptic-landi (ra_f=0.3) | `LandiEllipticFillet` | 79.5 % | benefit needs the raised D1 (paper default = limit contact diameter); D1=d_Ff gives only 98.6 % |
> | bezier-roth (Be=0.57) | `BezierFillet` | **77.9 %** | |
> | bezier-dong (dv1=1.0) | `DongToolBezierFillet` | 81.0 % | true hobbing envelope (`rack_tip_envelope`); paper's v1=0.35 endpoint constraint is wrong for the kst-E ρ*=0.2 tool (112 %!) → our default ends on the gap centreline |
> | bionic-voith (auto γ, b_f=0.35) | `BionicFillet` | 96.9 % | tuning swept γ×b_f (15–55° × 0.15–0.55): best 97.0 % — the closed tension-triangle form is inherently limited on this geometry/objective, defaults kept |
> | bionic-cao (12 it., tol 0.02) | `CaoFillet` | ≈ 85.9 % | Kassem 2023 growth loop, converges in 5 iterations (σ 274.9→236.2), junction node fixed, in-process cache |
>
> Junction plumbing: strategies may leave the involute above d_Ff (Landi ra_f, Dong) — the
> flank continues from `junction_radius_mm(strategy, profile)`; `junction_offset_mm` implements
> the literature's 0.03–0.05 mm interference fallback. Frühe/Landi(d2_frac=1)/Kassem/Roth reach
> the gap centreline; Dong/CAO keep a root land (with_root_land completes the plot).

Working document for the `RootFilletStrategy` implementation (plan v2, workstream C).
Sources: papers in `00_literatur/03_paper/` (Kassem 2023 + AGMA 22FTM13, OSU elliptical/asymmetric
thesis, Landi 2021, Dong 2020, Roth/Opferkuch 2017 Voith, Frühe FZG thesis). Extracted by the
literature-review agent on 2026-07-03; full per-paper details in the session log.

## Strategy parametrizations (implementable)

### `elliptic`
- **Axis-aligned symmetric ellipse (Kassem AGMA, easiest):** free params `e_f` (root-diameter
  factor, `d_f,e = d_f + m_n·e_f`, range ≈ −0.4…0) and `h*_fP` (dedendum factor). Solve semi-axes
  `a_e, b_e` from G1 conditions (position + slope) at the root-form point `P_dFf` (2×2 fsolve).
  Curve `y(x) = b_e + d_f,e/2 − b_e·√(1−(x/a_e)²)`.
- **Tilted ellipse (Frühe, more capable):** free params tilt `γ` (0–45°, optimum ≈30°) and aspect
  ratio `a/b` (0.5–4, optimum ≈3.0); tangent-continuous at `P_Ff` and `P_f`; `d_f` falls out of
  the fit. Superellipse power `j` adds <0.5% — keep `j=2`.
- **Double-tangent ellipse (Landi/OSU):** free params `R_A` (fillet–involute tangent radius,
  must stay below the limit-contact/SAP diameter) and `R_r` (root radius); G0+G1 at both ends;
  full circle is a special case. Fully-rounded root = degenerate case with only `h*_fP` free —
  literature says avoid for plastics (worst wear notch).

### `bezier`
- **Direct cubic Bézier (Roth/Voith, recommended):** `P0, P3` on transition diameter `d_ü ≈ d_Ff`,
  `P1, P2` on the involute tangents (G1 to flank). **One symmetric parameter `Be`**: distance of
  `P1/P2` from the tangent intersection = `Be ×` cathetus of the deepest tension triangle.
  Range 0.46–0.81, optimum ≈0.57; any `Be` ≥ classic baseline. Asymmetric teeth: two factors
  `Be_bel`/`Be_unb` per flank (fits the per-flank data model / `is_flank_symmetric` policy).
- (Alt, cut gears only) Dong 2020: 5-point Bézier on the **hob tip**, G2 blend, needs a hobbing
  envelope generator — matches the `tool_trochoid` route, not the molded free-form route.

### `bionic`
- **Tension-triangle tangent+arc (Voith 2009 / Kassem closed form):** free params wedge angle
  `γ_b` and centre-arc radius `r_b`. Guidance: `γ_b,opt = π/4 − π/z − α_t` (±20%, always <65°,
  practical optima 30–40°; fiber-reinforced → ≈30°); `r_b = b_f·S_L`, `b_f ∈ [0.1, 0.6]`,
  best 0.3–0.4 (reinforced: ≈0.1).
- **CAO free-form growth (Kassem 2023, later/stretch):** node growth `d_i = s·(σ_i−σ_ref)·n_i`,
  cap `d_per = 0.025·m_n`, junction node at `d_Ff` fixed, iterate FE↔remesh until surface stress
  uniform (≤0.2% deviation, 8–24 iterations). Our native 2D Q4 solver enables a simple version.

## Cross-cutting rules
- Attachment: **G1 at `d_Ff` minimum** (Bézier can do G2); the active involute flank is never
  altered.
- **Mandatory interference check** against the mating-gear tip trochoid — for plastics ideally
  under load over the whole mesh cycle; molded gears: no undercut. Fallbacks: nudge the start
  point 0.03–0.05 mm radially inward, or raise `h*_fP`.
- Manufacturing switch: molded/WEDM → free curve allowed; cut/hobbed → hob-envelope-reachable
  only (tool trochoid route, DIN 3972 profiles / protuberance) + warning in the UI.
- Evaluation: max surface stress **along the whole fillet** (max principal or local tangential
  bending stress — the choice shifts the optimum; document which), load at HPSTC (ISO 6336-3
  Method B) for steel, **full loaded mesh cycle** for plastics. Norm factors Y_F/Y_S only valid
  for the standard fillet → FE is the criterion for optimized shapes.
- Expected gains (sanity targets): elliptic 10–24% σ reduction, Bézier/bionic +20–30% root
  safety, CAO 17–24% vs max-rounded trochoid. **Wear caveat (plastics):** after wear the shape
  advantage shrinks (all forms converge except fully-rounded, which stays worst) — factor wear
  into plastic-gear objectives.
- Short-fiber specifics (Kassem): orthotropic Hill plasticity, fiber-following local frames,
  `R22=R33≈0.66`; the optimal fillet differs for reinforced vs unreinforced material and is
  friction-sensitive.
