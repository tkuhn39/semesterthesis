# `app.services.analysis` — three independent analyses (ADR-010)

Chair members can use each tool on its own, not only through the big rolling
implementation:

| `AnalysisKind` | What | Runner status |
|----------------|------|---------------|
| `stplus` | Spur-gear geometry & load capacity | **native** geometry (cross-platform, here) · capacity TODO · `exe` (Windows, full output) TODO |
| `rikor` | Tooth load distribution (FVA 30) | `native` TODO · `exe` (Windows) TODO |
| `rolling` | Quasi-static rolling FE (tooth-root stress) | TODO; consumes `stplus`/`rikor` outputs |

## Runners (how an analysis is computed)

`RunnerKind` = `native` (Python, cross-platform — the goal) · `exe` (subprocess
of the original Windows program, full original output) · `remote` (run on a
Windows host). Cross-platform coverage grows as native runners replace exe
runners; the structure stays fixed.

## Inputs / outputs

- Input: an **uploaded existing file** (a colleague's `.ste` / `.rexs`) **or** a
  **session-cached output** of a previous run.
- Output: an `AnalysisResult` (display-ready `values`) plus `artifacts` —
  storage keys (see `app.storage`) of produced files, exportable to a chosen
  folder or fed into the `rolling` analysis.

## Available now

```python
from app.io.ste import gear_stage_from_ste, load_ste
from app.services.analysis.stplus import run_stplus_geometry

result = run_stplus_geometry(gear_stage_from_ste(load_ste(path)))
result.values["working_center_distance_mm"]   # "52.0000" — matches STplus
```
