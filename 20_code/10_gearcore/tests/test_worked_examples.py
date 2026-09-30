"""Generic runner for the norm worked examples in ``data/worked_examples``.

Every ``expected`` key of every example must be either implemented here or listed as pending with
the increment that will implement it — a misspelt or forgotten key fails the test. Every entry
names the quantity as the norm prints it (description, symbol, unit, printed text); the number the
tests use must equal the number in the printed text. The link of every key to the quantity
registry is checked in ``test_quantities.py``.
"""

import math
import re
from collections.abc import Callable
from typing import Any

import pytest

from gearcore import involute as iv
from gearcore import pair as pr
from gearcore.data import (
    load_worked_example,
    printed_number,
    printed_tolerance,
    worked_example_ids,
)
from gearcore.errors import ParseError
from gearcore.models.common import Pair
from gearcore.models.inputs import GearInput, PairInput, SpanMeasurement, ToolProfile
from gearcore.models.results import BasicGearGeometry, PairGeometry
from gearcore.trace import load_sources

Evaluator = Callable[[dict[str, Any], str | None], float]
ROLES = ("pinion", "wheel")
COMMON_KEYS = {"description", "meaning", "symbol", "unit", "printed", "note", "quantity"}
INPUT_KEYS = COMMON_KEYS | {"table", "factor_of_normal_module", "derived"}
EXPECTED_KEYS = COMMON_KEYS | {"page", "formula", "decimals"}
PRINTED_UNITS = {"mm", "µm", "deg", "rad", "m/s", "1/min", "-"}
EXAMPLE_1 = "iso_tr_6336_30_2022_annex_a_example_1"


def _angles(inputs: dict[str, Any]) -> tuple[float, float]:
    return (
        math.radians(inputs["normal_pressure_angle_deg"]["value"]),
        math.radians(inputs["helix_angle_deg"]["value"]),
    )


def _module(inputs: dict[str, Any]) -> float:
    value: float = inputs["normal_module_mm"]["value"]
    return value


def _transverse_module(inputs: dict[str, Any], role: str | None) -> float:
    return iv.transverse_module(_module(inputs), _angles(inputs)[1])


def _reference_diameter(inputs: dict[str, Any], role: str | None) -> float:
    assert role is not None
    return iv.reference_diameter(
        inputs["number_of_teeth"][role], _module(inputs), _angles(inputs)[1]
    )


def _inv_alpha_n(inputs: dict[str, Any], role: str | None) -> float:
    return iv.inv(_angles(inputs)[0])


def _alpha_t_deg(inputs: dict[str, Any], role: str | None) -> float:
    return math.degrees(iv.transverse_pressure_angle(*_angles(inputs)))


def _inv_alpha_t(inputs: dict[str, Any], role: str | None) -> float:
    return iv.inv(iv.transverse_pressure_angle(*_angles(inputs)))


def _base_diameter(inputs: dict[str, Any], role: str | None) -> float:
    assert role is not None
    alpha_n, beta = _angles(inputs)
    return iv.base_diameter(inputs["number_of_teeth"][role], _module(inputs), alpha_n, beta)


def _base_helix_deg(inputs: dict[str, Any], role: str | None) -> float:
    alpha_n, beta = _angles(inputs)
    return math.degrees(iv.base_helix_angle(beta, alpha_n))


def pair_of_example(inputs: dict[str, Any]) -> PairInput:
    """The pair as the norm gives it: values in parentheses are calculated (clause 4.2.18) and
    therefore not passed on. The centre distance and x_2 lead, x_1 follows (ADR-107). The span
    measurements of Table A.1 are passed on; gearcore does not evaluate spans yet (ADR-107)."""
    shift = inputs["profile_shift_coefficient"]
    hand = {"left": -1.0, "right": 1.0}[inputs["hand_of_helix"]["pinion"]]
    # Table A.1: h_fP = 1,4 m_n, rho_fP = 0,39 m_n, q = 0, s_pr = 0. The protuberance follows from
    # s_pr = pr - q (ISO 6336-3:2019 Table 2, p. 4)
    tools = {
        role: ToolProfile(
            addendum_factor=inputs["basic_rack_dedendum_mm"]["factor_of_normal_module"][role],
            tip_radius_factor=inputs["basic_rack_fillet_radius_mm"]["factor_of_normal_module"][
                role
            ],
            protuberance_mm=inputs["residual_fillet_undercut_mm"][role]
            + inputs["machining_allowance_mm"][role],
            machining_allowance_mm=inputs["machining_allowance_mm"][role],
        )
        for role in ROLES
    }
    gears = [
        GearInput(
            number_of_teeth=inputs["number_of_teeth"][role],
            profile_shift_coefficient=None if role in shift.get("derived", []) else shift[role],
            span=SpanMeasurement(
                span_measurement_mm=inputs["span_measurement_mm"][role],
                number_of_teeth_spanned=inputs["number_of_teeth_spanned"][role],
            ),
            face_width_mm=inputs["face_width_mm"][role],
            tip_diameter_mm=inputs["tip_diameter_mm"][role],
            tip_chamfer_radial_mm=0.0,  # Table A.1 names no tip chamfer
            tool=tools[role],
        )
        for role in ROLES
    ]
    return PairInput(
        normal_module_mm=_module(inputs),
        normal_pressure_angle_deg=inputs["normal_pressure_angle_deg"]["value"],
        helix_angle_deg=hand * inputs["helix_angle_deg"]["value"],
        centre_distance_mm=inputs["centre_distance_mm"]["value"],
        gears=Pair(pinion=gears[0], wheel=gears[1]),
    )


def _pair_geometry(inputs: dict[str, Any]) -> PairGeometry:
    return pr.compute_pair_geometry(pair_of_example(inputs))


def _of_pair(field: str) -> Evaluator:
    def evaluate(inputs: dict[str, Any], role: str | None) -> float:
        value = getattr(_pair_geometry(inputs), field)
        return float(getattr(value, role)) if role is not None else float(value)

    return evaluate


IMPLEMENTED: dict[str, Evaluator] = {
    "transverse_module_mm": _transverse_module,
    "reference_diameter_mm": _reference_diameter,
    "inv_alpha_n_rad": _inv_alpha_n,
    "transverse_pressure_angle_deg": _alpha_t_deg,
    "inv_alpha_t_rad": _inv_alpha_t,
    "base_diameter_mm": _base_diameter,
    "base_helix_angle_deg": _base_helix_deg,
    # pair geometry (increment 2)
    "gear_ratio": _of_pair("gear_ratio"),
    "transverse_working_pressure_angle_deg": _of_pair("transverse_working_pressure_angle_deg"),
    "working_pitch_diameter_mm": _of_pair("working_pitch_diameter_mm"),
    "normal_pitch_mm": _of_pair("normal_pitch_mm"),
    "transverse_pitch_mm": _of_pair("transverse_pitch_mm"),
    "transverse_base_pitch_mm": _of_pair("transverse_base_pitch_mm"),
    "transverse_contact_pitch_mm": _of_pair("transverse_contact_pitch_mm"),
    "length_of_path_of_contact_mm": _of_pair("length_of_path_of_contact_mm"),
    "sap_diameter_mm": _of_pair("sap_diameter_mm"),
    "transverse_contact_ratio": _of_pair("transverse_contact_ratio"),
    "overlap_ratio": _of_pair("overlap_ratio"),
    "total_contact_ratio": _of_pair("total_contact_ratio"),
}

GENERATION = "increment 3 (tool-based generation)"
LOAD_CAPACITY = "stage 2 (load capacity)"
PENDING: dict[str, str] = {
    "generating_profile_shift_coefficient": GENERATION,
    "generated_root_diameter_mm": GENERATION,
    "root_form_diameter_mm": GENERATION,
    "transverse_base_pitch_deviation_um": LOAD_CAPACITY,
    "pitch_line_velocity_m_s": LOAD_CAPACITY,
    "circumferential_velocity_m_s": LOAD_CAPACITY,
}


def _cases() -> list[tuple[str, str, str | None]]:
    cases: list[tuple[str, str, str | None]] = []
    for example_id in worked_example_ids():
        expected = load_worked_example(example_id)["expected"]
        for key, entry in expected.items():
            if key not in IMPLEMENTED:
                continue
            roles: list[str | None] = [*ROLES] if "pinion" in entry else [None]
            cases.extend((example_id, key, role) for role in roles)
    return cases


def _entries(example_id: str, section: str) -> list[tuple[str, dict[str, Any]]]:
    return list(load_worked_example(example_id)[section].items())


def _values(entry: dict[str, Any]) -> dict[str | None, tuple[Any, str]]:
    """(value, printed text) per gear, or under ``None`` for a quantity of the pair."""
    if "value" in entry:
        assert not set(ROLES) & set(entry), "either one value or one per gear"
        assert isinstance(entry["printed"], str)
        return {None: (entry["value"], entry["printed"])}
    assert set(ROLES) <= set(entry) and set(entry["printed"]) == set(ROLES)
    return {role: (entry[role], entry["printed"][role]) for role in ROLES}


def test_worked_examples_exist_and_are_well_formed() -> None:
    ids = worked_example_ids()
    assert ids, "no worked examples packaged"
    sources = load_sources()
    for example_id in ids:
        example = load_worked_example(example_id)
        assert example["id"] == example_id
        assert example["source"] in sources, f"{example_id}: unknown source {example['source']}"
        assert sources[example["source"]]["confirmed_by_user"] is True
        assert example["transcribed"]["method"] == "visual", (
            "values must be read from the rendered page"
        )
        assert isinstance(example["transcribed"]["confirmed_by_user"], bool)
        unknown = set(example["expected"]) - set(IMPLEMENTED) - set(PENDING)
        assert not unknown, (
            f"{example_id}: expected keys neither implemented nor pending: {unknown}"
        )
        assert not set(IMPLEMENTED) & set(PENDING)


@pytest.mark.parametrize("example_id", worked_example_ids())
@pytest.mark.parametrize("section, allowed", [("inputs", INPUT_KEYS), ("expected", EXPECTED_KEYS)])
def test_every_entry_names_the_quantity_as_the_norm_prints_it(
    example_id: str, section: str, allowed: set[str]
) -> None:
    inputs = load_worked_example(example_id)["inputs"]
    for key, entry in _entries(example_id, section):
        where = f"{example_id}.{section}.{key}"
        assert set(entry) <= allowed | {"value", *ROLES}, f"{where}: unknown field"
        assert isinstance(entry["description"], str) and entry["description"].strip(), where
        assert entry["symbol"] is None or entry["symbol"].strip(), where
        assert entry["unit"] in PRINTED_UNITS, f"{where}: unit {entry['unit']!r}"
        if section == "inputs":
            assert re.fullmatch(r"Table A\.\d", entry["table"]), where
        else:
            assert entry["page"] in (45, 46), where
            assert entry["formula"].startswith(entry["symbol"].split(" ")[0]), where
            assert not re.search(r"\|\^-1|tan\^", entry["formula"]), (
                f"{where}: write abs(x) and atan(x)"
            )
            assert isinstance(entry["decimals"], int), where
        factors = entry.get("factor_of_normal_module")
        for role, (value, printed) in _values(entry).items():
            if isinstance(value, bool | str):
                assert printed.strip().lower() in {str(value).lower(), "yes", "no"}, where
                continue
            number, decimals = printed_number(printed)
            if factors is None:
                assert number == value, f"{where} {role or ''}: {value!r} vs printed {printed!r}"
            else:
                # printed as a multiple of m_n: the factor is printed, the value follows
                assert number == factors[role], f"{where} {role}: factor vs printed {printed!r}"
                assert value == factors[role] * inputs["normal_module_mm"]["value"], where
            if section == "expected":
                assert decimals == entry["decimals"], f"{where}: printed decimals {decimals}"
            if entry["symbol"] is not None and "=" in printed:
                symbol = entry["symbol"].replace(" ", "")
                assert printed.replace(" ", "").startswith(symbol), f"{where}: {printed!r}"
        for role in entry.get("derived", []):
            assert role in ROLES and entry["note"], f"{where}: say what the value follows from"


def test_example_1_is_complete() -> None:
    """ISO/TR 6336-30:2022: Table A.1 has 19 rows, A.6 has 12 results on p. 45 and 13 on p. 46."""
    example = load_worked_example(EXAMPLE_1)
    inputs, expected = example["inputs"], example["expected"]
    tables = [entry["table"] for entry in inputs.values()]
    assert tables.count("Table A.1") == 19 and len(tables) == 21
    assert tables[-2:] == ["Table A.2", "Table A.5"], "the rows A.6 needs from other tables"
    pages = [entry["page"] for entry in expected.values()]
    assert pages == sorted(pages) and (pages.count(45), pages.count(46)) == (12, 13)
    assert [entry["description"] for entry in inputs.values()][:4] == [
        "Number of teeth",
        "Normal module",
        "Normal pressure angle",
        "Helix angle",
    ]


def test_example_1_basic_rack_holds_for_both_gears() -> None:
    """User review 2026-09-29: the norm prints the evaluated value once, it holds for both."""
    inputs = load_worked_example(EXAMPLE_1)["inputs"]
    dedendum, radius = inputs["basic_rack_dedendum_mm"], inputs["basic_rack_fillet_radius_mm"]
    assert (dedendum["pinion"], dedendum["wheel"]) == (11.2, 11.2)
    assert (radius["pinion"], radius["wheel"]) == (3.12, 3.12)
    assert dedendum["factor_of_normal_module"] == {"pinion": 1.4, "wheel": 1.4}
    assert "11,2 mm" in dedendum["printed"]["wheel"] and "3,12 mm" in radius["printed"]["wheel"]
    assert "11,2" not in dedendum["printed"]["pinion"], "printed for the wheel only"
    assert inputs["tip_relief_um"]["unit"] == inputs["root_relief_um"]["unit"] == "µm"


def test_example_1_x1_follows_from_x2_and_the_centre_distance() -> None:
    """User review 2026-09-29: x_2 = 0 and a lead, x_1 is printed in parentheses (ADR-107)."""
    shift = load_worked_example(EXAMPLE_1)["inputs"]["profile_shift_coefficient"]
    assert shift["derived"] == ["pinion"] and shift["wheel"] == 0.0
    assert shift["printed"]["pinion"] == "x_1 = (0,145 22)" and shift["pinion"] == 0.14522


def test_example_1_pair_reproduces_the_value_in_parentheses() -> None:
    """The centre distance and x_2 = 0 are given; gearcore derives the x_1 that the norm prints in
    parentheses (clause 4.2.18: calculated, for reference only)."""
    inputs = load_worked_example(EXAMPLE_1)["inputs"]
    pair = pair_of_example(inputs)
    assert pair.gears.pinion.profile_shift_coefficient is None, "x_1 is not passed on"
    assert pair.helix_angle_deg == -15.8, "the pinion of the example is left-handed"
    result = pr.compute_pair_geometry(pair)
    printed, decimals = printed_number(inputs["profile_shift_coefficient"]["printed"]["pinion"])
    assert abs(result.profile_shift_coefficient.pinion - printed) <= printed_tolerance(decimals)
    assert result.profile_shift_coefficient.wheel == 0.0
    assert result.centre_distance_mm == 500.0, "a given centre distance is fixed"
    # the spans of Table A.1 give x_E1 = 0,117 79 (printed p. 45; spans with allowance). Spans
    # are not evaluated yet: they are reported and not used (gate finding G2A-05, ADR-107)
    not_used = ["span_measurement_not_used"] * 2
    assert [w.code for w in result.warnings] == [*not_used, "root_form_diameter_not_checked"]
    # the root form diameters the norm prints (p. 45) lie below the start of the active profile,
    # so the limit of Eq. (66), (67) does not change the mesh of this example
    d_Ff = load_worked_example(EXAMPLE_1)["expected"]["root_form_diameter_mm"]
    limited = pr.compute_pair_geometry(
        pair, root_form_diameter_mm=Pair(pinion=d_Ff["pinion"], wheel=d_Ff["wheel"])
    )
    assert limited.sap_diameter_mm == result.sap_diameter_mm
    assert [w.code for w in limited.warnings] == not_used


def test_symbols_of_the_example_are_the_symbols_of_the_contract() -> None:
    """ISO/TR 6336-30:2022 and DIN ISO 21771:2014-08 use the same symbols for these quantities."""
    expected = load_worked_example(EXAMPLE_1)["expected"]
    fields = BasicGearGeometry.model_fields
    for key in (
        "transverse_module_mm",
        "reference_diameter_mm",
        "base_diameter_mm",
        "transverse_pressure_angle_deg",
        "base_helix_angle_deg",
    ):
        extra = fields[key].json_schema_extra
        assert isinstance(extra, dict) and extra["symbol"] == expected[key]["symbol"], key


def test_printed_number() -> None:
    assert printed_number("x_1 = (0,145 22)") == (0.14522, 5)
    assert printed_number("h_fP2 = 1,4 m_n = 11,2 mm") == (1.4, 1)
    assert printed_number("-0,027 48") == (-0.02748, 5)
    assert printed_number("−0,027 48") == (-0.02748, 5)
    assert printed_number("alpha_n = 20,00°") == (20.0, 2)
    assert printed_number("z_2 = 103") == (103.0, 0)
    assert printed_number("E_1 = 206 000 N/mm2") == (206000.0, 0)
    assert printed_number("W_k2 = 307,943 mm") == (307.943, 3)
    assert printed_number("n_1 = 360 min^-1") == (360.0, 0)
    for text in ("Left", "", "m_n = ", None, 8):
        with pytest.raises(ParseError):
            printed_number(text)  # type: ignore[arg-type]


@pytest.mark.parametrize("example_id, key, role", _cases())
def test_worked_example_value(example_id: str, key: str, role: str | None) -> None:
    example = load_worked_example(example_id)
    entry = example["expected"][key]
    reference = entry[role] if role is not None else entry["value"]
    tolerance = printed_tolerance(entry["decimals"]) + 1e-9
    value = IMPLEMENTED[key](example["inputs"], role)
    assert abs(value - reference) <= tolerance, (
        f"{example_id} {key} {role or ''}: gearcore {value!r} vs norm {reference!r} "
        f"(tolerance {tolerance:.1e}, {example['location']})"
    )
