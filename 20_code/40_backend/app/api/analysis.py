"""
@module: app.api.analysis
@context: FastAPI backend — the gear-analysis HTTP surface for the frontend.
@role: Expose the domain services (geometry, ISO 6336 steel capacity, VDI 2736
       plastic capacity, native dynamics, the Stufenvariation) as JSON endpoints.
       The validated **kst-E** steel–plastic pair is preloaded as the working
       example; the frontend edits operating parameters and reads live results.
       (Extension points: a standard-gear example library and STplus/RIKOR import.)

Thin by design (project_rules §): the routes assemble inputs and delegate to
``app.services``; no computation lives here.
"""

from functools import lru_cache
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.io.ste import Pair, gear_stage_from_ste, load_ste
from app.services.capacity import (
    DynamicConditions,
    Iso6336Conditions,
    Iso6336LoadCase,
    RootMaterialGroup,
    Vdi2736Conditions,
    evaluate_iso6336,
    evaluate_vdi2736,
    native_dynamic_factors,
)
from app.services.geometry.gear import GearStage
from app.services.geometry.tooth_root import ToothRootGeometry
from app.services.materials import Material, MaterialKind
from app.services.variation import (
    VariationSpec,
    Varied,
    build_grid,
    build_sample,
    evaluate,
    pareto_front,
)

router = APIRouter(prefix="/api", tags=["analysis"])

# kst-E reference data lives outside the code tree (ADR-008); resolve from the repo root.
_KST_E_STE = (
    Path(__file__).resolve().parents[4]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)

# Materials of the kst-E pair (steel pinion 20MnCr5 + plastic wheel).
_STEEL = Material(
    name="20MnCr5",
    kind=MaterialKind.STEEL,
    elastic_modulus_mpa=210000.0,
    poisson_ratio=0.30,
    sigma_hlim_mpa=1500.0,
    sigma_flim_mpa=430.0,
)
_PLASTIC = Material(
    name="POM (Kunststoff)",
    kind=MaterialKind.PLASTIC,
    elastic_modulus_mpa=4156.0,
    poisson_ratio=0.34,
    sigma_hlim_mpa=60.0,
    sigma_flim_mpa=35.0,
)


@lru_cache(maxsize=1)
def _kst_e_stage() -> GearStage:
    if not _KST_E_STE.exists():
        raise HTTPException(503, f"example data not found at {_KST_E_STE}")
    return GearStage.from_ste(gear_stage_from_ste(load_ste(_KST_E_STE)))


def _kst_e_roots(stage: GearStage) -> Pair[ToothRootGeometry]:
    return Pair(ToothRootGeometry.from_stage(stage, 0), ToothRootGeometry.from_stage(stage, 1))


class ExampleGear(BaseModel):
    role: str
    material: str
    kind: str
    teeth: int
    profile_shift: float
    reference_diameter_mm: float
    tip_diameter_mm: float
    face_width_mm: float


class ExampleResponse(BaseModel):
    """The preloaded, validated kst-E steel–plastic pair (the working example)."""

    name: str
    description: str
    normal_module_mm: float
    normal_pressure_angle_deg: float
    helix_angle_deg: float
    center_distance_mm: float
    working_pressure_angle_deg: float
    transverse_contact_ratio: float
    overlap_ratio: float
    total_contact_ratio: float
    gears: list[ExampleGear]
    notes: list[str]


@router.get("/example/kst-e", response_model=ExampleResponse)
def example_kst_e() -> ExampleResponse:
    """The exact kst-E reference geometry (as cut), the basis for the capacity views."""
    stage = _kst_e_stage()
    ref = stage.reference_diameter_mm
    tip = stage.usable_tip_diameter_mm or Pair(0.0, 0.0)
    width = stage.face_width_mm or Pair(17.0, 15.0)
    roles = ("Pinion (steel)", "Wheel (plastic)")
    mats = ("20MnCr5", "POM (Kunststoff)")
    kinds = ("steel", "plastic")
    gears = [
        ExampleGear(
            role=roles[i],
            material=mats[i],
            kind=kinds[i],
            teeth=stage.teeth[i],
            profile_shift=round(stage.profile_shift[i], 4),
            reference_diameter_mm=round(ref[i], 3),
            tip_diameter_mm=round(tip[i], 3),
            face_width_mm=width[i],
        )
        for i in range(2)
    ]
    return ExampleResponse(
        name="kst-E",
        description="Steel–plastic spur pair (FZG standard test); the validated reference.",
        normal_module_mm=stage.normal_module_mm,
        normal_pressure_angle_deg=stage.normal_pressure_angle_deg,
        helix_angle_deg=stage.helix_angle_deg,
        center_distance_mm=stage.center_distance_mm or 52.0,
        working_pressure_angle_deg=round(stage.working_pressure_angle_deg, 4),
        transverse_contact_ratio=round(stage.transverse_contact_ratio, 4),
        overlap_ratio=round(stage.overlap_ratio, 4),
        total_contact_ratio=round(stage.total_contact_ratio, 4),
        gears=gears,
        notes=stage.check_validity(),
    )


# --------------------------------------------------------------------------- #
# Geometry (kernel-based; editable macro parameters)                           #
# --------------------------------------------------------------------------- #
class GeometryRequest(BaseModel):
    normal_module_mm: float = 1.0
    teeth_pinion: int = 51
    teeth_wheel: int = 52
    profile_shift_pinion: float = 0.2034
    profile_shift_wheel: float = 0.3143
    normal_pressure_angle_deg: float = 20.0
    helix_angle_deg: float = 0.0
    face_width_mm: float = 17.0


class GeometryResponse(BaseModel):
    reference_diameter_mm: list[float]
    base_diameter_mm: list[float]
    tip_diameter_mm: list[float]
    working_pressure_angle_deg: float
    working_center_distance_mm: float
    transverse_contact_ratio: float
    overlap_ratio: float
    total_contact_ratio: float
    valid: bool
    notes: list[str]


@router.post("/geometry", response_model=GeometryResponse)
def geometry(req: GeometryRequest) -> GeometryResponse:
    """Macro-geometry (diameters, contact ratios, α_wt) via the vectorized kernel."""
    from app.services.variation import kernel

    one = np.ones(1)
    geo = kernel.mesh_geometry(
        normal_module_mm=one * req.normal_module_mm,
        teeth_pinion=one * req.teeth_pinion,
        teeth_wheel=one * req.teeth_wheel,
        profile_shift_pinion=one * req.profile_shift_pinion,
        profile_shift_wheel=one * req.profile_shift_wheel,
        normal_pressure_angle=one * np.radians(req.normal_pressure_angle_deg),
        helix_angle=one * np.radians(req.helix_angle_deg),
        face_width_mm=one * req.face_width_mm,
    )
    notes: list[str] = []
    if geo.total_contact_ratio[0] < 1.0:
        notes.append("ε_γ < 1 — no continuous mesh.")
    if req.teeth_pinion < 14 and req.profile_shift_pinion < 0.3:
        notes.append("z₁ low — risk of undercut without enough profile shift.")
    return GeometryResponse(
        reference_diameter_mm=[
            float(geo.reference_diameter[0][0]),
            float(geo.reference_diameter[1][0]),
        ],
        base_diameter_mm=[float(geo.base_diameter[0][0]), float(geo.base_diameter[1][0])],
        tip_diameter_mm=[float(geo.tip_diameter[0][0]), float(geo.tip_diameter[1][0])],
        working_pressure_angle_deg=float(np.degrees(geo.working_pressure_angle[0])),
        working_center_distance_mm=float(geo.working_center_distance_mm[0]),
        transverse_contact_ratio=float(geo.transverse_contact_ratio[0]),
        overlap_ratio=float(geo.overlap_ratio[0]),
        total_contact_ratio=float(geo.total_contact_ratio[0]),
        valid=bool(geo.total_contact_ratio[0] >= 1.0),
        notes=notes,
    )


# --------------------------------------------------------------------------- #
# Capacity (kst-E: steel pinion → ISO 6336, plastic wheel → VDI 2736)          #
# --------------------------------------------------------------------------- #
class CapacityRequest(BaseModel):
    pinion_torque_nm: float = 7.85
    application_factor: float = 1.0
    power_w: float = 1848.7
    ambient_temperature_c: float = 80.0
    friction_coefficient: float = 0.04
    load_cycles: float = 1.324e7


class GearCapacity(BaseModel):
    label: str
    material: str
    method: str
    flank_stress_mpa: float
    flank_permissible_mpa: float | None = None
    flank_safety: float | None = None
    root_stress_mpa: float
    root_permissible_mpa: float | None = None
    root_safety: float | None = None
    form_factor: float
    stress_correction: float
    tooth_temperature_c: float | None = None
    wear_um: float | None = None
    allowable_wear_um: float | None = None
    deformation_mm: float | None = None


class CapacityResponse(BaseModel):
    pinion: GearCapacity
    wheel: GearCapacity


@router.post("/capacity", response_model=CapacityResponse)
def capacity(req: CapacityRequest) -> CapacityResponse:
    """Per-gear dispatch: steel pinion via ISO 6336, plastic wheel via VDI 2736."""
    stage = _kst_e_stage()
    roots = _kst_e_roots(stage)
    width = stage.face_width_mm or Pair(17.0, 15.0)
    f_t = 2000.0 * req.pinion_torque_nm / stage.reference_diameter_mm[0]
    materials = Pair(_STEEL, _PLASTIC)

    # steel pinion — ISO 6336
    iso_load = Iso6336LoadCase(
        tangential_force_n=f_t,
        common_face_width_mm=min(width),
        root_face_width_mm=width,
        gear_ratio=stage.teeth[1] / stage.teeth[0],
        pinion_reference_diameter_mm=stage.reference_diameter_mm[0],
        application_factor=req.application_factor,
    )
    iso_conditions = Iso6336Conditions(
        pitch_line_velocity_ms=6.067,
        lubricant_viscosity_40_mm2s=100.0,
        flank_roughness_rz_um=5.0,
        root_roughness_rz_um=Pair(5.0, 5.0),
        material_group=Pair(RootMaterialGroup.CASE_HARDENED, RootMaterialGroup.CASE_HARDENED),
    )
    iso = evaluate_iso6336(stage, roots, materials, iso_load, iso_conditions)
    pin = iso[0]
    pinion = GearCapacity(
        label="Pinion (steel)",
        material=_STEEL.name,
        method="ISO 6336:2019",
        flank_stress_mpa=round(pin.flank_stress_mpa, 3),
        flank_safety=_round(pin.flank_safety),
        root_stress_mpa=round(pin.root_stress_mpa, 3),
        root_safety=_round(pin.root_safety),
        form_factor=round(roots[0].form_factor, 4),
        stress_correction=round(roots[0].stress_correction_factor, 4),
    )

    # plastic wheel — VDI 2736
    vdi_conditions = Vdi2736Conditions(
        power_w=req.power_w,
        torque_nm=Pair(
            req.pinion_torque_nm, req.pinion_torque_nm * stage.teeth[1] / stage.teeth[0]
        ),
        pitch_velocity_ms=6.067,
        ambient_temperature_c=req.ambient_temperature_c,
        friction_coefficient=req.friction_coefficient,
        load_cycles=Pair(req.load_cycles, req.load_cycles),
    )
    vdi = evaluate_vdi2736(
        stage,
        roots,
        materials,
        vdi_conditions,
        root_face_width_mm=width,
        common_face_width_mm=min(width),
    )
    wh = vdi[1]
    wheel = GearCapacity(
        label="Wheel (plastic)",
        material=_PLASTIC.name,
        method="VDI 2736:2014",
        flank_stress_mpa=round(wh.flank_stress_mpa, 3),
        flank_safety=_round(wh.flank_safety),
        root_stress_mpa=round(wh.root_stress_mpa, 3),
        root_safety=_round(wh.root_safety),
        form_factor=round(roots[1].form_factor_tip, 4),
        stress_correction=round(roots[1].stress_correction_factor_tip, 4),
        tooth_temperature_c=round(wh.root_temperature_c, 2),
        wear_um=round(wh.linear_wear_um, 2),
        allowable_wear_um=round(wh.allowable_wear_um, 1),
        deformation_mm=round(wh.deformation_mm, 4),
    )
    return CapacityResponse(pinion=pinion, wheel=wheel)


# --------------------------------------------------------------------------- #
# Dynamics (native ISO 6336-1)                                                 #
# --------------------------------------------------------------------------- #
class DynamicsRequest(BaseModel):
    pinion_speed_min1: float = 1000.0
    pinion_torque_nm: float = 7.85
    application_factor: float = 1.0
    base_pitch_deviation_um: float = 6.0
    profile_form_deviation_um: float = 5.0


class DynamicsResponse(BaseModel):
    dynamic_factor: float
    transverse_factor_flank: float
    transverse_factor_root: float
    face_load_factor_flank: float
    mesh_stiffness: float
    reduced_mass: float
    resonance_speed_min1: float
    resonance_ratio: float
    regime: str


@router.post("/dynamics", response_model=DynamicsResponse)
def dynamics(req: DynamicsRequest) -> DynamicsResponse:
    """Native K_v (Method B), K_Hα, K_Hβ plus the resonance diagnostics."""
    stage = _kst_e_stage()
    roots = _kst_e_roots(stage)
    width = stage.face_width_mm or Pair(17.0, 15.0)
    f_t = 2000.0 * req.pinion_torque_nm / stage.reference_diameter_mm[0]
    load = Iso6336LoadCase(
        tangential_force_n=f_t,
        common_face_width_mm=min(width),
        root_face_width_mm=width,
        gear_ratio=stage.teeth[1] / stage.teeth[0],
        pinion_reference_diameter_mm=stage.reference_diameter_mm[0],
        application_factor=req.application_factor,
    )
    conditions = DynamicConditions(
        pinion_speed_min1=req.pinion_speed_min1,
        base_pitch_deviation_um=Pair(req.base_pitch_deviation_um, req.base_pitch_deviation_um),
        profile_form_deviation_um=Pair(
            req.profile_form_deviation_um, req.profile_form_deviation_um
        ),
    )
    f = native_dynamic_factors(stage, roots, Pair(_STEEL, _PLASTIC), load, conditions)
    regime = (
        "sub-critical"
        if f.resonance_ratio <= 0.85
        else ("main resonance" if f.resonance_ratio <= 1.15 else "super-critical")
    )
    return DynamicsResponse(
        dynamic_factor=round(f.dynamic_factor, 4),
        transverse_factor_flank=round(f.transverse_factor_flank, 4),
        transverse_factor_root=round(f.transverse_factor_root, 4),
        face_load_factor_flank=round(f.face_load_factor_flank, 4),
        mesh_stiffness=round(f.mesh_stiffness_alpha, 3),
        reduced_mass=round(f.reduced_mass, 6),
        resonance_speed_min1=round(f.resonance_speed, 1),
        resonance_ratio=round(f.resonance_ratio, 4),
        regime=regime,
    )


# --------------------------------------------------------------------------- #
# Stufenvariation (vectorized sweep + Pareto)                                  #
# --------------------------------------------------------------------------- #
class VariationRequest(BaseModel):
    normal_module_mm: float = 2.0
    teeth_wheel: int = 60
    profile_shift_wheel: float = 0.0
    torque_nm: float = 15.0
    teeth_pinion_min: int = 16
    teeth_pinion_max: int = 34
    teeth_pinion_steps: int = 19
    profile_shift_pinion_min: float = -0.3
    profile_shift_pinion_max: float = 0.6
    profile_shift_pinion_steps: int = 10
    face_width_mm: float = 20.0
    method: str = Field("grid", pattern="^(grid|sobol|lhs)$")
    sample_count: int = 256


class VariationPoint(BaseModel):
    teeth_pinion: float
    profile_shift_pinion: float
    total_contact_ratio: float
    root_safety_plastic: float | None
    flank_safety_plastic: float | None
    pareto: bool


class VariationResponse(BaseModel):
    count: int
    valid: int
    pareto: int
    eval_ms: float
    points: list[VariationPoint]
    warnings: list[str]


@router.post("/variation", response_model=VariationResponse)
def variation(req: VariationRequest) -> VariationResponse:
    """Run a plastic-capable Stufenvariation (steel pinion + plastic wheel)."""
    import time

    spec = VariationSpec(
        materials=(_STEEL, _PLASTIC),
        torque_nm=req.torque_nm,
        varied={
            "z1": Varied(
                values=tuple(
                    np.linspace(req.teeth_pinion_min, req.teeth_pinion_max, req.teeth_pinion_steps)
                ),
                bounds=(req.teeth_pinion_min, req.teeth_pinion_max),
            ),
            "x1": Varied(
                values=tuple(
                    np.linspace(
                        req.profile_shift_pinion_min,
                        req.profile_shift_pinion_max,
                        req.profile_shift_pinion_steps,
                    )
                ),
                bounds=(req.profile_shift_pinion_min, req.profile_shift_pinion_max),
            ),
        },
        fixed={
            "m_n": req.normal_module_mm,
            "z2": req.teeth_wheel,
            "x2": req.profile_shift_wheel,
            "b": req.face_width_mm,
        },
    )
    batch = (
        build_grid(spec)
        if req.method == "grid"
        else build_sample(spec, req.sample_count, method=req.method)
    )
    t = time.perf_counter()
    res = evaluate(spec, batch)
    eval_ms = (time.perf_counter() - t) * 1000.0

    valid = res.valid
    front = np.zeros(valid.shape, dtype=bool)
    if valid.any():
        sub = pareto_front(
            [res.root_safety[1][valid], res.flank_safety[1][valid], res.total_contact_ratio[valid]],
            maximize=[True, True, True],
        )
        front[np.flatnonzero(valid)[sub]] = True

    points = [
        VariationPoint(
            teeth_pinion=round(float(res.parameters["z1"][i]), 3),
            profile_shift_pinion=round(float(res.parameters["x1"][i]), 4),
            total_contact_ratio=round(float(res.total_contact_ratio[i]), 4),
            root_safety_plastic=_round(float(res.root_safety[1][i])),
            flank_safety_plastic=_round(float(res.flank_safety[1][i])),
            pareto=bool(front[i]),
        )
        for i in range(res.total_contact_ratio.size)
        if bool(valid[i])
    ]
    return VariationResponse(
        count=int(res.total_contact_ratio.size),
        valid=int(valid.sum()),
        pareto=int(front.sum()),
        eval_ms=round(eval_ms, 1),
        points=points,
        warnings=list(res.warnings),
    )


def _round(value: float | None, digits: int = 3) -> float | None:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return None
    return round(float(value), digits)
