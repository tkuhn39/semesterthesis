import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gearcore._safe import EPS, safe_acos, safe_asin, safe_div, safe_sqrt, safe_tan
from gearcore.errors import GeometryInfeasibleError, SolverError


@given(st.floats(min_value=-1.0, max_value=1.0))
def test_acos_asin_inside_domain_match_math(x: float) -> None:
    assert safe_acos(x, what="t") == math.acos(x)
    assert safe_asin(x, what="t") == math.asin(x)


@pytest.mark.parametrize("x", [1.0 + EPS / 2, -1.0 - EPS / 2])
def test_acos_folds_rounding_noise_onto_boundary(x: float) -> None:
    assert safe_acos(x, what="t") == math.acos(max(-1.0, min(1.0, x)))


@pytest.mark.parametrize("x", [1.0 + 2 * EPS, -1.0 - 2 * EPS, 2.0, -7.0])
def test_acos_outside_domain_raises_typed_error(x: float) -> None:
    with pytest.raises(GeometryInfeasibleError, match="acos"):
        safe_acos(x, what="cos alpha_wt")


@pytest.mark.parametrize("x", [math.nan, math.inf, -math.inf])
def test_non_finite_raises_solver_error(x: float) -> None:
    with pytest.raises(SolverError):
        safe_acos(x, what="t")
    with pytest.raises(SolverError):
        safe_sqrt(x, what="t")


def test_sqrt_negative_noise_is_zero_but_real_negative_raises() -> None:
    assert safe_sqrt(-EPS / 2, what="t") == 0.0
    with pytest.raises(GeometryInfeasibleError, match="negative"):
        safe_sqrt(-1e-9, what="t")


@given(st.floats(min_value=1e-6, max_value=1e6), st.floats(min_value=1e-6, max_value=1e6))
def test_div_matches_python_division(a: float, b: float) -> None:
    assert safe_div(a, b, what="t") == a / b


def test_div_by_zero_raises_typed_error() -> None:
    with pytest.raises(GeometryInfeasibleError, match="division by zero"):
        safe_div(1.0, 0.0, what="d_b / z")


def test_tan_at_pi_half_raises() -> None:
    with pytest.raises(GeometryInfeasibleError, match="tangent"):
        safe_tan(math.pi / 2, what="t")
    assert safe_tan(0.3, what="t") == math.tan(0.3)
