"""Importer of the running-test workbook: remark events, level and speed rules, duplicate and
continuation rows, crack window, loss intervals (L1)."""

import datetime as dt

import pytest

from gearcore.errors import InputRangeError, ParseError
from gearcore.measurement import test_rig as tr

HEADER = ["A", "Datum", "Prüfstand", "Werkstoff", "ME-Nr. Ritzel", "ME-Nr. Rad", "Öltemperatur",
          "Ziel\nZahntemperatur", None, "Versagensart", "Ziel \nDrehoment\nRitzel", "verspannt",
          "Drehmoment Ritzel\nT_0  nach Start", "15 min", "T\n60 min", "T_nachgespannt",
          "Drehmoment Rad", "Drehzahl", "Lastwechsel", "Bemerkung", "Grübchenfläche "]

REMARK_2026 = (
    "50000, 7,2-7,4 Nm, TA 78 °C, TP 74 °C ; \n"
    "270000 6,8 Nm -> nachverspannt auf 7,8-7,9 Nm bei TA 80 °C, TP 75 °C ;  "
    "(ca. 1,2 Nm Verlust über 220000)\n"
    "3653000 6,8 Nm -> nachverspannt auf 8,4-8,5 Nm bei TA 83 °C, TP 75 °C ;  "
    "(ca. 1 Nm Verlust über 3383000), Bilder aufgenommen. Noch keine Anrisse.\n"
    "6610000 6,8 Nm -> nachverspannt auf 8,5-8,7 Nm bei TA 86 °C, TP 76 °C ;  "
    "(ca. 1 Nm Verlust über 2957000), Bilder aufgenommen. Leichte Haarrisse\n"
    "32015000 6,8-7,0 Nm -> nachverspannt auf 7,9-8,0 Nm bei TA 81 °C, TP 75 °C; "
    "Anrisse deutlich sichtbar. Drehzahlsensor ausgefallen. Entsprechend Schätzung auf 40000000\n"
    "Lastwechsel. Versagensgeräusch sehr laut, entsprechend Versuch beendet."
)
REMARK_2023 = "Zahnfußbruch; nachgespannt bei 1 600 000 / 3 375 000 / 4 700 000"


def _row(run_id, date, rig, material, wheel, oil, target, mode, k, q, speed, cycles, remark,
         note=None):
    return [run_id, date, rig, material, "95919", wheel, oil, target, None, mode, k, None, None,
            None, None, None, q, speed, cycles, remark, note]


def test_remark_events_of_2026() -> None:
    events = tr.parse_remark(REMARK_2026)
    counts = [e.cycles for e in events]
    assert counts[:4] == [50000, 270000, 3653000, 6610000]
    second = events[1]
    assert second.torques_Nm == (6.8, 7.8, 7.9) and second.torque_after_Nm == (7.8, 7.9)
    assert (second.aggregate_temperature_C, second.gearing_temperature_C) == (80.0, 75.0)
    assert (second.loss_Nm, second.loss_over_cycles) == (1.2, 220000)
    assert "readjust" in second.observations
    assert events[2].has("no_crack", "check") and not events[2].has("cracks")
    assert (events[2].loss_Nm, events[2].loss_over_cycles) == (1.0, 3383000)
    assert events[3].has("first_signs")
    assert tr.classify("Noch keine Zähne locker. Versagensgeräusch wird lauter.") == ("noise",)
    last = [e for e in events if e.cycles == 32015000][0]
    assert last.has("cracks", "readjust")
    assert any(e.has("noise") for e in events)


def test_remark_lists_of_2023_split_and_inherit() -> None:
    events = tr.parse_remark(REMARK_2023)
    assert [e.cycles for e in events] == [None, 1600000, 3375000, 4700000]
    assert events[0].has("break")
    assert all(e.has("readjust") for e in events[1:])
    assert tr.parse_remark(None) == () and tr.parse_remark("  ") == ()


def test_classify_rules() -> None:
    assert tr.classify("Verzahnung mit bloßem Auge noch ohne Grübchen oder Fußbruchanbahnung") == (
        "no_crack", "pitting")
    assert "readjust" not in tr.classify("7,7-7,8 Nm --> nicht nachverspannt")
    assert tr.classify("sinusförmiges Geräusch -> Vermutung demnächst Versagen") == ("noise",)
    assert tr.classify("ZFB Zahn 31") == ("break",)


def _book() -> tr.Workbook:
    rows = [
        HEADER,
        _row("kst-E_40", dt.datetime(2023, 8, 11), "KV4", "POM", "86474", 76, 80,
             "ZFB: Zähne ab", 8, 8.1568, 2250, "39 370 251", "(ab 8,6Nm:) 39 366 468"),
        _row("kst-E_61", None, "KV3", "PEEK", None, 75, 80, None, 13.73, 13.999, 3058, None, None),
        _row("kst-E_61", dt.datetime(2026, 8, 5), "KV3", "PEEK", "95900", 75, 80, None, 13.73,
             13.999, 3058, "7 923 169", None),
        _row("kst-E_61", None, "KV3", "PEEK", None, 75, 80, None, 13.73, 13.999, 3058,
             "7 923 169", None),
        _row("kst-E_63", dt.datetime(2026, 8, 18), "KV3", "PA46-GF30", "97351", 75, 80, None,
             11.8, 12.03128, 2294, 149937, "nach 2h 81,0°C Zahnflankentemperatur mit Emissionsgrad 1"),
        _row(None, dt.datetime(2026, 8, 18), "KV3", "PA46-GF30", "97351", 75, 80, None, 11.8,
             12.03128, 3058, None, "nach 2h 81,9°C Zahnflankentemperatur"),
        _row(None, dt.datetime(2026, 8, 21), "KV3", "PA46-GF30", "97351", 75, 80, None, None,
             None, 3058, 2424628, "2198207 um 9 Uhr (11,0 Nm), keine Auffälligkeit; 5-6 kaputte Zähne"),
        _row("kst-E-67", dt.datetime(2026, 9, 4), "KV3", "POM", "95878", 75, 80, None, 9.8, None,
             3058, "5 404 530", None),
        _row("kst-E_75", dt.datetime(2026, 9, 28), "KV3", "PA46-GF30", "97364", 75, 80, None,
             7.8, 7.95294, 3058, 40000000, REMARK_2026),
        _row("kst-E_71", dt.datetime(2026, 9, 22), "KV3", "PA46-GF30", "97366", 67, 80,
             "ZFB: Zahn 31", 15.7, 16.00784, 3058, 1210000,
             "962000 13,7 Nm --> nachverspannt auf 16,5-16,7 Nm, bei 70 °C leichte Ermüdung im "
             "Zahnfußbereich zu sehen\n1173000 13,7 Nm --> nachverspannt auf 17,1-17,2 Nm\n"
             "1120000 14,7 Nm --> ZFB Zahn 31",
             "Durch Änderung des Temperatursensors beim Prüfkasten, andere Düse, und womöglich zu "
             "wenig Volumenstrom"),
    ]
    return tr.read_rows(rows, path="test")


def test_levels_speeds_and_flags() -> None:
    book = _book()
    run_2023 = book.run("kst-E_40")
    assert run_2023.level_Nm == 8 and run_2023.cycles == 39370251
    assert run_2023.speed_wheel_rpm == 2250.0
    assert run_2023.speed_pinion_rpm == pytest.approx(2250.0 * 52.0 / 51.0)
    assert run_2023.criterion_guess == "Totalausfall"
    run_2026 = book.run("kst-E_75")
    assert run_2026.level_Nm == 8 and run_2026.speed_wheel_rpm == pytest.approx(3000.0, abs=1.0)
    assert "estimated_cycles" in run_2026.flags
    assert run_2026.criterion_guess == "Versagensgeräusch, Lastspielzahl geschätzt"
    assert run_2026.crack_window == (3653000, 6610000)
    typo = book.run("kst-E_67")
    assert "id_typo" in typo.flags and "wheel_torque_from_pinion" in typo.flags
    assert typo.level_Nm == 10 and typo.wheel_torque_Nm == pytest.approx(9.8 * 52 / 51)
    assert any("kst-E_67: wheel_torque_from_pinion" in a for a in book.anomalies)


def test_duplicate_and_continuation_rows() -> None:
    book = _book()
    peek = book.run("kst-E_61")
    assert peek.rows == (4,) and peek.cycles == 7923169 and "duplicate_rows" in peek.flags
    matrix = book.run("kst-E_63")
    assert "stepped" in matrix.flags and matrix.rows == (6, 7, 8)
    assert [s.flank_temperature_2h_C for s in matrix.stages] == [81.0, 81.9, None]
    assert matrix.cycles == 2424628 and matrix.cycles_raw == "2424628 (letzte Stufenzeile)"
    assert matrix.crack_window == (2198207, None)
    assert matrix.criterion_guess == "Totalausfall"


def test_lubrication_flag_and_order_anomaly() -> None:
    book = _book()
    run = book.run("kst-E_71")
    assert "lubrication_deficit_possible" in run.flags
    assert run.crack_window == (None, 962000)
    assert any("kst-E_71: Lastspielzahlen in Spalte T nicht aufsteigend" in a for a in book.anomalies)


def test_loss_intervals() -> None:
    run = _book().run("kst-E_75")
    intervals = tr.loss_intervals(run)
    assert intervals[0][:4] == (50000, 270000, 1.2, pytest.approx(1.2 / 220000 * 1.0e6))
    assert intervals[1][:2] == (270000, 3653000) and intervals[1][4] == 83.0
    assert intervals[2][2] == 1.0


def test_confirmations(tmp_path) -> None:  # type: ignore[no-untyped-def]
    book = _book()
    path = tmp_path / "user.yaml"
    path.write_text(
        "runs:\n  kst-E_71:\n    criterion: Totalausfall\n    note: vollwertig\n"
        "    withdraw_flags: [lubrication_deficit_possible]\n",
        encoding="utf-8",
    )
    confirmed = tr.apply_confirmations(book, path)
    run = confirmed.run("kst-E_71")
    assert run.criterion == "Totalausfall" and run.criterion_confirmed == "Totalausfall"
    assert run.user_note == "vollwertig" and "lubrication_deficit_possible" not in run.flags
    assert not any(a.startswith("kst-E_71: lubrication") for a in confirmed.anomalies)
    assert confirmed.run("kst-E_75").criterion_confirmed is None
    assert run.cycles_wheel == pytest.approx(1210000 * 51 / 52)
    path.write_text("runs:\n  kst-E_67:\n    speed_pinion_rpm: 3058\n", encoding="utf-8")
    with_speed = tr.apply_confirmations(book, path).run("kst-E_67")
    assert with_speed.speed_pinion_rpm == 3058.0
    assert with_speed.speed_wheel_rpm == pytest.approx(3058.0 * 51 / 52)
    path.write_text("runs:\n  kst-E_99: {criterion: x}\n", encoding="utf-8")
    with pytest.raises(InputRangeError):
        tr.apply_confirmations(book, path)
    # the packaged file names only runs of the real workbook
    data = tr.CONFIRMATIONS.read_text(encoding="utf-8")
    assert "kst-E_66" in data and tr.CONFIRMATIONS.is_file()


def test_bad_header_and_id() -> None:
    with pytest.raises(ParseError):
        tr.read_rows([["x", "y"]])
    with pytest.raises(ParseError):
        tr.read_rows([HEADER, _row("Lauf 1", None, "KV3", None, None, None, None, None, None,
                                   None, None, None, None)])
