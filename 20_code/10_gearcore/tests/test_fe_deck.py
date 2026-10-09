"""Position files of the pair, the material card and the orientation file
(``gearcore.fe.deck``)."""

import dataclasses

import pytest

from gearcore.errors import InputRangeError, ParseError
from gearcore.fe import deck as dk
from gearcore.fe.placement import Placement
from gearcore.models.common import Pair

CARD = """** CONVERSE Orientation File for Solver ABAQUS
*DISTRIBUTION TABLE, NAME=DIS_TAB_COORD
 COORD3D, COORD3D
*DISTRIBUTION, NAME=DIS_W, LOCATION=ELEMENT, TABLE=DIS_TAB_COORD
 , 1.0, 0.0, 0.0, 0.0, 1.0, 0.0
 1, -0.5, 0.8, 0, -0.8, -0.5, 0
 2, 0.9, 0.1, 0, 0.1, -0.9, 0
*ORIENTATION, NAME=ORI_W, DEFINITION=COORDINATES
 DIS_W
*SOLID SECTION, ELSET=WHEEL, MATERIAL=PA46_TEST, ORIENTATION=ORI_W
** MatScape Material File for Solver Abaqus
*MATERIAL,\tNAME=PA46_TEST
*ELASTIC,TYPE=ENGINEERING CONSTANTS,DEPENDENCIES=2
5.130426E+003, 5.130428E+003, 3.405050E+003, 0.3175, 0.3230, 0.3230, 1.950872E+003, 1.150232E+003,
1.150231E+003, 23, 0.50000, 0.00000
4.110206E+003, 4.108386E+003, 4.108386E+003, 0.3032, 0.3032, 0.3035, 1.574798E+003, 1.574798E+003,
1.575870E+003, 23, 0.33333, 0.33333
2.282078E+003, 2.280776E+003, 2.280776E+003, 0.2997, 0.2997, 0.3001, 8.763875E+002, 8.763875E+002,
8.771577E+002, 80, 0.33333, 0.33333
*PLASTIC
5.9860E+000,\t0.0000E+000,\t23
9.3695E+001,\t3.6080E-002,\t80
*POTENTIAL,TYPE=HILL,DEPENDENCIES=2
0.8397, 0.8397, 0.5943, 0.6214, 0.5306, 0.5306, 23.0000, 0.50000,
0.00000
0.6835, 0.6832, 0.6832, 0.5057, 0.5057, 0.5056, 80.0000, 0.33333,
0.33333
*DENSITY
1.4112E-009,\t23
*INITIAL CONDITIONS, TYPE=FIELD, VARIABLE=1
 1, 0.588719
 2, 0.616998
*INITIAL CONDITIONS, TYPE=FIELD, VARIABLE=2
 1, 0.1
 2, 0.2
"""


@pytest.fixture
def card() -> dk.MaterialCard:
    return dk.read_material_card(CARD, 80.0)


@pytest.fixture
def placement() -> Placement:
    return Placement(
        axis_mm=Pair(pinion=(0.0, 0.0), wheel=(52.0, 0.0)),
        tooth_centre_angle_deg=Pair(pinion=-3.25, wheel=181.5),
    )


def _deck(
    card: dk.MaterialCard, placement: Placement, step: dk.MaterialStep = "W1"
) -> dk.PositionDeck:
    return dk.PositionDeck(
        wheel_mesh_file="wheel_mesh.inp",
        pinion_surface_file="pinion_surface.inp",
        placement=placement,
        torques_pinion_nmm=(7846.15, 11769.23, 15692.31),
        torque_sign=-1.0,
        seating_angle_rad=4.0e-5,
        temperature_c=80.0,
        material_step=step,
        card=card,
        orientation_part_file="wheel_orientation_part.inp",
        orientation_model_file="wheel_orientation_model.inp",
        title="test",
        step_names=("LOAD_8NM", "LOAD_12NM", "LOAD_16NM"),
    )


def test_material_card_isotropic_row_at_temperature(card: dk.MaterialCard) -> None:
    assert card.name == "PA46_TEST"
    assert card.youngs_modulus_mpa == 2282.078
    assert card.poisson_ratio == 0.2997
    assert len(card.engineering_constants) == 9
    assert card.plastic_rows == ((5.986, 0.0, 23.0), (93.695, 0.03608, 80.0))
    assert card.potential_rows == ((0.6835, 0.6832, 0.6832, 0.5057, 0.5057, 0.5056, 80.0),)
    assert card.density_rows == ((1.4112e-9, 23.0),)
    at_23 = dk.read_material_card(CARD, 23.0)
    assert at_23.youngs_modulus_mpa == 4110.206
    with pytest.raises(ParseError):
        dk.read_material_card(CARD, 50.0)
    with pytest.raises(ParseError):
        dk.read_material_card("*MATERIAL, NAME=X\n*ELASTIC\n1., 0.3\n", 80.0)


def test_orientation_file_is_split_for_parts_and_instances() -> None:
    pieces = dk.split_orientation_file(CARD, "WHEEL-1")
    assert pieces.part.startswith("*DISTRIBUTION, NAME=DIS_W")
    assert "*ORIENTATION, NAME=ORI_W" in pieces.part and "*SOLID SECTION" in pieces.part
    assert "*MATERIAL" not in pieces.part and "*DISTRIBUTION TABLE" not in pieces.part
    assert pieces.model.startswith("*DISTRIBUTION TABLE")
    assert "*MATERIAL" in pieces.model and "*PLASTIC" in pieces.model
    assert "WHEEL-1.1, 0.588719" in pieces.model and "WHEEL-1.2, 0.2" in pieces.model
    assert "*PLASTIC" not in pieces.model_without_plasticity
    assert "*POTENTIAL" not in pieces.model_without_plasticity
    assert "*ELASTIC" in pieces.model_without_plasticity
    assert "*INITIAL CONDITIONS" in pieces.model_without_plasticity
    with pytest.raises(ParseError):
        dk.split_orientation_file("*MATERIAL, NAME=X\n*ELASTIC\n1., 0.3\n")
    with pytest.raises(InputRangeError):
        dk.split_orientation_file(CARD, "")


def test_position_deck_holds_the_agreed_structure(
    card: dk.MaterialCard, placement: Placement
) -> None:
    text = dk.position_deck_text(_deck(card, placement))
    lines = text.splitlines()
    keywords = [line.split(",")[0].upper() for line in lines if line.startswith("*")]
    assert keywords.count("*STEP") == 4 and keywords.count("*STATIC") == 4
    assert "*STABILIZE" not in text and "STABILIZE" not in text
    assert text.count("NLGEOM=NO") == 4 and "NLGEOM=YES" not in text
    assert "*AMPLITUDE" not in text and "*DAMPING" not in text
    assert "*PREPRINT, ECHO=NO, MODEL=NO, HISTORY=NO, CONTACT=NO" in text
    assert text.count("RF, RM, UR") == 8 and keywords.count("*CONTACT PRINT") == 4
    assert "*INCLUDE, INPUT=wheel_mesh.inp" in text
    assert "*INCLUDE, INPUT=pinion_surface.inp" in text
    assert "*SOLID SECTION, ELSET=WHEEL, MATERIAL=WHEEL_PLASTIC" in text
    assert "2.282078000000e+03, 2.997000000000e-01" in text
    # instances: translation line, then rotation about the own axis by the tooth centre angle - 90
    k = lines.index("*INSTANCE, NAME=WHEEL-1, PART=WHEEL")
    assert lines[k + 1].startswith("5.200000000000e+01, 0.000000000000e+00, 0.")
    assert lines[k + 2].endswith(", 9.150000000000e+01")
    k = lines.index("*INSTANCE, NAME=PINION-1, PART=PINION")
    assert lines[k + 2].endswith(", -9.325000000000e+01")
    assert "*RIGID BODY, REF NODE=PINION_RP, ELSET=PINION-1.PINION" in text
    assert "*RIGID BODY, REF NODE=WHEEL_RP, TIE NSET=WHEEL-1.WHEEL_FESSELUNG" in text
    assert "WHEEL-1.WHEEL_TEETH_SURF, PINION-1.PINION_SURF" in text
    assert "WHEEL-1.WHEEL_NODES, 8.000000000000e+01" in text
    # seating: prescribed rotation with the sign of the torque; loads: released and torque
    assert "PINION_RP, 6, 6, -4.000000000000e-05" in text
    assert text.count("*BOUNDARY, OP=NEW") == 3 and text.count("*CLOAD, OP=NEW") == 3
    assert "PINION_RP, 6, -7.846150000000e+03" in text
    assert "PINION_RP, 6, -1.569231000000e+04" in text
    assert "*STEP, NAME=LOAD_16NM" in text and "*STEP, NAME=SEAT" in text
    assert text.count("S, E, PEEQ") == 4


def test_material_steps_differ_only_in_section_and_material(
    card: dk.MaterialCard, placement: Placement
) -> None:
    texts = {
        step: dk.position_deck_text(_deck(card, placement, step)).splitlines()
        for step in dk.MATERIAL_STEPS
    }

    def outside(lines: list[str]) -> list[str]:
        kept = []
        skip = False
        for line in lines:
            if line.startswith("*PART, NAME=WHEEL") or line.startswith("** --- material"):
                skip = True
            if line.startswith("*END PART") or line.startswith("*INITIAL CONDITIONS"):
                skip = False
            if line.startswith("** material step"):
                continue
            if not skip:
                # the steps with an orientation file also write the field variables
                kept.append("S, E, PEEQ" if line == "S, E, PEEQ, FV" else line)
        return kept

    base = outside(texts["W1"])
    for step in ("W2", "W3", "W4"):
        assert outside(texts[step]) == base
    assert "*PLASTIC" in "\n".join(texts["W2"]) and "*POTENTIAL, TYPE=HILL" in "\n".join(
        texts["W2"]
    )
    # the Hill potential of the isotropic row needs a local orientation (the part's frame);
    # the preprocessor rejects the section without one (W2 pilot 2026-10-09)
    w2 = "\n".join(texts["W2"])
    assert (
        "*ORIENTATION, NAME=WHEEL_ISO, DEFINITION=COORDINATES\n1., 0., 0., 0., 1., 0.\n3, 0.\n"
        in w2
    )
    assert "*SOLID SECTION, ELSET=WHEEL, MATERIAL=WHEEL_PLASTIC, ORIENTATION=WHEEL_ISO" in w2
    assert "*ORIENTATION" not in "\n".join(texts["W1"])
    assert "*SOLID SECTION, ELSET=WHEEL, MATERIAL=WHEEL_PLASTIC\n" in "\n".join(texts["W1"]) + "\n"
    assert "PEEQ" in "\n".join(texts["W2"]) and "PEEQ" in "\n".join(texts["W4"])
    assert "*INCLUDE, INPUT=wheel_orientation_part.inp" in "\n".join(texts["W3"])
    assert "*INCLUDE, INPUT=wheel_orientation_model.inp" in "\n".join(texts["W4"])
    assert "*SOLID SECTION" not in "\n".join(texts["W3"])


def test_orientation_file_section_elset_is_rewritten_to_the_wheel() -> None:
    # CONVERSE names a set of its own that no file defines; the part piece must name the
    # element set of the wheel mesh
    text = CARD.replace(
        "*SOLID SECTION, ELSET=WHEEL,", "*SOLID SECTION, ELSET=CONVERSE_AUTO_SOLID,"
    )
    pieces = dk.split_orientation_file(text, "WHEEL-1")
    assert "*SOLID SECTION, ELSET=WHEEL, MATERIAL=PA46_TEST, ORIENTATION=ORI_W" in pieces.part
    assert "CONVERSE_AUTO_SOLID" not in pieces.part
    assert "ELSET=RAD, MATERIAL=PA46_TEST" in dk.split_orientation_file(text, "WHEEL-1", "RAD").part
    with pytest.raises(InputRangeError):
        dk.split_orientation_file(text, "WHEEL-1", "not an identifier")
    with pytest.raises(ParseError):
        dk.split_orientation_file(
            text.replace("*SOLID SECTION, ELSET=CONVERSE_AUTO_SOLID, ", "*SOLID SECTION, ")
        )


def test_distribution_and_field_variables_are_read() -> None:
    assert dk.read_distribution(CARD) == {
        1: ((-0.5, 0.8, 0.0), (-0.8, -0.5, 0.0)),
        2: ((0.9, 0.1, 0.0), (0.1, -0.9, 0.0)),
    }
    assert dk.read_field_variables(CARD) == {1: (0.588719, 0.1), 2: (0.616998, 0.2)}
    with pytest.raises(ParseError):
        dk.read_distribution("*MATERIAL, NAME=X\n")
    with pytest.raises(ParseError):
        dk.read_distribution(CARD.replace(" 2, 0.9, 0.1, 0, 0.1, -0.9, 0", " 2, 0.9, 0.1"))
    with pytest.raises(ParseError):
        dk.read_field_variables(CARD.replace(" 2, 0.2\n", ""))
    with pytest.raises(ParseError):
        dk.read_field_variables(CARD.replace("VARIABLE=2", "VARIABLE=3"))


def test_steps_with_orientation_write_the_field_variables(
    card: dk.MaterialCard, placement: Placement
) -> None:
    for step in dk.MATERIAL_STEPS:
        text = dk.position_deck_text(_deck(card, placement, step))
        # FV is an element variable at the integration points (Abaqus 2025 output variable
        # identifiers), not a nodal one: the Learning Edition rejected "U, RF, FV"
        assert text.count("S, E, PEEQ, FV") == (4 if step in ("W3", "W4") else 0)
        assert "U, RF, FV" not in text
        assert text.count("DIRECTIONS=YES") == 4
    text = dk.position_deck_text(dataclasses.replace(_deck(card, placement, "W3"), rate="DY1"))
    assert "** material step W3, rate DY1, temperature 80 degC" in text


def test_element_type_and_nlgeom_follow_the_material_step() -> None:
    # the elastic steps run linear with C3D8I, the elastic-plastic steps nonlinear without
    # incompatible modes (element test 2026-10-07, FE-14)
    assert set(dk.NLGEOM_OF_STEP) == set(dk.MATERIAL_STEPS) == set(dk.ELEMENT_TYPE_OF_STEP)
    for step in dk.MATERIAL_STEPS:
        element = dk.ELEMENT_TYPE_OF_STEP[step]
        assert element.startswith("C3D8")
        if dk.NLGEOM_OF_STEP[step]:
            assert not element.endswith("I"), step
    assert dk.NLGEOM_OF_STEP["W1"] is False and dk.ELEMENT_TYPE_OF_STEP["W1"] == "C3D8I"
    assert dk.NLGEOM_OF_STEP["W4"] is True and dk.ELEMENT_TYPE_OF_STEP["W4"] == "C3D8"


def test_solver_and_contact_variants_change_only_their_keywords(
    card: dk.MaterialCard, placement: Placement
) -> None:
    base = dk.position_deck_text(_deck(card, placement))
    assert "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD\n" in base
    assert "*CONTROLS" not in base and "NLGEOM=YES" not in base
    # the standard since 2026-10-07: node-to-surface with the smoothed rigid main surface
    assert "TYPE=NODE TO SURFACE, SMOOTH=0.2\n" in base and "SURFACE TO SURFACE" not in base
    assert "** steps geometrically linear, contact node_to_surface (SMOOTH=0.2)" in base
    variants = {
        "nlgeom": {"nlgeom": True},
        "line_search": {"line_search": 5},
        "direct": {"enforcement": "direct"},
        "augmented": {"enforcement": "augmented_lagrange"},
        "penalty": {"enforcement": "penalty"},
        "s2s": {"contact": "surface_to_surface"},
        "smooth": {"smoothing": 0.5},
        "iterations": {"iteration_limits": (20, 30, 100)},
    }
    expected = {
        "nlgeom": ("NLGEOM=YES", 4),
        "line_search": ("*CONTROLS, PARAMETERS=LINE SEARCH\n5\n", 4),
        "iterations": ("*CONTROLS, PARAMETERS=TIME INCREMENTATION\n20, 30, , 100\n", 4),
        "direct": ("*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD, DIRECT\n", 1),
        "augmented": ("*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD, AUGMENTED LAGRANGE\n", 1),
        "penalty": ("*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD, PENALTY=LINEAR\n", 1),
        "s2s": ("*CONTACT PAIR, INTERACTION=FRICTIONLESS, TYPE=SURFACE TO SURFACE\n", 1),
        "smooth": (
            "*CONTACT PAIR, INTERACTION=FRICTIONLESS, TYPE=NODE TO SURFACE, SMOOTH=0.5\n",
            1,
        ),
    }
    for name, settings in variants.items():
        text = dk.position_deck_text(
            dataclasses.replace(_deck(card, placement), **settings)  # type: ignore[arg-type]
        )
        marker, count = expected[name]
        assert text.count(marker) == count, name
        # everything else is untouched: the same number of lines apart from the controls
        delta = 8 if name in ("line_search", "iterations") else 0
        assert len(text.splitlines()) == len(base.splitlines()) + delta, name
        assert text.count("*NODE PRINT") == 8 and "WHEEL_FESSELUNG" in text
        if name == "iterations":
            assert "iterations I_0/I_R/I_C 20/30/100" in text
    assert "iterations default" in base
    for bad in (
        {"contact": "general"},
        {"enforcement": "soft"},
        {"smoothing": 0.6},
        {"line_search": -1},
        {"iteration_limits": (2, 30, 100)},
        {"iteration_limits": (20, 30)},
    ):
        with pytest.raises(InputRangeError):
            dk.position_deck_text(dataclasses.replace(_deck(card, placement), **bad))


def test_deck_rejects_wrong_inputs(card: dk.MaterialCard, placement: Placement) -> None:
    good = _deck(card, placement)
    with pytest.raises(InputRangeError):
        dk.position_deck_text(dk.PositionDeck(**{**good.__dict__, "torques_pinion_nmm": ()}))
    with pytest.raises(InputRangeError):
        dk.position_deck_text(dk.PositionDeck(**{**good.__dict__, "torque_sign": 0.5}))
    with pytest.raises(InputRangeError):
        dk.position_deck_text(dk.PositionDeck(**{**good.__dict__, "card": None}))
    with pytest.raises(InputRangeError):
        dk.position_deck_text(
            dk.PositionDeck(
                **{**good.__dict__, "material_step": "W3", "orientation_part_file": None}
            )
        )
    assert dk.seating_angle_rad(0.001, 24.0) == pytest.approx(1.0 / 24000.0)
    assert dk.step_name(15692.31) == "LOAD_15P69231NM"
    with pytest.raises(InputRangeError):
        dk.seating_angle_rad(0.0, 24.0)
