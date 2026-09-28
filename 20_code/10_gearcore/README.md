# gearcore

Norm-traceable involute cylindrical gear geometry with pydantic data contracts.
Part of the semester thesis toolchain (see `../README.md`, `../project_rules.md`).

```bash
pip install -e ".[dev]"
pytest                                   # unit + property-based + STplus fixture parity
python scripts/stplus_oracle.py run-all  # Windows only — regenerates the STplus fixtures
python scripts/build_traceability.py     # norm → equation → function → test → notebook table
```

Every computational function is decorated with `@eq("<SOURCE>:<EDITION>", "<eq>", section=..., page=...)`;
`src/gearcore/data/sources.yaml` is the verified source registry.
