"""
@module: app.services.geometry.gear
@context: Domain layer — spur/helical gear-stage geometry.
@role: Reimplement the standard involute gear-stage geometry (DIN ISO 21771) from
       the defining parameters (module, teeth, pressure/helix angle, profile shift,
       center distance). The transverse contact ratio uses the usable tip diameter
       d_Na = d_Fa from the rack-tool generation (:mod:`app.services.geometry.
       generation`), so the tip chamfer (Kopfkantenbruch) is accounted for exactly.

Convention: per-gear quantities are returned as ``(pinion, wheel)`` tuples.
"""

import math

from pydantic import BaseModel

from app.io.ste import Pair, SteGearStage

# The involute primitives live in the (more foundational) generation module so the
# generation layer never has to import this meshing layer; re-exported here for the
# existing public API.
from app.services.geometry.generation import GearGeneration, inverse_involute, involute

__all__ = ["GearStage", "inverse_involute", "involute"]


class GearStage(BaseModel):
    """A two-gear involute spur/helical stage and its derived geometry.

    ``profile_shift`` and ``center_distance_mm`` follow STplus: if the (nominal)
    center distance is given it drives the working pressure angle; otherwise the
    backlash-free generated value is computed from the profile shifts.
    """

    normal_module_mm: float
    teeth: Pair[int]
    normal_pressure_angle_deg: float = 20.0
    helix_angle_deg: float = 0.0
    profile_shift: Pair[float] = Pair(0.0, 0.0)
    center_distance_mm: float | None = None
    face_width_mm: Pair[float] | None = None
    span_teeth: Pair[int] | None = None
    # Per-gear rack-tool generation; supplies the usable tip diameter (d_Na = d_Fa)
    # for the contact ratio. Absent when the `.ste` carries no tool/tip data.
    generation: Pair[GearGeneration] | None = None

    @classmethod
    def from_ste(cls, stage: SteGearStage) -> "GearStage":
        """Build from a parsed STplus gear stage (see :mod:`app.io.ste`).

        When the `.ste` carries the generating tool profiles and the tip diameter,
        the per-gear generation is built too, enabling the exact contact ratio.
        """
        generation: Pair[GearGeneration] | None = None
        if stage.tools is not None and stage.tip_diameter_mm is not None:
            try:
                generation = Pair(
                    GearGeneration.from_ste_gear(stage, 0),
                    GearGeneration.from_ste_gear(stage, 1),
                )
            except ValueError:
                generation = None
        return cls(
            normal_module_mm=stage.normal_module_mm,
            teeth=stage.teeth,
            normal_pressure_angle_deg=stage.pressure_angle_deg[0],
            helix_angle_deg=stage.helix_angle_deg[0],
            profile_shift=stage.profile_shift,
            center_distance_mm=stage.center_distance_mm,
            face_width_mm=stage.face_width_mm,
            span_teeth=stage.span_teeth,
            generation=generation,
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
    def reference_diameter_mm(self) -> Pair[float]:
        mt = self.transverse_module_mm
        return Pair(mt * self.teeth[0], mt * self.teeth[1])

    @property
    def base_diameter_mm(self) -> Pair[float]:
        factor = math.cos(math.radians(self.transverse_pressure_angle_deg))
        d1, d2 = self.reference_diameter_mm
        return Pair(d1 * factor, d2 * factor)

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
    def working_pitch_diameter_mm(self) -> Pair[float]:
        factor = math.cos(math.radians(self.working_pressure_angle_deg))
        db1, db2 = self.base_diameter_mm
        return Pair(db1 / factor, db2 / factor)

    @property
    def usable_tip_diameter_mm(self) -> Pair[float] | None:
        """Usable tip circle d_Na per gear (= tip form circle d_Fa from generation).

        ``None`` when no tool/tip data is available (then the contact ratio cannot
        be computed exactly).
        """
        if self.generation is None:
            return None
        return Pair(
            self.generation[0].tip_form_diameter_mm,
            self.generation[1].tip_form_diameter_mm,
        )

    @property
    def transverse_base_pitch_mm(self) -> float:
        """Transverse base pitch p_et = pi * m_t * cos(alpha_t) (ISO 21771)."""
        alpha_t = math.radians(self.transverse_pressure_angle_deg)
        return math.pi * self.transverse_module_mm * math.cos(alpha_t)

    @property
    def path_of_contact_mm(self) -> float:
        """Length of the path of contact g_alpha (ISO 21771 eq. 77), using d_Na.

        ``g_alpha = 1/2 [ sqrt(d_Na1^2 - d_b1^2) + (z2/|z2|) sqrt(d_Na2^2 - d_b2^2)
        - 2 a_w sin(alpha_wt) ]``.
        """
        usable = self.usable_tip_diameter_mm
        if usable is None:
            raise ValueError(
                "path of contact needs the usable tip diameters; build from a `.ste` "
                "with tool profiles and KOPFKREISDM"
            )
        db1, db2 = self.base_diameter_mm
        sign2 = 1.0 if self.teeth[1] >= 0 else -1.0
        alpha_wt = math.radians(self.working_pressure_angle_deg)
        return 0.5 * (
            math.sqrt(usable[0] ** 2 - db1**2)
            + sign2 * math.sqrt(usable[1] ** 2 - db2**2)
            - 2.0 * self.working_center_distance_mm * math.sin(alpha_wt)
        )

    @property
    def transverse_contact_ratio(self) -> float:
        """Transverse contact ratio eps_alpha = g_alpha / p_et (ISO 21771 eq. 90)."""
        return self.path_of_contact_mm / self.transverse_base_pitch_mm

    @property
    def overlap_ratio(self) -> float:
        """Overlap ratio eps_beta = b * sin(beta) / (pi * m_n) (ISO 21771 eq. 93).

        Zero for spur gears regardless of width; a helical stage needs the (common)
        face width.
        """
        if abs(self._beta) < 1e-12:
            return 0.0
        if self.face_width_mm is None:
            raise ValueError("overlap ratio of a helical stage needs the face width")
        width = min(abs(self.face_width_mm[0]), abs(self.face_width_mm[1]))
        return width * abs(math.sin(self._beta)) / (math.pi * self.normal_module_mm)

    @property
    def total_contact_ratio(self) -> float:
        """Total contact ratio eps_gamma = eps_alpha + eps_beta (ISO 21771 eq. 97)."""
        return self.transverse_contact_ratio + self.overlap_ratio

    @property
    def span_measurement_mm(self) -> Pair[float] | None:
        """Base tangent length (span) W_k over k teeth per gear (DIN 21773 eq. 14).

        ``W_k = m_n cos(alpha_n) [pi (k - 0.5) + z inv(alpha_t)] + 2 x m_n sin(alpha_n)``.
        ``None`` when the span teeth count k is unknown.
        """
        if self.span_teeth is None:
            return None
        alpha_n = math.radians(self.normal_pressure_angle_deg)
        alpha_t = math.radians(self.transverse_pressure_angle_deg)
        mn = self.normal_module_mm
        spans = [
            mn * math.cos(alpha_n) * (math.pi * (k - 0.5) + z * involute(alpha_t))
            + 2.0 * x * mn * math.sin(alpha_n)
            for z, x, k in zip(self.teeth, self.profile_shift, self.span_teeth, strict=True)
        ]
        return Pair(spans[0], spans[1])

    def check_validity(self) -> list[str]:
        """Advisory input checks: DIN ISO 1328-1 §1 ranges plus mesh sanity.

        Returns human-readable issues (empty means no objection). These are
        advisory, not hard errors: ISO 1328-1 permits values outside its ranges by
        extrapolation/agreement, but flagging them catches typos and inputs that
        mutually exclude one another (e.g. a near-pointed tooth or a mesh that is
        not continuous).
        """
        issues: list[str] = []
        labels = ("pinion", "wheel")
        mn = self.normal_module_mm
        if not 0.5 <= mn <= 70.0:
            issues.append(f"normal module {mn} mm outside ISO 1328-1 range [0.5, 70]")
        if abs(self.helix_angle_deg) > 45.0:
            issues.append(f"helix angle {self.helix_angle_deg} deg exceeds ISO 1328-1 limit 45")
        for label, z in zip(labels, self.teeth, strict=True):
            if not 5 <= abs(z) <= 1000:
                issues.append(f"{label} tooth count |{z}| outside ISO 1328-1 range [5, 1000]")
        for label, d in zip(labels, self.reference_diameter_mm, strict=True):
            if not 5.0 <= abs(d) <= 15000.0:
                issues.append(
                    f"{label} reference diameter {abs(d):.1f} mm "
                    "outside ISO 1328-1 range [5, 15000]"
                )
        if self.face_width_mm is not None:
            for label, width in zip(labels, self.face_width_mm, strict=True):
                if not 4.0 <= width <= 1200.0:
                    issues.append(
                        f"{label} face width {width} mm outside ISO 1328-1 range [4, 1200]"
                    )
        if self.generation is not None:
            if self.total_contact_ratio < 1.0:
                issues.append(
                    f"total contact ratio {self.total_contact_ratio:.3f} < 1 (mesh not continuous)"
                )
            for label, gen in zip(labels, self.generation, strict=True):
                tip_thickness = gen.rest_tip_thickness_mm
                if tip_thickness < 0.2 * mn:
                    issues.append(
                        f"{label} tip thickness {tip_thickness:.3f} mm "
                        "< 0.2*m_n (near-pointed tooth)"
                    )
        return issues
