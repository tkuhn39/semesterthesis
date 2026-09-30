"""Notebooks are documentation (ADR-104): they call gearcore, they never implement formulas.

* A function defined in a notebook may only plot (``_plot_*``); any other function body that does
  arithmetic with ``math``/``numpy`` or arithmetic operators is a violation.
* Outside functions a cell may add and subtract (a deviation shown next to a reference is not a
  formula) and convert units with ``math.radians``/``math.degrees``; products, quotients, powers
  and every other use of ``math``/``numpy`` belong into the package.
"""

import ast
import json
from pathlib import Path

import pytest

NOTEBOOKS = Path(__file__).resolve().parents[3] / "40_jupyter-notebooks"
ARITHMETIC = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.FloorDiv, ast.Mod)
FORMULA_OPERATORS = (ast.Mult, ast.Div, ast.Pow, ast.FloorDiv, ast.Mod)
NUMERIC_MODULES = {"math", "np", "numpy"}
ALLOWED_AT_CELL_LEVEL = {"radians", "degrees", "isclose"}


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


def _uses_numeric_module(node: ast.AST, allowed: set[str]) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in NUMERIC_MODULES
        and node.attr not in allowed
    )


def _offending_functions(source: str) -> list[str]:
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            continue
        name = getattr(node, "name", "<lambda>")
        if name.startswith("_plot"):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.BinOp) and isinstance(inner.op, ARITHMETIC):
                offenders.append(name)
                break
            if _uses_numeric_module(inner, set()):
                offenders.append(name)
                break
    return offenders


def _offending_statements(source: str) -> list[str]:
    """Formula-like expressions outside function definitions."""
    offenders: list[str] = []

    def visit(node: ast.AST) -> None:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            return  # judged by _offending_functions
        if isinstance(node, ast.BinOp) and isinstance(node.op, FORMULA_OPERATORS):
            text = isinstance(node.left, ast.Constant) and isinstance(node.left.value, str)
            if not text:  # "%s" % value is formatting
                offenders.append(f"line {node.lineno}: {ast.unparse(node)}")
        if _uses_numeric_module(node, ALLOWED_AT_CELL_LEVEL):
            offenders.append(f"line {getattr(node, 'lineno', 0)}: {ast.unparse(node)}")
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(ast.parse(source))
    return offenders


@pytest.mark.parametrize("path", sorted(NOTEBOOKS.glob("*.ipynb")), ids=lambda p: p.name)
def test_notebook_defines_no_formulas(path: Path) -> None:
    offenders = [name for cell in _code_cells(path) for name in _offending_functions(cell)]
    assert not offenders, (
        f"{path.name}: functions with arithmetic outside _plot_* helpers: {offenders}"
    )


@pytest.mark.parametrize("path", sorted(NOTEBOOKS.glob("*.ipynb")), ids=lambda p: p.name)
def test_notebook_cells_contain_no_formulas(path: Path) -> None:
    offenders = [found for cell in _code_cells(path) for found in _offending_statements(cell)]
    assert not offenders, f"{path.name}: formulas at cell level: {offenders}"


def test_notebooks_exist() -> None:
    names = {path.name for path in NOTEBOOKS.glob("*.ipynb")}
    assert {"00_index.ipynb", "01_involute_bezugsprofil.ipynb", "_template.ipynb"} <= names


@pytest.mark.parametrize(
    "source",
    [
        "pitch = math.pi * gear.transverse_module_mm",
        "tolerance = 0.5 * 10 ** -entry['decimals']",
        "angle = 180.0 / gear.number_of_teeth",
        "value = math.tan(alpha) - alpha",
        "x = np.sqrt(d_y**2 - d_b**2)",
        "rows = [{'s': m * (math.pi / 2)} for m in modules]",
    ],
)
def test_the_guard_recognises_formulas_at_cell_level(source: str) -> None:
    assert _offending_statements(source), source


@pytest.mark.parametrize(
    "source",
    [
        "deviation = value - reference",
        "alpha = math.radians(inputs['normal_pressure_angle_deg'])",
        "assert abs(value - reference) <= tolerance + 1e-9",
        "assert math.isclose(restored.base_diameter_mm, gear.base_diameter_mm)",
        "print('%s: %s' % (name, value))",
        "def _plot_curve(xs):\n    return [x * math.pi for x in xs]",
    ],
)
def test_the_guard_accepts_documentation_code(source: str) -> None:
    assert not _offending_statements(source) and not _offending_functions(source), source


def test_functions_other_than_plot_helpers_must_not_compute() -> None:
    assert _offending_functions("def area(r):\n    return math.pi * r * r") == ["area"]
    assert _offending_functions("scale = lambda v: v * 2.0") == ["<lambda>"]
    assert not _offending_functions("def _plot_area(r):\n    return math.pi * r * r")
    assert not _offending_functions("def describe(row):\n    return row.verdict.value")
