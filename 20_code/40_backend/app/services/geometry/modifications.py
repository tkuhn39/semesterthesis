"""
@module: app.services.geometry.modifications
@context: Domain layer — flank micro-geometry data model (ISO 21771 §6, plan v2 M6).
@role: Carry the per-flank modification parameters (Kopf-/Fußrücknahme, Profil-/Breiten-
       balligkeit, Endrücknahme, Schrägungswinkelkorrektur) through the stage definition so the
       UI can capture them and the flank-symmetry policy can check them. **Mechanically inactive
       for now**: these µm-scale surface offsets become effective in the load-distribution step
       (RIKOR K_Hβ) and the 3-D rolling contact — the FE mesh/contour intentionally ignores
       them (documented extension point of the symmetry policy: teeth stay rotation-congruent;
       mirror symmetry is dropped automatically when left ≠ right).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class FlankModification(BaseModel):
    """One flank's profile/lead modifications (ISO 21771 §6.2/§6.3), all in µm."""

    tip_relief_um: Annotated[float, Field(ge=0.0, le=500.0)] = 0.0  # C_αa (Kopfrücknahme)
    # Beginn der Kopfrücknahme d_Ca (ISO 21771 — the diameter where the relief ramp starts);
    # None → the tooth profile defaults to d_Na − m_n
    tip_relief_start_diameter_mm: Annotated[float, Field(gt=0.0)] | None = None
    root_relief_um: Annotated[float, Field(ge=0.0, le=500.0)] = 0.0  # C_αf (Fußrücknahme)
    profile_crowning_um: Annotated[float, Field(ge=0.0, le=500.0)] = 0.0  # C_α (Profilballigkeit)
    helix_crowning_um: Annotated[float, Field(ge=0.0, le=500.0)] = 0.0  # C_β (Breitenballigkeit)
    end_relief_um: Annotated[float, Field(ge=0.0, le=500.0)] = 0.0  # C_βe (Endrücknahme)
    helix_slope_um: Annotated[float, Field(ge=-500.0, le=500.0)] = 0.0  # f_Hβ (Schrägungskorr.)


class GearModifications(BaseModel):
    """Per-gear micro-geometry: left and right flank may deliberately differ (load/coast)."""

    left: FlankModification = Field(default_factory=FlankModification)
    right: FlankModification = Field(default_factory=FlankModification)

    @property
    def is_symmetric(self) -> bool:
        """Flank-symmetry policy input: identical left/right parameters → mirror-symmetric
        tooth (DIN 867 §4.2); any difference switches the mesher to rotation-congruence only."""
        return self.left == self.right

    @property
    def is_active(self) -> bool:
        return self.left != FlankModification() or self.right != FlankModification()
