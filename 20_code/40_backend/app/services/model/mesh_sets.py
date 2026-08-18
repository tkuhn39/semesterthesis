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
from collections import defaultdict
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
    tol_mm: float | None = None,
    flank_lower_radius_mm: float | None = None,  # fillet junction (audit FEM-04); None → d_Ff/2
) -> SectorSurfaces:
    """Classify the section boundary into bore / cut / tip / per-tooth flank surfaces.

    ``layers`` is the number of face-width layers used in the extrusion, so each boundary
    edge expands to that many swept side faces. Tooth centres follow the sector layout
    (``n_teeth`` teeth flanked by ``n_segments`` rim pitches each side). The bore radius is
    read off the actual mesh (its minimum node radius), not recomputed from a ``rim_depth``
    — so the BORE/Fesselung set can never come up empty if the mesher used a different rim.
    """
    tol = tol_mm if tol_mm is not None else 0.02 * profile.mn
    pitch = 2.0 * math.pi / profile.z
    total = n_teeth + 2 * n_segments
    centres = [(n_segments + i - (total - 1) / 2.0) * pitch for i in range(n_teeth)]
    half_sector = total * pitch / 2.0
    # flank band lower bound: the ACTIVE fillet's junction radius (audit FEM-04 — a Landi
    # junction above d_Ff must keep its elliptic portion out of the FLANK contact sets)
    r_na = profile.d_Na / 2.0
    r_ff = flank_lower_radius_mm if flank_lower_radius_mm is not None else profile.d_Ff / 2.0
    used = np.unique(section.quads)  # skip orphan geometry nodes (e.g. the arc-centre at r=0)
    r_bore = float(np.hypot(section.nodes[used, 0], section.nodes[used, 1]).min())  # inner radius
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


@dataclass
class GearReferenceSets:
    """Reference-named (FVA WoBe-892) sets/surfaces for one gear sector, in 1-based 3-D ids.

    The frozen FVA postprocessing builds its set names as ``G{gear}T{tooth:03d}F{flank}_NODESET`` /
    ``_ELEMENTSET`` and reads the matching ``TOOTH-{gear}-{tooth:03d}F{flank}`` element surfaces, so
    the deck must emit exactly these. ``flank`` is 1 (right, +angle) or 2 (left, −angle); ``tooth``
    is 1-based. Ids are 1-based and refer to the 3-D mesh swept by ``extrude_to_hex``.
    """

    gear: int
    n_teeth: int
    # Fesselung (reference parity): 1-based node ids of the bore surface PLUS both radial
    # sector cut planes as COMPLETE cross-sections — every node of those faces from the bore
    # to the shoulder contour, over all face-width planes. Measured against the reference
    # deck's Fesselung_Rad{1,2} (bore arc x all z planes + two full cut planes, 2 268/2 225
    # nodes each — nothing else, no z side faces). Selected by coordinate predicate over ALL
    # mesh nodes, not by boundary-edge traversal, so no node of a face can be missed.
    fastening_nodes: IntArray
    flank_nodes: dict[tuple[int, int], IntArray]  # (tooth, flank) -> 1-based node ids
    flank_elements: dict[tuple[int, int], IntArray]  # (tooth, flank) -> 1-based hex ids
    flank_faces: dict[tuple[int, int], list[tuple[int, str]]]  # (tooth, flank) -> (hex id, face)


def build_rigid_shell(
    section: Mesh2D,
    *,
    profile: ToothProfile,
    gear: int,
    n_teeth: int,
    n_segments: int,
    layers: int,
    width_mm: float,
    z0_mm: float,
    tol_mm: float | None = None,
    flank_lower_radius_mm: float | None = None,  # fillet junction (audit FEM-04); None → d_Ff/2
) -> tuple[Array, IntArray, GearReferenceSets]:
    """The ideally stiff Außenhülle of a gear sector: the LATERAL boundary surface only.

    User decision 2026-07-06: for a rigid gear the full solid is replaced by its prismatic
    lateral surface — tooth contour, both radial cut faces and the bore, swept over the face
    width; the axial END faces stay OPEN (see-through along the axis). One R3D4 element per
    2-D boundary edge per layer; nodes are RENUMBERED to the boundary nodes only (a full
    node table would leave thousands of dead nodes → zero-pivot warnings).

    Orientation: ``_boundary_edges`` yields each edge in its owning quad's CCW order, so the
    material lies left of (n0→n1) and the swept quad ``[n0@k, n1@k, n1@k+1, n0@k+1]`` has an
    OUTWARD right-hand normal — identical to the solid's S(3+p) face cycle. Every element
    face is therefore uniformly ``SPOS`` for the ``TOOTH-…`` contact surfaces.

    Returns ``(nodes, quads, sets)``: nodes ``(B·(layers+1), 3)`` in section coordinates
    (z from ``z0_mm`` over ``width_mm``), quads 0-based, and reference sets in the NEW
    1-based shell ids (``fastening_nodes`` empty — a rigid body needs no Fesselung tie;
    ``flank_faces`` empty — the surfaces are emitted as ``ELSET, SPOS``).
    """
    tol = tol_mm if tol_mm is not None else 0.02 * profile.mn
    pitch = 2.0 * math.pi / profile.z
    total = n_teeth + 2 * n_segments
    centres = [(n_segments + i - (total - 1) / 2.0) * pitch for i in range(n_teeth)]
    r_na = profile.d_Na / 2.0
    r_ff = flank_lower_radius_mm if flank_lower_radius_mm is not None else profile.d_Ff / 2.0

    boundary = _boundary_edges(section)
    edges = [(int(section.quads[qi][p]), int(section.quads[qi][(p + 1) % 4])) for qi, p in boundary]
    node2d = sorted({n for e in edges for n in e})
    rank = {n: i for i, n in enumerate(node2d)}
    n_boundary_nodes = len(node2d)
    n_edges = len(edges)

    zs = [z0_mm + width_mm * k / layers for k in range(layers + 1)]
    nodes = np.array(
        [[section.nodes[n, 0], section.nodes[n, 1], z] for z in zs for n in node2d],
        dtype=np.float64,
    )
    quads = np.array(
        [
            [
                k * n_boundary_nodes + rank[n0],
                k * n_boundary_nodes + rank[n1],
                (k + 1) * n_boundary_nodes + rank[n1],
                (k + 1) * n_boundary_nodes + rank[n0],
            ]
            for k in range(layers)
            for n0, n1 in edges
        ],
        dtype=np.int64,
    )

    flank_nodes: dict[tuple[int, int], set[int]] = defaultdict(set)
    flank_elems: dict[tuple[int, int], set[int]] = defaultdict(set)
    for e, (n0, n1) in enumerate(edges):
        mid = section.nodes[[n0, n1]].mean(axis=0)
        r = float(np.hypot(mid[0], mid[1]))
        ang = math.atan2(mid[0], mid[1])
        if r_ff + tol < r < r_na - tol:
            tooth = int(np.argmin([abs(ang - c) for c in centres])) + 1
            flank = 1 if ang > centres[tooth - 1] else 2
            key = (tooth, flank)
            flank_nodes[key].update(
                k * n_boundary_nodes + rank[n] + 1 for k in range(layers + 1) for n in (n0, n1)
            )
            flank_elems[key].update(k * n_edges + e + 1 for k in range(layers))

    def arr(ids: set[int]) -> IntArray:
        return np.array(sorted(ids), dtype=np.int64)

    sets = GearReferenceSets(
        gear=gear,
        n_teeth=n_teeth,
        fastening_nodes=np.array([], dtype=np.int64),
        flank_nodes={k: arr(v) for k, v in flank_nodes.items()},
        flank_elements={k: arr(v) for k, v in flank_elems.items()},
        flank_faces={k: [] for k in flank_elems},
    )
    return nodes, quads, sets


def tag_gear_reference(
    section: Mesh2D,
    *,
    profile: ToothProfile,
    gear: int,
    n_teeth: int,
    n_segments: int,
    layers: int,
    tol_mm: float | None = None,
    fasten_bore: bool = True,
    fasten_cuts: bool = True,
    fasten_bottom: bool = False,
    fasten_top: bool = False,
    flank_lower_radius_mm: float | None = None,  # fillet junction (audit FEM-04); None → d_Ff/2
) -> GearReferenceSets:
    """Classify a swept gear sector into the reference per-tooth/flank sets + Fesselung.

    Same boundary geometry as ``tag_sector_surfaces`` but emits the reference naming and **1-based
    3-D** ids: each 2-D boundary node expands over the ``layers + 1`` face-width node planes and
    each boundary quad-edge over the ``layers`` swept side faces (the ``extrude_to_hex`` layout).

    The Fesselung is selected by a coordinate predicate over ALL mesh nodes — every single node
    of the chosen faces, never an edge-traversal subset (reference parity, measured 2026-07-04):
    ``fasten_bore`` = the bore surface (full sector arc, all face-width planes), ``fasten_cuts``
    = both radial sector cut planes as complete cross-sections (bore → shoulder contour, all
    planes). ``fasten_bottom`` / ``fasten_top`` add the axial end faces (the FVA "Fesselung
    unten/oben" checkboxes; off in the reference). The tip land stays free — the postprocessing
    does not consume it.
    """
    tol = tol_mm if tol_mm is not None else 0.02 * profile.mn
    pitch = 2.0 * math.pi / profile.z
    total = n_teeth + 2 * n_segments
    centres = [(n_segments + i - (total - 1) / 2.0) * pitch for i in range(n_teeth)]
    half_sector = total * pitch / 2.0
    r_na = profile.d_Na / 2.0
    r_ff = flank_lower_radius_mm if flank_lower_radius_mm is not None else profile.d_Ff / 2.0
    used = np.unique(section.quads)
    r_used = np.hypot(section.nodes[used, 0], section.nodes[used, 1])
    r_bore = float(r_used.min())
    n_quads = section.n_quads
    n_nodes = section.n_nodes

    def nodes_3d(edge: tuple[int, int]) -> set[int]:
        return {layer * n_nodes + nd + 1 for layer in range(layers + 1) for nd in edge}

    # Fesselung: coordinate predicate over every used 2-D node, expanded over all planes.
    ang_used = np.arctan2(section.nodes[used, 0], section.nodes[used, 1])
    on_face = np.zeros(used.shape, dtype=bool)
    if fasten_bore:
        on_face |= np.abs(r_used - r_bore) < tol
    if fasten_cuts:  # arc-length tolerance: |Δangle| * r < tol — the two cut planes, completely
        on_face |= np.abs(np.abs(ang_used) - half_sector) * np.maximum(r_used, 1e-6) < tol
    fastening: set[int] = {
        layer * n_nodes + int(nd) + 1 for nd in used[on_face] for layer in range(layers + 1)
    }
    if fasten_bottom:  # axial end face at z0 — the first node plane, every node
        fastening.update(int(nd) + 1 for nd in used)
    if fasten_top:  # axial end face at z0 + width — the last node plane, every node
        fastening.update(layers * n_nodes + int(nd) + 1 for nd in used)

    flank_nodes: dict[tuple[int, int], set[int]] = defaultdict(set)
    flank_elems: dict[tuple[int, int], set[int]] = defaultdict(set)
    flank_faces: dict[tuple[int, int], list[tuple[int, str]]] = defaultdict(list)

    for qi, p in _boundary_edges(section):
        edge = (int(section.quads[qi][p]), int(section.quads[qi][(p + 1) % 4]))
        mid = section.nodes[list(edge)].mean(axis=0)
        r = float(np.hypot(mid[0], mid[1]))
        ang = math.atan2(mid[0], mid[1])
        if abs(abs(ang) - half_sector) < tol / max(r, 1e-6):
            continue  # radial cut face — already fastened by the node predicate above
        if abs(r - r_bore) < tol or abs(r - r_na) < tol:
            continue  # bore (fastened above) / tip land (not a named reference surface)
        if r_ff + tol < r < r_na - tol:
            tooth = int(np.argmin([abs(ang - c) for c in centres])) + 1
            flank = 1 if ang > centres[tooth - 1] else 2  # F1 = right (+), F2 = left (−)
            key = (tooth, flank)
            flank_nodes[key].update(nodes_3d(edge))
            for k in range(layers):
                hex_id = k * n_quads + qi + 1
                flank_elems[key].add(hex_id)
                flank_faces[key].append((hex_id, _SIDE_FACE[p]))

    def arr(ids: set[int]) -> IntArray:
        return np.array(sorted(ids), dtype=np.int64)

    return GearReferenceSets(
        gear=gear,
        n_teeth=n_teeth,
        fastening_nodes=arr(fastening),
        flank_nodes={k: arr(v) for k, v in flank_nodes.items()},
        flank_elements={k: arr(v) for k, v in flank_elems.items()},
        flank_faces=dict(flank_faces),
    )
