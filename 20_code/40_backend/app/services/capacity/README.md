# `app.services.capacity`

Analytical tooth load capacity: metal gears per **ISO 6336:2019** (the current
standard; numerically equivalent to DIN 3990:1987, which STplus computes) and
plastic gears per **VDI 2736**. Built on `app.services.geometry` (form factors
Y_F/Y_S, contact ratios) and `app.services.materials` (elastic data, limits).
Standards basis & validation rule: ADR-011/013.

## Modules

- **`iso6336.py`** — `evaluate_iso6336`: flank and tooth-root stress and safety.
  Computed **natively**: the geometry factors (`Z_E`, `Z_H`, `Z_ε`, `Z_B`, `Z_D`;
  `Y_F`/`Y_S` from `geometry.tooth_root`), the stresses `σ_H`/`σ_F`, and the
  permissible stresses `σ_HP`/`σ_FP` (via the strength modules + `Iso6336Conditions`).
  So `S_H`/`S_F` fall out of inputs; only `Z_NT`/`Y_NT` (life) remain inputs. Pass an
  optional `DynamicConditions` to also compute `K_v`/`K_Hα`/`K_Hβ` natively.
- **`iso6336_dynamics.py`** — ISO 6336-1 dynamic/load factors: the mesh stiffness
  `c′`/`c_γα`/`c_γβ` (§9, with the **E/E_st correction** so a plastic gear softens the
  mesh), the reduced mass `m_red` (§6.5.9), the resonance ratio `N`, **`K_v` Method B**
  (eq. 13–22), **`K_Hα`/`K_Fα`** (§7.6) and **`K_Hβ`/`K_Fβ` Method C** (eq. 41–44).
  `compute_dynamic_factors` / `native_dynamic_factors` return a `DynamicFactors`. The
  accuracy deviations (`f_pb`, `f_fα`) and the mesh misalignment `F_βx` are inputs
  (the latter is RIKOR's job; `K_Hβ` Method B is deferred). ADR-014.
- **`iso6336_root_strength.py`** — ISO 6336-3 root factors `Y_RrelT`, `Y_δrelT`, `Y_X`.
- **`iso6336_flank_strength.py`** — ISO 6336-2 flank factors `Z_L`, `Z_v`, `Z_R`, `Z_W`, `Z_X`.
- **`vdi2736.py`** — plastic gears (VDI 2736 Blatt 2): `evaluate_vdi2736` returns root
  stress (**tip-load** `Y_Fa`/`Y_Sa` from `geometry.tooth_root`), flank stress (shared
  `Z_E`/`Z_H`/`Z_ε`), the **tooth temperature** ϑ (frictional heat, eq. 9), the **wear**
  `W_m` (eq. 19) and the **deformation** λ (eq. 22); the loss factor `H_V` (Wimmer) and
  the active-flank length `l_Fl` are native. Strength limits σ_Flim/σ_Hlim are read
  temperature- and cycle-dependent from the material (Table 5). ADR-015.

## Validated against two complete references

- **kst-E** (spur, DIN 3990 / STplus): `Z_E` 31.0, `Z_H` 2.400, `σ_H` 99.6, `σ_F` 180.1,
  `S_F` 4.571 (native). *(S_H native ≈ 15.1; STplus 17.184 uses Z_L=Z_v=Z_R=1.0, a
  DIN 3990 convention — ADR-011.)*
- **helical** (ISO 6336 / Workbench, memory `din3990-helical-reference`): `Z_β` 1.032,
  `Z_R` 0.854, `Y_RrelT` 0.915, `S_H` 1.044, `S_F` 2.275/2.309.
- **dynamics** (helical): locked components `C_B` 0.95 (= report), `c_γα` 17.21,
  `m_red` 0.0074 kg/mm, `N` 0.163; assembled `K_v` 1.034 (ref. 1.05), `K_Hα` 1.143
  (ref. 1.18) — in-band, the residual being the unreported accuracy grade (ADR-011/014).
- **VDI 2736** (kst-E plastic wheel, all inputs known → near-exact): σ_H 79.9 (ref
  79.893), σ_F 77.8 (ref 77.896), ϑ 107.77 °C (ref 107.767), `W_m` 40.16 µm (ref 40.151),
  λ 0.0378 mm (ref 0.038), `H_V` 0.0626, `l_Fl` 1.349/1.330 mm. (The report's displayed
  wheel `Y_Fa` 2.024 is a Workbench artefact — the native `Y_Fa` reproduces its σ_F.)

```python
from app.services.capacity import Iso6336Conditions, evaluate_iso6336
pinion, wheel = evaluate_iso6336(stage, roots, materials, load, conditions)
pinion.root_safety   # S_F
```
