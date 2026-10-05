"""Derive the packaged sector template of the wheel mesh from the mined reference sector.

    python scripts/build_fe_template.py            # writes src/gearcore/data/fe/sector_template.json
    python scripts/build_fe_template.py --check    # exit 1 if the packaged file is stale

Source: ``reference_sector_rad_vz_1.json`` of the archived workbench, the mid z-slice of the part
``Part_Rad_Vz_1`` of the FVA reference deck ``kst-E_8_DY2-0_WS30_ohne_Radkoerper.inp`` (mined on
2026-07-03; four teeth and two toothless shoulder pitches). That folder is not under version
control, so this script runs only where the reference lies; the packaged file is what the
package reads.

The reference sector is cut along its gap centre lines into a shoulder block and tooth blocks.
One tooth block is kept, made exactly mirror symmetric about its tooth centre line, and the left
shoulder block; a sector of any number of teeth is assembled from them
(``gearcore.fe.sector_mesh``). Coordinates are polar: the angle ``phi`` in angular pitches, the
radius in millimetres of the reference gear.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE = (
    REPO_ROOT
    / "30_references_and_examples"
    / "38_legacy_workbench"
    / "40_backend"
    / "app"
    / "services"
    / "model"
    / "data"
    / "reference_sector_rad_vz_1.json"
)
TARGET = REPO_ROOT / "20_code" / "10_gearcore" / "src" / "gearcore" / "data" / "fe"
TARGET_FILE = TARGET / "sector_template.json"

LINE_TOLERANCE = 1.0e-4
"""Distance from a gap centre line or a tooth centre line, in pitches, below which a node of the
reference lies on that line (the reference holds them to 1e-7)."""
MATCH_TOLERANCE_MM = 1.0e-5
REFERENCE_MODULE_MM = 1.0
"""Normal module of the reference gear (kst-E, ``data/stplus/kst_e/input.ste``: NORMALMODUL = 1)."""
"""Largest distance between a node and the mirror image of its partner (reference: 1.2e-7 mm)."""

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]


def _block(quads: IntArray, phi: Array, lo: float, hi: float) -> tuple[IntArray, IntArray]:
    """Quads whose centre lies between the lines ``lo`` and ``hi``, and their nodes."""
    centre = phi[quads].mean(axis=1)
    chosen = quads[(centre > lo) & (centre < hi)]
    return chosen, np.unique(chosen)


def _local(quads: IntArray, nodes: IntArray) -> IntArray:
    index = {int(n): i for i, n in enumerate(nodes)}
    return np.array([[index[int(n)] for n in quad] for quad in quads], dtype=np.int64)


def _counter_clockwise(quads: IntArray, phi: Array, radius: Array) -> IntArray:
    """Every quad in counter-clockwise order (phi grows counter-clockwise)."""
    x, y = radius * np.cos(phi), radius * np.sin(phi)
    out = quads.copy()
    for row, quad in enumerate(quads):
        area = 0.0
        for k in range(4):
            a, b = quad[k], quad[(k + 1) % 4]
            area += x[a] * y[b] - x[b] * y[a]
        if area < 0.0:
            out[row] = quad[::-1]
    return out


def _on_line(phi: Array, line: float) -> IntArray:
    return np.flatnonzero(np.abs(phi - line) < LINE_TOLERANCE)


def _by_radius(nodes: IntArray, radius: Array) -> list[int]:
    return [int(n) for n in nodes[np.argsort(radius[nodes])]]


def _surface_path(quads: IntArray, kind: list[str], start: int) -> list[int]:
    """The surface nodes in the order of the contour, from ``start``: the edges that belong to
    one quad only and join two surface nodes form one open path."""
    count: dict[tuple[int, int], int] = {}
    for quad in quads:
        for k in range(4):
            a, b = int(quad[k]), int(quad[(k + 1) % 4])
            edge = (min(a, b), max(a, b))
            count[edge] = count.get(edge, 0) + 1
    neighbours: dict[int, list[int]] = {}
    for (a, b), n in count.items():
        if n == 1 and kind[a] == "surface" and kind[b] == "surface":
            neighbours.setdefault(a, []).append(b)
            neighbours.setdefault(b, []).append(a)
    path = [start]
    previous = -1
    while True:
        following = [n for n in neighbours.get(path[-1], []) if n != previous]
        if not following:
            return path
        if len(following) > 1:
            raise SystemExit(f"the surface branches at node {path[-1]}")
        previous = path[-1]
        path.append(following[0])


def _tooth_grid(
    quads: IntArray, radius: Array, centre_line: list[int], surface: set[int], root_mm: float
) -> tuple[list[int], tuple[int, int]]:
    """Which quads belong to the regular grid of the tooth (1) and which to the fine layers
    below it (0), and the two surface nodes at which the base line of the grid ends.

    Along the tooth centre line the steps are fine up to the base line of the grid and coarse
    above it. The base line is the mesh line through that node; it runs straight through the
    regular nodes to the surface on both sides. The grid is everything connected to the tip
    without crossing it.
    """
    steps = np.diff(radius[centre_line])
    base = next(
        centre_line[i]
        for i in range(1, len(steps))
        if radius[centre_line[i]] > root_mm and steps[i] > 2.5 * steps[i - 1]
    )
    around: dict[int, list[int]] = {}
    for q, quad in enumerate(quads.tolist()):
        for node in quad:
            around.setdefault(node, []).append(q)

    def neighbours(node: int) -> set[int]:
        found: set[int] = set()
        for q in around[node]:
            quad = quads[q].tolist()
            i = quad.index(node)
            found.update((quad[(i + 1) % 4], quad[(i - 1) % 4]))
        return found

    def straight_on(previous: int, here: int) -> int:
        """The node opposite ``previous`` at the regular interior node ``here``."""
        with_previous = {q for q in around[here] if previous in quads[q]}
        ahead = [
            node
            for node in neighbours(here)
            if node != previous
            and not ({q for q in around[here] if node in quads[q]} & with_previous)
        ]
        if len(around[here]) != 4 or len(ahead) != 1:
            raise SystemExit(f"the base line of the tooth grid meets an irregular node {here}")
        return ahead[0]

    line_edges: set[tuple[int, int]] = set()
    ends: list[int] = []
    for first in sorted(neighbours(base) - set(centre_line)):
        line = [base, first]
        while line[-1] not in surface:
            line.append(straight_on(line[-2], line[-1]))
        ends.append(line[-1])
        line_edges.update((min(a, b), max(a, b)) for a, b in zip(line[:-1], line[1:], strict=True))
    if len(ends) != 2:
        raise SystemExit("the base line of the tooth grid must run to the surface on both sides")
    edge_quads: dict[tuple[int, int], list[int]] = {}
    for q, quad in enumerate(quads.tolist()):
        for k in range(4):
            a, b = quad[k], quad[(k + 1) % 4]
            edge_quads.setdefault((min(a, b), max(a, b)), []).append(q)
    grid = set(around[centre_line[-1]])  # the quads at the tip on the centre line
    frontier = list(grid)
    while frontier:
        quad = quads[frontier.pop()].tolist()
        for k in range(4):
            a, b = quad[k], quad[(k + 1) % 4]
            edge = (min(a, b), max(a, b))
            if edge in line_edges:
                continue
            for other in edge_quads[edge]:
                if other not in grid:
                    grid.add(other)
                    frontier.append(other)
    if any(q in grid for q in around[centre_line[0]]):
        raise SystemExit("the tooth grid leaked through its base line")
    return [1 if q in grid else 0 for q in range(len(quads))], (ends[0], ends[1])


def _surface_features(
    surface_order: list[int],
    phi: Array,
    radius: Array,
    base_ends: tuple[int, int],
    tip_mm: float,
    teeth: int,
) -> list[int]:
    """Positions in ``surface_order`` of the points that divide the clockwise half of the
    contour: centre line of the gap, root form point (where the base line of the tooth grid
    ends), tip form point (the corner where the tip edge break begins), tip corner (where the
    tip circle begins) and tooth centre line. The other half is the mirror image."""
    centre = len(surface_order) // 2
    if phi[surface_order[centre]] != 0.0 or len(surface_order) % 2 != 1:
        raise SystemExit(
            "the surface of the tooth block must have its middle node on the centre line"
        )
    root_form = next(i for i in range(centre) if surface_order[i] in base_ends)
    corner = next(i for i in range(centre + 1) if radius[surface_order[i]] > tip_mm - 1.0e-4)
    angle = phi * 2.0 * math.pi / teeth
    xy = np.column_stack((-radius * np.sin(angle), radius * np.cos(angle)))[surface_order]
    turning = []
    for i in range(root_form + 1, corner):
        before, after = xy[i] - xy[i - 1], xy[i + 1] - xy[i]
        cross = before[0] * after[1] - before[1] * after[0]
        turning.append(abs(math.atan2(cross, float(before @ after))))
    tip_form = root_form + 1 + int(np.argmax(turning))
    if not 0 < root_form < tip_form < corner < centre:
        raise SystemExit("the features of the surface are not in their order")
    return [0, root_form, tip_form, corner, centre]


def _tooth_block(
    quads: IntArray,
    phi: Array,
    radius: Array,
    kind: list[str],
    pitch_mm_per_unit: Array,
    root_mm: float,
    tip_mm: float,
    teeth: int,
) -> dict[str, Any]:
    """The tooth block between the gap centre lines -1 and 0, about its tooth centre line."""
    chosen, nodes = _block(quads, phi, -1.0, 0.0)
    local_phi = phi[nodes] + 0.5
    local_r = radius[nodes].copy()
    # mirror partner of every node about the tooth centre line
    partner = np.empty(len(nodes), dtype=np.int64)
    for i in range(len(nodes)):
        distance = np.hypot(
            (local_phi + local_phi[i]) * pitch_mm_per_unit[nodes], local_r - local_r[i]
        )
        partner[i] = int(np.argmin(distance))
        if distance[partner[i]] > MATCH_TOLERANCE_MM:
            raise SystemExit(f"node {int(nodes[i])} of the tooth block has no mirror partner")
    if not np.array_equal(partner[partner], np.arange(len(nodes))):
        raise SystemExit("the mirror partners of the tooth block are no involution")
    sym_phi = 0.5 * (local_phi - local_phi[partner])
    sym_r = 0.5 * (local_r + local_r[partner])
    sym_phi[partner == np.arange(len(nodes))] = 0.0
    left = _on_line(sym_phi, -0.5)
    right = _on_line(sym_phi, 0.5)
    sym_phi[left], sym_phi[right] = -0.5, 0.5
    local_kind = [kind[int(n)] for n in nodes]
    local_quads = _counter_clockwise(_local(chosen, nodes), sym_phi * 0.1, sym_r)
    left_ordered = _by_radius(left, sym_r)
    right_ordered = _by_radius(right, sym_r)
    if [int(partner[n]) for n in left_ordered] != right_ordered:
        raise SystemExit("the interfaces of the tooth block are not mirror images")
    surface_start = [n for n in left_ordered if local_kind[n] == "surface"]
    if len(surface_start) != 1:
        raise SystemExit("the left interface of the tooth block must hold one surface node")
    surface_order = _surface_path(local_quads, local_kind, surface_start[0])
    centre_line = _by_radius(_on_line(sym_phi, 0.0), sym_r)
    grid, base_ends = _tooth_grid(local_quads, sym_r, centre_line, set(surface_order), root_mm)
    features = _surface_features(surface_order, sym_phi, sym_r, base_ends, tip_mm, teeth)
    return {
        "grid_quads": grid,
        "surface_features": features,
        "phi": [float(v) for v in sym_phi],
        "r_mm": [float(v) for v in sym_r],
        "quads": local_quads.tolist(),
        "kind": local_kind,
        "left_interface": left_ordered,
        "right_interface": right_ordered,
        "centre_line": centre_line,
        "mirror_partner": [int(n) for n in partner],
        "surface_order": surface_order,
    }


def _shoulder_block(quads: IntArray, phi: Array, radius: Array, kind: list[str]) -> dict[str, Any]:
    """The left shoulder block between the cut plane -3 and the gap centre line -2; its angle is
    counted from that gap centre line, so the cut plane lies at -1."""
    chosen, nodes = _block(quads, phi, -3.0, -2.0)
    local_phi = phi[nodes] + 2.0
    local_r = radius[nodes].copy()
    interface = _on_line(local_phi, 0.0)
    cut = _on_line(local_phi, -1.0)
    local_phi[interface], local_phi[cut] = 0.0, -1.0
    local_kind = [kind[int(n)] for n in nodes]
    local_quads = _counter_clockwise(_local(chosen, nodes), local_phi * 0.1, local_r)
    interface_ordered = _by_radius(interface, local_r)
    cut_ordered = _by_radius(cut, local_r)
    return {
        "phi": [float(v) for v in local_phi],
        "r_mm": [float(v) for v in local_r],
        "quads": local_quads.tolist(),
        "kind": local_kind,
        "interface": interface_ordered,
        "cut": cut_ordered,
        # from the top of the cut plane along the root circle to the gap centre line
        "surface_order": _surface_path(local_quads, local_kind + [], cut_ordered[-1]),
    }


def build() -> dict[str, Any]:
    reference = json.loads(SOURCE.read_text(encoding="utf-8"))
    xy = np.asarray(reference["nodes"], dtype=np.float64)
    quads = np.asarray(reference["quads"], dtype=np.int64)
    kind: list[str] = list(reference["kind"])
    meta = reference["meta"]
    teeth = int(meta["z_teeth"])
    pitch = 2.0 * math.pi / teeth
    bisector = 0.5 * (float(meta["theta_lo_rad"]) + float(meta["theta_hi_rad"]))
    radius = np.hypot(xy[:, 0], xy[:, 1])
    phi = (np.arctan2(xy[:, 1], xy[:, 0]) - bisector) / pitch
    # a node on the cut plane is a cut node for the shoulder; the surface path needs the top
    # node of the cut plane (on the root circle) to count as surface
    shoulder_kind = list(kind)
    top = int(_on_line(phi, -3.0)[np.argmax(radius[_on_line(phi, -3.0)])])
    shoulder_kind[top] = "surface"
    tooth = _tooth_block(
        quads,
        phi,
        radius,
        kind,
        pitch * radius,
        float(meta["surface_r_min_mm"]),
        float(meta["surface_r_max_mm"]),
        teeth,
    )
    shoulder = _shoulder_block(quads, phi, radius, shoulder_kind)
    shoulder["kind"] = [
        "cut" if n in set(shoulder["cut"]) else k for n, k in enumerate(shoulder["kind"])
    ]
    rings = sorted(radius[_on_line(phi, -3.0)])
    fan = float(meta["fan_ring_radius_mm"])
    rim_lines = [float(r) for r in rings if r < fan + 1.0e-3]
    return {
        "provenance": {
            "source": "kst-E_8_DY2-0_WS30_ohne_Radkoerper.inp, Part_Rad_Vz_1, mid z-slice",
            "mined": "2026-07-03, archived workbench, reference_sector_rad_vz_1.json",
            "derived_by": "scripts/build_fe_template.py",
            "note": (
                "one tooth block (gap centre to gap centre) made mirror symmetric about its "
                "tooth centre line, and the left shoulder block; phi in angular pitches, "
                "counter-clockwise"
            ),
        },
        "reference": {
            "number_of_teeth": teeth,
            "normal_module_mm": REFERENCE_MODULE_MM,
            "bore_radius_mm": float(meta["bore_radius_mm"]),
            "fan_ring_radius_mm": fan,
            "root_radius_mm": float(meta["surface_r_min_mm"]),
            "tip_radius_mm": float(meta["surface_r_max_mm"]),
            "rim_rings": len(rim_lines) - 1,
            "rim_line_radii_mm": rim_lines,
        },
        "tooth": tooth,
        "shoulder": shoulder,
    }


def render() -> str:
    return json.dumps(build(), indent=1) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = render()
    if args.check:
        current = TARGET_FILE.read_text(encoding="utf-8") if TARGET_FILE.is_file() else ""
        raise SystemExit(0 if current == text else 1)
    TARGET.mkdir(parents=True, exist_ok=True)
    TARGET_FILE.write_text(text, encoding="utf-8")
    print(TARGET_FILE.as_posix())


if __name__ == "__main__":
    main()
