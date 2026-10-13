"""Fibre orientation of the moulding simulation on the mapped wheel mesh, evaluated the way
FVA 856 I evaluates its CT scans of a tooth (ADR-119): the orientation tensor of every element
from the CONVERSE orientation file, zones of the middle tooth as Bild 17 of the report defines
them (surface bands along the flow, transition bands, the inner zones M and U), per zone the
eigenvalues, the anisotropy index and the preferred direction in the transverse plane
(Bild 17, Bild 18), the thirds of the face width (Bild 23), and the section figures with the
fibre direction of every element coloured by its orientation state (Bild 15).

    uv run --all-extras python scripts/fibre_orientation.py \\
        --mesh 80_output/fe/kst_e/<folder>/wheel_mesh.inp \\
        --cof 30_references_and_examples/91_Converse/wheel_mesh_QS.cof \\
        --tooth T3 --skin 0.2 --out 80_output/fe/faserorientierung

Writes ``zonen.csv``, ``drittel.csv``, ``bericht.md``, ``bildunterschriften.md`` and the
figures ``schnitt_<tooth>``, ``zonen_<tooth>``, ``vergleich_<tooth>``, ``drittel_<tooth>``
and ``breite_<tooth>`` (SVG and PNG) into the output folder.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
from matplotlib.path import Path as MplPath
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gearcore.errors import InputRangeError  # noqa: E402
from gearcore.fatigue import anisotropy as an  # noqa: E402
from gearcore.fe import deck as dk  # noqa: E402
from gearcore.fe import fibre as fb  # noqa: E402
from gearcore.plot_style import (  # noqa: E402
    DEGREE_COLOURMAP,
    MARKERS,
    caption,
    decimal_comma,
    german_number,
    legend_outside,
    new_figure,
)
from gearcore.plot_style import apply as apply_plot_style  # noqa: E402
from gearcore.plot_style import save as save_figure  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
Array = npt.NDArray[np.float64]
SOURCE_LABEL = "FVA 856 I"
THIRDS = ("z-", "mid", "z+")
THIRD_LABELS = {"z-": "Drittel z < −b/6", "mid": "mittleres Drittel", "z+": "Drittel z > b/6"}
SURFACE_KINDS = {"TIP": "tip", "FLANK": "flank", "ROOT": "root"}
VALLEY_FRACTION = 0.15
"""The lowest share of the fillet height (from the root circle) that counts as the valley zone
T of the report (the root land and the flattest part of the fillet arc)."""
SHEET = apply_plot_style()


def _g(value: float, digits: int = 2) -> str:
    return german_number(value, digits)


def _first_colour() -> str:
    """The first colour of the house palette (the primary blue of the style sheet)."""
    import matplotlib as mpl

    return str(mpl.rcParams["axes.prop_cycle"].by_key()["color"][0])


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def _angle_text(result: fb.ZoneResult) -> str:
    """The preferred angle, marked ``axial`` when the main axis lies mostly along the wheel
    axis (in-plane share below one half), where the angle in the plane says little."""
    text = f"{_g(result.angle_deg, 1)}°"
    return text if result.in_plane >= 0.5 else f"{text} (axial)"


def mirrored(zone: str) -> str:
    """The left-side name of a zone of the report: ``RFO`` -> ``LFO``, ``S`` stays."""
    return "L" + zone[1:] if zone.startswith("R") else zone


def reference_angle(zone: str) -> float | None:
    """The preferred direction of Bild 18 for a zone (the transition zones of a side merged)."""
    if zone in fb.FVA856_ANGLES_DEG:
        return fb.FVA856_ANGLES_DEG[zone]
    if len(zone) == 3 and zone[1] == "Ü":
        return fb.FVA856_ANGLES_DEG.get(zone[:2])
    return None


# --- the tooth -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Tooth:
    """Geometry of the evaluated tooth in the part frame."""

    name: str
    centre_angle_rad: float
    half_pitch_rad: float
    root_radius_mm: float
    tip_radius_mm: float
    half_width_mm: float
    radial: Array
    across: Array
    outline: dict[int, tuple[str, str]]
    """Outline node label -> (side 'L'/'R', kind tip/flank/root/valley)."""

    @property
    def height_mm(self) -> float:
        return self.tip_radius_mm - self.root_radius_mm


def _mean_angle(points: Array) -> float:
    unit = points[:, :2] / np.linalg.norm(points[:, :2], axis=1)[:, np.newaxis]
    mean = unit.mean(axis=0)
    return math.atan2(float(mean[1]), float(mean[0]))


def _wrapped(angle: Array | float, centre: float) -> Array | float:
    return (angle - centre + math.pi) % (2.0 * math.pi) - math.pi


def tooth_geometry(
    name: str,
    nodes: Mapping[int, tuple[float, float, float]],
    node_sets: Mapping[str, Sequence[int]],
) -> Tooth:
    """The tooth from the surface node sets of the mesh: centre angle from its tip nodes, the
    pitch from the neighbouring teeth, the outline from the tooth's own surface sets (its root
    sets reach to the middle of the gaps), the root circle as their smallest radius, and the
    valley as the lowest ``VALLEY_FRACTION`` of the fillet height (the root land, where there
    is one, and the flattest part of the fillet arc)."""
    number = int(name[1:])

    def labels(key: str) -> tuple[int, ...]:
        if key not in node_sets:
            raise InputRangeError(f"the mesh has no node set {key}")
        return tuple(node_sets[key])

    def xyz(keys: Sequence[int]) -> Array:
        return np.array([nodes[k] for k in keys], dtype=np.float64)

    tip = labels(f"WHEEL_{name}_LEFT_SURF_TIP_NODES") + labels(f"WHEEL_{name}_RIGHT_SURF_TIP_NODES")
    centre = _mean_angle(xyz(tip))
    neighbours = []
    for other in (number - 1, number + 1):
        key = f"WHEEL_T{other}_LEFT_SURF_TIP_NODES"
        if key in node_sets:
            neighbours.append(_mean_angle(xyz(labels(key) + labels(key.replace("LEFT", "RIGHT")))))
    if not neighbours:
        raise InputRangeError(f"tooth {name} has no neighbouring tooth in the mesh for the pitch")
    pitch = float(np.mean([abs(float(_wrapped(a, centre))) for a in neighbours]))
    outline: dict[int, tuple[str, str]] = {}
    for side_name, side in (("LEFT", "L"), ("RIGHT", "R")):
        for set_kind, kind in SURFACE_KINDS.items():
            for label in labels(f"WHEEL_{name}_{side_name}_SURF_{set_kind}_NODES"):
                outline[label] = (side, kind)
    # the fillet sets reach the middle of the gaps: their lowest band is the valley
    fillet_labels = [label for label, (_side, kind) in outline.items() if kind == "root"]
    fillet_radii = {k: float(np.hypot(*nodes[k][:2])) for k in fillet_labels}
    root_radius = min(fillet_radii.values())
    fillet_height = max(fillet_radii.values()) - root_radius
    if not fillet_height > 0.0:
        raise InputRangeError(f"the fillet of {name} has no height")
    for label, radius in fillet_radii.items():
        if radius - root_radius <= VALLEY_FRACTION * fillet_height:
            outline[label] = (outline[label][0], "valley")
    kinds = {kind for _side, kind in outline.values()}
    if kinds != {"tip", "flank", "root", "valley"}:
        raise InputRangeError(f"the outline of {name} has the kinds {sorted(kinds)}, not all four")
    # left = counter-clockwise (larger angle) seen from +z, as the mesh header says
    left = [label for label, (side, _kind) in outline.items() if side == "L"]
    if not float(_wrapped(_mean_angle(xyz(left)), centre)) > 0.0:
        raise InputRangeError(f"the LEFT side of {name} is not the counter-clockwise side")
    radial = np.array([math.cos(centre), math.sin(centre), 0.0])
    across = np.array([-math.sin(centre), math.cos(centre), 0.0])  # counter-clockwise = left
    return Tooth(
        name=name,
        centre_angle_rad=centre,
        half_pitch_rad=pitch / 2.0,
        root_radius_mm=root_radius,
        tip_radius_mm=max(float(np.hypot(*nodes[k][:2])) for k in tip),
        half_width_mm=max(abs(v[2]) for v in nodes.values()),
        radial=radial,
        across=across,
        outline=outline,
    )


# --- the elements --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Elements:
    """The elements of the tooth region with everything the zones need."""

    labels: npt.NDArray[np.int64]
    centroids: Array
    volumes: Array
    tensors: Array
    a11: Array
    depth_mm: Array
    zones: tuple[str, ...]
    thirds: tuple[str, ...]
    x_mm: Array
    """Across the tooth in the plot frame (positive to the right, the clockwise side)."""
    y_mm: Array
    """Above the root circle along the tooth axis."""
    e1: Array
    """Fibre direction of every element (unit vectors, n x 3)."""


def tooth_elements(
    tooth: Tooth,
    nodes: Mapping[int, tuple[float, float, float]],
    connectivity: Mapping[int, Sequence[int]],
    orientation: Mapping[int, tuple[dk.Vector, dk.Vector]],
    states: Mapping[int, tuple[float, float]],
    skin_mm: float,
    below_mm: float,
) -> Elements:
    """Every element whose centroid lies within half a pitch of the tooth axis and above the
    root circle minus ``below_mm``; depth = distance of the centroid to the nearest outline
    node in the transverse plane."""
    labels = np.array(sorted(connectivity), dtype=np.int64)
    corner_labels = np.array([connectivity[k] for k in labels], dtype=np.int64)
    if corner_labels.shape[1] != 8:
        raise InputRangeError("the tooth zones need hexahedral elements (8 nodes)")
    coordinates = np.array([nodes[int(k)] for k in corner_labels.ravel()], dtype=np.float64)
    corners = coordinates.reshape(len(labels), 8, 3)
    centroids = corners.mean(axis=1)
    angle = np.arctan2(centroids[:, 1], centroids[:, 0])
    radius = np.hypot(centroids[:, 0], centroids[:, 1])
    keep = (np.abs(_wrapped(angle, tooth.centre_angle_rad)) <= tooth.half_pitch_rad) & (
        radius >= tooth.root_radius_mm - below_mm
    )
    labels, corners, centroids, corner_labels = (
        labels[keep],
        corners[keep],
        centroids[keep],
        corner_labels[keep],
    )
    if labels.size == 0:
        raise InputRangeError(f"no element lies within the pitch of {tooth.name}")
    volumes = fb.hexahedron_volumes(corners)
    outline_labels = np.array(sorted(tooth.outline), dtype=np.int64)
    outline_xy = np.array([nodes[int(k)][:2] for k in outline_labels], dtype=np.float64)
    depth, nearest = cKDTree(outline_xy).query(centroids[:, :2])
    radius = np.hypot(centroids[:, 0], centroids[:, 1])
    height_fraction = (radius - tooth.root_radius_mm) / tooth.height_mm
    zones = []
    for i in range(labels.size):
        side, kind = tooth.outline[int(outline_labels[nearest[i]])]
        zones.append(
            fb.zone_name(
                side=side,
                kind=kind,
                depth_mm=float(depth[i]),
                skin_mm=skin_mm,
                height_fraction=float(height_fraction[i]),
            )
        )
    thirds = tuple(fb.third_of_width(float(z), tooth.half_width_mm) for z in centroids[:, 2])
    tensors = np.zeros((labels.size, 3, 3))
    a11 = np.zeros(labels.size)
    e1 = np.zeros((labels.size, 3))
    missing = [int(k) for k in labels if int(k) not in orientation]
    if missing:
        raise InputRangeError(
            f"{len(missing)} elements without an orientation (first {missing[:5]})"
        )
    for i, label in enumerate(labels):
        frame = an.element_frame(*orientation[int(label)])
        rows = [states[int(n)] for n in corner_labels[i]]
        a11[i] = float(np.mean([r[0] for r in rows]))
        a22 = float(np.mean([r[1] for r in rows]))
        tensors[i] = fb.orientation_tensor(frame, a11[i], a22)
        e1[i] = frame[:, 0]
    relative = centroids - tooth.radial * tooth.root_radius_mm
    return Elements(
        labels=labels,
        centroids=centroids,
        volumes=volumes,
        tensors=tensors,
        a11=a11,
        depth_mm=np.asarray(depth, dtype=np.float64),
        zones=tuple(zones),
        thirds=thirds,
        x_mm=-(relative @ tooth.across),
        y_mm=relative @ tooth.radial,
        e1=e1,
    )


# --- zones ---------------------------------------------------------------------------------------


def zone_results(
    elements: Elements, tooth: Tooth, third: str | None = None
) -> dict[str, fb.ZoneResult]:
    """The zone results in the order of the report; ``third`` restricts to one third of the
    width."""
    zones = np.array(elements.zones)
    thirds = np.array(elements.thirds)
    out: dict[str, fb.ZoneResult] = {}
    for name in fb.ZONE_ORDER:
        mask = zones == name
        if third is not None:
            mask &= thirds == third
        if not mask.any():
            continue
        out[name] = fb.evaluate_zone(
            name,
            elements.tensors[mask],
            elements.volumes[mask],
            elements.a11[mask].tolist(),
            tooth.radial,
            tooth.across,
        )
    return out


# --- figures -------------------------------------------------------------------------------------


def _outline_xy(tooth: Tooth, nodes: Mapping[int, tuple[float, float, float]]) -> Array:
    """The outline of the tooth in the plot frame, from the left valley to the right valley,
    one node per transverse position (the outline repeats per layer)."""
    seen: dict[tuple[float, float], None] = {}
    for label in tooth.outline:
        x, y, _z = nodes[label]
        seen[(round(x, 6), round(y, 6))] = None
    points = np.array(list(seen), dtype=np.float64)
    angle = np.arctan2(points[:, 1], points[:, 0])
    inside = np.abs(_wrapped(angle, tooth.centre_angle_rad)) <= tooth.half_pitch_rad * 1.0001
    points = points[inside]
    order = np.argsort(
        -np.asarray(_wrapped(np.arctan2(points[:, 1], points[:, 0]), tooth.centre_angle_rad))
    )
    points = points[order]
    relative = (
        np.column_stack([points, np.zeros(len(points))]) - tooth.radial * tooth.root_radius_mm
    )
    return np.column_stack([-(relative @ tooth.across), relative @ tooth.radial])


def _depth_contours(axes: Any, outline: Array, skin_mm: float) -> None:
    """The borders of the surface band and the transition band as contours of the distance to
    the outline, plus the root circle, the mid-height line and the tooth axis."""
    x = np.linspace(outline[:, 0].min(), outline[:, 0].max(), 220)
    y = np.linspace(outline[:, 1].min(), outline[:, 1].max(), 220)
    grid_x, grid_y = np.meshgrid(x, y)
    points = np.column_stack([grid_x.ravel(), grid_y.ravel()])
    distance, _ = cKDTree(outline).query(points)
    closed = np.vstack([outline, outline[-1] + [0.0, -5.0], outline[0] + [0.0, -5.0]])
    inside = MplPath(closed).contains_points(points)
    field = np.where(inside, distance, np.nan).reshape(grid_x.shape)
    axes.contour(
        grid_x, grid_y, field, levels=[skin_mm, 2.0 * skin_mm], colors="0.35", linewidths=0.5
    )
    height = outline[:, 1].max()
    for level in (0.0, 0.5 * height):
        axes.axhline(level, color="0.35", linewidth=0.5, linestyle=(0, (2, 2)))
    axes.axvline(0.0, color="0.35", linewidth=0.5, linestyle=(0, (2, 2)))


def _zone_labels(
    axes: Any,
    elements: Elements,
    mask: npt.NDArray[np.bool_],
    text_of: Any,
    *,
    dy: float = 0.0,
    va: str = "center",
) -> None:
    """A label per zone at the zone's centroid in the layer ``mask`` (``dy`` shifts it in
    mm, ``va`` is its vertical anchor)."""
    zones = np.array(elements.zones)
    for name in fb.ZONE_ORDER:
        sel = mask & (zones == name)
        if not sel.any():
            continue
        axes.text(
            float(np.mean(elements.x_mm[sel])),
            float(np.mean(elements.y_mm[sel])) + dy,
            text_of(name),
            fontsize=5.5,
            ha="center",
            va=va,
            color="0.15",
            zorder=3,
            bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.75},
        )


def figure_sections(
    elements: Elements,
    tooth: Tooth,
    nodes: Mapping[int, tuple[float, float, float]],
    skin_mm: float,
    stem: Path,
) -> list[Path]:
    """Two transverse sections (mid-width and the layer at the face): the fibre direction of
    every element as a line, coloured by its orientation state a_11, the zone borders over it."""
    outline = _outline_xy(tooth, nodes)
    z = elements.centroids[:, 2]
    levels = sorted(set(np.round(z, 4)))
    mid = min(levels, key=lambda v: abs(v))
    face = min(levels)
    figure, axes = new_figure("full", 0.52, cols=2, sharey=True)
    scatter = None
    for ax, level, title in zip(axes, (mid, face), ("Zahnmitte", "Stirnseite"), strict=True):
        mask = np.isclose(z, level, atol=1e-4)
        ax.plot(outline[:, 0], outline[:, 1], color="0.15", linewidth=0.8, marker="none")
        length = 0.09
        px = elements.x_mm[mask]
        py = elements.y_mm[mask]
        dx = -(elements.e1[mask] @ tooth.across) * length
        dy = (elements.e1[mask] @ tooth.radial) * length
        colours = elements.a11[mask]
        order = np.argsort(colours)
        segments = np.stack(
            [np.column_stack([px - dx, py - dy]), np.column_stack([px + dx, py + dy])], axis=1
        )[order]
        from matplotlib.collections import LineCollection
        from matplotlib.colors import Normalize

        collection = LineCollection(
            segments.tolist(),
            cmap=DEGREE_COLOURMAP,
            norm=Normalize(1.0 / 3.0, 1.0),
            linewidths=0.7,
        )
        collection.set_array(colours[order])
        ax.add_collection(collection)
        scatter = collection
        _depth_contours(ax, outline, skin_mm)
        _zone_labels(ax, elements, mask, lambda name: name)
        ax.set_title(f"{title}, $z$ = {_g(float(level), 2)} mm")
        ax.set_xlabel("Quer zum Zahn in mm")
        ax.set_aspect("equal")
        ax.set_xlim(outline[:, 0].min() - 0.05, outline[:, 0].max() + 0.05)
        ax.set_ylim(
            min(float(outline[:, 1].min()), float(elements.y_mm[mask].min())) - 0.05,
            outline[:, 1].max() + 0.1,
        )
        decimal_comma(ax)
    axes[0].set_ylabel("Über dem Fußkreis in mm")
    bar = figure.colorbar(scatter, ax=list(axes), pad=0.02, shrink=0.85)
    bar.set_label("Orientierungsgrad $a_{11}$")
    return save_figure(figure, stem)


def figure_zone_map(
    elements: Elements,
    tooth: Tooth,
    nodes: Mapping[int, tuple[float, float, float]],
    results: Mapping[str, fb.ZoneResult],
    skin_mm: float,
    stem: Path,
) -> list[Path]:
    """The zone map with the simulated preferred direction per zone, as Bild 18 prints it."""
    outline = _outline_xy(tooth, nodes)
    z = elements.centroids[:, 2]
    mid = min(sorted(set(np.round(z, 4))), key=lambda v: abs(v))
    mask = np.isclose(z, mid, atol=1e-4)
    figure, axes = new_figure("half", 1.05)
    axes.plot(outline[:, 0], outline[:, 1], color="0.15", linewidth=0.8, marker="none")
    _depth_contours(axes, outline, skin_mm)
    for name, result in results.items():
        sel = mask & (np.array(elements.zones) == name)
        if not sel.any():
            continue
        cx, cy = float(np.mean(elements.x_mm[sel])), float(np.mean(elements.y_mm[sel]))
        theta = math.radians(result.angle_deg)
        dx, dy = -math.sin(theta) * 0.12, math.cos(theta) * 0.12  # positive angle to the left
        axes.plot(
            [cx - dx, cx + dx],
            [cy - dy, cy + dy],
            color=_first_colour(),
            linewidth=1.8,
            marker="none",
            alpha=1.0 if result.in_plane >= 0.5 else 0.35,  # faint: the main axis is axial
            zorder=4,
        )
    # the label below its direction line, so that the line stays visible
    _zone_labels(
        axes,
        elements,
        mask,
        lambda name: f"{name} {_angle_text(results[name])}",
        dy=-0.08,
        va="top",
    )
    axes.set_xlabel("Quer zum Zahn in mm")
    axes.set_ylabel("Über dem Fußkreis in mm")
    axes.set_aspect("equal")
    decimal_comma(axes)
    return save_figure(figure, stem)


def figure_zone_comparison(
    results: Mapping[str, fb.ZoneResult], tooth: Tooth, stem: Path
) -> list[Path]:
    """λ_3 and the anisotropy index per zone: the CT of the report against the simulation."""
    names = [n for n in fb.ZONE_ORDER if n in results]
    x = np.arange(len(names))
    figure, axes = new_figure("full", 0.6, rows=2, sharex=True)
    ct_l3 = [
        fb.FVA856_ZONES[mirrored(n)][2] if mirrored(n) in fb.FVA856_ZONES else np.nan for n in names
    ]
    ct_ai = [
        fb.FVA856_ZONES[mirrored(n)][3] if mirrored(n) in fb.FVA856_ZONES else np.nan for n in names
    ]
    transferred = [n.startswith("R") for n in names]
    for ax, ct, own, label in (
        (axes[0], ct_l3, [results[n].eigenvalues[2] for n in names], "$\\lambda_3$"),
        (axes[1], ct_ai, [results[n].anisotropy_index for n in names], "AI"),
    ):
        ct_arr = np.array(ct, dtype=float)
        direct = ~np.array(transferred)
        # categories on the x axis: no lines, the house markers in their order
        ax.plot(
            x[direct],
            ct_arr[direct],
            linestyle="none",
            marker=MARKERS[0],
            label=f"CT, {SOURCE_LABEL} Bild 17",
        )
        ax.plot(
            x[~direct],
            ct_arr[~direct],
            linestyle="none",
            marker=MARKERS[0],
            markerfacecolor="white",
            label="CT, rechte Zone = linke Zone des Berichts",
        )
        ax.plot(
            x,
            own,
            linestyle="none",
            marker=MARKERS[1],
            label="Simulation (CADMOULD, CONVERSE-Mapping)",
        )
        ax.set_ylabel(label)
        ax.set_ylim(0.0, 1.0)
        decimal_comma(ax, which="y")
    axes[1].set_xticks(x, names, rotation=45, ha="right")
    legend_outside(figure, axes[0], where="bottom", ncol=1)
    return save_figure(figure, stem)


def figure_thirds(
    whole: Mapping[str, fb.ZoneResult],
    per_third: Mapping[str, Mapping[str, fb.ZoneResult]],
    tooth: Tooth,
    stem: Path,
) -> list[Path]:
    """The anisotropy index per zone over the whole width and in its thirds (Bild 23)."""
    names = [n for n in fb.ZONE_ORDER if n in whole]
    x = np.arange(len(names))
    figure, axes = new_figure("full", 0.5)
    offsets = {"z-": -0.22, "mid": 0.0, "z+": 0.22}
    for k, third in enumerate(THIRDS):
        values = [
            per_third[third][n].anisotropy_index if n in per_third[third] else np.nan for n in names
        ]
        axes.plot(
            x + offsets[third],
            values,
            linestyle="none",
            marker=MARKERS[k],
            label=THIRD_LABELS[third],
        )
    axes.plot(
        x,
        [whole[n].anisotropy_index for n in names],
        linestyle="none",
        marker="_",
        markersize=12,
        label="ganze Zahnbreite",
    )
    axes.set_xticks(x, names, rotation=45, ha="right")
    axes.set_ylabel("AI")
    axes.set_ylim(0.0, 1.0)
    decimal_comma(axes, which="y")
    legend_outside(figure, axes, where="bottom", ncol=2)
    return save_figure(figure, stem)


def figure_width(elements: Elements, tooth: Tooth, stem: Path) -> list[Path]:
    """a_11 of the elements in the axial plane through the tooth axis (|x| small): the skin
    at the faces and the core over the width."""
    mask = np.abs(elements.x_mm) <= 0.2
    figure, axes = new_figure("full", 0.4)
    scatter = axes.scatter(
        elements.centroids[mask, 2],
        elements.y_mm[mask],
        c=elements.a11[mask],
        s=6,
        cmap=DEGREE_COLOURMAP,
        vmin=1.0 / 3.0,
        vmax=1.0,
        marker="s",
        linewidths=0,
    )
    bar = figure.colorbar(scatter, ax=axes, pad=0.02)
    bar.set_label("$a_{11}$")
    axes.set_xlabel("$z$ in mm")
    axes.set_ylabel("Über dem Fußkreis in mm")
    decimal_comma(axes)
    return save_figure(figure, stem)


# --- report --------------------------------------------------------------------------------------


def write_report(
    out: Path,
    tooth: Tooth,
    elements: Elements,
    whole: Mapping[str, fb.ZoneResult],
    per_third: Mapping[str, Mapping[str, fb.ZoneResult]],
    inputs: Mapping[str, str],
    skin_mm: float,
    pictures: Mapping[str, Sequence[Path]],
) -> None:
    names = [n for n in fb.ZONE_ORDER if n in whole]
    with (out / "zonen.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "zone",
                "elements",
                "volume_mm3",
                "lambda_1",
                "lambda_2",
                "lambda_3",
                "AI",
                "angle_deg",
                "in_plane",
                "a11_mean",
                "ct_lambda_1",
                "ct_lambda_2",
                "ct_lambda_3",
                "ct_AI",
                "ct_zone",
                "ct_angle_deg",
            ]
        )
        for n in names:
            r = whole[n]
            ct = fb.FVA856_ZONES.get(mirrored(n))
            angle = reference_angle(n)
            writer.writerow(
                [
                    n,
                    r.elements,
                    f"{r.volume_mm3:.6g}",
                    *(f"{v:.6f}" for v in r.eigenvalues),
                    f"{r.anisotropy_index:.6f}",
                    f"{r.angle_deg:.3f}",
                    f"{r.in_plane:.4f}",
                    f"{r.a11_mean:.6f}",
                    *((f"{v:.2f}" for v in ct) if ct else ("", "", "", "")),
                    mirrored(n) if ct else "",
                    f"{angle:.1f}" if angle is not None else "",
                ]
            )
    with (out / "drittel.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["zone", "third", "elements", "lambda_3", "AI", "angle_deg", "in_plane", "tilt_deg"]
        )
        for n in names:
            for third in THIRDS:
                if n in per_third[third]:
                    r = per_third[third][n]
                    writer.writerow(
                        [
                            n,
                            third,
                            r.elements,
                            f"{r.eigenvalues[2]:.6f}",
                            f"{r.anisotropy_index:.6f}",
                            f"{r.angle_deg:.3f}",
                            f"{r.in_plane:.4f}",
                            f"{r.tilt_deg:.3f}",
                        ]
                    )

    doc = [f"# Faserorientierung der Spritzgusssimulation am Zahn {tooth.name}", ""]
    doc.append(
        f"Orientierung aus {inputs['cof']} (CONVERSE-Mapping der CADMOULD-Rechnung auf das Netz "
        f"{inputs['mesh']}), Karte {inputs['card']}; je Element der Orientierungstensor aus dem "
        "lokalen Faserrahmen und den Eigenwerten a_11, a_22 der Knoten (Mittel über die Knoten des "
        "Elements), je Zone das volumengewichtete Mittel der Elementtensoren, daraus die Eigenwerte "
        "λ_1 ≤ λ_2 ≤ λ_3, der Anisotropie-Index AI = 1 − λ_1/λ_3 und die Vorzugsrichtung in der "
        f"Stirnebene (0° Zahnachse, 90° quer, positiv nach links wie der Pfeil in Bild 18 von {SOURCE_LABEL})."
    )
    doc.append("")
    doc.append(
        f"Zahn {tooth.name}: Fußkreis r {_g(tooth.root_radius_mm, 3)} mm, Kopfkreis r "
        f"{_g(tooth.tip_radius_mm, 3)} mm, Zahnhöhe {_g(tooth.height_mm, 3)} mm, halbe Teilung "
        f"{_g(math.degrees(tooth.half_pitch_rad), 3)}°, Zahnbreite {_g(2 * tooth.half_width_mm, 1)} mm; "
        f"{elements.labels.size} Elemente innerhalb der Teilung ab r "
        f"{_g(tooth.root_radius_mm - inputs_below(inputs), 2)} mm. "
        f"Zonen wie Bild 17 des Berichts: Randstreifen bis {_g(skin_mm, 2)} mm unter der Kontur, "
        f"Übergangsstreifen bis {_g(2 * skin_mm, 2)} mm, darunter Kern M (über dem Fußkreis) und U "
        "(unter dem Fußkreis); Flanke unten/oben an der halben Zahnhöhe geteilt; die Tiefe ist der Abstand "
        "des Elementschwerpunkts zur Kontur in der Stirnebene."
    )
    doc.append("")
    doc.extend([f"## 1 Zonen gegen die CT-Zonen von {SOURCE_LABEL} (Bild 17, S. 19)", ""])
    doc.append(
        "Die rechten Zonen des Berichts sind dort nicht gedruckt („nahezu gleich zu denen der linken "
        "Zonen“); für R-Zonen steht die linke Zone des Berichts daneben."
    )
    doc.append("")
    rows = []
    for n in names:
        r = whole[n]
        ct = fb.FVA856_ZONES.get(mirrored(n))
        rows.append(
            [
                n,
                str(r.elements),
                _g(r.eigenvalues[0]),
                _g(r.eigenvalues[1]),
                _g(r.eigenvalues[2]),
                _g(r.anisotropy_index),
                *(_g(v) for v in r.diagonal),
                *((_g(ct[0]), _g(ct[1]), _g(ct[2]), _g(ct[3])) if ct else ("–", "–", "–", "–")),
                _g(r.anisotropy_index - ct[3], 2) if ct else "–",
            ]
        )
    doc.extend(
        _table(
            [
                "Zone",
                "Elemente",
                "λ1",
                "λ2",
                "λ3",
                "AI",
                "A_rr (Zahnachse)",
                "A_tt (quer)",
                "A_zz (Zahnbreite)",
                "CT λ1",
                "CT λ2",
                "CT λ3",
                "CT AI",
                "ΔAI (Sim − CT)",
            ],
            rows,
        )
    )
    doc.append("")
    doc.append(
        "A_rr, A_tt, A_zz sind die Diagonalglieder des Zonentensors im Zahnsystem (Zahnachse, quer "
        "zum Zahn, Zahnbreite; je 1/3 bei Isotropie). Das Zonenmittel über die ganze Zahnbreite "
        "unterschätzt die örtliche Orientierung, wo die Faserachse zu den beiden Stirnseiten hin "
        "aus der Stirnebene kippt (symmetrisch zur Zahnmitte): die Drittel in Abschnitt 3 zeigen "
        "die örtliche Ausprägung."
    )
    doc.append("")
    doc.extend(
        [f"## 2 Vorzugsrichtung in der Stirnebene gegen Bild 18 ({SOURCE_LABEL}, S. 19)", ""]
    )
    doc.append(
        "Winkel der Hauptachse des Zonentensors in der Stirnebene (Anteil in der Ebene daneben: 1 = "
        "Faser liegt in der Stirnebene); der Bericht fasst die drei Übergangszonen einer Seite zusammen."
    )
    doc.append("")
    rows = []
    for n in names:
        r = whole[n]
        angle = reference_angle(n)
        rows.append(
            [
                n,
                _angle_text(r),
                _g(r.in_plane, 2),
                _g(r.tilt_deg, 1),
                _g(angle, 1) if angle is not None else "–",
                _g(r.a11_mean),
            ]
        )
    doc.extend(
        _table(
            [
                "Zone",
                "Winkel Sim",
                "Anteil in der Ebene",
                "Neigung aus der Ebene in °",
                "Winkel Bild 18 in °",
                "a11 Mittel der Elemente",
            ],
            rows,
        )
    )
    doc.append("")
    doc.append(
        "„a11 Mittel der Elemente“ ist der volumengewichtete Mittelwert des größten Eigenwerts der "
        "einzelnen Elemente, die örtliche Ausprägung der Orientierung; „Neigung“ der Winkel der "
        "Hauptachse gegen die Stirnebene (positiv zu +z)."
    )
    doc.append("")
    doc.extend([f"## 3 Drittel der Zahnbreite ({SOURCE_LABEL}, Bild 23, S. 24)", ""])
    doc.append(
        "Der Bericht findet im mittleren Drittel der Außen- und Übergangszonen einen 5 bis 15 % "
        "(Außenzonen) bzw. bis 20 % (Übergangszonen) geringeren Modul E1 und einen geringeren größten "
        "Eigenwert; hier λ3 und AI je Drittel, das mittlere Drittel gegen das Mittel der äußeren."
    )
    doc.append("")
    rows = []
    for n in names:
        values: list[fb.ZoneResult | None] = [per_third[third].get(n) for third in THIRDS]
        outer = [r.eigenvalues[2] for r in (values[0], values[2]) if r is not None]
        middle = values[1].eigenvalues[2] if values[1] is not None else None
        drop = (middle / float(np.mean(outer)) - 1.0) if outer and middle is not None else None
        rows.append(
            [
                n,
                *(_g(r.eigenvalues[2]) if r is not None else "–" for r in values),
                *(_g(r.anisotropy_index) if r is not None else "–" for r in values),
                f"{_g(drop * 100.0, 1)} %" if drop is not None else "–",
                *(_angle_text(r) if r is not None else "–" for r in values),
                *(_g(r.tilt_deg, 1) if r is not None else "–" for r in values),
            ]
        )
    doc.extend(
        _table(
            [
                "Zone",
                "λ3 z−",
                "λ3 mitte",
                "λ3 z+",
                "AI z−",
                "AI mitte",
                "AI z+",
                "λ3 mitte gegen außen",
                "Winkel z−",
                "Winkel mitte",
                "Winkel z+",
                "Neigung z− in °",
                "Neigung mitte in °",
                "Neigung z+ in °",
            ],
            rows,
        )
    )
    doc.append("")
    doc.append(
        "Eine Neigung, die im Drittel z− negativ und im Drittel z+ positiv ist, heißt: die Faserachse "
        "kippt zur jeweils näheren Stirnseite; über die ganze Breite gemittelt heben sich die "
        "Nebendiagonalglieder auf, und das Zonenmittel in Abschnitt 1 wird isotroper, als die Elemente sind."
    )
    doc.append("")
    doc.extend(["## 4 Bilder", ""])
    for key, paths in pictures.items():
        doc.append(f"- {key}: " + ", ".join(p.name for p in paths))
    doc.append("")
    (out / "bericht.md").write_text("\n".join(doc), encoding="utf-8")

    captions = [
        "# Bildunterschriften",
        "",
        "- `schnitt_<Zahn>`: "
        + caption(
            f"Faserrichtung je Element in zwei Stirnschnitten des Zahns {tooth.name} (Zahnmitte und Stirnseite), "
            "Linienrichtung = Hauptachse der Faserorientierung, Farbe = Orientierungsgrad a_11; Zonen und "
            f"Streifen ({_g(skin_mm, 2)} mm) wie Bild 17",
            source=SOURCE_LABEL,
            relation="in Anlehnung an",
            page="17 und 19",
        ),
        "- `zonen_<Zahn>`: "
        + caption(
            f"Zonen des Zahns {tooth.name} mit der Vorzugsrichtung der Simulation in der Stirnebene",
            source=SOURCE_LABEL,
            relation="in Anlehnung an",
            page="19",
        ),
        "- `vergleich_<Zahn>`: "
        + caption(
            "Größter Eigenwert und Anisotropie-Index je Zone: CT-Messung des Forschungsvorhabens "
            "gegen die Spritzgusssimulation (CADMOULD, CONVERSE-Mapping)",
            source=SOURCE_LABEL,
            relation="nach",
            page="19",
        ),
        "- `drittel_<Zahn>`: "
        + caption(
            "Anisotropie-Index je Zone über die ganze Zahnbreite und in den Dritteln der Zahnbreite",
            source=SOURCE_LABEL,
            relation="in Anlehnung an",
            page="24",
        ),
        "- `breite_<Zahn>`: Orientierungsgrad a_11 in der Ebene der Zahnachse über der Zahnbreite "
        "(Randschicht an den Stirnflächen, Kern).",
        "",
    ]
    (out / "bildunterschriften.md").write_text("\n".join(captions), encoding="utf-8")


def inputs_below(inputs: Mapping[str, str]) -> float:
    return float(inputs["below_mm"])


# --- main ----------------------------------------------------------------------------------------


def run(
    mesh: Path, cof: Path, tooth_name: str, skin_mm: float, below_mm: float, out: Path
) -> list[str]:
    text = mesh.read_text(encoding="ascii", errors="replace")
    nodes = dk.read_node_coordinates(text)
    connectivity = dk.read_element_connectivity(text)
    node_sets, _element_sets = dk.read_sets(text)
    cof_text = cof.read_text(encoding="utf-8", errors="replace")
    orientation = dk.read_distribution(cof_text)
    states = dk.read_field_variables(cof_text)
    fit = dk.verify_orientation_file(
        cof_text,
        element_labels=tuple(sorted(connectivity)),
        node_labels=dk.read_node_labels(text),
        name=cof.name,
    )
    card = next(
        (line for line in cof_text.splitlines() if line.upper().startswith("*MATERIAL")), ""
    )
    tooth = tooth_geometry(tooth_name, nodes, node_sets)
    elements = tooth_elements(tooth, nodes, connectivity, orientation, states, skin_mm, below_mm)
    whole = zone_results(elements, tooth)
    per_third = {third: zone_results(elements, tooth, third) for third in THIRDS}
    out.mkdir(parents=True, exist_ok=True)
    pictures = {
        "schnitt": figure_sections(elements, tooth, nodes, skin_mm, out / f"schnitt_{tooth_name}"),
        "zonen": figure_zone_map(
            elements, tooth, nodes, whole, skin_mm, out / f"zonen_{tooth_name}"
        ),
        "vergleich": figure_zone_comparison(whole, tooth, out / f"vergleich_{tooth_name}"),
        "drittel": figure_thirds(whole, per_third, tooth, out / f"drittel_{tooth_name}"),
        "breite": figure_width(elements, tooth, out / f"breite_{tooth_name}"),
    }
    inputs = {
        "mesh": str(mesh.relative_to(REPO)) if mesh.is_relative_to(REPO) else str(mesh),
        "cof": str(cof.relative_to(REPO)) if cof.is_relative_to(REPO) else str(cof),
        "card": card[card.upper().index("NAME=") + 5 :].strip()
        if "NAME=" in card.upper()
        else card,
        "below_mm": repr(below_mm),
    }
    write_report(out, tooth, elements, whole, per_third, inputs, skin_mm, pictures)
    lines = [
        f"{tooth_name}: {elements.labels.size} elements, {len(whole)} zones; orientation file "
        f"{fit.elements} elements / {fit.nodes} nodes as the mesh",
    ]
    for name in fb.ZONE_ORDER:
        if name in whole:
            r = whole[name]
            ct = fb.FVA856_ZONES.get(mirrored(name))
            lines.append(
                f"  {name:4s} n {r.elements:5d}  λ3 {r.eigenvalues[2]:.3f}  AI {r.anisotropy_index:.3f}"
                + (f"  (CT λ3 {ct[2]:.2f}, AI {ct[3]:.2f})" if ct else "")
                + f"  angle {r.angle_deg:+6.1f}°, in plane {r.in_plane:.2f}, "
                f"A_rr/tt/zz {r.diagonal[0]:.2f}/{r.diagonal[1]:.2f}/{r.diagonal[2]:.2f}, "
                f"a11 mean {r.a11_mean:.2f}"
            )
    lines.append(str(out / "bericht.md"))
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--mesh", type=Path, required=True, help="wheel mesh (.inp) the orientation file belongs to"
    )
    parser.add_argument(
        "--cof", type=Path, required=True, help="CONVERSE orientation file (.cof) of that mesh"
    )
    parser.add_argument(
        "--tooth", default="T3", help="tooth to evaluate (default T3, the middle tooth)"
    )
    parser.add_argument(
        "--skin",
        type=float,
        default=0.2,
        help="depth of the surface band in mm (the transition band is as deep again)",
    )
    parser.add_argument(
        "--below",
        type=float,
        default=1.0,
        help="how far below the root circle the zone U reaches, in mm",
    )
    parser.add_argument("--out", type=Path, default=REPO / "80_output" / "fe" / "faserorientierung")
    args = parser.parse_args(argv)
    if not args.skin > 0.0 or not args.below >= 0.0:
        raise InputRangeError("--skin must be positive and --below not negative")
    for line in run(
        args.mesh.resolve(),
        args.cof.resolve(),
        args.tooth,
        args.skin,
        args.below,
        args.out.resolve(),
    ):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
