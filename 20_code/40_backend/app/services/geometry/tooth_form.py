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

import numpy as np

from app.io.ste import Pair
from app.services.geometry.gear import GearStage
from app.services.geometry.generation import involute
from app.services.geometry.tooth_root import ToothRootGeometry


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
        root_fillet_radius_mm: float,
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
        self.rho_F = root_fillet_radius_mm  # DIN 3990 / ISO 6336-3 root fillet radius ρ_F

    @classmethod
    def from_stage(cls, stage: GearStage, index: int) -> "ToothProfile":
        """Build for gear ``index`` (0 = pinion, 1 = wheel) from a built `GearStage`."""
        if stage.generation is None or stage.usable_tip_diameter_mm is None:
            raise ValueError("tooth profile needs the generation/tip data (tool + KOPFKREISDM)")
        gen = stage.generation[index]
        root = ToothRootGeometry.from_stage(stage, index)  # validated DIN 3990 / ISO 6336-3 ρ_F
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
            root_fillet_radius_mm=root.root_fillet_radius_mn * stage.normal_module_mm,
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

    @property
    def _psi_base(self) -> float:
        """Involute constant: half tooth-thickness angle at d plus inv(α_n)."""
        half = self._as_cut_tooth_thickness_mm / (2.0 * self.reference_radius_mm)
        return half + involute(self.alpha)

    def _involute_half_angle(self, radius: float) -> float:
        """Right-flank involute half-angle θ(r) from the tooth centre line (+y), radius ≥ d_b/2."""
        alpha_y = math.acos(min(1.0, self.d_b / 2.0 / radius))
        return self._psi_base - involute(alpha_y)

    def flank_points(self, count: int = 60) -> list[Pair[float]]:
        """Involute right-flank points from d_Ff to d_Na (root form → usable tip)."""
        points: list[Pair[float]] = []
        for i in range(count):
            radius = (self.d_Ff + (self.d_Na - self.d_Ff) * i / (count - 1)) / 2.0
            theta = self._involute_half_angle(radius)  # half angle from tooth centre line
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

    def transverse_right_boundary(
        self, *, fillet_points: int = 40, flank_points: int = 80
    ) -> list[Pair[float]]:
        """Clean continuous right-flank boundary d_f → d_Na (rounded root fillet + involute flank).

        The root fillet is the circular arc of radius ρ_F (DIN 3990 / ISO 6336-3) **tangent to the
        involute flank** (at the true form circle d_Ff, by bisection) **and tangent to the root
        circle d_f** — so it joins the flank C1 and blends into the root, giving a monotone, rounded
        root without the pinch the raw trochoid produced. Half-angle is monotone non-increasing with
        radius (root widest, tip narrowest); points are ordered root → tip.
        """
        r_f, r_na, rho = self.root_diameter_mm / 2.0, self.d_Na / 2.0, self.rho_F
        r_lo = max(self.d_b / 2.0 + 1e-6, r_f)  # involute only valid above the base circle

        def flank(r: float) -> tuple[float, float]:
            a = self._involute_half_angle(r)
            return r * math.sin(a), r * math.cos(a)

        def gap_normal(r: float) -> tuple[float, float]:
            x0, y0 = flank(r)
            x1, y1 = flank(r + 1e-4)
            tx, ty = x1 - x0, y1 - y0
            tn = math.hypot(tx, ty)
            nx, ny = -ty / tn, tx / tn  # flank normal pointing into the gap (+x side)
            return (nx, ny) if nx > 0.0 else (-nx, -ny)

        def centre_dist(r: float) -> float:  # |C(r)| for the ρ_F arc centre offset into the gap
            x0, y0 = flank(r)
            nx, ny = gap_normal(r)
            return math.hypot(x0 + rho * nx, y0 + rho * ny)

        # Fillet arc of radius ρ_F tangent to the flank (at the true d_Ff) and the root circle:
        # its centre sits on the flank gap-side offset at radius r_f + ρ_F. Solve d_Ff by bisection.
        target = r_f + rho
        lo, hi = r_lo, r_na
        if rho <= 1e-6 or centre_dist(lo) >= target:  # no room for a fillet — involute to the root
            grid = np.linspace(r_lo, r_na, fillet_points + flank_points)
            return [Pair(*flank(float(r))) for r in grid]
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if centre_dist(mid) < target:
                lo = mid
            else:
                hi = mid
        r_ff = 0.5 * (lo + hi)  # actual form circle (flank tangent point)
        jx, jy = flank(r_ff)
        nx, ny = gap_normal(r_ff)
        cx, cy = jx + rho * nx, jy + rho * ny
        c_norm = math.hypot(cx, cy)
        txr, tyr = r_f * cx / c_norm, r_f * cy / c_norm  # tangent point on the root circle
        a_j = math.atan2(jy - cy, jx - cx)
        a_t = math.atan2(tyr - cy, txr - cx)
        delta = a_j - a_t  # sweep root → flank along the SHORT arc
        while delta <= -math.pi:
            delta += 2.0 * math.pi
        while delta > math.pi:
            delta -= 2.0 * math.pi
        pts: list[Pair[float]] = []
        for k in range(fillet_points):  # root tangent → flank tangent (the rounded fillet arc)
            a = a_t + delta * k / (fillet_points - 1)
            pts.append(Pair(cx + rho * math.cos(a), cy + rho * math.sin(a)))
        for r in np.linspace(r_ff, r_na, flank_points)[1:]:  # flank tangent → tip (skip junction)
            pts.append(Pair(*flank(float(r))))
        return pts
