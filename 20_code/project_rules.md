# Project Rules & Context

This file defines the strict rules and architectural guidelines for the `semesterthesis/` project. All IDEs and AI agents MUST follow these rules.

## Directory Structure (under `20_code/`)
Two-digit prefixes; a nested subfolder keeps its parent's first digit and adds a second (e.g. `30_references_and_examples/31_FVA`). Python packages use import-safe names (e.g. `40_backend/app/`) because module names cannot start with a digit. **This list is the canonical map — keep it in sync with the repository whenever folders change.**

- `20_code/00_development_documentation/`: ADRs, architecture, lessons learned, development story (append-only, see §14).
- `20_code/10_verifiers/`: Python files used purely for verification/testing.
- `20_code/20_antigravity_scripts/`: Scripts used for moving files, automation, and command execution.
- `20_code/30_docker/`: Dockerfile, compose and deployment assets.
- `20_code/40_backend/`: FastAPI application — the `app/` package (`api`, `services`, `config`, `logging_config`, `errors`, `storage`, `database`).
- `20_code/50_frontend/`: React (Vite) single-page app.
- `20_code/60_cache/`: Disposable cache (mesh/FE intermediates); safe to delete (git-ignored, `CACHE_DIR`).
- `20_code/80_output/`: Persisted results in categorized subfolders; the local `app.storage` root (git-ignored, `STORAGE_LOCAL_BASE_PATH`).
- `20_code/90_logs/`: Runtime logs when not logging to stdout (git-ignored, `LOG_DIR`).

Reference code and examples live **outside** the code tree, at the repo root in `30_references_and_examples/` (read-only; do not edit or import).

## Global Rules
1. **File Generation**: New project files should be placed in their respective architected directories under `20_code/`.
2. **Backward Compatibility**: No backward compatibility requirements.
3. **Unused Code**: Code must always be tested against unused interfaces or unused variables.
4. **Exception Handling**: Route errors through a single, central error-handling utility rather than ad-hoc handlers scattered across modules.
5. **Exception Logs**: Check the logs under the `20_code/90_logs/` folder and handle exceptions.
6. **Timezone**: Always use **CET** (Central European Time) unless specified otherwise.
7. **OOP Paradigm**: Think in classes and utilize the object-oriented nature of Python.
8. **Fault Tolerance**: DO NOT silence faults. Avoid mutable defaults in `.get()` (e.g., `.get(key, [])`, `.get(key, {})`).
9. **Categorized Output**: Results, CSVs, logs, and photos must be placed in categorized subfolders under the `20_code/80_output/` folder.
10. **Prompt Headers**: Add a concise, machine-readable prompt at the beginning of each `.py` file describing its context and functionality.
11. **Minimal Try-Except**: Use as few try-except blocks as possible.
12. **Strict Dict Access**: Always use `dict["key"]` instead of `.get("key")` unless default behavior is explicitly required (and non-mutable).
13. **Type Jumps**: No jumps between types (e.g., list <-> tuple <-> dict) unless explicitly stated and limited to optimization.
14. **Accumulative Documentation**: Markdown files for e.g., lessons learned, decisions, and development stories (files in `20_code/00_development_documentation/`) **MUST NEVER** be replaced or overwritten entirely. New entries must be appended or merged to maintain a continuous, accumulating development story.

## Path & Notation Convention
- **Forward slashes everywhere**: Always write paths with `/` (POSIX-style) in code, docs, configs and storage keys — never `\`. This keeps the project identical across Windows, Linux containers and HA nodes.

## Configuration & Persistence Rules

15. **Single `.env` Source of Truth**: Every endpoint, credential, host and path
    (databases, object storage, external APIs, local directories) is configured
    in the **one** `20_code/.env` file and read through `app.config.Settings`.
    The frontend reads its `VITE_*` values from the same `.env` (Vite `envDir`).
16. **No Hardcoding**: Never hardcode endpoints, credentials, bucket names, or
    filesystem paths in source. If something must be stored locally, its path
    is provided via `.env` — not baked into the code.
17. **Persistence Through Abstractions Only**: All object/file persistence goes
    through `app.storage` (never raw `open()`/`Path.write_*` for application
    data). All database access goes through `app.database`. Backends are
    selected by `.env` (`STORAGE_BACKEND`, `DATABASE_BACKEND`) so local,
    S3-compatible (AWS S3 / Cloudflare R2 / Ceph / MinIO) or hosted DB
    (SQLite / Postgres / Cloudflare D1) can be swapped without code changes.

## Architecture & Future-Proofing Rules

18. **Stateless & Multi-Node Ready (HA)**: Treat every process as one of many.
    Keep no shared mutable state in process memory; do not assume a single
    node's local filesystem is shared. Anything that must survive a restart or
    be visible to other nodes goes to the configured storage/database backend.
    A local storage path is single-node/dev only — multi-node deployments use
    object storage or a shared volume.
19. **Decoupled Frontend (Web *or* Local)**: The frontend stays a standalone
    SPA that talks to the API purely over HTTP via `VITE_API_BASE_URL`. It must
    remain runnable both as a hosted web tool and as a small local program; do
    not couple it to backend internals.
20. **Successor-First Clarity**: This project is handed over after the thesis.
    Favor obvious, well-documented, conventional structures over cleverness.
    New capabilities follow the existing `base.py` + concrete backend +
    `factory.py` + `README.md` pattern (see `app/storage`) so a successor can
    extend by example.
