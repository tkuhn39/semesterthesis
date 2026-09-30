"""Domain-checked elementary operations.

Every function raises a typed error naming the quantity (``what``) instead of clamping, returning
NaN or letting ``math`` raise a bare ``ValueError``. Floating-point noise within ``EPS`` of a domain
boundary is folded onto the boundary — that is the only tolerance applied here, and it is tested.
"""

import math
import numbers
import sys

from gearcore.errors import GeometryInfeasibleError, InputRangeError, SolverError

EPS = 1e-12
"""Rounding tolerance at exact domain boundaries (e.g. ``cos alpha = 1 + 2e-16``)."""

MAX_EXACT_INTEGER = 2**53
"""Largest magnitude up to which every integer is a binary64 number."""


def finite_input(value: float, what: str) -> float:
    """Return a caller-supplied real number as binary64 ``float``.

    ``bool``, strings, ``None``, NaN, inf and integers beyond the binary64 range are input errors;
    integers and numpy scalars are converted (the conversion of a 32-bit float is exact).
    """
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise InputRangeError(f"{what} must be a finite number, got {value!r}")
    if isinstance(value, numbers.Integral):
        if abs(int(value)) > sys.float_info.max:
            raise InputRangeError(f"{what} exceeds the range of a floating-point number")
        return float(int(value))
    if not isinstance(value, float) and not hasattr(value, "dtype"):
        raise InputRangeError(f"{what} must be a float or an integer, got {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise InputRangeError(f"{what} must be a finite number, got {value!r}")
    return number


def positive_input(value: float, what: str) -> float:
    """A finite input that must be strictly positive (module, diameter, ...)."""
    number = finite_input(value, what)
    if number <= 0.0:
        raise InputRangeError(f"{what} must be > 0, got {value!r}")
    return number


def integer_input(value: int, what: str) -> int:
    """A caller-supplied integer (``bool`` and floats are rejected, numpy integers accepted)."""
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise InputRangeError(f"{what} must be an integer, got {value!r}")
    number = int(value)
    if abs(number) > MAX_EXACT_INTEGER:
        raise InputRangeError(f"{what} exceeds 2^53, the range of exactly representable integers")
    return number


def finite_result(value: float, what: str) -> float:
    """Return a computed value; inf or NaN means the inputs left the representable range."""
    if not math.isfinite(value):
        raise InputRangeError(
            f"{what}: the result is not a finite number, the inputs exceed the representable range"
        )
    return value


def require_finite(value: float, *, what: str) -> float:
    """Return ``value`` if it is a finite float, else raise ``SolverError``."""
    if not math.isfinite(value):
        raise SolverError(f"{what}: value is not finite ({value!r})")
    return value


def safe_acos(x: float, *, what: str) -> float:
    """``acos(x)`` with the domain check ``-1 <= x <= 1`` (± EPS)."""
    require_finite(x, what=what)
    if x > 1.0 + EPS or x < -1.0 - EPS:
        raise GeometryInfeasibleError(f"{what}: acos argument {x!r} lies outside [-1, 1]")
    return math.acos(min(1.0, max(-1.0, x)))


def safe_asin(x: float, *, what: str) -> float:
    """``asin(x)`` with the domain check ``-1 <= x <= 1`` (± EPS)."""
    require_finite(x, what=what)
    if x > 1.0 + EPS or x < -1.0 - EPS:
        raise GeometryInfeasibleError(f"{what}: asin argument {x!r} lies outside [-1, 1]")
    return math.asin(min(1.0, max(-1.0, x)))


def safe_sqrt(x: float, *, what: str) -> float:
    """``sqrt(x)`` for ``x >= 0`` (negative noise within EPS is treated as zero)."""
    require_finite(x, what=what)
    if x < -EPS:
        raise GeometryInfeasibleError(f"{what}: square root of a negative number ({x!r})")
    return math.sqrt(max(0.0, x))


def safe_div(numerator: float, denominator: float, *, what: str) -> float:
    """``numerator / denominator`` with a check against a (near-)zero denominator."""
    require_finite(numerator, what=what)
    require_finite(denominator, what=what)
    if abs(denominator) <= EPS:
        raise GeometryInfeasibleError(f"{what}: division by zero (denominator {denominator!r})")
    return numerator / denominator


def safe_tan(angle_rad: float, *, what: str) -> float:
    """``tan(angle)`` rejecting angles at which the tangent is unbounded."""
    require_finite(angle_rad, what=what)
    if abs(math.cos(angle_rad)) <= EPS:
        raise GeometryInfeasibleError(f"{what}: tangent undefined at {angle_rad!r} rad")
    return math.tan(angle_rad)
