"""Equation traceability: ``@eq`` references and the source registry.

Every computational function is decorated with one or more ``@eq(source, eq, ...)`` where
``source`` is a key of ``data/sources.yaml`` naming the document **and its edition**
(``"ISO21771:2014"``), because equation numbers are only unique within one document.
The decorator stores metadata in ``EQUATIONS`` and on the function (``__eq_refs__``); it does
not wrap the function, so signatures and performance are untouched.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

import yaml

from gearcore.data import data_path

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True, slots=True)
class EqRef:
    """One reference of a function to an equation (or table/section) of a source."""

    source: str
    """Key in ``sources.yaml``, e.g. ``"ISO21771:2014"`` or ``"DIN21773:2014"``."""
    eq: str
    """Equation label as printed, e.g. ``"(55)"``, ``"(3.6.08)"``, ``"A.3.06"``, ``"Tab. 1"``."""
    section: str | None = None
    page: int | None = None
    note: str | None = None

    def __str__(self) -> str:
        parts = [self.source, self.eq]
        if self.section:
            parts.append(f"§{self.section}")
        if self.page is not None:
            parts.append(f"p.{self.page}")
        return " ".join(parts)


EQUATIONS: dict[str, tuple[EqRef, ...]] = {}
"""``"module.qualname" -> refs`` for every decorated function, in decoration order."""


def eq(
    source: str,
    eq: str,
    *,
    section: str | None = None,
    page: int | None = None,
    note: str | None = None,
) -> Callable[[F], F]:
    """Record that the decorated function realises ``eq`` of ``source``.

    Decorators stack (outermost first in ``EQUATIONS``). The source key is validated lazily by
    ``tests/test_trace.py`` against ``sources.yaml`` so importing the package never touches the
    registry file.
    """
    ref = EqRef(source=source, eq=eq, section=section, page=page, note=note)

    def decorate(func: F) -> F:
        key = f"{func.__module__}.{func.__qualname__}"
        EQUATIONS[key] = (ref, *EQUATIONS.get(key, ()))
        func.__eq_refs__ = EQUATIONS[key]  # type: ignore[attr-defined]
        return func

    return decorate


def equations_of(func: Callable[..., Any]) -> tuple[EqRef, ...]:
    """References recorded for ``func`` (empty if it is not decorated)."""
    refs: tuple[EqRef, ...] = getattr(func, "__eq_refs__", ())
    return refs


def load_sources() -> dict[str, dict[str, Any]]:
    """The source registry ``data/sources.yaml`` as ``{key: entry}``."""
    with data_path("sources.yaml").open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict) or "sources" not in loaded:
        raise ValueError("sources.yaml must contain a top-level 'sources' mapping")
    sources = loaded["sources"]
    if not isinstance(sources, dict):
        raise ValueError("'sources' must be a mapping of key -> entry")
    return {str(key): dict(value) for key, value in sources.items()}
