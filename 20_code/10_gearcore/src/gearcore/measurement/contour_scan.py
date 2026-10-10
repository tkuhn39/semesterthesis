"""Contour scans of the Klingelnberg P40 (transverse section of two or three teeth): the axis
and the involutes of every flank, the tip circles, the tip relief, the base tooth thickness,
the angular pitch, the shape of every tip corner (tangent arc or symmetric chamfer), and the
tooth frames that overlay the measured teeth on the nominal tooth of the generation.

The scan points are x, y in mm with the gear axis near the origin; a scan runs from +x to −x,
so every tooth is a right flank (+x side, scanned first) followed by a left flank. Nothing here
is a norm equation: the involute is fitted with the nominal base circle of the generation
(``ScanGeometry``), one rotation angle per flank and one radius per tip land, the axis free; a
robust loss keeps the fillet and the tip corner out of the fit. "Material removed" counts
positive on both hands. The linear tip relief is a straight line through the relief points over
the roll length, the way ISO 21771 and the drawing define it (amount C_a at the tip, start at
the diameter d_Ca; registry ``tip_relief``, ``tip_relief_start_diameter``,
``tip_relief_length``).

Fit statistics (edge size, cut-back, axis offset, RMS) are coordinates of the fit without a
registry name, as in ``gearcore.contour``. The module writes nothing and draws nothing; the
script ``scripts/measurements.py contour`` does that.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import least_squares

from gearcore import contour as ct
from gearcore import involute as iv
from gearcore.errors import InputRangeError
from gearcore.io.p40_contour import ContourScan
from gearcore.models.common import FrozenModel
from gearcore.models.results import GenerationResult

Array = NDArray[np.float64]
Side = Literal["left", "right"]
Shape = Literal["arc", "chamfer"]
RunKind = Literal["tip", "flank", "root"]

EQ_EXEMPT = (
    "scan_geometry",
    "nominal_base_tooth_thickness",
    "segment",
    "fit_axis",
    "fit_corner_shapes",
    "fit_scan",
    "flank_normal_deviation",
    "flank_reliefs",
    "tooth_thicknesses",
    "angular_pitches",
    "measure_corner",
    "fit_corner_shapes",
    "evaluate_scan",
    "tooth_frames",
    "tooth_points",
    "nominal_outline",
    "closest_on_outline",
    "signed_deviation",
    "overlay_points",
    "outward_normals",
    "corner_frame",
)
"""Fits of the scan and its geometry: no equation of a norm."""


class FitSettings(FrozenModel):
    """Bands and windows of the fits (mm unless stated); the defaults are the ones the tip edge
    of the pinion 86481 was measured with on 2026-10-10."""

    tip_band_mm: float = 0.03
    """A point closer than this to the largest radius of its tip land counts as tip land."""
    root_band_mm: float = 0.03
    """A point closer than this to the smallest radius of its root counts as root circle."""
    corner_window_mm: float = 0.40
    """Arc length on either side of a corner that enters the corner fit."""
    corner_exclude_mm: float = 0.08
    """Arc length beside the corner left out of the preliminary straight-line fits."""
    flank_margin_above_root_form_mm: float = 0.15
    """Flank points for the involute fit start this far above the nominal root form radius."""
    flank_margin_below_tip_mm: float = 0.60
    """Flank points for the involute fit end this far below the tip land radius, so that a tip
    relief does not pull the involute (it shows in the relief table instead)."""
    relief_threshold_um: float = 4.0
    """The tip relief starts where the deviation from the involute exceeds this for good."""
    relief_sample_mm: float = 0.05
    """The relief at the tip is the mean deviation of the flank points within this distance of
    the tip land radius."""
    leave_threshold_mm: float = 0.003
    """A point farther than this from the straight piece has left it (resolution 1 µm)."""
    corner_size_max_mm: float = 0.30
    """Largest arc radius or chamfer length tried for a corner."""
    corner_size_step_mm: float = 0.01
    """Step of the size grid of the corner fits."""
    coarse_points: int = 600
    """A scan with fewer points is coarse (the batch of 2026-06-23 has about 400)."""

    def sizes(self) -> Array:
        if not 0.0 < self.corner_size_step_mm <= self.corner_size_max_mm:
            raise InputRangeError("corner size step must lie in (0, corner size max]")
        count = 1
        while count * self.corner_size_step_mm <= self.corner_size_max_mm + 1.0e-12:
            count += 1
        return np.asarray(np.arange(count) * self.corner_size_step_mm, dtype=np.float64)


DEFAULT_SETTINGS = FitSettings()
"""The settings every function takes unless told otherwise."""


class ScanGeometry(FrozenModel):
    """Nominal transverse geometry of the scanned gear from the generation (mm)."""

    role: ct.Role
    number_of_teeth: int
    base_diameter_mm: float
    tip_diameter_mm: float
    root_form_diameter_mm: float
    generated_root_diameter_mm: float
    base_tooth_thickness_nominal_mm: float
    """s_b of the nominal profile shift (no allowance)."""
    base_tooth_thickness_generated_mm: float
    """s_b of the generating profile shift (with the mean tooth thickness allowance)."""

    @property
    def r_b(self) -> float:
        return 0.5 * self.base_diameter_mm

    @property
    def r_a(self) -> float:
        return 0.5 * self.tip_diameter_mm

    @property
    def r_ff(self) -> float:
        return 0.5 * self.root_form_diameter_mm

    @property
    def pitch_angle_rad(self) -> float:
        return 2.0 * math.pi / self.number_of_teeth


def nominal_base_tooth_thickness(
    z: int, m_n_mm: float, alpha_n_rad: float, beta_rad: float, x: float
) -> float:
    """s_b = d_b (π/(2z) + 2 x tan α_n / z + inv α_t): the base tooth thickness of a profile
    shift x (``involute.base_tooth_thickness_half_angle``)."""
    alpha_t = iv.transverse_pressure_angle(alpha_n_rad, beta_rad)
    psi = math.pi / (2.0 * z) + 2.0 * x * math.tan(alpha_n_rad) / z
    return iv.base_diameter(z, m_n_mm, alpha_n_rad, beta_rad) * iv.base_tooth_thickness_half_angle(
        psi, alpha_t
    )


def scan_geometry(generation: GenerationResult, role: ct.Role) -> ScanGeometry:
    """The nominal geometry a scan of ``role`` is evaluated against."""
    if role not in ("pinion", "wheel"):
        raise InputRangeError(f"role must be 'pinion' or 'wheel', got {role!r}")
    pair = generation.inputs
    gear = generation.gears.pinion if role == "pinion" else generation.gears.wheel
    beta = math.radians(pair.helix_angle_deg)
    alpha_n = math.radians(pair.normal_pressure_angle_deg)
    z = gear.number_of_teeth
    return ScanGeometry(
        role=role,
        number_of_teeth=z,
        base_diameter_mm=iv.base_diameter(z, pair.normal_module_mm, alpha_n, beta),
        tip_diameter_mm=gear.tip_diameter_mm,
        root_form_diameter_mm=gear.root_form_diameter_mm,
        generated_root_diameter_mm=gear.generated_root_diameter_mm,
        base_tooth_thickness_nominal_mm=nominal_base_tooth_thickness(
            z, pair.normal_module_mm, alpha_n, beta, gear.profile_shift_coefficient
        ),
        base_tooth_thickness_generated_mm=nominal_base_tooth_thickness(
            z, pair.normal_module_mm, alpha_n, beta, gear.generating_profile_shift_coefficient
        ),
    )


# ---- segmentation --------------------------------------------------------------------------


class Run(FrozenModel):
    """Consecutive scan points of one kind: ``start`` to ``stop`` inclusive."""

    kind: RunKind
    start: int
    stop: int

    @property
    def count(self) -> int:
        return self.stop - self.start + 1


def _runs_of(labels: Sequence[str]) -> tuple[Run, ...]:
    out: list[Run] = []
    start = 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[start]:
            kind = labels[start]
            if kind not in ("tip", "flank", "root"):
                raise InputRangeError(f"unknown run kind {kind!r}")
            out.append(Run(kind=kind, start=start, stop=i - 1))
            start = i
    return tuple(out)


def _points(scan: ContourScan | Array) -> Array:
    points = scan.as_array() if isinstance(scan, ContourScan) else np.asarray(scan, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 10:
        raise InputRangeError("a scan is an (N, 2) array of x, y in mm with at least 10 points")
    if not np.all(np.isfinite(points)):
        raise InputRangeError("the scan contains non-finite coordinates")
    return points


def segment(scan: ContourScan | Array, settings: FitSettings = DEFAULT_SETTINGS) -> tuple[Run, ...]:
    """Tip lands, roots and flanks by the radius about the origin of the scan; the tip and root
    bands are taken per land, so an eccentric mounting (different tip radius per tooth) does not
    mislabel the corners."""
    points = _points(scan)
    r = np.hypot(points[:, 0], points[:, 1])
    coarse = np.where(r > r.max() - 0.3, "tip", np.where(r < r.min() + 0.3, "root", "flank"))
    labels = ["flank"] * len(r)
    for run in _runs_of([str(c) for c in coarse]):
        if run.kind == "tip":
            local = float(r[run.start : run.stop + 1].max())
            for i in range(run.start, run.stop + 1):
                if r[i] > local - settings.tip_band_mm:
                    labels[i] = "tip"
        elif run.kind == "root":
            local = float(r[run.start : run.stop + 1].min())
            for i in range(run.start, run.stop + 1):
                if r[i] < local + settings.root_band_mm:
                    labels[i] = "root"
    return _runs_of(labels)


# ---- axis, involutes, tip circles ------------------------------------------------------------


class AxisFit(FrozenModel):
    """The axis of one scan with the involute of every usable flank and the radius of every
    tip land."""

    centre_mm: tuple[float, float]
    """Axis position in scan coordinates."""
    flank_runs: tuple[Run, ...]
    flank_theta0_rad: tuple[float, ...]
    """Involute angle of every flank (the polar angle, from +y towards +x, where the involute
    leaves the base circle)."""
    flank_hand: tuple[int, ...]
    """+1: the polar angle grows with the radius (left flank, −x side); −1: it falls (right)."""
    flank_tip: tuple[int, ...]
    """Index of the tip land next to every flank (−1 without tip lands)."""
    tip_runs: tuple[Run, ...]
    tip_radius_mm: tuple[float, ...]
    rms_flank_um: float
    rms_tip_um: float
    flank_points_used: int
    fit_r_low_mm: float
    fit_r_high_mm: tuple[float, ...]

    @property
    def centre(self) -> Array:
        return np.asarray(self.centre_mm, dtype=float)


def flank_normal_deviation(xy: Array, centre: Array, r_b: float, theta0: float, hand: int) -> Array:
    """Deviation of points from the involute (r_b, theta0, hand) along its normal: a rotation
    by dθ shifts an involute by r_b dθ along its normal everywhere."""
    d = xy - centre
    r = np.hypot(d[:, 0], d[:, 1])
    theta = np.arctan2(d[:, 0], d[:, 1])
    alpha = np.arccos(np.clip(r_b / r, -1.0, 1.0))
    return np.asarray(r_b * (theta - (theta0 + hand * (np.tan(alpha) - alpha))), dtype=float)


def fit_axis(
    scan: ContourScan | Array,
    runs: Sequence[Run],
    geometry: ScanGeometry,
    settings: FitSettings = DEFAULT_SETTINGS,
    centre0: tuple[float, float] | None = None,
) -> AxisFit:
    """Axis, one involute angle per flank and one radius per tip land. With ``centre0`` (a
    previous solution) the point selection is made about that axis instead of the origin of
    the scan; ``fit_scan`` runs two passes so an eccentric mounting does not move the limits."""
    xy = _points(scan)
    c0 = np.zeros(2) if centre0 is None else np.asarray(centre0, dtype=float)
    d0 = xy - c0
    r0 = np.hypot(d0[:, 0], d0[:, 1])
    phi0 = np.arctan2(d0[:, 0], d0[:, 1])
    tip_runs = [run for run in runs if run.kind == "tip"]
    flank_runs = [run for run in runs if run.kind == "flank"]
    tip_centre_idx = np.array([(t.start + t.stop) / 2.0 for t in tip_runs])
    tip_local_r = np.array([r0[t.start : t.stop + 1].max() for t in tip_runs])

    selections: list[NDArray[np.intp]] = []
    hands: list[int] = []
    kept_runs: list[Run] = []
    kept_tip: list[int] = []
    highs: list[float] = []
    low = geometry.r_ff + settings.flank_margin_above_root_form_mm
    for run in flank_runs:
        idx = np.arange(run.start, run.stop + 1)
        gaps = np.abs(tip_centre_idx - idx.mean())
        nearest = int(np.argmin(gaps)) if len(tip_runs) else -1
        r_tip = float(tip_local_r[nearest]) if nearest >= 0 else geometry.r_a
        high = r_tip - settings.flank_margin_below_tip_mm
        sel = idx[(r0[idx] > low) & (r0[idx] < high)]
        if len(sel) < 20:
            continue
        slope = np.polyfit(r0[sel], phi0[sel], 1)[0]
        hands.append(1 if slope > 0 else -1)
        selections.append(sel)
        kept_runs.append(run)
        kept_tip.append(nearest)
        highs.append(high)
    if not selections:
        raise InputRangeError("no flank long enough for the involute fit")
    tip_sel = [np.arange(t.start, t.stop + 1) for t in tip_runs]

    def unpack(p: Array) -> tuple[Array, Array, Array]:
        return p[:2], p[2 : 2 + len(selections)], p[2 + len(selections) :]

    def residual(p: Array) -> Array:
        centre, theta0, r_a = unpack(p)
        parts = [
            flank_normal_deviation(xy[sel], centre, geometry.r_b, float(th), hand)
            for sel, th, hand in zip(selections, theta0, hands, strict=True)
        ]
        for sel, ra in zip(tip_sel, r_a, strict=True):
            d = xy[sel] - centre
            parts.append(np.hypot(d[:, 0], d[:, 1]) - ra)
        return np.concatenate(parts)

    p0 = [float(c0[0]), float(c0[1])]
    for sel, hand in zip(selections, hands, strict=True):
        alpha = math.acos(min(1.0, geometry.r_b / float(r0[sel[0]])))
        p0.append(float(phi0[sel[0]]) - hand * (math.tan(alpha) - alpha))
    p0.extend(float(v) for v in tip_local_r)
    sol = least_squares(residual, np.asarray(p0), loss="soft_l1", f_scale=0.004, x_scale="jac")
    centre, theta0, r_a = unpack(sol.x)
    res = residual(sol.x)
    n_flank = sum(len(s) for s in selections)
    rms_tip = float(np.sqrt(np.mean(res[n_flank:] ** 2))) if len(res) > n_flank else 0.0
    return AxisFit(
        centre_mm=(float(centre[0]), float(centre[1])),
        flank_runs=tuple(kept_runs),
        flank_theta0_rad=tuple(float(v) for v in theta0),
        flank_hand=tuple(hands),
        flank_tip=tuple(kept_tip),
        tip_runs=tuple(tip_runs),
        tip_radius_mm=tuple(float(v) for v in r_a),
        rms_flank_um=1000.0 * float(np.sqrt(np.mean(res[:n_flank] ** 2))),
        rms_tip_um=1000.0 * rms_tip,
        flank_points_used=n_flank,
        fit_r_low_mm=low,
        fit_r_high_mm=tuple(highs),
    )


def fit_scan(
    scan: ContourScan | Array, geometry: ScanGeometry, settings: FitSettings = DEFAULT_SETTINGS
) -> tuple[tuple[Run, ...], AxisFit]:
    """Segmentation and axis fit in two passes (the second selects the points about the axis
    of the first)."""
    runs = segment(scan, settings)
    first = fit_axis(scan, runs, geometry, settings)
    return runs, fit_axis(scan, runs, geometry, settings, centre0=first.centre_mm)


# ---- tip relief, thickness, pitch --------------------------------------------------------------


class FlankRelief(FrozenModel):
    """Tip relief of one flank: where the deviation from the involute (fitted below the relief)
    leaves the band for good, how large it is just below the tip land, and the straight line
    through the relief points over the roll length (linear relief: amount C_a at the tip, start
    at the diameter d_Ca)."""

    run: Run
    hand: int
    rms_fit_um: float | None
    """RMS of the flank points in the fit range about the fitted involute (None without points)."""
    relief_start_r_mm: float
    relief_at_tip_um: float | None
    ramp_start_r_mm: float | None
    """Zero crossing of the straight line (r_Ca = d_Ca / 2); None without a usable ramp (fewer
    than five relief points, a flat line, or a crossing below the base circle)."""
    ramp_at_tip_um: float | None
    """The line at the fitted tip land radius."""
    ramp_at_nominal_tip_um: float | None
    """The line at the nominal tip radius r_a."""
    ramp_slope_um_per_mm: float | None
    """Of the line, per mm of roll length."""
    ramp_rms_um: float | None


def flank_reliefs(
    scan: ContourScan | Array,
    fit: AxisFit,
    geometry: ScanGeometry,
    settings: FitSettings = DEFAULT_SETTINGS,
) -> tuple[FlankRelief, ...]:
    """Tip relief of every fitted flank; material removed counts positive on both hands."""
    xy = _points(scan)
    centre = fit.centre
    out: list[FlankRelief] = []
    for run, th, hand, k_tip, high in zip(
        fit.flank_runs,
        fit.flank_theta0_rad,
        fit.flank_hand,
        fit.flank_tip,
        fit.fit_r_high_mm,
        strict=True,
    ):
        r_tip = fit.tip_radius_mm[k_tip] if k_tip >= 0 else geometry.r_a
        idx = np.arange(run.start, run.stop + 1)
        d = xy[idx] - centre
        r = np.hypot(d[:, 0], d[:, 1])
        ok = (r > fit.fit_r_low_mm) & (r < r_tip - settings.tip_band_mm)
        r = r[ok]
        # the normal deviation is positive towards +θ; the material of a right flank (hand −1)
        # lies at smaller θ, of a left flank at larger θ: hand · deviation = material removed
        dev = hand * flank_normal_deviation(xy[idx][ok], centre, geometry.r_b, th, hand)
        order = np.argsort(r)
        r, dev = r[order], dev[order]
        in_fit = r < high
        rms = 1000.0 * float(np.sqrt(np.mean(dev[in_fit] ** 2))) if in_fit.any() else None
        within = np.flatnonzero(1000.0 * dev <= settings.relief_threshold_um)
        start = float(r[within[-1]]) if len(within) else float(r[0])
        near_tip = r > r_tip - settings.tip_band_mm - settings.relief_sample_mm
        at_tip = 1000.0 * float(dev[near_tip].mean()) if near_tip.any() else None
        ramp = (r > start + settings.relief_sample_mm) & (r < r_tip - settings.tip_band_mm)
        slope: float | None = None
        ramp_start: float | None = None
        ramp_tip: float | None = None
        ramp_nominal: float | None = None
        ramp_rms: float | None = None
        if ramp.sum() >= 5:
            roll = np.sqrt(r[ramp] ** 2 - geometry.r_b**2)
            slope, intercept = (float(v) for v in np.polyfit(roll, 1000.0 * dev[ramp], 1))
            if slope != 0.0:
                roll_start = -intercept / slope
                if roll_start > 0.0:
                    ramp_start = math.sqrt(geometry.r_b**2 + roll_start**2)
            ramp_tip = slope * math.sqrt(r_tip**2 - geometry.r_b**2) + intercept
            ramp_nominal = slope * math.sqrt(geometry.r_a**2 - geometry.r_b**2) + intercept
            ramp_rms = float(
                np.sqrt(np.mean((1000.0 * dev[ramp] - (slope * roll + intercept)) ** 2))
            )
        out.append(
            FlankRelief(
                run=run,
                hand=hand,
                rms_fit_um=rms,
                relief_start_r_mm=start,
                relief_at_tip_um=at_tip,
                ramp_start_r_mm=ramp_start,
                ramp_at_tip_um=ramp_tip,
                ramp_at_nominal_tip_um=ramp_nominal,
                ramp_slope_um_per_mm=slope,
                ramp_rms_um=ramp_rms,
            )
        )
    return tuple(out)


class ToothThickness(FrozenModel):
    """Base tooth thickness of one tooth with both flanks fitted."""

    tooth: int
    """0-based within the scan, in scan order (+x to −x)."""
    right_flank: int
    """Index of the right flank in ``AxisFit.flank_runs``; the left flank is the next one."""
    s_b_mm: float
    theta_centre_rad: float
    """Polar angle of the tooth centre line (mean of the two involute angles)."""


def tooth_thicknesses(fit: AxisFit, geometry: ScanGeometry) -> tuple[ToothThickness, ...]:
    """s_b = r_b (θ0 right − θ0 left) of every right flank followed by a left flank."""
    out: list[ToothThickness] = []
    n = 0
    for k in range(len(fit.flank_runs) - 1):
        if fit.flank_hand[k] == -1 and fit.flank_hand[k + 1] == 1:
            th_right, th_left = fit.flank_theta0_rad[k], fit.flank_theta0_rad[k + 1]
            out.append(
                ToothThickness(
                    tooth=n,
                    right_flank=k,
                    s_b_mm=geometry.r_b * (th_right - th_left),
                    theta_centre_rad=0.5 * (th_right + th_left),
                )
            )
            n += 1
    return tuple(out)


class AngularPitch(FrozenModel):
    """Angular pitch from two consecutive flanks of the same hand (a check of the fitted axis:
    an axis error e shows as about e / r in the pitch)."""

    first_flank: int
    second_flank: int
    hand: int
    pitch_deg: float


def angular_pitches(fit: AxisFit) -> tuple[AngularPitch, ...]:
    out: list[AngularPitch] = []
    for k in range(len(fit.flank_runs) - 2):
        if fit.flank_hand[k] == fit.flank_hand[k + 2]:
            pitch = math.degrees(fit.flank_theta0_rad[k] - fit.flank_theta0_rad[k + 2])
            out.append(
                AngularPitch(
                    first_flank=k, second_flank=k + 2, hand=fit.flank_hand[k], pitch_deg=pitch
                )
            )
    return tuple(out)


# ---- tip corners -------------------------------------------------------------------------------


@dataclass(frozen=True)
class CornerModel:
    """A tip corner: the sharp corner, the unit directions away from it along the flank (``a``)
    and along the tip land (``b``), and the size of the break: the radius of a tangent arc or
    the length of a symmetric chamfer along both legs (``shape``)."""

    corner: Array
    a: Array
    b: Array
    size: float
    shape: Shape = "arc"

    @property
    def interior_angle(self) -> float:
        return math.acos(max(-1.0, min(1.0, float(self.a @ self.b))))

    @property
    def tangent_length(self) -> float:
        """Distance from the sharp corner to where the break meets each leg."""
        if self.shape == "chamfer":
            return self.size
        return self.size / math.tan(0.5 * self.interior_angle)

    @property
    def centre(self) -> Array:
        bis = self.a + self.b
        bis = bis / float(np.hypot(*bis))
        return np.asarray(self.corner + bis * self.size / math.sin(0.5 * self.interior_angle))

    @property
    def cut_back(self) -> float:
        """Distance from the sharp corner to the break along the bisector."""
        if self.size <= 0.0:
            return 0.0
        if self.shape == "chamfer":
            return self.size * math.cos(0.5 * self.interior_angle)
        return self.size / math.sin(0.5 * self.interior_angle) - self.size

    def outline(self, leg: float, arc_points: int = 40) -> Array:
        """The broken corner as a polyline: ``leg`` along the flank, the break (``arc_points``
        points on the arc or on the chamfer), ``leg`` along the tip land."""
        t = self.tangent_length
        t_a = self.corner + self.a * t
        t_b = self.corner + self.b * t
        if self.size <= 0.0:
            return np.vstack((self.corner + self.a * leg, self.corner, self.corner + self.b * leg))
        if self.shape == "chamfer":
            along = np.linspace(0.0, 1.0, arc_points)[:, None]
            chamfer = t_a + along * (t_b - t_a)
            return np.vstack((self.corner + self.a * leg, chamfer, self.corner + self.b * leg))
        cen = self.centre
        a1 = math.atan2(*(t_a - cen)[::-1])
        a2 = math.atan2(*(t_b - cen)[::-1])
        sweep = math.remainder(a2 - a1, 2.0 * math.pi)
        ang = a1 + sweep * np.linspace(0.0, 1.0, arc_points)
        arc = cen + self.size * np.column_stack((np.cos(ang), np.sin(ang)))
        return np.vstack((self.corner + self.a * leg, t_a, arc, t_b, self.corner + self.b * leg))

    def distance(self, xy: Array) -> Array:
        """Unsigned distance of points to the broken corner (ray, break, ray)."""
        t = self.tangent_length
        t_a = self.corner + self.a * t
        t_b = self.corner + self.b * t
        out = np.full(len(xy), np.inf)
        for origin, direction in ((t_a, self.a), (t_b, self.b)):
            d = xy - origin
            s = d @ direction
            perp = np.abs(d[:, 0] * direction[1] - d[:, 1] * direction[0])
            dist = np.where(s >= 0.0, perp, np.hypot(d[:, 0], d[:, 1]))
            out = np.minimum(out, dist)
        if self.size <= 0.0:
            return np.asarray(np.minimum(out, np.hypot(*(xy - self.corner).T)), dtype=float)
        if self.shape == "chamfer":
            seg = t_b - t_a
            length2 = float(seg @ seg)
            u = (
                np.clip(((xy - t_a) @ seg) / length2, 0.0, 1.0)
                if length2 > 0.0
                else np.zeros(len(xy))
            )
            closest = t_a + u[:, None] * seg
            return np.asarray(np.minimum(out, np.hypot(*(xy - closest).T)), dtype=float)
        m = self.centre
        d = xy - m
        u_vec = t_a - m
        v_vec = t_b - m
        ang_u = math.atan2(u_vec[1], u_vec[0])
        sweep = math.remainder(math.atan2(v_vec[1], v_vec[0]) - ang_u, 2.0 * math.pi)
        ang = np.arctan2(d[:, 1], d[:, 0])
        rel = (ang - ang_u + math.pi) % (2.0 * math.pi) - math.pi
        inside = (rel * np.sign(sweep) >= 0.0) & (np.abs(rel) <= abs(sweep))
        arc_dist = np.abs(np.hypot(d[:, 0], d[:, 1]) - self.size)
        return np.asarray(np.where(inside, np.minimum(out, arc_dist), out), dtype=float)


class CornerFit(FrozenModel):
    """One tip corner of a scan with the best tangent arc and the best symmetric chamfer."""

    tip_index: int
    """Tip land number within the scan (0-based)."""
    side: Side
    """``right``: the +x side of the tooth (scanned first); ``left``."""
    tip_radius_mm: float
    corner_radius_mm: float
    """Radius of the sharp corner from the axis."""
    interior_angle_deg: float
    points_in_window: int
    corner_mm: tuple[float, float]
    flank_direction: tuple[float, float]
    tip_direction: tuple[float, float]
    arc_radius_mm: float
    arc_radius_low_mm: float
    """Radii whose RMS lies within 10 % of the minimum."""
    arc_radius_high_mm: float
    arc_rms_um: float
    chamfer_length_mm: float
    chamfer_length_low_mm: float
    chamfer_length_high_mm: float
    chamfer_rms_um: float
    sharp_rms_um: float
    tangent_flank_mm: float
    """Distance from the sharp corner at which the points leave the flank line."""
    tangent_tip_mm: float
    cut_back_um: float
    """Of the better of arc and chamfer."""
    better_shape: Shape
    arc_rms_curve: tuple[tuple[float, float], ...]
    """(radius in mm, RMS in µm) over the size grid."""
    chamfer_rms_curve: tuple[tuple[float, float], ...]
    window_points_mm: tuple[tuple[float, float], ...]

    def model(self, shape: Shape | None = None, size: float | None = None) -> CornerModel:
        """The fitted corner as a ``CornerModel`` (the better shape unless given)."""
        kind = self.better_shape if shape is None else shape
        if size is None:
            size = self.arc_radius_mm if kind == "arc" else self.chamfer_length_mm
        return CornerModel(
            corner=np.asarray(self.corner_mm, dtype=float),
            a=np.asarray(self.flank_direction, dtype=float),
            b=np.asarray(self.tip_direction, dtype=float),
            size=size,
            shape=kind,
        )


def _arc_length(xy: Array) -> Array:
    step = np.hypot(*(xy[1:] - xy[:-1]).T)
    return np.concatenate(([0.0], np.cumsum(step)))


def _line_fit(xy: Array) -> tuple[Array, Array]:
    """Point and unit direction of the total-least-squares line through the points."""
    c = xy.mean(axis=0)
    _, _, vt = np.linalg.svd(xy - c, full_matrices=False)
    return np.asarray(c), np.asarray(vt[0])


def _intersect(p1: Array, d1: Array, p2: Array, d2: Array) -> Array:
    a = np.column_stack((d1, -d2))
    s = np.linalg.solve(a, p2 - p1)
    return np.asarray(p1 + s[0] * d1, dtype=np.float64)


def _fit_corner(
    xy: Array, start: CornerModel, size: float, shape: Shape
) -> tuple[CornerModel, float]:
    ang_a = math.atan2(start.a[1], start.a[0])
    ang_b = math.atan2(start.b[1], start.b[0])
    p0 = np.array([start.corner[0], start.corner[1], ang_a, ang_b])

    def build(p: Array) -> CornerModel:
        return CornerModel(
            corner=p[:2],
            a=np.array([math.cos(p[2]), math.sin(p[2])]),
            b=np.array([math.cos(p[3]), math.sin(p[3])]),
            size=size,
            shape=shape,
        )

    sol = least_squares(lambda p: build(p).distance(xy), p0, x_scale=[0.01, 0.01, 0.01, 0.01])
    model = build(sol.x)
    rms = float(np.sqrt(np.mean(model.distance(xy) ** 2)))
    return model, rms


def _leave_length(xy: Array, origin: Array, direction: Array, threshold: float) -> float:
    """Distance from the corner along ``direction`` to the first point (coming from far away)
    whose distance from the straight line exceeds the threshold."""
    d = xy - origin
    s = d @ direction
    perp = np.abs(d[:, 0] * direction[1] - d[:, 1] * direction[0])
    order = np.argsort(-s)
    for k in order:
        if perp[k] > threshold:
            return max(0.0, float(s[k]))
    return 0.0


def _best_on_grid(
    pts: Array, start: CornerModel, sizes: Array, shape: Shape
) -> tuple[float, float, float, float, list[tuple[float, float]], float]:
    """Best size of a shape over the grid, refined once: (size, low, high, rms, curve, sharp rms)."""
    curve: list[tuple[float, float]] = []
    best: tuple[float, float] | None = None
    sharp_rms = math.nan
    for size in sizes:
        _, rms = _fit_corner(pts, start, float(size), shape)
        curve.append((float(size), 1000.0 * rms))
        if size == 0.0:
            sharp_rms = rms
        if best is None or rms < best[1]:
            best = (float(size), rms)
    if best is None:
        raise InputRangeError("the size grid is empty")
    step = float(sizes[1] - sizes[0]) if len(sizes) > 1 else 0.0
    for size in np.linspace(max(0.0, best[0] - step), best[0] + step, 11):
        _, rms = _fit_corner(pts, start, float(size), shape)
        if rms < best[1]:
            best = (float(size), rms)
    within = [s for s, v in curve if v <= 1.10 * 1000.0 * best[1]]
    low = min(within) if within else best[0]
    high = max(within) if within else best[0]
    return best[0], low, high, best[1], curve, sharp_rms


class ShapeFit(FrozenModel):
    """The best size of one break shape through the points of a corner window."""

    shape: Shape
    size_mm: float
    size_low_mm: float
    """Sizes whose RMS lies within 10 % of the minimum."""
    size_high_mm: float
    rms_um: float
    rms_curve: tuple[tuple[float, float], ...]
    """(size in mm, RMS in µm) over the size grid."""


def fit_corner_shapes(
    points: Array, start: CornerModel, settings: FitSettings = DEFAULT_SETTINGS
) -> tuple[ShapeFit, ShapeFit]:
    """The best tangent arc and the best symmetric chamfer through the points about the sharp
    corner ``start`` (the corner and the leg directions are refined with every size)."""
    sizes = settings.sizes()
    shapes: tuple[Shape, Shape] = ("arc", "chamfer")
    fits: list[ShapeFit] = []
    for shape in shapes:
        size, low, high, rms, curve, _ = _best_on_grid(points, start, sizes, shape)
        fits.append(
            ShapeFit(
                shape=shape,
                size_mm=size,
                size_low_mm=low,
                size_high_mm=high,
                rms_um=1000.0 * rms,
                rms_curve=tuple(curve),
            )
        )
    return fits[0], fits[1]


def measure_corner(
    scan: ContourScan | Array,
    fit: AxisFit,
    tip_index: int,
    side: Side,
    settings: FitSettings = DEFAULT_SETTINGS,
) -> CornerFit | None:
    """The corner at the start (right side, scanned first) or the end (left side) of a tip land
    with the best arc and the best chamfer; ``None`` where the window lacks contour on one side."""
    xy = _points(scan)
    if not 0 <= tip_index < len(fit.tip_runs):
        raise InputRangeError(f"tip index {tip_index} outside 0 to {len(fit.tip_runs) - 1}")
    at_start = side == "right"
    tip = fit.tip_runs[tip_index]
    arc = _arc_length(xy)
    k0 = tip.start if at_start else tip.stop
    window = np.flatnonzero(np.abs(arc - arc[k0]) <= settings.corner_window_mm)
    flank_side = window[window < k0] if at_start else window[window > k0]
    tip_side = window[window >= k0] if at_start else window[window <= k0]
    if len(flank_side) < 8 or len(tip_side) < 8:
        return None
    if (
        abs(arc[flank_side[0 if at_start else -1]] - arc[k0]) < 0.25
        or abs(arc[tip_side[-1 if at_start else 0]] - arc[k0]) < 0.25
    ):
        return None
    far_flank = flank_side[np.abs(arc[flank_side] - arc[k0]) > settings.corner_exclude_mm]
    far_tip = tip_side[np.abs(arc[tip_side] - arc[k0]) > settings.corner_exclude_mm]
    p_f, d_f = _line_fit(xy[far_flank])
    p_t, d_t = _line_fit(xy[far_tip])
    corner = _intersect(p_f, d_f, p_t, d_t)
    a = d_f if (xy[far_flank].mean(axis=0) - corner) @ d_f > 0 else -d_f
    b = d_t if (xy[far_tip].mean(axis=0) - corner) @ d_t > 0 else -d_t
    start = CornerModel(corner=corner, a=a, b=b, size=0.0)
    pts = xy[window]
    arc_fit, chamfer_fit = fit_corner_shapes(pts, start, settings)
    better: Shape = "arc" if arc_fit.rms_um <= chamfer_fit.rms_um else "chamfer"
    size = arc_fit.size_mm if better == "arc" else chamfer_fit.size_mm
    model, _ = _fit_corner(pts, start, size, better)
    sharp_model, sharp_rms = _fit_corner(pts, start, 0.0, "arc")
    t_flank = _leave_length(
        xy[flank_side], sharp_model.corner, sharp_model.a, settings.leave_threshold_mm
    )
    t_tip = _leave_length(
        xy[tip_side], sharp_model.corner, sharp_model.b, settings.leave_threshold_mm
    )
    d = model.corner - fit.centre
    return CornerFit(
        tip_index=tip_index,
        side=side,
        tip_radius_mm=fit.tip_radius_mm[tip_index],
        corner_radius_mm=float(np.hypot(*d)),
        interior_angle_deg=math.degrees(model.interior_angle),
        points_in_window=len(window),
        corner_mm=(float(model.corner[0]), float(model.corner[1])),
        flank_direction=(float(model.a[0]), float(model.a[1])),
        tip_direction=(float(model.b[0]), float(model.b[1])),
        arc_radius_mm=arc_fit.size_mm,
        arc_radius_low_mm=arc_fit.size_low_mm,
        arc_radius_high_mm=arc_fit.size_high_mm,
        arc_rms_um=arc_fit.rms_um,
        chamfer_length_mm=chamfer_fit.size_mm,
        chamfer_length_low_mm=chamfer_fit.size_low_mm,
        chamfer_length_high_mm=chamfer_fit.size_high_mm,
        chamfer_rms_um=chamfer_fit.rms_um,
        sharp_rms_um=1000.0 * sharp_rms,
        tangent_flank_mm=t_flank,
        tangent_tip_mm=t_tip,
        cut_back_um=1000.0 * model.cut_back,
        better_shape=better,
        arc_rms_curve=arc_fit.rms_curve,
        chamfer_rms_curve=chamfer_fit.rms_curve,
        window_points_mm=tuple((float(p[0]), float(p[1])) for p in pts),
    )


def corner_frame(points: Array, model: CornerModel) -> Array:
    """Points in the frame of a corner: origin at the sharp corner, the first coordinate across
    the bisector (towards the tip land), the second along the bisector into the tooth
    (negative outside); for the corner pictures at 1:1."""
    bis = model.a + model.b
    bis = -bis / float(np.hypot(*bis))
    perp = np.array([-bis[1], bis[0]])
    if perp @ model.b < 0:
        perp = -perp
    d = points - model.corner
    return np.asarray(np.column_stack((d @ perp, d @ bis)), dtype=float)


# ---- the whole scan ----------------------------------------------------------------------------


class ScanEvaluation(FrozenModel):
    name: str
    block: str
    z_mm: float
    points: int
    coarse: bool
    geometry: ScanGeometry
    settings: FitSettings
    runs: tuple[Run, ...]
    fit: AxisFit
    reliefs: tuple[FlankRelief, ...]
    teeth: tuple[ToothThickness, ...]
    pitches: tuple[AngularPitch, ...]
    corners: tuple[CornerFit, ...]


def evaluate_scan(
    scan: ContourScan,
    geometry: ScanGeometry,
    settings: FitSettings = DEFAULT_SETTINGS,
    *,
    corners: bool = True,
) -> ScanEvaluation:
    """Everything the module measures on one scan."""
    runs, fit = fit_scan(scan, geometry, settings)
    found: list[CornerFit] = []
    if corners:
        for k in range(len(fit.tip_runs)):
            for side in ("right", "left"):
                result = measure_corner(scan, fit, k, side, settings)
                if result is not None:
                    found.append(result)
    points = scan.as_array()
    return ScanEvaluation(
        name=scan.name,
        block=scan.block,
        z_mm=scan.z_mm,
        points=len(points),
        coarse=len(points) < settings.coarse_points,
        geometry=geometry,
        settings=settings,
        runs=runs,
        fit=fit,
        reliefs=flank_reliefs(points, fit, geometry, settings),
        teeth=tooth_thicknesses(fit, geometry),
        pitches=angular_pitches(fit),
        corners=tuple(found),
    )


# ---- tooth frames and overlays -----------------------------------------------------------------


class ToothFrame(FrozenModel):
    """One measured tooth in the frame of the nominal tooth: axis at the origin, the tooth
    centre line on +y, x to the right (the right flank of the scan on +x)."""

    tooth: int
    theta_centre_rad: float
    first_index: int
    last_index: int
    points_mm: tuple[tuple[float, float], ...]

    def as_array(self) -> Array:
        return np.asarray(self.points_mm, dtype=float)


def _midpoint(first: int, last: int) -> int:
    """The index halfway between two indices (integer arithmetic)."""
    return first + ((last - first) >> 1)


def tooth_points(
    scan: ContourScan | Array, fit: AxisFit, theta_centre_rad: float, first: int, last: int
) -> Array:
    """Scan points ``first`` to ``last`` (inclusive) rotated so that ``theta_centre_rad`` (polar
    angle from +y towards +x about the fitted axis) lies on +y."""
    xy = _points(scan)
    if not 0 <= first <= last < len(xy):
        raise InputRangeError(f"index range {first} to {last} outside the scan")
    d = xy[first : last + 1] - fit.centre
    c, s = math.cos(theta_centre_rad), math.sin(theta_centre_rad)
    # the polar angle is measured from +y towards +x: rotating by −θ about the axis maps the
    # direction (sin θ, cos θ) onto (0, 1)
    x = c * d[:, 0] - s * d[:, 1]
    y = s * d[:, 0] + c * d[:, 1]
    return np.asarray(np.column_stack((x, y)), dtype=float)


def tooth_frames(scan: ContourScan | Array, evaluation: ScanEvaluation) -> tuple[ToothFrame, ...]:
    """Every tooth of the scan with both flanks fitted, from the middle of the root before it
    to the middle of the root after it, in the frame of the nominal tooth."""
    runs = evaluation.runs
    fit = evaluation.fit
    out: list[ToothFrame] = []
    for tooth in evaluation.teeth:
        right = fit.flank_runs[tooth.right_flank]
        left = fit.flank_runs[tooth.right_flank + 1]
        before = [r for r in runs if r.kind == "root" and r.stop < right.start]
        after = [r for r in runs if r.kind == "root" and r.start > left.stop]
        first = _midpoint(before[-1].start, before[-1].stop) if before else right.start
        last = _midpoint(after[0].start, after[0].stop) if after else left.stop
        points = tooth_points(scan, fit, tooth.theta_centre_rad, first, last)
        out.append(
            ToothFrame(
                tooth=tooth.tooth,
                theta_centre_rad=tooth.theta_centre_rad,
                first_index=first,
                last_index=last,
                points_mm=tuple((float(p[0]), float(p[1])) for p in points),
            )
        )
    return tuple(out)


def nominal_outline(generation: GenerationResult, role: ct.Role, points: int = 400) -> Array:
    """The nominal tooth of the generation in the tooth frame, continued along the root circle
    to the centre of the gap on either side (an open polyline from the right gap centre over
    the tip to the left gap centre: the order of the scan)."""
    contour = ct.tooth_contour(generation, role, points=points)
    tooth = contour.as_array()[::-1]  # the contour runs left fillet → tip → right fillet
    r_f = 0.5 * contour.generated_root_diameter_mm
    half = math.pi / contour.number_of_teeth
    ang_first = math.atan2(tooth[0, 0], tooth[0, 1])
    ang_last = math.atan2(tooth[-1, 0], tooth[-1, 1])
    count = max(4, points >> 3)
    lead = np.linspace(half, ang_first, count, endpoint=False)
    trail = np.linspace(ang_last, -half, count + 1)[1:]
    before = r_f * np.column_stack((np.sin(lead), np.cos(lead)))
    after = r_f * np.column_stack((np.sin(trail), np.cos(trail)))
    return np.asarray(np.vstack((before, tooth, after)), dtype=float)


def closest_on_outline(points: Array, outline: Array) -> tuple[Array, Array]:
    """For every point the closest point of the polyline and the signed distance in mm:
    positive outside the nominal tooth (material beyond the nominal contour), negative inside
    (material missing, as worn or relieved)."""
    pts = np.asarray(points, dtype=float)
    a, b = outline[:-1], outline[1:]
    ab = b - a
    length2 = np.einsum("ij,ij->i", ab, ab)
    ap = pts[:, None, :] - a[None, :, :]
    t = np.einsum("pij,ij->pi", ap, ab) / np.where(length2 > 0.0, length2, 1.0)
    t = np.clip(t, 0.0, 1.0)
    closest = a[None, :, :] + t[:, :, None] * ab[None, :, :]
    gaps = np.linalg.norm(pts[:, None, :] - closest, axis=2)
    k = np.argmin(gaps, axis=1)
    nearest = closest[np.arange(len(pts)), k]
    # the outline runs counter-clockwise around the tooth (right gap → tip → left gap with the
    # tooth centre on +y): the material lies to the left of the direction of travel
    direction = ab[k]
    offset = pts - nearest
    cross = direction[:, 0] * offset[:, 1] - direction[:, 1] * offset[:, 0]
    sign = np.where(cross > 0.0, -1.0, 1.0)
    return np.asarray(nearest, dtype=float), np.asarray(
        sign * gaps[np.arange(len(pts)), k], dtype=float
    )


def signed_deviation(points: Array, outline: Array) -> Array:
    """Signed distance of every point from the nominal outline in µm (``closest_on_outline``)."""
    return 1000.0 * closest_on_outline(points, outline)[1]


def outward_normals(points: Array) -> Array:
    """Unit normals of a measured contour (ordered as the scan runs, counter-clockwise around
    the tooth) pointing away from the material: the right-hand perpendicular of the local
    tangent through the neighbouring points."""
    pts = np.asarray(points, dtype=float)
    if len(pts) < 3:
        raise InputRangeError("a contour needs at least 3 points for its normals")
    tangent = np.empty_like(pts)
    tangent[1:-1] = pts[2:] - pts[:-2]
    tangent[0] = pts[1] - pts[0]
    tangent[-1] = pts[-1] - pts[-2]
    length = np.hypot(tangent[:, 0], tangent[:, 1])
    tangent = tangent / np.where(length > 0.0, length, 1.0)[:, None]
    return np.asarray(np.column_stack((tangent[:, 1], -tangent[:, 0])), dtype=float)


def overlay_points(points: Array, outline: Array, magnify: float = 1.0) -> Array:
    """The measured contour with its deviation from the nominal outline magnified ``magnify``
    times: every point moves by (magnify − 1) times its signed distance along the outward
    normal of the measured contour, so the magnified curve stays smooth around the tip corners
    (the normal of the nominal outline jumps there; 1 = the measured contour itself)."""
    if not 1.0 <= magnify <= 1000.0:
        raise InputRangeError(f"magnify must lie in 1 to 1000, got {magnify!r}")
    pts = np.asarray(points, dtype=float)
    _, distance = closest_on_outline(pts, outline)
    normals = outward_normals(pts)
    return np.asarray(pts + (magnify - 1.0) * distance[:, None] * normals, dtype=float)


__all__ = [
    "EQ_EXEMPT",
    "AngularPitch",
    "AxisFit",
    "CornerFit",
    "CornerModel",
    "FitSettings",
    "FlankRelief",
    "Run",
    "ScanEvaluation",
    "ScanGeometry",
    "ShapeFit",
    "ToothFrame",
    "ToothThickness",
    "angular_pitches",
    "closest_on_outline",
    "corner_frame",
    "evaluate_scan",
    "fit_axis",
    "fit_corner_shapes",
    "fit_scan",
    "flank_normal_deviation",
    "flank_reliefs",
    "measure_corner",
    "nominal_base_tooth_thickness",
    "nominal_outline",
    "outward_normals",
    "overlay_points",
    "scan_geometry",
    "segment",
    "signed_deviation",
    "tooth_frames",
    "tooth_points",
    "tooth_thicknesses",
]
