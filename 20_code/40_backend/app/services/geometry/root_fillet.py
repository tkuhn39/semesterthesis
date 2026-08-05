"""
@module: app.services.geometry.root_fillet
@context: Domain layer — optimized tooth-root fillet strategies (plan v2 workstream C).
@role: Pluggable root-fillet geometries for the transverse tooth boundary. The standard
       tool-generated fillet stays the default (ρ_F arc in ``tooth_form``, exact trochoid via
       ``root_fillet_points``); these strategies add the literature-backed optimized shapes for
       molded plastic gears (see ``00_development_documentation/root_fillet_strategies.md``):

       - :class:`EllipticFillet` — axis-aligned ellipse, symmetric about the gap centre,
         G1-tangent to the involute at d_Ff (Kassem AGMA 22FTM13; 10–24 % σ reduction).
       - :class:`FruheEllipticFillet` — TILTED ellipse per Frühe (Diss. TU München 2012,
         §5.4.1 Eqs. 89–100): G1 at d_Ff AND at the gap centreline; the root diameter is a
         RESULT of the fit. Parameters tilt γ (study optimum 30°) and aspect a/b (optimum 3.0).
       - :class:`LandiEllipticFillet` — double-tangent AXIS-ALIGNED ellipse per Landi et al.
         2021 (MMT 166, 104496): pass + tangency to the involute at D1 (raisable towards the
         limit contact diameter, ``ra_f``) and to the root circle at D2 (``d2_frac`` of the
         angle to the gap centreline).
       - :class:`BezierFillet` — cubic Bézier between the two facing d_Ff junctions with
         control points on the involute tangents (G1), one factor ``be`` (Roth/Opferkuch,
         Voith; optimum ≈ 0.57, robust 0.46–0.81).
       - :class:`BionicFillet` — tension-triangle-inspired tangent curve + centre arc
         (Voith 2009 / Kassem Eq. 14–17 form, parameters wedge angle γ_b and arc factor b_f).

       All emit the right-half fillet polyline (gap centre → d_Ff junction) in the tooth frame;
       the mating-tip interference check (:func:`mating_tip_clearance`) is mandatory before
       using an optimized fillet in a deck. Manufacturing: molded/WEDM gears only — cut gears
       must stay with tool-generated fillets (DIN 3972 / protuberance).

Frame conventions: tooth frame (+y = tooth centre line, right flank on +x); the right-side gap
centre axis lies π/z *clockwise* from +y. The gap frame used internally has the gap centre
axis as +v; u is the transverse offset across the gap — the tooth-side junction sits at u < 0,
its mirror image on the neighbouring tooth at u > 0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from scipy.optimize import fsolve

from app.io.ste import Pair
from app.services.geometry.tooth_form import ToothProfile

__all__ = [
    "EllipticFillet",
    "FruheEllipticFillet",
    "LandiEllipticFillet",
    "BezierFillet",
    "DongToolBezierFillet",
    "BionicFillet",
    "PointsFillet",
    "TrochoidFillet",
    "fillet_boundary",
    "junction_radius_mm",
    "mating_tip_clearance",
    "rack_tip_envelope",
    "with_root_land",
]


def _gap_frame(profile: ToothProfile) -> float:
    """Angle of the right-side gap centre axis, measured CW from the tooth centre (+y)."""
    return math.pi / profile.z


def _to_gap(profile: ToothProfile, x: float, y: float) -> tuple[float, float]:
    d = _gap_frame(profile)
    c, s = math.cos(d), math.sin(d)
    return (c * x - s * y, s * x + c * y)  # rotate CCW by +delta: gap axis -> +y


def _to_tooth(profile: ToothProfile, u: float, v: float) -> tuple[float, float]:
    d = _gap_frame(profile)
    c, s = math.cos(d), math.sin(d)
    return (c * u + s * v, -s * u + c * v)  # rotate CW by delta (inverse of _to_gap)


def _junction(
    profile: ToothProfile, *, offset_mm: float = 0.0
) -> tuple[float, float, float, tuple[float, float]]:
    """Right-flank d_Ff junction in the gap frame.

    Returns (u_P, v_P, slope dv/du, unit tangent pointing DOWN the flank into the gap).
    The tooth-side junction sits at u_P < 0; going down the flank u increases toward the gap
    centre axis (u = 0). ``offset_mm`` nudges the junction radially inward — the literature's
    interference fallback (Landi/Kassem: 0.03–0.05 mm; see root_fillet_strategies.md).
    """
    r_j = profile.d_Ff / 2.0 - offset_mm
    step = 1e-2
    theta = profile._involute_half_angle(r_j)  # noqa: SLF001 — same-package geometry access
    x, y = r_j * math.sin(theta), r_j * math.cos(theta)
    theta2 = profile._involute_half_angle(r_j + step)  # noqa: SLF001
    x2, y2 = (r_j + step) * math.sin(theta2), (r_j + step) * math.cos(theta2)
    u1, v1 = _to_gap(profile, x, y)
    u2, v2 = _to_gap(profile, x2, y2)
    du, dv = u1 - u2, v1 - v2  # down-flank (radius decreasing)
    norm = math.hypot(du, dv)
    return (u1, v1, dv / du, (du / norm, dv / norm))


@dataclass(frozen=True)
class EllipticFillet:
    """Axis-aligned ellipse (Kassem AGMA): ``e_f`` shifts its root point, d_f,e = d_f + m_n·e_f."""

    e_f: float = 0.0
    points: int = 60
    junction_offset_mm: float = 0.0

    def right_half(self, profile: ToothProfile) -> list[Pair[float]]:
        u_p, v_p, slope, _ = _junction(profile, offset_mm=self.junction_offset_mm)
        v_root = profile.root_diameter_mm / 2.0 + profile.mn * self.e_f / 2.0

        def eqs(ab: np.ndarray) -> tuple[float, float]:
            a, b = abs(ab[0]), abs(ab[1])
            v_c = v_root + b
            inside = max(1.0 - (u_p / a) ** 2, 1e-12)
            on_curve = (v_c - b * math.sqrt(inside)) - v_p
            tangent = (b * u_p) / (a * a * math.sqrt(inside)) - slope
            return (on_curve, tangent)

        guess = np.array([abs(u_p) * 1.3, max(v_p - v_root, 1e-3) * 1.4])
        a, b = np.abs(fsolve(eqs, guess, full_output=False))
        residual = np.hypot(*eqs(np.array([a, b])))
        if residual > 1e-6:
            raise ValueError(f"elliptic fillet fit failed (e_f={self.e_f}): residual {residual}")
        v_c = v_root + b
        t_p = math.asin(min(1.0, max(-1.0, -u_p / a)))  # u = -a sin t (t=0 at gap centre)
        out: list[Pair[float]] = []
        for t in np.linspace(0.0, t_p, self.points):
            u = -a * math.sin(t)
            v = v_c - b * math.cos(t)
            out.append(Pair(*_to_tooth(profile, u, v)))
        return out


@dataclass(frozen=True)
class FruheEllipticFillet:
    """Tilted ellipse per Frühe (Diss. TU München 2012, §5.4.1, Eqs. 89–100).

    The ellipse is fitted tangent-continuously at the d_Ff junction AND at the gap
    centreline, where the mirrored ellipses of the two facing flanks meet perpendicular to
    the centreline. The root diameter therefore FALLS OUT of the fit (Frühe: "Aus der
    Tangentenstetigkeit ergibt sich zwangsläufig … der Fußkreisdurchmesser"). Free
    parameters: ``tilt_deg`` = tilt γ of the major axis against the centreline normal
    (study optimum 30°) and ``aspect`` = a/b (study optimum 3.0); γ = 30°, a/b = 3.0 gave
    −11.9 % σ_F,FEM on average over the 19 reference gears (overall ellipse optimum
    −14.5 %, Abb. 46). The superellipse exponent j (Eq. 101) is deliberately not exposed —
    Frühe found no further benefit (−14.8 %).

    Solved in closed form: with unit-major-axis coordinates x̂(m) = −sgn(m)/√(ρ²/m² + 1),
    ŷ(m) = ρ·√(1 − x̂²) (ρ = b/a, Eqs. 93/94) for the two known tangent slopes, the closure
    Δy = (x* − Δx)·tan(γ + π/z) (Eq. 99) yields the major axis a directly (Eq. 100). The
    junction slope is taken from the actual flank tangent (exact G1 in our geometry) rather
    than re-deriving α_Ff from the involute.
    """

    tilt_deg: float = 30.0
    aspect: float = 3.0
    points: int = 60
    junction_offset_mm: float = 0.0

    def right_half(self, profile: ToothProfile) -> list[Pair[float]]:
        u_p, v_p, slope, _ = _junction(profile, offset_mm=self.junction_offset_mm)
        gamma = math.radians(self.tilt_deg)
        rho = 1.0 / self.aspect  # b/a
        half_gap = math.pi / profile.z
        tau_f = math.pi / 2.0 - half_gap - gamma  # tangent angle at P_f in the ellipse frame
        if not 0.0 < tau_f < math.pi / 2.0:
            raise ValueError(f"fruehe fillet: tilt {self.tilt_deg}° invalid for z={profile.z}")
        m_f = math.tan(tau_f)  # Eq. (96), > 0
        # Flank tangent angle transformed into the ellipse frame (rotation gap→ellipse = +tau_f).
        m_ff_angle = math.atan(slope) + tau_f
        m_ff = math.tan(m_ff_angle)  # Eq. (95) analogue from the real flank tangent
        if m_ff >= 0.0:
            raise ValueError(
                f"fruehe fillet: tilt {self.tilt_deg}° too small for this flank "
                f"(junction tangent does not descend in the ellipse frame)"
            )

        def unit_point(m: float) -> tuple[float, float]:
            x_hat = -math.copysign(1.0, m) / math.sqrt(rho * rho / (m * m) + 1.0)  # Eq. (93)
            return x_hat, rho * math.sqrt(max(1.0 - x_hat * x_hat, 0.0))  # Eq. (94)

        x_ff, y_ff = unit_point(m_ff)  # junction side, x̂ > 0
        x_f, y_f = unit_point(m_f)  # centreline side, x̂ < 0
        t_axis = math.tan(gamma + half_gap)
        x_star = abs(u_p) / math.sin(gamma + half_gap)  # Eq. (89); |u_p| = u* (⊥ distance)
        denom = (y_ff - y_f) + (x_ff - x_f) * t_axis
        if denom <= 1e-12:
            raise ValueError(
                f"fruehe fillet: degenerate fit (tilt={self.tilt_deg}°, aspect={self.aspect})"
            )
        a = x_star * t_axis / denom  # Eq. (100)
        b = a * rho
        # Map ellipse frame → gap frame: rotate by ψ = π − τ_f — the P_f tangent becomes
        # horizontal AND P_f lands on the centreline RIGHT of the junction (u = 0 > u_p);
        # the ellipse's upper half becomes the concave fillet arc. Anchor at the junction.
        psi = math.pi - tau_f
        c_r, s_r = math.cos(psi), math.sin(psi)

        def to_gap(x: float, y: float) -> tuple[float, float]:
            dx, dy = x - a * x_ff, y - a * y_ff
            return (u_p + c_r * dx - s_r * dy, v_p + s_r * dx + c_r * dy)

        u_c, v_c = to_gap(a * x_f, a * y_f)  # P_f — must land on the gap centreline
        if abs(u_c) > 1e-6 * max(1.0, a):
            raise ValueError(f"fruehe fillet: centreline closure failed (u = {u_c:.3e} mm)")
        if not 0.0 < v_c < v_p:
            raise ValueError(f"fruehe fillet: root point radius {v_c:.3f} mm out of range")
        t_ff = math.atan2(y_ff / rho, x_ff)  # parametric angles (x = a·cos t, y = b·sin t)
        t_f = math.atan2(y_f / rho, x_f)
        out: list[Pair[float]] = []
        for i, t in enumerate(np.linspace(t_f, t_ff, self.points)):
            u, v = to_gap(a * math.cos(t), b * math.sin(t))
            if i == 0:
                u = 0.0  # exact centreline start (closure asserted above)
            out.append(Pair(*_to_tooth(profile, u, v)))
        return out


@dataclass(frozen=True)
class LandiEllipticFillet:
    """Double-tangent, axis-aligned ellipse per Landi et al. 2021 (MMT 166, 104496, §3).

    The ellipse axes are parallel to the tooth axes (paper Fig. 5b); its four parameters
    (x_c, y_c, r_1, r_2) are solved from the paper's Eq. (6) conditions: pass + tangency to
    the involute at D1 and pass + tangency to the ROOT CIRCLE at D2 (solved with fsolve,
    exactly as in the paper, start values from the normals' intersection). D1 sits on the
    involute at d_Ff + ``ra_f``·m_n — the paper's default is the limit contact diameter
    d_Nf (raise ``ra_f`` accordingly); D2 sits on the root circle at ``d2_frac`` of the
    angle towards the gap centreline (paper default: the half-compartment limit,
    d2_frac = 1 — beyond it the mirrored curves would cusp, §3.1). Moving both points is
    the paper's own interference fallback.
    """

    ra_f: float = 0.0
    d2_frac: float = 1.0
    points: int = 60

    def junction_radius_mm(self, profile: ToothProfile) -> float:
        return profile.d_Ff / 2.0 + self.ra_f * profile.mn

    def right_half(self, profile: ToothProfile) -> list[Pair[float]]:
        r_j = self.junction_radius_mm(profile)
        if r_j >= profile.d_Na / 2.0:
            raise ValueError(f"landi fillet: D1 radius {2 * r_j:.3f} mm reaches d_Na")
        # D1 + involute tangent, tooth frame (finite difference like _junction).
        step = 1e-2
        th1 = profile._involute_half_angle(r_j)  # noqa: SLF001 — same-package geometry access
        x1, y1 = r_j * math.sin(th1), r_j * math.cos(th1)
        th1b = profile._involute_half_angle(r_j + step)  # noqa: SLF001
        t1x = (r_j + step) * math.sin(th1b) - x1
        t1y = (r_j + step) * math.cos(th1b) - y1
        # D2 on the root circle + its tangent direction (⊥ radial).
        r_f = profile.root_diameter_mm / 2.0
        phi2 = self.d2_frac * math.pi / profile.z
        x2, y2 = r_f * math.sin(phi2), r_f * math.cos(phi2)
        t2x, t2y = y2, -x2

        def eqs(q: np.ndarray) -> tuple[float, float, float, float]:
            xc, yc, r1, r2 = q[0], q[1], abs(q[2]), abs(q[3])
            r1, r2 = max(r1, 1e-6), max(r2, 1e-6)
            scale = r1 * r1 + r2 * r2
            return (
                ((x1 - xc) / r1) ** 2 + ((y1 - yc) / r2) ** 2 - 1.0,
                (r2 * r2 * (x1 - xc) * t1x + r1 * r1 * (y1 - yc) * t1y) / scale,
                ((x2 - xc) / r1) ** 2 + ((y2 - yc) / r2) ** 2 - 1.0,
                (r2 * r2 * (x2 - xc) * t2x + r1 * r1 * (y2 - yc) * t2y) / scale,
            )

        # Paper start values: centre = intersection of the two normals, radii = distances.
        n1 = np.array([t1y, -t1x])
        if n1[0] < 0.0:
            n1 = -n1  # normal at D1 pointing into the gap
        e2 = np.array([math.sin(phi2), math.cos(phi2)])  # radial line through D2
        mat = np.array([[n1[0], -e2[0]], [n1[1], -e2[1]]])
        try:
            t_s = np.linalg.solve(mat, np.array([-x1, -y1]))
            c0 = np.array([x1, y1]) + t_s[0] * n1
        except np.linalg.LinAlgError:
            c0 = np.array([0.5 * (x1 + x2) + 0.3 * profile.mn, 0.5 * (y1 + y2)])
        r1_0 = max(float(np.hypot(*(c0 - [x1, y1]))), 0.1)
        r2_0 = max(float(np.hypot(*(c0 - [x2, y2]))), 0.1)
        sol, residual = None, math.inf
        for dr, dc in ((1.0, 0.0), (0.6, 0.0), (1.8, 0.0), (1.0, 0.4), (1.4, -0.4)):
            g = np.array([c0[0] + dc * profile.mn, c0[1] + dc * profile.mn, r1_0 * dr, r2_0 * dr])
            cand = fsolve(eqs, g, full_output=False)
            res = float(np.max(np.abs(eqs(cand))))
            if res < residual:
                sol, residual = cand, res
            if residual < 5e-5:
                break
        # residuals are dimensionless (relative on-ellipse / normalized tangency errors);
        # 5e-5 corresponds to sub-µm position error — fsolve stalls just above 1e-6 for
        # off-centre D2 without being geometrically wrong
        if sol is None or residual > 5e-5:
            raise ValueError(
                f"landi fillet fit failed (ra_f={self.ra_f}, d2_frac={self.d2_frac}): "
                f"residual {residual:.2e}"
            )
        xc, yc, r1, r2 = sol[0], sol[1], abs(sol[2]), abs(sol[3])
        t1a = math.atan2((y1 - yc) / r2, (x1 - xc) / r1)
        t2a = math.atan2((y2 - yc) / r2, (x2 - xc) / r1)
        dt = math.remainder(t1a - t2a, 2.0 * math.pi)  # shorter arc D2 → D1
        out: list[Pair[float]] = []
        for t in np.linspace(t2a, t2a + dt, self.points):
            out.append(Pair(xc + r1 * math.cos(t), yc + r2 * math.sin(t)))
        return out


@dataclass(frozen=True)
class BezierFillet:
    """Cubic Bézier between the facing d_Ff junctions, control points on the involute tangents.

    ``be`` scales the control-point distance as a fraction of the junction→tangent-intersection
    length (Roth/Opferkuch: optimum ≈ 0.57, any value in 0.46–0.81 robustly better than the
    classic fillet; values ≥ ~1 loop the curve).
    """

    be: float = 0.57
    points: int = 60
    junction_offset_mm: float = 0.0

    def right_half(self, profile: ToothProfile) -> list[Pair[float]]:
        u_p, v_p, _, tangent = _junction(profile, offset_mm=self.junction_offset_mm)
        # Tangent intersection of the two mirrored flank tangents lies on the gap axis (u=0).
        t_dir = np.array(tangent)
        if t_dir[0] <= 1e-9:
            raise ValueError("bezier fillet: flank tangent does not descend into the gap")
        length = abs(u_p / t_dir[0])  # junction -> tangent intersection along the tangent
        p0 = np.array([u_p, v_p])
        p1 = p0 + self.be * length * t_dir
        p3 = np.array([-u_p, v_p])  # mirrored junction
        p2 = p3 + self.be * length * np.array([-t_dir[0], t_dir[1]])
        out: list[Pair[float]] = []
        for t in np.linspace(0.5, 0.0, self.points):  # gap centre (t=0.5) -> right junction (t=0)
            q = (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3
            out.append(Pair(*_to_tooth(profile, float(q[0]), float(q[1]))))
        return out


def rack_tip_envelope(
    profile: ToothProfile,
    tool_pts: np.ndarray,
    tool_tangents: np.ndarray,
    *,
    r_hi: float,
    count: int,
) -> list[Pair[float]]:
    """Gear-frame envelope of an ARBITRARY rack-tip curve under rolling-rack kinematics.

    ``tool_pts`` are rack-frame points (u along the pitch line from the tooth centre,
    v = depth below the pitch line, tool tip = deepest); ``tool_tangents`` the matching unit
    tangents. For each sample the meshing condition — the curve normal passes through the
    pitch point (r·ψ, 0) — gives the roll angle ψ = (u·τ_u + v·τ_v)/(r·τ_u) in closed form;
    the sample then maps with the same rolling transform as ``root_fillet_points`` (the
    special case "tool tip = circular arc" of this function). Points are filtered to the
    right side and d_f … 2·r_hi, sorted by radius and thinned to ``count``.
    """
    r_ref = profile.reference_radius_mm
    r_lo = profile.root_diameter_mm / 2.0 - 1e-6
    collected: list[tuple[float, Pair[float]]] = []
    for (u_t, v_t), (t_u, t_v) in zip(tool_pts, tool_tangents, strict=True):
        if abs(t_u) < 1e-9:
            continue  # tangent ⊥ pitch line never meshes (outside the involute cone)
        psi = (u_t * t_u + v_t * t_v) / (r_ref * t_u)
        arm = u_t - r_ref * psi
        fx = (r_ref - v_t) * math.sin(psi) + arm * math.cos(psi)
        fy = (r_ref - v_t) * math.cos(psi) - arm * math.sin(psi)
        radius = math.hypot(fx, fy)
        if fx >= 0.0 and r_lo <= radius <= r_hi + 1e-9:
            collected.append((radius, Pair(fx, fy)))
    if len(collected) < 8:
        raise ValueError("rack tip envelope: too few valid points (undercut/degenerate tool?)")
    collected.sort(key=lambda item: item[0])
    if len(collected) <= count:
        return [point for _, point in collected]
    idx = [round(k * (len(collected) - 1) / (count - 1)) for k in range(count)]
    return [collected[i][1] for i in idx]


@dataclass(frozen=True)
class DongToolBezierFillet:
    """Hob-tip Bézier fillet per Dong et al. 2020 (MMT 151, 103910, §2, Eqs. 2–9).

    The GEAR fillet is generated as the hobbing ENVELOPE of a degree-4 Bézier that replaces
    the hob tip corner (Fig. 2): P0 on the straight flank at depth ``dv0``·h_kW below the
    tip, P1 = P0 + m_n·``dv2`` along the flank (G1 to the flank), P4 on the tip line at
    b_kE = ``dv1``·(half tip-land width) from the sharp corner, P3 = P4 − m_n·``dv2`` along
    the tip line (G1 to the tip), P2 interpolated in the P0–P4 box by (``dv3``, ``dv4``).
    dv2–dv4 defaults are the paper's GA optimum (v2=0.150, v3=0.499, v4=0.991; −18.2 %
    σ_max, Fig. 15j). dv1 defaults to 1.0 (P4 on the gap centreline) instead of the paper
    example's fixed v1=0.350: that constraint only pinned the endpoints of THEIR ρ*=0.35
    reference hob — on the kst-E tool (ρ*=0.2) it yields a tighter-than-arc corner
    (+12 % σ), while dv1=1.0 measures −19 %. Because P0 sits higher up the flank than the
    standard arc's tangency, the generated junction lies ABOVE d_Ff — the flank continues
    from :meth:`junction_radius_mm` like Landi's raised D1. Unlike the other optimized
    strategies this fillet IS hob-manufacturable: the optimization changes the TOOL, not
    the part (tip adjustment ≈ 150 µm ≈ m_n/60 in the paper).
    """

    dv0: float = 0.35
    dv1: float = 1.0
    dv2: float = 0.15
    dv3: float = 0.499
    dv4: float = 0.991
    points: int = 60
    samples: int = 400

    def _rack_geometry(self, profile: ToothProfile) -> tuple[np.ndarray, float, float]:
        """Control points (5×2, rack frame) + tip depth v_tip + corner u_C."""
        m, alpha = profile.mn, profile.alpha
        s_half = profile._as_cut_tooth_thickness_mm / 2.0  # noqa: SLF001 — same package
        v_tip = (profile.h_aP0 - profile.x_e) * m
        u_corner = s_half + v_tip * math.tan(alpha)
        land_half = math.pi * m / 2.0 - u_corner  # corner → gap centre on the tip line
        if land_half <= 0.0:
            raise ValueError("dong fillet: no tip land (tool corner past the gap centre)")
        v_p0 = v_tip - self.dv0 * profile.h_aP0 * m  # Eq. (2)/(7): h_kE = v0·h_kW below tip
        if v_p0 <= 0.0:
            raise ValueError(f"dong fillet: dv0={self.dv0} puts P0 above the pitch line")
        p0 = np.array([s_half + v_p0 * math.tan(alpha), v_p0])
        p1 = p0 + m * self.dv2 * np.array([math.sin(alpha), math.cos(alpha)])  # Eq. (3)
        b_ke = land_half * self.dv1  # Eq. (8) — dv1 = 1 puts P4 on the gap centreline
        p4 = np.array([u_corner + b_ke, v_tip])  # Eq. (6)
        p3 = p4 - np.array([m * self.dv2, 0.0])  # Eq. (5)
        p2 = np.array(
            [p0[0] + self.dv3 * (p4[0] - p0[0]), p0[1] + self.dv4 * (p4[1] - p0[1])]
        )  # Eq. (4)
        return np.array([p0, p1, p2, p3, p4]), v_tip, u_corner

    def _bezier(self, profile: ToothProfile) -> tuple[np.ndarray, np.ndarray]:
        """Sampled degree-4 Bézier (Eq. 9) + unit tangents (hodograph)."""
        ctrl, _, _ = self._rack_geometry(profile)
        t = np.linspace(0.0, 1.0, self.samples)[:, None]
        b = (
            (1 - t) ** 4 * ctrl[0]
            + 4 * (1 - t) ** 3 * t * ctrl[1]
            + 6 * (1 - t) ** 2 * t**2 * ctrl[2]
            + 4 * (1 - t) * t**3 * ctrl[3]
            + t**4 * ctrl[4]
        )
        d = (
            4 * (1 - t) ** 3 * (ctrl[1] - ctrl[0])
            + 12 * (1 - t) ** 2 * t * (ctrl[2] - ctrl[1])
            + 12 * (1 - t) * t**2 * (ctrl[3] - ctrl[2])
            + 4 * t**3 * (ctrl[4] - ctrl[3])
        )
        norm = np.hypot(d[:, 0], d[:, 1])[:, None]
        return b, d / np.maximum(norm, 1e-12)

    def junction_radius_mm(self, profile: ToothProfile) -> float:
        """Radius generated by P0 — where the Bézier fillet hands over to the involute."""
        ctrl, _, _ = self._rack_geometry(profile)
        r_ref = profile.reference_radius_mm
        u_t, v_t = float(ctrl[0][0]), float(ctrl[0][1])
        t_u, t_v = math.sin(profile.alpha), math.cos(profile.alpha)  # flank direction at P0
        psi = (u_t * t_u + v_t * t_v) / (r_ref * t_u)
        arm = u_t - r_ref * psi
        fx = (r_ref - v_t) * math.sin(psi) + arm * math.cos(psi)
        fy = (r_ref - v_t) * math.cos(psi) - arm * math.sin(psi)
        return math.hypot(fx, fy)

    def right_half(self, profile: ToothProfile) -> list[Pair[float]]:
        r_j = self.junction_radius_mm(profile)
        if r_j >= profile.d_Na / 2.0:
            raise ValueError(f"dong fillet: junction {2 * r_j:.3f} mm reaches d_Na")
        pts, tangents = self._bezier(profile)
        return rack_tip_envelope(profile, pts, tangents, r_hi=r_j, count=self.points)


@dataclass(frozen=True)
class BionicFillet:
    """Tension-triangle-inspired fillet (Voith 2009 form): tangent curve + centre arc.

    ``gamma_deg`` is the wedge angle at the junction (default: Kassem's rule
    γ_opt = 45° − 180°/z − α_t, always < 65°); ``b_f`` scales the centre arc radius
    r_b = b_f · s_L (gap width at the junctions), recommended 0.3–0.4.
    """

    gamma_deg: float | None = None
    b_f: float = 0.35
    points: int = 60
    junction_offset_mm: float = 0.0

    def right_half(self, profile: ToothProfile) -> list[Pair[float]]:
        # Kassem/Voith convention: work on the POSITIVE gap side (junction at +|u_P|, curve
        # y = a·tan(b·u) + c descending from the junction toward the centre arc), then mirror
        # the samples back onto the tooth side (our junction sits at u < 0).
        u_p_signed, v_p, _, _ = _junction(profile, offset_mm=self.junction_offset_mm)
        u_pos = abs(u_p_signed)
        gamma = (
            math.radians(self.gamma_deg)
            if self.gamma_deg is not None
            else max(0.15, math.pi / 4.0 - math.pi / profile.z - profile.alpha)
        )
        r_b = self.b_f * 2.0 * u_pos  # r_b = b_f · s_L (gap width at the junctions)
        r_f = profile.root_diameter_mm / 2.0
        slope_p = 1.0 / math.tan(gamma)  # dv/du at the junction (rising toward the flank)
        v_c = r_f + r_b  # closure: the centre arc bottoms on the standard root circle

        def eqs(q: np.ndarray) -> tuple[float, float, float, float]:
            a, b, c, u_t = q
            b = abs(b)
            u_t = min(max(abs(u_t), 1e-4), 0.98 * min(r_b, u_pos))
            inside = math.sqrt(max(r_b * r_b - u_t * u_t, 1e-12))
            return (
                a * math.tan(b * u_pos) + c - v_p,
                a * b / math.cos(b * u_pos) ** 2 - slope_p,
                a * b / math.cos(b * u_t) ** 2 - u_t / inside,
                a * math.tan(b * u_t) + c - (v_c - inside),
            )

        guess = np.array([0.2, 0.7 / u_pos, r_f, 0.4 * min(r_b, u_pos)])
        sol = fsolve(eqs, guess, full_output=False)
        residual = float(np.max(np.abs(eqs(sol))))
        if residual > 1e-6:
            raise ValueError(
                f"bionic fillet fit failed (gamma={math.degrees(gamma):.1f} deg, "
                f"b_f={self.b_f}): residual {residual:.2e}"
            )
        a, b, c, u_t = sol[0], abs(sol[1]), sol[2], min(max(abs(sol[3]), 1e-4), 0.98 * r_b)
        out: list[Pair[float]] = []
        # Centre arc from the gap bottom (u=0, v=r_f) up to the tangent point u_t …
        ang_t = math.asin(min(1.0, u_t / r_b))
        for ang in np.linspace(0.0, ang_t, self.points // 2):
            u, v = r_b * math.sin(ang), v_c - r_b * math.cos(ang)
            out.append(Pair(*_to_tooth(profile, -u, v)))  # mirror onto the tooth side
        # … then the tension curve up to the junction.
        for u in np.linspace(u_t, u_pos, self.points - self.points // 2)[1:]:
            v = a * math.tan(b * float(u)) + c
            out.append(Pair(*_to_tooth(profile, -float(u), v)))
        return out


@dataclass(frozen=True)
class PointsFillet:
    """A literal fillet polyline (tooth frame, gap side → junction) used as a strategy.

    Carrier for externally computed curves — e.g. one iteration of the CAO growth loop
    (``services/model/cao_fillet.py``) feeding the mesher.
    """

    pts: tuple[tuple[float, float], ...]

    def junction_radius_mm(self, profile: ToothProfile) -> float:  # noqa: ARG002 — protocol
        return math.hypot(self.pts[-1][0], self.pts[-1][1])

    def right_half(self, profile: ToothProfile) -> list[Pair[float]]:  # noqa: ARG002
        return [Pair(x, y) for x, y in self.pts]


@dataclass(frozen=True)
class TrochoidFillet:
    """The exact tool-generated trochoid (DIN 3960 §3.6.1/A.2.2, ISO 21771 §7) as a strategy.

    The norm-reference root: the envelope of the tool tip rounding ρ_aP0 as the rack rolls,
    from the root circle d_f up to the involute junction at d_Ff. Higher fidelity than the
    default ρ_F arc (whose radius is only the fillet's minimum curvature, DIN 867 §4.5 note);
    kept as an explicit strategy per ADR-017's "later high-fidelity option".
    """

    points: int = 60

    def right_half(self, profile: ToothProfile) -> list[Pair[float]]:
        pts = profile.root_fillet_points(self.points)
        if len(pts) < 8:
            raise ValueError("trochoid fillet: too few valid trochoid points (undercut gear?)")
        return pts


FilletStrategy = (
    EllipticFillet
    | FruheEllipticFillet
    | LandiEllipticFillet
    | BezierFillet
    | DongToolBezierFillet
    | BionicFillet
    | PointsFillet
    | TrochoidFillet
)


class FilletCurve(Protocol):
    """Structural fillet-strategy protocol — anything emitting a right-half polyline.

    Satisfied by every member of :data:`FilletStrategy` and by external strategies that
    cannot live in this module (the FE-driven ``CaoFillet`` in ``services/model``).
    """

    def right_half(self, profile: ToothProfile) -> list[Pair[float]]: ...


def junction_radius_mm(strategy: FilletCurve, profile: ToothProfile) -> float:
    """Radius where the strategy's fillet meets the involute flank.

    d_Ff/2 minus any junction offset by default; strategies that define their own junction
    (Landi's raised D1) override via a ``junction_radius_mm`` method.
    """
    fn = getattr(strategy, "junction_radius_mm", None)
    if callable(fn):
        return float(fn(profile))
    return profile.d_Ff / 2.0 - getattr(strategy, "junction_offset_mm", 0.0)


def fillet_boundary(
    profile: ToothProfile,
    strategy: FilletCurve,
    *,
    flank_points: int = 80,
    to_tip_circle: bool = False,
) -> list[Pair[float]]:
    """Full right boundary with an optimized fillet: gap centre → junction → flank (→ chamfer)."""
    fillet = strategy.right_half(profile)
    flank = profile.flank_points(flank_points, r_start_mm=junction_radius_mm(strategy, profile))
    chamfer = profile.tip_chamfer_points() if to_tip_circle else []
    return fillet + flank[1:] + chamfer


def with_root_land(
    profile: ToothProfile, pts: list[Pair[float]], *, points: int = 16
) -> list[Pair[float]]:
    """Prepend the root-land arc from the right gap centre to the boundary's first point.

    Fillets that leave the root circle BEFORE the gap centreline (the ρ_F arc, the tool
    trochoid) leave a root land on d_f between the two facing fillets — physically part of
    the outer envelope, but missing from the plotted boundary, which visually interrupts the
    contour at d_f (user report 2026-07-04). This completes the polyline with the circular
    arc at the start-point radius from the gap centre axis to the start point. Fillets that
    already reach the gap centre (Bézier, bionic, elliptic) get no extra points.
    """
    if not pts:
        return pts
    u0, v0 = _to_gap(profile, pts[0][0], pts[0][1])
    phi0 = math.atan2(-u0, v0)  # CW angle of the start point off the gap centre axis
    if phi0 <= 1e-9:  # already starts on (or past) the gap centreline
        return pts
    r0 = math.hypot(u0, v0)
    arc = [
        Pair(*_to_tooth(profile, -r0 * math.sin(phi), r0 * math.cos(phi)))
        for phi in np.linspace(0.0, phi0, points, endpoint=False)
    ]
    return arc + pts


def mating_tip_clearance(
    profile: ToothProfile,
    fillet_xy: np.ndarray,
    *,
    mating_tip_radius_mm: float,
    mating_teeth: int,
    centre_distance_mm: float,
    mating_half_tip_rad: float | None = None,
    steps: int = 361,
) -> float:
    """Minimum radial clearance between the fillet and the mating tooth-tip path (mm).

    The mating tip is swept through the mesh in this gear's rotating frame (standard external
    pair, the mating tooth centred in the analyzed gap at mid-roll). Only MATERIAL points of
    the mating tip are swept: the corner range is the mating tip half-thickness angle
    (``mating_half_tip_rad``, e.g. ``ToothProfile.half_thickness_angle(r_tip)``) — sweeping the
    half pitch instead would sample the mating gap (no material) and report false interference.
    For every swept sample in the fillet's angular window the radial margin
    ``r_tip − r_fillet(θ)`` is taken; the minimum is returned. **Negative = interference**
    (fallbacks per Landi/Kassem: nudge the junction 0.03–0.05 mm inward, raise h*_fP, or
    shrink the fillet parameter).
    """
    z1, z2 = profile.z, mating_teeth
    gap_axis = math.pi / 2.0 - _gap_frame(profile)  # right-side gap centre (tooth centre = +y)
    theta_f = np.arctan2(fillet_xy[:, 1], fillet_xy[:, 0])
    r_f = np.hypot(fillet_xy[:, 0], fillet_xy[:, 1])
    order = np.argsort(theta_f)
    theta_f, r_f = theta_f[order], r_f[order]
    centre = np.array([math.cos(gap_axis), math.sin(gap_axis)]) * centre_distance_mm
    half_tip = mating_half_tip_rad if mating_half_tip_rad is not None else 0.6 * math.pi / z2
    best = math.inf
    for t in np.linspace(-1.5 * math.pi / z1, 1.5 * math.pi / z1, steps):
        rot2 = -t * z1 / z2  # mating gear rolls opposite (external pair)
        for corner in np.linspace(-half_tip, half_tip, 9):
            ang = gap_axis + math.pi + rot2 + corner  # mating tip points back into our gap
            tip = centre + mating_tip_radius_mm * np.array([math.cos(ang), math.sin(ang)])
            c, s = math.cos(-t), math.sin(-t)  # transform into our rotating frame
            tip_local = np.array([c * tip[0] - s * tip[1], s * tip[0] + c * tip[1]])
            theta_t = math.atan2(tip_local[1], tip_local[0])
            if theta_f[0] <= theta_t <= theta_f[-1]:
                r_here = float(np.interp(theta_t, theta_f, r_f))
                best = min(best, float(np.hypot(*tip_local)) - r_here)
    return best
