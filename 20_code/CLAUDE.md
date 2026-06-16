# CLAUDE.md — guidance for AI agents in `20_code/`

This file orients AI coding agents (and humans) working inside `20_code/`.
The binding rules live in [`project_rules.md`](project_rules.md) — read them
first. This file summarizes the practical workflow.

## Project

FE-based tooth root stress analysis and optimization of plastic spur gears
(Abaqus, DIN 3990, VDI 2736). Python backend (FastAPI) + React frontend,
shipped as a Docker image.

## Language

All code, comments, docstrings, identifiers and Git messages are in **English**.
Only the thesis under `../10_report/` is German.

## Environment

Use the Anaconda environment `semesterthesis_3-12` (Python 3.12). Never install
into `base`.

```bash
conda activate semesterthesis_3-12
```

When you add or remove a dependency, update **all three** in the same change:

1. the live Conda env (`conda install ...` / `pip install ...`)
2. [`semesterthesis_3-12.yaml`](semesterthesis_3-12.yaml)
3. [`requirements.txt`](requirements.txt)

## Directory map

The canonical folder layout lives in
**[project_rules.md](project_rules.md) → Directory Structure** (kept in sync with
the repo, so there is one source of truth). Python packages use import-safe names
(e.g. `40_backend/app/`) because module names cannot start with a digit.

## Common commands

```bash
# lint + format + type-check
ruff check .
ruff format .
mypy .

# tests
pytest

# backend dev server
uvicorn app.main:app --reload          # from 40_backend/

# frontend dev server
npm run dev                            # from 50_frontend/
```

## Rules & architecture (authoritative docs)

This file only covers the workflow. The **binding rules** are the single source
of truth in **[project_rules.md](project_rules.md)** — read them before changing
code. The **system design** (HA / multi-node, statelessness, the `.env` config
contract, storage/database abstractions, decoupled frontend) lives in
**[00_development_documentation/ARCHITECTURE.md](00_development_documentation/ARCHITECTURE.md)**.

Things to never get wrong:

- One `20_code/.env` configures everything; read it via
  `app.config.get_settings()`. Never hardcode endpoints, credentials or paths,
  including local storage paths (project_rules §15–16).
- Persist files only via `app.storage`, data only via `app.database`; choose the
  backend through `.env` — local / S3-compatible (S3, R2, Ceph, MinIO) /
  SQLite / Postgres / D1 (project_rules §17).
- Assume the service runs on several nodes at once: no in-process shared state,
  no node-local filesystem assumptions (project_rules §18).
