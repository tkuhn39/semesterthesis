"""Preserve what STplus itself ships and presets: tool databases and evidence runs of its defaults.

User decision 2026-09-30 (ADR-109): nothing STplus offered may get lost. The tool databases of the
local installation are stored verbatim (line endings normalised to LF) with their provenance, and
probe runs record which defaults the program applies. The executable and the manual stay outside
git; the installation is read-only for this script.

    python scripts/import_stplus_program.py databases     # copy tool databases + provenance.yaml
    python scripts/import_stplus_program.py probes        # run the probes (Windows, local STplus)
    python scripts/import_stplus_program.py refresh-import   # typed-import record of every probe, no STplus run

Layout ``src/gearcore/data/stplus_program/``: ``tool_database_local.txt`` (``wkz/wkz.dat``),
``tool_database_global.txt`` (``global/WKZ_GLOB.DAT``), ``input_key_register.txt``
(``bin/DEFAULT.STY``: every input key with its register default), ``provenance.yaml`` (program, version,
release, hashes), ``defaults.yaml`` (defaults transcribed from the manual and the probes, written
by hand), ``probes/<name>/`` (``input.ste``, ``report.sta.txt``, ``interface.sts.txt``, ``meta.json``).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import stplus_oracle as oracle
import yaml

TARGET = oracle.PKG_ROOT / "src" / "gearcore" / "data" / "stplus_program"
PROBES = TARGET / "probes"

DATABASES = (
    ("tool_database_local.txt", "wkz/wkz.dat", "Werkzeugdatei_lokal"),
    ("tool_database_global.txt", "global/WKZ_GLOB.DAT", "Werkzeugdatei_global"),
    ("input_key_register.txt", "bin/DEFAULT.STY", "Register der Eingabeschluessel"),
)

_PAIR = (
    "$ Anfang\n\n$ Geometriedaten\nZAHNBREITE = 20 20\nNORMALMODUL = {module}\n"
    "ZAEHNEZAHL = {teeth}\nPROFILVERSCHIEBUNG_N = 0.0 0.0\n{more}\n$ Ende\n"
)
PROBE_INPUTS: dict[str, tuple[str, str]] = {
    "defaults_minimal": (
        "only tooth numbers, module, face width, x, helix angle and pressure angle are given: the "
        "listing shows every default STplus applies (tool, tip diameter, quality, allowances, "
        "centre distance allowance, span and ball dimension)",
        _PAIR.format(module=2, teeth="20 40", more="SCHRAEGUNGSWINKEL = 0\nEINGRIFFSWINKEL = 20\n"),
    ),
    "no_pressure_angle": (
        "as defaults_minimal without EINGRIFFSWINKEL: the batch input is rejected (ALN = 0.00), "
        "the default of 20 degrees belongs to the user interface",
        _PAIR.format(module=2, teeth="20 40", more="SCHRAEGUNGSWINKEL = 0\n"),
    ),
    "tool_consistent_record": (
        "tool S_19_00374_(Cr_64 of the local tool database, referenced by name: the listing prints "
        "the factors of the record",
        _PAIR.format(
            module=2.8,
            teeth="30 45",
            more="SCHRAEGUNGSWINKEL = 0\nEINGRIFFSWINKEL = 17.5\n"
            "WERKZEUG_VORVERZ. = S_19_00374_(Cr_64 S_19_00374_(Cr_64\n",
        ),
    ),
    "tool_contradicting_record": (
        "tool S_19_00374_F_(_77, whose factors and absolute values contradict: STplus uses the "
        "factor of the addendum (1.600) and reduces tip rounding and dedendum to what is possible",
        _PAIR.format(
            module=2.8,
            teeth="30 45",
            more="SCHRAEGUNGSWINKEL = 0\nEINGRIFFSWINKEL = 17.5\n"
            "WERKZEUG_VORVERZ. = S_19_00374_F_(_77 S_19_00374_F_(_77\n",
        ),
    ),
    "tool_without_tip_rounding": (
        "tool hochverz1 of the global tool database, which gives no tip rounding, module or "
        "pressure angle: STplus presets rho_aP0* = 0.250 and takes module and angle of the gear",
        _PAIR.format(
            module=2,
            teeth="30 45",
            more="SCHRAEGUNGSWINKEL = 0\nEINGRIFFSWINKEL = 20\nWERKZEUG_VORVERZ. = hochverz1 hochverz1\n",
        ),
    ),
}

# --- probes of 2026-10-03: how STplus completes an incomplete input (ADR-114) --------------------
#
# One pair for all of them: z 20/40, m_n 2, x 0,4/0,2, tools with h_aP0* = 1,6 so that a tip
# circle of 46,4 mm lies 1,2446 m_n above the datum line of the tool of gear 1 (between the
# default root form height 1,3 and the heights the probes give). Tool T2 is plain.

_HEAD = "KOPFHOEHENFAKTOR = 1.6\nKOPFABRUNDUNGSFAKTOR = 0.25\n"


def _tool_pair(
    tool_1: str = _HEAD,
    *,
    geometry: str = "",
    configuration: str = "",
    x: str = "0.4 0.2",
    tips: str = "46.4 85.6",
    helix: str = "SCHRAEGUNGSWINKEL = 0\n",
    pressure_angle: float = 20,
    tools: str = "WERKZEUG_VORVERZ. = T1 T2\n",
) -> str:
    return (
        "$ Anfang\n\n$ Geometriedaten\nZAHNBREITE = 20 20\nNORMALMODUL = 2\nZAEHNEZAHL = 20 40\n"
        f"PROFILVERSCHIEBUNG_N = {x}\n{helix}EINGRIFFSWINKEL = {pressure_angle}\n"
        + (f"KOPFKREISDM = {tips}\n" if tips else "")
        + tools
        + geometry
        + f"\n$ T1\n{tool_1}\n$ T2\n{_HEAD}"
        + (f"\n$ KONFIGURATIONSDATEN\n{configuration}" if configuration else "")
        + "\n$ Ende\n"
    )


PROBE_INPUTS.update(
    {
        "tool_without_addendum": (
            "tool 1 gives the tip rounding only: STplus presets h_aP0* = 1.250",
            _tool_pair("KOPFABRUNDUNGSFAKTOR = 0.25\n", tips=""),
        ),
        "tool_for_one_gear_only": (
            "WERKZEUG_VORVERZ. names a tool for gear 2 only: gear 1 gets the default hob "
            "(1.250 / 0.250 / 1.300 / 1.300); no KOPFKREISDM: d_a = d + 2 m_n (1 + x)",
            _tool_pair(tools="WERKZEUG_VORVERZ. = % T2\n", tips=""),
        ),
        "tool_addendum_limited": (
            "KOPFHOEHENFAKTOR = 2.1 at 20 degrees: reduced to 1.993 (tip land 0,120 m_n), the "
            "rounding to the full radius 0.086",
            _tool_pair("KOPFHOEHENFAKTOR = 2.1\nKOPFABRUNDUNGSFAKTOR = 0.25\n", tips=""),
        ),
        "tool_tip_rounding_limited": (
            "KOPFABRUNDUNGSFAKTOR = 0.6 with h_aP0* = 1.25: reduced to the full radius 0.472",
            _tool_pair("KOPFHOEHENFAKTOR = 1.25\nKOPFABRUNDUNGSFAKTOR = 0.6\n", tips=""),
        ),
        "tool_root_dedendum_only_low": (
            "FUSSHOEHENFAKTOR = 1.0 alone has no effect: 1.300 / 1.300 (as the kst-E pinion)",
            _tool_pair(_HEAD + "FUSSHOEHENFAKTOR = 1.0\n"),
        ),
        "tool_root_dedendum_only_high": (
            "FUSSHOEHENFAKTOR = 2.0 alone: h_FfP0* 1.300, h_fP0* limited to 1.822 (default edge "
            "break angle 30 degrees)",
            _tool_pair(_HEAD + "FUSSHOEHENFAKTOR = 2.0\n"),
        ),
        "tool_root_form_height_only": (
            "FUSSFORMHOEHENFAKTOR = 0.9 alone: h_fP0* 1.300 and a chamfer by the default edge "
            "break angle of 30 degrees",
            _tool_pair(_HEAD + "FUSSFORMHOEHENFAKTOR = 0.9\n"),
        ),
        "tool_root_both_heights": (
            "0.9 / 1.5 without KANTENBRECHWINKEL: chamfer by alpha_K0 = 30 degrees "
            "(d_Fa 46.307, h_K 0.047, Restdicke 0.407)",
            _tool_pair(_HEAD + "FUSSFORMHOEHENFAKTOR = 0.9\nFUSSHOEHENFAKTOR = 1.5\n"),
        ),
        "tool_root_form_height_and_angle": (
            "0.9 with KANTENBRECHWINKEL = 45 and no dedendum: h_fP0* 1.300, chamfer d_Fa 45.731",
            _tool_pair(_HEAD + "FUSSFORMHOEHENFAKTOR = 0.9\nKANTENBRECHWINKEL = 45\n"),
        ),
        "tool_root_dedendum_limited": (
            "0.9 / 1.5 with 45 degrees: the dedendum is limited to 1.347",
            _tool_pair(
                _HEAD
                + "FUSSFORMHOEHENFAKTOR = 0.9\nFUSSHOEHENFAKTOR = 1.5\nKANTENBRECHWINKEL = 45\n"
            ),
        ),
        "tool_root_dedendum_below_form_height": (
            "0.9 / 0.5: the dedendum is set to the root form height (0.900 / 0.900, not h_f0max "
            "as the manual says) and the tool cuts the tip circle to 45.021",
            _tool_pair(_HEAD + "FUSSFORMHOEHENFAKTOR = 0.9\nFUSSHOEHENFAKTOR = 0.5\n"),
        ),
        "tool_root_angle_only": (
            "KANTENBRECHWINKEL = 45 alone: 1.300 / 1.300, 'Kein Kopfkantenbruch durch Werkzeug 1'",
            _tool_pair(_HEAD + "KANTENBRECHWINKEL = 45\n"),
        ),
        "tool_root_form_height_limited": (
            "FUSSFORMHOEHENFAKTOR = 2.5 at 20 degrees: reduced to 2.007, the dedendum follows",
            _tool_pair(
                "KOPFHOEHENFAKTOR = 1.25\nKOPFABRUNDUNGSFAKTOR = 0.2\nFUSSFORMHOEHENFAKTOR = 2.5\n",
                tips="",
            ),
        ),
        "tool_root_presets_of_the_configuration": (
            "VB_FUSSFORMHOEHE_HFF0* = 1.0 and VB_FUSSHOEHE_HF0* = 1.2 in the configuration block: "
            "the listing still prints 1.300 / 1.300",
            _tool_pair(
                configuration="VB_FUSSFORMHOEHE_HFF0* = 1.0 1.0\nVB_FUSSHOEHE_HF0* = 1.2 1.2\n"
            ),
        ),
        "tool_root_other_pressure_angle": (
            "0.9 / 2.5 at alpha_n = 25 degrees without KANTENBRECHWINKEL: the dedendum is limited "
            "to 1.402, the limit of the default angle 35 degrees",
            _tool_pair(
                "KOPFHOEHENFAKTOR = 1.25\nKOPFABRUNDUNGSFAKTOR = 0.2\n"
                "FUSSFORMHOEHENFAKTOR = 0.9\nFUSSHOEHENFAKTOR = 2.5\n",
                tips="",
                pressure_angle=25,
            ),
        ),
        "tool_root_dedendum_limit_at_fifteen_degrees": (
            "0.9 / 2.5 with 45 degrees at alpha_n = 15 degrees: the dedendum is limited to 1.436",
            _tool_pair(
                "KOPFHOEHENFAKTOR = 1.25\nKOPFABRUNDUNGSFAKTOR = 0.2\n"
                "FUSSFORMHOEHENFAKTOR = 0.9\nFUSSHOEHENFAKTOR = 2.5\nKANTENBRECHWINKEL = 45\n",
                tips="",
                pressure_angle=15,
            ),
        ),
        "tool_root_dedendum_limit_at_twenty_five_degrees": (
            "0.9 / 2.5 with 45 degrees at alpha_n = 25 degrees: the dedendum is limited to 1.252",
            _tool_pair(
                "KOPFHOEHENFAKTOR = 1.25\nKOPFABRUNDUNGSFAKTOR = 0.2\n"
                "FUSSFORMHOEHENFAKTOR = 0.9\nFUSSHOEHENFAKTOR = 2.5\nKANTENBRECHWINKEL = 45\n",
                tips="",
                pressure_angle=25,
            ),
        ),
        "tool_root_form_height_limit_at_fifteen_degrees": (
            "FUSSFORMHOEHENFAKTOR = 3.0 at alpha_n = 15 degrees: reduced to 2.726",
            _tool_pair(
                "KOPFHOEHENFAKTOR = 1.25\nKOPFABRUNDUNGSFAKTOR = 0.2\nFUSSFORMHOEHENFAKTOR = 3.0\n",
                tips="",
                pressure_angle=15,
            ),
        ),
        "tool_root_form_height_limit_at_twenty_five_degrees": (
            "FUSSFORMHOEHENFAKTOR = 2.5 at alpha_n = 25 degrees: reduced to 1.566",
            _tool_pair(
                "KOPFHOEHENFAKTOR = 1.25\nKOPFABRUNDUNGSFAKTOR = 0.2\nFUSSFORMHOEHENFAKTOR = 2.5\n",
                tips="",
                pressure_angle=25,
            ),
        ),
        "tool_addendum_limit_at_fifteen_degrees": (
            "KOPFHOEHENFAKTOR = 2.8 at alpha_n = 15 degrees: reduced to 2.707, rounding 0.078",
            _tool_pair(
                "KOPFHOEHENFAKTOR = 2.8\nKOPFABRUNDUNGSFAKTOR = 0.25\n", tips="", pressure_angle=15
            ),
        ),
        "tool_addendum_limit_at_twenty_five_degrees": (
            "KOPFHOEHENFAKTOR = 1.65 at alpha_n = 25 degrees: reduced to 1.556, rounding 0.094",
            _tool_pair(
                "KOPFHOEHENFAKTOR = 1.65\nKOPFABRUNDUNGSFAKTOR = 0.25\n", tips="", pressure_angle=25
            ),
        ),
        "tip_circle_cut_by_tool": (
            "KOPFKREISDM = 46.8 above the root line of the default tool root (1.300): cut to "
            "46.621 = d + 2 m_n (x_E + h_fP0*)",
            _tool_pair(tips="46.8 85.6"),
        ),
        "tip_circle_cut_then_edge_break": (
            "0.9 / 1.1 with 45 degrees: the tip circle is cut to 45.821 and chamfered by the "
            "edge break flank (d_Fa 45.731)",
            _tool_pair(
                _HEAD
                + "FUSSFORMHOEHENFAKTOR = 0.9\nFUSSHOEHENFAKTOR = 1.1\nKANTENBRECHWINKEL = 45\n"
            ),
        ),
        "tip_circle_cut_helical": (
            "beta = 20 degrees, both tip circles above the root lines: cut to 49.189 and 90.901",
            _tool_pair(helix="SCHRAEGUNGSWINKEL = 20\n", tips="49.4 91.0"),
        ),
        "tip_circle_cut_with_chamfer": (
            "tip circle cut to 46.621 and a chamfer of 0.1 given as an input: d_Fa = 46.421, "
            "Restdicke 0.263 - 0.14 = 0.123",
            _tool_pair(tips="46.8 85.6", geometry="KOPFKANTENBRUCH = 0.1 0.1\n"),
        ),
        "pointed_by_edge_break": (
            "0.9 with 60 degrees: dedendum limited to 1.158, tip circle cut, the edge break "
            "flanks meet ('Spitzer Zahn am Rad 1 durch Kantenbruch', d_a 45.952)",
            _tool_pair(_HEAD + "FUSSFORMHOEHENFAKTOR = 0.9\nKANTENBRECHWINKEL = 60\n"),
        ),
        "helix_angle_from_centre_distance": (
            "no SCHRAEGUNGSWINKEL, ACHSABSTAND = 62.5 and both x: beta = 12.13130 is computed",
            _tool_pair(helix="", geometry="ACHSABSTAND = 62.5\n", tips=""),
        ),
        "no_helix_angle_no_centre_distance": (
            "no SCHRAEGUNGSWINKEL and no ACHSABSTAND: the input is rejected",
            _tool_pair(helix="", tips=""),
        ),
        "upper_span_allowance_only": (
            "OBERES_ZAHNW_ABMASS alone: the lower span allowance is set equal to it",
            _tool_pair(geometry="OBERES_ZAHNW_ABMASS = -60 -80\n"),
        ),
        "profile_shift_sum": (
            "PR.VERSCH.SUMME = 0.6 with x_1 = 0.4: x_2 = 0.2000",
            _tool_pair(x="0.4 %", geometry="PR.VERSCH.SUMME = 0.6\n", tips=""),
        ),
        "tip_chamfer_default": (
            "KOPFKANTENBRUCH = 0.2 0.3: Restdicke = s_an - 2 (0,7 h_K) = 0.143 and 0.508",
            _tool_pair(geometry="KOPFKANTENBRUCH = 0.2 0.3\n"),
        ),
        "tip_chamfer_tangential_given": (
            "TANG_BETRAG_ZU_H_KGF = 1.0: Restdicke of gear 2 = 0.928 - 0.6 = 0.328; gear 1 at "
            "its floor 0.085 = 0,2 s_an",
            _tool_pair(
                geometry="KOPFKANTENBRUCH = 0.2 0.3\n",
                configuration="TANG_BETRAG_ZU_H_KGF = 1.0 1.0\n",
            ),
        ),
        "tip_chamfer_limits": (
            "KOPFKANTENBRUCH = 0.25 0.6: gear 1 at the floor 0,2 s_an (0.085), gear 2 limited to "
            "0.20 m_n ('Eingabe zu Kopfkantenbruch begrenzt auf 0.20 * m_n')",
            _tool_pair(geometry="KOPFKANTENBRUCH = 0.25 0.6\n"),
        ),
        "tip_chamfer_helical": (
            "beta = 25 degrees: RESTDICKE = ZAHNDICKE_KOPF - 1.4 h_K in the normal section "
            "(1.12292 - 0.28 = 0.84292)",
            _tool_pair(
                helix="SCHRAEGUNGSWINKEL = 25\n", tips="", geometry="KOPFKANTENBRUCH = 0.2 0.3\n"
            ),
        ),
    }
)
# --- probes of the verification review of 2026-10-03 (gate report increment 3, G3X) ----------------

PROBE_INPUTS.update(
    {
        "default_hob_at_twenty_eight_degrees": (
            "as defaults_minimal at alpha_n = 28 degrees: the preset tip rounding 0.25 lies beyond "
            "the full radius and is reduced to 0.201; no remark is printed",
            _PAIR.format(
                module=2, teeth="20 40", more="SCHRAEGUNGSWINKEL = 0\nEINGRIFFSWINKEL = 28\n"
            ),
        ),
        "default_hob_at_thirty_degrees": (
            "as defaults_minimal at alpha_n = 30 degrees: tip rounding 0.110, and the preset root "
            "form height 1.3 is reduced to 1.265, the dedendum with it",
            _PAIR.format(
                module=2, teeth="20 40", more="SCHRAEGUNGSWINKEL = 0\nEINGRIFFSWINKEL = 30\n"
            ),
        ),
        "tool_addendum_limited_without_tip_rounding": (
            "KOPFHOEHENFAKTOR = 2.1 without tip rounding: 1.993, and the preset rounding 0.25 is "
            "reduced to the full radius 0.086",
            _tool_pair("KOPFHOEHENFAKTOR = 2.1\n", tips=""),
        ),
        "tool_for_gear_one_only": (
            "WERKZEUG_VORVERZ. names one tool: gear 2 gets the default hob (1.250 / 0.250), not "
            "the tool of gear 1 (1.400 / 0.300)",
            _tool_pair(
                "KOPFHOEHENFAKTOR = 1.4\nKOPFABRUNDUNGSFAKTOR = 0.3\n",
                tools="WERKZEUG_VORVERZ. = T1\n",
                tips="",
            ),
        ),
        "tip_circle_from_reference_profile_addendum": (
            "K_HOEHENF_VERZ_BEZ_PR = 1.1 0.9 without KOPFKREISDM: d_a = d + 2 m_n (h_aP* + x) = "
            "46.000 / 84.400, and the preset tool dedendum of gear 1 becomes 1.430",
            _tool_pair(tips="", geometry="K_HOEHENF_VERZ_BEZ_PR = 1.1 0.9\n"),
        ),
        "tip_circle_per_din3960": (
            "DA_NACH_DIN3960 = ja ja without KOPFKREISDM: tip circles with the tip alteration "
            "k m_n = -0.126 mm (45.347 / 85.347)",
            _tool_pair(tips="", geometry="DA_NACH_DIN3960 = ja ja\n", x="0.4 0.4"),
        ),
        "tip_chamfer_tangential_two_values": (
            "TANG_BETRAG_ZU_H_KGF = 1.0 0.5: the first value holds for both gears (Restdicke "
            "0.423 - 0.2 = 0.223 and 0.928 - 0.6 = 0.328)",
            _tool_pair(
                geometry="KOPFKANTENBRUCH = 0.1 0.3\n",
                configuration="TANG_BETRAG_ZU_H_KGF = 1.0 0.5\n",
            ),
        ),
        "tip_chamfer_limit_lowered": (
            "MAX_KOPFKANTENBRUCH = 0.1 0.4: both chamfers limited to 0.10 m_n = 0.200 ('Eingabe "
            "zu Kopfkantenbruch begrenzt auf 0.10 * m_n'); the first value holds for both gears",
            _tool_pair(
                geometry="KOPFKANTENBRUCH = 0.5 0.6\n",
                configuration="MAX_KOPFKANTENBRUCH = 0.1 0.4\n",
            ),
        ),
        "tip_chamfer_limit_raised": (
            "MAX_KOPFKANTENBRUCH = 0.4: the chamfer 0.6 of gear 2 is kept (limit 0.8 mm), its "
            "Restdicke is at the floor 0,2 s_an = 0.186",
            _tool_pair(
                geometry="KOPFKANTENBRUCH = 0.25 0.6\n",
                configuration="MAX_KOPFKANTENBRUCH = 0.4\n",
            ),
        ),
        "tool_edge_break_angle_ninety_degrees": (
            "0.9 / 1.5 with KANTENBRECHWINKEL = 90: a tool without edge break flank, 0.900 / "
            "0.900, the tip circle is cut to 45.021",
            _tool_pair(
                _HEAD
                + "FUSSFORMHOEHENFAKTOR = 0.9\nFUSSHOEHENFAKTOR = 1.5\nKANTENBRECHWINKEL = 90\n"
            ),
        ),
        "profile_shift_sum_with_centre_distance": (
            "PR.VERSCH.SUMME = 0.6, x_1 = 0.4, ACHSABSTAND = 61.0 and beta = 0: the sum is not "
            "used, x_2 = 0.1298 follows from the centre distance",
            _tool_pair(x="0.4 %", geometry="PR.VERSCH.SUMME = 0.6\nACHSABSTAND = 61.0\n", tips=""),
        ),
        "tip_chamfer_floor": (
            "KOPFKANTENBRUCH = 0.4 0.4 at d_a1 = 46.2: Restdicke of gear 1 at the floor 0,2 s_an "
            "= 0.113 (s_an 0.564)",
            _tool_pair(tips="46.2 85.6", geometry="KOPFKANTENBRUCH = 0.4 0.4\n"),
        ),
    }
)
# --- probes of the second verification review of 2026-10-03 (gate report increment 3, G3Y) ---------

PROBE_INPUTS.update(
    {
        "tip_circle_given_with_other_definitions": (
            "as tip_circle_cut_by_tool (KOPFKREISDM = 46.8 85.6) with all five other definitions "
            "of the tip circle set as well: the listing is the same (d_a 46.621 / 85.600, tool "
            "dedendum 1.300, tip clearance), the keys have no effect",
            _tool_pair(
                tips="46.8 85.6",
                geometry="K_HOEHENF_VERZ_BEZ_PR = 1.1 0.9\nKOPFSPIELFAKTOR = 0.3 0.3\n"
                "DA_NACH_DIN3960 = ja ja\nDA_DURCH_WKZ = ja ja\nBEZ_KOPFDICKE = 0.3 0.3\n",
            ),
        ),
        "tool_edge_break_angle_eighty_five_degrees": (
            "0.9 / 1.5 with KANTENBRECHWINKEL = 85: dedendum limited to 0.939, chamfer by the "
            "tool with a residual thickness of 0.021",
            _tool_pair(
                _HEAD
                + "FUSSFORMHOEHENFAKTOR = 0.9\nFUSSHOEHENFAKTOR = 1.5\nKANTENBRECHWINKEL = 85\n"
            ),
        ),
        "tool_edge_break_angle_eighty_eight_degrees": (
            "0.9 / 1.5 with KANTENBRECHWINKEL = 88: STplus aborts ('Iteration IREG = 10 fuer Rad 1 "
            "nach 100 Schritten abgebrochen')",
            _tool_pair(
                _HEAD
                + "FUSSFORMHOEHENFAKTOR = 0.9\nFUSSHOEHENFAKTOR = 1.5\nKANTENBRECHWINKEL = 88\n"
            ),
        ),
        "tool_edge_break_angle_below_pressure_angle": (
            "0.9 / 1.5 with KANTENBRECHWINKEL = 15 at alpha_n = 20: run with alfa_K0 = 30.00 "
            "(alpha_n0 + 10) and 'Wkz.daten ... geaendert', as tool_root_both_heights",
            _tool_pair(
                _HEAD
                + "FUSSFORMHOEHENFAKTOR = 0.9\nFUSSHOEHENFAKTOR = 1.5\nKANTENBRECHWINKEL = 15\n"
            ),
        ),
        "tool_edge_break_angle_equal_to_pressure_angle": (
            "0.9 / 1.5 with KANTENBRECHWINKEL = 20 at alpha_n = 20: no edge break flank, "
            "0.900 / 0.900, the tip circle is cut to 45.021",
            _tool_pair(
                _HEAD
                + "FUSSFORMHOEHENFAKTOR = 0.9\nFUSSHOEHENFAKTOR = 1.5\nKANTENBRECHWINKEL = 20\n"
            ),
        ),
        "tool_edge_break_angle_ninety_degrees_without_form_height": (
            "KANTENBRECHWINKEL = 90 without root heights: 1.300 / 1.300, no chamfer, no cut",
            _tool_pair(_HEAD + "KANTENBRECHWINKEL = 90\n"),
        ),
        "controls_first_value_holds": (
            "TANG_BETRAG_ZU_H_KGF = 0.5 1.0 and MAX_KOPFKANTENBRUCH = 0.4 0.1 with chamfers of "
            "0.3: both kept (limit 0.8 mm), Restdicke 0.123 and 0.628 (factor 0.5 for both "
            "gears): the first value holds, not the stricter one",
            _tool_pair(
                geometry="KOPFKANTENBRUCH = 0.3 0.3\n",
                configuration="TANG_BETRAG_ZU_H_KGF = 0.5 1.0\nMAX_KOPFKANTENBRUCH = 0.4 0.1\n",
            ),
        ),
        "control_outside_its_range": (
            "TANG_BETRAG_ZU_H_KGF = 2.0 (range 0.3 to 1.5): not accepted, Restdicke 0.283 and "
            "0.508 as with the preset 0.7",
            _tool_pair(
                geometry="KOPFKANTENBRUCH = 0.1 0.3\n",
                configuration="TANG_BETRAG_ZU_H_KGF = 2.0\n",
            ),
        ),
    }
)
# --- probes of 2026-10-03 on the causes of two deviations (gate report increment 3, last section) ---


def _fzg_c_with(configuration: str) -> str:
    """The fixture case fzg_c (undercut pinion) with a block of controls."""
    text = (oracle.FIXTURES / "fzg_c" / "input.ste").read_text(encoding="latin-1")
    if "$ Ende" not in text or "KONFIGURATIONSDATEN" in text.upper():
        raise SystemExit("fzg_c/input.ste: expected a file without a block of controls")
    return text.replace("$ Ende", "$ KONFIGURATIONSDATEN\n" + configuration + "$ Ende")


PROBE_INPUTS.update(
    {
        "helix_angle_without_profile_shift": (
            "no SCHRAEGUNGSWINKEL, ACHSABSTAND = 62.5, x = 0 0: the helix angle is "
            "arccos(60 / 62.5) = 16.26020 degrees; STplus lists 16.25980 and a sum of the "
            "profile shift coefficients of 0.00006",
            _tool_pair(helix="", geometry="ACHSABSTAND = 62.5\n", tips="", x="0.0 0.0"),
        ),
        "helix_angle_iteration_limit_tightened": (
            "as helix_angle_from_centre_distance with GRENZE_BETA_ITERATION = 0.00000001 (its "
            "lower bound): the same 12.13130 degrees, the control does not end this iteration",
            _tool_pair(
                helix="",
                geometry="ACHSABSTAND = 62.5\n",
                tips="",
                configuration="GRENZE_BETA_ITERATION = 0.00000001\n",
            ),
        ),
        "form_circle_limit_twenty_thousand": (
            "fzg_c with BOGENDIFFERENZ = 20000 (arcs equal within m_n / 20000 = 0.000225 mm): "
            "root form diameter of the undercut pinion 67.68128 (preset 10000: 67.68506)",
            _fzg_c_with("BOGENDIFFERENZ = 20000\n"),
        ),
        "form_circle_limit_fifty_thousand": (
            "fzg_c with BOGENDIFFERENZ = 50000 (0.00009 mm): root form diameter of the undercut "
            "pinion 67.67939; the exact intersection of fillet and involute is 67.67870",
            _fzg_c_with("BOGENDIFFERENZ = 50000\n"),
        ),
    }
)
# --- probes of 2026-10-03 on the controls of the tool limits and the ends of the ranges -------------

_TALL = "KOPFHOEHENFAKTOR = 2.1\nKOPFABRUNDUNGSFAKTOR = 0.25\n"
_FLANK = _HEAD + "FUSSFORMHOEHENFAKTOR = 0.9\nFUSSHOEHENFAKTOR = 1.5\nKANTENBRECHWINKEL = 45\n"

PROBE_INPUTS.update(
    {
        "tool_tip_land_control": (
            "as tool_addendum_limited with MIN_WKZ_ZAHNKOPFDICKE* = 0.2, the preset the manual "
            "names: the addendum is limited to 1.883 (tip land 0.2 m_n), not to 1.993",
            _tool_pair(_TALL, tips="", configuration="MIN_WKZ_ZAHNKOPFDICKE* = 0.2\n"),
        ),
        "tool_tip_land_control_at_program_preset": (
            "as tool_addendum_limited with MIN_WKZ_ZAHNKOPFDICKE* = 0.12: 1.993 as without the "
            "control, 0.12 is the preset of the program",
            _tool_pair(_TALL, tips="", configuration="MIN_WKZ_ZAHNKOPFDICKE* = 0.12\n"),
        ),
        "tool_space_control": (
            "as tool_root_form_height_limited with MIN_LUECKENWEITE_EFF0* = 0.4, the preset the "
            "manual names: the root form height is limited to 1.608 (tool space 0.4 m_n), not to "
            "2.007",
            _tool_pair(
                _HEAD + "FUSSFORMHOEHENFAKTOR = 2.5\n",
                configuration="MIN_LUECKENWEITE_EFF0* = 0.4\n",
            ),
        ),
        "tool_root_space_control": (
            "as tool_root_dedendum_limited with MIN_LUECKENWEITE_EF0* = 0.2: the dedendum is "
            "limited to 1.285, a root space of 2 x 0.2 x tan(alpha_n) m_n",
            _tool_pair(_FLANK, configuration="MIN_LUECKENWEITE_EF0* = 0.2\n"),
        ),
        "tool_root_space_control_without_effect": (
            "as tool_root_dedendum_limited with MIN_LUECKENWEITE_EF0* = 0.1: 1.347 as without "
            "the control (values up to 0.1 leave the preset in place)",
            _tool_pair(_FLANK, configuration="MIN_LUECKENWEITE_EF0* = 0.1\n"),
        ),
        "tool_controls_at_the_ends_of_their_ranges": (
            "MIN_WKZ_ZAHNKOPFDICKE* = 0.1 and MIN_LUECKENWEITE_EFF0* = 0.6, the ends of their "
            "ranges: not accepted, the presets hold (1.993 and 2.007)",
            _tool_pair(
                _TALL + "FUSSFORMHOEHENFAKTOR = 2.5\n",
                tips="",
                configuration="MIN_WKZ_ZAHNKOPFDICKE* = 0.1\nMIN_LUECKENWEITE_EFF0* = 0.6\n",
            ),
        ),
        "controls_at_the_ends_of_their_ranges": (
            "TANG_BETRAG_ZU_H_KGF = 0.3 and MAX_KOPFKANTENBRUCH = 0.5, the ends of their ranges: "
            "not accepted, chamfers limited to 0.20 m_n and Restdicke of gear 2 0.928 - 2 x 0.7 "
            "x 0.4 = 0.368 as with the presets",
            _tool_pair(
                geometry="KOPFKANTENBRUCH = 0.5 0.9\n",
                configuration="TANG_BETRAG_ZU_H_KGF = 0.3\nMAX_KOPFKANTENBRUCH = 0.5\n",
            ),
        ),
    }
)
PROBE_FILES = ("input.ste", "report.sta.txt", "interface.sts.txt", "meta.json")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _header(listing: str, label: str) -> str:
    match = re.search(rf"^\s*{label}:\s+(\S.*?)\s*$", listing, flags=re.MULTILINE)
    if match is None:
        raise SystemExit(f"listing header has no line '{label}:'")
    return match.group(1)


def import_databases(root: Path) -> None:
    """Copy the tool databases and write ``provenance.yaml``; needs the probe ``defaults_minimal``
    for the program version the installation prints."""
    probe = PROBES / "defaults_minimal" / "report.sta.txt"
    if not probe.is_file():
        raise SystemExit(
            "run 'probes' first: the version is read from a listing of this installation"
        )
    listing = probe.read_text(encoding="latin-1")
    TARGET.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    for stored, original, role in DATABASES:
        source = root / original
        raw = source.read_bytes()
        text = raw.decode("latin-1")
        normalised = text.replace("\r\n", "\n")
        (TARGET / stored).write_text(normalised, encoding="latin-1", newline="\n")
        modified = dt.datetime.fromtimestamp(source.stat().st_mtime).astimezone()
        files.append(
            {
                "stored": stored,
                "original": original,
                "role": role,
                "bytes": len(raw),
                "sha256": _sha256(raw),
                "stored_sha256": _sha256(normalised.encode("latin-1")),
                "line_endings": "CRLF, normalised to LF" if "\r\n" in text else "LF",
                "encoding": "latin-1",
                "modified": modified.isoformat(timespec="seconds"),
            }
        )
    provenance = {
        "program": _header(listing, "Programmname"),
        "version": _header(listing, "Version"),
        "release": _header(listing, "Freigabe"),
        "publisher": "Forschungsvereinigung Antriebstechnik e.V. (FVA)",
        "evidence": (
            "header of probes/defaults_minimal/report.sta.txt, printed by this installation: "
            "Programmname, Version, Freigabe"
        ),
        "installation": oracle._relative(root),
        "manual": {
            "file": "doku/STplus_11-1F_Benutzeranleitung.pdf",
            "note": (
                "page headers of the manual print 'STplus 11.0F' and 'STplus 10F'; pages are cited "
                "by their printed number (PDF page = printed page + 6)"
            ),
        },
        "imported": dt.date.today().isoformat(),
        "note": (
            "Files as found in the installation. The local tool database is meant to be extended "
            "by its users (manual p. 21), so its records are not vendor defaults."
        ),
        "files": files,
    }
    (TARGET / "provenance.yaml").write_text(
        yaml.safe_dump(provenance, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
        newline="\n",
    )
    print(f"{len(files)} files of {provenance['program']} {provenance['version']} -> {TARGET}")


def run_probes(root: Path, only: str | None) -> None:
    """Run the probes in a temporary fixture directory and keep the evidence files."""
    fixtures = oracle.FIXTURES
    with tempfile.TemporaryDirectory(prefix="gearcore_probe_") as scratch:
        oracle.FIXTURES = Path(scratch)
        try:
            for name, (notes, text) in PROBE_INPUTS.items():
                if only and name != only:
                    continue
                source = Path(scratch) / f"{name}.ste"
                source.write_text(text, encoding="latin-1", newline="\n")
                result = oracle.run_case(
                    name,
                    source,
                    root=root,
                    trust="generated",
                    plot_accuracy=0.005,
                    material_kinds=None,
                    notes=notes,
                )
                target = PROBES / name
                target.mkdir(parents=True, exist_ok=True)
                for file in PROBE_FILES:
                    if (result / file).is_file():
                        shutil.copyfile(result / file, target / file)
                # the contours of a probe are not kept; its meta must not point to them
                meta = json.loads((target / "meta.json").read_text(encoding="utf-8"))
                for key in ("contours", "contour_format"):
                    meta.pop(key, None)
                meta["kept_files"] = [f for f in PROBE_FILES if (target / f).is_file()]
                oracle._write_json(target / "meta.json", meta)
                print(f"probe {name} -> {target}")
        finally:
            oracle.FIXTURES = fixtures


def refresh_typed_import() -> None:
    """Recompute the typed-import record of every probe with the current importer (no STplus
    run): the record states what the importer of this version reads from ``input.ste``."""
    for target in sorted(p for p in PROBES.iterdir() if (p / "meta.json").is_file()):
        meta = json.loads((target / "meta.json").read_text(encoding="utf-8"))
        meta["typed_import"] = oracle._typed_import(target, meta)
        oracle._write_json(target / "meta.json", meta)
        status = "ok" if meta["typed_import"]["ok"] else meta["typed_import"]["error"]
        print(f"{target.name:<46} typed import: {status[:90]}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("databases", "probes", "refresh-import"))
    parser.add_argument("--stplus-root", default=None)
    parser.add_argument("--only", default=None, help="probes: run one probe")
    args = parser.parse_args(argv)
    if args.command == "refresh-import":
        refresh_typed_import()
        return
    root = oracle._stplus_root(args.stplus_root)
    if args.command == "probes":
        run_probes(root, args.only)
    else:
        import_databases(root)


if __name__ == "__main__":
    main()
