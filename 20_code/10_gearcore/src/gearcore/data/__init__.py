"""Packaged reference data: source registry, worked examples, STplus oracle fixtures.

The data ships inside the wheel so tests and notebooks read the same files
(``importlib.resources``); nothing here is read from the repository layout at run time.
Names of cases, examples and documents are checked against what is packaged; an unknown name is
an ``InputRangeError``, never a path.
"""

import json
import re
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from gearcore._safe import integer_input
from gearcore.errors import InputRangeError, ParseError

STPLUS_DOCUMENTS = ("geometry", "interface", "meta", "report", "contour_wz1", "contour_wz2")
"""JSON documents a STplus fixture case may contain (``interface`` only for own runs)."""

_PRINTED_NUMBER = re.compile(r"[-−]?\d+(?: \d{3})*(?:,\d+(?: \d+)*)?")
"""A number as ISO documents print it: decimal comma, digit groups separated by a space."""


def data_path(*parts: str) -> Path:
    """Absolute path of a file below ``gearcore/data`` (must exist as a regular file or dir)."""
    root = files("gearcore.data")
    target = root.joinpath(*parts)
    return Path(str(target))


def stplus_case_dirs() -> list[Path]:
    """All STplus fixture case directories (those containing a ``meta.json``), sorted by name."""
    base = data_path("stplus")
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir() and (p / "meta.json").is_file())


def _stplus_case_dir(case: str) -> Path:
    known = {path.name: path for path in stplus_case_dirs()}
    if not isinstance(case, str) or case not in known:
        raise InputRangeError(f"unknown STplus fixture case {case!r}; packaged: {sorted(known)}")
    return known[case]


def has_stplus(case: str, name: str) -> bool:
    """True if the STplus fixture case contains the JSON document ``name``."""
    if name not in STPLUS_DOCUMENTS:
        raise InputRangeError(f"unknown STplus document {name!r}; known: {STPLUS_DOCUMENTS}")
    return (_stplus_case_dir(case) / f"{name}.json").is_file()


def load_body_sections() -> dict[str, dict[str, dict[str, Any]]]:
    """Meridional half sections of gear bodies transcribed from the user's drawings
    (``fe/body_sections.yaml``): case -> role -> the dimensions of the drawing."""
    path = data_path("fe", "body_sections.yaml")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or not isinstance(loaded.get("bodies"), dict):
        raise ParseError("body_sections.yaml: expected a mapping 'bodies'")
    bodies: dict[str, dict[str, dict[str, Any]]] = loaded["bodies"]
    return bodies


def load_converse_rates() -> dict[str, dict[str, Any]]:
    """The strain rates behind the CONVERSE material cards of the user
    (``fe/converse_rates.yaml``): rate name -> test speed and strain rate."""
    path = data_path("fe", "converse_rates.yaml")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or not isinstance(loaded.get("rates"), dict):
        raise ParseError("converse_rates.yaml: expected a mapping 'rates'")
    rates: dict[str, dict[str, Any]] = loaded["rates"]
    return rates


def load_fva856_table4() -> dict[str, Any]:
    """Tabelle 4 of FVA 856 I (elastic constants of the conditioned skin layer of PA46-GF30
    per temperature and strain rate, ``fe/fva856_table4.yaml``): the mapping with ``rows``
    (label, temperature_c, rate, the nine values E_1, E_2, E_3, nu_12, nu_13, nu_23, G_12,
    G_13, G_23) and the provenance keys ``source``, ``table``, ``printed_page``, ``pdf_page``,
    ``state``, ``frame``, ``constant_names``, ``units``."""
    path = data_path("fe", "fva856_table4.yaml")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or not isinstance(loaded.get("rows"), list):
        raise ParseError("fva856_table4.yaml: expected a mapping with a list 'rows'")
    keys = (
        "source",
        "table",
        "printed_page",
        "pdf_page",
        "state",
        "frame",
        "constant_names",
        "units",
    )
    missing = [key for key in keys if key not in loaded]
    if missing:
        raise ParseError(f"fva856_table4.yaml: missing keys {missing}")
    if not isinstance(loaded["frame"], dict) or len(loaded["constant_names"]) != 9:
        raise ParseError(
            "fva856_table4.yaml: 'frame' must be a mapping, 'constant_names' nine names"
        )
    for row in loaded["rows"]:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("values"), list)
            or len(row["values"]) != 9
            or "temperature_c" not in row
            or "rate" not in row
            or "label" not in row
        ):
            raise ParseError(f"fva856_table4.yaml: malformed row {row!r}")
    document: dict[str, Any] = loaded
    return document


def fva856_table4_row(temperature_c: float, rate: str) -> tuple[float, ...]:
    """The nine engineering constants of Tabelle 4 of FVA 856 I at ``temperature_c`` and the
    strain rate ``rate`` (QS, DY1, DY2); an ``InputRangeError`` names the rows that exist when
    none matches."""
    rows = load_fva856_table4()["rows"]
    for row in rows:
        if abs(float(row["temperature_c"]) - float(temperature_c)) < 1.0e-9 and (
            str(row["rate"]).upper() == str(rate).upper()
        ):
            return tuple(float(v) for v in row["values"])
    labels = ", ".join(str(row["label"]) for row in rows)
    raise InputRangeError(
        f"FVA 856 I Tabelle 4 has no row at {temperature_c} degC and rate {rate!r}; rows: {labels}"
    )


def load_as_manufactured() -> dict[str, Any]:
    """The measured numbers of the manufactured gears that the FE variants put onto the STplus
    case (``fe/as_manufactured.yaml``): the mapping ``cases`` with, per case, ``gears`` (named
    sets of measured numbers) and ``variants`` (which gear takes which set), plus the
    ``provenance`` of the numbers (user decisions of 2026-10-19)."""
    path = data_path("fe", "as_manufactured.yaml")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or not isinstance(loaded.get("cases"), dict):
        raise ParseError("as_manufactured.yaml: expected a mapping 'cases'")
    if not isinstance(loaded.get("provenance"), dict):
        raise ParseError("as_manufactured.yaml: expected a mapping 'provenance'")
    for case, entry in loaded["cases"].items():
        if not isinstance(entry, dict) or not isinstance(entry.get("gears"), dict):
            raise ParseError(f"as_manufactured.yaml: case {case!r} needs a mapping 'gears'")
        if not isinstance(entry.get("variants"), dict):
            raise ParseError(f"as_manufactured.yaml: case {case!r} needs a mapping 'variants'")
        for label, variant in entry["variants"].items():
            if not isinstance(variant, dict) or not {"pinion", "wheel"} <= set(variant):
                raise ParseError(
                    f"as_manufactured.yaml: variant {label!r} of {case!r} names pinion and wheel"
                )
            for role in ("pinion", "wheel"):
                name = variant[role]
                if name is not None and name not in entry["gears"]:
                    raise ParseError(
                        f"as_manufactured.yaml: variant {label!r} of {case!r}: unknown gear set "
                        f"{name!r} for the {role}"
                    )
    document: dict[str, Any] = loaded
    return document


def load_stommel_materials() -> dict[str, Any]:
    """The material classes of Stommel et al. (2018), chapter 6, and the materials of the thesis
    (``fatigue/stommel_materials.yaml``): the mappings ``classes``, ``constants`` and
    ``materials`` with the provenance of the transcription (ADR-118)."""
    path = data_path("fatigue", "stommel_materials.yaml")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ParseError("stommel_materials.yaml: expected a mapping")
    for key in ("classes", "constants", "materials"):
        if not isinstance(loaded.get(key), dict):
            raise ParseError(f"stommel_materials.yaml: expected a mapping {key!r}")
    document: dict[str, Any] = loaded
    return document


def load_expected_differences() -> dict[str, dict[str, Any]]:
    """Documented differences between gearcore and the STplus oracle (ADR-105), by name."""
    path = data_path("stplus", "expected_differences.yaml")
    loaded: dict[str, dict[str, Any]] = yaml.safe_load(path.read_text(encoding="utf-8"))[
        "differences"
    ]
    return loaded


def load_not_compared() -> dict[str, dict[str, Any]]:
    """Quantities STplus defines or chooses differently from the norm and that are therefore not
    compared value by value, by name."""
    path = data_path("stplus", "expected_differences.yaml")
    loaded: dict[str, dict[str, Any]] = yaml.safe_load(path.read_text(encoding="utf-8"))[
        "not_compared"
    ]
    return loaded


def load_norm_deviations() -> dict[str, dict[str, Any]]:
    """Deliberate deviations of gearcore from the letter of the current norm (decisions of the
    user with an ADR), by name."""
    path = data_path("stplus", "expected_differences.yaml")
    loaded: dict[str, dict[str, Any]] = yaml.safe_load(path.read_text(encoding="utf-8"))[
        "deviations_from_the_norm"
    ]
    return loaded


def load_stplus(case: str, name: str = "geometry") -> dict[str, Any]:
    """One JSON document of an STplus fixture case (``geometry``, ``interface``, ``meta``, ...)."""
    if not has_stplus(case, name):
        raise InputRangeError(f"STplus fixture case {case!r} has no document {name!r}")
    path = _stplus_case_dir(case) / f"{name}.json"
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def stplus_input_path(case: str) -> Path:
    """Path of the ``input.ste`` of an STplus fixture case."""
    return _stplus_case_dir(case) / "input.ste"


MEASUREMENT_FIXTURE_SUFFIXES = (".mew", ".mka", ".scan.txt", ".utf16.txt")
"""Packaged measurement fixtures: GINA value and curve files, contour scans (renamed, the
repository ignores ``*.dat``), roughness exports (UTF-16 bytes verbatim)."""


def load_measurement_parts() -> dict[str, Any]:
    """The user's decisions on the measured parts (``measurement/parts.yaml``): groups of ME
    numbers per part, drawings, batch labels, known anomalies."""
    path = data_path("measurement", "parts.yaml")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or not isinstance(loaded.get("parts"), dict):
        raise ParseError("parts.yaml: expected a mapping 'parts'")
    for part in ("wheel", "pinion"):
        entry = loaded["parts"].get(part)
        if not isinstance(entry, dict) or not isinstance(entry.get("groups"), dict):
            raise ParseError(f"parts.yaml: part {part!r} needs a mapping 'groups'")
        for name, members in entry["groups"].items():
            if not isinstance(members, list) or not all(
                isinstance(me, str) and re.fullmatch(r"\d{5}", me) for me in members
            ):
                raise ParseError(f"parts.yaml: group {name!r} of {part!r}: five-digit ME strings")
        if not isinstance(entry.get("scatter_group"), str):
            raise ParseError(f"parts.yaml: part {part!r} needs 'scatter_group'")
        for name, members in entry.get("labels", {}).items():
            if not isinstance(members, list) or not all(
                isinstance(me, str) and re.fullmatch(r"\d{5}", me) for me in members
            ):
                raise ParseError(f"parts.yaml: label {name!r} of {part!r}: five-digit ME strings")
    result: dict[str, Any] = loaded
    return result


def measurement_fixture_names() -> list[str]:
    """Names of the packaged measurement fixtures (files below ``measurement/fixtures``)."""
    base = data_path("measurement", "fixtures")
    if not base.is_dir():
        return []
    return sorted(
        p.name
        for p in base.iterdir()
        if p.is_file() and p.name.endswith(MEASUREMENT_FIXTURE_SUFFIXES)
    )


def measurement_fixture(name: str) -> Path:
    """Path of a packaged measurement fixture; an unknown name is an ``InputRangeError``."""
    known = measurement_fixture_names()
    if not isinstance(name, str) or name not in known:
        raise InputRangeError(f"unknown measurement fixture {name!r}; packaged: {known}")
    return data_path("measurement", "fixtures", name)


def worked_example_ids() -> list[str]:
    """Identifiers of the packaged norm worked examples."""
    base = data_path("worked_examples")
    if not base.is_dir():
        return []
    return sorted(p.stem for p in base.glob("*.yaml"))


def load_worked_example(example_id: str) -> dict[str, Any]:
    """A worked example transcribed from a norm (inputs, expected values with printed decimals)."""
    known = worked_example_ids()
    if not isinstance(example_id, str) or example_id not in known:
        raise InputRangeError(f"unknown worked example {example_id!r}; packaged: {known}")
    path = data_path("worked_examples", f"{example_id}.yaml")
    loaded: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded


def printed_number(text: str) -> tuple[float, int]:
    """Value and number of decimals of a number as a norm prints it.

    ``'x_1 = (0,145 22)'`` gives ``(0.14522, 5)``; the first number after the first equals sign
    counts (``'h_fP2 = 1,4 m_n = 11,2 mm'`` gives ``(1.4, 1)``).
    """
    if not isinstance(text, str):
        raise ParseError(f"printed value must be text, got {text!r}")
    tail = text.split("=", 1)[1] if "=" in text else text
    match = _PRINTED_NUMBER.search(tail)
    if match is None:
        raise ParseError(f"no number in the printed value {text!r}")
    token = match.group(0).replace("−", "-").replace(" ", "")
    decimals = len(token.partition(",")[2])
    return float(token.replace(",", ".")), decimals


def printed_tolerance(decimals: int) -> float:
    """Half a unit of the last printed digit of a reference value with ``decimals`` decimals."""
    count = integer_input(decimals, "number of printed decimals")
    if not 0 <= count <= 15:
        raise InputRangeError(f"number of printed decimals must lie in [0, 15], got {decimals!r}")
    return 0.5 * 10.0 ** (-count)
