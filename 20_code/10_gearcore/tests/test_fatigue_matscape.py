"""The material side of the check against the Haigh diagrams Matscape (PART Engineering) draws
for the same cards (screenshots of 2026-10-11, values in ``stommel_materials.yaml``): the
static reference σ_B,S, the static limit σ_SK (A_max of the single load), the alternating
strength σ_WK (A_W) at 23 and 80 °C and M = σ_WK / σ_B,S. The curves are the values Matscape
itself uses (``data/fatigue/matscape/*.csv``, the user's copy of 2026-10-11), so the
reproduction is exact up to the reading of a strain between two points of the curve."""

import pytest

from gearcore.data import load_stommel_materials
from gearcore.errors import InputRangeError
from gearcore.fatigue import materials as mt

MATERIALS = ("pa46_gf30_linear", "pa46_gf30_qs", "pa46_gf30_dy1", "pa46_gf30_dy2")


def test_cards_carry_the_matscape_failure_type() -> None:
    loaded = load_stommel_materials()
    for name in MATERIALS:
        entry = loaded["materials"][name]
        assert entry["failure_hypothesis"]["f_tau"] == 0.577
        assert entry["failure_hypothesis"]["q"] == 0.0
        assert entry["validation_matscape"][80]["M"] > 0.2
        assert entry["curves"]["room_temperature"]["source"] == "matscape_csv"
    assert mt.material_names() == sorted(MATERIALS)


@pytest.mark.parametrize("name", MATERIALS)
def test_material_side_reproduces_matscape(name: str) -> None:
    material = mt.load_material(name)
    assert material.q == 0.0 and material.f_tau == 0.577
    room = mt.validation_values(name, 23.0)
    hot = mt.validation_values(name, 80.0)
    a_max = material.reduction_class.a_range("einmalig").maximum
    a_w = material.reduction_class.cyclic_reduction_factor.maximum
    # 23 degC: the reference curve itself (its maximum is sigma_B,S)
    assert material.K_mpa == pytest.approx(room["sigma_B_S_mpa"], abs=0.01)
    assert a_max * material.K_mpa == pytest.approx(room["sigma_SK_mpa"], abs=0.01)
    assert a_w * material.K_mpa == pytest.approx(room["sigma_WK_mpa"], abs=0.01)
    # the same through the nomogram functions on the reference curve itself
    for factor, key in ((a_max, "sigma_SK_mpa"), (a_w, "sigma_WK_mpa")):
        strain = mt.strain_limit_percent(material.room_curve, factor, material.K_mpa)
        on_curve = float(mt.stress_on_isotherm(material.room_curve, strain))
        assert on_curve == pytest.approx(room[key], abs=0.01)
    # 80 degC: the strains of the reference curve transferred to the isotherm; Matscape prints
    # two decimals and reads the isotherm off its own interpolation between the same points
    assert material.sigma_Y_service_mpa == pytest.approx(hot["sigma_B_S_mpa"], abs=0.01)
    sigma_stat = float(mt.static_component_strength_mpa(material, "einmalig", 1.0 / 3.0))
    assert sigma_stat == pytest.approx(hot["sigma_SK_mpa"], abs=0.01)
    sigma_w = float(mt.component_alternating_strength_mpa(material, 1.0 / 3.0))
    assert sigma_w == pytest.approx(hot["sigma_WK_mpa"], abs=0.01)
    assert sigma_w / material.sigma_Y_service_mpa == pytest.approx(hot["M"], abs=0.003)


def test_model_properties_match_the_curves() -> None:
    """E_0 and the maxima Matscape prints as model properties are those of the curves."""
    for name in MATERIALS[1:]:
        material = mt.load_material(name)
        for temperature, curve in ((23.0, material.room_curve), (80.0, material.service_curve)):
            assert curve.maximum[0] == pytest.approx(
                mt.model_property(name, temperature, "sigma_b_0_mpa"), abs=0.01
            )
            e_0 = curve.stress_mpa[1] / curve.strain_percent[1] * 100.0
            assert e_0 == pytest.approx(mt.model_property(name, temperature, "E_0_mpa"), rel=0.01)
            ninety = [
                c
                for r, c in material.other_curves
                if r.direction_deg == 90 and r.temperature_c == temperature
            ]
            assert len(ninety) == 1
            assert ninety[0].maximum[0] == pytest.approx(
                mt.model_property(name, temperature, "sigma_b_90_mpa"), abs=0.01
            )
    with pytest.raises(InputRangeError):
        mt.model_property("pa46_gf30_linear", 23.0, "E_0_mpa")
