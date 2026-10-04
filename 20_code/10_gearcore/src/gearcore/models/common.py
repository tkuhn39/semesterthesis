"""Shared model base, the pinion/wheel pair container and the field helper.

``FrozenModel`` is the base of every contract: immutable, no unknown fields, no NaN/inf anywhere
(``allow_inf_nan=False`` makes "every result is finite" a structural guarantee), whitespace-stripped
strings. ``F`` attaches machine-readable ``symbol``/``unit``/``source`` metadata to a field; it lands
in ``model_json_schema()`` so the later API/UI/AI layers can read units and norm references.
"""

import math
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Ranges the implementation is verified for (not physical limits). The input contracts and the
# orchestrators of the computational modules share them, so both reject the same inputs.
TEETH_RANGE: tuple[int, int] = (5, 1000)
PROFILE_SHIFT_RANGE: tuple[float, float] = (-2.0, 2.0)
NORMAL_MODULE_RANGE_MM: tuple[float, float] = (0.05, 100.0)
PRESSURE_ANGLE_RANGE_DEG: tuple[float, float] = (10.0, 30.0)
HELIX_ANGLE_RANGE_DEG: tuple[float, float] = (-45.0, 45.0)


class FrozenModel(BaseModel):
    """Immutable, strict base model for all gearcore contracts."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        allow_inf_nan=False,
        validate_assignment=True,
        str_strip_whitespace=True,
        ser_json_inf_nan="null",
    )


class Pair[T](FrozenModel):
    """A (pinion, wheel) value pair as an object, so the roles survive JSON and never swap.

    Gear 1 = pinion = the first value on an STplus line, gear 2 = wheel = the second value.
    """

    pinion: T
    wheel: T

    @model_validator(mode="after")
    def _finite(self) -> Self:
        """Bare ``Pair`` (T = Any) would bypass ``allow_inf_nan``; keep the guarantee (gate ADV0-16)."""
        for role, value in (("pinion", self.pinion), ("wheel", self.wheel)):
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"{role}: value must be finite, got {value!r}")
        return self

    def as_tuple(self) -> tuple[T, T]:
        return (self.pinion, self.wheel)

    @classmethod
    def same(cls, value: T) -> "Pair[T]":
        return cls(pinion=value, wheel=value)


class DimensionLimits(FrozenModel):
    """Nominal dimension and limits of an inspection dimension of the tooth thickness.

    DIN 21773:2014-08 §4 (p. 8): an equation of §5 to §13 gives the nominal dimension with the
    profile shift coefficient x, and the upper limit, the mean and the lower limit of the
    finished gear with x_Es, x_Em and x_Ei. For an external gear a thicker tooth has the larger
    dimension, so ``upper >= mean >= lower``; the nominal dimension lies above the upper limit
    where the upper allowance is negative.
    """

    nominal: float
    upper: float
    mean: float
    lower: float

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        slack = 1.0e-12 * max(abs(self.upper), abs(self.lower), 1.0)
        if not self.upper + slack >= self.mean >= self.lower - slack:
            raise ValueError(
                f"limits must be ordered upper >= mean >= lower, got {self.upper!r}, "
                f"{self.mean!r}, {self.lower!r}"
            )
        return self

    @classmethod
    def same(cls, value: float) -> "DimensionLimits":
        """A dimension without allowance: all four values are the nominal one."""
        return cls(nominal=value, upper=value, mean=value, lower=value)


class InputWarning(FrozenModel):
    """A soft finding about an input that is valid but unusual (never raised, always returned)."""

    code: str
    message: str
    field: str | None = None


def F(
    symbol: str,
    unit: str,
    description: str = "",
    *,
    source: str | None = None,
    **kwargs: Any,
) -> Any:
    """``pydantic.Field`` with ``symbol``/``unit``/``source`` in ``json_schema_extra``.

    Only for physical quantities. ``unit`` follows the field-name suffix convention (``mm``,
    ``deg``, ``um``, ``MPa``, ``-``); ``test_models.py::test_units_match_field_names`` enforces it.
    Name-like fields use a plain ``pydantic.Field``.
    """
    extra: dict[str, Any] = {"symbol": symbol, "unit": unit}
    if source is not None:
        extra["source"] = source
    return Field(description=description, json_schema_extra=extra, **kwargs)
