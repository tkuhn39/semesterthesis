"""Preserve what STplus itself ships and presets: tool databases and evidence runs of its defaults.

User decision 2026-09-30 (ADR-109): nothing STplus offered may get lost. The tool databases of the
local installation are stored verbatim (line endings normalised to LF) with their provenance, and
probe runs record which defaults the program applies. The executable and the manual stay outside
git; the installation is read-only for this script.

    python scripts/import_stplus_program.py databases     # copy tool databases + provenance.yaml
    python scripts/import_stplus_program.py probes        # run the probes (Windows, local STplus)

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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("databases", "probes"))
    parser.add_argument("--stplus-root", default=None)
    parser.add_argument("--only", default=None, help="probes: run one probe")
    args = parser.parse_args(argv)
    root = oracle._stplus_root(args.stplus_root)
    if args.command == "probes":
        run_probes(root, args.only)
    else:
        import_databases(root)


if __name__ == "__main__":
    main()
