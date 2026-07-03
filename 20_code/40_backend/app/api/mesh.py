"""
@module: app.api.mesh
@context: API layer — FE mesh preview/3D data + Abaqus deck download (plan v2, M4).
@role: Expose the ADR-019 transplant mesher over HTTP for the frontend mesh viewer:
       a 2-D sector preview (nodes, quads, per-element scaled Jacobian), a render-ready 3-D
       payload (outer surface faces of the extruded hex sector + per-face quality), the native
       density-convergence quick check, and the full implicit rolling deck as an ``.inp``
       download with the mixed-pairing material rule (steel side as ideally stiff rigid shell).
       Stateless: everything is computed from the request (kst-E example stage for now; the
       free-design stage plugs in via the same models in M6).
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Annotated, Literal

import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.api.analysis import _kst_e_stage
from app.io.ste import Pair
from app.services.geometry.gear import GearStage, ToolReferenceProfile
from app.services.geometry.root_fillet import (
    BezierFillet,
    BionicFillet,
    EllipticFillet,
    fillet_boundary,
    mating_tip_clearance,
)
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.implicit_deck import build_implicit_pair_from_stage
from app.services.model.materials_card import LinearElastic, MarlowUniaxial
from app.services.model.mesh3d import extrude_to_hex
from app.services.model.plane_fe import density_convergence, root_tensile_stress
from app.services.model.template_mesher import SectorMesh2D, generate_sector_2d, scaled_jacobians
from app.services.model.tooth_mesh import Mesh2D

router = APIRouter(prefix="/api/mesh", tags=["mesh"])


# ----------------------------------------------------------------------------------------------
# request models
# ----------------------------------------------------------------------------------------------
class FilletSpec(BaseModel):
    """Optimized root-fillet strategy selection (see geometry/root_fillet.py)."""

    kind: Literal["standard", "elliptic", "bezier", "bionic"] = "standard"
    e_f: Annotated[float, Field(ge=-0.5, le=0.2)] = 0.0  # elliptic root-diameter factor
    be: Annotated[float, Field(ge=0.3, le=0.95)] = 0.57  # Bézier factor (Roth/Voith)
    gamma_deg: Annotated[float, Field(gt=5.0, lt=65.0)] | None = None  # bionic wedge angle
    b_f: Annotated[float, Field(ge=0.1, le=0.6)] = 0.35  # bionic arc factor

    def strategy(self) -> EllipticFillet | BezierFillet | BionicFillet | None:
        if self.kind == "elliptic":
            return EllipticFillet(e_f=self.e_f)
        if self.kind == "bezier":
            return BezierFillet(be=self.be)
        if self.kind == "bionic":
            return BionicFillet(gamma_deg=self.gamma_deg, b_f=self.b_f)
        return None


class MeshRequest(BaseModel):
    """Mesh one gear of the (kst-E) stage with FVA density factors + fillet strategy."""

    gear: Literal[1, 2] = 1  # 1 = pinion (steel side), 2 = wheel (plastic side) — .ste order
    refine_root: int = Field(1, ge=1, le=3)
    refine_flank: int = Field(1, ge=1, le=3)
    fillet: FilletSpec = Field(default_factory=FilletSpec)
    bore_radius_mm: float | None = Field(None, gt=0.0)


class DeckRequest(BaseModel):
    """Full implicit rolling deck (both gears) as .inp text."""

    wheel_torque_nmm: float = Field(20000.0, gt=0.0)
    face_layers: int = Field(6, ge=1, le=80)
    n_roll_positions: int = Field(30, ge=1, le=200)
    refine_root: int = Field(1, ge=1, le=3)
    refine_flank: int = Field(1, ge=1, le=3)
    steel_shell: bool = Field(
        False,
        description="Mixed-pairing rule: steel gear as ideally stiff rigid body "
        "(saves DOFs; default False = reference-faithful deformable pair)",
    )
    fillet_wheel: FilletSpec = Field(default_factory=FilletSpec)


# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------
def _profile(gear: int) -> ToothProfile:
    return ToothProfile.from_stage(_kst_e_stage(), gear - 1)


def _sector(req: MeshRequest) -> tuple[ToothProfile, SectorMesh2D]:
    profile = _profile(req.gear)
    strategy = req.fillet.strategy()
    if strategy is not None:
        # Mandatory interference check before handing out an optimized fillet.
        stage = _kst_e_stage()
        mating = ToothProfile.from_stage(stage, 2 - req.gear)  # the other gear (0/1 index)
        fillet_pts = np.array([(p[0], p[1]) for p in strategy.right_half(profile)])
        clearance = mating_tip_clearance(
            profile,
            fillet_pts,
            mating_tip_radius_mm=(mating.d_a or mating.d_Na) / 2.0,
            mating_teeth=mating.z,
            mating_half_tip_rad=mating.half_thickness_angle((mating.d_a or mating.d_Na) / 2.0),
            centre_distance_mm=stage.working_center_distance_mm,
        )
        if clearance < 0.0:
            raise HTTPException(
                422,
                f"optimized fillet interferes with the mating tooth tip "
                f"(clearance {clearance:.3f} mm) — reduce the fillet parameter",
            )
    try:
        mesh = generate_sector_2d(
            profile,
            bore_radius_mm=req.bore_radius_mm,
            refine_root=req.refine_root,
            refine_flank=req.refine_flank,
            fillet=strategy,
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
    stage = _kst_e_stage()
    if face_width_mm is None:
        if stage.face_width_mm is None:
            raise HTTPException(422, "stage carries no face width; pass face_width_mm")
        face_width_mm = float(abs(stage.face_width_mm[req.gear - 1]))
    section = Mesh2D(mesh.points, np.asarray(mesh.quads, dtype=np.int64))
    quality = scaled_jacobians(mesh.coords, mesh.quads)
    m3 = extrude_to_hex(section, quality, width=face_width_mm, layers=layers)

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
        vertices=[round(float(v), 5) for v in verts.ravel()],
        faces=[remap[v] for face, _ in hull for v in face],
        face_quality=[round(float(qual[hi]), 4) for _, hi in hull],
    )


class ConvergenceRequest(BaseModel):
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
    profile = _profile(req.gear)
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


class FilletCompareResponse(BaseModel):
    """Quick-FE root-stress ranking of the fillet strategies (same load, same topology)."""

    gear: int
    names: list[str]
    sigma_mpa: list[float]
    delta_percent: list[float]
    clearance_mm: list[float]


@router.post("/fillet-compare", response_model=FilletCompareResponse)
def fillet_compare(gear: Literal[1, 2] = 1) -> FilletCompareResponse:
    """Rank standard / elliptic / Bézier / bionic fillets by quick-FE root stress."""
    stage = _kst_e_stage()
    profile = _profile(gear)
    mating = ToothProfile.from_stage(stage, 2 - gear)
    strategies: list[tuple[str, EllipticFillet | BezierFillet | BionicFillet | None]] = [
        ("standard", None),
        ("elliptic", EllipticFillet(e_f=-0.2)),
        ("bezier", BezierFillet(be=0.57)),
        ("bionic", BionicFillet()),
    ]
    names: list[str] = []
    sigmas: list[float] = []
    clearances: list[float] = []
    for name, strategy in strategies:
        mesh = generate_sector_2d(profile, fillet=strategy)
        sigmas.append(root_tensile_stress(mesh, profile).sigma_max_mpa)
        if strategy is None:
            boundary = np.array([(p[0], p[1]) for p in profile.transverse_right_boundary()])
            fillet_pts = boundary[
                np.hypot(boundary[:, 0], boundary[:, 1]) < profile.d_Ff / 2.0 + 1e-6
            ]
        else:
            fillet_pts = np.array([(p[0], p[1]) for p in strategy.right_half(profile)])
        clearances.append(
            mating_tip_clearance(
                profile,
                fillet_pts,
                mating_tip_radius_mm=(mating.d_a or mating.d_Na) / 2.0,
                mating_teeth=mating.z,
                mating_half_tip_rad=mating.half_thickness_angle((mating.d_a or mating.d_Na) / 2.0),
                centre_distance_mm=stage.working_center_distance_mm,
            )
        )
        names.append(name)
    ref = sigmas[0]
    return FilletCompareResponse(
        gear=gear,
        names=names,
        sigma_mpa=[round(s, 2) for s in sigmas],
        delta_percent=[round((s / ref - 1.0) * 100.0, 2) for s in sigmas],
        clearance_mm=[round(c, 3) for c in clearances],
    )


class ContourRequest(BaseModel):
    """Real as-cut tooth contour (plan v2, M5) — kst-E by default or free variant parameters.

    Free parameters use the standard tool (DIN 867 / ISO 53 A: h*_aP0 = 1.25, ρ*_aP0 = 0.38),
    so Stufenvariation variants can be drawn with their true generated root fillet.
    """

    gear: Literal[1, 2] = 2
    use_example: bool = True
    normal_module_mm: float = Field(1.0, gt=0.0)
    teeth_pinion: int = Field(51, ge=5)
    teeth_wheel: int = Field(52, ge=5)
    profile_shift_pinion: float = 0.2034
    profile_shift_wheel: float = 0.3143
    normal_pressure_angle_deg: float = Field(20.0, gt=5.0, lt=35.0)
    helix_angle_deg: float = 0.0
    face_width_mm: float = Field(15.0, gt=0.0)
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


def _stage_for(req: ContourRequest) -> GearStage:
    if req.use_example:
        return _kst_e_stage()
    tool = ToolReferenceProfile(addendum_factor=1.25, tip_radius_factor=0.38)
    try:
        return GearStage.from_parameters(
            normal_module_mm=req.normal_module_mm,
            teeth=Pair(req.teeth_pinion, req.teeth_wheel),
            profile_shift=Pair(req.profile_shift_pinion, req.profile_shift_wheel),
            face_width_mm=Pair(req.face_width_mm, req.face_width_mm),
            tool=Pair(tool, tool),
            normal_pressure_angle_deg=req.normal_pressure_angle_deg,
            helix_angle_deg=req.helix_angle_deg,
        )
    except (ValueError, ZeroDivisionError) as exc:
        raise HTTPException(422, f"invalid gear geometry: {exc}") from exc


@router.post("/contour", response_model=ContourResponse)
def tooth_contour(req: ContourRequest) -> ContourResponse:
    """The real generated tooth boundary (ρ_F fillet or optimized strategy, chamfer to d_a)."""
    stage = _stage_for(req)
    profile = ToothProfile.from_stage(stage, req.gear - 1)
    strategy = req.fillet.strategy()
    clearance: float | None = None
    if strategy is None:
        pts = profile.transverse_right_boundary(
            fillet_points=req.points // 3,
            flank_points=req.points - req.points // 3,
            to_tip_circle=True,
        )
    else:
        pts = fillet_boundary(
            profile, strategy, flank_points=req.points - req.points // 3, to_tip_circle=True
        )
        mating = ToothProfile.from_stage(stage, 2 - req.gear)
        fillet_pts = np.array([(p[0], p[1]) for p in strategy.right_half(profile)])
        clearance = float(
            mating_tip_clearance(
                profile,
                fillet_pts,
                mating_tip_radius_mm=(mating.d_a or mating.d_Na) / 2.0,
                mating_teeth=mating.z,
                mating_half_tip_rad=mating.half_thickness_angle((mating.d_a or mating.d_Na) / 2.0),
                centre_distance_mm=stage.working_center_distance_mm,
            )
        )
        if clearance < 0.0:
            raise HTTPException(
                422,
                f"optimized fillet interferes with the mating tooth tip "
                f"(clearance {clearance:.3f} mm)",
            )
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
    """The full implicit rolling deck (.inp) for the kst-E pair with the requested options."""
    stage = _kst_e_stage()
    deck = build_implicit_pair_from_stage(
        stage,
        plastic_material=MarlowUniaxial("PA_kstE"),
        steel_material=LinearElastic("STEEL", 210000.0, 0.3),
        wheel_torque_nmm=req.wheel_torque_nmm,
        face_layers=req.face_layers,
        n_roll_positions=req.n_roll_positions,
        refine_root=req.refine_root,
        refine_flank=req.refine_flank,
        steel_shell=req.steel_shell,
        fillet1=req.fillet_wheel.strategy(),  # part 1 = plastic wheel (kst-E contract)
    )
    pitch_deg = math.degrees(2.0 * math.pi / _profile(1).z)
    headers = {
        "Content-Disposition": "attachment; filename=kst-e_implicit_generated.inp",
        "X-Roll-Pitch-Deg": f"{pitch_deg:.4f}",
    }
    return PlainTextResponse(deck, media_type="text/plain", headers=headers)
