"""
@module: app.services.geometry.root_fillet
@context: Domain layer — optimized tooth-root fillet strategies (plan v2 workstream C).
@role: Pluggable root-fillet geometries for the transverse tooth boundary. The standard
       tool-generated fillet stays the default (ρ_F arc in ``tooth_form``, exact trochoid via
       ``root_fillet_points``); these strategies add the literature-backed optimized shapes for
       molded plastic gears (see ``00_development_documentation/root_fillet_strategies.md``):

       - :class:`EllipticFillet` — axis-aligned ellipse, symmetric about the gap centre,
         G1-tangent to the involute at d_Ff (Kassem AGMA 22FTM13; 10–24 % σ reduction).
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

import numpy as np
from scipy.optimize import fsolve

from app.io.ste import Pair
from app.services.geometry.tooth_form import ToothProfile

__all__ = [
    "EllipticFillet",
    "BezierFillet",
    "BionicFillet",
    "TrochoidFillet",
    "fillet_boundary",
    "mating_tip_clearance",
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


def _junction(profile: ToothProfile) -> tuple[float, float, float, tuple[float, float]]:
    """Right-flank d_Ff junction in the gap frame.

    Returns (u_P, v_P, slope dv/du, unit tangent pointing DOWN the flank into the gap).
    The tooth-side junction sits at u_P < 0; going down the flank u increases toward the gap
    centre axis (u = 0).
    """
    r_j = profile.d_Ff / 2.0
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

    def right_half(self, profile: ToothProfile) -> list[Pair[float]]:
        u_p, v_p, slope, _ = _junction(profile)
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
class BezierFillet:
    """Cubic Bézier between the facing d_Ff junctions, control points on the involute tangents.

    ``be`` scales the control-point distance as a fraction of the junction→tangent-intersection
    length (Roth/Opferkuch: optimum ≈ 0.57, any value in 0.46–0.81 robustly better than the
    classic fillet; values ≥ ~1 loop the curve).
    """

    be: float = 0.57
    points: int = 60

    def right_half(self, profile: ToothProfile) -> list[Pair[float]]:
        u_p, v_p, _, tangent = _junction(profile)
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

    def right_half(self, profile: ToothProfile) -> list[Pair[float]]:
        # Kassem/Voith convention: work on the POSITIVE gap side (junction at +|u_P|, curve
        # y = a·tan(b·u) + c descending from the junction toward the centre arc), then mirror
        # the samples back onto the tooth side (our junction sits at u < 0).
        u_p_signed, v_p, _, _ = _junction(profile)
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


FilletStrategy = EllipticFillet | BezierFillet | BionicFillet | TrochoidFillet


def fillet_boundary(
    profile: ToothProfile,
    strategy: FilletStrategy,
    *,
    flank_points: int = 80,
    to_tip_circle: bool = False,
) -> list[Pair[float]]:
    """Full right boundary with an optimized fillet: gap centre → d_Ff → flank (→ chamfer)."""
    fillet = strategy.right_half(profile)
    flank = profile.flank_points(flank_points)
    chamfer = profile.tip_chamfer_points() if to_tip_circle else []
    return fillet + flank[1:] + chamfer


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
