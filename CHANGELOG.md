# Changelog

All notable changes to this project's FE / analysis toolchain (under
[`20_code/`](20_code/)) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Dates are ISO 8601 (YYYY-MM-DD).

## [Unreleased]

_Nothing yet._

## [0.2.0] - 2026-07-03

### Added (2026-07-03 — mesh API, deck rewiring + rigid shell, workbench UI; ADR-019/020, M3–M5)
- **API — mesh router** (`app/api/mesh.py`): `/api/mesh/preview` (2-D sector + per-quad scaled
  Jacobian), `/api/mesh/3d` (outer hull of the extruded sector for the three.js viewer),
  `/api/mesh/convergence` (native root/flank density quick check), `/api/mesh/fillet-compare`
  (quick-FE ranking of the fillet strategies incl. clearances), `/api/mesh/contour` (real as-cut
  boundary — kst-E or free variant parameters, fillet-strategy-capable, with interference check)
  and `/api/mesh/deck` (implicit rolling deck download).
- **FE deck on the transplant mesher (M3):** `implicit_deck.build_gear_part` now meshes via
  ADR-019 (4 teeth + 2 shoulders, density factors, fillet strategy); the mixed-pairing material
  rule ships as `steel_shell`/`rigid_gears` (steel gear = ideally stiff rigid body about its
  rotation node, contact + frozen FVA set contract unchanged); `plastic_index` fixes the
  Workstream-C convention (Part_Rad_Vz_1 = plastic wheel, second `.ste` entry).
- **Geometry:** `ToothProfile.half_thickness_angle` (tip thickness via the edge-break involute);
  the mating-tip interference sweep now samples only MATERIAL tip points and rolls the correct
  direction (a half-pitch corner sweep produced false interference for u ≠ 1 pairs).
- **Frontend v2 (ADR-020):** Next.js workbench under `50_frontend_v2/` — model tree, condensed
  attribute-table editors (Geist, Tailwind), dark three.js FE-mesh viewport with Jacobian
  heatmap, convergence + fillet-ranking panels, deck download with rigid-shell toggle, real
  tooth-form panel (standard vs optimized fillet overlay + clearance), Stufenvariation with
  parallel coordinates, Pareto and the up-to-4-variant **real-contour overlay comparison**;
  DE/EN i18n keys from day one. Served as a static export by FastAPI (`app/static`, gitignored).

### Added (2026-07-03 — reference-topology transplant mesher, ADR-019)
- **FE model — reference miner** (`model/reference_slice.py` + committed template
  `model/data/reference_sector_rad_vz_1.json`, verifier `10_verifiers/make_reference_template.py`):
  the ANSA/FVA wheel slice is parsed with correct cyclic face ordering (rim hexes carry a rotated
  local axis — naive ordering creates bowtie quads) and pinned by tests: 3024 quads / 3329 nodes,
  interior valences {4: 2716, 5: 2, 6: 3} — **exactly one fan-convergence node per tooth gap**,
  rim grid 26×25, min scaled Jacobian 0.243 (24 tip cells < 0.35).
- **FE model — transplant mesher** (`model/template_mesher.py`): generates the reference-identical
  block-structured 2D sector for any spur gear by re-using the mined connectivity and deriving node
  positions from the target geometry (pitch scaling, radial feature map, exact foot-point
  projection onto the analytic contour incl. the ISO 21771 tip chamfer up to d_a, selective §11
  tip lift). kst-E wheel: topology-identical, min scaled Jacobian 0.45, **0 cells < 0.35**.
- **FE model — canonical symmetry**: sector symmetry orbits enforce **exact tooth-to-tooth
  congruence** (≤ 1e-14 mm) and, gated by the data-driven `ToothProfile.is_flank_symmetric()`
  (DIN 867 §4.2), exact in-tooth mirror symmetry; the tip lift is rolled out orbit-synchronously.
- **FE model — parametric density** (`model/refine.py`): conformal chord splits with separate
  FVA-style root/flank factors; structure, gates and congruence survive every level.
- **FE model — native quick solver** (`model/plane_fe.py`): vectorized plane-strain Q4 FE
  (< 0.1 s/solve) for root/flank density-convergence checks (separate searches) — confirms the
  mined reference density is already converged for the root stress (Δ < 0.1 %).
- **Geometry — optimized root fillets** (`geometry/root_fillet.py`, supervisor's topic):
  `EllipticFillet` / `BezierFillet` / `BionicFillet` per the literature synthesis
  (`00_development_documentation/root_fillet_strategies.md`), pluggable into the mesher, with the
  mandatory mating-tip clearance check and a DIN 3960 eq. 3.6.06 undercut warning. Quick-FE on
  kst-E: ellipse −9.9 %, Bézier −22.1 % root stress vs the standard ρ_F arc.
- **Geometry — tip chamfer boundary**: `transverse_right_boundary(to_tip_circle=True)` continues
  past d_Na along the edge-break involute to d_a (`generation.edge_break_flank_transverse`).
- **Docs:** norm audit (`norm_geometry_audit.md` — DIN 3960/867/3972 findings incl. tool-profile
  presets I–IV and protuberance parameters living in DIN 3960 Anhang A) and the root-fillet
  literature synthesis with measured results.

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
- **FE model — reference ground truth + dome (WIP):** the reference deck `…_ohne_Radkoerper.inp` is
  now mined as the *meshed ground truth* (parse a z-slice → exact 2D topology, instead of guessing
  from screenshots): wheel 269 649 nodes, 81 z-levels (b=15, z-centered, Δz=0.1875), bore r=12.38,
  ~723 quads/pitch; structure = fine tooth → dome-cap fan → structured rim grid. New structured
  pieces toward it: optimization-based (quality-greedy) smoothing `structured_mesher._optimize_smooth`
  (+ `boundary_nodes`) and `assemble_pitch_2d` (merge tooth+body, hold only the outer contour, smooth
  the dome). Validated by overlay on the parsed reference; bad-cell count on the kst-E pitch fell from
  26 to 9 toward the reference dome. Dome-quality finish + sector/extrude next. (ADR-017)
- **FE model — body mesh matches the reference (kst-E):** the body is now built as a **root
  boundary layer** (fine surface-aligned arcs hugging the fillet, where the bending stress peaks)
  that runs out into a structured rim grid — the reason the reference is meshed this way. The
  reference itself is fully structured (all interior nodes valence 4; its only 6 cells < 0.35 sit at
  the tooth *tip*, min 0.243). The dome transition is lifted by the now **lexicographic**
  `_optimize_smooth` (maximise the worst incident scaled Jacobian, then the mean — the mean
  tie-breaker unlocks the plateau Laplacian/greedy-min got stuck at). Result on the kst-E wheel
  pitch: all-quad, **min Jacobian 0.736, 0 cells < 0.35** — exceeding the reference (0.243 / 6) with
  a reference-like structure. (ADR-017)
- **FE model — block-structured FVA mesher (`model/block_mesh.py`, WIP):** the reference-faithful
  multiblock route per `MESHING_SPEC.md`, built on the proven scaffold pipeline (TFI/Coons blocks +
  shared-node `NodeRegistry` for conformity, no tolerance merge, no paving/gmsh). Adds B3 fillet band
  (curve-seeded, densified to the 30°-tangent — not offset marching), B4 core, B1 rim, B2 deep 2:1
  quad templates, and the **section-11 finish** (optimization-based worst-first node relocation,
  frozen connectivity, fixed boundary/feature/cut nodes). On kst-E: registry conformity asserted,
  4-tooth + 2-toothless sector periodic to 5e-15 mm, B2 template det(J) **0.21 → 0.66** after the
  finish (0 cells < 0.35, 0 inverted). Element type **C3D8I** in the root. (ADR-018)
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
- **CI:** the workflow now installs the system OpenGL libs (`libglu1-mesa`, `libgl1`) the gmsh wheel
  links against, and runs `ruff format --check`; CI had been red since gmsh was introduced because
  importing it on the Linux runner failed with `libGLU.so.1: cannot open shared object file`, erroring
  out collection of every gmsh-importing test.

### Verified
- `ruff check .` clean, `mypy .` clean, `pytest` → 136 passed (full gold-standard
  validation active: kst-E, RIKOR, helical references present).
- FE geometry/mesh checked numerically + visually on kst-E (rounded root, deep rim, boundary layer,
  Jacobi 0.9); the all-quad 4→2 body-coarsening template validated standalone (|Jacobi| 1.0, ADR-017).
