"""
@module: tests.test_abaqus_writer
@context: Domain-layer tests — FE rolling model, the Abaqus `.inp` generator.
@role: The structured mesh + tagged surfaces become a valid keyword deck — part with
       nodes / C3D8 / Fesselung set / flank surfaces / solid section, an assembly with a
       master node and a rigid body, the material, and a quasi-static step — round-trips
       through the deck parser with the mesh counts intact.
"""

import pytest

from app.io.inp import parse_inp
from app.io.ste import Pair
from app.services.geometry.gear import GearStage, ToolReferenceProfile
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.abaqus_writer import (
    ElasticMaterial,
    RollingSetup,
    build_gear_deck,
    build_rolling_deck,
)
from app.services.model.mapped_mesher import mesh_sector_mapped_2d, mesh_sector_mapped_3d
from app.services.model.mesh3d import Mesh3D
from app.services.model.mesh_sets import SectorSurfaces, tag_sector_surfaces


def _gear(
    index: int, n_teeth: int, n_seg: int, layers: int, **counts: int
) -> tuple[Mesh3D, SectorSurfaces]:
    common = dict(n_teeth=n_teeth, n_segments=n_seg, **counts)
    section, _ = mesh_sector_mapped_2d(_profile(index), **common)
    mesh = mesh_sector_mapped_3d(_profile(index), face_width_mm=15.0, face_layers=layers, **common)
    surfaces = tag_sector_surfaces(
        section, profile=_profile(index), n_teeth=n_teeth, n_segments=n_seg, layers=layers
    )
    return mesh, surfaces


def _rolling_deck(n_roll_positions: int = 30) -> str:
    wheel, wheel_s = _gear(1, 2, 1, 4, height_elements=8, root_elements=8, thickness_elements=4)
    pinion, pinion_s = _gear(0, 2, 1, 3, height_elements=6, root_elements=4, thickness_elements=3)
    setup = RollingSetup(
        center_distance_mm=52.0,
        wheel_torque_nmm=7846.0,
        roll_span_rad=0.2417,
        n_roll_positions=n_roll_positions,
        penetration_mm=0.01,
    )
    return build_rolling_deck(
        wheel_mesh=wheel,
        wheel_surfaces=wheel_s,
        wheel_material=ElasticMaterial("PA46GF30", 4156.0, 0.4),
        pinion_mesh=pinion,
        pinion_surfaces=pinion_s,
        pinion_material=ElasticMaterial("STEEL", 210000.0, 0.3),
        setup=setup,
    )


def _profile(index: int = 0) -> ToothProfile:
    tool = ToolReferenceProfile(addendum_factor=1.25, tip_radius_factor=0.38)
    stage = GearStage.from_parameters(
        normal_module_mm=2.0,
        teeth=Pair(24, 60),
        profile_shift=Pair(0.3, 0.1),
        face_width_mm=Pair(20.0, 20.0),
        tool=Pair(tool, tool),
    )
    return ToothProfile.from_stage(stage, index)


def _deck(n_teeth: int = 2, n_seg: int = 1, layers: int = 4) -> tuple[str, int, int]:
    common = {"n_teeth": n_teeth, "n_segments": n_seg, "height_elements": 10, "root_elements": 10}
    section, _ = mesh_sector_mapped_2d(_profile(), **common)
    mesh = mesh_sector_mapped_3d(_profile(), face_width_mm=15.0, face_layers=layers, **common)
    surfaces = tag_sector_surfaces(
        section, profile=_profile(), n_teeth=n_teeth, n_segments=n_seg, layers=layers
    )
    material = ElasticMaterial("PA46GF30", 4156.0, 0.4, density_t_per_mm3=1.42e-9)
    deck = build_gear_deck(mesh, surfaces, material=material, rotation_rad=-0.2417, axis_z_mm=7.5)
    return deck, mesh.n_nodes, mesh.n_hexes


def test_deck_round_trips_with_mesh_counts() -> None:
    deck, n_nodes, n_hexes = _deck()
    parsed = parse_inp(deck)
    keywords = [block.keyword for block in parsed.blocks]
    for required in ("HEADING", "PART", "ELEMENT", "ASSEMBLY", "RIGID BODY", "MATERIAL", "STEP"):
        assert required in keywords
    node_block = next(b for b in parsed.blocks if b.keyword == "NODE")
    element_block = next(b for b in parsed.blocks if b.keyword == "ELEMENT")
    assert len(node_block.data.splitlines()) == n_nodes
    assert len(element_block.data.splitlines()) == n_hexes
    assert element_block.parameter("TYPE") == "C3D8"


def test_deck_has_flank_surfaces_and_fastened_master() -> None:
    deck, _, _ = _deck(n_teeth=2)
    parsed = parse_inp(deck)
    surfaces = [b for b in parsed.blocks if b.keyword == "SURFACE"]
    flank_names = {
        b.parameter("NAME") for b in surfaces if str(b.parameter("NAME")).startswith("FLANK_T")
    }
    assert flank_names == {f"FLANK_T{t}_{s}" for t in range(2) for s in ("L", "R")}
    assert any(b.parameter("NAME") == "FLANKS" for b in surfaces)  # combined contact surface
    rigid = next(b for b in parsed.blocks if b.keyword == "RIGID BODY")
    assert rigid.parameter("TIE NSET") == "WHEEL-1.FESSELUNG"
    # the master node is fully fixed except the driven rotation DOF 6
    boundaries = [b.data for b in parsed.blocks if b.keyword == "BOUNDARY"]
    assert any("MASTER, 1, 5" in d for d in boundaries)
    assert any("MASTER, 6, 6, -0.2417" in d for d in boundaries)


def test_rolling_deck_two_gears_contact_and_steps() -> None:
    parsed = parse_inp(_rolling_deck())
    parts = {b.parameter("NAME") for b in parsed.blocks if b.keyword == "PART"}
    assert parts == {"WHEEL", "PINION"}
    steps = [b.parameter("NAME") for b in parsed.blocks if b.keyword == "STEP"]
    assert steps == ["Engage", "Roll"]  # engage + load, then roll
    rigids = [b.header for b in parsed.blocks if b.keyword == "RIGID BODY"]
    assert any("TIE NSET=WHEEL-1.FESSELUNG" in r for r in rigids)  # wheel fastened
    assert any("ELSET=PINION-1.PINION_EL" in r for r in rigids)  # pinion made rigid
    contact = next(b for b in parsed.blocks if b.keyword == "CONTACT PAIR")
    assert contact.data.strip() == "WHEEL-1.FLANKS, PINION-1.FLANKS"  # slave wheel, master pinion


def test_rolling_positions_are_parametric() -> None:
    # the Roll step uses fixed increments dt = 1/n_roll_positions — the Wälzstellungen count
    for n in (15, 30, 60):
        parsed = parse_inp(_rolling_deck(n_roll_positions=n))
        roll = next(b for b in parsed.blocks if b.keyword == "STATIC" and "DIRECT" in b.header)
        dt = float(roll.data.splitlines()[0].split(",")[0])
        assert dt == pytest.approx(1.0 / n, rel=1e-6)


def test_rolling_deck_is_abaqus_encoding_safe() -> None:
    _rolling_deck().encode("latin-1")  # the .inp must survive Abaqus' latin-1 reader
