"""``scripts/fe_fatigue.py``: what a folder records for the orientation-file guard of one
series (its own orientation piece, the file and the card the decks were built with)."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


@pytest.fixture(scope="module")
def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("fe_fatigue", SCRIPTS / "fe_fatigue.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_the_piece_file_and_card_of_the_series_rate(script: ModuleType, tmp_path: Path) -> None:
    (tmp_path / "wheel_orientation_DY1_part.inp").write_text("*DISTRIBUTION\n", encoding="utf-8")
    manifest = {
        "rates": {
            "QS": {
                "file": "C:/cards/wheel_mesh_QS.cof",
                "name": "PA46_GF30_QS_cond_aniso",
                "orientation_files": ["wheel_orientation_QS_part.inp"],
            },
            "DY1": {
                "file": "C:/cards/wheel_mesh_DY1.cof",
                "name": "PA46_GF30_DY1_cond_aniso",
                "orientation_files": [
                    "wheel_orientation_DY1_part.inp",
                    "wheel_orientation_DY1_model.inp",
                ],
            },
        }
    }
    found = script._orientation_reference(tmp_path, manifest, "W3_DY1")
    assert found.piece_name == "wheel_orientation_DY1_part.inp"
    assert found.piece_text == "*DISTRIBUTION\n"
    assert found.recorded_file == "wheel_mesh_DY1.cof"
    assert found.recorded_card == "PA46_GF30_DY1_cond_aniso"
    # the QS piece is not on disk: no piece, but the file and the card are known
    missing = script._orientation_reference(tmp_path, manifest, "W4_QS")
    assert missing.piece_name is None and missing.piece_text is None
    assert missing.recorded_file == "wheel_mesh_QS.cof"
    assert missing.recorded_card == "PA46_GF30_QS_cond_aniso"
    # a series without a rate name in a folder of two rates: nothing to pick
    none = script._orientation_reference(tmp_path, manifest, "W3")
    assert none == script.OrientationReference(None, None, None, None)


def test_a_single_rate_and_an_old_folder(script: ModuleType, tmp_path: Path) -> None:
    (tmp_path / "wheel_orientation_part.inp").write_text("*DISTRIBUTION\n", encoding="utf-8")
    single = {
        "rates": {
            "QS": {
                "file": "cards/wheel-pocket_mesh_QS.cof",
                "name": "PA46_GF30_QS_cond_aniso",
                "orientation_files": [],
            }
        },
        "orientation_files": ["wheel_orientation_part.inp"],
    }
    found = script._orientation_reference(tmp_path, single, "W3")
    assert found.recorded_file == "wheel-pocket_mesh_QS.cof"
    assert found.recorded_card == "PA46_GF30_QS_cond_aniso"
    assert found.piece_name is None  # the rate entry lists no files, the top level is not used
    old = {
        "material_card": {"name": "PA46_GF30_QS_cond_aniso"},
        "orientation_files": ["wheel_orientation_part.inp"],
    }
    found = script._orientation_reference(tmp_path, old, None)
    assert found.piece_name == "wheel_orientation_part.inp"
    assert found.recorded_file is None
    assert found.recorded_card == "PA46_GF30_QS_cond_aniso"
