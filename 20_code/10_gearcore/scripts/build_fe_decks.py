"""Build the finite element model of a gear pair: previews of the positions and the mesh files
(decks follow).

    python scripts/build_fe_decks.py mesh --case kst_e --teeth 5 --rim-rings 12 --layers 80
    python scripts/build_fe_decks.py mesh --case kst_e --teeth 5 --layers 80 \
        --over-tooth-height 18 --at-tip-edge-break 2 --at-tooth-root 80 \
        --over-tooth-thickness 20 --root-layers 6 --rings 12 --shoulder-columns 4
    python scripts/build_fe_decks.py preview --case kst_e
    python scripts/build_fe_decks.py preview --case kst_e --pinion-rotation counterclockwise

The pinion drives. Its sense of rotation is the one seen in the pictures (pinion on the left,
wheel on the right); the preset is clockwise, as on the test rig, where the wheel then turns
counter-clockwise and the torque on the pinion is negative about +z.

``preview`` draws the transverse section of the pair in five positions, from half a base pitch
before the start A of the path of contact to half a base pitch after its end E, and writes the
distances of the working flanks and of the back flanks into each picture. The pictures go to
``80_output/fe/<case>/preview`` (not under version control).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from gearcore import contour as ct
from gearcore import data
from gearcore import involute as iv
from gearcore._safe import integer_input
from gearcore.errors import InputRangeError
from gearcore.fe import abaqus as ab
from gearcore.fe import body as bd
from gearcore.fe import convergence as cv
from gearcore.fe import deck as dk
from gearcore.fe import evaluation as ev
from gearcore.fe import placement as pl
from gearcore.fe import refine as rf
from gearcore.fe import resample as rs
from gearcore.fe import rigid_surface as rsf
from gearcore.fe import sector_mesh as sm
from gearcore.fe import solid as so
from gearcore.generation import compute_generation
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.results import GenerationResult

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT = REPO_ROOT / "80_output" / "fe"

PINION_COLOUR = "#5b6f85"
WHEEL_COLOUR = "#d98c3f"
LINE_COLOUR = "#1f1f1f"


def _generation(case: str) -> GenerationResult:
    return compute_generation(pair_input_from_ste(load_ste(data.stplus_input_path(case))).pair)


def _number(value: float, digits: int) -> str:
    """A number with a decimal comma, as the pictures are labelled in German."""
    return f"{value:.{digits}f}".replace(".", ",")


def _preview_positions(generation: GenerationResult) -> list[tuple[str, float]]:
    rho_a, rho_e = pl.path_of_contact_limits(generation)
    half = 0.5 * generation.pair_geometry.transverse_base_pitch_mm
    return [
        ("halbe Eingriffsteilung vor A", rho_a - half),
        ("Eingriffsbeginn A", rho_a),
        ("Mitte der Eingriffsstrecke", 0.5 * (rho_a + rho_e)),
        ("Eingriffsende E", rho_e),
        ("halbe Eingriffsteilung nach E", rho_e + half),
    ]


def _draw_pair(
    axes: Axes,
    generation: GenerationResult,
    position: pl.MeshPosition,
    polygons: tuple[np.ndarray, np.ndarray],
) -> None:
    place = pl.fixed_axes(position)
    for polygon, axis, angle, colour in (
        (polygons[0], place.axis_mm.pinion, place.tooth_centre_angle_deg.pinion, PINION_COLOUR),
        (polygons[1], place.axis_mm.wheel, place.tooth_centre_angle_deg.wheel, WHEEL_COLOUR),
    ):
        outline = pl.placed(polygon, axis, angle)
        axes.fill(outline[:, 0], outline[:, 1], facecolor=colour, alpha=0.35, linewidth=0.0)
        # the outline as one closed path, so that it has no line ends
        axes.fill(outline[:, 0], outline[:, 1], facecolor="none", edgecolor=colour, linewidth=0.9)
    # line of action through the contact point of the followed pair
    alpha_wt = math.radians(generation.pair_geometry.transverse_working_pressure_angle_deg)
    side = 1.0 if position.working_flank == "left" else -1.0
    direction = np.array([math.sin(alpha_wt), side * math.cos(alpha_wt)])
    contact = np.asarray(position.contact_point_mm)
    rho_1 = position.radius_of_curvature_mm.pinion
    rho_a, rho_e = pl.path_of_contact_limits(generation)
    start, end = contact + (rho_a - rho_1) * direction, contact + (rho_e - rho_1) * direction
    axes.plot(
        [start[0], end[0]], [start[1], end[1]], color=LINE_COLOUR, linewidth=0.8, linestyle="--"
    )
    for label, point in (("A", start), ("E", end)):
        axes.plot(*point, marker="|", color=LINE_COLOUR, markersize=7)
        axes.annotate(
            label,
            (float(point[0]), float(point[1])),
            textcoords="offset points",
            xytext=(6, -3),
            fontsize=8,
        )
    p_bt = generation.pair_geometry.transverse_base_pitch_mm
    sign = 1 if position.working_flank == "left" else -1
    for k in position.tooth_pairs_on_path:
        point = contact + sign * k * p_bt * direction
        axes.plot(*point, marker="o", color="#c0392b", markersize=3.5)
    axes.set_aspect("equal")
    axes.tick_params(labelsize=7)


def preview(case: str, rotation: pl.Rotation, out: Path) -> list[Path]:
    generation = _generation(case)
    flank = pl.working_flank_of_the_driving_pinion(rotation)
    clockwise = rotation == "clockwise"
    senses = ("im Uhrzeigersinn", "gegen den Uhrzeigersinn")
    pinion_sense, wheel_sense = senses if clockwise else senses[::-1]
    torque = "negativ" if pl.pinion_torque_sign(flank) < 0.0 else "positiv"
    geometry = generation.pair_geometry
    polygons = (
        ct.gear_polygon(ct.tooth_contour(generation, "pinion", points=80)),
        ct.gear_polygon(ct.tooth_contour(generation, "wheel", points=80)),
    )
    rho_a, _ = pl.path_of_contact_limits(generation)
    back = pl.back_flank_distance(generation)
    module = generation.inputs.normal_module_mm
    pitch_point = 0.5 * geometry.working_pitch_diameter_mm.pinion
    other: pl.Flank = "right" if flank == "left" else "left"
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for index, (label, rho_1) in enumerate(_preview_positions(generation), start=1):
        position = pl.mesh_position(generation, rho_1, working_flank=flank)
        working = max(
            abs(pl.flank_distance(generation, position, flank, pinion_tooth=k, wheel_tooth=-k))
            for k in position.tooth_pairs_on_path
        )
        step = 1 if flank == "left" else -1
        back_here = pl.flank_distance(generation, position, other, pinion_tooth=step)
        figure, (overview, detail) = plt.subplots(1, 2, figsize=(11.0, 5.2), dpi=160)
        for axes in (overview, detail):
            _draw_pair(axes, generation, position, polygons)
        overview.set_xlim(pitch_point - 5.0 * module, pitch_point + 5.0 * module)
        overview.set_ylim(-6.0 * module, 6.0 * module)
        overview.set_title("Eingriff", fontsize=9)
        box = {"facecolor": "white", "alpha": 0.85, "edgecolor": "none", "pad": 2.0}
        overview.text(
            0.03,
            0.97,
            f"Ritzel (treibt): {pinion_sense}" + chr(10) + f"Moment um +z {torque}",
            transform=overview.transAxes,
            ha="left",
            va="top",
            fontsize=7,
            bbox=box,
        )
        overview.text(
            0.97,
            0.03,
            f"Rad: {wheel_sense}",
            transform=overview.transAxes,
            ha="right",
            va="bottom",
            fontsize=7,
            bbox=box,
        )
        overview.set_xlabel("x in mm", fontsize=8)
        overview.set_ylabel("y in mm", fontsize=8)
        centre = np.asarray(position.contact_point_mm)
        k = position.tooth_pairs_on_path[0]
        alpha_wt = math.radians(geometry.transverse_working_pressure_angle_deg)
        side = 1.0 if flank == "left" else -1.0
        centre = centre + step * k * geometry.transverse_base_pitch_mm * np.array(
            [math.sin(alpha_wt), side * math.cos(alpha_wt)]
        )
        detail.set_xlim(centre[0] - 0.6 * module, centre[0] + 0.6 * module)
        detail.set_ylim(centre[1] - 0.6 * module, centre[1] + 0.6 * module)
        detail.set_title("Berührpunkt des tragenden Zahnpaars", fontsize=9)
        detail.set_xlabel("x in mm", fontsize=8)
        detail.set_ylabel("y in mm", fontsize=8)
        pairs = ", ".join(str(k) for k in position.tooth_pairs_on_path)
        figure.suptitle(
            f"{case}: {label} (Stellung {index} von 5, Wälzweg ab A = "
            f"{_number(rho_1 - rho_a, 3)} mm)",
            fontsize=10,
        )
        figure.text(
            0.5,
            0.02,
            f"Arbeitsflanke ({'links' if flank == 'left' else 'rechts'}): Abstand "
            f"{_number(1000.0 * working, 6)} µm   |   Rückflanke: Abstand "
            f"{_number(1000.0 * back_here, 1)} µm (Sollwert {_number(1000.0 * back, 1)} µm)"
            f"   |   Zahnpaare auf der Eingriffsstrecke: {pairs}",
            ha="center",
            fontsize=8,
        )
        figure.tight_layout(rect=(0.0, 0.05, 1.0, 0.95))
        target = out / f"position_{index}.png"
        figure.savefig(target)
        plt.close(figure)
        written.append(target)
    return written


def _draw_quads(
    axes: Axes,
    points: np.ndarray,
    quads: np.ndarray,
    *,
    face: str = "none",
    edge: str = "#3a3a3a",
    width: float = 0.25,
) -> None:
    axes.add_collection(
        PolyCollection(points[quads], facecolors=face, edgecolors=edge, linewidths=width)
    )


def _mesh_pictures(
    section: sm.SectorMesh, solid: so.SolidMesh, sets: so.GearSets, out: Path
) -> None:
    points = section.points_mm
    m = len(section.quads)
    middle = (section.teeth + 1) // 2
    module_mm = (section.tip_radius_mm - section.root_radius_mm) / 2.25
    name = f"{sets.prefix}_T{middle}"

    def quads_of(element_set: str) -> np.ndarray:
        elements = sets.element_sets[element_set]
        return section.quads[elements[elements < m]]

    def nodes_of(node_set: str) -> np.ndarray:
        nodes = sets.node_sets[node_set]
        return points[nodes[nodes < len(points)]]

    # 1 the whole sector with the tooth numbers and the fixed nodes
    figure, axes = plt.subplots(figsize=(11.0, 6.0), dpi=160)
    _draw_quads(axes, points, section.quads, width=0.2)
    fixed = nodes_of(f"{sets.prefix}_FESSELUNG")
    axes.plot(fixed[:, 0], fixed[:, 1], ".", color="#c0392b", markersize=2.5, label="Fesselung")
    for tooth in range(1, section.teeth + 1):
        angle = 0.5 * math.pi + (tooth - 0.5 * (section.teeth + 1)) * section.pitch_angle_rad
        radius = section.tip_radius_mm + 0.6 * module_mm
        axes.text(
            radius * math.cos(angle),
            radius * math.sin(angle),
            f"T{tooth}",
            ha="center",
            va="center",
            fontsize=8,
        )
    axes.set_aspect("equal")
    axes.autoscale_view()
    axes.margins(0.03)
    # room above the teeth for their numbers
    axes.set_ylim(top=section.tip_radius_mm + 1.6 * module_mm)
    axes.legend(loc="lower center", fontsize=8, frameon=False)
    axes.set_title(
        f"Radsektor: {section.teeth} Zähne + 2 zahnlose Segmente, {len(points)} Knoten und "
        f"{m} Elemente je Schicht, Bohrungsradius {_number(section.bore_radius_mm, 2)} mm",
        fontsize=9,
    )
    axes.set_xlabel("x in mm", fontsize=8)
    axes.set_ylabel("y in mm", fontsize=8)
    axes.tick_params(labelsize=7)
    figure.tight_layout()
    figure.savefig(out / "mesh_sector.png")
    plt.close(figure)

    # 2 one tooth, 3 its root on the right side
    root_nodes = nodes_of(f"{name}_RIGHT_SURF_ROOT_NODES")
    root_centre = root_nodes.mean(axis=0)
    windows = (
        (
            "mesh_tooth.png",
            f"Zahn T{middle}",
            (-1.9 * module_mm, 1.9 * module_mm),
            (section.fan_ring_radius_mm - 0.5 * module_mm, section.tip_radius_mm + 0.3 * module_mm),
        ),
        (
            "mesh_root.png",
            f"Zahnfuß von T{middle}, rechte Seite",
            (root_centre[0] - 0.45 * module_mm, root_centre[0] + 0.45 * module_mm),
            (root_centre[1] - 0.35 * module_mm, root_centre[1] + 0.35 * module_mm),
        ),
    )
    for file_name, title, x_limits, y_limits in windows:
        figure, axes = plt.subplots(figsize=(8.0, 6.4), dpi=160)
        _draw_quads(axes, points, section.quads, width=0.3)
        axes.set_xlim(*x_limits)
        axes.set_ylim(*y_limits)
        axes.set_aspect("equal")
        axes.set_title(title, fontsize=9)
        axes.set_xlabel("x in mm", fontsize=8)
        axes.set_ylabel("y in mm", fontsize=8)
        axes.tick_params(labelsize=7)
        figure.tight_layout()
        figure.savefig(out / file_name)
        plt.close(figure)

    def _background(axes: Axes) -> None:
        _draw_quads(axes, points, quads_of(f"{sets.prefix}_RIM"), face="#e6e6e6", edge="#b0b0b0")
        _draw_quads(
            axes, points, quads_of(f"{sets.prefix}_TOOTH_ZONE"), face="#f7f7f7", edge="#c8c8c8"
        )
        axes.set_xlim(-2.2 * module_mm, 2.2 * module_mm)
        axes.set_ylim(
            section.fan_ring_radius_mm - 1.2 * module_mm, section.tip_radius_mm + 0.5 * module_mm
        )
        axes.set_aspect("equal")
        axes.set_xlabel("x in mm", fontsize=8)
        axes.set_ylabel("y in mm", fontsize=8)
        axes.tick_params(labelsize=7)

    # 4 the element sets around one tooth: by half, and by root and head
    figure, (by_half, by_zone) = plt.subplots(1, 2, figsize=(15.0, 7.2), dpi=160)
    for axes in (by_half, by_zone):
        _background(axes)
    fills = (("LEFT", "#a9c8e8", "#3f7fbf"), ("RIGHT", "#f3c9a0", "#d9822b"))
    handles: list[Artist] = []
    for side, light, dark in fills:
        _draw_quads(by_half, points, quads_of(f"{name}_{side}_HALF"), face=light, edge="#8a8a8a")
        _draw_quads(by_half, points, quads_of(f"{name}_{side}_LAYER1"), face=dark, edge=dark)
        handles.append(Patch(facecolor=light, edgecolor="#8a8a8a", label=f"{name}_{side}_HALF"))
        handles.append(Patch(facecolor=dark, edgecolor=dark, label=f"{name}_{side}_LAYER1"))
    by_half.legend(handles=handles, loc="upper left", fontsize=6.5, frameon=True)
    by_half.set_title("Elementsets je Zahnhälfte", fontsize=9)
    zones = [(f"{sets.prefix}_HEAD_T{middle}", "#b7dfb9", "#2e8b57")]
    if middle > 1:
        zones.append((f"{sets.prefix}_ROOT_T{middle - 1}_T{middle}", "#f5b7b1", "#c0392b"))
    if middle < section.teeth:
        zones.append((f"{sets.prefix}_ROOT_T{middle}_T{middle + 1}", "#d7bde2", "#7d3c98"))
    handles = []
    for zone, light, dark in zones:
        _draw_quads(by_zone, points, quads_of(zone), face=light, edge="#8a8a8a")
        _draw_quads(by_zone, points, quads_of(f"{zone}_LAYER1"), face=dark, edge=dark)
        handles.append(Patch(facecolor=light, edgecolor="#8a8a8a", label=zone))
        handles.append(Patch(facecolor=dark, edgecolor=dark, label=f"{zone}_LAYER1"))
    by_zone.legend(handles=handles, loc="upper left", fontsize=6.5, frameon=True)
    by_zone.set_title("Elementsets Fuß je Zahnlücke und Kopf je Zahn", fontsize=9)

    figure.suptitle(
        f"Elementsets um Zahn T{middle} (für alle Zähne und Zahnlücken des Sektors gleich aufgebaut)",
        fontsize=10,
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))
    figure.savefig(out / "mesh_sets.png")
    plt.close(figure)

    # 5 the surface sets around one tooth: one panel per group of sets that divides the surface
    def faces_of(surface_name: str) -> list[np.ndarray]:
        """The faces of a surface in the first layer as segments of the contour."""
        rows = sets.surfaces[surface_name]
        rows = rows[rows[:, 0] < m]
        corners = section.quads[rows[:, 0]]
        edge = rows[:, 1] - so.FIRST_SIDE_FACE
        index = np.arange(len(rows))
        first, second = points[corners[index, edge]], points[corners[index, (edge + 1) % 4]]
        return list(np.stack((first, second), axis=1))

    groups: list[tuple[str, list[tuple[str, str]]]] = [
        ("Ganze Zahnoberfläche (Kontaktfläche)", [(f"{sets.prefix}_TEETH_SURF", "#444444")]),
        ("Je Zahnhälfte", [(f"{name}_{side}_SURF", dark) for side, _, dark in fills]),
        (
            "Je Zahnhälfte geteilt an Fußformkreis und Kopfformkreis",
            [
                (f"{name}_{side}_SURF_{part}", colour)
                for part, colours in (
                    ("ROOT", ("#c0392b", "#f1948a")),
                    ("FLANK", ("#1e8449", "#7dcea0")),
                    ("TIP", ("#6c3483", "#bb8fce")),
                )
                for (side, _, _), colour in zip(fills, colours, strict=True)
            ],
        ),
        ("Kopf je Zahn und Fuß je Zahnlücke", [(f"{zone}_SURF", dark) for zone, _, dark in zones]),
    ]
    figure, panels = plt.subplots(2, 2, figsize=(15.0, 13.5), dpi=150)
    for axes, (title, members) in zip(panels.ravel(), groups, strict=True):
        _background(axes)
        handles = []
        for surface_name, colour in members:
            axes.add_collection(
                LineCollection(faces_of(surface_name), colors=colour, linewidths=3.0)
            )
            handles.append(Line2D([], [], color=colour, linewidth=3.0, label=surface_name))
        axes.legend(handles=handles, loc="lower center", fontsize=7, frameon=True)
        axes.set_title(title, fontsize=9)
    figure.suptitle(
        f"Oberflächensets um Zahn T{middle}; zu jedem Set gibt es das Knotenset mit der Endung "
        "_NODES (für alle Zähne und Zahnlücken gleich aufgebaut)",
        fontsize=10,
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.97))
    figure.savefig(out / "mesh_surfaces.png")
    plt.close(figure)
    del solid


def _set_list(written: str, sets: so.GearSets) -> str:
    """The sets as the written mesh file names them, with their sizes. The names are read back
    from the text of the file and must be the sets the pictures are drawn from."""
    in_file: dict[str, list[str]] = {"*NSET": [], "*ELSET": [], "*SURFACE": []}
    for line in written.splitlines():
        if line.startswith("*") and not line.startswith("**"):
            keyword, _, rest = line.partition(",")
            if keyword in in_file:
                in_file[keyword].append(rest.rsplit("=", 1)[1].strip())
            elif keyword in ("*NODE", "*ELEMENT"):
                key = "*NSET" if keyword == "*NODE" else "*ELSET"
                in_file[key].append(rest.rsplit("=", 1)[1].strip())
    expected = {
        "*NSET": sets.node_sets,
        "*ELSET": sets.element_sets,
        "*SURFACE": sets.surfaces,
    }
    lines = []
    titles = {"*NSET": "node sets", "*ELSET": "element sets", "*SURFACE": "surfaces (faces)"}
    for keyword, names in in_file.items():
        if sorted(names) != sorted(expected[keyword]):
            raise SystemExit(f"the {titles[keyword]} of the file are not those of the model")
        lines.append(f"{titles[keyword]}: {len(names)}")
        lines.extend(f"  {name:36s} {len(expected[keyword][name]):8d}" for name in sorted(names))
        lines.append("")
    return "\n".join(lines)


def _body_picture(built: bd.BodyMesh, out: Path) -> None:
    """Meridional section (r, z) of the body mesh through the centre line of the middle tooth,
    with the walls and the floor of the drawing in red."""
    section, solid, body = built.section, built.solid, built.body
    middle = rf.middle_tooth(section.teeth)
    centre = 0.5 * math.pi + (middle - 0.5 * (section.teeth + 1)) * section.pitch_angle_rad
    xy = solid.nodes_mm[:, :2]
    offset = np.angle(np.exp(1j * (np.arctan2(xy[:, 1], xy[:, 0]) - centre)))
    on_line = np.abs(offset) < 1.0e-7
    radius = np.hypot(xy[:, 0], xy[:, 1])
    z = solid.nodes_mm[:, 2]
    mask = on_line[solid.hexes]
    candidates = np.flatnonzero((mask[:, :4].sum(axis=1) == 2) & (mask[:, 4:].sum(axis=1) == 2))
    polygons = []
    for element in candidates.tolist():
        corners = solid.hexes[element]
        lower = sorted(corners[:4][mask[element, :4]].tolist(), key=lambda k: radius[k])
        upper = sorted(corners[4:][mask[element, 4:]].tolist(), key=lambda k: -radius[k])
        polygons.append([(radius[k], z[k]) for k in (*lower, *upper)])
    figure, axes = plt.subplots(figsize=(11.0, 6.5), dpi=160)
    axes.add_collection(
        PolyCollection(polygons, facecolors="#e6e6e6", edgecolors="#3a3a3a", linewidths=0.3)
    )
    half, floor, depth = 0.5 * body.face_width_mm, body.bottom_z_mm, body.pocket_depth_mm
    hub_face, hub_floor = body.hub_wall_radius_at(0.0), body.hub_wall_radius_at(depth)
    rim_face, rim_floor = body.rim_wall_radius_at(0.0), body.rim_wall_radius_at(depth)
    for sign in (1.0, -1.0):
        axes.plot(
            [hub_face, hub_floor, rim_floor, rim_face],
            [sign * half, sign * floor, sign * floor, sign * half],
            color="#c0392b",
            linewidth=1.2,
            label="Zeichnung" if sign > 0 else None,
        )
    axes.axvline(body.bore_radius_mm, color="#c0392b", linewidth=0.8, linestyle=":")
    axes.axvline(body.tip_radius_mm, color="#c0392b", linewidth=0.8, linestyle=":")
    axes.set_xlim(body.bore_radius_mm - 0.5, body.tip_radius_mm + 0.5)
    axes.set_ylim(-half - 0.5, half + 0.5)
    axes.set_aspect("equal")
    axes.legend(loc="upper right", fontsize=8, frameon=False)
    axes.set_title(
        f"Radkörper im Meridianschnitt durch die Mitte von Zahn T{middle}: Nabe, Steg und Taschen "
        f"nach Zeichnung; Ringe Nabe/Tasche/Felge {built.counts.hub_rings}/{built.counts.pocket_rings}/"
        f"{built.counts.rim_rings}, Schichten Steg {built.counts.web_layers}, je Tasche "
        f"{built.counts.flange_layers}; {len(solid.nodes_mm)} Knoten, {len(solid.hexes)} Elemente",
        fontsize=9,
    )
    axes.set_xlabel("r in mm", fontsize=8)
    axes.set_ylabel("z in mm", fontsize=8)
    axes.tick_params(labelsize=7)
    figure.tight_layout()
    figure.savefig(out / "mesh_body.png")
    plt.close(figure)


def _body_lines(built: bd.BodyMesh) -> list[str]:
    """Report lines of a body with pockets."""
    body, counts = built.body, built.counts
    depth = body.pocket_depth_mm
    return [
        f"body: pockets after the drawing ({body.source}); hub r {body.bore_radius_mm:.3f} to "
        f"{body.hub_wall_radius_at(0.0):.3f} mm at the face, pocket to r {body.rim_wall_radius_at(0.0):.3f} "
        f"mm, {depth:g} mm deep, walls {body.wall_angle_deg:g} deg (floor r "
        f"{body.hub_wall_radius_at(depth):.3f} to {body.rim_wall_radius_at(depth):.3f} mm), web "
        f"{body.web_thickness_mm:g} mm, rim from r {body.rim_wall_radius_at(0.0):.3f} mm; corner radii "
        f"R {body.corner_radius_mm:g} not meshed",
        f"body mesh: rings hub/pocket/rim {counts.hub_rings}/{counts.pocket_rings}/{counts.rim_rings}, "
        f"layers web {counts.web_layers} x {body.web_thickness_mm / counts.web_layers:.4f} mm, each pocket "
        f"{counts.flange_layers} x {depth / counts.flange_layers:.4f} mm; {len(built.removed_elements)} "
        f"elements removed, {len(built.sets.surfaces[built.sets.prefix + '_POCKET_SURF'])} faces on "
        f"the pocket surfaces; the element numbering differs from the ring body (new CONVERSE mapping)",
    ]


@dataclass(frozen=True)
class MeshResult:
    """What ``mesh`` built and wrote: the report lines and the mesh for the deck writer."""

    lines: list[str]
    file_name: str
    """Name of the written mesh file: ``<role>_mesh.inp`` for the ring body,
    ``<role>-pocket_mesh.inp`` for the body with pockets (naming of the user)."""
    section: sm.SectorMesh
    solid: so.SolidMesh
    sets: so.GearSets
    body: bd.BodyMesh | None


def mesh(
    case: str,
    role: ct.Role,
    teeth: int,
    rim_rings: int,
    layers: int,
    element_type: str,
    out: Path,
    counts: rs.MeshCounts | None = None,
    bore_radius_mm: float | None = None,
    body: bd.BodyShape = "ring",
    body_counts: bd.BodyCounts | None = None,
) -> MeshResult:
    """Write the mesh file of one gear sector and its pictures. ``body`` ``pocket`` meshes the
    body of the drawing (``fe.body``) with ``body_counts`` (rings hub / pocket / rim, layers
    web / flange) instead of ``layers`` equal layers of the full ring."""
    if body not in bd.BODY_SHAPES:
        raise InputRangeError(f"body must be one of {bd.BODY_SHAPES}, got {body!r}")
    generation = _generation(case)
    gear = generation.inputs.gears.pinion if role == "pinion" else generation.inputs.gears.wheel
    section = sm.sector_mesh(
        generation,
        role,
        teeth=teeth,
        rim_rings=rim_rings,
        bore_radius_mm=bore_radius_mm,
        counts=counts,
    )
    effective = rf.effective_counts(section)
    prefix = role.upper()
    built: bd.BodyMesh | None = None
    if body == "pocket":
        shape = bd.body_section(case, role)
        if abs(shape.face_width_mm - gear.face_width_mm) > 1.0e-6:
            raise InputRangeError(
                f"the drawing has the face width {shape.face_width_mm:g} mm, the STplus file "
                f"{gear.face_width_mm:g} mm"
            )
        built = bd.body_mesh(section, shape, body_counts or bd.BodyCounts(), prefix)
        section, solid, sets = built.section, built.solid, built.sets
    else:
        solid = so.extrude(section, face_width_mm=gear.face_width_mm, layers=layers)
        sets = so.gear_sets(solid, prefix)
    out.mkdir(parents=True, exist_ok=True)
    file_name = f"{role}-pocket_mesh.inp" if body == "pocket" else f"{role}_mesh.inp"
    target = out / file_name
    written = ab.mesh_text(
        solid,
        sets,
        element_type=element_type,
        title=f"{case}: {role}, face width {gear.face_width_mm:g} mm, body {body}, built by gearcore",
    )
    target.write_text(written, encoding="ascii")
    if built is not None:
        _mesh_pictures(section, built.full, built.full_sets, out)
        _body_picture(built, out)
    else:
        _mesh_pictures(section, solid, sets, out)
    (out / "sets.txt").write_text(_set_list(written, sets), encoding="utf-8")
    quality = sm.scaled_jacobians(section.points_mm, section.quads)
    edges = np.concatenate(
        [
            np.hypot(
                *(
                    section.points_mm[section.quads[:, k]]
                    - section.points_mm[section.quads[:, (k + 1) % 4]]
                ).T
            )
            for k in range(4)
        ]
    )
    thickness = (
        f"layer thickness {gear.face_width_mm / solid.layers:.4f} mm"
        if built is None
        else "layers of the web and of the pockets differ (see body mesh)"
    )
    lines = [
        target.as_posix(),
        f"nodes {len(solid.nodes_mm)}, elements {len(solid.hexes)} ({element_type}), "
        f"layers {solid.layers}, {thickness}",
        f"mesh parameters: {teeth} teeth + {effective.shoulder_pitches} shoulder pitches, "
        f"elements over the tooth height {effective.over_tooth_height}, at the tooth root (one "
        f"gap) {effective.at_tooth_root}, over the tooth thickness "
        f"{effective.over_tooth_thickness}, over the face width {solid.layers}, rim rings "
        f"{counts.rim_rings if counts is not None else rim_rings}, layers normal to the root "
        f"surface {counts.root_layers if counts is not None else 'template (3)'}; "
        f"{'counts ' + counts.label() if counts is not None else 'density of the template'}",
        f"transverse mesh: {len(section.points_mm)} nodes, {len(section.quads)} quads, smallest "
        f"corner sine {float(quality.min()):.3f}, quads below 0.35: {int((quality < 0.35).sum())}, "
        f"edge lengths {float(edges.min()):.4f} to {float(edges.max()):.4f} mm",
        f"circles: bore {section.bore_radius_mm:.4f}, fan ring {section.fan_ring_radius_mm:.4f}, "
        f"root {section.root_radius_mm:.4f}, tip {section.tip_radius_mm:.4f} mm",
        f"sets: {len(sets.node_sets)} node sets, {len(sets.element_sets)} element sets, "
        f"{len(sets.surfaces)} surfaces; fixed nodes {len(sets.node_sets[prefix + '_FESSELUNG'])}",
    ]
    if built is not None:
        lines.extend(_body_lines(built))
    return MeshResult(
        lines=lines, file_name=file_name, section=section, solid=solid, sets=sets, body=built
    )


def surface(
    case: str,
    role: ct.Role,
    mating_teeth: int,
    mating_layers: int,
    max_edge_mm: float,
    rotation: pl.Rotation,
    out: Path,
    tip_rounding_mm: float = 0.0,
) -> list[str]:
    """Write the rigid tooth surface of the gear ``role`` and a picture of it in mesh with the
    sector of the mating gear; returns the lines of the report. ``tip_rounding_mm`` > 0 rounds
    the corners of the tip land of the rigid surface (``rigid_surface``)."""
    generation = _generation(case)
    gears = generation.inputs.gears
    mating_role: ct.Role = "wheel" if role == "pinion" else "pinion"
    gear, mating = (gears.pinion, gears.wheel) if role == "pinion" else (gears.wheel, gears.pinion)
    levels = rsf.surface_z_levels(
        so.sweep_levels(mating.face_width_mm, mating_layers), gear.face_width_mm
    )
    rigid = rsf.rigid_surface(
        generation,
        role,
        teeth=mating_teeth + 2,
        max_edge_mm=max_edge_mm,
        z_levels_mm=levels,
        tip_rounding_mm=tip_rounding_mm,
    )
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{role}_surface.inp"
    rounding_note = f", tip rounding {tip_rounding_mm:g} mm" if tip_rounding_mm > 0.0 else ""
    target.write_text(
        ab.rigid_surface_text(
            rigid,
            role.upper(),
            title=f"{case}: {role}, face width {gear.face_width_mm:g} mm{rounding_note}, "
            "built by gearcore",
        ),
        encoding="ascii",
    )
    # the pair in the middle of the path of contact: both parts have their middle tooth on +y
    section = sm.sector_mesh(generation, mating_role, teeth=mating_teeth, rim_rings=12)
    rho_a, rho_e = pl.path_of_contact_limits(generation)
    flank = pl.working_flank_of_the_driving_pinion(rotation)
    place = pl.fixed_axes(pl.mesh_position(generation, 0.5 * (rho_a + rho_e), working_flank=flank))
    by_role = {
        "pinion": (place.axis_mm.pinion, place.tooth_centre_angle_deg.pinion),
        "wheel": (place.axis_mm.wheel, place.tooth_centre_angle_deg.wheel),
    }
    profile = pl.placed(rigid.nodes_mm[: rigid.profile_nodes, :2], *by_role[role])
    points = pl.placed(section.points_mm, *by_role[mating_role])
    module_mm = generation.inputs.normal_module_mm
    pitch_point = 0.5 * generation.pair_geometry.working_pitch_diameter_mm.pinion
    figure, (overview, detail) = plt.subplots(1, 2, figsize=(12.0, 6.0), dpi=160)
    for axes, half, width in ((overview, 5.0 * module_mm, 0.9), (detail, 1.4 * module_mm, 1.2)):
        _draw_quads(axes, points, section.quads, edge=WHEEL_COLOUR, width=0.25)
        axes.plot(profile[:, 0], profile[:, 1], "-", color=PINION_COLOUR, linewidth=width)
        axes.set_xlim(pitch_point - half, pitch_point + half)
        axes.set_ylim(-1.2 * half, 1.2 * half)
        axes.set_aspect("equal")
        axes.set_xlabel("x in mm", fontsize=8)
        axes.tick_params(labelsize=7)
    overview.set_ylabel("y in mm", fontsize=8)
    detail.set_ylabel("y in mm", fontsize=8)
    overview.set_title("Starre Fläche und Netz des Gegenrads", fontsize=9)
    detail.set_title("Ausschnitt am Wälzpunkt", fontsize=9)
    figure.suptitle(
        f"{case}: Mitte der Eingriffsstrecke, {rigid.teeth} Zähne der starren Fläche, "
        f"{rigid.profile_nodes} Knoten am Profil, {len(levels)} z-Ebenen",
        fontsize=10,
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    figure.savefig(out / "pair_mesh.png")
    plt.close(figure)
    along = rigid.nodes_mm[: rigid.profile_nodes, :2]
    steps = np.hypot(*(along[1:] - along[:-1]).T)
    return [
        target.as_posix(),
        f"nodes {len(rigid.nodes_mm)}, elements {len(rigid.quads)} (R3D4), {rigid.teeth} teeth",
        f"profile: {rigid.profile_nodes} nodes, steps {float(steps.min()):.4f} to "
        f"{float(steps.max()):.4f} mm",
        f"z: {len(levels)} levels from {float(levels[0]):g} to {float(levels[-1]):g} mm, steps "
        f"{float(np.diff(levels).min()):.4f} to {float(np.diff(levels).max()):.4f} mm",
        *(
            [
                f"tip corners rounded with {tip_rounding_mm:g} mm (at least "
                f"{rsf.ROUNDING_FACETS} facets per arc); 0 = the sharp corner of the drawing"
            ]
            if tip_rounding_mm > 0.0
            else []
        ),
    ]


# --- position files, manifest and runner (step S5) -----------------------------------------------

REFERENCE_COF = (
    REPO_ROOT / "30_references_and_examples" / "32_Abaqus" / "implicit" / "kstE_OF_QS.cof"
)
LEARNING_EDITION = Path(r"C:\SIMULIA\Commands\abq2025le.bat")
LE_COUNTS = rs.MeshCounts(
    over_tooth_height=6,
    at_tip_edge_break=1,
    at_tooth_root=16,
    over_tooth_thickness=6,
    root_layers=2,
    rim_rings=2,
    shoulder_columns=2,
)

VARIANTS: dict[str, tuple[dict[str, object], str]] = {
    "ls": (
        {"nlgeom": False, "contact": "surface_to_surface", "line_search": 5},
        "wie Pilot 2 (geometrisch linear, Fläche-zu-Fläche, Penalty) plus Line Search N_ls = 5",
    ),
    "direct": (
        {"nlgeom": False, "contact": "surface_to_surface", "enforcement": "direct"},
        "geometrisch linear, Fläche-zu-Fläche, Lagrange-Multiplikatoren (DIRECT) statt Penalty",
    ),
    "n2s": (
        {"nlgeom": False, "contact": "node_to_surface", "smoothing": 0.2},
        "geometrisch linear, Knoten-zu-Fläche mit Glättung der starren Facetten (SMOOTH 0,2); "
        "seit 2026-10-07 die Standardeinstellung",
    ),
    "n2s_smooth0": (
        {"nlgeom": False, "contact": "node_to_surface", "smoothing": 0.0},
        "geometrisch linear, Knoten-zu-Fläche ohne Glättung der starren Facetten (SMOOTH 0); "
        "Abaqus 2025 bricht damit vor dem ersten Inkrement ab (THE NORMAL VECTOR ON THE SURFACE "
        "IS ZERO, danach Segmentation Fault; 2026-10-07, die starre Fläche hat kein entartetes "
        "Facett) - stattdessen `n2s_smooth0p01`",
    ),
    "n2s_smooth0p01": (
        {"nlgeom": False, "contact": "node_to_surface", "smoothing": 0.01},
        "geometrisch linear, Knoten-zu-Fläche mit der kleinsten lauffähigen Glättung (SMOOTH 0,01, "
        "ein Hundertstel einer Facette): trennt die Ursache des Abbruchs von Fläche-zu-Fläche bei "
        "16 Nm (Pilot 2) in Facettenknicke der starren Fläche (dann bricht auch diese Datei ab) "
        "oder Integration über die Radflankenfacetten (dann läuft sie durch)",
    ),
    "nlgeom_ls": (
        {"nlgeom": True, "contact": "surface_to_surface", "line_search": 5},
        "wie Pilot 1 (NLGEOM=YES, Fläche-zu-Fläche, Penalty) plus Line Search N_ls = 5",
    ),
    "nlgeom_direct": (
        {"nlgeom": True, "contact": "surface_to_surface", "enforcement": "direct"},
        "NLGEOM=YES, Fläche-zu-Fläche, Lagrange-Multiplikatoren (DIRECT)",
    ),
    "nlgeom_n2s": (
        {"nlgeom": True, "contact": "node_to_surface", "smoothing": 0.2},
        "NLGEOM=YES, Knoten-zu-Fläche mit Glättung der starren Facetten (SMOOTH 0,2)",
    ),
}
"""Variants of the solver and contact settings for the diagnosis of a broken-off pilot: one
position file per variant, same mesh files, same position. Every variant names its contact
formulation itself, so a change of the ``PositionDeck`` defaults does not move it."""
ENFORCEMENT_README: dict[str, str] = {
    "default": "harte Kontaktbedingung mit der Abaqus-Voreinstellung der Durchsetzung (direkt "
    "mit Lagrange-Multiplikatoren bei Knoten-zu-Fläche)",
    "penalty": "harte Kontaktbedingung mit linearer Penalty-Durchsetzung (PENALTY=LINEAR, "
    "Penalty-Steifigkeit 10 × repräsentative Elementsteifigkeit nach Abaqus-Voreinstellung; "
    "Abhilfe gegen das Flattern eines Flankenknotens auf dem Knick der starren Fläche, "
    "Abbrüche der 60-je-Teilung-Studie 2026-10-07)",
    "direct": "harte Kontaktbedingung, direkt mit Lagrange-Multiplikatoren (DIRECT)",
    "augmented_lagrange": "harte Kontaktbedingung mit Augmented-Lagrange-Durchsetzung",
}
"""Sentence of the README for the enforcement of the contact constraint."""
"""Coarse numbers for the function test in the Learning Edition (1000 nodes)."""
LE_POCKET_COUNTS = rs.MeshCounts(
    over_tooth_height=4,
    at_tip_edge_break=1,
    at_tooth_root=12,
    over_tooth_thickness=4,
    root_layers=1,
    rim_rings=3,
    shoulder_columns=2,
)
"""Coarser numbers for the pocket body in the Learning Edition: five levels instead of three."""


def _positions(
    generation: GenerationResult, chosen: list[str], steps_per_pitch: int, margin: float
) -> list[tuple[str, float]]:
    """(label, rho_1) of the positions: the named points A to E, or the grid from a margin
    before A to a margin after E in steps of a fraction of the base pitch plus the named
    points, or the pilot position C."""
    rho_a, rho_e = pl.path_of_contact_limits(generation)
    rho_b, rho_d = pl.single_contact_points(generation)
    geometry = generation.pair_geometry
    pair = generation.inputs
    r_b1 = 0.5 * iv.base_diameter(
        generation.gears.pinion.number_of_teeth,
        pair.normal_module_mm,
        math.radians(pair.normal_pressure_angle_deg),
        0.0,
    )
    # the pitch point C on the line of action: T_1 C = r_b1 tan(alpha_wt)
    rho_c = r_b1 * math.tan(math.radians(geometry.transverse_working_pressure_angle_deg))
    named = {"A": rho_a, "B": rho_b, "C": rho_c, "D": rho_d, "E": rho_e}
    p_bt = geometry.transverse_base_pitch_mm
    if chosen == ["pilot"]:
        return [("C", rho_c)]
    if chosen == ["grid"]:
        count = int(round((rho_e - rho_a + 2.0 * margin * p_bt) / (p_bt / steps_per_pitch)))
        values = [
            (("", rho_a - margin * p_bt + k * p_bt / steps_per_pitch)) for k in range(count + 1)
        ]
        values.extend(named.items())
    else:
        values = [(label, named[label]) for label in chosen]
    values.sort(key=lambda item: item[1])
    merged: list[tuple[str, float]] = []
    for label, rho in values:
        if merged and abs(rho - merged[-1][1]) < 1.0e-9 * p_bt:
            if label:
                merged[-1] = (label, rho)
            continue
        merged.append((label, rho))
    return merged


def _runner_text() -> str:
    return "\n".join(
        [
            "# Runs every position file in this folder one after another with Abaqus (full",
            "# licence). Skips a position whose .sta file reports completion. Start it from the",
            "# Abaqus command prompt in this folder:  powershell -File run_all.ps1 [-Launcher abq2025]",
            'param([string]$Launcher = "abaqus", [int]$Cpus = 4)',
            "Set-Location $PSScriptRoot",
            '$log = Join-Path $PSScriptRoot "run_log.txt"',
            'foreach ($deck in Get-ChildItem -Filter "pos_*.inp" | Sort-Object Name) {',
            "    $job = $deck.BaseName",
            '    $sta = "$job.sta"',
            '    if ((Test-Path $sta) -and (Select-String -Path $sta -Pattern "COMPLETED SUCCESSFULLY" -Quiet)) {',
            '        "$(Get-Date -Format s) $job already completed" | Tee-Object -FilePath $log -Append',
            "        continue",
            "    }",
            '    "$(Get-Date -Format s) start $job" | Tee-Object -FilePath $log -Append',
            '    & $Launcher "job=$job" "input=$($deck.Name)" "cpus=$Cpus" "interactive" "ask_delete=OFF"',
            '    $outcome = "NOT completed (see $job.msg)"',
            '    if ((Test-Path $sta) -and (Select-String -Path $sta -Pattern "COMPLETED SUCCESSFULLY" -Quiet)) {',
            '        $outcome = "completed"',
            "    }",
            '    "$(Get-Date -Format s) end $job exit $LASTEXITCODE, $outcome" | Tee-Object -FilePath $log -Append',
            '    if ((Test-Path "$job.odb") -and (Test-Path "extract_odb.py")) {',
            "        # the fields of the .odb (contact, fillets, heads, reference points) into",
            "        # <job>_fields.json, read by build_fe_decks.py report",
            '        & $Launcher "python" "extract_odb.py" "$job" 2>&1 | Tee-Object -FilePath $log -Append',
            '        "$(Get-Date -Format s) fields of $job written to ${job}_fields.json" '
            "| Tee-Object -FilePath $log -Append",
            "    }",
            "}",
            "",
        ]
    )


EXTRACTION_SCRIPT = Path(__file__).with_name("fe_odb_extract.py")


def extract(folder: Path, launcher: Path) -> list[str]:
    """Run the extraction script of a folder with the Python of an Abaqus installation for
    every job that has an ``.odb`` but no ``_fields.json`` yet (the Learning Edition's Python
    reads the output databases of the full licence)."""
    script = folder / "extract_odb.py"
    if not script.exists():
        script.write_text(EXTRACTION_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    report: list[str] = []
    for odb in sorted(folder.glob("pos_*.odb")):
        job = odb.stem
        target = folder / f"{job}_fields.json"
        if target.exists():
            report.append(f"{job}: fields already extracted")
            continue
        command = f'"{launcher}" python extract_odb.py {job}'
        completed = subprocess.run(
            command, cwd=folder, shell=True, capture_output=True, text=True, timeout=3600
        )
        tail = (completed.stdout + completed.stderr).strip().splitlines()[-3:]
        report.append(
            f"{job}: " + ("written" if target.exists() else "FAILED") + " - " + " | ".join(tail)
        )
    return report


def _fillet_chains(section: sm.SectorMesh) -> dict[str, list[int]]:
    """Ordered surface node ids (0-based, transverse mesh) of the fillet of every tooth half,
    from the root form point to the centre line of the gap, for the later evaluation."""
    chains: dict[str, list[int]] = {}
    for tooth in range(1, section.teeth + 1):
        for side, name in ((1, "LEFT"), (-1, "RIGHT")):
            edges = [
                e
                for e in cv._surface_edges_of(section)
                if e[2] == tooth and e[3] == side and e[4] == "root"
            ]
            if not edges:
                continue
            chain = [edges[0][0]] + [e[1] for e in edges]
            chains[f"T{tooth}_{name}"] = chain if side == 1 else chain[::-1]
    return chains


def _body_manifest(built: bd.BodyMesh | None) -> dict[str, object]:
    """The body block of the manifest: the shape, and for pockets the drawing and the mesh."""
    if built is None:
        return {"shape": "ring"}
    body, counts = built.body, built.counts
    return {
        "shape": "pocket",
        "source": body.source,
        "section_mm": {
            name: getattr(body, name)
            for name in (
                "face_width_mm",
                "tip_radius_mm",
                "bore_radius_mm",
                "hub_wall_radius_mm",
                "hub_wall_height_mm",
                "rim_wall_radius_mm",
                "rim_wall_height_mm",
                "pocket_depth_mm",
                "wall_angle_deg",
                "corner_radius_mm",
            )
        },
        "web_thickness_mm": body.web_thickness_mm,
        "hub_wall_radius_at_floor_mm": body.hub_wall_radius_at(body.pocket_depth_mm),
        "rim_wall_radius_at_floor_mm": body.rim_wall_radius_at(body.pocket_depth_mm),
        "counts": {
            "hub_rings": counts.hub_rings,
            "pocket_rings": counts.pocket_rings,
            "rim_rings": counts.rim_rings,
            "web_layers": counts.web_layers,
            "flange_layers": counts.flange_layers,
        },
        "z_levels_mm": built.solid.z_levels_mm.tolist(),
        "elements_removed": int(len(built.removed_elements)),
        "pocket_surface_faces": int(len(built.sets.surfaces[built.sets.prefix + "_POCKET_SURF"])),
        "corner_radii_meshed": False,
    }


def _body_readme(built: bd.BodyMesh | None) -> str:
    """The paragraph of the README that names the body of the wheel."""
    if built is None:
        return (
            "Radkörper: voller Ring von der Bohrung bis zu den Zähnen (Vergleichsvariante `ring`; "
            "der Stahleinsatz in der Bohrung ist die feste Fesselung)."
        )
    body, counts = built.body, built.counts
    depth = body.pocket_depth_mm
    return (
        f"Radkörper nach Zeichnung ({body.source}): Nabe r {body.bore_radius_mm:g} bis "
        f"{body.hub_wall_radius_mm:g} mm in voller Breite, von beiden Stirnseiten je eine Tasche bis "
        f"r {body.rim_wall_radius_at(0.0):.3f} mm an der Stirnseite ({depth:g} mm tief, Wände "
        f"{body.wall_angle_deg:g}° zur Stirnseite, am Taschengrund r {body.hub_wall_radius_at(depth):.3f} "
        f"bis {body.rim_wall_radius_at(depth):.3f} mm), Steg {body.web_thickness_mm:g} mm, Felge ab "
        f"r {body.rim_wall_radius_at(0.0):.3f} mm in voller Breite; die Rundungen R {body.corner_radius_mm:g} "
        f"der Zeichnung sind nicht vernetzt (FE-18). Ringe Nabe/Tasche/Felge "
        f"{counts.hub_rings}/{counts.pocket_rings}/{counts.rim_rings}, Schichten Steg {counts.web_layers}, "
        f"je Tasche {counts.flange_layers}; {len(built.removed_elements)} Elemente der Taschen entfernt, "
        f"Elementsets `WHEEL_BODY_HUB`, `WHEEL_BODY_WEB`, `WHEEL_BODY_RIM`, Fläche `WHEEL_POCKET_SURF`. "
        "Die Elementnummern unterscheiden sich vom Ringkörper: das CONVERSE-Mapping wird auf dieser "
        "`wheel-pocket_mesh.inp` neu erzeugt (Variante `pocket`; der Ringkörper bleibt als Variante "
        "`ring` mit `wheel_mesh.inp`)."
    )


def decks(
    case: str,
    *,
    teeth: int,
    rim_rings: int,
    layers: int,
    element_type: str | None,
    counts: rs.MeshCounts | None,
    bore_radius_mm: float | None,
    rotation: pl.Rotation,
    material_steps: list[dk.MaterialStep],
    cofs: list[Path],
    rates: list[str],
    temperature_c: float,
    torques_wheel_nm: list[float],
    positions: list[str],
    steps_per_pitch: int,
    margin: float,
    seating_arc_mm: float,
    max_edge_mm: float,
    out: Path,
    variants: list[str] | None = None,
    body: bd.BodyShape = "ring",
    body_counts: bd.BodyCounts | None = None,
    enforcement: dk.Enforcement = "default",
    grid_indices: list[int] | None = None,
    tip_rounding_mm: float = 0.0,
    iteration_limits: tuple[int, int, int] | None = None,
) -> list[str]:
    """Write the wheel mesh, the pinion surface, one position file per position and
    combination, the manifest and the runner into ``out``; returns the lines of the report.
    ``tip_rounding_mm`` rounds the tip corners of the rigid pinion surface (``surface``);
    ``iteration_limits`` (I_0, I_R, I_C) raises the equilibrium iteration limits of every step
    (``deck.PositionDeck.iteration_limits``).

    ``enforcement`` sets the enforcement of the hard contact of every file (a variant that
    names its own enforcement wins): ``default`` leaves it to Abaqus (direct Lagrange
    multipliers for node-to-surface), ``penalty`` writes ``PENALTY=LINEAR``, the remedy of the
    Abaqus guide for chattering of a secondary node on a kink of the main surface (the 11
    broken-off positions of the 60-per-pitch study, 2026-10-09). ``grid_indices`` keeps only
    these positions of the grid (1-based, the numbering of the full grid is preserved, so
    ``pos_045.inp`` of a retry folder is the same position as in the study folder).

    The material steps and the strain rates are variant axes: one CONVERSE file per rate
    (``cofs`` and ``rates`` in the same order; the same mesh, the material card of that rate),
    and every position gets one file per step and rate, ``pos_NNN_<step>_<rate>.inp``; one
    step and one rate keep ``pos_NNN.inp``. With ``variants`` every such file comes once per
    variant of ``VARIANTS`` (``..._<variant>.inp``). The orientation pieces are written per
    rate (``wheel_orientation_<rate>_part.inp``, ``_model.inp`` for W4, ``_model_elastic.inp``
    for W3). ``element_type`` None takes the element type of each step
    (``deck.ELEMENT_TYPE_OF_STEP``), and the mesh is written once per element type needed
    (the second one as ``<mesh>_<type>.inp``, same nodes and elements, so the CONVERSE mapping
    holds for both); the steps are geometrically nonlinear where ``deck.NLGEOM_OF_STEP`` says
    so, unless a variant sets ``nlgeom`` itself. ``body`` ``pocket`` meshes the wheel body of
    the drawing (``fe.body``) with ``body_counts``."""
    for variant in variants or ():
        if variant not in VARIANTS:
            raise InputRangeError(f"variant {variant!r} is not one of {tuple(VARIANTS)}")
    if not material_steps or any(s not in dk.MATERIAL_STEPS for s in material_steps):
        raise InputRangeError(
            f"material steps must be among {dk.MATERIAL_STEPS}, got {material_steps!r}"
        )
    if len(dict.fromkeys(material_steps)) != len(material_steps):
        raise InputRangeError(f"material steps repeat: {material_steps!r}")
    if not rates or len(cofs) != len(rates) or len(set(rates)) != len(rates):
        raise InputRangeError("one CONVERSE file per rate is required, rate names distinct")
    for rate in rates:
        if not rate.isidentifier():
            raise InputRangeError(f"a rate name must be an identifier, got {rate!r}")
    types_of_step: dict[str, str] = {
        s: element_type if element_type is not None else dk.ELEMENT_TYPE_OF_STEP[s]
        for s in material_steps
    }
    main_type = types_of_step[material_steps[0]]
    generation = _generation(case)
    gears = generation.gears
    flank = pl.working_flank_of_the_driving_pinion(rotation)
    sign = pl.pinion_torque_sign(flank)
    out.mkdir(parents=True, exist_ok=True)
    built = mesh(
        case,
        "wheel",
        teeth,
        rim_rings,
        layers,
        main_type,
        out,
        counts,
        bore_radius_mm,
        body=body,
        body_counts=body_counts,
    )
    report = list(built.lines)
    report += surface(
        case, "pinion", teeth, layers, max_edge_mm, rotation, out, tip_rounding_mm=tip_rounding_mm
    )
    section = built.section
    layers = built.solid.layers
    effective = rf.effective_counts(section)
    face_width = generation.inputs.gears.wheel.face_width_mm
    mesh_files: dict[str, str] = {main_type: built.file_name}
    for other in sorted(set(types_of_step.values()) - {main_type}):
        name = built.file_name.removesuffix(".inp") + f"_{other}.inp"
        (out / name).write_text(
            ab.mesh_text(
                built.solid,
                built.sets,
                element_type=other,
                title=f"{case}: wheel, face width {face_width:g} mm, body {body}, built by gearcore",
            ),
            encoding="ascii",
        )
        mesh_files[other] = name
        report.append(f"{(out / name).as_posix()}: the same mesh with {other}")
    cards: dict[str, dk.MaterialCard] = {}
    pieces_of: dict[str, tuple[str, str | None, str | None]] = {}
    orientation_files: list[str] = []
    needs_orientation = any(s in ("W3", "W4") for s in material_steps)
    for rate, cof in zip(rates, cofs, strict=True):
        cof_text = cof.read_text(encoding="utf-8", errors="replace")
        cards[rate] = dk.read_material_card(cof_text, temperature_c)
        if not needs_orientation:
            continue
        pieces = dk.split_orientation_file(cof_text, dk.WHEEL_INSTANCE, dk.WHEEL)
        part_file = f"wheel_orientation_{rate}_part.inp"
        (out / part_file).write_text(pieces.part, encoding="utf-8")
        orientation_files.append(part_file)
        model_file = elastic_file = None
        if "W4" in material_steps:
            model_file = f"wheel_orientation_{rate}_model.inp"
            (out / model_file).write_text(pieces.model, encoding="utf-8")
            orientation_files.append(model_file)
        if "W3" in material_steps:
            elastic_file = f"wheel_orientation_{rate}_model_elastic.inp"
            (out / elastic_file).write_text(pieces.model_without_plasticity, encoding="utf-8")
            orientation_files.append(elastic_file)
        pieces_of[rate] = (part_file, model_file, elastic_file)
    known_rates = data.load_converse_rates()
    z1, z2 = gears.pinion.number_of_teeth, gears.wheel.number_of_teeth
    torques_pinion = tuple(1000.0 * t * z1 / z2 for t in torques_wheel_nm)
    pair = generation.inputs
    r_b1 = 0.5 * iv.base_diameter(
        z1, pair.normal_module_mm, math.radians(pair.normal_pressure_angle_deg), 0.0
    )
    seating = dk.seating_angle_rad(seating_arc_mm, r_b1)
    step_names = tuple(f"LOAD_{t:g}NM".replace(".", "P") for t in torques_wheel_nm)
    chosen = _positions(generation, positions, steps_per_pitch, margin)
    if enforcement not in dk.ENFORCEMENT_KEYWORDS:
        raise InputRangeError(f"enforcement {enforcement!r} is not known")
    if grid_indices is not None:
        bad = [k for k in grid_indices if not 1 <= k <= len(chosen)]
        if bad or not grid_indices or len(set(grid_indices)) != len(grid_indices):
            raise InputRangeError(
                f"grid indices must be distinct and between 1 and {len(chosen)}, got {grid_indices!r}"
            )
    rho_a, _ = pl.path_of_contact_limits(generation)
    entries = []
    single = len(material_steps) == 1 and len(rates) == 1

    def settings_of(step: dk.MaterialStep) -> dict[str, dict[str, object]]:
        nlgeom = dk.NLGEOM_OF_STEP[step]
        common: dict[str, object] = {
            "nlgeom": nlgeom,
            "enforcement": enforcement,
            "iteration_limits": iteration_limits,
        }
        if variants:
            return {v: {**common, **VARIANTS[v][0]} for v in variants}
        return {"": common}

    for k, (label, rho) in enumerate(chosen, start=1):
        if grid_indices is not None and k not in grid_indices:
            continue
        position = pl.mesh_position(generation, rho, working_flank=flank)
        place = pl.fixed_axes(position)
        for step in material_steps:
            for rate in rates:
                for variant, settings in settings_of(step).items():
                    name = (
                        f"pos_{k:03d}"
                        + ("" if single else f"_{step}_{rate}")
                        + (f"_{variant}" if variant else "")
                    )
                    part_file, model_file, elastic_file = pieces_of.get(rate, ("", None, None))
                    with_orientation = step in ("W3", "W4")
                    deck = dk.PositionDeck(
                        wheel_mesh_file=mesh_files[types_of_step[step]],
                        pinion_surface_file="pinion_surface.inp",
                        placement=place,
                        torques_pinion_nmm=torques_pinion,
                        torque_sign=sign,
                        seating_angle_rad=seating,
                        temperature_c=temperature_c,
                        material_step=step,
                        card=cards[rate],
                        orientation_part_file=part_file if with_orientation else None,
                        orientation_model_file=(
                            model_file if step == "W4" else elastic_file if step == "W3" else None
                        ),
                        title=f"{case}: position {k} of {len(chosen)}"
                        f"{' (' + label + ')' if label else ''}, rho_1 = {rho:.6f} mm, "
                        f"{step} {rate}{', variant ' + variant if variant else ''}, built by gearcore",
                        step_names=step_names,
                        rate=rate,
                        **settings,  # type: ignore[arg-type]
                    )
                    (out / f"{name}.inp").write_text(dk.position_deck_text(deck), encoding="ascii")
                    entries.append(
                        {
                            "index": k,
                            "file": f"{name}.inp",
                            "material_step": step,
                            "rate": rate,
                            "element_type": types_of_step[step],
                            "nlgeom": bool(settings["nlgeom"]),
                            "enforcement": str(settings["enforcement"]),
                            "iteration_limits": (
                                list(settings["iteration_limits"])  # type: ignore[call-overload]
                                if settings.get("iteration_limits") is not None
                                else None
                            ),
                            "variant": variant,
                            "point": label,
                            "rho_1_mm": rho,
                            "rho_2_mm": position.radius_of_curvature_mm.wheel,
                            "from_A_mm": rho - rho_a,
                            "pinion_tooth_centre_angle_deg": place.tooth_centre_angle_deg.pinion,
                            "wheel_tooth_centre_angle_deg": place.tooth_centre_angle_deg.wheel,
                            "tooth_pairs_on_path": list(position.tooth_pairs_on_path),
                        }
                    )
    first_card = cards[rates[0]]
    manifest = {
        "case": case,
        "pinion_rotation": rotation,
        "working_flank_of_the_pinion": flank,
        "torque_sign_about_z": sign,
        "torques_wheel_nm": list(torques_wheel_nm),
        "torques_pinion_nmm": list(torques_pinion),
        "step_names": ["SEAT", *step_names],
        "seating_arc_mm": seating_arc_mm,
        "seating_angle_rad": seating,
        "material_step": material_steps[0],
        "material_steps": list(material_steps),
        "nlgeom": dk.NLGEOM_OF_STEP[material_steps[0]],
        "nlgeom_of_step": {s: dk.NLGEOM_OF_STEP[s] for s in material_steps},
        "rates": {
            rate: {
                "file": cof.as_posix(),
                "name": cards[rate].name,
                "temperature_c": cards[rate].temperature_c,
                "youngs_modulus_mpa": cards[rate].youngs_modulus_mpa,
                "poisson_ratio": cards[rate].poisson_ratio,
                "orientation_files": list(pieces_of.get(rate, ())),
                **known_rates.get(rate, {}),
            }
            for rate, cof in zip(rates, cofs, strict=True)
        },
        "contact": "node_to_surface",
        "enforcement": enforcement,
        "iteration_limits": list(iteration_limits) if iteration_limits is not None else None,
        "grid": {
            "positions": positions,
            "indices": grid_indices,
            "steps_per_pitch": steps_per_pitch,
            "margin_pitches": margin,
            "transverse_base_pitch_mm": generation.pair_geometry.transverse_base_pitch_mm,
            "path_of_contact_mm": pl.path_of_contact_limits(generation)[1] - rho_a,
        },
        "material_card": {
            "file": cofs[0].as_posix(),
            "name": first_card.name,
            "temperature_c": first_card.temperature_c,
            "engineering_constants": list(first_card.engineering_constants),
            "youngs_modulus_mpa": first_card.youngs_modulus_mpa,
            "poisson_ratio": first_card.poisson_ratio,
        },
        "orientation_files": orientation_files,
        "wheel_mesh": {
            "file": built.file_name,
            "files": mesh_files,
            "teeth": teeth,
            "shoulder_pitches": 2,
            "layers": layers,
            "element_type": main_type,
            "element_type_of_step": types_of_step,
            "nodes_per_level": len(section.points_mm),
            "elements_per_layer": len(section.quads),
            "nodes": len(built.solid.nodes_mm),
            "elements": len(built.solid.hexes),
            "bore_radius_mm": section.bore_radius_mm,
            "counts": {
                "over_tooth_height": effective.over_tooth_height,
                "at_tooth_root": effective.at_tooth_root,
                "over_tooth_thickness": effective.over_tooth_thickness,
                "rim_rings": counts.rim_rings if counts is not None else effective.rim_rings,
                "root_layers": counts.root_layers if counts is not None else 3,
                "shoulder_columns": counts.shoulder_columns if counts is not None else 4,
            },
            "body": _body_manifest(built.body),
            "fillet_chains_transverse": _fillet_chains(section),
        },
        "pinion_surface": {
            "file": "pinion_surface.inp",
            "teeth": teeth + 2,
            "max_edge_mm": max_edge_mm,
            "tip_rounding_mm": tip_rounding_mm,
        },
        "positions": entries,
        "variants": {v: VARIANTS[v][1] for v in variants} if variants else {},
        "runner": "run_all.ps1",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (out / "run_all.ps1").write_text(_runner_text(), encoding="utf-8")
    (out / "extract_odb.py").write_text(
        EXTRACTION_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (out / "README.md").write_text(
        "\n".join(
            [
                f"# Stellungsrechnungen {case}, Werkstoffstufe{'n' if len(material_steps) > 1 else ''} "
                f"{', '.join(material_steps)}, Rate{'n' if len(rates) > 1 else ''} {', '.join(rates)}",
                "",
                f"Radsektor {teeth} Zähne + 2 zahnlose Segmente, {layers} Schichten, "
                f"{', '.join(f'{t} ({f})' for t, f in mesh_files.items())}, "
                f"{len(built.solid.nodes_mm)} Knoten; starre Ritzelfläche mit {teeth + 2} Zähnen"
                + (
                    f", Kopfkanten mit {tip_rounding_mm:g} mm gerundet (Entgratung als "
                    "Modellannahme der starren Fläche, nicht der Zeichnung; FE-17)"
                    if tip_rounding_mm > 0.0
                    else ", scharfe Kopfkanten wie das reale Ritzel (FE-17)"
                )
                + ". "
                + (
                    "Je Stellung eine Datei `pos_NNN.inp`"
                    if single
                    else "Je Stellung, Werkstoffstufe und Rate eine Datei `pos_NNN_<Stufe>_<Rate>.inp`"
                )
                + f" (Schritte: SEAT, dann {', '.join(step_names)}); "
                "Momente am Rad " + ", ".join(f"{t:g}" for t in torques_wheel_nm) + " Nm.",
                "",
                _body_readme(built.body),
                "",
                "Raten (CONVERSE-Karten des Nutzers, dieselbe Faserorientierung, Werkstofftabellen je "
                "Prüfgeschwindigkeit): "
                + "; ".join(
                    f"`{rate}` = `{Path(cof).name}` ({cards[rate].name}, isotrope Zeile E = "
                    f"{cards[rate].youngs_modulus_mpa:g} MPa, ν = {cards[rate].poisson_ratio:g} bei "
                    f"{cards[rate].temperature_c:g} °C"
                    + (
                        f", Dehnrate {known_rates[rate].get('strain_rate_1_s')} 1/s"
                        if rate in known_rates
                        else ""
                    )
                    + ")"
                    for rate, cof in zip(rates, cofs, strict=True)
                )
                + ". W1 und W2 nehmen die isotrope Zeile der Karte, W3 und W4 die Orientierungsdatei "
                "der Rate (`wheel_orientation_<Rate>_*.inp`; das Elset der Section ist auf `WHEEL` "
                "umgeschrieben). In W3 und W4 schreibt die Ausgabe die Feldvariablen (FV) der Knoten "
                "und die lokalen Materialrichtungen (DIRECTIONS=YES) in die .odb; `report` prüft "
                "daraus, dass die Faserorientierung mit der Instanz mitgedreht wurde und die "
                "Feldvariablen die der Datei sind.",
                "",
                "Schritte geometrisch "
                + ", ".join(
                    f"{s}: {'nichtlinear (NLGEOM=YES)' if dk.NLGEOM_OF_STEP[s] else 'linear (NLGEOM=NO)'} "
                    f"mit {types_of_step[s]}"
                    for s in material_steps
                )
                + "; Kontakt Knoten-zu-Fläche mit Glättung der starren Facetten (SMOOTH 0,2), "
                + ENFORCEMENT_README[enforcement]
                + (
                    f", Iterationsgrenzen je Inkrement I_0/I_R/I_C = {iteration_limits[0]}/"
                    f"{iteration_limits[1]}/{iteration_limits[2]} statt 4/8/16 (*CONTROLS, "
                    "PARAMETERS=TIME INCREMENTATION): der flatternde Flankenknoten an der "
                    "Ritzelkopfkante konvergiert mit Faktor 0,85 bis 0,95 je Iteration und lief "
                    "mit 16 Iterationen in den Rückschnitt (Wiederholungsläufe 2026-10-09)"
                    if iteration_limits is not None
                    else ""
                )
                + ", keine Stabilisierung. Regel je Werkstoffstufe (`deck.NLGEOM_OF_STEP`, "
                "`deck.ELEMENT_TYPE_OF_STEP`): W1 und W3 linear mit C3D8I, W2 und W4 nichtlinear "
                "mit C3D8 auf demselben Netz, weil C3D8I mit NLGEOM=YES negative Eigenwerte erzeugt "
                "und abbricht (Elementtest 2026-10-07, FE-14); `--element-type` überschreibt.",
                "",
                *(
                    [
                        "## Varianten",
                        "",
                        "Je Variante eine Datei `pos_NNN_<Variante>.inp` mit denselben Netzdateien "
                        "und derselben Stellung; die Varianten unterscheiden sich nur in den "
                        "Löser- und Kontakteinstellungen (Kopfzeile `** steps ...` der Datei):",
                        "",
                        *[f"- `{v}`: {VARIANTS[v][1]}" for v in variants],
                        "",
                    ]
                    if variants
                    else []
                ),
                "## Rechnen auf der Vollversion",
                "",
                f"1. Diesen Ordner kopieren (die Stellungsdateien binden `{built.file_name}` und "
                "`pinion_surface.inp` ein, sie müssen daneben liegen).",
                "2. Abaqus-Eingabeaufforderung im Ordner öffnen, Datenprüfung einer Datei: "
                "`abaqus job=pos_001 datacheck interactive`.",
                "3. Alle Stellungen nacheinander: `powershell -ExecutionPolicy Bypass -File run_all.ps1` "
                "(anderer Starter: `-Launcher abq2025`, Kerne: `-Cpus 4`). Fertige Stellungen werden "
                "übersprungen; `run_log.txt` protokolliert.",
                "4. Abnahme je Stellung: `.sta` muss mit COMPLETED SUCCESSFULLY enden (ohne "
                "Stabilisierung; Löser- und Kontakteinstellung jeder Datei stehen in ihrer Kopfzeile "
                "`** steps ...`). In `pos_NNN.dat` stehen nach "
                "jedem Schritt für beide Bezugspunkte (Knoten 1 Rad, Knoten 2 Ritzel) die "
                "Reaktionskräfte RF1, RF2 (die Kontaktkraft), das Stützmoment RM3 und die Drehung "
                "UR3 sowie die Kontaktspannungen der Radflankenknoten. Das Stützmoment am Rad "
                "entspricht dem Moment am Rad ("
                + ", ".join(f"{1000 * t:g}" for t in torques_wheel_nm)
                + " N mm, Vorzeichen nach Drehsinn) bis auf die Drehung Δψ der Kontaktkraft "
                "(RF1, RF2) gegen die Eingriffslinie: ihr Hebelarm am Rad ist a·cos(α_wt + Δψ) − "
                "r_b1 statt r_b2 (bekannte Grenze FE-15).",
                "5. Nach jedem Job ruft `run_all.ps1` das Abaqus-Python mit `extract_odb.py` auf und "
                "schreibt `pos_NNN_fields.json` (Bezugspunkte, geschlossene Kontaktknoten mit "
                "Koordinaten, Druck und Normalkraft, Hauptspannungen jeder Fußrundung, "
                "Kopfverschiebungen). Zurück an die Auswertung: `.sta`, `.dat`, `.msg`, "
                "`run_log.txt` und die `_fields.json` je Stellung in diesen Ordner; die `.odb` "
                "bleibt auf dem Rechner mit der Lizenz (fehlt eine `_fields.json`, holt "
                "`build_fe_decks.py extract --folder` sie dort oder in der Learning Edition nach).",
                "6. Auswertung im Repo: `python scripts/build_fe_decks.py report --folder <dieser "
                "Ordner>` listet je Stellung und Schritt Status, Inkremente, Stützmoment, Drehung, "
                "Richtung der Kontaktkraft gegen die Eingriffslinie, Hebelarme und Kontakt, aus den "
                "Feldern je Zahnhälfte Kontaktdruck mit Ort und Normalkraft, je Fußrundung die "
                "Hauptspannungen mit Ort und die Kopfverschiebung; bei einem Stellungsgitter dazu "
                "die Kurven über dem Eingriffsweg (`path_<Schritt>.png`) und die Auflösungstabelle "
                "der Teilgitter (`path_report.md`).",
                "",
                "`manifest.json` nennt die Stellungen (Wälzweg ab A, Punkte A bis E, Winkel), die Momente, "
                "die Werkstoffkarte und die Knotenpfade der Fußrundungen.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report.append(
        f"{len(entries)} position files ({len(chosen)} positions: "
        f"{', '.join(str(label or k) for k, (label, _) in enumerate(chosen, start=1))}), "
        f"material steps {', '.join(material_steps)}, rates "
        + ", ".join(
            f"{rate} (E = {cards[rate].youngs_modulus_mpa:g} MPa, nu = {cards[rate].poisson_ratio:g} "
            f"at {cards[rate].temperature_c:g} degC)"
            for rate in rates
        )
        + ", torques at the pinion "
        + ", ".join(f"{t:.2f}" for t in torques_pinion)
        + f" N mm (sign {sign:+g}), seating angle {seating:.3e} rad; manifest.json, run_all.ps1"
    )
    return report


def synthetic_orientation_text(elements: int, nodes: int, card_text: str) -> str:
    """A CONVERSE-like orientation file for a function test: every element's local
    1-direction along +x and 2-direction along +y of the part, the field variables 0,6 and 0,1
    at every node, and the material blocks of ``card_text`` (a real CONVERSE card) unchanged.
    After the run the directions in the output database must be +x turned by the rotation of
    the wheel instance."""
    count = integer_input(elements, "number of elements")
    node_count = integer_input(nodes, "number of nodes")
    if count < 1 or node_count < 1:
        raise InputRangeError("a synthetic orientation file needs elements and nodes")
    start = card_text.find("*MATERIAL")
    end = card_text.find("*INITIAL CONDITIONS")
    if start < 0 or end < 0 or end < start:
        raise InputRangeError("the card text must hold *MATERIAL before *INITIAL CONDITIONS")
    name = dk.read_material_card(card_text, 80.0).name
    lines = [
        "** synthetic orientation file of gearcore for the function test of the orientation",
        "*DISTRIBUTION TABLE, NAME=DIS_TAB_COORD",
        " COORD3D, COORD3D",
        "*DISTRIBUTION, NAME=DIS_SYNTHETIC, LOCATION=ELEMENT, TABLE=DIS_TAB_COORD",
        " , 1.0, 0.0, 0.0, 0.0, 1.0, 0.0",
        *(f" {e}, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0" for e in range(1, count + 1)),
        "*ORIENTATION, NAME=ORI_SYNTHETIC, DEFINITION=COORDINATES",
        " DIS_SYNTHETIC",
        f"*SOLID SECTION, ELSET=CONVERSE_AUTO_SOLID, MATERIAL={name}, ORIENTATION=ORI_SYNTHETIC",
        card_text[start:end].rstrip(),
        "*INITIAL CONDITIONS, TYPE=FIELD, VARIABLE=1",
        *(f" {n}, 0.6" for n in range(1, node_count + 1)),
        "*INITIAL CONDITIONS, TYPE=FIELD, VARIABLE=2",
        *(f" {n}, 0.1" for n in range(1, node_count + 1)),
    ]
    return "\n".join(lines) + "\n"


ORIENTATION_TEST = """*HEADING
gearcore function test: an orientation defined by a distribution turns with the instance
** part: a block of two C3D8 along x with the material 1-direction along x
*PART, NAME=BLOCK
*NODE
1, 0., 0., 0.
2, 0., 2., 0.
3, 0., 2., 2.
4, 0., 0., 2.
5, 5., 0., 0.
6, 5., 2., 0.
7, 5., 2., 2.
8, 5., 0., 2.
9, 10., 0., 0.
10, 10., 2., 0.
11, 10., 2., 2.
12, 10., 0., 2.
*ELEMENT, TYPE=C3D8, ELSET=ALL
1, 1, 2, 3, 4, 5, 6, 7, 8
2, 5, 6, 7, 8, 9, 10, 11, 12
*NSET, NSET=FIX
1, 2, 3, 4
*NSET, NSET=TIP
9, 10, 11, 12
*DISTRIBUTION, NAME=D_ORI, LOCATION=ELEMENT, TABLE=T_ORI
, 1., 0., 0., 0., 1., 0.
1, 1., 0., 0., 0., 1., 0.
2, 1., 0., 0., 0., 1., 0.
*ORIENTATION, NAME=O_BLOCK, DEFINITION=COORDINATES
D_ORI
*SOLID SECTION, ELSET=ALL, MATERIAL=ORTHO, ORIENTATION=O_BLOCK
*END PART
** assembly: instance A as the part, instance B turned by 90 degrees about z
*ASSEMBLY, NAME=TEST
*INSTANCE, NAME=A, PART=BLOCK
0., 0., 0.
*END INSTANCE
*INSTANCE, NAME=B, PART=BLOCK
0., 20., 0.
0., 20., 0., 0., 20., 1., 90.
*END INSTANCE
*NSET, NSET=A_FIX, INSTANCE=A
1, 2, 3, 4
*NSET, NSET=A_TIP, INSTANCE=A
9, 10, 11, 12
*NSET, NSET=B_FIX, INSTANCE=B
1, 2, 3, 4
*NSET, NSET=B_TIP, INSTANCE=B
9, 10, 11, 12
*END ASSEMBLY
*DISTRIBUTION TABLE, NAME=T_ORI
COORD3D, COORD3D
*MATERIAL, NAME=ORTHO
*ELASTIC, TYPE=ENGINEERING CONSTANTS
10000., 1000., 1000., 0.3, 0.3, 0.3, 400., 400.,
400.
*BOUNDARY
A_FIX, 1, 3
B_FIX, 1, 3
** both blocks pulled along their own length by 100 N: A along x, B along y
*STEP, NAME=PULL
*STATIC
*CLOAD
A_TIP, 1, 25.
B_TIP, 2, 25.
*NODE PRINT, NSET=A_TIP
U
*NODE PRINT, NSET=B_TIP
U
*END STEP
"""


def _dat_tables(text: str) -> list[tuple[str, list[list[float]]]]:
    """(header, rows) of every printed node table of a .dat file (node number first)."""
    tables: list[tuple[str, list[list[float]]]] = []
    number = r"[-+]?(?:\d+\.\d*|\.\d+)(?:E[-+]?\d+)?"
    row = re.compile(rf"^\s*(\d+)\s+((?:{number}\s+)*{number})\s*$")
    for line in text.splitlines():
        if "NODE" in line and "FOOT" in line:
            tables.append((line.strip(), []))
            continue
        if tables:
            found = row.match(line)
            if found:
                values = [float(v) for v in re.findall(number, found.group(2))]
                tables[-1][1].append([float(found.group(1)), *values])
    return tables


def _contact_tables(text: str) -> list[list[tuple[int, str, float]]]:
    """Per printed contact table of a .dat file: (label, status, CPRESS) of the listed
    entries; Abaqus lists only the closed ones (status CL) and labels them with its internal
    contact element numbers, not with the node labels of the secondary surface."""
    tables: list[list[tuple[int, str, float]]] = []
    number = r"[-+]?(?:\d+\.\d*|\.\d+)(?:E[-+]?\d+)?"
    row = re.compile(rf"^\s*(\d+)\s+([A-Z]+)\s+({number})\s+{number}\s+{number}\s*$")
    for line in text.splitlines():
        if "C O N T A C T   O U T P U T" in line:
            tables.append([])
            continue
        if tables:
            found = row.match(line)
            if found:
                tables[-1].append((int(found.group(1)), found.group(2), float(found.group(3))))
    return tables


def _instance_axes(deck_text: str) -> dict[str, tuple[float, float]]:
    """Axis position (x, y) of each instance from the translation line of ``*INSTANCE``."""
    axes: dict[str, tuple[float, float]] = {}
    lines = deck_text.splitlines()
    for i, line in enumerate(lines):
        if line.upper().startswith("*INSTANCE"):
            name = line.split("NAME=")[1].split(",")[0].strip()
            fields = lines[i + 1].split(",")
            axes[name] = (float(fields[0]), float(fields[1]))
    return axes


def _instance_turns(deck_text: str) -> dict[str, float]:
    """Rotation of each instance about its own axis in degrees (the last item of the rotation
    line of ``*INSTANCE``: axis through two points, then the angle)."""
    turns: dict[str, float] = {}
    lines = deck_text.splitlines()
    for i, line in enumerate(lines):
        if line.upper().startswith("*INSTANCE"):
            name = line.split("NAME=")[1].split(",")[0].strip()
            turns[name] = float(lines[i + 2].split(",")[-1])
    return turns


def report(folder: Path) -> list[str]:
    """Evaluation of a position folder after the run, without ODB access: status and
    increments per step, support moment and rotation, the direction of the contact force
    against the line of action and the lever arms (known limit FE-15: the force stays tangent
    to the base circle of the pinion, a_1 = T_1/F, and is turned by dpsi, so that
    a_2 = a cos(alpha_wt + dpsi) - r_b1), the elastic approach, and the contact (closed nodes,
    largest contact pressure)."""
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    r_b1 = manifest["seating_arc_mm"] / manifest["seating_angle_rad"]
    torques_pinion = [float(t) for t in manifest["torques_pinion_nmm"]]
    torques_wheel = [1000.0 * float(t) for t in manifest["torques_wheel_nm"]]
    r_b2 = r_b1 * torques_wheel[0] / torques_pinion[0]
    step_names = list(manifest["step_names"])
    out = [
        f"{folder.as_posix()}: r_b1 {r_b1:.4f} mm, r_b2 {r_b2:.4f} mm, steps {', '.join(step_names)}"
    ]
    rates = manifest.get("rates") if isinstance(manifest.get("rates"), dict) else {}
    distributions: dict[str, dict[int, tuple[dk.Vector, dk.Vector]]] = {}
    field_variables: dict[str, dict[int, tuple[float, float]]] = {}

    def orientation_source(rate: str) -> str | None:
        """Path of the CONVERSE file of a rate (older manifests name one card only)."""
        if rate in rates and isinstance(rates[rate], dict):
            return str(rates[rate].get("file"))
        card = manifest.get("material_card")
        return str(card["file"]) if isinstance(card, dict) and "file" in card else None

    for entry in manifest["positions"]:
        job = Path(entry["file"]).stem
        label = entry["point"] or f"rho_1 {entry['rho_1_mm']:.4f} mm"
        step_of_entry = str(entry.get("material_step") or manifest.get("material_step") or "")
        rate_of_entry = str(entry.get("rate") or "")
        if step_of_entry:
            label += f", {step_of_entry}" + (f" {rate_of_entry}" if rate_of_entry else "")
        if entry.get("variant"):
            label += f", variant {entry['variant']}"
        deck_text = (folder / entry["file"]).read_text(encoding="utf-8")
        axes = _instance_axes(deck_text)
        wheel_turn = _instance_turns(deck_text).get(dk.WHEEL_INSTANCE, 0.0)
        o1, o2 = axes[dk.PINION_INSTANCE], axes[dk.WHEEL_INSTANCE]
        a = math.hypot(o2[0] - o1[0], o2[1] - o1[1])
        e = ((o2[0] - o1[0]) / a, (o2[1] - o1[1]) / a)
        alpha_wt = math.acos((r_b1 + r_b2) / a)
        sta = folder / f"{job}.sta"
        if not sta.exists():
            out.append(f"{job} ({label}): not run")
            continue
        sta_text = sta.read_text(errors="replace")
        status = "completed" if "COMPLETED SUCCESSFULLY" in sta_text else "NOT completed"
        increments: dict[int, int] = {}
        for line in sta_text.splitlines():
            found = re.match(r"^\s+(\d+)\s+(\d+)\s+(\d+)U?\s", line)
            if found:
                step = int(found.group(1))
                increments[step] = increments.get(step, 0) + 1
        msg = folder / f"{job}.msg"
        negatives = (
            msg.read_text(errors="replace").count("NEGATIVE EIGENVALUES") if msg.exists() else 0
        )
        out.append(
            f"{job} ({label}): {status}; increments per step "
            + ", ".join(f"{increments.get(k + 1, 0)}" for k in range(len(step_names)))
            + f"; negative-eigenvalue warnings {negatives}; a {a:.4f} mm, "
            f"alpha_wt {math.degrees(alpha_wt):.4f} deg"
        )
        dat = folder / f"{job}.dat"
        if not dat.exists():
            continue
        text = dat.read_text(errors="replace")
        tables = _dat_tables(text)
        fields_file = folder / f"{job}_fields.json"
        summaries: dict[str, ev.StepSummary] = {}
        steps_fields: dict[str, ev.StepFields] = {}
        if fields_file.exists():
            steps_fields = {s.name: s for s in ev.read_fields(fields_file).steps}
            summaries = {name: ev.step_summary(s) for name, s in steps_fields.items()}
        checks: dict[str, list[str]] = {}
        if step_of_entry in ("W3", "W4") and steps_fields:
            source = orientation_source(rate_of_entry)
            if source and rate_of_entry not in distributions:
                cof_path = Path(source)
                if cof_path.exists():
                    cof_text = cof_path.read_text(encoding="utf-8", errors="replace")
                    distributions[rate_of_entry] = dk.read_distribution(cof_text)
                    field_variables[rate_of_entry] = dk.read_field_variables(cof_text)
            if rate_of_entry in distributions:
                for name, step_fields in steps_fields.items():
                    if not step_fields.orientation:
                        continue
                    check = ev.orientation_check(
                        step_fields, distributions[rate_of_entry], wheel_turn
                    )
                    fv_check = ev.field_variable_check(step_fields, field_variables[rate_of_entry])
                    checks[name] = ev.format_orientation(check, fv_check)
                    if name != "SEAT" and bool(entry.get("nlgeom")) and not check.turned:
                        checks[name].append(
                            "    (geometrically nonlinear step: the material directions of the "
                            "output database rotate with the deformation, so the deviation grows "
                            "with the load; the placement check is the one at SEAT)"
                        )
            else:
                checks = {
                    name: [f"    orientation: CONVERSE file {source!r} not found, check skipped"]
                    for name in steps_fields
                }
        wheel = [(h, r[-1]) for h, r in tables if r and r[-1][0] == float(dk.WHEEL_REFERENCE_NODE)]
        pinion = [
            (h, r[-1]) for h, r in tables if r and r[-1][0] == float(dk.PINION_REFERENCE_NODE)
        ]
        contact = _contact_tables(text)

        def value(header: str, row: list[float], name: str) -> float | None:
            columns = header.split()
            return row[columns.index(name) - 1] if name in columns else None

        for k, ((h_w, row_w), (h_p, row_p)) in enumerate(zip(wheel, pinion, strict=False)):
            name = step_names[k] if k < len(step_names) else f"step {k + 1}"
            rm2 = value(h_w, row_w, "RM3")
            ur3 = value(h_p, row_p, "UR3")
            rm1 = value(h_p, row_p, "RM3")
            t1 = torques_pinion[k - 1] if k >= 1 else abs(rm1 or 0.0)
            parts = [f"  {name}: RM3 wheel {rm2:.2f} N mm" if rm2 is not None else f"  {name}:"]
            if rm2 is not None and t1 > 0.0:
                parts.append(
                    f" ({(abs(rm2) / (t1 * r_b2 / r_b1) - 1.0) * 100:+.3f} % vs z_2/z_1 T_1)"
                )
            if ur3 is not None:
                parts.append(
                    f"; pinion rotation {ur3:.4e} rad = {abs(ur3) * r_b1 * 1000:.1f} um at r_b1"
                )
            rf1, rf2 = value(h_p, row_p, "RF1"), value(h_p, row_p, "RF2")
            if rf1 is not None and rf2 is not None and rm2 is not None and t1 > 0.0:
                force = math.hypot(rf1, rf2)
                if force > 0.0:
                    f = (rf1 / force, rf2 / force)
                    cos_psi = abs(e[0] * f[1] - e[1] * f[0])
                    psi = math.acos(min(1.0, cos_psi))
                    a1, a2 = t1 / force, abs(rm2) / force
                    predicted = a * cos_psi - r_b1
                    parts.append(
                        f"; |F| {force:.3f} N, force turned {math.degrees(psi - alpha_wt):+.4f} deg "
                        f"against the line of action, a_1/r_b1 {a1 / r_b1:.5f}, a_2/r_b2 "
                        f"{a2 / r_b2:.5f} (formula a cos(alpha_wt + dpsi) - r_b1: "
                        f"{predicted / r_b2:.5f})"
                    )
            if k < len(contact):
                closed = [(p, label) for label, status_, p in contact[k] if status_ == "CL"]
                largest, at = max(closed, default=(0.0, 0))
                parts.append(
                    f"; contact: {len(closed)} closed nodes, largest CPRESS {largest:.2f} MPa"
                    + (
                        f" (contact element {at}; the location needs the ODB)"
                        if at and name not in summaries
                        else ""
                    )
                )
            out.append("".join(parts))
            if name in summaries:
                out.extend(ev.format_summary(summaries[name]))
            out.extend(checks.get(name, []))
    out.extend(_path_report(folder, manifest))
    return out


PATH_QUANTITIES = ("pinion_rotation_rad", "p_max", "s1_max", "s3_min", "u_head_max")


def _path_report(folder: Path, manifest: dict[str, object]) -> list[str]:
    """Curves over the path of contact (one picture per load step and series) and the
    resolution table of the sub-grids (``path_report.md``) for a folder with extracted fields
    of three or more positions; a series is one material step, rate and variant."""
    lines: list[str] = []
    document = ["# Auswertung über dem Eingriffsweg", ""]
    series = ev.series_names(manifest)
    for name in series:
        points = [p for p in ev.path_points(manifest, folder, name) if p.summaries]
        if len(points) < 3:
            continue
        lines.extend(
            _path_series(folder, manifest, name if len(series) > 1 else "", points, document)
        )
    if len(document) > 2:
        (folder / "path_report.md").write_text("\n".join(document) + "\n", encoding="utf-8")
    return lines


def _path_series(
    folder: Path,
    manifest: dict[str, object],
    series: str,
    points: list[ev.PathPoint],
    document: list[str],
) -> list[str]:
    """The pictures and the resolution rows of one series (``series`` empty: the only one)."""
    r_b1 = float(manifest["seating_arc_mm"]) / float(manifest["seating_angle_rad"])  # type: ignore[arg-type]
    names = manifest["step_names"]
    step_names = [str(s) for s in names if s != "SEAT"] if isinstance(names, list) else []
    grid = manifest.get("grid")
    grid = grid if isinstance(grid, dict) else {}
    halves = sorted(
        {f"{t.tooth}_{t.side}" for p in points for s in p.summaries.values() for t in s.teeth}
    )
    fillets = sorted({f.name for p in points for s in p.summaries.values() for f in s.fillets})
    named = [(p.from_a_mm, p.label) for p in points if p.label]
    tag = f"{series}: " if series else ""
    incomplete = sorted({p.job for p in points for s in p.summaries.values() if not s.complete})
    lines = [
        f"{tag}path of contact: {len(points)} positions with extracted fields"
        + (
            f"; broken-off steps left out of the curves at {', '.join(incomplete)}"
            if incomplete
            else ""
        )
    ]
    for step in step_names:
        fig, axes = plt.subplots(4, 1, figsize=(8.0, 11.0), sharex=True)
        rotation = ev.curve(points, step, "pinion_rotation_rad")
        axes[0].plot([x for x, _ in rotation], [v * r_b1 * 1000.0 for _, v in rotation], ".-")
        axes[0].set_ylabel("Ritzeldrehung · r_b1 in µm")
        for half in halves:
            pressure = ev.curve(points, step, f"p:{half}")
            axes[1].plot([x for x, _ in pressure], [v for _, v in pressure], ".-", label=half)
        axes[1].set_ylabel("CPRESS max in MPa")
        axes[1].legend(fontsize=7, ncol=2)
        s1 = ev.curve(points, step, "s1_max")
        s3 = ev.curve(points, step, "s3_min")
        axes[2].plot([x for x, _ in s1], [v for _, v in s1], ".-", label="σ1 max (Zug)")
        axes[2].plot([x for x, _ in s3], [v for _, v in s3], ".-", label="|σ3| max (Druck)")
        axes[2].set_ylabel("Fußspannung in MPa")
        axes[2].legend(fontsize=7)
        any_force = False
        for half in halves:
            force = ev.curve(points, step, f"force:{half}")
            if any(v for _, v in force):
                any_force = True
                axes[3].plot([x for x, _ in force], [v for _, v in force], ".-", label=half)
        axes[3].set_ylabel(
            "Normalkraft je Zahnhälfte in N" if any_force else "Normalkraft: ohne CFORCE"
        )
        if any_force:
            axes[3].legend(fontsize=7, ncol=2)
        axes[3].set_xlabel("Wälzweg ab A in mm")
        for ax in axes:
            for x, _ in named:
                ax.axvline(x, color="0.7", linewidth=0.7)
            ax.grid(True, linewidth=0.4)
        for x, label in named:
            axes[0].text(x, axes[0].get_ylim()[1], label, ha="center", va="bottom", fontsize=8)
        fig.suptitle(f"{Path(folder).name}: {tag}{step}")
        fig.tight_layout()
        picture = folder / (f"path_{series}_{step}.png" if series else f"path_{step}.png")
        fig.savefig(picture, dpi=150)
        plt.close(fig)
        lines.append(f"  {tag}{step}: {picture.name}")
        steps_per_pitch = grid.get("steps_per_pitch")
        base_pitch = grid.get("transverse_base_pitch_mm")
        margin = grid.get("margin_pitches")
        if not (isinstance(steps_per_pitch, int) and isinstance(base_pitch, float)):
            continue
        factors = [
            f
            for f in (1, 2, 3, 4, 5, 6, 10, 12)
            if steps_per_pitch % f == 0 and steps_per_pitch / f >= 4
        ]
        # the global maxima first, then per tooth half and per fillet (the maxima of one tooth
        # over its own history, so that a maximum does not jump to the same point of the
        # neighbouring tooth one pitch away)
        quantities = [
            *PATH_QUANTITIES,
            *(f"force:{h}" for h in halves if any_force),
            *(f"s1:{f}" for f in fillets),
            *(f"s3:{f}" for f in fillets),
        ]
        rows = ev.resolution_rows(
            points, step, quantities, steps_per_pitch, base_pitch, float(margin or 0.0), factors
        )
        table = ev.format_resolution(rows)
        document.extend([f"## {tag}{step}", "", *table, ""])
        coarse = [
            r
            for r in rows
            if r.steps_per_pitch == rows[-1].steps_per_pitch and r.quantity in PATH_QUANTITIES
        ]
        lines.append(
            f"  {tag}{step}: resolution table with {len(factors)} sub-grids in path_report.md; "
            f"coarsest ({rows[-1].steps_per_pitch} per pitch) shifts the global maxima by up to "
            f"{max(abs(r.shift_mm) for r in coarse):.3f} mm and changes them by up to "
            f"{max(abs(r.change) for r in coarse) * 100:.2f} %"
            if rows and coarse
            else f"  {tag}{step}: no resolution table (no curves)"
        )
    return lines


report_folder = report
"""``report`` under a name the local report list of ``le_tests`` does not shadow."""


def le_tests(out: Path, run: bool) -> list[str]:
    """The small models of the Learning Edition: the coarse pair with the complete structure
    of a position file (parts, instances, rigid bodies, contact, seating and load steps), the
    same pair on the body with pockets, the pair in W3 with a synthetic orientation file
    (orientation and field variables read back from the output database), and the
    orientation test of section 2b of the plan."""
    report: list[str] = []
    pair_dir = out / "pair_coarse"
    report.extend(
        decks(
            "kst_e",
            teeth=1,
            rim_rings=12,
            layers=2,
            element_type="C3D8I",
            counts=LE_COUNTS,
            bore_radius_mm=None,
            rotation="clockwise",
            material_steps=["W1"],
            cofs=[REFERENCE_COF],
            rates=["QS"],
            temperature_c=80.0,
            torques_wheel_nm=[8.0, 12.0, 16.0],
            positions=["pilot"],
            steps_per_pitch=12,
            margin=0.5,
            seating_arc_mm=0.01,  # the coarse rigid profile (0,4 mm chords) lies up to 2 um inside the involute
            max_edge_mm=0.4,
            out=pair_dir,
        )
    )
    report.append(f"pair_coarse written to {pair_dir.as_posix()}")
    # the same coarse pair on the body with pockets: hub, web and rim one ring each, one layer
    # per pocket depth and two over the web (the smallest body the carving allows); the tooth
    # and the rigid profile coarser than above so that the five levels stay below 1000 nodes
    pocket_dir = out / "pair_coarse_pocket"
    report.extend(
        decks(
            "kst_e",
            teeth=1,
            rim_rings=12,
            layers=4,
            element_type="C3D8I",
            counts=LE_POCKET_COUNTS,
            bore_radius_mm=bd.body_section("kst_e", "wheel").bore_radius_mm,
            rotation="clockwise",
            material_steps=["W1"],
            cofs=[REFERENCE_COF],
            rates=["QS"],
            temperature_c=80.0,
            torques_wheel_nm=[8.0, 12.0, 16.0],
            positions=["pilot"],
            steps_per_pitch=12,
            margin=0.5,
            seating_arc_mm=0.01,
            max_edge_mm=0.6,
            out=pocket_dir,
            body="pocket",
            body_counts=bd.BodyCounts(
                hub_rings=1, pocket_rings=1, rim_rings=1, web_layers=2, flange_layers=1
            ),
        )
    )
    report.append(f"pair_coarse_pocket written to {pocket_dir.as_posix()}")
    # the coarse pair in the material step W3 with a synthetic orientation file: every
    # element's 1-direction along +x of the part, the field variables 0,6 / 0,1 at every node,
    # the material tables of the reference card; after the run the extraction reads the
    # material directions and the field variables back and the report checks that the
    # directions are +x turned by the rotation of the wheel instance (orientation turned with
    # the instance) and the field variables those of the file
    w3_dir = out / "pair_coarse_w3"
    coarse = mesh("kst_e", "wheel", 1, 12, 2, "C3D8I", w3_dir, LE_COUNTS, None)
    synthetic = w3_dir / "synthetic_orientation.cof"
    synthetic.write_text(
        synthetic_orientation_text(
            len(coarse.solid.hexes),
            len(coarse.solid.nodes_mm),
            REFERENCE_COF.read_text(encoding="utf-8", errors="replace"),
        ),
        encoding="ascii",
    )
    report.extend(
        decks(
            "kst_e",
            teeth=1,
            rim_rings=12,
            layers=2,
            element_type="C3D8I",
            counts=LE_COUNTS,
            bore_radius_mm=None,
            rotation="clockwise",
            material_steps=["W3"],
            cofs=[synthetic],
            rates=["SYN"],
            temperature_c=80.0,
            torques_wheel_nm=[8.0, 12.0, 16.0],
            positions=["pilot"],
            steps_per_pitch=12,
            margin=0.5,
            seating_arc_mm=0.01,
            max_edge_mm=0.4,
            out=w3_dir,
        )
    )
    report.append(f"pair_coarse_w3 (synthetic orientation file) written to {w3_dir.as_posix()}")
    orientation_dir = out / "orientation"
    orientation_dir.mkdir(parents=True, exist_ok=True)
    (orientation_dir / "orientation.inp").write_text(ORIENTATION_TEST, encoding="ascii")
    report.append(f"orientation test written to {orientation_dir.as_posix()}")
    if not run:
        return report
    for folder, job in (
        (orientation_dir, "orientation"),
        (pair_dir, "pos_001"),
        (pocket_dir, "pos_001"),
        (w3_dir, "pos_001"),
    ):
        command = f'"{LEARNING_EDITION}" job={job} input={job}.inp interactive ask_delete=OFF'
        completed = subprocess.run(
            command, cwd=folder, shell=True, capture_output=True, text=True, timeout=1800
        )
        (folder / f"{job}.console.txt").write_text(
            completed.stdout + completed.stderr, encoding="utf-8"
        )
        sta = folder / f"{job}.sta"
        status = "no .sta file"
        if sta.exists():
            status = (
                "completed"
                if "COMPLETED SUCCESSFULLY" in sta.read_text(errors="replace")
                else "NOT completed"
            )
        report.append(f"{folder.name} {job}: {status}")
        dat = folder / f"{job}.dat"
        if not dat.exists():
            continue
        tables = _dat_tables(dat.read_text(errors="replace"))
        if job == "orientation":
            tips = [rows for header, rows in tables if rows]
            if len(tips) >= 2:
                u_a = sum(r[1] for r in tips[-2]) / len(tips[-2])
                u_b = sum(r[2] for r in tips[-1]) / len(tips[-1])
                report.append(
                    f"orientation: u_x of A_TIP {u_a:.4e} mm, u_y of B_TIP {u_b:.4e} mm, ratio B/A "
                    f"{u_b / u_a:.3f} (1 = the orientation turned with the instance, 10 = it did not)"
                )
        else:
            moments = [
                rows[-1][header.split().index("RM3") - 1]
                for header, rows in tables
                if "RM3" in header and rows and rows[-1][0] == 1.0
            ]
            report.append(
                f"{folder.name} pos_001: support moment RM3 at the wheel reference point per "
                "printed step: "
                + ", ".join(f"{m:.2f}" for m in moments)
                + " N mm (expected 8000, 12000, 16000 after the seating step)"
            )
    # the orientation check of the W3 model: extraction with the Python of the Learning
    # Edition, then the report lines of the check
    if (w3_dir / "pos_001.odb").exists():
        stale = w3_dir / "pos_001_fields.json"  # of an earlier run of this test
        if stale.exists():
            stale.unlink()
        report.extend(extract(w3_dir, LEARNING_EDITION))
        report.extend(
            f"pair_coarse_w3 {line.strip()}"
            for line in report_folder(w3_dir)
            if "orientation:" in line or "field variables" in line
        )
    return report


# --- simulation diary ----------------------------------------------------------------------------

LOG_NOTES = REPO_ROOT / "20_code" / "00_development_documentation" / "fe_simulation_notes.yaml"
LOG_FILE = REPO_ROOT / "20_code" / "00_development_documentation" / "fe_simulation_log.md"
RUN_LOG_LINE = re.compile(r"^(\S+) (start|end) (\S+)(?: exit (-?\d+), (.*))?$")
STA_LINE = re.compile(r"^\s+(\d+)\s+(\d+)\s+(\d+)U?\s")


def _sta_state(text: str) -> tuple[str, dict[int, int], str]:
    """Status of a .sta file (``complete``, ``not completed``, ``open`` = no closing line, the
    job is running or crashed), the increments per step and the last increment written."""
    increments: dict[int, int] = {}
    last = ""
    for line in text.splitlines():
        found = STA_LINE.match(line)
        if found:
            step = int(found.group(1))
            increments[step] = increments.get(step, 0) + 1
            last = f"step {step} inc {found.group(2)}"
    if "COMPLETED SUCCESSFULLY" in text:
        return "complete", increments, last
    if "NOT BEEN COMPLETED" in text:
        return "not completed", increments, last
    return "open", increments, last


def _text_of(path: Path) -> str:
    """Text of a file the runner or Abaqus wrote: UTF-16 with a byte order mark (PowerShell's
    ``Out-File`` default on Windows), else UTF-8."""
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def _run_times(folder: Path) -> dict[str, tuple[str, float | None]]:
    """job -> (time of the end line, wall-clock seconds) from ``run_log.txt`` of the runner."""
    out: dict[str, tuple[str, float | None]] = {}
    path = folder / "run_log.txt"
    if not path.exists():
        return out
    starts: dict[str, datetime] = {}
    for raw in _text_of(path).splitlines():
        found = RUN_LOG_LINE.match(raw.strip())
        if not found:
            continue
        stamp, kind, job = found.group(1), found.group(2), found.group(3)
        try:
            when = datetime.fromisoformat(stamp)
        except ValueError:
            continue
        if kind == "start":
            starts[job] = when
        else:
            wall = (when - starts[job]).total_seconds() if job in starts else None
            out[job] = (stamp, wall)
    return out


def _deck_settings(deck_path: Path) -> dict[str, str]:
    """Material step, rate, geometric nonlinearity, contact and solver options of a position
    file, in short form: from its heading lines where they exist (since 2026-10-06), else
    from the ``*STEP`` and ``*CONTACT PAIR`` lines (the first pilots)."""
    out: dict[str, str] = {}
    if not deck_path.exists():
        return out
    text = deck_path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        upper = line.upper()
        if line.startswith("** material step"):
            head = line[len("** material step") :].split(",")
            out["step"] = head[0].strip()
            for item in head[1:]:
                if item.strip().startswith("rate "):
                    out["rate"] = item.strip()[5:]
        elif upper.startswith("*STEP") and "nlgeom" not in out:
            out["nlgeom"] = "NLGEOM" if "NLGEOM=YES" in upper else "linear"
        elif upper.startswith("*CONTACT PAIR"):
            if "NODE TO SURFACE" in upper:
                smooth = (
                    upper.split("SMOOTH=")[1].split(",")[0].strip() if "SMOOTH=" in upper else "0.2"
                )
                out["contact"] = f"N2S {smooth}"
            else:
                out["contact"] = "S2S"
        elif upper.startswith("*SURFACE BEHAVIOR") and "DIRECT" in upper:
            out["enforcement"] = "DIRECT"
        elif upper.startswith("*SURFACE BEHAVIOR") and "PENALTY" in upper:
            out["enforcement"] = "PENALTY"
        elif upper.startswith("*CONTROLS") and "LINE SEARCH" in upper:
            out["line_search"] = "LS"
    return out


def _solver_label(settings: dict[str, str]) -> str:
    """One cell: ``linear, N2S 0.2`` or ``NLGEOM, S2S, DIRECT, LS``."""
    return ", ".join(
        settings[k] for k in ("nlgeom", "contact", "enforcement", "line_search") if k in settings
    )


def _dat_wallclock(text: str) -> float | None:
    """The wall-clock seconds of the job time summary at the end of a .dat file."""
    found = re.search(r"WALLCLOCK TIME \(SEC\)\s*=\s*([\d.]+)", text)
    return float(found.group(1)) if found else None


def _dat_results(text: str, manifest: dict[str, object]) -> dict[str, str]:
    """The key numbers of the last printed step of a .dat file (a run without a fields
    file): deviation of the support moment, rotation of the pinion, largest contact pressure
    of the closed nodes (without its place, which needs the output database)."""
    names = manifest.get("step_names")
    torques = manifest.get("torques_wheel_nm")
    arc, angle = manifest.get("seating_arc_mm"), manifest.get("seating_angle_rad")
    if not (isinstance(names, list) and isinstance(torques, list)):
        return {}
    r_b1 = arc / angle if isinstance(arc, float) and isinstance(angle, float) else None
    tables = _dat_tables(text)
    wheel = [(h, r[-1]) for h, r in tables if r and r[-1][0] == float(dk.WHEEL_REFERENCE_NODE)]
    pinion = [(h, r[-1]) for h, r in tables if r and r[-1][0] == float(dk.PINION_REFERENCE_NODE)]
    if not wheel or not pinion:
        return {}
    k = min(len(wheel), len(pinion)) - 1
    out = {"step": str(names[k]) if k < len(names) else f"step {k + 1}"}

    def value(header: str, row: list[float], name: str) -> float | None:
        columns = header.split()
        return row[columns.index(name) - 1] if name in columns else None

    rm3 = value(wheel[k][0], wheel[k][1], "RM3")
    if rm3 is not None and 1 <= k <= len(torques):
        out["rm3"] = f"{(abs(rm3) / (1000.0 * float(torques[k - 1])) - 1.0) * 100:+.2f} %"
    ur3 = value(pinion[k][0], pinion[k][1], "UR3")
    if ur3 is not None and r_b1 is not None:
        out["rotation"] = f"{abs(ur3) * r_b1 * 1000.0:.1f}"
    contact = _contact_tables(text)
    if k < len(contact):
        closed = [p for _, status, p in contact[k] if status == "CL"]
        if closed:
            out["cpress"] = f"{max(closed):.1f}"
            out["cpress_at"] = f"({len(closed)} geschlossene Knoten, Ort nur mit .odb)"
    return out


def _table(columns: tuple[str, ...], rows: list[list[str]]) -> list[str]:
    """A markdown table whose columns are padded to equal width, so that the source reads as
    a table too."""
    widths = [max(len(c), *(len(r[i]) for r in rows)) for i, c in enumerate(columns)]
    line = "| " + " | ".join(c.ljust(w) for c, w in zip(columns, widths, strict=True)) + " |"
    rule = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    body = [
        "| " + " | ".join(c.ljust(w) for c, w in zip(r, widths, strict=True)) + " |" for r in rows
    ]
    return [line, rule, *body]


def _key_results(
    fields_path: Path, manifest: dict[str, object], entry: dict[str, object], teeth_z2: int | None
) -> dict[str, str]:
    """The key numbers of the last load step that has fields: deviation of the support
    moment, rotation of the pinion, largest contact pressure with its place, largest root
    stress with fillet, place and the tangent angle at that place, most compressive root
    stress, largest head displacement."""
    fields = ev.read_fields(fields_path)
    loads = [s for s in fields.steps if s.name != "SEAT"]
    if not loads:
        return {}
    # the last load step that reached its end; a broken-off step holds the state of its last
    # converged increment only and is named with its step time
    finished = [s for s in loads if abs(s.time - 1.0) < 1.0e-9]
    step = finished[-1] if finished else loads[-1]
    summary = ev.step_summary(step)
    out = {"step": step.name if finished else f"{step.name} (abgebrochen bei t = {step.time:.3f})"}
    names = manifest.get("step_names")
    torques = manifest.get("torques_wheel_nm")
    arc, angle = manifest.get("seating_arc_mm"), manifest.get("seating_angle_rad")
    r_b1 = arc / angle if isinstance(arc, float) and isinstance(angle, float) else None
    if (
        summary.wheel_moment_nmm is not None
        and isinstance(names, list)
        and isinstance(torques, list)
        and step.name in names
        and names.index(step.name) - 1 < len(torques)
    ):
        expected = 1000.0 * float(torques[names.index(step.name) - 1])
        out["rm3"] = f"{(abs(summary.wheel_moment_nmm) / expected - 1.0) * 100:+.2f} %"
    if summary.pinion_rotation_rad is not None and r_b1 is not None:
        out["rotation"] = f"{abs(summary.pinion_rotation_rad) * r_b1 * 1000.0:.1f}"
    at = summary.p_max_at
    if at is not None:
        out["cpress"] = f"{summary.p_max:.1f}"
        out["cpress_at"] = f"{at.tooth} {at.side}, r {at.r:.2f}, z {at.z:+.1f}"
    extreme = summary.s1_max_fillet
    if extreme is not None:
        layer = extreme.s1_layer
        fillet = step.fillets[extreme.name]
        point = next((n for n in (*fillet.nodes, *fillet.mid_width) if n.n == layer.n_s1), None)
        tangent = None
        centre = entry.get("wheel_tooth_centre_angle_deg")
        mesh = manifest.get("wheel_mesh")
        teeth = mesh.get("teeth") if isinstance(mesh, dict) else None
        if point is not None and teeth_z2 and isinstance(centre, float) and isinstance(teeth, int):
            right = int(extreme.name.split("_")[1][1:])
            pitch = 360.0 / teeth_z2
            right_centre = centre + (right - rf.middle_tooth(teeth)) * pitch
            tangent = ev.tangent_angle_deg(
                fillet, (point.x, point.y), fields.wheel_axis, right_centre, pitch
            )
        out["s1"] = f"{extreme.s1_max:.1f}"
        out["s1_at"] = f"{extreme.name}, r {layer.r_s1:.2f}, z {layer.z:+.1f}" + (
            f", Tangente {tangent:.0f}°" if tangent is not None else ""
        )
    if summary.s3_min_fillet is not None:
        out["s3"] = f"{summary.s3_min:.1f}"
        out["s3_at"] = summary.s3_min_fillet.name
    if summary.u_head_tooth:
        out["head"] = f"{summary.u_head_max * 1000.0:.1f}"
        out["head_at"] = summary.u_head_tooth
    return out


def _folder_stamp(folder: Path) -> datetime:
    """When the folder was last worked on: the newest .sta, else the manifest, else any file."""
    for pattern in ("*.sta", "manifest.json", "*"):
        files = [p for p in folder.glob(pattern) if p.is_file()]
        if files:
            return datetime.fromtimestamp(max(p.stat().st_mtime for p in files))
    return datetime.fromtimestamp(folder.stat().st_mtime)


def _note_lines(note: dict[str, object]) -> list[str]:
    if not note:
        return ["(keine Notiz in fe_simulation_notes.yaml)"]
    parts = []
    if note.get("purpose"):
        parts.append(f"**Zweck:** {note['purpose']}.")
    if note.get("outcome"):
        parts.append(f"**Ergebnis:** {note['outcome']}.")
    if note.get("status"):
        parts.append(f"**Stand:** {note['status']}.")
    extras = []
    if note.get("machine") and note["machine"] != "-":
        extras.append(f"gerechnet: {note['machine']}")
    findings = note.get("findings")
    if isinstance(findings, list) and findings:
        extras.append("Befunde " + ", ".join(str(f) for f in findings))
    if extras:
        parts.append("(" + "; ".join(extras) + ")")
    return [" ".join(parts)]


def _mesh_line(manifest: dict[str, object]) -> str:
    mesh = manifest.get("wheel_mesh")
    if not isinstance(mesh, dict):
        return ""
    body = mesh.get("body")
    shape = body.get("shape") if isinstance(body, dict) else "ring"
    types = mesh.get("files")
    element = ", ".join(types) if isinstance(types, dict) else str(mesh.get("element_type", ""))
    listed_steps = manifest.get("material_steps")
    steps = listed_steps if isinstance(listed_steps, list) else [manifest.get("material_step", "")]
    rates = manifest.get("rates")
    rate_names = ", ".join(rates) if isinstance(rates, dict) else "QS (eine Karte)"
    torques = manifest.get("torques_wheel_nm")
    grid = manifest.get("grid")
    entries = manifest.get("positions")
    positions = len(entries) if isinstance(entries, list) else 0
    chosen = grid.get("positions") if isinstance(grid, dict) else None
    where = ", ".join(str(p) for p in chosen) if isinstance(chosen, list) else ""
    bore = mesh.get("bore_radius_mm")
    return (
        f"Netz: {mesh.get('nodes')} Knoten, {mesh.get('elements')} Elemente ({element}), "
        f"{mesh.get('layers')} Schichten, Bohrung r "
        f"{bore:.3f} mm, Körper {shape}; "
        if isinstance(bore, float)
        else f"Netz: {mesh.get('nodes')} Knoten, {mesh.get('elements')} Elemente ({element}), "
        f"{mesh.get('layers')} Schichten, Körper {shape}; "
    ) + (
        f"Werkstoffstufen {', '.join(str(s) for s in steps)}, Raten {rate_names}; Momente am Rad "
        + (", ".join(f"{t:g}" for t in torques) if isinstance(torques, list) else "?")
        + " Nm; "
        + (
            f"{positions} Stellungsdateien ({where}, {grid.get('steps_per_pitch')} je Teilung)"
            if isinstance(grid, dict)
            else f"{positions} Stellungsdateien"
        )
    )


RUN_COLUMNS = (
    "Datei",
    "Stellung",
    "Stufe",
    "Rate",
    "Variante",
    "Löser",
    "Status",
    "Inkremente je Schritt",
    "Wand s",
    "neg. EW",
    "Ende",
)
VALUE_COLUMNS = (
    "Datei",
    "Schritt",
    "RM3 Abw.",
    "Drehung µm",
    "CPRESS max MPa",
    "Ort",
    "σ1 max MPa",
    "Fußrundung, Ort, Tangente",
    "σ3 min MPa",
    "Fußrundung",
    "Kopf µm",
    "Zahn",
)


def simulation_log(root: Path, notes_path: Path, out: Path) -> list[str]:
    """Write the simulation diary: every output folder below ``root`` with its purpose and
    outcome (``notes_path``), its mesh and settings (manifest), and per position file the
    status, increments, wall-clock time, negative-eigenvalue warnings and the key results of
    the last load step (fields file, else the support moments of the .dat). Returns the
    report lines."""
    loaded = yaml.safe_load(notes_path.read_text(encoding="utf-8")) if notes_path.exists() else {}
    notes = loaded.get("folders", {}) if isinstance(loaded, dict) else {}
    if not isinstance(notes, dict):
        raise InputRangeError(f"{notes_path}: expected a mapping 'folders'")
    folders = sorted(
        {
            p.parent
            for pattern in ("*.inp", "*.sta", "manifest.json")
            for p in root.rglob(pattern)
            if p.is_file()
        },
        key=lambda f: (_folder_stamp(f), f.as_posix()),
    )
    z2_of: dict[str, int] = {}
    counts = {"complete": 0, "not completed": 0, "open": 0, "not run": 0}
    blocks: list[str] = []
    for folder in folders:
        name = folder.relative_to(root).as_posix()
        note = notes.get(name, {})
        stamp = _folder_stamp(folder)
        manifest_path = folder / "manifest.json"
        loaded_manifest = (
            json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        )
        # the convergence folders carry a manifest of their own (a list of decks)
        manifest: dict[str, object] = loaded_manifest if isinstance(loaded_manifest, dict) else {}
        times = _run_times(folder)
        lines = [
            f"## {stamp:%Y-%m-%d %H:%M} `{name}`",
            "",
            *_note_lines(note if isinstance(note, dict) else {}),
            "",
        ]
        mesh_line = _mesh_line(manifest)
        if mesh_line:
            lines.extend([mesh_line, ""])
        listed = manifest.get("positions")
        entries: list[object]
        if isinstance(listed, list):
            entries = list(listed)
            plain = False
        else:
            jobs = sorted(p.stem for p in folder.glob("*.inp"))
            entries = [{"file": f"{job}.inp", "point": ""} for job in jobs]
            plain = True
        case = str(manifest.get("case", ""))
        if case and case not in z2_of:
            z2_of[case] = _generation(case).gears.wheel.number_of_teeth
        runs: list[list[str]] = []
        values: list[list[str]] = []
        not_run: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            job = Path(str(entry["file"])).stem
            sta = folder / f"{job}.sta"
            if sta.exists():
                status, increments, last = _sta_state(_text_of(sta))
            elif (folder / f"{job}.odb").exists():
                status, increments, last = "open", {}, "odb without .sta"
            else:
                counts["not run"] += 1
                not_run.append(job)
                continue
            counts[status] += 1
            msg = folder / f"{job}.msg"
            negatives = _text_of(msg).count("NEGATIVE EIGENVALUES") if msg.exists() else 0
            settings = _deck_settings(folder / str(entry["file"]))
            step = str(
                entry.get("material_step")
                or settings.get("step")
                or manifest.get("material_step")
                or ""
            )
            rate = str(entry.get("rate") or settings.get("rate") or "")
            if not rate:
                # folders written before the rates were an axis: the rate is in the card name
                card = manifest.get("material_card")
                card_name = str(card.get("name", "")) if isinstance(card, dict) else ""
                rate = next((r for r in ("QS", "DY1", "DY2") if f"_{r}_" in card_name), "")
            variant = str(entry.get("variant") or "")
            label = str(entry.get("point") or "")
            rho = entry.get("rho_1_mm")
            position = label or (f"ρ1 {rho:.3f}" if isinstance(rho, float) else "")
            when, wall = times.get(job, ("", None))
            dat = folder / f"{job}.dat"
            dat_text = _text_of(dat) if dat.exists() else ""
            if wall is None and dat_text and status == "complete":
                # the time summary of a broken-off job covers the pre-processing only
                wall = _dat_wallclock(dat_text)
            if not when and sta.exists():
                when = datetime.fromtimestamp(sta.stat().st_mtime).strftime("%Y-%m-%dT%H:%M")
            fields_path = folder / f"{job}_fields.json"
            results: dict[str, str] = {}
            if fields_path.exists() and not plain:
                results = _key_results(fields_path, manifest, entry, z2_of.get(case))
            elif dat_text and not plain:
                results = _dat_results(dat_text, manifest)
            runs.append(
                [
                    f"`{job}`",
                    position,
                    step,
                    rate,
                    variant,
                    _solver_label(settings),
                    status + (f" ({last})" if status != "complete" and last else ""),
                    ", ".join(str(increments[k]) for k in sorted(increments)),
                    f"{wall:.0f}" if wall is not None else "",
                    str(negatives),
                    when[:16].replace("T", " "),
                ]
            )
            if results:
                values.append(
                    [
                        f"`{job}`",
                        results.get("step", ""),
                        results.get("rm3", ""),
                        results.get("rotation", ""),
                        results.get("cpress", ""),
                        results.get("cpress_at", ""),
                        results.get("s1", ""),
                        results.get("s1_at", ""),
                        results.get("s3", ""),
                        results.get("s3_at", ""),
                        results.get("head", ""),
                        results.get("head_at", ""),
                    ]
                )
        if runs:
            lines.extend(["**Läufe**", "", *_table(RUN_COLUMNS, runs), ""])
        if values:
            lines.extend(
                [
                    "**Kennwerte des letzten gedruckten Lastschritts**",
                    "",
                    *_table(VALUE_COLUMNS, values),
                    "",
                ]
            )
        if not_run:
            shown = ", ".join(f"`{j}`" for j in not_run[:6]) + (" …" if len(not_run) > 6 else "")
            lines.extend([f"Nicht gerechnet: {len(not_run)} Dateien ({shown}).", ""])
        blocks.extend(lines)
    header = [
        "# Simulationstagebuch (generiert)",
        "",
        f"Stand {datetime.now():%Y-%m-%d %H:%M}; Quelle `{root.as_posix()}`; Notizen "
        f"`{notes_path.name}`; erzeugt von `build_fe_decks.py log`. Ein Abschnitt je Ordner in der "
        "Reihenfolge der letzten Bearbeitung, mit Zweck und Ergebnis aus den Notizen, Netz und "
        "Einstellungen aus `manifest.json`, dann zwei Tabellen: **Läufe** je Stellungsdatei mit "
        "Status aus `.sta` (complete, not completed mit dem letzten geschriebenen Inkrement, open = "
        "ohne Schlusszeile: läuft oder abgestürzt), Inkrementen je Schritt, Rechenzeit (Wanduhr aus "
        "`run_log.txt`, sonst aus der Zeitbilanz der `.dat`), Warnungen negativer Eigenwerte aus "
        "`.msg` und Endzeit; **Kennwerte** des letzten gedruckten Lastschritts aus "
        "`<job>_fields.json` (RM3-Abweichung gegen z_2/z_1·T_1, Drehung des Ritzels am Grundkreis "
        "in µm, größter Kontaktdruck mit Zahnhälfte und Ort, größte Fußspannung σ1 mit Fußrundung, "
        "Ort und Tangentenwinkel zur Zahnmittellinie, kleinste σ3 mit Fußrundung, größte "
        "Kopfverschiebung mit Zahn), für Läufe ohne Felddatei aus der `.dat` (Moment, Drehung, "
        "Druck ohne Ort). Löser: linear oder NLGEOM, N2S = Knoten-zu-Fläche mit SMOOTH, S2S = "
        "Fläche-zu-Fläche, DIRECT/PENALTY = Zwangsbedingung, LS = Line Search.",
        "",
        f"Läufe: {counts['complete']} vollständig, {counts['not completed']} abgebrochen, "
        f"{counts['open']} offen, {counts['not run']} Dateien nicht gerechnet; {len(folders)} Ordner.",
        "",
    ]
    out.write_text("\n".join(header + blocks) + "\n", encoding="utf-8")
    return [
        f"{out.as_posix()}: {len(folders)} folders, {counts['complete']} complete, "
        f"{counts['not completed']} not completed, {counts['open']} open, {counts['not run']} not run"
    ]


def _body_arguments(parser: argparse.ArgumentParser) -> None:
    """The options of the wheel body (``mesh`` and ``decks``)."""
    preset = bd.BodyCounts()
    parser.add_argument(
        "--body",
        choices=bd.BODY_SHAPES,
        default="ring",
        help="ring: full body from the bore to the teeth (comparison variant); pocket: the body "
        "of the drawing with hub, web and pockets (data/fe/body_sections.yaml)",
    )
    parser.add_argument(
        "--hub-rings",
        type=int,
        default=preset.hub_rings,
        help="pocket body: rings between the bore and the hub wall",
    )
    parser.add_argument(
        "--pocket-rings",
        type=int,
        default=preset.pocket_rings,
        help="pocket body: rings between the hub wall and the rim wall (the web); --rings then "
        f"counts the rings between the rim wall and the fan ring (preset {preset.rim_rings})",
    )
    parser.add_argument(
        "--web-layers",
        type=int,
        default=preset.web_layers,
        help="pocket body: layers over the web (even); the rest of --layers goes to the pockets",
    )


def _body_counts(args: argparse.Namespace) -> bd.BodyCounts | None:
    """The body counts of the command line for ``--body pocket``, else None."""
    if args.body != "pocket":
        return None
    preset = bd.BodyCounts()
    rim = args.rings if args.rings is not None else preset.rim_rings
    outside = args.layers - args.web_layers
    if outside < 2 or outside % 2:
        raise InputRangeError(
            f"--layers {args.layers} minus --web-layers {args.web_layers} must leave an even "
            "number of pocket layers, at least 2"
        )
    return bd.BodyCounts(
        hub_rings=args.hub_rings,
        pocket_rings=args.pocket_rings,
        rim_rings=rim,
        web_layers=args.web_layers,
        flange_layers=outside // 2,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)
    mesh_parser = commands.add_parser("mesh", help="write the mesh file of one gear sector")
    mesh_parser.add_argument("--case", default="kst_e", help="packaged STplus case")
    mesh_parser.add_argument("--role", choices=("pinion", "wheel"), default="wheel")
    mesh_parser.add_argument("--teeth", type=int, default=5)
    mesh_parser.add_argument("--rim-rings", type=int, default=12)
    mesh_parser.add_argument("--layers", type=int, default=80)
    mesh_parser.add_argument("--element-type", default="C3D8R")
    mesh_parser.add_argument(
        "--bore-radius",
        type=float,
        default=None,
        help="mm; preset: the depth of --rim-rings rings of the template (18,10 mm for kst-E)",
    )
    counts_group = mesh_parser.add_argument_group(
        "numbers of elements (all given: the template is resampled; none given: the "
        "template density, 18 + 2 / 80 / 10 / 3 / 12 / 4)"
    )
    for name, text in (
        ("over-tooth-height", "rows between the root form point and the tip form point"),
        ("at-tip-edge-break", "rows of the tip edge break"),
        ("at-tooth-root", "elements along the rounding of one gap (even)"),
        ("over-tooth-thickness", "columns across the tooth (even)"),
        ("root-layers", "layers normal to the root surface (= outer columns of the head)"),
        ("rings", "rings of the rim between the bore and the fan ring"),
        ("shoulder-columns", "columns of each toothless shoulder pitch"),
    ):
        counts_group.add_argument(f"--{name}", type=int, default=None, help=text)
    _body_arguments(mesh_parser)
    mesh_parser.add_argument("--out", type=Path, default=None)
    surface_parser = commands.add_parser("surface", help="write the rigid tooth surface")
    surface_parser.add_argument("--case", default="kst_e", help="packaged STplus case")
    surface_parser.add_argument("--role", choices=("pinion", "wheel"), default="pinion")
    surface_parser.add_argument("--mating-teeth", type=int, default=5)
    surface_parser.add_argument("--mating-layers", type=int, default=80)
    surface_parser.add_argument("--max-edge", type=float, default=0.05, help="mm along the profile")
    surface_parser.add_argument(
        "--pinion-rotation", choices=("clockwise", "counterclockwise"), default="clockwise"
    )
    surface_parser.add_argument(
        "--tip-rounding",
        type=float,
        default=0.0,
        help="mm; radius of the rounding of the tip corners of the rigid surface (deburring as "
        "a modelling choice), 0 = sharp corners as the drawing",
    )
    surface_parser.add_argument("--out", type=Path, default=None)
    preview_parser = commands.add_parser("preview", help="draw the pair in five positions")
    preview_parser.add_argument("--case", default="kst_e", help="packaged STplus case")
    preview_parser.add_argument(
        "--pinion-rotation",
        choices=("clockwise", "counterclockwise"),
        default="clockwise",
        help="sense of rotation of the driving pinion as seen in the pictures (test rig: clockwise)",
    )
    preview_parser.add_argument("--out", type=Path, default=None)
    decks_parser = commands.add_parser(
        "decks", help="wheel mesh, pinion surface, one position file per position, manifest, runner"
    )
    decks_parser.add_argument("--case", default="kst_e")
    decks_parser.add_argument("--teeth", type=int, default=5)
    decks_parser.add_argument("--rim-rings", type=int, default=12)
    decks_parser.add_argument("--layers", type=int, default=80)
    decks_parser.add_argument(
        "--element-type",
        default=None,
        help="wheel element type; preset by the material step (W1, W3: C3D8I; W2, W4: C3D8)",
    )
    decks_parser.add_argument("--bore-radius", type=float, default=None)
    for name, text in (
        ("over-tooth-height", "rows between the root form point and the tip form point"),
        ("at-tip-edge-break", "rows of the tip edge break"),
        ("at-tooth-root", "elements along the rounding of one gap (even)"),
        ("over-tooth-thickness", "columns across the tooth (even)"),
        ("root-layers", "layers normal to the root surface"),
        ("rings", "rings of the rim between the bore and the fan ring"),
        ("shoulder-columns", "columns of each toothless shoulder pitch"),
    ):
        decks_parser.add_argument(f"--{name}", type=int, default=None, help=text)
    _body_arguments(decks_parser)
    decks_parser.add_argument(
        "--pinion-rotation", choices=("clockwise", "counterclockwise"), default="clockwise"
    )
    decks_parser.add_argument(
        "--material",
        nargs="+",
        choices=dk.MATERIAL_STEPS,
        default=["W1"],
        help="material steps, one file per step and rate (W1 W2 W3 W4)",
    )
    decks_parser.add_argument(
        "--cof",
        type=Path,
        nargs="+",
        default=[REFERENCE_COF],
        help="CONVERSE orientation files, one per rate of --rates (same mesh, the material "
        "card of that strain rate): the isotropic row for W1/W2, the pieces for W3/W4",
    )
    decks_parser.add_argument(
        "--rates",
        nargs="+",
        default=["QS"],
        help="names of the strain rates of the files of --cof, in the same order (QS DY1 DY2)",
    )
    decks_parser.add_argument("--temperature", type=float, default=80.0, help="degC, required")
    decks_parser.add_argument(
        "--torques", type=float, nargs="+", default=[8.0, 12.0, 16.0], help="N m at the wheel"
    )
    decks_parser.add_argument(
        "--positions",
        nargs="+",
        default=["grid"],
        help="'grid' (margin before A to margin after E plus A..E), 'pilot' (C), or letters A B C D E",
    )
    decks_parser.add_argument("--steps-per-pitch", type=int, default=12)
    decks_parser.add_argument(
        "--margin", type=float, default=0.5, help="base pitches before A and after E"
    )
    decks_parser.add_argument(
        "--seating-arc", type=float, default=0.001, help="mm at the base circle of the pinion"
    )
    decks_parser.add_argument(
        "--max-edge", type=float, default=0.05, help="mm along the pinion profile"
    )
    decks_parser.add_argument(
        "--tip-rounding",
        type=float,
        default=0.0,
        help="mm; radius of the rounding of the tip corners of the rigid pinion surface, "
        "0 = sharp corners as the drawing (FE-17)",
    )
    decks_parser.add_argument(
        "--variants",
        nargs="+",
        choices=tuple(VARIANTS),
        default=None,
        help="one position file per solver/contact variant (diagnosis of a broken-off run)",
    )
    decks_parser.add_argument(
        "--enforcement",
        choices=tuple(dk.ENFORCEMENT_KEYWORDS),
        default="default",
        help="enforcement of the hard contact in every file: 'default' (Abaqus: direct Lagrange "
        "multipliers for node-to-surface), 'penalty' (PENALTY=LINEAR, against chattering of a "
        "flank node on the kink of the rigid surface), 'direct', 'augmented_lagrange'",
    )
    decks_parser.add_argument(
        "--grid-indices",
        type=int,
        nargs="+",
        default=None,
        help="write only these positions of the grid (1-based indices of the full grid, the "
        "file names pos_NNN keep the numbering of the full grid): a retry folder",
    )
    decks_parser.add_argument(
        "--iterations",
        type=int,
        nargs=3,
        default=None,
        metavar=("I0", "IR", "IC"),
        help="equilibrium iteration limits of every step, *CONTROLS, PARAMETERS=TIME "
        "INCREMENTATION (Abaqus defaults 4 8 16): more iterations before a cutback for the "
        "slowly converging contact of a flank node on the pinion tip corner",
    )
    decks_parser.add_argument("--out", type=Path, default=None)
    report_parser = commands.add_parser(
        "report", help="evaluate the .sta/.msg/.dat files of a position folder after the run"
    )
    report_parser.add_argument("--folder", type=Path, required=True)
    extract_parser = commands.add_parser(
        "extract", help="extract <job>_fields.json from every .odb of a folder with Abaqus Python"
    )
    extract_parser.add_argument("--folder", type=Path, required=True)
    extract_parser.add_argument(
        "--launcher", type=Path, default=LEARNING_EDITION, help="Abaqus command (abq2025le.bat)"
    )
    le_parser = commands.add_parser("le-tests", help="the small models of the Learning Edition")
    le_parser.add_argument("--run", action="store_true", help="run them in the Learning Edition")
    le_parser.add_argument("--out", type=Path, default=None)
    log_parser = commands.add_parser(
        "log", help="the simulation diary of every output folder (fe_simulation_log.md)"
    )
    log_parser.add_argument("--case", default="kst_e")
    log_parser.add_argument("--root", type=Path, default=None, help="preset 80_output/fe/<case>")
    log_parser.add_argument("--notes", type=Path, default=LOG_NOTES)
    log_parser.add_argument("--out", type=Path, default=LOG_FILE)
    args = parser.parse_args()
    if args.command == "mesh":
        body_counts = _body_counts(args)
        given = {
            "over_tooth_height": args.over_tooth_height,
            "at_tip_edge_break": args.at_tip_edge_break,
            "at_tooth_root": args.at_tooth_root,
            "over_tooth_thickness": args.over_tooth_thickness,
            "root_layers": args.root_layers,
            "rim_rings": body_counts.rings if body_counts is not None else args.rings,
            "shoulder_columns": args.shoulder_columns,
        }
        counts = None
        if any(value is not None for value in given.values()):
            counts = rs.MeshCounts(**{k: v for k, v in given.items() if v is not None})
        folder = f"{args.role}_{args.teeth}teeth_{args.rim_rings}rings_{args.layers}layers"
        if counts is not None:
            folder += f"_{counts.label()}"
        if body_counts is not None:
            folder += f"_pocket_{body_counts.label()}"
        out = args.out if args.out is not None else OUTPUT / args.case / folder
        for line in mesh(
            args.case,
            args.role,
            args.teeth,
            args.rim_rings,
            args.layers,
            args.element_type,
            out,
            counts,
            args.bore_radius,
            body=args.body,
            body_counts=body_counts,
        ).lines:
            print(line)
    if args.command == "surface":
        folder = f"{args.role}_surface_{args.mating_teeth + 2}teeth_{args.mating_layers}layers"
        out = args.out if args.out is not None else OUTPUT / args.case / folder
        for line in surface(
            args.case,
            args.role,
            args.mating_teeth,
            args.mating_layers,
            args.max_edge,
            args.pinion_rotation,
            out,
            tip_rounding_mm=args.tip_rounding,
        ):
            print(line)
    if args.command == "preview":
        out = args.out if args.out is not None else OUTPUT / args.case / "preview"
        for path in preview(args.case, args.pinion_rotation, out):
            print(path.as_posix())
    if args.command == "decks":
        body_counts = _body_counts(args)
        given = {
            "over_tooth_height": args.over_tooth_height,
            "at_tip_edge_break": args.at_tip_edge_break,
            "at_tooth_root": args.at_tooth_root,
            "over_tooth_thickness": args.over_tooth_thickness,
            "root_layers": args.root_layers,
            "rim_rings": body_counts.rings if body_counts is not None else args.rings,
            "shoulder_columns": args.shoulder_columns,
        }
        counts = None
        if any(value is not None for value in given.values()):
            counts = rs.MeshCounts(**{k: v for k, v in given.items() if v is not None})
        folder = (
            f"decks_{'_'.join(args.material)}_{'_'.join(args.rates)}_{args.layers}layers_"
            f"{'_'.join(args.positions)}"
        )
        if body_counts is not None:
            folder += "_pocket"
        if args.variants:
            folder += "_variants"
        if args.enforcement != "default":
            folder += f"_{args.enforcement}"
        if args.tip_rounding > 0.0:
            folder += f"_round{args.tip_rounding:g}"
        if args.iterations:
            folder += f"_iter{args.iterations[2]}"
        if args.grid_indices:
            folder += f"_retry{len(args.grid_indices)}"
        out = args.out if args.out is not None else OUTPUT / args.case / folder
        for line in decks(
            args.case,
            teeth=args.teeth,
            rim_rings=args.rim_rings,
            layers=args.layers,
            element_type=args.element_type,
            counts=counts,
            bore_radius_mm=args.bore_radius,
            rotation=args.pinion_rotation,
            material_steps=args.material,
            cofs=args.cof,
            rates=args.rates,
            temperature_c=args.temperature,
            torques_wheel_nm=args.torques,
            positions=args.positions,
            steps_per_pitch=args.steps_per_pitch,
            margin=args.margin,
            seating_arc_mm=args.seating_arc,
            max_edge_mm=args.max_edge,
            out=out,
            variants=args.variants,
            body=args.body,
            body_counts=body_counts,
            enforcement=args.enforcement,
            grid_indices=args.grid_indices,
            tip_rounding_mm=args.tip_rounding,
            iteration_limits=tuple(args.iterations) if args.iterations else None,
        ):
            print(line)
    if args.command == "report":
        for line in report(args.folder):
            print(line)
    if args.command == "extract":
        for line in extract(args.folder, args.launcher):
            print(line)
    if args.command == "le-tests":
        out = args.out if args.out is not None else OUTPUT / "kst_e" / "le_tests"
        for line in le_tests(out, args.run):
            print(line)
    if args.command == "log":
        root = args.root if args.root is not None else OUTPUT / args.case
        for line in simulation_log(root, args.notes, args.out):
            print(line)


if __name__ == "__main__":
    main()
