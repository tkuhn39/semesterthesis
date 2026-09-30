"""Traceability guards: every @eq source exists, every source entry is well-formed, every public
computational function is decorated."""

import importlib
import inspect
import pkgutil
from collections.abc import Callable
from typing import Any

import pytest

import gearcore
from gearcore.trace import EQUATIONS, EqRef, eq, equations_of, load_sources

COMPUTATIONAL_MODULES = [
    "gearcore.involute",
    "gearcore.rack",
    "gearcore.pair",
    "gearcore.generation",
    "gearcore.trochoid",
    "gearcore.inspection",
    "gearcore.tolerances.din3967",
    "gearcore.tolerances.din3964",
    "gearcore.tolerances.iso1328_1",
]
"""Modules whose public functions must carry @eq; a module that does not exist yet is skipped visibly."""

REQUIRED_SOURCE_FIELDS = {"type", "title", "file", "verified", "confirmed_by_user"}
VERIFIED_METHODS = {
    "pdf-header",
    "pdf-imprint",
    "pdf-print",
    "pdf-footer",
    "isbn-checksum",
    "crossref",
    "dpma-front-page",
    "urn-resolver",
    None,
}


def _all_gearcore_modules() -> list[str]:
    names: list[str] = []
    for info in pkgutil.walk_packages(gearcore.__path__, prefix="gearcore."):
        names.append(info.name)
    return sorted(names)


def test_sources_yaml_entries_are_well_formed() -> None:
    sources = load_sources()
    assert sources, "sources.yaml is empty"
    for key, entry in sources.items():
        missing = REQUIRED_SOURCE_FIELDS - set(entry)
        assert not missing, f"{key}: missing fields {sorted(missing)}"
        verified = entry["verified"]
        assert set(verified) == {"method", "by", "date"}, (
            f"{key}: verified block must have method/by/date"
        )
        assert verified["method"] in VERIFIED_METHODS, (
            f"{key}: unknown verification method {verified['method']!r}"
        )
        if entry.get("status") == "missing":
            assert verified["method"] is None, (
                f"{key}: status missing but a verification method is set"
            )
        else:
            assert verified["method"] is not None, (
                f"{key}: no verification method (set status: missing instead)"
            )
        assert isinstance(entry["confirmed_by_user"], bool)
        if entry["type"] in {"article", "conference", "book", "thesis"}:
            assert (
                any(k in entry for k in ("doi", "isbn13", "urn"))
                or entry.get("status") == "missing"
            ), f"{key}: article/book/thesis without doi/isbn13/urn must be marked status: missing"


def test_isbn13_checksums_are_valid() -> None:
    for key, entry in load_sources().items():
        isbn = entry.get("isbn13")
        if isbn is None:
            continue
        digits = [int(c) for c in str(isbn).replace("-", "")]
        assert len(digits) == 13, f"{key}: isbn13 must have 13 digits"
        total = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
        assert (10 - total % 10) % 10 == digits[12], f"{key}: invalid ISBN-13 checksum {isbn}"


def test_every_eq_source_key_is_registered() -> None:
    for module in _all_gearcore_modules():
        importlib.import_module(module)
    sources = load_sources()
    for func_key, refs in EQUATIONS.items():
        for ref in refs:
            assert ref.source in sources, f"{func_key}: unknown source key {ref.source!r}"
            assert sources[ref.source].get("status") not in {"missing", "draft"}, (
                f"{func_key}: cites {ref.source}, which has no verifiable identifier yet or is only a draft edition"
            )
            assert sources[ref.source].get("confirmed_by_user") is True, (
                f"{func_key}: cites {ref.source}, which the user has not confirmed against the PDF yet "
                "(set confirmed_by_user: true in sources.yaml after checking)"
            )


@pytest.mark.parametrize("module_name", COMPUTATIONAL_MODULES)
def test_public_functions_carry_eq(module_name: str) -> None:
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        pytest.skip(f"{module_name} not implemented yet (stage-1 increment pending)")
    exempt: set[str] = set(getattr(module, "EQ_EXEMPT", ()))
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if name.startswith("_") or obj.__module__ != module_name or name in exempt:
            continue
        assert equations_of(obj), f"{module_name}.{name} has no @eq reference"


def test_eq_decorator_records_without_wrapping() -> None:
    def plain(x: float) -> float:
        return x

    decorated: Callable[..., Any] = eq("ISO21771:2014", "(1)", section="4.1", page=19)(
        eq("DIN3960:1987", "(3.1.01)")(plain)
    )
    assert decorated is plain
    refs = equations_of(decorated)
    assert refs == (
        EqRef(source="ISO21771:2014", eq="(1)", section="4.1", page=19),
        EqRef(source="DIN3960:1987", eq="(3.1.01)"),
    )
    assert str(refs[0]) == "ISO21771:2014 (1) §4.1 p.19"
