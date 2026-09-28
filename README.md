# Semester Thesis — Tooth Root Stress of Plastic Gears

Semester thesis at the Technical University of Munich, Institute of Machine
Elements / Gear Research Center (FZG). The work investigates the tooth root
load capacity of (short-fibre-reinforced) plastic gears, comparing analytical
norm methods with FE analysis, and builds its own verified gear toolchain.

> **Language convention:** code, comments, identifiers, ADRs and Git history are
> **English**. The thesis in [`10_report/`](10_report/) and the norm-facing
> documentation that feeds it (`norm_map.md`, `norm_differences.md`, notebook
> prose) are **German**.

## Repository layout

| Path | Contents |
|------|----------|
| [`00_literatur/`](00_literatur/) | Reference literature (PDFs: norms, papers, theses, patents, datasheets). **Git-ignored.** |
| [`10_report/`](10_report/) | LaTeX sources of the thesis (German). |
| [`20_code/`](20_code/) | The toolchain: `10_gearcore/` (pydantic domain package `gearcore`), `00_development_documentation/` (ADRs, roadmap, norm map, gate protocol). See [`20_code/README.md`](20_code/README.md). |
| [`30_references_and_examples/`](30_references_and_examples/) | Read-only references: STplus installation + reference runs, FVA scripts, Abaqus decks, the archived legacy workbench (`38_legacy_workbench/`). **Git-ignored**, never imported. |
| [`40_jupyter-notebooks/`](40_jupyter-notebooks/) | Executable norm documentation: one notebook per norm chapter, importing `gearcore`, run in CI. |

Numbered folders use a two-digit prefix; nested folders keep the parent's first
digit (e.g. `30_references_and_examples/33_STplus`).

## Quick start

```bash
# Python 3.12 Anaconda environment (Windows: C:\ProgramData\anaconda3\Scripts\conda.exe)
conda activate semesterthesis_3-12
pip install -e "20_code/10_gearcore[dev]"
python -m ipykernel install --user --name semesterthesis_3-12

# tests (unit + property-based + notebook execution)
pytest 20_code/10_gearcore
pytest --nbmake 40_jupyter-notebooks

# regenerate STplus oracle fixtures (Windows only, needs the local STplus installation)
python 20_code/10_gearcore/scripts/stplus_oracle.py run-all
```

## History

The first toolchain (FastAPI + Next.js workbench, 2026-06 … 2026-09) was retired on
2026-09-28 and archived under `30_references_and_examples/38_legacy_workbench/`
(git tag `legacy-workbench-final`). See [`CHANGELOG.md`](CHANGELOG.md).

## License

Released under the [MIT License](LICENSE) © 2026 Technical University of
Munich, Institute of Machine Elements / Gear Research Center (FZG).
