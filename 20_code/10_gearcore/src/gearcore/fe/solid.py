"""Solid mesh of a spur gear sector: the transverse mesh swept along the face width, and the
named sets of nodes, elements and element faces the model and the evaluation refer to.

Numbering (0-based here, the writer adds 1): node ``level * n + i`` is node ``i`` of the
transverse mesh on the z-level ``level``; element ``layer * m + q`` is quad ``q`` between the
levels ``layer`` and ``layer + 1``. Its eight nodes are the quad on the lower level followed by
the quad on the upper level, both counter-clockwise seen from +z: the node order of the Abaqus
element C3D8, whose faces S3 to S6 are then the four edges of the quad in their order.

Sets of a gear with the prefix P (for example ``WHEEL``), tooth t counted counter-clockwise from
1, SIDE ``LEFT`` (counter-clockwise half of the tooth) or ``RIGHT``; a half reaches from the
tooth centre line to the centre line of the gap:

    P                        all elements;            P_NODES  all nodes
    P_RIM, P_TOOTH_ZONE      elements below / above the fan ring
    P_FESSELUNG              nodes of the bore and of both cut planes
    P_TEETH_SURF             faces of the whole surface of the tooth blocks
    P_Tt_SIDE_SURF           faces of the surface of the half, with _ROOT (up to the root form
                             circle), _FLANK (to the tip form circle) and _TIP as its parts
    P_Tt_SIDE_..._NODES      the nodes of each of these four surfaces
    P_Tt_SIDE_LAYER1         elements with a face on the surface of the half
    P_Tt_SIDE_HALF           all elements of the half above the fan ring
    P_Tt_SIDE_ROOT, _HEAD    the half divided along the mesh line that joins the two root form
                             points of the tooth: the fine layers along the fillet below it,
                             the regular grid of the tooth above it; with _ROOT_LAYER1 and
                             _HEAD_LAYER1 as their first layer
    P_ROOT_Tt_Tu             root of the tooth space between the teeth t and u = t + 1: the
                             LEFT root of t and the RIGHT root of u; with _LAYER1, _SURF and
                             _SURF_NODES
    P_HEAD_Tt                head of tooth t (flanks and tip of both halves); with _LAYER1,
                             _SURF and _SURF_NODES

The root form point, the tip form point and the tip corner are nodes of the mesh, so the parts
of a surface end exactly on the form circles, and the surface of a head is its flanks and tip.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from gearcore._safe import finite_input, integer_input, positive_input
from gearcore.errors import InputRangeError
from gearcore.fe.sector_mesh import SectorMesh

EQ_EXEMPT = ("sweep_levels", "extrude", "gear_sets", "hex_corner_volumes")
"""Mesh construction: no equation of a norm."""

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]

SIDES = ((1, "LEFT"), (-1, "RIGHT"))
FIRST_SIDE_FACE = 3
"""Face S3 of a C3D8 is the first edge of the swept quad; S4, S5, S6 follow."""


@dataclass(frozen=True)
class SolidMesh:
    """Nodes (x, y, z in mm) and 8-node hexahedra of a swept sector, 0-based."""

    nodes_mm: Array
    hexes: IntArray
    z_levels_mm: Array
    section: SectorMesh

    @property
    def layers(self) -> int:
        return len(self.z_levels_mm) - 1


@dataclass(frozen=True)
class GearSets:
    """Named sets, 0-based: node sets, element sets, and surfaces as (element, face) rows with
    the face number 1 to 6 of the C3D8."""

    prefix: str
    node_sets: dict[str, IntArray]
    element_sets: dict[str, IntArray]
    surfaces: dict[str, IntArray]


def sweep_levels(face_width_mm: float, layers: int, z_centre_mm: float = 0.0) -> Array:
    """The z-levels of ``layers`` equal layers over the face width, symmetric about
    ``z_centre_mm``."""
    width = positive_input(face_width_mm, "face width")
    count = integer_input(layers, "number of layers")
    if count < 1:
        raise InputRangeError(f"the sweep needs at least 1 layer, got {layers!r}")
    centre = finite_input(z_centre_mm, "z of the mid plane")
    return np.asarray(
        centre + width * (np.arange(count + 1, dtype=np.float64) / count - 0.5), dtype=np.float64
    )


def extrude(
    section: SectorMesh, *, face_width_mm: float, layers: int, z_centre_mm: float = 0.0
) -> SolidMesh:
    """Sweep the transverse mesh over the face width in ``layers`` equal layers, symmetric about
    ``z_centre_mm``."""
    if not isinstance(section, SectorMesh):
        raise InputRangeError(f"a SectorMesh is required, got {type(section).__name__}")
    z = sweep_levels(face_width_mm, layers, z_centre_mm)
    count = len(z) - 1
    n = len(section.points_mm)
    nodes = np.empty(((count + 1) * n, 3), dtype=np.float64)
    nodes[:, :2] = np.tile(section.points_mm, (count + 1, 1))
    nodes[:, 2] = np.repeat(z, n)
    lower = np.concatenate([section.quads + level * n for level in range(count)])
    hexes = np.concatenate((lower, lower + n), axis=1)
    for array in (nodes, hexes, z):
        array.setflags(write=False)
    return SolidMesh(nodes_mm=nodes, hexes=hexes, z_levels_mm=z, section=section)


def hex_corner_volumes(mesh: SolidMesh) -> Array:
    """Per element the smallest triple product of the three edges at a corner (mm^3); positive
    for a properly oriented element."""
    corners = mesh.nodes_mm[mesh.hexes]
    # neighbours of every corner in the order that gives a positive volume
    order = (
        (0, 1, 3, 4),
        (1, 2, 0, 5),
        (2, 3, 1, 6),
        (3, 0, 2, 7),
        (4, 7, 5, 0),
        (5, 4, 6, 1),
        (6, 5, 7, 2),
        (7, 6, 4, 3),
    )
    worst = np.full(len(mesh.hexes), np.inf)
    for here, a, b, c in order:
        origin = corners[:, here]
        volume = np.einsum(
            "ij,ij->i",
            np.cross(corners[:, a] - origin, corners[:, b] - origin),
            corners[:, c] - origin,
        )
        worst = np.minimum(worst, volume)
    return worst


def _over_levels(nodes: IntArray, n: int, levels: int) -> IntArray:
    return (nodes[None, :] + n * np.arange(levels, dtype=np.int64)[:, None]).ravel()


def gear_sets(mesh: SolidMesh, prefix: str) -> GearSets:
    """The named sets of a swept gear sector (see the module docstring)."""
    if not isinstance(mesh, SolidMesh):
        raise InputRangeError(f"a SolidMesh is required, got {type(mesh).__name__}")
    if not isinstance(prefix, str) or not prefix.isidentifier() or not prefix.isupper():
        raise InputRangeError(f"the prefix must be an upper-case name, got {prefix!r}")
    section = mesh.section
    n, m = len(section.points_mm), len(section.quads)
    layers = mesh.layers
    levels = layers + 1
    radius = np.hypot(section.points_mm[:, 0], section.points_mm[:, 1])
    kind = np.array(section.node_kind)

    def swept(quads: IntArray) -> IntArray:
        return (quads[None, :] + m * np.arange(layers, dtype=np.int64)[:, None]).ravel()

    # the quad and the edge of it that carries each piece of the surface
    owner: dict[tuple[int, int], tuple[int, int]] = {}
    for q, quad in enumerate(section.quads.tolist()):
        for edge in range(4):
            owner[(quad[edge], quad[(edge + 1) % 4])] = (q, edge)
    path = section.surface_path
    pieces: list[tuple[int, int, int, int]] = []  # quad, edge of the quad, node a, node b
    for a, b in zip(path[:-1], path[1:], strict=True):
        found = owner.get((int(a), int(b))) or owner.get((int(b), int(a)))
        if found is None:
            raise InputRangeError("the surface path of the sector does not follow element edges")
        pieces.append((found[0], found[1], int(a), int(b)))

    node_sets: dict[str, IntArray] = {
        f"{prefix}_NODES": np.arange(levels * n, dtype=np.int64),
        f"{prefix}_FESSELUNG": _over_levels(
            np.flatnonzero((kind == "bore") | (kind == "cut")), n, levels
        ),
    }
    element_sets: dict[str, IntArray] = {
        prefix: np.arange(layers * m, dtype=np.int64),
        f"{prefix}_RIM": swept(np.flatnonzero(section.quad_zone == 0)),
        f"{prefix}_TOOTH_ZONE": swept(np.flatnonzero(section.quad_zone == 1)),
    }
    surfaces: dict[str, IntArray] = {}

    def surface(name: str, chosen: list[tuple[int, int, int, int]]) -> None:
        quads = np.array([piece[0] for piece in chosen], dtype=np.int64)
        faces = np.array([FIRST_SIDE_FACE + piece[1] for piece in chosen], dtype=np.int64)
        elements = (quads[None, :] + m * np.arange(layers, dtype=np.int64)[:, None]).ravel()
        surfaces[name] = np.column_stack((elements, np.tile(faces, layers)))
        nodes = np.unique(np.array([piece[2:] for piece in chosen], dtype=np.int64))
        node_sets[f"{name}_NODES"] = _over_levels(nodes, n, levels)

    surface(f"{prefix}_TEETH_SURF", [p for p in pieces if section.quad_tooth[p[0]] > 0])
    halves: dict[tuple[int, int], tuple[list[tuple[int, int, int, int]], ...]] = {}
    for tooth in range(1, section.teeth + 1):
        for side, side_name in SIDES:
            name = f"{prefix}_T{tooth}_{side_name}"
            half = [
                p
                for p in pieces
                if section.quad_tooth[p[0]] == tooth and section.quad_side[p[0]] == side
            ]
            surface(f"{name}_SURF", half)
            middle = {p: 0.5 * (radius[p[2]] + radius[p[3]]) for p in half}
            parts = {
                "ROOT": [p for p in half if middle[p] < section.root_form_radius_mm],
                "FLANK": [
                    p
                    for p in half
                    if section.root_form_radius_mm <= middle[p] <= section.tip_form_radius_mm
                ],
                "TIP": [p for p in half if middle[p] > section.tip_form_radius_mm],
            }
            for part, chosen in parts.items():
                if chosen:
                    surface(f"{name}_SURF_{part}", chosen)
            element_sets[f"{name}_LAYER1"] = swept(
                np.unique(np.array([p[0] for p in half], dtype=np.int64))
            )
            in_half = (
                (section.quad_tooth == tooth)
                & (section.quad_side == side)
                & (section.quad_zone == 1)
            )
            element_sets[f"{name}_HALF"] = swept(np.flatnonzero(in_half))
            # head: the regular grid of the tooth above the mesh line through the root form
            # points; root: the fine layers along the fillet below it. The first layer and the
            # surface of each are the elements and faces of the half that belong to it.
            in_head = section.quad_head == 1
            element_sets[f"{name}_ROOT"] = swept(np.flatnonzero(in_half & ~in_head))
            element_sets[f"{name}_HEAD"] = swept(np.flatnonzero(in_half & in_head))
            on_root = [p for p in half if not in_head[p[0]]]
            on_head = [p for p in half if in_head[p[0]]]
            for zone, chosen in (("ROOT", on_root), ("HEAD", on_head)):
                element_sets[f"{name}_{zone}_LAYER1"] = swept(
                    np.unique(np.array([p[0] for p in chosen], dtype=np.int64))
                )
            halves[(tooth, side)] = (on_root, on_head)

    def joined(target: str, first: str, second: str) -> None:
        for ending in ("", "_LAYER1"):
            element_sets[f"{target}{ending}"] = np.union1d(
                element_sets[f"{first}{ending}"], element_sets[f"{second}{ending}"]
            )

    # the root of a tooth space: the right half of a tooth and the left half of the tooth
    # clockwise of it; the head of a tooth: both of its halves
    for tooth in range(1, section.teeth):
        target = f"{prefix}_ROOT_T{tooth}_T{tooth + 1}"
        joined(target, f"{prefix}_T{tooth}_LEFT_ROOT", f"{prefix}_T{tooth + 1}_RIGHT_ROOT")
        surface(f"{target}_SURF", halves[(tooth, 1)][0] + halves[(tooth + 1, -1)][0])
    for tooth in range(1, section.teeth + 1):
        target = f"{prefix}_HEAD_T{tooth}"
        joined(target, f"{prefix}_T{tooth}_LEFT_HEAD", f"{prefix}_T{tooth}_RIGHT_HEAD")
        surface(f"{target}_SURF", halves[(tooth, 1)][1] + halves[(tooth, -1)][1])
    return GearSets(
        prefix=prefix, node_sets=node_sets, element_sets=element_sets, surfaces=surfaces
    )
