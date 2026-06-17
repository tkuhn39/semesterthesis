"""
@module: app.services.geometry.tooth_form
@context: Domain layer — the full transverse tooth profile (the tooth *shape*).
@role: Emit the complete tooth flank as coordinates — the involute flank from the
       root form circle d_Ff to the usable tip d_Na, plus the **root fillet
       trochoid** cut by the tool tip rounding ρ_aP0 down to the root circle d_f.
       This is the plottable/exportable counterpart to the scalar characteristic
       values (form circles, ρ_F, s_Fn) and feeds the FE mesh / CAD (as STplus's
       transverse coordinates do).

As-cut geometry: both the involute phase and the fillet trochoid use the generation
profile shift x_E, so they join continuously at d_Ff and the root reaches d_f
exactly. Validated against STplus (kst-E): the fillet bottom equals d_f and the
flank spans d_Ff … d_Na. Coordinates are in the transverse plane with the tooth
centred on the +y axis (the right flank on +x); spur gears (β = 0).
"""

import math

from app.io.ste import Pair
from app.services.geometry.gear import GearStage
from app.services.geometry.generation import involute


class ToothProfile:
    """Transverse tooth profile generator (right flank: root fillet + involute).

    Built from the per-gear generation; left flank and tooth repetition follow by
    mirroring about the y-axis and rotating by the angular pitch.
    """

    def __init__(
        self,
        *,
        normal_module_mm: float,
        teeth: int,
        normal_pressure_angle_deg: float,
        generation_profile_shift: float,
        tool_addendum_factor: float,
        tool_tip_radius_factor: float,
        base_diameter_mm: float,
        root_form_diameter_mm: float,
        usable_tip_diameter_mm: float,
    ) -> None:
        self.mn = normal_module_mm
        self.z = teeth
        self.alpha = math.radians(normal_pressure_angle_deg)
        self.x_e = generation_profile_shift
        self.h_aP0 = tool_addendum_factor
        self.rho_aP0 = tool_tip_radius_factor
        self.d_b = base_diameter_mm
        self.d_Ff = root_form_diameter_mm
        self.d_Na = usable_tip_diameter_mm

    @classmethod
    def from_stage(cls, stage: GearStage, index: int) -> "ToothProfile":
        """Build for gear ``index`` (0 = pinion, 1 = wheel) from a built `GearStage`."""
        if stage.generation is None or stage.usable_tip_diameter_mm is None:
            raise ValueError("tooth profile needs the generation/tip data (tool + KOPFKREISDM)")
        gen = stage.generation[index]
        return cls(
            normal_module_mm=stage.normal_module_mm,
            teeth=stage.teeth[index],
            normal_pressure_angle_deg=stage.normal_pressure_angle_deg,
            generation_profile_shift=gen.generation_profile_shift,
            tool_addendum_factor=gen.tool.addendum_factor,
            tool_tip_radius_factor=gen.tool.tip_radius_factor,
            base_diameter_mm=stage.base_diameter_mm[index],
            root_form_diameter_mm=gen.root_form_diameter_mm,
            usable_tip_diameter_mm=stage.usable_tip_diameter_mm[index],
        )

    @property
    def reference_radius_mm(self) -> float:
        return self.mn * self.z / 2.0  # spur: m_t = m_n

    @property
    def _as_cut_tooth_thickness_mm(self) -> float:
        return self.mn * math.pi / 2.0 + 2.0 * self.x_e * self.mn * math.tan(self.alpha)

    @property
    def root_diameter_mm(self) -> float:
        """Root circle d_f = d − 2·(h_aP0 − x_E)·m_n (the tool tip cuts to here)."""
        return self.mn * self.z - 2.0 * (self.h_aP0 - self.x_e) * self.mn

    def flank_points(self, count: int = 60) -> list[Pair[float]]:
        """Involute right-flank points from d_Ff to d_Na (root form → usable tip)."""
        r_ref = self.reference_radius_mm
        psi_base = self._as_cut_tooth_thickness_mm / (2.0 * r_ref) + involute(self.alpha)
        r_b = self.d_b / 2.0
        points: list[Pair[float]] = []
        for i in range(count):
            radius = (self.d_Ff + (self.d_Na - self.d_Ff) * i / (count - 1)) / 2.0
            alpha_y = math.acos(r_b / radius)
            theta = psi_base - involute(alpha_y)  # half angle from tooth centre line
            points.append(Pair(radius * math.sin(theta), radius * math.cos(theta)))
        return points

    def root_fillet_points(self, count: int = 40) -> list[Pair[float]]:
        """Root fillet trochoid points (right side) from d_f up to d_Ff.

        The fillet is the envelope of the tool tip rounding (radius ρ_aP0) as the
        rack rolls — the trochoid traced by the rounding centre, offset inward by
        ρ_aP0.
        """
        r_ref = self.reference_radius_mm
        v_tip = (self.h_aP0 - self.x_e) * self.mn
        v_c = v_tip - self.rho_aP0 * self.mn
        u_c = (
            self._as_cut_tooth_thickness_mm / 2.0
            + v_c * math.tan(self.alpha)
            - self.rho_aP0 * self.mn / math.cos(self.alpha)
        )
        rho = self.rho_aP0 * self.mn
        # Sample the rolling angle; keep the inward-offset points within d_f … d_Ff.
        collected: list[tuple[float, Pair[float]]] = []
        steps = 2000
        span = 0.12
        for j in range(steps + 1):
            psi = -span + 2.0 * span * j / steps
            arm = u_c - r_ref * psi
            cx = (r_ref - v_c) * math.sin(psi) + arm * math.cos(psi)
            cy = (r_ref - v_c) * math.cos(psi) - arm * math.sin(psi)
            dx = -v_c * math.cos(psi) - arm * math.sin(psi)
            dy = v_c * math.sin(psi) - arm * math.cos(psi)
            norm = math.hypot(dx, dy)
            nx, ny = dy / norm, -dx / norm
            if nx * cx + ny * cy > 0.0:  # make the normal point toward the gear centre
                nx, ny = -nx, -ny
            fx, fy = cx + rho * nx, cy + rho * ny
            radius = math.hypot(fx, fy)
            if fx >= 0.0 and self.root_diameter_mm / 2.0 - 1e-6 <= radius <= self.d_Ff / 2.0:
                collected.append((radius, Pair(fx, fy)))
        collected.sort(key=lambda item: item[0])
        # Thin to ``count`` points spread over the radius range.
        if len(collected) <= count:
            return [point for _, point in collected]
        idx = [round(k * (len(collected) - 1) / (count - 1)) for k in range(count)]
        return [collected[i][1] for i in idx]

    def right_flank_profile(
        self, *, fillet_points: int = 40, flank_points: int = 60
    ) -> list[Pair[float]]:
        """The whole right flank from the root fillet bottom (d_f) up to the tip (d_Na)."""
        return self.root_fillet_points(fillet_points) + self.flank_points(flank_points)
