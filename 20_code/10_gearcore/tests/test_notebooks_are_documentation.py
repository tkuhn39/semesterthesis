"""Notebooks are documentation (ADR-104): they call gearcore, they never implement formulas.

A code cell may define helpers only for plotting (``_plot_*``); any other function body that does
arithmetic with ``math``/``numpy`` or arithmetic operators is a violation.
"""

import ast
import json
from pathlib import Path

import pytest

NOTEBOOKS = Path(__file__).resolve().parents[3] / "40_jupyter-notebooks"
ARITHMETIC = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.FloorDiv, ast.Mod)


def _code_cells(path: Path) -> list[str]:
    cells = json.loads(path.read_text(encoding="utf-8")).get("cells", [])
    sources: list[str] = []
    for cell in cells:
        if cell.get("cell_type") != "code":
            continue
        lines = [
            ln
            for ln in "".join(cell.get("source", [])).splitlines()
            if not ln.lstrip().startswith(("%", "!"))
        ]
        sources.append("\n".join(lines))
    return sources


def _offending_functions(source: str) -> list[str]:
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if node.name.startswith("_plot"):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.BinOp) and isinstance(inner.op, ARITHMETIC):
                offenders.append(node.name)
                break
            if (
                isinstance(inner, ast.Attribute)
                and isinstance(inner.value, ast.Name)
                and inner.value.id in {"math", "np", "numpy"}
            ):
                offenders.append(node.name)
                break
    return offenders


@pytest.mark.parametrize("path", sorted(NOTEBOOKS.glob("*.ipynb")), ids=lambda p: p.name)
def test_notebook_defines_no_formulas(path: Path) -> None:
    offenders = [name for cell in _code_cells(path) for name in _offending_functions(cell)]
    assert not offenders, (
        f"{path.name}: functions with arithmetic outside _plot_* helpers: {offenders}"
    )


def test_notebooks_exist() -> None:
    assert (NOTEBOOKS / "00_index.ipynb").is_file()
