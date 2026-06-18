# RIKOR (FVA 30) load distribution — method notes

Source analysis of the FVA 30 method for the native reimplementation in
`app.services.loaddist`. Read thoroughly from the FVA reports and the RIKOR
reference outputs; this captures *what RIKOR computes* and how the native model
relates. Page references are to **`00_literatur/07_themis/BUS_30_XI_AB_1586.pdf`**
(FVA 30 XI final report) unless noted; the **`Benutzeranleitung.pdf`** (268 p.,
in `35_Rikor/.../doc/manual`) is the input/output reference.

## What RIKOR does (purpose)
RIKOR ("Ritzelkorrektur") computes the **load distribution over the tooth face**
of a gear mesh inside the real shaft–bearing system, and from it the face load
factor **K_Hβ** and the **flank-line correction** ("Ritzelkorrektur") that makes the
load uniform. It is the lab's source for the initial mesh misalignment **F_βx** that
ISO 6336-1 needs for K_Hβ (Method C).

## Computational chain (FVA 30 XI §2.12)
1. **Nominal mesh forces & stiffness** (R1, exact in the native code). Design load
   = K_A·T_nom. F_bt = 2000·T/d_b1 at the base circle; F_bn = F_bt/cos β_b;
   F_bx = F_bt·tan β_b; mean line load F_bt/b over the common face width. Mesh line
   stiffness c_γ from ISO 6336-1 (c′_th, C_B, C_M, c_γα). *(test 001: F_bt/b 1319.34,
   c_γ 16.70 — exact.)*

2. **Shaft–bearing deformation → flank gap δ^{VZ}** (§2.12.2, eq. 2.12.1–2.12.2).
   The gap (Klaffung) along the contact line is the **superposition** of several
   deformation contributions, added because the flexibilities act in series:
   - shaft **bending** of pinion and gear, in **two transverse planes** v and w
     (the line-of-action plane and perpendicular) — `(δ^{VZ})_v`, `(δ^{VZ})_w`;
   - **torsional wind-up** of both shafts (the loaded teeth lag as the torque is
     reacted across the face);
   - **gear-body deformation** `δ^{VV}` (the blank/rim flexibility);
   - **bearing** radial/axial deflections and tilt (and, for plain bearings, the
     hydrodynamic operating eccentricity, §2.10.3).
   Shafts are stepped **Timoshenko beams** (shear from the transverse force is
   explicitly included — the reference bending line is headed "Verformung aus
   Schubspannung aufgrund Querkraft berücksichtigt"). In the **toothed region**
   the shaft is replaced by **equivalent diameters**: `d_Q` for bending and `d_T`
   for torsion (FVA 30 XI §1.5.5; for test 001: d_Q 116.68/481.52, d_T 102.37/469.45
   mm — d_Q > the shaft body, d_T < it).

3. **Load distribution** (§2.12.4, eq. 2.12.7–2.12.13). The mesh is discretised into
   **n point springs** over the contact line(s) (face width × contact positions),
   each with the mesh stiffness c′. The spring forces F′ = [F′_1…F′_n] satisfy
   Σ F′_i = F_bn (eq. 2.12.7) and, at every support point, deformation + correction =
   common approach (eq. 2.12.9). Contact-loss points (negative force) are removed and
   the system re-solved. RIKOR couples this with the bearing/shaft deformation and
   **iterates** (the run log shows "Verzahnungs/Lager-Iteration nach N Durchläufen
   beendet"): the load changes the bearing reactions, which change the gap. Solved
   with the Schmidt / Pinkepank / Wunder / Neubauer scheme (§2.12.4).

4. **Results.** The converged line load w(b) → **K_Hβ = w_max/w̄** and K_Fβ; the
   "Gesamtkorrektur" g(b) = the gap for *uniform* load (the correction for an even
   distribution). The bending lines, bearing loads and equivalent diameters are all
   printed in the `.ria`.

## How the native model relates (R2)
`shaft.py` implements the dominant terms of step 2 natively: stepped **Timoshenko**
beams (`beam.py`, validated exactly vs closed-form deflection) for both shafts'
**bending+shear**, plus the **torsional wind-up**, superposed in the line of action.
This reproduces RIKOR test 001's Gesamtkorrektur **in shape and magnitude (peak ≈ 44
vs 41.8 µm, ~6 %)**: bending sets the magnitude (validated against RIKOR's own
bending line, ~21 µm sag), torsion the asymmetry, shear the peak.

**Why it is not yet bit-exact.** RIKOR's gap is a richer multi-component model than
the native R2: it adds the **gear-body deformation δ^{VV}**, the **two-plane (v,w)**
decomposition with the bearing friction coupling, the **coupled load–deformation
iteration**, and the exact **equivalent-diameter** treatment (d_Q/d_T) in the toothed
region. Replicating these bit-exactly is effectively re-implementing all of RIKOR.
The derivation of the equivalent-diameter and iteration formulas is **not** in the
available PDFs (they are input/output references + feature lists), so the native
model captures the engineering essence at ~6 % rather than to the last digit.

## Oracle (rikor.exe)
For exact values the original `rikor.exe` runs locally (Windows): place an example's
`rikor.cfg` as `bin/rikor.cfg`, run from `bin/` (it reads `rikor.cfg` from the CWD and
needs its runtime helper files there), output goes to the cfg's `AUSGABEDATEI`. Verified
to reproduce the bundled reference `.ria` (test 001: F_bt/b 1319.34, K_Hβ 1.36). Kept as
an optional, non-default oracle for exact F_βx / K_Hβ and for generating validation
cases — the native path stays the cross-platform default (ADR: native runners ship in
Docker; the `.exe` is Windows-only).

## Validation targets (test 001, single helical stage)
F_bt/b 1319.34 N/mm · c_γ 16.70 · K_Hβ 1.36 · K_Fβ 1.30 · Gesamtkorrektur peak
41.82 µm (vertex 77.76 mm) · w(b) 1799.82 → 1147 N/mm. Equivalent diameters
d_Q 116.68/481.52, d_T 102.37/469.45 mm.
