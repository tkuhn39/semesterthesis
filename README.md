# Semester Thesis — Tooth Root Stress Optimization of Plastic Gears

Semester thesis at the Technical University of Munich, Institute of Machine
Elements / Gear Research Center (FZG). The work investigates and optimizes the
tooth root stress of plastic spur gears using FE analysis (Abaqus) against the
analytical methods of DIN 3990 and VDI 2736.

> **Language convention:** The whole repository is documented in **English**,
> including code, comments and Git history. **Exception:** the thesis itself in
> [`10_report/`](10_report/) is written in **German**.

## Repository layout

| Path | Contents |
|------|----------|
| [`00_literatur/`](00_literatur/) | Reference literature (PDFs). **Git-ignored** — not version controlled. |
| [`10_report/`](10_report/) | LaTeX sources of the thesis (German). |
| [`20_code/`](20_code/) | All source code: backend, frontend, verification, Docker. See [`20_code/README.md`](20_code/README.md). |
| [`30_references_and_examples/`](30_references_and_examples/) | Read-only reference code and examples from other programs (kept out of the code tree). |

Numbered folders use a two-digit prefix. Nested subfolders keep the parent's
first digit and add a second one (e.g. `30_references_and_examples/31_FVA`).

## Quick start

The Python toolchain runs inside the Anaconda environment
`semesterthesis_3-12` (Python 3.12).

```bash
# 1. Create/update the environment from the pinned spec
conda env update --file 20_code/semesterthesis_3-12.yaml --prune
conda activate semesterthesis_3-12

# 2. (Optional) install dev tooling hooks
pre-commit install

# 3. Run the backend API
cd 20_code/40_backend
uvicorn app.main:app --reload

# 4. Run the frontend (separate shell)
cd 20_code/50_frontend
npm install && npm run dev
```

See [`20_code/30_docker/README.md`](20_code/30_docker/README.md) for the
containerized deployment.

## Dependency management

Dependencies are kept in sync across three places — update them **together**:

1. The live Conda environment `semesterthesis_3-12`
2. [`20_code/semesterthesis_3-12.yaml`](20_code/semesterthesis_3-12.yaml) — reproducible Conda spec
3. [`20_code/requirements.txt`](20_code/requirements.txt) — pip lockfile (used by Docker)

## Changelog

Notable changes to the FE / analysis toolchain are recorded in
[`CHANGELOG.md`](CHANGELOG.md) (Keep a Changelog format).

## License

Released under the [MIT License](LICENSE) © 2026 Technical University of
Munich, Institute of Machine Elements / Gear Research Center (FZG).
