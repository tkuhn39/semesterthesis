"""The equations of chapter 6 of Stommel, Stojek, Korte (2018) against the numbers the book
prints (``gearcore.fatigue.stommel``) and the class tables (``data/fatigue/stommel_materials.yaml``)."""

import math

import numpy as np
import pytest

from gearcore.errors import InputRangeError
from gearcore.fatigue import materials as mt
from gearcore.fatigue import stommel as st

pytestmark = pytest.mark.eq("Stommel2018", "chapter 6")


def test_tensor_helpers_round_trip() -> None:
    components = np.array([[10.0, -5.0, 2.0, 3.0, 1.0, -2.0], [0.0] * 6])
    tensors = st.tensors_from_components(components)
    assert tensors.shape == (2, 3, 3)
    assert np.allclose(tensors[0], tensors[0].T)
    assert np.allclose(st.components_from_tensors(tensors), components)
    s1, s2, s3 = st.principal_stresses([100.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert (float(s1), float(s2), float(s3)) == pytest.approx((100.0, 0.0, 0.0))
    s1, s2, s3 = st.principal_stresses([0.0, 0.0, 0.0, 30.0, 0.0, 0.0])  # pure shear
    assert (float(s1), float(s2), float(s3)) == pytest.approx((30.0, 0.0, -30.0))
    with pytest.raises(InputRangeError):
        st.tensors_from_components([1.0, 2.0, 3.0])


def test_control_variable_reproduces_tabelle_6_1() -> None:
    # Tabelle 6.1, p. 323: f_tau 0,58 / 0,65 / 0,74 give q 0 / 0,26 / 0,52
    assert float(st.control_variable(0.58)) == pytest.approx(0.0, abs=0.011)  # 0,0108, printed 0
    assert float(st.control_variable(0.65)) == pytest.approx(0.26, abs=0.005)
    assert float(st.control_variable(0.74)) == pytest.approx(0.52, abs=0.005)
    assert float(st.control_variable(1.0)) == pytest.approx(1.0)
    with pytest.raises(InputRangeError):
        st.control_variable(0.5)  # ideal ductile: below the von Mises value, no mixing rule


def test_equivalent_stress_interpolates_between_the_hypotheses() -> None:
    assert float(st.equivalent_stress(60.0, 50.0, 0.0)) == pytest.approx(50.0)
    assert float(st.equivalent_stress(60.0, 50.0, 1.0)) == pytest.approx(60.0)
    assert float(st.equivalent_stress(60.0, 50.0, 0.26)) == pytest.approx(52.6)


def test_multiaxiality_degree_reproduces_tabelle_6_2() -> None:
    # Tabelle 6.2, p. 325: pure shear 0, uniaxial 1/3, equibiaxial 2/3, hydrostatic infinity
    assert float(st.multiaxiality_degree(10.0, -10.0, 0.0)) == pytest.approx(0.0)
    assert float(st.multiaxiality_degree(10.0, 0.0, 0.0)) == pytest.approx(1.0 / 3.0)
    assert float(st.multiaxiality_degree(10.0, 10.0, 0.0)) == pytest.approx(2.0 / 3.0)
    assert math.isinf(float(st.multiaxiality_degree(10.0, 10.0, 10.0)))
    assert float(st.multiaxiality_degree(0.0, 0.0, 0.0)) == 0.0  # unloaded: convention
    assert float(st.hydrostatic_stress(30.0, 0.0, 0.0)) == pytest.approx(10.0)
    assert float(st.mises_stress(30.0, 0.0, 0.0)) == pytest.approx(30.0)
    assert float(st.mises_stress(30.0, 30.0, 30.0)) == 0.0


def test_permissible_strain_follows_bild_6_8() -> None:
    # Bild 6.8, p. 326: epsilon_min 1,5 %, epsilon_max 3,0 %
    assert float(st.permissible_strain(1.0 / 3.0, 1.5, 3.0)) == pytest.approx(3.0)
    assert float(st.permissible_strain(0.1, 1.5, 3.0)) == pytest.approx(3.0)
    assert float(st.permissible_strain(2.0 / 3.0, 1.5, 3.0)) == pytest.approx(2.25)
    assert float(st.permissible_strain(10.0, 1.5, 3.0)) == pytest.approx(1.55)
    assert float(st.permissible_strain(math.inf, 1.5, 3.0)) == pytest.approx(1.5)
    with pytest.raises(InputRangeError):
        st.permissible_strain(0.5, 3.0, 1.5)


def test_natural_multiaxiality_and_its_scaling() -> None:
    # Eq. (6.5), p. 327: 1 uniaxial, 2 equibiaxial, 3 hydrostatic, 0 pure shear
    assert float(st.natural_multiaxiality_degree(10.0, 0.0, 0.0)) == pytest.approx(1.0)
    assert float(st.natural_multiaxiality_degree(10.0, 10.0, 0.0)) == pytest.approx(2.0)
    assert float(st.natural_multiaxiality_degree(10.0, 10.0, 10.0)) == pytest.approx(3.0)
    assert float(st.natural_multiaxiality_degree(10.0, -10.0, 0.0)) == pytest.approx(0.0)
    # Eq. (6.6): the hydrostatic state reaches epsilon_min exactly
    assert float(st.permissible_strain_natural(1.0, 1.5, 3.0)) == pytest.approx(3.0)
    assert float(st.permissible_strain_natural(2.0, 1.5, 3.0)) == pytest.approx(1.875)
    assert float(st.permissible_strain_natural(3.0, 1.5, 3.0)) == pytest.approx(1.5)


def test_haigh_approximations_of_eq_6_7() -> None:
    # Bild 6.10, p. 330: PA66+GF35, sigma_w 48,5 MPa at R = -1, static strength about 150 MPa;
    # the measured point at R = 0 lies near 35 MPa amplitude
    assert float(st.goodman_amplitude(48.5, 0.0, 150.0)) == pytest.approx(48.5)
    assert float(st.goodman_amplitude(48.5, 150.0, 150.0)) == pytest.approx(0.0)
    assert float(st.goodman_amplitude(48.5, 35.0, 150.0)) == pytest.approx(35.0, abs=3.0)
    assert float(st.gerber_amplitude(48.5, 35.0, 150.0)) > float(
        st.goodman_amplitude(48.5, 35.0, 150.0)
    )


def test_amplitude_mean_and_signed_mises_of_a_history() -> None:
    assert float(st.stress_amplitude(100.0, -50.0)) == pytest.approx(75.0)
    assert float(st.mean_stress(100.0, -50.0)) == pytest.approx(25.0)
    with pytest.raises(InputRangeError):
        st.stress_amplitude(10.0, 20.0)
    # Eq. (6.8): plane stress von Mises; uniaxial gives the stress itself
    assert float(st.mises_stress_plane(50.0, 0.0, 0.0)) == pytest.approx(50.0)
    assert float(st.mises_stress_plane(0.0, 0.0, 10.0)) == pytest.approx(10.0 * math.sqrt(3.0))
    # Eq. (6.10): the sign of I_1 turns the compression state negative
    states = np.array([[100.0, 0.0, 0.0], [-50.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    mises = st.mises_stress(states[:, 0], states[:, 1], states[:, 2])
    trace = st.first_stress_invariant(states[:, 0], states[:, 1], states[:, 2])
    signed = st.signed_mises_stress(mises, trace)
    assert signed.tolist() == pytest.approx([100.0, -50.0, 0.0])
    assert float(st.signed_mises_amplitude(signed.max(), signed.min())) == pytest.approx(75.0)
    assert float(st.signed_mises_mean(signed.max(), signed.min())) == pytest.approx(25.0)
    # Eq. (6.11) and (6.12): the sign of the mean
    assert float(st.manson_mcknight_mean(30.0, -5.0)) == pytest.approx(-30.0)
    assert float(st.modified_manson_mcknight_mean(30.0, 100.0, -50.0)) == pytest.approx(10.0)
    assert float(st.modified_manson_mcknight_mean(30.0, 50.0, 50.0)) == 0.0
    # Eq. (6.13): normalised von Mises utilisation
    assert float(st.normalised_mises_utilisation(0.6, 0.0, 0.0)) == pytest.approx(0.6)
    assert float(st.normalised_mises_utilisation(0.0, 0.0, 0.5)) == pytest.approx(0.5)
    # Eq. (6.14): Neuber
    assert float(st.neuber_product(100.0, 2000.0)) == pytest.approx(5.0)


def test_static_check_of_section_6_2() -> None:
    assert float(st.static_utilisation(2.4, 2.4)) == pytest.approx(1.0)
    assert float(st.static_utilisation(1.2, 2.4, 2.0)) == pytest.approx(1.0)
    assert math.isinf(float(st.static_utilisation(math.inf, 2.4)))
    # Eq. (6.17): compression divided by 1,3; the hypotheses take the magnitudes
    assert float(st.pressure_corrected_principal_stress(-39.0)) == pytest.approx(-30.0)
    assert float(st.pressure_corrected_principal_stress(39.0)) == pytest.approx(39.0)
    assert float(st.normal_stress_hypothesis_stress(10.0, -40.0, 0.0)) == pytest.approx(40.0)
    uniaxial_compression = float(st.equivalent_stress_static(0.0, 0.0, -39.0, 0.26))
    assert uniaxial_compression == pytest.approx(30.0)
    uniaxial_tension = float(st.equivalent_stress_static(39.0, 0.0, 0.0, 0.26))
    assert uniaxial_tension == pytest.approx(39.0)
    assert float(st.utilisation(42.0, 52.0)) == pytest.approx(42.0 / 52.0)


def test_fatigue_strengths_of_section_6_3() -> None:
    # Bild 6.27, p. 364: sigma_W of PA66-GF35 computed 37,5 MPa with A_W 0,25 and the static
    # strength of about 150 MPa (Bild 6.10)
    assert float(st.component_alternating_strength(0.25, 150.0)) == pytest.approx(37.5)
    assert float(st.component_fatigue_strength(1.0, 0.8, 25.0)) == pytest.approx(20.0)
    assert float(st.mean_stress_factor(20.0, 25.0)) == pytest.approx(0.8)
    # Bild 6.28, p. 365: sigma_Y 100 MPa, sigma_W 25 MPa, M = 0,25
    M = float(st.mean_stress_sensitivity(25.0, 100.0))
    assert pytest.approx(0.25) == M
    # the four overload cases meet the Goodman line (Bild 6.29): F1 at sigma_m 25,
    # F2 and F3 at R = 0 (sigma_m = sigma_a = 20, sigma_min = 0), F4 at sigma_max 40
    assert float(st.mean_stress_factor_case_1(M, 25.0, 25.0)) == pytest.approx(0.75)
    assert float(st.goodman_amplitude(25.0, 25.0, 100.0)) / 25.0 == pytest.approx(0.75)
    assert float(st.mean_stress_factor_case_2(M, 20.0, 20.0)) == pytest.approx(0.8)
    assert float(st.mean_stress_factor_case_3(M, 0.0, 25.0)) == pytest.approx(0.8)
    assert float(st.mean_stress_factor_case_4(M, 40.0, 25.0)) == pytest.approx(0.8)
    assert float(st.mean_stress_factor_case_2(M, 0.0, 0.0)) == 1.0  # no amplitude: no ratio
    # compression side: the ray of constant R misses the continued line, no Goodman limit
    assert math.isinf(float(st.mean_stress_factor_case_2(M, -40.0, 5.0)))
    assert float(st.mean_stress_factor_case_2(M, -20.0, 20.0)) == pytest.approx(1.0 / 0.75)
    assert float(st.mean_stress_factor_case_1(M, -25.0, 25.0)) == pytest.approx(1.25)  # mirrored
    with pytest.raises(InputRangeError):
        st.mean_stress_factor_case_4(1.2, 40.0, 25.0)


def test_woehler_line_of_section_6_3_4() -> None:
    assert float(st.fatigue_life_factor(1.0e7, 1.0e7, 15.65)) == pytest.approx(1.0)
    k_b = float(st.fatigue_life_factor(1.0e7, 1.0e4, 20.44))
    assert k_b == pytest.approx(10.0 ** (3.0 / 20.44))
    assert float(st.cycles_at_fatigue_life_factor(k_b, 20.44)) == pytest.approx(1.0e4, rel=1e-9)
    # Tabelle 6.3, p. 371, from the rows of Bild 6.18 and Bild 6.26
    assert float(st.woehler_slope_exponent(0.55, 0.25)) == pytest.approx(20.44, abs=0.005)
    assert float(st.woehler_slope_exponent(0.7, 0.25)) == pytest.approx(15.65, abs=0.005)
    with pytest.raises(InputRangeError):
        st.woehler_slope_exponent(0.25, 0.25)
    # Eq. (6.23): the cap
    assert float(st.max_component_fatigue_strength(70.0, 25.0)) == pytest.approx(45.0)
    assert float(st.max_component_fatigue_strength(70.0, -25.0)) == pytest.approx(45.0)
    assert float(st.capped_component_fatigue_strength(50.0, 45.0)) == pytest.approx(45.0)
    assert float(st.capped_component_fatigue_strength(40.0, 45.0)) == pytest.approx(40.0)
    assert float(st.capped_component_fatigue_strength(40.0, -5.0)) == 0.0
    assert float(st.capped_component_fatigue_strength(math.inf, 45.0)) == pytest.approx(45.0)


def test_cyclic_utilisation_of_section_6_3_5() -> None:
    a = st.single_utilisation([20.0, 0.0, 0.0], 16.0)
    assert a.tolist() == pytest.approx([1.25, 0.0, 0.0])
    assert float(st.cyclic_utilisation_mises(1.25, 0.0, 0.0)) == pytest.approx(1.25)
    assert float(st.cyclic_utilisation_normal_stress(1.25, 0.0, 0.0)) == pytest.approx(1.25)
    assert float(st.cyclic_utilisation_mises(0.5, 0.5, 0.5)) == 0.0
    assert float(st.cyclic_utilisation(0.5, 0.0, 1.0)) == pytest.approx(0.5)
    assert float(st.cyclic_utilisation(0.5, 0.0, 0.0)) == 0.0
    assert math.isinf(float(st.single_utilisation(5.0, 0.0)))
    assert float(st.single_utilisation(0.0, 0.0)) == 0.0
    with pytest.raises(InputRangeError):
        st.single_utilisation(-1.0, 10.0)


def test_class_tables_reproduce_tabelle_6_3() -> None:
    classes = mt.material_classes()
    assert set(classes) == {
        "semi_crystalline_unreinforced",
        "amorphous_unreinforced",
        "semi_crystalline_reinforced",
        "amorphous_reinforced",
    }
    for name, cls in classes.items():
        single = cls.a_range("einmalig")
        cyclic = cls.cyclic_reduction_factor
        low = float(st.woehler_slope_exponent(single.minimum, cyclic.minimum))
        high = float(st.woehler_slope_exponent(single.maximum, cyclic.maximum))
        printed = sorted((cls.slope_exponent.minimum, cls.slope_exponent.maximum))
        assert sorted((low, high)) == pytest.approx(printed, abs=0.006), name
        assert float(st.control_variable(cls.f_tau)) == pytest.approx(cls.q, abs=0.011), name
        assert cls.a_range("wechselnd").maximum == cyclic.maximum, name
    reinforced = classes["semi_crystalline_reinforced"]
    assert (
        reinforced.cyclic_reduction_factor.minimum
        == reinforced.cyclic_reduction_factor.maximum
        == 0.25
    )
    assert not reinforced.cyclic_factor_scaled_by_multiaxiality
    assert classes["semi_crystalline_unreinforced"].cyclic_factor_scaled_by_multiaxiality
    with pytest.raises(InputRangeError):
        reinforced.a_range("dauernd")  # type: ignore[arg-type]
