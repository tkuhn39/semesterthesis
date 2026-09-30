"""Basic rack tooth profile contract (DIN ISO 21771:2014-08 Bild 4; DIN 867:1986-02; ISO 53:1998).

Pure data: the geometric admissibility of the fillet radius (DIN 867 Eq. (7)/(8), ISO 53 Eq.
(2)/(3)) is checked by ``gearcore.rack.validate_basic_rack`` so that models stay free of
computational imports. Names, symbols and designations come from the quantity registry.
"""

from typing import ClassVar, Self

from pydantic import Field, model_validator

from gearcore.models.common import FrozenModel
from gearcore.quantities import Q


class BasicRackProfile(FrozenModel):
    """Basic rack of a cylindrical gear; factors refer to the module (``*`` in the norms)."""

    QUANTITY_PREFIX: ClassVar[str] = "basic_rack_"

    name: str = Field(min_length=1, description="designation, e.g. 'ISO 53 type A'")
    source: str = Field(min_length=1, description="key in sources.yaml of the defining norm")
    profile_angle_deg: float = Q("basic_rack_profile_angle", ge=10.0, le=30.0)
    addendum_factor: float = Q("basic_rack_addendum", factor=True, gt=0.0, le=2.0)
    dedendum_factor: float = Q("basic_rack_dedendum", factor=True, gt=0.0, le=2.5)
    bottom_clearance_factor: float = Q("basic_rack_bottom_clearance", factor=True, ge=0.0, le=1.0)
    fillet_radius_factor: float = Q("basic_rack_fillet_radius", factor=True, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _clearance_is_dedendum_minus_addendum(self) -> Self:
        """DIN 867:1986 §4.3: c_P is the difference between h_fP and h_aP of the mating profile."""
        expected = self.dedendum_factor - self.addendum_factor
        if abs(self.bottom_clearance_factor - expected) > 1e-9:
            raise ValueError(
                f"bottom clearance factor {self.bottom_clearance_factor} must equal "
                f"h_fP* - h_aP* = {expected:.9f}"
            )
        return self
