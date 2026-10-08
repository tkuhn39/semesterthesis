"""Wheel body of the real part: hub, web and pockets behind the rim (ADR-116 amendment of
2026-10-07).

The transverse mesh of ``fe.sector_mesh`` has a rim of concentric element rings between the
bore and the fan ring. The body of the real kst-E wheel (drawing of the user, transcribed in
``data/fe/body_sections.yaml``) is a hub of full width at the bore, a web in the mid plane and
a rim of full width under the teeth; between hub and rim a pocket is open to each face, its
walls drafted. This module sweeps the transverse mesh to z-levels with a level on the pocket
bottom, moves the rings of the rim onto the stations bore, hub wall, rim wall and fan ring (the
walls level by level with their draft), removes the elements inside the pockets and renumbers
nodes and elements compactly. The corner radii of the drawing are not meshed (FE-18). The
numbering of such a mesh differs from the ring body, so the CONVERSE mapping is made anew on it.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, replace
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from gearcore import data
from gearcore._safe import finite_input, integer_input, positive_input
from gearcore.errors import GeometryInfeasibleError, InputRangeError, ParseError
from gearcore.fe.sector_mesh import SectorMesh
from gearcore.fe.solid import (
    FACE_NODES,
    GearSets,
    SolidMesh,
    extrude_to_levels,
    gear_sets,
    hex_corner_volumes,
    remove_elements,
)

EQ_EXEMPT = ("body_section", "rim_ring_index", "body_levels", "body_mesh")
"""Mesh construction from a drawing: no equation of a norm."""

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]
BodyShape = Literal["ring", "pocket"]
BODY_SHAPES: tuple[BodyShape, ...] = ("ring", "pocket")
"""``ring``: the full body from the bore to the teeth (the frozen mesh, kept as the comparison
variant); ``pocket``: the body of the drawing."""
RING_TOLERANCE_MM = 0.05
"""Nodes of the rim whose radii differ by less than this lie on the same ring (the rings of
the template scatter by 3e-3 mm between the tooth blocks and the shoulder blocks)."""
FAN_TOLERANCE_MM = 1.0e-3
"""A node this close to the fan ring radius belongs to the fan ring."""
LEVEL_TOLERANCE_MM = 1.0e-9
TIP_TOLERANCE_MM = 2.0e-3
"""The tip radius of the drawing must agree with the STplus tooth to this (drawing precision)."""


@dataclass(frozen=True)
class BodySection:
    """The half section of a body as the drawing gives it (mm and degrees; the meaning of each
    number is noted in ``data/fe/body_sections.yaml``). The body is symmetric about the mid
    plane; a pocket is open to each face and narrows with the depth by the draft of its walls."""

    face_width_mm: float
    tip_radius_mm: float
    bore_radius_mm: float
    hub_wall_radius_mm: float
    hub_wall_height_mm: float
    rim_wall_radius_mm: float
    rim_wall_height_mm: float
    pocket_depth_mm: float
    wall_angle_deg: float
    corner_radius_mm: float
    source: str = ""

    def __post_init__(self) -> None:
        for name in (
            "face_width_mm",
            "tip_radius_mm",
            "bore_radius_mm",
            "hub_wall_radius_mm",
            "rim_wall_radius_mm",
            "pocket_depth_mm",
        ):
            positive_input(getattr(self, name), name)
        for name in ("hub_wall_height_mm", "rim_wall_height_mm", "corner_radius_mm"):
            if finite_input(getattr(self, name), name) < 0.0:
                raise InputRangeError(f"{name} must be >= 0, got {getattr(self, name)!r}")
        angle = finite_input(self.wall_angle_deg, "wall angle")
        if not 90.0 <= angle < 135.0:
            raise InputRangeError(f"the wall angle must lie in 90 to 135 deg, got {angle!r}")
        if not (
            self.bore_radius_mm
            < self.hub_wall_radius_mm
            < self.rim_wall_radius_mm
            < self.tip_radius_mm
        ):
            raise InputRangeError(
                "the radii of the body must grow outwards: bore < hub wall < rim wall < tip"
            )
        if not self.pocket_depth_mm < 0.5 * self.face_width_mm:
            raise InputRangeError("the pocket depth must be below half the face width")
        if max(self.hub_wall_height_mm, self.rim_wall_height_mm) >= self.pocket_depth_mm:
            raise InputRangeError("a wall radius must be measured between the face and the bottom")
        if not self.hub_wall_radius_at(self.pocket_depth_mm) < self.rim_wall_radius_at(
            self.pocket_depth_mm
        ):
            raise GeometryInfeasibleError("the pocket walls cross above the bottom")
        if not isinstance(self.source, str):
            raise InputRangeError("the source of a body section must be a string")

    @property
    def draft_angle_rad(self) -> float:
        """Angle of each wall against the normal of the face."""
        return math.radians(self.wall_angle_deg - 90.0)

    @property
    def web_thickness_mm(self) -> float:
        return self.face_width_mm - 2.0 * self.pocket_depth_mm

    @property
    def bottom_z_mm(self) -> float:
        """Distance of the pocket bottom from the mid plane."""
        return 0.5 * self.face_width_mm - self.pocket_depth_mm

    def hub_wall_radius_at(self, depth_mm: float) -> float:
        """Radius of the hub-side wall at a depth below the face (it leans into the pocket)."""
        depth = finite_input(depth_mm, "depth below the face")
        return self.hub_wall_radius_mm + (depth - self.hub_wall_height_mm) * math.tan(
            self.draft_angle_rad
        )

    def rim_wall_radius_at(self, depth_mm: float) -> float:
        """Radius of the rim-side wall at a depth below the face (it leans into the pocket)."""
        depth = finite_input(depth_mm, "depth below the face")
        return self.rim_wall_radius_mm - (depth - self.rim_wall_height_mm) * math.tan(
            self.draft_angle_rad
        )

    def pocket_volume_mm3(self, sector_angle_rad: float) -> float:
        """Volume of both pockets within a sector of the given angle: the annulus between the
        walls integrated over the depth with Simpson's rule, exact for its quadratic integrand."""
        angle = positive_input(sector_angle_rad, "sector angle")

        def annulus(depth: float) -> float:
            outer, inner = self.rim_wall_radius_at(depth), self.hub_wall_radius_at(depth)
            return 0.5 * angle * (outer * outer - inner * inner)

        depth = self.pocket_depth_mm
        return 2.0 * depth / 6.0 * (annulus(0.0) + 4.0 * annulus(0.5 * depth) + annulus(depth))


def body_section(case: str, role: str) -> BodySection:
    """The transcribed body section of a gear of a packaged case (``data/fe/body_sections.yaml``)."""
    bodies = data.load_body_sections()
    known = sorted(f"{c}/{r}" for c, roles in bodies.items() for r in roles)
    if (
        not isinstance(case, str)
        or not isinstance(role, str)
        or case not in bodies
        or role not in bodies[case]
    ):
        raise InputRangeError(f"no body section for {case!r}/{role!r}; transcribed: {known}")
    entry = bodies[case][role]
    names = {field.name for field in dataclasses.fields(BodySection)}
    unknown, missing = set(entry) - names, names - set(entry) - {"source"}
    if unknown or missing:
        raise ParseError(
            f"body section {case}/{role}: unknown {sorted(unknown)}, missing {sorted(missing)}"
        )
    values = {k: (str(v) if k == "source" else float(v)) for k, v in entry.items()}
    return BodySection(**values)  # type: ignore[arg-type]


@dataclass(frozen=True)
class BodyCounts:
    """Numbers of elements of the body: rings of the rim from the bore to the hub wall, from
    the hub wall to the rim wall (the web) and from the rim wall to the fan ring; layers over
    the web (even, so that the mid plane is a level) and over the depth of each pocket."""

    hub_rings: int = 3
    pocket_rings: int = 3
    rim_rings: int = 2
    web_layers: int = 6
    flange_layers: int = 7

    def __post_init__(self) -> None:
        for name in ("hub_rings", "pocket_rings", "rim_rings", "web_layers", "flange_layers"):
            if integer_input(getattr(self, name), name) < 1:
                raise InputRangeError(f"{name} must be >= 1, got {getattr(self, name)!r}")
        if self.web_layers % 2:
            raise InputRangeError(f"web_layers must be even, got {self.web_layers}")

    @property
    def rings(self) -> int:
        """Rings of the rim between the bore and the fan ring."""
        return self.hub_rings + self.pocket_rings + self.rim_rings

    @property
    def layers(self) -> int:
        """Layers over the face width."""
        return self.web_layers + 2 * self.flange_layers

    def label(self) -> str:
        return (
            f"hub{self.hub_rings}_pocket{self.pocket_rings}_rim{self.rim_rings}_"
            f"web{self.web_layers}_flange{self.flange_layers}"
        )


def rim_ring_index(section: SectorMesh) -> tuple[IntArray, Array]:
    """The ring of every node of the rim (0 at the bore up to the fan ring), -1 for the nodes
    above the fan ring; and the mean radius of every ring."""
    if not isinstance(section, SectorMesh):
        raise InputRangeError(f"a SectorMesh is required, got {type(section).__name__}")
    radius = np.hypot(section.points_mm[:, 0], section.points_mm[:, 1])
    below = np.flatnonzero(radius <= section.fan_ring_radius_mm + FAN_TOLERANCE_MM)
    order = below[np.argsort(radius[below], kind="stable")]
    values = radius[order]
    ring_of_sorted = np.zeros(len(values), dtype=np.int64)
    ring_of_sorted[np.flatnonzero(np.diff(values) > RING_TOLERANCE_MM) + 1] = 1
    ring_of_sorted = np.cumsum(ring_of_sorted)
    index = np.full(len(radius), -1, dtype=np.int64)
    index[order] = ring_of_sorted
    count = int(ring_of_sorted[-1]) + 1
    means = np.array([values[ring_of_sorted == k].mean() for k in range(count)], dtype=np.float64)
    kind = np.array(section.node_kind)
    if count < 2 or not bool(np.all(index[kind == "bore"] == 0)):
        raise GeometryInfeasibleError("the rim of the sector is not a stack of rings")
    if abs(float(means[-1]) - section.fan_ring_radius_mm) > RING_TOLERANCE_MM:
        raise GeometryInfeasibleError("the outermost ring of the rim is not the fan ring")
    for array in (index, means):
        array.setflags(write=False)
    return index, means


def body_levels(body: BodySection, counts: BodyCounts) -> Array:
    """The z-levels of the sweep: ``web_layers`` equal layers over the web and
    ``flange_layers`` equal layers over each pocket depth, symmetric about the mid plane, with
    levels on the mid plane and on both pocket bottoms."""
    if not isinstance(body, BodySection) or not isinstance(counts, BodyCounts):
        raise InputRangeError("body_levels needs a BodySection and BodyCounts")
    half, bottom = 0.5 * body.face_width_mm, body.bottom_z_mm
    upper = np.concatenate(
        (
            np.linspace(0.0, bottom, (counts.web_layers >> 1) + 1),
            np.linspace(bottom, half, counts.flange_layers + 1)[1:],
        )
    )
    return np.concatenate((-upper[:0:-1], upper))


@dataclass(frozen=True)
class BodyMesh:
    """The swept and carved mesh of a body with pockets, and what the carving was made of."""

    body: BodySection
    counts: BodyCounts
    section: SectorMesh
    """The transverse mesh with the rings of the rim at the stations of the face."""
    solid: SolidMesh
    sets: GearSets
    full: SolidMesh
    """The swept mesh before the pockets were removed (transverse pictures, checks)."""
    full_sets: GearSets
    removed_elements: IntArray
    """Elements of ``full`` that lie in the pockets."""
    ring_index: IntArray
    """Ring of every transverse node, -1 above the fan ring."""
    node_map: IntArray
    element_map: IntArray


def _stations(
    body: BodySection, counts: BodyCounts, depth: float, bore: float, fan: float
) -> Array:
    """Radius of every ring (bore first, fan ring last) at a depth below the face."""
    hub_wall, rim_wall = body.hub_wall_radius_at(depth), body.rim_wall_radius_at(depth)
    return np.concatenate(
        (
            np.linspace(bore, hub_wall, counts.hub_rings + 1),
            np.linspace(hub_wall, rim_wall, counts.pocket_rings + 1)[1:],
            np.linspace(rim_wall, fan, counts.rim_rings + 1)[1:],
        )
    )


def body_mesh(section: SectorMesh, body: BodySection, counts: BodyCounts, prefix: str) -> BodyMesh:
    """Sweep ``section`` over the face width of ``body`` with the pockets of the drawing cut out.

    The sector must have been meshed with the bore radius of the drawing and with
    ``counts.rings`` rings of the rim; its tip must be the tip of the drawing. The rings are
    moved onto the stations bore, hub wall, rim wall, fan ring, level by level with the draft
    of the walls (the web levels take the stations of the bottom). The sets of ``fe.solid`` are
    carried over without their removed members; the body adds the element sets
    ``P_BODY_HUB``, ``P_BODY_WEB``, ``P_BODY_RIM`` (the rim below the fan ring outside the
    hub and the web) and the surface ``P_POCKET_SURF`` with ``P_POCKET_SURF_NODES`` (walls and
    bottoms of both pockets)."""
    if not isinstance(section, SectorMesh):
        raise InputRangeError(f"a SectorMesh is required, got {type(section).__name__}")
    if not isinstance(body, BodySection) or not isinstance(counts, BodyCounts):
        raise InputRangeError("body_mesh needs a BodySection and BodyCounts")
    if abs(section.bore_radius_mm - body.bore_radius_mm) > 1.0e-6:
        raise InputRangeError(
            f"the sector has the bore radius {section.bore_radius_mm:.6f} mm, the drawing "
            f"{body.bore_radius_mm:.6f} mm: mesh the sector with the bore of the drawing"
        )
    if abs(section.tip_radius_mm - body.tip_radius_mm) > TIP_TOLERANCE_MM:
        raise GeometryInfeasibleError(
            f"the tip radius of the drawing ({body.tip_radius_mm:.4f} mm) is not the tip of the "
            f"STplus tooth ({section.tip_radius_mm:.4f} mm): the drawing belongs to another gear"
        )
    fan = section.fan_ring_radius_mm
    if body.rim_wall_radius_at(0.0) >= fan - RING_TOLERANCE_MM:
        raise GeometryInfeasibleError(
            f"no room for the rim rings: the rim wall at the face ({body.rim_wall_radius_at(0.0):.4f} "
            f"mm) reaches the fan ring ({fan:.4f} mm)"
        )
    index, _ = rim_ring_index(section)
    last = int(index.max())
    if last != counts.rings:
        raise InputRangeError(
            f"the rim of the sector has {last} rings, the body counts need {counts.rings} "
            f"(hub {counts.hub_rings} + pocket {counts.pocket_rings} + rim {counts.rim_rings}): "
            f"mesh the sector with rim_rings={counts.rings}"
        )
    hub, pocket = counts.hub_rings, counts.pocket_rings
    quad_rings = index[section.quads]
    rim_quads = np.flatnonzero(np.all(quad_rings >= 0, axis=1))
    low, high = quad_rings[rim_quads].min(axis=1), quad_rings[rim_quads].max(axis=1)
    if not bool(np.all(high - low == 1)):
        raise GeometryInfeasibleError("a quad of the rim does not lie between two adjacent rings")
    pocket_quads = rim_quads[(low >= hub) & (high <= hub + pocket)]
    hub_quads = rim_quads[low < hub]
    rim_ring_quads = rim_quads[low >= hub + pocket]

    # the rings at the stations: the transverse section at the face, the levels by their depth
    points = section.points_mm
    angle = np.arctan2(points[:, 1], points[:, 0])
    moved = np.flatnonzero((index > 0) & (index < last))
    bore = section.bore_radius_mm

    def placed(depth: float) -> Array:
        xy = np.array(points, dtype=np.float64)
        radius = _stations(body, counts, depth, bore, fan)[index[moved]]
        xy[moved, 0] = radius * np.cos(angle[moved])
        xy[moved, 1] = radius * np.sin(angle[moved])
        return xy

    at_face = placed(0.0)
    at_face.setflags(write=False)
    face_section = replace(section, points_mm=at_face)
    z = body_levels(body, counts)
    full = extrude_to_levels(face_section, z)
    nodes = np.array(full.nodes_mm, dtype=np.float64)
    n = len(points)
    half = 0.5 * body.face_width_mm
    for level, z_level in enumerate(z.tolist()):
        depth = min(half - abs(z_level), body.pocket_depth_mm)
        nodes[level * n : (level + 1) * n, :2] = placed(depth)
    nodes.setflags(write=False)
    full = SolidMesh(
        nodes_mm=nodes, hexes=full.hexes, z_levels_mm=full.z_levels_mm, section=face_section
    )
    full_sets = gear_sets(full, prefix)

    # the pockets: their quads in the layers outside the web
    bottom = body.bottom_z_mm
    m = len(section.quads)
    flange_layers = [
        layer
        for layer in range(len(z) - 1)
        if min(abs(z[layer]), abs(z[layer + 1])) >= bottom - LEVEL_TOLERANCE_MM
    ]
    removed = np.array(
        [layer * m + q for layer in flange_layers for q in pocket_quads.tolist()], dtype=np.int64
    )
    carved = remove_elements(full, full_sets, removed)
    worst = float(hex_corner_volumes(carved.mesh).min())
    if worst <= 0.0:
        raise GeometryInfeasibleError(
            f"the body mesh has a degenerate or inverted element (corner volume {worst:.3e} mm^3)"
        )

    # body sets
    layers = len(z) - 1

    def swept(quads: IntArray) -> IntArray:
        old = (quads[None, :] + m * np.arange(layers, dtype=np.int64)[:, None]).ravel()
        new = carved.element_map[old]
        return np.asarray(np.sort(new[new >= 0]), dtype=np.int64)

    element_sets = dict(carved.sets.element_sets)
    element_sets[f"{prefix}_BODY_HUB"] = swept(hub_quads)
    element_sets[f"{prefix}_BODY_WEB"] = swept(pocket_quads)
    element_sets[f"{prefix}_BODY_RIM"] = swept(rim_ring_quads)
    on_wall_ring = (index == hub) | (index == hub + pocket)
    in_pocket_rings = (index >= hub) & (index <= hub + pocket)
    pocket_nodes_old: list[IntArray] = []
    for level, z_level in enumerate(z.tolist()):
        outside = abs(z_level) >= bottom - LEVEL_TOLERANCE_MM
        on_bottom = abs(abs(z_level) - bottom) < LEVEL_TOLERANCE_MM
        chosen = (on_wall_ring & outside) | (in_pocket_rings & on_bottom)
        pocket_nodes_old.append(np.flatnonzero(chosen) + level * n)
    pocket_nodes = carved.node_map[np.concatenate(pocket_nodes_old)]
    pocket_nodes = np.asarray(np.sort(pocket_nodes[pocket_nodes >= 0]), dtype=np.int64)
    on_pocket = np.zeros(len(carved.mesh.nodes_mm), dtype=bool)
    on_pocket[pocket_nodes] = True
    hexes = carved.mesh.hexes
    face_order = sorted(FACE_NODES)
    faces = np.stack([hexes[:, FACE_NODES[f]] for f in face_order], axis=1)  # (E, 6, 4)
    keyed = np.sort(faces.reshape(-1, 4), axis=1)
    _, inverse, occurrences = np.unique(keyed, axis=0, return_inverse=True, return_counts=True)
    exposed = (occurrences[inverse.ravel()] == 1).reshape(len(hexes), len(face_order))
    pocket_face = exposed & np.all(on_pocket[faces], axis=2)
    element, which = np.nonzero(pocket_face)
    surfaces = dict(carved.sets.surfaces)
    surfaces[f"{prefix}_POCKET_SURF"] = np.column_stack(
        (element.astype(np.int64), np.array(face_order, dtype=np.int64)[which])
    )
    node_sets = dict(carved.sets.node_sets)
    node_sets[f"{prefix}_POCKET_SURF_NODES"] = pocket_nodes
    sets = GearSets(
        prefix=prefix, node_sets=node_sets, element_sets=element_sets, surfaces=surfaces
    )
    removed.setflags(write=False)
    return BodyMesh(
        body=body,
        counts=counts,
        section=face_section,
        solid=carved.mesh,
        sets=sets,
        full=full,
        full_sets=full_sets,
        removed_elements=removed,
        ring_index=index,
        node_map=carved.node_map,
        element_map=carved.element_map,
    )
