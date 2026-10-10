"""Tables and labels of the measurement reports."""

import pytest

from gearcore.errors import InputRangeError
from gearcore.measurement import report


def test_german_number_and_plain_symbols() -> None:
    assert report.german_number(31.567, 1) == "31,6" and report.german_number(2.0, 3) == "2,000"
    assert report.german_number(-0.004, 2) == "0,00" and report.german_number(-0.5, 1) == "-0,5"
    assert report.plain_symbol("F_p") == "F_p"
    assert report.plain_symbol("f_H_alpha") == "f_Hα"
    assert report.plain_symbol("L_C_alpha_a") == "L_Cαa"
    assert report.plain_symbol("d_a") == "d_a" and report.plain_symbol("F_r") == "F_r"
    assert report.plain_symbol("alpha_wt") == "α_wt"
    with pytest.raises(InputRangeError):
        report.plain_symbol("")


def test_quantity_labels_come_from_the_registry() -> None:
    assert report.quantity_label("profile_slope_deviation") == "f_Hα in µm"
    assert report.quantity_label("span_measurement") == "W_k in mm"
    assert report.quantity_label("sector_pitch_deviation", unit=False) == "F_pk"
    with pytest.raises(InputRangeError):
        report.quantity_label("no_such_quantity")


def test_tables() -> None:
    lines = report.markdown_table(["ME", "F_p in µm"], [["97340", "31,6"], ["97341", "33,1"]])
    assert lines[0] == "| ME | F_p in µm |" and lines[1] == "|---|---|"
    assert lines[2] == "| 97340 | 31,6 |" and len(lines) == 4
    text = report.csv_text(["me", "value"], [["97340", "31,6"]])
    assert text == "me;value\n97340;31,6\n"
    with pytest.raises(InputRangeError):
        report.markdown_table(["a", "b"], [["only one"]])
    with pytest.raises(InputRangeError):
        report.csv_text(["a"], [["x", "y"]])
