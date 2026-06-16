# `app.services` — domain / simulation layer

Business logic lives here, kept separate from the HTTP layer (`app/api`) and the
infrastructure layers (`app/storage`, `app/database`). API routes stay thin and
delegate to services; services contain the actual gear/FE computations.

## Service map (the gear toolchain pipeline, ADR-009)

Built incrementally — each package is added when its first real logic lands.

| Package | Responsibility | Wraps / replaces |
|---------|----------------|------------------|
| `../io/` | Typed parsers/writers (pydantic): STplus `.ste`, REXS, STIRAK `.fsk`, Abaqus `.inp`/`.cof`, Z88 | file formats |
| `geometry/` | Spur-gear geometry: involute, root form circle, line of action A–E | — |
| `capacity/` | Analytical geometry & load capacity | STplus (FVA 241) |
| `loaddist/` | Tooth load distribution | RIKOR (FVA 30) |
| `body/` | CAD `.stp` → sector cut (pitches + run-in/out) → tet mesh → couple to rim | FVA 484 / FVA-Workbench |
| `model/` | Assemble the Abaqus rolling inp (rigid steel, sector body, ≥30 positions, material modes simple-nonlinear \| Converse-cof) | FVA 892 / STIRAK |
| `solve/` | Drive the Abaqus 2025 solver | — |
| `postprocess/` | Abaqus-Python 3.10 odbAccess extractor → neutral CSV/JSON (decoupled from workbench naming) | FVA postproc |
| `evaluation/` | Root tangent stress over width over A–E, tip deformation, flank pressure, per tooth | — |
| `visualization/` | 3D / holistic result views | — |

Pipeline: `geometry → capacity/loaddist → body → model → (Converse cof hand-off) → solve → postprocess → evaluation`.
External `.exe` are first wrapped behind typed services, then progressively reimplemented in Python.

## Conventions

- **One module per cohesive capability** (e.g. `tooth_root_stress.py`,
  `mesh.py`, `din3990.py`), classes for stateful pipelines (project_rules.md §7).
- **No I/O assumptions**: read configuration via `app.config.get_settings()`;
  persist results via `app.storage`; store disposable intermediates under
  `settings.cache_dir`. Never hardcode paths or call `open()` for app data
  (§16–17).
- **Stateless**: do not keep cross-request state in module globals; a service
  may run on any node (§18).
- **Testable**: pure computation functions belong in `10_verifiers/` tests or
  `40_backend/tests/`; cross-check against the analytical methods.

## Example shape

```python
# app/services/tooth_root_stress.py
from app.config import Settings
from app.storage import StorageBackend


class ToothRootStressService:
    def __init__(self, settings: Settings, storage: StorageBackend) -> None:
        self._settings = settings
        self._storage = storage

    def evaluate(self, run_id: str, ...) -> ...:
        ...  # compute, cache under settings.cache_dir, persist via self._storage
```
