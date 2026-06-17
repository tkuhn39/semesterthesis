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
| ADR-012 | Native involute geometry incl. tool-generated tip chamfer | Accepted | 2026-06-17 |
| ADR-013 | Plastic-capable Stufenvariation and its performance strategy | Accepted | 2026-06-17 |
| ADR-014 | Native ISO 6336-1 dynamic/load factors (K_v, K_Hα, K_Hβ) | Accepted | 2026-06-17 |
| ADR-015 | Native VDI 2736 plastic-gear capacity (root/flank/temperature/wear/deformation) | Accepted | 2026-06-17 |

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

---
