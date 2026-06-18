# `app.services.loaddist`

Native **RIKOR (FVA 30)** load distribution — the face-/profile load over the tooth
width and the resulting face load factor **K_Hβ**, reimplemented from the documented
FVA 30 method (not by fitting RIKOR's I/O). Reads the RIKOR `.rie` input
(`app.io.rie`) and is validated against the bundled standard tests
(`30_references_and_examples/35_Rikor/.../Beispiele`).

Why: K_Hβ (ISO 6336-1 Method C) needs the **initial mesh misalignment F_βx**, a
shaft/mounting quantity. RIKOR computes it from the shaft–bearing system; this
package reproduces it so the analytical capacity no longer *feeds* K_Hβ. The result
also drives the load positions of the FE rolling model (Step 3).

## Phases
- **R1 — `forces.py`** ✅ — nominal mesh forces (F_bt, F_bn, F_bx, mean line load
  F_bt/b at the base circle, from the drive-gear design torque K_A·T_nom) and the
  ISO 6336-1 mesh line stiffness c_γ (c′_th, C_B, c′, c_γα/c_γβ — reusing the
  `capacity.iso6336_dynamics` stiffness chain, one implementation for both). Builds
  the meshing `GearStage` from the two `.rie` gears via `GearStage.from_parameters`.
- **R2 — `shaft.py` + `beam.py`** ✅ — each shaft a stepped **Timoshenko** beam
  (`UK/DA` stations → EI, G·A_s) on elastic bearings (`beam.py`, a small FE solver,
  validated exactly against closed-form beam deflection); the mesh force over the gear
  face + the **torsional wind-up** of both shafts → the **gap g(b)** (relative flank
  misalignment, line of action) and the equivalent misalignment f_βx. Bending sets the
  magnitude, torsion the asymmetry, shear lifts the peak. Reproduces RIKOR 001's
  Gesamtkorrektur in shape + magnitude (peak ≈ 44 µm vs 41.8; vertex in the loaded
  face). Bit-exact needs RIKOR's internal torque-transfer/bearing conventions.
- **R3 — `distribution.py`** ⬜ — 1-D elastic-foundation load sharing under g(b) with
  line stiffness c_γ → **w(b)**, **K_Hβ = w_max/w_mean**, K_Fβ, and the flank-line
  correction for uniform load.

## Validated vs RIKOR standard test 001 (single helical stage)
F_bt 167555.8 N, F_bt/b 1319.34 N/mm, F_bn 170316.0 N, F_bx 30538.0 N;
c′_th 18.4 (RIKOR c_sth 18.44), C_B 0.865 (0.87), c_γ 16.69 N/(µm·mm) (16.70).

```python
from app.io.rie import RikorInput
from app.services.loaddist import evaluate_mesh

ri = RikorInput.load(path_to_rikor_rie)
mesh = evaluate_mesh(ri)
mesh.forces.line_load_n_per_mm   # 1319.34
mesh.stiffness.mesh_alpha        # 16.69  (c_γ)
```
