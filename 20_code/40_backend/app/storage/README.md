# `app.storage` — object/file storage abstraction

All application file/object persistence goes through this package. Code depends
only on the `StorageBackend` interface and obtains an instance via
`get_storage()`; the concrete backend is chosen by `.env` — **never** open files
directly for application data (project_rules.md §17).

## Backends

| `STORAGE_BACKEND` | Class | Use |
|-------------------|-------|-----|
| `local` | `LocalStorageBackend` | A directory (`STORAGE_LOCAL_BASE_PATH`). Single-node / dev only — a local path is not shared across HA nodes. |
| `s3` | `S3StorageBackend` | Any S3-compatible service: AWS S3, Cloudflare R2, Ceph radosgw, MinIO. HA-friendly (shared, stateless). |

Switching backend = editing `.env` only. See `../../.env.example`.

## Interface

```python
from app.storage import get_storage

storage = get_storage()
storage.save_bytes("results/run1/stress.csv", data)
raw = storage.load_bytes("results/run1/stress.csv")
storage.exists("results/run1/stress.csv")
storage.list_keys(prefix="results/")
storage.delete("results/run1/stress.csv")
```

Keys are POSIX-style relative paths and are identical across backends, so the
same code works locally and against object storage.

## Adding a backend

Follow the existing pattern (project_rules.md §20):

1. Add the selector value to `StorageBackend` in `app/config.py` and any needed
   settings (read from `.env`).
2. Implement `app/storage/<name>.py` subclassing `StorageBackend` from
   `base.py`.
3. Wire it into `build_storage()` in `factory.py` (lazy-import heavy SDKs).
4. Document it here.
