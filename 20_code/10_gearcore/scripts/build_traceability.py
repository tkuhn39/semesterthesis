"""Render the traceability table: source → equation → function → tests → notebooks → status.

    python scripts/build_traceability.py            # writes 00_development_documentation/traceability.md
    python scripts/build_traceability.py --check    # exit 1 if any stage-1 equation is untested

Tests are linked through ``@pytest.mark.eq(source, eq)`` markers (collected with pytest) and,
as a fallback, through the function name appearing in a test file; notebooks through the function
name appearing in a notebook's code cells.
"""

from __future__ import annotations

import argparse
import importlib
import json
import pkgutil
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import gearcore
from gearcore.trace import EQUATIONS, load_sources

HERE = Path(__file__).resolve().parent
PKG_ROOT = HERE.parent
REPO_ROOT = PKG_ROOT.parents[1]
DOCS = REPO_ROOT / "20_code" / "00_development_documentation"
NOTEBOOKS = REPO_ROOT / "40_jupyter-notebooks"


def _import_all() -> None:
    for info in pkgutil.walk_packages(gearcore.__path__, prefix="gearcore."):
        importlib.import_module(info.name)


def _tests_by_marker() -> dict[tuple[str, str], set[str]]:
    """``(source, eq) -> test node ids`` from pytest markers (collection only)."""
    plugin = HERE / "_collect_eq_markers.py"
    plugin.write_text(
        "import json\n"
        "COLLECTED = {}\n"
        "def pytest_collection_modifyitems(session, config, items):\n"
        "    for item in items:\n"
        "        for marker in item.iter_markers(name='eq'):\n"
        "            key = f'{marker.args[0]}|{marker.args[1]}'\n"
        "            COLLECTED.setdefault(key, []).append(item.nodeid)\n"
        "def pytest_sessionfinish(session, exitstatus):\n"
        "    (session.config.rootpath / 'build').mkdir(exist_ok=True)\n"
        "    (session.config.rootpath / 'build' / 'eq_markers.json').write_text(json.dumps(COLLECTED))\n",
        encoding="utf-8",
    )
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "-p",
                "scripts._collect_eq_markers",
            ],
            cwd=PKG_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        out = PKG_ROOT / "build" / "eq_markers.json"
        data = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else {}
    finally:
        plugin.unlink(missing_ok=True)
    result: dict[tuple[str, str], set[str]] = defaultdict(set)
    for key, ids in data.items():
        source, eq = key.split("|", 1)
        result[(source, eq)].update(ids)
    return result


def _mentions(name: str, files: list[Path]) -> list[str]:
    pattern = re.compile(rf"\b{re.escape(name)}\b")
    hits: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix == ".ipynb":
            cells = json.loads(text).get("cells", [])
            text = "\n".join(
                "".join(c.get("source", [])) for c in cells if c.get("cell_type") == "code"
            )
        if pattern.search(text):
            hits.append(path.name)
    return hits


def build(check: bool) -> int:
    _import_all()
    sources = load_sources()
    markers = _tests_by_marker()
    test_files = sorted((PKG_ROOT / "tests").glob("test_*.py"))
    notebooks = sorted(NOTEBOOKS.glob("[0-9]*.ipynb"))
    rows: list[tuple[str, str, str, str, str, str, str]] = []
    untested = 0
    for func_key, refs in sorted(EQUATIONS.items()):
        short = func_key.removeprefix("gearcore.")
        func_name = short.rsplit(".", 1)[-1]
        by_name_tests = _mentions(func_name, test_files)
        by_name_nb = _mentions(func_name, notebooks)
        for ref in refs:
            tests = sorted(markers.get((ref.source, ref.eq), set()))
            test_cell = (
                ", ".join(t.split("::")[-1] for t in tests) if tests else ", ".join(by_name_tests)
            )
            status = "✓ tested" if (tests or by_name_tests) else "⚠ untested"
            if not (tests or by_name_tests):
                untested += 1
            title = sources.get(ref.source, {}).get("title", "?")
            where = " ".join(
                p
                for p in (
                    f"§{ref.section}" if ref.section else "",
                    f"p.{ref.page}" if ref.page else "",
                )
                if p
            )
            rows.append(
                (
                    ref.source,
                    ref.eq,
                    where,
                    short,
                    test_cell or "–",
                    ", ".join(by_name_nb) or "–",
                    status,
                )
            )
            _ = title
    lines = [
        "# Traceability: source → equation → function → tests → notebooks",
        "",
        "Generated by `scripts/build_traceability.py`; do not edit by hand.",
        "",
        "Tests are linked through `@pytest.mark.eq(source, eq)` markers and, as a fallback, "
        "through the function name in a test file. The notebook column is a match of the "
        "function name in the code cells of a notebook: a notebook that documents an equation "
        "through the orchestrator (`compute_pair_geometry`) is not listed for it, and a name "
        "that two modules share is listed for both.",
        "",
        "| Source | Eq. | §/page | Function | Tests | Notebooks | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    if not rows:
        lines.append("| – | – | – | (no @eq-decorated functions yet) | – | – | – |")
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "traceability.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # ASCII only: the Windows console may run with cp1252
    print(f"{len(rows)} equation references, {untested} untested -> {DOCS / 'traceability.md'}")
    return 1 if (check and untested) else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raise SystemExit(build(args.check))


if __name__ == "__main__":
    main()
