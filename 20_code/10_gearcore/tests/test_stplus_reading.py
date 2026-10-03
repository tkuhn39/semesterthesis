"""The ``.ste`` importer reads a file as STplus 11.1F computes it (user decision 2026-10-03, ADR-114).

Every rule the importer applies is checked against a listing STplus printed: the probe runs of
``data/stplus_program/probes`` (incomplete and contradicting inputs) and the 18 fixture cases.
The rules themselves are ``stplus_program.stplus_tool_factors`` and its neighbours; where the
manual and the program disagree, the listings decide.
"""

import math
import re
from pathlib import Path

import numpy as np
import pytest
from scipy.optimize import brentq, minimize_scalar

from gearcore import generation as gn
from gearcore import involute as iv
from gearcore import pair as pr
from gearcore.data import data_path, stplus_case_dirs
from gearcore.errors import (
    GeometryInfeasibleError,
    InputRangeError,
    NotSupportedError,
    ParseError,
)
from gearcore.io.ste import SteImport, load_ste, pair_input_from_ste, parse_ste
from gearcore.models.common import Pair
from gearcore.models.inputs import PairInput
from gearcore.models.results import GearGeneration, GenerationResult
from gearcore.stplus_program import (
    DIRECTORY,
    probe_listing,
    stplus_helix_angle_deg,
    stplus_max_tool_addendum_factor,
    stplus_max_tool_dedendum_factor,
    stplus_max_tool_root_form_height_factor,
    stplus_max_tool_tip_radius_factor,
    stplus_residual_tip_thickness,
    stplus_tip_chamfer_height,
    stplus_tool_factors,
)

PRINTED = 5.1e-4
"""Half a unit of the third decimal a listing prints, with the rounding of the comparison."""

_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")
TOOL_ROWS = (
    ("Kopfhoehenfaktor (Wkz_Bezugspr.)", "addendum_factor"),
    ("Wkz-Kopfabrundungsfaktor", "tip_radius_factor"),
    ("Fussform-Hoehenf.(Wkz-Bezugspr.)", "root_form_height_factor"),
    ("Fuss-Hoehenfaktor (Wkz-Bezugspr.)", "dedendum_factor"),
)
REJECTED = {"no_pressure_angle", "no_helix_angle_no_centre_distance"}
"""Probes whose input STplus rejects; the importer raises ``ParseError`` for them."""
DATABASE_TOOLS = {
    "tool_consistent_record",
    "tool_contradicting_record",
    "tool_without_tip_rounding",
}
"""Probes that name a tool of the STplus tool databases (``stplus_program.stplus_tool``)."""
BEYOND_THE_CONTRACT = {
    "tool_addendum_limit_at_fifteen_degrees",
    "tool_root_form_height_limit_at_fifteen_degrees",
}
"""STplus reduces the addendum to 2,707 and the root form height to 2,726 there, above the 2,5
the tool contract admits: the importer reports that as a ``ParseError``."""
NOT_TRANSLATED = {
    "tip_circle_from_reference_profile_addendum",
    "tip_circle_per_din3960",
    "tool_edge_break_angle_eighty_eight_degrees",
}
"""Probes whose tip circle is defined by a key the importer does not translate, and the run
STplus aborted (``NotSupportedError``)."""


def _row(listing: str, label: str) -> list[float]:
    for line in listing.splitlines():
        if label in line:
            tail = line.split(label, 1)[1]
            return [float(token) for token in tail.split() if _NUMBER.match(token)]
    raise AssertionError(f"listing has no line with {label!r}")


def _interface(folder: Path, key: str) -> list[float]:
    """Numbers of ``KEY = a b`` in the interface file of a run (five decimals)."""
    for name in ("interface.sts.txt",):
        text = (folder / name).read_text(encoding="latin-1")
        for line in text.splitlines():
            if line.split("=")[0].strip() == key:
                return [float(token) for token in line.split("=", 1)[1].split()]
    raise AssertionError(f"{folder.name}: interface file has no key {key}")


def _probe(name: str) -> Path:
    return data_path(DIRECTORY, "probes", name)


def _probes() -> list[str]:
    return sorted(path.name for path in data_path(DIRECTORY, "probes").iterdir() if path.is_dir())


def _imported(folder: Path) -> SteImport:
    return pair_input_from_ste(load_ste(folder / "input.ste"))


def _generated(folder: Path, pair: PairInput) -> GenerationResult:
    """The generation with the tooth thickness allowances STplus printed (it presets the series
    c25, which gearcore evaluates with increment 5): the transverse allowance of the interface
    file times cos(beta), as ``parity.generation_data`` takes it."""
    upper = _interface(folder, "OBERES_ZAHNDICKENABM")
    lower = _interface(folder, "UNTERES_ZAHNDICKENABM")
    cos_beta = math.cos(math.radians(pair.helix_angle_deg))
    gears = []
    for index, gear in enumerate(pair.gears.as_tuple()):
        e_s, e_i = 1.0e3 * upper[index] * cos_beta, 1.0e3 * lower[index] * cos_beta
        gears.append(
            gear.model_copy(
                update={
                    "tooth_thickness_allowance_um": (e_s, min(e_s, e_i)),
                    "residual_tip_thickness_mm": None,
                }
            )
        )
    return gn.compute_generation(
        pair.model_copy(update={"gears": Pair(pinion=gears[0], wheel=gears[1])})
    )


# --- the tool as STplus completes it ---------------------------------------------------------------


@pytest.mark.parametrize(
    "folder",
    [
        _probe(n)
        for n in _probes()
        if n not in REJECTED | DATABASE_TOOLS | BEYOND_THE_CONTRACT | NOT_TRANSLATED
    ]
    + list(stplus_case_dirs()),
    ids=lambda path: path.name,
)
def test_tool_factors_are_those_the_listing_prints(folder: Path) -> None:
    """Addendum, tip rounding, root form height and dedendum of both tools as STplus lists them:
    presets where the file is silent, limits where it asks for too much."""
    listing = (folder / "report.sta.txt").read_text(encoding="latin-1")
    pair = _imported(folder).pair
    for label, field in TOOL_ROWS:
        listed = _row(listing, label)
        ours = [getattr(gear.tool, field) for gear in pair.gears.as_tuple()]
        assert ours == pytest.approx(listed, abs=PRINTED), (folder.name, field)


@pytest.mark.parametrize(
    "probe, gear, angle",
    [
        ("tool_root_form_height_only", 1, 30.0),
        ("tool_root_both_heights", 1, 30.0),
        ("tool_root_dedendum_only_high", 1, 30.0),
        ("tool_root_other_pressure_angle", 1, 35.0),
        ("tool_root_form_height_and_angle", 1, 45.0),
        ("tool_root_dedendum_limited", 1, 45.0),
        ("tip_circle_cut_then_edge_break", 1, 45.0),
        ("tool_root_angle_only", 1, 45.0),
    ],
)
def test_edge_break_angle_is_given_or_the_preset(probe: str, gear: int, angle: float) -> None:
    """alpha_K0 = alpha_n0 + 10 degrees where the tool has a flank between root form height and
    dedendum and gives no angle (manual p. 186); the listing names the angle it used."""
    tool = _imported(_probe(probe)).pair.gears.as_tuple()[gear - 1].tool
    assert tool.edge_break_angle_deg == pytest.approx(angle, abs=1e-12)
    listing = probe_listing(probe)
    if probe not in ("tool_root_dedendum_only_high", "tool_root_other_pressure_angle"):
        assert f"(alfa_K0 = {angle:.2f} grd)" in listing
    # a tool whose dedendum equals its root form height has no such flank and gets no angle
    plain = _imported(_probe("tool_root_dedendum_only_low")).pair.gears.pinion.tool
    assert plain.edge_break_angle_deg is None
    assert plain.dedendum_factor == plain.root_form_height_factor == 1.3


def test_a_lone_dedendum_below_the_preset_has_no_effect() -> None:
    """The user's example: FUSSHOEHENFAKTOR = 1.0 without FUSSFORMHOEHENFAKTOR (kst-E pinion,
    probe tool_root_dedendum_only_low) is run with 1,300 / 1,300; a lone 2.0 does take effect."""
    low = _imported(_probe("tool_root_dedendum_only_low"))
    assert (
        low.pair.gears.pinion.tool.dedendum_factor,
        low.pair.gears.pinion.tool.root_form_height_factor,
    ) == (1.3, 1.3)
    assert any("h_fP0* = 1.0 set to the root form height h_FfP0* = 1.3" in n for n in low.notes)
    high = _imported(_probe("tool_root_dedendum_only_high")).pair.gears.pinion.tool
    assert high.root_form_height_factor == 1.3
    assert high.dedendum_factor == pytest.approx(1.822, abs=PRINTED)
    kst_e = pair_input_from_ste(
        load_ste(next(p for p in stplus_case_dirs() if p.name == "kst_e") / "input.ste")
    )
    assert kst_e.pair.gears.pinion.tool.dedendum_factor == 1.3


def test_manual_and_program_disagree_and_the_program_is_followed() -> None:
    """Manual p. 224 presets h_Ff0* with 1,1; the program lists 1,300 (also in the manual's own
    example, p. 259), and the controls VB_... change nothing. Manual p. 186 sends h_f0 < h_Ff0
    to h_f0max; the program sets h_f0 = h_Ff0. (Known at the FZG, user 2026-10-03.)"""
    listing = probe_listing("tool_root_presets_of_the_configuration")
    assert "VB_FUSSFORMHOEHE_HFF0* = 1.0 1.0" in listing
    assert _row(listing, "Fussform-Hoehenf.(Wkz-Bezugspr.)") == [1.3, 1.3]
    assert _row(listing, "Fuss-Hoehenfaktor (Wkz-Bezugspr.)") == [1.3, 1.3]
    imported = _imported(_probe("tool_root_presets_of_the_configuration"))
    assert any("VB_FUSS" in note and "no effect" in note for note in imported.notes)
    below = probe_listing("tool_root_dedendum_below_form_height")
    assert _row(below, "Fuss-Hoehenfaktor (Wkz-Bezugspr.)")[0] == 0.9
    h_f0max = stplus_max_tool_dedendum_factor(0.9, math.radians(20.0), math.radians(30.0))
    assert h_f0max == pytest.approx(1.674, abs=PRINTED)  # what the manual's rule would print


@pytest.mark.parametrize(
    "probe, gear, alpha_n, h_Ff, alpha_K",
    [
        ("tool_root_dedendum_limited", 1, 20.0, 0.9, 45.0),
        ("pointed_by_edge_break", 1, 20.0, 0.9, 60.0),
        ("tool_root_dedendum_only_high", 1, 20.0, 1.3, 30.0),
        ("tool_root_other_pressure_angle", 1, 25.0, 0.9, 35.0),
        ("tool_root_dedendum_limit_at_fifteen_degrees", 1, 15.0, 0.9, 45.0),
        ("tool_root_dedendum_limit_at_twenty_five_degrees", 1, 25.0, 0.9, 45.0),
    ],
)
def test_largest_dedendum_of_a_tool_with_edge_break_flanks(
    probe: str, gear: int, alpha_n: float, h_Ff: float, alpha_K: float
) -> None:
    listing = probe_listing(probe)
    listed = _row(listing, "Fuss-Hoehenfaktor (Wkz-Bezugspr.)")[gear - 1]
    limit = stplus_max_tool_dedendum_factor(h_Ff, math.radians(alpha_n), math.radians(alpha_K))
    assert limit == pytest.approx(listed, abs=PRINTED)
    assert f"Wkz.daten h_FfP0*, d_Ff0, alfa_Kn0 oder alfa_Kt0 fuer Rad {gear} geaendert" in listing
    # the fixtures: the wheels of kst-B and kst-C (0,7388 and 0,6973 with 45 degrees)
    for h, printed in ((0.7388, 1.244), (0.6973, 1.218)):
        assert stplus_max_tool_dedendum_factor(
            h, math.radians(20.0), math.radians(45.0)
        ) == pytest.approx(printed, abs=PRINTED)


@pytest.mark.parametrize(
    "probe, alpha_n",
    [
        ("tool_root_form_height_limited", 20.0),
        ("tool_root_form_height_limit_at_fifteen_degrees", 15.0),
        ("tool_root_form_height_limit_at_twenty_five_degrees", 25.0),
        ("tool_contradicting_record", 17.5),
    ],
)
def test_largest_root_form_height(probe: str, alpha_n: float) -> None:
    listed = _row(probe_listing(probe), "Fussform-Hoehenf.(Wkz-Bezugspr.)")[0]
    limit = stplus_max_tool_root_form_height_factor(math.radians(alpha_n))
    assert limit == pytest.approx(listed, abs=PRINTED)
    # the tool space at that height is 0,110 m_n wide at every pressure angle
    assert math.pi / 2.0 - 2.0 * limit * math.tan(math.radians(alpha_n)) == pytest.approx(0.11)


@pytest.mark.parametrize(
    "probe, alpha_n",
    [
        ("tool_addendum_limited", 20.0),
        ("tool_addendum_limit_at_fifteen_degrees", 15.0),
        ("tool_addendum_limit_at_twenty_five_degrees", 25.0),
    ],
)
def test_largest_addendum_and_the_full_radius(probe: str, alpha_n: float) -> None:
    listing = probe_listing(probe)
    alpha = math.radians(alpha_n)
    addendum = stplus_max_tool_addendum_factor(alpha)
    assert addendum == pytest.approx(
        _row(listing, "Kopfhoehenfaktor (Wkz_Bezugspr.)")[0], abs=PRINTED
    )
    rounding = stplus_max_tool_tip_radius_factor(addendum, alpha)
    assert rounding == pytest.approx(_row(listing, "Wkz-Kopfabrundungsfaktor")[0], abs=PRINTED)
    assert "Werkzeugdaten h_aP0*, d_a0, rho_aP0 oder rho_at0 fuer Rad 1 geaendert" in listing


def test_full_radius_is_where_the_roundings_meet() -> None:
    """The limit of the tip rounding is the full radius of ``trochoid.tip_rounding``: the centre
    of the rounding lies on the centre line of the tool tooth."""
    from gearcore import trochoid as tr

    alpha = math.radians(20.0)
    limit = stplus_max_tool_tip_radius_factor(1.25, alpha)
    assert limit == pytest.approx(0.472, abs=PRINTED)  # probe tool_tip_rounding_limited
    rounding = tr.tip_rounding(20, 2.0, alpha, 0.0, 2.5, limit * 2.0, 0.0)
    assert rounding.centre_xi_mm == pytest.approx(0.0, abs=1e-12)
    with pytest.raises(GeometryInfeasibleError):
        tr.tip_rounding(20, 2.0, alpha, 0.0, 2.5, (limit + 1e-6) * 2.0, 0.0)
    with pytest.raises(GeometryInfeasibleError, match="pointed"):
        stplus_max_tool_tip_radius_factor(2.2, alpha)


def test_tool_rules_are_typed_and_recorded() -> None:
    notes: list[str] = []
    factors = stplus_tool_factors(
        "T",
        addendum=None,
        tip_radius=None,
        root_form_height=None,
        dedendum=None,
        edge_break_angle_deg=None,
        alpha_n_deg=20.0,
        notes=notes,
    )
    assert factors == {
        "addendum_factor": 1.25,
        "tip_radius_factor": 0.25,
        "root_form_height_factor": 1.3,
        "dedendum_factor": 1.3,
        "edge_break_angle_deg": None,
    }
    assert len(notes) == 4 and all("STplus default" in note for note in notes)
    # the limits need the profile angle: a tool without one is a parse error, whatever it gives
    for heights in ((0.9, 1.5), (None, None), (2.4, None)):
        with pytest.raises(ParseError, match="profile angle"):
            stplus_tool_factors(
                "T",
                addendum=1.25,
                tip_radius=0.25,
                root_form_height=heights[0],
                dedendum=heights[1],
                edge_break_angle_deg=None,
                alpha_n_deg=None,
                notes=[],
            )
    # a root form height beyond its limit with a larger dedendum is not probed
    with pytest.raises(NotSupportedError, match="not probed"):
        stplus_tool_factors(
            "T",
            addendum=1.25,
            tip_radius=0.25,
            root_form_height=2.5,
            dedendum=3.0,
            edge_break_angle_deg=None,
            alpha_n_deg=20.0,
            notes=[],
        )


def test_tool_keys_the_importer_does_not_translate_are_rejected() -> None:
    head = "$ Anfang\n$ T\nKOPFHOEHENFAKTOR = 1.25\nKOPFABRUNDUNGSFAKTOR = 0.25\n"
    for key in (
        "MASS_BZ0 = 1.0",
        "PROT_HOEHENFAKTOR = 0.5",
        "WKZ_NDPITCH = 10",
        "ZAHNDICKE_S_0 = 3.1",
    ):
        section = parse_ste(head + key + "\n$ Ende\n").section("T")
        assert section is not None
        with pytest.raises(NotSupportedError, match=key.split(" = ")[0]):
            from gearcore.io.ste import tool_from_section

            tool_from_section(section, [], normal_pressure_angle_deg=20.0)


def test_absolute_tool_dimensions_are_read_with_the_module() -> None:
    from gearcore.io.ste import tool_from_section

    section = parse_ste(
        "$ Anfang\n$ T\nKOPFHOEHE = 2.5\nKOPFABRUNDUNGSRADIUS = 0.5\nFUSSFORMHOEHE = 1.8\n"
        "FUSSHOEHE = 2.4\nKANTENBRECHWINKEL = 45\n$ Ende\n"
    ).section("T")
    assert section is not None
    notes: list[str] = []
    tool = tool_from_section(section, notes, normal_module_mm=2.0, normal_pressure_angle_deg=20.0)
    assert (tool.addendum_factor, tool.tip_radius_factor) == (1.25, 0.25)
    assert (tool.root_form_height_factor, tool.dedendum_factor) == (0.9, 1.2)
    assert sum("with the module 2.0" in note for note in notes) == 4
    with pytest.raises(ParseError, match="needs the module"):
        tool_from_section(section, [], normal_pressure_angle_deg=20.0)
    # factor and absolute value that contradict: the factor wins, as STplus computes
    both = parse_ste(
        "$ Anfang\n$ T\nKOPFHOEHENFAKTOR = 1.4\nKOPFHOEHE = 2.5\nKOPFABRUNDUNGSFAKTOR = 0.2\n$ Ende\n"
    ).section("T")
    assert both is not None
    notes = []
    tool = tool_from_section(both, notes, normal_module_mm=2.0, normal_pressure_angle_deg=20.0)
    assert tool.addendum_factor == 1.4
    assert any("contradicts KOPFHOEHENFAKTOR = 1.4" in note for note in notes)


# --- the gear and the pair as STplus completes them --------------------------------------------------


def test_helix_angle_from_the_centre_distance() -> None:
    """No SCHRAEGUNGSWINKEL: STplus iterates the helix angle from the centre distance and the
    sum of the profile shift coefficients (manual p. 16, GE12) and lists the angle it stopped
    at; gearcore solves the same equation to the precision of binary64."""
    folder = _probe("helix_angle_from_centre_distance")
    listing = probe_listing("helix_angle_from_centre_distance")
    imported = _imported(folder)
    listed = _row(listing, "Schraegungswinkel am Teilkreis")[0]
    assert listed == 12.1313
    assert imported.pair.helix_angle_deg == pytest.approx(listed, abs=2e-3)
    assert imported.pair.helix_angle_deg == stplus_helix_angle_deg(62.5, 2.0, 20.0, 20, 40, 0.6)
    assert any(note.startswith("SCHRAEGUNGSWINKEL not given → beta = ") for note in imported.notes)
    # the solution reproduces the centre distance; STplus's angle misses it by its tolerance
    result = _generated(folder, imported.pair)
    assert result.pair_geometry.centre_distance_mm == 62.5
    assert result.gears.wheel.profile_shift_coefficient == pytest.approx(0.2, abs=1e-12)
    assert _row(listing, "Profilverschiebungsfaktor (Nennw.)") == [0.4, 0.2001]
    # spur gears where the centre distance is that of beta = 0, no solution below it
    alpha_n = math.radians(20.0)
    alpha_wt = pr.working_pressure_angle_without_backlash(20, 40, alpha_n, 0.0, 0.6)
    spur = pr.centre_distance(20, 40, 2.0, alpha_n, 0.0, alpha_wt)
    assert spur == pytest.approx(61.125, abs=PRINTED)  # the probes with beta = 0 list 61.125
    assert stplus_helix_angle_deg(spur, 2.0, 20.0, 20, 40, 0.6) == 0.0
    with pytest.raises(GeometryInfeasibleError, match="no helix angle"):
        stplus_helix_angle_deg(61.0, 2.0, 20.0, 20, 40, 0.6)


def test_inputs_stplus_rejects_are_parse_errors() -> None:
    for name, match in (
        ("no_helix_angle_no_centre_distance", "SCHRAEGUNGSWINKEL missing"),
        ("no_pressure_angle", "EINGRIFFSWINKEL missing"),
    ):
        assert "sind unvollstaendig oder unzulaessig" in probe_listing(name)
        with pytest.raises(ParseError, match=match):
            _imported(_probe(name))


def test_profile_shift_sum_and_upper_allowance_alone() -> None:
    imported = _imported(_probe("profile_shift_sum"))
    listing = probe_listing("profile_shift_sum")
    assert _row(listing, "Profilverschiebungsfaktor (Nennw.)") == [0.4, 0.2]
    shifts = [gear.profile_shift_coefficient for gear in imported.pair.gears.as_tuple()]
    assert shifts == pytest.approx([0.4, 0.2], abs=1e-12)
    assert any(note.startswith("PR.VERSCH.SUMME = 0.6") for note in imported.notes)

    imported = _imported(_probe("upper_span_allowance_only"))
    listing = probe_listing("upper_span_allowance_only")
    assert _row(listing, "oberes Zahnweitenabmass") == _row(listing, "unteres Zahnweitenabmass")
    for gear, upper in zip(imported.pair.gears.as_tuple(), (-60.0, -80.0), strict=True):
        assert gear.span_allowance_um == (upper, upper)
    assert sum("UNTERES_ZAHNW_ABMASS not given" in note for note in imported.notes) == 2
    text = (_probe("upper_span_allowance_only") / "input.ste").read_text(encoding="latin-1")
    with pytest.raises(ParseError, match="without OBERES_ZAHNW_ABMASS"):
        pair_input_from_ste(parse_ste(text.replace("OBERES_ZAHNW_ABMASS", "UNTERES_ZAHNW_ABMASS")))


@pytest.mark.parametrize(
    "probe",
    ["defaults_minimal", "tool_for_one_gear_only", "tool_without_addendum", "profile_shift_sum"],
)
def test_tip_diameters_stplus_presets(probe: str) -> None:
    """No KOPFKREISDM: d_a = d + 2 m_n (1 + x), without the tip alteration k of Eq. (33)."""
    imported = _imported(_probe(probe))
    listed = _row(probe_listing(probe), "Kopfkreisdurchmesser")
    tips = [gear.tip_diameter_mm for gear in imported.pair.gears.as_tuple()]
    assert tips == pytest.approx(listed, abs=PRINTED)
    assert imported.preset_tip_diameters == (True, True)
    pair = imported.pair
    for gear, x in zip(
        pair.gears.as_tuple(),
        _row(probe_listing(probe), "Profilverschiebungsfaktor (Nennw.)"),
        strict=True,
    ):
        d = iv.reference_diameter(gear.number_of_teeth, pair.normal_module_mm, 0.0)
        assert gear.tip_diameter_mm == pytest.approx(d + 2.0 * pair.normal_module_mm * (1.0 + x))


# --- the generation of what the importer read ---------------------------------------------------------


@pytest.mark.parametrize(
    "probe, cut",
    [
        ("tip_circle_cut_by_tool", (True, False)),
        ("tip_circle_cut_helical", (True, True)),
        ("tip_circle_cut_with_chamfer", (True, False)),
        ("tip_circle_cut_then_edge_break", (True, False)),
        ("tool_root_dedendum_below_form_height", (True, False)),
        ("tool_root_dedendum_only_low", (False, False)),
    ],
)
def test_tip_circle_above_the_tool_root_line_is_cut(probe: str, cut: tuple[bool, bool]) -> None:
    """User decision 2026-10-03: cut and warn as STplus does ("Kopfkreis ... von Wkz mit
    Fusshoehenfaktor geschnitten"): d_a = d + 2 m_n (x_E + h_fP0*)."""
    folder = _probe(probe)
    listing = probe_listing(probe)
    imported = _imported(folder)
    result = _generated(folder, imported.pair)
    listed = _interface(folder, "KOPFKREISDURCHM")
    for index, (gear, given) in enumerate(
        zip(result.gears.as_tuple(), imported.pair.gears.as_tuple(), strict=True)
    ):
        # five decimals of the interface file, and the allowance it prints with five decimals
        assert gear.tip_diameter_mm == pytest.approx(listed[index], abs=2e-5), probe
        codes = [w.code for w in gear.warnings]
        assert ("tip_circle_cut_by_tool" in codes) == cut[index]
        assert (gear.tip_diameter_mm < given.tip_diameter_mm) == cut[index]
    if any(cut):
        assert "geschnitten" in listing
    else:
        assert "geschnitten" not in listing
    assert (
        result.pair_geometry.inputs.gears.pinion.tip_diameter_mm
        == result.gears.pinion.tip_diameter_mm
    )


@pytest.mark.parametrize(
    "probe",
    [
        "tool_root_form_height_only",
        "tool_root_both_heights",
        "tool_root_form_height_and_angle",
        "tool_root_dedendum_limited",
        "tip_circle_cut_then_edge_break",
    ],
)
def test_chamfer_by_the_edge_break_flank_of_the_tool(probe: str) -> None:
    """DIN 3960 Anhang A.3.1 with the angle the importer read or preset: tip form diameter,
    chamfer height and residual tip thickness as STplus prints them."""
    folder = _probe(probe)
    result = _generated(folder, _imported(folder).pair)
    gear = result.gears.pinion
    assert gear.tip_form_diameter_mm == pytest.approx(
        _interface(folder, "KOPFFORMKREISDURCHM")[0], abs=1e-4
    )
    assert gear.tip_chamfer_radial_mm == pytest.approx(
        _interface(folder, "KOPFKANTENBRUCH")[0], abs=1e-4
    )
    assert gear.residual_tip_thickness_mm == pytest.approx(
        _interface(folder, "RESTDICKE")[0], abs=1e-4
    )
    assert (
        f"Kopfkantenbruch an Rad 1 durch Werkzeug (alfa_K0 = {gear.tool_edge_break_angle_deg:.2f} grd)"
        in (probe_listing(probe))
    )


def test_tool_without_edge_break_flank_breaks_no_edge() -> None:
    folder = _probe("tool_root_angle_only")
    result = _generated(folder, _imported(folder).pair)
    assert "Kein Kopfkantenbruch durch Werkzeug 1 (alfa_K0 = 45.00 grd)" in probe_listing(
        "tool_root_angle_only"
    )
    gear = result.gears.pinion
    assert gear.tip_form_diameter_mm == gear.tip_diameter_mm and gear.tip_chamfer_radial_mm == 0.0
    assert [w.code for w in gear.warnings] == ["edge_break_angle_without_flank"]


def test_tooth_pointed_by_the_edge_break_is_a_typed_error() -> None:
    """STplus cuts the tip where the chamfer flanks meet ("Spitzer Zahn am Rad 1 durch
    Kantenbruch"); gearcore reports the tooth as not feasible (known limit GEN-13)."""
    folder = _probe("pointed_by_edge_break")
    assert "Spitzer Zahn am Rad 1 durch Kantenbruch" in probe_listing("pointed_by_edge_break")
    with pytest.raises(
        GeometryInfeasibleError, match="pointed by the chamfer; a smaller tip diameter"
    ):
        _generated(folder, _imported(folder).pair)


@pytest.mark.parametrize(
    "probe",
    [
        "tip_chamfer_default",
        "tip_chamfer_tangential_given",
        "tip_chamfer_tangential_two_values",
        "tip_chamfer_limits",
        "tip_chamfer_limit_lowered",
        "tip_chamfer_limit_raised",
        "tip_chamfer_floor",
        "tip_chamfer_helical",
        "tip_circle_cut_with_chamfer",
    ],
)
def test_tip_chamfer_given_as_an_input(probe: str) -> None:
    """Radial height limited to 0,20 m_n (or to the control MAX_KOPFKANTENBRUCH), residual
    thickness s_an - 2 (0,7 h_K) (or with the control TANG_BETRAG_ZU_H_KGF) but at least
    0,2 s_an, in the normal section (probes; manual p. 19 and p. 225)."""
    folder = _probe(probe)
    listing = probe_listing(probe)
    imported = _imported(folder)
    heights = [gear.tip_chamfer_radial_mm for gear in imported.pair.gears.as_tuple()]
    assert heights == pytest.approx(_interface(folder, "KOPFKANTENBRUCH"), abs=6e-6)
    result = _generated(folder, imported.pair)
    factor = 1.0 if probe.startswith("tip_chamfer_tangential") else None
    for index, gear in enumerate(result.gears.as_tuple()):
        s_an = gear.normal_tip_tooth_thickness_mm
        assert s_an == pytest.approx(_interface(folder, "ZAHNDICKE_KOPF")[index], abs=2e-5)
        residual = stplus_residual_tip_thickness(s_an, heights[index], tangential_factor=factor)
        assert residual == pytest.approx(_interface(folder, "RESTDICKE")[index], abs=2e-5), probe
        assert gear.tip_form_diameter_mm == pytest.approx(
            _interface(folder, "KOPFFORMKREISDURCHM")[index], abs=2e-5
        )
    assert "Kopfkantenbrueche an Rad 1/2 durch getrennten Fertigungsgang" in listing
    # the importer states the residual thickness itself, for the gear without allowance
    for gear in imported.pair.gears.as_tuple():
        assert gear.residual_tip_thickness_mm is not None
    assert sum("residual tip thickness of the chamfer → s_aK" in n for n in imported.notes) == 2


def test_chamfer_rules_of_the_program() -> None:
    assert stplus_tip_chamfer_height(0.6, 2.0) == 0.4  # "begrenzt auf 0.20 * m_n"
    assert stplus_tip_chamfer_height(0.6, 2.0, max_factor=0.4) == 0.6
    assert stplus_tip_chamfer_height(0.25, 2.0) == 0.25
    assert stplus_residual_tip_thickness(0.928, 0.3) == pytest.approx(0.508)
    assert stplus_residual_tip_thickness(0.423, 0.25) == pytest.approx(0.2 * 0.423)  # the floor
    assert stplus_residual_tip_thickness(0.928, 0.3, tangential_factor=1.0) == pytest.approx(0.328)
    limited = _imported(_probe("tip_chamfer_limits"))
    assert any("KOPFKANTENBRUCH = 0.6 limited to 0.4 mm" in note for note in limited.notes)
    assert "Rad 2: Eingabe zu Kopfkantenbruch begrenzt auf 0.20 * m_n" in probe_listing(
        "tip_chamfer_limits"
    )
    text = (_probe("tip_chamfer_default") / "input.ste").read_text(encoding="latin-1")
    # the controls of the tool limits are read (test_controls_of_the_tool_limits_...)
    moved = text.replace("$ Ende", "$ KONFIGURATIONSDATEN\nMIN_WKZ_ZAHNKOPFDICKE* = 0.3\n$ Ende")
    assert any(
        "MIN_WKZ_ZAHNKOPFDICKE* = 0.3 is used" in note
        for note in pair_input_from_ste(parse_ste(moved)).notes
    )
    # a control outside its range is not accepted by STplus: the preset holds (test_g3y08)
    outside = text.replace("$ Ende", "$ KONFIGURATIONSDATEN\nTANG_BETRAG_ZU_H_KGF = 2.0\n$ Ende")
    assert (
        pair_input_from_ste(parse_ste(outside)).pair
        == _imported(_probe("tip_chamfer_default")).pair
    )


# --- example 1 of the manual (p. 254 to 259) -----------------------------------------------------------


def test_manual_example_1_edge_break_of_a_pre_machining_tool() -> None:
    """Pinion z 25, m_n 5, beta 20 degrees, x 0,25, hob with h_FfP0* = 0,55 and h_fP0* = 1,23
    without an edge break angle, machining allowance q = 0,15 mm, finished by a grinding wheel.
    The manual prints (p. 257 to 259): x_E of the hob 0,3061, 'Kopfkantenbruch an Rad 1 durch
    Werkzeug (Winkel alfa_K0 = 30.00 grd)', d_Fa 144,536, h_K 0,493, Restdicke 3,039.

    The chamfer flank is generated by the hob at its x_E (DIN 3960 (A.3.03)), the involute it
    meets is the finished one at the upper allowance A_sne = -0,115 mm (p. 258)."""
    z, m_n, alpha_n, beta = 25, 5.0, math.radians(20.0), math.radians(20.0)
    d_a, x, A_sne, q = 145.522, 0.25, -0.115, 0.15
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta)
    d = iv.reference_diameter(z, m_n, beta)
    d_b = iv.base_diameter(z, m_n, alpha_n, beta)
    x_E = gn.generating_profile_shift_coefficient(x, m_n, alpha_n, 1.0e3 * A_sne)
    x_EV = gn.pre_machining_generating_profile_shift_coefficient(x_E, m_n, alpha_n, q)
    assert x_EV == pytest.approx(0.3061, abs=5.1e-5)
    factors = stplus_tool_factors(
        "Fraes_WKZ",
        addendum=1.5,
        tip_radius=0.25,
        root_form_height=0.55,
        dedendum=1.23,
        edge_break_angle_deg=None,
        alpha_n_deg=20.0,
        notes=[],
    )
    assert factors["edge_break_angle_deg"] == pytest.approx(30.0)
    assert (factors["root_form_height_factor"], factors["dedendum_factor"]) == (0.55, 1.23)
    alpha_tK = gn.edge_break_transverse_angle(math.radians(30.0), beta)
    d_bK = gn.edge_break_base_diameter(d, alpha_tK)
    s_tK = gn.edge_break_transverse_tooth_thickness(m_n, beta, 0.55 * m_n, alpha_t, alpha_tK, x_EV)
    psi_bK = gn.edge_break_base_half_angle(s_tK, d, alpha_tK)
    psi_bE = iv.base_tooth_thickness_half_angle(
        iv.tooth_thickness_half_angle(z, x_E, alpha_n), alpha_t
    )
    d_Fa = gn.tip_form_diameter_from_edge_break(d_b, d_bK, psi_bE, psi_bK, d_a)
    assert d_Fa == pytest.approx(144.536, abs=1.5e-3)
    assert gn.tip_chamfer_height(d_a, d_Fa) == pytest.approx(0.493, abs=1.5e-3)
    s_aK = gn.residual_tip_thickness(d_a, d_bK, psi_bK)
    assert gn.normal_tip_tooth_thickness(s_aK, d_a, d, beta) == pytest.approx(3.039, abs=PRINTED)


@pytest.mark.parametrize("probe", sorted(BEYOND_THE_CONTRACT))
def test_limits_of_stplus_beyond_the_tool_contract_are_parse_errors(probe: str) -> None:
    with pytest.raises(ParseError, match="less than or equal to 2.5"):
        _imported(_probe(probe))


# --- findings of the verification review of the fourth round (G3X, gate report increment 3) -----------

_FILE = (
    "$ Anfang\n$ Geometriedaten\nZAHNBREITE = 20 20\nNORMALMODUL = 2\nZAEHNEZAHL = 20 40\n"
    "PROFILVERSCHIEBUNG_N = 0.4 0.2\nSCHRAEGUNGSWINKEL = 0\nEINGRIFFSWINKEL = 20\n{more}$ Ende\n"
)
"""The pair of the probes: z 20/40, m_n 2, x 0,4/0,2; ``more`` takes further geometry lines and
blocks. Without them both gears get the hob and the tip circles STplus presets."""


def _file(more: str = "") -> SteImport:
    return pair_input_from_ste(parse_ste(_FILE.format(more=more)))


def test_g3x01_contour_of_a_tool_that_states_an_angle_but_has_no_flank() -> None:
    """A tool with KANTENBRECHWINKEL and no root heights has the dedendum of its root form height
    (1,3 / 1,3): a sharp corner, no edge break flank. A chamfer of its gear is the given one; the
    contour drew the edge break involute of the angle instead (tip land wider than the tooth)."""
    from gearcore import contour as ct

    tool = "KOPFHOEHENFAKTOR = 1.6\nKOPFABRUNDUNGSFAKTOR = 0.25\n"
    geometry = "KOPFKREISDM = 46.4 85.6\nKOPFKANTENBRUCH = 0.2 0.3\nWERKZEUG_VORVERZ. = T %\n$ T\n"
    with_angle = _file(geometry + tool + "KANTENBRECHWINKEL = 45\n")
    stated = with_angle.pair.gears.pinion.tool
    assert stated.edge_break_angle_deg == 45.0
    assert stated.dedendum_factor == stated.root_form_height_factor == 1.3
    result = gn.compute_generation(with_angle.pair)
    gear = result.gears.pinion
    assert "edge_break_angle_without_flank" in [w.code for w in gear.warnings]
    assert gear.tool_edge_break_angle_deg is None, "the result names the flank the tool has"
    assert gear.tip_chamfer_radial_mm == 0.2
    s_aK, d_a = gear.residual_tip_thickness_mm, gear.tip_diameter_mm
    assert s_aK == pytest.approx(0.4979 - 2.0 * 0.7 * 0.2, abs=5e-5)
    assert s_aK < gear.transverse_tip_tooth_thickness_mm
    points = np.asarray(ct.tooth_contour(result, "pinion").points)
    radius = np.hypot(points[:, 0], points[:, 1])
    on_tip = points[np.abs(radius - 0.5 * d_a) < 1e-9]
    land = float(np.max(on_tip[:, 0]) - np.min(on_tip[:, 0]))
    assert land == pytest.approx(d_a * math.sin(s_aK / d_a), rel=1e-9), "chord of the arc s_aK"
    # the same contour as with a tool that states no angle
    plain = gn.compute_generation(_file(geometry + tool).pair)
    assert np.array_equal(np.asarray(ct.tooth_contour(plain, "pinion").points), points)
    # without the shape of the chamfer the contour asks for it
    pinion = with_angle.pair.gears.pinion.model_copy(update={"residual_tip_thickness_mm": None})
    open_pair = with_angle.pair.model_copy(
        update={"gears": Pair(pinion=pinion, wheel=with_angle.pair.gears.wheel)}
    )
    with pytest.raises(InputRangeError, match="shape of the tip chamfer"):
        ct.tooth_contour(gn.compute_generation(open_pair), "pinion")


def test_g3x02_a_module_or_an_angle_of_zero_is_a_typed_error() -> None:
    from gearcore.io.ste import tool_from_section

    tools = "WERKZEUG_VORVERZ. = T T\n$ T\n"
    for more, match in (
        (tools + "WKZ_EINGRIFFSWINKEL = 0\nKOPFHOEHENFAKTOR = 0.05\n", "no rack tool"),
        (
            tools + "WKZ_NORMALMODUL = 0\nKOPFHOEHE = 2.5\nKOPFABRUNDUNGSFAKTOR = 0.25\n",
            "no module",
        ),
    ):
        with pytest.raises(ParseError, match=match):
            _file(more)
    for line, match in (
        ("EINGRIFFSWINKEL = 20", "EINGRIFFSWINKEL = 0"),
        ("NORMALMODUL = 2", "NORMALMODUL = 0"),
    ):
        zero = _FILE.format(more="").replace(line, line.split(" = ")[0] + " = 0")
        with pytest.raises(ParseError, match=match):
            pair_input_from_ste(parse_ste(zero))
    for limit in (stplus_max_tool_addendum_factor, stplus_max_tool_root_form_height_factor):
        with pytest.raises(InputRangeError, match="above zero"):
            limit(0.0)
    with pytest.raises(InputRangeError, match="above zero"):
        stplus_max_tool_tip_radius_factor(1.25, 0.0)
    with pytest.raises(InputRangeError, match="above zero"):
        stplus_max_tool_dedendum_factor(0.9, 0.0, math.radians(45.0))
    with pytest.raises(InputRangeError, match="not a finite number"):
        stplus_max_tool_dedendum_factor(-1.0e308, math.radians(20.0), math.radians(45.0))
    for module in (0.0, -2.0, "a", None):
        if module is None:
            continue
        with pytest.raises(InputRangeError):
            tool_from_section(
                None, [], name="hob", normal_module_mm=module, normal_pressure_angle_deg=20.0
            )  # type: ignore[arg-type]
    for angle in (0.0, 90.0, -20.0):
        with pytest.raises(ParseError, match="no rack tool"):
            tool_from_section(None, [], name="hob", normal_pressure_angle_deg=angle)


def test_g3x03_the_tool_rule_takes_finite_numbers_only() -> None:
    good: dict[str, float | None] = {
        "addendum": 1.25,
        "tip_radius": 0.25,
        "root_form_height": 0.9,
        "dedendum": 1.2,
        "edge_break_angle_deg": 45.0,
        "alpha_n_deg": 20.0,
    }
    assert stplus_tool_factors("T", notes=[], **good)["dedendum_factor"] == 1.2  # type: ignore[arg-type]
    for key in good:
        for bad in (float("nan"), float("inf"), float("-inf"), "1.25", [1.0], 1.0j, True):
            with pytest.raises(InputRangeError):
                stplus_tool_factors("T", notes=[], **{**good, key: bad})  # type: ignore[arg-type]
    for name in (None, 7, b"T"):
        with pytest.raises(InputRangeError, match="name of the tool"):
            stplus_tool_factors(name, notes=[], **good)  # type: ignore[arg-type]
    for angle in (0.0, -5.0, 90.5):
        with pytest.raises(InputRangeError, match="KANTENBRECHWINKEL"):
            stplus_tool_factors("T", notes=[], **{**good, "edge_break_angle_deg": angle})  # type: ignore[arg-type]
    for angle in (0.0, 90.0, -20.0):
        with pytest.raises(InputRangeError, match="profile angle"):
            stplus_tool_factors("T", notes=[], **{**good, "alpha_n_deg": angle})  # type: ignore[arg-type]
    # an addendum that is not positive is passed on for the contract to reject
    negative = stplus_tool_factors("T", notes=[], **{**good, "addendum": -1.0})  # type: ignore[arg-type]
    assert negative["addendum_factor"] == -1.0


@pytest.mark.parametrize(
    "probe, rounding, root",
    [
        ("default_hob_at_twenty_eight_degrees", 0.201, 1.3),
        ("default_hob_at_thirty_degrees", 0.110, 1.265),
    ],
)
def test_g3x04_presets_are_limited_like_given_values(
    probe: str, rounding: float, root: float
) -> None:
    """The hob STplus presets has the tip rounding 0,25 and the root form height 1,3 only where
    its limits admit them: at 28 degrees the full radius is 0,201, at 30 degrees 0,110 and the
    root form height 1,265 (listings). The importer applied the limits to given values only."""
    imported = _imported(_probe(probe))
    listing = probe_listing(probe)
    assert _row(listing, "Wkz-Kopfabrundungsfaktor") == [rounding, rounding]
    assert _row(listing, "Fussform-Hoehenf.(Wkz-Bezugspr.)") == [root, root]
    for gear in imported.pair.gears.as_tuple():
        assert gear.tool.tip_radius_factor == pytest.approx(rounding, abs=PRINTED)
        assert gear.tool.root_form_height_factor == pytest.approx(root, abs=PRINTED)
        assert gear.tool.dedendum_factor == gear.tool.root_form_height_factor
    assert (
        sum("the preset rho_aP0* = 0.25 reduced to the full radius" in n for n in imported.notes)
        == 2
    )
    assert sum("the preset h_FfP0* = 1.3 reduced" in n for n in imported.notes) == (
        2 if root < 1.3 else 0
    )
    gn.compute_generation(imported.pair)  # the tool is one the generation accepts
    # a given addendum beyond its limit takes the preset rounding with it
    tool = _imported(_probe("tool_addendum_limited_without_tip_rounding")).pair.gears.pinion.tool
    assert (tool.addendum_factor, tool.tip_radius_factor) == pytest.approx(
        (1.993, 0.086), abs=PRINTED
    )


def test_g3x05_other_definitions_of_the_tip_circle_are_not_translated() -> None:
    """Manual Bild 4.12 (p. 25): the tip circle is given by KOPFKREISDM or by one of five other
    keys. The importer set the preset d + 2 m_n (1 + x) and said "the default of STplus" although
    the file asked for something else."""
    for probe, key in (
        ("tip_circle_from_reference_profile_addendum", "K_HOEHENF_VERZ_BEZ_PR"),
        ("tip_circle_per_din3960", "DA_NACH_DIN3960"),
    ):
        with pytest.raises(NotSupportedError, match=key):
            _imported(_probe(probe))
    listing = probe_listing("tip_circle_from_reference_profile_addendum")
    assert _row(listing, "Kopfkreisdurchmesser") == [46.0, 84.4]  # d + 2 m_n (h_aP* + x)
    assert _row(listing, "Fuss-Hoehenfaktor (Wkz-Bezugspr.)") == [1.43, 1.3], "more than the tip"
    assert "Kopfkreise 1/2 nach DIN 3960 gemaess k*m_n =-0.126 mm festgelegt" in probe_listing(
        "tip_circle_per_din3960"
    )
    for line in (
        "BEZ_KOPFDICKE = 0.3 0.3",
        "DA_DURCH_WKZ = ja ja",
        "DA_NACH_DIN3960 = ja nein",
        "KOPFSPIELFAKTOR = 0.3",
        "K_HOEHENF_VERZ_BEZ_PR = 1.1",
    ):
        with pytest.raises(NotSupportedError, match=line.split(" = ")[0]):
            _file(line + "\n")
        with pytest.raises(NotSupportedError, match=line.split(" = ")[0]):
            _file("KOPFKREISDM = 46.4 %\n" + line + "\n")
    # with KOPFKREISDM of both gears the key defines nothing; it is reported as unmapped
    given = _file("KOPFKREISDM = 46.4 85.6\nK_HOEHENF_VERZ_BEZ_PR = 1.1\n")
    assert [g.tip_diameter_mm for g in given.pair.gears.as_tuple()] == [46.4, 85.6]
    assert "K_HOEHENF_VERZ_BEZ_PR" in given.unmapped_keys
    # "nein" and the placeholder define nothing either: the preset holds
    plain = _file("DA_NACH_DIN3960 = nein nein\nDA_DURCH_WKZ = nein nein\nBEZ_KOPFDICKE = % %\n")
    assert [g.tip_diameter_mm for g in plain.pair.gears.as_tuple()] == pytest.approx([45.6, 84.8])
    assert plain.preset_tip_diameters == (True, True)
    assert all(
        "STplus shortens it afterwards" in n for n in plain.notes if "KOPFKREISDM not given" in n
    )


def test_g3x06_a_control_is_one_value_for_the_stage() -> None:
    """Manual Bild 4.231 (p. 229): ``KEY = % (%)``. A second value has no effect on gear 2 (the
    importer read it as the value of gear 2), the use of a control is recorded, and controls the
    importer does not evaluate are named."""
    folder = _probe("tip_chamfer_tangential_two_values")
    assert "TANG_BETRAG_ZU_H_KGF = 1.0 0.5" in probe_listing(folder.name)
    tips = _interface(folder, "ZAHNDICKE_KOPF")
    assert _interface(folder, "RESTDICKE") == pytest.approx(
        [tips[0] - 2.0 * 1.0 * 0.1, tips[1] - 2.0 * 1.0 * 0.3], abs=2e-5
    ), "the factor 1,0 for both gears; 0,5 for gear 2 would leave 0,3 mm more"
    two = _imported(folder)
    assert any("TANG_BETRAG_ZU_H_KGF = 1 is used in place of the preset" in n for n in two.notes)
    assert any(
        "TANG_BETRAG_ZU_H_KGF has 2 values; the first holds for both" in n for n in two.notes
    )
    assert sum("s_an - 2 (1 h_K)" in n for n in two.notes) == 2
    generated = gn.compute_generation(two.pair)
    for given, gear in zip(two.pair.gears.as_tuple(), generated.gears.as_tuple(), strict=True):
        s_an = gear.normal_tip_tooth_thickness_mm
        assert given.residual_tip_thickness_mm == pytest.approx(
            s_an - 2.0 * 1.0 * given.tip_chamfer_radial_mm, rel=1e-12
        ), "spur gears: the transverse arc is the normal thickness"
    lowered = _imported(_probe("tip_chamfer_limit_lowered"))
    assert "Rad 1/2: Eingabe zu Kopfkantenbruch begrenzt auf 0.10 * m_n" in probe_listing(
        "tip_chamfer_limit_lowered"
    )
    assert [g.tip_chamfer_radial_mm for g in lowered.pair.gears.as_tuple()] == [0.2, 0.2]
    assert any(
        "MAX_KOPFKANTENBRUCH = 0.1 is used in place of the preset" in n for n in lowered.notes
    )
    assert sum("limited to 0.2 mm as STplus does (0.1 m_n)" in n for n in lowered.notes) == 2
    raised = _imported(_probe("tip_chamfer_limit_raised"))
    assert [g.tip_chamfer_radial_mm for g in raised.pair.gears.as_tuple()] == [0.25, 0.6]
    # without a control no such note
    assert not [n for n in _imported(_probe("tip_chamfer_default")).notes if "in place of" in n]
    # other controls are named, the circle in place of the ellipse is refused
    text = (_probe("tip_chamfer_default") / "input.ste").read_text(encoding="latin-1")
    named = text.replace(
        "$ Ende",
        "$ KONFIGURATIONSDATEN\nMIN_ZAHNKOPFDICKE* = 0.3\nABSCHALTEN_KORRGLIED = 0\n$ Ende",
    )
    notes = pair_input_from_ste(parse_ste(named)).notes
    assert "$ KONFIGURATIONSDATEN: MIN_ZAHNKOPFDICKE* not evaluated by the importer" in notes
    circle = text.replace("$ Ende", "$ KONFIGURATIONSDATEN\nABSCHALTEN_KORRGLIED = 1\n$ Ende")
    with pytest.raises(NotSupportedError, match="ABSCHALTEN_KORRGLIED = 1"):
        pair_input_from_ste(parse_ste(circle))
    # the rules keep the ranges of the controls (manual p. 225)
    with pytest.raises(InputRangeError, match="MAX_KOPFKANTENBRUCH"):
        stplus_tip_chamfer_height(0.1, 2.0, max_factor=0.6)
    with pytest.raises(InputRangeError, match="TANG_BETRAG_ZU_H_KGF"):
        stplus_residual_tip_thickness(1.0, 0.1, tangential_factor=1.0e9)


def test_g3x07_an_edge_break_angle_of_ninety_degrees_is_a_tool_without_flank() -> None:
    """Manual p. 186: "Ein Kopfüberschneider ohne Kantenbrecher kann mit h_Ff0 und
    alpha_Kn0 = 90° oder h_Ff0 = h_f0 eingegeben werden." The importer rejected the angle."""
    folder = _probe("tool_edge_break_angle_ninety_degrees")
    listing = probe_listing(folder.name)
    assert "KANTENBRECHWINKEL = 90" in listing and "FUSSHOEHENFAKTOR = 1.5" in listing
    assert _row(listing, "Fussform-Hoehenf.(Wkz-Bezugspr.)") == [0.9, 1.3]
    assert _row(listing, "Fuss-Hoehenfaktor (Wkz-Bezugspr.)") == [0.9, 1.3]
    imported = _imported(folder)
    tool = imported.pair.gears.pinion.tool
    assert (tool.root_form_height_factor, tool.dedendum_factor) == (0.9, 0.9)
    assert tool.edge_break_angle_deg is None
    assert any(
        "KANTENBRECHWINKEL = 90.0 deg → a tool without edge break flank" in n
        for n in imported.notes
    )
    result = _generated(folder, imported.pair)
    assert result.gears.pinion.tip_diameter_mm == pytest.approx(
        _interface(folder, "KOPFKREISDURCHM")[0], abs=2e-5
    )
    assert "Kopfkreis 1 von Wkz mit Fusshoehenfaktor geschnitten (h_fP0*1= 0.900)" in listing
    assert result.gears.pinion.tip_chamfer_radial_mm == 0.0


def test_g3x08_the_generation_of_a_cut_gear_stands_on_the_cut_circle() -> None:
    """Tooth depth, tip clearance, tip tooth thickness and contour of a gear whose tip the tool
    cuts, against the interface file of STplus (beta = 20 degrees, both gears cut)."""
    from gearcore import contour as ct

    folder = _probe("tip_circle_cut_helical")
    result = _generated(folder, _imported(folder).pair)
    tips = _interface(folder, "KOPFKREISDURCHM")
    for index, (role, gear) in enumerate(
        zip(("pinion", "wheel"), result.gears.as_tuple(), strict=True)
    ):
        assert gear.tip_diameter_mm == pytest.approx(tips[index], abs=2e-5)
        assert gear.tooth_depth_mm == pytest.approx(
            _interface(folder, "ZAHNHOEHE")[index], abs=2e-5
        )
        assert gear.normal_tip_tooth_thickness_mm == pytest.approx(
            _interface(folder, "ZAHNDICKE_KOPF")[index], abs=2e-5
        )
        points = np.asarray(ct.tooth_contour(result, role).points)  # type: ignore[arg-type]
        assert float(np.max(np.hypot(points[:, 0], points[:, 1]))) == pytest.approx(
            0.5 * gear.tip_diameter_mm, rel=1e-12
        )
    clearance = result.tip_clearance_mm
    assert [clearance.pinion, clearance.wheel] == pytest.approx(
        _interface(folder, "KOPFSPIEL"), abs=2e-5
    )


def test_g3x08_the_cut_starts_where_the_root_line_lies_below_the_tip_circle() -> None:
    pair = _file("KOPFKREISDM = 47.5 85.6\n").pair
    cut = gn.compute_generation(pair).gears.pinion
    root_line = cut.tip_diameter_mm
    assert root_line == pytest.approx(40.0 + 2.0 * 2.0 * (0.4 + 1.3), rel=1e-12)

    def generated(tip: float) -> GearGeneration:
        pinion = pair.gears.pinion.model_copy(update={"tip_diameter_mm": tip})
        return gn.compute_generation(
            pair.model_copy(update={"gears": Pair(pinion=pinion, wheel=pair.gears.wheel)})
        ).gears.pinion

    for above, is_cut in ((0.0, False), (1.0e-13, False), (1.0e-9, True), (1.0e-3, True)):
        gear = generated(root_line * (1.0 + above))
        assert ("tip_circle_cut_by_tool" in [w.code for w in gear.warnings]) == is_cut, above
        assert (gear.tip_diameter_mm == root_line) == (is_cut or above == 0.0), above


def test_g3x08_the_importer_stores_the_transverse_residual_thickness() -> None:
    """STplus forms the residual thickness of a chamfer in the normal section; the contract
    carries the arc on the tip circle in the transverse section (beta = 25 degrees)."""
    imported = _imported(_probe("tip_chamfer_helical"))
    generated = gn.compute_generation(imported.pair)
    for given, gear in zip(imported.pair.gears.as_tuple(), generated.gears.as_tuple(), strict=True):
        s_an, s_at = gear.normal_tip_tooth_thickness_mm, gear.transverse_tip_tooth_thickness_mm
        normal = stplus_residual_tip_thickness(s_an, given.tip_chamfer_radial_mm)
        assert given.residual_tip_thickness_mm == pytest.approx(normal * s_at / s_an, rel=1e-12)
        assert given.residual_tip_thickness_mm > 1.05 * normal
        assert gear.residual_tip_thickness_mm == given.residual_tip_thickness_mm


def test_g3x08_every_correction_of_a_tool_is_in_the_notes() -> None:
    for probe, text in (
        ("tool_root_both_heights", "KANTENBRECHWINKEL not given → alpha_K0 = 30.0 deg"),
        ("tool_addendum_limited", "KOPFHOEHENFAKTOR = 2.1 reduced to h_aP0* = 1.99"),
        ("tool_addendum_limited", "KOPFABRUNDUNGSFAKTOR = 0.25 reduced to the full radius"),
        ("tool_tip_rounding_limited", "KOPFABRUNDUNGSFAKTOR = 0.6 reduced to the full radius"),
        ("tool_root_form_height_limited", "FUSSFORMHOEHENFAKTOR = 2.5 reduced to h_FfP0* = 2.00"),
        ("tool_root_dedendum_limited", "h_fP0* = 1.5 reduced to h_f0max* = 1.34"),
    ):
        notes = _imported(_probe(probe)).notes
        assert any(note.startswith("tool 'T1': " + text) for note in notes), (probe, text)
    # a gear without a tool name gets the hob of STplus, not the tool of the other gear
    one = _imported(_probe("tool_for_gear_one_only"))
    pinion, wheel = one.pair.gears.pinion.tool, one.pair.gears.wheel.tool
    assert (pinion.addendum_factor, pinion.tip_radius_factor) == (1.4, 0.3)
    assert (wheel.addendum_factor, wheel.tip_radius_factor) == (1.25, 0.25)
    assert any(
        n.startswith("tool 'STplus default hob of gear 2': no tool block named") for n in one.notes
    )
    assert _row(probe_listing("tool_for_gear_one_only"), "Kopfhoehenfaktor (Wkz_Bezugspr.)") == [
        1.4,
        1.25,
    ]


@pytest.mark.parametrize("name", _probes())
def test_g3x09_typed_import_of_the_probe_is_current(name: str) -> None:
    """The record of a probe states what the importer of this version reads from its input."""
    import json

    from gearcore.errors import GearCoreError

    folder = _probe(name)
    recorded = json.loads((folder / "meta.json").read_text(encoding="utf-8"))["typed_import"]
    try:
        imported = _imported(folder)
    except GearCoreError as error:
        assert recorded == {"ok": False, "error": f"{type(error).__name__}: {error}"}
    else:
        assert recorded == {
            "ok": True,
            "unmapped_keys": list(imported.unmapped_keys),
            "notes": list(imported.notes),
        }


def test_g3x12_sum_of_the_profile_shift_coefficients_and_the_centre_distance() -> None:
    """With centre distance and helix angle given, STplus derives x_2 from the centre distance
    and does not use the sum (listing: 0,4000 / 0,1298 for a sum of 0,6)."""
    folder = _probe("profile_shift_sum_with_centre_distance")
    listing = probe_listing(folder.name)
    assert "PR.VERSCH.SUMME = 0.6" in listing
    assert _row(listing, "Profilverschiebungsfaktor (Nennw.)") == [0.4, 0.1298]
    imported = _imported(folder)
    shifts = [gear.profile_shift_coefficient for gear in imported.pair.gears.as_tuple()]
    assert shifts == [0.4, None] and imported.pair.centre_distance_mm == 61.0
    assert any("PR.VERSCH.SUMME = 0.6 is not used" in note for note in imported.notes)
    assert not [note for note in imported.notes if "of the file is not passed on" in note]
    assert "PR.VERSCH.SUMME" not in imported.unmapped_keys
    result = _generated(folder, imported.pair)
    assert result.gears.wheel.profile_shift_coefficient == pytest.approx(0.1298, abs=5.1e-5)
    # the sum with the coefficient of gear 2 only is not probed
    text = (folder / "input.ste").read_text(encoding="latin-1")
    with pytest.raises(NotSupportedError, match="not probed"):
        pair_input_from_ste(parse_ste(text.replace("= 0.4 %", "= % 0.2")))
    # without a helix angle the sum gives the angle; x_2 still follows from the centre distance
    free = pair_input_from_ste(
        parse_ste(text.replace("SCHRAEGUNGSWINKEL = 0\n", "").replace("61.0", "62.5"))
    )
    assert free.pair.helix_angle_deg == stplus_helix_angle_deg(62.5, 2.0, 20.0, 20, 40, 0.6)
    assert any("of PR.VERSCH.SUMME is not passed on" in note for note in free.notes)


def test_g3x12_the_helix_angle_is_found_at_both_ends_of_its_range() -> None:
    alpha_n = math.radians(20.0)
    for beta_deg in (0.0, 45.0):
        beta = math.radians(beta_deg)
        alpha_wt = pr.working_pressure_angle_without_backlash(20, 40, alpha_n, beta, 0.6)
        a_w = pr.centre_distance(20, 40, 2.0, alpha_n, beta, alpha_wt)
        # a centre distance within 1e-12 (relative) of the end of the range is that end
        for off in (-5.0e-13, 0.0, 5.0e-13):
            assert stplus_helix_angle_deg(a_w * (1.0 + off), 2.0, 20.0, 20, 40, 0.6) == beta_deg
    with pytest.raises(GeometryInfeasibleError, match="no helix angle"):
        stplus_helix_angle_deg(a_w * (1.0 + 1.0e-9), 2.0, 20.0, 20, 40, 0.6)


# --- findings of the second verification review (G3Y, gate report increment 3) --------------------------


def test_g3y01_other_tip_circle_keys_have_no_effect_where_the_tip_diameters_are_given() -> None:
    """The five keys together with KOPFKREISDM of both gears: the listing of STplus equals that
    of the file without them (tip circles, tool factors, tip clearance, tip tooth thickness),
    although K_HOEHENF_VERZ_BEZ_PR moves the tool dedendum where it defines the tip circle."""
    with_keys = probe_listing("tip_circle_given_with_other_definitions")
    plain = probe_listing("tip_circle_cut_by_tool")
    assert "K_HOEHENF_VERZ_BEZ_PR = 1.1 0.9" in with_keys and "DA_NACH_DIN3960 = ja ja" in with_keys
    for label in (
        "Kopfkreisdurchmesser",
        "Kopfspiel (Istwert)",
        "Zahndicke am Kopfkreis fuer A_We",
        "Fuss-Formkreisdurchmesser",
        "Fusskreisdurchmesser",
        *(row for row, _ in TOOL_ROWS),
    ):
        assert _row(with_keys, label) == _row(plain, label), label
    imported = _imported(_probe("tip_circle_given_with_other_definitions"))
    reference = _imported(_probe("tip_circle_cut_by_tool"))
    assert imported.pair == reference.pair
    assert set(imported.unmapped_keys) >= {
        "K_HOEHENF_VERZ_BEZ_PR",
        "KOPFSPIELFAKTOR",
        "BEZ_KOPFDICKE",
    }
    assert any(
        "K_HOEHENF_VERZ_BEZ_PR" in note and "no effect in STplus where KOPFKREISDM is given" in note
        for note in imported.notes
    )
    assert not [note for note in reference.notes if "no effect in STplus where" in note]


def test_g3y02_steep_edge_break_flanks() -> None:
    """STplus computes a flank of 85 degrees and aborts at 88 degrees (probes). The generation
    resolves a flank up to 89,9 degrees; beyond it DIN 3960 (A.3.05) loses its digits, and the
    values the importer let through between 89,9999 degrees and the band of the 90 degree rule
    were wrong (one negative)."""
    folder = _probe("tool_edge_break_angle_eighty_five_degrees")
    imported = _imported(folder)
    tool = imported.pair.gears.pinion.tool
    assert tool.dedendum_factor == pytest.approx(_interface(folder, "WKZ_FUSSHOEHENF")[0], abs=6e-6)
    assert tool.edge_break_angle_deg == 85.0
    gear = _generated(folder, imported.pair).gears.pinion
    assert gear.tip_diameter_mm == pytest.approx(_interface(folder, "KOPFKREISDURCHM")[0], abs=2e-5)
    assert gear.tip_form_diameter_mm == pytest.approx(
        _interface(folder, "KOPFFORMKREISDURCHM")[0], abs=2e-5
    )
    assert gear.tip_chamfer_radial_mm == pytest.approx(
        _interface(folder, "KOPFKANTENBRUCH")[0], abs=2e-5
    )
    # the residual thickness of so flat a flank changes by 2 tan(85 deg) = 23 um per um of radius;
    # STplus takes arcs as equal within m_n / 10 000 = 0,2 um (BOGENDIFFERENZ) and prints 0,02051
    assert gear.residual_tip_thickness_mm == pytest.approx(0.020019, abs=1e-6)
    assert gear.residual_tip_thickness_mm == pytest.approx(
        _interface(folder, "RESTDICKE")[0], abs=6e-4
    )

    aborted = probe_listing("tool_edge_break_angle_eighty_eight_degrees")
    assert "Iteration IREG =  10 fuer Rad  1 nach   100 Schritten abgebrochen" in aborted
    with pytest.raises(NotSupportedError, match="aborts its iteration at 88 deg"):
        _imported(_probe("tool_edge_break_angle_eighty_eight_degrees"))
    text = (folder / "input.ste").read_text(encoding="latin-1")
    for angle, error in (
        ("85.000001", NotSupportedError),
        ("89.999999", NotSupportedError),
        ("90.5", InputRangeError),
    ):
        with pytest.raises(error, match="KANTENBRECHWINKEL"):
            pair_input_from_ste(
                parse_ste(text.replace("KANTENBRECHWINKEL = 85", f"KANTENBRECHWINKEL = {angle}"))
            )
    # the band of the 90 degree rule: within 1e-12 (relative) of 90 degrees there is no flank
    band = pair_input_from_ste(
        parse_ste(text.replace("KANTENBRECHWINKEL = 85", "KANTENBRECHWINKEL = 89.99999999999995"))
    ).pair.gears.pinion.tool
    assert (band.dedendum_factor, band.edge_break_angle_deg) == (0.9, None)

    # the core: the chamfer of ever steeper flanks approaches 0,06 m_n tan(alpha_n) d_a / d from
    # below, steadily; beyond 89,9 degrees the generation refuses
    def residual(angle: float) -> float:
        flank = stplus_tool_factors(
            "T",
            addendum=1.6,
            tip_radius=0.25,
            root_form_height=0.9,
            dedendum=1.5,
            edge_break_angle_deg=min(angle, 85.0),
            alpha_n_deg=20.0,
            notes=[],
        )
        limit = stplus_max_tool_dedendum_factor(0.9, math.radians(20.0), math.radians(angle))
        steep = imported.pair.gears.pinion.tool.model_copy(
            update={"edge_break_angle_deg": angle, "dedendum_factor": limit}
        )
        assert flank["root_form_height_factor"] == 0.9
        pinion = imported.pair.gears.pinion.model_copy(update={"tool": steep})
        pair = imported.pair.model_copy(
            update={"gears": Pair(pinion=pinion, wheel=imported.pair.gears.wheel)}
        )
        generated = gn.compute_generation(pair).gears.pinion
        assert generated.residual_tip_thickness_mm is not None
        return generated.residual_tip_thickness_mm * 40.0 / generated.tip_diameter_mm

    closed = 0.06 * 2.0 * math.tan(math.radians(20.0))
    gaps = [closed - residual(angle) for angle in (85.0, 88.0, 89.0, 89.5, 89.9)]
    assert all(0.0 < later < earlier for earlier, later in zip(gaps, gaps[1:], strict=False))
    assert gaps[-1] == pytest.approx(0.1 * gaps[2], rel=0.05), (
        "the gap closes with 90 deg - alpha_K"
    )
    for angle in (89.91, 89.9999, 89.999999, 89.99999999):
        with pytest.raises(InputRangeError, match="steeper than 89.9 deg"):
            residual(angle)


def test_g3y02_edge_break_angle_at_or_below_the_pressure_angle() -> None:
    """An angle below the profile angle is replaced by alpha_n0 + 10 degrees, an angle equal to
    it is a tool without edge break flank (probes at 15 and 20 degrees, alpha_n = 20 degrees)."""
    below = _probe("tool_edge_break_angle_below_pressure_angle")
    listing = probe_listing(below.name)
    assert "KANTENBRECHWINKEL = 15" in listing
    assert "Kopfkantenbruch an Rad 1 durch Werkzeug (alfa_K0 = 30.00 grd)" in listing
    assert "Wkz.daten h_FfP0*, d_Ff0, alfa_Kn0 oder alfa_Kt0 fuer Rad 1 geaendert" in listing
    imported = _imported(below)
    tool = imported.pair.gears.pinion.tool
    assert (
        tool.edge_break_angle_deg == pytest.approx(30.0, abs=1e-12) and tool.dedendum_factor == 1.5
    )
    assert any(
        "KANTENBRECHWINKEL = 15.0 deg lies below the profile angle" in n for n in imported.notes
    )
    gear = _generated(below, imported.pair).gears.pinion
    reference = _probe("tool_root_both_heights")
    for key in ("KOPFFORMKREISDURCHM", "KOPFKANTENBRUCH", "RESTDICKE"):
        assert _interface(below, key) == _interface(reference, key), key
    assert gear.tip_form_diameter_mm == pytest.approx(
        _interface(below, "KOPFFORMKREISDURCHM")[0], abs=1e-4
    )

    equal = _probe("tool_edge_break_angle_equal_to_pressure_angle")
    listing = probe_listing(equal.name)
    assert "KANTENBRECHWINKEL = 20" in listing
    assert _row(listing, "Fuss-Hoehenfaktor (Wkz-Bezugspr.)") == [0.9, 1.3]
    assert "Kopfkreis 1 von Wkz mit Fusshoehenfaktor geschnitten (h_fP0*1= 0.900)" in listing
    imported = _imported(equal)
    tool = imported.pair.gears.pinion.tool
    assert (tool.root_form_height_factor, tool.dedendum_factor, tool.edge_break_angle_deg) == (
        0.9,
        0.9,
        None,
    )
    assert any("(h_fP0* = 1.5 is not used)" in note for note in imported.notes)
    assert _generated(equal, imported.pair).gears.pinion.tip_diameter_mm == pytest.approx(
        _interface(equal, "KOPFKREISDURCHM")[0], abs=2e-5
    )
    # 90 degrees without root heights: the presets 1,3 / 1,3, no flank, nothing "not used"
    plain = _probe("tool_edge_break_angle_ninety_degrees_without_form_height")
    assert _row(probe_listing(plain.name), "Fuss-Hoehenfaktor (Wkz-Bezugspr.)") == [1.3, 1.3]
    imported = _imported(plain)
    tool = imported.pair.gears.pinion.tool
    assert (tool.root_form_height_factor, tool.dedendum_factor, tool.edge_break_angle_deg) == (
        1.3,
        1.3,
        None,
    )
    assert not [note for note in imported.notes if "is not used" in note]
    assert "geschnitten" not in probe_listing(plain.name)


def test_g3y03_the_pair_geometry_announces_a_flank_only_where_the_tool_has_one() -> None:
    sharp = _file("KOPFKREISDM = 46.4 85.6\nWERKZEUG_VORVERZ. = T %\n$ T\nKANTENBRECHWINKEL = 45\n")
    assert sharp.pair.gears.pinion.tool.edge_break_angle_deg == 45.0
    codes = [w.code for w in pr.compute_pair_geometry(sharp.pair).warnings]
    assert "tip_form_diameter_not_generated" not in codes
    assert gn.compute_generation(sharp.pair).gears.pinion.tool_edge_break_angle_deg is None
    flank = _imported(_probe("tool_root_form_height_and_angle"))
    codes = [w.code for w in pr.compute_pair_geometry(flank.pair).warnings]
    assert "tip_form_diameter_not_generated" in codes


def test_g3y04_the_placeholder_is_not_given() -> None:
    """Manual §3.2: ``%`` stands for a value that is not given; the templates of the manual list
    every key with it. A control, a control that is not supported and a tool key given as the
    placeholder leave the preset in place."""
    plain = _file("KOPFKREISDM = 46.4 85.6\nKOPFKANTENBRUCH = 0.2 0.3\n")
    for control in (
        "MAX_KOPFKANTENBRUCH = %",
        "TANG_BETRAG_ZU_H_KGF = % %",
        "MIN_WKZ_ZAHNKOPFDICKE* = %",
        "MINDESTKOPFSPIEL = %",
    ):
        with_placeholder = _file(
            f"KOPFKREISDM = 46.4 85.6\nKOPFKANTENBRUCH = 0.2 0.3\n$ KONFIGURATIONSDATEN\n{control}\n"
        )
        assert with_placeholder.pair == plain.pair, control
        assert not [n for n in with_placeholder.notes if "in place of the preset" in n], control
    tool = "WERKZEUG_VORVERZ. = T T\n$ T\nKOPFHOEHENFAKTOR = 1.25\n"
    reference = _file(tool).pair
    for line in (
        "MASS_BZ0 = %",
        "KANTENBRECHWINKEL = %",
        "FUSSHOEHENFAKTOR = %",
        "PROT_HOEHENFAKTOR = % %",
    ):
        assert _file(tool + line + "\n").pair == reference, line
    with pytest.raises(NotSupportedError, match="MASS_BZ0"):
        _file(tool + "MASS_BZ0 = 1.0\n")


def test_g3y05_what_a_tool_block_holds_besides_its_keys_is_named() -> None:
    tool = "WERKZEUG_VORVERZ. = T T\n$ T\n"
    imported = _file(
        tool + "KOPFHOEHENFAKTOR = 1.4 9\nFUSSRUNDUNGSRADIUS = 0.3\nWERKZEUGTYP = 2\nFOO = 1\n"
    )
    assert imported.pair.gears.pinion.tool.addendum_factor == 1.4
    assert (
        "tool 'T': KOPFHOEHENFAKTOR has 2 values; the first is used (a tool block describes one tool)"
        in imported.notes
    )
    assert (
        "tool 'T': keys not read by the importer: FOO, FUSSRUNDUNGSRADIUS, WERKZEUGTYP"
        in imported.notes
    )
    with pytest.raises(ParseError, match="non-numeric token 'abc'"):
        _file(tool + "KOPFHOEHENFAKTOR = 1.4 abc\n")
    # a tool name must point to a tool block
    for name in ("Ende", "Geometriedaten", "ANFANG"):
        with pytest.raises(ParseError, match="block of the file structure"):
            _file(f"WERKZEUG_VORVERZ. = {name} %\n")
    with pytest.raises(ParseError, match="is no tool block"):
        _file("WERKZEUG_VORVERZ. = WST %\n$ WST\nELASTIZITAETSMODUL = 210000\n")
    # an empty block is the hob of STplus with its presets
    empty = _file("WERKZEUG_VORVERZ. = T %\n$ T\n").pair.gears.pinion.tool
    assert (empty.addendum_factor, empty.tip_radius_factor) == (1.25, 0.25)


def test_g3y06_every_control_the_importer_reads_goes_one_way() -> None:
    base = "KOPFKREISDM = 46.4 85.6\n$ KONFIGURATIONSDATEN\n"
    two = _file(base + "MINDESTKOPFSPIEL = 0.25 0.5\n")
    assert two.pair.min_tip_clearance_factor == 0.25
    assert (
        "$ KONFIGURATIONSDATEN: MINDESTKOPFSPIEL = 0.25 is used in place of the preset" in two.notes
    )
    assert any("MINDESTKOPFSPIEL has 2 values; the first holds" in note for note in two.notes)
    three = _file(base + "MINDESTKOPFSPIEL = 0.13 0.5 0.7\n")
    assert three.pair.min_tip_clearance_factor == 0.13
    outside = _file(base + "MINDESTKOPFSPIEL = 5\n")
    assert outside.pair.min_tip_clearance_factor is None
    assert any(
        "MINDESTKOPFSPIEL = 5 does not lie between 0.001 and 0.99" in n for n in outside.notes
    )
    with pytest.raises(NotSupportedError, match="ABSCHALTEN_KORRGLIED = 1"):
        _file(base + "ABSCHALTEN_KORRGLIED = 1 0\n")
    flag = _file(base + "ABSCHALTEN_KORRGLIED = 0 1\n")
    assert any("ABSCHALTEN_KORRGLIED has 2 values; the first holds" in note for note in flag.notes)
    with pytest.raises(ParseError, match="non-numeric token 'abc'"):
        _file(base + "MAX_KOPFKANTENBRUCH = 0.1 abc\n")


def test_g3y07_what_no_test_pinned() -> None:
    from gearcore.io.ste import tool_from_section
    from gearcore.stplus_program import stplus_tool

    # the sum of the profile shift coefficients beside both coefficients, and with gear 2 only
    with pytest.raises(NotSupportedError, match="exactly one gear"):
        _file("PR.VERSCH.SUMME = 0.7\n")
    text = _FILE.format(more="PR.VERSCH.SUMME = 0.6\nACHSABSTAND = 62.5\n").replace(
        "PROFILVERSCHIEBUNG_N = 0.4 0.2\nSCHRAEGUNGSWINKEL = 0\n", "PROFILVERSCHIEBUNG_N = % 0.2\n"
    )
    with pytest.raises(
        NotSupportedError, match=r"gear 2\s+only \(no SCHRAEGUNGSWINKEL\) is not probed"
    ):
        pair_input_from_ste(parse_ste(text))
    # (the ranges of the controls are open intervals: test_the_range_of_a_control_is_an_open_interval)
    # a record beyond the tool contract stays a NotSupportedError with the data of a gear
    with pytest.raises(NotSupportedError, match="no tool contract"):
        stplus_tool(
            "S_19_00373_F_(_80", normal_module_mm=2.0, normal_pressure_angle_deg=20.0, notes=[]
        )
    # the data of the gear are numbers
    for angle in ("20", [20.0], float("nan")):
        with pytest.raises(InputRangeError, match="normal pressure angle of the gear"):
            tool_from_section(None, [], name="hob", normal_pressure_angle_deg=angle)  # type: ignore[arg-type]
    # "nein" in any case defines no tip circle
    upper = _file("DA_NACH_DIN3960 = NEIN Nein\n")
    assert upper.preset_tip_diameters == (True, True)
    # no preset tip circle where the profile shift coefficients do not follow from the file
    spans = _FILE.format(
        more="ACHSABSTAND = 61.125\nZAHNWEITE = 15.5 27.8\nMESSZAEHNEZAHL = 3 5\n"
    ).replace("PROFILVERSCHIEBUNG_N = 0.4 0.2\n", "")
    open_tips = pair_input_from_ste(parse_ste(spans))
    assert [gear.tip_diameter_mm for gear in open_tips.pair.gears.as_tuple()] == [None, None]
    assert (
        sum("KOPFKREISDM not given; the default of STplus needs" in n for n in open_tips.notes) == 2
    )


def test_g3y08_the_first_value_of_a_control_holds_and_one_outside_its_range_does_not() -> None:
    """Both earlier probes put the stricter value first; with the order reversed the first value
    still holds. A value outside the range of the control is not accepted: the preset stays."""
    folder = _probe("controls_first_value_holds")
    listing = probe_listing(folder.name)
    assert (
        "TANG_BETRAG_ZU_H_KGF = 0.5 1.0" in listing and "MAX_KOPFKANTENBRUCH = 0.4 0.1" in listing
    )
    assert _interface(folder, "KOPFKANTENBRUCH") == [0.3, 0.3], "0.1 m_n would limit them to 0.2"
    tips = _interface(folder, "ZAHNDICKE_KOPF")
    assert _interface(folder, "RESTDICKE") == pytest.approx(
        [tips[0] - 2.0 * 0.5 * 0.3, tips[1] - 2.0 * 0.5 * 0.3], abs=2e-5
    )
    imported = _imported(folder)
    assert [g.tip_chamfer_radial_mm for g in imported.pair.gears.as_tuple()] == [0.3, 0.3]
    assert sum("s_an - 2 (0.5 h_K)" in note for note in imported.notes) == 2

    folder = _probe("control_outside_its_range")
    assert "TANG_BETRAG_ZU_H_KGF = 2.0" in probe_listing(folder.name)
    tips = _interface(folder, "ZAHNDICKE_KOPF")
    assert _interface(folder, "RESTDICKE") == pytest.approx(
        [tips[0] - 2.0 * 0.7 * 0.1, tips[1] - 2.0 * 0.7 * 0.3], abs=2e-5
    ), "the preset 0,7"
    imported = _imported(folder)
    assert any(
        "TANG_BETRAG_ZU_H_KGF = 2 does not lie between 0.3 and 1.5: STplus does not accept it" in n
        for n in imported.notes
    )
    assert sum("s_an - 2 (0.7 h_K)" in note for note in imported.notes) == 2


def test_g3y09_the_limits_are_finite_or_typed() -> None:
    for limit in (stplus_max_tool_addendum_factor, stplus_max_tool_root_form_height_factor):
        with pytest.raises(InputRangeError, match="not a finite number"):
            limit(5.0e-324)
    with pytest.raises(GeometryInfeasibleError, match="no room for an edge break flank"):
        stplus_max_tool_dedendum_factor(2.2, math.radians(20.0), math.radians(45.0))
    # at the largest root form height the rule admits there is room
    highest = stplus_max_tool_root_form_height_factor(math.radians(20.0))
    assert (
        stplus_max_tool_dedendum_factor(highest, math.radians(20.0), math.radians(45.0)) > highest
    )


def test_g3y05_the_first_position_of_a_tool_key_holds_its_value() -> None:
    tool = "WERKZEUG_VORVERZ. = T T\n$ T\nKOPFABRUNDUNGSFAKTOR = 0.3\n"
    shifted = _file(tool + "KOPFHOEHENFAKTOR = % 1.4\n")
    assert shifted.pair.gears.pinion.tool.addendum_factor == 1.25, "the preset: no first value"
    assert shifted.pair == _file(tool).pair


# --- where the deviations from STplus come from (question of the user, 2026-10-03) -----------------------


@pytest.mark.parametrize(
    "probe, sum_x",
    [
        ("helix_angle_from_centre_distance", 0.6),
        ("helix_angle_iteration_limit_tightened", 0.6),
        ("helix_angle_without_profile_shift", 0.0),
    ],
)
def test_stplus_ends_its_helix_angle_iteration_before_the_centre_distance_is_met(
    probe: str, sum_x: float
) -> None:
    """Without SCHRAEGUNGSWINKEL STplus iterates the helix angle from the centre distance. Its
    angle is always slightly too small: the centre distance that belongs to it lies up to
    0,43 um below the given one (18 pairs at m_n 1 to 8, three runs kept), and STplus puts the
    remainder into x_2. No documented control changes that (GRENZE_BETA_ITERATION at its lower
    bound gives the same angle). gearcore solves the equation; without profile shift the
    solution is elementary, arccos(m_n (z_1 + z_2) / (2 a))."""
    listing = probe_listing(probe)
    listed = _row(listing, "Schraegungswinkel am Teilkreis")[0]
    alpha_n, beta = math.radians(20.0), math.radians(listed)
    alpha_wt = pr.working_pressure_angle_without_backlash(20, 40, alpha_n, beta, sum_x)
    short = 62.5 - pr.centre_distance(20, 40, 2.0, alpha_n, beta, alpha_wt)
    assert 0.0 < short < 5.0e-4, (
        "the centre distance at STplus's angle is short by less than 0,5 um"
    )
    exact = stplus_helix_angle_deg(62.5, 2.0, 20.0, 20, 40, sum_x)
    assert 0.0 < exact - listed < 2.0e-3
    assert _imported(_probe(probe)).pair.helix_angle_deg == exact
    # what STplus is short in the centre distance it adds to x_2
    assert _interface(_probe(probe), "SUMME_X")[0] > sum_x + 5.0e-5
    if sum_x == 0.0:
        assert exact == pytest.approx(math.degrees(math.acos(60.0 / 62.5)), abs=1e-12)
        assert listed == 16.2598 and round(exact, 4) == 16.2602
    else:
        assert listed == 12.1313, "the same angle with and without the tightened control"


def test_stplus_root_form_circle_approaches_the_intersection_as_its_arc_limit_is_tightened() -> (
    None
):
    """The root form diameter STplus prints for an undercut gear is the result of an iteration
    that takes two tooth thickness arcs as equal within m_n / BOGENDIFFERENZ (manual p. 227).
    With the limit tightened from the preset 10 000 to 20 000 and 50 000 its value for the
    pinion of fzg_c moves onto the intersection of fillet and involute gearcore computes:
    6,4 um, 2,6 um, 0,7 um. This is what ``parity.FORM_CIRCLE_ACCURACY_MM`` allows for."""
    from gearcore.parity import compute_generation_from_data, generation_data

    data = generation_data("fzg_c")
    ours = compute_generation_from_data(data, data.values).gears.pinion
    assert ours.undercut and ours.root_form_diameter_mm == pytest.approx(67.678697, abs=1e-6)
    preset = next(p for p in stplus_case_dirs() if p.name == "fzg_c")
    runs = (
        (preset, 10000),
        (_probe("form_circle_limit_twenty_thousand"), 20000),
        (_probe("form_circle_limit_fifty_thousand"), 50000),
    )
    deviations = []
    for folder, limit in runs:
        listing = (folder / "report.sta.txt").read_text(encoding="latin-1")
        if limit != 10000:
            assert f"BOGENDIFFERENZ = {limit}" in listing
            assert f"{4.5 / limit:.10f}" in listing, "the limit m_n / BOGENDIFFERENZ the run used"
        deviations.append(_interface(folder, "FUSSFORMKREISDURCHM")[0] - ours.root_form_diameter_mm)
    assert deviations == pytest.approx([6.36e-3, 2.58e-3, 0.69e-3], abs=2e-5)
    assert deviations[0] > deviations[1] > deviations[2] > 0.0
    # the wheel is free of undercut: its root form circle does not depend on the limit
    wheels = {_interface(folder, "FUSSFORMKREISDURCHM")[1] for folder, _ in runs}
    assert wheels == {101.84732}


def test_residual_thickness_of_a_flat_edge_break_flank_in_single_precision() -> None:
    """At an edge break angle of 85 degrees gearcore gives a residual tip thickness of 0,02002 mm,
    STplus prints 0,02051 mm. gearcore's value is confirmed without the formula of the norm (the
    envelope of the rolling tool flank on the tip circle). STplus computes in single precision
    (ADR-106): DIN 3960 (A.3.05) subtracts two numbers of the size 11 there, and in binary32 the
    formula yields 0,01960 or 0,02051 mm, depending on the last bit of the tip diameter."""
    import numpy as np

    folder = _probe("tool_edge_break_angle_eighty_five_degrees")
    gear = _generated(folder, _imported(folder).pair).gears.pinion
    assert gear.residual_tip_thickness_mm == pytest.approx(0.0200191, abs=1e-7)
    assert _interface(folder, "RESTDICKE")[0] == 0.02051

    z, m_n, alpha_n, alpha_K = 20, 2.0, math.radians(20.0), math.radians(85.0)
    x_E, h_Ff = gear.generating_profile_shift_coefficient, 0.9 * m_n
    r, r_a = 0.5 * z * m_n, 0.5 * gear.tip_diameter_mm

    # (1) independent of the norm: the tool space rolls on the gear; the gear keeps what no
    # position of the edge break flank cuts away on the tip circle
    def flank_on_tip_circle(phi: float) -> float:
        def half_width(h: float) -> float:
            return 0.25 * math.pi * m_n - h_Ff * math.tan(alpha_n) - (h - h_Ff) * math.tan(alpha_K)

        def off_circle(h: float) -> float:
            return math.hypot(half_width(h) + r * phi, r + x_E * m_n + h) - r_a

        h = brentq(off_circle, h_Ff, r_a - r - x_E * m_n, xtol=1e-15)
        return math.atan2(half_width(h) + r * phi, r + x_E * m_n + h) - phi

    turned = minimize_scalar(
        flank_on_tip_circle, bounds=(-0.05, 0.05), method="bounded", options={"xatol": 1e-13}
    )
    assert 2.0 * r_a * turned.fun == pytest.approx(gear.residual_tip_thickness_mm, abs=1e-9)

    # (2) the formula of the norm in binary32
    def in_single_precision(units_of_the_last_place: int) -> float:
        f = np.float32
        d = f(z) * f(m_n)
        s_K = (
            f(m_n) * f(math.pi) / f(2)
            + f(2) * f(h_Ff) * (np.tan(f(alpha_K)) - np.tan(f(alpha_n)))
            + f(2) * f(x_E) * f(m_n) * np.tan(f(alpha_K))
        )
        psi_bK = s_K / d + (np.tan(f(alpha_K)) - f(alpha_K))
        d_a = f(2.0 * r_a)
        for _ in range(abs(units_of_the_last_place)):
            d_a = np.nextafter(d_a, f(np.inf if units_of_the_last_place > 0 else -np.inf))
        alpha_a = np.arccos(d * np.cos(f(alpha_K)) / d_a)
        return float(d_a * (psi_bK - (np.tan(alpha_a) - alpha_a)))

    singles = {round(in_single_precision(shift), 5) for shift in range(-3, 4)}
    assert singles == {0.0196, 0.02051}, "two values, 0,9 um apart; STplus prints the upper one"
    assert min(singles) < gear.residual_tip_thickness_mm < max(singles)


# --- the controls of the tool limits and the ends of the ranges (question of the user, 2026-10-03) ------


def test_controls_of_the_tool_limits_act_as_documented_with_other_presets() -> None:
    """The manual presets the smallest tool tip thickness with 0,2 and the smallest tool space at
    the root form height with 0,4 (p. 224); the listings showed 0,120 and 0,110. Varying the
    controls settles it: they act as documented (tip land = s_a0*, tool space = e_Ff0*), and the
    program presets them with 0,12 and 0,11. The control of the root space enters as
    2 e_f0* tan(alpha_n), with e_f0* = 0,03 where it is not set."""
    alpha = math.radians(20.0)
    # tip land: the value the manual names, given explicitly, moves the limit
    manual = _imported(_probe("tool_tip_land_control"))
    assert manual.pair.gears.pinion.tool.addendum_factor == pytest.approx(1.88312, abs=6e-6)
    assert _interface(_probe("tool_tip_land_control"), "WKZ_KOPFHOEHENFAKTOR")[0] == 1.88312
    assert stplus_max_tool_addendum_factor(alpha, min_tip_land_factor=0.2) == pytest.approx(
        (math.pi / 2.0 - 0.2) / (2.0 * math.tan(alpha))
    )
    assert (
        "$ KONFIGURATIONSDATEN: MIN_WKZ_ZAHNKOPFDICKE* = 0.2 is used in place of the preset"
        in manual.notes
    )
    assert any("narrows to 0.2 m_n there" in note for note in manual.notes)
    # ... and the preset of the program is 0,12: the same listing with and without the control
    for probe in ("tool_tip_land_control_at_program_preset", "tool_addendum_limited"):
        assert _interface(_probe(probe), "WKZ_KOPFHOEHENFAKTOR")[0] == 1.99302
    assert stplus_max_tool_addendum_factor(alpha, min_tip_land_factor=0.12) == (
        stplus_max_tool_addendum_factor(alpha)
    )
    # tool space at the root form height
    space = _imported(_probe("tool_space_control")).pair.gears.pinion.tool
    assert space.root_form_height_factor == pytest.approx(1.60837, abs=6e-6)
    assert space.dedendum_factor == space.root_form_height_factor
    assert _interface(_probe("tool_space_control"), "WKZ_FUSSFORMHOEHENF")[0] == 1.60837
    assert _interface(_probe("tool_root_form_height_limited"), "WKZ_FUSSFORMHOEHENF")[0] == 2.00675
    assert stplus_max_tool_root_form_height_factor(alpha, min_space_factor=0.11) == (
        stplus_max_tool_root_form_height_factor(alpha)
    )
    # tool space on the root line: 2 e_f0* tan(alpha_n)
    root = _imported(_probe("tool_root_space_control")).pair.gears.pinion.tool
    assert _interface(_probe("tool_root_space_control"), "WKZ_FUSSHOEHENF")[0] == 1.28503
    assert root.dedendum_factor == pytest.approx(1.28503, abs=6e-6)
    width = math.pi / 2.0 - 2.0 * 0.9 * math.tan(alpha) - 2.0 * (root.dedendum_factor - 0.9)
    assert width == pytest.approx(2.0 * 0.2 * math.tan(alpha), abs=1e-12)
    assert stplus_max_tool_dedendum_factor(
        0.9, alpha, math.radians(45.0), min_root_space_factor=0.2
    ) == pytest.approx(root.dedendum_factor)
    # a value up to 0,1 leaves the run as it is without the control
    idle = _imported(_probe("tool_root_space_control_without_effect"))
    assert (
        _interface(_probe("tool_root_space_control_without_effect"), "WKZ_FUSSHOEHENF")[0]
        == 1.34691
    )
    assert (
        idle.pair.gears.pinion.tool
        == _imported(_probe("tool_root_dedendum_limited")).pair.gears.pinion.tool
    )
    assert any(
        "MIN_LUECKENWEITE_EF0* = 0.1 does not lie between 0.1 and 0.6" in n for n in idle.notes
    )


def test_the_range_of_a_control_is_an_open_interval() -> None:
    """STplus accepts the values between the ends of the range it documents, not the ends
    themselves: TANG_BETRAG_ZU_H_KGF = 0.3 and MAX_KOPFKANTENBRUCH = 0.5 leave the presets, as
    MIN_WKZ_ZAHNKOPFDICKE* = 0.1 and MIN_LUECKENWEITE_EFF0* = 0.6 do."""
    folder = _probe("controls_at_the_ends_of_their_ranges")
    listing = probe_listing(folder.name)
    assert "TANG_BETRAG_ZU_H_KGF = 0.3" in listing and "MAX_KOPFKANTENBRUCH = 0.5" in listing
    assert _interface(folder, "KOPFKANTENBRUCH") == [0.4, 0.4], "limited to the preset 0,20 m_n"
    tips = _interface(folder, "ZAHNDICKE_KOPF")
    assert _interface(folder, "RESTDICKE")[1] == pytest.approx(tips[1] - 2.0 * 0.7 * 0.4, abs=2e-5)
    imported = _imported(folder)
    assert [g.tip_chamfer_radial_mm for g in imported.pair.gears.as_tuple()] == [0.4, 0.4]
    for key, low, high in (
        ("TANG_BETRAG_ZU_H_KGF = 0.3", 0.3, 1.5),
        ("MAX_KOPFKANTENBRUCH = 0.5", 0, 0.5),
    ):
        expected = f"$ KONFIGURATIONSDATEN: {key} does not lie between {low:g} and {high:g}: STplus"
        assert any(note.startswith(expected) for note in imported.notes), key
    assert sum("s_an - 2 (0.7 h_K)" in note for note in imported.notes) == 2

    folder = _probe("tool_controls_at_the_ends_of_their_ranges")
    assert _interface(folder, "WKZ_KOPFHOEHENFAKTOR")[0] == 1.99302
    assert _interface(folder, "WKZ_FUSSFORMHOEHENF")[0] == 2.00675
    tool = _imported(folder).pair.gears.pinion.tool
    assert tool.addendum_factor == pytest.approx(1.99302, abs=6e-6)
    assert tool.root_form_height_factor == pytest.approx(2.00675, abs=6e-6)
    assert sum("does not lie between" in note for note in _imported(folder).notes) == 2

    # the rule functions: ends refused, values just inside taken
    for factor in (0.3, 1.5, 0.29, 1.51):
        with pytest.raises(InputRangeError, match="TANG_BETRAG_ZU_H_KGF"):
            stplus_residual_tip_thickness(1.0, 0.1, tangential_factor=factor)
    assert stplus_residual_tip_thickness(1.0, 0.1, tangential_factor=0.31) == pytest.approx(0.938)
    assert stplus_residual_tip_thickness(1.0, 0.1, tangential_factor=1.49) == pytest.approx(0.702)
    for factor in (0.0, -0.0, 0.5, 0.51):
        with pytest.raises(InputRangeError, match="MAX_KOPFKANTENBRUCH"):
            stplus_tip_chamfer_height(0.3, 2.0, max_factor=factor)
    assert stplus_tip_chamfer_height(0.3, 2.0, max_factor=0.01) == 0.02
    assert stplus_tip_chamfer_height(5.0, 2.0, max_factor=0.49) == 0.98
    alpha = math.radians(20.0)
    for value in (0.1, 1.0):
        with pytest.raises(InputRangeError, match="MIN_WKZ_ZAHNKOPFDICKE"):
            stplus_max_tool_addendum_factor(alpha, min_tip_land_factor=value)
    for value in (0.1, 0.6):
        with pytest.raises(InputRangeError, match="MIN_LUECKENWEITE_EFF0"):
            stplus_max_tool_root_form_height_factor(alpha, min_space_factor=value)
        with pytest.raises(InputRangeError, match="MIN_LUECKENWEITE_EF0"):
            stplus_max_tool_dedendum_factor(
                0.9, alpha, math.radians(45.0), min_root_space_factor=value
            )
