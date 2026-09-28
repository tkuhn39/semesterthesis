# `20_code/` — the gear toolchain (restart 2026-09-28)

| Folder | Contents |
|---|---|
| `00_development_documentation/` | ADRs (series 101+), roadmap, norm map, norm differences, traceability table, adversarial-gate protocol, known limits, extension points. Append-only story. |
| `10_gearcore/` | Python package `gearcore` (src layout): pydantic contracts + norm-traceable gear geometry. Tests, fixtures, scripts. |
| `20_api/` *(later)* | FastAPI service wrapping `gearcore` contracts. |
| `30_docker/` *(later)* | Container build. |
| `40_ui/` *(later)* | Slim user interface. |

## Working with the package

```bash
conda activate semesterthesis_3-12            # Python 3.12; never install into base
pip install -e "20_code/10_gearcore[dev]"     # editable install, all dev tooling
pytest 20_code/10_gearcore                    # unit + hypothesis + fixture parity
pytest --nbmake 40_jupyter-notebooks          # executable norm documentation
ruff check 20_code 40_jupyter-notebooks && ruff format --check 20_code 40_jupyter-notebooks
mypy --strict 20_code/10_gearcore/src
python 20_code/10_gearcore/scripts/stplus_oracle.py run-all     # Windows only
python 20_code/10_gearcore/scripts/build_traceability.py
```

The binding rules are in [`project_rules.md`](project_rules.md); the agent
workflow summary is in [`CLAUDE.md`](CLAUDE.md).
