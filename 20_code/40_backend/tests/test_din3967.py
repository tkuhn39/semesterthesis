"""
@module: tests.test_din3967
@context: Domain-layer tests — DIN 3967:1978 tooth-thickness allowance tables.
@role: The transcribed Tables 1/2 reproduce the norm's own worked example (designation
       27cd at d = 100 mm), the diameter-range boundaries follow the über/bis semantics,
       and the series flow through the geometry-report request as an input alternative
       to direct span allowances.
"""

import math

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.geometry.din3967 import allowances_um, tolerance_um, upper_allowance_um

client = TestClient(create_app())


def test_norm_example_27cd() -> None:
    """DIN 3967 §3.1 example: '27cd' at d = 100 mm → E_sns = −70 µm, E_sni = −170 µm."""
    e_sns, e_sni = allowances_um(100.0, "cd", 27)
    assert e_sns == -70.0
    assert e_sni == -170.0


def test_range_boundaries_and_series_ends() -> None:
    # über/bis: d = 10 belongs to the FIRST row, d just above to the second
    assert upper_allowance_um(10.0, "a") == -100.0
    assert upper_allowance_um(10.001, "a") == -135.0
    assert upper_allowance_um(50.0, "cd") == -54.0
    assert upper_allowance_um(10000.0, "a") == -2000.0
    # series h is the zero-allowance series everywhere
    for d in (5.0, 100.0, 9000.0):
        assert upper_allowance_um(d, "h") == 0.0
    assert tolerance_um(5.0, 21) == 3.0
    assert tolerance_um(10000.0, 30) == 2400.0


def test_invalid_inputs_raise() -> None:
    with pytest.raises(ValueError, match="allowance series"):
        upper_allowance_um(100.0, "x")
    with pytest.raises(ValueError, match="tolerance series"):
        tolerance_um(100.0, 20)
    with pytest.raises(ValueError, match="exceeds"):
        upper_allowance_um(20000.0, "cd")


def test_series_flow_through_geometry_report() -> None:
    """A DIN 3967 designation on the request yields the exact E_sn values in the report
    (the A_W = E_sn·cos α_n conversion round-trips through the SSOT service)."""
    free_stage = {
        "use_example": False,
        "normal_module_mm": 2.0,
        "teeth_pinion": 20,
        "teeth_wheel": 41,
        "profile_shift_pinion": 0.3,
        "profile_shift_wheel": 0.1,
        "face_width_pinion_mm": 20.0,
        "face_width_wheel_mm": 20.0,
    }
    res = client.post(
        "/api/geometry/report",
        json={
            "stage": free_stage,
            "allowance_series_gear1": "cd",
            "tolerance_series_gear1": 25,
            "allowance_series_gear2": "cd",
            "tolerance_series_gear2": 25,
        },
    )
    assert res.status_code == 200
    body = res.json()
    # gear 1: d = 40 mm (10 < d ≤ 50): E_sns = −54 µm, T_sn(25) = 30 µm → E_sni = −84 µm
    assert body["gear1"]["thickness_allowance_upper_mm"] == pytest.approx(-0.054, abs=1e-6)
    assert body["gear1"]["thickness_allowance_lower_mm"] == pytest.approx(-0.084, abs=1e-6)
    # gear 2: d = 82 mm (50 < d ≤ 125): E_sns = −70 µm, T_sn(25) = 40 µm → E_sni = −110 µm
    assert body["gear2"]["thickness_allowance_upper_mm"] == pytest.approx(-0.070, abs=1e-6)
    assert body["gear2"]["thickness_allowance_lower_mm"] == pytest.approx(-0.110, abs=1e-6)
    # the backlash chain runs off the series values (both flanks thinned → positive play)
    j_n = body["pair"]["backlash_normal_mm"]
    cos_an = math.cos(math.radians(20.0))
    assert j_n == pytest.approx((0.054 + 0.070) * cos_an, abs=1e-6)
    # direct µm input wins over the series when both are present
    res2 = client.post(
        "/api/geometry/report",
        json={
            "stage": free_stage,
            "allowance_series_gear1": "cd",
            "tolerance_series_gear1": 25,
            "allowance_series_gear2": "cd",
            "tolerance_series_gear2": 25,
            "span_allowance_upper_um": [-100.0, -100.0],
            "span_allowance_lower_um": [-150.0, -150.0],
        },
    )
    assert res2.status_code == 200
    assert res2.json()["gear1"]["span_allowance_upper_mm"] == pytest.approx(-0.1, abs=1e-9)
