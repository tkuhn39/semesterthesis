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
the native R2 — and, on a thorough page-by-page read of §2.12, it is **fully
documented** (an earlier note here wrongly said otherwise). See *The complete method*
below: the gap/load distribution is an **influence-number compliance matrix**
δ = δ^W + δ^Z + δ^H solved against the misalignment, with each block a classic,
citable method. The native R2 implements only the shaft block δ^W (+ a derived
torsion); bit-exactness needs the tooth/gear-body block δ^Z (Weber–Banaschek / Schmidt)
and the Hertzian block δ^H — i.e. a full **loaded tooth contact analysis (LTCA)**.

## Oracle decomposition of the gap (test 001)
Running the oracle twice — drive torque at the input end vs. moved to the far end —
flips the torsion asymmetry and cleanly separates the Gesamtkorrektur into
`sym = (A+B)/2` (the direction-independent **bending** part) and `asym = (A−B)/2`
(the **torsion** part):
- **Bending (sym): a parabola, ptp ≈ 32 µm** (vertex near the face centre). The
  native Timoshenko shaft model gives only ~22 µm — the missing ~45 % is the
  **tooth/gear-body compliance δ^Z** (Weber–Banaschek tooth + Schmidt plate-strip
  gear-body cross-influence; see *The complete method*).
- **Torsion (asym): essentially LINEAR, ptp ≈ 35 µm** (a tilt across the face). The
  native quadratic `r_b·φ` wind-up had the wrong shape; the correct linear law (below)
  reproduces it.

So a bit-exact native rebuild needs the right structure for each part.

### Torsion — derived and matched
The linear torsion part *is* reproducible from first principles. The lead deviation
over the face is the shaft wind-up across the reacted gear width:

> **f_tors(b) = r_b · (T/2) / (G·J_T) · (b − b_mid)**,  J_T = π/32 · d_T⁴

with the **average** transmitted torque T/2 (linear reaction over the face) and the
**equivalent torsion diameter** `d_T`. For test 001 this gives 34.9 µm ptp vs the
oracle's 35.0 — exact. And d_T itself follows a simple rule:

> **d_T ≈ d − m_n · h_aP0*** (reference diameter minus the tool addendum)

— pinion 102.34 vs RIKOR 102.37, wheel 469.07 vs 469.45. (Bending uses ≈ the
reference diameter d_Q ≈ d.)

### Bending — shaft part validated, tooth/gear-body block to add
The native Timoshenko shaft bending matches RIKOR's printed bending line (~21 µm under
the actual load) and gives ~24 µm under uniform load; the oracle's bending part is
~32 µm. The missing ~33 % is the **tooth/gear-body compliance δ^Z**, which is the
Weber–Banaschek + Schmidt influence-number block — documented, not a free factor.

## The complete method (FVA 30 XI §2.12.5–2.12.7) — the path to bit-exact
The load distribution is a **loaded tooth contact analysis** on the discretised
contact line(s). For n support points, the spring forces F = [F_1…F_n] satisfy the
elastic compatibility δ·F = w_common − f_app and Σ F_i = F_bn (eq. 2.12.7–2.12.13;
contact-loss points are dropped and the system re-solved). The **total compliance
matrix** is the sum of three blocks (eq. 2.12.16):

> **δ = δ^W + δ^Z + δ^H**

- **δ^W — shaft/bearing** (a *full* matrix): the deflection at point i from a unit
  load at j, from both shafts on their elastic bearings, **including torsion**. The
  native `beam.py` system produces this (apply unit loads at each support → columns of
  δ^W); the off-diagonals are the bending cross-coupling along the face. Equivalent
  diameters d_Q (bending ≈ d) and d_T (torsion ≈ d − m_n·h_aP0*) apply in the toothed
  span; the torsion follows the derived linear law above.
- **δ^Z — tooth + gear-body** (diagonal + off-diagonal): the tooth bending/shear/
  compression on the diagonal (Weber–Banaschek [75], DIN 3990 [32]) and the
  **gear-body cross-influence** off-diagonal — a loaded tooth elastically twists and
  transversely deforms the rim, deflecting neighbouring teeth (Schmidt plate-strip
  influence numbers [6], Fig. 2.12.7). This is the ~33 % the native shaft model omits.
- **δ^H — Hertzian flattening** (diagonal only): the local contact flattening; a load
  at i only deforms its immediate neighbourhood (Fig. 2.12.8), so δ^H is diagonal.

The misalignment f_app (shaft tilt + manufacturing flank deviations F_Hβ/F_Hα) enters
the right-hand side; the whole system is iterated with the bearing operating points
("Verzahnungs/Lager-Iteration"). K_Hβ = w_max/w̄.

### Status & path
Torsion: **derived** (linear law, exact vs oracle). Shaft compliance δ^W: have it
(beam system). Missing for bit-exact: assemble δ^W as a **matrix** (unit-load columns),
add **δ^Z** (Weber–Banaschek tooth + Schmidt gear-body influence numbers) and **δ^H**
(Hertz), then solve the LTCA with contact-loss handling and the bearing iteration.
That is the realistic native rebuild — large but fully specified by cited methods, no
free parameters. The oracle validates each block and the final K_Hβ.

## Oracle (rikor.exe)
For exact values the original `rikor.exe` runs locally (Windows): place an example's
`rikor.cfg` as `bin/rikor.cfg`, run from `bin/` (it reads `rikor.cfg` from the CWD and
needs its runtime helper files there), output goes to the cfg's `AUSGABEDATEI`. Verified
to reproduce the bundled reference `.ria` (test 001: F_bt/b 1319.34, K_Hβ 1.36). Kept as
an optional, non-default oracle for exact F_βx / K_Hβ and for generating validation
cases — the native path stays the cross-platform default (ADR: native runners ship in
Docker; the `.exe` is Windows-only).

## Source methods for the compliance blocks (FVA 30 XI bibliography)
- **δ^Z tooth deformation — Weber, C.; Banaschek, K. (1955):** *Formänderung und
  Profilrücknahme bei gerad- und schrägverzahnten Rädern*, Schriftenreihe
  Antriebstechnik Bd. 11, Vieweg ([75]). Classic; the tooth bending+shear+compression
  compliance (also the basis of the ISO 6336-1 c′). Formulas implementable from the
  published method.
- **δ^Z gear-body cross-influence — FVA-Arbeitsblatt Nr. T309 (1989):** *Einfluss der
  Radkörpergestalt auf die Zahnfedersteifigkeit und Breitenlastverteilung von
  Stirnrädern* ([25]). The plate-strip Radkörper influence numbers. **Not in
  `00_literatur`** — would be needed for a bit-exact gear-body block (else approximate).
- **δ^H** — Hertzian line-contact flattening (standard). **δ^W** — the native beam.

## Validation targets (test 001, single helical stage)
F_bt/b 1319.34 N/mm · c_γ 16.70 · K_Hβ 1.36 · K_Fβ 1.30 · Gesamtkorrektur peak
41.82 µm (vertex 77.76 mm) · w(b) 1799.82 → 1147 N/mm. Equivalent diameters
d_Q 116.68/481.52, d_T 102.37/469.45 mm.
