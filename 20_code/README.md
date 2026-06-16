# `20_code` — Source code

Code for the FE-based tooth root stress analysis and optimization of plastic
gears: a FastAPI backend, a React (Vite) frontend, and a Docker deployment.

> Documentation language is **English** throughout (see [`CLAUDE.md`](CLAUDE.md)
> and [`project_rules.md`](project_rules.md)).

## Layout

| Folder | Purpose |
|--------|---------|
| [`00_development_documentation/`](00_development_documentation/) | ADRs, lessons learned, development story (append-only). |
| [`10_verifiers/`](10_verifiers/) | Verification / test scripts. |
| [`20_antigravity_scripts/`](20_antigravity_scripts/) | Automation and utility scripts. |
| [`30_docker/`](30_docker/) | Dockerfile, compose, deployment assets. |
| [`40_backend/`](40_backend/) | FastAPI application. |
| [`50_frontend/`](50_frontend/) | React (Vite) single-page app. |
| [`60_references_other_programs/`](60_references_other_programs/) | Read-only reference code (e.g. FVA Abaqus scripts). |
| `80_output/` | Generated results (git-ignored). |
| `90_logs/` | Runtime logs (git-ignored). |

## Environment setup

```bash
# create or update the Conda environment (Python 3.12)
conda env update --file semesterthesis_3-12.yaml --prune
conda activate semesterthesis_3-12

# install the git hooks (optional but recommended)
pre-commit install
```

`requirements.txt` mirrors the pip-installable dependencies and is the source
of truth used by the Docker build. Keep it, the `.yaml`, and the live Conda
environment in sync.

## Running

| Component | Command | Working dir |
|-----------|---------|-------------|
| Backend (API) | `uvicorn app.main:app --reload` | `40_backend/` |
| Frontend (SPA) | `npm install && npm run dev` | `50_frontend/` |
| Full stack (containers) | `docker compose -f 30_docker/docker-compose.yml up --build` | `20_code/` |

## Quality gates

```bash
ruff check .      # lint
ruff format .     # format
mypy .            # static types
pytest            # tests
```

## Configuration

Runtime configuration is read from a `.env` file (never committed). Copy the
template and adjust:

```bash
cp .env.example .env
```
