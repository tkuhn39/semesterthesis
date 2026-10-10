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


def test_gina_writes_tables_and_figures(
    script: ModuleType, measurements_root: Path, tmp_path: Path
) -> None:
    written = script.run_gina(
        measurements_root,
        tmp_path / "gina",
        me_filter=["97340", "95911"],
        rounds="all",
        curves=True,
    )
    names = sorted(p.relative_to(tmp_path / "gina").as_posix() for p in written)
    assert "wheel/tabelle_streuung.md" in names and "wheel/tabelle_streuung.csv" in names
    assert "wheel/wiederholbarkeit.md" in names and "wheel/toleranzen_protokoll.md" in names
    assert "wheel/fenster_zaehne.md" in names and "pinion/kopfruecknahme_ritzel.md" in names
    assert "wheel/zaehne_97340-neu.svg" in names and "wheel/zaehne_97340-neu.png" in names
    assert "wheel/profil_97340-neu.svg" in names and "wheel/flankenlinie_97340-neu.svg" in names
    assert "pinion/zaehne_95911-neu.svg" in names and "pinion/profil_95911-neu2.svg" in names
    scatter = (tmp_path / "gina" / "wheel" / "tabelle_streuung.md").read_text(encoding="utf-8")
    assert "| f_Hβ | links | µm |" in scatter and "Fertigungsstreuung" not in scatter.split("\n")[0]
    with (tmp_path / "gina" / "wheel" / "tabelle_streuung.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    by_key = {(r["label"], r["flank"]): r for r in rows}
    assert by_key[("Fr", "")]["quantity"] == "runout" and int(by_key[("Fr", "")]["core_n"]) == 1
    repeat = (tmp_path / "gina" / "pinion" / "wiederholbarkeit.md").read_text(encoding="utf-8")
    assert "| 95911 | fKo | links | µm | 2 | -23,1, -22,4 | 0,7 |" in repeat
    assert "Kein Teil" in (tmp_path / "gina" / "wheel" / "wiederholbarkeit.md").read_text(
        encoding="utf-8"
    )
    relief = (tmp_path / "gina" / "pinion" / "kopfruecknahme_ritzel.md").read_text(encoding="utf-8")
    assert (
        "| 95911 | -neu | 2025-10-13 | links | Z1: -23,2, Z18: -22,8, Z35: -23,2 | -23,1 |"
        in relief
    )
    assert "| 51,946 | 52,880 | 1,155 |" in relief
    window = (tmp_path / "gina" / "wheel" / "fenster_zaehne.md").read_text(encoding="utf-8")
    assert window.startswith("# Zähne 36 bis 40 (Ausfallfenster), Kunststoffrad (z = 52)")
    assert "| 97340 | -neu | links |" in window
    assert "wheel/teilungssektoren.md" in names
    sectors = (tmp_path / "gina" / "wheel" / "teilungssektoren.md").read_text(encoding="utf-8")
    assert "| 97340 | -neu | links | 7 | 16,7 | 16,7 | 20,7 | 16,3 | 22,0 |" in sectors
    assert "| 97340 | -neu | rechts | 7 | 21,7 | 21,7 | 21,7 | 13,0 | 22,0 |" in sectors
    tolerances = (tmp_path / "gina" / "wheel" / "toleranzen_protokoll.md").read_text(
        encoding="utf-8"
    )
    assert "| 97340 | -neu | Rs |  | 17,6 | 14,0 |" in tolerances  # Rs above the program value
    assert "Fpz/8 | Fpz/8 (Messprogramm) | 22,0 | 22,0 | 7 |" in tolerances
    assert "core_me_max" in rows[0]
    svg = (tmp_path / "gina" / "wheel" / "zaehne_97340-neu.svg").read_text(encoding="utf-8")
    assert "<text" in svg and "Ausfallfenster" in svg


def test_gina_refuses_an_unknown_round_selection(script: ModuleType, tmp_path: Path) -> None:
    from gearcore.errors import InputRangeError

    with pytest.raises(InputRangeError):
        script.run_gina(tmp_path, tmp_path / "out", rounds="newest")


def test_gina_over_the_whole_folder_pins_the_core_group(
    script: ModuleType, measurements_root: Path, tmp_path: Path
) -> None:
    written = script.run_gina(measurements_root, tmp_path / "all", plots=False)
    names = {p.name for p in written}
    assert "zaehne_97340-neu.svg" not in names and "teilungssektoren.md" in names
    with (tmp_path / "all" / "wheel" / "tabelle_streuung.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    by_key = {(r["label"], r["flank"]): r for r in rows}
    fp = by_key[("Fp", "links")]
    assert (fp["core_n"], fp["scatter_n"]) == ("10", "26")
    assert float(fp["core_mean"]) == pytest.approx(47.9, abs=0.05)
    assert float(fp["core_sd"]) == pytest.approx(36.8, abs=0.05)
    assert fp["core_me_max"] == "97345" and fp["quantity"] == "total_cumulative_pitch_deviation"
    window = (tmp_path / "all" / "wheel" / "fenster_zaehne.md").read_text(encoding="utf-8")
    assert "| 97365 | -neu | links |" in window and "| 97365 | _neu |" not in window  # later time
    sectors = (tmp_path / "all" / "wheel" / "teilungssektoren.md").read_text(encoding="utf-8")
    assert "Über der Toleranz des Programms: Fpz/8 in " in sectors
    assert "| 97348 |" in sectors


def test_contour_writes_tables_and_figures(
    script: ModuleType, measurements_root: Path, tmp_path: Path
) -> None:
    written = script.run_contour(
        measurements_root, tmp_path / "kontur", parts=("pinion",), me_filter=["86481"]
    )
    names = sorted(p.relative_to(tmp_path / "kontur").as_posix() for p in written)
    for name in (
        "pinion/bericht.md",
        "pinion/kanten.csv",
        "pinion/kopfruecknahme.csv",
        "pinion/zahndicke.csv",
        "pinion/teilung.csv",
        "pinion/ueberlagerung_86481_86481_Z01.svg",
        "pinion/ueberlagerung_86481_86481_Z18.png",
        "pinion/kopfkante_86481_86481_Z36.svg",
        "pinion/ueberlagerung_pinion_older.svg",
    ):
        assert name in names, name
    report = (tmp_path / "kontur" / "pinion" / "bericht.md").read_text(encoding="utf-8")
    assert "| 86481 | 86481_Z01 | B | 87,572 | 1088 | nein | 0,0250, -0,0578 |" in report
    assert "| 86481 | älteres Ritzel | 3 |" in report
    with (tmp_path / "kontur" / "pinion" / "kanten.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    assert 12 <= len(rows) <= 15 and {r["scan"] for r in rows} == {
        "86481_Z01",
        "86481_Z18",
        "86481_Z36",
    }
    assert all(float(r["arc_radius_mm"]) <= 0.03 for r in rows)  # the sharp edge of 86481


def test_roughness_writes_tables(
    script: ModuleType, measurements_root: Path, tmp_path: Path
) -> None:
    written = script.run_roughness(measurements_root, tmp_path / "rauheit")
    names = sorted(p.relative_to(tmp_path / "rauheit").as_posix() for p in written)
    assert names == ["wheel/gruppen.md", "wheel/rohdaten.csv", "wheel/tabelle.md"]  # no pinion data
    table = (tmp_path / "rauheit" / "wheel" / "tabelle.md").read_text(encoding="utf-8")
    assert "72 doppelte Exporte" in table  # 97840 (2 files) stays unassigned, MEAS-04
    assert (
        "| 97340 | Laufversuch (Kerngruppe) |" in table
        and "| links | 2026-05-31 | 1,022 |" in table
    )
    with (tmp_path / "rauheit" / "wheel" / "rohdaten.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    assert len(rows) == 70 and {r["flank"] for r in rows} == {"links", "rechts"}
    assert "Messung-3.Rvk" in rows[0] and rows[0]["Xq-Ra"]
    groups = (tmp_path / "rauheit" / "wheel" / "gruppen.md").read_text(encoding="utf-8")
    assert "| Laufversuch (Kerngruppe) | R_a | links |" in groups
    assert "| Fertigungsstreuung | R_z | rechts |" in groups
