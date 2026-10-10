"""Inventory of the measurement folder: folder rules, rounds by date, the user's groups, the scan
of the real folder (skipped where it is absent)."""

from collections import Counter
from pathlib import Path

import pytest

from gearcore.data import load_measurement_parts, measurement_fixture_names
from gearcore.errors import InputRangeError, ParseError
from gearcore.measurement.inventory import (
    COARSE_SCAN_POINTS,
    Inventory,
    classify,
    rounds_by_date,
    scan_folder,
)


@pytest.mark.parametrize(
    "relative, me, part, kind, extra",
    [
        (
            "GINA/Kunststoffrad/Rr_F4028-Kunst_52Z_neu_messwerte/97340-neu.mew",
            "97340",
            "wheel",
            "mew",
            {"variant": "-neu"},
        ),
        (
            "GINA/Kunststoffrad/Rr_F4028-Kunst_52Z_neu_messwerte/97341.mew",
            "97341",
            "wheel",
            "mew",
            {"variant": None},
        ),
        (
            "GINA/Kunststoffrad/Rr_F4028-Kunst_52Z_neu_messkurven/97365_neu.mka",
            "97365",
            "wheel",
            "mka",
            {"variant": "_neu"},
        ),
        (
            "GINA/Stahlritzel/Lw_Stahlri_51Z_kst-E_n_messwerte/95911-neu2.mew",
            "95911",
            "pinion",
            "mew",
            {"variant": "-neu2"},
        ),
        (
            "GINA/Stahlritzel/Lw.Stahlri_51Z_kst-E_n_messblatt/95911-neu.pdf",
            "95911",
            "pinion",
            "messblatt_pdf",
            {},
        ),
        ("Konturscan/Stahlritzel/86481_Z18.DAT", "86481", "pinion", "contour", {"tooth": 18}),
        ("Konturscan/Kunststoffrad/97340-Z1.DAT", "97340", "wheel", "contour", {"tooth": 1}),
        (
            "Konturscan/Kunststoffrad/von_Hiwis/97341_z36.DAT",
            "97341",
            "wheel",
            "contour",
            {"tooth": 36},
        ),
        (
            "Konturscan/Kunststoffrad/von_Hiwis/97373_1.DAT",
            "97373",
            "wheel",
            "contour",
            {"tooth": 1, "anomalies": ("file name without the tooth letter z",)},
        ),
        (
            "Rauheit/Kunststoffrad/ASCII_Export/F4092_97340_li.txt",
            "97340",
            "wheel",
            "roughness",
            {"flank": "li"},
        ),
        (
            "Rauheit/Kunststoffrad/ASCII_Export/F4092_97340_neu_re.txt",
            "97340",
            "wheel",
            "roughness",
            {"flank": "re", "variant": "_neu"},
        ),
        (
            "Rauheit/Kunststoffrad/HWP_Profil_Export/F4092_97340_neu_li_Messung-2.hwp",
            "97340",
            "wheel",
            "roughness_profile",
            {"flank": "li", "trace": 2},
        ),
        (
            "Rauheit/Kunststoffrad/PDF/97340-KST-E_PA46-GF30-li-neu_.pdf",
            "97340",
            "wheel",
            "roughness_pdf",
            {"flank": "li", "batch_label": "KST-E_PA46-GF30"},
        ),
        (
            "Rauheit/Kunststoffrad/PDF/97341-KST_Kunstsoff PA-re-neu_.pdf",
            "97341",
            "wheel",
            "roughness_pdf",
            {"flank": "re", "batch_label": "KST_Kunstsoff PA"},
        ),
    ],
)
def test_classify_by_the_folder_rules(
    relative: str, me: str, part: str, kind: str, extra: dict[str, object]
) -> None:
    file = classify(relative)
    assert file is not None
    assert (file.me, file.part, file.kind) == (me, part, kind)
    for name, value in extra.items():
        assert getattr(file, name) == value, name


def test_ignored_and_unknown_paths() -> None:
    assert classify("Auswertung/MEW_Auslesen_V1.xlsm") is None
    assert classify("GINA/Kunststoffrad/Rr_F4028-Kunst_52Z_neu_messblatt/Thumbs.db") is None
    for relative in (
        "GINA/Kunststoffrad/x/97340.mew",
        "Konturscan/Kunststoffrad/97340.DAT",
        "notes.txt",
    ):
        with pytest.raises(ParseError):
            classify(relative)


def test_rounds_by_date_cluster_close_dates() -> None:
    rounds = rounds_by_date(["2026-05-09", "2026-05-08", "2026-05-13", "2026-05-27", "2026-06-10"])
    assert rounds == {
        "2026-05-08": 1,
        "2026-05-09": 1,
        "2026-05-13": 1,
        "2026-05-27": 2,
        "2026-06-10": 3,
    }
    assert rounds_by_date([]) == {}
    assert rounds_by_date(["2025-10-13", "2025-10-10"]) == {"2025-10-10": 1, "2025-10-13": 1}


def test_parts_yaml_carries_the_user_groups() -> None:
    parts = load_measurement_parts()
    wheel = parts["parts"]["wheel"]["groups"]
    assert len(wheel["core"]) == 10 and "97340" in wheel["core"] and "97364" not in wheel["core"]
    labels = parts["parts"]["wheel"]["labels"]
    assert labels["running_in"] == ["97351"] and labels["extra_test"] == ["97364"]
    assert set(labels["running_in"]) <= set(wheel["core"])
    pinion = parts["parts"]["pinion"]["groups"]
    assert len(pinion["rig_series"]) == 7 and pinion["older"] == ["86481"]
    assert parts["failure_window"]["wheel"] == {"first_tooth": 36, "last_tooth": 40}
    assert set(measurement_fixture_names()) >= {"wheel_97340-neu.mew", "pinion_95911-neu.mew"}


def test_scan_of_the_real_folder(measurements_root: Path) -> None:
    inventory = scan_folder(measurements_root)
    assert isinstance(inventory, Inventory) and not inventory.unknown
    groups = Counter((part.part, part.group) for part in inventory.parts)
    assert groups[("wheel", "core")] == 10 and ("wheel", "extra_test") not in groups
    assert groups[("pinion", "rig_series")] == 7 and groups[("pinion", "older")] == 1
    assert groups[("wheel", "scatter")] >= 26
    assert inventory.part("97364").group == "scatter"
    assert inventory.part("97364").labels == ("extra_test",)
    assert inventory.part("97351").labels == ("running_in",)
    kinds = Counter(file.kind for part in inventory.parts for file in part.files)
    assert kinds["mew"] == kinds["mka"] and kinds["mew"] >= 68
    assert kinds["contour"] >= 79 and kinds["roughness"] >= 140
    assert {file.me for file in inventory.unassigned} == {"97840"}
    core = inventory.of_group("core")
    assert {part.me for part in core} == {
        "97340",
        "97345",
        "97346",
        "97350",
        "97351",
        "97355",
        "97360",
        "97361",
        "97365",
        "97366",
    }
    wheel_97340 = inventory.part("97340")
    assert wheel_97340.material == "PA46-GF30" and wheel_97340.rounds == (1,)
    assert all(f.measured_on == "2026-05-09" for f in wheel_97340.of_kind("mew"))
    assert len(wheel_97340.of_kind("contour")) == 1 and wheel_97340.of_kind("contour")[0].points
    coarse = [a for a in inventory.anomalies if "coarse scan" in a]
    assert len(coarse) >= 30 and all(
        int(a.split("(")[1].split()[0]) < COARSE_SCAN_POINTS for a in coarse
    )
    assert any("2 blocks" in a for a in inventory.anomalies)
    assert any("97373_1.DAT" in a for a in inventory.anomalies)
    pinion = inventory.part("95911")
    assert pinion.group == "rig_series" and len(pinion.of_kind("mew")) == 2
    assert sorted(f.repeat for f in pinion.of_kind("mew")) == [1, 2]
    assert {f.measurement_round for f in pinion.of_kind("mew")} == {1}
    assert inventory.part("97342").rounds == (3,)
    with pytest.raises(InputRangeError):
        inventory.part("00000")


def test_scan_of_a_missing_folder_is_an_input_error(tmp_path: Path) -> None:
    with pytest.raises(InputRangeError):
        scan_folder(tmp_path / "nowhere")
