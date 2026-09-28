# Known limits (append-only)

Findings from adversarial gates that were deliberately deferred, with reason and owner. Entries are never
deleted; a resolved entry gets a "resolved in <commit/ADR>" line.

| ID | Increment | Severity | Description | Reason for deferral | Owner | Status |
|---|---|---|---|---|---|---|
| ADV0-23b | 0 | P2 | `quality_grade` bounds 0…12 not yet verified against DIN ISO 1328-1:2018 (grades) and DIN 3962 (1…12); the tolerance system is now explicit (`QualitySystem`) | verified when the tolerance module is implemented (increment 5) | implementer | open |
| ADV0-35 | 0 | P3 | On the developer machine the `python3` kernelspec resolves to another conda env; notebooks must be run with the `semesterthesis_3-12` kernel (registered) or via CI | environment-specific; README documents the kernel registration | user | open |
| ADV0-36 | 0 | P3 | `.sta` section detection assumes the dashed title frame is not split by a page break; not observed in any of the 15 listings | no reproduction in real listings; revisit if a listing shows it | implementer | open |
| ADV0-37 | 0 | P3 | Plastic E/ν from a `.ste` material block are kept only in the provenance note (no typed polymer layer from STplus data) | STplus carries no ISO 10350 data; typed polymer data comes with the material database in stage 2 | implementer | open |
| ADV0-29 | 0 | P3 | `kst_e/report.sta.txt` contains one NUL byte printed by STplus 11.0F (`theta_Bmax` line); kept verbatim for provenance | cosmetic; `grep` treats the file as binary | – | accepted |
