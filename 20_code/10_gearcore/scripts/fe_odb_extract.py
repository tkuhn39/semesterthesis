"""Extraction of one position result from its Abaqus output database (``.odb``).

Runs under the Python of Abaqus (``abaqus python extract_odb.py <job>``; Abaqus 2025 ships
Python 3.10), standalone, without ``gearcore``. ``run_all.ps1`` calls it after every job; the
Learning Edition's Python opens the output databases of the full licence as well
(``build_fe_decks.py extract``). It writes ``<job>_fields.json`` next to the ``.odb``: per step
(last frame) the reactions, moments and rotations of both reference points, the closed contact
nodes of the wheel flank with their coordinates, pressure and (when CFORCE was requested)
normal force, the nodal averaged stresses of every root fillet surface (mid-width nodes in full,
per layer the largest tensile and the most compressive principal stress) and the largest
displacement of every tooth head. The reader of this file is ``gearcore.fe.evaluation``.
"""

import json
import math
import sys
from typing import Any

from abaqusConstants import ELEMENT_NODAL  # type: ignore[import-not-found]
from odbAccess import openOdb  # type: ignore[import-not-found]

WHEEL_INSTANCE = "WHEEL-1"
WHEEL_REFERENCE_NODE = 1
PINION_REFERENCE_NODE = 2
FORMAT_VERSION = 1

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


def extract(odb_path: str, out_path: str) -> dict[str, Any]:
    """Read the output database and write the fields file; returns the document."""
    odb = openOdb(odb_path, readOnly=True)
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
        steps = []
        for step_name, step in odb.steps.items():
            if len(step.frames) == 0:
                continue  # a step that broke off before its first increment has no frame
            frame = step.frames[-1]
            steps.append(
                {
                    "name": step_name,
                    "frame": int(frame.frameId),
                    "time": float(frame.frameValue),
                    "complete": bool(abs(float(frame.frameValue) - 1.0) < 1.0e-9),
                    "reference_points": _reference_points(frame, instance_names),
                    "history": _history_reference_points(step),
                    "contact": _contact(frame, coordinates, membership, origin),
                    "fillets": _fillets(frame, instance, fillets, coordinates, origin, z_mid),
                    "heads": _heads(frame, heads, coordinates),
                }
            )
        document: dict[str, Any] = {
            "format": FORMAT_VERSION,
            "odb": odb_path,
            "wheel_axis": list(origin),
            "z_levels": zs,
            "z_mid": z_mid,
            "steps": steps,
        }
    finally:
        odb.close()
    with open(out_path, "w") as handle:
        json.dump(document, handle, separators=(",", ":"))
    return document


if __name__ == "__main__":
    job = sys.argv[1]
    if job.lower().endswith(".odb"):
        job = job[:-4]
    result = extract(job + ".odb", job + "_fields.json")
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
