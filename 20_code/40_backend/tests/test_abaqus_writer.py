"""
@module: tests.test_abaqus_writer
@context: Domain-layer tests — FE rolling model, the Abaqus `.inp` generator.
@role: The structured mesh + tagged surfaces become a valid keyword deck — part with
       nodes / C3D8 / Fesselung set / flank surfaces / solid section, an assembly with a
       master node and a rigid body, the material, and a quasi-static step — round-trips
       through the deck parser with the mesh counts intact.
"""

from app.io.inp import parse_inp
from app.io.ste import Pair
from app.services.geometry.gear import GearStage, ToolReferenceProfile
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.abaqus_writer import ElasticMaterial, build_gear_deck
from app.services.model.mapped_mesher import mesh_sector_mapped_2d, mesh_sector_mapped_3d
from app.services.model.mesh_sets import tag_sector_surfaces


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
    common = dict(n_teeth=n_teeth, n_segments=n_seg, height_elements=10, root_elements=10)
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
        b.parameter("NAME") for b in surfaces if str(b.parameter("NAME")).startswith("FLANK")
    }
    assert flank_names == {f"FLANK_T{t}_{s}" for t in range(2) for s in ("L", "R")}
    rigid = next(b for b in parsed.blocks if b.keyword == "RIGID BODY")
    assert rigid.parameter("TIE NSET") == "WHEEL-1.FESSELUNG"
    # the master node is fully fixed except the driven rotation DOF 6
    boundaries = [b.data for b in parsed.blocks if b.keyword == "BOUNDARY"]
    assert any("MASTER, 1, 5" in d for d in boundaries)
    assert any("MASTER, 6, 6, -0.2417" in d for d in boundaries)
