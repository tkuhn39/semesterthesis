"""``scripts/fe_series_analysis.py``: the helpers of the series analysis on synthetic path
points (contact window of the middle tooth, shift within a pitch, values at the named points,
common positions of two folders, the runner's UTF-16 log)."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from gearcore.fe import evaluation as ev

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
PITCH = 2.952131434093549


@pytest.fixture(scope="module")
def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "fe_series_analysis", SCRIPTS / "fe_series_analysis.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _node(n: int, r: float) -> ev.ContactNode:
    return ev.ContactNode(
        n=n, x=r, y=0.0, z=0.0, r=r, p=10.0, f=None, tooth="T3", side="RIGHT", zone="flank"
    )


def _summary(
    step: str, x: float, forces: dict[str, float], rotation: float, s1: float, complete: bool = True
) -> ev.StepSummary:
    teeth = tuple(
        ev.ToothContact(
            tooth=half.split("_")[0],
            side=half.split("_")[1],
            nodes=3,
            p_max=50.0,
            at=_node(1, 26.0),
            force=f,
        )
        for half, f in forces.items()
    )
    return ev.StepSummary(
        name=step,
        pinion_rotation_rad=-rotation,
        wheel_moment_nmm=-16000.0,
        teeth=teeth,
        p_max=50.0 + x,
        p_max_at=None,
        fillets=(),
        s1_max=s1,
        s1_max_fillet=None,
        s3_min=-s1 * 1.2,
        s3_min_fillet=None,
        u_head_max=0.1,
        u_head_tooth="T3",
        time=1.0 if complete else 0.5,
        complete=complete,
    )


def _points(step: str = "LOAD_16NM", broken_at: int | None = None) -> list[ev.PathPoint]:
    """A grid of 10 per pitch from −1 to +1 pitch around A…E (path 3,4 mm): the middle tooth
    T3 carries load from −0,5 pitch to E + 0,5 pitch, the neighbours one pitch earlier and
    later; the rotation has its maximum at C (1,6 mm)."""
    out = []
    step_mm = PITCH / 10
    k = 0
    x = -PITCH
    labels = {10: "A", 15: "C", 22: "E"}  # grid indices: A at 0, C at 1,476, E at 3,542 mm
    while x <= PITCH + 3.4 + 1e-9:
        forces = {
            "T3_RIGHT": 300.0 if -0.5 * PITCH <= x <= 3.4 + 0.5 * PITCH else 0.0,
            "T4_RIGHT": 300.0 if x <= 3.4 - 0.5 * PITCH else 0.0,
            "T2_RIGHT": 300.0 if x >= 0.5 * PITCH else 0.0,
        }
        label = labels.get(k, "")
        complete = broken_at is None or k != broken_at
        out.append(
            ev.PathPoint(
                index=k + 1,
                label=label,
                from_a_mm=x,
                rho_1_mm=5.0 + x,
                job=f"pos_{k + 1:03d}",
                summaries={
                    step: _summary(
                        step,
                        x,
                        forces,
                        3.0e-3 - 1.0e-4 * (x - 1.476) ** 2,
                        80.0 - abs(x - 1.476) * 5.0,
                        complete,
                    )
                },
                series="W1_QS",
            )
        )
        k += 1
        x = -PITCH + k * step_mm
    return out


def test_contact_window_of_the_middle_tooth(script: ModuleType) -> None:
    points = _points()
    windows = script.contact_window(points, "LOAD_16NM")
    assert set(windows) == {"T2_RIGHT", "T3_RIGHT", "T4_RIGHT"}
    half = script.middle_tooth_half(windows, 3.4)
    assert half == "T3_RIGHT"
    lo, hi = windows[half]
    assert lo == pytest.approx(-0.5 * PITCH, abs=PITCH / 10)
    assert hi == pytest.approx(3.4 + 0.5 * PITCH, abs=PITCH / 10)
    assert script.middle_tooth_half({}, 3.4) is None


def test_shift_within_a_pitch(script: ModuleType) -> None:
    assert script.shift_within_pitch(0.1, PITCH) == pytest.approx(0.1)
    assert script.shift_within_pitch(PITCH + 0.1, PITCH) == pytest.approx(0.1)
    assert script.shift_within_pitch(-PITCH - 0.1, PITCH) == pytest.approx(-0.1)
    assert script.shift_within_pitch(0.6 * PITCH, PITCH) == pytest.approx(-0.4 * PITCH)
    assert script.shift_within_pitch(0.3, 0.0) == 0.3


def test_values_at_points_and_relative(script: ModuleType) -> None:
    points = _points()
    at = script.values_at_points(points, "LOAD_16NM", "pinion_rotation_rad")
    assert set(at) == {"A", "C", "E"}
    assert at["C"] == pytest.approx(3.0e-3) and at["A"] < at["C"]  # magnitudes
    assert script.relative(2.0, 2.5) == pytest.approx(0.25)
    assert script.relative(None, 2.5) is None and script.relative(0.0, 2.5) is None
    broken = _points(broken_at=15)
    assert "C" not in script.values_at_points(broken, "LOAD_16NM", "s1_max")
    edge = dict(script.edge_tooth_force(points, "LOAD_16NM"))
    assert edge[0.0] == 300.0  # at A two teeth carry 300 N: the second largest is 300
    assert edge[max(edge)] == 0.0  # beyond E + half a pitch only T2 carries: no second tooth
    assert len(edge) == len(points)
    single = [
        ev.PathPoint(
            index=1,
            label="C",
            from_a_mm=1.5,
            rho_1_mm=6.5,
            job="pos_001",
            summaries={"LOAD_16NM": _summary("LOAD_16NM", 1.5, {"T3_RIGHT": 300.0}, 3e-3, 80.0)},
            series="W1_QS",
        )
    ]
    assert script.edge_tooth_force(single, "LOAD_16NM") == ((1.5, 0.0),)
    assert script._pct(-0.0002) == "+0,0 %" and script._pct(-0.0012) == "-0,1 %"
    assert script._pct(None) == "–"


def test_common_positions(script: ModuleType) -> None:
    a = _points()
    b = [p for p in _points() if p.index % 2 == 1]
    pairs = script.common_positions(a, b)
    assert len(pairs) == len(b)
    assert all(abs(p.from_a_mm - q.from_a_mm) < 1e-9 for p, q in pairs)
    assert script.is_full_grid(a, 10, PITCH)
    assert not script.is_full_grid(b, 10, PITCH)  # every second point: a selection
    assert not script.is_full_grid([p for p in a if p.label], 10, PITCH)  # A, C, E only
    assert not script.is_full_grid(a[:1], 10, PITCH)


def test_run_log_in_utf16(script: ModuleType, tmp_path: Path) -> None:
    text = (
        "2026-10-09T17:45:17 start pos_001_W1_QS\n"
        "2026-10-09T17:48:20 end pos_001_W1_QS exit 0, completed\n"
        "SEAT: 42 closed contact nodes, largest CPRESS 3.77 MPa at node 42619\n"
        "2026-10-11T07:37:22 start pos_073_W1_QS\n"
        "2026-10-11T08:01:15 end pos_073_W1_QS exit 0, NOT completed (see pos_073_W1_QS.msg)\n"
    )
    (tmp_path / "run_log.txt").write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    runs = script.read_run_log(tmp_path, {"pos_001_W1_QS": "W1_QS", "pos_073_W1_QS": "W1_QS"})
    assert [r.job for r in runs] == ["pos_001_W1_QS", "pos_073_W1_QS"]
    assert runs[0].completed and runs[0].wall_s == pytest.approx(183.0)
    assert not runs[1].completed and runs[1].wall_s == pytest.approx(1433.0)
    (tmp_path / "run_log.txt").write_text(text, encoding="utf-8")
    assert len(script.read_run_log(tmp_path, {})) == 2
    assert script.read_run_log(tmp_path / "none", {}) == ()


def test_run_log_of_the_parallel_runner(script: ModuleType, tmp_path: Path) -> None:
    """The parallel runner (ADR-116 item 55 (f)) writes no exit code and a core note."""
    text = (
        "2026-10-22T11:38:44 start pos_001_W1_DY1 (4 cores, 3 at a time)\n"
        "2026-10-22T11:38:44 start pos_001_W1_DY2 (4 cores, 3 at a time)\n"
        "2026-10-22T11:43:08 end pos_001_W1_DY1, completed\n"
        "SEAT: 21 closed contact nodes, largest CPRESS 12.42 MPa at node 44420 (r 26.902, z 0.000)\n"
        "2026-10-22T11:43:09 fields of pos_001_W1_DY1 written to pos_001_W1_DY1_fields.json\n"
        "2026-10-22T11:44:00 end pos_001_W1_DY2, NOT completed (see pos_001_W1_DY2.msg)\n"
    )
    (tmp_path / "run_log.txt").write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    runs = script.read_run_log(tmp_path, {"pos_001_W1_DY1": "W1_DY1", "pos_001_W1_DY2": "W1_DY2"})
    assert [r.job for r in runs] == ["pos_001_W1_DY1", "pos_001_W1_DY2"]
    assert runs[0].completed and runs[0].wall_s == 264.0 and runs[0].series == "W1_DY1"
    assert not runs[1].completed and runs[1].wall_s == 316.0


def test_chattering_nodes_of_a_message_file(script: ModuleType, tmp_path: Path) -> None:
    msg = tmp_path / "pos_073_W1_QS.msg"
    lines = ["noise"] * 10 + [
        " NODE WHEEL-1.42619 OF CONTACT PAIR (WHEEL_FLANKS,PINION) HAS PENETRATION",
        " NODE WHEEL-1.42619 OF CONTACT PAIR (WHEEL_FLANKS,PINION) HAS PENETRATION",
        " NODE WHEEL-1.7 OF CONTACT PAIR (WHEEL_FLANKS,PINION) HAS PENETRATION",
    ]
    msg.write_text("\n".join(lines), encoding="utf-8")
    mesh = {42619: (18.25, 18.25, -3.0)}
    out = script.chattering_nodes(msg, mesh)
    assert out[0].startswith("Knoten 42619 (r 25,809 mm, z -3,00 mm, 2 Nennungen)")
    assert out[1] == "Knoten 7 (?, 1 Nennungen)"
    assert script.chattering_nodes(tmp_path / "none.msg", mesh) == []


def _stommel_table(
    path: Path, rows: list[tuple[int, str, float, float, float, float, float | str, str]]
) -> None:
    head = "node,zone,r_mm,z_mm,a_B_V,a_stat,N_predicted,life_flag\n"
    body = "".join(
        f"{n},{zone},{r},{z},{a},{s},{life},{flag}\n" for n, zone, r, z, a, s, life, flag in rows
    )
    path.write_text(head + body, encoding="utf-8")


def test_read_stommel_tables(script: ModuleType, tmp_path: Path) -> None:
    for torque, factor in (("16NM", 2.0), ("8NM", 1.0), ("12NM", 1.5)):
        _stommel_table(
            tmp_path / f"knoten_LOAD_{torque}.csv",
            [
                (1, "head", 25.8, -3.0, 5.0 * factor, 0.9, "inf", "infinite"),
                (
                    2,
                    "fillet T3_T4",
                    19.1,
                    -6.0,
                    1.2 * factor,
                    0.5 * factor,
                    1.0e5 / factor,
                    "finite",
                ),
                (3, "fillet T2_T3", 19.1, 0.0, 1.1 * factor, 0.6 * factor, 2.0e5, "finite"),
                (4, "rim", 16.5, 0.0, 0.3, 0.1, "inf", "infinite"),
            ],
        )
    out = script.read_stommel("W2", tmp_path)
    assert [s.step for s in out] == ["LOAD_8NM", "LOAD_12NM", "LOAD_16NM"]  # by torque, not name
    first = out[0]
    assert first.critical_node == 2 and first.critical_zone == "fillet T3_T4"
    assert first.a_B_V == pytest.approx(1.2) and first.N_predicted == pytest.approx(1.0e5)
    assert first.fillet_a_stat_node == 3 and first.fillet_a_stat_max == pytest.approx(0.6)
    assert first.global_node == 1 and first.global_zone == "head"
    assert first.fillet_nodes == 2 and first.nodes == 4
    assert first.fillet_above_cyclic == 2 and first.fillet_above_static == 0
    assert out[2].fillet_above_static == 1  # 16 Nm: a_stat 1,0 at node 2 is not above, 1,2 at 3 is
    # a table without the middle fillets is refused, never silently read as the whole sector
    _stommel_table(
        tmp_path / "knoten_LOAD_16NM.csv", [(1, "head", 25.8, -3.0, 5.0, 0.9, "inf", "x")]
    )
    with pytest.raises(script.InputRangeError):
        script.read_stommel("W2", tmp_path)
    assert script.read_stommel("W2", tmp_path / "none") == []
