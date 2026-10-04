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
