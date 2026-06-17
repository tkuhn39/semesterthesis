# `app.services.capacity`

Analytical tooth load capacity: steel gears per **DIN 3990** and plastic gears per
**VDI 2736**. Built on `app.services.geometry` (tooth-root form factors Y_F/Y_S,
contact ratios) and `app.services.materials` (elastic data, endurance limits).

## Modules

- **`din3990.py`** — flank (pitting) and tooth-root (bending) stress and safety.
  Geometry-derived factors computed exactly: elasticity `Z_E`, zone `Z_H`, contact
  ratio `Z_ε`; form `Y_F` and stress correction `Y_S` come from
  `geometry.tooth_root`. The load/dynamic/face/transverse factors (`K_A`, `K_v`,
  `K_Hβ`, `K_Fβ`, …), the single-contact factors (`Z_B`, `Z_D`) and the
  permissible-stress life/sub factors are typed inputs with **neutral defaults
  (1.0)** — a missing factor never blocks the evaluation (graceful), it just yields
  the corresponding nominal/static result.
- **`vdi2736.py`** *(next)* — plastic gears: flank/root stress, tooth temperature,
  wear and deformation; validated against the VDI 2736 Workbench report.

## Validated vs STplus (kst-E)

`Z_E` 31.0, `Z_H` 2.400, `σ_H0` 72.4, `σ_H` 99.6/99.5, `σ_F0` 99.5/100.2,
`σ_F` 180.1/181.4, and the safety factors `S_F` 4.571/0.375, `S_H` 17.184/0.703.

```python
from app.services.capacity import Din3990LoadCase, evaluate_din3990
result = evaluate_din3990(stage, roots, materials, load)
result.pinion.root_safety   # S_F
```
