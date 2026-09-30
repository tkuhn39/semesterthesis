"""Input guards shared by the geometry modules (one definition, project rule 6)."""

import math

from gearcore._safe import EPS, finite_input, integer_input
from gearcore.errors import InputRangeError, NotSupportedError

HALF_PI = math.pi / 2.0


def teeth(z: int, what: str = "number of teeth z") -> int:
    """A number of teeth of an external gear: a positive integer."""
    number = integer_input(z, what)
    if number == 0:
        raise InputRangeError(f"{what} must not be zero")
    if number < 0:
        raise NotSupportedError("internal gears (z < 0) are a prepared extension point")
    return number


def helix(beta_rad: float) -> float:
    """A helix angle in radians with |beta| < 90 deg."""
    beta = finite_input(beta_rad, "helix angle beta")
    if abs(beta) >= HALF_PI - EPS:
        raise InputRangeError(f"helix angle |beta| must be < 90 deg, got {math.degrees(beta)!r}")
    return beta


def pressure_angle(alpha_rad: float, what: str) -> float:
    """A pressure or profile angle in radians in [0, 90 deg)."""
    alpha = finite_input(alpha_rad, what)
    if not 0.0 <= alpha < HALF_PI - EPS:
        raise InputRangeError(f"{what} must lie in [0, 90 deg), got {math.degrees(alpha)!r}")
    return alpha
