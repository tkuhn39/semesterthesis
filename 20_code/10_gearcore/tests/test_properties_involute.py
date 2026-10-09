"""Property-based invariants of the involute fundamentals (project rule 17).

Tolerances are a few units of the last place: the identities hold up to the rounding of the
operations involved, and a looser bound would hide a defect.
"""

import math
from collections.abc import Callable
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gearcore import involute as iv
from gearcore._safe import EPS
from gearcore.errors import GearCoreError, GeometryInfeasibleError
from gearcore.models.results import BasicGearGeometry

ULP = math.ulp(1.0)
angles = st.floats(1e-3, iv.INV_ALPHA_MAX_RAD)  # below 1e-3 rad: see the conditioning test
alpha_n = st.floats(math.radians(10.0), math.radians(30.0))
beta = st.floats(math.radians(-45.0), math.radians(45.0))
teeth = st.integers(5, 1000)
module = st.floats(0.05, 100.0)
shift = st.floats(-2.0, 2.0)
anything = st.one_of(
    st.floats(allow_nan=True, allow_infinity=True),
    st.integers(-(10**400), 10**400),
    st.booleans(),
    st.none(),
    st.text(max_size=3),
)


def inverse_bound(alpha: float) -> float:
    tangent = math.tan(alpha)
    return 8.0 * math.ulp(tangent) / (tangent * tangent) + 1.0e-15


@given(angles)
def test_inverse_involute_round_trip(alpha: float) -> None:
    assert abs(iv.inv_inverse(iv.inv(alpha)) - alpha) <= inverse_bound(alpha)


@given(st.floats(0.0, iv.INV_MAX))
def test_inverse_involute_is_a_right_inverse(value: float) -> None:
    alpha = iv.inv_inverse(value)
    assert 0.0 <= alpha <= iv.INV_ALPHA_MAX_RAD
    tangent = math.tan(alpha)
    # residual at the rounding level of tan, or a Newton step below the spacing of alpha
    assert abs(iv.inv(alpha) - value) <= 4.0 * math.ulp(tangent) + 4.0e-16 * tangent * tangent


@given(anything)
def test_inverse_involute_never_returns_garbage(value: object) -> None:
    try:
        alpha = iv.inv_inverse(value)  # type: ignore[arg-type]
    except GearCoreError:
        return
    assert isinstance(alpha, float) and 0.0 <= alpha <= iv.INV_ALPHA_MAX_RAD


@given(teeth, module, alpha_n, beta)
def test_base_diameter_forms_19_and_20_agree(z: int, m_n: float, a_n: float, b: float) -> None:
    beta_b = iv.base_helix_angle(b, a_n)
    eq20 = z * m_n * math.cos(a_n) / math.cos(beta_b)
    assert iv.base_diameter(z, m_n, a_n, b) == pytest.approx(eq20, rel=8 * ULP)
    assert iv.base_diameter(z, m_n, a_n, b) < iv.reference_diameter(z, m_n, b)
    assert abs(beta_b) <= abs(b) and math.copysign(1.0, beta_b) == math.copysign(1.0, b)


@given(teeth, module, alpha_n, beta, shift)
def test_basic_geometry_is_finite_consistent_and_serialisable(
    z: int, m_n: float, a_n: float, b: float, x: float
) -> None:
    result = iv.compute_basic_gear_geometry(
        number_of_teeth=z,
        normal_module_mm=m_n,
        normal_pressure_angle_deg=math.degrees(a_n),
        helix_angle_deg=math.degrees(b),
        profile_shift_coefficient=x,
    )
    for name in type(result).model_fields:
        if name != "warnings":
            value = getattr(result, name)
            assert isinstance(value, int | float) and math.isfinite(value)
    pitch = math.pi * result.transverse_module_mm
    assert result.transverse_tooth_thickness_mm + result.transverse_space_width_mm == pytest.approx(
        pitch, rel=4 * ULP
    )
    assert result.normal_tooth_thickness_mm + result.normal_space_width_mm == pytest.approx(
        math.pi * m_n, rel=4 * ULP
    )
    assert (
        result.tooth_thickness_half_angle_deg + result.space_width_half_angle_deg
        == pytest.approx(180.0 / z, rel=4 * ULP)
    )
    codes = {warning.code for warning in result.warnings}
    assert ("no_tooth_at_reference_cylinder" in codes) == (result.normal_tooth_thickness_mm <= 0.0)
    assert ("no_space_at_reference_cylinder" in codes) == (result.normal_space_width_mm <= 0.0)
    restored = BasicGearGeometry.model_validate_json(result.model_dump_json())
    assert restored == result and hash(restored) == hash(result)


@given(teeth, module, alpha_n, beta, shift)
def test_helix_sign_changes_nothing_but_the_sign(
    z: int, m_n: float, a_n: float, b: float, x: float
) -> None:
    arguments = {
        "number_of_teeth": z,
        "normal_module_mm": m_n,
        "normal_pressure_angle_deg": math.degrees(a_n),
        "profile_shift_coefficient": x,
    }
    plus = iv.compute_basic_gear_geometry(helix_angle_deg=abs(math.degrees(b)), **arguments)  # type: ignore[arg-type]
    minus = iv.compute_basic_gear_geometry(helix_angle_deg=-abs(math.degrees(b)), **arguments)  # type: ignore[arg-type]
    for name in type(plus).model_fields:
        if name in {"helix_angle_deg", "base_helix_angle_deg"}:
            assert getattr(minus, name) == -getattr(plus, name)
        else:
            assert getattr(minus, name) == getattr(plus, name)


@given(teeth, module, alpha_n, beta, shift, st.floats(1.0, 1.5))
def test_tooth_and_space_half_angles_sum_to_the_pitch_angle(
    z: int, m_n: float, a_n: float, b: float, x: float, factor: float
) -> None:
    """Holds on both sides of the pointed tooth: Eq. (40) raises there, Eq. (45) keeps its sign."""
    d_b = iv.base_diameter(z, m_n, a_n, b)
    alpha_t = iv.transverse_pressure_angle(a_n, b)
    alpha_yt = iv.transverse_profile_angle_at(factor * d_b, d_b)
    psi = iv.tooth_thickness_half_angle(z, x, a_n)
    eta = iv.space_width_half_angle(z, x, a_n)
    eta_y = iv.space_width_half_angle_at(eta, alpha_t, alpha_yt)
    pitch_angle = math.pi / z
    # each involute value is accurate to one ulp of its tangent, not of the pitch angle
    noise = 8.0 * math.ulp(math.tan(alpha_yt)) + 8.0 * math.ulp(math.tan(alpha_t)) + 4 * ULP
    try:
        psi_y = iv.tooth_thickness_half_angle_at(psi, alpha_t, alpha_yt)
    except GeometryInfeasibleError:
        assert eta_y > pitch_angle, "beyond the pointed tooth the space is wider than the pitch"
        return
    assert psi_y >= 0.0
    assert abs(psi_y + eta_y - pitch_angle) <= noise + EPS * (psi_y == 0.0)


@given(teeth, module, alpha_n, beta)
def test_helix_angle_grows_with_the_diameter(z: int, m_n: float, a_n: float, b: float) -> None:
    d = iv.reference_diameter(z, m_n, b)
    inner = abs(iv.helix_angle_at(0.9 * d, d, b))
    outer = abs(iv.helix_angle_at(1.1 * d, d, b))
    assert inner <= abs(b) <= outer
    assert iv.helix_angle_at(d, d, b) == pytest.approx(b, abs=ULP)


@given(st.floats(1e-3, 1e4), st.floats(1e-12, 0.5))
def test_base_circle_is_treated_alike_by_eq_12_and_eq_17(d_b: float, offset: float) -> None:
    """Both equations accept and reject the same diameters around the base circle."""
    for d_y in (d_b, d_b * (1.0 + offset), d_b * (1.0 - offset), math.nextafter(d_b, 0.0)):
        outcomes: list[bool | None] = []
        for function in (iv.transverse_profile_angle_at, iv.radius_of_curvature):
            try:
                outcomes.append(function(d_y, d_b) >= 0.0)
            except GeometryInfeasibleError:
                outcomes.append(None)
        assert outcomes[0] == outcomes[1], (d_y, d_b, outcomes)
        if d_y >= d_b:
            assert outcomes == [True, True]


@given(anything, anything, anything, anything, anything)
def test_orchestrator_returns_a_valid_result_or_a_typed_error(
    z: object, m_n: object, a_n: object, b: object, x: object
) -> None:
    try:
        result = iv.compute_basic_gear_geometry(
            number_of_teeth=z,  # type: ignore[arg-type]
            normal_module_mm=m_n,  # type: ignore[arg-type]
            normal_pressure_angle_deg=a_n,  # type: ignore[arg-type]
            helix_angle_deg=b,  # type: ignore[arg-type]
            profile_shift_coefficient=x,  # type: ignore[arg-type]
        )
    except GearCoreError:
        return
    assert 5 <= result.number_of_teeth <= 1000 and 0.05 <= result.normal_module_mm <= 100.0
    assert 10.0 <= result.normal_pressure_angle_deg <= 30.0 and abs(result.helix_angle_deg) <= 45.0
    assert abs(result.profile_shift_coefficient) <= 2.0


# the guards are probed with arbitrary values, so the lambdas take anything
SINGLE_FUNCTIONS: tuple[Callable[[Any, Any, Any], float], ...] = (
    lambda a, b, c: iv.transverse_module(a, b),
    lambda a, b, c: iv.reference_diameter(a, b, c),
    lambda a, b, c: iv.transverse_pressure_angle(a, b),
    lambda a, b, c: iv.base_helix_angle(a, b),
    lambda a, b, c: iv.helix_angle_at(a, b, c),
    lambda a, b, c: iv.transverse_profile_angle_at(a, b),
    lambda a, b, c: iv.normal_profile_angle_at(a, b),
    lambda a, b, c: iv.roll_angle(a),
    lambda a, b, c: iv.radius_of_curvature(a, b),
    lambda a, b, c: iv.inv(a),
    lambda a, b, c: iv.tooth_thickness_half_angle(a, b, c),
    lambda a, b, c: iv.tooth_thickness_half_angle_at(a, b, c),
    lambda a, b, c: iv.base_tooth_thickness_half_angle(a, b),
    lambda a, b, c: iv.transverse_tooth_thickness(a, b, c, 0.1),
    lambda a, b, c: iv.transverse_tooth_thickness_at(a, b),
    lambda a, b, c: iv.space_width_half_angle(a, b, c),
    lambda a, b, c: iv.space_width_half_angle_at(a, b, c),
    lambda a, b, c: iv.base_space_width_half_angle(a, b),
    lambda a, b, c: iv.transverse_space_width(a, b, c, 0.1),
    lambda a, b, c: iv.transverse_space_width_at(a, b),
    lambda a, b, c: iv.normal_tooth_thickness(a, b, c),
    lambda a, b, c: iv.normal_tooth_thickness_at(a, b),
    lambda a, b, c: iv.normal_space_width(a, b, c),
    lambda a, b, c: iv.normal_space_width_at(a, b),
    lambda a, b, c: iv.base_diameter(a, b, c, 0.1),
)


@given(anything, anything, anything)
def test_every_function_returns_a_finite_float_or_a_typed_error(
    a: object, b: object, c: object
) -> None:
    assert len(SINGLE_FUNCTIONS) == 25, "26 traced functions; inv_inverse has its own property"
    for function in SINGLE_FUNCTIONS:
        try:
            value = function(a, b, c)
        except GearCoreError:
            continue
        assert isinstance(value, float) and math.isfinite(value)
