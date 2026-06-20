"""
@module: app.services.model.mesh_sets
@context: Domain layer — FE rolling model, bridge from the structured mesh to the Abaqus
          assembly. The WoBe-892 deck needs *named* surfaces and node sets: the bore (the
          "Fesselung" tied to the gear's master node via a rigid body), the radial cut
          faces (the sector edges, also fastened), the tip, and — per tooth and per side —
          the involute flank surfaces that become the contact pairs.
@role: Classify the 2-D section's boundary edges geometrically (by radius and angle from
       the known STplus diameters and the tooth centres), then map each boundary edge to
       the swept C3D8 side faces it generates over the face width. Output element-face
       surfaces (ELSET + Abaqus face id) and node sets the `.inp` writer consumes. Pure
       geometry on the final mesh — no tags threaded through the mesher.
"""

import math
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from app.services.geometry.tooth_form import ToothProfile
from app.services.model.tooth_mesh import Mesh2D

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]
# Abaqus C3D8 side faces for a hex built as [quad@layer k, quad@layer k+1]: a 2-D quad
# edge at local position p (0=n0-n1, 1=n1-n2, 2=n2-n3, 3=n3-n0) sweeps to face S(3+p).
_SIDE_FACE = ("S3", "S4", "S5", "S6")


@dataclass
class SectorSurfaces:
    """Named element-face surfaces ``[(hex_index, face_id)]`` and node sets for the deck."""

    faces: dict[str, list[tuple[int, str]]] = field(default_factory=dict)
    node_sets: dict[str, IntArray] = field(default_factory=dict)


def _boundary_edges(section: Mesh2D) -> list[tuple[int, int]]:
    """Return ``(quad_index, local_edge)`` for every edge owned by exactly one quad."""
    seen: dict[frozenset[int], int] = {}
    owner: dict[frozenset[int], tuple[int, int]] = {}
    for qi, quad in enumerate(section.quads):
        for p in range(4):
            key = frozenset((int(quad[p]), int(quad[(p + 1) % 4])))
            seen[key] = seen.get(key, 0) + 1
            owner[key] = (qi, p)
    return [owner[k] for k, n in seen.items() if n == 1]


def tag_sector_surfaces(
    section: Mesh2D,
    *,
    profile: ToothProfile,
    n_teeth: int,
    n_segments: int,
    layers: int,
    rim_depth_mm: float | None = None,
    tol_mm: float | None = None,
) -> SectorSurfaces:
    """Classify the section boundary into bore / cut / tip / per-tooth flank surfaces.

    ``layers`` is the number of face-width layers used in the extrusion, so each boundary
    edge expands to that many swept side faces. Tooth centres follow the sector layout
    (``n_teeth`` teeth flanked by ``n_segments`` rim pitches each side).
    """
    tol = tol_mm if tol_mm is not None else 0.02 * profile.mn
    pitch = 2.0 * math.pi / profile.z
    total = n_teeth + 2 * n_segments
    centres = [(n_segments + i - (total - 1) / 2.0) * pitch for i in range(n_teeth)]
    half_sector = total * pitch / 2.0
    r_na, r_ff = profile.d_Na / 2.0, profile.d_Ff / 2.0
    r_bore = profile.root_diameter_mm / 2.0 - (
        rim_depth_mm if rim_depth_mm is not None else 2.0 * profile.mn
    )
    n_quads = section.n_quads

    faces: dict[str, list[tuple[int, str]]] = {}
    node_groups: dict[str, set[int]] = {}

    def add(name: str, qi: int, p: int, nodes: tuple[int, int]) -> None:
        bucket = faces.setdefault(name, [])
        for k in range(layers):
            bucket.append((k * n_quads + qi, _SIDE_FACE[p]))
        grp = node_groups.setdefault(name, set())
        grp.update(int(n) for n in nodes)

    for qi, p in _boundary_edges(section):
        edge = (int(section.quads[qi][p]), int(section.quads[qi][(p + 1) % 4]))
        mid = section.nodes[list(edge)].mean(axis=0)
        r = float(np.hypot(mid[0], mid[1]))
        ang = math.atan2(mid[0], mid[1])
        if abs(abs(ang) - half_sector) < tol / max(r, 1e-6):
            add("CUT", qi, p, edge)
        elif abs(r - r_bore) < tol:
            add("BORE", qi, p, edge)
        elif abs(r - r_na) < tol:
            add("TIP", qi, p, edge)
        elif r_ff + tol < r < r_na - tol:
            tooth = int(np.argmin([abs(ang - c) for c in centres]))
            side = "R" if ang > centres[tooth] else "L"
            add(f"FLANK_T{tooth}_{side}", qi, p, edge)
        # else: root fillet / gap floor (r_bore..r_ff) — not needed as a named surface yet

    surfaces = SectorSurfaces(faces=faces)
    surfaces.node_sets = {
        name: np.array(sorted(ns), dtype=np.int64) for name, ns in node_groups.items()
    }
    return surfaces
