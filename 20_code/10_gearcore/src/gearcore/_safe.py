"""Domain-checked elementary operations.

Every function raises a typed error naming the quantity (``what``) instead of clamping, returning
NaN or letting ``math`` raise a bare ``ValueError``. Floating-point noise within ``EPS`` of a domain
boundary is folded onto the boundary — that is the only tolerance applied here, and it is tested.
"""

import math

from gearcore.errors import GeometryInfeasibleError, SolverError

EPS = 1e-12
"""Rounding tolerance at exact domain boundaries (e.g. ``cos alpha = 1 + 2e-16``)."""


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
