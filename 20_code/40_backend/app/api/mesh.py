"""
@module: app.api.mesh
@context: API layer — FE mesh preview/3D data, fillet tooling + Abaqus deck download (M4–M6).
@role: Expose the ADR-019 transplant mesher over HTTP for the workbench: 2-D sector preview,
       render-ready 3-D hull, native density-convergence quick check, fillet ranking and
       parameter sweep (quick-FE objective — the Stufenvariation axis for optimized root
       fillets), the real as-cut tooth contour, and the implicit rolling deck with the
       mixed-pairing material rule. Every endpoint consumes the shared ``StageParams``
       (kst-E example or free parameters — plan v2 product vision), and the flank-symmetry
       policy flows from the per-flank micro-geometry data.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Annotated, ClassVar, Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, model_validator

from app.api.stage_params import StageParams
from app.services.geometry.gear import GearStage
from app.services.geometry.root_fillet import (
    BezierFillet,
    BionicFillet,
    DongToolBezierFillet,
    EllipticFillet,
    FilletStrategy,
    FruheEllipticFillet,
    LandiEllipticFillet,
    TrochoidFillet,
    fillet_boundary,
    junction_radius_mm,
    mating_tip_clearance,
    with_root_land,
)
from app.services.geometry.tooth_form import ToothProfile
from app.services.materials import catalog_material
from app.services.model.cao_fillet import CaoFillet
from app.services.model.implicit_deck import (
    assemble_centered_pair,
    build_implicit_pair_from_stage,
    build_position_series,
)
from app.services.model.materials_card import LinearElastic, MarlowUniaxial, card_from_catalog
from app.services.model.mesh3d import extrude_to_hex
from app.services.model.plane_fe import density_convergence, root_tensile_stress
from app.services.model.template_mesher import SectorMesh2D, generate_sector_2d, scaled_jacobians
from app.services.model.tooth_mesh import Mesh2D

router = APIRouter(prefix="/api/mesh", tags=["mesh"])


# ----------------------------------------------------------------------------------------------
# request models
# ----------------------------------------------------------------------------------------------
FilletApproach = Literal["kassem", "fruehe", "landi", "roth", "dong", "voith", "cao"]
AnyFillet = FilletStrategy | CaoFillet  # CaoFillet lives in the model layer (FE loop)


class FilletSpec(BaseModel):
    """Root-fillet strategy selection (see geometry/root_fillet.py).

    ``kind`` picks the geometry family, ``approach`` the literature method within it
    (elliptic: kassem | fruehe | landi; bezier: roth | dong; bionic: voith | cao).
    ``approach = None`` normalizes to the family default (kassem / roth / voith), so legacy
    payloads keep their exact behaviour. ``standard`` = the ρ_F arc; ``trochoid`` = the exact
    tool trochoid; the optimized shapes (molded/WEDM gears only, except Dong's hob-tip form)
    carry their literature parameters.
    """

    _APPROACHES: ClassVar[dict[str, tuple[FilletApproach, ...]]] = {
        "elliptic": ("kassem", "fruehe", "landi"),
        "bezier": ("roth", "dong"),
        "bionic": ("voith", "cao"),
    }
    _PENDING: ClassVar[frozenset[str]] = frozenset()  # all seven approaches implemented

    kind: Literal["standard", "trochoid", "elliptic", "bezier", "bionic"] = "standard"
    approach: FilletApproach | None = None
    e_f: Annotated[float, Field(ge=-0.5, le=0.2)] = 0.0  # elliptic/kassem root-diameter factor
    tilt_deg: Annotated[float, Field(gt=0.0, le=45.0)] = 30.0  # fruehe tilt γ (optimum 30°)
    aspect: Annotated[float, Field(ge=1.0, le=6.0)] = 3.0  # fruehe axis ratio a/b (optimum 3.0)
    ra_f: Annotated[float, Field(ge=0.0, le=1.5)] = 0.0  # landi D1 offset above d_Ff (·m_n)
    d2_frac: Annotated[float, Field(ge=0.5, le=1.0)] = 1.0  # landi D2 angle fraction to gap centre
    be: Annotated[float, Field(ge=0.3, le=0.95)] = 0.57  # Bézier factor (Roth/Voith)
    # dong hob-tip Bézier variables V = [v0…v4] (dv2–dv4 = paper GA optimum, Fig. 15j;
    # dv1 = 1.0 ends on the gap centreline — see DongToolBezierFillet docstring)
    dv0: Annotated[float, Field(ge=0.05, le=0.9)] = 0.35  # P0 depth below tip (·h_kW)
    dv1: Annotated[float, Field(ge=0.05, le=1.0)] = 1.0  # P4 along tip land (1 = gap centre)
    dv2: Annotated[float, Field(ge=0.02, le=0.6)] = 0.15  # tangent lengths at P0/P4 (·m_n)
    dv3: Annotated[float, Field(ge=0.0, le=1.0)] = 0.499  # P2 x-interpolation P0→P4
    dv4: Annotated[float, Field(ge=0.0, le=1.2)] = 0.991  # P2 y-interpolation P0→P4
    gamma_deg: Annotated[float, Field(gt=5.0, lt=65.0)] | None = None  # bionic wedge angle
    b_f: Annotated[float, Field(ge=0.1, le=0.6)] = 0.35  # bionic arc factor
    cao_step: Annotated[float, Field(ge=0.1, le=3.0)] = 1.0  # cao: growth scale (·0.025·m_n)
    cao_iterations: Annotated[int, Field(ge=1, le=30)] = 12  # cao: FE↔growth budget
    cao_tol: Annotated[float, Field(ge=0.001, le=0.2)] = 0.02  # cao: uniformity target
    junction_offset_mm: Annotated[float, Field(ge=0.0, le=0.2)] = 0.0  # interference fallback

    @model_validator(mode="after")
    def _normalize_approach(self) -> FilletSpec:
        allowed = self._APPROACHES.get(self.kind)
        if allowed is None:
            if self.approach is not None:
                raise ValueError(f"kind '{self.kind}' takes no approach")
            return self
        if self.approach is None:
            self.approach = allowed[0]  # family default = pre-approach behaviour
        elif self.approach not in allowed:
            raise ValueError(f"approach '{self.approach}' is not valid for kind '{self.kind}'")
        if self.approach in self._PENDING:
            raise ValueError(f"approach '{self.approach}' is not implemented yet")
        return self

    def strategy(self) -> AnyFillet | None:
        off = self.junction_offset_mm
        if self.kind == "trochoid":
            return TrochoidFillet()
        if self.kind == "elliptic":
            if self.approach == "fruehe":
                return FruheEllipticFillet(
                    tilt_deg=self.tilt_deg, aspect=self.aspect, junction_offset_mm=off
                )
            if self.approach == "landi":
                return LandiEllipticFillet(ra_f=self.ra_f, d2_frac=self.d2_frac)
            return EllipticFillet(e_f=self.e_f, junction_offset_mm=off)
        if self.kind == "bezier":
            if self.approach == "dong":
                return DongToolBezierFillet(
                    dv0=self.dv0, dv1=self.dv1, dv2=self.dv2, dv3=self.dv3, dv4=self.dv4
                )
            return BezierFillet(be=self.be, junction_offset_mm=off)
        if self.kind == "bionic":
            if self.approach == "cao":
                return CaoFillet(
                    cao_step=self.cao_step,
                    cao_iterations=self.cao_iterations,
                    cao_tol=self.cao_tol,
                )
            return BionicFillet(gamma_deg=self.gamma_deg, b_f=self.b_f, junction_offset_mm=off)
        return None


class MeshRequest(BaseModel):
    """Mesh one gear of the stage with FVA density factors + fillet strategy."""

    stage: StageParams = Field(default_factory=StageParams)
    gear: Literal[1, 2] = 1  # input slot: 1 = the stage's first gear, 2 = the second (ADR-021)
    refine_root: int = Field(1, ge=1, le=3)
    refine_flank: int = Field(1, ge=1, le=3)
    refine_thickness: int = Field(1, ge=1, le=3)  # Elemente über Zahndicke (FVA dialog)
    fillet: FilletSpec = Field(default_factory=FilletSpec)
    bore_radius_mm: float | None = Field(None, gt=0.0)


class DeckRequest(BaseModel):
    """Full implicit rolling deck (both gears) as .inp text.

    Slot semantics (ADR-021, amended): gear 1 = the stage's FIRST gear, gear 2 = the second —
    every per-gear field follows that input chain and is never re-ordered by role or tooth
    count (kst-E: gear 1 = steel pinion z=51 at the origin/left, gear 2 = plastic wheel z=52
    at the centre distance/right — the Kleingetriebeprüfstand top view). ``torque_gear2_nmm``
    is the resisting torque expressed AT GEAR 2 (M₂); the deck applies the equivalent torque
    at whichever gear carries the load. ``axial_offset_*`` displace each gear along its
    rotation axis from the default mid-plane alignment (both gears are extruded symmetric
    about z = 0, reference parity).
    """

    stage: StageParams = Field(default_factory=StageParams)
    torque_gear2_nmm: float = Field(20000.0, gt=0.0)
    face_layers: int = Field(6, ge=1, le=80)
    n_roll_positions: int = Field(30, ge=1, le=200)
    # per-position torque cycle (user decision 2026-07-06; increments per phase)
    roll_pitches: float = Field(3.0, gt=0.0, le=4.0)
    ramp_up: int = Field(2, ge=1, le=20)
    hold: int = Field(2, ge=1, le=20)
    ramp_down: int = Field(2, ge=1, le=20)
    move: int = Field(2, ge=1, le=20)
    settle: int = Field(6, ge=1, le=40)
    base_torque_fraction: float = Field(0.01, ge=0.0, le=0.5)
    start_at_edge: bool = Field(
        True,
        description="Begin the roll at an edge tooth so the middle teeth sweep the full "
        "engagement boundary-free (user decision 2026-07-06)",
    )
    rotation_sense: Literal["cw", "ccw"] = Field(
        "cw",
        description="Drehrichtung of the drive (Leistungsfluss): cw = validated default "
        "(torque gear clockwise in the rig top view); ccw mirrors the load case",
    )
    # FVA mesh-fineness factors ("Vernetzungsparameter" dialog): the plain fields apply to
    # BOTH gears, each *_gear2 field overrides gear 2 (root = Zahnfuß, flank = Zahnhöhe,
    # thickness = Zahndicke; Zahnbreite = face_layers, shared)
    refine_root: int = Field(1, ge=1, le=3)
    refine_flank: int = Field(1, ge=1, le=3)
    refine_thickness: int = Field(1, ge=1, le=3)
    refine_root_gear2: int | None = Field(None, ge=1, le=3)
    refine_flank_gear2: int | None = Field(None, ge=1, le=3)
    refine_thickness_gear2: int | None = Field(None, ge=1, le=3)
    gear1_material: Literal["steel", "plastic"] = "steel"
    gear2_material: Literal["steel", "plastic"] = "plastic"
    axial_offset_gear1_mm: float = Field(0.0, ge=-50.0, le=50.0)
    axial_offset_gear2_mm: float = Field(0.0, ge=-50.0, le=50.0)
    steel_shell: bool = Field(
        False,
        description="Legacy mixed-pairing shortcut: the steel side as ideally stiff "
        "Außenhülle (equivalent to setting rigid_shell_gear{n} on the steel slot)",
    )
    # per-gear ideally stiff Außenhülle (R3D4 lateral surface, open axial end faces —
    # user decision 2026-07-06); the contact slave must stay deformable
    rigid_shell_gear1: bool = Field(False, description="Rad 1 als ideal steife Außenhülle")
    rigid_shell_gear2: bool = Field(False, description="Rad 2 als ideal steife Außenhülle")
    fillet_gear1: FilletSpec = Field(default_factory=FilletSpec)
    fillet_gear2: FilletSpec = Field(default_factory=FilletSpec)
    align_contact: bool = Field(
        True,
        description="Rotate gear 2 into single-flank contact (~15 µm arc clearance) so the "
        "torque ramp closes the gap like the reference deck; False keeps the tooth centred "
        "in the gap with the full allowance backlash",
    )
    # FVA "Fesselung" checkboxes (Dynamisches Abwälzen (FEM)); defaults = reference parity
    fasten_bore: bool = Field(True, description="Fesselung an der Bohrung")
    fasten_cuts: bool = Field(True, description="Fesselung im Schnitt (both radial cut planes)")
    fasten_top: bool = Field(False, description="Fesselung oben (axial end face, +z)")
    fasten_bottom: bool = Field(False, description="Fesselung unten (axial end face, -z)")


# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------
def _profiles(stage_params: StageParams, gear: int) -> tuple[GearStage, ToothProfile, ToothProfile]:
    """(stage, this gear's profile, mating profile) for a 1-based gear index.

    The tooth profiles carry the stage's micro-geometry (Kopfrücknahme C_αa) so preview,
    mesh and deck all show the SAME as-meshed contour (user decision 2026-07-06).
    """
    stage = stage_params.stage()

    def prof(index: int) -> ToothProfile:
        c_aa, d_ca = stage_params.tip_relief(index)
        return ToothProfile.from_stage(
            stage, index, tip_relief_um=c_aa, tip_relief_start_diameter_mm=d_ca
        )

    return stage, prof(gear - 1), prof(2 - gear)


def _clearance(
    stage: GearStage, profile: ToothProfile, mating: ToothProfile, strategy: AnyFillet
) -> float:
    """Mating-tip clearance of an optimized fillet (mandatory check; negative = interference)."""
    fillet_pts = np.array([(p[0], p[1]) for p in strategy.right_half(profile)])
    r_tip = (mating.d_a or mating.d_Na) / 2.0
    return float(
        mating_tip_clearance(
            profile,
            fillet_pts,
            mating_tip_radius_mm=r_tip,
            mating_teeth=mating.z,
            mating_half_tip_rad=mating.half_thickness_angle(r_tip),
            centre_distance_mm=stage.working_center_distance_mm,
        )
    )


def _checked_strategy(
    stage: GearStage, profile: ToothProfile, mating: ToothProfile, spec: FilletSpec
) -> tuple[AnyFillet | None, float | None]:
    """Resolve the fillet strategy and enforce the interference check (422 on interference)."""
    strategy = spec.strategy()
    if strategy is None or isinstance(strategy, TrochoidFillet):
        return strategy, None
    clearance = _clearance(stage, profile, mating, strategy)
    if clearance < 0.0:
        raise HTTPException(
            422,
            f"optimized fillet interferes with the mating tooth tip "
            f"(clearance {clearance:.3f} mm) — reduce the fillet parameter",
        )
    return strategy, clearance


def _sector(req: MeshRequest) -> tuple[ToothProfile, SectorMesh2D]:
    stage, profile, mating = _profiles(req.stage, req.gear)
    strategy, _ = _checked_strategy(stage, profile, mating, req.fillet)
    try:
        mesh = generate_sector_2d(
            profile,
            bore_radius_mm=req.bore_radius_mm,
            refine_root=req.refine_root,
            refine_flank=req.refine_flank,
            refine_thickness=req.refine_thickness,
            fillet=strategy,
            mirror_symmetric=req.stage.mirror_symmetric(req.gear),
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return profile, mesh


# ----------------------------------------------------------------------------------------------
# endpoints
# ----------------------------------------------------------------------------------------------
class MeshPreviewResponse(BaseModel):
    """2-D sector slice for plotting: flat node coords, quad indices, per-quad quality."""

    gear: int
    n_nodes: int
    n_quads: int
    nodes_xy: list[float]  # x0, y0, x1, y1, …
    quads: list[int]  # 4 indices per quad
    quality: list[float]  # scaled Jacobian per quad
    min_scaled_jacobian: float
    cells_below_035: int
    kind_surface: list[int]  # node indices on the gear surface (contour plotting)
    # effective per-tooth element counts (FVA mesh-fineness dialog "effektive Werte"):
    # one gap rounding (Zahnfuß), one flank (Zahnhöhe), the tip land (Zahndicke)
    elements_root: int
    elements_flank: int
    elements_thickness: int


@router.post("/preview", response_model=MeshPreviewResponse)
def mesh_preview(req: MeshRequest) -> MeshPreviewResponse:
    """The 2-D transplant sector (reference topology on the requested parameters)."""
    _, mesh = _sector(req)
    sj = scaled_jacobians(mesh.coords, mesh.quads)
    pts = mesh.points
    return MeshPreviewResponse(
        gear=req.gear,
        n_nodes=len(pts),
        n_quads=len(mesh.quads),
        nodes_xy=[round(float(v), 6) for v in pts.ravel()],
        quads=[int(i) for q in mesh.quads for i in q],
        quality=[round(float(v), 4) for v in sj],
        min_scaled_jacobian=float(sj.min()),
        cells_below_035=int((sj < 0.35).sum()),
        kind_surface=[i for i, k in enumerate(mesh.kind) if k == "surface"],
        elements_root=int(mesh.meta["elements_root"]),
        elements_flank=int(mesh.meta["elements_flank"]),
        elements_thickness=int(mesh.meta["elements_thickness"]),
    )


def _outer_hull(hexes: np.ndarray) -> list[tuple[tuple[int, ...], int]]:
    """(face node tuple, source hex index) for every hex face used exactly once.

    C3D8 face node patterns (bottom, top, 4 sides) — the render-ready outer surface.
    """
    patterns = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    count: dict[frozenset[int], int] = defaultdict(int)
    keeper: dict[frozenset[int], tuple[tuple[int, ...], int]] = {}
    for hi, hexa in enumerate(hexes):
        for pat in patterns:
            face = tuple(int(hexa[p]) for p in pat)
            key = frozenset(face)
            count[key] += 1
            keeper[key] = (face, hi)
    return [keeper[k] for k, c in count.items() if c == 1]


class Mesh3DResponse(BaseModel):
    """Render-ready extruded sector: outer surface quad faces + per-face quality."""

    gear: int
    n_nodes_3d: int
    n_hexes: int
    min_scaled_jacobian: float
    cells_below_035: int
    face_width_mm: float
    vertices: list[float]  # x, y, z per surface vertex (deduplicated)
    faces: list[int]  # 4 vertex indices per outer quad face
    face_quality: list[float]  # source-hex scaled Jacobian per face


@router.post("/3d", response_model=Mesh3DResponse)
def mesh_3d(
    req: MeshRequest, face_width_mm: float | None = None, layers: int = 6
) -> Mesh3DResponse:
    """Extrude the sector and return only the outer hull (surface faces) for three.js."""
    if not 1 <= layers <= 80:
        raise HTTPException(422, "layers must be in 1..80")
    profile, mesh = _sector(req)
    stage = req.stage.stage()
    if face_width_mm is None:
        if stage.face_width_mm is None:
            raise HTTPException(422, "stage carries no face width; pass face_width_mm")
        face_width_mm = float(abs(stage.face_width_mm[req.gear - 1]))
    section = Mesh2D(mesh.points, np.asarray(mesh.quads, dtype=np.int64))
    quality = scaled_jacobians(mesh.coords, mesh.quads)
    # mid-plane-symmetric extrusion (z = ±b/2, reference parity): gears of different width
    # roll centred on each other and the rotation nodes sit at mid-width, not on a side face
    m3 = extrude_to_hex(section, quality, width=face_width_mm, layers=layers, z0=-face_width_mm / 2)
    hull = _outer_hull(m3.hexes)
    used = sorted({v for face, _ in hull for v in face})
    remap = {v: i for i, v in enumerate(used)}
    verts = m3.nodes[used]
    qual = m3.quality if m3.quality is not None else np.ones(len(m3.hexes))
    return Mesh3DResponse(
        gear=req.gear,
        n_nodes_3d=m3.n_nodes,
        n_hexes=m3.n_hexes,
        min_scaled_jacobian=float(np.min(qual)),
        cells_below_035=int(np.sum(qual < 0.35)),
        face_width_mm=float(face_width_mm),
        vertices=[round(float(v), 5) for v in verts.ravel()],
        faces=[remap[v] for face, _ in hull for v in face],
        face_quality=[round(float(qual[hi]), 4) for _, hi in hull],
    )


class ConvergenceRequest(BaseModel):
    stage: StageParams = Field(default_factory=StageParams)
    gear: Literal[1, 2] = 1
    target: Literal["root", "flank"] = "root"
    levels: list[int] = Field(default=[1, 2, 3], min_length=2, max_length=4)
    tolerance: float = Field(0.02, gt=0.0, lt=0.5)


class ConvergenceResponse(BaseModel):
    target: str
    levels: list[int]
    sigma_mpa: list[float]
    relative_change: list[float]
    converged_level: int | None
    reference_sigma_mpa: float


@router.post("/convergence", response_model=ConvergenceResponse)
def mesh_convergence(req: ConvergenceRequest) -> ConvergenceResponse:
    """Native quick-FE density convergence (separate root/flank searches, seconds not hours)."""
    _, profile, _ = _profiles(req.stage, req.gear)
    result = density_convergence(
        profile, target=req.target, levels=tuple(req.levels), tol=req.tolerance
    )
    return ConvergenceResponse(
        target=result.target,
        levels=result.levels,
        sigma_mpa=[round(s, 3) for s in result.sigma_mpa],
        relative_change=[round(c, 5) for c in result.relative_change],
        converged_level=result.converged_level,
        reference_sigma_mpa=round(result.sigma_mpa[0], 3),
    )


class FilletCompareRequest(BaseModel):
    stage: StageParams = Field(default_factory=StageParams)
    gear: Literal[1, 2] = 2
    include_cao: bool = False  # the CAO row costs a full FE growth loop (~10 s uncached)


class FilletCompareResponse(BaseModel):
    """Quick-FE root-stress ranking of the fillet strategies (same load, same topology)."""

    gear: int
    names: list[str]
    sigma_mpa: list[float]
    delta_percent: list[float]
    clearance_mm: list[float]


@router.post("/fillet-compare", response_model=FilletCompareResponse)
def fillet_compare(req: FilletCompareRequest) -> FilletCompareResponse:
    """Rank the fillet approaches (kind-approach rows) by quick-FE root stress."""
    stage, profile, mating = _profiles(req.stage, req.gear)
    strategies: list[tuple[str, AnyFillet | None]] = [
        ("standard", None),
        ("trochoid", TrochoidFillet()),
        ("elliptic-kassem", EllipticFillet(e_f=-0.2)),
        ("elliptic-fruehe", FruheEllipticFillet()),
        # Landi's benefit needs the raised D1 (paper default: limit contact diameter)
        ("elliptic-landi", LandiEllipticFillet(ra_f=0.3)),
        ("bezier-roth", BezierFillet(be=0.57)),
        ("bezier-dong", DongToolBezierFillet()),
        ("bionic-voith", BionicFillet()),
    ]
    if req.include_cao:
        strategies.append(("bionic-cao", CaoFillet()))
    names: list[str] = []
    sigmas: list[float] = []
    clearances: list[float] = []
    for name, strategy in strategies:
        try:
            mesh = generate_sector_2d(profile, fillet=strategy)
        except ValueError:
            continue  # a strategy that fails on this geometry is simply omitted
        limit = None if strategy is None else junction_radius_mm(strategy, profile)
        sigmas.append(
            root_tensile_stress(mesh, profile, fillet_limit_radius_mm=limit).sigma_max_mpa
        )
        if strategy is None:
            boundary = np.array([(p[0], p[1]) for p in profile.transverse_right_boundary()])
            fillet_pts = boundary[
                np.hypot(boundary[:, 0], boundary[:, 1]) < profile.d_Ff / 2.0 + 1e-6
            ]
            r_tip = (mating.d_a or mating.d_Na) / 2.0
            clearances.append(
                float(
                    mating_tip_clearance(
                        profile,
                        fillet_pts,
                        mating_tip_radius_mm=r_tip,
                        mating_teeth=mating.z,
                        mating_half_tip_rad=mating.half_thickness_angle(r_tip),
                        centre_distance_mm=stage.working_center_distance_mm,
                    )
                )
            )
        else:
            clearances.append(_clearance(stage, profile, mating, strategy))
        names.append(name)
    ref = sigmas[0]
    return FilletCompareResponse(
        gear=req.gear,
        names=names,
        sigma_mpa=[round(s, 2) for s in sigmas],
        delta_percent=[round((s / ref - 1.0) * 100.0, 2) for s in sigmas],
        clearance_mm=[round(c, 3) for c in clearances],
    )


class FilletSweepRequest(BaseModel):
    """Sweep ONE approach's shape parameter with the quick-FE objective (Variation axis)."""

    stage: StageParams = Field(default_factory=StageParams)
    gear: Literal[1, 2] = 2
    kind: Literal["elliptic", "bezier", "bionic"] = "bezier"
    approach: FilletApproach | None = None  # None = family default (kassem/roth/voith)
    parameter: str | None = None  # None = the approach's primary parameter
    points: int = Field(6, ge=3, le=12)


class FilletSweepResponse(BaseModel):
    gear: int
    kind: str
    approach: str
    parameter: str
    values: list[float]
    sigma_mpa: list[float]
    clearance_mm: list[float]
    feasible: list[bool]  # clearance > 0 and gates met
    best_value: float | None
    best_sigma_mpa: float | None
    standard_sigma_mpa: float


# (kind, approach) → ordered {parameter: (lo, hi)}; first entry = primary sweep parameter
_SWEEP_RANGES: dict[tuple[str, str], dict[str, tuple[float, float]]] = {
    ("elliptic", "kassem"): {"e_f": (-0.4, 0.0)},
    ("elliptic", "fruehe"): {"tilt_deg": (10.0, 45.0), "aspect": (1.5, 4.5)},
    ("elliptic", "landi"): {"ra_f": (0.0, 0.8), "d2_frac": (0.6, 1.0)},
    ("bezier", "roth"): {"be": (0.42, 0.9)},
    ("bezier", "dong"): {
        "dv1": (0.35, 1.0),
        "dv4": (0.6, 1.15),
        "dv2": (0.05, 0.4),
        "dv3": (0.2, 0.9),
    },
    ("bionic", "voith"): {"b_f": (0.15, 0.55), "gamma_deg": (15.0, 55.0)},
}


@router.post("/fillet-sweep", response_model=FilletSweepResponse)
def fillet_sweep(req: FilletSweepRequest) -> FilletSweepResponse:
    """σ_F quick-FE over the approach's parameter range; recommends the feasible optimum."""
    stage, profile, mating = _profiles(req.stage, req.gear)
    standard = root_tensile_stress(generate_sector_2d(profile), profile).sigma_max_mpa
    approach = req.approach or FilletSpec(kind=req.kind).approach or ""
    ranges = _SWEEP_RANGES.get((req.kind, approach))
    if ranges is None:
        raise HTTPException(422, f"no sweep ranges for {req.kind}/{approach} (self-optimizing?)")
    param = req.parameter or next(iter(ranges))
    if param not in ranges:
        raise HTTPException(422, f"parameter '{param}' not sweepable for {req.kind}/{approach}")
    lo, hi = ranges[param]
    values = np.linspace(lo, hi, req.points)
    sigmas: list[float] = []
    clearances: list[float] = []
    feasible: list[bool] = []
    for v in values:
        spec = FilletSpec(kind=req.kind, approach=approach, **{param: float(v)})  # type: ignore[arg-type]
        strategy = spec.strategy()
        assert strategy is not None
        try:
            clearance = _clearance(stage, profile, mating, strategy)
            mesh = generate_sector_2d(
                profile, fillet=strategy, mirror_symmetric=req.stage.mirror_symmetric(req.gear)
            )
            sj = scaled_jacobians(mesh.coords, mesh.quads)
            ok = clearance > 0.0 and float(sj.min()) >= 0.35
            sigma = root_tensile_stress(
                mesh, profile, fillet_limit_radius_mm=junction_radius_mm(strategy, profile)
            ).sigma_max_mpa
        except (ValueError, HTTPException):
            clearance, sigma, ok = math.nan, math.nan, False
        sigmas.append(round(sigma, 2) if not math.isnan(sigma) else math.nan)
        clearances.append(round(clearance, 3) if not math.isnan(clearance) else math.nan)
        feasible.append(ok)
    best_i = min(
        (i for i in range(len(values)) if feasible[i]),
        key=lambda i: sigmas[i],
        default=None,
    )
    return FilletSweepResponse(
        gear=req.gear,
        kind=req.kind,
        approach=approach,
        parameter=param,
        values=[round(float(v), 4) for v in values],
        sigma_mpa=[s if not math.isnan(s) else -1.0 for s in sigmas],
        clearance_mm=[c if not math.isnan(c) else -99.0 for c in clearances],
        feasible=feasible,
        best_value=round(float(values[best_i]), 4) if best_i is not None else None,
        best_sigma_mpa=sigmas[best_i] if best_i is not None else None,
        standard_sigma_mpa=round(standard, 2),
    )


class FilletCaoRequest(BaseModel):
    """Run the CAO growth loop (Kassem 2023) and report its convergence history."""

    stage: StageParams = Field(default_factory=StageParams)
    gear: Literal[1, 2] = 2
    cao_step: Annotated[float, Field(ge=0.1, le=3.0)] = 1.0
    cao_iterations: Annotated[int, Field(ge=1, le=30)] = 12
    cao_tol: Annotated[float, Field(ge=0.001, le=0.2)] = 0.02


class FilletCaoResponse(BaseModel):
    gear: int
    iterations_run: int
    converged: bool
    sigma_history_mpa: list[float]  # max fillet σ1 per iteration
    uniformity_history: list[float]  # (σ_max − σ_ref)/σ_ref per iteration
    boundary_xy: list[float]  # optimized fillet polyline (tooth frame, gap → junction)
    effective_root_diameter_mm: float
    clearance_mm: float


@router.post("/fillet-cao", response_model=FilletCaoResponse)
def fillet_cao(req: FilletCaoRequest) -> FilletCaoResponse:
    """CAO growth diagnostics; also warms the in-process cache for subsequent deck builds."""
    stage, profile, mating = _profiles(req.stage, req.gear)
    strategy = CaoFillet(
        cao_step=req.cao_step, cao_iterations=req.cao_iterations, cao_tol=req.cao_tol
    )
    try:
        result = strategy.result(profile)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    clearance = _clearance(stage, profile, mating, strategy)
    r_min = min(math.hypot(x, y) for x, y in result.points)
    return FilletCaoResponse(
        gear=req.gear,
        iterations_run=result.iterations_run,
        converged=result.converged,
        sigma_history_mpa=[round(s, 2) for s in result.sigma_history_mpa],
        uniformity_history=[round(u, 4) for u in result.uniformity_history],
        boundary_xy=[round(float(v), 5) for p in result.points for v in p],
        effective_root_diameter_mm=round(2.0 * r_min, 4),
        clearance_mm=round(clearance, 4),
    )


class ContourRequest(BaseModel):
    """Real as-cut tooth contour (M5) — the shared stage (kst-E or free parameters)."""

    stage: StageParams = Field(default_factory=StageParams)
    gear: Literal[1, 2] = 2
    fillet: FilletSpec = Field(default_factory=FilletSpec)
    points: int = Field(160, ge=40, le=600)


class ContourResponse(BaseModel):
    """One gear's right-half boundary (gap side → tip) in the tooth frame (+y = tooth centre)."""

    gear: int
    teeth: int
    pitch_deg: float
    root_diameter_mm: float
    root_form_diameter_mm: float
    usable_tip_diameter_mm: float
    tip_diameter_mm: float | None
    boundary_xy: list[float]  # x0, y0, x1, y1, … right boundary, root side → tip circle
    fillet_kind: str
    fillet_approach: str | None  # literature approach (None for standard/trochoid)
    effective_root_diameter_mm: float  # 2·min|boundary| — Frühe digs below d_f by design
    clearance_mm: float | None  # mating-tip clearance for optimized fillets (None = standard)


@router.post("/contour", response_model=ContourResponse)
def tooth_contour(req: ContourRequest) -> ContourResponse:
    """The real generated tooth boundary (ρ_F fillet, trochoid or optimized strategy, to d_a)."""
    stage, profile, mating = _profiles(req.stage, req.gear)
    strategy, clearance = _checked_strategy(stage, profile, mating, req.fillet)
    if strategy is None:
        pts = profile.transverse_right_boundary(
            fillet_points=req.points // 3,
            flank_points=req.points - req.points // 3,
            to_tip_circle=True,
        )
    else:
        try:
            pts = fillet_boundary(
                profile, strategy, flank_points=req.points - req.points // 3, to_tip_circle=True
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    # complete the drawn envelope across the root land on d_f (fillet end → gap centreline),
    # so the standard/trochoid contour is continuous like the Bézier one (user report)
    pts = with_root_land(profile, pts)
    r_min = min(math.hypot(p[0], p[1]) for p in pts)
    return ContourResponse(
        gear=req.gear,
        teeth=profile.z,
        pitch_deg=360.0 / profile.z,
        root_diameter_mm=round(profile.root_diameter_mm, 4),
        root_form_diameter_mm=round(profile.d_Ff, 4),
        usable_tip_diameter_mm=round(profile.d_Na, 4),
        tip_diameter_mm=round(profile.d_a, 4) if profile.d_a is not None else None,
        boundary_xy=[round(float(v), 5) for p in pts for v in (p[0], p[1])],
        fillet_kind=req.fillet.kind,
        fillet_approach=req.fillet.approach if strategy is not None else None,
        effective_root_diameter_mm=round(2.0 * r_min, 4),
        clearance_mm=round(clearance, 4) if clearance is not None else None,
    )


@router.post("/deck", response_class=PlainTextResponse)
def build_deck(req: DeckRequest) -> PlainTextResponse:
    """The full implicit rolling deck (.inp) for the stage with the requested options."""
    stage = req.stage.stage()
    roles = _deck_roles(req)
    deck = build_implicit_pair_from_stage(
        stage,
        torque_gear2_nmm=req.torque_gear2_nmm,
        face_layers=req.face_layers,
        axial_offset_mm=(req.axial_offset_gear1_mm, req.axial_offset_gear2_mm),
        roll_pitches=req.roll_pitches,
        n_roll_positions=req.n_roll_positions,
        ramp_up=req.ramp_up,
        hold=req.hold,
        ramp_down=req.ramp_down,
        move=req.move,
        settle=req.settle,
        base_torque_fraction=req.base_torque_fraction,
        start_at_edge=req.start_at_edge,
        rotation_sense=req.rotation_sense,
        tip_relief=(req.stage.tip_relief(0), req.stage.tip_relief(1)),
        **_deck_refine(req),
        fillet_gear1=req.fillet_gear1.strategy(),
        fillet_gear2=req.fillet_gear2.strategy(),
        align_contact=req.align_contact,
        fasten_bore=req.fasten_bore,
        fasten_cuts=req.fasten_cuts,
        fasten_bottom=req.fasten_bottom,
        fasten_top=req.fasten_top,
        **roles,
    )
    pitch_deg = 360.0 / stage.teeth[roles["driven_gear"] - 1]  # the angle-driven gear's pitch
    headers = {
        "Content-Disposition": "attachment; filename=implicit_rolling_generated.inp",
        "X-Roll-Pitch-Deg": f"{pitch_deg:.4f}",
    }
    return PlainTextResponse(deck, media_type="text/plain", headers=headers)


def _deck_refine(req: DeckRequest) -> dict:
    """Per-gear (root, flank, thickness) fineness tuples; *_gear2 overrides the shared value."""
    return {
        "refine_gear1": (req.refine_root, req.refine_flank, req.refine_thickness),
        "refine_gear2": (
            req.refine_root if req.refine_root_gear2 is None else req.refine_root_gear2,
            req.refine_flank if req.refine_flank_gear2 is None else req.refine_flank_gear2,
            req.refine_thickness
            if req.refine_thickness_gear2 is None
            else req.refine_thickness_gear2,
        ),
    }


def _deck_roles(req: DeckRequest) -> dict:
    """Materials + role assignment shared by both deck modes (single file and series).

    Roles follow the MATERIAL (reference parity), the chain follows the input slot: the
    plastic side is angle-driven and the contact slave; same-material pairs keep gear 2.
    The mixed-pairing rigid-shell rule applies to the steel side only.
    """

    def deck_material(kind: str) -> LinearElastic | MarlowUniaxial:
        # properties from THE material catalog (single source, user decision 2026-07-04)
        return card_from_catalog(catalog_material(kind))

    kinds = (req.gear1_material, req.gear2_material)
    plastic_side = 1 if kinds == ("plastic", "steel") else 2
    rigid: set[int] = set()
    if req.rigid_shell_gear1:
        rigid.add(1)
    if req.rigid_shell_gear2:
        rigid.add(2)
    # legacy shortcut: "Stahlseite ideal steif" of a mixed pairing
    if req.steel_shell and "plastic" in kinds and "steel" in kinds:
        rigid.add(1 + kinds.index("steel"))
    if plastic_side in rigid:
        raise HTTPException(
            422,
            "the contact slave (plastic side) must stay deformable — "
            "only the mating gear can be an ideally stiff Außenhülle",
        )
    return {
        "gear1_material": deck_material(req.gear1_material),
        "gear2_material": deck_material(req.gear2_material),
        "rigid_gears": frozenset(rigid),
        "driven_gear": plastic_side,
        "slave_gear": plastic_side,
    }


@router.post("/deck-series")
def build_deck_series(req: DeckRequest) -> Response:
    """The position series (default mode): one INP per Wälzstellung as a ZIP.

    Contains ``pair_common.inp`` (shared mesh), ``pos_NNN.inp`` per position,
    ``manifest.json`` (angles/torque/files for the postprocessing) and run scripts.
    """
    import io
    import zipfile

    stage = req.stage.stage()
    roles = _deck_roles(req)
    files = build_position_series(
        stage,
        torque_gear2_nmm=req.torque_gear2_nmm,
        face_layers=req.face_layers,
        axial_offset_mm=(req.axial_offset_gear1_mm, req.axial_offset_gear2_mm),
        roll_pitches=req.roll_pitches,
        n_roll_positions=req.n_roll_positions,
        hold=req.hold,
        settle=req.settle,
        start_at_edge=req.start_at_edge,
        rotation_sense=req.rotation_sense,
        tip_relief=(req.stage.tip_relief(0), req.stage.tip_relief(1)),
        **_deck_refine(req),
        fillet_gear1=req.fillet_gear1.strategy(),
        fillet_gear2=req.fillet_gear2.strategy(),
        align_contact=req.align_contact,
        fasten_bore=req.fasten_bore,
        fasten_cuts=req.fasten_cuts,
        fasten_bottom=req.fasten_bottom,
        fasten_top=req.fasten_top,
        **roles,
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for name, content in files:
            zf.writestr(name, content)
    headers = {"Content-Disposition": "attachment; filename=rolling_position_series.zip"}
    return Response(buf.getvalue(), media_type="application/zip", headers=headers)


class PairGearOut(BaseModel):
    """One gear of the assembled pair, render-ready and positioned like the deck.

    ``vertices`` are absolute assembly coordinates at the CLOSED, CENTERED configuration
    (backlash-closing rotation baked in). The viewer animates the Wälzstellungen by rotating
    the gear about its own axis: φ_g(k) = ``start_angle_rad`` + k · ``step_angle_rad``
    (k = 0 … n_positions−1; position 0 = the edge-tooth start of the deck).
    """

    gear: int
    teeth: int
    center: list[float]  # [cx, cy] rotation-axis position in the assembly
    z_mid_mm: float  # mid-plane z (= axial offset; rotation node sits here)
    face_width_mm: float
    rigid_shell: bool
    n_elements: int  # hexes (solid) or R3D4 quads (rigid shell)
    vertices: list[float]  # x, y, z per surface vertex
    faces: list[int]  # 4 vertex indices per quad face
    start_angle_rad: float
    step_angle_rad: float


class PairAssemblyResponse(BaseModel):
    """THE deck assembly for the viewport (single source of truth, user point 3):
    exactly the geometry, positioning and roll schedule of the generated .inp."""

    center_distance_mm: float
    closing_rad: float  # backlash-closing rotation of gear 2 (baked into the vertices)
    driven_gear: int  # angle-driven gear (the plastic side)
    n_positions: int  # Wälzstellungen (measurement positions)
    roll_angle_rad: float  # driven gear total sweep (signed by the Drehrichtung)
    contact_pairs: list[str]  # slave surface, master surface
    gear1: PairGearOut
    gear2: PairGearOut


@router.post("/pair", response_model=PairAssemblyResponse)
def pair_assembly(req: DeckRequest) -> PairAssemblyResponse:
    """Both gears assembled EXACTLY like the deck (one code path — no viewport-local math).

    Runs the same :func:`assemble_centered_pair` the deck builders use (fillets, tip relief,
    rigid shells, closing rotation, sweep contact pairing) and returns the outer hulls plus
    the per-gear angle schedule of the roll (edge start + kinematic coupling).
    """
    stage = req.stage.stage()
    roles = _deck_roles(req)
    roll_sign = 1.0 if req.rotation_sense != "ccw" else -1.0
    driven = int(roles["driven_gear"])
    z = (stage.teeth[0], stage.teeth[1])
    roll_angle = roll_sign * req.roll_pitches * 2.0 * math.pi / z[driven - 1]
    try:
        pair = assemble_centered_pair(
            stage,
            gear1_material=roles["gear1_material"],
            gear2_material=roles["gear2_material"],
            face_layers=req.face_layers,
            face_width_mm=None,
            axial_offset_mm=(req.axial_offset_gear1_mm, req.axial_offset_gear2_mm),
            phase_rad=0.0,
            align_contact=req.align_contact,
            contact_gap_mm=None,
            roll_angle_rad=roll_angle,
            start_at_edge=req.start_at_edge,
            driven_gear=driven,
            slave_gear=int(roles["slave_gear"]),
            roll_sign=roll_sign,
            rigid_gears=roles["rigid_gears"],
            tip_relief=(req.stage.tip_relief(0), req.stage.tip_relief(1)),
            **_deck_refine(req),
            fillet_gear1=req.fillet_gear1.strategy(),
            fillet_gear2=req.fillet_gear2.strategy(),
            fasten_bore=req.fasten_bore,
            fasten_cuts=req.fasten_cuts,
            fasten_bottom=req.fasten_bottom,
            fasten_top=req.fasten_top,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    # per-gear angle schedule (mirrors build_implicit_pair_from_stage): the driven gear
    # starts at −roll/2 (edge tooth) and steps roll/(n−1); the other gear counter-rotates
    # kinematically by the tooth-count ratio
    n = req.n_roll_positions
    step_driven = roll_angle / max(n - 1, 1)
    start_driven = -roll_angle / 2.0 if req.start_at_edge else 0.0
    other = 3 - driven
    coupling = -z[driven - 1] / z[other - 1]

    def gear_out(part_gear: int) -> PairGearOut:
        part = pair.part1 if part_gear == 1 else pair.part2
        if part.shell_quads is not None:
            verts = part.mesh.nodes
            faces = [int(i) for quad in part.shell_quads for i in quad]
            n_elements = len(part.shell_quads)
        else:
            hull = _outer_hull(part.mesh.hexes)
            used = sorted({v for face, _ in hull for v in face})
            remap = {v: i for i, v in enumerate(used)}
            verts = part.mesh.nodes[used]
            faces = [remap[v] for face, _ in hull for v in face]
            n_elements = len(part.mesh.hexes)
        driven_side = part_gear == driven
        return PairGearOut(
            gear=part_gear,
            teeth=part.teeth,
            center=[round(part.center_xy[0], 6), round(part.center_xy[1], 6)],
            z_mid_mm=part.z_mid_mm,
            face_width_mm=part.face_width_mm,
            rigid_shell=part.shell_quads is not None,
            n_elements=n_elements,
            vertices=[round(float(v), 5) for v in verts.ravel()],
            faces=faces,
            start_angle_rad=start_driven if driven_side else start_driven * coupling,
            step_angle_rad=step_driven if driven_side else step_driven * coupling,
        )

    return PairAssemblyResponse(
        center_distance_mm=round(pair.a, 6),
        closing_rad=round(pair.closing_rad, 8),
        driven_gear=driven,
        n_positions=n,
        roll_angle_rad=roll_angle,
        contact_pairs=[f"{s}, {m}" for s, m in pair.pairs],
        gear1=gear_out(1),
        gear2=gear_out(2),
    )
