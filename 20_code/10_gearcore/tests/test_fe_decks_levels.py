"""``scripts/build_fe_decks.py decks --levels pocket``: the ring body swept to the z-levels of
the pocket body, so that a ring mesh and a pocket mesh share the node positions of their teeth
(the CONVERSE mapping on both then samples the fibre orientation at the same points)."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

from gearcore.errors import InputRangeError
from gearcore.fe import body as bd

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


@pytest.fixture(scope="module")
def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_fe_decks", SCRIPTS / "build_fe_decks.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _z_levels(mesh_file: Path) -> list[float]:
    levels: set[float] = set()
    inside = False
    for line in mesh_file.read_text(encoding="ascii").splitlines():
        if line.startswith("*"):
            inside = line.upper().startswith("*NODE")
            continue
        if inside and line[:1].strip():
            levels.add(float(line.split(",")[3]))
    return sorted(levels)


def _decks(script: ModuleType, out: Path, **overrides: object) -> list[str]:
    settings: dict[str, object] = {
        "teeth": 1,
        "rim_rings": 12,
        "layers": 4,
        "element_type": "C3D8I",
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


def test_ring_body_on_the_levels_of_the_pocket_body(script: ModuleType, tmp_path: Path) -> None:
    counts = bd.BodyCounts(web_layers=2, flange_layers=1)
    out = tmp_path / "levels"
    lines = _decks(script, out, level_counts=counts)
    shape = bd.body_section("kst_e", "wheel")
    expected = bd.body_levels(shape, counts)
    assert np.allclose(_z_levels(out / "wheel_mesh.inp"), expected)
    assert np.allclose(expected, [-7.5, -shape.bottom_z_mm, 0.0, shape.bottom_z_mm, 7.5])
    assert any("z-levels of the pocket body" in line for line in lines)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["wheel_mesh"]["levels"] == "pocket"
    assert manifest["wheel_mesh"]["body"] == {"shape": "ring"}
    assert np.allclose(manifest["wheel_mesh"]["z_levels_mm"], expected)
    assert manifest["wheel_mesh"]["level_counts"] == {"web_layers": 2, "flange_layers": 1}
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "z-Ebenen des Taschenkörpers" in readme and "eigenes Mapping" in readme
    # the ring body without levels keeps the equal layers and says so
    plain = tmp_path / "plain"
    _decks(script, plain)
    assert np.allclose(_z_levels(plain / "wheel_mesh.inp"), [-7.5, -3.75, 0.0, 3.75, 7.5])
    plain_manifest = json.loads((plain / "manifest.json").read_text(encoding="utf-8"))
    assert plain_manifest["wheel_mesh"]["levels"] == "equal"
    assert plain_manifest["wheel_mesh"]["level_counts"] is None


def test_levels_must_match_the_layers_and_the_ring_body(script: ModuleType, tmp_path: Path) -> None:
    with pytest.raises(InputRangeError, match="layers is 4"):
        _decks(script, tmp_path / "a", level_counts=bd.BodyCounts(web_layers=2, flange_layers=2))
    with pytest.raises(InputRangeError, match="apply to the ring body"):
        _decks(
            script,
            tmp_path / "b",
            level_counts=bd.BodyCounts(web_layers=2, flange_layers=1),
            body="pocket",
            body_counts=bd.BodyCounts(
                hub_rings=1, pocket_rings=1, rim_rings=1, web_layers=2, flange_layers=1
            ),
        )
