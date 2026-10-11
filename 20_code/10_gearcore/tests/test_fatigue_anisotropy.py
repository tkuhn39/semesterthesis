"""The Hill equivalent stress and the nodal fibre frames of the anisotropic extension (E7)."""

import math

import numpy as np
import pytest

from gearcore.errors import InputRangeError, ParseError
from gearcore.fatigue import anisotropy as an
from gearcore.fatigue import check as ck
from gearcore.fatigue import materials as mt
from gearcore.fatigue import stommel as st
from gearcore.fe.deck import read_element_connectivity
from gearcore.io.converse_card import read_converse_card

ONES = np.ones((1, 6))


def _rotation(axis: str, angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    if axis == "z":
        return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def test_hill_reduces_to_mises_for_unit_ratios() -> None:
    rng = np.random.default_rng(1)
    s = rng.normal(size=(20, 6)) * 50.0
    s1, s2, s3 = st.principal_stresses(s)
    mises = st.mises_stress(s1, s2, s3)
    assert np.allclose(an.hill_equivalent_stress(s, np.ones((20, 6))), mises)
    assert np.allclose(an.hill_equivalent_stress(s, ONES), mises)


def test_uniaxial_and_shear_states_scale_with_their_ratio() -> None:
    ratios = np.array([[1.5, 0.6, 0.5, 0.7, 0.75, 0.4]])
    uniaxial = np.array([[90.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    assert an.hill_equivalent_stress(uniaxial, ratios)[0] == pytest.approx(90.0 / 1.5)
    transverse = np.array([[0.0, -30.0, 0.0, 0.0, 0.0, 0.0]])
    assert an.hill_equivalent_stress(transverse, ratios)[0] == pytest.approx(30.0 / 0.6)
    shear = np.array([[0.0, 0.0, 0.0, 14.0, 0.0, 0.0]])
    assert an.hill_equivalent_stress(shear, ratios)[0] == pytest.approx(math.sqrt(3.0) * 14.0 / 0.7)
    shear23 = np.array([[0.0, 0.0, 0.0, 0.0, 0.0, 10.0]])
    assert an.hill_equivalent_stress(shear23, ratios)[0] == pytest.approx(
        math.sqrt(3.0) * 10.0 / 0.4
    )
    with pytest.raises(InputRangeError):
        an.hill_equivalent_stress(uniaxial, np.array([[1.0, 1.0, 0.0, 1.0, 1.0, 1.0]]))


def test_hill_is_invariant_when_tensor_and_frame_rotate_together() -> None:
    ratios = np.array([[1.4, 0.6, 0.5, 0.6, 0.55, 0.45]])
    local = np.array([[70.0, -20.0, 5.0, 12.0, -3.0, 8.0]])
    reference = an.hill_equivalent_stress(local, ratios)[0]
    q = _rotation("z", 0.7) @ _rotation("x", -0.4)
    tensor = st.tensors_from_components(local)[0]
    rotated = st.components_from_tensors((q @ tensor @ q.T)[np.newaxis])
    back = an.to_local_frame(rotated, q[np.newaxis])
    assert np.allclose(back, local)
    assert an.hill_equivalent_stress(back, ratios)[0] == pytest.approx(reference)
    # in the wrong frame the value differs (the material is anisotropic)
    assert an.hill_equivalent_stress(rotated, ratios)[0] != pytest.approx(reference)


def test_static_equivalent_with_hill_follows_eq_6_16() -> None:
    hill = np.array([40.0])
    s1, s2, s3 = np.array([30.0]), np.array([0.0]), np.array([-26.0])
    assert an.equivalent_stress_static_hill(s1, s2, s3, hill, 0.0)[0] == pytest.approx(40.0)
    # q = 1: the normal stress hypothesis with the compression corrected by 1,3
    assert an.equivalent_stress_static_hill(s1, s2, s3, hill, 1.0)[0] == pytest.approx(30.0)
    assert an.equivalent_stress_static_hill(s1, s2, s3, hill, 0.5)[0] == pytest.approx(35.0)


def test_element_frame_is_orthonormal_and_right_handed() -> None:
    frame = an.element_frame((2.0, 0.0, 0.0), (1.0, 1.0, 0.0))
    assert np.allclose(frame @ frame.T, np.eye(3))
    assert np.allclose(frame[:, 0], [1.0, 0.0, 0.0])
    assert np.allclose(frame[:, 1], [0.0, 1.0, 0.0])
    assert np.allclose(frame[:, 2], [0.0, 0.0, 1.0])
    with pytest.raises(InputRangeError):
        an.element_frame((1.0, 0.0, 0.0), (2.0, 0.0, 0.0))


def test_nodal_frames_average_without_a_sign() -> None:
    labels = np.array([1, 2, 3, 4])
    a = (0.6, 0.8, 0.0)
    b = (-0.8, 0.6, 0.0)
    minus = (-0.6, -0.8, 0.0)
    connectivity = {10: [1, 2], 11: [2, 3]}
    orientation = {10: (a, b), 11: (minus, b)}
    frames, count, gap = an.nodal_frames(labels, connectivity, orientation)
    assert count.tolist() == [1, 2, 1, 0]
    assert gap[0] == pytest.approx(1.0) and gap[3] == 0.0
    expected = an.element_frame(a, b)
    for row in range(3):
        # the same line, whatever the sign
        assert abs(float(frames[row][:, 0] @ expected[:, 0])) == pytest.approx(1.0)
        assert abs(float(frames[row][:, 1] @ expected[:, 1])) == pytest.approx(1.0)
        assert np.allclose(frames[row] @ frames[row].T, np.eye(3))
        assert np.linalg.det(frames[row]) == pytest.approx(1.0)
    assert np.allclose(frames[3], np.eye(3))
    with pytest.raises(InputRangeError):
        an.nodal_frames(labels, {12: [1]}, orientation)


def test_nodal_frames_take_the_dominant_direction() -> None:
    labels = np.array([1])
    connectivity = {1: [1], 2: [1], 3: [1]}
    along_x = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    tilted = ((math.cos(0.3), math.sin(0.3), 0.0), (-math.sin(0.3), math.cos(0.3), 0.0))
    frames, _, _ = an.nodal_frames(labels, connectivity, {1: along_x, 2: along_x, 3: tilted})
    angle = math.acos(abs(float(frames[0][:, 0] @ np.array([1.0, 0.0, 0.0]))))
    assert 0.0 < angle < 0.15


CARD = """*MATERIAL, NAME=TEST
*ELASTIC,TYPE=ENGINEERING CONSTANTS,DEPENDENCIES=2
4000.0, 4000.0, 4000.0, 0.3, 0.3, 0.3, 1500.0, 1500.0,
1500.0, 80, 0.33333, 0.33333
8000.0, 3000.0, 3000.0, 0.3, 0.3, 0.3, 1200.0, 1200.0,
1200.0, 80, 1.00000, 0.00000
*PLASTIC
50.0, 0.0, 80
100.0, 0.05, 80
*POTENTIAL,TYPE=HILL,DEPENDENCIES=2
0.65, 0.65, 0.65, 0.5, 0.5, 0.5, 80.0, 0.33333,
0.33333
1.5, 0.5, 0.5, 0.7, 0.7, 0.3, 80.0, 1.00000,
0.00000
1.0, 0.6, 0.6, 0.6, 0.6, 0.4, 80.0, 0.60000,
0.30000
"""


def test_nearest_ratios_and_states() -> None:
    card = read_converse_card(CARD)
    states = np.array([[0.35, 0.3], [0.9, 0.05]])
    ratios = an.nearest_hill_ratios(card, 80.0, states)
    assert ratios[0].tolist() == [0.65, 0.65, 0.65, 0.5, 0.5, 0.5]
    assert ratios[1].tolist() == [1.5, 0.5, 0.5, 0.7, 0.7, 0.3]
    with pytest.raises(InputRangeError):
        an.nearest_hill_ratios(card, 23.0, states)
    fields = {1: (0.6, 0.1), 2: (0.34, 0.33)}
    assert an.nodal_states([1, 2], fields).tolist() == [[0.6, 0.1], [0.34, 0.33]]
    with pytest.raises(InputRangeError):
        an.nodal_states([1, 3], fields)


def test_build_nodal_anisotropy_end_to_end() -> None:
    card = read_converse_card(CARD)
    connectivity = {1: [1, 2], 2: [2, 3]}
    orientation = {
        1: ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        2: ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
    }
    fields = {1: (0.95, 0.03), 2: (0.5, 0.2), 3: (0.34, 0.33)}
    built = an.build_nodal_anisotropy([1, 2, 3], connectivity, orientation, fields, card, 80.0)
    assert built.n == 3 and built.card == "TEST"
    # the ratios are interpolated over the lattice (three states in this card)
    assert np.allclose(built.ratios, an.interpolated_hill_ratios(card, 80.0, built.states))
    assert built.ratios[0, 0] > 1.2 and built.ratios[2, 0] == pytest.approx(0.65, abs=0.02)
    assert built.element_count.tolist() == [1, 2, 1]
    with pytest.raises(InputRangeError):
        an.build_nodal_anisotropy([1, 2, 3, 4], connectivity, orientation, fields, card, 80.0)


def test_read_element_connectivity() -> None:
    text = (
        "*NODE\n1, 0., 0., 0.\n*ELEMENT, TYPE=C3D8I, ELSET=WHEEL\n"
        "1, 1, 2, 3, 4, 5, 6, 7, 8\n2, 2, 3, 4, 5, 6, 7, 8,\n9\n"
        "*ELEMENT, TYPE=C3D4\n7, 1, 2, 3, 4\n"
    )
    elements = read_element_connectivity(text)
    assert elements == {1: (1, 2, 3, 4, 5, 6, 7, 8), 2: (2, 3, 4, 5, 6, 7, 8, 9), 7: (1, 2, 3, 4)}
    with pytest.raises(ParseError):
        read_element_connectivity("*ELEMENT, TYPE=C3D8\n1, 1, 2, 3\n")


def test_check_with_unit_ratios_equals_the_mises_check() -> None:
    """Hill with identity frames and unit ratios reproduces the von Mises check exactly."""
    material = mt.load_material("pa46_gf30_qs")
    rng = np.random.default_rng(3)
    states = [rng.normal(size=(5, 6)) * 7.0 for _ in range(3)]
    base = ck.accumulate(material, ck.CheckSettings(amplitude_route="signed_mises"), states)
    unit = an.NodalAnisotropy(
        node_labels=np.arange(1, 6),
        frames=np.broadcast_to(np.eye(3), (5, 3, 3)).copy(),
        element_count=np.ones(5, dtype=np.int64),
        states=np.full((5, 2), 1.0 / 3.0),
        ratios=np.ones((5, 6)),
        temperature_c=80.0,
        card="unit",
    )
    hill = ck.accumulate(
        material,
        ck.CheckSettings(amplitude_route="signed_hill", equivalent="hill"),
        states,
        anisotropy=unit,
    )
    assert np.all(np.isfinite(base.a_stat))
    assert np.allclose(hill.a_stat, base.a_stat)
    assert np.allclose(hill.sigma_V_at_max, base.sigma_V_at_max)
    assert np.allclose(hill.hill_signed_max, base.signed_max)
    assert np.allclose(hill.hill_signed_min, base.signed_min)
    result_base = ck.check(base, np.arange(1, 6))
    result_hill = ck.check(hill, np.arange(1, 6))
    assert np.allclose(result_hill.cyclic.a_B_V, result_base.cyclic.a_B_V)
    assert result_hill.equivalent == "hill"
    with pytest.raises(InputRangeError):
        ck.CheckSettings(amplitude_route="signed_hill")
    with pytest.raises(InputRangeError):
        ck.CheckSettings(equivalent="hill")  # the principal route keeps isotropic strengths
    with pytest.raises(InputRangeError):
        ck.HistoryAccumulator(
            material, ck.CheckSettings(equivalent="hill", amplitude_route="signed_hill"), 5
        )


def test_anisotropic_ratios_change_the_static_result() -> None:
    material = mt.load_material("pa46_gf30_qs")
    state = np.array([[0.0, 60.0, 0.0, 0.0, 0.0, 0.0]])  # 60 MPa across the fibres (axis 2)
    weak = an.NodalAnisotropy(
        node_labels=np.array([1]),
        frames=np.eye(3)[np.newaxis].copy(),
        element_count=np.ones(1, dtype=np.int64),
        states=np.array([[0.64, 0.083]]),
        ratios=np.array([[0.96, 0.6, 0.5, 0.58, 0.55, 0.41]]),
        temperature_c=80.0,
        card="root",
    )
    settings = ck.CheckSettings(amplitude_route="signed_hill", equivalent="hill")
    history = ck.accumulate(material, settings, [state], anisotropy=weak)
    # 60 MPa across the fibres count as 60 / 0,6 = 100 MPa of the reference curve
    assert history.sigma_V_at_max[0] == pytest.approx(100.0, abs=0.5)
    isotropic = ck.accumulate(material, ck.CheckSettings(amplitude_route="signed_mises"), [state])
    assert history.a_stat[0] > isotropic.a_stat[0]


def test_reduction_class_can_be_swapped_for_the_extension() -> None:
    """Under the Hill extension the anisotropy is not counted twice (user, 2026-10-11): the
    reduction factors of another class replace those of the reinforced class."""
    material = mt.load_material("pa46_gf30_qs")
    ductile = mt.with_reduction_class(material, "semi_crystalline_unreinforced")
    assert ductile.reduction_class.name == "semi_crystalline_unreinforced"
    assert ductile.failure_hypothesis_class is material.failure_hypothesis_class
    assert ductile.K_mpa == material.K_mpa
    assert float(mt.static_component_strength_mpa(ductile, "einmalig", 1.0 / 3.0)) > float(
        mt.static_component_strength_mpa(material, "einmalig", 1.0 / 3.0)
    )
    with pytest.raises(InputRangeError):
        mt.with_reduction_class(material, "steel")


def test_interpolated_ratios_follow_the_lattice_linearly() -> None:
    card = read_converse_card(CARD)
    lattice = np.array([[1.0 / 3.0, 1.0 / 3.0], [1.0, 0.0], [0.6, 0.3]])
    at_lattice = an.interpolated_hill_ratios(card, 80.0, lattice)
    assert np.allclose(at_lattice[0], [0.65, 0.65, 0.65, 0.5, 0.5, 0.5], atol=1e-6)
    assert np.allclose(at_lattice[1], [1.5, 0.5, 0.5, 0.7, 0.7, 0.3], atol=1e-6)
    midpoint = an.interpolated_hill_ratios(card, 80.0, np.array([[0.8, 0.15]]))
    assert np.allclose(midpoint[0], [1.25, 0.55, 0.55, 0.65, 0.65, 0.35], atol=1e-6)
    outside = an.interpolated_hill_ratios(card, 80.0, np.array([[0.05, 0.05]]))
    assert np.allclose(outside[0], an.nearest_hill_ratios(card, 80.0, np.array([[0.05, 0.05]]))[0])


def test_pressure_corrected_components_divide_the_compression_only() -> None:
    uniaxial = np.array([[-60.0, 0.0, 0.0, 0.0, 0.0, 0.0], [60.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    corrected = an.pressure_corrected_components(uniaxial, 1.3)
    assert np.allclose(corrected[0], [-60.0 / 1.3, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert np.allclose(corrected[1], uniaxial[1])
    # a rotated compressive state keeps its directions
    q = _rotation("z", 0.5)
    tensor = q @ np.diag([-60.0, 0.0, 10.0]) @ q.T
    rotated = st.components_from_tensors(tensor[np.newaxis])
    back = st.tensors_from_components(an.pressure_corrected_components(rotated, 1.3))[0]
    assert np.allclose(np.sort(np.linalg.eigvalsh(back)), [-60.0 / 1.3, 0.0, 10.0])
    # with unit ratios the static Hill branch equals the published one for compression
    s1, s2, s3 = st.principal_stresses(uniaxial)
    published = st.equivalent_stress_static(s1, s2, s3, 0.0, 1.3)
    hill = an.hill_equivalent_stress(corrected, np.ones((2, 6)))
    assert np.allclose(an.equivalent_stress_static_hill(s1, s2, s3, hill, 0.0, 1.3), published)
