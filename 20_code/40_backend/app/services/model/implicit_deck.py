"""
@module: app.services.model.implicit_deck
@context: Domain layer — FE rolling model, the reference-faithful implicit Abaqus deck
          (reproduces ``32_Abaqus/implicit/kst-E_8_DY2-0_WS30_ohne_Radkoerper.inp``).
@role: Assemble two meshed gear sectors into the WoBe-892 implicit rolling deck so the frozen
       FVA postprocessing runs unmodified: two ``Part_Rad_Vz_{g}`` parts with per-tooth/flank
       ``G{g}T{nnn}F{f}`` sets + ``TOOTH-{g}-{nnn}F{f}`` surfaces, each bore (``Fesselung_Rad{g}``)
       rigid-tied to a rotation node, frictionless hard contact as explicit meshing flank pairs, and
       ONE quasi-static step driving gear 1 through a staircase angle while gear 2 carries the
       resisting torque. Pure text (the caller persists via ``app.storage``). The plastic gear is
       the contact slave; the steel gear is deformable (not rigid). Spur gears, swept along +z.
"""

import math
from dataclasses import dataclass, replace

import numpy as np
from numpy.typing import NDArray

from app.services.geometry.gear import GearStage
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.mapped_mesher import mesh_sector_mapped_2d
from app.services.model.materials_card import Material, material_card
from app.services.model.mesh3d import Mesh3D, extrude_to_hex
from app.services.model.mesh_sets import GearReferenceSets, tag_gear_reference

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]
AmpTable = list[tuple[float, float]]  # (time, value) rows of an *AMPLITUDE table


# ----------------------------------------------------------------------------------------------
# gear part (a meshed, positioned sector + its reference sets + material)
# ----------------------------------------------------------------------------------------------
@dataclass
class GearPart:
    """One meshed gear sector positioned in the assembly, with its reference sets and material."""

    gear: int  # 1 (plastic, driven) or 2 (steel, loaded)
    mesh: Mesh3D  # nodes already in absolute assembly coordinates
    sets: GearReferenceSets
    material: Material


def _transform(nodes: Array, *, rot_rad: float, dx: float, dy: float) -> Array:
    """Rotate node (x, y) CCW about z by ``rot_rad`` then translate by (dx, dy); z unchanged."""
    c, s = math.cos(rot_rad), math.sin(rot_rad)
    x, y, z = nodes[:, 0], nodes[:, 1], nodes[:, 2]
    return np.column_stack([c * x - s * y + dx, s * x + c * y + dy, z])


def build_gear_part(
    profile: ToothProfile,
    *,
    gear: int,
    material: Material,
    n_teeth: int,
    face_width_mm: float,
    face_layers: int,
    rot_rad: float,
    dx: float = 0.0,
    dy: float = 0.0,
    n_segments: int = 1,
    **mesh_kw: int,
) -> GearPart:
    """Mesh one gear sector, tag its reference sets, and position it in the assembly.

    One 2-D section is meshed once and both extruded (``extrude_to_hex``) and tagged
    (``tag_gear_reference``) from it, so the node/hex ids in the sets match the part exactly.
    """
    section, quality = mesh_sector_mapped_2d(
        profile, n_teeth=n_teeth, n_segments=n_segments, **mesh_kw
    )
    mesh = extrude_to_hex(section, quality, width=face_width_mm, layers=face_layers)
    nodes = _transform(mesh.nodes, rot_rad=rot_rad, dx=dx, dy=dy)
    mesh = Mesh3D(nodes, mesh.hexes, quality=mesh.quality)
    sets = tag_gear_reference(
        section,
        profile=profile,
        gear=gear,
        n_teeth=n_teeth,
        n_segments=n_segments,
        layers=face_layers,
    )
    return GearPart(gear=gear, mesh=mesh, sets=sets, material=material)


# ----------------------------------------------------------------------------------------------
# kinematics + staircase amplitudes
# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class RollKinematics:
    """The single-step rolling load case — every value a parameter (WoBe-892 §3.3.1)."""

    center_distance_mm: float
    wheel_torque_nmm: float  # resisting torque on gear 2 (steel), DOF6
    roll_angle_rad: float  # total rotation of gear 1 over the roll (covers A–E + pre/post margins)
    n_roll_positions: int = 30  # Wälzstellungen captured over the roll
    sub_increments: int = 3  # solver sub-steps held per Wälzstellung (reference uses 3)
    settle_positions: int = 6  # leading flat (angle 0) positions while the torque ramps in
    stabilize: float = 2.0e-4  # *STATIC, STABILIZE (contact-driven rigid-body damping)

    @property
    def total_increments(self) -> int:
        return (self.settle_positions + self.n_roll_positions) * self.sub_increments


def _staircase_pairs(kin: RollKinematics) -> tuple[AmpTable, AmpTable]:
    """Return the (time, value) tables for AMP-ANGLE (0→1 staircase) and AMP-TORQUE (0→1 ramp-hold).

    Time is normalised to [0, 1] at ``total_increments`` equal steps. AMP-ANGLE holds the angle
    flat through the settle phase, then steps up once per Wälzstellung (held ``sub_increments``
    increments each). AMP-TORQUE ramps linearly to 1 over the settle phase, then holds.
    """
    settle_inc = kin.settle_positions * kin.sub_increments
    total = kin.total_increments
    angle: list[tuple[float, float]] = []
    torque: list[tuple[float, float]] = []
    for j in range(total + 1):
        t = j / total
        if j <= settle_inc:
            angle.append((t, 0.0))
            torque.append((t, min(1.0, j / max(settle_inc, 1))))
        else:
            position = (j - settle_inc - 1) // kin.sub_increments + 1
            angle.append((t, min(1.0, position / kin.n_roll_positions)))
            torque.append((t, 1.0))
    return angle, torque


# ----------------------------------------------------------------------------------------------
# keyword block helpers
# ----------------------------------------------------------------------------------------------
def _wrap(ids: list[int] | IntArray, per_line: int = 16) -> str:
    vals = [int(v) for v in ids]
    rows = [vals[i : i + per_line] for i in range(0, len(vals), per_line)]
    return "\n".join(", ".join(str(v) for v in row) for row in rows)


def _amplitude_block(name: str, pairs: list[tuple[float, float]], per_line: int = 4) -> str:
    flat = [f"{t:.9f}, {v:.9f}" for t, v in pairs]
    rows = [flat[i : i + per_line] for i in range(0, len(flat), per_line)]
    body = "\n".join(", ".join(r) for r in rows)
    return f"*AMPLITUDE, NAME={name}\n{body}"


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
    part1: GearPart, part2: GearPart, *, max_gap_mm: float
) -> list[tuple[str, str]]:
    """Pair each gear-1 flank with the nearest gear-2 flank within ``max_gap_mm`` (plastic = slave).

    Geometry-driven so it adapts to the assembly phase: only flanks that face each other across the
    mesh (near the line of centres) fall within the gap and become explicit contact pairs.
    """
    c1, c2 = _flank_centroids(part1), _flank_centroids(part2)
    pairs: list[tuple[str, str]] = []
    for (t1, f1), p1 in sorted(c1.items()):
        best: tuple[float, tuple[int, int]] | None = None
        for (t2, f2), p2 in c2.items():
            d = float(np.linalg.norm(p1 - p2))
            if best is None or d < best[0]:
                best = (d, (t2, f2))
        if best is not None and best[0] <= max_gap_mm:
            t2, f2 = best[1]
            s1 = f"Rad_Vz_{part1.gear}.TOOTH-{part1.gear}-{t1:03d}F{f1}"
            s2 = f"Rad_Vz_{part2.gear}.TOOTH-{part2.gear}-{t2:03d}F{f2}"
            pairs.append((s1, s2))
    return pairs


def build_implicit_pair_deck(
    part1: GearPart,
    part2: GearPart,
    *,
    kin: RollKinematics,
    contact_gap_mm: float | None = None,
    element_type: str = "C3D8R",
    heading: str = "FE rolling model (implicit, ohne Radkoerper) - generated",
) -> str:
    """Build the full reference-faithful implicit deck for a meshed gear pair.

    ``part1`` is the plastic, driven gear (rotation node Rot_Node_Rad1 at the origin); ``part2``
    the steel gear carrying the resisting torque (Rot_Node_Rad2 at the centre distance). Contact is
    frictionless hard, as explicit meshing flank pairs (gear-1 flank = slave). One static step
    drives gear 1 through ``kin.roll_angle_rad`` as a staircase while gear 2 holds the torque.
    ``element_type`` defaults to C3D8R (the reference choice). Data lines are tab-indented so the
    long mesh blocks fold in an editor.
    """
    gap = 2.0 if contact_gap_mm is None else contact_gap_mm  # mm; ~one module, caller-tunable
    a = kin.center_distance_mm
    angle_pairs, torque_pairs = _staircase_pairs(kin)
    pairs = _meshing_contact_pairs(part1, part2, max_gap_mm=gap)

    assembly_nodes = "\n".join(
        (
            "*NODE",
            "1, 0., 0., 0.",
            "*NODE",
            f"2, {a:.6f}, 0., 0.",
            "*NSET, NSET=Rot_Node_Rad1\n1,",
            "*NSET, NSET=Rot_Node_Rad2\n2,",
            "*NSET, NSET=MASTERKNOTEN_NODE_SET\n1, 2",
            f"*NSET, NSET=Fesselung_Rad1, INSTANCE=Rad_Vz_1\n{_wrap(part1.sets.bore_nodes)}",
            f"*NSET, NSET=Fesselung_Rad2, INSTANCE=Rad_Vz_2\n{_wrap(part2.sets.bore_nodes)}",
            "*RIGID BODY, REF NODE=1, TIE NSET=Fesselung_Rad1",
            "*RIGID BODY, REF NODE=2, TIE NSET=Fesselung_Rad2",
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
    step = "\n".join(
        (
            "*STEP, NAME=STEP-1, NLGEOM=YES, INC=100000",
            f"*STATIC, STABILIZE={kin.stabilize:.4g}\n{dt:.8g}, 1.0, 1e-08, {dt:.8g}",
            f"*OUTPUT, FIELD, NUMBER INTERVAL={kin.total_increments}",
            "*ELEMENT OUTPUT, directions=YES\nE, MISESMAX, MISESONLY, NE, PRESSONLY, S",
            "*NODE OUTPUT\nCF, RF, U",
            "*CONTACT OUTPUT\nCFORCE, CSTRESS, CDISP",
            "*BOUNDARY\nRot_Node_Rad1, 1, 5",
            "*BOUNDARY\nRot_Node_Rad2, 1, 5",
            f"*BOUNDARY, AMPLITUDE=AMP-ANGLE\nRot_Node_Rad1, 6, 6, {kin.roll_angle_rad:.8g}",
            f"*CLOAD, AMPLITUDE=AMP-TORQUE\nRot_Node_Rad2, 6, {kin.wheel_torque_nmm:.8g}",
            "*END STEP",
        )
    )
    return _foldable(
        "\n".join(
            (
                f"*HEADING\n{heading}",
                "**",
                _part_block(part1, element_type),
                "**",
                _part_block(part2, element_type),
                "**",
                assembly,
                "**",
                "**MATERIALS",
                _material_card_for(part1),
                _material_card_for(part2),
                "**",
                _amplitude_block("AMP-ANGLE", angle_pairs),
                _amplitude_block("AMP-TORQUE", torque_pairs),
                "**",
                step,
            )
        )
    )


def build_implicit_pair_from_stage(
    stage: GearStage,
    *,
    plastic_material: Material,
    steel_material: Material,
    wheel_torque_nmm: float,
    n_teeth: int = 4,
    face_layers: int = 6,
    n_segments: int = 1,
    face_width_mm: float | None = None,
    roll_pitches: float = 2.0,
    n_roll_positions: int = 30,
    settle_positions: int = 6,
    sub_increments: int = 3,
    stabilize: float = 2.0e-4,
    phase_rad: float = 0.0,
    contact_gap_mm: float | None = None,
    element_type: str = "C3D8R",
    heading: str = "FE rolling model (implicit, ohne Radkoerper) - generated from GearStage",
    **mesh_kw: int,
) -> str:
    """One-call build: a ``GearStage`` → meshed, positioned pair → reference-faithful implicit deck.

    Gear 1 (plastic, driven) sits at the origin facing +x; gear 2 (steel) at the working centre
    distance facing −x, offset half a pitch so a gap meshes gear 1's tooth (``phase_rad`` adds a
    tunable mounting offset). The default roll sweeps ``roll_pitches`` angular pitches of gear 1
    (covering A–E plus pre-/post-engagement). The contact gap defaults to 1.5·mₙ. Extra ``mesh_kw``
    (height_elements, root_elements, …) pass straight through to the mapped mesher.
    """
    p1 = ToothProfile.from_stage(stage, 0)
    p2 = ToothProfile.from_stage(stage, 1)
    a = stage.working_center_distance_mm
    if face_width_mm is None:
        if stage.face_width_mm is None:
            raise ValueError("face width needed: pass face_width_mm or a stage carrying it")
        face_width_mm = min(abs(stage.face_width_mm[0]), abs(stage.face_width_mm[1]))
    part1 = build_gear_part(
        p1,
        gear=1,
        material=plastic_material,
        n_teeth=n_teeth,
        face_width_mm=face_width_mm,
        face_layers=face_layers,
        rot_rad=-math.pi / 2.0,
        n_segments=n_segments,
        **mesh_kw,
    )
    part2 = build_gear_part(
        p2,
        gear=2,
        material=steel_material,
        n_teeth=n_teeth,
        face_width_mm=face_width_mm,
        face_layers=face_layers,
        rot_rad=math.pi / 2.0 + math.pi / p2.z + phase_rad,
        dx=a,
        n_segments=n_segments,
        **mesh_kw,
    )
    kin = RollKinematics(
        center_distance_mm=a,
        wheel_torque_nmm=wheel_torque_nmm,
        roll_angle_rad=roll_pitches * 2.0 * math.pi / p1.z,
        n_roll_positions=n_roll_positions,
        settle_positions=settle_positions,
        sub_increments=sub_increments,
        stabilize=stabilize,
    )
    gap = contact_gap_mm if contact_gap_mm is not None else 1.5 * stage.normal_module_mm
    return build_implicit_pair_deck(
        part1, part2, kin=kin, contact_gap_mm=gap, element_type=element_type, heading=heading
    )
