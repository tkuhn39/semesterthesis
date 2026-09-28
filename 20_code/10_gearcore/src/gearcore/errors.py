"""Typed error hierarchy.

Rule 7 of ``project_rules.md``: unsupported or infeasible inputs raise one of these classes;
functions never return ``None`` or a placeholder for "could not compute", and no ``try/except``
wraps mathematics. The mixin bases (``ValueError`` etc.) keep the classes catchable by generic
callers without losing the specific type.
"""


class GearCoreError(Exception):
    """Base class of every error raised by gearcore."""


class InputRangeError(GearCoreError, ValueError):
    """An input lies outside the range the norm or the implementation supports."""


class GeometryInfeasibleError(GearCoreError, ValueError):
    """Inputs are individually valid but describe no realisable gear (e.g. a < a_min, d_y < d_b)."""


class SolverError(GearCoreError, ArithmeticError):
    """A numerical solver left its domain or did not converge."""


class NotSupportedError(GearCoreError, NotImplementedError):
    """A prepared extension point (internal gear, shaper tool, ...) is not implemented yet."""


class ParseError(GearCoreError, ValueError):
    """An STplus file (.ste, .sta, contour export) does not match the expected grammar."""
