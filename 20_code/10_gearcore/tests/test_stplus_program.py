"""What STplus ships and presets is kept with its provenance (user decision 2026-09-30, ADR-109).

The tool databases are packaged verbatim, the defaults are transcribed from the manual and from
probe runs, and every record names program, version and release. gearcore applies none of it
silently.
"""

import hashlib
import re

import pytest

from gearcore.data import data_path
from gearcore.errors import InputRangeError, NotSupportedError, ParseError
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
    assert {name for name, record in records.items() if record.profile is not None} == VALID_TOOLS
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


def test_contradicting_records_are_kept_but_are_no_contracts() -> None:
    """Factor and absolute value contradict in the records with '_F_' in the name. STplus computes with the
    factor and reduces what is not possible; gearcore keeps the record and rejects it."""
    records = tool_database()
    for name in CONTRADICTING_TOOLS:
        record = records[name]
        assert record.profile is None, name
        assert any("KOPFHOEHE = " in issue and "contradicts" in issue for issue in record.issues)
        assert any("no tool contract" in issue for issue in record.issues), name
        with pytest.raises(NotSupportedError, match="contradicts"):
            stplus_tool(name)
    entries = dict(records["S_19_00374_F_(_77"].entries)
    assert (entries["KOPFHOEHENFAKTOR"], entries["KOPFHOEHE"]) == ("1.6", "5.377")
    listing = probe_listing("tool_contradicting_record")
    assert _row(listing, "Kopfhoehenfaktor (Wkz_Bezugspr.)") == [1.6, 1.6], "the factor wins"
    assert _row(listing, "Wkz-Kopfabrundungsfaktor") == [0.383, 0.383], "record says 0.5"
    assert _row(listing, "Fuss-Hoehenfaktor (Wkz-Bezugspr.)") == [2.317, 2.317], "record says 3.0"
    assert "Wkz.daten h_FfP0*, d_Ff0, alfa_Kn0 oder alfa_Kt0 fuer Rad 1 geaendert" in listing


def test_records_without_tip_rounding_are_kept_but_are_no_contracts() -> None:
    records = tool_database()
    for name in GLOBAL_TOOLS:
        assert records[name].profile is None
        assert any("KOPFABRUNDUNGSFAKTOR" in issue for issue in records[name].issues), name
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
    assert len(defaults) == 24
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
    """The input of the probe runs in STplus with its default hob; gearcore asks for the tool."""
    ste = load_ste(data_path(DIRECTORY, "probes", "defaults_minimal", "input.ste"))
    with pytest.raises(ParseError, match="gearcore requires the tool explicitly"):
        pair_input_from_ste(ste)
    # falling back on the old default is an explicit, labelled choice
    assert stplus_default_tool().addendum_factor == 1.25
