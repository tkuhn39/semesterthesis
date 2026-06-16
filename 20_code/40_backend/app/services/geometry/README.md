# `app.services.geometry`

Involute spur/helical gear-stage geometry (DIN 3960 / ISO 21771), reimplemented
in Python and **validated against STplus output**.

`GearStage` takes the defining parameters (module, teeth, pressure/helix angle,
profile shift, optional center distance) and derives:

- transverse module & pressure angle
- reference, base and working-pitch diameters `(pinion, wheel)`
- reference and working center distance
- working (operating) pressure angle — from the given center distance, or the
  backlash-free generated value (profile shifts) when no center distance is given

```python
from app.services.geometry import GearStage
from app.io.ste import gear_stage_from_ste, load_ste

stage = GearStage.from_ste(gear_stage_from_ste(load_ste(path)))
stage.working_pitch_diameter_mm   # (51.495, 52.505) for kst-E — matches STplus
```

## Deferred

The transverse contact ratio is **not** exposed yet: STplus reduces the effective
tip diameter by the tip chamfer (Kopfkantenbruch, e.g. hK=0.117 on the wheel), so
the raw-tip formula (~1.25) disagrees with STplus (1.154). It will be added with
the tool/chamfer model so the value matches STplus.
