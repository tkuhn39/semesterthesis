"""The stress files of the positions (``gearcore.fe.stress``)."""

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from gearcore.errors import InputRangeError, ParseError
from gearcore.fe import stress as sf


def write_stress_file(
    path: Path,
    *,
    labels: tuple[int, ...] = (1, 2, 3, 10),
    steps: tuple[str, ...] = ("SEAT", "LOAD_8NM"),
    complete: tuple[bool, ...] = (True, True),
    turn_deg: float = 30.0,
    turn_known: bool = True,
    values: dict[str, np.ndarray] | None = None,
    format_version: int = 1,
) -> Path:
    """A stress file as ``fe_odb_extract.py`` writes it (stress format 1)."""
    n = len(labels)
    arrays: dict[str, Any] = {}
    for i, name in enumerate(steps):
        if values is not None and name in values:
            arrays["S__" + name] = np.asarray(values[name], dtype=np.float32)
        else:
            arrays["S__" + name] = (np.arange(n * 6, dtype=np.float32).reshape(n, 6) + 1.0) * (
                i + 1
            )
    np.savez_compressed(
        path,
        format=np.int32(format_version),
        odb=np.str_("pos_001.odb"),
        components=np.array(sf.COMPONENTS),
        frame=np.str_("wheel part frame"),
        wheel_turn_deg=np.float64(turn_deg),
        wheel_turn_known=np.bool_(turn_known),
        wheel_axis=np.array([52.0, 0.0]),
        node_labels=np.array(labels, dtype=np.int32),
        coordinates=np.arange(n * 3, dtype=np.float32).reshape(n, 3),
        node_element_count=np.full(n, 8, dtype=np.int16),
        step_names=np.array(steps),
        step_complete=np.array(complete, dtype=bool),
        step_time=np.array([1.0 if c else 0.4 for c in complete]),
        set__WHEEL_ROOT_T2_T3_SURF_NODES=np.array([2, 3], dtype=np.int32),
        **arrays,
    )
    return path


def test_reads_the_file_and_its_arrays(tmp_path: Path) -> None:
    file = sf.read_stress_file(write_stress_file(tmp_path / "pos_001_stress.npz"))
    assert file.n_nodes == 4 and file.step_names == ("SEAT", "LOAD_8NM")
    assert file.wheel_turn_deg == 30.0 and file.wheel_turn_known and file.wheel_axis == (52.0, 0.0)
    assert file.coordinates.shape == (4, 3) and file.node_element_count.tolist() == [8, 8, 8, 8]
    stress = file.stress("LOAD_8NM")
    assert stress.dtype == np.float64 and stress.shape == (4, 6)
    assert stress[0].tolist() == pytest.approx([2.0, 4.0, 6.0, 8.0, 10.0, 12.0])
    assert file.is_complete("SEAT")
    assert file.index_of([10, 2]).tolist() == [3, 1]
    assert file.sets["WHEEL_ROOT_T2_T3_SURF_NODES"].tolist() == [2, 3]
    with pytest.raises(InputRangeError):
        file.stress("LOAD_99NM")
    with pytest.raises(InputRangeError):
        file.index_of([99])
    with pytest.raises(InputRangeError):
        file.is_complete("LOAD_99NM")


def test_refuses_other_files(tmp_path: Path) -> None:
    with pytest.raises(ParseError, match="format 2"):
        sf.read_stress_file(write_stress_file(tmp_path / "a_stress.npz", format_version=2))
    np.savez(tmp_path / "b_stress.npz", format=np.int32(1), odb=np.str_("x"))
    with pytest.raises(ParseError, match="not a stress file"):
        sf.read_stress_file(tmp_path / "b_stress.npz")
    with pytest.raises(ParseError):
        sf.read_stress_file(tmp_path / "missing_stress.npz")


def test_positions_with_stress_follow_the_manifest(tmp_path: Path) -> None:
    manifest = {
        "material_step": "W1",
        "positions": [
            {"index": 2, "file": "pos_002.inp", "point": "", "from_A_mm": 2.0, "rho_1_mm": 9.5},
            {"index": 1, "file": "pos_001.inp", "point": "C", "from_A_mm": 1.0, "rho_1_mm": 9.0},
        ],
    }
    write_stress_file(tmp_path / "pos_001_stress.npz")
    positions = sf.positions_with_stress(manifest, tmp_path, series="W1")
    assert [p.point.job for p in positions] == ["pos_001", "pos_002"]  # sorted along the path
    assert positions[0].path == tmp_path / "pos_001_stress.npz" and positions[1].path is None
    assert sf.positions_with_stress(manifest, tmp_path, series="W3") == ()
