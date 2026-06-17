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
  So `S_H`/`S_F` fall out of inputs; only `K_v`/`K_Hβ`/`K_Hα` (dynamics) and
  `Z_NT`/`Y_NT` (life) remain inputs.
- **`iso6336_root_strength.py`** — ISO 6336-3 root factors `Y_RrelT`, `Y_δrelT`, `Y_X`.
- **`iso6336_flank_strength.py`** — ISO 6336-2 flank factors `Z_L`, `Z_v`, `Z_R`, `Z_W`, `Z_X`.
- **`vdi2736.py`** *(next)* — plastic gears: flank/root stress, tooth temperature,
  wear, deformation; validated against the VDI 2736 Workbench report.

## Validated against two complete references

- **kst-E** (spur, DIN 3990 / STplus): `Z_E` 31.0, `Z_H` 2.400, `σ_H` 99.6, `σ_F` 180.1,
  `S_F` 4.571 (native). *(S_H native ≈ 15.1; STplus 17.184 uses Z_L=Z_v=Z_R=1.0, a
  DIN 3990 convention — ADR-011.)*
- **helical** (ISO 6336 / Workbench, memory `din3990-helical-reference`): `Z_β` 1.032,
  `Z_R` 0.854, `Y_RrelT` 0.915, `S_H` 1.044, `S_F` 2.275/2.309.

```python
from app.services.capacity import Iso6336Conditions, evaluate_iso6336
pinion, wheel = evaluate_iso6336(stage, roots, materials, load, conditions)
pinion.root_safety   # S_F
```
