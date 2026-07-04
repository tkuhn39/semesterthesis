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
        tool_root_form_height_factor=tool0.root_form_height_factor if tool0 is not None else None,
        tool_edge_break_angle_deg=tool0.edge_break_angle_deg if tool0 is not None else None,
    )
    return SteImportResponse(params=params, notes=stage.check_validity())
