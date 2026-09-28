# `30_references_and_examples`

**Read-only** reference code and examples from other programs and projects, kept
for orientation and comparison. This lives at the repository root, **outside**
the clean code tree (`20_code/`), on purpose. The whole folder is **git-ignored**
(local only): licensed software, licensed listings and the archived legacy code.

Do **not** edit these files and do **not** import them into the application —
copy and adapt the relevant parts into the proper package under
`20_code/40_backend/app/` instead.

| Subfolder | Source |
|-----------|--------|
| `31_FVA/` | FVA Abaqus post-processing scripts (`abaqus_postprocessing.py`, `odbElementConnectivity.py`). |
| `32_Abaqus/` | Reference Abaqus decks of the kst-E rolling simulation (implicit/explicit). |
| `33_STplus/` | FVA STplus 11.1F installation (`STplus11-1F/`: exe, manual, examples, tolerance XMLs) and reference runs: `kst-E_eingabe.ste`/`kst-E-ausgabe.sta`, `weitere_Konfigurationen/` (kst-A/B/C/E pairs; kst-E and kst-B verified, kst-A and kst-C unconfirmed). Used only as a numeric oracle via `20_code/10_gearcore/scripts/stplus_oracle.py`. |
| `34_LDA_Workbench/`, `35_Rikor/` | Other FZG tools (load distribution, RIKOR) for orientation. |
| `38_legacy_workbench/` | **Archived first toolchain** (FastAPI + Next.js, retired 2026-09-28, git tag `legacy-workbench-final`). Read-only design reference — never import from it, never revive it. |
