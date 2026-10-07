"""Text of Abaqus input files for the finite element model of a gear pair.

``mesh_text`` writes one gear sector: nodes, elements, node sets, element sets and surfaces.
The keywords it uses are valid inside a part as well as in a file without parts, so the same
file is read by CONVERSE on its own and included into the ``*PART`` of the model.
``rigid_surface_text`` writes the rigid tooth surface of the mating gear.

Numbers are written with 13 significant digits; a data item of an Abaqus input line may not be
longer than that allows. Labels in the file are 1-based.
"""

import re

import numpy as np
from numpy.typing import NDArray

from gearcore.errors import InputRangeError
from gearcore.fe.refine import effective_counts
from gearcore.fe.rigid_surface import RigidSurface
from gearcore.fe.solid import GearSets, SolidMesh

EQ_EXEMPT = ("mesh_text", "rigid_surface_text")
"""Writing of files: no equation of a norm."""

IntArray = NDArray[np.int64]

IDS_PER_LINE = 16
ELEMENT_TYPE = re.compile(r"[A-Z][A-Z0-9]*")


def _id_lines(ids: IntArray) -> list[str]:
    labels = [str(int(i) + 1) for i in ids]
    return [
        ", ".join(labels[start : start + IDS_PER_LINE])
        for start in range(0, len(labels), IDS_PER_LINE)
    ]


def mesh_text(mesh: SolidMesh, sets: GearSets, *, element_type: str, title: str) -> str:
    """The input text of one gear sector: ``*NODE``, ``*ELEMENT`` of ``element_type`` (an
    8-node brick such as C3D8R), then the sets of ``sets``. ``title`` goes into the comment
    lines at the top."""
    if not isinstance(mesh, SolidMesh) or not isinstance(sets, GearSets):
        raise InputRangeError("mesh_text needs a SolidMesh and its GearSets")
    if not isinstance(element_type, str) or ELEMENT_TYPE.fullmatch(element_type) is None:
        raise InputRangeError(f"element type must be an Abaqus element name, got {element_type!r}")
    if not isinstance(title, str) or "\n" in title or "\r" in title:
        raise InputRangeError("the title must be one line of text")
    prefix = sets.prefix
    section = mesh.section
    lines = [
        f"** {title}",
        f"** {section.teeth} teeth + 2 shoulder pitches of a gear with {section.number_of_teeth} "
        f"teeth, {mesh.layers} layers, {len(mesh.nodes_mm)} nodes, {len(mesh.hexes)} elements",
        f"** bore radius {section.bore_radius_mm:.6f} mm, {effective_counts(section).rim_rings} "
        "rim rings; teeth numbered counter-clockwise seen from +z, LEFT = counter-clockwise half "
        "of a tooth",
        f"*NODE, NSET={prefix}_NODES",
    ]
    lines.extend(
        f"{label}, {x:.12e}, {y:.12e}, {z:.12e}"
        for label, (x, y, z) in enumerate(mesh.nodes_mm.tolist(), start=1)
    )
    lines.append(f"*ELEMENT, TYPE={element_type}, ELSET={prefix}")
    lines.extend(
        f"{label}, " + ", ".join(str(node + 1) for node in nodes)
        for label, nodes in enumerate(mesh.hexes.tolist(), start=1)
    )
    for name, nodes in sets.node_sets.items():
        if name == f"{prefix}_NODES":
            continue
        lines.append(f"*NSET, NSET={name}")
        lines.extend(_id_lines(nodes))
    for name, elements in sets.element_sets.items():
        if name == prefix:
            continue
        lines.append(f"*ELSET, ELSET={name}")
        lines.extend(_id_lines(elements))
    for name, faces in sets.surfaces.items():
        lines.append(f"*SURFACE, TYPE=ELEMENT, NAME={name}")
        lines.extend(f"{element + 1}, S{face}" for element, face in faces.tolist())
    return "\n".join(lines) + "\n"


def rigid_surface_text(surface: RigidSurface, prefix: str, *, title: str) -> str:
    """The input text of a rigid tooth surface: ``*NODE``, ``*ELEMENT`` of type R3D4 and the
    surface ``<prefix>_SURF`` on the positive side of the elements, the side their right-hand
    normal points to (out of the gear)."""
    if not isinstance(surface, RigidSurface):
        raise InputRangeError(f"a RigidSurface is required, got {type(surface).__name__}")
    if not isinstance(prefix, str) or not prefix.isidentifier() or not prefix.isupper():
        raise InputRangeError(f"the prefix must be an upper-case name, got {prefix!r}")
    if not isinstance(title, str) or "\n" in title or "\r" in title:
        raise InputRangeError("the title must be one line of text")
    lines = [
        f"** {title}",
        f"** rigid tooth surface: {surface.teeth} teeth of a gear with {surface.number_of_teeth} "
        f"teeth, {surface.profile_nodes} nodes along the profile, {len(surface.z_levels_mm)} "
        f"z-levels, {len(surface.nodes_mm)} nodes, {len(surface.quads)} elements",
        "** no volume, no end faces; the positive side of the elements faces the mating gear",
        f"*NODE, NSET={prefix}_NODES",
    ]
    lines.extend(
        f"{label}, {x:.12e}, {y:.12e}, {z:.12e}"
        for label, (x, y, z) in enumerate(surface.nodes_mm.tolist(), start=1)
    )
    lines.append(f"*ELEMENT, TYPE=R3D4, ELSET={prefix}")
    lines.extend(
        f"{label}, " + ", ".join(str(node + 1) for node in nodes)
        for label, nodes in enumerate(surface.quads.tolist(), start=1)
    )
    lines.append(f"*SURFACE, TYPE=ELEMENT, NAME={prefix}_SURF")
    lines.append(f"{prefix}, SPOS")
    return "\n".join(lines) + "\n"
