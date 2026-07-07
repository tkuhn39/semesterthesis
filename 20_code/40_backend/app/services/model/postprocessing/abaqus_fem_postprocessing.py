# coding: utf8
"""Own Abaqus-Python postprocessing for the plastic-gear rolling deck (Zahnfuss-Workbench).

Decoupled from the frozen FVA script (which reads REFERENCE_POINT_ node sets and
``Geometrieberechnung_E1`` text files that our deck does not produce): this one works
against OUR set naming and dumps a NEUTRAL JSON that the workbench uploads
(``POST /api/fem/results``) and renders as the 3-D stress/strain viewer.

Runs in the Abaqus Python interpreter (2.7 or the 2024+ 3.10 kernel):

    abaqus python abaqus_fem_postprocessing.py            # auto-detect mode
    abaqus python abaqus_fem_postprocessing.py <odb>      # force one single-file odb

Modes (auto-detected):
  * position series (default deck mode): a ``manifest.json`` next to this script lists
    ``pos_NNN`` positions; the matching ``pos_NNN.odb`` each contribute their single
    measurement frame (step end, t = 1.0). The roll angle per position comes from the
    manifest.
  * single quasi-static deck: one odb (the CLI arg or the only ``*.odb`` in the folder);
    the measurement frames are the STEP-1 frames that carry the ``S`` field (the
    ``*TIME POINTS=MEASURE`` full-torque holds — the U-only animation frames are skipped).

For every measurement frame and every flank set ``G{g}T{ttt}F{f}`` (per gear g, tooth t,
flank f) it collects, per SURFACE node: the radius from the gear's rotation axis, the
axial z, the von-Mises / max- / min-principal stress and strain (E or NE), the contact
pressure CPRESS, and the displacement magnitude. Element fields are averaged from their
ELEMENT_NODAL values per node (like the reference). The r -> path-of-contact unwrapping
and the A..E markers are done on the BACKEND from the GearStage (single source of truth),
so this script stays geometry-light and never re-derives gear data.

Output: ``fem_results.json`` (schema ``zahnfuss.fem_results/1``).
"""
from __future__ import print_function

import json
import math
import os
import sys

from odbAccess import openOdb, isUpgradeRequiredForOdb, upgradeOdb  # noqa: F401
from abaqusConstants import ELEMENT_NODAL, NODAL  # noqa: F401


def _open_odb(path):
    """Open an odb read-only, upgrading it first if the kernel is newer than the file."""
    if isUpgradeRequiredForOdb(upgradeRequiredOdbPath=path):
        upgraded = path[:-4] + "_upgraded.odb"
        upgradeOdb(existingOdbPath=path, upgradedOdbPath=upgraded)
        path = upgraded
    return openOdb(path=path, readOnly=True)


def _gear_axis(odb, gear):
    """(x, y) of gear g's rotation axis from the Rot_Node_Rad{g} assembly node set."""
    node_set = odb.rootAssembly.nodeSets["ROT_NODE_RAD%d" % gear]
    coords = node_set.nodes[0][0].coordinates  # assembly-level set, one node
    return (float(coords[0]), float(coords[1]))


def _instance(odb, gear):
    return odb.rootAssembly.instances["RAD_VZ_%d" % gear]


def _gears_present(odb):
    names = odb.rootAssembly.instances.keys()
    return [g for g in (1, 2) if ("RAD_VZ_%d" % g) in names]


def _flank_sets(instance, gear):
    """{(tooth, flank): node set name} for every G{g}T{ttt}F{f}_NODESET on the instance."""
    prefix = "G%dT" % gear
    out = {}
    for name in instance.nodeSets.keys():
        if name.startswith(prefix) and name.endswith("_NODESET") and len(name) >= 16:
            core = name.split("_")[0]  # e.g. G1T002F2
            try:
                tooth = int(core[len(prefix) : len(prefix) + 3])
                flank = int(core[-1])
            except ValueError:
                continue
            out[(tooth, flank)] = name
    return out


def _coordinates_by_label(instance):
    """{label: (x, y, z)} built ONCE per odb/instance (undeformed mesh coordinates)."""
    coords = {}
    for node in instance.nodes:
        c = node.coordinates
        coords[node.label] = (float(c[0]), float(c[1]), float(c[2]))
    return coords


def _averaged_element_nodal(field, element_set, keys):
    """Average an element field's ELEMENT_NODAL values per node -> {nodeId: {key: value}}.

    ``keys`` maps an output name to the odb value attribute, e.g.
    ``{'mises': 'mises', 'maxp': 'maxPrincipal', 'minp': 'minPrincipal'}``.
    """
    subset = field.getSubset(region=element_set, position=ELEMENT_NODAL)
    acc = {}
    counts = {}
    for value in subset.values:
        nid = value.nodeLabel
        if nid not in acc:
            acc[nid] = dict((k, 0.0) for k in keys)
            counts[nid] = 0
        counts[nid] += 1
        for out_name in keys:
            acc[nid][out_name] += float(getattr(value, keys[out_name]))
    for nid in acc:
        n = float(counts[nid])
        for k in acc[nid]:
            acc[nid][k] /= n
    return acc


def _nodal_scalar(field, node_set):
    """{nodeId: value} for a nodal scalar field (e.g. CPRESS) over a node set."""
    out = {}
    for value in field.getSubset(region=node_set, position=NODAL).values:
        out[value.nodeLabel] = float(value.data)
    return out


def _nodal_vector_magnitude(field, node_set):
    """{nodeId: |vector|} for a nodal vector field (U) over a node set."""
    out = {}
    for value in field.getSubset(region=node_set, position=NODAL).values:
        d = value.data
        out[value.nodeLabel] = float(math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]))
    return out


def _extract_flank(instance, frame, node_set_name, geo):
    """The per-node field payload of one flank set at one frame (list of node dicts).

    ``geo`` maps nodeId -> (radius, z) for exactly this set's nodes.
    """
    node_set = instance.nodeSets[node_set_name]
    element_set_name = node_set_name.replace("_NODESET", "_ELEMENTSET")
    outputs = frame.fieldOutputs
    output_keys = outputs.keys()

    stress = {}
    strain = {}
    if element_set_name in instance.elementSets.keys() and "S" in output_keys:
        element_set = instance.elementSets[element_set_name]
        stress = _averaged_element_nodal(
            outputs["S"],
            element_set,
            {"mises": "mises", "maxp": "maxPrincipal", "minp": "minPrincipal"},
        )
        strain_key = "E" if "E" in output_keys else ("NE" if "NE" in output_keys else None)
        if strain_key is not None:
            strain = _averaged_element_nodal(
                outputs[strain_key], element_set, {"mises": "mises", "maxp": "maxPrincipal"}
            )
    cpress = _nodal_scalar(outputs["CPRESS"], node_set) if "CPRESS" in output_keys else {}
    disp = _nodal_vector_magnitude(outputs["U"], node_set) if "U" in output_keys else {}

    nodes = []
    for nid in geo:
        radius, z = geo[nid]
        s = stress.get(nid, {})
        e = strain.get(nid, {})
        nodes.append(
            {
                "id": int(nid),
                "r": round(radius, 6),
                "z": round(z, 6),
                "s_mises": round(s.get("mises", 0.0), 4),
                "s_maxp": round(s.get("maxp", 0.0), 4),
                "s_minp": round(s.get("minp", 0.0), 4),
                "e_mises": round(e.get("mises", 0.0), 8),
                "e_maxp": round(e.get("maxp", 0.0), 8),
                "cpress": round(cpress.get(nid, 0.0), 4),
                "u": round(disp.get(nid, 0.0), 6),
            }
        )
    nodes.sort(key=lambda nd: (nd["z"], nd["r"]))
    return nodes


def _build_geometry(odb):
    """Per gear: instance, axis and per-flank-set nodeId -> (radius, z) maps — ONCE per odb."""
    geometry = {}
    for gear in _gears_present(odb):
        instance = _instance(odb, gear)
        ax, ay = _gear_axis(odb, gear)
        coords = _coordinates_by_label(instance)
        sets = {}
        for (tooth, flank), set_name in _flank_sets(instance, gear).items():
            geo = {}
            for node in instance.nodeSets[set_name].nodes:
                x, y, z = coords[node.label]
                geo[node.label] = (math.hypot(x - ax, y - ay), z)
            sets[(tooth, flank, set_name)] = geo
        geometry[gear] = (instance, (ax, ay), sets)
    return geometry


def _frame_flanks(geometry, frame):
    """{'G{g}T{ttt}F{f}': [node dicts]} for all flank sets at one frame."""
    flanks = {}
    for gear in geometry:
        instance, _axis, sets = geometry[gear]
        for (tooth, flank, set_name) in sets:
            geo = sets[(tooth, flank, set_name)]
            if not geo:
                continue
            tag = "G%dT%03dF%d" % (gear, tooth, flank)
            flanks[tag] = _extract_flank(instance, frame, set_name, geo)
    return flanks


def _gear_meta(geometry):
    meta = {}
    for gear in geometry:
        _instance_, axis, _sets = geometry[gear]
        meta[str(gear)] = {"axis": [round(axis[0], 6), round(axis[1], 6)]}
    return meta


def _measurement_frames(step):
    """The frames that carry the full field payload (the S field).

    The deck writes two field requests: a U-only animation (every increment) and the
    per-flank measurement payload only on the *TIME POINTS=MEASURE holds — those are the
    only frames with 'S', so a frame is a measurement frame iff 'S' is present.
    """
    out = []
    for i, frame in enumerate(step.frames):
        if "S" in frame.fieldOutputs.keys():
            out.append((i, frame))
    return out


def run_series(manifest_path):
    with open(manifest_path, "r") as fh:
        manifest = json.load(fh)
    base = os.path.dirname(os.path.abspath(manifest_path))
    frames_out = []
    gear_meta = None
    for pos in manifest["positions"]:
        odb_path = os.path.join(base, pos["file"].replace(".inp", ".odb"))
        if not os.path.exists(odb_path):
            print("skip (no odb): %s" % odb_path)
            continue
        odb = _open_odb(odb_path)
        try:
            geometry = _build_geometry(odb)
            if gear_meta is None:
                gear_meta = _gear_meta(geometry)
            step = odb.steps["STEP-1"]
            meas = _measurement_frames(step)
            frame = meas[-1][1] if meas else step.frames[-1]
            frames_out.append(
                {
                    "index": pos["index"],
                    "phi_driven_rad": pos["phi_driven_rad"],
                    "phi_other_rad": pos["phi_other_rad"],
                    "flanks": _frame_flanks(geometry, frame),
                }
            )
            print("position %d: %d flank sets" % (pos["index"], len(frames_out[-1]["flanks"])))
        finally:
            odb.close()
    return {
        "schema": "zahnfuss.fem_results/1",
        "mode": "position_series",
        "driven_gear": manifest.get("driven_gear"),
        "torque_gear": manifest.get("torque_gear"),
        "torque_nmm": manifest.get("torque_nmm"),
        "roll_pitches": manifest.get("roll_pitches"),
        "roll_angle_rad": manifest.get("roll_angle_rad"),
        "gears": gear_meta or {},
        "frames": frames_out,
    }


def run_single(odb_path):
    odb = _open_odb(odb_path)
    try:
        geometry = _build_geometry(odb)
        step = odb.steps["STEP-1"]
        frames_out = []
        for ordinal, (frame_index, frame) in enumerate(_measurement_frames(step)):
            frames_out.append(
                {
                    "index": ordinal + 1,
                    "frame_index": frame_index,
                    "frame_value": float(frame.frameValue),
                    "flanks": _frame_flanks(geometry, frame),
                }
            )
            print("measurement frame %d (odb frame %d)" % (ordinal + 1, frame_index))
        return {
            "schema": "zahnfuss.fem_results/1",
            "mode": "single_deck",
            "gears": _gear_meta(geometry),
            "frames": frames_out,
        }
    finally:
        odb.close()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(here, "manifest.json")
    if len(args) >= 1 and args[0].endswith(".odb"):
        result = run_single(args[0])
    elif os.path.exists(manifest):
        result = run_series(manifest)
    else:
        candidates = [f for f in os.listdir(here) if f.endswith(".odb")]
        if not candidates:
            print("ERROR: no manifest.json and no *.odb found next to the script")
            sys.exit(1)
        result = run_single(os.path.join(here, sorted(candidates)[0]))

    out_path = os.path.join(here, "fem_results.json")
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=1)
    total_nodes = sum(len(nodes) for fr in result["frames"] for nodes in fr["flanks"].values())
    print(
        "wrote %s: %d frames, %d flank-node records"
        % (out_path, len(result["frames"]), total_nodes)
    )


if __name__ == "__main__":
    main()
