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
from typing import Annotated, Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.api.stage_params import StageParams
from app.services.geometry.gear import GearStage
from app.services.geometry.root_fillet import (
    BezierFillet,
    BionicFillet,
    EllipticFillet,
    FilletStrategy,
    TrochoidFillet,
    fillet_boundary,
    mating_tip_clearance,
    with_root_land,
)
from app.services.geometry.tooth_form import ToothProfile
from app.services.materials import catalog_material
from app.services.model.implicit_deck import build_implicit_pair_from_stage, build_position_series
from app.services.model.materials_card import LinearElastic, MarlowUniaxial, card_from_catalog
from app.services.model.mesh3d import extrude_to_hex
from app.services.model.plane_fe import density_convergence, root_tensile_stress
from app.services.model.template_mesher import SectorMesh2D, generate_sector_2d, scaled_jacobians
from app.services.model.tooth_mesh import Mesh2D

router = APIRouter(prefix="/api/mesh", tags=["mesh"])


# ----------------------------------------------------------------------------------------------
# request models
# ----------------------------------------------------------------------------------------------
class FilletSpec(BaseModel):
    """Root-fillet strategy selection (see geometry/root_fillet.py).

    ``standard`` = the ρ_F arc; ``trochoid`` = the exact DIN 3960 tool trochoid; the optimized
    shapes (molded/WEDM gears only) carry their literature parameters.
    """

    kind: Literal["standard", "trochoid", "elliptic", "bezier", "bionic"] = "standard"
    e_f: Annotated[float, Field(ge=-0.5, le=0.2)] = 0.0  # elliptic root-diameter factor
    be: Annotated[float, Field(ge=0.3, le=0.95)] = 0.57  # Bézier factor (Roth/Voith)
    gamma_deg: Annotated[float, Field(gt=5.0, lt=65.0)] | None = None  # bionic wedge angle
    b_f: Annotated[float, Field(ge=0.1, le=0.6)] = 0.35  # bionic arc factor

    def strategy(self) -> FilletStrategy | None:
        if self.kind == "trochoid":
            return TrochoidFillet()
        if self.kind == "elliptic":
            return EllipticFillet(e_f=self.e_f)
        if self.kind == "bezier":
            return BezierFillet(be=self.be)
        if self.kind == "bionic":
            return BionicFillet(gamma_deg=self.gamma_deg, b_f=self.b_f)
        return None


class MeshRequest(BaseModel):
    """Mesh one gear of the stage with FVA density factors + fillet strategy."""

    stage: StageParams = Field(default_factory=StageParams)
    gear: Literal[1, 2] = 1  # input slot: 1 = the stage's first gear, 2 = the second (ADR-021)
    refine_root: int = Field(1, ge=1, le=3)
    refine_flank: int = Field(1, ge=1, le=3)
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
    refine_root: int = Field(1, ge=1, le=3)
    refine_flank: int = Field(1, ge=1, le=3)
    gear1_material: Literal["steel", "plastic"] = "steel"
    gear2_material: Literal["steel", "plastic"] = "plastic"
    axial_offset_gear1_mm: float = Field(0.0, ge=-50.0, le=50.0)
    axial_offset_gear2_mm: float = Field(0.0, ge=-50.0, le=50.0)
    steel_shell: bool = Field(
        False,
        description="Mixed-pairing rule: the steel side as ideally stiff rigid body "
        "(saves DOFs; only effective for mixed pairings; default False = "
        "reference-faithful deformable pair)",
    )
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
    """(stage, this gear's profile, mating profile) for a 1-based gear index."""
    stage = stage_params.stage()
    return (
        stage,
        ToothProfile.from_stage(stage, gear - 1),
        ToothProfile.from_stage(stage, 2 - gear),
    )


def _clearance(
    stage: GearStage, profile: ToothProfile, mating: ToothProfile, strategy: FilletStrategy
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
) -> tuple[FilletStrategy | None, float | None]:
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
    )


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

    # Outer hull: hex faces used exactly once. C3D8 face node patterns (bottom, top, 4 sides).
    patterns = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    count: dict[frozenset[int], int] = defaultdict(int)
    keeper: dict[frozenset[int], tuple[tuple[int, ...], int]] = {}
    for hi, hexa in enumerate(m3.hexes):
        for pat in patterns:
            face = tuple(int(hexa[p]) for p in pat)
            key = frozenset(face)
            count[key] += 1
            keeper[key] = (face, hi)
    hull = [keeper[k] for k, c in count.items() if c == 1]

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


class FilletCompareResponse(BaseModel):
    """Quick-FE root-stress ranking of the fillet strategies (same load, same topology)."""

    gear: int
    names: list[str]
    sigma_mpa: list[float]
    delta_percent: list[float]
    clearance_mm: list[float]


@router.post("/fillet-compare", response_model=FilletCompareResponse)
def fillet_compare(req: FilletCompareRequest) -> FilletCompareResponse:
    """Rank standard / trochoid / elliptic / Bézier / bionic fillets by quick-FE root stress."""
    stage, profile, mating = _profiles(req.stage, req.gear)
    strategies: list[tuple[str, FilletStrategy | None]] = [
        ("standard", None),
        ("trochoid", TrochoidFillet()),
        ("elliptic", EllipticFillet(e_f=-0.2)),
        ("bezier", BezierFillet(be=0.57)),
        ("bionic", BionicFillet()),
    ]
    names: list[str] = []
    sigmas: list[float] = []
    clearances: list[float] = []
    for name, strategy in strategies:
        try:
            mesh = generate_sector_2d(profile, fillet=strategy)
        except ValueError:
            continue  # a strategy that fails on this geometry is simply omitted
        sigmas.append(root_tensile_stress(mesh, profile).sigma_max_mpa)
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
    """Sweep ONE strategy's shape parameter with the quick-FE objective (Variation axis)."""

    stage: StageParams = Field(default_factory=StageParams)
    gear: Literal[1, 2] = 2
    kind: Literal["elliptic", "bezier", "bionic"] = "bezier"
    points: int = Field(6, ge=3, le=12)


class FilletSweepResponse(BaseModel):
    gear: int
    kind: str
    parameter: str
    values: list[float]
    sigma_mpa: list[float]
    clearance_mm: list[float]
    feasible: list[bool]  # clearance > 0 and gates met
    best_value: float | None
    best_sigma_mpa: float | None
    standard_sigma_mpa: float


@router.post("/fillet-sweep", response_model=FilletSweepResponse)
def fillet_sweep(req: FilletSweepRequest) -> FilletSweepResponse:
    """σ_F quick-FE over the strategy's parameter range; recommends the feasible optimum."""
    stage, profile, mating = _profiles(req.stage, req.gear)
    standard = root_tensile_stress(generate_sector_2d(profile), profile).sigma_max_mpa
    ranges: dict[str, tuple[str, np.ndarray]] = {
        "elliptic": ("e_f", np.linspace(-0.4, 0.0, req.points)),
        "bezier": ("be", np.linspace(0.42, 0.9, req.points)),
        "bionic": ("b_f", np.linspace(0.15, 0.55, req.points)),
    }
    param, values = ranges[req.kind]
    sigmas: list[float] = []
    clearances: list[float] = []
    feasible: list[bool] = []
    for v in values:
        strategy: FilletStrategy = (
            EllipticFillet(e_f=float(v))
            if req.kind == "elliptic"
            else BezierFillet(be=float(v))
            if req.kind == "bezier"
            else BionicFillet(b_f=float(v))
        )
        try:
            clearance = _clearance(stage, profile, mating, strategy)
            mesh = generate_sector_2d(
                profile, fillet=strategy, mirror_symmetric=req.stage.mirror_symmetric(req.gear)
            )
            sj = scaled_jacobians(mesh.coords, mesh.quads)
            ok = clearance > 0.0 and float(sj.min()) >= 0.35
            sigma = root_tensile_stress(mesh, profile).sigma_max_mpa
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
        parameter=param,
        values=[round(float(v), 4) for v in values],
        sigma_mpa=[s if not math.isnan(s) else -1.0 for s in sigmas],
        clearance_mm=[c if not math.isnan(c) else -99.0 for c in clearances],
        feasible=feasible,
        best_value=round(float(values[best_i]), 4) if best_i is not None else None,
        best_sigma_mpa=sigmas[best_i] if best_i is not None else None,
        standard_sigma_mpa=round(standard, 2),
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
        refine_root=req.refine_root,
        refine_flank=req.refine_flank,
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
    rigid_gears: frozenset[int] = frozenset()
    if req.steel_shell and "plastic" in kinds and "steel" in kinds:
        rigid_gears = frozenset({1 + kinds.index("steel")})
    return {
        "gear1_material": deck_material(req.gear1_material),
        "gear2_material": deck_material(req.gear2_material),
        "rigid_gears": rigid_gears,
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
        refine_root=req.refine_root,
        refine_flank=req.refine_flank,
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
