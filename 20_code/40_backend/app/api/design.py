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

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.stage_params import StageParams, kst_e_stage
from app.io.ste import Pair, gear_stage_from_ste, parse_ste
from app.services.geometry.gear import GearStage
from app.services.material_store import all_materials, delete_user_material, save_user_material
from app.services.materials import CATALOG, DEFAULT_BY_KIND, Material, MaterialKind

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
# Material catalog (SSOT served, audit F2/P2) + user material library (CRUD)   #
# --------------------------------------------------------------------------- #
class CatalogMaterialOut(BaseModel):
    """One servable catalog material — THE source the Werkstoff-tab name options and
    the frontend's name→kind mirror must follow (the catalog used to be maintained in
    three places that could drift silently). Since the user material library exists,
    ``builtin`` separates the immutable built-ins from user records; the property set
    is complete enough for the frontend to LOAD a selection into its editable
    Werkstoff fields (session-local working copy, never written back)."""

    name: str
    kind: str  # "steel" | "plastic" — drives the norm dispatch (ADR-026)
    elastic_modulus_mpa: float
    poisson_ratio: float
    density_kg_dm3: float | None
    sigma_hlim_mpa: float | None
    sigma_flim_mpa: float | None
    yield_strength_mpa: float | None
    allowable_temperature_c: float | None
    is_default_for_kind: bool
    builtin: bool


def _material_out(mat: Material, *, builtin: bool) -> CatalogMaterialOut:
    return CatalogMaterialOut(
        name=mat.name,
        kind=mat.kind.value,
        elastic_modulus_mpa=mat.elastic_modulus_mpa,
        poisson_ratio=mat.poisson_ratio,
        density_kg_dm3=(mat.density_kg_m3 / 1000.0 if mat.density_kg_m3 else None),
        sigma_hlim_mpa=mat.sigma_hlim_mpa,
        sigma_flim_mpa=mat.sigma_flim_mpa,
        yield_strength_mpa=mat.yield_strength_mpa,
        allowable_temperature_c=mat.allowable_temperature_c,
        is_default_for_kind=builtin and DEFAULT_BY_KIND[mat.kind] == mat.name,
        builtin=builtin,
    )


@router.get("/materials/catalog", response_model=list[CatalogMaterialOut])
def materials_catalog() -> list[CatalogMaterialOut]:
    """THE material catalog: built-ins first, then the user library (single source)."""
    return [_material_out(mat, builtin=mat.name in CATALOG) for mat in all_materials().values()]


class UserMaterialIn(BaseModel):
    """A user-defined material record (the library's reference values).

    The flat shape mirrors the Werkstoff-tab fields; strength values are optional
    (ADR-013 graceful degradation: absent limits only block the sub-results that
    need them). Density in kg/dm³ like the tab.
    """

    name: str = Field(min_length=1, max_length=80)
    kind: Literal["steel", "plastic"]
    elastic_modulus_mpa: float = Field(gt=0.0)
    poisson_ratio: float = Field(gt=0.0, lt=0.5)
    density_kg_dm3: float | None = Field(None, gt=0.0)
    sigma_hlim_mpa: float | None = Field(None, ge=0.0)
    sigma_flim_mpa: float | None = Field(None, ge=0.0)
    yield_strength_mpa: float | None = Field(None, ge=0.0)
    allowable_temperature_c: float | None = None

    def to_material(self) -> Material:
        return Material(
            name=self.name.strip(),
            kind=MaterialKind(self.kind),
            elastic_modulus_mpa=self.elastic_modulus_mpa,
            poisson_ratio=self.poisson_ratio,
            density_kg_m3=(self.density_kg_dm3 * 1000.0 if self.density_kg_dm3 else None),
            sigma_hlim_mpa=self.sigma_hlim_mpa,
            sigma_flim_mpa=self.sigma_flim_mpa,
            yield_strength_mpa=self.yield_strength_mpa,
            allowable_temperature_c=self.allowable_temperature_c,
            source="user",
        )


@router.put("/materials/user", response_model=CatalogMaterialOut)
def save_material(req: UserMaterialIn) -> CatalogMaterialOut:
    """Create or update a user material (upsert by name; built-ins are immutable)."""
    try:
        saved = save_user_material(req.to_material())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _material_out(saved, builtin=False)


@router.delete("/materials/user/{name}", status_code=204)
def delete_material(name: str) -> None:
    """Delete a user material; 404 if unknown, 422 for a built-in name."""
    try:
        deleted = delete_user_material(name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=f"user material not found: {name}")
