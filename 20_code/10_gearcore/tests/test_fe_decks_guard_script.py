"""``scripts/build_fe_decks.py decks`` with W3: the orientation-file guard at the generation
(labels of the file against the mesh) and the order of ``--cof`` against ``--rates``."""

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
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _decks(script: ModuleType, out: Path, **overrides: object) -> list[str]:
    settings: dict[str, object] = {
        "teeth": 1,
        "rim_rings": 12,
        "layers": 2,
        "element_type": None,
        "counts": script.LE_COUNTS,
        "bore_radius_mm": None,
        "rotation": "clockwise",
        "material_steps": ["W1"],
        "cofs": [script.REFERENCE_COF],
        "rates": ["QS"],
        "temperature_c": 80.0,
        "torques_wheel_nm": [8.0],
        "positions": ["pilot"],
        "steps_per_pitch": 4,
        "margin": 0.5,
        "seating_arc_mm": 0.01,
        "max_edge_mm": 0.4,
        "out": out,
    }
    settings.update(overrides)
    lines: list[str] = script.decks("kst_e", **settings)
    return lines


@pytest.fixture(scope="module")
def mesh_counts(script: ModuleType, tmp_path_factory: pytest.TempPathFactory) -> tuple[int, int]:
    out = tmp_path_factory.mktemp("w1")
    _decks(script, out)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    return int(manifest["wheel_mesh"]["elements"]), int(manifest["wheel_mesh"]["nodes"])


def test_a_fitting_synthetic_file_passes_the_generation_guard(
    script: ModuleType, mesh_counts: tuple[int, int], tmp_path: Path
) -> None:
    elements, nodes = mesh_counts
    card = script.REFERENCE_COF.read_text(encoding="utf-8", errors="replace")
    cof = tmp_path / "synthetic_QS.cof"
    cof.write_text(script.synthetic_orientation_text(elements, nodes, card), encoding="utf-8")
    lines = _decks(script, tmp_path / "w3", material_steps=["W3"], cofs=[cof], rates=["QS"])
    assert any("fits the mesh by its labels" in line for line in lines)
    assert not any(line.startswith("note: the card") for line in lines)
    assert (tmp_path / "w3" / "wheel_orientation_QS_part.inp").is_file()


def test_a_file_of_another_mesh_is_refused_at_the_generation(
    script: ModuleType, mesh_counts: tuple[int, int], tmp_path: Path
) -> None:
    elements, nodes = mesh_counts
    card = script.REFERENCE_COF.read_text(encoding="utf-8", errors="replace")
    cof = tmp_path / "other_mesh_QS.cof"
    cof.write_text(script.synthetic_orientation_text(elements + 1, nodes, card), encoding="utf-8")
    with pytest.raises(InputRangeError, match="not in the mesh"):
        _decks(script, tmp_path / "w3", material_steps=["W3"], cofs=[cof], rates=["QS"])


def test_a_swapped_cof_order_is_refused(
    script: ModuleType, mesh_counts: tuple[int, int], tmp_path: Path
) -> None:
    # the reference card is the QS card: given as the file of rate DY1 it is refused, with
    # W1 alone as well (the material tables would be those of the other rate)
    with pytest.raises(InputRangeError, match="carries the rate QS"):
        _decks(script, tmp_path / "w1", cofs=[script.REFERENCE_COF], rates=["DY1"])
