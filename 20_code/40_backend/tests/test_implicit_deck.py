"""
@module: tests.test_implicit_deck
@context: Domain-layer tests — FE rolling model, the reference-faithful implicit deck.
@role: A meshed gear pair becomes a WoBe-892 implicit deck the frozen FVA postprocessing can read:
       Part_Rad_Vz_{g} parts with per-tooth/flank G{g}T{nnn}F{f} sets + TOOTH surfaces,
       bore Fesselung rigid-tied to a rotation node, frictionless hard contact as meshing flank
       pairs, Marlow plastic + elastic steel, and one static step with staircase angle + torque.
"""

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
        face_width_mm=Pair(20.0, 20.0),
        tool=Pair(tool, tool),
    )


def _profiles() -> tuple[ToothProfile, ToothProfile]:
    tool = ToolReferenceProfile(addendum_factor=1.25, tip_radius_factor=0.38)
    stage = GearStage.from_parameters(
        normal_module_mm=2.0,
        teeth=Pair(24, 60),
        profile_shift=Pair(0.3, 0.1),
        face_width_mm=Pair(20.0, 20.0),
        tool=Pair(tool, tool),
    )
    return ToothProfile.from_stage(stage, 0), ToothProfile.from_stage(stage, 1)


def _deck(n_teeth: int = 3) -> str:
    p1, p2 = _profiles()
    a = p1.mn * (p1.z + p2.z) / 2.0
    mesh_kw = {
        "height_elements": 6,
        "root_elements": 6,
        "thickness_elements": 3,
        "rim_elements": 3,
        "gap_elements": 3,
    }
    part1 = build_gear_part(
        p1,
        gear=1,
        material=MarlowUniaxial("PA_kstE"),
        n_teeth=n_teeth,
        face_width_mm=15.0,
        face_layers=2,
        rot_rad=-math.pi / 2.0,
        **mesh_kw,
    )
    part2 = build_gear_part(
        p2,
        gear=2,
        material=LinearElastic("STEEL", 210000.0, 0.3),
        n_teeth=n_teeth,
        face_width_mm=15.0,
        face_layers=2,
        rot_rad=math.pi / 2.0 + math.pi / p2.z,
        dx=a,
        **mesh_kw,
    )
    kin = RollKinematics(
        center_distance_mm=a,
        wheel_torque_nmm=7846.0,
        roll_angle_rad=0.25,
        n_roll_positions=10,
        settle_positions=3,
    )
    return build_implicit_pair_deck(part1, part2, kin=kin, contact_gap_mm=6.0)


def test_deck_has_reference_parts_sets_and_surfaces() -> None:
    parsed = parse_inp(_deck())
    parts = {b.parameter("NAME") for b in parsed.blocks if b.keyword == "PART"}
    assert parts == {"Part_Rad_Vz_1", "Part_Rad_Vz_2"}
    surf_names = {b.parameter("NAME") for b in parsed.blocks if b.keyword == "SURFACE"}
    nset_names = {b.parameter("NSET") for b in parsed.blocks if b.keyword == "NSET"}
    elset_names = {b.parameter("ELSET") for b in parsed.blocks if b.keyword == "ELSET"}
    # reference naming the frozen postprocessing builds: G{g}T{nnn}F{f}, TOOTH-{g}-{nnn}F{f}
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


def test_deck_fastening_contact_and_step() -> None:
    parsed = parse_inp(_deck())
    rigids = [b.header for b in parsed.blocks if b.keyword == "RIGID BODY"]
    assert any("REF NODE=1" in r and "Fesselung_Rad1" in r for r in rigids)
    assert any("REF NODE=2" in r and "Fesselung_Rad2" in r for r in rigids)
    # frictionless hard contact, plastic gear (Rad_Vz_1) listed first (slave)
    pairs = [b for b in parsed.blocks if b.keyword == "CONTACT PAIR"]
    assert len(pairs) >= 1
    assert all(b.data.strip().startswith("Rad_Vz_1.") for b in pairs)
    assert any(b.keyword == "SURFACE BEHAVIOR" for b in parsed.blocks)
    # exactly one static step driving the angle and holding the torque
    steps = [b for b in parsed.blocks if b.keyword == "STEP"]
    assert len(steps) == 1
    boundaries = "\n".join(b.data for b in parsed.blocks if b.keyword == "BOUNDARY")
    assert "Rot_Node_Rad1, 6, 6" in boundaries
    cload = next(b for b in parsed.blocks if b.keyword == "CLOAD")
    assert cload.data.strip().startswith("Rot_Node_Rad2, 6")


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
    """The GearStage convenience wrapper produces a complete, parseable reference deck."""
    deck = build_implicit_pair_from_stage(
        _stage(),
        plastic_material=MarlowUniaxial("PA_kstE"),
        steel_material=LinearElastic("STEEL", 210000.0, 0.3),
        wheel_torque_nmm=7846.0,
        n_teeth=3,
        face_layers=2,
        n_roll_positions=8,
        settle_positions=2,
        height_elements=6,
        root_elements=6,
        thickness_elements=3,
        rim_elements=3,
        gap_elements=3,
    )
    parsed = parse_inp(deck)
    parts = {b.parameter("NAME") for b in parsed.blocks if b.keyword == "PART"}
    assert parts == {"Part_Rad_Vz_1", "Part_Rad_Vz_2"}
    assert len([b for b in parsed.blocks if b.keyword == "STEP"]) == 1
    assert len([b for b in parsed.blocks if b.keyword == "CONTACT PAIR"]) >= 1
