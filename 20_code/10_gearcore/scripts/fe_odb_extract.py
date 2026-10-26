"""Extraction of one position result from its Abaqus output database (``.odb``).

Runs under the Python of Abaqus (``abaqus python extract_odb.py <job>``; Abaqus 2025 ships
Python 3.10 with numpy), standalone, without ``gearcore``. ``run_all.ps1`` calls it after every
job; the Learning Edition's Python opens the output databases of the full licence as well
(``build_fe_decks.py extract``). It writes two files next to the ``.odb``:

``<job>_fields.json`` (format 1): per step (last frame) the reactions, moments and rotations of
both reference points, the closed contact nodes of the wheel flank with their coordinates,
pressure and (when CFORCE was requested) normal force, the nodal averaged stresses of every root
fillet surface (mid-width nodes in full, per layer the largest tensile and the most compressive
principal stress) and the largest displacement of every tooth head. Its reader is
``gearcore.fe.evaluation``.

``<job>_stress.npz`` (stress format 1, ADR-118): the nodal averaged stress tensor of every node
of the wheel per step, six components ``S11, S22, S33, S12, S13, S23`` in single precision,
together with the node labels, the coordinates and every node set of the wheel instance. Tensor
and coordinates are given in the frame of the wheel *part*: the rotation of the instance about
its axis in this position (``*INSTANCE`` of the deck, ``deck.py``) is undone, so that the same
node carries the same frame in every position and the history of a node over the mesh cycle can
be assembled component by component; a local ``*ORIENTATION`` system of the material steps
W3/W4 is transformed to the global frame first. The bulk data blocks of the output database
carry that local system as a quaternion (vector part first, scalar last; the rotation from
global to local), the field values as the 3 x 3 matrix of direction cosines whose rows are the
local axes: the matrix built from the quaternion is checked against the matrix of one field
value of the same element and node before it is used, and the extraction stops when they do not
agree. The averaging is over the element-nodal values (``ELEMENT_NODAL``) of the elements that
share the node, like the averaging of Abaqus/CAE with "compute scalars after averaging". Its
reader is ``gearcore.fatigue`` (the design check after Stommel et al.). The fields JSON is
written even when the stress extraction fails; the failure is raised afterwards.

The numpy helpers (``tensors_from_components``, ``rotation_about_z``,
``rotation_from_quaternion``, ``to_part_frame``) import without Abaqus, so that the tests of
``gearcore`` cover the algebra.
"""

from __future__ import annotations

import json
import math
import os
import sys
from typing import Any

import numpy as np

try:
    from abaqusConstants import (  # type: ignore[import-not-found]
        CENTROID,
        ELEMENT_NODAL,
        INTEGRATION_POINT,
    )
    from odbAccess import openOdb  # type: ignore[import-not-found]

    ABAQUS_PYTHON = True
except ImportError:  # outside the Python of Abaqus: only the numpy helpers are usable
    ABAQUS_PYTHON = False

WHEEL_INSTANCE = "WHEEL-1"
WHEEL_REFERENCE_NODE = 1
PINION_REFERENCE_NODE = 2
FORMAT_VERSION = 1
STRESS_FORMAT_VERSION = 1
STRESS_COMPONENTS = ("S11", "S22", "S33", "S12", "S13", "S23")
ORIENTATION_SAMPLE = 300
"""Elements per sampled set whose material directions are stored (the rim and one tooth head)."""
LOCAL_SYSTEM_TOLERANCE = 1.0e-5
"""Largest difference between the quaternion-built matrix and the field value's matrix."""
LOCAL_SYSTEM_CONVENTIONS = {"none": "no local system in the output database"}
"""Per step: how the rows of the local system came out of the quaternion (``R(q)`` or
``R(q)^T``), as the check against the field value decided; recorded in the stress file."""

Coordinates = dict[int, tuple[float, float, float]]


def _field(frame: Any, prefix: str) -> Any:
    """The field output whose name starts with ``prefix`` (contact fields carry the pair)."""
    names = list(frame.fieldOutputs.keys())  # an Abaqus repository, not a dict
    for name in names:
        if name == prefix or name.startswith(prefix + " "):
            return frame.fieldOutputs[name]
    return None


def _reference_points(frame: Any, instance_names: set[str]) -> dict[str, dict[str, list[float]]]:
    """RF, RM, UR, U of the two assembly-level reference nodes (labels 1 and 2)."""
    out: dict[str, dict[str, list[float]]] = {"wheel": {}, "pinion": {}}
    for variable in ("RF", "RM", "UR", "U"):
        field = _field(frame, variable)
        if field is None:
            continue
        for value in field.values:
            instance = value.instance
            if instance is not None and instance.name in instance_names:
                continue
            if value.nodeLabel == WHEEL_REFERENCE_NODE:
                out["wheel"][variable] = [float(v) for v in value.data]
            elif value.nodeLabel == PINION_REFERENCE_NODE:
                out["pinion"][variable] = [float(v) for v in value.data]
    return out


def _history_reference_points(step: Any) -> dict[str, dict[str, float]]:
    """RM3 and UR3 of both reference points from the history output (fallback)."""
    out: dict[str, dict[str, float]] = {}
    for key, region in step.historyRegions.items():
        for label, name in ((WHEEL_REFERENCE_NODE, "wheel"), (PINION_REFERENCE_NODE, "pinion")):
            if key.endswith("." + str(label)):
                values: dict[str, float] = {}
                for variable, history in region.historyOutputs.items():
                    data = history.data
                    if data:
                        values[variable] = float(data[-1][1])
                out[name] = values
    return out


def _set_members(
    instance: Any,
) -> tuple[dict[int, tuple[str, str, str]], dict[str, list[int]], dict[str, list[int]]]:
    """node label -> (tooth, side, zone) from the surface node sets of the wheel, and the
    fillet and head sets by name."""
    membership: dict[int, tuple[str, str, str]] = {}
    fillets: dict[str, list[int]] = {}
    heads: dict[str, list[int]] = {}
    for name, node_set in instance.nodeSets.items():
        parts = name.split("_")
        if name.startswith("WHEEL_ROOT_T") and name.endswith("_SURF_NODES"):
            fillets[parts[2] + "_" + parts[3]] = [n.label for n in node_set.nodes]
        elif name.startswith("WHEEL_HEAD_T") and name.endswith("_SURF_NODES"):
            heads[parts[2]] = [n.label for n in node_set.nodes]
        elif (
            name.startswith("WHEEL_T")
            and name.endswith("_NODES")
            and len(parts) == 6
            and parts[3] == "SURF"
        ):
            tooth, side, zone = parts[1], parts[2], parts[4]
            for node in node_set.nodes:
                membership[node.label] = (tooth, side, zone)
    return membership, fillets, heads


def _contact(
    frame: Any,
    coordinates: Coordinates,
    membership: dict[int, tuple[str, str, str]],
    origin: tuple[float, float],
) -> list[dict[str, Any]]:
    """Closed contact nodes: label, coordinates, radius about the wheel axis, pressure, normal
    force (if CFORCE was requested) and the tooth half they belong to."""
    pressure = _field(frame, "CPRESS")
    if pressure is None:
        return []
    force = _field(frame, "CNORMF")
    force_by_label: dict[int, float] = {}
    if force is not None:
        for value in force.values:
            force_by_label[value.nodeLabel] = math.sqrt(sum(float(v) ** 2 for v in value.data))
    closed: list[dict[str, Any]] = []
    for value in pressure.values:
        p = float(value.data)
        if p <= 0.0:
            continue
        label = value.nodeLabel
        x, y, z = coordinates[label]
        tooth, side, zone = membership.get(label, ("", "", ""))
        closed.append(
            {
                "n": label,
                "x": x,
                "y": y,
                "z": z,
                "r": math.hypot(x - origin[0], y - origin[1]),
                "p": p,
                "f": force_by_label.get(label),
                "tooth": tooth,
                "side": side,
                "zone": zone,
            }
        )
    closed.sort(key=lambda item: (-item["p"], item["n"]))
    return closed


def _centroid_values(frame: Any, name: str, element_set: Any) -> dict[int, float]:
    """A scalar element field (FV1, FV2) at the centroid of every element of a set, when the
    step requested it."""
    field = _field(frame, name)
    if field is None:
        return {}
    subset = field.getSubset(region=element_set, position=CENTROID)
    return {value.elementLabel: float(value.data) for value in subset.values}


def _orientation(frame: Any, instance: Any, heads: dict[str, list[int]]) -> list[dict[str, Any]]:
    """Local material directions of a sample of elements (the rim and the head of the middle
    tooth): the rows of ``localCoordSystem`` of the stress at the first integration point,
    the local 1- and 2-directions in global coordinates; with the element's nodes and, when
    the step wrote them, the field variables FV1 and FV2 at the centroid (the mean of the
    nodal values of the orientation file for a trilinear element). Empty when the stresses
    carry no local system (isotropic steps without orientation)."""
    stress = _field(frame, "S")
    if stress is None:
        return []
    names = ["WHEEL_RIM"]
    teeth = sorted(heads, key=lambda t: int(t[1:]))
    if teeth:
        names.append("WHEEL_HEAD_" + teeth[(len(teeth) - 1) // 2])
    out: list[dict[str, Any]] = []
    present = list(instance.elementSets.keys())  # an Abaqus repository, not a dict
    for name in names:
        if name not in present:
            continue
        element_set = instance.elementSets[name]
        connectivity = {e.label: [int(n) for n in e.connectivity] for e in element_set.elements}
        labels = sorted(connectivity)
        stride = max(1, len(labels) // ORIENTATION_SAMPLE)
        chosen = set(labels[::stride])
        first = _centroid_values(frame, "FV1", element_set)
        second = _centroid_values(frame, "FV2", element_set)
        subset = stress.getSubset(region=element_set, position=INTEGRATION_POINT)
        seen: set[int] = set()
        for value in subset.values:
            label = value.elementLabel
            if label not in chosen or label in seen:
                continue
            system = _value_local_system(value)
            if system is None:
                continue
            seen.add(label)
            sample: dict[str, Any] = {
                "set": name,
                "e": label,
                "a": [float(c) for c in system[0]],
                "b": [float(c) for c in system[1]],
                "nodes": connectivity[label],
            }
            if label in first and label in second:
                sample["fv"] = [first[label], second[label]]
            out.append(sample)
    return out


def _fillets(
    frame: Any,
    instance: Any,
    fillets: dict[str, list[int]],
    coordinates: Coordinates,
    origin: tuple[float, float],
    z_mid: float,
) -> dict[str, dict[str, Any]]:
    """Nodal averaged principal stresses on every fillet surface: the mid-width nodes in full,
    per layer (z) the largest s1 and the smallest s3 with their nodes."""
    stress = _field(frame, "S")
    out: dict[str, dict[str, Any]] = {}
    if stress is None:
        return out
    for name in fillets:
        node_set = instance.nodeSets["WHEEL_ROOT_" + name + "_SURF_NODES"]
        subset = stress.getSubset(region=node_set, position=ELEMENT_NODAL)
        sums: dict[int, list[float]] = {}
        for value in subset.values:
            entry = sums.setdefault(value.nodeLabel, [0.0, 0.0, 0.0, 0.0])
            entry[0] += float(value.maxPrincipal)
            entry[1] += float(value.minPrincipal)
            entry[2] += float(value.mises)
            entry[3] += 1.0
        averaged: dict[int, dict[str, Any]] = {}
        for label, (s1, s3, mises, count) in sums.items():
            x, y, z = coordinates[label]
            averaged[label] = {
                "n": label,
                "x": x,
                "y": y,
                "z": z,
                "r": math.hypot(x - origin[0], y - origin[1]),
                "s1": s1 / count,
                "s3": s3 / count,
                "mises": mises / count,
            }
        by_layer: dict[float, list[dict[str, Any]]] = {}
        for item in averaged.values():
            by_layer.setdefault(round(item["z"], 6), []).append(item)
        layers = []
        for z in sorted(by_layer):
            items = by_layer[z]
            top = max(items, key=lambda i: i["s1"])
            bottom = min(items, key=lambda i: i["s3"])
            layers.append(
                {
                    "z": z,
                    "s1": top["s1"],
                    "n_s1": top["n"],
                    "r_s1": top["r"],
                    "s3": bottom["s3"],
                    "n_s3": bottom["n"],
                    "r_s3": bottom["r"],
                }
            )
        mid = sorted(
            (i for i in averaged.values() if abs(i["z"] - z_mid) < 1.0e-6),
            key=lambda i: i["r"],
        )
        # every node of the fillet surface (width x arc), for the pictures over the face width
        nodes = sorted(averaged.values(), key=lambda i: (i["z"], i["r"]))
        out[name] = {"mid_width": mid, "layers": layers, "nodes": nodes}
    return out


def _heads(frame: Any, heads: dict[str, list[int]], coordinates: Coordinates) -> dict[str, Any]:
    """Largest displacement magnitude of the head surface of every tooth."""
    displacement = _field(frame, "U")
    if displacement is None:
        return {}
    magnitude: dict[int, float] = {}
    for value in displacement.values:
        if value.instance is not None and value.instance.name == WHEEL_INSTANCE:
            magnitude[value.nodeLabel] = math.sqrt(sum(float(v) ** 2 for v in value.data))
    out: dict[str, Any] = {}
    for tooth, labels in heads.items():
        best = max(labels, key=lambda label: magnitude.get(label, 0.0))
        x, y, z = coordinates[best]
        out[tooth] = {"u": magnitude.get(best, 0.0), "n": best, "x": x, "y": y, "z": z}
    return out


# --- the stress tensor of every node (ADR-118) ---------------------------------------------


def wheel_turn_deg(job: str) -> float | None:
    """Rotation of the wheel instance about its axis in this position, in degrees: the seventh
    number of the second data line of ``*INSTANCE, NAME=WHEEL-1`` in the deck ``<job>.inp``
    (``deck.py`` writes the translation on the first data line and the two axis points with the
    angle on the second). Falls back to the manifest of the folder
    (``wheel_tooth_centre_angle_deg - 90``, the same number). ``None`` when neither exists."""
    inp_path = job + ".inp"
    if os.path.exists(inp_path):
        with open(inp_path, encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
        for i, line in enumerate(lines):
            if line.upper().replace(" ", "").startswith("*INSTANCE,NAME=" + WHEEL_INSTANCE):
                data = [
                    follow for follow in lines[i + 1 : i + 3] if not follow.lstrip().startswith("*")
                ]
                if len(data) >= 2:
                    parts = [p.strip() for p in data[1].split(",") if p.strip()]
                    if len(parts) == 7:
                        return float(parts[6])
                return 0.0  # an instance without the rotation line is not rotated
    manifest_path = os.path.join(os.path.dirname(os.path.abspath(job)), "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
        wanted = os.path.basename(job) + ".inp"
        for entry in manifest.get("positions", []):
            if entry.get("file") == wanted and "wheel_tooth_centre_angle_deg" in entry:
                return float(entry["wheel_tooth_centre_angle_deg"]) - 90.0
    return None


def rotation_about_z(angle_deg: float) -> np.ndarray:
    """R_z(angle): global = axis + R_z @ part for the instance rotation of the deck."""
    c = math.cos(math.radians(angle_deg))
    s = math.sin(math.radians(angle_deg))
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def rotation_from_quaternion(quaternion: np.ndarray) -> np.ndarray:
    """(n, 4) unit quaternions (x, y, z, w), vector part first and scalar last as the bulk
    data blocks of Abaqus return them, to (n, 3, 3) rotation matrices R(q) (the standard
    matrix of the rotation the quaternion describes). Whether R or its transpose is the matrix
    of direction cosines whose rows are the local axes (``FieldValue.localCoordSystem``) is
    decided at run time by ``_local_system_matrices`` against one field value."""
    q = np.asarray(quaternion, dtype=np.float64)
    if q.ndim != 2 or q.shape[1] != 4:
        raise ValueError(f"quaternions of shape (n, 4) expected, got {q.shape}")
    x, y, z, w = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    r = np.empty((q.shape[0], 3, 3), dtype=np.float64)
    r[:, 0, 0] = 1.0 - 2.0 * (y * y + z * z)
    r[:, 0, 1] = 2.0 * (x * y - z * w)
    r[:, 0, 2] = 2.0 * (x * z + y * w)
    r[:, 1, 0] = 2.0 * (x * y + z * w)
    r[:, 1, 1] = 1.0 - 2.0 * (x * x + z * z)
    r[:, 1, 2] = 2.0 * (y * z - x * w)
    r[:, 2, 0] = 2.0 * (x * z - y * w)
    r[:, 2, 1] = 2.0 * (y * z + x * w)
    r[:, 2, 2] = 1.0 - 2.0 * (x * x + y * y)
    return r


def tensors_from_components(components: np.ndarray) -> np.ndarray:
    """(n, 6) Abaqus components S11, S22, S33, S12, S13, S23 -> (n, 3, 3) symmetric tensors."""
    s = np.asarray(components, dtype=np.float64)
    t = np.empty((s.shape[0], 3, 3), dtype=np.float64)
    t[:, 0, 0] = s[:, 0]
    t[:, 1, 1] = s[:, 1]
    t[:, 2, 2] = s[:, 2]
    t[:, 0, 1] = t[:, 1, 0] = s[:, 3]
    t[:, 0, 2] = t[:, 2, 0] = s[:, 4]
    t[:, 1, 2] = t[:, 2, 1] = s[:, 5]
    return t


def components_from_tensors(tensors: np.ndarray) -> np.ndarray:
    """(n, 3, 3) -> (n, 6) in the Abaqus order."""
    t = np.asarray(tensors, dtype=np.float64)
    return np.stack(
        [t[:, 0, 0], t[:, 1, 1], t[:, 2, 2], t[:, 0, 1], t[:, 0, 2], t[:, 1, 2]], axis=1
    )


def local_to_global(components_local: np.ndarray, rows_local_axes: np.ndarray) -> np.ndarray:
    """Components written in a local system -> global: with Q the matrix whose rows are the
    local axes in global coordinates (v_local = Q v_global), S_global = Q^T S_local Q."""
    q = np.asarray(rows_local_axes, dtype=np.float64)
    return components_from_tensors(
        np.einsum("nji,njk,nkl->nil", q, tensors_from_components(components_local), q)
    )


def to_part_frame(
    components_global: np.ndarray,
    coordinates_global: np.ndarray,
    axis_xy: tuple[float, float],
    turn_deg: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Global components and coordinates -> the frame of the part: with global = axis + R @ part,
    S_part = R^T S_global R and x_part = R^T (x_global − axis)."""
    r = rotation_about_z(turn_deg)
    s = components_from_tensors(
        np.einsum("ji,njk,kl->nil", r, tensors_from_components(components_global), r)
    )
    x = (
        np.asarray(coordinates_global, dtype=np.float64) - np.array([axis_xy[0], axis_xy[1], 0.0])
    ) @ r
    return s, x


def _block_data(block: Any) -> np.ndarray:
    """The components of a bulk data block in single or double precision."""
    try:
        return np.asarray(block.data, dtype=np.float64)
    except Exception:  # noqa: BLE001 - Abaqus raises its own exception type for double precision
        return np.asarray(block.dataDouble, dtype=np.float64)


def _value_local_system(value: Any) -> Any:
    """The 3 x 3 direction cosines of a field value, in single or double precision; ``None``
    when the value carries no local system."""
    try:
        system = value.localCoordSystem
    except Exception:  # noqa: BLE001
        system = None
    if system is None:
        try:
            system = value.localCoordSystemDouble
        except Exception:  # noqa: BLE001
            system = None
    return system


def _reference_value(
    stress: Any, instance: Any, subset: Any, element_label: int, node_label: int
) -> Any:
    """The field value of one element-nodal location (element, node): first through a subset
    on that element (cheap), else by walking the values of the whole subset until the location
    is met."""
    try:
        element = instance.getElementFromLabel(element_label)
        for value in stress.getSubset(region=element, position=ELEMENT_NODAL).values:
            if value.elementLabel == element_label and value.nodeLabel == node_label:
                return value
    except Exception:  # noqa: BLE001 - a region type the installation does not accept
        pass
    for value in subset.values:
        if value.elementLabel == element_label and value.nodeLabel == node_label:
            return value
    return None


def _local_system_matrices(
    block: Any, stress: Any, instance: Any, subset: Any
) -> np.ndarray | None:
    """(n, 3, 3) matrices whose rows are the local axes, for every value of the block, built
    from its quaternions and checked against the matrix of one field value of the same element
    and node. ``None`` when the block carries no local system. Raises when the built matrix
    matches neither as is nor transposed."""
    quaternion = block.localCoordSystem
    if quaternion is None:
        return None
    q = np.asarray(quaternion, dtype=np.float64)
    if q.ndim == 1:
        q = q.reshape(1, -1)
    if q.shape[1] != 4:
        raise RuntimeError(
            f"the local coordinate system of a bulk data block has {q.shape[1]} numbers per value, "
            "four (a quaternion) expected"
        )
    built = rotation_from_quaternion(q)
    labels_e = np.asarray(block.elementLabels)
    labels_n = np.asarray(block.nodeLabels)
    reference = _reference_value(stress, instance, subset, int(labels_e[0]), int(labels_n[0]))
    system = _value_local_system(reference) if reference is not None else None
    if system is None:
        raise RuntimeError(
            f"no field value found to check the local coordinate system against (element "
            f"{int(labels_e[0])}, node {int(labels_n[0])})"
        )
    matrix = np.asarray(system, dtype=np.float64)
    if np.max(np.abs(built[0] - matrix)) <= LOCAL_SYSTEM_TOLERANCE:
        LOCAL_SYSTEM_CONVENTIONS["last"] = "rows of the local system = R(q)"
        return built
    transposed = np.transpose(built, (0, 2, 1))
    if np.max(np.abs(transposed[0] - matrix)) <= LOCAL_SYSTEM_TOLERANCE:
        LOCAL_SYSTEM_CONVENTIONS["last"] = "rows of the local system = R(q)^T"
        return transposed
    raise RuntimeError(
        "the matrix built from the quaternion of the bulk data block matches the field value's "
        f"direction cosines neither as is nor transposed (largest difference "
        f"{np.max(np.abs(built[0] - matrix)):.3e} / {np.max(np.abs(transposed[0] - matrix)):.3e})"
    )


def _nodal_stress_global(
    frame: Any, instance: Any, index_of_label: np.ndarray, n_nodes: int
) -> tuple[np.ndarray, np.ndarray]:
    """Nodal averaged stress tensor (n_nodes, 6) in the global frame and the count of
    element-nodal values per node, from the bulk data blocks of the element-nodal subset of
    the wheel instance; values in a local system are rotated to the global frame first."""
    stress = _field(frame, "S")
    sums = np.zeros((n_nodes, 6), dtype=np.float64)
    counts = np.zeros(n_nodes, dtype=np.int32)
    if stress is None:
        return sums, counts
    subset = stress.getSubset(region=instance, position=ELEMENT_NODAL)
    for block in subset.bulkDataBlocks:
        data = _block_data(block)
        if data.ndim != 2 or data.shape[1] != 6:
            raise RuntimeError(f"unexpected stress block shape {data.shape}")
        systems = _local_system_matrices(block, stress, instance, subset)
        if systems is not None:
            data = local_to_global(data, systems)
        idx = index_of_label[np.asarray(block.nodeLabels, dtype=np.int64)]
        if np.any(idx < 0):
            raise RuntimeError("stress value at a node that is not in the wheel instance")
        np.add.at(sums, idx, data)
        np.add.at(counts, idx, 1)
    return sums, counts


def extract(
    odb_path: str, out_path: str, stress_path: str | None = None, turn_deg: float | None = None
) -> dict[str, Any]:
    """Read the output database, write the fields file and (when ``stress_path`` is given)
    the stress file; returns the fields document. A failure of the stress extraction is
    raised only after the fields file was written."""
    if not ABAQUS_PYTHON:
        raise RuntimeError("extract() needs the Python of Abaqus (abaqusConstants, odbAccess)")
    odb = openOdb(odb_path, readOnly=True)
    stress_error: Exception | None = None
    try:
        assembly = odb.rootAssembly
        instance_names = set(assembly.instances.keys())
        instance = assembly.instances[WHEEL_INSTANCE]
        coordinates: Coordinates = {
            n.label: (float(n.coordinates[0]), float(n.coordinates[1]), float(n.coordinates[2]))
            for n in instance.nodes
        }
        origin = (0.0, 0.0)
        for node in assembly.nodes:
            if node.label == WHEEL_REFERENCE_NODE:
                origin = (float(node.coordinates[0]), float(node.coordinates[1]))
        zs = sorted({round(c[2], 6) for c in coordinates.values()})
        z_mid = zs[len(zs) // 2]
        membership, fillets, heads = _set_members(instance)

        # the node table of the stress file (sorted labels; part frame)
        labels = np.array(sorted(coordinates), dtype=np.int64)
        index_of_label = np.full(int(labels.max()) + 1, -1, dtype=np.int64)
        index_of_label[labels] = np.arange(labels.size)
        xyz_global = np.array([coordinates[int(label)] for label in labels], dtype=np.float64)
        turn = 0.0 if turn_deg is None else float(turn_deg)
        stress_arrays: dict[str, Any] = {}
        step_names: list[str] = []
        step_complete: list[bool] = []
        step_times: list[float] = []

        steps = []
        for step_name, step in odb.steps.items():
            if len(step.frames) == 0:
                continue  # a step that broke off before its first increment has no frame
            frame = step.frames[-1]
            complete = bool(abs(float(frame.frameValue) - 1.0) < 1.0e-9)
            steps.append(
                {
                    "name": step_name,
                    "frame": int(frame.frameId),
                    "time": float(frame.frameValue),
                    "complete": complete,
                    "reference_points": _reference_points(frame, instance_names),
                    "history": _history_reference_points(step),
                    "contact": _contact(frame, coordinates, membership, origin),
                    "fillets": _fillets(frame, instance, fillets, coordinates, origin, z_mid),
                    "heads": _heads(frame, heads, coordinates),
                    "orientation": _orientation(frame, instance, heads),
                }
            )
            if stress_path is not None and stress_error is None:
                try:
                    sums, counts = _nodal_stress_global(
                        frame, instance, index_of_label, labels.size
                    )
                    averaged = np.zeros_like(sums)
                    has = counts > 0
                    averaged[has] = sums[has] / counts[has, None]
                    part, xyz_part = to_part_frame(averaged, xyz_global, origin, turn)
                    stress_arrays["S__" + step_name] = part.astype(np.float32)
                    if "node_element_count" not in stress_arrays:
                        stress_arrays["node_element_count"] = counts.astype(np.int16)
                        stress_arrays["coordinates"] = xyz_part.astype(np.float32)
                    step_names.append(step_name)
                    step_complete.append(complete)
                    step_times.append(float(frame.frameValue))
                except Exception as error:  # noqa: BLE001 - reported after the fields file is safe
                    stress_error = error
        document: dict[str, Any] = {
            "format": FORMAT_VERSION,
            "odb": odb_path,
            "wheel_axis": list(origin),
            "z_levels": zs,
            "z_mid": z_mid,
            "steps": steps,
        }
        if stress_path is not None and stress_error is None:
            for name, node_set in instance.nodeSets.items():
                stress_arrays["set__" + name] = np.array(
                    [n.label for n in node_set.nodes], dtype=np.int32
                )
            # written under a .part name and renamed when complete, so that a run cut short
            # during the extraction never leaves a file that passes as complete
            stress_part = stress_path[:-4] + ".part.npz"
            np.savez_compressed(
                stress_part,
                format=np.int32(STRESS_FORMAT_VERSION),
                odb=np.str_(odb_path),
                components=np.array(STRESS_COMPONENTS),
                frame=np.str_("wheel part frame: global = axis + R_z(wheel_turn_deg) @ part"),
                wheel_turn_deg=np.float64(turn),
                wheel_turn_known=np.bool_(turn_deg is not None),
                local_system_convention=np.str_(
                    LOCAL_SYSTEM_CONVENTIONS.get("last", LOCAL_SYSTEM_CONVENTIONS["none"])
                ),
                wheel_axis=np.array(origin, dtype=np.float64),
                node_labels=labels.astype(np.int32),
                step_names=np.array(step_names),
                step_complete=np.array(step_complete, dtype=bool),
                step_time=np.array(step_times, dtype=np.float64),
                **stress_arrays,
            )
            os.replace(stress_part, stress_path)
    finally:
        odb.close()
    with open(out_path + ".part", "w") as handle:
        json.dump(document, handle, separators=(",", ":"))
    os.replace(out_path + ".part", out_path)
    if stress_error is not None:
        raise RuntimeError(
            f"stress extraction failed after the fields file was written: {stress_error}"
        )
    return document


if __name__ == "__main__":
    job = sys.argv[1]
    if job.lower().endswith(".odb"):
        job = job[:-4]
    turn = wheel_turn_deg(job)
    if turn is None:
        print(
            f"warning: neither {job}.inp nor manifest.json gives the rotation of the wheel "
            "instance; the stress file keeps the global frame (wheel_turn_known = False)"
        )
    result = extract(job + ".odb", job + "_fields.json", job + "_stress.npz", turn)
    for step_document in result["steps"]:
        closed_nodes = step_document["contact"]
        largest = closed_nodes[0] if closed_nodes else None
        location = ""
        if largest:
            location = (
                f", largest CPRESS {largest['p']:.2f} MPa at node {largest['n']} "
                f"(r {largest['r']:.3f}, z {largest['z']:.3f})"
            )
        print(f"{step_document['name']}: {len(closed_nodes)} closed contact nodes{location}")
    print(
        f"stress tensors of every wheel node written to {job}_stress.npz (wheel turn {turn} deg; "
        + LOCAL_SYSTEM_CONVENTIONS.get("last", LOCAL_SYSTEM_CONVENTIONS["none"])
        + ")"
    )
