"""The numpy helpers of the extraction script (``scripts/fe_odb_extract.py``): the tensor
helpers, the rotation into the part frame, the local-to-global transform and the quaternion.
The script imports without Abaqus; only ``extract`` needs its Python."""

import importlib.util
import math
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


@pytest.fixture(scope="module")
def extract() -> ModuleType:
    spec = importlib.util.spec_from_file_location("fe_odb_extract", SCRIPTS / "fe_odb_extract.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_module_imports_without_abaqus(extract: ModuleType) -> None:
    assert extract.ABAQUS_PYTHON is False
    with pytest.raises(RuntimeError, match="Python of Abaqus"):
        extract.extract("x.odb", "x.json")


def test_tensor_helpers_round_trip(extract: ModuleType) -> None:
    components = np.array([[10.0, -5.0, 2.0, 3.0, 1.0, -2.0], [1.0, 2.0, 3.0, 0.0, 0.0, 0.0]])
    tensors = extract.tensors_from_components(components)
    assert np.allclose(tensors[0], tensors[0].T)
    assert np.allclose(extract.components_from_tensors(tensors), components)


def test_part_frame_undoes_the_instance_rotation(extract: ModuleType) -> None:
    """A uniaxial stress along the part x-axis, seen in a global frame where the instance was
    turned by 30 degrees about z, comes back as the uniaxial stress along x."""
    turn = 30.0
    r = extract.rotation_about_z(turn)
    assert np.allclose(r @ r.T, np.eye(3))
    part = np.array([[100.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    t_part = extract.tensors_from_components(part)[0]
    global_tensor = r @ t_part @ r.T  # global = R part R^T
    global_components = extract.components_from_tensors(global_tensor[None])
    assert global_components[0, 3] == pytest.approx(100.0 * math.sin(math.radians(60.0)) / 2.0)
    axis = (52.0, 0.0)
    x_part = np.array([[24.8, 1.0, -3.0]])
    x_global = (r @ x_part.T).T + np.array([axis[0], axis[1], 0.0])
    s_back, x_back = extract.to_part_frame(global_components, x_global, axis, turn)
    assert np.allclose(s_back, part, atol=1e-12)
    assert np.allclose(x_back, x_part, atol=1e-12)


def test_local_to_global_uses_rows_as_local_axes(extract: ModuleType) -> None:
    """A local system whose 1-axis is the global y-axis: a local S11 becomes a global S22."""
    q = np.array([[[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]])  # rows = local axes
    local = np.array([[50.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    assert np.allclose(extract.local_to_global(local, q), [[0.0, 50.0, 0.0, 0.0, 0.0, 0.0]])


def test_rotation_from_quaternion(extract: ModuleType) -> None:
    identity = extract.rotation_from_quaternion(np.array([[0.0, 0.0, 0.0, 1.0]]))
    assert np.allclose(identity[0], np.eye(3))
    half = math.radians(45.0)  # a rotation of 90 degrees about z
    about_z = extract.rotation_from_quaternion(
        np.array([[0.0, 0.0, math.sin(half), math.cos(half)]])
    )
    assert np.allclose(about_z[0], extract.rotation_about_z(90.0), atol=1e-12)
    assert np.allclose(about_z[0] @ about_z[0].T, np.eye(3))
    with pytest.raises(ValueError):
        extract.rotation_from_quaternion(np.array([[1.0, 0.0, 0.0]]))
