"""
@module: app.services.geometry.gear
@context: Domain layer — spur/helical gear-stage geometry.
@role: Reimplement the standard involute gear-stage geometry (DIN 3960 / ISO 21771)
       from the defining parameters (module, teeth, pressure/helix angle, profile
       shift, center distance). Quantities that can be validated exactly against
       STplus are exposed here; the transverse contact ratio is deferred because
       STplus reduces the effective tip diameter by the tip chamfer (Kopfkanten-
       bruch), which needs the tool/chamfer model.

Convention: per-gear quantities are returned as ``(pinion, wheel)`` tuples.
"""

import math

from pydantic import BaseModel

from app.io.ste import Pair, SteGearStage


def involute(angle_rad: float) -> float:
    """Involute function inv(alpha) = tan(alpha) - alpha (radians)."""
    return math.tan(angle_rad) - angle_rad


def inverse_involute(value: float, *, guess_rad: float = 0.35) -> float:
    """Solve inv(alpha) = ``value`` for alpha (radians) by Newton iteration."""
    alpha = guess_rad
    for _ in range(60):
        delta = (math.tan(alpha) - alpha - value) / math.tan(alpha) ** 2
        alpha -= delta
        if abs(delta) < 1e-14:
            break
    return alpha


class GearStage(BaseModel):
    """A two-gear involute spur/helical stage and its derived geometry.

    ``profile_shift`` and ``center_distance_mm`` follow STplus: if the (nominal)
    center distance is given it drives the working pressure angle; otherwise the
    backlash-free generated value is computed from the profile shifts.
    """

    normal_module_mm: float
    teeth: tuple[int, int]
    normal_pressure_angle_deg: float = 20.0
    helix_angle_deg: float = 0.0
    profile_shift: Pair = (0.0, 0.0)
    center_distance_mm: float | None = None

    @classmethod
    def from_ste(cls, stage: SteGearStage) -> "GearStage":
        """Build from a parsed STplus gear stage (see :mod:`app.io.ste`)."""
        return cls(
            normal_module_mm=stage.normal_module_mm,
            teeth=stage.teeth,
            normal_pressure_angle_deg=stage.pressure_angle_deg[0],
            helix_angle_deg=stage.helix_angle_deg[0],
            profile_shift=stage.profile_shift,
            center_distance_mm=stage.center_distance_mm,
        )

    @property
    def _beta(self) -> float:
        return math.radians(self.helix_angle_deg)

    @property
    def transverse_module_mm(self) -> float:
        return self.normal_module_mm / math.cos(self._beta)

    @property
    def transverse_pressure_angle_deg(self) -> float:
        alpha_n = math.radians(self.normal_pressure_angle_deg)
        return math.degrees(math.atan(math.tan(alpha_n) / math.cos(self._beta)))

    @property
    def reference_diameter_mm(self) -> Pair:
        mt = self.transverse_module_mm
        return (mt * self.teeth[0], mt * self.teeth[1])

    @property
    def base_diameter_mm(self) -> Pair:
        factor = math.cos(math.radians(self.transverse_pressure_angle_deg))
        d1, d2 = self.reference_diameter_mm
        return (d1 * factor, d2 * factor)

    @property
    def reference_center_distance_mm(self) -> float:
        return (self.teeth[0] + self.teeth[1]) * self.transverse_module_mm / 2.0

    @property
    def working_pressure_angle_deg(self) -> float:
        alpha_t = math.radians(self.transverse_pressure_angle_deg)
        if self.center_distance_mm is not None:
            cos_awt = (
                self.reference_center_distance_mm * math.cos(alpha_t) / self.center_distance_mm
            )
            return math.degrees(math.acos(cos_awt))
        z_sum = self.teeth[0] + self.teeth[1]
        x_sum = self.profile_shift[0] + self.profile_shift[1]
        inv_awt = (
            involute(alpha_t)
            + 2.0 * math.tan(math.radians(self.normal_pressure_angle_deg)) * x_sum / z_sum
        )
        return math.degrees(inverse_involute(inv_awt))

    @property
    def working_center_distance_mm(self) -> float:
        if self.center_distance_mm is not None:
            return self.center_distance_mm
        alpha_t = math.radians(self.transverse_pressure_angle_deg)
        alpha_wt = math.radians(self.working_pressure_angle_deg)
        return self.reference_center_distance_mm * math.cos(alpha_t) / math.cos(alpha_wt)

    @property
    def working_pitch_diameter_mm(self) -> Pair:
        factor = math.cos(math.radians(self.working_pressure_angle_deg))
        db1, db2 = self.base_diameter_mm
        return (db1 / factor, db2 / factor)
