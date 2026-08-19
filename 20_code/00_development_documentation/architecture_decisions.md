# Architecture Decision Record

Design decisions for the plastic-gear tooth root stress project. Each entry
follows the ADR-lite template (Status / Context / Decision / Alternatives /
Consequences). See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the resulting design.

**Append-only:** Per [`../project_rules.md`](../project_rules.md) §14, future
entries are appended below — earlier ADRs are never overwritten. Mark a
superseded ADR with a `Superseded by ADR-NNN` line rather than editing it.

The index's **Status since** column records the date the ADR reached its current
status (ISO `YYYY-MM-DD`). Set it on creation and update it whenever the status
changes (e.g. on supersession), keeping it consistent with the date in the ADR
body.

---

## Index

| ADR | Title | Status | Status since |
|-----|-------|--------|--------------|
| ADR-001 | Tech stack, environment and conventions | Accepted | 2026-06-16 |
| ADR-002 | Single `.env` as configuration source of truth | Accepted | 2026-06-16 |
| ADR-003 | Pluggable storage abstraction (local + S3-compatible) | Accepted | 2026-06-16 |
| ADR-004 | Database abstraction as a documented extension point | Accepted | 2026-06-16 |
| ADR-005 | Stateless, multi-node (HA) design with probes | Accepted | 2026-06-16 |
| ADR-006 | Decoupled frontend and single-image default deployment | Accepted | 2026-06-16 |
| ADR-007 | Backend layering, cache dir and central logging/errors | Accepted | 2026-06-16 |
| ADR-008 | References moved out of the code tree; cache renumbered | Accepted | 2026-06-16 |
| ADR-009 | Unified gear toolchain: app pipeline (STplus/RIKOR/FE) replacing the FVA-Workbench | Accepted | 2026-06-16 |
| ADR-010 | Three independent analyses (STplus/RIKOR/rolling) with pluggable runners | Accepted | 2026-06-16 |
| ADR-011 | Compute on current standards only; withdrawn norms are cross-checks | Accepted | 2026-06-17 |
| ADR-012 | Native involute geometry incl. tool-generated tip chamfer (amended: per-gear tool fields, Kopfrücknahme C_αa in the FE contour) | Accepted | 2026-07-07 |
| ADR-013 | Plastic-capable Stufenvariation and its performance strategy | Accepted | 2026-06-17 |
| ADR-014 | Native ISO 6336-1 dynamic/load factors (K_v, K_Hα, K_Hβ) | Accepted | 2026-06-17 |
| ADR-015 | Native VDI 2736 plastic-gear capacity (root/flank/temperature/wear/deformation) | Accepted | 2026-06-17 |
| ADR-016 | Native ISO 1328-1 accuracy-grade tolerances (grade → deviations) | Accepted | 2026-06-18 |
| ADR-017 | FE rolling-model mesh: ρ_F-arc root, transfinite tooth, all-quad body fan | Accepted | 2026-06-24 |
| ADR-018 | Block-structured FVA/STIRAK gear mesh on a fixed scaffold (MESHING_SPEC.md) | Superseded by ADR-019 | 2026-07-03 |
| ADR-019 | Reference-topology transplant mesher: mined ground truth, canonical symmetry, chord density, quick FE, fillet strategies (amended: Zahndicke chord group, effective counts, per-gear deck fineness) | Accepted | 2026-07-07 |
| ADR-020 | Next.js workbench frontend (FVA layout language, Geist, static export; amended: backend-served pair assembly, ortho + CATIA viewports) | Accepted | 2026-07-07 |
| ADR-021 | Deck gear numbering follows the stage input order; mid-plane-centred extrusion with parametric axial offsets (amended: rig-view slot layout + Fesselung parity + per-position torque cycle, edge start, position series) | Accepted | 2026-07-06 |
| ADR-022 | Own FE postprocessing: neutral JSON dump + backend path-of-contact transform (GearStage SSOT) + 3-D stress/strain viewer | Accepted | 2026-07-07 |

---

## ADR-001 — Tech stack, environment and conventions

**Status:** Accepted (2026-06-16)

**Context:** Semester thesis tool (FE tooth root stress of plastic gears) that
should be runnable, deployable and handed over to a successor.

**Decision:** Python 3.12 in the Anaconda env `semesterthesis_3-12`; FastAPI
backend + React (Vite) frontend; MIT license (© TUM/FZG). Repository is English
except the German thesis in `10_report/`. Numbered folders use a two-digit
prefix; nested subfolders keep the parent's first digit (Python packages use
import-safe names). Dependencies stay in sync across `requirements.txt`,
`requirements-dev.txt`, `semesterthesis_3-12.yaml` and the live env.

**Alternatives:** Streamlit (rejected: couples UI and backend, limits the
web/local split); Poetry/pip-tools (rejected: Conda is the mandated env).

**Consequences:** Clear separation of concerns; a successor can run, test and
containerize from documented commands.

---

## ADR-002 — Single `.env` as configuration source of truth

**Status:** Accepted (2026-06-16)

**Context:** Endpoints will grow (databases, object storage, external APIs).
Scattered or hardcoded configuration is the main source of handover pain.

**Decision:** One `20_code/.env` holds every endpoint, credential and path,
read only through `app.config.Settings`. The frontend reads its `VITE_*` values
from the same file via Vite `envDir`. Nothing is hardcoded; local storage paths
are configured too. Secrets use `SecretStr` and are never exposed by the API.

**Alternatives:** Per-component config files (rejected: duplication, drift);
reading `os.environ` ad hoc (rejected: untyped, scattered).

**Consequences:** New settings are added in one typed place and documented in
`.env.example`. See project_rules.md §15–16.

---

## ADR-003 — Pluggable storage abstraction (local + S3-compatible)

**Status:** Accepted (2026-06-16)

**Context:** The tool must support self-managed local directories *and* hosted
object storage (Cloudflare R2, S3, Ceph), switchable without code changes.

**Decision:** `app.storage` defines a `StorageBackend` interface; `local` and
`s3` backends are selected by `.env`. The single `s3` backend covers AWS S3,
R2, Ceph radosgw and MinIO via `S3_ENDPOINT_URL` + path-style addressing.
Application code persists files only through `get_storage()`.

**Alternatives:** Separate backends per provider (rejected: they share the S3
API); direct filesystem access (rejected: not portable, not HA-safe).

**Consequences:** Backend swap = `.env` edit. A `local` path is single-node;
multi-node uses `s3` (see ADR-005).

---

## ADR-004 — Database abstraction as a documented extension point

**Status:** Accepted (2026-06-16)

**Context:** A successor may need a database (self-hosted SQLite/Postgres or
hosted Cloudflare D1), but no data model exists yet.

**Decision:** `app.database` mirrors the storage pattern with a minimal
`DatabaseBackend` interface. Only `none` (no-op) is implemented; `sqlite`,
`postgres` and `d1` are configured in `.env` and reserved as documented slots.
No ORM/SDK is added until needed.

**Alternatives:** Add SQLAlchemy now (rejected: unused dependency, premature
modeling); no abstraction (rejected: forces later restructuring).

**Consequences:** Zero unused runtime deps now; the extension path is obvious
(`app/database/README.md`).

---

## ADR-005 — Stateless, multi-node (HA) design with probes

**Status:** Accepted (2026-06-16)

**Context:** The program may grow into a high-availability service on one or
several nodes; it must not break when scaled out.

**Decision:** Processes are stateless — no shared in-memory state, no reliance
on node-local disk for shared data (that goes to storage/database). Expose
`GET /api/health` (liveness) and `GET /api/ready` (readiness). Log to stdout
(`LOG_TO_STDOUT`); identify instances via `NODE_NAME`.

**Alternatives:** In-memory sessions / local-file state (rejected: breaks under
multiple nodes); a single combined health endpoint (rejected: conflates
liveness and readiness).

**Consequences:** Horizontal scaling needs only shared backends + a load
balancer honoring readiness. See project_rules.md §18.

---

## ADR-006 — Decoupled frontend and single-image default deployment

**Status:** Accepted (2026-06-16)

**Context:** The result may be a hosted web tool or a small local program.

**Decision:** The frontend is a standalone SPA talking to the API only over
HTTP via `VITE_API_BASE_URL`. Default deployment is a single Docker image that
builds and serves the SPA alongside the API; the frontend may also be hosted
separately by repointing `VITE_API_BASE_URL`.

**Alternatives:** Server-rendered/coupled UI (rejected: removes the local-app
option); always-separate services (rejected: heavier default for a thesis tool).

**Consequences:** Both deployment modes stay open without code changes.
See project_rules.md §19.

---

## ADR-007 — Backend layering, cache dir and central logging/errors

**Status:** Accepted (2026-06-16)

> Note (2026-06-16): the cache folder was later renumbered `70_cache` → `60_cache`
> by ADR-008; references below to `70_cache` are historical.

**Context:** Before the simulation logic grows, the base needs an obvious home
for domain code, a tidy place for disposable intermediates, and consistent
logging/error handling — without over-building.

**Decision:** Introduce `app/services/` as the domain/simulation layer (API
routes stay thin and delegate). Add a dedicated, git-ignored `70_cache/`
(`CACHE_DIR`) for disposable mesh/FE intermediates — explicitly *not*
`10_verifiers/` (tests) nor a persistence store. Drop the redundant `OUTPUT_DIR`:
persisted results go through `app.storage` (`STORAGE_LOCAL_BASE_PATH` = `80_output`).
Add `app/logging_config.py` (stdout/file logging with `NODE_NAME`) and
`app/errors.py` (one JSON error envelope), wired in the app factory.

**Alternatives:** Cache under `80_output` (rejected: mixes disposable and
persisted data); keep `OUTPUT_DIR` alongside storage (rejected: two settings for
one directory); per-module ad-hoc logging/error handling (rejected: §4, drift).

**Consequences:** Clear separation (api → services → storage/database);
predictable cleanup (`70_cache` is safe to wipe); functional `LOG_*`/`NODE_NAME`
settings. See project_rules.md §4, §16–18.

---

## ADR-008 — References moved out of the code tree; cache renumbered

**Status:** Accepted (2026-06-16)

**Context:** `60_references_other_programs/` held read-only third-party code
(FVA Abaqus scripts) *inside* `20_code/`, mixing non-project reference material
into the clean code tree.

**Decision:** Move reference material out of `20_code/` to a new repo-root
folder `30_references_and_examples/` (subfolder `61_FVA` → `31_FVA`). The freed
slot is reused for the cache: `20_code/70_cache` → `20_code/60_cache`
(`CACHE_DIR`); `80_output` and `90_logs` are unchanged. All links, ignore files
and tool excludes were updated accordingly.

**Alternatives:** Keep references under `20_code` (rejected: not project code);
leave the cache at `70_cache` with a gap at `60` (rejected: less contiguous, and
references no longer occupy `60`).

**Consequences:** The code tree contains only project code; reference code is
clearly separated and excluded from linting/builds. Supplements ADR-007.

---

## ADR-009 — Unified gear toolchain: app pipeline replacing the FVA-Workbench

**Status:** Accepted (2026-06-16)

**Context:** The current workflow chains several separate programs (FVA-Workbench/
STIRAK for the rolling FE model, STplus for geometry/capacity, RIKOR for load
distribution, Converse for the anisotropic material card, Abaqus for the solve)
plus a workbench post-processing that **breaks on any inp modification**. The
chair runs many such tools. Goal: one lean, maintainable app that consolidates
the chain and lets us improve the FE model (rigid steel pinion, sector body,
element type, ≥30 rolling positions) and own the evaluation.

**Decision:** Build a single Python app (OOP + pydantic, FastAPI backend, modern
frontend later) layered into services under `40_backend/app`:
`io/` (typed parsers/writers: STplus `.ste`, REXS, STIRAK `.fsk`, Abaqus `.inp`/
`.cof`, Z88), `geometry/`, `capacity/` (STplus), `loaddist/` (RIKOR), `body/`
(CAD `.stp` → sector cut → mesh → couple to rim, per FVA 484), `model/` (assemble
the Abaqus rolling inp; material modes simple-nonlinear | Converse-cof), `solve/`
(drive Abaqus 2025), `postprocess/` (Abaqus-Python 3.10 odbAccess extractor,
decoupled from workbench naming, neutral CSV/JSON), `evaluation/`, `visualization/`.
External programs are first wrapped behind typed services, then progressively
reimplemented in Python. The FVA-Workbench code (STIRAK kernel templates, post
scripts) serves as the reference basis.

**Alternatives:** Keep scripting the workbench (rejected: postproc breaks on inp
edits, no model freedom, not consolidatable); a thin script collection (rejected:
not maintainable/handover-friendly, no typed contracts).

**Consequences:** One traceable codebase; model improvements and own evaluation
become possible; off-Workbench path. Abaqus postprocessing runs in Abaqus' bundled
Python 3.10 (2025), the rest in the `semesterthesis_3-12` env. See project_rules §17–20.

---

## ADR-010 — Three independent analyses with pluggable runners

**Status:** Accepted (2026-06-16)

**Context:** Chair members want to *use* STplus and RIKOR through the app without
the big rolling implementation, and ideally not only on Windows (the original
programs are Windows `.exe`). The rolling analysis in turn consumes STplus/RIKOR
outputs — either legacy files from colleagues or freshly generated ones.

**Decision:** Expose three first-class, independently runnable analyses —
`stplus`, `rikor`, `rolling` (`AnalysisKind`). Each analysis's compute is a
**pluggable runner**:
1. `exe` — subprocess of the original Windows program (full original output, Windows-only),
2. `native` — Python reimplementation (cross-platform; STplus geometry done, capacity/load-distribution to follow),
3. `remote` — optional, run on a Windows host with a cross-platform client.

Inputs are an uploaded existing file **or** a session-cached prior output;
results are persisted via `app.storage` and exportable to a chosen folder. The
`rolling` analysis takes `stplus`/`rikor` outputs as input. Cross-platform
coverage grows as native runners replace exe runners — the structure stays fixed.

**Alternatives:** Only wrap the exes (rejected: Windows-only, defeats the
cross-platform goal); one monolithic pipeline (rejected: the three uses must be
runnable independently).

**Consequences:** The three-option UX is stable from the start; each program can
be adopted independently; portability improves incrementally without rearchitecting.
See ADR-009, project_rules §17–20.

---

## ADR-011 — Compute on current standards only; withdrawn norms are cross-checks

**Status:** Accepted (2026-06-17)

**Context:** A native reimplementation used in engineering must be standards-
defensible. Current standards are mandatory; referencing **withdrawn** standards
as the basis of a calculation can be legally problematic. The legacy DIN 3960 /
3961 / 3963 / 21772 are superseded by **DIN ISO 21771**, **DIN ISO 1328-1/-2** and
**DIN 21773**. Separately, the available reference tools are not infallible: STplus
reproduces exactly for geometry, but the FVA-Workbench did **not** reproduce the
STplus values 1:1 and is suspected to carry a Kopfkantenbruch error.

**Decision:** All computation rests only on the current state of the art —
DIN ISO 21771 (geometry), DIN 21773 (tooth-thickness measures), DIN ISO 1328-1/-2
(tolerances), and for capacity **ISO 6336:2019 (parts 1–6) + VDI 2736** (plastics).
ISO 6336:2019 is the current international standard and the primary documented
basis; **DIN 3990:1987** is the equivalent, still-valid German method (not withdrawn
— it shares the core factor set with ISO 6336) and is used as a cross-check (and is
what STplus computes). The truly withdrawn standards (DIN 3960, DIN 21772) are
consulted **only** to cross-check understanding and are never cited as a basis.
ISO 6336 (2019) PDFs are text-readable (formulas read directly); the scanned
DIN 3990 is visual-only. Results are validated against shipped reference cases;
**where a reference tool deviates from a norm-correct result, the norm wins** — the
deviation is documented, not chased.

**Alternatives:** Fit to STplus/Workbench I/O (rejected: couples us to possibly-
buggy tools and, indirectly, to withdrawn methods); implement straight from
DIN 3960 (rejected: withdrawn).

**Consequences:** The tool is standards-defensible and decoupled from third-party
tool bugs. Small, documented deviations from STplus/Workbench output are acceptable
and expected. See [[reimpl-from-method-not-io]] and the memory references for the
exact formula chains.

---

## ADR-012 — Native involute geometry incl. tool-generated tip chamfer

**Status:** Accepted (2026-06-17)

**Context:** STplus geometry must be reproduced natively and **exactly**, variable
in the inputs (not fitted to I/O). The transverse contact ratio ε_α depends on the
tip chamfer (Kopfkantenbruch) h_K, which STplus generates from the tool edge-break
angle; ISO 21771 treats h_K as a *given* radial modification (eq. 127) and gives no
closed form for it from the tool.

**Decision:** Implement the geometry chain per ISO 21771 (involute, α_wt, form
circles, ε_α/ε_β/ε_γ, tooth thickness) and DIN 21773 (span W_k). Compute the tip
chamfer by **rack-tool generation** (`app/services/geometry/generation.py`): the
tip form circle d_Fa is the **intersection of the usable involute and the edge-break
(Kantenbruch) involute** (base d·cos α_tK), solved by iteration; h_K = (d_a − d_Fa)/2;
the generation profile shift x_E uses the tooth-thickness allowance (A_We/cos α_n).
This is pure involute geometry built from ISO 21771 primitives — cross-checked
against the historical DIN 3960 §A.3.1 worked form (understanding only, per ADR-011).
Validated exactly against STplus (kst-E): x_E, d_Ff, d_Fa, h_K, s_aK, ε_α, W_k.

**Alternatives:** Accept only a directly-given h_K (rejected: not variable for
tool-chamfered gears); defer the chamfer (rejected: ε_α off by ~8 %).

**Consequences:** ε_α and the usable tip circle d_Na are exact; the same generation
layer yields the root form circle d_Ff, feeding the tooth-root capacity work.
See [[iso21771-geometry-formulas]], [[tool-generation-kantenbruch]].

**Amendment (2026-07-07 — per-gear tools + micro-geometry in the FE contour, user
feedback round v0.8, points 5/6):**
1. **One tool reference profile per gear** in the free-parameter path: `StageParams`
   gains `tool_*_gear2` override fields (None → same as gear 1), matching the .ste
   ground truth (kst-E: h_aP0* 1.1/1.25, ρ_aP0* 0.2/0.2, and the 45° Kantenbrechwinkel
   exists ONLY on the wheel tool → h_K = 0/0.117 mm). The .ste importer fills both
   tools; the Geometrie tab renders the tool rows per gear; the Stufenvariation
   "Übernehmen" writes h_fP*/ρ_fP* per gear.
2. **Kopfrücknahme C_αa enters the FE contour** (like the FVA transient FEM):
   `ToothProfile` accepts `(C_αa, d_Ca)` and applies the relief inside
   `_involute_half_angle` as an angular reduction δ/(r·cos α_y) with a linear ramp from
   d_Ca (default d_Na − m_n) to d_Na — every consumer (contour preview, mesher
   reprojection, deck assembly, collision alignment) inherits the SAME modified
   boundary. Values come from the Flankenmodifikation editor via
   `StageParams.tip_relief()` (symmetric flanks only; asymmetric per-flank relief needs
   the per-flank mesher extension and stays carried). Gear 1's "chamfer look" was a
   misreading: it has a Kopfrücknahme, no chamfer — now guarded by verifier checks
   (gear 1 d_Na = d_a, gear 2 h_K = 0.117 mm, flank sets end at d_Na, tip pull-back
   ≈ C_αa/cos α).

---

## ADR-013 — Plastic-capable Stufenvariation and its performance strategy

**Status:** Accepted (2026-06-17)

**Context:** Macro-geometry pre-design — the analytical step *before* the FE rolling
model — needs a parameter sweep (Stufenvariation) over the geometry with capacity
results (S_H/S_F per gear, ε_γ, …). The FVA-Workbench Stufenvariation only supports
**DIN 3990 (steel)** and fails as soon as a **plastic** gear is involved — a real
gap since this project's gear is a steel-plastic pair. The Workbench is also very
slow at high variable counts, and it locks the run when a non-essential input is
missing.

**Decision:** Build a native, **plastic-capable** Stufenvariation with capacity via
**DIN 3990 (steel)** and **VDI 2736 (plastic)**. Performance is layered:
1. **Vectorized batch evaluation (numpy)** — all variants as arrays; the two
   iterative steps (inv α_wt, d_Fa) as fixed-iteration vectorized Newton; ~100–1000×
   over a per-variant Python loop (the Workbench's bottleneck).
2. **Early validity pruning** — discard geometrically invalid variants (undercut,
   ε_γ<1, near-pointed tip, interference, tip clearance) *before* the costly capacity.
3. **Smart sampling (Sobol / Latin-Hypercube)** — for high-dimensional spaces where
   the full grid (∏ steps) explodes (e.g. 10 vars × 10 steps = 10¹⁰).
4. **Multi-objective optimization (Pareto, e.g. NSGA-II)** — find good macro-
   geometries directly (max S_F/S_H, min weight/sliding, ε_γ ≥ target) instead of scanning.
5. **Parallelism** — numpy/BLAS threads; chunked multiprocessing; later distributed
   across the HA nodes.
**Graceful degradation:** a missing non-essential parameter (e.g. a wear coefficient)
yields a *warning* and skips only that sub-result; the sweep keeps running, unlocked.

**Alternatives:** Per-variant evaluation through the scalar pydantic models
(rejected: too slow at scale); exhaustive grid only (rejected: infeasible for many
DOF); DIN-3990-only like the Workbench (rejected: the plastic gap is the point).

**Consequences:** A fast, plastic-capable design-exploration tool that beats the
Workbench on capability *and* speed. The vectorized kernel is validated against the
scalar models; capacity is validated against kst-E (DIN 3990) and the VDI 2736
Workbench report (with the ADR-011 caveat that the reference may itself deviate).
numpy becomes a core dependency (kept in sync across the three dependency files).

**Outlook — material pairings (the key plastic advantage):** the Stufenvariation must
support **steel–steel, plastic–plastic and steel–plastic** pairs. Approach: a **per-gear
capacity-method dispatch**. The meshing layer (geometry, load, and the *mutual* factors
— the elasticity factor Z_E combines *both* materials' E/ν, plus the contact ratio and
load distribution) is shared and computed once per variant (vectorized); then **each
gear's** flank/root capacity is dispatched by its own material kind — steel → ISO 6336,
plastic → VDI 2736. So steel–steel = both ISO 6336, plastic–plastic = both VDI 2736,
steel–plastic = ISO 6336 for the steel gear + VDI 2736 for the plastic gear over the
shared mesh. Vectorized: a material-kind mask routes rows to the ISO-6336 vs VDI-2736
kernel, so all three pairings run in one batched pass.

**Outlook — i18n:** the tool (and its reports) shall be switchable to **English** at a
button press; the domain model already uses English identifiers, and the ISO 6336 (2019)
English terminology is the reference vocabulary.

**Status — implemented (2026-06-17):** `app/services/variation/` — `kernel.py` (the
vectorized batch: macro-geometry, tip-load Y_Fa/Y_Sa, capacity, validity pruning;
reproduces the scalar models bit-for-bit, validated against kst-E) and `sweep.py`
(grid + Sobol/LHS sampling, per-gear material dispatch, Pareto front, graceful
warnings). Measured: a **5-DOF grid of 98 000 variants in ~165 ms (~6·10⁵ variants/s)**
on one core — the performance argument for the thesis. Layers ① (vectorized batch),
② (pruning), ③ (Sobol/LHS) and ④ (Pareto) are in; layer ⑤ (multiprocessing/distributed)
and a full NSGA-II evolutionary search remain an outlook.

---

## ADR-014 — Native ISO 6336-1 dynamic/load factors (K_v, K_Hα, K_Hβ)

**Status:** Accepted (2026-06-17)

**Context:** After de-circularizing the permissible stresses (ADR-011), the last
fed-in capacity inputs were the dynamic factor **K_v** and the transverse/face load
factors **K_Hα/K_Hβ**. For the Stufenvariation these must be *computed*, and — unlike
the Workbench, whose DIN-3990 dynamics path is steel-only — they must work for a
**plastic** gear too. The validation references report only the *result* K_v/K_Hα/K_Hβ,
not the gear-accuracy grade or mesh stiffness they used (the spur kst-E even overrides
c_γ), so an exact end-to-end reproduction is impossible — the same situation as the
de-circularized permissible factors.

**Decision:** Implement the ISO 6336-1:2019 factors **natively** in
`capacity/iso6336_dynamics.py`: the mesh stiffness c′/c_γα/c_γβ (§9, with the
**E/E_st material correction** so a soft plastic gear lowers c_γ), the reduced mass
m_red (§6.5.9, solid-disc eq. 30–32), the resonance speed n_E1 / ratio N, **K_v by
Method B** over all running ranges (eq. 13–22), **K_Hα/K_Fα** (§7.6) and **K_Hβ/K_Fβ
by Method C** (eq. 41–44). The accuracy deviations (f_pb, f_fα) and the initial mesh
misalignment F_βx are inputs (the latter from the shaft analysis / RIKOR; K_Hβ
Method B stays deferred to RIKOR). `evaluate_iso6336` gains an optional
`dynamics: DynamicConditions` that overrides the scalar `load` factors.

**Validation (per ADR-011, the norm wins):** the *determinable* components are
locked — C_B = 0.95 (= the reference's own value), c_γα ≈ 17.21, m_red ≈ 0.0074 kg/mm,
n_E1 ≈ 18 420 min⁻¹, N ≈ 0.163 (sub-critical) for the helical example; the assembled
K_v ≈ 1.034 (ref. 1.05) and K_Hα ≈ 1.143 (ref. 1.18) land in the reference band, the
residual being the unreported accuracy grade + the DIN-3990-vs-ISO-6336 method
difference. The plastic-pair behaviour is physical: a soft gear (E 8000 vs 206000)
drops c_γα ~13× and raises N and K_v.

**Alternatives:** Keep K_v/K_Hα/K_Hβ as fed inputs (rejected: blocks a native
Stufenvariation and reintroduces a hidden circularity); Method A (numeric, rejected:
needs an FE/MKS dynamic model — out of scope for the analytical pre-design);
K_Hβ Method C with a built-in shaft model (deferred: that is RIKOR's job, FVA 30).

**Consequences:** S_H/S_F now fall out of geometry + operating data end-to-end. The
dynamics kernel is plastic-capable and feeds straight into the vectorized
Stufenvariation (ADR-013). Exact-match validation is explicitly **not** claimed for
K_v/K_Hα (documented in code and tests); the formula correctness is asserted on the
locked components and the reference band.

---

## ADR-015 — Native VDI 2736 plastic-gear capacity

**Status:** Accepted (2026-06-17)

**Context:** The thesis gear is a **steel–plastic** pair; ISO 6336 covers the steel
gear but not the thermoplastic one, whose limits depend on **tooth temperature** and
which also fails by **wear** and excessive **deformation**, not only pitting/bending.
VDI 2736 Blatt 2 (2014) is the current method for plastic cylindrical gears.

**Decision:** Implement VDI 2736 Blatt 2 natively in `capacity/vdi2736.py`: tooth-root
stress σ_F with the **tip-load** form factors Y_Fa/Y_Sa (eq. 10; added to
`geometry.tooth_root` as `form_factor_tip`/`stress_correction_factor_tip`, a load point
at d_a sharing the validated 30°-tangent machinery), flank stress σ_H (eq. 15-17, the
same Z_E/Z_H/Z_ε form as ISO 6336, reused), the Wimmer loss factor H_V (eq. 8), the
local **tooth temperature** ϑ_Fla/ϑ_Fuß (eq. 9), the **wear** W_m (eq. 19, with the
active-flank length l_Fl from the path of contact) and the **deformation** λ (eq. 22).
The temperature- and cycle-dependent strength σ_Flim/σ_Hlim (Table 5) is read from the
material via a bilinear (temperature × log₁₀ cycles) lookup, falling back gracefully to
the constant endurance limit (ADR-013). The steel gear of a pair stays on ISO 6336; the
plastic gear uses this module (the per-gear material dispatch of ADR-013).

**Validation (the reference is the kst-E pair = the VDI-2736 Workbench report; all
inputs known → near-exact):** σ_H 79.92 (ref 79.893), σ_F 77.78 (ref 77.896), ϑ 107.77 °C
(ref 107.767), W_m 40.16 µm (ref 40.151), λ 0.0378 mm (ref 0.038), H_V 0.0626, l_Fl
1.349/1.330 mm, and the pinion tip form factors Y_Fa 2.694 (ref 2.693) / Y_Sa 1.759
(ref 1.759). **Known Workbench inconsistency (ADR-011, the norm wins):** the report's
displayed *wheel* Y_Fa = 2.024 contradicts its own σ_F = 77.896 (which needs Y_Fa ≈
2.21); the native Y_Fa = 2.211 reproduces the σ_F. Same pattern as the helical Y_F bug.

**Alternatives:** ISO 6336 with reduced plastic limits (rejected: ignores temperature,
wear and deformation — the plastic failure modes); the Workbench (rejected: the
Stufenvariation cannot run with a plastic gear, ADR-013).

**Consequences:** the plastic side of the steel–plastic pair is now covered with a
near-exactly validated method, completing the analytical capacity (steel = ISO 6336,
plastic = VDI 2736) ahead of the Stufenvariation and the FE rolling model.

**Addendum (2026-06-18) — static peak load (VDI 2736 §3.3):** added the static
overload check `permissible_peak_stress`: σ_F,P = σ_F0·K_A,stat (the nominal root
stress scaled by the static overload factor F_zmax/F_t, eq. 23) must stay below the
**yield-based** permissible 2·σ_S/S_Smin (eq. 24; σ_S = yield strength R_p0.2 at the
operating temperature, S_Smin ≈ 1.5). Opt-in via `static_overload_factor` and the
material `yield_strength_mpa`; reported as `peak_root_stress_mpa`/`peak_root_safety`
(left None when not configured, ADR-013). The yield strength is the `R_p0,2` of the
Workbench *Werkstoff* tab. This is the bending peak check only; other tabs
(*Zusatzberechnungen*, micropitting/scuffing) remain open.

---

## ADR-016 — Native ISO 1328-1 accuracy-grade tolerances

**Status:** Accepted (2026-06-18)

**Context:** Until now the gear-accuracy deviations the dynamics needs (f_pb, f_fα)
and the manufacturing part of the face load factor (F_β) were **raw µm inputs**.
Engineers think in a **quality grade** (e.g. ISO 1328 class 6), and the geometry layer
only range-checked accuracy (`check_validity`) — it never *computed* the tolerances.
This was the one real remaining gap on the capacity side (the "A1" item).

**Decision:** Implement the current inspection standard **DIN ISO 1328-1:2018** natively
in `geometry/tolerances.py`: the flank class A (1…11) → single/total pitch (f_ptT, F_pT),
profile slope/form/total (f_HαT, f_fαT, F_αT) and helix slope/form/total (f_HβT, f_fβT,
F_βT) via eq. 5–12, with the (√2)^(A−5) grade step (§5.2.2, from the unrounded class-5
value), the §5.2.3 rounding (>10→1, 5…10→0.5, <5→0.1 µm) and the totals from the
**unrounded** slope/form components (eq. 9/12). `dynamics_deviations(grade, m_n, d)`
returns (f_pb=f_ptT, f_fα=f_fαT); `validity_warnings` enforces the §1 application ranges.
`/api/capacity` gains an optional `accuracy_grade` that derives the deviations from the
grade (else the raw µm inputs stand), and a `/api/tolerances` endpoint exposes the table.

**Validation (the formulas are read visually from §5.2.4 → the code *is* the standard):**
hand-verified for m_n=2, d=100, b=20, class 5 — f_ptT 6.0, F_pT 19, f_HαT 4.8, f_fαT 6.0,
F_αT 8.0, f_HβT 6.0, f_fβT 6.5, F_βT 9.0 µm; class 6 = class-5 unrounded × √2 → 8.5; the
rounding bands and the §1 range warnings are covered (`tests/test_tolerances.py`). Driving
the dynamics by grade is physical (K_v rises with a coarser class).

**Scope / not yet:** the ISO 1328-2 double-flank composite (master-gear QC, peripheral)
and the **tooth-thickness / centre-distance allowances** (A_We/A_Wi per DIN 3967,
A_Ae/A_Ai per DIN 3964) are deferred — those standards are not in the repo and the
allowances arrive as `.ste` inputs today. DIN 21773 span W_k already lives in `gear.py`.

**Consequences:** users specify a quality grade instead of raw µm; the accuracy feeds
the native dynamics and (later) the face load factor consistently — closing the last
analytical-capacity gap before RIKOR.

---

## ADR-017 — FE rolling-model mesh: ρ_F-arc root, transfinite tooth, all-quad body fan

**Status:** Accepted (2026-06-24)

**Context:** The first FE rolling deck (Step 3) was structurally right but the mesh was wrong
versus the reference ANSA mesh (`32_Abaqus/implicit/…_ohne_Radkoerper.inp`): the tooth root came
out **inverted/pinched** ("Pokal" shape), the rim was a thin band, and the body lacked the
reference's coarsening transition. Root cause (verified numerically on kst-E): `tooth_form.
root_fillet_points` produced a **non-monotonic, branch-mixed trochoid** whose half-angle did not
even meet the involute at d_Ff (2.75° vs 2.25°); `_monotone_fillet` only masked the dip.

**Decision:**
1. **Geometry — clean boundary.** New `tooth_form.transverse_right_boundary`: the root fillet is the
   **circular arc of radius ρ_F** (validated DIN 3990 / ISO 6336-3 value from `tooth_root.py`)
   **tangent to the involute flank** (true d_Ff by bisection) **and to the root circle d_f**. The
   half-angle is monotone non-increasing root→tip (rounded root, no pinch). Regression test guards it.
2. **Mesher — transfinite from the clean boundary.** Feed the clean boundary into the structured
   **transfinite `mapped_mesher`** (not a pure radius-arc Coons tooth: that hit Jacobi ≈ 0.13 at the
   fillet tangent). Result: rounded root, deep rim to the real bore, **Jacobi-Güte ≥ 0.9**. A
   native radius-arc mesher (`structured_mesher.py`) is kept as a fallback.
3. **Surface boundary layer.** Thickness curves graded with a gmsh "Bump" (`flank_bias`) so the
   contact/root surface layer is finer than the interior; the rim is radially graded fine→coarse.
4. **Winding.** `_extract_2d_quality` normalises every quad to CCW so the face-width sweep yields
   positively-oriented C3D8 hexahedra (Abaqus rejects negative Jacobians).
5. **Body fan — all-quad 2:1 template.** The reference's circumferential coarsening (fine surface →
   coarse body) must be **pure hexahedra**. gmsh recombine cannot do conformal all-quad coarsening
   here (Blossom → triangles; full-quad → "cannot divide by 2"). A hand-built **conformal all-quad
   4→2 transition template** (6 quads, 3 interior nodes, near-rectangular) was designed and validated
   standalone (conformal, |Jacobi| = 1.0). Integration into the annular body is the next step.

**Validation:** kst-E both gears — boundary half-angle monotone, root widest, within the half pitch,
C0 at the stitch; transfinite sector Jacobi 0.90–0.95; the 4→2 template 16→8→4→2 all-quad,
conformal, |Jacobi| 1.0 (`80_output/coarsen_template_check.png`).

**Consequences:** the tooth/root mesh (the stress-critical region and the thesis target) is now
reference-grade; the body fan lands via the validated template, then the deck conventions/BCs
(Workstream C) follow. The trochoid (`root_fillet_points`) remains for a later high-fidelity option.

**Update (2026-06-24):** the 4→2 template is integrated into the annular body
(`structured_mesher.body_section_2d` = tooth interface → compact coarsening bands → graded ring) with
Laplacian smoothing. BUT a uniform 4→2 fan at d_f is a **hard break in the tooth-root region** — the
reference instead **continues the fine structure as a dome/ellipse under the tooth and runs it out
only outside the root** (ANSA O-grid paving). The body target is therefore the **O-grid dome**, not
the d_f fan. This is body geometry only: by Saint-Venant it does not change the (already
reference-grade) tooth-root stress, so it is an efficiency/fidelity refinement, not a results issue.

**Update 2 (2026-06-24) — ground truth + smoothing method:** stopped reverse-engineering the body
topology from screenshots (the real cause of going in circles). The reference `.inp` is the *meshed
ground truth*: parsing one z-slice gives the exact 2D topology (wheel 269 649 nodes, 81 z-levels,
bore 12.38, ~723 quads/pitch; tooth → dome-cap fan → structured rim grid). gmsh is confirmed the
wrong tool for the body — size-field/recombine leaves triangles, subdivision drops quality to 0.10,
full-quad-3 and BoundaryLayer-field both fail, and any unstructured path re-opens the hang risk. The
mesh is built **structured** (transfinite tooth + all-quad coarsening + ring) and the irregular
dome-cap fan nodes are lifted with **optimization-based (quality-greedy) smoothing**
(`_optimize_smooth`: per node, maximise the min scaled Jacobian of incident quads — Laplacian cannot,
it inverts them). `assemble_pitch_2d` merges tooth+body and smooths with only the outer contour held.
Validated by overlaying the generated pitch on the parsed reference slice. The ANSA batch-mesh recipe
is not available (maybe later); the topology is reverse-engineered from the `.inp`.
See memory `reference-mesh-ground-truth`.

**Update 3 (2026-06-24) — body = root boundary layer, reference parity exceeded:** analysing the
reference slice showed *why* it is meshed this way — the dense concentric arcs hugging the fillet are
a **root boundary layer**: the tooth-root fillet is the max bending-stress site (the thesis quantity),
so fine surface-aligned elements (arcs ∥ surface, spokes ⟂) resolve the steep notch gradient, then
run out into a coarse rim where stress has decayed (Saint-Venant). The reference is fully structured
(all interior nodes valence 4; its only 6 sub-0.35 cells are at the tooth *tip*, min 0.243). Two
changes made the generated body reach/exceed this: (1) build the body as that boundary layer (fine
ring arcs at d_f → graded reduction → rim) rather than a hard fan; (2) make `_optimize_smooth`
**lexicographic** — maximise the worst incident scaled Jacobian, then the mean; the mean tie-breaker
unlocks the plateau pure-min/greedy got stuck at (0.139). Result on the kst-E wheel pitch: all-quad,
**min Jacobian 0.736, 0 cells < 0.35**, exceeding the reference (0.243 / 6) with a reference-like
structure. Winning params: tooth thickness 30, body bore_columns 8, cap_rows 5, rim_rows 18,
band_aspect 1.1, opt_iters 120. Sector + extrude next.

---

## ADR-018: Block-structured FVA/STIRAK gear mesh on a fixed scaffold (MESHING_SPEC.md)

**Status:** superseded by ADR-019 (2026-07-03) — the mined reference topology has no distributed
2:1 template band; the scaffold utilities live on. Originally: accepted (2026-06-25) · supersedes the body-mesh construction of ADR-017 for the
reference reproduction.

**Context:** the optimizer-finished boundary-layer body (ADR-017) hit det(J) 0.74 but its *element
distribution* still differed from the FVA reference — the reference is a true **block-structured
multiblock** (C-form fillet band, transfinite core, fine→coarse templates only in the load-far body),
which a paving/relax approach cannot reproduce. A binding spec (`MESHING_SPEC.md`) + a proven scaffold
(`gear_mesh_scaffold.py`, both under `30_references_and_examples/36_Claude_Chat_Vorschlag/`) were
provided.

**Decision:** adopt the scaffold pipeline **verbatim and unchanged** (TFI/Coons blocks, a shared-node
`NodeRegistry` enforcing conformity *by construction* — no tolerance merge, no paving/advancing-front/
gmsh) and build the gear blocks on top: B3 fillet band (n_fuss over the rounding, densified to the
30°-tangent via curve seeding — not offset marching), B4 core, B1 rim, B2 fine→coarse 2:1 quad
templates placed **deep** in the load-far body, sector = **4 teeth + 2 toothless segments**. The 2:1
valence-3 nodes are lifted by a **section-11 node-relocation finish**: optimization-based
(lexicographic worst-element-first), **frozen connectivity**, boundary/feature/cut nodes (incl. the
30°-point) held fixed so periodicity is preserved. This lives in `app/services/model/block_mesh.py`.

**Evidence (kst-E):** registry conformity asserted (no merge); B3|B4 share the d_Ff edge; coarse
sector periodic to 5e-15 mm; B2 deep 2:1 template det(J)min 0.21 → **0.66 after the finish, 0 cells
< 0.35, 0 inverted**, connectivity frozen. Parameters are the four FVA integers
(n_flanke, n_fuss, n_dicke, n_breite); quality is won in n_fuss + n_dicke, not the flank.

**Consequences:** the previous `structured_mesher` boundary-layer path (ADR-017) is kept but no longer
the reference route. Remaining: integrate B2 reduction + finish into the full sector with the
periodicity re-assert, refine n_fuss ≥ 6, compute G, the root-stress convergence study (30°-tangent +
max GEH), then wire the deck (materials/BCs/torque/periodicity MPC). Element type **C3D8I** (not C3D8R)
in the root.

---

## ADR-019: Reference-topology transplant mesher (mined ground truth, canonical symmetry, chord density, quick FE, fillet strategies)

**Status:** accepted (2026-07-03) · supersedes ADR-018's B2 2:1-template construction for the
reference route; the scaffold utilities (`NodeRegistry`, TFI helpers, §11 `optimize_finish`,
`extrude`, `write_inp`) remain in use.

**Context:** definitive parsing of the reference deck (committed miner, not scratchpad) showed the
ANSA/FVA mesh concentrates the whole fine→coarse reduction in **exactly one fan-convergence node
per tooth gap** on the rim-top ring (valence 6 mid-sector, 5 at the sector edges) — all other
interior nodes are valence 4. There is no distributed 4→2 template band; ADR-018's approach could
therefore never reproduce the reference element distribution. A parser trap masked this earlier:
rim hexes carry a different local axis orientation, so slice faces must be re-ordered cyclically
around their centroid or bowtie quads corrupt every valence measurement.

**Decision:**
1. **Mine, don't model** (`model/reference_slice.py`): parse the wheel part, slice the mid
   z-plane, measure (pin-tested: 3024 quads / 3329 nodes, interior valences {4: 2716, 5: 2, 6: 3},
   rim 26×25, min scaled Jacobian 0.243 with 24 sub-0.35 tip cells) and export the sector as a
   committed JSON **topology template** (`model/data/reference_sector_rad_vz_1.json`).
2. **Topology transplant** (`model/template_mesher.py`): re-use the reference connectivity
   verbatim; derive node positions from the target geometry — angular pitch scaling about the
   sector bisector, piecewise radial feature map (bore → fan ring → actual contour bottom → tip
   circle d_a incl. the ISO 21771 §7.6 edge-break chamfer, now emitted by
   `tooth_form.transverse_right_boundary(to_tip_circle=True)`), and exact foot-point projection
   of tooth-zone surface nodes onto the analytic contour. A **selective** §11 finish lifts only
   the sub-0.4 tip-cap cells. Result (kst-E wheel): topology-identical to the reference,
   min scaled Jacobian 0.45 with **0 cells < 0.35** (reference: 0.243 / 24).
3. **Canonical symmetry** (user requirement): orbit decomposition under the sector symmetry group
   (rotations × bisector reflection, bijective per-orbit transform assignment, self-mirror orbits
   projected onto their half-pitch axis). Teeth are **exactly rotation-congruent** (≤ 1e-14 mm);
   in-tooth mirror symmetry is applied only when `ToothProfile.is_flank_symmetric()` — DIN 867
   §4.2 backs the symmetric default, per-flank parameters stay an extension point.
4. **Parametric density** (`model/refine.py`): conformal chord splits (opposite-edge bands) with
   separate root/flank factors seeded from radius-banded tooth-zone surface edges — valences,
   the fan signature and tooth congruence survive every level.
5. **Native quick FE** (`model/plane_fe.py`): vectorized plane-strain Q4 solver (sparse, < 0.1 s)
   for root/flank **density-convergence checks** (separate searches by design) and fillet
   ranking; load = tip point force, criterion = max tensile stress along the whole fillet.
6. **Optimized root fillets** (`geometry/root_fillet.py`, thesis add-on): `EllipticFillet`
   (Kassem), `BezierFillet` (Roth/Voith, one factor), `BionicFillet` (tension-triangle form),
   pluggable into the mesher via the projection contour; mandatory `mating_tip_clearance`
   check and a DIN 3960 eq. 3.6.06 undercut warning. Quick-FE on kst-E: ellipse −9.9 %,
   Bézier −22.1 % root stress vs the standard ρ_F arc, gates intact.

**Evidence:** 159 tests green (topology pins, quality gates, exact congruence/mirror symmetry,
refinement invariants, fillet tangency/clearance/stress ranking); checkpoint plots under
`40_backend/80_output/cp2_*.png`; user-reviewed at checkpoints 1 and 2.

**Consequences:** `mapped_mesher` remains only as the legacy deck path until the deck is rewired
(next step: extrusion + FVA set contract + rigid-shell steel side in mixed pairings). The
convergence quick check confirms the mined reference density is already converged for the root
stress (Δ < 0.1 %), matching the FVA "Konvergenz Fuß" preset. Fillet-shape parameters become
Stufenvariation axes with the quick solver as objective.

**Amendment (2026-07-07 — third chord group + effective counts, user point 7, round v0.8):**
`refine_thickness` ("Elemente über Zahndicke") completes the FVA mesh-fineness quartet
(root/flank/thickness factors + face-width layers). Its chords are seeded ONLY at the flat
tip-land surface edges — they run tangentially down through the whole tooth; chamfer edges
(d_Na…d_a) are excluded because their chords slice the 45° corner cells into slivers
(measured SJ 0.22 on kst-E gear 2; land-only seeding keeps min SJ ≈ 0.45 at factors 1–3 on
both gears). The mesher meta now reports the EFFECTIVE per-tooth element counts (one gap
rounding, one flank, the tip land — counted on the final mesh) which `/api/mesh/preview`
exposes for the dialog's "effektive Werte"; the deck path carries per-gear
`(root, flank, thickness)` tuples, and the pair view preseeds root/flank per gear from the
native 2D quick convergence.

---

## ADR-020: Next.js workbench frontend (FVA layout language, Geist, static export)

**Status:** accepted (2026-07-03) · user decision at checkpoint review.

**Context:** the Vite SPA's page-per-topic layout does not scale to the tool's real workflows —
"in einzelnen Fenstern alles gut einstellen" like the FVA Workbench (model tree, tabbed attribute
editors, quick results, 3D view), but visually modern, clean and condensed.

**Decision:** rebuild the frontend as a **Next.js** app (App Router, TypeScript, Tailwind v4)
under `20_code/50_frontend_v2/` with the **Geist** font (self-hosted via `next/font`), following
the FVA-Workbench layout language: model tree (Getriebe → Stufe → Ritzel/Rad → Berechnungen) on
the left, condensed attribute-table editors in the centre, a bottom messages strip, and a dark
ANSA-like three.js viewport for the FE mesh. `output: 'export'` keeps ADR-006 intact — FastAPI
serves the static bundle same-origin (`app/static`, gitignored; the API base stays empty, an
explicit `NEXT_PUBLIC_API_BASE_URL` in the shared `20_code/.env` is dev-only). i18n keys
(DE default, EN complete) from day one with a header language switch.

**Consequences:** the legacy Vite app in `50_frontend/` stays untouched until the remaining
views (Tragfähigkeit, Dynamik, Übersicht details) are ported; the swap (delete Vite app, rename
`50_frontend_v2` → `50_frontend`, update project_rules' directory map and the Docker build) is
its own reviewed commit. New panels shipped now: Übersicht, Geometrie, Zahnform (real as-cut
contour + fillet strategies + clearance), FE-Mesh (density, 3D hull viewer with Jacobian heatmap,
convergence quick check, fillet ranking, deck download incl. rigid-shell rule), Stufenvariation
(parallel coordinates, Pareto, variants table + up-to-4 real-contour overlay comparison).

**Amendment (2026-07-07 — viewport parity, user feedback round v0.8, points 1–3):**
1. **Pair positioning comes from the backend** (`POST /api/mesh/pair`): the endpoint runs the
   deck builders' own `assemble_centered_pair` (fillets, tip relief, rigid R3D4 shells,
   backlash-closing rotation, sweep contact pairing) and returns the outer hulls in absolute
   assembly coordinates plus the per-gear angle law of the roll (edge start + kinematic
   coupling). The viewport-local positioning math (half-pitch heuristic, no closing rotation)
   is deleted — what the viewer shows IS the .inp; the roll slider walks the deck's real
   Wälzstellungen (position k/n, measurement points marked).
2. **Orthographic camera + CATIA mouse controls** in both three.js viewports (shared
   `CatiaControls`): MMB drag = pan, MMB+LMB/RMB = quaternion free-tumble (full 360°, no
   polar clamp), wheel = orthographic zoom; middle-click autoscroll suppressed. Rigid-shell
   gears render as semi-transparent open mantles (the missing end faces are deliberate).
3. **One deck payload builder + store SSOT** (`lib/deck.ts`): every deck consumer — the
   Dyn-Abwälzen tab action, the pair-view assembly preview and the deck/series download —
   builds its request through `deckPayload()`, so identical settings give byte-identical
   decks. The PairPanel's panel-local state (layers, fineness, fillets, offsets,
   rigid-shell, roll positions) moved into `fem.*`; the tab and the pair view edit the
   same values.
4. **Resizable panes + no clipping** (`components/SplitPane.tsx`): the tree, the
   Ergebnis-Schnellansicht and the viewport panels get a draggable divider clamped at a
   content min-width (user: "verschieben, aber ein Block, dass man nicht mehr
   verkleinern kann"); `Section`/QuickView wrappers use `overflow-x-auto` (scroll, never
   cut); numeric fineness selects use a narrow variant so per-gear column pairs fit.

---

## ADR-021: Deck gear numbering follows the stage input order; mid-plane-centred extrusion with parametric axial offsets

**Status:** accepted (2026-07-04) · user decision after reviewing the generated pair.

**Context:** the generated implicit deck had inherited the FVA reference deck's gear numbering,
where `Part_Rad_Vz_1` is the **plastic wheel** (z=52) and `Part_Rad_Vz_2` the **steel pinion**
(z=51) — verified directly against the reference deck's material cards (Vz_1 = Marlow
hyperelastic, Vz_2 = E 210000) and tip diameters. That is the reverse of the .ste input order
(pinion first), which is what a user naturally expects when postprocessing. Additionally both
gears were extruded from z = 0 with a single shared face width, so the 15/17 mm kst-E pair sat
flush on one side (2 mm overhang on the other) and the rotation nodes lay on a side face —
while the reference deck centres both parts about z = 0 with their own widths.

**Decision:**
1. **Numbering = stage input order:** gear 1 = the stage's first gear (kst-E: steel pinion
   z=51), gear 2 = the second (plastic wheel z=52) — across `build_implicit_pair_from_stage`,
   the `G{g}T{nnn}F{f}`/`TOOTH-{g}-…` sets, `Rot_Node_Rad{g}` and `Fesselung_Rad{g}`. The
   physical load case stays reference-faithful (wheel at the origin, angle-driven via
   AMP-ANGLE; pinion at the centre distance carrying the resisting torque via AMP-TORQUE;
   plastic side = contact slave), and a comment table in the deck heading documents z, b,
   material, axis position, mid-plane and role per gear — including the note that the FVA
   deck numbers the other way around.
2. **Torque semantics:** the API keeps the user-facing `wheel_torque_nmm` (M₂) and converts it
   to the applied pinion torque T₁ = M₂·z₁/z₂ (static pair equilibrium).
3. **Mid-plane extrusion + axial offsets:** each gear keeps its own face width and is extruded
   symmetric about its mid-plane (z = ±b/2, reference parity), so unequal-width gears roll
   centred by default; `axial_offset_(pinion|wheel)_mm` displaces each gear parametrically
   along its rotation axis, and each rotation node sits at its gear's mid-plane (z = offset),
   not on a side face. The single-gear `/api/mesh/3d` hull is centred the same way.
4. **Material matrix in the deck:** `DeckRequest` gains `pinion_material`/`wheel_material`
   (steel/plastic); the rigid-shell rule resolves to whichever side is steel in a mixed
   pairing, and the contact slave to the plastic side.

**Consequences:** decks generated from here on are **not name-compatible** with the FVA
reference deck's gear indices — postprocessing that reads G1/G2 sets must use the mapping in
the deck header (plastic stress sets are now G2 for kst-E). The frozen-reference comparison
path is unaffected (the reference .inp itself is untouched). Frontend pair view mirrors the
convention (wheel triad = driven/green, pinion triad = torque/amber, offsets in the panel).

**Amendment (2026-07-04, same review cycle — user decision):**
1. **Rig-view slot layout:** the assembly follows the Kleingetriebeprüfstand top view — gear 1
   (the stage's FIRST gear) at the origin, on the LEFT of the default 3D pair view; gear 2 at
   the working centre distance, on the RIGHT. Every per-gear input (material, face width,
   axial offset, fillet) is keyed by input slot through the whole chain and never re-ordered
   by role or tooth count (gear 1 may well be the larger "wheel"); Ritzel/Rad remain display
   labels. The angle/torque/slave ROLES follow the material (plastic side angle-driven +
   contact slave, reference parity), independent of the slot. Deck request fields renamed to
   slot names (`gear1_material`, `axial_offset_gear1_mm`, `fillet_gear1`, …;
   `torque_gear2_nmm` = M₂, the torque level expressed at gear 2, converted to the loaded
   gear via T_g = M₂·z_g/z₂).
2. **Fesselung parity:** `Fesselung_Rad{g}` ties the bore surface AND both radial sector cut
   faces (bore → shoulder contour, all layers) — matching the reference deck's set, which was
   verified to hold the full bore arc plus two complete radial node chains up to the root
   circle. Closes the parity gap noted in the original consequences.

**Second amendment (2026-07-04, evening review — measured ground truth + user report):**
1. **Fesselung is a node predicate, not an edge subset.** Parsing the reference deck
   (`kst-E_8_DY2-0_WS30_ohne_Radkoerper.inp`) shows `Fesselung_Rad{1,2}` = the bore surface
   (full sector arc × all face-width planes) plus BOTH radial cut planes as **complete
   cross-sections — every single node** of those faces from the bore to the root circle
   (2 268 / 2 225 nodes per cut plane; no z side faces, no rim volume beyond them).
   `mesh_sets.tag_gear_reference` therefore selects the Fesselung by a coordinate predicate
   over ALL mesh nodes instead of traversing boundary edges (which can miss face nodes), and
   exposes the FVA checkboxes as writer flags: `fasten_bore` / `fasten_cuts` (defaults, the
   reference) plus `fasten_bottom` / `fasten_top` (axial end faces, off in the reference).
2. **Initial contact alignment (single-flank, reference parity).** The reference gears stand
   in single-flank contact at t=0 (~25 µm node gap along the whole contact line on the −y
   flank); AMP-TORQUE switches on first while AMP-ANGLE dwells, so the torque ramp closes the
   last micrometres. The previous half-pitch-only placement left the tooth centred in the gap
   with the full allowance backlash split onto both flanks (~0.24 mm per side for kst-E) —
   the gears "ran in the air". `build_implicit_pair_from_stage(align_contact=True)` now
   computes the backlash-closing rotation of gear 2 by exact rotational collision detection
   on the 2-D boundary polylines (same-radius angular-gap minimisation, 15 µm arc backoff)
   and documents the applied angle in the deck heading. Verified end-to-end by
   `10_verifiers/verify_deck_parity.py` (Fesselung composition, ≤35 µm single-flank gap on
   −y, torque-before-angle amplitudes, flank-wise contact pairs; `--reference` re-measures
   the FVA deck).

**Third amendment (2026-07-06 — load-case redesign, user feedback round):**
1. **Per-position torque cycle** (user requirement, matches the reference deck's
   −78.5/−7846.2 alternation): the angle side is HELD per Wälzstellung; the torque side
   ramps base→full (SMOOTH STEP), holds at full (measurement at the END of the hold —
   Newton equilibrium each increment plus STABILIZE-energy decay), ramps back to the
   base fraction (default 1 % of the powerflow torque; first ramp from 0), then the
   angle sub-ramps to the next position at base torque. `*STATIC` gains
   `ALLSDTOL=0.0, CONTINUE=NO`; `*RESTART, WRITE`; measurement frames via
   `*TIME POINTS, NAME=MEASURE` with the reference's per-flank-set output grouping,
   plus a U-only all-increment animation request.
2. **Roll starts at an edge tooth** (`start_at_edge`, default): pre-rotation ±roll/2,
   kinematically coupled — the middle teeth are the evaluation teeth (boundary-free
   full engagement); `roll_pitches` default 3. Contact pairs come from the
   **sweep-union pairing** (centroids rotated through the whole roll) and reproduce
   the reference's 7 pairs exactly.
3. **Position series is the default deck mode** (`POST /api/mesh/deck-series`): one
   independent static INP per Wälzstellung — result-identical because the model is
   path-independent (Marlow hyperelastic + frictionless), robust against convergence
   aborts and parallelisable. Shared mesh via `*INCLUDE, INPUT=pair_common.inp`,
   per-position `*INSTANCE` rotations, `manifest.json` + run scripts. The single
   quasi-static deck stays available ("Referenz/Animation" mode).
4. **Drehrichtung** (`rotation_sense`, from the Leistungsfluss) mirrors roll sign,
   closing flank and start offset consistently.

---

## ADR-022: Own FE postprocessing — neutral JSON dump + backend path-of-contact transform + 3-D viewer

**Status:** accepted (2026-07-07) · user goal of the v0.8 feedback round.

**Context:** the target of the whole rolling pipeline is the user's 3-D result plot — per
contact flank pair, tooth-root/flank stress (and strain, contact pressure) over the
**path-of-contact coordinate × the face width**, sliderable over the Wälzstellungen, with the
range extended beyond A/E for the pre-/post-engagement of the compliant plastic pair. The
frozen FVA script (`31_FVA/abaqus_postprocessing.py`) cannot produce it against our decks: it
reads `REFERENCE_POINT_` node sets and `Geometrieberechnung_E1`/`eingabedaten.fsk` text files
that our decks never emit, couples the measurement frames to a hard-coded `%3` cadence, and
writes an FVA-XML tied to Workbench component IDs. It is a structural template only.

**Decision:** a decoupled three-stage pipeline, each stage owning what it is best placed to:
1. **Own Abaqus-Python script** (`app/services/model/postprocessing/abaqus_fem_postprocessing.py`,
   shipped in the series ZIP and runnable on the single deck) that works against OUR set
   naming (`G{g}T{ttt}F{f}_NODESET`/`_ELEMENTSET`, `Rot_Node_Rad{g}`) and dumps a **neutral
   JSON** (`fem_results.json`, schema `zahnfuss.fem_results/1`): per measurement frame, per
   flank set, per surface node the radius-from-axis, the axial z, the S/E von-Mises &
   principals (averaged from ELEMENT_NODAL like the reference), CPRESS and |U|. Measurement
   frames are auto-detected (a frame is one iff it carries the `S` field — the
   `*TIME POINTS=MEASURE` holds; the U-only animation frames are skipped), and the series
   mode reads `manifest.json` for the per-position roll angles. The script is deliberately
   **geometry-light** — it never re-derives gear data — and stays Abaqus-Python (2.7/3.10)
   compatible (kept out of the py312 ruff/mypy scope as a shipped resource).
2. **Backend transform** (`POST /api/fem/results`, `app/api/fem_results.py`): the r → ξ
   unwrapping onto the line of action is done HERE from THE `GearStage` (single source of
   truth, same quantities as the Zahneingriff plot), never in the script or the client:
   `ξ(r) = ±(sqrt(r² − r_b²) − r_w·sin α_wt)` relative to the pitch point C (gear 1 towards
   E, gear 2 towards A), with the ISO 21771 A/B/C/D/E markers and the extended d_Nf…d_Na
   range (root form circles from the validated tooth-profile chain) as axis annotations.
3. **Client viewer** (`FemResultsPanel` + `FemResultsViewport`, "Ergebnisse (3D)" tab): upload
   the dump (client-side file read like the .ste import) → the endpoint returns
   structure-of-arrays viewer data → three.js renders each flank set as a vertex-colored
   surface (ξ × z × field height/heat), with the A…E markers on the ξ axis, the frame maximum
   flagged, a stable per-tag color scale, a position slider over the Wälzstellungen, and the
   shared orthographic CATIA controls (ADR-020 amendment).

**Alternatives:** run the frozen FVA script (rejected — not runnable on our decks, FVA-XML
output, brittle); do the r→ξ transform in the Abaqus script (rejected — would duplicate the
gear geometry away from the GearStage SSOT and couple the dump to a stage); do it in the
browser (rejected — the geometry belongs on the backend). 

**Consequences:** the dump is stage-agnostic and small (structure-of-arrays, rounded); a run
can be re-viewed against a corrected stage without re-solving. The measurement-frame
auto-detection means the viewer works for BOTH deck modes without a cadence constant. The
extended ξ range shows the deformation-driven pre-/post-engagement the compliant plastic pair
exhibits beyond the theoretical A/E. See [[commit-doc-chain]].

## ADR-023: All seven literature root-fillet approaches native; `FilletSpec(kind, approach)`; CAO as a cached lazy strategy

**Date:** 2026-08-05 · **Status:** Accepted

**Context:** Only the first approach per fillet family was implemented (elliptic = Kassem,
bezier = Roth/Opferkuch, bionic = Voith tension triangle), all hard-anchored at d_Ff. The
supervisor's priority is Frühe's tilted ellipse; the thesis task names all three families.
Every approach had to be implemented from its PRIMARY source (user rule: primary sources or
repo contents only — the Nautos PDFs read fine via pdftotext/pdftoppm although the built-in
reader mislabels them as password-protected).

**Decision:**
1. **Two-level schema** `FilletSpec(kind, approach)` — kind stays the geometry family
   (`standard | trochoid | elliptic | bezier | bionic`), `approach` picks the literature
   method (elliptic: kassem|fruehe|landi, bezier: roth|dong, bionic: voith|cao);
   `approach=None` normalizes to the family default, so every legacy payload keeps its exact
   behaviour (pinned by test). Flat per-approach parameter fields, validated ranges.
2. **Frühe** (`FruheEllipticFillet`): closed-form Eqs. 89–100 of the dissertation (no
   fsolve); G1 at d_Ff AND at the gap centreline; the root diameter is a RESULT of the fit
   (kst-E: 0.35·m_n below d_f). Anchored on the numeric flank tangent, so G1 holds exactly
   for modified flanks. Superellipse exponent not exposed (Frühe: no benefit).
3. **Landi** (`LandiEllipticFillet`): the paper's own 4-unknown fsolve (axis-aligned ellipse,
   pass+tangency at D1 on the involute and at D2 on the root circle) with the normals'
   intersection as start value and multi-start; D1 raisable towards the limit contact
   diameter (`ra_f`), D2 positionable up to the gap centreline (`d2_frac`).
4. **Dong** (`DongToolBezierFillet`) via a NEW generic `rack_tip_envelope(profile, pts,
   tangents)` — closed-form meshing condition per tool-tip sample, the same rolling map as
   `root_fillet_points` (cross-checked: arc input reproduces the trochoid to < 5 µm). The
   degree-4 hob-tip Bézier follows the paper's Eqs. 2–9; default dv1 = 1.0 (gap-centre end)
   instead of the paper example's v1 = 0.35, which is an endpoint-pinning constraint for
   THEIR ρ* = 0.35 hob and yields +12 % σ on the kst-E ρ* = 0.2 tool. The only optimized
   fillet that stays hob-manufacturable (neutral UI note instead of the molded-only warning).
5. **CAO** (`CaoFillet` in `services/model/cao_fillet.py`): direct-method growth
   d_i = s·(σ_i − σ_ref)·n_i, s = d_per/max|d_i|, d_per = 0.025·m_n, σ_ref = stress at the
   junction node which never moves (paper Fig. 6); quick-FE surface stress via the new
   `fillet_surface_stress` (tensile-gap nodes mirrored onto the right-half polyline frame);
   converges on kst-E in 5 iterations (274.9 → 236.2 MPa). Lazy strategy with an in-process
   memo cache (multi-node safe: pure recompute, no storage; project_rules §18);
   `/api/mesh/fillet-cao` exposes the convergence history.
6. **Junction plumbing:** strategies may own their junction (`junction_radius_mm`) — the
   flank continues from there (`ToothProfile.flank_points(r_start_mm=…)`), the quick-FE
   evaluation band follows (`fillet_limit_radius_mm`), and `junction_offset_mm` implements
   the literature's 0.03–0.05 mm interference fallback. Voith tuning was run (γ×b_f grid on
   kst-E): best −3.0 % vs default −3.1 % — defaults kept, the closed tension-triangle form is
   inherently limited here; CAO is the recommended bionic approach.

**Consequences:** `/api/mesh/fillet-compare` ranks eight named rows (`kind-approach`),
`/api/mesh/fillet-sweep` sweeps per (kind, approach, parameter) incl. the previously missing
bionic γ axis, the Stufenvariation carries the FULL FilletSpec (the kind-only forwarding that
silently dropped parameters is fixed), and the contour reports `fillet_approach` +
`effective_root_diameter_mm` (Frühe's deeper root is visible in the UI incl. d_f/d_Ff
reference circles). The measured kst-E ranking lives in `root_fillet_strategies.md`.

## ADR-024: Geometry SSOT report on current norms; native K_Hβ by default

**Date:** 2026-08-05 · **Status:** Accepted

**Context:** The frontend showed only 8 geometry numbers although the reference output
(kst-E .sta Blatt 6–8, legacy DIN 3960/STplus) prints ~80; several quantities were computed
but never serialized, and a whole block (tooth-thickness chords, span with auto tooth
count, ball/roller measures, allowance conversion, backlash, specific sliding) was not
computed at all. User direction: verify the norm supersession chain FIRST (the successors
DIN ISO 21771:2014 + DIN 21773:2014 are in the repo; DIN 3967/3964 remain valid), compute
on current norms only, and provide ONE backend source of truth the frontend reads
everywhere — with the selected root-fillet strategy's influence visible in the output.

**Decision:** `app/services/geometry/report.py::compute_geometry_report` is the SSOT: it
computes the full per-gear + pair value set on DIN ISO 21771 (incl. Annex NB corrected
equations), DIN 21773 §5–§14 (inspection measures; allowances as EXACT measure differences
at the allowance-equivalent generation shift, not linearized factors), DIN 3967 (E_sn =
A_W/cos α_n input route) and DIN 3964 (A_a → Δj). Auto measuring tooth count k per the
classic V-circle rule clamped to the §7.2 k_min/k_max bounds. Fillet-aware: callers pass
the selected strategies' deepest contour radii; the report carries nominal (tool) AND
effective root diameters. Exposed via `POST /api/geometry/report` (FastAPI serializes the
service dataclasses directly); the Geometrie tab renders it as grouped sections and the
HTML report appends the same rows. `/api/capacity` now also returns the previously dropped
K_Fα/K_Fβ/Z_ε/Z_B/Z_D/F_t/v/line-load/z_n and per-gear σ_H0/σ_F0 + the 30°-tangent section
values. **Bugfix:** `face_load_factor = null` now means the NATIVE ISO 6336-1 Method C
K_Hβ/K_Fβ (they were computed and discarded); an explicit number remains an override.

**Consequences:** kst-E parity is pinned by `tests/test_geometry_report.py` (27 transcribed
.sta literals; two documented norm-over-tool deviations: the chordal-measure cylinder
d_a − 2·m_n per DIN 21773 §5, and the as-cut tip thickness at d_Na). Legacy
`/api/geometry` stays untouched for compatibility. Open follow-ups: scuffing per
ISO/TS 6336-20/-21 (primary sources now in the repo, pdftotext-readable), the individual
Z_L/Z_v/Z_R/Z_W/Z_X and Y_δrelT/Y_RrelT/Y_X sub-factors as explicit response fields (they
are currently folded into σ_HP/σ_FP inside the strength modules), and the DIN 3967
allowance-series tables as an input alternative to direct A_W values.

## ADR-025: Audit round P1 — per-norm helix fidelity, TRUE VDI safeties, native F_βx, guarded spur-only paths

**Date:** 2026-08-18 · **Status:** Accepted

**Context:** The 11-agent consistency audit (`consistency_audit_2026-08-18.md`) confirmed
that the validated kst-E path is correct but flagged P1 defects that produce
plausible-looking wrong numbers off that path: helical capacity factors silently dropped
(NRM-03/04), the Y_X group map scrambled (NRM-05), VDI "safeties" that already contained
S_min and were compared against S_min again (NRM-06), an inert K_Hβ Method C (V-02, the
kst-E reference prints 1.19), diverging Dynamikfaktoren/Tragfähigkeit results (GAP-01),
hardcoded material group/density (NRM-07/08), unguarded spur-only geometry paths
(NRM-01/02), a missing 0.001·d term (NRM-09) and deck endpoints skipping the fillet
interference check (FEM-01). User direction: fix ALL of P1, nothing forgotten.

**Decision:**
1. **Per-norm helix fidelity, no shared Y_β/Z_β.** Each branch implements its own norm's
   definition: ISO branch Z_β = √(1/cos β) (6336-2:2019 eq. 41) and Y_β with the 2019
   1/cos³β term and ε_β ≤ 1 / β ≤ 30° caps (6336-3:2019 eq. 66/67), computed NATIVELY in
   `evaluate_iso6336` (the never-set load-case field was removed — a caller cannot forget
   it again); VDI branch Y_β = 1 − min(ε_β,1)·β/120° (2736-2 eq. 12) and Z_β = √cos β
   (VDI gives no formula, states Z_β ≤ 1 and sources its flank factors from DIN 3990 →
   DIN 3990-2:1987 eq. 6.01, verified from the repo PDF). The Stufenvariation kernel uses
   the VDI pair (its stress chain is the VDI tip-load form). This knowingly deviates from
   the audit's "shared helper" recommendation — norm fidelity beats DRY here.
2. **TRUE safeties everywhere** (NRM-06): S = σ_lim/σ; the norm's σ_P (which carries
   S_min per VDI eq. 13/17/24) is a separate explicit field. Downstream S ≥ S_min
   comparisons (GearCard tones, variation Pareto/report threshold) are thereby correct.
3. **F_βx estimation is native** (V-02): ISO 6336-1:2019 §7.5 eq. 54/58/61/66 with the
   optional eq. 59 pinion-shaft route (d_sh, l, s, K′ inputs); f_Hβ comes from the
   accuracy grade (`dynamics_deviations` returns a triple now) or a direct input; an
   explicit F_βx override wins. Running-in per eq. 52/53: per-gear y/χ averaged for mixed
   materials — min(σ_Hlim) had frozen χ_β to 0 for steel–plastic pairs.
4. **One request base for materials** (GAP-01): `MaterialParams` is shared by
   `/api/capacity` and `/api/dynamics`; the Dynamikfaktoren tab and the report send the
   same store values (parity is API-test-pinned).
5. **Refuse instead of degrade** (NRM-01/02): the spur-only SSOT report and the 2-D
   ToothProfile raise for β ≠ 0 (422) until helical support exists.
6. **Deck safety** (FEM-01): all deck/pair endpoints run both gears' fillets through the
   mating-tip interference check; standard/trochoid stay uncheckable by design.

**Consequences:** 256 backend tests (new pins: Y_X per group incl. m_n > 5, ISO/VDI helix
factors, F_βx hand-checks for both routes, TRUE-safety identities, capacity↔dynamics API
parity, helical-422 guards); kst-E spur values unchanged except K_Hβ/K_Fβ, which now come
out ≈ 1.12/1.10 natively at Q7 (reference 1.19 under the 1987 estimation model — the 2019
§7.5 estimate differs by design, ADR-011). VDI safeties change value semantics: S_F is now
S_min times larger than before (the UI thresholds compare correctly); consumers of the old
`root_safety` must re-read it as a TRUE safety. `VariationSpec` lost its unused
`*_minimum_safety` fields (the API request keeps them for the report threshold).

**Amendment (same day, adversarial verify pass):** a 5-agent refutation round over the P1
diff (each fix area re-derived from the norm PDFs) found four defects that were fixed
before commit: the VDI root check omitted **Y_St ≈ 2.0** (Eq. 13, σ_FG = Y_St·σ_FlimN —
worked example A1 and the FVA reference's printed Y_St 2.000 pin it; the sweep's root
limit is 2·σ_Flim for the same reason on both norm branches), VDI Eq. 12 also caps β at
30°, the y_α running-in cap for Eh/IF/NT/NV is 3 µm at all velocities (eq. 79), and the
new helical ValueError guards needed 422 mapping on every profile-consuming route
(tooth-profile, mesh preview/3d, decks, FEM postprocessing). The verify pass also
confirmed the rest of the diff against the rendered norm pages (Z_β radical, Y_β 1/cos³
term and caps, Eq. 54/58/59/61/66 transcriptions, B1 = B2 = 1 per Table 12, F_m = K_A·K_v·F_t).

## ADR-026: Material kind is THE dispatch — coupled name/kind input, per-gear norm branches in the sweep, glossary as the vocabulary SSOT

**Date:** 2026-08-18 · **Status:** Accepted

**Context:** User directive (high priority): the steel and plastic calculation methods
differ fundamentally — the branches must be computed separately and never mixed when a
material is changed in the input mask, the material definition must carry an explicit
metal/plastic selector, and conflicts had to be found and cleaned up. A 3-agent trace
found the Stufenvariation evaluating BOTH gears with one hybrid VDI-form chain
(MAT-01/02), the variation panel ignoring the Werkstoff mask entirely (VAR-01/02),
uncoupled name/kind fields, diverging backend defaults, dead density inputs and a
temperature model feeding the wrong gear's tooth count (MAT-15, primary-source-checked).

**Decision:**
1. **The kind is the single dispatch** and is enforced end-to-end: the store couples
   Werkstoffname ↔ Werkstoffart bidirectionally (catalog-foreign names rejected), every
   consumer (capacity, dynamics, variation, deck, report) reads the ONE materials store,
   side channels are locked (Radkörper mirror computed), and backend property overrides
   branch on the resolved material's kind.
2. **The sweep dispatches the stress FORM per gear**: plastic → VDI 2736-2 tip-load
   chain, steel → ISO 6336-3:2019 Method B (vectorized Y_F/Y_S at d_en, scalar-parity
   test-pinned), each with its norm's helix conventions; σ_H/S_H per gear. The
   permissible sides remain pre-design (no strength sub-factors) — declared via a
   permanent warning, not silently.
3. **The glossary is the vocabulary SSOT** (~200 entries, new "inspection" category):
   every displayed symbol exists with current-norm references incl. edition years and
   related-symbol links; project-internal references are prefixed "Projekt:". Symbol
   collisions were split (h_K vs span k, Kopfspiel c vs Freigang c_F).

**Consequences:** /api/variation results now change when the Werkstoff tab changes —
that is the point. VariationResult.flank_stress_mpa became per-gear. kst-E spur values
are unchanged (both Z_β/Y_β conventions = 1 at β = 0; z 51/52 makes the MAT-15 z-fix
invisible there). Open follow-ups (P2): per-gear material objects for same-kind pairs
(free-pairing vision), deck material cards from the live overrides, variation-panel
re-seed scope, serving the material catalog (name→kind+properties) so the frontend
mirror map disappears. NOTE: during this round a subagent violated its read-only/file
scope twice (overwrote a parallel kernel edit; fixed and re-reviewed) — future
multi-agent rounds must partition files per agent explicitly.

**Provenance note (added after review, same day):** the implementation half of this round
did NOT follow the intended process. The dispatch-trace subagent was instructed to
REPORT ONLY, but implemented and even committed autonomously via its shell access
(commit `67078d0`), interleaved with the main session's own edits (glossary base set,
deck-role/dynamics-sentinel/store-guard fixes, GAP-01 panel work) — at one point both
writers collided (a revert destroyed and restored the kernel Y_F/Y_S half). The commit
was therefore re-reviewed afterwards IN FULL by the main session: every norm-relevant
hunk checked against the primary sources (incl. the MAT-15 z-of-the-plastic-gear symbol
verified in the VDI 2736-2 text), and all gates re-run independently (259 backend tests,
ruff, mypy, tsc, eslint, production build — all green). Process lesson recorded: read-only
agents still hold shell write access; future audit agents get an explicit no-write guard
in their prompt, and their sessions are watched for tree mutations before their reports
are trusted.

## ADR-027: State consistency round (audit P2) — every tab-visible input has exactly one store home

**Date:** 2026-08-18 · **Status:** Accepted

**Context:** After the dispatch round (ADR-026) the user asked for a guarantee that the
materials are defined in ONE frontend place with every consumer reading it, and approved
the audit's P2 block. Verification showed the material store was already the single
read/write source except the FE deck cards (raw catalog only, FEM-03/F4); beyond
materials, four state fragmentations remained: fillet specs and mesh densities in
panel-local useState (STR-03/FEM-02/FIL-01), a triple accuracy-grade state (STR-02),
two competing micro-geometry editors (STR-01), and the allowance band collapsing to a
mean while the frozen kst-E example silently ignored edits (COV-01/FEM-05).

**Decision:** one store home per input, consumers derive: (1) deck material cards take
the Werkstoff-tab overrides (Marlow curves stay catalog data); the catalog itself is
served (`GET /api/materials/catalog`) with a three-way drift-guard test until the copies
are removed entirely. (2) `fem.fillet_gear{n}` + `fem.refine_*` are THE fillet/density
state — Zahnform/Netz tabs bind to them; the variation's compared Fußform lands there on
Übernehmen. (3) `tol.grade1/grade2` drive `operating.accuracy_grade` (worse grade
governs). (4) The Flankenmodifikation tab is THE pinion micro-geometry source; the
Auslegung editor mirrors it read-only and seeds its draft from the new `rawStage` (the
effective stage is for consumers, never for editors). (5) Allowance edits leave example
mode, and the full A_We/A_Wi band travels in the geometry-report/report requests.
(6) FE set classification, refine bands and FEM-result markers follow the active
fillet's junction radius (FEM-04) — the deck's geometry semantics now match the
stress-evaluation chain for raised junctions (Landi).

**Consequences:** what any tab displays is what every endpoint computes with; the
Toleranzen band is finally visible (E_sns ≠ E_sni) and effective in example sessions.
Backend gates: full suite + ruff + mypy; frontend tsc/eslint/build. Open (P3/P4 +
follow-ups): per-gear material NAMES driving properties (two different steels), serving
the uimodel options from the catalog endpoint, COV-02 backlash-delta row, remaining
visibility items.

## ADR-028: Per-gear Flankenmodifikation nodes + schema binding-remap; visibility round P3

**Date:** 2026-08-18 · **Status:** Accepted

**Context:** The user challenged the micro-geometry asymmetry left by ADR-027: the wheel
could only edit simplified micro rows while the pinion had the full Flankenmodifikation
editor (the kst-E tree carries the node [34] at the pinion only). Additionally the
audit's P3 block (computed-but-invisible values, inert mode switches) was approved.

**Decision:** (1) The tree gains a wheel-side Flankenmodifikation node [41] — an
extension beyond the kst-E instance list, id chosen after the Radkörper [40]. It renders
the IDENTICAL backend gear_correction schema through a new, generic SchemaTab
binding-remap (`remapNamespace: correction → correction2`); the store holds a second
CorrectionState and `effectiveStage` derives `modifications_wheel` from it. One full
editor per gear, zero schema duplication; the Auslegung micro table is a read-only
mirror of both. (2) The per-gear C_αa now actually reaches the K_v excitation chain
(`DynamicConditions.tip_relief_um` from the stage micro-geometry) — the former
Tragfähigkeit-tab copy is deleted in favour of a computed mirror row. (3) Visibility:
tab and HTML report carry the same field sets (factors, per-gear norm rows, ISO 1328-1
components, pair quantities, undercut verdict, W_zul/λ), inert switches became live
(ϑ₀ user mode, Ra→Rz per ISO 6336-2's Ra ≈ Rz/6, K_A,stat input), the Übersicht follows
the active stage, and W_k has a single implementation.

**Consequences:** helical-relevant pair rows (m_t, α_t, β_b) are display-ready for the
upcoming helical geometry package; the loaddist package and io/rexs remain intentionally
unrouted (Step-2 groundwork — recorded in the roadmap, audit COV-10/11). Open: P4
(clipping/polish LOWs), COV-02 delta-row edge cases, serving uimodel material options
from the catalog endpoint.

**Amendment (same day, round P4):** the audit's final polish block is done — display
clipping (card stacking below ~1900 px, wider panes, centred pair values in the report),
fillet UX (CAO-only parameter gating, response-derived legend, per-gear result resets,
opt-in CAO ranking, Dong sweep mirror, deck-faithful meshing check), wiring LOWs
(two-gear ISO 1328 check at d/cos β, D_M inputs, live Meldungen strip, regime i18n
token, working-a pair header, routed overview cards) and contract hygiene (CAO response
diagnostics-only, label echo removed, memoized effectiveStage, chamfer-aware CAO cache,
per-gear flank-symmetry into the deck mesher, root circles + SSOT ε_α in the engagement
plot). With this, all P1–P4 audit findings are fixed, intentional, or deferred with
rationale (see the audit banner) — the deferred set is an architecture-cleanup round
(STR-05/06/07, STR-15, FEM-09, GAP-10 rest), not open defects.
