"""The packaged template of a gear sector mesh: one tooth block and one shoulder block.

``data/fe/sector_template.json`` is derived by ``scripts/build_fe_template.py`` from the mid
z-slice of the wheel of the FVA reference deck of kst-E (the provenance is stored in the file).
The reference sector cuts cleanly along its gap centre lines: a toothless shoulder block at each
end and congruent tooth blocks between them, each reaching from one gap centre line to the next.
The file keeps one tooth block, mirror symmetric about its tooth centre line, and the shoulder
block of the clockwise end.

Coordinates are polar: ``phi`` in angular pitches, counter-clockwise, and the radius in
millimetres of the reference gear. The tooth block has its tooth centre line at phi = 0 and its
interfaces at -0.5 and +0.5; the shoulder block has its interface at 0 and the cut plane at -1.
A block is fully structured except for the node on the fan ring below each gap centre, where the
fine layers of the tooth zone run together; below the fan ring the rim is a polar grid.
"""

import json
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from gearcore.data import data_path
from gearcore.errors import ParseError

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]

NODE_KINDS = ("interior", "surface", "bore", "cut")

EQ_EXEMPT = ("load_sector_template",)
"""Reading of packaged data: no equation of a norm."""


@dataclass(frozen=True)
class Block:
    """Nodes and quads of one block of the template (reference geometry, polar coordinates)."""

    phi: Array
    radius_mm: Array
    quads: IntArray
    kind: tuple[str, ...]
    surface_order: tuple[int, ...]


@dataclass(frozen=True)
class SectorTemplate:
    """The tooth block, the shoulder block and the radii of the reference gear.

    ``tooth_left_interface`` are the nodes of the tooth block on phi = -0.5 (its clockwise
    side), ``tooth_right_interface`` those on +0.5, both from the bore outwards;
    ``tooth_mirror_partner`` names for every node the node at the mirrored place.
    ``shoulder_interface`` are the nodes of the shoulder block on phi = 0, ``shoulder_cut``
    those on the cut plane, again from the bore outwards. ``rim_line_radii_mm`` are the radii of
    the grid circles of the rim from the bore to the fan ring.

    ``tooth_grid_quads`` marks the quads of the regular grid of the tooth (1): everything above
    the mesh line that joins the two root form points; below it lie the fine layers along the
    fillets (0). ``tooth_surface_features`` are the positions in ``tooth.surface_order`` of the
    points that divide the clockwise half of the contour: centre line of the gap, root form
    point, tip form point (where the tip edge break begins), tip corner, tooth centre line.
    """

    number_of_teeth: int
    normal_module_mm: float
    bore_radius_mm: float
    fan_ring_radius_mm: float
    root_radius_mm: float
    tip_radius_mm: float
    rim_line_radii_mm: tuple[float, ...]
    tooth: Block
    tooth_left_interface: tuple[int, ...]
    tooth_right_interface: tuple[int, ...]
    tooth_centre_line: tuple[int, ...]
    tooth_mirror_partner: tuple[int, ...]
    tooth_grid_quads: tuple[int, ...]
    tooth_surface_features: tuple[int, ...]
    shoulder: Block
    shoulder_interface: tuple[int, ...]
    shoulder_cut: tuple[int, ...]

    @property
    def rim_rings(self) -> int:
        """Number of element rings of the rim between the bore and the fan ring."""
        return len(self.rim_line_radii_mm) - 1


def _frozen(values: object, dtype: type) -> NDArray[np.generic]:
    array: NDArray[np.generic] = np.array(values, dtype=dtype)
    array.setflags(write=False)
    return array


def _block(raw: dict[str, object], name: str) -> Block:
    try:
        phi = _frozen(raw["phi"], np.float64)
        radius = _frozen(raw["r_mm"], np.float64)
        quads = _frozen(raw["quads"], np.int64)
        kind = tuple(str(k) for k in raw["kind"])  # type: ignore[attr-defined]
        surface = tuple(int(n) for n in raw["surface_order"])  # type: ignore[attr-defined]
    except (KeyError, TypeError, ValueError) as error:
        raise ParseError(f"sector template: the {name} block is incomplete: {error}") from error
    count = len(phi)
    if (
        phi.ndim != 1
        or radius.shape != phi.shape
        or len(kind) != count
        or quads.ndim != 2
        or quads.shape[1] != 4
        or int(quads.min()) < 0
        or int(quads.max()) >= count
        or not set(kind) <= set(NODE_KINDS)
        or any(not 0 <= n < count for n in surface)
        or not bool(np.all(np.isfinite(phi)) and np.all(np.isfinite(radius)))
    ):
        raise ParseError(f"sector template: the {name} block is not consistent")
    return Block(
        phi=phi,  # type: ignore[arg-type]
        radius_mm=radius,  # type: ignore[arg-type]
        quads=quads,  # type: ignore[arg-type]
        kind=kind,
        surface_order=surface,
    )


def _nodes(raw: dict[str, object], key: str, count: int) -> tuple[int, ...]:
    try:
        nodes = tuple(int(n) for n in raw[key])  # type: ignore[attr-defined]
    except (KeyError, TypeError, ValueError) as error:
        raise ParseError(f"sector template: {key!r} is missing or no list of nodes") from error
    if any(not 0 <= n < count for n in nodes):
        raise ParseError(f"sector template: {key!r} names nodes the block does not have")
    return nodes


def load_sector_template() -> SectorTemplate:
    """Read ``data/fe/sector_template.json``."""
    path = data_path("fe", "sector_template.json")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        reference = raw["reference"]
        tooth_raw, shoulder_raw = raw["tooth"], raw["shoulder"]
        tooth = _block(tooth_raw, "tooth")
        shoulder = _block(shoulder_raw, "shoulder")
        template = SectorTemplate(
            number_of_teeth=int(reference["number_of_teeth"]),
            normal_module_mm=float(reference["normal_module_mm"]),
            bore_radius_mm=float(reference["bore_radius_mm"]),
            fan_ring_radius_mm=float(reference["fan_ring_radius_mm"]),
            root_radius_mm=float(reference["root_radius_mm"]),
            tip_radius_mm=float(reference["tip_radius_mm"]),
            rim_line_radii_mm=tuple(float(r) for r in reference["rim_line_radii_mm"]),
            tooth=tooth,
            tooth_left_interface=_nodes(tooth_raw, "left_interface", len(tooth.phi)),
            tooth_right_interface=_nodes(tooth_raw, "right_interface", len(tooth.phi)),
            tooth_centre_line=_nodes(tooth_raw, "centre_line", len(tooth.phi)),
            tooth_mirror_partner=_nodes(tooth_raw, "mirror_partner", len(tooth.phi)),
            tooth_grid_quads=tuple(int(flag) for flag in tooth_raw["grid_quads"]),
            tooth_surface_features=_nodes(tooth_raw, "surface_features", len(tooth.surface_order)),
            shoulder=shoulder,
            shoulder_interface=_nodes(shoulder_raw, "interface", len(shoulder.phi)),
            shoulder_cut=_nodes(shoulder_raw, "cut", len(shoulder.phi)),
        )
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise ParseError(f"sector template {path.name}: {error}") from error
    if not (
        len(template.tooth_left_interface)
        == len(template.tooth_right_interface)
        == len(template.shoulder_interface)
        == len(template.shoulder_cut)
        and len(template.tooth_mirror_partner) == len(tooth.phi)
        and len(template.tooth_grid_quads) == len(tooth.quads)
        and set(template.tooth_grid_quads) <= {0, 1}
        and len(template.tooth_surface_features) == 5
        and list(template.tooth_surface_features) == sorted(set(template.tooth_surface_features))
        and template.tooth_surface_features[0] == 0
        and 2 * template.tooth_surface_features[-1] + 1 == len(tooth.surface_order)
        and len(template.rim_line_radii_mm) >= 2
        and 0.0
        < template.bore_radius_mm
        < template.fan_ring_radius_mm
        < template.root_radius_mm
        < template.tip_radius_mm
    ):
        raise ParseError(f"sector template {path.name}: interfaces or radii are not consistent")
    return template
