# Changelog

All notable changes to this project's FE / analysis toolchain (under
[`20_code/`](20_code/)) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Dates are ISO 8601 (YYYY-MM-DD).

## [Unreleased]

### Removed
- **FE model:** deleted the unstructured gmsh tooth/sector mesher
  (`model/gmsh_mesher.py`: `mesh_sector_3d`, `mesh_tooth_pitch`,
  `mesh_tooth_pitch_3d`). Its self-intersecting multi-tooth boundary could make
  gmsh's Frontal-Delaunay meshing run unbounded — a multi-hour hang at full CPU.
  The structured, deterministic transfinite `mapped_mesher` is now the single
  meshing path.

### Added
- **FE model:** `model/mesh3d.py` holding the pure-numpy `Mesh3D` container and
  the native `extrude_to_hex` (quad section → C3D8 hexahedra), free of gmsh.
- **FE model:** an element-count safety valve (`max_elements`, default
  4,000,000) on the mapped mesher — an over-budget request is rejected up front
  instead of being meshed, so the mesher can no longer hang the machine.

### Fixed
- **FE model:** `tag_sector_surfaces` now reads the bore radius off the actual
  mesh (its quad-referenced nodes) instead of recomputing it from `rim_depth`,
  so the BORE / Fesselung node set can no longer come up empty when the mesher
  used a different rim depth.
- **Tooling:** cleared all outstanding ruff and mypy findings across the model
  layer and the test suite.

### Verified
- `ruff check .` clean, `mypy .` clean, `pytest` → 130 passed (full gold-standard
  validation active: kst-E, RIKOR, helical references present).
