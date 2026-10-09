"""Evaluation of extracted position results over the path of contact
(``gearcore.fe.evaluation``)."""

import json
import math
from pathlib import Path

import pytest

from gearcore.errors import InputRangeError, ParseError
from gearcore.fe import evaluation as ev


def _node(n: int, r: float, z: float, p: float, f: float | None, tooth: str, side: str) -> dict:
    return {
        "n": n,
        "x": r,
        "y": 0.0,
        "z": z,
        "r": r,
        "p": p,
        "f": f,
        "tooth": tooth,
        "side": side,
        "zone": "FLANK",
    }


def _fillet(z_levels: list[float], s1_peak: float) -> dict:
    layers = [
        {
            "z": z,
            "s1": s1_peak - abs(z),
            "n_s1": 10 + k,
            "r_s1": 24.8,
            "s3": -2.0 * s1_peak + abs(z),
            "n_s3": 20 + k,
            "r_s3": 24.9,
        }
        for k, z in enumerate(z_levels)
    ]
    mid = [
        {
            "n": 30 + k,
            "x": 24.8 + 0.01 * k,
            "y": 0.0,
            "z": 0.0,
            "r": 24.8 + 0.01 * k,
            "s1": s1_peak - k,
            "s3": -s1_peak,
            "mises": s1_peak,
        }
        for k in range(3)
    ]
    nodes = [{**m, "z": z} for z in z_levels for m in mid]
    return {"mid_width": mid, "layers": layers, "nodes": nodes}


def _document(rotation: float, p_t3: float, force_t3: float | None, s1_t2_t3: float) -> dict:
    z_levels = [-7.5, 0.0, 7.5]
    step = {
        "name": "LOAD_8NM",
        "frame": 6,
        "time": 1.0,
        "reference_points": {
            "wheel": {"RF": [1.0, 2.0, 0.0], "RM": [0.0, 0.0, -7910.0], "UR": [0.0, 0.0, 0.0]},
            "pinion": {
                "RF": [-1.0, -2.0, 0.0],
                "RM": [0.0, 0.0, 7846.0],
                "UR": [0.0, 0.0, -rotation],
            },
        },
        "history": {"wheel": {"RM3": -7910.0}, "pinion": {"UR3": -rotation}},
        "contact": [
            _node(1, 26.1, 0.0, p_t3, force_t3, "T3", "RIGHT"),
            _node(2, 26.1, 0.75, 0.9 * p_t3, force_t3, "T3", "RIGHT"),
            _node(
                3,
                25.9,
                0.0,
                0.5 * p_t3,
                0.5 * force_t3 if force_t3 is not None else None,
                "T4",
                "RIGHT",
            ),
        ],
        "fillets": {
            "T2_T3": _fillet(z_levels, s1_t2_t3),
            "T3_T4": _fillet(z_levels, 0.3 * s1_t2_t3),
        },
        "heads": {
            "T3": {"u": 0.2, "n": 50, "x": 27.0, "y": 0.0, "z": 0.0},
            "T4": {"u": 0.05, "n": 51, "x": 27.0, "y": 1.0, "z": 0.0},
        },
    }
    seat = {**step, "name": "SEAT", "contact": step["contact"][:1], "fillets": {}, "heads": {}}
    return {
        "format": 1,
        "odb": "x.odb",
        "wheel_axis": [52.0, 0.0],
        "z_levels": z_levels,
        "z_mid": 0.0,
        "steps": [seat, step],
    }


def test_read_fields_and_step_summary(tmp_path: Path) -> None:
    path = tmp_path / "pos_001_fields.json"
    path.write_text(json.dumps(_document(2.3e-3, 60.0, 4.0, 70.0)), encoding="utf-8")
    fields = ev.read_fields(path)
    assert fields.job == "pos_001" and fields.wheel_axis == (52.0, 0.0) and len(fields.steps) == 2
    summary = ev.step_summary(fields.steps[1])
    assert summary.name == "LOAD_8NM"
    assert summary.pinion_rotation_rad == pytest.approx(-2.3e-3)
    assert summary.wheel_moment_nmm == pytest.approx(-7910.0)
    assert [(t.tooth, t.side, t.nodes) for t in summary.teeth] == [
        ("T3", "RIGHT", 2),
        ("T4", "RIGHT", 1),
    ]
    assert summary.teeth[0].force == pytest.approx(8.0) and summary.teeth[1].force == pytest.approx(
        2.0
    )
    assert summary.p_max == pytest.approx(60.0) and summary.p_max_at is not None
    assert summary.p_max_at.n == 1 and summary.p_max_at.z == 0.0
    fillet = fields.steps[1].fillets["T2_T3"]
    assert len(fillet.nodes) == 9 and len(fillet.mid_width) == 3  # width x arc, and the mid row
    assert summary.s1_max == pytest.approx(70.0) and summary.s1_max_fillet is not None
    assert summary.s1_max_fillet.name == "T2_T3" and summary.s1_max_fillet.s1_layer.z == 0.0
    assert summary.s3_min == pytest.approx(-140.0)
    assert summary.u_head_max == pytest.approx(0.2) and summary.u_head_tooth == "T3"
    # without CFORCE the force of a tooth half is unknown, not zero
    path.write_text(json.dumps(_document(2.3e-3, 60.0, None, 70.0)), encoding="utf-8")
    summary = ev.step_summary(ev.read_fields(path).steps[1])
    assert summary.teeth[0].force is None
    lines = ev.format_summary(summary)
    assert any("T3 RIGHT: 2 closed nodes" in line for line in lines)
    assert any("fillet T2_T3" in line for line in lines)
    assert summary.complete and summary.time == 1.0 and not lines[0].startswith("    step NOT")


def test_broken_off_step_is_marked_and_left_out_of_the_curves(tmp_path: Path) -> None:
    # the extraction stores the last converged frame of a broken-off step with its step time
    # (and, since 2026-10-07, the flag ``complete``); older files carry the time only
    document = _document(2.3e-3, 60.0, 4.0, 70.0)
    document["steps"][1]["time"] = 0.206
    document["steps"][1]["complete"] = False
    path = tmp_path / "pos_001_fields.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    step = ev.read_fields(path).steps[1]
    assert not step.complete and step.time == pytest.approx(0.206)
    summary = ev.step_summary(step)
    assert not summary.complete and summary.time == pytest.approx(0.206)
    assert ev.format_summary(summary)[0].startswith("    step NOT complete") and (
        "0.206" in ev.format_summary(summary)[0]
    )
    del document["steps"][1]["complete"]
    path.write_text(json.dumps(document), encoding="utf-8")
    assert not ev.read_fields(path).steps[1].complete
    document["steps"][1]["time"] = 1.0
    path.write_text(json.dumps(document), encoding="utf-8")
    assert ev.read_fields(path).steps[1].complete


def test_read_fields_rejects_other_files(tmp_path: Path) -> None:
    bad = tmp_path / "x_fields.json"
    bad.write_text('{"format": 2}', encoding="utf-8")
    with pytest.raises(ParseError):
        ev.read_fields(bad)
    bad.write_text("not json", encoding="utf-8")
    with pytest.raises(ParseError):
        ev.read_fields(bad)


def _folder(tmp_path: Path, steps_per_pitch: int, p_bt: float, margin: float) -> dict:
    """A grid folder whose pressure peaks at 1,0 mm from A with a parabola, and whose
    rotation peaks at 2,0 mm."""
    count = round((3.4 + 2.0 * margin * p_bt) / (p_bt / steps_per_pitch))
    positions = []
    for k in range(count + 1):
        from_a = -margin * p_bt + k * p_bt / steps_per_pitch
        positions.append(
            {
                "index": k + 1,
                "file": f"pos_{k + 1:03d}.inp",
                "point": "",
                "rho_1_mm": 7.79 + from_a,
                "from_A_mm": from_a,
            }
        )
    positions.append(
        {
            "index": count + 2,
            "file": "pos_c.inp",
            "point": "C",
            "rho_1_mm": 9.42,
            "from_A_mm": 1.637,
        }
    )
    for entry in positions:
        from_a = entry["from_A_mm"]
        p = max(0.0, 60.0 - 40.0 * (from_a - 1.0) ** 2)
        rotation = max(0.0, 3.0e-3 - 1.0e-3 * (from_a - 2.0) ** 2)
        job = Path(entry["file"]).stem
        (tmp_path / f"{job}_fields.json").write_text(
            json.dumps(_document(rotation, p, 4.0, 70.0 - 10.0 * abs(from_a - 1.5))),
            encoding="utf-8",
        )
    return {"positions": positions}


def test_path_points_grid_subsets_and_resolution(tmp_path: Path) -> None:
    p_bt, steps, margin = 2.952, 12, 0.5
    manifest = _folder(tmp_path, steps, p_bt, margin)
    points = ev.path_points(manifest, tmp_path)
    assert [p.from_a_mm for p in points] == sorted(p.from_a_mm for p in points)
    assert sum(1 for p in points if p.label == "C") == 1
    full = ev.grid_subset(points, steps, p_bt, margin, 1)
    halved = ev.grid_subset(points, steps, p_bt, margin, 2)
    assert len(full) == len(points)
    # the named point stays, every second grid point goes
    assert sum(1 for p in halved if p.label == "C") == 1
    assert len(halved) == 1 + (len(points) - 1 + 1) // 2
    pressure = ev.curve(points, "LOAD_8NM", "p_max")
    peak = ev.extremum(pressure)
    assert peak is not None and peak[0] == pytest.approx(1.0, abs=1.0e-6)
    # the value is the measured maximum of the grid, not the vertex of the parabola
    assert peak[1] == max(v for _, v in pressure) and peak[1] <= 60.0
    rotation = ev.curve(points, "LOAD_8NM", "pinion_rotation_rad")
    assert all(v >= 0.0 for _, v in rotation)
    force = ev.curve(points, "LOAD_8NM", "force:T3_RIGHT")
    assert force and force[0][1] == pytest.approx(8.0)
    assert ev.curve(points, "LOAD_8NM", "force:T9_LEFT")[0][1] == 0.0
    # the principal stresses of one fillet: s1 of T2_T3 peaks at 1,5 mm with 70 MPa, s3 is
    # taken by magnitude, a fillet without data counts as zero
    s1 = ev.curve(points, "LOAD_8NM", "s1:T2_T3")
    s1_peak = ev.extremum(s1)
    assert s1_peak is not None and abs(s1_peak[0] - 1.5) < 0.13
    assert s1_peak[1] == max(v for _, v in s1) and 69.0 < s1_peak[1] <= 70.0
    assert ev.curve(points, "LOAD_8NM", "s1:T3_T4")[0][1] == pytest.approx(0.3 * s1[0][1])
    assert all(v > 0.0 for _, v in ev.curve(points, "LOAD_8NM", "s3:T2_T3"))
    assert ev.curve(points, "LOAD_8NM", "s3:T9_T9")[0][1] == 0.0
    # a broken-off step (last converged increment at a fraction of the load) leaves the curves
    broken = points[3]
    document = json.loads((tmp_path / f"{broken.job}_fields.json").read_text(encoding="utf-8"))
    document["steps"][1]["time"] = 0.4
    document["steps"][1]["complete"] = False
    (tmp_path / f"{broken.job}_fields.json").write_text(json.dumps(document), encoding="utf-8")
    again = ev.path_points(manifest, tmp_path)
    assert not again[3].summaries["LOAD_8NM"].complete
    assert len(ev.curve(again, "LOAD_8NM", "p_max")) == len(pressure) - 1
    assert all(x != broken.from_a_mm for x, _ in ev.curve(again, "LOAD_8NM", "p_max"))
    rows = ev.resolution_rows(
        points, "LOAD_8NM", ("p_max", "pinion_rotation_rad"), steps, p_bt, margin, factors=(1, 2, 3)
    )
    assert [r.steps_per_pitch for r in rows] == [12, 12, 6, 6, 4, 4]
    finest = rows[0]
    assert finest.shift_mm == 0.0 and finest.change == 0.0
    # the parabola through the neighbours recovers the location of the peak on every sub-grid;
    # the measured maximum of a coarser grid lies below the peak by at most the curvature
    # times the square of half a sub-grid step
    for row in rows:
        if row.quantity == "p_max":
            assert abs(row.shift_mm) < 1.0e-6 and -0.1 < row.change <= 0.0
    table = ev.format_resolution(rows)
    assert table[0].startswith("| steps per pitch") and len(table) == 2 + len(rows)
    with pytest.raises(InputRangeError):
        ev.resolution_rows(points, "LOAD_8NM", ("p_max",), steps, p_bt, margin, factors=(5,))
    with pytest.raises(InputRangeError):
        ev.curve(points, "LOAD_8NM", "nonsense")
    assert ev.extremum(()) is None
    assert ev.extremum(((0.0, 1.0),)) == (0.0, 1.0)


def _turned(vector: tuple[float, float, float], turn_deg: float) -> list[float]:
    c, s = math.cos(math.radians(turn_deg)), math.sin(math.radians(turn_deg))
    return [c * vector[0] - s * vector[1], s * vector[0] + c * vector[1], vector[2]]


def test_orientation_check_tells_turned_from_not_turned(tmp_path: Path) -> None:
    turn = 91.5
    distribution = {
        1: ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        2: ((0.6, 0.8, 0.0), (-0.8, 0.6, 0.0)),
    }
    document = _document(2.3e-3, 60.0, 4.0, 70.0)
    document["steps"][1]["orientation"] = [
        {
            "set": "WHEEL_RIM",
            "e": e,
            "a": _turned(a, turn),
            "b": _turned(b, turn),
            "nodes": [10 * e + k for k in range(8)],
            "fv": [0.6, 0.1],
        }
        for e, (a, b) in distribution.items()
    ] + [{"set": "WHEEL_HEAD_T3", "e": 99, "a": [1, 0, 0], "b": [0, 1, 0]}]
    path = tmp_path / "pos_001_fields.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    fields = ev.read_fields(path)
    step = fields.steps[1]
    assert len(step.orientation) == 3 and step.orientation[2].set_name == "WHEEL_HEAD_T3"
    assert step.orientation[0].nodes == tuple(range(10, 18)) and step.orientation[0].fv == (
        0.6,
        0.1,
    )
    assert step.orientation[2].nodes == () and step.orientation[2].fv is None
    # the directions of the database are the file turned by the instance: turned
    check = ev.orientation_check(step, distribution, turn)
    assert check.elements == 2 and check.missing == 1 and check.turned
    assert check.max_deviation_deg < 1.0e-9
    assert check.mean_if_not_turned_deg == pytest.approx(turn)
    # the same directions against an instance that was not turned: not as expected
    stuck = ev.orientation_check(step, distribution, 0.0)
    assert not stuck.turned and stuck.max_deviation_deg == pytest.approx(turn)
    # the centroid value is the mean of the nodal values of the file: element 1 exact, element 2
    # with one node at 0,68 instead of 0,6 (mean 0,61, difference 0,01); the third sample has
    # no field variables
    nodal = dict.fromkeys(range(10, 30), (0.6, 0.1))
    nodal[27] = (0.68, 0.1)
    fv = ev.field_variable_check(step, nodal)
    assert (fv.elements, fv.missing) == (2, 1)
    assert fv.max_difference_1 == pytest.approx(0.01) and fv.max_difference_2 == 0.0
    partial = ev.field_variable_check(step, dict.fromkeys(range(10, 18), (0.6, 0.1)))
    assert (partial.elements, partial.missing) == (1, 2)
    lines = ev.format_orientation(check, fv)
    assert (
        "turned with the instance" in lines[0] and "1 sampled elements not in the file" in lines[0]
    )
    assert "field variables at the centroids of 2 sampled elements" in lines[1]
    assert "NOT as expected" in ev.format_orientation(stuck, None)[0]
    empty = ev.orientation_check(fields.steps[0], distribution, turn)
    assert empty.elements == 0 and not empty.turned
    assert "no element" in ev.format_orientation(empty, None)[0]
    with pytest.raises(InputRangeError):
        ev.orientation_check(step, {1: ((0.0, 0.0, 0.0), (0.0, 1.0, 0.0))}, turn)


def test_tangent_angle_at_a_point_of_the_fillet() -> None:
    # a circular fillet of radius 0,5 mm around (0,4; 25,0): the tangent at the point whose
    # radius vector makes the angle beta with +x makes the angle |beta| with the centre line
    # of the tooth (+y, the tooth at 90 deg; the gap centre at 86,5 deg for a 7 deg pitch)
    def node(beta_deg: float, label: int) -> ev.FilletNode:
        x = 0.4 + 0.5 * math.cos(math.radians(beta_deg))
        y = 25.0 + 0.5 * math.sin(math.radians(beta_deg))
        return ev.FilletNode(label, x, y, 0.0, math.hypot(x, y), 1.0, -1.0, 1.0)

    contour = tuple(node(beta, 100 + k) for k, beta in enumerate(range(-80, 11, 10)))
    fillet = ev.Fillet("T2_T3", mid_width=contour[::-1], layers=())
    at = node(-30.0, 0)
    angle = ev.tangent_angle_deg(fillet, (at.x, at.y), (0.0, 0.0), 90.0, 7.0)
    assert angle == pytest.approx(30.0, abs=1e-9)
    at = node(-60.0, 0)
    assert ev.tangent_angle_deg(fillet, (at.x, at.y), (0.0, 0.0), 90.0, 7.0) == pytest.approx(60.0)
    # the centre line of the counter-clockwise tooth at 83 deg: the point (polar angle 88 deg)
    # lies beyond the gap centre 79,5 deg, so it belongs to that tooth and the angle shrinks by
    # the 7 deg; with the tooth at 97 deg the point lies before the gap centre 93,5 deg and
    # belongs to the clockwise tooth at 90 deg again
    assert ev.tangent_angle_deg(fillet, (at.x, at.y), (0.0, 0.0), 83.0, 7.0) == pytest.approx(53.0)
    assert ev.tangent_angle_deg(fillet, (at.x, at.y), (0.0, 0.0), 97.0, 7.0) == pytest.approx(60.0)
    assert (
        ev.tangent_angle_deg(
            ev.Fillet("x", mid_width=contour[:2], layers=()), (0.0, 25.0), (0.0, 0.0), 90.0, 7.0
        )
        is None
    )
    with pytest.raises(InputRangeError):
        ev.tangent_angle_deg(fillet, (at.x, at.y), (0.0, 0.0), math.nan, 7.0)


def test_series_of_a_folder_with_steps_and_rates(tmp_path: Path) -> None:
    manifest = {
        "material_step": "W1",
        "positions": [
            {
                "index": 1,
                "file": "pos_001_W1_QS.inp",
                "material_step": "W1",
                "rate": "QS",
                "variant": "",
                "point": "C",
                "rho_1_mm": 9.42,
                "from_A_mm": 1.6,
            },
            {
                "index": 1,
                "file": "pos_001_W3_DY1.inp",
                "material_step": "W3",
                "rate": "DY1",
                "variant": "",
                "point": "C",
                "rho_1_mm": 9.42,
                "from_A_mm": 1.6,
            },
            {"index": 2, "file": "pos_002.inp", "point": "", "rho_1_mm": 9.0, "from_A_mm": 1.2},
        ],
    }
    assert ev.series_names(manifest) == ("W1_QS", "W3_DY1", "W1")
    chosen = ev.path_points(manifest, tmp_path, "W3_DY1")
    assert [p.job for p in chosen] == ["pos_001_W3_DY1"] and chosen[0].series == "W3_DY1"
    assert [p.series for p in ev.path_points(manifest, tmp_path)] == ["W1", "W1_QS", "W3_DY1"]
    with pytest.raises(ParseError):
        ev.series_names({})
