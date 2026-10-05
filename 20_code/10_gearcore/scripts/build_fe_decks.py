"""Build the finite element model of a gear pair: previews of the positions and the mesh files
(decks follow).

    python scripts/build_fe_decks.py mesh --case kst_e --teeth 5 --rim-rings 12 --layers 80
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
import math
from pathlib import Path

import matplotlib

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
from gearcore.fe import abaqus as ab
from gearcore.fe import placement as pl
from gearcore.fe import rigid_surface as rs
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


def mesh(
    case: str, role: ct.Role, teeth: int, rim_rings: int, layers: int, element_type: str, out: Path
) -> list[str]:
    """Write the mesh file of one gear sector and its pictures; returns the lines of the report."""
    generation = _generation(case)
    gear = generation.inputs.gears.pinion if role == "pinion" else generation.inputs.gears.wheel
    section = sm.sector_mesh(generation, role, teeth=teeth, rim_rings=rim_rings)
    solid = so.extrude(section, face_width_mm=gear.face_width_mm, layers=layers)
    prefix = role.upper()
    sets = so.gear_sets(solid, prefix)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{role}_mesh.inp"
    written = ab.mesh_text(
        solid,
        sets,
        element_type=element_type,
        title=f"{case}: {role}, face width {gear.face_width_mm:g} mm, built by gearcore",
    )
    target.write_text(written, encoding="ascii")
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
    return [
        target.as_posix(),
        f"nodes {len(solid.nodes_mm)}, elements {len(solid.hexes)} ({element_type}), "
        f"layers {layers}, layer thickness {gear.face_width_mm / layers:.4f} mm",
        f"transverse mesh: {len(section.points_mm)} nodes, {len(section.quads)} quads, smallest "
        f"corner sine {float(quality.min()):.3f}, quads below 0.35: {int((quality < 0.35).sum())}, "
        f"edge lengths {float(edges.min()):.4f} to {float(edges.max()):.4f} mm",
        f"circles: bore {section.bore_radius_mm:.4f}, fan ring {section.fan_ring_radius_mm:.4f}, "
        f"root {section.root_radius_mm:.4f}, tip {section.tip_radius_mm:.4f} mm",
        f"sets: {len(sets.node_sets)} node sets, {len(sets.element_sets)} element sets, "
        f"{len(sets.surfaces)} surfaces; fixed nodes {len(sets.node_sets[prefix + '_FESSELUNG'])}",
    ]


def surface(
    case: str,
    role: ct.Role,
    mating_teeth: int,
    mating_layers: int,
    max_edge_mm: float,
    rotation: pl.Rotation,
    out: Path,
) -> list[str]:
    """Write the rigid tooth surface of the gear ``role`` and a picture of it in mesh with the
    sector of the mating gear; returns the lines of the report."""
    generation = _generation(case)
    gears = generation.inputs.gears
    mating_role: ct.Role = "wheel" if role == "pinion" else "pinion"
    gear, mating = (gears.pinion, gears.wheel) if role == "pinion" else (gears.wheel, gears.pinion)
    levels = rs.surface_z_levels(
        so.sweep_levels(mating.face_width_mm, mating_layers), gear.face_width_mm
    )
    rigid = rs.rigid_surface(
        generation, role, teeth=mating_teeth + 2, max_edge_mm=max_edge_mm, z_levels_mm=levels
    )
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{role}_surface.inp"
    target.write_text(
        ab.rigid_surface_text(
            rigid,
            role.upper(),
            title=f"{case}: {role}, face width {gear.face_width_mm:g} mm, built by gearcore",
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
    ]


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
    args = parser.parse_args()
    if args.command == "mesh":
        folder = f"{args.role}_{args.teeth}teeth_{args.rim_rings}rings_{args.layers}layers"
        out = args.out if args.out is not None else OUTPUT / args.case / folder
        for line in mesh(
            args.case, args.role, args.teeth, args.rim_rings, args.layers, args.element_type, out
        ):
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
        ):
            print(line)
    if args.command == "preview":
        out = args.out if args.out is not None else OUTPUT / args.case / "preview"
        for path in preview(args.case, args.pinion_rotation, out):
            print(path.as_posix())


if __name__ == "__main__":
    main()
