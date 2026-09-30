"""Result contracts. Names, symbols and designations come from the quantity registry."""

from gearcore.models.common import (
    HELIX_ANGLE_RANGE_DEG,
    NORMAL_MODULE_RANGE_MM,
    PRESSURE_ANGLE_RANGE_DEG,
    PROFILE_SHIFT_RANGE,
    TEETH_RANGE,
    FrozenModel,
    InputWarning,
)
from gearcore.quantities import Q

_SRC = "ISO21771:2014"


class BasicGearGeometry(FrozenModel):
    """Reference/base quantities and nominal tooth thickness of one external gear (DIN ISO 21771 §4).

    Thickness, space width and their half angles at the reference cylinder are the signed values
    of the norm equations. A value <= 0 means that the reference cylinder lies outside the toothed
    zone (possible for large |x| together with a large pressure angle); ``warnings`` names it.
    Whether the gear can be generated is decided by the generation module, not here.
    """

    number_of_teeth: int = Q("number_of_teeth", ge=TEETH_RANGE[0], le=TEETH_RANGE[1], strict=True)
    normal_module_mm: float = Q(
        "normal_module", ge=NORMAL_MODULE_RANGE_MM[0], le=NORMAL_MODULE_RANGE_MM[1]
    )
    normal_pressure_angle_deg: float = Q(
        "normal_pressure_angle", ge=PRESSURE_ANGLE_RANGE_DEG[0], le=PRESSURE_ANGLE_RANGE_DEG[1]
    )
    helix_angle_deg: float = Q(
        "helix_angle", ge=HELIX_ANGLE_RANGE_DEG[0], le=HELIX_ANGLE_RANGE_DEG[1]
    )
    profile_shift_coefficient: float = Q(
        "profile_shift_coefficient", ge=PROFILE_SHIFT_RANGE[0], le=PROFILE_SHIFT_RANGE[1]
    )
    transverse_module_mm: float = Q("transverse_module", equation=f"{_SRC} (2)", gt=0.0)
    transverse_pressure_angle_deg: float = Q(
        "transverse_pressure_angle", equation=f"{_SRC} (14)", gt=0.0, lt=90.0
    )
    base_helix_angle_deg: float = Q("base_helix_angle", equation=f"{_SRC} (6)", gt=-90.0, lt=90.0)
    reference_diameter_mm: float = Q("reference_diameter", equation=f"{_SRC} (1)", gt=0.0)
    base_diameter_mm: float = Q("base_diameter", equation=f"{_SRC} (19)", gt=0.0)
    transverse_tooth_thickness_mm: float = Q("transverse_tooth_thickness", equation=f"{_SRC} (39)")
    normal_tooth_thickness_mm: float = Q("normal_tooth_thickness", equation=f"{_SRC} (49)")
    transverse_space_width_mm: float = Q("transverse_space_width", equation=f"{_SRC} (44)")
    normal_space_width_mm: float = Q("normal_space_width", equation=f"{_SRC} (51)")
    tooth_thickness_half_angle_deg: float = Q("tooth_thickness_half_angle", equation=f"{_SRC} (41)")
    space_width_half_angle_deg: float = Q("space_width_half_angle", equation=f"{_SRC} (46)")
    base_tooth_thickness_half_angle_deg: float = Q(
        "base_tooth_thickness_half_angle", equation=f"{_SRC} (42)"
    )
    base_space_width_half_angle_deg: float = Q(
        "base_space_width_half_angle", equation=f"{_SRC} (47)"
    )
    warnings: tuple[InputWarning, ...] = ()
