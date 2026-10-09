"""Options of ``scripts/build_fe_decks.py decks`` that write a retry folder: a subset of the
grid with the numbering of the full grid, the enforcement of the contact constraint, the
rounding of the tip corners of the rigid surface."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from gearcore.errors import InputRangeError

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


@pytest.fixture(scope="module")
def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_fe_decks", SCRIPTS / "build_fe_decks.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # the dataclasses of the script resolve their string annotations through sys.modules
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _decks(script: ModuleType, out: Path, **overrides: object) -> list[str]:
    settings: dict[str, object] = {
        "teeth": 1,
        "rim_rings": 12,
        "layers": 2,
        "element_type": "C3D8I",
        "counts": script.LE_COUNTS,
        "bore_radius_mm": None,
        "rotation": "clockwise",
        "material_steps": ["W1"],
        "cofs": [script.REFERENCE_COF],
        "rates": ["QS"],
        "temperature_c": 80.0,
        "torques_wheel_nm": [8.0],
        "positions": ["grid"],
        "steps_per_pitch": 4,
        "margin": 0.5,
        "seating_arc_mm": 0.01,
        "max_edge_mm": 0.4,
        "out": out,
    }
    settings.update(overrides)
    lines: list[str] = script.decks("kst_e", **settings)
    return lines


def _profile_nodes(folder: Path) -> int:
    return sum(
        1
        for line in (folder / "pinion_surface.inp").read_text(encoding="ascii").splitlines()
        if line[:1].isdigit() and line.count(",") == 3
    )


def test_retry_folder_keeps_the_numbering_and_sets_the_enforcement(
    script: ModuleType, tmp_path: Path
) -> None:
    out = tmp_path / "retry"
    lines = _decks(
        script, out, grid_indices=[3, 2], enforcement="penalty", iteration_limits=(20, 30, 100)
    )
    assert sorted(p.name for p in out.glob("pos_*.inp")) == ["pos_002.inp", "pos_003.inp"]
    assert any("2 position files" in line for line in lines)
    deck = (out / "pos_003.inp").read_text(encoding="ascii")
    assert "position 3 of " in deck and "enforcement penalty" in deck
    assert "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD, PENALTY=LINEAR" in deck
    assert "iterations I_0/I_R/I_C 20/30/100" in deck
    assert deck.count("*CONTROLS, PARAMETERS=TIME INCREMENTATION\n20, 30, , 100\n") == 2  # 2 steps
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["enforcement"] == "penalty" and manifest["grid"]["indices"] == [3, 2]
    assert manifest["iteration_limits"] == [20, 30, 100]
    assert [e["index"] for e in manifest["positions"]] == [2, 3]
    assert all(e["enforcement"] == "penalty" for e in manifest["positions"])
    assert all(e["iteration_limits"] == [20, 30, 100] for e in manifest["positions"])
    assert manifest["pinion_surface"]["tip_rounding_mm"] == 0.0
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "PENALTY=LINEAR" in readme and "I_0/I_R/I_C = 20/30/100" in readme
    # line search and a shift of the positions along the path (a retry of a position whose
    # contact state does not converge): the file keeps its number, the manifest the shift
    shifted = tmp_path / "shifted"
    _decks(script, shifted, grid_indices=[2], line_search=5, shift_mm=0.01)
    deck = (shifted / "pos_002.inp").read_text(encoding="ascii")
    assert deck.count("*CONTROLS, PARAMETERS=LINE SEARCH\n5\n") == 2 and "line search 5" in deck
    assert "(shifted by 0.01 mm)" in deck
    moved = json.loads((shifted / "manifest.json").read_text(encoding="utf-8"))
    assert moved["line_search"] == 5 and moved["shift_mm"] == 0.01
    entry, original = moved["positions"][0], manifest["positions"][0]
    assert entry["index"] == original["index"] == 2 and entry["shift_mm"] == 0.01
    assert entry["from_A_mm"] == pytest.approx(original["from_A_mm"] + 0.01)
    assert entry["rho_1_mm"] == pytest.approx(original["rho_1_mm"] + 0.01)
    assert "0.01 mm" in (shifted / "README.md").read_text(encoding="utf-8")
    # a variant that names its own enforcement wins over the option
    other = tmp_path / "direct"
    _decks(script, other, grid_indices=[2], variants=["direct"], enforcement="penalty")
    deck = (other / "pos_002_direct.inp").read_text(encoding="ascii")
    assert "TYPE=SURFACE TO SURFACE" in deck and "enforcement direct" in deck
    assert "PRESSURE-OVERCLOSURE=HARD, DIRECT" in deck
    with pytest.raises(InputRangeError):
        _decks(script, tmp_path / "bad", grid_indices=[0])
    with pytest.raises(InputRangeError):
        _decks(script, tmp_path / "bad", grid_indices=[2, 2])
    with pytest.raises(InputRangeError):
        _decks(script, tmp_path / "bad", enforcement="soft")


def test_tip_rounding_reaches_the_rigid_surface_and_the_manifest(
    script: ModuleType, tmp_path: Path
) -> None:
    sharp = tmp_path / "sharp"
    rounded = tmp_path / "rounded"
    _decks(script, sharp, grid_indices=[2])
    lines = _decks(script, rounded, grid_indices=[2], tip_rounding_mm=0.05, rounding_facets=12)
    assert any("tip corners rounded with 0.05 mm (at least 12 facets" in line for line in lines)
    assert _profile_nodes(rounded) > _profile_nodes(sharp)
    manifest = json.loads((rounded / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["pinion_surface"]["tip_rounding_mm"] == 0.05
    assert manifest["pinion_surface"]["rounding_facets"] == 12
    assert "mindestens 12 Facetten" in (rounded / "README.md").read_text(encoding="utf-8")
    assert "0.05 mm gerundet" in (rounded / "README.md").read_text(encoding="utf-8")
    assert "scharfe Kopfkanten" in (sharp / "README.md").read_text(encoding="utf-8")
