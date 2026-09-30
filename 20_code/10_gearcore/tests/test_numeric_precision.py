"""Numeric precision of gearcore (project rule 8a, ADR-106).

gearcore computes in IEEE 754 binary64 and never rounds inside the computational chain; values are
handed over between functions, models and JSON with all their digits.

The source scan below is a guard against the usual ways of losing digits. It inspects the syntax
tree, so it cannot prove their absence (a rounding hidden behind ``getattr`` or in a dependency
passes); the behavioural tests at the end and the reviews of the adversarial gates cover the rest.
"""

import ast
import math
from pathlib import Path

import pytest

from gearcore import involute as iv
from gearcore.models.results import BasicGearGeometry

SRC = Path(__file__).resolve().parents[1] / "src" / "gearcore"
ULP = math.ulp(1.0)

NUMERIC_MODULES = {"np", "numpy"}
REDUCED_PRECISION_TYPES = {
    "float32",
    "float16",
    "single",
    "half",
    "csingle",
    "complex64",
    "longfloat",
}
REDUCED_PRECISION_CODES = {"float32", "float16", "f4", "f2", "<f4", "<f2", ">f4", ">f2", "=f4"}
BINARY_PACKING_MODULES = {"struct", "array"}
ROUNDING_NAMES = {
    "round",
    "around",
    "round_",
    "rint",
    "trunc",
    "floor",
    "ceil",
    "fix",
    "__round__",
    "__trunc__",
    "__floor__",
    "__ceil__",
    "quantize",
}
ARITHMETIC = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.FloorDiv, ast.Mod)


def violations(source: str) -> list[str]:
    """Constructs that lose digits: reduced-precision types, rounding, format-and-parse."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        line = getattr(node, "lineno", 0)
        if isinstance(node, ast.Attribute):
            owner = node.value.id if isinstance(node.value, ast.Name) else None
            if node.attr in REDUCED_PRECISION_TYPES and owner in NUMERIC_MODULES:
                found.append(f"line {line}: {owner}.{node.attr}")
            if node.attr in ROUNDING_NAMES:
                found.append(f"line {line}: .{node.attr}")
        elif isinstance(node, ast.Name) and node.id in ROUNDING_NAMES:
            found.append(f"line {line}: {node.id}")
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                numeric = node.module is not None and node.module.split(".")[0] == "numpy"
                if alias.name in ROUNDING_NAMES or (
                    numeric and alias.name in REDUCED_PRECISION_TYPES
                ):
                    found.append(f"line {line}: from {node.module} import {alias.name}")
            if node.module in BINARY_PACKING_MODULES:
                found.append(f"line {line}: from {node.module} import ...")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in BINARY_PACKING_MODULES:
                    found.append(f"line {line}: import {alias.name}")
        elif isinstance(node, ast.Constant) and node.value in REDUCED_PRECISION_CODES:
            found.append(f"line {line}: type code {node.value!r}")
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
            found.append(f"line {line}: floor division")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            arguments = node.args
            if node.func.id == "float" and arguments:
                formatted = isinstance(arguments[0], ast.JoinedStr) or (
                    isinstance(arguments[0], ast.Call)
                    and getattr(arguments[0].func, "id", getattr(arguments[0].func, "attr", ""))
                    == "format"
                )
                percent = isinstance(arguments[0], ast.BinOp) and isinstance(
                    arguments[0].op, ast.Mod
                )
                if formatted or percent:
                    found.append(f"line {line}: float() of a formatted number")
            if node.func.id == "int" and arguments:
                inner = (n for n in ast.walk(arguments[0]) if isinstance(n, ast.BinOp))
                if any(isinstance(n.op, ARITHMETIC) for n in inner):
                    found.append(f"line {line}: int() of an arithmetic expression")
    return found


def _python_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: p.relative_to(SRC).as_posix())
def test_source_uses_neither_reduced_precision_nor_rounding(path: Path) -> None:
    found = violations(path.read_text(encoding="utf-8"))
    assert not found, f"{path.relative_to(SRC).as_posix()}: {found}"


def test_the_package_is_scanned() -> None:
    names = {path.relative_to(SRC).as_posix() for path in _python_files()}
    assert {"involute.py", "rack.py", "parity.py", "_safe.py", "io/ste.py"} <= names


@pytest.mark.parametrize(
    "snippet",
    [
        "import numpy as np\nx = np.float32(1.0)",
        "import numpy\nx = numpy.single(1.0)",
        "from numpy import float32",
        "import numpy as np\nx = np.zeros(3, dtype='float32')",
        "x = values.astype('f4')",
        "import struct\nx = struct.pack('f', 1.0)",
        "from struct import pack",
        "x = round(y, 3)",
        "r = round\nx = r(y, 3)",
        "import math\nx = math.floor(y)",
        "from math import floor as fl\nx = fl(y)",
        "import numpy as np\nx = np.around(y, 3)",
        "x = y.__round__(3)",
        "x = value.quantize(step)",
        "x = float(f'{y:.5f}')",
        "x = float('{:.5f}'.format(y))",
        "x = float('%.5f' % y)",
        "x = int(y * 1000) / 1000",
        "x = y // 1",
    ],
)
def test_the_guard_recognises_the_usual_ways_of_losing_digits(snippet: str) -> None:
    assert violations(snippet), snippet


@pytest.mark.parametrize(
    "snippet",
    [
        "half = 0.5 * width\nsingle = one_value\nhalf_space = half - x",
        "x = float(value)\nn = int(value)\ny = float(token.replace('d', 'e'))",
        '"""STplus computes in single precision (float32), about half the digits."""',
        "import numpy as np\nx = np.float64(1.0)\ny = np.spacing(x)",
        "message = f'{value!r} exceeds {limit:.3f}'",
        "x = a % b",
    ],
)
def test_the_guard_leaves_harmless_code_alone(snippet: str) -> None:
    assert not violations(snippet), snippet


def test_results_keep_every_digit_through_json() -> None:
    geometry = iv.compute_basic_gear_geometry(
        number_of_teeth=17,
        normal_module_mm=8.0,
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=15.8,
        profile_shift_coefficient=0.14522,
    )
    restored = BasicGearGeometry.model_validate_json(geometry.model_dump_json())
    for field in BasicGearGeometry.model_fields:
        assert getattr(restored, field) == getattr(geometry, field), field
    assert restored == geometry
    assert type(geometry.base_diameter_mm) is float and type(geometry.number_of_teeth) is int
    # seventeen significant digits identify a binary64 number
    assert "132.19856920126213" in geometry.model_dump_json()


def test_rounding_errors_do_not_accumulate_over_a_chain_of_hand_overs() -> None:
    """d -> d_b -> alpha_t -> d again, a thousand times: the drift stays within a few ulp."""
    alpha_n, beta = math.radians(20.0), math.radians(15.8)
    d_start = iv.reference_diameter(17, 8.0, beta)
    d = d_start
    for _ in range(1000):
        d_b = d * math.cos(iv.transverse_pressure_angle(alpha_n, beta))
        alpha_t = iv.transverse_profile_angle_at(d, d_b)
        d = d_b / math.cos(alpha_t)
    assert d == pytest.approx(d_start, rel=4 * ULP)


def test_tooth_thickness_and_space_width_close_the_pitch() -> None:
    geometry = iv.compute_basic_gear_geometry(
        number_of_teeth=25,
        normal_module_mm=3.0,
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=30.0,
        profile_shift_coefficient=0.3,
    )
    pitch = math.pi * geometry.transverse_module_mm
    closed = geometry.transverse_tooth_thickness_mm + geometry.transverse_space_width_mm
    assert closed == pytest.approx(pitch, rel=4 * ULP)
