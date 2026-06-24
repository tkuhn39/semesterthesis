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
- **FE model:** reference-faithful implicit deck generator (`model/implicit_deck.py`)
  reproducing `32_Abaqus/implicit/…_ohne_Radkoerper.inp` — two `Part_Rad_Vz_{g}`
  sectors, bore `Fesselung` rigid-tied to a rotation node, frictionless hard contact
  as explicit meshing flank pairs (plastic = slave), and one quasi-static step driving
  gear 1 through a staircase angle while gear 2 carries the resisting torque. One-call
  entry `build_implicit_pair_from_stage(stage, …)`.
- **FE model:** reference per-tooth/flank tagging (`mesh_sets.tag_gear_reference`) emitting
  the exact `G{g}T{nnn}F{f}_NODESET/_ELEMENTSET` + `TOOTH-{g}-{nnn}F{f}` names the frozen
  FVA postprocessing requires, in 1-based 3-D ids.
- **FE model:** material cards (`model/materials_card.py`) — linear `*ELASTIC` (steel) and
  `*Hyperelastic, MARLOW` + `*Uniaxial Test Data` (plastic), with the kst-E PA curve embedded
  for validation.
- **FE model — geometry:** clean rounded root fillet (`tooth_form.transverse_right_boundary`): the
  ρ_F arc tangent to the involute flank (true d_Ff) and the root circle d_f → a monotone boundary
  with no pinch. Regression test guards monotonicity + flank/fillet continuity for both gears.
- **FE model — mesher:** the transfinite `mapped_mesher` now builds the tooth from that clean
  boundary, with a fine **surface boundary layer** (`flank_bias`, gmsh "Bump") and a radially graded
  **deep rim** to the real bore; Jacobi-Güte ≥ 0.9. Native fallback mesher
  `model/structured_mesher.py` (radius-arc tooth + rim) with a scaled-Jacobian check. (ADR-017)
- **FE model — body mesh (WIP):** building blocks toward the reference gear-body mesh —
  `mapped_mesher.tooth_section_2d` (transfinite tooth+fillet, no rim, + ordered d_f base interface),
  a validated **conformal all-quad 4→2 coarsening template** + graded ring (`structured_mesher.
  body_section_2d`), and Laplacian smoothing. The exact reference **O-grid "dome + run-out"** body
  (fine structure continued under the tooth, coarsening only outside the root) is the next step;
  the tooth/root itself is already reference-grade and (Saint-Venant) sets the root stress. (ADR-017)
- **FE model:** `model/mesh3d.py` holding the pure-numpy `Mesh3D` container and
  the native `extrude_to_hex` (quad section → C3D8 hexahedra), free of gmsh.
- **FE model:** an element-count safety valve (`max_elements`, default
  4,000,000) on the mapped mesher — an over-budget request is rejected up front
  instead of being meshed, so the mesher can no longer hang the machine.

### Fixed
- **FE model:** the inverted / pinched tooth root ("Pokal" shape) is fixed — the root cause was
  `tooth_form.root_fillet_points` producing a non-monotonic, branch-mixed trochoid that did not even
  meet the involute at d_Ff; the `_monotone_fillet` band-aid is removed. (ADR-017)
- **FE model:** gmsh section quads are normalised to CCW winding before the face-width sweep, so the
  C3D8 hexahedra are positively oriented (Abaqus rejects negative-Jacobian elements).
- **FE model:** `tag_sector_surfaces` now reads the bore radius off the actual
  mesh (its quad-referenced nodes) instead of recomputing it from `rim_depth`,
  so the BORE / Fesselung node set can no longer come up empty when the mesher
  used a different rim depth.
- **Tooling:** cleared all outstanding ruff and mypy findings across the model
  layer and the test suite.

### Verified
- `ruff check .` clean, `mypy .` clean, `pytest` → 136 passed (full gold-standard
  validation active: kst-E, RIKOR, helical references present).
- FE geometry/mesh checked numerically + visually on kst-E (rounded root, deep rim, boundary layer,
  Jacobi 0.9); the all-quad 4→2 body-coarsening template validated standalone (|Jacobi| 1.0, ADR-017).
