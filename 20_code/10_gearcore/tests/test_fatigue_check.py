"""The node-wise check after Stommel et al. on a synthetic material and history
(``gearcore.fatigue.check``, ``gearcore.fatigue.materials``)."""

import math
from pathlib import Path

import numpy as np
import pytest
from test_fe_stress import write_stress_file

from gearcore.errors import InputRangeError
from gearcore.fatigue import check as ck
from gearcore.fatigue import materials as mt
from gearcore.io.matscape import StressStrainCurve


def _line(slope_mpa_per_percent: float, knee_percent: float = 5.0) -> StressStrainCurve:
    """A linear curve up to the knee, flat to 6 % (the maximum sits at the knee)."""
    strains = [0.0, 1.0, 2.0, 3.0, 4.0, knee_percent, 6.0]
    stresses = [slope_mpa_per_percent * min(s, knee_percent) for s in strains]
    return StressStrainCurve(strain_percent=tuple(strains), stress_mpa=tuple(stresses))


@pytest.fixture(scope="module")
def material() -> mt.StommelMaterial:
    classes = mt.material_classes()
    reference = mt.CurveReference(
        file="synthetic", direction_deg=0, rate="QS", temperature_c=23, humidity_percent=50
    )
    service = mt.CurveReference(
        file="synthetic", direction_deg=0, rate="QS", temperature_c=80, humidity_percent=50
    )
    return mt.StommelMaterial(
        name="synthetic",
        designation="synthetic reinforced polyamide",
        reduction_class=classes["semi_crystalline_reinforced"],
        failure_hypothesis_class=classes["semi_crystalline_unreinforced"],
        room_temperature=reference,
        service=service,
        room_curve=_line(20.0),  # K = 100 MPa at 5 %
        service_curve=_line(16.0),  # sigma_Y(80 degC) = 80 MPa
        provenance="test",
    )


K_SYNTHETIC = 7.0 / math.log10(2.8)
"""k of the synthetic material at h = 1/3: sigma_stat 56 over sigma_W 20 (both at 80 degC)."""


def test_material_side_of_the_nomogram(material: mt.StommelMaterial) -> None:
    assert material.K_mpa == 100.0 and material.K_strain_percent == 5.0
    assert material.sigma_Y_service_mpa == 80.0 and material.q == 0.0
    assert mt.strain_limits_percent(material, "einmalig") == pytest.approx((2.75, 3.5))
    assert float(mt.permissible_strain_percent(material, "einmalig", 1.0 / 3.0)) == pytest.approx(
        3.5
    )
    assert float(mt.permissible_strain_percent(material, "einmalig", math.inf)) == pytest.approx(
        2.75
    )
    assert float(
        mt.static_component_strength_mpa(material, "einmalig", 1.0 / 3.0)
    ) == pytest.approx(56.0)
    assert float(mt.effective_reduction_factor(material, "einmalig", 1.0 / 3.0)) == pytest.approx(
        0.7
    )
    assert float(mt.effective_reduction_factor(material, "einmalig", math.inf)) == pytest.approx(
        0.55
    )
    # A_W 0,25 fixed: strain 1,25 % on the room curve, 20 MPa on the 80 degC isotherm
    assert float(mt.component_alternating_strength_mpa(material, 1.0 / 3.0)) == pytest.approx(20.0)
    assert mt.cyclic_reduction_factor(material, np.array([0.1, 5.0])).tolist() == [0.25, 0.25]
    # k at the service temperature: lg N_G / lg(sigma_stat,T / sigma_W,T) (p. 371)
    assert float(mt.slope_exponent(material, 1.0 / 3.0)) == pytest.approx(K_SYNTHETIC)
    assert float(mt.slope_exponent(material, math.inf)) == pytest.approx(7.0 / math.log10(2.2))
    assert mt.equivalent_strain_percent(material.service_curve, [40.0, 80.0]).tolist() == (
        pytest.approx([2.5, 5.0])
    )
    assert math.isinf(float(mt.equivalent_strain_percent(material.service_curve, 90.0)))
    with pytest.raises(InputRangeError):
        mt.stress_on_isotherm(material.service_curve, 7.0)
    with pytest.raises(InputRangeError):
        mt.strain_limit_percent(material.room_curve, 1.2, 100.0)


def test_inverse_reading_bridges_a_dip() -> None:
    curve = StressStrainCurve(
        strain_percent=(0.0, 1.0, 2.0, 3.0, 4.0), stress_mpa=(0.0, 20.0, 19.0, 30.0, 31.0)
    )
    strains = mt.equivalent_strain_percent(curve, [10.0, 20.0, 25.0, 31.0])
    assert strains.tolist() == pytest.approx(
        [0.5, 1.0, 2.0, 4.0]
    )  # 25 MPa between 20 at 1 % and 30 at 3 %


def _state(tension: float = 0.0, compression: float = 0.0) -> np.ndarray:
    """Three nodes: node 0 unloaded, node 1 with S11 = tension, node 2 with S33 = -compression."""
    s = np.zeros((3, 6))
    s[1, 0] = tension
    s[2, 2] = -compression
    return s


def test_check_of_three_nodes_by_hand(material: mt.StommelMaterial) -> None:
    settings = ck.CheckSettings()
    result = ck.check(ck.accumulate(material, settings, [_state(40.0, 40.0)]), [100, 200, 300])
    assert result.states == 2 and np.allclose(result.K_B, 1.0)
    # static check: tension 40 MPa gives epsilon_V 2,5 % against epsilon_zul 3,5 %;
    # compression 40 MPa is divided by 1,3 before the hypotheses
    assert result.a_stat.tolist() == pytest.approx([0.0, 2.5 / 3.5, (40.0 / 1.3 / 16.0) / 3.5])
    assert result.sigma_V_max.tolist() == pytest.approx([0.0, 40.0, 40.0 / 1.3])
    assert result.h_at_max.tolist() == pytest.approx([0.0, 1.0 / 3.0, -1.0 / 3.0])
    assert result.sigma_stat.tolist() == pytest.approx([56.0, 56.0, 56.0])
    assert result.state_of_max.tolist() == [-1, 0, 0]
    # cyclic check, route principal, overload case 2: sigma_W 20, M 0,25
    assert result.sigma_W.tolist() == pytest.approx([20.0, 20.0, 20.0])
    assert result.M.tolist() == pytest.approx([0.25, 0.25, 0.25])
    cyc = result.cyclic
    assert cyc.sigma_a[1].tolist() == pytest.approx([20.0, 0.0, 0.0])
    assert cyc.sigma_m[1].tolist() == pytest.approx([20.0, 0.0, 0.0])
    assert cyc.K_M[1].tolist() == pytest.approx([0.8, 1.0, 1.0])
    assert cyc.sigma_B[1].tolist() == pytest.approx([16.0, 20.0, 20.0])
    assert cyc.a_B_V.tolist() == pytest.approx([0.0, 1.25, 0.75])
    assert cyc.sigma_a[2].tolist() == pytest.approx([0.0, 0.0, 20.0])
    assert cyc.K_M[2][2] == pytest.approx(1.0 / 0.75)
    # the predicted life on the synthetic line: K_B = 1,25 for the tension node
    assert result.k.tolist() == pytest.approx([K_SYNTHETIC] * 3)
    assert result.N_predicted[1] == pytest.approx(1.0e7 / 1.25**K_SYNTHETIC, rel=0.02)
    assert result.N_predicted[2] == pytest.approx(1.0e7 / 0.75**K_SYNTHETIC, rel=0.02)
    assert math.isinf(result.N_predicted[0])
    assert result.life_flags == ("none", "ok", "beyond_N_G")
    assert result.critical_cyclic == 1 and result.critical_static == 1
    assert result.a_B_V_at_N_G.tolist() == pytest.approx(cyc.a_B_V.tolist())


def test_reversal_keeps_its_sign_on_fixed_directions(material: mt.StommelMaterial) -> None:
    """Tension +40 then compression -40 in the same direction: one component with the
    amplitude 40 and the mean 0, not two half amplitudes (review finding P0-2)."""
    states = [_state(40.0, 0.0), _state(-40.0, 0.0)]
    principal = ck.check(ck.accumulate(material, ck.CheckSettings(), states), [1, 2, 3])
    assert principal.cyclic.sigma_a[1].tolist() == pytest.approx([40.0, 0.0, 0.0])
    assert principal.cyclic.sigma_m[1].tolist() == pytest.approx([0.0, 0.0, 0.0])
    assert principal.cyclic.K_M[1][0] == pytest.approx(1.0)
    assert principal.cyclic.a_B_V[1] == pytest.approx(2.0)
    signed = ck.check(
        ck.accumulate(material, ck.CheckSettings(amplitude_route="signed_mises"), states), [1, 2, 3]
    )
    assert signed.cyclic.a_B_V[1] == pytest.approx(2.0)
    # the governing state is the tension state (a_stat 0,71 against 0,55 in compression)
    assert principal.state_of_max[1] == 0
    without_second_pass = ck.HistoryAccumulator(material, ck.CheckSettings(), 3)
    without_second_pass.add_state(_state(40.0), label=0)
    with pytest.raises(InputRangeError, match="second pass"):
        ck.check(without_second_pass, [1, 2, 3])


def test_other_routes_and_cases(material: mt.StommelMaterial) -> None:
    states = [_state(40.0, 40.0)]
    signed = ck.check(
        ck.accumulate(material, ck.CheckSettings(amplitude_route="signed_mises"), states), [1, 2, 3]
    )
    assert signed.cyclic.a_B_V.tolist() == pytest.approx([0.0, 1.25, 0.75])
    assert signed.cyclic.sigma_m.tolist() == pytest.approx([0.0, 20.0, -20.0])
    mmk = ck.check(
        ck.accumulate(material, ck.CheckSettings(amplitude_route="mmk"), states), [1, 2, 3]
    )
    assert mmk.cyclic.sigma_a.tolist() == pytest.approx([0.0, 20.0, 20.0])
    assert mmk.cyclic.sigma_m.tolist() == pytest.approx([0.0, 20.0, -20.0])
    modified = ck.check(
        ck.accumulate(material, ck.CheckSettings(amplitude_route="mmk_modified"), states), [1, 2, 3]
    )
    assert modified.cyclic.sigma_m.tolist() == pytest.approx([0.0, 20.0, -20.0])
    # the overload cases at the tension node: F1 1 - 0,25 * 20/20, F3 with sigma_min 0,
    # F4 with sigma_max 40 (all on the Goodman line of Bild 6.29)
    case_1 = ck.check(ck.accumulate(material, ck.CheckSettings(overload_case=1), states), [1, 2, 3])
    assert case_1.cyclic.K_M[1][0] == pytest.approx(0.75)
    case_3 = ck.check(ck.accumulate(material, ck.CheckSettings(overload_case=3), states), [1, 2, 3])
    assert case_3.cyclic.K_M[1][0] == pytest.approx(0.8)
    case_4 = ck.check(ck.accumulate(material, ck.CheckSettings(overload_case=4), states), [1, 2, 3])
    assert case_4.cyclic.K_M[1][0] == pytest.approx((1.0 - 0.25 * 40.0 / 20.0) / 0.75)
    # fewer required cycles raise K_B and lower the utilisation
    short = ck.check(
        ck.accumulate(material, ck.CheckSettings(required_cycles=1.0e5), states), [1, 2, 3]
    )
    assert np.all(short.K_B > 1.0) and short.cyclic.a_B_V[1] < 1.25
    with pytest.raises(InputRangeError):
        ck.CheckSettings(overload_case=5)
    with pytest.raises(InputRangeError):
        ck.CheckSettings(amplitude_route="other")  # type: ignore[arg-type]
    history = ck.HistoryAccumulator(material, ck.CheckSettings(), 2)
    with pytest.raises(InputRangeError):
        history.add_state(np.zeros((3, 6)), label=1)
    with pytest.raises(InputRangeError):
        ck.check(
            ck.HistoryAccumulator(material, ck.CheckSettings(include_unloaded_state=False), 2),
            [1, 2],
        )


def test_limits_of_the_method_are_flagged(material: mt.StommelMaterial) -> None:
    """Stress above the isotherm (infinite strain), no strength left (infinite utilisation),
    the compression side without a Goodman limit, the life below 10^4 (review P1-1 to P1-3)."""
    # node 1 at 100 MPa: the 80 degC isotherm ends at 80 MPa, a_stat is infinite
    above = ck.check(ck.accumulate(material, ck.CheckSettings(), [_state(100.0)]), [1, 2, 3])
    assert math.isinf(above.a_stat[1]) and above.life_flags[1] == "immediate"
    # a near-hydrostatic compression: the mean stress exhausts the static strength, sigma_B = 0
    s = np.zeros((3, 6))
    s[1, :3] = (-120.0, -120.0, -110.0)
    exhausted = ck.check(ck.accumulate(material, ck.CheckSettings(), [s]), [1, 2, 3])
    # the cap 56 - 55 leaves 1 MPa to the first direction, nothing to the other two
    assert exhausted.cyclic.sigma_B[1].tolist() == pytest.approx([1.0, 0.0, 0.0])
    assert math.isinf(exhausted.cyclic.a_B_V[1])
    assert exhausted.life_flags[1] == "immediate" and exhausted.N_predicted[1] == 0.0
    # F2 without a Goodman limit: states -40 and -30 only, the cap governs
    settings = ck.CheckSettings(amplitude_route="signed_mises", include_unloaded_state=False)
    cap_only = ck.check(
        ck.accumulate(material, settings, [_state(-40.0), _state(-30.0)]), [1, 2, 3]
    )
    assert math.isinf(cap_only.cyclic.K_M[1])
    assert cap_only.cyclic.sigma_B[1] == pytest.approx(56.0 - 35.0)
    assert cap_only.cyclic.a_B_V[1] == pytest.approx(5.0 / 21.0)
    assert cap_only.a_stat[1] == pytest.approx((40.0 / 1.3 / 16.0) / 3.5)
    # tension 51,2 MPa: a_B,V 1,6 at N_G, the life falls below 10^4
    low = ck.check(ck.accumulate(material, ck.CheckSettings(), [_state(51.2)]), [1, 2, 3])
    assert low.cyclic.a_B_V[1] == pytest.approx(1.6)
    assert low.life_flags[1] == "below_1e4" and 1.0e3 < low.N_predicted[1] < 1.0e4


def test_check_folder_streams_the_positions(tmp_path: Path, material: mt.StommelMaterial) -> None:
    labels = (1, 2, 3)
    tension = np.zeros((3, 6))
    tension[1, 0] = 40.0
    compression = np.zeros((3, 6))
    compression[2, 2] = -40.0
    write_stress_file(tmp_path / "pos_001_stress.npz", labels=labels, values={"LOAD_8NM": tension})
    write_stress_file(
        tmp_path / "pos_002_stress.npz", labels=labels, values={"LOAD_8NM": compression}
    )
    write_stress_file(tmp_path / "pos_003_stress.npz", labels=labels, complete=(True, False))
    manifest = {
        "material_step": "W1",
        "positions": [
            {
                "index": i,
                "file": f"pos_00{i}.inp",
                "point": "",
                "from_A_mm": float(i),
                "rho_1_mm": 9.0,
            }
            for i in (1, 2, 3, 4)
        ],
    }
    folder = ck.check_folder(
        tmp_path, manifest, material, ck.CheckSettings(), step="LOAD_8NM", series="W1"
    )
    assert folder.positions_used == ("pos_001", "pos_002")
    assert folder.positions_skipped == (
        ("pos_003", "step LOAD_8NM broke off"),
        ("pos_004", "no stress file"),
    )
    assert folder.result.states == 3
    # node 2 (index 1) sees tension, node 3 compression: the same values as by hand
    assert folder.result.cyclic.a_B_V.tolist() == pytest.approx([0.0, 1.25, 0.75])
    assert folder.result.node_labels.tolist() == [1, 2, 3]
    with pytest.raises(InputRangeError):
        ck.check_folder(tmp_path, manifest, material, ck.CheckSettings(), step="SEAT", series="W3")
    # the component routes need the instance rotation of every file
    write_stress_file(
        tmp_path / "pos_002_stress.npz",
        labels=labels,
        values={"LOAD_8NM": compression},
        turn_known=False,
    )
    with pytest.raises(InputRangeError, match="instance rotation is unknown"):
        ck.check_folder(
            tmp_path,
            manifest,
            material,
            ck.CheckSettings(amplitude_route="mmk"),
            step="LOAD_8NM",
            series="W1",
        )
    unaffected = ck.check_folder(
        tmp_path,
        manifest,
        material,
        ck.CheckSettings(amplitude_route="signed_mises"),
        step="LOAD_8NM",
        series="W1",
    )
    assert unaffected.result.cyclic.a_B_V.tolist() == pytest.approx([0.0, 1.25, 0.75])
