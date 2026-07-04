"""
@module: app.api.stage_params
@context: API layer — THE shared stage model (single source of truth, user decision
          2026-07-04: "the geometry active in the system must be identical in every tab").
@role: ``StageParams`` is the one request model every endpoint that needs the gear pair
       consumes — geometry, capacity, dynamics, tooth profile, mesh, contour and deck all
       derive their :class:`GearStage` from the SAME parameters, so a change in one tab is
       reflected everywhere. Also hosts the kst-E example loader (``use_example=True``
       short-circuits to the validated reference stage). Split out of ``app.api.design`` so
       ``analysis``/``mesh``/``design`` can share it without import cycles.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.io.ste import Pair, gear_stage_from_ste, load_ste
from app.services.geometry.gear import GearStage, ToolReferenceProfile
from app.services.geometry.modifications import GearModifications


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
    if len(parents) > 4:  # dev checkout: <repo>/20_code/40_backend/app/api/stage_params.py
        candidates.append(
            parents[4] / "30_references_and_examples" / "33_STplus" / "kst-E_eingabe.ste"
        )
    return next((c for c in candidates if c.exists()), None)


@lru_cache(maxsize=1)
def kst_e_stage() -> GearStage:
    """The preloaded, validated kst-E steel–plastic reference stage."""
    path = _example_ste_path()
    if path is None:
        raise HTTPException(503, "example data (kst-E .ste) not found; set EXAMPLE_DATA_FILE")
    return GearStage.from_ste(gear_stage_from_ste(load_ste(path)))


class StageParams(BaseModel):
    """Free gear-pair definition; ``use_example=True`` short-circuits to the kst-E stage."""

    use_example: bool = True
    normal_module_mm: Annotated[float, Field(gt=0.0)] = 1.0
    teeth_pinion: Annotated[int, Field(ge=5)] = 51
    teeth_wheel: Annotated[int, Field(ge=5)] = 52
    profile_shift_pinion: float = 0.2034
    profile_shift_wheel: float = 0.3143
    normal_pressure_angle_deg: Annotated[float, Field(gt=5.0, lt=35.0)] = 20.0
    helix_angle_deg: float = 0.0
    face_width_pinion_mm: Annotated[float, Field(gt=0.0)] = 17.0
    face_width_wheel_mm: Annotated[float, Field(gt=0.0)] = 15.0
    center_distance_mm: Annotated[float, Field(gt=0.0)] | None = None
    # tool reference profile (DIN 867 semantics; presets: design.TOOL_PRESETS)
    tool_addendum_factor: Annotated[float, Field(gt=0.5, lt=2.0)] = 1.25
    tool_tip_radius_factor: Annotated[float, Field(ge=0.0, lt=0.47)] = 0.38
    tool_dedendum_factor: Annotated[float, Field(gt=0.5, lt=2.0)] | None = None
    tool_root_form_height_factor: Annotated[float, Field(gt=0.0, lt=2.0)] | None = None
    tool_edge_break_angle_deg: Annotated[float, Field(gt=0.0, lt=80.0)] | None = None
    # tip circles: explicit d_a, else from the gear addendum factor (DIN 21771)
    gear_addendum_factor: float = 1.0
    tip_diameter_pinion_mm: Annotated[float, Field(gt=0.0)] | None = None
    tip_diameter_wheel_mm: Annotated[float, Field(gt=0.0)] | None = None
    # mean tooth-width allowance A_We (Toleranzen tab; drives x_E and the deck backlash)
    tooth_width_allowance_pinion_mm: float = 0.0
    tooth_width_allowance_wheel_mm: float = 0.0
    # micro-geometry (per flank per gear; carried + symmetry-checked, mechanics later)
    modifications_pinion: GearModifications = Field(default_factory=GearModifications)
    modifications_wheel: GearModifications = Field(default_factory=GearModifications)

    def stage(self) -> GearStage:
        if self.use_example:
            return kst_e_stage()
        tool = ToolReferenceProfile(
            addendum_factor=self.tool_addendum_factor,
            tip_radius_factor=self.tool_tip_radius_factor,
            dedendum_factor=self.tool_dedendum_factor,
            root_form_height_factor=self.tool_root_form_height_factor,
            normal_pressure_angle_deg=self.normal_pressure_angle_deg,
            edge_break_angle_deg=self.tool_edge_break_angle_deg,
        )
        tip = (
            Pair(self.tip_diameter_pinion_mm, self.tip_diameter_wheel_mm)
            if self.tip_diameter_pinion_mm is not None and self.tip_diameter_wheel_mm is not None
            else None
        )
        try:
            return GearStage.from_parameters(
                normal_module_mm=self.normal_module_mm,
                teeth=Pair(self.teeth_pinion, self.teeth_wheel),
                profile_shift=Pair(self.profile_shift_pinion, self.profile_shift_wheel),
                face_width_mm=Pair(self.face_width_pinion_mm, self.face_width_wheel_mm),
                tool=Pair(tool, tool),
                normal_pressure_angle_deg=self.normal_pressure_angle_deg,
                helix_angle_deg=self.helix_angle_deg,
                center_distance_mm=self.center_distance_mm,
                tip_diameter_mm=tip,
                gear_addendum_factor=self.gear_addendum_factor,
                tooth_width_allowance_mm=Pair(
                    self.tooth_width_allowance_pinion_mm, self.tooth_width_allowance_wheel_mm
                ),
            )
        except (ValueError, ZeroDivisionError) as exc:
            raise HTTPException(422, f"invalid gear geometry: {exc}") from exc

    def mirror_symmetric(self, gear: int) -> bool:
        """Flank-symmetry policy: mirror the tooth only when left/right data agree."""
        mods = self.modifications_pinion if gear == 1 else self.modifications_wheel
        return mods.is_symmetric
