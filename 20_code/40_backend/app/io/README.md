# `app.io` — typed file-format layer

Parsers/writers for the gear toolchain's file formats. Each format is a module
exposing pydantic models, so services depend on **typed data**, never on raw text.

| Module | Format | Status |
|--------|--------|--------|
| `ste.py` | STplus `.ste` (FVA 241 spur-gear input) | parse + typed gear-stage extraction |
| `rexs.py` | REXS gear-model XML | planned |
| `fsk.py` | STIRAK `.fsk` | planned |
| `inp.py` | Abaqus `.inp` (keyword-block aware) | planned |
| `cof.py` | Converse `.cof` material card | planned |
| `z88.py` | Z88 mesh | planned |

## Example

```python
from pathlib import Path
from app.io.ste import load_ste, gear_stage_from_ste

stage = gear_stage_from_ste(load_ste(Path("kst-E_eingabe.ste")))
stage.teeth              # (51, 52)
stage.normal_module_mm   # 1.0
```

New formats follow the same pattern: pydantic models + `parse_*`/`load_*` (+ `dump_*` where needed).
