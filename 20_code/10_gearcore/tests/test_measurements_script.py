"""``scripts/measurements.py inventory`` on the real measurement folder (skipped where absent)."""

import csv
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


@pytest.fixture(scope="module")
def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("measurements", SCRIPTS / "measurements.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_inventory_writes_tables(
    script: ModuleType, measurements_root: Path, tmp_path: Path
) -> None:
    written = script.run_inventory(measurements_root, tmp_path / "inventory")
    assert [p.name for p in written] == ["inventory.md", "inventory.csv", "anomalies.md"]
    markdown = written[0].read_text(encoding="utf-8")
    assert "## Kunststoffrad (z = 52)" in markdown and "## Stahlritzel (z = 51)" in markdown
    assert "| 97340 | Laufversuch (Kerngruppe) |" in markdown
    assert "| 95911 | Serie des Prüfstandsritzels |" in markdown
    assert "97840" in markdown  # unassigned
    with written[1].open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    assert rows[0].keys() >= {"me", "part", "group", "kind", "path", "round", "tooth", "anomalies"}
    assert sum(row["kind"] == "contour" for row in rows) >= 79
    assert {row["group"] for row in rows} >= {
        "core",
        "scatter",
        "rig_series",
        "older",
        "unassigned",
    }
    anomalies = written[2].read_text(encoding="utf-8")
    assert "coarse scan" in anomalies and "97373_1.DAT" in anomalies


def test_inventory_of_a_missing_folder_fails_visibly(script: ModuleType, tmp_path: Path) -> None:
    from gearcore.errors import InputRangeError

    with pytest.raises(InputRangeError):
        script.run_inventory(tmp_path / "nowhere", tmp_path / "out")
