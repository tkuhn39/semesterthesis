"""Drawings of the thesis that no analysis script makes (T5), in the house style: lines only
with distinct dash patterns, every value in the legend, no title inside the picture (user,
2026-10-17); every figure is written as SVG, as its vector PDF twin and as a 300 dpi PNG.

    uv run --all-extras python scripts/thesis_figures.py WHAT [--out DIR]

``WHAT``:

``fillets``       the root fillet variants of the kst-E wheel against the trochoid of the
                  generation (``80_output/fe/kst_e/fussrundung_konturen/konturen``)
``stirnschnitt``  the pair in the transverse section in the position C: the contours of the
                  generation, the circles of the geometry table, the line of action with the
                  points A to E (``stirnschnitt_kste``)
``zahnkontur``    one tooth of the wheel with the trochoid, the landmark circles, the 30°
                  tangent, the root chord s_Fn and the radius of curvature (``zahnkontur_kste``)
``radkoerper``    the meridional section of the wheel body after the drawing of the user
                  (``fe.body.body_section``; ``radkoerper_kste``)
``mesh``          the frozen pocket mesh of the wheel without the titles of the deck builder:
                  the sector, one tooth, the body section, the pair in the position C with
                  the rigid pinion surface (``netz_sektor``, ``netz_zahn``, ``netz_koerper``,
                  ``paarung_netz``)
``all``           everything above

The contours come from ``gearcore.contour`` and ``gearcore.fillet`` (the same functions that
built the FE meshes), the placement from ``gearcore.fe.placement``, the mesh from the same
builders as the deck folder ``frozen_mesh_20layers_bore33_pocket``. Everything but ``fillets``
goes to ``80_output/thesis/`` with a ``bildunterschriften.md``.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fe_fillet_comparison as ffc  # noqa: E402

from gearcore import contour as ct  # noqa: E402
from gearcore import fillet as fl  # noqa: E402
from gearcore import pair as pr  # noqa: E402
from gearcore.errors import InputRangeError  # noqa: E402
from gearcore.fe import body as bd  # noqa: E402
from gearcore.fe import placement as pl  # noqa: E402
from gearcore.fe import refine as rf  # noqa: E402
from gearcore.fe import resample as rs  # noqa: E402
from gearcore.fe import rigid_surface as rsf  # noqa: E402
from gearcore.fe import sector_mesh as sm  # noqa: E402
from gearcore.models.results import GenerationResult  # noqa: E402
from gearcore.parity import compute_generation_from_data, generation_data  # noqa: E402
from gearcore.plot_style import (  # noqa: E402
    LineStyle,
    apply,
    decimal_comma,
    legend_outside,
    new_figure,
)
from gearcore.plot_style import save as save_figure  # noqa: E402

SHEET = apply()  # house style of every figure (FZG first, then TUM)

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "80_output" / "thesis"
FILLETS_OUT = REPO / "80_output" / "fe" / "kst_e" / "fussrundung_konturen"
CASE = "kst_e"
ROTATION: pl.Rotation = "clockwise"
"""Sense of rotation of the driving pinion on the test rig (deck manifests: pinion clockwise)."""

PINION_COLOUR = SHEET.colour("tum_blau_dunkel")
WHEEL_COLOUR = SHEET.colour("tum_orange")
BLACK = SHEET.colour("tum_schwarz")
GREY = SHEET.colour("tum_grau_50")
QUAD_EDGE = SHEET.colour("tum_grau_80")
MARK_COLOUR = SHEET.colour("diag5")  # the drawing and the Fesselung, as in the deck builder

VARIANT_STYLES: tuple[LineStyle, ...] = (
    "--",
    ":",
    "-.",
    (0.0, (6.0, 2.0)),
    (0.0, (4.0, 1.0, 1.0, 1.0)),
    (0.0, (1.0, 1.0)),
)
"""Six dash patterns for the six variants beside the solid base line (lines only, distinct in
black and white; user 2026-10-17)."""

CIRCLE_STYLES: tuple[tuple[str, str, LineStyle], ...] = (
    ("tip", "Kopfkreis $d_{\\mathrm{a}}$", (0.0, (6.0, 2.0))),
    ("working", "Wälzkreis $d_{\\mathrm{w}}$", "-"),
    ("reference", "Teilkreis $d$", "-."),
    ("base", "Grundkreis $d_{\\mathrm{b}}$", ":"),
    ("root_form", "Fußformkreis $d_{\\mathrm{Ff}}$", "--"),
    ("root", "erzeugter Fußkreis $d_{\\mathrm{fE}}$", (0.0, (4.0, 1.0, 1.0, 1.0))),
)
"""The circles of Tabelle 3.1 and their dash patterns (the same for both gears)."""

VARIANTS: tuple[tuple[str, fl.FilletVariant], ...] = (
    ("ellipse_g30_ab3", fl.FilletVariant(kind="ellipse", inclination_deg=30.0, axis_ratio=3.0)),
    ("ellipse_g25_ab2", fl.FilletVariant(kind="ellipse", inclination_deg=25.0, axis_ratio=2.0)),
    ("bezier_f1", fl.FilletVariant(kind="bezier", control_factor=1.0)),
    ("bezier_f2.5", fl.FilletVariant(kind="bezier", control_factor=2.5)),
    ("bionic_phiauto_r0.3", fl.FilletVariant(kind="bionic", root_radius_factor=0.3)),
    (
        "bionic_phi35_r0.2",
        fl.FilletVariant(kind="bionic", root_angle_deg=35.0, root_radius_factor=0.2),
    ),
)
"""The six variants of the chain of 2026-10-14 (ADR-116 item 53), labels as the folders."""

FROZEN_COUNTS = rs.MeshCounts(
    over_tooth_height=18,
    at_tip_edge_break=1,
    at_tooth_root=60,
    over_tooth_thickness=14,
    root_layers=4,
    rim_rings=8,
    shoulder_columns=2,
)
FROZEN_BODY_COUNTS = bd.BodyCounts(
    hub_rings=3, pocket_rings=3, rim_rings=2, web_layers=6, flange_layers=7
)
FROZEN_TEETH = 5
FROZEN_RIM_RINGS = 12
FROZEN_BORE_RADIUS_MM = 16.5
PINION_SURFACE_TEETH = 7
PINION_SURFACE_MAX_EDGE_MM = 0.05
PINION_TIP_ROUNDING_MM = 0.1
PINION_ROUNDING_FACETS = 12
"""The frozen pocket mesh and the rigid pinion surface of the deck folders
(``frozen_mesh_20layers_bore33_pocket/manifest.json``, ADR-116 items 44 and 50)."""


def kst_e() -> GenerationResult:
    data = generation_data(CASE)
    result = compute_generation_from_data(data, data.values)
    assert isinstance(result, GenerationResult)
    return result


def _number(value: float, digits: int) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def _count(value: int) -> str:
    """An integer with a narrow space as the thousands separator (83 650)."""
    return f"{value:,}".replace(",", " ")


def _left_half(points: Sequence[tuple[float, float]]) -> np.ndarray:
    """The points of the left half of the tooth (x ≤ 0): from the gap centre over the fillet
    up to the tip."""
    array = np.asarray(points, dtype=float)
    return array[array[:, 0] <= 1e-9]


def _root_arc(base: ct.ToothContour, first: np.ndarray) -> np.ndarray:
    """The root circle arc of the generated contour from the centre line of the gap to the
    first fillet point (the fillet polyline of ``tooth_contour`` starts where the trochoid
    leaves the root circle)."""
    radius = base.generated_root_diameter_mm / 2.0
    gap_angle = np.pi / base.number_of_teeth
    first_angle = float(np.arctan2(-first[0], first[1]))
    angles = np.linspace(gap_angle, first_angle, 40)
    return np.column_stack([-radius * np.sin(angles), radius * np.cos(angles)])


# --- fillets -------------------------------------------------------------------------------------


def figure_fillets(generation: GenerationResult, out: Path) -> list[Path]:
    """The left tooth half of every contour from the gap centre to the involute, lines only
    (a method figure): the base line solid, every variant with its own dash pattern."""
    base = ct.tooth_contour(generation, "wheel")
    figure, ax = new_figure("full", 0.8)
    left = _left_half(base.points)
    base_line = np.vstack([_root_arc(base, left[0]), left])
    ax.plot(
        base_line[:, 0],
        base_line[:, 1],
        color=BLACK,
        linestyle="-",
        marker="none",
        label=ffc.variant_name(ffc.BASELINE_LABEL),
    )
    for k, (label, variant) in enumerate(VARIANTS):
        built = fl.apply(generation, "wheel", variant)
        left = _left_half(built.contour.points)
        ax.plot(
            left[:, 0],
            left[:, 1],
            linestyle=VARIANT_STYLES[k % len(VARIANT_STYLES)],
            marker="none",
            label=ffc.variant_name(label),
        )
    root = base.generated_root_diameter_mm / 2.0
    ax.set_xlim(-1.65, -0.35)
    ax.set_ylim(root - 0.45, root + 1.55)
    ax.set_aspect("equal")
    ax.set_xlabel("x in mm, Lückenmitte bei $x$ = $-$1,51 mm")
    ax.set_ylabel("y in mm, Radachse bei 0")
    decimal_comma(ax)
    legend_outside(figure, ax, where="bottom", ncol=2)
    return save_figure(figure, out / "konturen")


# --- the pair in the transverse section ----------------------------------------------------------


@dataclass(frozen=True)
class PathOfContact:
    """The line of action of the pair in the frame of ``fe.placement`` (pinion axis at the
    origin, wheel axis at (a_w, 0)): the tangent points, the points A to E and the placement
    of both gears in the position C."""

    tangent_points_mm: tuple[tuple[float, float], tuple[float, float]]
    named_points_mm: dict[str, tuple[float, float]]
    placement: pl.Placement


def path_of_contact(generation: GenerationResult) -> PathOfContact:
    """A, B, C, D, E and T_1, T_2 on the line of action of the working flanks of the driving
    pinion (test rig: clockwise, the right flanks), the gears placed in the position C."""
    geometry = generation.pair_geometry
    a_w = geometry.centre_distance_mm
    alpha_wt = math.radians(geometry.transverse_working_pressure_angle_deg)
    flank = pl.working_flank_of_the_driving_pinion(ROTATION)
    rho_a, rho_e = pl.path_of_contact_limits(generation)
    rho_b, rho_d = pl.single_contact_points(generation)
    rho_c = 0.5 * geometry.gears.pinion.base_diameter_mm * math.tan(alpha_wt)
    t1_t2 = pr.length_between_tangent_points(a_w, alpha_wt)

    def point(rho: float) -> tuple[float, float]:
        return pl.mesh_position(generation, rho, working_flank=flank).contact_point_mm

    return PathOfContact(
        tangent_points_mm=(point(0.0), point(t1_t2)),
        named_points_mm={
            name: point(rho)
            for name, rho in (("A", rho_a), ("B", rho_b), ("C", rho_c), ("D", rho_d), ("E", rho_e))
        },
        placement=pl.fixed_axes(pl.mesh_position(generation, rho_c, working_flank=flank)),
    )


def _draw_path_of_contact(ax: Any, path: PathOfContact) -> None:
    t1, t2 = path.tangent_points_mm
    ax.plot(
        [t1[0], t2[0]],
        [t1[1], t2[1]],
        color=BLACK,
        linestyle=":",
        linewidth=0.6,
        marker="none",
        label="Eingriffslinie $T_{\\mathrm{1}}T_{\\mathrm{2}}$",
    )
    a, e = path.named_points_mm["A"], path.named_points_mm["E"]
    ax.plot(
        [a[0], e[0]],
        [a[1], e[1]],
        color=BLACK,
        linestyle="-",
        linewidth=0.9,
        marker="none",
        label="Eingriffsstrecke $AE$",
    )
    xs = [p[0] for p in path.named_points_mm.values()]
    ys = [p[1] for p in path.named_points_mm.values()]
    ax.plot(
        xs,
        ys,
        linestyle="none",
        marker="o",
        markersize=3.5,
        color=BLACK,
        label="Normpunkte $A$ bis $E$ ($C$ Wälzpunkt, $B$ und $D$ äußere Einzeleingriffspunkte)",
    )
    # the names beside the points, away from the line of action (its normal points to +x)
    direction = np.array([e[0] - a[0], e[1] - a[1]])
    normal = np.array([direction[1], -direction[0]]) / float(np.hypot(*direction))
    if normal[0] < 0.0:
        normal = -normal
    for name, (x, y) in path.named_points_mm.items():
        ax.annotate(
            name,
            (x, y),
            xytext=(7.0 * normal[0], 7.0 * normal[1]),
            textcoords="offset points",
            ha="center",
            va="center",
        )


def figure_stirnschnitt(generation: GenerationResult, out: Path) -> list[Path]:
    """Both gears in the position C with the circles of the geometry table and the line of
    action: the transverse section around the pitch point."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle

    path = path_of_contact(generation)
    geometry = generation.pair_geometry
    figure, ax = new_figure("full", 0.78)
    gears = (
        (
            "pinion",
            PINION_COLOUR,
            "Ritzel",
            path.placement.axis_mm.pinion,
            path.placement.tooth_centre_angle_deg.pinion,
        ),
        (
            "wheel",
            WHEEL_COLOUR,
            "Rad",
            path.placement.axis_mm.wheel,
            path.placement.tooth_centre_angle_deg.wheel,
        ),
    )
    for role_name, colour, name, axis, angle in gears:
        role: ct.Role = "pinion" if role_name == "pinion" else "wheel"
        contour = ct.tooth_contour(generation, role, points=60)
        polygon = pl.placed(ct.gear_polygon(contour), axis, angle)
        closed = np.vstack([polygon, polygon[:1]])
        z = contour.number_of_teeth
        ax.plot(
            closed[:, 0],
            closed[:, 1],
            color=colour,
            linestyle="-",
            linewidth=0.9,
            marker="none",
            label=f"{name}, $z$ = {z}, Kontur der Erzeugung",
        )
        basic = geometry.gears.pinion if role == "pinion" else geometry.gears.wheel
        generated = generation.gears.pinion if role == "pinion" else generation.gears.wheel
        working = (
            geometry.working_pitch_diameter_mm.pinion
            if role == "pinion"
            else geometry.working_pitch_diameter_mm.wheel
        )
        diameters = {
            "tip": generated.tip_diameter_mm,
            "working": working,
            "reference": basic.reference_diameter_mm,
            "base": basic.base_diameter_mm,
            "root_form": generated.root_form_diameter_mm,
            "root": generated.generated_root_diameter_mm,
        }
        for key, _, style in CIRCLE_STYLES:
            ax.add_patch(
                Circle(
                    axis,
                    0.5 * diameters[key],
                    fill=False,
                    edgecolor=colour,
                    linestyle=style,
                    linewidth=0.6,
                )
            )
    _draw_path_of_contact(ax, path)
    handles, labels = ax.get_legend_handles_labels()
    for _, label, style in CIRCLE_STYLES:
        dash: Any = style  # matplotlib's stub names only the literal styles
        handles.append(Line2D([], [], color=GREY, linestyle=dash, linewidth=0.6))
        labels.append(label)
    module_mm = generation.inputs.normal_module_mm
    pitch_point = path.named_points_mm["C"]
    ax.set_xlim(pitch_point[0] - 4.2 * module_mm, pitch_point[0] + 4.2 * module_mm)
    ax.set_ylim(pitch_point[1] - 3.0 * module_mm, pitch_point[1] + 3.0 * module_mm)
    ax.set_aspect("equal")
    ax.set_xlabel("$x$ in mm, Ritzelachse bei 0")
    ax.set_ylabel("$y$ in mm")
    decimal_comma(ax)
    figure.legend(handles, labels, loc="outside lower center", ncol=2)
    return save_figure(figure, out / "stirnschnitt_kste")


# --- one tooth with the 30° tangent --------------------------------------------------------------


@dataclass(frozen=True)
class TangentPoint:
    """The point of the left fillet where the tangent makes ``angle_deg`` with the centre line
    of the tooth (x, y in mm, the tooth centre on +y), the chord between it and its mirror
    image and the radius of curvature of the fillet there."""

    angle_deg: float
    x_mm: float
    y_mm: float
    chord_mm: float
    curvature_radius_mm: float

    @property
    def diameter_mm(self) -> float:
        return 2.0 * math.hypot(self.x_mm, self.y_mm)


def tangent_point(contour: ct.ToothContour, angle_deg: float = 30.0) -> TangentPoint:
    """The 30° tangent of ISO 6336-3 on the left fillet of the contour: along the fillet
    polyline, from the root circle (tangent at 90° to the centre line) towards the involute,
    the first point where the angle of the tangent falls to ``angle_deg``; the chord is twice
    its distance from the centre line (the tooth is symmetric), the radius of curvature the
    circumradius of three fillet points about it."""
    if not 0.0 < angle_deg < 90.0:
        raise InputRangeError(f"the tangent angle must lie in 0 to 90 deg, got {angle_deg!r}")
    fillet = contour.segment("left_fillet")
    if len(fillet) < 8:
        raise InputRangeError("the fillet needs at least 8 points for the tangent")
    steps = fillet[1:] - fillet[:-1]
    phi = np.degrees(np.arctan2(np.abs(steps[:, 0]), np.abs(steps[:, 1])))
    crossings = np.flatnonzero((phi[:-1] >= angle_deg) & (phi[1:] < angle_deg))
    if len(crossings) == 0:
        raise InputRangeError(f"no tangent at {angle_deg:g} deg on the fillet")
    k = int(crossings[0])
    # the tangent angle belongs to a segment; interpolate between the segment midpoints
    fraction = (phi[k] - angle_deg) / (phi[k] - phi[k + 1])
    mid_before, mid_after = 0.5 * (fillet[k] + fillet[k + 1]), 0.5 * (fillet[k + 1] + fillet[k + 2])
    point = mid_before + fraction * (mid_after - mid_before)
    span = max(3, len(fillet) // 60)
    i = k + 1
    a, b, c = (
        fillet[max(i - span, 0)],
        fillet[i],
        fillet[min(i + span, len(fillet) - 1)],
    )
    area2 = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
    radius = (
        float(np.hypot(*(a - b)) * np.hypot(*(b - c)) * np.hypot(*(c - a)) / (2.0 * area2))
        if area2 > 0.0
        else math.inf
    )
    return TangentPoint(
        angle_deg=angle_deg,
        x_mm=float(point[0]),
        y_mm=float(point[1]),
        chord_mm=2.0 * abs(float(point[0])),
        curvature_radius_mm=radius,
    )


def figure_zahnkontur(generation: GenerationResult, out: Path) -> list[Path]:
    """One tooth of the wheel: the contour of the generation with the root arcs to both gap
    centres, the landmark circles, the 30° tangents from their points of contact to the apex
    on the centre line, the osculating circles of the fillet there and the chord (user,
    2026-10-17: the tangents start at the fillet, legend entries of circles as lines)."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Circle

    handles: list[Any] = []
    labels: list[str] = []
    base = ct.tooth_contour(generation, "wheel", points=400)
    points = base.as_array()
    left_arc = _root_arc(base, points[0])
    right_arc = np.column_stack([-left_arc[::-1, 0], left_arc[::-1, 1]])
    outline = np.vstack([left_arc, points, right_arc])
    tangent = tangent_point(base)
    basic = generation.pair_geometry.gears.wheel
    generated = generation.gears.wheel
    module_mm = generation.inputs.normal_module_mm
    figure, ax = new_figure("full", 0.85)
    ax.plot(
        outline[:, 0],
        outline[:, 1],
        color=WHEEL_COLOUR,
        linestyle="-",
        linewidth=1.2,
        marker="none",
        label="Zahnkontur des Rades: Evolvente und Trochoide der Werkzeugkopfrundung, Kantenbruch am Kopf",
    )
    circles = (
        ("Kopfkreis $d_{\\mathrm{a}}$", generated.tip_diameter_mm, CIRCLE_STYLES[0][2]),
        ("Teilkreis $d$", basic.reference_diameter_mm, CIRCLE_STYLES[2][2]),
        ("Fußformkreis $d_{\\mathrm{Ff}}$", generated.root_form_diameter_mm, CIRCLE_STYLES[4][2]),
        (
            "erzeugter Fußkreis $d_{\\mathrm{fE}}$",
            generated.generated_root_diameter_mm,
            CIRCLE_STYLES[5][2],
        ),
    )
    for label, diameter, style in circles:
        ax.add_patch(
            Circle(
                (0.0, 0.0),
                0.5 * diameter,
                fill=False,
                edgecolor=GREY,
                linestyle=style,
                linewidth=0.6,
            )
        )
        dash: Any = style  # matplotlib's stub names only the literal styles
        handles.append(Line2D([], [], color=GREY, linestyle=dash, linewidth=0.6))
        labels.append(f"{label} = {_number(diameter, 3)} mm")
    ax.axvline(0.0, color=GREY, linestyle="-.", linewidth=0.4)
    angle = math.radians(tangent.angle_deg)
    x_touch, y_touch = abs(tangent.x_mm), tangent.y_mm
    rho = tangent.curvature_radius_mm
    # the two tangents run from their point of contact on the fillet to the apex on the centre line
    apex_y = y_touch + x_touch / math.tan(angle)
    for sign in (-1.0, 1.0):
        ax.plot(
            [sign * x_touch, 0.0],
            [y_touch, apex_y],
            color=BLACK,
            linestyle="-",
            linewidth=0.6,
            marker="none",
            label=f"{_number(tangent.angle_deg, 0)}°-Tangenten an die Fußrundung bis zur Zahnmitte"
            if sign < 0.0
            else None,
        )
        # the osculating circle of the fillet at the point of contact: its centre lies in the
        # gap, on the normal of the tangent, rho_F away from the point
        ax.add_patch(
            Circle(
                (sign * (x_touch + rho * math.cos(angle)), y_touch + rho * math.sin(angle)),
                rho,
                fill=False,
                edgecolor=BLACK,
                linestyle=":",
                linewidth=0.6,
            )
        )
    ax.plot(
        [-x_touch, x_touch],
        [y_touch, y_touch],
        color=BLACK,
        linestyle="--",
        linewidth=0.9,
        marker="|",
        markersize=5,
        label=f"Fußdickensehne $s_{{\\mathrm{{Fn}}}}$ = {_number(tangent.chord_mm, 3)} mm",
    )
    ax.plot(
        [-x_touch, x_touch],
        [y_touch, y_touch],
        linestyle="none",
        marker="o",
        markersize=3.5,
        color=BLACK,
        label=f"Berührpunkte der Tangenten bei $d$ = {_number(tangent.diameter_mm, 3)} mm",
    )
    line_handles, line_labels = ax.get_legend_handles_labels()
    handles = line_handles + handles
    labels = line_labels + labels
    handles.append(Line2D([], [], color=BLACK, linestyle=":", linewidth=0.6))
    labels.append(
        f"Krümmungskreise der Fußrundung in den Berührpunkten, $\\rho_{{\\mathrm{{F}}}}$ = "
        f"{_number(rho, 3)} mm ($\\rho_{{\\mathrm{{F}}}}/m_{{\\mathrm{{n}}}}$ = {_number(rho / module_mm, 2)})"
    )
    root = 0.5 * generated.generated_root_diameter_mm
    tip = 0.5 * generated.tip_diameter_mm
    ax.set_xlim(-1.9 * module_mm, 1.9 * module_mm)
    ax.set_ylim(root - 0.45 * module_mm, tip + 0.35 * module_mm)
    ax.set_aspect("equal")
    ax.set_xlabel("$x$ in mm, Zahnmitte bei 0")
    ax.set_ylabel("$y$ in mm, Radachse bei 0")
    decimal_comma(ax)
    figure.legend(handles, labels, loc="outside lower center", ncol=1)
    return save_figure(figure, out / "zahnkontur_kste")


# --- the body of the wheel after the drawing -----------------------------------------------------


def _rounded_corner(
    before: np.ndarray, corner: np.ndarray, after: np.ndarray, radius: float, n: int = 12
) -> np.ndarray:
    """The arc of radius ``radius`` tangent to both legs of the corner, from the leg towards
    ``before`` to the leg towards ``after``."""
    u = (before - corner) / float(np.hypot(*(before - corner)))
    v = (after - corner) / float(np.hypot(*(after - corner)))
    theta = math.acos(max(-1.0, min(1.0, float(u @ v))))
    tangent_length = radius / math.tan(0.5 * theta)
    first, last = corner + u * tangent_length, corner + v * tangent_length
    bisector = (u + v) / float(np.hypot(*(u + v)))
    centre = corner + bisector * radius / math.sin(0.5 * theta)
    a1 = math.atan2(first[1] - centre[1], first[0] - centre[0])
    a2 = math.atan2(last[1] - centre[1], last[0] - centre[0])
    sweep = math.atan2(math.sin(a2 - a1), math.cos(a2 - a1))
    angles = a1 + sweep * np.linspace(0.0, 1.0, n)
    return np.column_stack(
        [centre[0] + radius * np.cos(angles), centre[1] + radius * np.sin(angles)]
    )


def body_outline(body: bd.BodySection) -> np.ndarray:
    """The meridional section of the body as a closed polyline in (r, z): bore, both faces,
    both pockets with their draft and the corner radii of the drawing, the tip."""
    half, floor, depth = 0.5 * body.face_width_mm, body.bottom_z_mm, body.pocket_depth_mm
    hub_face, hub_floor = body.hub_wall_radius_at(0.0), body.hub_wall_radius_at(depth)
    rim_face, rim_floor = body.rim_wall_radius_at(0.0), body.rim_wall_radius_at(depth)
    corners = np.array(
        [
            (body.bore_radius_mm, -half),
            (hub_face, -half),
            (hub_floor, -floor),
            (rim_floor, -floor),
            (rim_face, -half),
            (body.tip_radius_mm, -half),
            (body.tip_radius_mm, half),
            (rim_face, half),
            (rim_floor, floor),
            (hub_floor, floor),
            (hub_face, half),
            (body.bore_radius_mm, half),
        ]
    )
    rounded = {2, 3, 4, 7, 8, 9}  # the floor corners and the rim-side corner at each face
    pieces: list[np.ndarray] = []
    count = len(corners)
    for i in range(count):
        if i in rounded and body.corner_radius_mm > 0.0:
            pieces.append(
                _rounded_corner(
                    corners[(i - 1) % count],
                    corners[i],
                    corners[(i + 1) % count],
                    body.corner_radius_mm,
                )
            )
        else:
            pieces.append(corners[i : i + 1])
    pieces.append(pieces[0][:1])
    return np.vstack(pieces)


def _dimension(
    ax: Any,
    start: tuple[float, float],
    end: tuple[float, float],
    text: str,
    offset: tuple[float, float] = (0.0, 0.0),
) -> None:
    """A dimension line with arrow heads at both ends and the value beside its middle."""
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={
            "arrowstyle": "<->",
            "color": BLACK,
            "linewidth": 0.6,
            "shrinkA": 0.0,
            "shrinkB": 0.0,
        },
    )
    ax.annotate(
        text,
        (0.5 * (start[0] + end[0]), 0.5 * (start[1] + end[1])),
        xytext=offset,
        textcoords="offset points",
        ha="center",
        va="center",
        fontsize="small",
        bbox={"boxstyle": "square,pad=0.1", "facecolor": "white", "edgecolor": "none"},
    )


def figure_radkoerper(body: bd.BodySection, generation: GenerationResult, out: Path) -> list[Path]:
    """The meridional section of the wheel body through the centre of a tooth with the
    dimensions of the drawing; the steel insert sits in the bore and is not part of it."""
    from matplotlib.colors import to_rgba
    from matplotlib.patches import Polygon

    outline = body_outline(body)
    half, floor, depth = 0.5 * body.face_width_mm, body.bottom_z_mm, body.pocket_depth_mm
    root = 0.5 * generation.gears.wheel.generated_root_diameter_mm
    figure, ax = new_figure("full", 0.66)
    r, g, b, _ = to_rgba(SHEET.colour("tum_elfenbein"))
    ax.add_patch(Polygon(outline, closed=True, facecolor=(r, g, b, 0.5), edgecolor="none"))
    ax.plot(
        outline[:, 0],
        outline[:, 1],
        color=BLACK,
        linestyle="-",
        linewidth=0.9,
        marker="none",
        label="Kunststoffkörper nach Zeichnung, Schnitt durch die Zahnmitte",
    )
    ax.plot(
        [root, root],
        [-half, half],
        color=GREY,
        linestyle=CIRCLE_STYLES[5][2],
        linewidth=0.6,
        marker="none",
        label=f"erzeugter Fußkreis, $r$ = {_number(root, 3)} mm: Beginn der Verzahnung",
    )
    ax.plot(
        [body.bore_radius_mm, body.bore_radius_mm],
        [-half, half],
        color=MARK_COLOUR,
        linestyle="-",
        linewidth=1.2,
        marker="none",
        label=(
            f"Bohrung Ø {_number(2.0 * body.bore_radius_mm, 0)} mm: Sitz des Stahleinlegers "
            "(nicht Teil der Zeichnung des Kunststoffkörpers)"
        ),
    )
    pocket_mid = 0.5 * (body.hub_wall_radius_at(0.5 * depth) + body.rim_wall_radius_at(0.5 * depth))
    web_mid = 0.5 * (body.hub_wall_radius_at(depth) + body.rim_wall_radius_at(depth))
    for name, x, y, turn in (
        ("Nabe", 0.5 * (body.bore_radius_mm + body.hub_wall_radius_mm), 0.0, 0),
        ("Steg", web_mid + 0.5, 0.0, 0),
        ("Tasche", pocket_mid - 0.6, floor + 0.7 * depth, 0),
        ("Tasche", pocket_mid - 0.6, -floor - 0.7 * depth, 0),
        ("Felge", 0.5 * (body.rim_wall_radius_mm + root), 0.0, 90),
        ("Zahn", 0.5 * (root + body.tip_radius_mm), 0.0, 90),
    ):
        ax.text(x, y, name, ha="center", va="center", rotation=turn)
    # the dimensions of the drawing (mm): face width, pocket depth and web inside the body,
    # the radii as leaders above the upper face, the draft angle and one corner radius
    tip = body.tip_radius_mm
    _dimension(
        ax,
        (tip + 0.6, -half),
        (tip + 0.6, half),
        f"$b$ = {_number(body.face_width_mm, 0)}",
        (10, 0),
    )
    _dimension(ax, (pocket_mid + 0.55, floor), (pocket_mid + 0.55, half), _number(depth, 1), (9, 0))
    _dimension(
        ax,
        (web_mid - 0.8, -floor),
        (web_mid - 0.8, floor),
        _number(body.web_thickness_mm, 0),
        (-8, 0),
    )
    leader = {"arrowstyle": "-", "color": BLACK, "linewidth": 0.4}
    for text, x, y, row in (
        (f"r {_number(body.bore_radius_mm, 1)}", body.bore_radius_mm, half, 0),
        (f"r {_number(body.hub_wall_radius_mm, 3)}", body.hub_wall_radius_mm, half, 1),
        (
            f"r {_number(body.rim_wall_radius_mm, 3)} in {_number(body.rim_wall_height_mm, 3)} Tiefe",
            body.rim_wall_radius_mm,
            half - body.rim_wall_height_mm,
            0,
        ),
        (f"r {_number(tip, 3)}", tip, half, 1),
    ):
        ax.annotate(
            text,
            (x, y),
            xytext=(x, half + 0.9 + 0.9 * row),  # two rows, so that the labels do not touch
            textcoords="data",
            ha="center",
            va="bottom",
            fontsize="small",
            arrowprops=leader,
        )
    ax.annotate(
        f"{_number(body.wall_angle_deg, 0)}°",
        (body.rim_wall_radius_at(0.3 * depth), floor + 0.3 * depth),
        xytext=(12, 6),
        textcoords="offset points",
        ha="left",
        va="center",
        fontsize="small",
        arrowprops=leader,
    )
    ax.annotate(
        f"R {_number(body.corner_radius_mm, 1)}",
        (body.hub_wall_radius_at(depth) + body.corner_radius_mm, floor + body.corner_radius_mm),
        xytext=(-46, 20),
        textcoords="offset points",
        ha="center",
        va="center",
        fontsize="small",
        arrowprops=leader,
    )
    ax.set_xlim(body.bore_radius_mm - 0.6, tip + 1.6)
    ax.set_ylim(-half - 1.2, half + 3.0)
    ax.set_aspect("equal")
    ax.set_xlabel("$r$ in mm, Radachse bei 0")
    ax.set_ylabel("$z$ in mm, Mittelebene bei 0")
    decimal_comma(ax)
    legend_outside(figure, ax, where="bottom", ncol=1)
    return save_figure(figure, out / "radkoerper_kste")


# --- the frozen mesh without titles --------------------------------------------------------------


def frozen_mesh(generation: GenerationResult) -> bd.BodyMesh:
    """The frozen pocket mesh of the wheel, built as the deck folder was."""
    section = sm.sector_mesh(
        generation,
        "wheel",
        teeth=FROZEN_TEETH,
        rim_rings=FROZEN_RIM_RINGS,
        bore_radius_mm=FROZEN_BORE_RADIUS_MM,
        counts=FROZEN_COUNTS,
    )
    return bd.body_mesh(section, bd.body_section(CASE, "wheel"), FROZEN_BODY_COUNTS, "WHEEL")


def _draw_quads(
    ax: Any,
    points: np.ndarray,
    quads: np.ndarray,
    *,
    edge: Any = QUAD_EDGE,
    width: float = 0.25,
    face: Any = "none",
) -> None:
    from matplotlib.collections import PolyCollection

    ax.add_collection(
        PolyCollection(points[quads], facecolors=face, edgecolors=edge, linewidths=width)
    )


def figure_mesh(built: bd.BodyMesh, generation: GenerationResult, out: Path) -> list[Path]:
    """The four mesh pictures of the thesis: sector, one tooth, body section, the pair in C."""
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import to_rgba

    written: list[Path] = []
    section, solid, body = built.section, built.solid, built.body
    points = section.points_mm
    quads = section.quads
    middle = rf.middle_tooth(section.teeth)
    module_mm = generation.inputs.normal_module_mm
    fixed_set = built.full_sets.node_sets["WHEEL_FESSELUNG"]
    fixed = points[fixed_set[fixed_set < len(points)]]

    # 1 the sector
    figure, ax = new_figure("full", 0.58)
    _draw_quads(ax, points, quads, width=0.2)
    ax.plot(
        [],
        [],
        color=QUAD_EDGE,
        linestyle="-",
        linewidth=0.6,
        marker="none",
        label=(
            f"Netz im Stirnschnitt: {section.teeth} Zähne und zwei zahnlose Teilungen, "
            f"{_count(len(points))} Knoten und {_count(len(quads))} Elemente je Schicht"
        ),
    )
    ax.plot(
        fixed[:, 0],
        fixed[:, 1],
        linestyle="none",
        marker=".",
        markersize=2.5,
        color=MARK_COLOUR,
        label=f"Fesselung: Knoten der Bohrung ($r$ = {_number(section.bore_radius_mm, 1)} mm) und der Schnittufer",
    )
    for tooth in range(1, section.teeth + 1):
        angle = section.tooth_centre_angle_rad(tooth)
        radius = section.tip_radius_mm + 0.6 * module_mm
        ax.text(
            radius * math.cos(angle),
            radius * math.sin(angle),
            f"T{tooth}",
            ha="center",
            va="center",
        )
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.margins(0.03)
    ax.set_ylim(top=section.tip_radius_mm + 1.6 * module_mm)
    ax.set_xlabel("$x$ in mm")
    ax.set_ylabel("$y$ in mm")
    decimal_comma(ax)
    legend_outside(figure, ax, where="bottom", ncol=1)
    written += save_figure(figure, out / "netz_sektor")
    plt.close(figure)

    # 2 one tooth
    counts = rf.effective_counts(section)
    figure, ax = new_figure(120.0, 0.95)
    _draw_quads(ax, points, quads, width=0.3)
    ax.plot(
        [],
        [],
        color=QUAD_EDGE,
        linestyle="-",
        linewidth=0.6,
        marker="none",
        label=(
            f"Zahn T{middle}: {counts.over_tooth_height - FROZEN_COUNTS.at_tip_edge_break} Reihen "
            f"über der Zahnhöhe und {FROZEN_COUNTS.at_tip_edge_break} am Kopfkantenbruch,\n"
            f"{counts.at_tooth_root} Elemente je Fußbogen, {counts.over_tooth_thickness} Spalten "
            f"über der Zahndicke, {FROZEN_COUNTS.root_layers} Fußschichten"
        ),
    )
    ax.set_xlim(-1.9 * module_mm, 1.9 * module_mm)
    ax.set_ylim(
        section.fan_ring_radius_mm - 0.5 * module_mm, section.tip_radius_mm + 0.3 * module_mm
    )
    ax.set_aspect("equal")
    ax.set_xlabel("$x$ in mm")
    ax.set_ylabel("$y$ in mm")
    decimal_comma(ax)
    legend_outside(figure, ax, where="bottom", ncol=1)
    written += save_figure(figure, out / "netz_zahn")
    plt.close(figure)

    # 3 the body in the meridional section through the middle tooth
    centre = section.tooth_centre_angle_rad(middle)
    xy = solid.nodes_mm[:, :2]
    offset = np.angle(np.exp(1j * (np.arctan2(xy[:, 1], xy[:, 0]) - centre)))
    on_line = np.abs(offset) < 1.0e-7
    node_radius = np.hypot(xy[:, 0], xy[:, 1])
    z = solid.nodes_mm[:, 2]
    mask = on_line[solid.hexes]
    candidates = np.flatnonzero((mask[:, :4].sum(axis=1) == 2) & (mask[:, 4:].sum(axis=1) == 2))
    polygons = []
    for element in candidates.tolist():
        corners = solid.hexes[element]
        lower = sorted(corners[:4][mask[element, :4]].tolist(), key=lambda k: node_radius[k])
        upper = sorted(corners[4:][mask[element, 4:]].tolist(), key=lambda k: -node_radius[k])
        polygons.append([(node_radius[k], z[k]) for k in (*lower, *upper)])
    figure, ax = new_figure("full", 0.6)
    r, g, b, _ = to_rgba(SHEET.colour("tum_grau_20"))
    ax.add_collection(
        PolyCollection(polygons, facecolors=(r, g, b, 0.5), edgecolors=QUAD_EDGE, linewidths=0.3)
    )
    ax.plot(
        [],
        [],
        color=QUAD_EDGE,
        linestyle="-",
        linewidth=0.6,
        marker="none",
        label=(
            f"Elemente im Meridianschnitt durch die Mitte von Zahn T{middle}: Ringe Nabe/Tasche/Felge "
            f"{built.counts.hub_rings}/{built.counts.pocket_rings}/{built.counts.rim_rings},\n"
            f"Schichten Steg {built.counts.web_layers} und je Tasche {built.counts.flange_layers}; "
            f"{_count(len(solid.nodes_mm))} Knoten, {_count(len(solid.hexes))} Elemente"
        ),
    )
    outline = body_outline(body)
    ax.plot(
        outline[:, 0],
        outline[:, 1],
        color=MARK_COLOUR,
        linestyle="-",
        linewidth=1.0,
        marker="none",
        label=(
            "Zeichnung: Nabenwand, Taschengrund und Felgenwand\n"
            "mit den Rundungen R 0,5 (nicht vernetzt)"
        ),
    )
    half = 0.5 * body.face_width_mm
    ax.set_xlim(body.bore_radius_mm - 0.5, body.tip_radius_mm + 0.5)
    ax.set_ylim(-half - 0.5, half + 0.5)
    ax.set_aspect("equal")
    ax.set_xlabel("$r$ in mm")
    ax.set_ylabel("$z$ in mm")
    decimal_comma(ax)
    legend_outside(figure, ax, where="bottom", ncol=1)
    written += save_figure(figure, out / "netz_koerper")
    plt.close(figure)

    # 4 the pair in the position C: the sector and the rigid pinion surface
    path = path_of_contact(generation)
    rigid = rsf.rigid_surface(
        generation,
        "pinion",
        teeth=PINION_SURFACE_TEETH,
        max_edge_mm=PINION_SURFACE_MAX_EDGE_MM,
        z_levels_mm=np.array([-0.5, 0.5]),
        tip_rounding_mm=PINION_TIP_ROUNDING_MM,
        rounding_facets=PINION_ROUNDING_FACETS,
    )
    profile = pl.placed(
        rigid.nodes_mm[: rigid.profile_nodes, :2],
        path.placement.axis_mm.pinion,
        path.placement.tooth_centre_angle_deg.pinion,
    )
    placed_points = pl.placed(
        points, path.placement.axis_mm.wheel, path.placement.tooth_centre_angle_deg.wheel
    )
    figure, ax = new_figure("full", 0.62)
    _draw_quads(ax, placed_points, quads, edge=WHEEL_COLOUR, width=0.2)
    ax.plot(
        [],
        [],
        color=WHEEL_COLOUR,
        linestyle="-",
        linewidth=0.6,
        marker="none",
        label=f"Radsektor: Netz im Stirnschnitt, {section.teeth} Zähne",
    )
    ax.plot(
        profile[:, 0],
        profile[:, 1],
        color=PINION_COLOUR,
        linestyle="-",
        linewidth=0.9,
        marker="none",
        label=(
            f"starre Ritzelfläche: {rigid.teeth} Zähne, {rigid.profile_nodes} Profilknoten, "
            f"Facetten bis {_number(PINION_SURFACE_MAX_EDGE_MM, 2)} mm, Kopfkantenrundung "
            f"{_number(PINION_TIP_ROUNDING_MM, 1)} mm"
        ),
    )
    _draw_path_of_contact(ax, path)
    pitch_point = path.named_points_mm["C"]
    ax.set_xlim(pitch_point[0] - 5.0 * module_mm, pitch_point[0] + 5.0 * module_mm)
    ax.set_ylim(pitch_point[1] - 3.6 * module_mm, pitch_point[1] + 3.6 * module_mm)
    ax.set_aspect("equal")
    ax.set_xlabel("$x$ in mm, Ritzelachse bei 0")
    ax.set_ylabel("$y$ in mm")
    decimal_comma(ax)
    legend_outside(figure, ax, where="bottom", ncol=1)
    written += save_figure(figure, out / "paarung_netz")
    plt.close(figure)
    return written


# --- command line ----------------------------------------------------------------------------------

CAPTIONS = {
    "konturen": (
        "Fußrundungsvarianten des Rades kst-E im Stirnschnitt gegen die Trochoide der Erzeugung, "
        "linke Zahnhälfte von der Lückenmitte bis zum Kopf; die Ellipsen setzen am Fußformkreis an, "
        "die Patentkonturen am mittleren Durchmesser zwischen Nutzkreis und Fußformkreis (Konturen "
        "aus gearcore.fillet, dieselben wie in den FE-Netzen)."
    ),
    "stirnschnitt_kste": (
        "Stirnschnitt der Prüfverzahnung kst-E in der Stellung C: Konturen der Erzeugung, die "
        "Kreise der Geometrietabelle, Eingriffslinie und Eingriffsstrecke mit den Normpunkten A bis E "
        "(Ritzel treibt im Uhrzeigersinn, rechte Flanken arbeiten)."
    ),
    "zahnkontur_kste": (
        "Zahn des Rades kst-E im Stirnschnitt: Evolvente, Trochoide der Werkzeugkopfrundung und "
        "Kantenbruch, die Kreise der Erzeugung, die 30°-Tangenten mit Fußdickensehne und "
        "Krümmungsradius (Werte aus der Kontur der Geometriekette)."
    ),
    "radkoerper_kste": (
        "Radkörper des Rades kst-E im Meridianschnitt durch die Zahnmitte nach der Zeichnung: "
        "Nabe, Taschen mit Formschräge und Rundungen, Steg, Felge und Zahn; die Bohrung ist der "
        "Sitz des Stahleinlegers."
    ),
    "netz_sektor": (
        "Sektornetz des Rades im Stirnschnitt mit der Fesselung an Bohrung und Schnittufern "
        "(Taschenkörper, 20 Schichten über der Zahnbreite)."
    ),
    "netz_zahn": "Netz eines Zahns im Stirnschnitt: Randschicht an Flanke und Fußrundung, Vergröberung zum Körper.",
    "netz_koerper": "Radkörper des Taschennetzes im Meridianschnitt mit den Linien der Zeichnung.",
    "paarung_netz": (
        "Radsektor und starre Ritzelfläche in der Stellung C mit Eingriffslinie und den "
        "Normpunkten A bis E."
    ),
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "what", choices=["fillets", "stirnschnitt", "zahnkontur", "radkoerper", "mesh", "all"]
    )
    parser.add_argument("--out", type=Path, default=OUT, help="folder of the thesis drawings")
    args = parser.parse_args(argv)
    generation = kst_e()
    written: list[Path] = []
    wanted = (
        ["fillets", "stirnschnitt", "zahnkontur", "radkoerper", "mesh"]
        if args.what == "all"
        else [args.what]
    )
    if "fillets" in wanted:
        FILLETS_OUT.mkdir(parents=True, exist_ok=True)
        written += figure_fillets(generation, FILLETS_OUT)
        (FILLETS_OUT / "bildunterschriften.md").write_text(
            "\n".join(["# Bildunterschriften", "", f"- `konturen`: {CAPTIONS['konturen']}", ""]),
            encoding="utf-8",
        )
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    if "stirnschnitt" in wanted:
        written += figure_stirnschnitt(generation, out)
    if "zahnkontur" in wanted:
        written += figure_zahnkontur(generation, out)
    if "radkoerper" in wanted:
        written += figure_radkoerper(bd.body_section(CASE, "wheel"), generation, out)
    if "mesh" in wanted:
        written += figure_mesh(frozen_mesh(generation), generation, out)
    stems = sorted({path.stem for path in written if path.parent == out})
    if stems:
        lines = ["# Bildunterschriften", ""] + [f"- `{stem}`: {CAPTIONS[stem]}" for stem in stems]
        (out / "bildunterschriften.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
