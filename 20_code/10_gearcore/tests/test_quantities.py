"""The quantity registry is the single source of truth (project rule 3b, ADR-108).

Names, symbols and designations are defined in ``data/quantities.yaml`` and nowhere else. These
tests bind everything that names a quantity to the registry: contract fields, arguments of the
computational functions, the worked examples, the comparison with STplus, the notebooks.
"""

import inspect
import json
import re
import typing
from pathlib import Path
from typing import Any

import pytest

from gearcore import contour, generation, inspection, involute, pair, rack, trochoid
from gearcore.data import (
    has_stplus,
    load_stplus,
    load_worked_example,
    stplus_case_dirs,
    worked_example_ids,
)
from gearcore.errors import InputRangeError
from gearcore.io import ste
from gearcore.models import inputs as inputs_module
from gearcore.models import profiles as profiles_module
from gearcore.models import results as results_module
from gearcore.models.common import DimensionLimits, FrozenModel, Pair
from gearcore.models.inputs import (
    BallMeasurement,
    GearInput,
    PairInput,
    SpanMeasurement,
    ToolProfile,
)
from gearcore.models.profiles import BasicRackProfile
from gearcore.models.results import (
    BasicGearGeometry,
    GearGeneration,
    GearInspection,
    GenerationResult,
    InspectionResult,
    PairGeometry,
)
from gearcore.parity import COMPARED_FIELDS, PROFILE_SHIFT_FIELD, stplus_names
from gearcore.quantities import (
    GREEK,
    UNIT_SUFFIX,
    designation_differences,
    latex,
    quantities,
    quantity,
    quantity_of_field,
    render_markdown,
    stplus_symbol_in_registry_notation,
    symbol_differences,
)
from gearcore.trace import load_sources

REPO = Path(__file__).resolve().parents[3]
DOCS = REPO / "20_code" / "00_development_documentation"
NOTEBOOKS = REPO / "40_jupyter-notebooks"

CONTRACTS: tuple[type[FrozenModel], ...] = (
    ToolProfile,
    SpanMeasurement,
    BallMeasurement,
    GearInput,
    PairInput,
    BasicGearGeometry,
    BasicRackProfile,
    GearGeneration,
    GenerationResult,
    GearInspection,
)
RESULTS: tuple[type[FrozenModel], ...] = (
    BasicGearGeometry,
    BasicRackProfile,
    PairGeometry,
    GearGeneration,
    GenerationResult,
    GearInspection,
    InspectionResult,
)
"""Contracts of implemented computations: every quantity must be verified. ``ToothContour``
holds coordinates, which are no quantities; its landmark diameters use the registry."""

OLDER_NOTATION = {"DIN3972:1952"}
"""Valid norms that print an older notation; their symbols stand under ``replaced``."""

STPLUS_REFERENCE_CASE = "helix30_z25_40"
HOMONYMS = {
    "k": {"number_of_teeth_spanned", "tip_alteration_coefficient"},
    "d_M": {"span_measuring_circle_diameter", "ball_measuring_circle_diameter"},
    "D_M": {"measuring_ball_diameter", "ideal_measuring_ball_diameter"},
}
"""One symbol for two quantities: k in the symbol list of DIN ISO 21771:2014-08 (§3.1, p. 12);
d_M in DIN 21773:2014-08 for the measuring circle of the span (§7.2) and of the ball (§8); D_M
for the ball that is used and for the diameter Eq. (26) gives."""
MANUAL_INPUT_KEYS = {"ZAEHNEZAHLVERHAELTNIS", "PR.VERSCH.SUMME"}
"""Input keys of the STplus manual (Bild 4.12, p. 25) that the importer does not map."""

# arguments that name no quantity: (function, argument) -> what it is
NOT_A_QUANTITY = {
    ("inv", "alpha_rad"): "the involute function takes any angle",
    ("inv_inverse", "value"): "a value of the involute function",
    ("iso53_basic_rack", "kind"): "type A to D of ISO 53",
    ("din3972_tool_addendum_mm", "profile"): "reference profile I to IV of DIN 3972",
    ("din3972_machining_allowance_mm", "profile"): "reference profile I to IV of DIN 3972",
    ("din3972_tool", "profile"): "reference profile I to IV of DIN 3972",
    ("validate_basic_rack", "rack"): "a contract",
    ("has_edge_break_flank", "tool"): "a contract",
    ("check_basic_rack", "rack"): "a contract",
    ("tool_from_basic_rack", "rack"): "a contract",
    ("compute_pair_geometry", "pair"): "a contract",
    ("resolve_profile_shift", "pair"): "a contract",
    ("resolve_tooth_thickness", "pair"): "a contract",
    ("with_nominal_tip_diameters", "pair"): "a contract",
    ("compute_generation", "pair"): "a contract",
    # DIN 3960 Anhang A names the edge break involute with symbols the current norm lacks
    ("edge_break_base_diameter", "alpha_tK_rad"): "transverse angle of the edge break flank",
    ("edge_break_transverse_tooth_thickness", "alpha_tK_rad"): "transverse edge break angle",
    ("edge_break_base_half_angle", "s_tK_mm"): "tooth thickness of the edge break involute",
    ("edge_break_base_half_angle", "alpha_tK_rad"): "transverse edge break angle",
    ("tip_form_diameter_from_edge_break", "d_bK_mm"): "base diameter of the edge break involute",
    (
        "tip_form_diameter_from_edge_break",
        "psi_bK_rad",
    ): "base half angle of the edge break involute",
    ("tip_form_diameter_from_edge_break", "psi_b_rad"): "base half angle (symbol psi_b, registry)",
    ("residual_tip_thickness", "d_bK_mm"): "base diameter of the edge break involute",
    ("residual_tip_thickness", "psi_bK_rad"): "base half angle of the edge break involute",
    ("tip_tooth_thickness", "psi_rad"): "tooth thickness half angle (symbol psi, registry)",
    # rolling: coordinates, parameters and geometry objects
    ("tip_rounding", "rho_aP0_mm"): "symbol of the registry (tool tip radius)",
    ("pitch_point_position", "xi_mm"): "rack coordinate",
    ("pitch_point_position", "eta_mm"): "rack coordinate",
    ("pitch_point_position", "tangent_xi"): "tangent component",
    ("pitch_point_position", "tangent_eta"): "tangent component",
    ("generated_point", "xi_mm"): "rack coordinate",
    ("generated_point", "eta_mm"): "rack coordinate",
    ("generated_point", "c_mm"): "position of the pitch point on the rack",
    ("generated_point", "r_mm"): "reference radius (DIN 3960 r; d / 2)",
    ("fillet_point", "rounding"): "the tool tip rounding",
    ("fillet_point", "theta_rad"): "parameter of the ellipse",
    ("fillet_curve", "rounding"): "the tool tip rounding",
    ("fillet_curve", "theta_end_rad"): "parameter of the ellipse",
    ("fillet_curve", "n"): "number of points",
    ("involute_half_angle", "radius_mm"): "a radius",
    ("involute_half_angle", "psi_b_rad"): "base half angle (symbol psi_b, registry)",
    ("root_form_diameter_by_intersection", "rounding"): "the tool tip rounding",
    ("root_form_diameter_by_intersection", "psi_b_rad"): "base half angle (symbol psi_b, registry)",
    ("root_form_diameter_by_intersection", "undercut_expected"): "a flag of the caller",
    ("distances", "contour"): "a contract",
    ("distances", "reference"): "reference points",
    # contour sampling and measurement
    ("involute_flank", "psi_b_rad"): "base half angle (symbol psi_b, registry)",
    ("involute_flank", "d_start_mm"): "a diameter",
    ("involute_flank", "d_end_mm"): "a diameter",
    ("involute_flank", "n"): "number of points",
    ("chamfer_flank", "r_Fa_mm"): "tip form radius",
    ("chamfer_flank", "psi_Fa_rad"): "half angle at the tip form circle",
    ("chamfer_flank", "r_a_mm"): "tip radius",
    ("chamfer_flank", "n"): "number of points",
    ("tooth_contour", "pair"): "a contract",
    ("tooth_contour", "generation"): "a contract",
    ("tooth_contour", "role"): "pinion or wheel",
    ("tooth_contour", "points"): "number of points",
    ("gear_polygon", "contour"): "a contract",
    ("gear_polygon", "arc_points"): "number of points",
    ("compare", "contour"): "a contract",
    ("compare", "reference"): "reference points",
    ("stplus_contour", "case"): "a fixture case",
    ("stplus_contour", "gear"): "gear number",
    # inspection dimensions
    ("compute_inspection", "generation"): "a contract",
    ("compute_inspection", "chord_diameter_mm"): "cylinders d_y of the chord, one per gear",
    ("upper_limit_dimension", "mean_mm"): "mean of any inspection dimension",
    ("lower_limit_dimension", "mean_mm"): "mean of any inspection dimension",
    ("upper_limit_dimension", "allowance_factor"): "allowance factor of any inspection dimension",
    ("lower_limit_dimension", "allowance_factor"): "allowance factor of any inspection dimension",
    ("tooth_thickness_tolerance", "E_sns_um"): "upper allowance (registry: E_sns/E_sni)",
    ("tooth_thickness_tolerance", "E_sni_um"): "lower allowance (registry: E_sns/E_sni)",
    ("mean_tooth_thickness_allowance", "E_sns_um"): "upper allowance (registry: E_sns/E_sni)",
    ("overcut_tip_diameter", "x_Es"): "symbol of the registry (upper generating coefficient)",
    ("number_of_teeth_spanned", "d_v_mm"): "symbol of the registry (V-circle diameter)",
}
ARGUMENT_SUFFIXES = ("_mm", "_rad", "_deg", "_um")


def _is_numeric(annotation: Any) -> bool:
    if annotation in (int, float, DimensionLimits):  # (nominal dimension and limits: numbers)
        return True
    generic = getattr(annotation, "__pydantic_generic_metadata__", None)
    if generic and generic["origin"] is Pair:  # Pair[float]: one number per gear
        return any(_is_numeric(argument) for argument in generic["args"])
    return any(_is_numeric(argument) for argument in typing.get_args(annotation))


# --- the registry itself ----------------------------------------------------------------------


def test_registry_is_well_formed() -> None:
    sources = load_sources()
    registry = quantities()
    assert len(registry) == 142
    symbols: dict[str, str] = {}
    for name, entry in registry.items():
        current = [entry.source] if entry.source else []
        if entry.english is not None:
            current.append(entry.english.source)
        current += [printed.source for printed in entry.also]
        for key in current:
            assert key in sources, f"{name}: unknown source {key}"
            assert sources[key]["confirmed_by_user"] is True, f"{name}: {key} is not confirmed"
            assert sources[key].get("status") not in {"withdrawn", "missing", "draft"}, (
                f"{name}: {key} is not a current document"
            )
        for printed in entry.replaced:
            assert printed.source in sources, f"{name}: unknown source {printed.source}"
            withdrawn = sources[printed.source].get("status") == "withdrawn"
            assert withdrawn or printed.source in OLDER_NOTATION, (
                f"{name}: {printed.source} is current, its symbol belongs under 'also'"
            )
        if entry.symbol is not None and entry.symbol not in HOMONYMS:
            assert entry.symbol not in symbols, (
                f"symbol {entry.symbol} names {symbols[entry.symbol]} and {name}"
            )
            symbols[entry.symbol] = name
        assert entry.unit in UNIT_SUFFIX
        assert 0 <= entry.since <= 4, f"{name}: increment {entry.since} has not started"
    for symbol, names in HOMONYMS.items():
        assert {name for name, entry in registry.items() if entry.symbol == symbol} == names


def test_verified_and_pending_quantities() -> None:
    registry = quantities()
    pending = sorted(name for name, entry in registry.items() if entry.status == "pending")
    assert pending == [
        "min_tip_clearance",
        "quality_grade",
        "tool_normal_module",
        "tool_protuberance",
        "tool_protuberance_angle",
    ]
    for name in pending:
        entry = registry[name]
        assert entry.description is None and entry.source is None, name
        assert entry.note, f"{name}: a pending quantity says when it is verified"
    with pytest.raises(InputRangeError, match="unknown quantity"):
        quantity("teeth")
    with pytest.raises(InputRangeError, match="no quantity"):
        quantity_of_field("pressure_angle_deg")


def test_naming_rule() -> None:
    assert quantity("number_of_teeth").field_name() == "number_of_teeth"
    assert quantity("centre_distance").field_name() == "centre_distance_mm"
    assert quantity("tip_relief").field_name() == "tip_relief_um"
    assert quantity("tool_addendum").field_name(prefix="tool_", factor=True) == "addendum_factor"
    assert quantity("tool_addendum").field_symbol(factor=True) == "h_aP0*"
    assert quantity("tool_addendum").field_unit(factor=True) == "-"
    assert quantity_of_field("basic_rack_dedendum_factor") == (
        quantity("basic_rack_dedendum"),
        True,
    )
    assert quantity_of_field("profile_angle_deg", prefix="tool_")[0].symbol == "alpha_P0"
    assert quantity_of_field("profile_angle_deg", prefix="basic_rack_")[0].symbol == "alpha_P"


# --- contracts ------------------------------------------------------------------------------------


@pytest.mark.parametrize("model", CONTRACTS, ids=lambda m: m.__name__)
def test_contract_fields_take_name_symbol_and_unit_from_the_registry(
    model: type[FrozenModel],
) -> None:
    prefix = getattr(model, "QUANTITY_PREFIX", "")
    seen = 0
    for name, info in model.model_fields.items():
        extra = info.json_schema_extra
        if not _is_numeric(info.annotation):
            assert extra is None, f"{model.__name__}.{name}: metadata on a non-numeric field"
            continue
        assert isinstance(extra, dict) and "quantity" in extra, (
            f"{model.__name__}.{name}: a numeric field is declared with Q(<quantity>)"
        )
        entry = quantity(str(extra["quantity"]))
        factor = bool(extra["factor"])
        assert name == entry.field_name(prefix=prefix, factor=factor), (
            f"{model.__name__}.{name}: the registry names this field "
            f"{entry.field_name(prefix=prefix, factor=factor)}"
        )
        assert extra["symbol"] == entry.field_symbol(factor=factor)
        assert extra["unit"] == entry.field_unit(factor=factor)
        assert extra["designation"] == entry.description and extra["status"] == entry.status
        if model in RESULTS:
            assert entry.status == "verified", f"{model.__name__}.{name}: pending quantity"
        seen += 1
    assert seen >= 2


def test_models_define_no_symbol_of_their_own() -> None:
    for module in (inputs_module, results_module, profiles_module):
        source = inspect.getsource(module)
        assert not re.search(r"\bF\(", source), f"{module.__name__} declares a symbol with F(...)"
        assert "from gearcore.quantities import Q" in source


def test_schema_carries_the_designation_of_the_norm() -> None:
    schema = PairInput.model_json_schema()["properties"]["centre_distance_mm"]
    assert schema["symbol"] == "a_w" and schema["unit"] == "mm"
    assert schema["designation"] == "Achsabstand eines Zylinderradpaares"
    assert schema["designation_en"] == "Centre distance"
    assert schema["source"] == "ISO21771:2014" and schema["stplus_key"] == "ACHSABSTAND"
    result = BasicGearGeometry.model_json_schema()["properties"]["base_diameter_mm"]
    assert result["equation"] == "ISO21771:2014 (19)" and result["symbol"] == "d_b"


# --- functions ------------------------------------------------------------------------------------


def _public_functions(module: Any) -> list[tuple[str, Any]]:
    return [
        (name, function)
        for name, function in inspect.getmembers(module, inspect.isfunction)
        if not name.startswith("_") and function.__module__ == module.__name__
    ]


def _names_a_quantity(argument: str) -> bool:
    symbols = {entry.symbol for entry in quantities().values() if entry.symbol is not None}
    bare = argument
    for suffix in ARGUMENT_SUFFIXES:
        bare = bare.removesuffix(suffix)
    # the norm appends 1 (pinion) and 2 (wheel) to a symbol: z_1, d_a1, rho_y2
    bare = re.sub(r"_?[12]$", "", bare) if re.search(r"[A-Za-z]_?[12]$", bare) else bare
    if bare in symbols:
        return True
    # an angle in radians is a quantity the registry lists in degrees
    candidates = [argument, bare + "_deg"] if argument.endswith("_rad") else [argument]
    for candidate in candidates:
        for prefix in ("", "basic_rack_", "tool_"):
            try:
                quantity_of_field(candidate, prefix=prefix)
            except InputRangeError:
                continue
            return True
    return False


@pytest.mark.parametrize(
    "module",
    [involute, rack, pair, generation, trochoid, contour, inspection],
    ids=lambda m: m.__name__,
)
def test_arguments_are_named_by_symbol_or_registry_name(module: Any) -> None:
    checked = 0
    for function_name, function in _public_functions(module):
        for argument in inspect.signature(function).parameters:
            if (function_name, argument) in NOT_A_QUANTITY:
                continue
            assert _names_a_quantity(argument), (
                f"{module.__name__}.{function_name}({argument}): neither a symbol nor a name "
                "of the registry"
            )
            checked += 1
    # rolling and contour work with coordinates and parameters; the norm modules with quantities
    assert checked >= (2 if module in (trochoid, contour) else 10), module.__name__
    assert not _names_a_quantity("teeth") and not _names_a_quantity("pressure_angle_deg")


def test_function_names_follow_the_designations() -> None:
    names = {name for name, _ in _public_functions(involute)}
    # 'Profilwinkel' at any cylinder, 'Eingriffswinkel' at the reference cylinder
    assert {"transverse_profile_angle_at", "normal_profile_angle_at"} <= names
    assert {"transverse_pressure_angle", "base_helix_angle", "reference_diameter"} <= names
    assert not {name for name in names if "pressure_angle_at" in name}


# --- STplus ---------------------------------------------------------------------------------------


def _label(text: str) -> str:
    return re.sub(r"[ .]+$", "", text)


def test_stplus_names_of_the_registry_exist_in_the_fixtures() -> None:
    listing = load_stplus(STPLUS_REFERENCE_CASE, "geometry")
    interface = load_stplus(STPLUS_REFERENCE_CASE, "interface")
    input_keys = set(ste.TOOL_KEYS) | set(ste.GEOMETRY_KEYS_MAPPED) | MANUAL_INPUT_KEYS
    checked = 0
    for name, entry in quantities().items():
        names = entry.stplus
        if names is None:
            continue
        if names.symbol is not None:
            assert names.symbol in listing, f"{name}: listing prints no symbol {names.symbol}"
            if names.label is not None:
                assert _label(listing[names.symbol]["label"]) == _label(names.label), name
        else:
            assert names.label is None, f"{name}: a label without a symbol"
        if names.interface_key is not None:
            assert f"GEOMETRIEDATEN/{names.interface_key}" in interface, name
        if names.input_key is not None:
            assert names.input_key in input_keys, f"{name}: unknown input key {names.input_key}"
        checked += 1
    assert checked >= 40


def test_the_comparison_with_stplus_uses_the_registry() -> None:
    for field in (*COMPARED_FIELDS, PROFILE_SHIFT_FIELD):
        entry, factor = quantity_of_field(field)
        assert entry.status == "verified" and not factor
        assert entry.stplus is not None
        assert stplus_names(field) == (entry.stplus.symbol, entry.stplus.interface_key)
        assert field in BasicGearGeometry.model_fields
    assert stplus_names("base_helix_angle_deg") == ("beta_b", "SCHRAEGUNGSWINKEL_GRUND")


def test_importer_maps_input_keys_to_the_fields_of_the_registry() -> None:
    for key, field in ste.TOOL_KEYS.items():
        entry, _ = quantity_of_field(field, prefix="tool_")
        assert field in ToolProfile.model_fields
        assert entry.stplus is not None and entry.stplus.input_key == key, (key, field)


# --- registry review of 2026-09-29 (independent reviewers, gate_reports/increment_1.md) -----------


def test_review_symbols_that_changed_since_din_3960() -> None:
    """DIN 3960 printed the symbols of the sections (s_t, s_n, e_t, p_bt, alpha_yt ...) as
    DIN ISO 21771 does; its list §2.1 only omits the index. These symbols did change."""
    changed = {
        name: sorted(
            (
                printed.symbol
                for printed in entry.replaced
                if printed.source == "DIN3960:1987" and printed.symbol != entry.symbol
            ),
            key=lambda symbol: symbol or "",  # a symbol None stays in the list and fails below
        )
        for name, entry in quantities().items()
    }
    assert {name: old for name, old in changed.items() if old} == {
        "centre_distance": ["a"],
        "tip_alteration_coefficient": ["k*"],
        "tool_tip_radius": ["rho_a0"],
        "tool_edge_break_angle": ["alpha_K", "alpha_KP0"],
        "transverse_tip_tooth_thickness": ["s_a", "s_ta"],
        "residual_tip_thickness": ["s_taK"],
        "upper_generating_profile_shift_coefficient": ["x_Ee"],
        "pre_machining_generating_profile_shift_coefficient": ["x_EV/x_EiV"],
        # inspection dimensions (increment 4): DIN 3960 sets a bar above s and h for chords
        # ('s-bar'), writes R for rollers where DIN 21773 writes Z, and A for allowances
        "profile_angle_at_v_circle": ["alpha_v"],
        "normal_base_tooth_thickness": ["s_b"],
        "chordal_tooth_thickness": ["s-bar"],
        "height_above_chord": ["h-bar_a"],
        "constant_chord": ["s-bar_c"],
        "height_above_constant_chord": ["h-bar_c"],
        "radial_single_roller_dimension": ["M_rR"],
        "diametral_two_roller_dimension": ["M_dR"],
        "tooth_thickness_tolerance": ["T_s"],
        "span_allowance": ["A_W"],
    }
    for name in (
        "transverse_tooth_thickness",
        "normal_tooth_thickness",
        "transverse_space_width",
        "normal_space_width",
        "transverse_tooth_thickness_at_y",
        "normal_tooth_thickness_at_y",
        "transverse_space_width_at_y",
        "normal_space_width_at_y",
        "transverse_profile_angle_at_y",
        "normal_profile_angle_at_y",
        "transverse_base_pitch",
        "transverse_contact_pitch",
    ):
        entry = quantity(name)
        assert [p.symbol for p in entry.replaced] == [entry.symbol], name
        assert entry.replaced[0].location.startswith("§3."), f"{name}: cite the clause, not §2.1"


def test_review_designations_belong_to_the_quantity() -> None:
    rounding = quantity("tool_tip_radius")
    assert rounding.english is not None
    assert (rounding.english.text, rounding.english.source) == (
        "tool tip corner rounding",
        "ISO6336-3:2019",
    )
    # ISO/TR 6336-30 uses rho_aP0 for a dimensionless coefficient of a pinion cutter
    assert all("Pinion cutter" not in printed.description for printed in rounding.also)
    assert rounding.note is not None and "Pinion cutter tip radius coefficient" in rounding.note
    assert {p.symbol for p in rounding.replaced} == {"rho_a0", "r_1"}
    addendum = quantity("tool_addendum")
    assert addendum.english is not None and addendum.english.text == "addendum of tool"
    clearance = quantity("basic_rack_bottom_clearance")
    assert clearance.description == "Kopfspiel zwischen Bezugsprofil und Gegenprofil"
    speed = quantity("rotation_speed")
    assert {p.symbol for p in speed.also} == {"n_1", "n"}
    shift = quantity("profile_shift_coefficient")
    assert shift.note is not None and "4.2.18" in shift.note


def test_review_stplus_names_are_complete_for_the_geometry() -> None:
    ratio = quantity("gear_ratio").stplus
    assert ratio is not None and (ratio.symbol, ratio.label) == ("z2/z1", "Zaehnezahlverhaeltnis")
    width = quantity("contact_face_width").stplus
    assert width is not None and width.interface_key == "GEMEINSAME_BREITE"
    root = quantity("generated_root_diameter").stplus
    assert root is not None and root.interface_key == "FUSSKREISDURCHM"
    allowance = quantity("machining_allowance")
    assert allowance.note is not None
    assert "BEARBEITUNGSZUGABE" in allowance.note and "BEARB_ZUGABE_WKZ" in allowance.note
    assert "BEARBEITUNGSZUGABE" not in ste.GEOMETRY_KEYS_MAPPED, (
        "the importer maps q of the geometry data now: update the registry entry and its note"
    )


def test_review_stplus_addendum_factor_is_an_actual_value() -> None:
    """'Bezugspr.-Kopfhoehenfaktor (Istw.)' = (d_a - d) / (2 m_n) - x: it contains the tip
    alteration and is no input of the basic rack (kst_c_rerun: 0.88761 and 0.75096)."""
    names = quantity("basic_rack_addendum").stplus
    assert names is not None and names.interface_key == "BEZPR_KOPFHOEHENFAKTOR"
    checked, below_one = 0, 0
    for case in sorted(path.name for path in stplus_case_dirs()):
        if not has_stplus(case, "interface"):
            continue  # supplied listings of older versions come without an interface file
        interface = load_stplus(case, "interface")

        def numbers(key: str, table: dict[str, Any] = interface) -> list[float]:
            return [float(value) for value in table[f"GEOMETRIEDATEN/{key}"]["numbers"]]

        (module,) = numbers("NORMALMODUL")
        rows = zip(
            numbers("BEZPR_KOPFHOEHENFAKTOR"),
            numbers("KOPFKREISDURCHM"),
            numbers("TEILKREISDURCHM"),
            numbers("PROFILVERSCHIEBFAKTOR"),
            strict=True,
        )
        for factor, d_a, d, x in rows:
            assert factor == pytest.approx((d_a - d) / (2.0 * module) - x, abs=3e-5), case
            checked += 1
            below_one += factor < 0.999
    assert checked >= 20 and below_one >= 3


def test_review_base_space_half_angle_changes_its_sign() -> None:
    """Note of eta_b: for x = 0, alpha_n = 20 deg, beta = 0 negative from z = 106 on."""

    def eta_b(z: int) -> float:
        gear = involute.compute_basic_gear_geometry(
            number_of_teeth=z,
            normal_module_mm=1.0,
            normal_pressure_angle_deg=20.0,
            helix_angle_deg=0.0,
            profile_shift_coefficient=0.0,
        )
        return gear.base_space_width_half_angle_deg

    assert eta_b(50) > 0.0 and eta_b(105) > 0.0
    assert eta_b(106) < 0.0 and eta_b(200) < 0.0


# --- what differs from the current norm (user request 2026-09-30) ----------------------------------


def test_symbol_differences_list_exactly_what_changed() -> None:
    """The table of differences shows only symbols that are not those of the current norm."""
    verified = [d for d in symbol_differences() if d.status == "verified"]
    older = {(d.quantity, d.other, d.source) for d in verified if d.kind == "replaced"}
    assert older == {
        ("centre_distance", "a", "DIN3960:1987"),
        ("tool_tip_radius", "rho_a0", "DIN3960:1987"),
        ("tip_alteration_coefficient", "k*", "DIN3960:1987"),
        ("tool_edge_break_angle", "alpha_K", "DIN3960:1987"),
        ("tool_edge_break_angle", "alpha_KP0", "DIN3960:1987"),
        ("transverse_tip_tooth_thickness", "s_a", "DIN3960:1987"),
        ("transverse_tip_tooth_thickness", "s_ta", "DIN3960:1987"),
        ("residual_tip_thickness", "s_taK", "DIN3960:1987"),
        ("upper_generating_profile_shift_coefficient", "x_Ee", "DIN3960:1987"),
        ("pre_machining_generating_profile_shift_coefficient", "x_EV/x_EiV", "DIN3960:1987"),
        ("profile_angle_at_v_circle", "alpha_v", "DIN3960:1987"),
        ("normal_base_tooth_thickness", "s_b", "DIN3960:1987"),
        ("chordal_tooth_thickness", "s-bar", "DIN3960:1987"),
        ("height_above_chord", "h-bar_a", "DIN3960:1987"),
        ("constant_chord", "s-bar_c", "DIN3960:1987"),
        ("height_above_constant_chord", "h-bar_c", "DIN3960:1987"),
        ("radial_single_roller_dimension", "M_rR", "DIN3960:1987"),
        ("diametral_two_roller_dimension", "M_dR", "DIN3960:1987"),
        ("tooth_thickness_tolerance", "T_s", "DIN3960:1987"),
        ("span_allowance", "A_W", "DIN3960:1987"),
        ("pitch", "t_0", "DIN3972:1952"),
        ("basic_rack_dedendum", "h_fr", "DIN3972:1952"),
        ("tool_profile_angle", "alpha_0", "DIN3972:1952"),
        ("tool_addendum", "h_kw", "DIN3972:1952"),
        ("tool_tip_radius", "r_1", "DIN3972:1952"),
        ("machining_allowance", "p", "DIN3972:1952"),
    }
    stplus = {d.quantity: d.other for d in verified if d.kind == "stplus" and not d.spelling_only}
    assert stplus == {
        "centre_distance": "a",
        "contact_face_width": "b_gem",
        "tool_profile_angle": "alfa_n0",
        "gear_ratio": "z2/z1",
        "generated_root_diameter": "d_f",
        "length_of_path_of_contact": "g",
        "sum_of_profile_shift_coefficients": "x_1+x_2",
        "common_tooth_depth": "h_gem",
        "length_of_addendum_path_of_contact": "g_alfa-a",
        "form_over_dimension": "c_n",
        "tooth_thickness_allowance": "A_ste",
        "span_allowance": "A_We",
        "chordal_tooth_thickness_at_y": "s_n-",
        "height_above_chord_at_y": "h_a-",
        "diametral_two_roller_dimension": "M_dR",
        "span_allowance_factor": "A_W/A_Sn",
        "diametral_ball_dimension_allowance_factor": "A_Md/A_sn",
    }
    spelled = {d.other for d in verified if d.kind == "stplus" and d.spelling_only}
    assert spelled == {"alfa_n", "alfa_t", "alfa_wt", "eps_alfa", "eps_beta", "eps_gamma"}
    # the factor mark of STplus and a function with its argument are no differences. Between
    # norms the mark is one: DIN 3960 writes k* for the factor and k for the alteration in mm
    starred = [d for d in verified if d.other.removesuffix("*") == d.symbol]
    assert [(d.quantity, d.kind) for d in starred] == [("tip_alteration_coefficient", "replaced")]
    assert not [d for d in verified if d.quantity == "involute_function"]
    pending = {d.quantity for d in symbol_differences() if d.status == "pending"}
    assert "tool_edge_break_angle" not in pending, "verified in increment 3 (alpha_kP, Bild 36 a))"
    assert "tool_protuberance_angle" in pending


def test_stplus_spelling_of_greek_letters() -> None:
    assert stplus_symbol_in_registry_notation("eps_alfa") == "epsilon_alpha"
    assert stplus_symbol_in_registry_notation("rho_aP0*") == "rho_aP0"
    assert stplus_symbol_in_registry_notation("alfa_n0") == "alpha_n0"
    assert stplus_symbol_in_registry_notation("b_gem") == "b_gem"


def test_designation_differences_ignore_the_spelling_reform() -> None:
    differences = {(d.quantity, d.other) for d in designation_differences()}
    assert ("base_tooth_thickness_half_angle", "Grunddicken-Halbwinkel") in differences
    assert (
        "tip_chamfer_radial",
        "Radialbetrag des Kopfkantenbruchs oder der Kopfkantenrundung",
    ) in (differences)
    # 'Meßzähne' against 'Messzähne' is no difference; identical designations are not listed
    assert not [d for d in designation_differences() if d.quantity == "span_measurement"]
    assert not [d for d in designation_differences() if d.quantity == "number_of_teeth"]
    assert all(d.other != d.description for d in designation_differences())


def test_quantities_table_shows_the_differences_first() -> None:
    text = render_markdown()
    differences = text.index("## Was sich gegenüber der aktuellen Norm unterscheidet")
    assert differences < text.index("## Aktuelle Norm")
    section = text[differences : text.index("## Aktuelle Norm")]
    assert "| `centre_distance` | a_w | a | Achsabstand eines Stirnradpaares |" in section
    assert "| `contact_face_width` | b_w | b_gem | Gemeinsame Breite |" in section
    assert "alfa_n = alpha_n" in section
    assert "`number_of_teeth`" not in section, "z is the same everywhere"
    assert "Noch nicht an der Normseite geprüft" in section


# --- worked examples ------------------------------------------------------------------------------


@pytest.mark.parametrize("example_id", worked_example_ids())
def test_worked_examples_name_quantities_of_the_registry(example_id: str) -> None:
    example = load_worked_example(example_id)
    for section in ("inputs", "expected"):
        for key, entry in example[section].items():
            where = f"{example_id}.{section}.{key}"
            named = entry.get("quantity")
            found = quantity(named) if named is not None else quantity_of_field(key)[0]
            assert found.status == "verified", f"{where}: pending quantity {found.name}"
            if entry["symbol"] is None:
                assert found.symbol is None, where
                assert entry["description"] == found.description, where
            else:
                assert entry["symbol"] in found.printed_symbols(example["source"]), (
                    f"{where}: the registry knows no symbol {entry['symbol']!r} of "
                    f"{example['source']} for {found.name}"
                )


# --- typography -------------------------------------------------------------------------------------

SUBSCRIPT = re.compile(
    r"_(\{(?:[^{}]|\{[^{}]*\})*\}|\\(?:mathrm|text)\{[^{}]*\}|\\[A-Za-z]+|[A-Za-z0-9])"
)
UPRIGHT = re.compile(r"\\(?:mathrm|text)\{[^{}]*\}")
GREEK_COMMANDS = {command.lstrip("\\") for command in GREEK.values()} | {"epsilon", "varrho"}


def italic_subscripts(math: str) -> list[str]:
    """Subscripts of a LaTeX expression that contain a letter set in italics."""
    found = []
    for match in SUBSCRIPT.finditer(math):
        token = match.group(1)
        inner = token[1:-1] if token.startswith("{") else token
        rest = UPRIGHT.sub("", inner)
        rest = re.sub(r"\\([A-Za-z]+)", lambda m: "" if m.group(1) in GREEK_COMMANDS else "x", rest)
        if re.search(r"[A-Za-z]", rest):
            found.append(match.group(0))
    return found


def test_latex_of_the_registry_sets_every_subscript_upright() -> None:
    assert latex("m_n") == r"m_{\mathrm{n}}"
    assert latex("rho_aP0*") == r"\rho_{\mathrm{aP0}}^{*}"
    assert latex("inv alpha_t") == r"\operatorname{inv}\,\alpha_{\mathrm{t}}"
    assert latex("epsilon_alpha") == r"\varepsilon_{\alpha}"
    assert latex("C_alpha_a") == r"C_{\alpha\mathrm{a}}"
    assert latex("E_sns/E_sni") == r"E_{\mathrm{sns}} / E_{\mathrm{sni}}"
    assert latex("z") == "z"
    for entry in quantities().values():
        if entry.symbol is not None:
            assert not italic_subscripts(latex(entry.symbol)), entry.symbol
    for bad in ("", "m_n$", r"\alpha", None, 3):
        with pytest.raises(InputRangeError):
            latex(bad)  # type: ignore[arg-type]


def test_the_typography_check_finds_italic_subscripts() -> None:
    assert italic_subscripts(r"d_b = d \cos\alpha_t") == ["_b", "_t"]
    assert italic_subscripts(r"h_{aP0}") == ["_{aP0}"]
    assert italic_subscripts(r"\rho_{fP}") == ["_{fP}"]
    assert not italic_subscripts(r"d_\mathrm{b} = d \cos\alpha_{\mathrm{t}} + z_1 + g_{\alpha}")
    assert not italic_subscripts(r"h_{\mathrm{aP0}}^{*} + x_{\mathrm{E}1}")


@pytest.mark.parametrize("path", sorted(NOTEBOOKS.glob("*.ipynb")), ids=lambda p: p.name)
def test_notebooks_set_every_subscript_upright(path: Path) -> None:
    cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
    offenders = []
    for cell in cells:
        if cell["cell_type"] != "markdown":
            continue
        text = "".join(cell["source"])
        for math in re.findall(r"\$\$(.+?)\$\$|\$([^$\n]+?)\$", text, flags=re.DOTALL):
            offenders += italic_subscripts(math[0] or math[1])
    assert not offenders, f"{path.name}: italic subscripts {sorted(set(offenders))}"


# --- generated documentation ------------------------------------------------------------------------


def test_quantities_table_is_current() -> None:
    path = DOCS / "quantities.md"
    assert path.is_file(), "run scripts/build_quantities.py"
    assert path.read_text(encoding="utf-8") == render_markdown(), (
        "quantities.md is stale: run scripts/build_quantities.py"
    )
    text = render_markdown()
    assert "| `centre_distance` | a_w | mm | Achsabstand eines Zylinderradpaares |" in text
    assert "## STplus 11.1F" in text and "## Ersetzte und ältere Normen" in text
