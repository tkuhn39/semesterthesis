# Architecture

System design and the principles a successor must preserve. The binding,
itemized rules are in [`../project_rules.md`](../project_rules.md); this document
explains the *why* and the *how to extend*.

## Handover note

This project is developed during a semester thesis and **will not be maintained
afterwards**, but a successor may build on it. Therefore everything favors
clarity and conventional structure over cleverness, and every extension point
follows the same visible pattern: `base.py` (interface) + concrete backend +
`factory.py` (selection from `.env`) + `README.md`.

## High-level view

```
            ┌────────────────────┐        HTTP (VITE_API_BASE_URL)
            │  Frontend (React)  │  ───────────────────────────────┐
            │  50_frontend/      │   web tool OR small local app    │
            └────────────────────┘                                  │
                                                                    ▼
                                                   ┌────────────────────────────┐
                                                   │   API (FastAPI)            │
                                                   │   40_backend/app           │
                                                   │   stateless, N instances   │
                                                   └─────────────┬──────────────┘
                                            app.storage          │   app.database
                                       ┌─────────────────┐       │  ┌─────────────────┐
                                       │ local | s3      │ ◀─────┴─▶│ none|sqlite|     │
                                       │ (S3/R2/Ceph/    │          │ postgres|d1      │
                                       │  MinIO)         │          │ (extension pt.)  │
                                       └─────────────────┘          └─────────────────┘
```

All selection happens in `app.config.Settings` from the single `20_code/.env`.

## Configuration contract (single `.env`)

There is exactly **one** configuration file: [`../.env`](../.env)
(template: [`../.env.example`](../.env.example)). Every endpoint, credential and
path lives there and is read through `app.config.get_settings()`. The frontend
reads its `VITE_*` values from the *same* file via Vite's `envDir`.

Rules: never hardcode endpoints, credentials or paths — including local storage
paths (project_rules.md §15–16). Secrets use `SecretStr` and are never returned
by the API (`/api/info` exposes only non-secret fields).

## Storage abstraction (`app.storage`)

Backend-agnostic object/file persistence. Code calls `get_storage()` and uses
the `StorageBackend` interface only.

- `local` — a directory (`STORAGE_LOCAL_BASE_PATH`); single-node/dev.
- `s3` — any S3-compatible service: **AWS S3, Cloudflare R2, Ceph radosgw,
  MinIO**, selected purely via `.env` (`S3_ENDPOINT_URL`, `S3_USE_PATH_STYLE`, …).

See [`../40_backend/app/storage/README.md`](../40_backend/app/storage/README.md).

## Database abstraction (`app.database`)

Same shape as storage, kept minimal until a data model exists. `none` is
implemented; `sqlite` / `postgres` / `d1` are documented extension points.
See [`../40_backend/app/database/README.md`](../40_backend/app/database/README.md).

## High availability & statelessness

The service is designed to run as **one or many interchangeable instances**:

- **Stateless processes** — no shared mutable state in process memory; nothing
  important is stored on a node's local disk. Anything that must survive a
  restart or be visible to peers goes to the configured storage/database backend.
- **Local storage is single-node only.** Multi-node deployments use object
  storage (`s3`) or a shared volume — a `local` path is not shared across nodes.
- **Probes** — `GET /api/health` is liveness (process up, no dependencies);
  `GET /api/ready` is readiness (storage/database usable). A load balancer or
  orchestrator routes only to ready instances.
- **Logging** — `LOG_TO_STDOUT=true` so logs are collected by the platform
  rather than written to per-node files (12-factor); `NODE_NAME` identifies the
  instance.
- **Caching** — `get_settings`/`get_storage`/`get_database` use `lru_cache` for
  per-process reuse only; they hold no cross-node shared state.

## Decoupled frontend (web *or* local)

The frontend is a standalone SPA that talks to the API solely over HTTP via
`VITE_API_BASE_URL`. This keeps two deployment modes open:

- **Hosted web tool** — frontend served (e.g. by the backend as static files in
  the single Docker image) and the API reachable over the network.
- **Small local program** — run the API locally and point the SPA (or a future
  desktop wrapper) at `http://localhost:8000`.

Do not couple the frontend to backend internals; communicate only through the
documented API.

## Deployment

Default: a **single Docker image** (`30_docker/`) that builds the SPA and serves
it together with the API. For horizontal scaling, run multiple replicas behind a
load balancer, set `STORAGE_BACKEND=s3` (shared) and a networked database, and
rely on the readiness probe. The frontend may alternatively be hosted
separately by pointing `VITE_API_BASE_URL` at the API.

## How to extend (successor guide)

- **New API endpoint** → add to `app/api/` (new router for a new domain); read
  config via `get_settings()`; persist via `get_storage()` / `get_database()`.
- **New storage backend** → see `app/storage/README.md`.
- **New database backend** → see `app/database/README.md`.
- **New configuration** → add a field to `app.config.Settings` and document it
  in `.env.example`. Never read `os.environ` directly elsewhere.
