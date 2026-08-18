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
from typing import Literal

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.stage_params import StageParams, _example_ste_path, kst_e_stage
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
from app.services.geometry.din3967 import allowances_um as din3967_allowances_um
from app.services.geometry.gear import GearStage, line_of_action_points
from app.services.geometry.report import GeometryReport, compute_geometry_report
from app.services.geometry.root_fillet import with_root_land
from app.services.geometry.tolerances import (
    FlankTolerances,
    dynamics_deviations,
    flank_tolerances,
    validity_warnings,
)
from app.services.geometry.tooth_form import ToothProfile
from app.services.geometry.tooth_root import ToothRootGeometry
from app.services.materials import Material, MaterialKind, catalog_material
from app.services.variation import (
    VariationSpec,
    Varied,
    build_grid,
    build_sample,
    evaluate,
    pareto_front,
)

router = APIRouter(prefix="/api", tags=["analysis"])

#: material kind per input slot — the norm dispatch follows the MATERIAL, never the role
#: (user decision 2026-07-04: steel → ISO 6336, plastic → VDI 2736, no mixing)
MaterialKindName = Literal["steel", "plastic"]

# retained internal alias — the kst-E loader lives in app.api.stage_params (shared model)
_kst_e_stage = kst_e_stage


def _stage_roots(stage: GearStage) -> Pair[ToothRootGeometry]:
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
    # catalog names (FVA Workbench parity: 20MnCr5 + Stanyl TW200F6, PA46 cond. 80 °C)
    mats = (catalog_material("steel").name, catalog_material("plastic").name)
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
# Geometry — computed from THE shared StageParams (single source of truth)     #
# --------------------------------------------------------------------------- #
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


def _tip_diameters(stage: GearStage) -> Pair[float]:
    """The REAL tip diameter d_a (FVA parity: kst-E wheel 54.022, not the usable d_Na
    53.788 after the tip edge break) — generation value, else the DIN 21771 nominal."""
    if stage.generation is not None:
        return Pair(stage.generation[0].tip_diameter_mm, stage.generation[1].tip_diameter_mm)
    d = stage.reference_diameter_mm
    x = stage.profile_shift
    m = stage.normal_module_mm
    return Pair(d[0] + 2.0 * m * (1.0 + x[0]), d[1] + 2.0 * m * (1.0 + x[1]))


@router.post("/geometry", response_model=GeometryResponse)
def geometry(req: StageParams) -> GeometryResponse:
    """Macro-geometry (diameters, contact ratios, α_wt) of the ONE active stage."""
    stage = req.stage()
    notes = stage.check_validity()
    if stage.total_contact_ratio < 1.0:
        notes = [*notes, "ε_γ < 1 — no continuous mesh."]
    tip = _tip_diameters(stage)
    return GeometryResponse(
        reference_diameter_mm=[round(stage.reference_diameter_mm[i], 4) for i in range(2)],
        base_diameter_mm=[round(stage.base_diameter_mm[i], 4) for i in range(2)],
        tip_diameter_mm=[round(tip[i], 4) for i in range(2)],
        working_pressure_angle_deg=round(stage.working_pressure_angle_deg, 4),
        working_center_distance_mm=round(stage.working_center_distance_mm, 4),
        transverse_contact_ratio=round(stage.transverse_contact_ratio, 4),
        overlap_ratio=round(stage.overlap_ratio, 4),
        total_contact_ratio=round(stage.total_contact_ratio, 4),
        valid=bool(stage.total_contact_ratio >= 1.0),
        notes=notes,
    )


# --------------------------------------------------------------------------- #
# Full geometry report — the backend SSOT (DIN ISO 21771 / DIN 21773 / 3967 /  #
# 3964), fillet-aware. FastAPI serializes the service dataclasses directly.    #
# --------------------------------------------------------------------------- #
class GeometryReportRequest(BaseModel):
    stage: StageParams = Field(default_factory=StageParams)
    # full FilletSpec dicts (validated by the mesh router's model on use); kept loose here
    # to avoid a router-to-router import — resolved via the shared strategy factory below
    fillet_gear1: dict | None = None
    fillet_gear2: dict | None = None
    ball_diameter_gear1_mm: float | None = Field(None, gt=0.0)
    ball_diameter_gear2_mm: float | None = Field(None, gt=0.0)
    center_distance_allowance_mm: float | None = Field(None, ge=0.0)  # DIN 3964 js field
    span_allowance_upper_um: tuple[float, float] | None = None  # A_We per gear
    span_allowance_lower_um: tuple[float, float] | None = None  # A_Wi per gear
    # DIN 3967 designation per gear (e.g. drawing "27cd" = allowance "cd" + tolerance 27);
    # used when no direct span allowances are given
    allowance_series_gear1: (
        Literal["a", "ab", "b", "bc", "c", "cd", "d", "e", "f", "g", "h"] | None
    ) = None
    allowance_series_gear2: (
        Literal["a", "ab", "b", "bc", "c", "cd", "d", "e", "f", "g", "h"] | None
    ) = None
    tolerance_series_gear1: int | None = Field(None, ge=21, le=30)
    tolerance_series_gear2: int | None = Field(None, ge=21, le=30)


def _report_allowances(
    req: GeometryReportRequest, stage: GearStage | None = None
) -> tuple[Pair[float] | None, Pair[float] | None]:
    """A_We/A_Wi per gear: explicit µm > DIN 3967 series > example STE > StageParams mean."""
    if req.span_allowance_upper_um is not None and req.span_allowance_lower_um is not None:
        up, low = req.span_allowance_upper_um, req.span_allowance_lower_um
        return (
            Pair(up[0] / 1000.0, up[1] / 1000.0),
            Pair(low[0] / 1000.0, low[1] / 1000.0),
        )
    series = (
        (req.allowance_series_gear1, req.tolerance_series_gear1),
        (req.allowance_series_gear2, req.tolerance_series_gear2),
    )
    if stage is not None and all(a is not None and t is not None for a, t in series):
        # DIN 3967 tables give E_sn; the report pipeline takes span allowances
        # A_W = E_sn·cos α_n (DIN 21773 §14.4) — the service converts back exactly
        cos_an = math.cos(math.radians(stage.normal_pressure_angle_deg))
        ups: list[float] = []
        lows: list[float] = []
        for i, (a_series, t_series) in enumerate(series):
            assert a_series is not None and t_series is not None
            e_sns_um, e_sni_um = din3967_allowances_um(
                stage.reference_diameter_mm[i], a_series, t_series
            )
            ups.append(e_sns_um / 1000.0 * cos_an)
            lows.append(e_sni_um / 1000.0 * cos_an)
        return Pair(ups[0], ups[1]), Pair(lows[0], lows[1])
    if req.stage.use_example:
        path = _example_ste_path()
        if path is not None:
            data = gear_stage_from_ste(load_ste(path))
            if (
                data.tooth_width_allowance_upper_um is not None
                and data.tooth_width_allowance_lower_um is not None
            ):
                u, lo = data.tooth_width_allowance_upper_um, data.tooth_width_allowance_lower_um
                return (
                    Pair(u[0] / 1000.0, u[1] / 1000.0),
                    Pair(lo[0] / 1000.0, lo[1] / 1000.0),
                )
        return None, None
    mean = Pair(req.stage.tooth_width_allowance_pinion_mm, req.stage.tooth_width_allowance_wheel_mm)
    if mean[0] == 0.0 and mean[1] == 0.0:
        return None, None
    return mean, mean


def _fillet_min_radii(req: GeometryReportRequest, stage: GearStage) -> Pair[float] | None:
    """Deepest contour radius per gear for the selected root-fillet strategies."""
    from app.api.mesh import FilletSpec  # runtime import: routers stay independent

    specs = (req.fillet_gear1, req.fillet_gear2)
    if all(s is None or s.get("kind", "standard") == "standard" for s in specs):
        return None
    radii: list[float] = []
    for i, raw in enumerate(specs):
        profile = ToothProfile.from_stage(stage, i)
        strategy = FilletSpec(**raw).strategy() if raw is not None else None
        if strategy is None:
            radii.append(profile.root_diameter_mm / 2.0)
            continue
        pts = strategy.right_half(profile)
        radii.append(min(math.hypot(p[0], p[1]) for p in pts))
    return Pair(radii[0], radii[1])


@router.post("/geometry/report", response_model=GeometryReport)
def geometry_report(req: GeometryReportRequest) -> GeometryReport:
    """The FULL geometry report (SSOT): every DIN ISO 21771 / DIN 21773 quantity at once."""
    stage = req.stage.stage()
    up, low = _report_allowances(req, stage)
    balls = None
    if req.ball_diameter_gear1_mm is not None or req.ball_diameter_gear2_mm is not None:
        mn = stage.normal_module_mm
        balls = Pair(
            req.ball_diameter_gear1_mm or 1.75 * mn, req.ball_diameter_gear2_mm or 1.75 * mn
        )
    try:
        return compute_geometry_report(
            stage,
            ball_diameter_mm=balls,
            span_allowance_upper_mm=up,
            span_allowance_lower_mm=low,
            center_distance_allowance_mm=req.center_distance_allowance_mm,
            fillet_contour_min_radius_mm=_fillet_min_radii(req, stage),
        )
    except ValueError as exc:  # e.g. helical stage (spur-only report, audit NRM-01)
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
# Capacity — norm dispatch per gear by MATERIAL (steel → ISO 6336,             #
# plastic → VDI 2736; user decision 2026-07-04, never mixed by role)           #
# --------------------------------------------------------------------------- #
class MaterialParams(BaseModel):
    """Material slots + catalog overrides — SHARED by /capacity and /dynamics (GAP-01:
    both endpoints must evaluate the same materials or their K-factors disagree)."""

    pinion_material: MaterialKindName = "steel"
    wheel_material: MaterialKindName = "plastic"
    # --- steel material ---
    steel_modulus_mpa: float = 210000.0
    steel_poisson: float = 0.30
    steel_sigma_hlim_mpa: float = 1500.0
    steel_sigma_flim_mpa: float = 430.0
    # --- plastic material ---
    plastic_modulus_mpa: float = 4156.0
    plastic_poisson: float = 0.34
    plastic_sigma_hlim_mpa: float = 60.0
    plastic_sigma_flim_mpa: float = 35.0
    plastic_yield_strength_mpa: float | None = None  # σ_S / R_p0.2 of the plastic


class CapacityRequest(MaterialParams):
    # --- THE shared stage (single source of truth for the geometry) ---
    stage: StageParams = Field(default_factory=StageParams)
    # --- load & application (Welle / Getriebeeinheit) ---
    pinion_torque_nm: float = 7.85  # T_1
    pinion_speed_min1: float = 1000.0  # n_1
    application_factor: float = 1.0  # K_A
    # --- dynamics (ISO 6336-1): native K_v from accuracy, or override ---
    compute_dynamics: bool = True
    dynamic_factor: float = 1.0  # K_v (override when compute_dynamics = False)
    # K_Hβ: None = use the NATIVE ISO 6336-1 Method-C value when compute_dynamics is on
    # (bugfix 2026-08-05: the computed value was silently discarded before); a number
    # overrides it (legacy payloads with an explicit value keep their behaviour)
    face_load_factor: float | None = None
    accuracy_grade: int | None = None  # ISO 1328-1 class; if set, derives f_pb/f_fα/f_Hβ
    base_pitch_deviation_um: float = 6.0  # f_pb (ISO 1328) — used when no grade given
    profile_form_deviation_um: float = 5.0  # f_fα
    # f_Hβ (helix slope) — used when no grade given; feeds the native F_βx estimate for
    # K_Hβ (audit V-02: without it Method C degenerates to K_Hβ = 1). None → 0 (legacy).
    helix_slope_deviation_um: float | None = None
    # F_βx override in µm (shaft analysis / RIKOR); None → native ISO 6336-1 §7.5 estimate
    mesh_misalignment_um: float | None = None
    # --- ISO 6336 conditions (steel) ---
    lubricant_viscosity_40_mm2s: float = 100.0  # ν_40
    flank_roughness_rz_um: float = 5.0  # R_zH
    root_roughness_rz_um: float = 20.0  # R_zF
    flank_life_factor: float = 1.0  # Z_NT
    root_life_factor: float = 1.0  # Y_NT
    # ISO 6336-3 material group per gear (ρ′, Y_RrelT, Y_X curves; audit NRM-07: this was
    # hardcoded to case-hardened for both gears) + the softer gear's hardness for Z_W
    pinion_material_group: RootMaterialGroup = RootMaterialGroup.CASE_HARDENED
    wheel_material_group: RootMaterialGroup = RootMaterialGroup.CASE_HARDENED
    softer_gear_hardness_hb: float | None = None  # HB of the softer mating gear (Z_W)
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
    # --- static peak load (VDI 2736 §3.3) ---
    static_overload_factor: float | None = None  # K_A,stat (F_zmax/F_t); None → skip
    static_minimum_safety: float = 1.5  # S_Smin


class CapacityFactors(BaseModel):
    application_factor: float  # K_A
    dynamic_factor: float  # K_v
    transverse_factor: float  # K_Hα
    transverse_factor_root: float  # K_Fα
    face_load_factor: float  # K_Hβ (native ISO 6336-1 Method C unless overridden)
    face_load_factor_root: float  # K_Fβ
    elasticity_factor: float  # Z_E
    zone_factor: float  # Z_H
    contact_ratio_factor: float  # Z_ε (ISO 6336-2 §8)
    single_contact_b: float  # Z_B
    single_contact_d: float  # Z_D
    tangential_force_n: float  # F_t at the reference circle
    pitch_velocity_ms: float  # v at the reference circle
    line_load_n_mm: float  # F_t·K_A / b_gem
    virtual_teeth: list[float]  # z_n per gear (spur: = z)


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
    # ISO branch: nominal stresses + the critical-section geometry behind Y_F/Y_S
    nominal_flank_stress_mpa: float | None = None  # σ_H0
    nominal_root_stress_mpa: float | None = None  # σ_F0
    # ISO 6336-2 flank strength sub-factors (σ_HP = σ_Hlim·Z_NT·Z_L·Z_v·Z_R·Z_W·Z_X)
    lubricant_factor: float | None = None  # Z_L
    velocity_factor: float | None = None  # Z_v
    roughness_factor: float | None = None  # Z_R
    work_hardening_factor: float | None = None  # Z_W
    size_factor_flank: float | None = None  # Z_X
    life_factor_flank: float | None = None  # Z_NT
    # ISO 6336-3 root strength sub-factors (σ_FP = σ_FE·Y_NT·Y_δrelT·Y_RrelT·Y_X)
    notch_sensitivity_factor: float | None = None  # Y_δrelT
    surface_factor: float | None = None  # Y_RrelT
    size_factor_root: float | None = None  # Y_X
    life_factor_root: float | None = None  # Y_NT
    root_chord_mn: float | None = None  # s_Fn* (30°-tangent, ·m_n)
    fillet_radius_mn: float | None = None  # ρ_F* (·m_n)
    notch_parameter: float | None = None  # q_s
    bending_lever_mn: float | None = None  # h_Fe* (·m_n)
    load_angle_deg: float | None = None  # α_Fen
    # VDI branch extras
    flank_temperature_c: float | None = None  # ϑ_Fla
    loss_factor: float | None = None  # H_V
    tooth_temperature_c: float | None = None
    wear_um: float | None = None
    allowable_wear_um: float | None = None
    deformation_mm: float | None = None
    peak_stress_mpa: float | None = None  # σ_F,P (static overload)
    peak_safety: float | None = None  # S_static


class CapacityResponse(BaseModel):
    factors: CapacityFactors
    pinion: GearCapacity
    wheel: GearCapacity


def _materials(req: MaterialParams) -> Pair[Material]:
    """Per-slot materials from the catalog, with the request's property overrides."""

    def build(kind: MaterialKindName) -> Material:
        base = catalog_material(kind)
        if kind == "steel":
            return base.model_copy(
                update={
                    "elastic_modulus_mpa": req.steel_modulus_mpa,
                    "poisson_ratio": req.steel_poisson,
                    "sigma_hlim_mpa": req.steel_sigma_hlim_mpa,
                    "sigma_flim_mpa": req.steel_sigma_flim_mpa,
                }
            )
        return base.model_copy(
            update={
                "elastic_modulus_mpa": req.plastic_modulus_mpa,
                "poisson_ratio": req.plastic_poisson,
                "sigma_hlim_mpa": req.plastic_sigma_hlim_mpa,
                "sigma_flim_mpa": req.plastic_sigma_flim_mpa,
                "yield_strength_mpa": req.plastic_yield_strength_mpa,
            }
        )

    return Pair(build(req.pinion_material), build(req.wheel_material))


@router.post("/capacity", response_model=CapacityResponse)
def capacity(req: CapacityRequest) -> CapacityResponse:
    """Per-gear norm dispatch by material on THE shared stage (geometry + operating values)."""
    stage = req.stage.stage()
    return _run_capacity(stage, _stage_roots(stage), _materials(req), req)


def _run_capacity(
    stage: GearStage,
    roots: Pair[ToothRootGeometry],
    materials: Pair[Material],
    req: CapacityRequest,
) -> CapacityResponse:
    """Per-gear norm dispatch by material (steel → ISO 6336, plastic → VDI 2736).

    Works for any generated stage (the preloaded kst-E or a free `from_parameters`) and any
    material pairing — steel/steel, plastic/plastic, or mixed in either orientation.
    """
    from app.services.capacity.iso6336 import (
        elasticity_factor,
        flank_contact_ratio_factor,
        single_contact_factors,
        zone_factor,
    )

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
        f_pb, f_fa, f_hb = dynamics_deviations(
            accuracy_grade=req.accuracy_grade,
            normal_module_mm=stage.normal_module_mm,
            reference_diameter_mm=stage.reference_diameter_mm[0],
            face_width_mm=min(width),
        )
    else:
        f_pb, f_fa = req.base_pitch_deviation_um, req.profile_form_deviation_um
        f_hb = req.helix_slope_deviation_um or 0.0

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
                # f_Hβ feeds the native F_βx estimate for K_Hβ (audit V-02); an explicit
                # mesh-misalignment override (shaft analysis / RIKOR) wins
                helix_slope_deviation_um=Pair(f_hb, f_hb),
                initial_mesh_misalignment_um=req.mesh_misalignment_um or 0.0,
            ),
        )
        k_v, k_ha = dyn.dynamic_factor, dyn.transverse_factor_flank
        k_fa = dyn.transverse_factor_root
        # native K_Hβ/K_Fβ (ISO 6336-1 §7 Method C) unless explicitly overridden
        k_hb = (
            req.face_load_factor
            if req.face_load_factor is not None
            else (dyn.face_load_factor_flank)
        )
        k_fb = (
            req.face_load_factor
            if req.face_load_factor is not None
            else (dyn.face_load_factor_root)
        )
    else:
        k_v, k_ha, k_fa = req.dynamic_factor, 1.0, 1.0
        k_hb = k_fb = req.face_load_factor if req.face_load_factor is not None else 1.0

    iso_load = base_load.model_copy(
        update={
            "dynamic_factor": k_v,
            "face_load_factor_flank": k_hb,
            "face_load_factor_root": k_fb,
            "transverse_factor_flank": k_ha,
            "transverse_factor_root": k_fa,
        }
    )
    iso_conditions = Iso6336Conditions(
        pitch_line_velocity_ms=v_t,
        lubricant_viscosity_40_mm2s=req.lubricant_viscosity_40_mm2s,
        flank_roughness_rz_um=req.flank_roughness_rz_um,
        root_roughness_rz_um=Pair(req.root_roughness_rz_um, req.root_roughness_rz_um),
        material_group=Pair(req.pinion_material_group, req.wheel_material_group),
        flank_life_factor=Pair(req.flank_life_factor, req.flank_life_factor),
        root_life_factor=Pair(req.root_life_factor, req.root_life_factor),
        softer_gear_hardness_hb=req.softer_gear_hardness_hb,
    )
    kinds = (materials[0].kind, materials[1].kind)
    iso = (
        evaluate_iso6336(stage, roots, materials, iso_load, iso_conditions)
        if MaterialKind.STEEL in kinds
        else None
    )
    vdi = None
    if MaterialKind.PLASTIC in kinds:
        # VDI 2736 load factor K = K_A·K_v
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
            static_overload_factor=req.static_overload_factor,
            static_minimum_safety=req.static_minimum_safety,
        )
        vdi = evaluate_vdi2736(
            stage,
            roots,
            materials,
            vdi_conditions,
            root_face_width_mm=width,
            common_face_width_mm=min(width),
        )

    def gear_result(i: int) -> GearCapacity:
        """Norm dispatch by MATERIAL: steel → ISO 6336, plastic → VDI 2736 (never by role)."""
        mat = materials[i]
        slot = "Ritzel" if i == 0 else "Rad"
        section = {
            "root_chord_mn": round(roots[i].critical_root_chord_mn, 4),
            "fillet_radius_mn": round(roots[i].root_fillet_radius_mn, 4),
            "notch_parameter": round(roots[i].notch_parameter, 4),
            "bending_lever_mn": round(roots[i].bending_lever_mn, 4),
            "load_angle_deg": round(roots[i].load_application_angle_deg, 4),
        }
        if mat.is_plastic:
            assert vdi is not None
            r = vdi[i]
            return GearCapacity(
                label=f"{slot} (Kunststoff)",
                material=mat.name,
                method="VDI 2736:2014",
                flank_stress_mpa=round(r.flank_stress_mpa, 3),
                flank_safety=_round(r.flank_safety),
                root_stress_mpa=round(r.root_stress_mpa, 3),
                root_safety=_round(r.root_safety),
                # σ_P directly from the norm (Eq. 13/17) — no longer safety·stress, which
                # broke once the safeties became TRUE S = σ_lim/σ (audit NRM-06)
                flank_permissible_mpa=_round(r.permissible_flank_stress_mpa),
                root_permissible_mpa=_round(r.permissible_root_stress_mpa),
                form_factor=round(roots[i].form_factor_tip, 4),
                stress_correction=round(roots[i].stress_correction_factor_tip, 4),
                **section,
                flank_temperature_c=round(r.flank_temperature_c, 2),
                loss_factor=round(r.loss_factor, 4),
                tooth_temperature_c=round(r.root_temperature_c, 2),
                wear_um=round(r.linear_wear_um, 2),
                allowable_wear_um=round(r.allowable_wear_um, 1),
                deformation_mm=round(r.deformation_mm, 4),
                peak_stress_mpa=_round(r.peak_root_stress_mpa),
                peak_safety=_round(r.peak_root_safety),
            )
        assert iso is not None
        s = iso[i]
        return GearCapacity(
            label=f"{slot} (Stahl)",
            material=mat.name,
            method="ISO 6336:2019",
            flank_stress_mpa=round(s.flank_stress_mpa, 3),
            flank_safety=_round(s.flank_safety),
            root_stress_mpa=round(s.root_stress_mpa, 3),
            root_safety=_round(s.root_safety),
            flank_permissible_mpa=_round(s.permissible_flank_stress_mpa),
            root_permissible_mpa=_round(s.permissible_root_stress_mpa),
            form_factor=round(roots[i].form_factor, 4),
            stress_correction=round(roots[i].stress_correction_factor, 4),
            nominal_flank_stress_mpa=round(s.nominal_flank_stress_mpa, 3),
            nominal_root_stress_mpa=round(s.nominal_root_stress_mpa, 3),
            lubricant_factor=_round(s.lubricant_factor, 4),
            velocity_factor=_round(s.velocity_factor, 4),
            roughness_factor=_round(s.roughness_factor, 4),
            work_hardening_factor=_round(s.work_hardening_factor, 4),
            size_factor_flank=_round(s.size_factor_flank, 4),
            life_factor_flank=_round(s.life_factor_flank, 4),
            notch_sensitivity_factor=_round(s.notch_sensitivity_factor, 4),
            surface_factor=_round(s.surface_factor, 4),
            size_factor_root=_round(s.size_factor_root, 4),
            life_factor_root=_round(s.life_factor_root, 4),
            **section,
        )

    z_bd = single_contact_factors(stage)
    factors = CapacityFactors(
        application_factor=round(req.application_factor, 3),
        dynamic_factor=round(k_v, 4),
        transverse_factor=round(k_ha, 4),
        transverse_factor_root=round(k_fa, 4),
        face_load_factor=round(k_hb, 4),
        face_load_factor_root=round(k_fb, 4),
        elasticity_factor=round(elasticity_factor(materials[0], materials[1]), 3),
        zone_factor=round(zone_factor(stage), 4),
        contact_ratio_factor=round(
            flank_contact_ratio_factor(stage.transverse_contact_ratio, stage.overlap_ratio), 4
        ),
        single_contact_b=round(z_bd[0], 4),
        single_contact_d=round(z_bd[1], 4),
        tangential_force_n=round(f_t, 2),
        pitch_velocity_ms=round(v_t, 4),
        line_load_n_mm=round(f_t * req.application_factor / min(width), 3),
        virtual_teeth=[round(roots[i].virtual_teeth, 3) for i in range(2)],
    )
    return CapacityResponse(factors=factors, pinion=gear_result(0), wheel=gear_result(1))


# NOTE: the former /api/evaluate route (its own copy of the geometry fields) is gone —
# /api/capacity now carries THE shared StageParams, so one endpoint serves both cases
# (single-source-of-truth decision 2026-07-04).


# --------------------------------------------------------------------------- #
# Dynamics (native ISO 6336-1)                                                 #
# --------------------------------------------------------------------------- #
class DynamicsRequest(MaterialParams):
    stage: StageParams = Field(default_factory=StageParams)  # THE shared stage
    pinion_speed_min1: float = 1000.0
    pinion_torque_nm: float = 7.85
    application_factor: float = 1.0
    # same accuracy inputs as /capacity (GAP-01: both tabs must agree on the deviations)
    accuracy_grade: int | None = None  # ISO 1328-1 class; if set, derives f_pb/f_fα/f_Hβ
    base_pitch_deviation_um: float = 6.0
    profile_form_deviation_um: float = 5.0
    helix_slope_deviation_um: float | None = None  # f_Hβ — used when no grade given
    mesh_misalignment_um: float | None = None  # F_βx override; None → native estimate


class DynamicsResponse(BaseModel):
    dynamic_factor: float
    transverse_factor_flank: float
    transverse_factor_root: float
    face_load_factor_flank: float
    face_load_factor_root: float
    mesh_stiffness: float
    reduced_mass: float
    resonance_speed_min1: float
    resonance_ratio: float
    regime: str


@router.post("/dynamics", response_model=DynamicsResponse)
def dynamics(req: DynamicsRequest) -> DynamicsResponse:
    """Native K_v (Method B), K_Hα, K_Hβ plus the resonance diagnostics."""
    stage = req.stage.stage()
    roots = _stage_roots(stage)
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
    if req.accuracy_grade is not None:
        f_pb, f_fa, f_hb = dynamics_deviations(
            accuracy_grade=req.accuracy_grade,
            normal_module_mm=stage.normal_module_mm,
            reference_diameter_mm=stage.reference_diameter_mm[0],
            face_width_mm=min(width),
        )
    else:
        f_pb, f_fa = req.base_pitch_deviation_um, req.profile_form_deviation_um
        f_hb = req.helix_slope_deviation_um or 0.0
    conditions = DynamicConditions(
        pinion_speed_min1=req.pinion_speed_min1,
        base_pitch_deviation_um=Pair(f_pb, f_pb),
        profile_form_deviation_um=Pair(f_fa, f_fa),
        helix_slope_deviation_um=Pair(f_hb, f_hb),
        initial_mesh_misalignment_um=req.mesh_misalignment_um or 0.0,
    )
    f = native_dynamic_factors(
        stage,
        roots,
        _materials(req),
        load,
        conditions,
    )
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
        face_load_factor_root=round(f.face_load_factor_root, 4),
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
    # the macro-geometry matrix (vary → min/max/steps, else fixed at value) — the row set
    # mirrors the FVA Stufenvariation dialog (screenshots Stufenvariation_Ansicht-1*.png)
    m_n: VarSpec = VarSpec(value=2.0, min=1.0, max=4.0)
    alpha_n: VarSpec = VarSpec(value=20.0, min=17.5, max=22.5)  # Normaleingriffswinkel Rad 1
    beta_deg: VarSpec = VarSpec(value=0.0, min=0.0, max=25.0)  # Schrägungswinkel Rad 1
    z1: VarSpec = VarSpec(value=24, min=16, max=34, vary=True, steps=19)
    z2: VarSpec = VarSpec(value=60, min=40, max=80)
    x1: VarSpec = VarSpec(value=0.0, min=-0.3, max=0.6, vary=True, steps=10)
    x2: VarSpec = VarSpec(value=0.0, min=-0.3, max=0.6)
    b: VarSpec = VarSpec(value=20.0, min=10.0, max=40.0)  # Zahnbreite Rad 1
    # per-gear reference-profile rows — REAL sweep parameters (the kernel is per-gear
    # for width, addendum, tool dedendum and tool tip radius); shared-mesh quantities
    # use min(b, b2), each root stress its own width
    b2: VarSpec = VarSpec(value=20.0, min=10.0, max=40.0)  # Zahnbreite Rad 2
    h_ap1: VarSpec = VarSpec(value=1.0, min=0.8, max=1.2)  # Kopfhöhenfaktor Rad 1
    h_ap2: VarSpec = VarSpec(value=1.0, min=0.8, max=1.2)
    h_fp1: VarSpec = VarSpec(value=1.25, min=1.0, max=1.45)  # Fußhöhenfaktor Rad 1
    h_fp2: VarSpec = VarSpec(value=1.25, min=1.0, max=1.45)
    rho_fp1: VarSpec = VarSpec(value=0.38, min=0.2, max=0.48)  # Fußausrundung Rad 1
    rho_fp2: VarSpec = VarSpec(value=0.38, min=0.2, max=0.48)
    q1_mm: float = 0.0  # Bearbeitungszugabe (not in the kernel — carried, warns)
    q2_mm: float = 0.0
    pr_p1_mm: float = 0.0  # Protuberanzbetrag
    pr_p2_mm: float = 0.0
    alpha_pr_p1_deg: float = 0.0  # Protuberanzwinkel
    alpha_pr_p2_deg: float = 0.0
    # FVA dialog top checkboxes (geometry-generation options; not in the sweep kernel yet)
    allow_tip_shortening: bool = False  # Automatische Kopfkürzung zulassen
    full_root_round: bool = False  # Vollausrundung
    dedendum_with_clearance: bool = False  # Fußhöhen mit Kopfspiel berechnen
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
    sample_count: int = Field(256, ge=8, le=65536)
    # material matrix (user decision/plan v2): each side steel or plastic — steel/steel,
    # plastic/plastic, or mixed in either orientation. The kernel dispatches per gear
    # (steel → ISO 6336 limits, plastic → VDI 2736 limits, ADR-013).
    pinion_material: str = Field("steel", pattern="^(steel|plastic)$")
    wheel_material: str = Field("plastic", pattern="^(steel|plastic)$")
    steel_modulus_mpa: float = 206000.0
    plastic_modulus_mpa: float = 2800.0


class VariationPoint(BaseModel):
    m_n: float
    z1: float
    z2: float
    x1: float
    x2: float
    beta_deg: float
    b: float
    b2: float
    h_ap1: float
    h_ap2: float
    h_fp1: float
    h_fp2: float
    rho_fp1: float
    rho_fp2: float
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
    "alpha_n_deg": "Pressure angle α_n",
    "z1": "Teeth z₁",
    "z2": "Teeth z₂",
    "x1": "Shift x₁",
    "x2": "Shift x₂",
    "beta_deg": "Helix β",
    "b": "Face width b",
    "b2": "Face width b₂",
    "h_ap1": "Addendum h_aP*₁",
    "h_ap2": "Addendum h_aP*₂",
    "h_fp1": "Dedendum h_fP*₁",
    "h_fp2": "Dedendum h_fP*₂",
    "rho_fp1": "Root fillet ρ_fP*₁",
    "rho_fp2": "Root fillet ρ_fP*₂",
}


@router.post("/variation", response_model=VariationResponse)
def variation(req: VariationRequest) -> VariationResponse:
    """Plastic-capable Stufenvariation over the macro-geometry matrix (steel + plastic)."""
    import time

    from app.services.variation import kernel

    def _material(kind: str) -> Material:
        # catalog defaults + the request's overrides (single material source)
        base = catalog_material(kind)
        if kind == "steel":
            return base.model_copy(
                update={
                    "elastic_modulus_mpa": req.steel_modulus_mpa,
                    "sigma_hlim_mpa": req.steel_sigma_hlim_mpa,
                    "sigma_flim_mpa": req.steel_sigma_flim_mpa,
                }
            )
        return base.model_copy(
            update={
                "elastic_modulus_mpa": req.plastic_modulus_mpa,
                "sigma_hlim_mpa": req.plastic_sigma_hlim_mpa,
                "sigma_flim_mpa": req.plastic_sigma_flim_mpa,
            }
        )

    pinion_mat = _material(req.pinion_material)  # gear 1
    wheel_mat = _material(req.wheel_material)  # gear 2
    specs = {
        "m_n": req.m_n,
        "alpha_n_deg": req.alpha_n,
        "z1": req.z1,
        "z2": req.z2,
        "x1": req.x1,
        "x2": req.x2,
        "beta_deg": req.beta_deg,
        "b": req.b,
        # per-gear reference-profile rows — real sweep parameters since v0.7
        "b2": req.b2,
        "h_ap1": req.h_ap1,
        "h_ap2": req.h_ap2,
        "h_fp1": req.h_fp1,
        "h_fp2": req.h_fp2,
        "rho_fp1": req.rho_fp1,
        "rho_fp2": req.rho_fp2,
    }
    # honesty notes: rows the FVA dialog has but the sweep kernel does not evaluate —
    # reported, never silently dropped
    extra_warnings: list[str] = []
    for label, v1, v2 in (
        ("Bearbeitungszugabe q", req.q1_mm, req.q2_mm),
        ("Protuberanzbetrag pr_P", req.pr_p1_mm, req.pr_p2_mm),
        ("Protuberanzwinkel α_prP", req.alpha_pr_p1_deg, req.alpha_pr_p2_deg),
    ):
        if abs(v1 - v2) > 1e-12:
            extra_warnings.append(
                f"{label}: per-gear values not separable in the sweep kernel yet — "
                f"Rad-1 value {v1:g} drives the sweep (Rad 2: {v2:g})."
            )
    if any((req.q1_mm, req.q2_mm, req.pr_p1_mm, req.pr_p2_mm)):
        extra_warnings.append(
            "Bearbeitungszugabe/Protuberanz are carried as inputs but not evaluated in the "
            "sweep kernel yet."
        )
    for flag, name in (
        (req.allow_tip_shortening, "Automatische Kopfkürzung"),
        (req.full_root_round, "Vollausrundung"),
        (req.dedendum_with_clearance, "Fußhöhen mit Kopfspiel"),
    ):
        if flag:
            extra_warnings.append(f"{name}: option not implemented in the sweep kernel yet.")
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
        materials=(pinion_mat, wheel_mat),
        torque_nm=req.torque_nm,
        varied=varied,
        fixed=fixed,
        normal_pressure_angle_deg=req.alpha_n.value,
        # reference-profile semantics: gear h_aP* = addendum, gear h_fP* = tool h_aP0*,
        # gear ρ_fP* = tool tip radius (scalar fallbacks; the per-gear specs above win)
        addendum_factor=req.h_ap1.value,
        tool_addendum_factor=req.h_fp1.value,
        tool_tip_radius_factor=req.rho_fp1.value,
    )
    # Sobol needs a power-of-two count for balance (scipy warns otherwise) — round UP
    # and say so (honesty: never silently change the user's request)
    sample_count = req.sample_count
    if req.method == "sobol":
        rounded = 1 << (sample_count - 1).bit_length()
        if rounded != sample_count:
            extra_warnings.append(
                f"Sobol: sample count rounded up to the next power of two "
                f"({req.sample_count} → {rounded})."
            )
            sample_count = rounded
    batch = (
        build_grid(spec)
        if req.method == "grid"
        else build_sample(spec, sample_count, method=req.method)
    )
    if req.fix_center_distance:
        # derive x₂ so the working centre distance equals the target a (per variant)
        size = next((v.size for v in batch.values()), 1)

        def _col(key: str) -> np.ndarray:
            return batch[key] if key in batch else np.full(size, fixed[key])

        beta_r = np.radians(_col("beta_deg"))
        alpha_n = np.radians(_col("alpha_n_deg"))  # sweepable α_n (per variant)
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
    alpha = (
        batch["alpha_n_deg"]
        if "alpha_n_deg" in batch
        else np.full(n, fixed.get("alpha_n_deg", req.alpha_n.value))
    )
    geo = kernel.mesh_geometry(
        normal_module_mm=p["m_n"],
        teeth_pinion=p["z1"],
        teeth_wheel=p["z2"],
        profile_shift_pinion=p["x1"],
        profile_shift_wheel=p["x2"],
        normal_pressure_angle=np.radians(alpha),
        helix_angle=np.radians(beta),
        face_width_mm=np.minimum(p["b"], p["b2"]),
        addendum_factor_pinion=p["h_ap1"],
        addendum_factor_wheel=p["h_ap2"],
    )
    # solid-disc weight estimate (density follows each gear's material kind; each gear
    # its own face width), grams
    quarter_pi = math.pi / 4.0
    weight = (
        (req.steel_density_kg_m3 if req.pinion_material == "steel" else req.plastic_density_kg_m3)
        * quarter_pi
        * (geo.tip_diameter[0] * 1e-3) ** 2
        * (p["b"] * 1e-3)
        + (
            req.plastic_density_kg_m3
            if req.wheel_material == "plastic"
            else req.steel_density_kg_m3
        )
        * quarter_pi
        * (geo.tip_diameter[1] * 1e-3) ** 2
        * (p["b2"] * 1e-3)
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
            b2=round(float(p["b2"][i]), 2),
            h_ap1=round(float(p["h_ap1"][i]), 3),
            h_ap2=round(float(p["h_ap2"][i]), 3),
            h_fp1=round(float(p["h_fp1"][i]), 3),
            h_fp2=round(float(p["h_fp2"][i]), 3),
            rho_fp1=round(float(p["rho_fp1"][i]), 3),
            rho_fp2=round(float(p["rho_fp2"][i]), 3),
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
        warnings=[*res.warnings, *extra_warnings],
    )


# --------------------------------------------------------------------------- #
# Tooth profile — the REAL as-cut flanks (same geometry as the FE contour;     #
# the simplified standard-addendum reimplementation is gone, SSOT decision)    #
# --------------------------------------------------------------------------- #
class ToothGear(BaseModel):
    teeth: int
    center_x_mm: float
    reference_radius_mm: float
    base_radius_mm: float
    tip_radius_mm: float
    root_radius_mm: float
    half_flank: list[list[float]]  # one right half-flank [[x, y], …], tooth centred on +y


class LineOfAction(BaseModel):
    """T1/A/B/C/D/E of the line of action in the tooth-profile frame (gear 1 at the
    origin, gear 2 at (a, 0)) — the zoomed Zahneingriff plot draws these."""

    t1: list[float]
    t2: list[float]
    a: list[float]
    b: list[float]
    c: list[float]
    d: list[float]
    e: list[float]
    working_pressure_angle_deg: float
    path_of_contact_mm: float
    transverse_base_pitch_mm: float
    working_pitch_radius_mm: list[float]
    base_radius_mm: list[float]


class ToothProfileResponse(BaseModel):
    center_distance_mm: float
    pinion: ToothGear
    wheel: ToothGear
    line_of_action: LineOfAction | None = None


def _tooth_gear_from_profile(
    stage: GearStage, index: int, tip_relief: tuple[float, float | None] = (0.0, None)
) -> ToothGear:
    """One gear's right tooth boundary (root fillet → flank → tip), as cut.

    ``tip_relief`` = (C_αa [µm], d_Ca [mm] or None) so the Zahneingriff plot shows the
    SAME modified contour that goes into the FE mesh (SSOT, user decision 2026-07-06).
    """
    profile = ToothProfile.from_stage(
        stage, index, tip_relief_um=tip_relief[0], tip_relief_start_diameter_mm=tip_relief[1]
    )
    pts = with_root_land(
        profile,
        profile.transverse_right_boundary(fillet_points=24, flank_points=48, to_tip_circle=True),
    )
    return ToothGear(
        teeth=profile.z,
        center_x_mm=0.0,
        reference_radius_mm=round(stage.reference_diameter_mm[index] / 2.0, 4),
        base_radius_mm=round(stage.base_diameter_mm[index] / 2.0, 4),
        tip_radius_mm=round((profile.d_a or profile.d_Na) / 2.0, 4),
        root_radius_mm=round(profile.root_diameter_mm / 2.0, 4),
        half_flank=[[round(float(p[0]), 4), round(float(p[1]), 4)] for p in pts],
    )


@router.post("/tooth-profile", response_model=ToothProfileResponse)
def tooth_profile(req: StageParams) -> ToothProfileResponse:
    """Both gears' real tooth flanks for the mesh plot (Zahneingriff), from THE shared stage."""
    stage = req.stage()
    a = stage.working_center_distance_mm
    try:
        pinion = _tooth_gear_from_profile(stage, 0, req.tip_relief(0))
        wheel_gear = _tooth_gear_from_profile(stage, 1, req.tip_relief(1))
    except ValueError as exc:  # e.g. helical stage (2-D profile is spur-only, NRM-02)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    wheel = wheel_gear.model_copy(update={"center_x_mm": round(a, 4)})
    loa = line_of_action_points(stage)
    line = (
        LineOfAction(
            t1=[round(v, 4) for v in loa.t1],
            t2=[round(v, 4) for v in loa.t2],
            a=[round(v, 4) for v in loa.a],
            b=[round(v, 4) for v in loa.b],
            c=[round(v, 4) for v in loa.c],
            d=[round(v, 4) for v in loa.d],
            e=[round(v, 4) for v in loa.e],
            working_pressure_angle_deg=round(loa.working_pressure_angle_deg, 4),
            path_of_contact_mm=round(loa.path_of_contact_mm, 4),
            transverse_base_pitch_mm=round(loa.transverse_base_pitch_mm, 4),
            working_pitch_radius_mm=[round(v, 4) for v in loa.working_pitch_radius_mm],
            base_radius_mm=[round(v, 4) for v in loa.base_radius_mm],
        )
        if loa is not None
        else None
    )
    return ToothProfileResponse(
        center_distance_mm=round(a, 4), pinion=pinion, wheel=wheel, line_of_action=line
    )


def _round(value: float | None, digits: int = 3) -> float | None:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return None
    return round(float(value), digits)
