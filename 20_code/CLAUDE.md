# CLAUDE.md — guidance for AI agents in `20_code/`

The binding rules live in [`project_rules.md`](project_rules.md) — read them first.

## Project
Norm-traceable gear toolchain for the semester thesis (tooth root load capacity of plastic gears).
Stage 1 (current): 2D involute geometry chain in the pydantic package `gearcore`
(`10_gearcore/`), verified against norm worked examples and the STplus oracle, documented in
executable notebooks (`../40_jupyter-notebooks/`). Later stages: load capacity + material
database, alternative root fillets, parameter studies, FE deck generation, API/UI/Docker.

## Environment
Anaconda env `semesterthesis_3-12` (Python 3.12). In Git Bash the `python` alias is missing —
use `/c/Users/kuhnt/.conda/envs/semesterthesis_3-12/python.exe` or
`C:\ProgramData\anaconda3\Scripts\conda.exe run -n semesterthesis_3-12 ...`.
Dependencies live in **one** place: `10_gearcore/pyproject.toml`.

## Reading the sources
Norm/patent/FVA/datasheet PDFs cannot be opened with the Read tool (false "password-protected").
Use Poppler: `pdftotext -f A -l B -layout file.pdf -` for numbers/pages,
`pdftoppm -f P -l P -r 150 -png file.pdf out` + view the PNG for formula bodies and tables.
Never trust the text layer for formula bodies or multi-column tables.

## Commands
```bash
pip install -e "10_gearcore[dev]"
pytest 10_gearcore                          # unit + hypothesis + parity
pytest --nbmake ../40_jupyter-notebooks     # notebooks
ruff check . ../40_jupyter-notebooks && ruff format --check . ../40_jupyter-notebooks
mypy --strict 10_gearcore/src
python 10_gearcore/scripts/stplus_oracle.py run-all      # Windows only, local STplus
python 10_gearcore/scripts/build_traceability.py
```
Git signing (SSH via 1Password) only works from PowerShell, not from Git Bash.

## Things to never get wrong
- One equation = one function with a full `@eq` reference (norm + edition + eq + section + page).
- Current norm wins; STplus mismatches become documented norm differences, never code "fixes".
- Typed errors instead of `None`/clamping; steel and plastic never mixed; helical always supported.
- Never import from `30_references_and_examples/38_legacy_workbench` (`app` is banned).
- Every increment ends with the adversarial gate (`00_development_documentation/adversarial_gate.md`)
  run by a read-only reviewer agent; check `git status` after it.
