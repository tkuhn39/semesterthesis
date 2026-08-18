"""
@module: app.api.design
@context: API layer — free gear-pair definition, presets and STplus import (plan v2, M6).
@role: The product vision's entry paths: (a) FZG presets (kst-E first, structure extensible),
       (b) STplus ``.ste`` upload (sent as text — parsed with the existing io layer, no extra
       dependency), (c) fully parametric definition. ``StageParams`` is the shared stage model
       every mesh/contour/deck endpoint consumes, including the tool reference profile
       (DIN 867 / DIN 3972 presets) and the per-flank micro-geometry fields (ISO 21771 §6,
       mechanically inactive until the load-distribution step — see geometry/modifications.py).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.stage_params import StageParams, kst_e_stage
from app.io.ste import Pair, gear_stage_from_ste, parse_ste
from app.services.geometry.gear import GearStage
from app.services.materials import CATALOG, DEFAULT_BY_KIND

__all__ = ["StageParams", "TOOL_PRESETS", "router"]

router = APIRouter(prefix="/api", tags=["design"])

#: DIN 3972 tool reference profiles (h_aP0* per Bezugsprofil; ρ ≈ 0.2·m per the standard,
#: ISO 53 profile A uses 0.38). III/IV are pre-cut profiles (finish stock left on the flank).
TOOL_PRESETS: dict[str, dict[str, float | str]] = {
    "iso53-a": {"addendum_factor": 1.25, "tip_radius_factor": 0.38, "label": "ISO 53 A (Standard)"},
    "din3972-i": {
        "addendum_factor": 1.167,
        "tip_radius_factor": 0.2,
        "label": "DIN 3972 I (Fertig)",
    },
    "din3972-ii": {
        "addendum_factor": 1.25,
        "tip_radius_factor": 0.2,
        "label": "DIN 3972 II (Fertig)",
    },
    "din3972-iii": {
        "addendum_factor": 1.25,
        "tip_radius_factor": 0.2,
        "label": "DIN 3972 III (Vorverzahnung +0.25·∛m Aufmaß)",
    },
}


class PresetInfo(BaseModel):
    id: str
    name: str
    description: str
    params: StageParams


class PresetsResponse(BaseModel):
    presets: list[PresetInfo]
    tools: dict[str, dict[str, float | str]]


@router.get("/presets", response_model=PresetsResponse)
def presets() -> PresetsResponse:
    """FZG standard gear presets (kst-E for now; drop further .ste files to extend) + tools."""
    stage = kst_e_stage()
    width = stage.face_width_mm or Pair(17.0, 15.0)
    kst_e = StageParams(
        use_example=True,
        normal_module_mm=stage.normal_module_mm,
        teeth_pinion=stage.teeth[0],
        teeth_wheel=stage.teeth[1],
        profile_shift_pinion=round(stage.profile_shift[0], 4),
        profile_shift_wheel=round(stage.profile_shift[1], 4),
        normal_pressure_angle_deg=stage.normal_pressure_angle_deg,
        helix_angle_deg=stage.helix_angle_deg,
        face_width_pinion_mm=abs(width[0]),
        face_width_wheel_mm=abs(width[1]),
        center_distance_mm=stage.center_distance_mm,
    )
    return PresetsResponse(
        presets=[
            PresetInfo(
                id="kst-e",
                name="kst-E (FZG)",
                description=(
                    "Stahlritzel z=51 + Kunststoffrad z=52, a=52 mm — die validierte Referenz"
                ),
                params=kst_e,
            )
        ],
        tools=TOOL_PRESETS,
    )


class SteImportRequest(BaseModel):
    """The .ste file content as text (the browser reads the file client-side)."""

    content: str = Field(min_length=10)


class SteImportResponse(BaseModel):
    params: StageParams
    notes: list[str]


@router.post("/import/ste", response_model=SteImportResponse)
def import_ste(req: SteImportRequest) -> SteImportResponse:
    """Parse an STplus ``.ste`` input into editable stage parameters."""
    try:
        stage = GearStage.from_ste(gear_stage_from_ste(parse_ste(req.content)))
    except Exception as exc:  # parser errors surface as 422 with the reason
        raise HTTPException(422, f"could not parse .ste: {exc}") from exc
    width = stage.face_width_mm or Pair(17.0, 15.0)
    gen = stage.generation
    tool0 = gen[0].tool if gen is not None else None
    tool1 = gen[1].tool if gen is not None else None  # per-gear tools (kst-E: 1.1/1.25)
    params = StageParams(
        use_example=False,
        normal_module_mm=stage.normal_module_mm,
        teeth_pinion=stage.teeth[0],
        teeth_wheel=stage.teeth[1],
        profile_shift_pinion=round(stage.profile_shift[0], 4),
        profile_shift_wheel=round(stage.profile_shift[1], 4),
        normal_pressure_angle_deg=stage.normal_pressure_angle_deg,
        helix_angle_deg=stage.helix_angle_deg,
        face_width_pinion_mm=abs(width[0]),
        face_width_wheel_mm=abs(width[1]),
        center_distance_mm=stage.center_distance_mm,
        tool_addendum_factor=tool0.addendum_factor if tool0 is not None else 1.25,
        tool_tip_radius_factor=(tool0.tip_radius_factor or 0.38) if tool0 is not None else 0.38,
        tool_dedendum_factor=tool0.dedendum_factor if tool0 is not None else None,
        tool_root_form_height_factor=tool0.root_form_height_factor if tool0 is not None else None,
        tool_edge_break_angle_deg=tool0.edge_break_angle_deg if tool0 is not None else None,
        tool_addendum_factor_gear2=tool1.addendum_factor if tool1 is not None else None,
        tool_tip_radius_factor_gear2=tool1.tip_radius_factor if tool1 is not None else None,
        tool_dedendum_factor_gear2=tool1.dedendum_factor if tool1 is not None else None,
        tool_root_form_height_factor_gear2=(
            tool1.root_form_height_factor if tool1 is not None else None
        ),
        tool_edge_break_angle_deg_gear2=tool1.edge_break_angle_deg if tool1 is not None else None,
    )
    return SteImportResponse(params=params, notes=stage.check_validity())


# --------------------------------------------------------------------------- #
# Material catalog (SSOT served, audit F2/P2)                                  #
# --------------------------------------------------------------------------- #
class CatalogMaterialOut(BaseModel):
    """One servable catalog material — THE source the Werkstoff-tab name options and
    the frontend's name→kind mirror must follow (the catalog used to be maintained in
    three places that could drift silently)."""

    name: str
    kind: str  # "steel" | "plastic" — drives the norm dispatch (ADR-026)
    elastic_modulus_mpa: float
    poisson_ratio: float
    density_kg_dm3: float | None
    sigma_hlim_mpa: float | None
    sigma_flim_mpa: float | None
    is_default_for_kind: bool


@router.get("/materials/catalog", response_model=list[CatalogMaterialOut])
def materials_catalog() -> list[CatalogMaterialOut]:
    """THE material catalog: names, kinds and core properties (single source)."""
    return [
        CatalogMaterialOut(
            name=mat.name,
            kind=mat.kind.value,
            elastic_modulus_mpa=mat.elastic_modulus_mpa,
            poisson_ratio=mat.poisson_ratio,
            density_kg_dm3=(mat.density_kg_m3 / 1000.0 if mat.density_kg_m3 else None),
            sigma_hlim_mpa=mat.sigma_hlim_mpa,
            sigma_flim_mpa=mat.sigma_flim_mpa,
            is_default_for_kind=DEFAULT_BY_KIND[mat.kind] == name,
        )
        for name, mat in CATALOG.items()
    ]
