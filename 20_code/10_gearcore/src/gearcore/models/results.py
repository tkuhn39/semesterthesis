"""Result contracts. Names, symbols and designations come from the quantity registry."""

from gearcore.models.common import (
    HELIX_ANGLE_RANGE_DEG,
    NORMAL_MODULE_RANGE_MM,
    PRESSURE_ANGLE_RANGE_DEG,
    PROFILE_SHIFT_RANGE,
    TEETH_RANGE,
    DimensionLimits,
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


_OLD = "DIN3960:1987"


class GearGeneration(FrozenModel):
    """What a rack-type tool generates on one external gear (DIN ISO 21771:2014-08 §7; DIN 3960
    Anhang A for the edge break flank of the tool).

    The tool quantities are the absolute values used (factors times the normal module). The
    generation is evaluated at the upper tooth thickness allowance, ``generating_profile_shift_
    coefficient`` = x_Es (maximum material); x_Ei and the root diameter at x_Ei are reported
    alongside. Without an allowance x_E = x (the nominal tooth thickness) and ``warnings`` says so.

    ``root_form_diameter_mm`` is Eq. (128) (Anhang NB) where the gear is free of undercut, else
    the intersection of the fillet generated by the tool tip rounding with the involute (§7.6,
    numerical, ``gearcore.trochoid``); ``undercut`` says which, ``min_generating_profile_shift_
    coefficient`` is the limit of Eq. (135).

    ``tip_form_diameter_mm`` is d_a - 2 h_K (Eq. (127)) with the chamfer of the input, or the
    intersection of the involute with the edge break involute of the tool (DIN 3960 Eq. (A.3.06));
    ``tip_chamfer_radial_mm`` is then the generated height. ``residual_tip_thickness_mm`` is
    s_aK in the transverse section: from the tool (DIN 3960 Eq. (A.3.05)), or the input, or
    ``None`` where there is no chamfer (the tip tooth thickness applies) or where the shape of a
    given chamfer is not given.

    Tooth depth, addendum and dedendum are the first forms of Eq. (35) to (37) with the generated
    root diameter; the tip tooth thickness is Eq. (38) on the tip circle with x_E (§4.7).

    ``tool_edge_break_angle_deg`` is the angle of the edge break flank the tool has. It is
    ``None`` where the tool has no such flank, also where its contract states an angle but its
    dedendum equals its root form height (warning ``edge_break_angle_without_flank``): a tip
    chamfer of such a gear is the given one (h_K, s_aK), not one generated by the tool.
    """

    number_of_teeth: int = Q("number_of_teeth", ge=TEETH_RANGE[0], le=TEETH_RANGE[1], strict=True)
    profile_shift_coefficient: float = Q(
        "profile_shift_coefficient", ge=PROFILE_SHIFT_RANGE[0], le=PROFILE_SHIFT_RANGE[1]
    )
    tool_profile_angle_deg: float = Q("tool_profile_angle", gt=0.0, lt=90.0)
    tool_addendum_mm: float = Q("tool_addendum", gt=0.0)
    tool_tip_radius_mm: float = Q("tool_tip_radius", ge=0.0)
    tool_tip_form_height_mm: float = Q(
        "tool_tip_form_height", equation=f"{_SRC} (128), bracket; Bild 36 a)", gt=0.0
    )
    tool_root_form_height_mm: float | None = Q("tool_root_form_height", default=None, ge=0.0)
    tool_edge_break_angle_deg: float | None = Q(
        "tool_edge_break_angle", default=None, gt=0.0, lt=90.0
    )
    machining_allowance_mm: float = Q("machining_allowance", ge=0.0)
    # the allowances (upper, lower) the gear is generated with: given, converted from span
    # allowances, or following from an inspection dimension (``pair.resolve_tooth_thickness``)
    tooth_thickness_allowance_um: tuple[float, float] | None = Q(
        "tooth_thickness_allowance", default=None
    )
    upper_generating_profile_shift_coefficient: float = Q(
        "upper_generating_profile_shift_coefficient", equation=f"{_SRC} (123)"
    )
    lower_generating_profile_shift_coefficient: float = Q(
        "lower_generating_profile_shift_coefficient", equation=f"{_SRC} (124)"
    )
    generating_profile_shift_coefficient: float = Q(
        "generating_profile_shift_coefficient", equation=f"{_SRC} (123): x_Es is used"
    )
    min_generating_profile_shift_coefficient: float = Q(
        "min_generating_profile_shift_coefficient", equation=f"{_SRC} (135)"
    )
    undercut: bool
    generated_root_diameter_mm: float = Q(
        "generated_root_diameter", equation=f"{_SRC} (125)", gt=0.0
    )
    lower_generated_root_diameter_mm: float = Q(
        "lower_generated_root_diameter", equation=f"{_SRC} (125) with x_Ei", gt=0.0
    )
    root_form_diameter_mm: float = Q(
        "root_form_diameter",
        equation=f"{_SRC} (128) Anhang NB, or the intersection of fillet and involute (§7.6)",
        gt=0.0,
    )
    tip_diameter_mm: float = Q("tip_diameter", gt=0.0)
    tip_form_diameter_mm: float = Q(
        "tip_form_diameter", equation=f"{_SRC} (127), or {_OLD} (A.3.06)", gt=0.0
    )
    tip_chamfer_radial_mm: float = Q("tip_chamfer_radial", ge=0.0)
    residual_tip_thickness_mm: float | None = Q(
        "residual_tip_thickness", equation=f"{_OLD} (A.3.05), or given", default=None, gt=0.0
    )
    transverse_tip_tooth_thickness_mm: float = Q(
        "transverse_tip_tooth_thickness", equation=f"{_SRC} (38) at d_a", gt=0.0
    )
    normal_tip_tooth_thickness_mm: float = Q(
        "normal_tip_tooth_thickness", equation=f"{_SRC} (48) at d_a", gt=0.0
    )
    tooth_depth_mm: float = Q("tooth_depth", equation=f"{_SRC} (35) with d_fE", gt=0.0)
    addendum_mm: float = Q("addendum", equation=f"{_SRC} (36)")
    dedendum_mm: float = Q("dedendum", equation=f"{_SRC} (37) with d_fE, signed")
    warnings: tuple[InputWarning, ...] = ()


class GenerationResult(FrozenModel):
    """The tool-based generation of both gears of a pair and the pair geometry that follows.

    ``pair_geometry`` is ``compute_pair_geometry`` with the generated root form and tip form
    diameters; ``tip_clearance_mm`` is Eq. (60) per gear (its tip against the generated root of
    the mating gear) and ``form_over_dimension_mm`` Eq. (76) per gear. ``inputs`` is the pair as
    the contract validated it.
    """

    inputs: PairInput
    gears: Pair[GearGeneration]
    pair_geometry: PairGeometry
    tip_clearance_mm: Pair[float] = Q("tip_clearance", equation=f"{_SRC} (60)")
    form_over_dimension_mm: Pair[float] = Q("form_over_dimension", equation=f"{_SRC} (76)")
    warnings: tuple[InputWarning, ...] = ()


_INS = "DIN21773:2014"


class GearInspection(FrozenModel):
    """Inspection dimensions of the tooth thickness of one external gear (DIN 21773:2014-08;
    measuring ball diameters per DIN 3977:1981-02).

    A field of type ``DimensionLimits`` holds the nominal dimension (with x) and the upper
    limit, the mean and the lower limit of the finished gear (with x_Es, x_Em, x_Ei; §4, p. 8).
    Without allowances all four are the nominal dimension. Circles and allowance factors that
    belong to a measurement are given for the gear at its upper limit (the state the gear is
    generated with), the allowance factors of §14 at the mean.

    ``number_of_teeth_spanned`` is the k the span is computed with: the one of the input, else
    Eq. (9), moved into the usable range of Eq. (12), (13) where it lies outside. The span
    fields are ``None`` where no number of teeth spanned touches the usable flank.
    ``measuring_ball_diameter_mm`` is the ball the ball dimensions are computed with: the one
    of the input, else the next larger diameter of DIN 3977 Tabelle 1 above the ideal diameter
    of Eq. (26). The chord on the reference cylinder is ``None`` where that cylinder lies
    outside the usable flank; the chord on a Y-cylinder is given where the caller names one.
    """

    number_of_teeth: int = Q("number_of_teeth", ge=TEETH_RANGE[0], le=TEETH_RANGE[1], strict=True)
    profile_shift_coefficient: float = Q(
        "profile_shift_coefficient", ge=PROFILE_SHIFT_RANGE[0], le=PROFILE_SHIFT_RANGE[1]
    )
    upper_generating_profile_shift_coefficient: float = Q(
        "upper_generating_profile_shift_coefficient", equation=f"{_SRC} (123)"
    )
    mean_generating_profile_shift_coefficient: float = Q(
        "mean_generating_profile_shift_coefficient", equation=f"{_INS} (44)"
    )
    lower_generating_profile_shift_coefficient: float = Q(
        "lower_generating_profile_shift_coefficient", equation=f"{_SRC} (124)"
    )
    tooth_thickness_allowance_um: tuple[float, float] | None = Q(
        "tooth_thickness_allowance", default=None
    )
    tooth_thickness_tolerance_um: float | None = Q(
        "tooth_thickness_tolerance", equation=f"{_INS} (45)", default=None, ge=0.0
    )
    span_allowance_um: tuple[float, float] | None = Q(
        "span_allowance", equation=f"{_INS} (54)", default=None
    )
    v_circle_diameter_mm: float = Q("v_circle_diameter", equation=f"{_SRC} (32) with x_Es", gt=0.0)
    # span measurement
    number_of_teeth_spanned: int | None = Q(
        "number_of_teeth_spanned", equation=f"{_INS} (9)", default=None, ge=2, strict=True
    )
    min_number_of_teeth_spanned: int = Q(
        "min_number_of_teeth_spanned", equation=f"{_INS} (12)", strict=True
    )
    max_number_of_teeth_spanned: int = Q(
        "max_number_of_teeth_spanned", equation=f"{_INS} (13)", strict=True
    )
    span_measurement_mm: DimensionLimits | None = Q(
        "span_measurement", equation=f"{_INS} (14)", default=None
    )
    span_measuring_circle_diameter_mm: float | None = Q(
        "span_measuring_circle_diameter",
        equation=f"{_INS} (17); DIN3960:1987 (3.8.15)",
        default=None,
        gt=0.0,
    )
    span_allowance_factor: float = Q("span_allowance_factor", equation=f"{_INS} (54)", gt=0.0)
    min_usable_face_width_mm: float | None = Q(
        "min_usable_face_width", equation=f"{_INS} (15), (16)", default=None, gt=0.0
    )
    # chords
    chordal_tooth_thickness_mm: DimensionLimits | None = Q(
        "chordal_tooth_thickness", equation=f"{_INS} (4)", default=None
    )
    height_above_chord_mm: float | None = Q(
        "height_above_chord", equation=f"{_INS} (6)", default=None, ge=0.0
    )
    y_diameter_mm: float | None = Q("y_diameter", default=None, gt=0.0)
    chordal_tooth_thickness_at_y_mm: DimensionLimits | None = Q(
        "chordal_tooth_thickness_at_y", equation=f"{_INS} (2)", default=None
    )
    height_above_chord_at_y_mm: float | None = Q(
        "height_above_chord_at_y", equation=f"{_INS} (5)", default=None, ge=0.0
    )
    chordal_tooth_thickness_allowance_factor: float | None = Q(
        "chordal_tooth_thickness_allowance_factor", equation=f"{_INS} (51)", default=None, gt=0.0
    )
    constant_chord_mm: DimensionLimits | None = Q(
        "constant_chord", equation=f"{_INS} (7)", default=None
    )
    height_above_constant_chord_mm: float | None = Q(
        "height_above_constant_chord", equation=f"{_INS} (8)", default=None
    )
    # balls and rollers
    ideal_measuring_ball_diameter_mm: float | None = Q(
        "ideal_measuring_ball_diameter", equation=f"{_INS} (26), (27)", default=None, gt=0.0
    )
    measuring_ball_diameter_mm: float = Q("measuring_ball_diameter", gt=0.0)
    ball_centre_circle_diameter_mm: float = Q(
        "ball_centre_circle_diameter", equation=f"{_INS} (31)", gt=0.0
    )
    ball_measuring_circle_diameter_mm: float = Q(
        "ball_measuring_circle_diameter", equation=f"{_INS} (33)", gt=0.0
    )
    measuring_circle_offset_factor: float = Q(
        "measuring_circle_offset", factor=True, equation="DIN3977:1981 Abschnitt 6"
    )
    radial_single_ball_dimension_mm: DimensionLimits = Q(
        "radial_single_ball_dimension", equation=f"{_INS} (32)"
    )
    diametral_two_ball_dimension_mm: DimensionLimits = Q(
        "diametral_two_ball_dimension", equation=f"{_INS} (35), (36)"
    )
    diametral_two_roller_dimension_mm: DimensionLimits = Q(
        "diametral_two_roller_dimension", equation=f"{_INS} §11"
    )
    radial_ball_dimension_allowance_factor: float = Q(
        "radial_ball_dimension_allowance_factor", equation=f"{_INS} (57)", gt=0.0
    )
    diametral_ball_dimension_allowance_factor: float = Q(
        "diametral_ball_dimension_allowance_factor", equation=f"{_INS} (60), (61)", gt=0.0
    )
    overcut_tip_diameter_mm: float | None = Q(
        "overcut_tip_diameter", equation=f"{_INS} (40)", default=None, gt=0.0
    )
    warnings: tuple[InputWarning, ...] = ()


class InspectionResult(FrozenModel):
    """Inspection dimensions of both gears of a generated pair. ``inputs`` is the pair as the
    contract validated it."""

    inputs: PairInput
    gears: Pair[GearInspection]
    warnings: tuple[InputWarning, ...] = ()
