"""``scripts/fe_fillet_comparison.py``: the effect of a root fillet variant against the
baseline at the named points, the compatibility refusals, the point of the largest root
stress, the location of the maximum and the rows of the plane-strain sweep report."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from gearcore.errors import InputRangeError
from gearcore.fe import evaluation as ev

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
POINTS = {"A": 0.0, "B": 0.7, "C": 1.476, "D": 2.4, "E": 3.4}


@pytest.fixture(scope="module")
def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "fe_fillet_comparison", SCRIPTS / "fe_fillet_comparison.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _layer(z: float, s1: float, r: float) -> ev.FilletLayer:
    return ev.FilletLayer(z=z, s1=s1, n_s1=4711, r_s1=r, s3=-s1, n_s3=4712, r_s3=r)


def _summary(step: str, s1: float, rotation: float, fillet: str = "T3_T4") -> ev.StepSummary:
    extreme = ev.FilletExtreme(
        name=fillet,
        s1_max=s1,
        s1_layer=_layer(-6.0, s1, 25.1),
        s3_min=-s1 * 1.2,
        s3_layer=_layer(-3.0, -s1 * 1.2, 25.2),
    )
    return ev.StepSummary(
        name=step,
        pinion_rotation_rad=-rotation,
        wheel_moment_nmm=-16000.0,
        teeth=(),
        p_max=70.0,
        p_max_at=None,
        fillets=(extreme,),
        s1_max=s1,
        s1_max_fillet=extreme,
        s3_min=-s1 * 1.2,
        s3_min_fillet=extreme,
        u_head_max=0.05,
        u_head_tooth="T3",
    )


def _points(s1_of: dict[str, float], rotation: float = 2.0e-3) -> list[ev.PathPoint]:
    return [
        ev.PathPoint(
            index=i,
            label=label,
            from_a_mm=x,
            rho_1_mm=7.0 + x,
            job=f"pos_{i:03d}_W1_QS",
            summaries={"LOAD_16NM": _summary("LOAD_16NM", s1_of[label], rotation)},
            series="W1_QS",
        )
        for i, (label, x) in enumerate(POINTS.items(), start=31)
    ]


def _manifest(
    edge: float = 0.1, body: str = "pocket", fillet: dict[str, Any] | None = None
) -> dict[str, Any]:
    mesh: dict[str, Any] = {"body": {"shape": body}}
    if fillet is not None:
        mesh["fillet"] = fillet
    return {
        "step_names": ["SEAT", "LOAD_16NM"],
        "pinion_surface": {"tip_rounding_mm": edge},
        "wheel_mesh": mesh,
        "positions": [
            {"index": i, "file": f"pos_{i:03d}_W1_QS.inp", "point": label, "from_A_mm": x}
            for i, (label, x) in enumerate(POINTS.items(), start=31)
        ],
    }


def _folder(script: ModuleType, name: str, s1_of: dict[str, float], **kwargs: Any) -> Any:
    manifest = _manifest(**kwargs)
    return script.Folder(
        Path(name), manifest, {"W1_QS": _points(s1_of)}, manifest["wheel_mesh"].get("fillet")
    )


BASE = {"A": 36.0, "B": 34.0, "C": 59.0, "D": 38.0, "E": 36.5}
FILLET = {"label": "bezier_f1", "kind": "bezier"}


def test_effect_and_peak_point(script: ModuleType) -> None:
    baseline = _folder(script, "base", BASE)
    variant = _folder(script, "var", {k: v * 0.75 for k, v in BASE.items()}, fillet=FILLET)
    rel = script.effect(baseline, variant, "W1_QS", "LOAD_16NM", "s1_max")
    assert set(rel) == set(POINTS)
    assert all(v == pytest.approx(-0.25) for v in rel.values())
    # the rotation is unchanged, the compressive stress scales with σ1 in the fixture
    assert script.effect(baseline, variant, "W1_QS", "LOAD_16NM", "pinion_rotation_rad") == {
        k: pytest.approx(0.0) for k in POINTS
    }
    assert script.effect(baseline, variant, "W1_QS", "LOAD_16NM", "s3_min")["C"] == pytest.approx(
        -0.25
    )
    assert script.effect(baseline, variant, "W2_QS", "LOAD_16NM", "s1_max") == {}
    assert script.peak_point(baseline, "W1_QS", "LOAD_16NM") == "C"
    with pytest.raises(InputRangeError):
        script.peak_point(baseline, "W2_QS", "LOAD_16NM")


def test_s1_location(script: ModuleType) -> None:
    points = _points(BASE)
    name, s1, r, z = script.s1_location(points, "LOAD_16NM", "C")
    assert (name, s1, r, z) == ("T3_T4", 59.0, 25.1, -6.0)
    assert script.s1_location(points, "LOAD_8NM", "C") is None
    assert script.s1_location(points, "LOAD_16NM", "F") is None


def test_check_compatible_refuses_everything_but_the_fillet(script: ModuleType) -> None:
    baseline = _folder(script, "base", BASE)
    script.check_compatible(baseline, _folder(script, "ok", BASE, fillet=FILLET))
    with pytest.raises(InputRangeError, match="pinion tip edge"):
        script.check_compatible(baseline, _folder(script, "edge", BASE, edge=0.05, fillet=FILLET))
    with pytest.raises(InputRangeError, match="body"):
        script.check_compatible(baseline, _folder(script, "ring", BASE, body="ring", fillet=FILLET))
    with pytest.raises(InputRangeError, match="no wheel_mesh.fillet"):
        script.check_compatible(baseline, _folder(script, "plain", BASE))
    with pytest.raises(InputRangeError, match="baseline carries"):
        script.check_compatible(_folder(script, "b", BASE, fillet=FILLET), baseline)
    shifted = _folder(script, "shift", BASE, fillet=FILLET)
    shifted.manifest["positions"][2]["from_A_mm"] += 0.01
    with pytest.raises(InputRangeError, match="other positions"):
        script.check_compatible(baseline, shifted)
    other_steps = _folder(script, "steps", BASE, fillet=FILLET)
    other_steps.manifest["step_names"] = ["SEAT", "LOAD_8NM", "LOAD_16NM"]
    with pytest.raises(InputRangeError, match="other load steps"):
        script.check_compatible(baseline, other_steps)


def test_read_sweep(script: ModuleType, tmp_path: Path) -> None:
    def row(*cells: str) -> str:
        return "| " + " | ".join(cells) + " |"

    header = row(
        "Art", "Variante", "σ1 in MPa", "Δ", "Mises in MPa", "Kopfverschiebung in mm",
        "Übergang d in mm", "Fußkreis d in mm", "ρ_min in mm", "Abstand Kopfkante in mm",
        "Eckensinus", "Status",
    )  # fmt: skip
    report = tmp_path / "bericht.md"
    report.write_text(
        "\n".join(
            [
                "# Parameterstudie",
                "",
                header,
                "|---|---|---|---|---|---|---|---|---|---|---|---|",
                row(
                    "trochoid",
                    "trochoid",
                    "145,20",
                    "0,0 %",
                    "120,66",
                    "0,1990",
                    "50,157",
                    "49,524",
                    "0,240",
                    "0,490",
                    "0,631",
                    "ok",
                ),  # fmt: skip
                row(
                    "bezier",
                    "bezier_f1",
                    "98,40",
                    "-32,2 %",
                    "84,63",
                    "0,1461",
                    "51,210",
                    "50,216",
                    "0,633",
                    "0,203",
                    "0,656",
                    "ok",
                ),  # fmt: skip
                row(
                    "bionic",
                    "bionic_phiauto_r0.6",
                    "–",
                    "–",
                    "–",
                    "–",
                    "–",
                    "–",
                    "–",
                    "–",
                    "–",
                    "nicht baubar: no circle",
                ),  # fmt: skip
                row(
                    "ellipse",
                    "ellipse_g15_ab3.5",
                    "155,96",
                    "7,4 %",
                    "123,17",
                    "0,2528",
                    "50,157",
                    "48,466",
                    "0,074",
                    "0,490",
                    "0,683",
                    "ok",
                ),  # fmt: skip
            ]
        ),
        encoding="utf-8",
    )
    rows = script.read_sweep(report)
    assert set(rows) == {"trochoid", "bezier_f1", "ellipse_g15_ab3.5"}
    assert rows["bezier_f1"].delta == pytest.approx(-0.322)
    assert rows["bezier_f1"].clearance_mm == pytest.approx(0.203)
    assert rows["trochoid"].root_mm == pytest.approx(49.524)
    assert rows["ellipse_g15_ab3.5"].delta == pytest.approx(0.074)
    empty = tmp_path / "leer.md"
    empty.write_text("# nichts\n", encoding="utf-8")
    with pytest.raises(InputRangeError):
        script.read_sweep(empty)


def test_read_sweep_skips_the_summary_table_and_refuses_a_malformed_row(
    script: ModuleType, tmp_path: Path
) -> None:
    def row(*cells: str) -> str:
        return "| " + " | ".join(cells) + " |"

    ok = row("bezier", "bezier_f1", "98,40", "-32,2 %", "84,63", "0,1461", "51,210", "50,216",
             "0,633", "0,203", "0,656", "ok")  # fmt: skip
    # the summary table of the report has eight cells and is not a variant row
    summary = row("bezier", "bezier_f1", "98,40", "-32,2 %", "bezier_f2.5", "93,82", "-35,4 %",
                  "0,203 mm")  # fmt: skip
    report = tmp_path / "bericht.md"
    report.write_text("\n".join([summary, ok]), encoding="utf-8")
    assert set(script.read_sweep(report)) == {"bezier_f1"}
    broken = row("bezier", "bezier_f1", "98,40", "n. a.", "84,63", "0,1461", "51,210", "50,216",
                 "0,633", "0,203", "0,656", "ok")  # fmt: skip
    report.write_text(broken, encoding="utf-8")
    with pytest.raises(InputRangeError, match="bezier_f1"):
        script.read_sweep(report)


def test_check_compatible_refuses_other_labels_and_other_settings(script: ModuleType) -> None:
    baseline = _folder(script, "base", BASE)
    relabelled = _folder(script, "label", BASE, fillet=FILLET)
    relabelled.manifest["positions"][2]["point"] = "X"
    with pytest.raises(InputRangeError, match="other positions"):
        script.check_compatible(baseline, relabelled)
    other = _folder(script, "iter", BASE, fillet=FILLET)
    other.manifest["iteration_limits"] = [20, 30, 50]
    with pytest.raises(InputRangeError, match="iteration_limits"):
        script.check_compatible(baseline, other)
    other_mesh = _folder(script, "layers", BASE, fillet=FILLET)
    other_mesh.manifest["wheel_mesh"]["layers"] = 40
    with pytest.raises(InputRangeError, match="wheel_mesh.layers"):
        script.check_compatible(baseline, other_mesh)
    # the rate cards may differ in their file (the user's mapping per variant mesh), not in
    # their material data
    card = {"file": "wheel-pocket_mesh_QS.cof", "youngs_modulus_mpa": 2282.078, "name": "QS"}
    baseline.manifest["rates"] = {"QS": dict(card)}
    same_data = _folder(script, "cof", BASE, fillet=FILLET)
    same_data.manifest["rates"] = {"QS": {**card, "file": "wheel-pocket-bezier_f1_mesh_QS.cof"}}
    script.check_compatible(baseline, same_data)
    other_data = _folder(script, "modul", BASE, fillet=FILLET)
    other_data.manifest["rates"] = {"QS": {**card, "youngs_modulus_mpa": 4156.0}}
    with pytest.raises(InputRangeError, match="rates"):
        script.check_compatible(baseline, other_data)


def test_figures_on_a_single_series(script: ModuleType, tmp_path: Path) -> None:
    """Both figures draw with one series present (the other material steps plot nothing but
    keep their place in the cycle); ``save`` warns on legend overlaps, warnings are errors."""
    baseline = _folder(script, "base", BASE)
    variant = _folder(script, "var", {k: v * 0.75 for k, v in BASE.items()}, fillet=FILLET)
    written = script.figure_effect(
        baseline, [variant], "QS", "LOAD_16NM", "s1_max", tmp_path / "effekt"
    )
    assert {p.suffix for p in written} == {".svg", ".png"}
    sweep = {
        "bezier_f1": script.SweepRow(
            "bezier", "bezier_f1", 98.4, -0.322, 51.21, 50.216, 0.633, 0.203
        )
    }
    written = script.figure_overview(
        baseline, [variant], "QS", "LOAD_16NM", "C", tmp_path / "uebersicht", sweep
    )
    assert all(p.is_file() for p in written)
    assert "σ1 max" in script.caption_effect("QS", "LOAD_16NM", "s1_max")
    assert script.caption_overview("QS", "LOAD_16NM", "C", True).endswith("Lastfleck an B).")


def test_variant_names(script: ModuleType) -> None:
    assert script.variant_name("bezier_f1").startswith("Bézier")
    assert script.plain_name("bionic_phiauto_r0.3").endswith("r 0,3 S_L")
    assert script.variant_name("unbekannt_x") == "unbekannt_x"
    assert script.short_name("ellipse_g30_ab3") == "Ellipse 30°, 3,0"
    assert script.series_sorted(["W2_DY2", "W1_QS", "W1_DY1", "W4_QS"]) == [
        "W1_QS",
        "W4_QS",
        "W1_DY1",
        "W2_DY2",
    ]
