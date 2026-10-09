"""What STplus ships and presets is kept with its provenance (user decision 2026-09-30, ADR-109).

The tool databases are packaged verbatim, the defaults are transcribed from the manual and from
probe runs, and every record names program, version and release. gearcore applies none of it
silently: the importer reads a record or a file as STplus computes it and records every default
and every correction in its notes (user decision 2026-10-03, ADR-114).
"""

import hashlib
import re

import pytest

from gearcore.data import data_path
from gearcore.errors import InputRangeError, NotSupportedError
from gearcore.io.ste import load_ste, pair_input_from_ste, parse_ste
from gearcore.models.inputs import ToolKind, ToolProfile
from gearcore.quantities import quantities
from gearcore.stplus_program import (
    DIRECTORY,
    input_key_register,
    probe_listing,
    program_provenance,
    stplus_default,
    stplus_default_tool,
    stplus_defaults,
    stplus_tool,
    tool_database,
)

LABEL = "STplus 11.1F (Freigabe 01.12.2025)"
PROBES = (
    "defaults_minimal",
    "no_pressure_angle",
    "tool_consistent_record",
    "tool_contradicting_record",
    "tool_without_tip_rounding",
    # 2026-10-03: how STplus completes an incomplete input (ADR-114)
    "tool_without_addendum",
    "tool_for_one_gear_only",
    "tool_addendum_limited",
    "tool_tip_rounding_limited",
    "tool_root_dedendum_only_low",
    "tool_root_dedendum_only_high",
    "tool_root_form_height_only",
    "tool_root_both_heights",
    "tool_root_form_height_and_angle",
    "tool_root_dedendum_limited",
    "tool_root_dedendum_below_form_height",
    "tool_root_angle_only",
    "tool_root_form_height_limited",
    "tool_root_presets_of_the_configuration",
    "tool_root_other_pressure_angle",
    "tip_circle_cut_by_tool",
    "tip_circle_cut_then_edge_break",
    "tip_circle_cut_helical",
    "tip_circle_cut_with_chamfer",
    "pointed_by_edge_break",
    "helix_angle_from_centre_distance",
    "no_helix_angle_no_centre_distance",
    "upper_span_allowance_only",
    "profile_shift_sum",
    "tip_chamfer_default",
    "tip_chamfer_tangential_given",
    "tip_chamfer_limits",
    "tip_chamfer_helical",
    # 2026-10-03: probes of the verification review (gate report increment 3, G3X)
    "default_hob_at_twenty_eight_degrees",
    "default_hob_at_thirty_degrees",
    "tool_addendum_limited_without_tip_rounding",
    "tool_for_gear_one_only",
    "tip_circle_from_reference_profile_addendum",
    "tip_circle_per_din3960",
    "tip_chamfer_tangential_two_values",
    "tip_chamfer_limit_lowered",
    "tip_chamfer_limit_raised",
    "tool_edge_break_angle_ninety_degrees",
    "profile_shift_sum_with_centre_distance",
    "tip_chamfer_floor",
    # 2026-10-03: probes of the second verification review (G3Y)
    "tip_circle_given_with_other_definitions",
    "tool_edge_break_angle_eighty_five_degrees",
    "tool_edge_break_angle_eighty_eight_degrees",
    "tool_edge_break_angle_below_pressure_angle",
    "tool_edge_break_angle_equal_to_pressure_angle",
    "tool_edge_break_angle_ninety_degrees_without_form_height",
    "controls_first_value_holds",
    "control_outside_its_range",
    # 2026-10-03: where two deviations from STplus come from
    "helix_angle_without_profile_shift",
    "helix_angle_iteration_limit_tightened",
    "form_circle_limit_twenty_thousand",
    "form_circle_limit_fifty_thousand",
    # 2026-10-03: the controls of the tool limits and the ends of the ranges
    "tool_tip_land_control",
    "tool_tip_land_control_at_program_preset",
    "tool_space_control",
    "tool_root_space_control",
    "tool_root_space_control_without_effect",
    "tool_controls_at_the_ends_of_their_ranges",
    "controls_at_the_ends_of_their_ranges",
    # 2026-10-04: inspection dimensions as inputs and as choices of the program (increment 4)
    "span_of_both_gears",
    "span_with_upper_allowance_of_gear_one",
    "span_with_upper_allowance_of_gear_two",
    "span_with_upper_allowances_of_both_gears",
    "span_with_allowance_series",
    "span_of_gear_one_beside_x_of_gear_two",
    "span_of_gear_two_beside_x_of_gear_one",
    "span_beside_x_of_the_same_gear",
    "span_without_centre_distance",
    "span_of_one_gear_only",
    "spans_too_thick_for_the_centre_distance",
    "generating_profile_shift_given",
    "ball_dimension_given",
    "number_of_teeth_spanned_for_the_listing",
    "measuring_ball_of_the_program",
    "measuring_ball_of_the_program_larger_tip",
    "measuring_ball_given_above_the_tip",
    "measuring_ball_given_below_the_tip",
)
VALID_TOOLS = {
    "S_19_00376_(FI_61",
    "S_19_00374_(Cr_64",
    "S_19_00375_(Ai_67",
    "S_19_00372_(Id_71",
    "S_19_00373_(Id_72",
    "S_xx_xxxxx_(PT_82",
}
CONTRADICTING_TOOLS = {
    "S_19_00374_F_(_77",
    "S_19_00376_F_(_78",
    "S_19_00375_F_(_79",
    "S_19_00373_F_(_80",
    "S_19_00372_F_(_81",
    "S_xx_xxxxx_F_(_83",
}
GLOBAL_TOOLS = {"hochverz1", "hochverz2"}
BEYOND_THE_CONTRACT = {"S_19_00373_F_(_80", "S_19_00372_F_(_81"}
"""Records at alpha_n0 = 16 degrees whose root heights (3,0 and 4,0) STplus would reduce to
2,547, above the 2,5 the tool contract admits."""
_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


def _row(listing: str, label: str) -> list[float]:
    """Numbers a listing prints in the first line that contains ``label``."""
    for line in listing.splitlines():
        if label in line:
            tail = line.split(label, 1)[1]
            return [float(token) for token in tail.split() if _NUMBER.match(token)]
    raise AssertionError(f"listing has no line with {label!r}")


# --- provenance -----------------------------------------------------------------------------------


def test_program_version_is_the_one_the_installation_prints() -> None:
    provenance = program_provenance()
    assert (provenance.program, provenance.version, provenance.release) == (
        "STplus",
        "11.1F",
        "01.12.2025",
    )
    assert provenance.label == LABEL
    header = probe_listing("defaults_minimal")
    assert re.search(r"Programmname:\s+STplus\b", header)
    assert re.search(r"Version:\s+11\.1F\b", header)
    assert re.search(r"Freigabe:\s+01\.12\.2025\b", header)


def test_packaged_databases_are_the_files_of_the_provenance() -> None:
    provenance = program_provenance()
    assert [(f.stored, f.original, f.role) for f in provenance.files] == [
        ("tool_database_local.txt", "wkz/wkz.dat", "Werkzeugdatei_lokal"),
        ("tool_database_global.txt", "global/WKZ_GLOB.DAT", "Werkzeugdatei_global"),
        ("input_key_register.txt", "bin/DEFAULT.STY", "Register der Eingabeschluessel"),
    ]
    for file in provenance.files:
        stored = data_path(DIRECTORY, file.stored).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(stored).hexdigest() == file.stored_sha256, file.stored
        # the original had CRLF line endings: restoring them gives the hash of the original file
        assert hashlib.sha256(stored.replace(b"\n", b"\r\n")).hexdigest() == file.sha256
        assert len(stored.replace(b"\n", b"\r\n")) == file.bytes


# --- tool databases -------------------------------------------------------------------------------


def test_tool_database_keeps_every_record_and_entry() -> None:
    records = tool_database()
    assert set(records) == VALID_TOOLS | CONTRADICTING_TOOLS | GLOBAL_TOOLS
    assert {name for name, record in records.items() if record.database == "global"} == GLOBAL_TOOLS
    for file in program_provenance().files[:2]:
        text = data_path(DIRECTORY, file.stored).read_text(encoding=file.encoding)
        written = {
            section.name: tuple((entry.key, " ".join(entry.values)) for entry in section.entries)
            for section in parse_ste(text).sections
            if section.entries
        }
        assert written, file.stored
        for name, entries in written.items():
            assert records[name].entries == entries, name
            assert records[name].origin == f"{LABEL}, {file.original}"
        assert sum(len(e) for e in written.values()) == sum(
            1 for line in text.splitlines() if "=" in line
        ), "every KEY = value line of the file is kept"


def test_consistent_records_are_tool_contracts() -> None:
    records = tool_database()
    # every rack tool of the databases that names its profile angle is a contract, read as
    # STplus computes with it (ADR-114); the two of the global database take the angle of the gear
    assert {name for name, record in records.items() if record.profile is None} == (
        BEYOND_THE_CONTRACT | GLOBAL_TOOLS
    )
    assert {name for name, record in records.items() if not record.issues} == VALID_TOOLS
    tool = stplus_tool("S_19_00374_(Cr_64")
    assert isinstance(tool, ToolProfile) and tool.kind is ToolKind.RACK
    assert tool.name == "S_19_00374_(Cr_64"
    assert (tool.normal_module_mm, tool.profile_angle_deg) == (2.8, 17.5)
    assert (tool.addendum_factor, tool.tip_radius_factor) == (1.92036, 0.2)
    assert (tool.dedendum_factor, tool.root_form_height_factor) == (1.17786, 0.94643)
    assert tool.edge_break_angle_deg == 43.0
    for name in VALID_TOOLS:
        assert records[name].issues == (), name
        assert dict(records[name].entries)["WERKZEUGTYP"] == "1", "kept although undocumented"


def test_stplus_prints_the_factors_of_a_consistent_record() -> None:
    listing = probe_listing("tool_consistent_record")
    tool = stplus_tool("S_19_00374_(Cr_64")
    assert _row(listing, "Kopfhoehenfaktor (Wkz_Bezugspr.)") == [1.920, 1.920]
    assert _row(listing, "Wkz-Kopfabrundungsfaktor") == [tool.tip_radius_factor] * 2
    assert _row(listing, "Fuss-Hoehenfaktor (Wkz-Bezugspr.)") == [1.178, 1.178]
    assert _row(listing, "Fussform-Hoehenf.(Wkz-Bezugspr.)") == [0.946, 0.946]
    assert _row(listing, "Wkz-Normaleingriffswinkel") == [17.5, 17.5]
    assert "alfa_K01/2=  43.00/ 43.00" in listing


def test_contradicting_records_are_read_as_stplus_computes_them() -> None:
    """Factor and absolute value contradict in the records with '_F_' in the name. STplus computes
    with the factor and reduces what is not possible; the importer does the same, keeps the
    contradiction as an issue of the record and the corrections as its notes (ADR-114)."""
    records = tool_database()
    for name in CONTRADICTING_TOOLS:
        record = records[name]
        assert any("KOPFHOEHE = " in issue and "contradicts" in issue for issue in record.issues)
        if name in BEYOND_THE_CONTRACT:
            assert any("less than or equal to 2.5" in issue for issue in record.issues), name
            with pytest.raises(NotSupportedError, match="no tool contract"):
                stplus_tool(name)
            continue
        assert record.profile is not None and stplus_tool(name) == record.profile, name
        assert any("reduced" in note for note in record.notes), name
    record = records["S_19_00374_F_(_77"]
    entries = dict(record.entries)
    assert (entries["KOPFHOEHENFAKTOR"], entries["KOPFHOEHE"]) == ("1.6", "5.377")
    listing = probe_listing("tool_contradicting_record")
    profile = record.profile
    assert profile is not None
    assert _row(listing, "Kopfhoehenfaktor (Wkz_Bezugspr.)") == [1.6, 1.6], "the factor wins"
    assert profile.addendum_factor == 1.6
    assert _row(listing, "Wkz-Kopfabrundungsfaktor") == [0.383, 0.383], "record says 0.5"
    assert profile.tip_radius_factor == pytest.approx(0.383, abs=5e-4)
    assert _row(listing, "Fuss-Hoehenfaktor (Wkz-Bezugspr.)") == [2.317, 2.317], "record says 3.0"
    assert _row(listing, "Fussform-Hoehenf.(Wkz-Bezugspr.)") == [2.317, 2.317], "record says 3.0"
    assert profile.dedendum_factor == pytest.approx(2.317, abs=5e-4)
    assert profile.root_form_height_factor == pytest.approx(2.317, abs=5e-4)
    assert "Wkz.daten h_FfP0*, d_Ff0, alfa_Kn0 oder alfa_Kt0 fuer Rad 1 geaendert" in listing
    assert "Werkzeugdaten h_aP0*, d_a0, rho_aP0 oder rho_at0 fuer Rad 1 geaendert" in listing


def test_records_without_tip_rounding_get_the_preset_of_stplus() -> None:
    records = tool_database()
    for name in GLOBAL_TOOLS:
        # (G3X-10) the limits of STplus need a profile angle; these records take that of the gear
        assert records[name].profile is None
        assert any("profile angle" in issue for issue in records[name].issues), name
        with pytest.raises(NotSupportedError, match="profile angle"):
            stplus_tool(name)
        notes: list[str] = []
        profile = stplus_tool(
            name, normal_module_mm=2.0, normal_pressure_angle_deg=20.0, notes=notes
        )
        assert profile.tip_radius_factor == 0.25, name
        assert any("KOPFABRUNDUNGSFAKTOR not given" in note for note in notes), name
        with pytest.raises(InputRangeError, match="needs notes"):
            stplus_tool(name, normal_module_mm=2.0, normal_pressure_angle_deg=20.0)
    with pytest.raises(InputRangeError, match="notes are taken"):
        stplus_tool("S_19_00374_(Cr_64", notes=[])
    # at 25 degrees the full radius of hochverz2 (h_aP0* 1,5) lies below the preset rounding
    notes = []
    steep = stplus_tool(
        "hochverz2", normal_module_mm=2.0, normal_pressure_angle_deg=25.0, notes=notes
    )
    assert steep.tip_radius_factor == pytest.approx(0.135, abs=5e-4)
    assert any("the preset rho_aP0* = 0.25 reduced to the full radius" in note for note in notes)
    hochverz = stplus_tool(
        "hochverz1", normal_module_mm=2.0, normal_pressure_angle_deg=20.0, notes=[]
    )
    assert (hochverz.addendum_factor, hochverz.root_form_height_factor) == (1.45, 1.5)
    assert hochverz.dedendum_factor == 1.5 and hochverz.edge_break_angle_deg is None
    assert records["hochverz1"].entries == (
        ("KOPFHOEHENFAKTOR", "1.45"),
        ("FUSSHOEHENFAKTOR", "1.500"),
        ("FUSSFORMHOEHENFAKTOR", "1.500"),
    )
    listing = probe_listing("tool_without_tip_rounding")
    preset = stplus_default("tool_tip_radius")
    assert _row(listing, "Wkz-Kopfabrundungsfaktor") == [preset.value, preset.value]
    assert _row(listing, "Kopfhoehenfaktor (Wkz_Bezugspr.)") == [1.45, 1.45]
    assert _row(listing, "Wkz-Normalmodul") == [2.0, 2.0], "module of the gear"


def test_unknown_names_are_typed_errors() -> None:
    for name in ("nope", "", None, 7):
        with pytest.raises(InputRangeError):
            stplus_tool(name)  # type: ignore[arg-type]
        with pytest.raises(InputRangeError):
            stplus_default(name)  # type: ignore[arg-type]
        with pytest.raises(InputRangeError):
            probe_listing(name)  # type: ignore[arg-type]


# --- defaults -------------------------------------------------------------------------------------


def test_defaults_are_labelled_and_carry_their_evidence() -> None:
    defaults = stplus_defaults()
    registry = quantities()
    assert len(defaults) == 62
    for name, default in defaults.items():
        assert default.origin == LABEL, name
        if default.quantity is not None:
            assert default.quantity in registry, f"{name}: unknown quantity {default.quantity}"
        if default.status == "verified":
            evidence = (default.manual, default.probe, default.file)
            assert any(item is not None for item in evidence), name
            assert default.value is not None or default.rule is not None, name
            if default.manual is not None:
                assert "not transcribed" not in default.manual.text, name
        else:
            assert default.value is None, f"{name}: a located default carries no value"
        if default.probe is not None:
            match = re.match(r"([a-z_]+)[: ]", default.probe)
            assert match is not None and match.group(1) in PROBES, name
    located = sorted(name for name, default in defaults.items() if default.status == "located")
    assert located == ["empty_input_falls_back", "load_capacity_defaults", "shaper_cutter_defaults"]


def test_defaults_are_what_the_probe_run_shows() -> None:
    listing = probe_listing("defaults_minimal")
    tool = stplus_default_tool()
    assert LABEL in (tool.name or "")
    assert (tool.normal_module_mm, tool.profile_angle_deg) == (None, None), "those of the gear"
    assert _row(listing, "Kopfhoehenfaktor (Wkz_Bezugspr.)") == [tool.addendum_factor] * 2
    assert _row(listing, "Wkz-Kopfabrundungsfaktor") == [tool.tip_radius_factor] * 2
    assert _row(listing, "Fuss-Hoehenfaktor (Wkz-Bezugspr.)") == [tool.dedendum_factor] * 2
    assert _row(listing, "Fussform-Hoehenf.(Wkz-Bezugspr.)") == [tool.root_form_height_factor] * 2
    assert _row(listing, "Wkz-Normalmodul") == [2.0, 2.0]
    assert _row(listing, "Gesamt-Bearbeitungszugabe") == [0.0, 0.0]
    assert (
        _row(listing, "Verzahnungsqualitaet (DIN3961/63,Aug.78)")
        == [stplus_default("quality_din").value] * 2
    )
    assert stplus_default("tooth_thickness_allowance_series").value == "c25"
    assert re.search(r"Abmassreihe \(DIN 3967, Aug\.78\)[ .]+C\s+C\s", listing)
    assert _row(listing, "Toleranzreihe (DIN 3967, Aug.78)") == [25.0, 25.0]
    assert stplus_default("centre_distance_allowance").value == "js7"
    assert _row(listing, "Toleranzfeld JS") == [7.0]
    assert _row(listing, "Kopfkreisdurchmesser") == [44.0, 84.0], "d + 2 m_n (h_aP* + x)"
    assert _row(listing, "Messzaehnezahl") == [3.0, 5.0]
    assert _row(listing, "Messtueckdurchmesser") == [3.5, 3.5]
    assert re.search(r"verwendeter Wert:\s+0\.0002000000", listing)
    assert stplus_default("geometry_accuracy_limit").value == 0.0002


def test_input_key_register_is_kept() -> None:
    register = input_key_register()
    keys = [key for key, _ in register]
    assert (len(register), len(set(keys))) == (822, 816), "configurable input data"
    packaged = data_path(DIRECTORY, "input_key_register.txt").read_text(encoding="latin-1")
    assert packaged.count("\n[") + packaged.startswith("[") == 844, "with 22 internal entries"
    assert "Programminterne Steuerdaten" in packaged and "IWELLE" not in keys
    assert {key for key in keys if keys.count(key) > 1} == {
        "ANWENDUNGSFAKTOR",
        "BV2010",
        "KOPFRUECKN_FAKTOR_X_CA",
        "MASSENTEMPERATUR",
        "SCHMIERUNGSFAKTOR_X_S",
        "WERKZEUGTYP",
    }
    assert {key: value for key, value in register if value != "0"} == {
        "RAUHTIEFE_FLANKE": "5",
        "RAUHTIEFE_FUSS": "20",
        "SW_TRIKOR": "J",
        "NUMERISCHE_GEO_FEINHEIT": "170",
        "RECHTSFL_TRAEGT": "j",
    }
    default = stplus_default("register_default_sty")
    assert default.file == "input_key_register.txt"
    for key, value in (item.split(" = ") for item in str(default.value).split("; ")):
        assert (key, value) in register
    # the keys the importer maps are keys of the program
    assert {"KOPFHOEHENFAKTOR", "WKZ_NORMALMODUL", "BEARB_ZUGABE_WKZ", "BEARBEITUNGSZUGABE"} <= set(
        keys
    )


def test_pressure_angle_default_belongs_to_the_user_interface() -> None:
    default = stplus_default("normal_pressure_angle")
    assert (default.value, default.applies_to) == (20.0, "user interface")
    assert default.manual is not None and default.manual.page == 15
    rejected = probe_listing("no_pressure_angle")
    assert "sind unvollstaendig oder unzulaessig" in rejected
    assert re.search(r"ALN =\s+0\.00", rejected)
    assert "Geometrieberechnung nach DIN 3960" not in rejected.split("Ende des Echoprints")[1]


def test_gearcore_applies_no_stplus_default_silently() -> None:
    """The input of the probe runs in STplus with its default hob and its default tip circles.
    The importer reads it the same way (ADR-114) and says what it preset; the computing core
    still takes nothing it is not given."""
    ste = load_ste(data_path(DIRECTORY, "probes", "defaults_minimal", "input.ste"))
    imported = pair_input_from_ste(ste)
    listing = probe_listing("defaults_minimal")
    default = stplus_default_tool()
    for gear in imported.pair.gears.as_tuple():
        tool = gear.tool
        assert (tool.addendum_factor, tool.tip_radius_factor) == (1.25, 0.25)
        assert (tool.root_form_height_factor, tool.dedendum_factor) == (
            default.root_form_height_factor,
            default.dedendum_factor,
        )
    tips = [gear.tip_diameter_mm for gear in imported.pair.gears.as_tuple()]
    assert tips == _row(listing, "Kopfkreisdurchmesser") == [44.0, 84.0]
    assert imported.preset_tip_diameters == (True, True)
    assert sum("no tool block named" in note for note in imported.notes) == 2
    assert sum("KOPFKREISDM not given" in note for note in imported.notes) == 2
    # the core: a tool is a contract with its factors, a generation needs its tip diameters
    with pytest.raises(Exception, match="addendum_factor"):
        ToolProfile(protuberance_mm=0.0, machining_allowance_mm=0.0)
    assert stplus_default_tool().addendum_factor == 1.25
