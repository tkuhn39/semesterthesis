"""
@module: tests.test_implicit_deck
@context: Domain-layer tests — FE rolling model, the reference-faithful implicit deck.
@role: A meshed gear pair becomes a WoBe-892 implicit deck: Part_Rad_Vz_{g} parts with
       per-tooth/flank G{g}T{nnn}F{f} sets + TOOTH surfaces, bore Fesselung rigid-tied to a
       rotation node at the gear's mid-plane, frictionless hard contact as meshing flank pairs
       (plastic side = slave), Marlow plastic + elastic steel, and one static step with
       staircase angle + torque. Gear numbering follows the stage input order (ADR-021):
       gear 1 = pinion (steel), gear 2 = wheel (plastic) — the FVA reference deck numbers
       the other way around.
"""

import functools
import math

from app.io.inp import parse_inp
from app.io.ste import Pair
from app.services.geometry.gear import GearStage, ToolReferenceProfile
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.implicit_deck import (
    RollKinematics,
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
    part_pinion = build_gear_part(
        pinion,
        gear=1,
        material=LinearElastic("STEEL", 210000.0, 0.3),
        face_width_mm=17.0,
        face_layers=2,
        rot_rad=math.pi / 2.0 + math.pi / pinion.z,
        dx=a,
        axial_offset_mm=1.0,
    )
    part_wheel = build_gear_part(
        wheel,
        gear=2,
        material=MarlowUniaxial("PA_kstE"),
        face_width_mm=15.0,
        face_layers=2,
        rot_rad=-math.pi / 2.0,
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
    assert n1[0] == 1 and math.isclose(n1[1], a) and math.isclose(n1[3], 1.0)  # offset 1 mm
    assert n2[0] == 2 and n2[1] == 0.0 and n2[3] == 0.0
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
    """The GearStage convenience wrapper produces a complete, parseable deck: STE-order
    numbering, per-gear face widths, mid-plane rotation nodes, wheel-torque conversion."""
    deck = build_implicit_pair_from_stage(
        _stage(),
        pinion_material=LinearElastic("STEEL", 210000.0, 0.3),
        wheel_material=MarlowUniaxial("PA_kstE"),
        wheel_torque_nmm=7846.0,
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
    # wheel torque 7846 N·mm → applied pinion torque 7846·24/60 at Rot_Node_Rad1
    cload = next(b for b in parsed.blocks if b.keyword == "CLOAD")
    node, dof, value = (v.strip() for v in cload.data.strip().split(","))
    assert node == "Rot_Node_Rad1" and dof == "6"
    assert math.isclose(float(value), 7846.0 * 24 / 60, rel_tol=1e-9)


def test_steel_shell_mode_makes_the_steel_pinion_rigid() -> None:
    """Mixed-pairing material rule: the steel pinion (gear 1) becomes an ideally stiff rigid
    body (whole element set about its rotation node) instead of the bore-only Fesselung tie;
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
