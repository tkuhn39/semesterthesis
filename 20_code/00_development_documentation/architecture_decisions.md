# Architecture Decision Record

Design decisions for the plastic-gear tooth root stress project. Each entry
follows the ADR-lite template (Status / Context / Decision / Alternatives /
Consequences). See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the resulting design.

**Append-only:** Per [`../project_rules.md`](../project_rules.md) §14, future
entries are appended below — earlier ADRs are never overwritten. Mark a
superseded ADR with a `Superseded by ADR-NNN` line rather than editing it.

The index's **Status since** column records the date the ADR reached its current
status (ISO `YYYY-MM-DD`). Set it on creation and update it whenever the status
changes (e.g. on supersession), keeping it consistent with the date in the ADR
body.

---

## Index

| ADR | Title | Status | Status since |
|-----|-------|--------|--------------|
| ADR-001 | Tech stack, environment and conventions | Accepted | 2026-06-16 |
| ADR-002 | Single `.env` as configuration source of truth | Accepted | 2026-06-16 |
| ADR-003 | Pluggable storage abstraction (local + S3-compatible) | Accepted | 2026-06-16 |
| ADR-004 | Database abstraction as a documented extension point | Accepted | 2026-06-16 |
| ADR-005 | Stateless, multi-node (HA) design with probes | Accepted | 2026-06-16 |
| ADR-006 | Decoupled frontend and single-image default deployment | Accepted | 2026-06-16 |
| ADR-007 | Backend layering, cache dir and central logging/errors | Accepted | 2026-06-16 |
| ADR-008 | References moved out of the code tree; cache renumbered | Accepted | 2026-06-16 |
| ADR-009 | Unified gear toolchain: app pipeline (STplus/RIKOR/FE) replacing the FVA-Workbench | Accepted | 2026-06-16 |

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

## ADR-007 — Backend layering, cache dir and central logging/errors

**Status:** Accepted (2026-06-16)

> Note (2026-06-16): the cache folder was later renumbered `70_cache` → `60_cache`
> by ADR-008; references below to `70_cache` are historical.

**Context:** Before the simulation logic grows, the base needs an obvious home
for domain code, a tidy place for disposable intermediates, and consistent
logging/error handling — without over-building.

**Decision:** Introduce `app/services/` as the domain/simulation layer (API
routes stay thin and delegate). Add a dedicated, git-ignored `70_cache/`
(`CACHE_DIR`) for disposable mesh/FE intermediates — explicitly *not*
`10_verifiers/` (tests) nor a persistence store. Drop the redundant `OUTPUT_DIR`:
persisted results go through `app.storage` (`STORAGE_LOCAL_BASE_PATH` = `80_output`).
Add `app/logging_config.py` (stdout/file logging with `NODE_NAME`) and
`app/errors.py` (one JSON error envelope), wired in the app factory.

**Alternatives:** Cache under `80_output` (rejected: mixes disposable and
persisted data); keep `OUTPUT_DIR` alongside storage (rejected: two settings for
one directory); per-module ad-hoc logging/error handling (rejected: §4, drift).

**Consequences:** Clear separation (api → services → storage/database);
predictable cleanup (`70_cache` is safe to wipe); functional `LOG_*`/`NODE_NAME`
settings. See project_rules.md §4, §16–18.

---

## ADR-008 — References moved out of the code tree; cache renumbered

**Status:** Accepted (2026-06-16)

**Context:** `60_references_other_programs/` held read-only third-party code
(FVA Abaqus scripts) *inside* `20_code/`, mixing non-project reference material
into the clean code tree.

**Decision:** Move reference material out of `20_code/` to a new repo-root
folder `30_references_and_examples/` (subfolder `61_FVA` → `31_FVA`). The freed
slot is reused for the cache: `20_code/70_cache` → `20_code/60_cache`
(`CACHE_DIR`); `80_output` and `90_logs` are unchanged. All links, ignore files
and tool excludes were updated accordingly.

**Alternatives:** Keep references under `20_code` (rejected: not project code);
leave the cache at `70_cache` with a gap at `60` (rejected: less contiguous, and
references no longer occupy `60`).

**Consequences:** The code tree contains only project code; reference code is
clearly separated and excluded from linting/builds. Supplements ADR-007.

---

## ADR-009 — Unified gear toolchain: app pipeline replacing the FVA-Workbench

**Status:** Accepted (2026-06-16)

**Context:** The current workflow chains several separate programs (FVA-Workbench/
STIRAK for the rolling FE model, STplus for geometry/capacity, RIKOR for load
distribution, Converse for the anisotropic material card, Abaqus for the solve)
plus a workbench post-processing that **breaks on any inp modification**. The
chair runs many such tools. Goal: one lean, maintainable app that consolidates
the chain and lets us improve the FE model (rigid steel pinion, sector body,
element type, ≥30 rolling positions) and own the evaluation.

**Decision:** Build a single Python app (OOP + pydantic, FastAPI backend, modern
frontend later) layered into services under `40_backend/app`:
`io/` (typed parsers/writers: STplus `.ste`, REXS, STIRAK `.fsk`, Abaqus `.inp`/
`.cof`, Z88), `geometry/`, `capacity/` (STplus), `loaddist/` (RIKOR), `body/`
(CAD `.stp` → sector cut → mesh → couple to rim, per FVA 484), `model/` (assemble
the Abaqus rolling inp; material modes simple-nonlinear | Converse-cof), `solve/`
(drive Abaqus 2025), `postprocess/` (Abaqus-Python 3.10 odbAccess extractor,
decoupled from workbench naming, neutral CSV/JSON), `evaluation/`, `visualization/`.
External programs are first wrapped behind typed services, then progressively
reimplemented in Python. The FVA-Workbench code (STIRAK kernel templates, post
scripts) serves as the reference basis.

**Alternatives:** Keep scripting the workbench (rejected: postproc breaks on inp
edits, no model freedom, not consolidatable); a thin script collection (rejected:
not maintainable/handover-friendly, no typed contracts).

**Consequences:** One traceable codebase; model improvements and own evaluation
become possible; off-Workbench path. Abaqus postprocessing runs in Abaqus' bundled
Python 3.10 (2025), the rest in the `semesterthesis_3-12` env. See project_rules §17–20.

---
