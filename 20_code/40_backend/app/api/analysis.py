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

import math
import os
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
from app.services.geometry.gear import GearStage, ToolReferenceProfile
from app.services.geometry.tolerances import (
    FlankTolerances,
    dynamics_deviations,
    flank_tolerances,
    validity_warnings,
)
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


def _example_ste_path() -> Path | None:
    """Locate the kst-E example .ste robustly (env override → bundled → dev tree).

    The image bundles a small copy at ``app/examples/`` so the demo works
    self-contained; in the dev checkout the reference tree (outside the code tree,
    ADR-008) is used if present. Never raises at import — resolved lazily.
    """
    override = os.environ.get("EXAMPLE_DATA_FILE")
    if override:
        path = Path(override)
        return path if path.exists() else None
    here = Path(__file__).resolve()
    candidates = [here.parent.parent / "examples" / "kst-E_eingabe.ste"]
    parents = here.parents
    if len(parents) > 4:  # dev checkout: <repo>/20_code/40_backend/app/api/analysis.py
        candidates.append(
            parents[4] / "30_references_and_examples" / "33_STplus" / "kst-E_eingabe.ste"
        )
    return next((c for c in candidates if c.exists()), None)


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
    path = _example_ste_path()
    if path is None:
        raise HTTPException(503, "example data (kst-E .ste) not found; set EXAMPLE_DATA_FILE")
    return GearStage.from_ste(gear_stage_from_ste(load_ste(path)))


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
    roles = ("Ritzel (Stahl)", "Rad (Kunststoff)")
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
        description="Stahl-Kunststoff-Stirnradpaar (FZG-Standardtest); die validierte Referenz.",
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
# Tolerances (ISO 1328-1:2018 — accuracy grade → flank deviations)             #
# --------------------------------------------------------------------------- #
class ToleranceRequest(BaseModel):
    accuracy_grade: int = 6  # ISO 1328-1 flank class (1…11)
    normal_module_mm: float = 2.0
    teeth: int = 24
    reference_diameter_mm: float = 48.0
    face_width_mm: float = 20.0
    helix_angle_deg: float = 0.0


class ToleranceResponse(BaseModel):
    tolerances: FlankTolerances
    base_pitch_deviation_um: float  # f_pb (= f_ptT) for the dynamics
    profile_form_deviation_um: float  # f_fα (= f_fαT)
    warnings: list[str]


@router.post("/tolerances", response_model=ToleranceResponse)
def tolerances(req: ToleranceRequest) -> ToleranceResponse:
    """Flank deviations from the accuracy grade (ISO 1328-1:2018, eq. 5–12)."""
    t = flank_tolerances(
        accuracy_grade=req.accuracy_grade,
        normal_module_mm=req.normal_module_mm,
        reference_diameter_mm=req.reference_diameter_mm,
        face_width_mm=req.face_width_mm,
    )
    return ToleranceResponse(
        tolerances=t,
        base_pitch_deviation_um=t.single_pitch,
        profile_form_deviation_um=t.profile_form,
        warnings=validity_warnings(
            accuracy_grade=req.accuracy_grade,
            teeth=req.teeth,
            reference_diameter_mm=req.reference_diameter_mm,
            normal_module_mm=req.normal_module_mm,
            face_width_mm=req.face_width_mm,
            helix_angle_deg=req.helix_angle_deg,
        ),
    )


# --------------------------------------------------------------------------- #
# Capacity (kst-E: steel pinion → ISO 6336, plastic wheel → VDI 2736)          #
# --------------------------------------------------------------------------- #
class CapacityRequest(BaseModel):
    # --- load & application (Welle / Getriebeeinheit) ---
    pinion_torque_nm: float = 7.85  # T_1
    pinion_speed_min1: float = 1000.0  # n_1
    application_factor: float = 1.0  # K_A
    # --- dynamics (ISO 6336-1): native K_v from accuracy, or override ---
    compute_dynamics: bool = True
    dynamic_factor: float = 1.0  # K_v (override when compute_dynamics = False)
    face_load_factor: float = 1.0  # K_Hβ (override; native K_Hβ needs RIKOR)
    accuracy_grade: int | None = None  # ISO 1328-1 class; if set, derives f_pb/f_fα
    base_pitch_deviation_um: float = 6.0  # f_pb (ISO 1328) — used when no grade given
    profile_form_deviation_um: float = 5.0  # f_fα
    # --- ISO 6336 conditions (steel) ---
    lubricant_viscosity_40_mm2s: float = 100.0  # ν_40
    flank_roughness_rz_um: float = 5.0  # R_zH
    root_roughness_rz_um: float = 20.0  # R_zF
    flank_life_factor: float = 1.0  # Z_NT
    root_life_factor: float = 1.0  # Y_NT
    # --- steel material ---
    steel_modulus_mpa: float = 210000.0
    steel_poisson: float = 0.30
    steel_sigma_hlim_mpa: float = 1500.0
    steel_sigma_flim_mpa: float = 430.0
    # --- VDI 2736 (plastic) conditions ---
    power_w: float = 1848.7  # P
    ambient_temperature_c: float = 80.0  # ϑ_0
    duty_cycle: float = 1.0  # ED
    housing_surface_m2: float = 0.010  # A_G
    friction_coefficient: float = 0.04  # μ
    wear_coefficient_e6: float = 1.0  # k_W × 1e-6 mm³/(N·m)
    load_cycles: float = 1.324e7  # N_L
    root_minimum_safety: float = 2.0  # S_Fmin
    flank_minimum_safety: float = 1.4  # S_Hmin
    # --- plastic material ---
    plastic_modulus_mpa: float = 4156.0
    plastic_poisson: float = 0.34
    plastic_sigma_hlim_mpa: float = 60.0
    plastic_sigma_flim_mpa: float = 35.0


class CapacityFactors(BaseModel):
    application_factor: float  # K_A
    dynamic_factor: float  # K_v
    transverse_factor: float  # K_Hα
    face_load_factor: float  # K_Hβ
    elasticity_factor: float  # Z_E
    zone_factor: float  # Z_H


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
    factors: CapacityFactors
    pinion: GearCapacity
    wheel: GearCapacity


def _materials(req: CapacityRequest) -> Pair[Material]:
    return Pair(
        Material(
            name="20MnCr5",
            kind=MaterialKind.STEEL,
            elastic_modulus_mpa=req.steel_modulus_mpa,
            poisson_ratio=req.steel_poisson,
            sigma_hlim_mpa=req.steel_sigma_hlim_mpa,
            sigma_flim_mpa=req.steel_sigma_flim_mpa,
        ),
        Material(
            name="POM (Kunststoff)",
            kind=MaterialKind.PLASTIC,
            elastic_modulus_mpa=req.plastic_modulus_mpa,
            poisson_ratio=req.plastic_poisson,
            sigma_hlim_mpa=req.plastic_sigma_hlim_mpa,
            sigma_flim_mpa=req.plastic_sigma_flim_mpa,
        ),
    )


@router.post("/capacity", response_model=CapacityResponse)
def capacity(req: CapacityRequest) -> CapacityResponse:
    """Per-gear dispatch on the preloaded kst-E reference (operating values editable)."""
    stage = _kst_e_stage()
    return _run_capacity(stage, _kst_e_roots(stage), _materials(req), req)


def _run_capacity(
    stage: GearStage,
    roots: Pair[ToothRootGeometry],
    materials: Pair[Material],
    req: CapacityRequest,
) -> CapacityResponse:
    """Steel pinion via ISO 6336, plastic wheel via VDI 2736; native dynamics.

    Works for any generated stage (the preloaded kst-E or a free `from_parameters`).
    """
    from app.services.capacity.iso6336 import elasticity_factor, zone_factor

    width = stage.face_width_mm or Pair(17.0, 15.0)
    u = stage.teeth[1] / stage.teeth[0]
    v_t = math.pi * stage.reference_diameter_mm[0] * req.pinion_speed_min1 / 60000.0
    f_t = 2000.0 * req.pinion_torque_nm / stage.reference_diameter_mm[0]

    base_load = Iso6336LoadCase(
        tangential_force_n=f_t,
        common_face_width_mm=min(width),
        root_face_width_mm=width,
        gear_ratio=u,
        pinion_reference_diameter_mm=stage.reference_diameter_mm[0],
        application_factor=req.application_factor,
    )

    # accuracy deviations: from the quality grade (ISO 1328-1) or the raw µm inputs
    if req.accuracy_grade is not None:
        f_pb, f_fa = dynamics_deviations(
            accuracy_grade=req.accuracy_grade,
            normal_module_mm=stage.normal_module_mm,
            reference_diameter_mm=stage.reference_diameter_mm[0],
        )
    else:
        f_pb, f_fa = req.base_pitch_deviation_um, req.profile_form_deviation_um

    # --- dynamics: native K_v / K_Hα, or override ---
    if req.compute_dynamics:
        dyn = native_dynamic_factors(
            stage,
            roots,
            materials,
            base_load,
            DynamicConditions(
                pinion_speed_min1=req.pinion_speed_min1,
                base_pitch_deviation_um=Pair(f_pb, f_pb),
                profile_form_deviation_um=Pair(f_fa, f_fa),
            ),
        )
        k_v, k_ha = dyn.dynamic_factor, dyn.transverse_factor_flank
    else:
        k_v, k_ha = req.dynamic_factor, 1.0
    k_hb = req.face_load_factor

    iso_load = base_load.model_copy(
        update={
            "dynamic_factor": k_v,
            "face_load_factor_flank": k_hb,
            "face_load_factor_root": k_hb,
            "transverse_factor_flank": k_ha,
            "transverse_factor_root": k_ha,
        }
    )
    iso_conditions = Iso6336Conditions(
        pitch_line_velocity_ms=v_t,
        lubricant_viscosity_40_mm2s=req.lubricant_viscosity_40_mm2s,
        flank_roughness_rz_um=req.flank_roughness_rz_um,
        root_roughness_rz_um=Pair(req.root_roughness_rz_um, req.root_roughness_rz_um),
        material_group=Pair(RootMaterialGroup.CASE_HARDENED, RootMaterialGroup.CASE_HARDENED),
        flank_life_factor=Pair(req.flank_life_factor, req.flank_life_factor),
        root_life_factor=Pair(req.root_life_factor, req.root_life_factor),
    )
    iso = evaluate_iso6336(stage, roots, materials, iso_load, iso_conditions)
    pin = iso[0]
    pinion = GearCapacity(
        label="Ritzel (Stahl)",
        material=materials[0].name,
        method="ISO 6336:2019",
        flank_stress_mpa=round(pin.flank_stress_mpa, 3),
        flank_safety=_round(pin.flank_safety),
        root_stress_mpa=round(pin.root_stress_mpa, 3),
        root_safety=_round(pin.root_safety),
        flank_permissible_mpa=_round(_safe_mul(pin.flank_safety, pin.flank_stress_mpa)),
        root_permissible_mpa=_round(_safe_mul(pin.root_safety, pin.root_stress_mpa)),
        form_factor=round(roots[0].form_factor, 4),
        stress_correction=round(roots[0].stress_correction_factor, 4),
    )

    # plastic wheel — VDI 2736 (load factor K = K_A·K_v)
    k_load = req.application_factor * k_v
    vdi_conditions = Vdi2736Conditions(
        power_w=req.power_w,
        torque_nm=Pair(req.pinion_torque_nm, req.pinion_torque_nm * u),
        pitch_velocity_ms=v_t,
        ambient_temperature_c=req.ambient_temperature_c,
        duty_cycle=req.duty_cycle,
        housing_surface_m2=req.housing_surface_m2,
        friction_coefficient=req.friction_coefficient,
        load_cycles=Pair(req.load_cycles, req.load_cycles),
        wear_coefficient_mm3_nm=req.wear_coefficient_e6 * 1.0e-6,
        root_minimum_safety=req.root_minimum_safety,
        flank_minimum_safety=req.flank_minimum_safety,
        load_factor_root=k_load,
        load_factor_flank=k_load,
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
        label="Rad (Kunststoff)",
        material=materials[1].name,
        method="VDI 2736:2014",
        flank_stress_mpa=round(wh.flank_stress_mpa, 3),
        flank_safety=_round(wh.flank_safety),
        root_stress_mpa=round(wh.root_stress_mpa, 3),
        root_safety=_round(wh.root_safety),
        flank_permissible_mpa=_round(_safe_mul(wh.flank_safety, wh.flank_stress_mpa)),
        root_permissible_mpa=_round(_safe_mul(wh.root_safety, wh.root_stress_mpa)),
        form_factor=round(roots[1].form_factor_tip, 4),
        stress_correction=round(roots[1].stress_correction_factor_tip, 4),
        tooth_temperature_c=round(wh.root_temperature_c, 2),
        wear_um=round(wh.linear_wear_um, 2),
        allowable_wear_um=round(wh.allowable_wear_um, 1),
        deformation_mm=round(wh.deformation_mm, 4),
    )
    factors = CapacityFactors(
        application_factor=round(req.application_factor, 3),
        dynamic_factor=round(k_v, 4),
        transverse_factor=round(k_ha, 4),
        face_load_factor=round(k_hb, 4),
        elasticity_factor=round(elasticity_factor(materials[0], materials[1]), 3),
        zone_factor=round(zone_factor(stage), 4),
    )
    return CapacityResponse(factors=factors, pinion=pinion, wheel=wheel)


def _safe_mul(safety: float | None, stress: float) -> float | None:
    return safety * stress if safety is not None else None


# --------------------------------------------------------------------------- #
# Free geometry → capacity (any gear, built from raw parameters + tool profile) #
# --------------------------------------------------------------------------- #
class EvaluateRequest(BaseModel):
    # geometry
    normal_module_mm: float = 2.0
    teeth_pinion: int = 24
    teeth_wheel: int = 60
    profile_shift_pinion: float = 0.2
    profile_shift_wheel: float = 0.2
    normal_pressure_angle_deg: float = 20.0
    helix_angle_deg: float = 0.0
    center_distance_mm: float | None = None
    face_width_pinion_mm: float = 20.0
    face_width_wheel_mm: float = 20.0
    # rack-tool reference profile (shared by both gears)
    tool_addendum_factor: float = 1.25  # h_aP0*
    tool_tip_radius_factor: float = 0.38  # ρ_aP0*
    tool_dedendum_factor: float | None = None  # h_fP0*
    tool_root_form_height_factor: float | None = None  # h_FfP0*
    tool_edge_break_angle_deg: float | None = None  # α_Kn0 (tip chamfer)
    gear_addendum_factor: float = 1.0  # for d_a when no tip diameter is given
    tip_diameter_pinion_mm: float | None = None
    tip_diameter_wheel_mm: float | None = None
    tooth_width_allowance_pinion_mm: float = 0.0  # mean A_We → x_E
    tooth_width_allowance_wheel_mm: float = 0.0
    # operating + material (reuses the capacity inputs)
    operating: CapacityRequest = CapacityRequest()


class GeometrySummary(BaseModel):
    working_pressure_angle_deg: float
    center_distance_mm: float
    reference_diameter_mm: list[float]
    tip_diameter_mm: list[float]
    transverse_contact_ratio: float
    overlap_ratio: float
    total_contact_ratio: float
    span_measurement_mm: list[float] | None
    notes: list[str]


class EvaluateResponse(BaseModel):
    geometry: GeometrySummary
    capacity: CapacityResponse


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_custom(req: EvaluateRequest) -> EvaluateResponse:
    """Build any gear pair from raw parameters + tool profile, then geometry + capacity."""
    tool = ToolReferenceProfile(
        addendum_factor=req.tool_addendum_factor,
        tip_radius_factor=req.tool_tip_radius_factor,
        dedendum_factor=req.tool_dedendum_factor,
        root_form_height_factor=req.tool_root_form_height_factor,
        normal_pressure_angle_deg=req.normal_pressure_angle_deg,
        edge_break_angle_deg=req.tool_edge_break_angle_deg,
    )
    tip = (
        Pair(req.tip_diameter_pinion_mm, req.tip_diameter_wheel_mm)
        if req.tip_diameter_pinion_mm is not None and req.tip_diameter_wheel_mm is not None
        else None
    )
    try:
        stage = GearStage.from_parameters(
            normal_module_mm=req.normal_module_mm,
            teeth=Pair(req.teeth_pinion, req.teeth_wheel),
            profile_shift=Pair(req.profile_shift_pinion, req.profile_shift_wheel),
            face_width_mm=Pair(req.face_width_pinion_mm, req.face_width_wheel_mm),
            tool=Pair(tool, tool),
            normal_pressure_angle_deg=req.normal_pressure_angle_deg,
            helix_angle_deg=req.helix_angle_deg,
            center_distance_mm=req.center_distance_mm,
            tip_diameter_mm=tip,
            gear_addendum_factor=req.gear_addendum_factor,
            tooth_width_allowance_mm=Pair(
                req.tooth_width_allowance_pinion_mm, req.tooth_width_allowance_wheel_mm
            ),
        )
        roots = Pair(ToothRootGeometry.from_stage(stage, 0), ToothRootGeometry.from_stage(stage, 1))
    except (ValueError, ZeroDivisionError) as exc:
        raise HTTPException(422, f"invalid gear geometry: {exc}") from exc

    materials = _materials(req.operating)
    cap = _run_capacity(stage, roots, materials, req.operating)
    span = stage.span_measurement_mm
    geo = GeometrySummary(
        working_pressure_angle_deg=round(stage.working_pressure_angle_deg, 4),
        center_distance_mm=round(stage.working_center_distance_mm, 3),
        reference_diameter_mm=[round(stage.reference_diameter_mm[i], 3) for i in range(2)],
        tip_diameter_mm=[
            round((stage.usable_tip_diameter_mm or Pair(0.0, 0.0))[i], 3) for i in range(2)
        ],
        transverse_contact_ratio=round(stage.transverse_contact_ratio, 4),
        overlap_ratio=round(stage.overlap_ratio, 4),
        total_contact_ratio=round(stage.total_contact_ratio, 4),
        span_measurement_mm=[round(span[i], 3) for i in range(2)] if span is not None else None,
        notes=stage.check_validity(),
    )
    return EvaluateResponse(geometry=geo, capacity=cap)


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
class VarSpec(BaseModel):
    """One swept/fixed macro parameter (the Workbench Stufenvariation matrix row)."""

    vary: bool = False
    value: float
    min: float
    max: float
    steps: int = 6


class VariationRequest(BaseModel):
    # the macro-geometry matrix (vary → min/max/steps, else fixed at value)
    m_n: VarSpec = VarSpec(value=2.0, min=1.0, max=4.0)
    z1: VarSpec = VarSpec(value=24, min=16, max=34, vary=True, steps=19)
    z2: VarSpec = VarSpec(value=60, min=40, max=80)
    x1: VarSpec = VarSpec(value=0.0, min=-0.3, max=0.6, vary=True, steps=10)
    x2: VarSpec = VarSpec(value=0.0, min=-0.3, max=0.6)
    beta_deg: VarSpec = VarSpec(value=0.0, min=0.0, max=25.0)
    b: VarSpec = VarSpec(value=20.0, min=10.0, max=40.0)
    # center-distance coupling: hold a fixed → teeth locked, x₂ derived from a
    fix_center_distance: bool = False
    center_distance_mm: float = 80.0
    # fixed design context
    normal_pressure_angle_deg: float = 20.0
    tool_addendum_factor: float = 1.25  # h_aP0*
    tool_tip_radius_factor: float = 0.38  # ρ_aP0*
    torque_nm: float = 15.0
    steel_density_kg_m3: float = 7800.0
    plastic_density_kg_m3: float = 1400.0
    steel_sigma_hlim_mpa: float = 1500.0
    steel_sigma_flim_mpa: float = 430.0
    plastic_sigma_hlim_mpa: float = 60.0
    plastic_sigma_flim_mpa: float = 35.0
    root_minimum_safety: float = 2.0
    flank_minimum_safety: float = 1.0
    method: str = Field("grid", pattern="^(grid|sobol|lhs)$")
    sample_count: int = 256


class VariationPoint(BaseModel):
    m_n: float
    z1: float
    z2: float
    x1: float
    x2: float
    beta_deg: float
    b: float
    center_distance_mm: float
    transverse_contact_ratio: float
    overlap_ratio: float
    total_contact_ratio: float
    root_safety_pinion: float | None
    root_safety_wheel: float | None
    flank_safety_pinion: float | None
    flank_safety_wheel: float | None
    weight_g: float
    pareto: bool


class VariationResponse(BaseModel):
    count: int
    valid: int
    pareto: int
    eval_ms: float
    varied: list[str]
    points: list[VariationPoint]
    warnings: list[str]


_VAR_LABELS = {
    "m_n": "Module m_n",
    "z1": "Teeth z₁",
    "z2": "Teeth z₂",
    "x1": "Shift x₁",
    "x2": "Shift x₂",
    "beta_deg": "Helix β",
    "b": "Face width b",
}


@router.post("/variation", response_model=VariationResponse)
def variation(req: VariationRequest) -> VariationResponse:
    """Plastic-capable Stufenvariation over the macro-geometry matrix (steel + plastic)."""
    import time

    from app.services.variation import kernel

    steel = Material(
        name="steel",
        kind=MaterialKind.STEEL,
        elastic_modulus_mpa=206000.0,
        poisson_ratio=0.30,
        sigma_hlim_mpa=req.steel_sigma_hlim_mpa,
        sigma_flim_mpa=req.steel_sigma_flim_mpa,
    )
    plastic = Material(
        name="plastic",
        kind=MaterialKind.PLASTIC,
        elastic_modulus_mpa=2800.0,
        poisson_ratio=0.35,
        sigma_hlim_mpa=req.plastic_sigma_hlim_mpa,
        sigma_flim_mpa=req.plastic_sigma_flim_mpa,
    )
    specs = {
        "m_n": req.m_n,
        "z1": req.z1,
        "z2": req.z2,
        "x1": req.x1,
        "x2": req.x2,
        "beta_deg": req.beta_deg,
        "b": req.b,
    }
    varied: dict[str, Varied] = {}
    fixed: dict[str, float] = {}
    for key, s in specs.items():
        # Centre-distance coupling: teeth are locked and x₂ is derived → never varied.
        if req.fix_center_distance and key in ("z1", "z2", "x2"):
            if key != "x2":
                fixed[key] = s.value
            continue
        if s.vary and s.steps > 1:
            varied[key] = Varied(
                values=tuple(np.linspace(s.min, s.max, s.steps)), bounds=(s.min, s.max)
            )
        else:
            fixed[key] = s.value

    spec = VariationSpec(
        materials=(steel, plastic),
        torque_nm=req.torque_nm,
        varied=varied,
        fixed=fixed,
        normal_pressure_angle_deg=req.normal_pressure_angle_deg,
        tool_addendum_factor=req.tool_addendum_factor,
        tool_tip_radius_factor=req.tool_tip_radius_factor,
        root_minimum_safety=req.root_minimum_safety,
        flank_minimum_safety=req.flank_minimum_safety,
    )
    batch = (
        build_grid(spec)
        if req.method == "grid"
        else build_sample(spec, req.sample_count, method=req.method)
    )
    if req.fix_center_distance:
        # derive x₂ so the working centre distance equals the target a (per variant)
        size = next((v.size for v in batch.values()), 1)

        def _col(key: str) -> np.ndarray:
            return batch[key] if key in batch else np.full(size, fixed[key])

        beta_r = np.radians(_col("beta_deg"))
        alpha_n = np.radians(req.normal_pressure_angle_deg)
        m_t = _col("m_n") / np.cos(beta_r)
        alpha_t = np.arctan(np.tan(alpha_n) / np.cos(beta_r))
        a_ref = (_col("z1") + _col("z2")) * m_t / 2.0
        cos_awt = np.clip(a_ref * np.cos(alpha_t) / req.center_distance_mm, -1.0, 1.0)
        alpha_wt = np.arccos(cos_awt)
        inv_awt = np.tan(alpha_wt) - alpha_wt
        inv_at = np.tan(alpha_t) - alpha_t
        sum_x = (inv_awt - inv_at) * (_col("z1") + _col("z2")) / (2.0 * np.tan(alpha_n))
        batch["x2"] = sum_x - _col("x1")

    t = time.perf_counter()
    res = evaluate(spec, batch)
    eval_ms = (time.perf_counter() - t) * 1000.0

    n = int(res.total_contact_ratio.size)
    p = res.parameters
    overlap = np.broadcast_to(res.overlap_ratio, (n,))
    beta = batch["beta_deg"] if "beta_deg" in batch else np.full(n, fixed.get("beta_deg", 0.0))
    geo = kernel.mesh_geometry(
        normal_module_mm=p["m_n"],
        teeth_pinion=p["z1"],
        teeth_wheel=p["z2"],
        profile_shift_pinion=p["x1"],
        profile_shift_wheel=p["x2"],
        normal_pressure_angle=np.radians(req.normal_pressure_angle_deg),
        helix_angle=np.radians(beta),
        face_width_mm=p["b"],
    )
    # solid-disc weight estimate (steel pinion + plastic wheel), grams
    quarter_pi = math.pi / 4.0
    weight = (
        req.steel_density_kg_m3 * quarter_pi * (geo.tip_diameter[0] * 1e-3) ** 2 * (p["b"] * 1e-3)
        + req.plastic_density_kg_m3
        * quarter_pi
        * (geo.tip_diameter[1] * 1e-3) ** 2
        * (p["b"] * 1e-3)
    ) * 1000.0

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
            m_n=round(float(p["m_n"][i]), 3),
            z1=round(float(p["z1"][i]), 2),
            z2=round(float(p["z2"][i]), 2),
            x1=round(float(p["x1"][i]), 4),
            x2=round(float(p["x2"][i]), 4),
            beta_deg=round(float(beta[i]), 2),
            b=round(float(p["b"][i]), 2),
            center_distance_mm=round(float(geo.working_center_distance_mm[i]), 3),
            transverse_contact_ratio=round(float(res.transverse_contact_ratio[i]), 4),
            overlap_ratio=round(float(overlap[i]), 4),
            total_contact_ratio=round(float(res.total_contact_ratio[i]), 4),
            root_safety_pinion=_round(float(res.root_safety[0][i])),
            root_safety_wheel=_round(float(res.root_safety[1][i])),
            flank_safety_pinion=_round(float(res.flank_safety[0][i])),
            flank_safety_wheel=_round(float(res.flank_safety[1][i])),
            weight_g=round(float(weight[i]), 1),
            pareto=bool(front[i]),
        )
        for i in range(n)
        if bool(valid[i])
    ]
    return VariationResponse(
        count=n,
        valid=int(valid.sum()),
        pareto=int(front.sum()),
        eval_ms=round(eval_ms, 1),
        varied=[_VAR_LABELS[k] for k in varied],
        points=points,
        warnings=list(res.warnings),
    )


# --------------------------------------------------------------------------- #
# Tooth profile (real involute flanks for the mesh plot of a selected variant) #
# --------------------------------------------------------------------------- #
class ToothProfileRequest(BaseModel):
    normal_module_mm: float = 2.0
    teeth_pinion: float = 24
    teeth_wheel: float = 60
    profile_shift_pinion: float = 0.0
    profile_shift_wheel: float = 0.0
    normal_pressure_angle_deg: float = 20.0
    helix_angle_deg: float = 0.0


class ToothGear(BaseModel):
    teeth: int
    center_x_mm: float
    reference_radius_mm: float
    base_radius_mm: float
    tip_radius_mm: float
    root_radius_mm: float
    half_flank: list[list[float]]  # one right half-flank [[x, y], …], tooth centred on +y


class ToothProfileResponse(BaseModel):
    center_distance_mm: float
    pinion: ToothGear
    wheel: ToothGear


def _tooth_gear(m_n: float, z: float, x: float, alpha_n_deg: float, beta_deg: float) -> ToothGear:
    """Exact transverse involute half-flank (d_f → d_a) of one tooth, centred on +y."""
    beta = math.radians(beta_deg)
    alpha_n = math.radians(alpha_n_deg)
    m_t = m_n / math.cos(beta)
    alpha_t = math.atan(math.tan(alpha_n) / math.cos(beta))
    r = m_t * z / 2.0
    r_b = r * math.cos(alpha_t)
    r_a = r + m_n * (1.0 + x)  # standard addendum
    r_f = max(0.1, r - m_n * (1.25 - x))  # standard dedendum
    s_t = m_t * (math.pi / 2.0 + 2.0 * x * math.tan(alpha_n))  # transverse thickness at d
    psi = s_t / (2.0 * r) + (math.tan(alpha_t) - alpha_t)  # half-angle to right flank at base
    start = max(r_b, r_f)
    pts: list[list[float]] = []
    if r_f < start:  # radial root segment up to where the involute starts
        a0 = math.acos(min(1.0, r_b / start))
        th0 = psi - (math.tan(a0) - a0)
        pts.append([r_f * math.sin(th0), r_f * math.cos(th0)])
    steps = 36
    for k in range(steps + 1):
        rr = start + (r_a - start) * k / steps
        a_y = math.acos(min(1.0, r_b / rr))
        th = psi - (math.tan(a_y) - a_y)
        pts.append([rr * math.sin(th), rr * math.cos(th)])
    return ToothGear(
        teeth=int(round(z)),
        center_x_mm=0.0,
        reference_radius_mm=r,
        base_radius_mm=r_b,
        tip_radius_mm=r_a,
        root_radius_mm=r_f,
        half_flank=[[round(a, 4), round(b, 4)] for a, b in pts],
    )


@router.post("/tooth-profile", response_model=ToothProfileResponse)
def tooth_profile(req: ToothProfileRequest) -> ToothProfileResponse:
    """Real involute tooth flanks of both gears for the mesh plot (Zahneingriff)."""
    beta = math.radians(req.helix_angle_deg)
    alpha_n = math.radians(req.normal_pressure_angle_deg)
    m_t = req.normal_module_mm / math.cos(beta)
    alpha_t = math.atan(math.tan(alpha_n) / math.cos(beta))
    z1, z2 = req.teeth_pinion, req.teeth_wheel
    a_ref = (z1 + z2) * m_t / 2.0
    inv_at = math.tan(alpha_t) - alpha_t
    inv_awt = inv_at + 2.0 * (req.profile_shift_pinion + req.profile_shift_wheel) * math.tan(
        alpha_n
    ) / (z1 + z2)
    alpha_wt = _inv_involute(inv_awt)
    a = a_ref * math.cos(alpha_t) / math.cos(alpha_wt)
    pinion = _tooth_gear(
        req.normal_module_mm,
        z1,
        req.profile_shift_pinion,
        req.normal_pressure_angle_deg,
        req.helix_angle_deg,
    )
    wheel = _tooth_gear(
        req.normal_module_mm,
        z2,
        req.profile_shift_wheel,
        req.normal_pressure_angle_deg,
        req.helix_angle_deg,
    )
    wheel = wheel.model_copy(update={"center_x_mm": round(a, 4)})
    return ToothProfileResponse(center_distance_mm=round(a, 4), pinion=pinion, wheel=wheel)


def _inv_involute(value: float, *, guess: float = 0.4) -> float:
    """Solve inv α = tan α − α for α (scalar Newton)."""
    alpha = max(0.05, (3.0 * value) ** (1.0 / 3.0))
    for _ in range(40):
        alpha -= (math.tan(alpha) - alpha - value) / math.tan(alpha) ** 2
    return alpha


def _round(value: float | None, digits: int = 3) -> float | None:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return None
    return round(float(value), digits)
