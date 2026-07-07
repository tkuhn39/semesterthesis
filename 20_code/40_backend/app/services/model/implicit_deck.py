"""
@module: app.services.model.implicit_deck
@context: Domain layer — FE rolling model, the reference-faithful implicit Abaqus deck
          (structure of ``32_Abaqus/implicit/kst-E_8_DY2-0_WS30_ohne_Radkoerper.inp``).
@role: Assemble two meshed gear sectors into the WoBe-892 implicit rolling deck: two
       ``Part_Rad_Vz_{g}`` parts with per-tooth/flank ``G{g}T{nnn}F{f}`` sets +
       ``TOOTH-{g}-{nnn}F{f}`` surfaces, each gear's bore + radial sector cut faces
       (``Fesselung_Rad{g}``, reference parity) rigid-tied to a rotation node at the gear's
       mid-plane, frictionless hard contact as explicit meshing
       flank pairs, and ONE quasi-static step driving the ``driven_gear`` through a staircase
       angle while the other gear carries the resisting torque. Pure text (the caller persists
       via ``app.storage``). The plastic gear is the contact slave; a steel gear is deformable
       by default (reference parity) or an ideally stiff rigid body via the mixed-pairing
       material rule (``rigid_gears``). Sectors come from the ADR-019 transplant mesher;
       each gear is extruded about its mid-plane (z = ±b/2 + axial offset, like the
       reference deck). Spur gears, swept along +z.

       **Gear numbering (ADR-021, user decision 2026-07-04):** gear 1 = the FIRST gear of the
       stage input (.ste order — kst-E: steel pinion z=51), gear 2 = the second (plastic wheel
       z=52). NOTE: the FVA reference deck numbers the other way around (its Part_Rad_Vz_1 is
       the plastic z52 wheel) — verified against the deck's material cards and tip diameters.
       Layout follows the Kleingetriebeprüfstand top view (ADR-021 amendment): gear 1 at the
       origin (left), gear 2 at the centre distance (right) — per-gear inputs are keyed by
       input position only, never re-ordered by role or tooth count. The load case is kept
       physically identical to the reference: the plastic wheel is angle-driven, the steel
       pinion carries the resisting torque (roles by material, not by slot).
"""

import math
from dataclasses import dataclass, replace

import numpy as np
from numpy.typing import NDArray

from app.services.geometry.gear import GearStage
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.materials_card import Material, material_card
from app.services.model.mesh3d import Mesh3D, extrude_to_hex
from app.services.model.mesh_sets import (
    GearReferenceSets,
    _boundary_edges,
    build_rigid_shell,
    tag_gear_reference,
)
from app.services.model.template_mesher import generate_sector_2d, scaled_jacobians
from app.services.model.tooth_mesh import Mesh2D

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]
AmpTable = list[tuple[float, float]]  # (time, value) rows of an *AMPLITUDE table


# ----------------------------------------------------------------------------------------------
# gear part (a meshed, positioned sector + its reference sets + material)
# ----------------------------------------------------------------------------------------------
@dataclass
class GearPart:
    """One meshed gear sector positioned in the assembly, with its reference sets and material."""

    gear: int  # 1-based deck index — 1 = first stage gear (pinion), 2 = second (wheel)
    mesh: Mesh3D  # nodes already in absolute assembly coordinates
    sets: GearReferenceSets
    material: Material
    teeth: int  # full tooth count z of this gear
    face_width_mm: float
    center_xy: tuple[float, float] = (0.0, 0.0)  # rotation-axis position in the assembly
    z_mid_mm: float = 0.0  # mid-plane z (= axial offset; rotation node sits here)
    # 2-D section boundary polyline segments (E, 2, 2) in assembly coordinates — the
    # contact-closing rotation collides these against the mating gear's segments.
    boundary_segments_xy: Array | None = None
    # rigid Außenhülle (user decision 2026-07-06): when set, ``mesh.nodes`` are the LATERAL
    # boundary nodes only and these R3D4 quads replace the hexes (open axial end faces)
    shell_quads: IntArray | None = None


def _transform(nodes: Array, *, rot_rad: float, dx: float, dy: float) -> Array:
    """Rotate node (x, y) CCW about z by ``rot_rad`` then translate by (dx, dy); z unchanged."""
    c, s = math.cos(rot_rad), math.sin(rot_rad)
    x, y, z = nodes[:, 0], nodes[:, 1], nodes[:, 2]
    return np.column_stack([c * x - s * y + dx, s * x + c * y + dy, z])


def _transform_xy(pts: Array, *, rot_rad: float, dx: float, dy: float) -> Array:
    """Rotate 2-D points CCW about the origin by ``rot_rad`` then translate by (dx, dy)."""
    c, s = math.cos(rot_rad), math.sin(rot_rad)
    x, y = pts[..., 0], pts[..., 1]
    return np.stack([c * x - s * y + dx, s * x + c * y + dy], axis=-1)


def _rotate_part_about_own_axis(part: GearPart, rot_rad: float) -> GearPart:
    """Rotate a positioned part about its own rotation axis (sets/ids are untouched)."""
    cx, cy = part.center_xy
    nodes = _transform(
        np.column_stack(
            [part.mesh.nodes[:, 0] - cx, part.mesh.nodes[:, 1] - cy, part.mesh.nodes[:, 2]]
        ),
        rot_rad=rot_rad,
        dx=cx,
        dy=cy,
    )
    segments = part.boundary_segments_xy
    if segments is not None:
        segments = _transform_xy(segments - (cx, cy), rot_rad=rot_rad, dx=cx, dy=cy)
    return replace(
        part,
        mesh=Mesh3D(nodes, part.mesh.hexes, quality=part.mesh.quality),
        boundary_segments_xy=segments,
    )


def _resample_segments(segments: Array, step_mm: float) -> Array:
    """Points sampled along every polyline segment at ``step_mm`` arc spacing (both ends kept)."""
    a, b = segments[:, 0, :], segments[:, 1, :]
    lengths = np.hypot(*(b - a).T)
    out = [a, b]
    for seg_a, seg_b, ln in zip(a, b, lengths, strict=True):
        n_inner = int(ln // step_mm)
        if n_inner >= 1:
            t = (np.arange(1, n_inner + 1) / (n_inner + 1))[:, None]
            out.append(seg_a + t * (seg_b - seg_a))
    return np.concatenate(out, axis=0)


def _closing_rotation_rad(
    part1: GearPart,
    part2: GearPart,
    *,
    direction: float,
    resample_mm: float = 0.005,
    bin_mm: float = 0.010,
    backoff_mm: float = 0.015,
) -> float:
    """Rotation of gear 2 about its own axis that closes the flank gap to ~``backoff_mm``.

    Exact rotational collision detection on the 2-D boundary polylines (spur gears are
    prismatic): a rotation about gear 2's axis moves its material points on circles of
    constant radius, so first contact happens at the smallest positive angular gap between
    same-radius surface points of the two boundaries. Both boundaries are resampled at
    ``resample_mm`` arc steps, binned radially at ``bin_mm`` (each bin matched against its
    neighbours, so near-equal-radius pairs are never missed — quantisation only errs on the
    safe, smaller-rotation side), and the minimum positive angular gap in the closing
    ``direction`` (+1 = CCW of gear 2) is returned less a ``backoff_mm`` arc so the deck
    starts a hair clear of contact like the reference (~25 µm node gap) and the torque
    ramp closes it. Returns 0.0 when the boundaries do not overlap radially.
    """
    if part1.boundary_segments_xy is None or part2.boundary_segments_xy is None:
        raise ValueError("closing rotation needs boundary_segments_xy on both parts")
    ax, ay = part2.center_xy
    p1 = _resample_segments(part1.boundary_segments_xy, resample_mm)
    p2 = _resample_segments(part2.boundary_segments_xy, resample_mm)

    def polar_about_2(pts: Array) -> tuple[Array, Array]:
        x, y = pts[:, 0] - ax, pts[:, 1] - ay
        r = np.hypot(x, y)
        phi = np.arctan2(y, x) - math.pi  # contact zone (gear 2's teeth face gear 1) near 0
        return r, np.arctan2(np.sin(phi), np.cos(phi))

    r1, f1 = polar_about_2(p1)
    r2, f2 = polar_about_2(p2)
    c1x, c1y = part1.center_xy
    r_tip1 = float(np.hypot(p1[:, 0] - c1x, p1[:, 1] - c1y).max())
    a = math.hypot(ax - c1x, ay - c1y)
    r_lo, r_hi = a - r_tip1, float(r2.max())
    keep1 = (r1 >= r_lo - bin_mm) & (r1 <= r_hi + bin_mm) & (np.abs(f1) < 0.6)
    keep2 = (r2 >= r_lo - bin_mm) & (r2 <= r_hi + bin_mm) & (np.abs(f2) < 0.6)
    if not keep1.any() or not keep2.any():
        return 0.0
    # closing direction: gear-2 points move by +direction·δ in φ; contact when φ2 + s·δ = φ1
    s = 1.0 if direction >= 0.0 else -1.0
    f1k, f2k = s * f1[keep1], s * f2[keep2]
    b1 = np.floor(r1[keep1] / bin_mm).astype(np.int64)
    b2 = np.floor(r2[keep2] / bin_mm).astype(np.int64)
    order2 = np.lexsort((f2k, b2))
    b2s, f2s = b2[order2], f2k[order2]
    r1k = r1[keep1]
    delta = math.inf
    r_at_min = r_hi
    for offset in (-1, 0, 1):
        # for every gear-1 point: the largest gear-2 angle ≤ its own within bin b1 + offset
        target = b1 + offset
        for tb in np.unique(target):
            lo = int(np.searchsorted(b2s, tb, side="left"))
            hi = int(np.searchsorted(b2s, tb, side="right"))
            if hi == lo:
                continue
            mask = target == tb
            f1b = f1k[mask]
            idx = np.searchsorted(f2s[lo:hi], f1b, side="right") - 1
            ok = idx >= 0
            if not ok.any():
                continue
            gaps = f1b[ok] - f2s[lo + idx[ok]]
            i = int(np.argmin(gaps))
            if float(gaps[i]) < delta:
                delta = float(gaps[i])
                r_at_min = float(r1k[mask][ok][i])
    if not math.isfinite(delta):
        return 0.0
    return s * max(delta - backoff_mm / max(r_at_min, 1e-6), 0.0)


def build_gear_part(
    profile: ToothProfile,
    *,
    gear: int,
    material: Material,
    face_width_mm: float,
    face_layers: int,
    rot_rad: float,
    dx: float = 0.0,
    dy: float = 0.0,
    axial_offset_mm: float = 0.0,
    n_teeth: int = 4,
    n_segments: int = 1,
    bore_radius_mm: float | None = None,
    refine_root: int = 1,
    refine_flank: int = 1,
    fillet: object | None = None,
    fasten_bore: bool = True,
    fasten_cuts: bool = True,
    fasten_bottom: bool = False,
    fasten_top: bool = False,
    rigid_shell: bool = False,
) -> GearPart:
    """Mesh one gear sector, tag its reference sets, and position it in the assembly.

    The sector comes from the reference-topology transplant mesher (ADR-019): exactly the
    ANSA/FVA block structure — 4 teeth + 2 toothless shoulder pitches — with optional density
    factors and root-fillet strategy. One 2-D section is meshed once and both extruded
    (``extrude_to_hex``) and tagged (``tag_gear_reference``) from it, so the node/hex ids in
    the sets match the part exactly. The extrusion is symmetric about the mid-plane
    (z = ±b/2, reference parity) shifted by ``axial_offset_mm`` along the rotation axis —
    so gears of different face widths roll centred on each other by default and can be
    displaced parametrically (user request 2026-07-04).
    """
    if n_teeth != 4 or n_segments != 1:
        raise ValueError(
            "the reference-topology sector is fixed at 4 teeth + 2 shoulder pitches "
            f"(got n_teeth={n_teeth}, n_segments={n_segments}) — per the FVA reference deck"
        )
    sector = generate_sector_2d(
        profile,
        bore_radius_mm=bore_radius_mm,
        refine_root=refine_root,
        refine_flank=refine_flank,
        fillet=fillet,
    )
    section = Mesh2D(sector.points, np.asarray(sector.quads, dtype=np.int64))
    z0 = -face_width_mm / 2.0 + axial_offset_mm
    shell_quads: IntArray | None = None
    if rigid_shell:
        # ideally stiff Außenhülle: LATERAL boundary surface only (open axial end faces),
        # renumbered to the boundary nodes — the element reduction is the whole point
        shell_nodes, shell_quads, sets = build_rigid_shell(
            section,
            profile=profile,
            gear=gear,
            n_teeth=n_teeth,
            n_segments=n_segments,
            layers=face_layers,
            width_mm=face_width_mm,
            z0_mm=z0,
        )
        mesh = Mesh3D(
            _transform(shell_nodes, rot_rad=rot_rad, dx=dx, dy=dy),
            np.zeros((0, 8), dtype=np.int64),
            quality=None,
        )
    else:
        quality = scaled_jacobians(sector.coords, sector.quads)
        solid = extrude_to_hex(
            section,
            quality,
            width=face_width_mm,
            layers=face_layers,
            z0=z0,
        )
        mesh = Mesh3D(
            _transform(solid.nodes, rot_rad=rot_rad, dx=dx, dy=dy),
            solid.hexes,
            quality=solid.quality,
        )
        sets = tag_gear_reference(
            section,
            profile=profile,
            gear=gear,
            n_teeth=n_teeth,
            n_segments=n_segments,
            layers=face_layers,
            fasten_bore=fasten_bore,
            fasten_cuts=fasten_cuts,
            fasten_bottom=fasten_bottom,
            fasten_top=fasten_top,
        )
    segments = np.array(
        [
            [
                section.nodes[int(section.quads[qi][p])][:2],
                section.nodes[int(section.quads[qi][(p + 1) % 4])][:2],
            ]
            for qi, p in _boundary_edges(section)
        ]
    )
    segments = _transform_xy(segments, rot_rad=rot_rad, dx=dx, dy=dy)
    return GearPart(
        gear=gear,
        mesh=mesh,
        sets=sets,
        material=material,
        teeth=profile.z,
        face_width_mm=face_width_mm,
        center_xy=(dx, dy),
        z_mid_mm=axial_offset_mm,
        boundary_segments_xy=segments,
        shell_quads=shell_quads,
    )


# ----------------------------------------------------------------------------------------------
# kinematics + per-position torque-cycle amplitudes
# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class RollKinematics:
    """The rolling load case — per-Wälzstellung torque cycle (user decision 2026-07-06).

    Physics per position k (reference parity — the FVA deck alternates base/full torque the
    same way): the angle-driven gear is HELD at position k while the torque gear ramps its
    moment ``base → full`` (SMOOTH STEP), holds ``hold`` increments at full torque (Newton
    equilibrium every increment; the hold lets the STABILIZE artificial-damping energy decay
    before the measurement frame at the END of the hold), ramps back down to the base torque
    (``base_fraction`` of full — keeps the flanks seated, no free rigid-body spin), and only
    then the angle sub-ramps to position k+1 over ``move`` increments. The very first ramp
    starts from 0 over ``settle`` increments.
    """

    center_distance_mm: float
    torque_nmm: float  # full torque applied at the NON-driven gear's rotation node, DOF6
    roll_angle_rad: float  # total driven-gear rotation over the roll
    n_roll_positions: int = 30  # Wälzstellungen (measurement positions) over the roll
    ramp_up: int = 2  # increments per position: base → full torque
    hold: int = 2  # increments held at full torque (measurement at the END)
    ramp_down: int = 2  # increments per position: full → base torque
    move: int = 2  # increments of the angle sub-ramp between positions (at base torque)
    settle: int = 6  # increments of the very first ramp 0 → full (contact seating)
    base_fraction: float = 0.01  # holding torque between positions, fraction of full
    stabilize: float = 2.0e-4  # *STATIC, STABILIZE (contact-driven rigid-body damping)

    @property
    def per_position_increments(self) -> int:
        return self.ramp_down + self.move + self.ramp_up + self.hold

    @property
    def total_increments(self) -> int:
        return self.settle + self.hold + (self.n_roll_positions - 1) * self.per_position_increments


def _torque_cycle_pairs(kin: RollKinematics) -> tuple[AmpTable, AmpTable, list[float]]:
    """(AMP-ANGLE, AMP-TORQUE, measurement instants) for the per-position torque cycle.

    Time is normalised to [0, 1] over ``total_increments`` equal increments; the tables carry
    only the PHASE BOUNDARY vertices (the amplitudes are emitted as ``SMOOTH STEP``, so ramps
    are S-shaped with zero slope at both ends — gentle contact seating at low torque, no
    overshoot when reaching full torque; constant segments stay exactly constant). Measurement
    instants are the ends of the full-torque holds — exact multiples of dt by construction —
    and become the ``*TIME POINTS, NAME=MEASURE`` table.
    """
    total = kin.total_increments
    dt = 1.0 / total
    beta = kin.base_fraction
    dphi = 1.0 / max(kin.n_roll_positions - 1, 1)  # angle fraction per move
    angle: AmpTable = [(0.0, 0.0)]
    torque: AmpTable = [(0.0, 0.0)]
    measure: list[float] = []
    j = 0  # increment cursor

    def seg(n: int, torque_value: float, angle_value: float) -> None:
        nonlocal j
        if n > 0:
            j += n
            torque.append((j * dt, torque_value))
            angle.append((j * dt, angle_value))

    seg(kin.settle, 1.0, 0.0)  # position 1: first ramp 0 → full
    seg(kin.hold, 1.0, 0.0)
    measure.append(j * dt)
    for k in range(2, kin.n_roll_positions + 1):
        a_prev, a_new = (k - 2) * dphi, (k - 1) * dphi
        seg(kin.ramp_down, beta, a_prev)  # full → base, angle held
        seg(kin.move, beta, a_new)  # angle sub-ramp at base torque (smooth)
        seg(kin.ramp_up, 1.0, a_new)  # base → full at the new position
        seg(kin.hold, 1.0, a_new)
        measure.append(j * dt)  # measurement = end of hold
    assert j == total, f"cycle increments mismatch: {j} != {total}"
    return angle, torque, measure


# ----------------------------------------------------------------------------------------------
# keyword block helpers
# ----------------------------------------------------------------------------------------------
def _wrap(ids: list[int] | IntArray, per_line: int = 16) -> str:
    vals = [int(v) for v in ids]
    rows = [vals[i : i + per_line] for i in range(0, len(vals), per_line)]
    return "\n".join(", ".join(str(v) for v in row) for row in rows)


def _amplitude_block(
    name: str, pairs: list[tuple[float, float]], per_line: int = 4, *, smooth_step: bool = True
) -> str:
    """An ``*AMPLITUDE`` table; ``smooth_step`` emits ``DEFINITION=SMOOTH STEP`` (S-shaped
    transitions with zero slope at both vertices — user decision 2026-07-06; constant
    segments between equal vertices stay exactly constant)."""
    flat = [f"{t:.9f}, {v:.9f}" for t, v in pairs]
    rows = [flat[i : i + per_line] for i in range(0, len(flat), per_line)]
    body = "\n".join(", ".join(r) for r in rows)
    definition = ", DEFINITION=SMOOTH STEP" if smooth_step else ""
    return f"*AMPLITUDE, NAME={name}{definition}\n{body}"


def _time_points_block(name: str, times: list[float], per_line: int = 8) -> str:
    flat = [f"{t:.9f}" for t in times]
    rows = [flat[i : i + per_line] for i in range(0, len(flat), per_line)]
    body = "\n".join(", ".join(r) for r in rows)
    return f"*TIME POINTS, NAME={name}\n{body}"


def _foldable(deck: str) -> str:
    """Indent every data line one tab (keyword and ``**`` lines stay at column 0).

    Lets editors fold the long ``*NODE`` / ``*ELEMENT`` / ``*NSET`` blocks by indentation; Abaqus
    ignores leading whitespace on data lines, and the keyword lines stay column-0 so the parser
    still finds them.
    """
    return "\n".join(
        line if not line or line.startswith("*") else f"\t{line}" for line in deck.split("\n")
    )


def _part_block(part: GearPart, element_type: str) -> str:
    g = part.gear
    mesh, sets = part.mesh, part.sets
    elset = f"ALL_ELEMENTS_Part_Rad_Vz_{g}"
    nodes = "\n".join(
        f"{i + 1}, {x:.6f}, {y:.6f}, {z:.6f}" for i, (x, y, z) in enumerate(mesh.nodes)
    )
    if part.shell_quads is not None:
        # rigid Außenhülle: R3D4 lateral surface, open end faces, no section/material;
        # every quad is outward-oriented by construction → contact surfaces are SPOS
        elems = "\n".join(
            f"{e + 1}, " + ", ".join(str(n + 1) for n in quad)
            for e, quad in enumerate(part.shell_quads)
        )
        lines = [
            f"*PART, NAME=Part_Rad_Vz_{g}",
            f"*NODE\n{nodes}",
            f"*ELEMENT, TYPE=R3D4, ELSET={elset}\n{elems}",
        ]
        for (tooth, flank), node_ids in sorted(sets.flank_nodes.items()):
            tag = f"G{g}T{tooth:03d}F{flank}"
            surf = f"TOOTH-{g}-{tooth:03d}F{flank}"
            lines += [
                f"*NSET, NSET={tag}_NODESET\n{_wrap(node_ids)}",
                f"*ELSET, ELSET={tag}_ELEMENTSET\n{_wrap(sets.flank_elements[(tooth, flank)])}",
                f"*SURFACE, NAME={surf}, TYPE=ELEMENT\n{tag}_ELEMENTSET, SPOS",
            ]
        lines.append("*END PART")
        return "\n".join(lines)
    elems = "\n".join(
        f"{e + 1}, " + ", ".join(str(n + 1) for n in hexa) for e, hexa in enumerate(mesh.hexes)
    )
    lines = [
        f"*PART, NAME=Part_Rad_Vz_{g}",
        f"*NODE\n{nodes}",
        f"*ELEMENT, TYPE={element_type}, ELSET={elset}\n{elems}",
    ]
    for (tooth, flank), node_ids in sorted(sets.flank_nodes.items()):
        tag = f"G{g}T{tooth:03d}F{flank}"
        surf = f"TOOTH-{g}-{tooth:03d}F{flank}"
        faces = "\n".join(f"{hid}, {face}" for hid, face in sets.flank_faces[(tooth, flank)])
        lines += [
            f"*NSET, NSET={tag}_NODESET\n{_wrap(node_ids)}",
            f"*ELSET, ELSET={tag}_ELEMENTSET\n{_wrap(sets.flank_elements[(tooth, flank)])}",
            f"*SURFACE, NAME={surf}, TYPE=ELEMENT\n{faces}",
        ]
    lines.append(f"*SOLID SECTION, ELSET={elset}, MATERIAL=MATERIAL-Part_Rad_Vz_{g}\n1.,")
    lines.append("*END PART")
    return "\n".join(lines)


def _material_card_for(part: GearPart) -> str:
    """The material card named ``MATERIAL-Part_Rad_Vz_{g}`` (what the solid section references)."""
    label = part.material.name
    renamed = replace(part.material, name=f"MATERIAL-Part_Rad_Vz_{part.gear}")
    return f"** material: {label}\n{material_card(renamed)}"


def _flank_centroids(part: GearPart) -> dict[tuple[int, int], Array]:
    """Absolute centroid of each (tooth, flank) flank surface (mean of its node coordinates)."""
    return {
        key: part.mesh.nodes[ids - 1].mean(axis=0) for key, ids in part.sets.flank_nodes.items()
    }


def _meshing_contact_pairs(
    slave: GearPart, master: GearPart, *, max_gap_mm: float
) -> list[tuple[str, str]]:
    """Pair each slave flank with the nearest master flank within ``max_gap_mm``.

    The slave (plastic side, reference parity) is listed FIRST in each *CONTACT PAIR line.
    Geometry-driven so it adapts to the assembly phase: only flanks that face each other across the
    mesh (near the line of centres) fall within the gap and become explicit contact pairs.
    """
    c1, c2 = _flank_centroids(slave), _flank_centroids(master)
    return _nearest_flank_pairs(slave.gear, c1, master.gear, c2, max_gap_mm=max_gap_mm)


def _nearest_flank_pairs(
    slave_gear: int,
    slave_centroids: dict[tuple[int, int], Array],
    master_gear: int,
    master_centroids: dict[tuple[int, int], Array],
    *,
    max_gap_mm: float,
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for (t1, f1), p1 in sorted(slave_centroids.items()):
        best: tuple[float, tuple[int, int]] | None = None
        for (t2, f2), p2 in master_centroids.items():
            d = float(np.linalg.norm(p1 - p2))
            if best is None or d < best[0]:
                best = (d, (t2, f2))
        if best is not None and best[0] <= max_gap_mm:
            t2, f2 = best[1]
            s1 = f"Rad_Vz_{slave_gear}.TOOTH-{slave_gear}-{t1:03d}F{f1}"
            s2 = f"Rad_Vz_{master_gear}.TOOTH-{master_gear}-{t2:03d}F{f2}"
            pairs.append((s1, s2))
    return pairs


def _sweep_contact_pairs(
    slave: GearPart,
    master: GearPart,
    *,
    max_gap_mm: float,
    roll_angle_rad: float,
    start_at_edge: bool,
    driven_gear: int,
    z: dict[int, int],
    samples: int = 9,
) -> list[tuple[str, str]]:
    """Union of the nearest-flank pairings over the WHOLE roll (kinematically sampled).

    Proximity pairing at one configuration misses flank pairs that only engage later in the
    sweep (the reference deck pairs the edge teeth too — 7 pairs for kst-E). The flank
    centroids are rotated through ``samples`` coupled roll positions and every pairing found
    within ``max_gap_mm`` at any position becomes a *CONTACT PAIR* (an open pair is harmless;
    a missing pair means undetected penetration mid-roll).
    """

    def rotate(centroids: dict[tuple[int, int], Array], part: GearPart, phi: float) -> dict:
        cx, cy = part.center_xy
        c, s = math.cos(phi), math.sin(phi)
        out = {}
        for key, p in centroids.items():
            x, y = p[0] - cx, p[1] - cy
            out[key] = np.array([c * x - s * y + cx, s * x + c * y + cy, p[2]])
        return out

    c_slave = _flank_centroids(slave)
    c_master = _flank_centroids(master)
    torque_gear = 3 - driven_gear
    union: set[tuple[str, str]] = set()
    n = max(samples, 2)
    for i in range(n):
        s = i / (n - 1)
        phi_driven = (-roll_angle_rad / 2.0 if start_at_edge else 0.0) + s * roll_angle_rad
        phis = {driven_gear: phi_driven, torque_gear: -phi_driven * z[driven_gear] / z[torque_gear]}
        rs = rotate(c_slave, slave, phis[slave.gear])
        rm = rotate(c_master, master, phis[master.gear])
        union.update(_nearest_flank_pairs(slave.gear, rs, master.gear, rm, max_gap_mm=max_gap_mm))
    return sorted(union)


def _measurement_output_lines(parts: dict[int, GearPart], rigid_gears: frozenset[int]) -> list[str]:
    """Per-flank-set output requests (reference grouping: NODE F1, NODE F2, CONTACT F1,
    CONTACT F2, ELEMENT F1, ELEMENT F2 per tooth per gear). Rigid gears get no ELEMENT
    output (E/S undefined on rigid elements) and no CONTACT output (master side carries
    no contact data under surface-to-surface)."""
    lines = ["*NODE OUTPUT, NSET=MASTERKNOTEN_NODE_SET\nCF, RF, U,"]
    for g in sorted(parts):
        part = parts[g]
        rigid = g in rigid_gears
        for tooth in sorted({t for t, _ in part.sets.flank_nodes}):
            tags = [f"G{g}T{tooth:03d}F{f}" for f in (1, 2) if (tooth, f) in part.sets.flank_nodes]
            for tag in tags:
                lines.append(f"*NODE OUTPUT, NSET=Rad_Vz_{g}.{tag}_NODESET\nCF,RF,U,")
            if not rigid:
                for tag in tags:
                    lines.append(
                        f"*CONTACT OUTPUT, NSET=Rad_Vz_{g}.{tag}_NODESET\nCFORCE,CSTRESS,CDISP,"
                    )
                for tag in tags:
                    lines.append(
                        f"*ELEMENT OUTPUT, ELSET=Rad_Vz_{g}.{tag}_ELEMENTSET, directions=YES\n"
                        "E, MISESMAX, MISESONLY, NE, PRESSONLY, S,"
                    )
    lines.append("*NODE OUTPUT\nU,")
    return lines


def build_implicit_pair_deck(
    part1: GearPart,
    part2: GearPart,
    *,
    kin: RollKinematics,
    contact_gap_mm: float | None = None,
    contact_pairs: list[tuple[str, str]] | None = None,
    element_type: str = "C3D8R",
    rigid_gears: frozenset[int] = frozenset(),
    driven_gear: int = 2,
    slave_gear: int = 2,
    heading: str = "FE rolling model (implicit, ohne Radkoerper) - generated",
) -> str:
    """Build the full reference-faithful implicit deck for a meshed gear pair.

    Each gear's rotation node ``Rot_Node_Rad{g}`` sits on its rotation axis at the gear's
    mid-plane (``center_xy``, ``z_mid_mm``). Contact is frictionless hard, as explicit meshing
    flank pairs with the ``slave_gear`` flank listed first (slave — the plastic side, reference
    parity); pass ``contact_pairs`` when the pairing was computed at a different configuration
    (e.g. the closed centered state before the edge-start pre-rotation — the pair set is
    roll-invariant). One static step runs the per-position torque cycle (``RollKinematics``):
    the ``driven_gear`` angle staircases through ``kin.roll_angle_rad`` with smooth sub-ramps
    while the other gear cycles ``kin.torque_nmm`` base→full→base per position; field frames
    land on every increment (animation, U only) plus the exact measurement instants
    (``*TIME POINTS, NAME=MEASURE`` — full reference payload per flank set).
    ``element_type`` defaults to C3D8R (the reference choice). Data lines are tab-indented so
    the long mesh blocks fold in an editor. A comment table in the heading documents the gear
    mapping — the FVA reference deck numbers its gears the other way around (ADR-021).

    ``rigid_gears`` implements the material-mode rule for mixed pairings (user decision): the
    listed gears become **ideally stiff** rigid bodies about their rotation node instead of the
    bore + cut-face Fesselung tie. Contact surfaces and set names are unchanged.
    """
    if driven_gear not in (1, 2) or slave_gear not in (1, 2):
        raise ValueError("driven_gear and slave_gear must be 1 or 2")
    if slave_gear in rigid_gears:
        raise ValueError("the contact slave must stay deformable (rigid side is the master)")
    gap = 2.0 if contact_gap_mm is None else contact_gap_mm  # mm; ~one module, caller-tunable
    torque_gear = 3 - driven_gear
    parts = {part1.gear: part1, part2.gear: part2}
    angle_pairs, torque_pairs, measure_times = _torque_cycle_pairs(kin)
    pairs = (
        contact_pairs
        if contact_pairs is not None
        else _meshing_contact_pairs(parts[slave_gear], parts[3 - slave_gear], max_gap_mm=gap)
    )

    def fastening(part: GearPart) -> str:
        g = part.gear
        if g in rigid_gears:
            return f"*RIGID BODY, REF NODE={g}, ELSET=Rad_Vz_{g}.ALL_ELEMENTS_Part_Rad_Vz_{g}"
        return f"*RIGID BODY, REF NODE={g}, TIE NSET=Fesselung_Rad{g}"

    def rot_node(part: GearPart) -> str:
        cx, cy = part.center_xy
        return f"{part.gear}, {cx:.6f}, {cy:.6f}, {part.z_mid_mm:.6f}"

    def gear_comment(part: GearPart) -> str:
        role = "angle-driven (AMP-ANGLE)" if part.gear == driven_gear else "torque (AMP-TORQUE)"
        rigid = (
            ", RIGID SHELL (R3D4 lateral surface, open end faces)"
            if part.gear in rigid_gears
            else ""
        )
        cx, cy = part.center_xy
        return (
            f"** Gear {part.gear}: z={part.teeth}, b={part.face_width_mm:g} mm, "
            f"material={part.material.name}, axis at ({cx:g}, {cy:g}), "
            f"mid-plane z={part.z_mid_mm:g} mm, {role}{rigid}"
        )

    # rigid gears carry no Fesselung nset (the rigid body IS the constraint; the shell has
    # no interior nodes an empty tie set could reference)
    fesselung_nsets = [
        f"*NSET, NSET=Fesselung_Rad{p.gear}, INSTANCE=Rad_Vz_{p.gear}\n"
        f"{_wrap(p.sets.fastening_nodes)}"
        for p in (part1, part2)
        if p.gear not in rigid_gears
    ]
    assembly_nodes = "\n".join(
        (
            "*NODE",
            rot_node(part1),
            "*NODE",
            rot_node(part2),
            "*NSET, NSET=Rot_Node_Rad1\n1,",
            "*NSET, NSET=Rot_Node_Rad2\n2,",
            "*NSET, NSET=MASTERKNOTEN_NODE_SET\n1, 2",
            *fesselung_nsets,
            fastening(part1),
            fastening(part2),
        )
    )
    contact = "\n".join(
        [
            "*SURFACE INTERACTION, NAME=INTPROP-1",
            "1.,",
            "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD",
        ]
        + [
            f"*CONTACT PAIR, INTERACTION=INTPROP-1, TYPE=SURFACE TO SURFACE\n{s1}, {s2}"
            for s1, s2 in pairs
        ]
    )
    assembly = "\n".join(
        (
            "*ASSEMBLY, NAME=Assembly",
            "*INSTANCE, NAME=Rad_Vz_1, PART=Part_Rad_Vz_1\n*END INSTANCE",
            "*INSTANCE, NAME=Rad_Vz_2, PART=Part_Rad_Vz_2\n*END INSTANCE",
            assembly_nodes,
            contact,
            "*END ASSEMBLY",
        )
    )
    dt = 1.0 / kin.total_increments
    # dt = initial = MAX pins the increment grid (frame alignment); tiny min lets a cutback
    # recover instead of aborting. TIME POINTS are hit exactly by Standard regardless.
    step = "\n".join(
        (
            "*STEP, NAME=STEP-1, NLGEOM=YES, INC=100000",
            f"*STATIC, STABILIZE={kin.stabilize:.4g}, ALLSDTOL=0.0, CONTINUE=NO\n"
            f"{dt:.8g}, 1.0, 1e-08, {dt:.8g}",
            "*RESTART, WRITE, FREQUENCY=0",
            _time_points_block("MEASURE", measure_times),
            "** animation frames: one per increment, displacements only",
            f"*OUTPUT, FIELD, NUMBER INTERVAL={kin.total_increments}, TIMEMARKS=NO",
            "*NODE OUTPUT\nU,",
            "** measurement frames: full-torque equilibrium at the end of every hold",
            "*OUTPUT, FIELD, TIME POINTS=MEASURE",
            *_measurement_output_lines(parts, rigid_gears),
            "*BOUNDARY\nRot_Node_Rad1, 1, 5",
            "*BOUNDARY\nRot_Node_Rad2, 1, 5",
            f"*BOUNDARY, AMPLITUDE=AMP-ANGLE\nRot_Node_Rad{driven_gear}, 6, 6, "
            f"{kin.roll_angle_rad:.8g}",
            f"*CLOAD, AMPLITUDE=AMP-TORQUE\nRot_Node_Rad{torque_gear}, 6, {kin.torque_nmm:.8g}",
            "*END STEP",
        )
    )
    cycle_comment = (
        f"** Load cycle per Wälzstellung (SMOOTH STEP): torque {kin.base_fraction:.0%}"
        f"->100%->{kin.base_fraction:.0%} of {kin.torque_nmm:.6g} N·mm "
        f"(ramp_up={kin.ramp_up}, hold={kin.hold}, ramp_down={kin.ramp_down}, "
        f"move={kin.move}, settle={kin.settle}); angle steps only at base torque."
    )
    measure_comment = "\n".join(
        "** measure t = " + ", ".join(f"{t:.9f}" for t in measure_times[i : i + 8])
        for i in range(0, len(measure_times), 8)
    )
    return _foldable(
        "\n".join(
            (
                f"*HEADING\n{heading}",
                "** Gear numbering follows the stage input order (ADR-021): "
                "gear 1 = the stage's first gear, gear 2 = the second.",
                "** Rig layout: gear 1 on the axis at the origin, gear 2 at the centre "
                "distance. (The FVA reference",
                "** deck kst-E_8_DY2-0_WS30 numbers its gears the other way around.)",
                gear_comment(part1),
                gear_comment(part2),
                cycle_comment,
                measure_comment,
                "**",
                _part_block(part1, element_type),
                "**",
                _part_block(part2, element_type),
                "**",
                assembly,
                "**",
                "**MATERIALS",
                # rigid shells take no section/material card
                *(_material_card_for(p) for p in (part1, part2) if p.gear not in rigid_gears),
                "**",
                _amplitude_block("AMP-ANGLE", angle_pairs),
                _amplitude_block("AMP-TORQUE", torque_pairs),
                "**",
                step,
            )
        )
    )


@dataclass(frozen=True)
class AssembledPair:
    """A meshed, positioned, backlash-closed pair at the CENTERED configuration.

    The shared assembly stage of BOTH deck modes (single quasi-static file and position
    series) — one code path, one geometry (SSOT). ``pairs`` is the roll-invariant contact
    pair list computed at this closed configuration.
    """

    part1: GearPart
    part2: GearPart
    pairs: list[tuple[str, str]]
    a: float
    z: dict[int, int]
    closing_rad: float
    gap: float


def assemble_centered_pair(
    stage: GearStage,
    *,
    gear1_material: Material,
    gear2_material: Material,
    face_layers: int,
    face_width_mm: tuple[float, float] | None,
    axial_offset_mm: tuple[float, float],
    phase_rad: float,
    align_contact: bool,
    contact_gap_mm: float | None,
    roll_angle_rad: float,
    start_at_edge: bool,
    driven_gear: int,
    slave_gear: int,
    roll_sign: float = 1.0,
    rigid_gears: frozenset[int] = frozenset(),
    tip_relief: tuple[tuple[float, float | None], tuple[float, float | None]] = (
        (0.0, None),
        (0.0, None),
    ),
    refine_root: int,
    refine_flank: int,
    fillet_gear1: object | None,
    fillet_gear2: object | None,
    fasten_bore: bool,
    fasten_cuts: bool,
    fasten_bottom: bool,
    fasten_top: bool,
) -> AssembledPair:
    """Mesh, position (centered), close the backlash and pair the contact flanks.

    ``tip_relief`` carries per-gear (C_αa [µm], d_Ca [mm] or None) into the tooth profiles
    so the FE contour includes the Kopfrücknahme like the FVA transient FEM.
    """
    profile1 = ToothProfile.from_stage(
        stage, 0, tip_relief_um=tip_relief[0][0], tip_relief_start_diameter_mm=tip_relief[0][1]
    )
    profile2 = ToothProfile.from_stage(
        stage, 1, tip_relief_um=tip_relief[1][0], tip_relief_start_diameter_mm=tip_relief[1][1]
    )
    a = stage.working_center_distance_mm
    if face_width_mm is None:
        if stage.face_width_mm is None:
            raise ValueError("face widths needed: pass face_width_mm or a stage carrying them")
        face_width_mm = (abs(stage.face_width_mm[0]), abs(stage.face_width_mm[1]))
    fasten = {
        "fasten_bore": fasten_bore,
        "fasten_cuts": fasten_cuts,
        "fasten_bottom": fasten_bottom,
        "fasten_top": fasten_top,
    }
    part1 = build_gear_part(
        profile1,
        gear=1,
        material=gear1_material,
        face_width_mm=face_width_mm[0],
        face_layers=face_layers,
        rot_rad=-math.pi / 2.0,
        axial_offset_mm=axial_offset_mm[0],
        refine_root=refine_root,
        refine_flank=refine_flank,
        fillet=fillet_gear1,
        rigid_shell=1 in rigid_gears,
        **fasten,
    )
    part2 = build_gear_part(
        profile2,
        gear=2,
        material=gear2_material,
        face_width_mm=face_width_mm[1],
        face_layers=face_layers,
        rot_rad=math.pi / 2.0 + math.pi / profile2.z + phase_rad,
        dx=a,
        axial_offset_mm=axial_offset_mm[1],
        refine_root=refine_root,
        refine_flank=refine_flank,
        fillet=fillet_gear2,
        rigid_shell=2 in rigid_gears,
        **fasten,
    )
    closing_rad = 0.0
    if align_contact:
        # the driven gear's step rotation defines the closing sense (flips with the drive's
        # Drehrichtung): rotate gear 2 so its working flank ends up a hair clear of gear 1's
        # (single-flank contact, like the reference), letting the torque ramp close the rest
        closing_rad = _closing_rotation_rad(
            part1, part2, direction=roll_sign * (1.0 if driven_gear == 2 else -1.0)
        )
        if closing_rad != 0.0:
            part2 = _rotate_part_about_own_axis(part2, closing_rad)
    gap = contact_gap_mm if contact_gap_mm is not None else 1.5 * stage.normal_module_mm
    # Contact pairs as the union over the WHOLE kinematically sampled roll — proximity at
    # one configuration would miss the edge-tooth pairs that only engage later (the
    # reference deck pairs them too: 7 pairs for kst-E).
    parts = {1: part1, 2: part2}
    z = {1: profile1.z, 2: profile2.z}
    pairs = _sweep_contact_pairs(
        parts[slave_gear],
        parts[3 - slave_gear],
        max_gap_mm=gap,
        roll_angle_rad=roll_angle_rad,
        start_at_edge=start_at_edge,
        driven_gear=driven_gear,
        z=z,
    )
    return AssembledPair(
        part1=part1,
        part2=part2,
        pairs=pairs,
        a=a,
        z=z,
        closing_rad=closing_rad,
        gap=gap,
    )


def build_implicit_pair_from_stage(
    stage: GearStage,
    *,
    gear1_material: Material,
    gear2_material: Material,
    torque_gear2_nmm: float,
    face_layers: int = 6,
    face_width_mm: tuple[float, float] | None = None,
    axial_offset_mm: tuple[float, float] = (0.0, 0.0),
    roll_pitches: float = 3.0,
    n_roll_positions: int = 30,
    ramp_up: int = 2,
    hold: int = 2,
    ramp_down: int = 2,
    move: int = 2,
    settle: int = 6,
    base_torque_fraction: float = 0.01,
    stabilize: float = 2.0e-4,
    phase_rad: float = 0.0,
    align_contact: bool = True,
    start_at_edge: bool = True,
    rotation_sense: str = "cw",
    contact_gap_mm: float | None = None,
    element_type: str = "C3D8R",
    rigid_gears: frozenset[int] = frozenset(),
    tip_relief: tuple[tuple[float, float | None], tuple[float, float | None]] = (
        (0.0, None),
        (0.0, None),
    ),
    driven_gear: int = 2,
    slave_gear: int = 2,
    refine_root: int = 1,
    refine_flank: int = 1,
    fillet_gear1: object | None = None,
    fillet_gear2: object | None = None,
    fasten_bore: bool = True,
    fasten_cuts: bool = True,
    fasten_bottom: bool = False,
    fasten_top: bool = False,
    heading: str = "FE rolling model (implicit, ohne Radkoerper) - generated from GearStage",
) -> str:
    """One-call build: a ``GearStage`` → meshed, positioned pair → reference-faithful implicit deck.

    **Slot semantics (ADR-021, amended):** everything is keyed by the stage INPUT position —
    gear 1 = the stage's first gear, gear 2 = the second — and never re-ordered by role or
    tooth count (kst-E: gear 1 = steel pinion z=51, gear 2 = plastic wheel z=52; but gear 1
    may just as well be the larger wheel). All per-gear inputs (materials, face widths, axial
    offsets, fillets) follow that chain. Layout matches the Kleingetriebeprüfstand top view:
    **gear 1 at the origin (left), gear 2 at the working centre distance (right)**, gear 2
    rotated half a pitch so a gap meshes gear 1's tooth (``phase_rad`` adds a tunable
    mounting offset).

    ``align_contact`` (default, reference parity) then rotates gear 2 about its own axis by
    the backlash-closing angle so the WORKING flanks start a hair (~15 µm arc) clear of
    contact — measured 2026-07-04: the reference deck stands in single-flank contact
    (~25 µm node gap on the −y flanks) and lets the torque ramp close the rest, instead of
    the tooth floating centred in the gap with the full allowance backlash on each side.
    ``fasten_bore``/``fasten_cuts``/``fasten_bottom``/``fasten_top`` mirror the FVA
    "Fesselung" checkboxes (defaults = the reference: bore + both cut planes, complete).

    Load case (user decision 2026-07-06, reference-parity cycle): ``driven_gear`` (default 2
    — the plastic wheel for kst-E) is angle-STEPPED through ``roll_pitches`` of its pitches
    (default 3 — with the 4-tooth sector the middle two teeth complete the whole engagement
    boundary-free; the edge teeth carry the run-in/run-out); the other gear cycles the torque
    base→full→base per position (see :class:`RollKinematics`). ``start_at_edge`` pre-rotates
    the pair so the roll BEGINS at an edge tooth instead of the middle. ``torque_gear2_nmm``
    is the torque level expressed AT GEAR 2 (M₂); it is converted to the loaded gear via the
    tooth counts (T_g = M₂ · z_g/z₂). Contact pairs are computed at the closed, centered
    configuration (roll-invariant set) and passed through. The contact gap defaults to 1.5·mₙ.

    Each gear keeps its own face width (``face_width_mm`` overrides the stage values, order
    (gear 1, gear 2)) and is extruded symmetric about its mid-plane, shifted by
    ``axial_offset_mm`` (gear 1, gear 2) along the rotation axis — reference parity: gears of
    unequal width roll centred on each other by default, and both rotation nodes sit at their
    gear's mid-plane instead of on a side face.

    Both sectors come from the reference-topology transplant mesher; ``refine_root`` /
    ``refine_flank`` set the FVA density factors and ``fillet_gear1`` / ``fillet_gear2`` an
    optional optimized root-fillet strategy per gear (run the mating-tip clearance check
    first). ``rigid_gears`` lists gears rendered ideally stiff (mixed-pairing rule — pass the
    steel side); ``slave_gear`` is the contact slave (the plastic side).
    """
    # rotation sense of the drive (Leistungsfluss "Drehrichtung"): "cw" = the validated
    # default (torque gear turns clockwise in the rig top view, user images 2026-07-06);
    # "ccw" mirrors the whole load case (roll sign, closing flank, start offset).
    roll_sign = 1.0 if rotation_sense != "ccw" else -1.0
    roll_angle_rad = roll_sign * roll_pitches * 2.0 * math.pi / stage.teeth[driven_gear - 1]
    pair = assemble_centered_pair(
        stage,
        gear1_material=gear1_material,
        gear2_material=gear2_material,
        face_layers=face_layers,
        face_width_mm=face_width_mm,
        axial_offset_mm=axial_offset_mm,
        phase_rad=phase_rad,
        align_contact=align_contact,
        contact_gap_mm=contact_gap_mm,
        roll_angle_rad=roll_angle_rad,
        start_at_edge=start_at_edge,
        driven_gear=driven_gear,
        slave_gear=slave_gear,
        roll_sign=roll_sign,
        rigid_gears=rigid_gears,
        tip_relief=tip_relief,
        refine_root=refine_root,
        refine_flank=refine_flank,
        fillet_gear1=fillet_gear1,
        fillet_gear2=fillet_gear2,
        fasten_bore=fasten_bore,
        fasten_cuts=fasten_cuts,
        fasten_bottom=fasten_bottom,
        fasten_top=fasten_top,
    )
    part1, part2 = pair.part1, pair.part2
    a, z, closing_rad, gap, pairs = pair.a, pair.z, pair.closing_rad, pair.gap, pair.pairs
    torque_gear = 3 - driven_gear

    start_offset_rad = 0.0
    if start_at_edge:
        # start of roll at an EDGE tooth (user decision 2026-07-06): pre-rotate the driven
        # gear by −roll/2 and counter-rotate the other kinematically (φ_other = −φ·z_d/z_o),
        # so the sweep walks the contact across the sector and the MIDDLE teeth see the
        # full, boundary-free engagement.
        start_offset_rad = -roll_angle_rad / 2.0
        if driven_gear == 2:
            part2 = _rotate_part_about_own_axis(part2, start_offset_rad)
            part1 = _rotate_part_about_own_axis(part1, -start_offset_rad * z[2] / z[1])
        else:
            part1 = _rotate_part_about_own_axis(part1, start_offset_rad)
            part2 = _rotate_part_about_own_axis(part2, -start_offset_rad * z[1] / z[2])

    kin = RollKinematics(
        center_distance_mm=a,
        # M₂ (torque at gear 2) converted to the gear that actually carries the load
        torque_nmm=torque_gear2_nmm * z[torque_gear] / z[2],
        roll_angle_rad=roll_angle_rad,
        n_roll_positions=n_roll_positions,
        ramp_up=ramp_up,
        hold=hold,
        ramp_down=ramp_down,
        move=move,
        settle=settle,
        base_fraction=base_torque_fraction,
        stabilize=stabilize,
    )
    if align_contact:
        heading = f"{heading} | contact-aligned: gear 2 rotated {closing_rad:+.8f} rad"
    if start_at_edge:
        heading = (
            f"{heading} | roll start at edge tooth: driven gear pre-rotated "
            f"{start_offset_rad:+.8f} rad (middle teeth = evaluation teeth)"
        )
    return build_implicit_pair_deck(
        part1,
        part2,
        kin=kin,
        contact_gap_mm=gap,
        contact_pairs=pairs,
        element_type=element_type,
        rigid_gears=rigid_gears,
        driven_gear=driven_gear,
        slave_gear=slave_gear,
        heading=heading,
    )


# ----------------------------------------------------------------------------------------------
# position series — one INP per Wälzstellung (default mode, user decision 2026-07-06)
# ----------------------------------------------------------------------------------------------
def build_position_series(
    stage: GearStage,
    *,
    gear1_material: Material,
    gear2_material: Material,
    torque_gear2_nmm: float,
    face_layers: int = 6,
    face_width_mm: tuple[float, float] | None = None,
    axial_offset_mm: tuple[float, float] = (0.0, 0.0),
    roll_pitches: float = 3.0,
    n_roll_positions: int = 30,
    hold: int = 2,
    settle: int = 6,
    stabilize: float = 2.0e-4,
    phase_rad: float = 0.0,
    align_contact: bool = True,
    start_at_edge: bool = True,
    rotation_sense: str = "cw",
    contact_gap_mm: float | None = None,
    element_type: str = "C3D8R",
    rigid_gears: frozenset[int] = frozenset(),
    tip_relief: tuple[tuple[float, float | None], tuple[float, float | None]] = (
        (0.0, None),
        (0.0, None),
    ),
    driven_gear: int = 2,
    slave_gear: int = 2,
    refine_root: int = 1,
    refine_flank: int = 1,
    fillet_gear1: object | None = None,
    fillet_gear2: object | None = None,
    fasten_bore: bool = True,
    fasten_cuts: bool = True,
    fasten_bottom: bool = False,
    fasten_top: bool = False,
) -> list[tuple[str, str]]:
    """One independent static INP per Wälzstellung + shared mesh include + manifest + runners.

    Rationale (user decision 2026-07-06): the model is hyperelastic (Marlow) + frictionless,
    hence PATH-INDEPENDENT — each position's equilibrium does not depend on the roll history,
    so a series of independent static solves yields the same stresses as the quasi-static
    single-file sweep while being robust (a non-convergence costs one position, not the run)
    and trivially parallelisable.

    Layout: ``pair_common.inp`` carries the two ``*PART`` blocks + material cards ONCE (baked
    at the closed, centered configuration); every ``pos_NNN.inp`` is small — it ``*INCLUDE``\\ s
    the common file and positions the pair via ``*INSTANCE`` rotation lines (driven gear at
    its Wälzstellung, the other kinematically coupled), locks the driven gear in ALL DOFs,
    and SMOOTH-STEP-ramps the torque 0→full over ``settle`` increments + ``hold`` increments
    at full torque; the measurement frame is the step end (``*TIME POINTS, NAME=MEASURE``).
    ``manifest.json`` records angles/torque/files for the postprocessing; ``run_all.bat`` /
    ``run_all.sh`` run the jobs sequentially (edit for parallel queues).
    """
    import json

    roll_sign = 1.0 if rotation_sense != "ccw" else -1.0
    roll_angle_rad = roll_sign * roll_pitches * 2.0 * math.pi / stage.teeth[driven_gear - 1]
    pair = assemble_centered_pair(
        stage,
        gear1_material=gear1_material,
        gear2_material=gear2_material,
        face_layers=face_layers,
        face_width_mm=face_width_mm,
        axial_offset_mm=axial_offset_mm,
        phase_rad=phase_rad,
        align_contact=align_contact,
        contact_gap_mm=contact_gap_mm,
        roll_angle_rad=roll_angle_rad,
        start_at_edge=start_at_edge,
        driven_gear=driven_gear,
        slave_gear=slave_gear,
        roll_sign=roll_sign,
        rigid_gears=rigid_gears,
        tip_relief=tip_relief,
        refine_root=refine_root,
        refine_flank=refine_flank,
        fillet_gear1=fillet_gear1,
        fillet_gear2=fillet_gear2,
        fasten_bore=fasten_bore,
        fasten_cuts=fasten_cuts,
        fasten_bottom=fasten_bottom,
        fasten_top=fasten_top,
    )
    if slave_gear in rigid_gears:
        raise ValueError("the contact slave must stay deformable (rigid side is the master)")
    part1, part2 = pair.part1, pair.part2
    z = pair.z
    torque_gear = 3 - driven_gear
    torque_nmm = torque_gear2_nmm * z[torque_gear] / z[2]
    total_inc = settle + hold
    dt = 1.0 / total_inc
    ramp_end = settle * dt
    parts = {1: part1, 2: part2}

    def fastening(part: GearPart) -> str:
        g = part.gear
        if g in rigid_gears:
            return f"*RIGID BODY, REF NODE={g}, ELSET=Rad_Vz_{g}.ALL_ELEMENTS_Part_Rad_Vz_{g}"
        return f"*RIGID BODY, REF NODE={g}, TIE NSET=Fesselung_Rad{g}"

    def rot_node(part: GearPart) -> str:
        cx, cy = part.center_xy
        return f"{part.gear}, {cx:.6f}, {cy:.6f}, {part.z_mid_mm:.6f}"

    def gear_comment(part: GearPart) -> str:
        role = "position-locked" if part.gear == driven_gear else "torque (AMP-TORQUE)"
        rigid = ", RIGID (ideally stiff)" if part.gear in rigid_gears else ""
        cx, cy = part.center_xy
        return (
            f"** Gear {part.gear}: z={part.teeth}, b={part.face_width_mm:g} mm, "
            f"material={part.material.name}, axis at ({cx:g}, {cy:g}), "
            f"mid-plane z={part.z_mid_mm:g} mm, {role}{rigid}"
        )

    common = _foldable(
        "\n".join(
            (
                "** pair_common.inp - shared mesh of the position series (closed, centered "
                "configuration; each pos_NNN.inp positions it via *INSTANCE rotations)",
                gear_comment(part1),
                gear_comment(part2),
                f"** contact-aligned: gear 2 rotated {pair.closing_rad:+.8f} rad",
                "**",
                _part_block(part1, element_type),
                "**",
                _part_block(part2, element_type),
                "**",
                "**MATERIALS",
                *(_material_card_for(p) for p in (part1, part2) if p.gear not in rigid_gears),
            )
        )
    )

    def instance_block(part: GearPart, phi_rad: float) -> str:
        cx, cy = part.center_xy
        lines = [f"*INSTANCE, NAME=Rad_Vz_{part.gear}, PART=Part_Rad_Vz_{part.gear}"]
        if abs(phi_rad) > 1e-15:
            lines.append("0., 0., 0.")
            lines.append(
                f"{cx:.6f}, {cy:.6f}, 0., {cx:.6f}, {cy:.6f}, 1., {math.degrees(phi_rad):.9f}"
            )
        lines.append("*END INSTANCE")
        return "\n".join(lines)

    files: list[tuple[str, str]] = [("pair_common.inp", common)]
    manifest_positions = []
    n = max(n_roll_positions, 1)
    for k in range(n):
        s = k / (n - 1) if n > 1 else 0.0
        phi_driven = (-roll_angle_rad / 2.0 if start_at_edge else 0.0) + s * roll_angle_rad
        phi_other = -phi_driven * z[driven_gear] / z[torque_gear]
        phis = {driven_gear: phi_driven, torque_gear: phi_other}
        assembly = "\n".join(
            (
                "*ASSEMBLY, NAME=Assembly",
                instance_block(part1, phis[1]),
                instance_block(part2, phis[2]),
                "*NODE",
                rot_node(part1),
                "*NODE",
                rot_node(part2),
                "*NSET, NSET=Rot_Node_Rad1\n1,",
                "*NSET, NSET=Rot_Node_Rad2\n2,",
                "*NSET, NSET=MASTERKNOTEN_NODE_SET\n1, 2",
                f"*NSET, NSET=Fesselung_Rad1, INSTANCE=Rad_Vz_1\n"
                f"{_wrap(part1.sets.fastening_nodes)}",
                f"*NSET, NSET=Fesselung_Rad2, INSTANCE=Rad_Vz_2\n"
                f"{_wrap(part2.sets.fastening_nodes)}",
                fastening(part1),
                fastening(part2),
                "*SURFACE INTERACTION, NAME=INTPROP-1",
                "1.,",
                "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD",
                *(
                    f"*CONTACT PAIR, INTERACTION=INTPROP-1, TYPE=SURFACE TO SURFACE\n{s1}, {s2}"
                    for s1, s2 in pair.pairs
                ),
                "*END ASSEMBLY",
            )
        )
        step = "\n".join(
            (
                "*STEP, NAME=STEP-1, NLGEOM=YES, INC=100000",
                f"*STATIC, STABILIZE={stabilize:.4g}, ALLSDTOL=0.0, CONTINUE=NO\n"
                f"{dt:.8g}, 1.0, 1e-08, {dt:.8g}",
                "*RESTART, WRITE, FREQUENCY=0",
                _time_points_block("MEASURE", [1.0]),
                f"*OUTPUT, FIELD, NUMBER INTERVAL={total_inc}, TIMEMARKS=NO",
                "*NODE OUTPUT\nU,",
                "*OUTPUT, FIELD, TIME POINTS=MEASURE",
                *_measurement_output_lines(parts, rigid_gears),
                f"*BOUNDARY\nRot_Node_Rad{driven_gear}, 1, 6",
                f"*BOUNDARY\nRot_Node_Rad{torque_gear}, 1, 5",
                f"*CLOAD, AMPLITUDE=AMP-TORQUE\nRot_Node_Rad{torque_gear}, 6, {torque_nmm:.8g}",
                "*END STEP",
            )
        )
        deck = _foldable(
            "\n".join(
                (
                    f"*HEADING\nposition {k + 1}/{n} of the rolling series | "
                    f"phi_driven={phi_driven:+.8f} rad (gear {driven_gear}) | "
                    f"torque {torque_nmm:.6g} N·mm SMOOTH-STEP 0->full over t=[0,{ramp_end:.4g}]"
                    f", measure at t=1.0",
                    "*INCLUDE, INPUT=pair_common.inp",
                    "**",
                    assembly,
                    "**",
                    _amplitude_block("AMP-TORQUE", [(0.0, 0.0), (ramp_end, 1.0), (1.0, 1.0)]),
                    "**",
                    step,
                )
            )
        )
        name = f"pos_{k + 1:03d}.inp"
        files.append((name, deck))
        manifest_positions.append(
            {
                "index": k + 1,
                "file": name,
                "phi_driven_rad": round(phi_driven, 10),
                "phi_other_rad": round(phi_other, 10),
                "measure_time": 1.0,
            }
        )

    manifest = {
        "mode": "position_series",
        "n_positions": n,
        "roll_pitches": roll_pitches,
        "roll_angle_rad": round(roll_angle_rad, 10),
        "start_at_edge": start_at_edge,
        "driven_gear": driven_gear,
        "torque_gear": torque_gear,
        "torque_nmm": round(torque_nmm, 6),
        "torque_gear2_nmm": torque_gear2_nmm,
        "base_torque_fraction": 0.0,
        "closing_rad": round(pair.closing_rad, 10),
        "gears": {
            str(g): {
                "z": parts[g].teeth,
                "b_mm": parts[g].face_width_mm,
                "material": parts[g].material.name,
                "rigid": g in rigid_gears,
            }
            for g in (1, 2)
        },
        "positions": manifest_positions,
    }
    files.append(("manifest.json", json.dumps(manifest, indent=1)))
    bat = "\r\n".join(
        ["@echo off", "rem run all rolling positions sequentially (edit for parallel queues)"]
        + [
            f"call abaqus job=pos_{k + 1:03d} input=pos_{k + 1:03d}.inp interactive"
            for k in range(n)
        ]
        + [""]
    )
    sh = "\n".join(
        ["#!/bin/sh", "# run all rolling positions sequentially (edit for parallel queues)"]
        + [f"abaqus job=pos_{k + 1:03d} input=pos_{k + 1:03d}.inp interactive" for k in range(n)]
        + [""]
    )
    files.append(("run_all.bat", bat))
    files.append(("run_all.sh", sh))
    return files
