"""Result contracts. Names, symbols and designations come from the quantity registry."""

from gearcore.models.common import (
    HELIX_ANGLE_RANGE_DEG,
    NORMAL_MODULE_RANGE_MM,
    PRESSURE_ANGLE_RANGE_DEG,
    PROFILE_SHIFT_RANGE,
    TEETH_RANGE,
    FrozenModel,
    InputWarning,
    Pair,
)
from gearcore.models.inputs import PairInput
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


class PairGeometry(FrozenModel):
    """Mating quantities of an external gear pair (DIN ISO 21771:2014-08 §5).

    ``profile_shift_coefficient`` and ``centre_distance_mm`` are the resolved values: two of a_w,
    x_1, x_2 are given, the third follows (ADR-107). ``gears`` holds the single-gear quantities
    with the resolved profile shift; the helix angle of the wheel has the opposite sign.
    Quantities per gear are written for that gear: ``length_of_addendum_path_of_contact_mm`` is
    g_a1 (Eq. (80)) and g_a2 = g_f1 (Eq. (79)); ``sliding_factor_at_tip`` is K_ga (Eq. (113)) for
    the pinion and the norm's K_gf (Eq. (112)) for the wheel; ``specific_sliding_at_end_points``
    is zeta_f1 (Eq. (116)) and zeta_f2 (Eq. (117)), the values at the root of each gear.
    ``root_form_diameter_mm`` holds the root form diameters the mesh was computed with (the
    optional input, a value within rounding noise below the base circle taken as the base
    circle); without it ``warnings`` says that the limit of the active profile by the root form
    circle was not applied. ``inputs`` is the pair as the contract validated it.
    ``common_tooth_depth_mm`` is Eq. (59) evaluated with the tip form circles instead of the tip
    circles (user decision, ADR-112); where the two differ, ``warnings`` names the value of the
    tip circles.
    """

    inputs: PairInput
    gears: Pair[BasicGearGeometry]
    gear_ratio: float = Q("gear_ratio", equation=f"{_SRC} (52)", ge=1.0)
    centre_distance_mm: float = Q("centre_distance", equation=f"{_SRC} (54)", gt=0.0)
    transverse_working_pressure_angle_deg: float = Q(
        "transverse_working_pressure_angle", equation=f"{_SRC} (54), (55)", ge=0.0, lt=90.0
    )
    profile_shift_coefficient: Pair[float] = Q("profile_shift_coefficient")
    sum_of_profile_shift_coefficients: float = Q(
        "sum_of_profile_shift_coefficients", equation=f"x_1 + x_2 of the result; {_SRC} §5.3"
    )
    working_pitch_diameter_mm: Pair[float] = Q(
        "working_pitch_diameter", equation=f"{_SRC} (56), (57)"
    )
    tip_diameter_mm: Pair[float] = Q("tip_diameter")
    tip_form_diameter_mm: Pair[float] = Q(
        "tip_form_diameter", equation=f"{_SRC} (127), or given by the generation"
    )
    active_tip_diameter_mm: Pair[float] = Q("active_tip_diameter", equation=f"{_SRC} (68), (69)")
    sap_diameter_mm: Pair[float] = Q("sap_diameter", equation=f"{_SRC} (64) to (67)")
    root_form_diameter_mm: Pair[float] | None = Q("root_form_diameter", default=None)
    common_tooth_depth_mm: float = Q(
        "common_tooth_depth", equation=f"{_SRC} (59), with the tip form diameters (ADR-112)"
    )
    normal_pitch_mm: float = Q("normal_pitch", equation=f"{_SRC} (24)", gt=0.0)
    transverse_pitch_mm: float = Q("transverse_pitch", equation=f"{_SRC} (23)", gt=0.0)
    transverse_base_pitch_mm: float = Q("transverse_base_pitch", equation=f"{_SRC} (28)", gt=0.0)
    transverse_contact_pitch_mm: float = Q(
        "transverse_contact_pitch", equation=f"{_SRC} (30)", gt=0.0
    )
    contact_face_width_mm: float = Q("contact_face_width", gt=0.0)
    length_of_path_of_contact_mm: float = Q(
        "length_of_path_of_contact", equation=f"{_SRC} (77)", gt=0.0
    )
    length_of_addendum_path_of_contact_mm: Pair[float] = Q(
        "length_of_addendum_path_of_contact", equation=f"{_SRC} (80), (79)"
    )
    transverse_contact_ratio: float = Q("transverse_contact_ratio", equation=f"{_SRC} (90)", gt=0.0)
    overlap_ratio: float = Q("overlap_ratio", equation=f"{_SRC} (93)", ge=0.0)
    total_contact_ratio: float = Q("total_contact_ratio", equation=f"{_SRC} (97)", gt=0.0)
    sliding_factor_at_tip: Pair[float] = Q("sliding_factor_at_tip", equation=f"{_SRC} (113), (112)")
    specific_sliding_at_end_points: Pair[float] = Q(
        "specific_sliding_at_end_points", equation=f"{_SRC} (116), (117)"
    )
    warnings: tuple[InputWarning, ...] = ()
