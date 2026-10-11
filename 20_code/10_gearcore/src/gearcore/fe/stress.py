"""Reader of the stress files of the positions (``<job>_stress.npz``, stress format 1).

``scripts/fe_odb_extract.py`` writes, beside the fields JSON, the nodal averaged stress tensor of
every node of the wheel per step in the frame of the wheel part (ADR-118): six components in the
Abaqus order ``S11, S22, S33, S12, S13, S23`` in the single precision of the output database,
the node labels, the coordinates in the
part frame, the count of element-nodal values behind every node, every node set of the wheel
instance and the rotation of the instance that was undone. This module reads such a file and
lines the files of a folder up along the path of contact with ``gearcore.fe.evaluation``; the
check after Stommel et al. (``gearcore.fatigue.check``) consumes them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt

from gearcore.errors import InputRangeError, ParseError
from gearcore.fe import evaluation as ev

STRESS_FORMAT_VERSION = 1
COMPONENTS = ("S11", "S22", "S33", "S12", "S13", "S23")
_REQUIRED = (
    "format",
    "odb",
    "components",
    "wheel_turn_deg",
    "wheel_turn_known",
    "wheel_axis",
    "node_labels",
    "coordinates",
    "node_element_count",
    "step_names",
    "step_complete",
    "step_time",
)


@dataclass(frozen=True)
class StressFile:
    """The stress tensors of every wheel node of one position, per step."""

    path: Path
    odb: str
    wheel_turn_deg: float
    wheel_turn_known: bool
    wheel_axis: tuple[float, float]
    node_labels: npt.NDArray[np.int32]
    coordinates: npt.NDArray[np.float64]
    """(n, 3) in the part frame of the wheel."""
    node_element_count: npt.NDArray[np.int16]
    step_names: tuple[str, ...]
    step_complete: tuple[bool, ...]
    step_time: tuple[float, ...]
    sets: Mapping[str, npt.NDArray[np.int32]]
    """Node labels of every node set of the wheel instance."""
    _stress: Mapping[str, npt.NDArray[np.float64]]

    def stress(self, step: str) -> npt.NDArray[np.float64]:
        """(n, 6) components of the step (read into double precision, ADR-106)."""
        if step not in self._stress:
            raise InputRangeError(f"{self.path.name}: no step {step!r}; steps: {self.step_names}")
        return np.asarray(self._stress[step], dtype=np.float64)

    def is_complete(self, step: str) -> bool:
        if step not in self.step_names:
            raise InputRangeError(f"{self.path.name}: no step {step!r}; steps: {self.step_names}")
        return self.step_complete[self.step_names.index(step)]

    def index_of(self, labels: npt.ArrayLike) -> npt.NDArray[np.int64]:
        """Row indices of node labels (``InputRangeError`` for a label that is not a wheel node)."""
        wanted = np.asarray(labels, dtype=np.int64)
        lookup = np.full(int(self.node_labels.max()) + 1, -1, dtype=np.int64)
        lookup[self.node_labels] = np.arange(self.node_labels.size)
        if np.any(wanted < 0) or np.any(wanted >= lookup.size):
            raise InputRangeError("node label outside the wheel")
        index = lookup[wanted]
        if np.any(index < 0):
            raise InputRangeError("node label is not a node of the wheel")
        return index

    @property
    def n_nodes(self) -> int:
        return int(self.node_labels.size)


def stress_file_path(folder: Path, job: str) -> Path:
    return folder / f"{job}_stress.npz"


def read_stress_file(path: Path) -> StressFile:
    """Read one stress file; ``ParseError`` when it is not a stress file of format 1."""
    try:
        archive = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as error:
        raise ParseError(f"{path}: {error}") from error
    with archive:
        keys = set(archive.files)
        missing = [key for key in _REQUIRED if key not in keys]
        if missing:
            raise ParseError(f"{path}: not a stress file (missing {missing})")
        version = int(archive["format"])
        if version != STRESS_FORMAT_VERSION:
            raise ParseError(f"{path}: stress format {version}, expected {STRESS_FORMAT_VERSION}")
        components = tuple(str(c) for c in archive["components"])
        if components != COMPONENTS:
            raise ParseError(f"{path}: components {components} differ from {COMPONENTS}")
        step_names = tuple(str(name) for name in archive["step_names"])
        stress: dict[str, npt.NDArray[np.float64]] = {}
        for name in step_names:
            key = "S__" + name
            if key not in keys:
                raise ParseError(f"{path}: step {name!r} without stress array {key!r}")
            array = np.asarray(archive[key], dtype=np.float64)
            stress[name] = array
        labels = np.asarray(archive["node_labels"], dtype=np.int32)
        coordinates = np.asarray(archive["coordinates"], dtype=np.float64)
        if coordinates.shape != (labels.size, 3):
            raise ParseError(
                f"{path}: coordinates {coordinates.shape} do not match {labels.size} nodes"
            )
        for name, array in stress.items():
            if array.shape != (labels.size, 6):
                raise ParseError(f"{path}: stress of step {name!r} has shape {array.shape}")
        sets = {
            key[5:]: np.asarray(archive[key], dtype=np.int32)
            for key in sorted(keys)
            if key.startswith("set__")
        }
        axis = np.asarray(archive["wheel_axis"], dtype=np.float64)
        return StressFile(
            path=path,
            odb=str(archive["odb"]),
            wheel_turn_deg=float(archive["wheel_turn_deg"]),
            wheel_turn_known=bool(archive["wheel_turn_known"]),
            wheel_axis=(float(axis[0]), float(axis[1])),
            node_labels=labels,
            coordinates=coordinates,
            node_element_count=np.asarray(archive["node_element_count"], dtype=np.int16),
            step_names=step_names,
            step_complete=tuple(bool(c) for c in archive["step_complete"]),
            step_time=tuple(float(t) for t in archive["step_time"]),
            sets=sets,
            _stress=stress,
        )


@dataclass(frozen=True)
class PositionStress:
    """A position of a folder with its stress file (``None`` when not extracted yet)."""

    point: ev.PathPoint
    path: Path | None


def positions_with_stress(
    manifest: Mapping[str, object], folder: Path, series: str | None = None
) -> tuple[PositionStress, ...]:
    """The positions of a folder (one series) along the path of contact with the paths of their
    stress files; a position without a stress file carries ``None``."""
    points = ev.path_points(manifest, folder, series)
    out = []
    for point in points:
        path = stress_file_path(folder, point.job)
        out.append(PositionStress(point=point, path=path if path.is_file() else None))
    return tuple(out)
