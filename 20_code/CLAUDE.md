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

| Folder | Purpose |
|--------|---------|
| `00_development_documentation/` | ADRs, lessons learned, dev story. **Append-only** (rule §14). |
| `10_verifiers/` | Verification / test scripts. |
| `20_antigravity_scripts/` | Automation, file-moving, command-execution scripts. |
| `30_docker/` | Dockerfile, compose, deployment assets. |
| `40_backend/` | FastAPI application (`app/` package). |
| `50_frontend/` | React (Vite) single-page app. |
| `60_references_other_programs/` | Read-only reference code (e.g. FVA Abaqus scripts). Do not edit. |
| `80_output/` | Generated results, CSVs, plots, photos — in categorized subfolders. Git-ignored. |
| `90_logs/` | Runtime logs. Git-ignored. |

Subfolders keep the parent's first digit and add a second (e.g. `61_FVA`).
Python packages, however, must use import-safe names (e.g. `40_backend/app/`),
since module names cannot start with a digit.

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

## Conventions (see project_rules.md for the full list)

- Object-oriented Python; think in classes.
- Prefer `dict["key"]` over `.get("key")` unless a non-mutable default is required.
- Minimal `try/except`; never silence faults.
- Each `.py` starts with a concise, machine-readable header describing its role.
- Results/logs go into categorized subfolders of `80_output/` and `90_logs/`.
- Documentation files in `00_development_documentation/` are appended, never overwritten.
