# `app.services` — domain / simulation layer

Business logic lives here, kept separate from the HTTP layer (`app/api`) and the
infrastructure layers (`app/storage`, `app/database`). API routes stay thin and
delegate to services; services contain the actual gear/FE computations.

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
