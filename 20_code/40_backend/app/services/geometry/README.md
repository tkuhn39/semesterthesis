# `app.services.geometry`

Involute spur/helical gear geometry per **DIN ISO 21771** (+ DIN 21773 for span),
reimplemented natively and **validated exactly against STplus** for the project
gear (kst-E). Computation uses current standards only; the withdrawn DIN 3960 is a
cross-check, never a basis (ADR-011).

## Modules

- **`generation.py`** — rack-tool generation (*Verzahnen*). Per gear: the
  generation profile shift `x_E`, the root form circle `d_Ff`, and the tip chamfer
  `h_K` / tip form circle `d_Fa` from the tool edge-break flank. The tip chamfer is
  the **intersection of the usable involute and the edge-break (Kantenbruch)
  involute** (ADR-012). Also the involute primitives `involute` / `inverse_involute`.
- **`gear.py`** — `GearStage`, the meshing pair: transverse module/pressure angle,
  reference/base/working-pitch diameters, working pressure angle & centre distance,
  usable tip circle `d_Na = d_Fa`, base pitch `p_et`, path of contact `g_α`, contact
  ratios `ε_α/ε_β/ε_γ`, span `W_k`, and `check_validity()` (ISO 1328-1 ranges + mesh
  sanity, advisory).

```python
from app.services.geometry import GearStage
from app.io.ste import gear_stage_from_ste, load_ste

stage = GearStage.from_ste(gear_stage_from_ste(load_ste(path)))
stage.transverse_contact_ratio    # 1.154 for kst-E — matches STplus (chamfer included)
stage.span_measurement_mm         # (17.090, 17.180) — matches STplus
```

## Validated vs STplus (kst-E)

`x_E`, `d_Ff` (49.081/50.158), `d_Fa` (52.894/53.788), `h_K` (0/0.117),
rest tip thickness `s_aK` (0.672/0.634), `α_wt` (21.46251°), `p_et` (2.952),
`g_α` (3.406), `ε_α = ε_γ` (1.154), `W_k` over k=6 (17.090/17.180).

## Not yet covered

Internal gears (`z < 0`) are only partly sign-handled; helical (`β > 0`) follows the
transverse chain but is not yet validated against a helical reference. The tooth-root
fillet geometry (s_Fn, h_F, ρ_F — the Y_F inputs) is added with the capacity work.
