"""The S-Life Plastics fixture of E4 (built from the user's reports by `scripts/slife_reports.py`):
well-formed, the named nodes with three load cases, the arithmetic of the transcribed tables."""

from __future__ import annotations

import numpy as np
import pytest
import yaml

from gearcore.data import data_path

NODES = (5741, 6147, 41143, 41472)
CASES = ("8 Nm", "12 Nm", "16 Nm")


@pytest.fixture(scope="module")
def fixture() -> dict[str, object]:
    path = data_path("fatigue", "slife", "pos_C_W1_QS.yaml")
    data: dict[str, object] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data


def test_fixture_names_the_nodes_load_cases_and_provenance(fixture: dict[str, object]) -> None:
    nodes = fixture["nodes"]
    assert isinstance(nodes, dict)
    assert tuple(sorted(nodes)) == tuple(sorted(NODES))
    provenance = fixture["provenance"]
    assert isinstance(provenance, dict)
    for key in (
        "source",
        "result_file",
        "settings",
        "program",
        "K_RT_mpa",
        "A_S_min",
        "A_S_max",
        "f_tau",
    ):
        assert key in provenance
    assert provenance["K_RT_mpa"] == pytest.approx(115.51)
    assert provenance["A_S_min"] == pytest.approx(0.55)
    assert provenance["A_S_max"] == pytest.approx(0.70)
    for label in NODES:
        cases = nodes[label]["load_cases"]
        assert tuple(cases) == CASES
        assert [cases[c]["load_case"] for c in CASES] == ["LC1", "LC2", "LC3"]
        for c in CASES:
            assert cases[c]["element"] > 0  # the most severe element of the static check


@pytest.mark.parametrize("label", NODES)
@pytest.mark.parametrize("case", CASES)
def test_tensor_principal_values_and_ratios_are_consistent(
    fixture: dict[str, object], label: int, case: str
) -> None:
    nodes = fixture["nodes"]
    assert isinstance(nodes, dict)
    lc = nodes[label]["load_cases"][case]
    t = lc["tensor_mpa"]
    tensor = np.array(
        [
            [t["sx"], t["txy"], t["txz"]],
            [t["txy"], t["sy"], t["tyz"]],
            [t["txz"], t["tyz"], t["sz"]],
        ]
    )
    principal = np.linalg.eigvalsh(tensor)[::-1]
    assert principal == pytest.approx(np.array(lc["principal_mpa"]), abs=1.0e-6)
    # the static utilisation is the strain ratio of the first extremal state, unless another
    # criterion of the report is more severe (the compressive head node 5741)
    strain_ratio = lc["epsilon_eq_percent"] / lc["epsilon_allow_percent"]
    assert lc["a_stat"] >= strain_ratio - 0.02
    if label != 5741:
        assert lc["a_stat"] == pytest.approx(strain_ratio, rel=0.02)
    cyc = lc["cyclic"]
    assert cyc["sigma_WK_first_mpa"] == pytest.approx(20.12, abs=0.01)
    if cyc["table_complete"]:
        for a, applied, ratio in zip(
            cyc["sigma_a_mpa"], cyc["sigma_BK_applied_mpa"], cyc["a_BK_components"], strict=True
        ):
            if applied > 0.0:
                assert a / applied == pytest.approx(ratio, rel=0.02, abs=0.01)
        if cyc["sigma_BK_cap_mpa"] is not None:
            for cap, applied in zip(
                cyc["sigma_BK_cap_mpa"], cyc["sigma_BK_applied_mpa"], strict=True
            ):
                assert applied <= cap + 1.0e-6


def test_load_cases_scale_with_the_torque(fixture: dict[str, object]) -> None:
    nodes = fixture["nodes"]
    assert isinstance(nodes, dict)
    cases = nodes[6147]["load_cases"]
    s1 = [cases[c]["principal_mpa"][0] for c in CASES]
    assert s1[0] < s1[1] < s1[2]
