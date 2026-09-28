"""Shared model base, the pinion/wheel pair container and the field helper.

``FrozenModel`` is the base of every contract: immutable, no unknown fields, no NaN/inf anywhere
(``allow_inf_nan=False`` makes "every result is finite" a structural guarantee), whitespace-stripped
strings. ``F`` attaches machine-readable ``symbol``/``unit``/``source`` metadata to a field; it lands
in ``model_json_schema()`` so the later API/UI/AI layers can read units and norm references.
"""

import math
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
