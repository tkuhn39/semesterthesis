"""The material card of the CONVERSE orientation files (``gearcore.io.converse_card``)."""

from pathlib import Path

import pytest

from gearcore.errors import InputRangeError, ParseError
from gearcore.fatigue import materials as mt
from gearcore.io.converse_card import read_converse_card

REPO = Path(__file__).resolve().parents[3]
CARDS = REPO / "30_references_and_examples" / "91_Converse"

SMALL = """*MATERIAL, NAME=TEST
*ELASTIC,TYPE=ENGINEERING CONSTANTS,DEPENDENCIES=2
4000.0, 4000.0, 4000.0, 0.3, 0.3, 0.3, 1500.0, 1500.0,
1500.0, 23, 0.33333, 0.33333
8000.0, 3000.0, 3000.0, 0.3, 0.3, 0.3, 1200.0, 1200.0,
1200.0, 23, 1.00000, 0.00000
*PLASTIC
50.0, 0.0, 23
100.0, 0.05, 23
*POTENTIAL,TYPE=HILL,DEPENDENCIES=2
0.65, 0.65, 0.65, 0.5, 0.5, 0.5, 23.0, 0.33333,
0.33333
1.5, 0.5, 0.5, 0.7, 0.7, 0.3, 23.0, 1.00000,
0.00000
*DENSITY
1.4e-9, 23
"""


def test_reads_the_tables_and_builds_state_curves() -> None:
    card = read_converse_card(SMALL)
    assert card.name == "TEST" and card.temperatures_c == (23.0,)
    assert card.states(23.0) == ((0.33333, 0.33333), (1.0, 0.0))
    assert card.elastic_at(23.0, 0.3, 0.3).E1_mpa == 4000.0
    assert card.hill_at(23.0, 0.9, 0.0).R11 == 1.5
    stress, strain = card.plastic_at(23.0)
    assert stress.tolist() == [50.0, 100.0] and strain.tolist() == [0.0, 0.05]
    # reference with E 5000: 100 MPa true at log strain 0,05 + 0,02 = 0,07 -> 7,25 % eng, 93,2 MPa
    reference = card.reference_curve(23.0, 5000.0)
    assert reference.strain_percent[-1] == pytest.approx(7.2508, abs=1e-3)
    assert reference.stress_mpa[-1] == pytest.approx(100.0 * 2.718281828 ** (-0.07), abs=1e-3)
    isotropic = card.state_curve(23.0, 1.0 / 3.0, 1.0 / 3.0)
    assert isotropic.stress_mpa[-1] == pytest.approx(
        65.0 * 2.718281828 ** (-(0.05 / 0.65 + 65.0 / 4000.0)), abs=1e-3
    )
    assert isotropic.strain_percent[0] == 0.0 and isotropic.stress_mpa[0] == 0.0
    # plastic strain 0,05 / 0,65 plus elastic 65 / 4000, in engineering strain
    assert isotropic.strain_percent[-1] == pytest.approx(
        (2.718281828 ** (0.05 / 0.65 + 65.0 / 4000.0) - 1.0) * 100.0, abs=1e-3
    )
    with pytest.raises(InputRangeError):
        card.plastic_at(80.0)
    with pytest.raises(ParseError):
        read_converse_card("*MATERIAL, NAME=X\n*PLASTIC\n1, 0, 23\n")


@pytest.mark.skipif(
    not (CARDS / "wheel_mesh_QS.cof").is_file(), reason="CONVERSE cards not present"
)
@pytest.mark.parametrize("name", ["pa46_gf30_qs", "pa46_gf30_dy1", "pa46_gf30_dy2"])
def test_reference_curve_of_the_card_is_the_flow_direction_bar(name: str) -> None:
    """The *PLASTIC curve converted with Matscape's E_0 reproduces the 0 deg curve within
    0,2 MPa at both temperatures; the isotropic state is weaker (R_11 about 0,65)."""
    material = mt.load_material(name)
    card = mt.converse_card(material)
    for temperature, measured in ((23.0, material.room_curve), (80.0, material.service_curve)):
        modulus = mt.model_property(name, temperature, "E_0_mpa")
        reference = card.reference_curve(temperature, modulus)
        assert reference.maximum[0] == pytest.approx(measured.maximum[0], abs=0.2)
        for strain in (0.5, 1.0, 2.0, 3.0):
            assert reference.stress_at(strain) == pytest.approx(measured.stress_at(strain), abs=0.2)
        isotropic = card.hill_at(temperature, 1.0 / 3.0, 1.0 / 3.0).R11
        assert 0.5 < isotropic < 0.7
        assert card.hill_at(temperature, 1.0, 0.0).R11 > 1.3
    weaker = mt.material_for_state(material, "isotropic")
    assert weaker.K_mpa < 0.7 * material.K_mpa
    assert mt.material_for_state(material, "reference") is material
    with pytest.raises(InputRangeError):
        mt.state_of((0.2, 0.5))
