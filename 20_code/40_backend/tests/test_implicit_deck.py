"""
@module: tests.test_implicit_deck
@context: Domain-layer tests — FE rolling model, the reference-faithful implicit deck.
@role: A meshed gear pair becomes a WoBe-892 implicit deck: Part_Rad_Vz_{g} parts with
       per-tooth/flank G{g}T{nnn}F{f} sets + TOOTH surfaces, Fesselung (bore + radial cut
       faces, reference parity) rigid-tied to a
       rotation node at the gear's mid-plane, frictionless hard contact as meshing flank pairs
       (plastic side = slave), Marlow plastic + elastic steel, and one static step with
       staircase angle + torque. Gear numbering follows the stage input order (ADR-021):
       gear 1 = pinion (steel), gear 2 = wheel (plastic) — the FVA reference deck numbers
       the other way around.
"""

import functools
import math

import numpy as np

from app.io.inp import parse_inp
from app.io.ste import Pair
from app.services.geometry.gear import GearStage, ToolReferenceProfile
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.implicit_deck import (
    GearPart,
    RollKinematics,
    _closing_rotation_rad,
    _rotate_part_about_own_axis,
    build_gear_part,
    build_implicit_pair_deck,
    build_implicit_pair_from_stage,
)
from app.services.model.materials_card import LinearElastic, MarlowUniaxial


def _stage() -> GearStage:
    tool = ToolReferenceProfile(addendum_factor=1.25, tip_radius_factor=0.38)
    return GearStage.from_parameters(
        normal_module_mm=2.0,
        teeth=Pair(24, 60),
        profile_shift=Pair(0.3, 0.1),
        face_width_mm=Pair(20.0, 18.0),
        tool=Pair(tool, tool),
    )


def _profiles() -> tuple[ToothProfile, ToothProfile]:
    stage = _stage()
    return ToothProfile.from_stage(stage, 0), ToothProfile.from_stage(stage, 1)


@functools.cache
def _deck(rigid_gear1: bool = False) -> str:
    pinion, wheel = _profiles()
    a = pinion.mn * (pinion.z + wheel.z) / 2.0
    # rig layout (ADR-021 amendment): gear 1 at the origin (left), gear 2 at (a, 0) (right)
    part_pinion = build_gear_part(
        pinion,
        gear=1,
        material=LinearElastic("STEEL", 210000.0, 0.3),
        face_width_mm=17.0,
        face_layers=2,
        rot_rad=-math.pi / 2.0,
        axial_offset_mm=1.0,
    )
    part_wheel = build_gear_part(
        wheel,
        gear=2,
        material=MarlowUniaxial("PA_kstE"),
        face_width_mm=15.0,
        face_layers=2,
        rot_rad=math.pi / 2.0 + math.pi / wheel.z,
        dx=a,
    )
    kin = RollKinematics(
        center_distance_mm=a,
        torque_nmm=7846.0,
        roll_angle_rad=0.25,
        n_roll_positions=10,
        settle_positions=3,
    )
    return build_implicit_pair_deck(
        part_pinion,
        part_wheel,
        kin=kin,
        contact_gap_mm=6.0,
        rigid_gears=frozenset({1}) if rigid_gear1 else frozenset(),
        driven_gear=2,
        slave_gear=2,
    )


def test_deck_has_reference_parts_sets_and_surfaces() -> None:
    parsed = parse_inp(_deck())
    parts = {b.parameter("NAME") for b in parsed.blocks if b.keyword == "PART"}
    assert parts == {"Part_Rad_Vz_1", "Part_Rad_Vz_2"}
    surf_names = {b.parameter("NAME") for b in parsed.blocks if b.keyword == "SURFACE"}
    nset_names = {b.parameter("NSET") for b in parsed.blocks if b.keyword == "NSET"}
    elset_names = {b.parameter("ELSET") for b in parsed.blocks if b.keyword == "ELSET"}
    # reference naming the postprocessing builds on: G{g}T{nnn}F{f}, TOOTH-{g}-{nnn}F{f}
    assert "TOOTH-1-001F1" in surf_names and "TOOTH-2-001F2" in surf_names
    assert "G1T001F1_NODESET" in nset_names and "G2T003F2_NODESET" in nset_names
    assert "G1T001F1_ELEMENTSET" in elset_names
    assert {
        "Rot_Node_Rad1",
        "Rot_Node_Rad2",
        "MASTERKNOTEN_NODE_SET",
        "Fesselung_Rad1",
        "Fesselung_Rad2",
    } <= nset_names


def test_deck_numbering_follows_stage_order() -> None:
    """ADR-021: gear 1 = pinion (steel, torque), gear 2 = wheel (plastic, angle-driven)."""
    deck = _deck()
    assert "Gear 1: z=24" in deck and "material=STEEL" in deck
    assert "Gear 2: z=60" in deck and "material=PA_kstE" in deck
    parsed = parse_inp(deck)
    # the wheel (gear 2) is angle-driven, the pinion (gear 1) carries the torque
    boundaries = "\n".join(b.data for b in parsed.blocks if b.keyword == "BOUNDARY")
    assert "Rot_Node_Rad2, 6, 6" in boundaries
    cload = next(b for b in parsed.blocks if b.keyword == "CLOAD")
    assert cload.data.strip().startswith("Rot_Node_Rad1, 6")


def test_deck_fastening_contact_and_step() -> None:
    parsed = parse_inp(_deck())
    rigids = [b.header for b in parsed.blocks if b.keyword == "RIGID BODY"]
    assert any("REF NODE=1" in r and "Fesselung_Rad1" in r for r in rigids)
    assert any("REF NODE=2" in r and "Fesselung_Rad2" in r for r in rigids)
    # frictionless hard contact, plastic wheel (Rad_Vz_2) listed first (slave)
    pairs = [b for b in parsed.blocks if b.keyword == "CONTACT PAIR"]
    assert len(pairs) >= 1
    assert all(b.data.strip().startswith("Rad_Vz_2.") for b in pairs)
    assert any(b.keyword == "SURFACE BEHAVIOR" for b in parsed.blocks)
    # exactly one static step
    steps = [b for b in parsed.blocks if b.keyword == "STEP"]
    assert len(steps) == 1


def test_rotation_nodes_sit_at_the_gear_mid_planes() -> None:
    """Both gears extrude symmetric about their mid-plane (z = ±b/2 + axial offset, reference
    parity) and each rotation node sits at that mid-plane — not on a side face."""
    deck = _deck()
    lines = deck.splitlines()
    # assembly rotation nodes come right after the *ASSEMBLY instances
    start = lines.index("*ASSEMBLY, NAME=Assembly")
    rot = [lines[i + 1].strip() for i in range(start, len(lines)) if lines[i].startswith("*NODE")][
        :2
    ]
    n1 = [float(v) for v in rot[0].split(",")]
    n2 = [float(v) for v in rot[1].split(",")]
    a = 2.0 * (24 + 60) / 2.0
    # rig layout: gear 1 on the axis at the ORIGIN (left), gear 2 at the centre distance
    assert n1[0] == 1 and n1[1] == 0.0 and math.isclose(n1[3], 1.0)  # offset 1 mm
    assert n2[0] == 2 and math.isclose(n2[1], a) and n2[3] == 0.0
    # part node z-ranges: pinion b=17 shifted +1 → [-7.5, 9.5]; wheel b=15 centred → [-7.5, 7.5]
    parsed = parse_inp(deck)
    for part, lo, hi in (("Part_Rad_Vz_1", -7.5, 9.5), ("Part_Rad_Vz_2", -7.5, 7.5)):
        block = deck.split(f"*PART, NAME={part}")[1]
        node_data = block.split("*ELEMENT")[0].split("*NODE")[1]
        zs = [float(ln.split(",")[3]) for ln in node_data.strip().splitlines()]
        assert math.isclose(min(zs), lo, abs_tol=1e-9) and math.isclose(max(zs), hi, abs_tol=1e-9)
    assert parsed.blocks  # parsed above; keep the parse in the test path


def test_deck_materials_and_amplitudes() -> None:
    deck = _deck()
    parsed = parse_inp(deck)
    mats = {b.parameter("NAME") for b in parsed.blocks if b.keyword == "MATERIAL"}
    assert mats == {"MATERIAL-Part_Rad_Vz_1", "MATERIAL-Part_Rad_Vz_2"}
    assert any(b.keyword == "HYPERELASTIC" for b in parsed.blocks)  # plastic Marlow
    assert any(b.keyword == "ELASTIC" for b in parsed.blocks)  # steel
    amps = {b.parameter("NAME") for b in parsed.blocks if b.keyword == "AMPLITUDE"}
    assert amps == {"AMP-ANGLE", "AMP-TORQUE"}
    deck.encode("latin-1")  # the .inp must survive Abaqus' latin-1 reader


def test_one_call_build_from_stage() -> None:
    """The GearStage convenience wrapper produces a complete, parseable deck: slot-order
    numbering with gear 1 at the origin (rig view: left), per-gear face widths, mid-plane
    rotation nodes, and the M₂ torque conversion to the loaded gear."""
    deck = build_implicit_pair_from_stage(
        _stage(),
        gear1_material=LinearElastic("STEEL", 210000.0, 0.3),
        gear2_material=MarlowUniaxial("PA_kstE"),
        torque_gear2_nmm=7846.0,
        face_layers=2,
        axial_offset_mm=(0.0, -1.0),
        n_roll_positions=8,
        settle_positions=2,
    )
    parsed = parse_inp(deck)
    parts = {b.parameter("NAME") for b in parsed.blocks if b.keyword == "PART"}
    assert parts == {"Part_Rad_Vz_1", "Part_Rad_Vz_2"}
    assert len([b for b in parsed.blocks if b.keyword == "STEP"]) == 1
    assert len([b for b in parsed.blocks if b.keyword == "CONTACT PAIR"]) >= 1
    assert "Gear 1: z=24, b=20 mm" in deck and "Gear 2: z=60, b=18 mm" in deck
    # rig layout: gear 1 on the axis at the origin, gear 2 at the working centre distance
    # (a_w ≈ 84.774 — null distance 84 plus the profile-shift widening)
    assert "Gear 1: z=24" in deck and "axis at (0, 0)" in deck.split("Gear 2")[0]
    assert "axis at (84.77" in deck.split("Gear 2: z=60")[1].split("\n")[0]
    # M₂ = 7846 N·mm at gear 2 → applied at the torque gear 1 as 7846·24/60 (Rot_Node_Rad1)
    cload = next(b for b in parsed.blocks if b.keyword == "CLOAD")
    node, dof, value = (v.strip() for v in cload.data.strip().split(","))
    assert node == "Rot_Node_Rad1" and dof == "6"
    assert math.isclose(float(value), 7846.0 * 24 / 60, rel_tol=1e-9)


def test_fesselung_contains_every_node_of_bore_and_cut_planes() -> None:
    """Reference parity (measured 2026-07-04): the Fesselung is the bore surface plus BOTH
    radial cut planes as complete cross-sections — every single node of those faces, from
    the bore to the root circle, over all face-width planes. Cross-checked here with an
    independent coordinate predicate over the whole 3-D mesh."""
    pinion, _ = _profiles()
    layers = 3
    part = build_gear_part(
        pinion,
        gear=1,
        material=LinearElastic("STEEL", 210000.0, 0.3),
        face_width_mm=17.0,
        face_layers=layers,
        rot_rad=0.0,  # unrotated: section coordinates = assembly coordinates
    )
    nodes = part.mesh.nodes
    used = np.unique(part.mesh.hexes)  # skip orphan geometry nodes (e.g. arc centres)
    r = np.hypot(nodes[used, 0], nodes[used, 1])
    ang = np.arctan2(nodes[used, 0], nodes[used, 1])
    tol = 0.02 * pinion.mn
    r_bore = float(r.min())
    half_sector = 6.0 * math.pi / pinion.z  # 4 teeth + 2 shoulder pitches, half of 6 pitches
    on_face = (np.abs(r - r_bore) < tol) | (
        np.abs(np.abs(ang) - half_sector) * np.maximum(r, 1e-6) < tol
    )
    expected = {int(nd) + 1 for nd in used[on_face]}
    assert set(part.sets.fastening_nodes.tolist()) == expected
    # both cut planes reach exactly the root circle (like the reference deck), not further
    fast = nodes[part.sets.fastening_nodes - 1]
    r_fast = np.hypot(fast[:, 0], fast[:, 1])
    assert math.isclose(float(r_fast.max()), pinion.root_diameter_mm / 2.0, rel_tol=1e-3)
    # every face-width plane is present (complete cross-sections, not an edge subset)
    zs = np.unique(np.round(nodes[part.sets.fastening_nodes - 1, 2], 6))
    assert len(zs) == layers + 1


def test_fesselung_flags_follow_the_fva_checkboxes() -> None:
    """The FVA 'Fesselung' checkboxes map to writer flags: oben/unten add the complete axial
    end faces; disabling Bohrung/Schnitt removes those faces."""
    pinion, _ = _profiles()
    layers = 2
    common: dict = {
        "gear": 1,
        "material": LinearElastic("STEEL", 210000.0, 0.3),
        "face_width_mm": 17.0,
        "face_layers": layers,
        "rot_rad": 0.0,
    }
    ends_only = build_gear_part(
        pinion, fasten_bore=False, fasten_cuts=False, fasten_bottom=True, fasten_top=True, **common
    )
    n2d = ends_only.mesh.nodes.shape[0] // (layers + 1)
    ids = set(ends_only.sets.fastening_nodes.tolist())
    # bottom plane = first node plane, top plane = last; both complete
    used = np.unique(ends_only.mesh.hexes)
    bottom = {int(nd) + 1 for nd in used if nd < n2d}
    top = {int(nd) + 1 for nd in used if nd >= layers * n2d}
    assert ids == bottom | top
    reference = build_gear_part(pinion, **common)
    assert bottom - set(reference.sets.fastening_nodes.tolist())  # ends are NOT in the default


def test_contact_alignment_closes_the_backlash() -> None:
    """The closing rotation turns gear 2 from 'floating centred in the gap' (with the full
    allowance backlash split onto both flanks — the gears 'run in the air') into single-flank
    contact with the reference-like ~5–35 µm clearance on the −y flank (the side the
    reference deck touches). Gears cut with a mean tooth-width allowance A_We like kst-E."""
    tool = ToolReferenceProfile(addendum_factor=1.25, tip_radius_factor=0.38)
    stage = GearStage.from_parameters(
        normal_module_mm=2.0,
        teeth=Pair(24, 60),
        profile_shift=Pair(0.3, 0.1),
        face_width_mm=Pair(20.0, 18.0),
        tool=Pair(tool, tool),
        tooth_width_allowance_mm=Pair(-0.10, -0.08),  # thinned teeth → real backlash
    )
    pinion = ToothProfile.from_stage(stage, 0)
    wheel = ToothProfile.from_stage(stage, 1)
    a = stage.working_center_distance_mm
    part1 = build_gear_part(
        pinion,
        gear=1,
        material=LinearElastic("STEEL", 210000.0, 0.3),
        face_width_mm=17.0,
        face_layers=1,
        rot_rad=-math.pi / 2.0,
    )
    part2 = build_gear_part(
        wheel,
        gear=2,
        material=MarlowUniaxial("PA_kstE"),
        face_width_mm=15.0,
        face_layers=1,
        rot_rad=math.pi / 2.0 + math.pi / wheel.z,
        dx=a,
    )

    def min_gap(p1: GearPart, p2: GearPart) -> tuple[float, float]:
        n1, n2 = p1.mesh.nodes, p2.mesh.nodes
        r1 = np.hypot(n1[:, 0], n1[:, 1])
        r2 = np.hypot(n2[:, 0] - a, n2[:, 1])
        t1 = n1[(r1 > pinion.d_Ff / 2.0) & (n1[:, 0] > 0.7 * r1.max())][:, :2]
        t2 = n2[(r2 > wheel.d_Ff / 2.0) & (n2[:, 0] < a - 0.7 * r2.max())][:, :2]
        d = np.hypot(*(t1[:, None, :] - t2[None, :, :]).transpose(2, 0, 1))
        i, j = np.unravel_index(int(np.argmin(d)), d.shape)
        return float(d[i, j]), float(t1[i, 1])

    gap_before, _ = min_gap(part1, part2)
    assert gap_before > 0.06  # half the allowance backlash per flank — 'running in the air'
    delta = _closing_rotation_rad(part1, part2, direction=1.0)
    # ≈ (ΣA_sn/2)/r_w2 − backoff = ((0.10+0.08)/cos20°/2)/60.55 − 0.015/60.55 ≈ 0.0013 rad
    assert 0.0008 < delta < 0.003
    aligned = _rotate_part_about_own_axis(part2, delta)
    gap_after, y_contact = min_gap(part1, aligned)
    assert 0.004 <= gap_after <= 0.035  # reference: ~25 µm single-flank clearance
    assert y_contact < 0.0  # contact on the −y flank like the reference deck


def test_from_stage_documents_the_contact_alignment() -> None:
    deck = build_implicit_pair_from_stage(
        _stage(),
        gear1_material=LinearElastic("STEEL", 210000.0, 0.3),
        gear2_material=MarlowUniaxial("PA_kstE"),
        torque_gear2_nmm=7846.0,
        face_layers=1,
        n_roll_positions=4,
        settle_positions=1,
    )
    assert "contact-aligned: gear 2 rotated" in deck


def test_steel_shell_mode_makes_the_steel_pinion_rigid() -> None:
    """Mixed-pairing material rule: the steel pinion (gear 1) becomes an ideally stiff rigid
    body (whole element set about its rotation node) instead of the Fesselung tie;
    the plastic wheel stays deformable."""
    parsed = parse_inp(_deck(rigid_gear1=True))
    rigids = [b.header for b in parsed.blocks if b.keyword == "RIGID BODY"]
    assert any("REF NODE=2" in r and "TIE NSET=Fesselung_Rad2" in r for r in rigids)
    assert any(
        "REF NODE=1" in r and "ELSET=Rad_Vz_1.ALL_ELEMENTS_Part_Rad_Vz_1" in r for r in rigids
    )
    assert not any("TIE NSET=Fesselung_Rad1" in r for r in rigids)
    # contact pairs and reference sets survive unchanged (postprocessing contract)
    assert len([b for b in parsed.blocks if b.keyword == "CONTACT PAIR"]) >= 1
    nset_names = {b.parameter("NSET") for b in parsed.blocks if b.keyword == "NSET"}
    assert "G1T001F1_NODESET" in nset_names
