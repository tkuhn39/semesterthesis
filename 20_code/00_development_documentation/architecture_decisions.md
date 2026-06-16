# Architecture Decision Record

Design decisions for the plastic-gear tooth root stress project. Each entry
follows the ADR-lite template (Status / Context / Decision / Alternatives /
Consequences). See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the resulting design.

**Append-only:** Per [`../project_rules.md`](../project_rules.md) §14, future
entries are appended below — earlier ADRs are never overwritten. Mark a
superseded ADR with a `Superseded by ADR-NNN` line rather than editing it.

---

## Index

| ADR | Title | Status |
|-----|-------|--------|
| ADR-001 | Tech stack, environment and conventions | Accepted |
| ADR-002 | Single `.env` as configuration source of truth | Accepted |
| ADR-003 | Pluggable storage abstraction (local + S3-compatible) | Accepted |
| ADR-004 | Database abstraction as a documented extension point | Accepted |
| ADR-005 | Stateless, multi-node (HA) design with probes | Accepted |
| ADR-006 | Decoupled frontend and single-image default deployment | Accepted |

---

## ADR-001 — Tech stack, environment and conventions

**Status:** Accepted (2026-06-16)

**Context:** Semester thesis tool (FE tooth root stress of plastic gears) that
should be runnable, deployable and handed over to a successor.

**Decision:** Python 3.12 in the Anaconda env `semesterthesis_3-12`; FastAPI
backend + React (Vite) frontend; MIT license (© TUM/FZG). Repository is English
except the German thesis in `10_report/`. Numbered folders use a two-digit
prefix; nested subfolders keep the parent's first digit (Python packages use
import-safe names). Dependencies stay in sync across `requirements.txt`,
`requirements-dev.txt`, `semesterthesis_3-12.yaml` and the live env.

**Alternatives:** Streamlit (rejected: couples UI and backend, limits the
web/local split); Poetry/pip-tools (rejected: Conda is the mandated env).

**Consequences:** Clear separation of concerns; a successor can run, test and
containerize from documented commands.

---

## ADR-002 — Single `.env` as configuration source of truth

**Status:** Accepted (2026-06-16)

**Context:** Endpoints will grow (databases, object storage, external APIs).
Scattered or hardcoded configuration is the main source of handover pain.

**Decision:** One `20_code/.env` holds every endpoint, credential and path,
read only through `app.config.Settings`. The frontend reads its `VITE_*` values
from the same file via Vite `envDir`. Nothing is hardcoded; local storage paths
are configured too. Secrets use `SecretStr` and are never exposed by the API.

**Alternatives:** Per-component config files (rejected: duplication, drift);
reading `os.environ` ad hoc (rejected: untyped, scattered).

**Consequences:** New settings are added in one typed place and documented in
`.env.example`. See project_rules.md §15–16.

---

## ADR-003 — Pluggable storage abstraction (local + S3-compatible)

**Status:** Accepted (2026-06-16)

**Context:** The tool must support self-managed local directories *and* hosted
object storage (Cloudflare R2, S3, Ceph), switchable without code changes.

**Decision:** `app.storage` defines a `StorageBackend` interface; `local` and
`s3` backends are selected by `.env`. The single `s3` backend covers AWS S3,
R2, Ceph radosgw and MinIO via `S3_ENDPOINT_URL` + path-style addressing.
Application code persists files only through `get_storage()`.

**Alternatives:** Separate backends per provider (rejected: they share the S3
API); direct filesystem access (rejected: not portable, not HA-safe).

**Consequences:** Backend swap = `.env` edit. A `local` path is single-node;
multi-node uses `s3` (see ADR-005).

---

## ADR-004 — Database abstraction as a documented extension point

**Status:** Accepted (2026-06-16)

**Context:** A successor may need a database (self-hosted SQLite/Postgres or
hosted Cloudflare D1), but no data model exists yet.

**Decision:** `app.database` mirrors the storage pattern with a minimal
`DatabaseBackend` interface. Only `none` (no-op) is implemented; `sqlite`,
`postgres` and `d1` are configured in `.env` and reserved as documented slots.
No ORM/SDK is added until needed.

**Alternatives:** Add SQLAlchemy now (rejected: unused dependency, premature
modeling); no abstraction (rejected: forces later restructuring).

**Consequences:** Zero unused runtime deps now; the extension path is obvious
(`app/database/README.md`).

---

## ADR-005 — Stateless, multi-node (HA) design with probes

**Status:** Accepted (2026-06-16)

**Context:** The program may grow into a high-availability service on one or
several nodes; it must not break when scaled out.

**Decision:** Processes are stateless — no shared in-memory state, no reliance
on node-local disk for shared data (that goes to storage/database). Expose
`GET /api/health` (liveness) and `GET /api/ready` (readiness). Log to stdout
(`LOG_TO_STDOUT`); identify instances via `NODE_NAME`.

**Alternatives:** In-memory sessions / local-file state (rejected: breaks under
multiple nodes); a single combined health endpoint (rejected: conflates
liveness and readiness).

**Consequences:** Horizontal scaling needs only shared backends + a load
balancer honoring readiness. See project_rules.md §18.

---

## ADR-006 — Decoupled frontend and single-image default deployment

**Status:** Accepted (2026-06-16)

**Context:** The result may be a hosted web tool or a small local program.

**Decision:** The frontend is a standalone SPA talking to the API only over
HTTP via `VITE_API_BASE_URL`. Default deployment is a single Docker image that
builds and serves the SPA alongside the API; the frontend may also be hosted
separately by repointing `VITE_API_BASE_URL`.

**Alternatives:** Server-rendered/coupled UI (rejected: removes the local-app
option); always-separate services (rejected: heavier default for a thesis tool).

**Consequences:** Both deployment modes stay open without code changes.
See project_rules.md §19.

---
