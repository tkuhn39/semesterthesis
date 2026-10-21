"""The wear evaluation of the after-test contour scans (``scripts/contour_wear.py``, M5): the
axis from the GINA tip and root circles, the rotation of a tooth on its fillets and the wear
metrics, checked on a synthetic scan built from the nominal tooth of the kst-E generation."""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest

from gearcore.io.p40_contour import ContourScan
from gearcore.measurement import contour_scan as cs

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


@pytest.fixture(scope="module")
def wear() -> ModuleType:
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("contour_wear", SCRIPTS / "contour_wear.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["contour_wear"] = module  # dataclasses resolve InitVar through sys.modules
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def synthetic(wear: ModuleType) -> dict[str, Any]:
    """Three nominal teeth of the wheel in scan order (+x to −x) about a centre away from the
    origin; the middle tooth carries a 100 µm uniform recession of its right flank above
    r = 25,5 mm (a worn flank), the others are untouched."""
    generation = wear.ms._generation("kst_e")
    geometry = cs.scan_geometry(generation, "wheel")
    outline = cs.nominal_outline(generation, "wheel", points=600)
    pitch = 2.0 * math.pi / geometry.number_of_teeth
    centre = np.array([0.15, -0.10])
    teeth = []
    for k, theta in enumerate((pitch, 0.0, -pitch)):
        pts = outline.copy()
        if k == 1:
            r = np.hypot(pts[:, 0], pts[:, 1])
            worn = (pts[:, 0] > 0.0) & (r > 25.5) & (r < geometry.r_a - 0.02)
            normals = cs.outward_normals(pts)
            pts[worn] -= 0.100 * normals[worn]
        teeth.append(wear._rotate(pts, -theta))
    xy = np.vstack(teeth) + centre
    scan = ContourScan(
        name="synthetic", block="A", z_mm=85.95,
        points_mm=tuple((float(p[0]), float(p[1])) for p in xy),
    )
    r_root = 0.5 * geometry.generated_root_diameter_mm
    return {
        "geometry": geometry, "outline": outline, "scan": scan, "centre": centre,
        "r_root": r_root,
    }


def test_axis_from_the_gina_circles_recovers_the_centre(wear: ModuleType, synthetic: dict[str, Any]) -> None:
    scan = synthetic["scan"]
    geometry = synthetic["geometry"]
    runs = cs.segment(scan)
    axis = wear.axis_from_circles(scan, runs, geometry.r_a, synthetic["r_root"])
    assert axis.tip_runs_used == 3 and axis.root_runs_used >= 2
    assert abs(axis.centre_mm[0] - synthetic["centre"][0]) < 0.005
    assert abs(axis.centre_mm[1] - synthetic["centre"][1]) < 0.010
    assert axis.rms_um < 25.0  # the tip chamfers and the fillet starts sit in the bands


def test_fillet_rotation_and_flank_curves_show_the_worn_flank(
    wear: ModuleType, synthetic: dict[str, Any]
) -> None:
    scan = synthetic["scan"]
    geometry = synthetic["geometry"]
    outline = synthetic["outline"]
    ev, axis = wear.evaluate_fixed(scan, geometry, cs.DEFAULT_SETTINGS, geometry.r_a, synthetic["r_root"])
    assert len(ev.teeth) == 3
    middle = ev.teeth[1]
    frame = wear.fillet_frame(scan, ev, middle, axis, geometry, outline, "synthetic", "Zahn 2")
    assert frame.fillet_rms_um < 5.0
    assert abs(frame.theta_rad) < 2.0e-4  # the middle tooth sits on +y
    curves = {c.hand: c for c in wear.flank_curves(frame, geometry, outline)}
    assert set(curves) == {-1, 1}
    left = curves[1]
    assert float(np.max(np.abs(left.deviation_um))) < 5.0  # untouched flank
    right = curves[-1]
    above = right.r_mm > 25.6
    assert float(np.median(right.deviation_um[above])) == pytest.approx(-100.0, abs=5.0)
    below = right.r_mm < 25.4
    assert float(np.max(np.abs(right.deviation_um[below]))) < 5.0


def test_wear_row_metrics_on_a_flat_reference(wear: ModuleType, synthetic: dict[str, Any]) -> None:
    geometry = synthetic["geometry"]
    grid = wear._grid(geometry)
    ref = wear.Reference(hand=-1, r_mm=grid, mean_um=np.zeros(len(grid)), std_um=np.zeros(len(grid)), flanks=3)
    deviation = np.where(grid >= 25.5, -100.0, 0.0)
    curve = wear.FlankCurve(me="x", scan="s", tooth_label="Zahn 1", hand=-1, r_mm=grid, deviation_um=deviation)
    row = wear.wear_row(curve, ref, grid, geometry, 8, -200.0, 3.0, None, 10.0)
    assert row.wear_max_um == pytest.approx(100.0)
    assert row.onset_r_mm == pytest.approx(25.5, abs=0.011)
    assert row.tip_loss_um == pytest.approx(100.0)
    assert row.step_edge_mm is None  # the wear never drops below 10 µm above the maximum
    assert 75.0 < row.wear_mean_um < 90.0  # the active profile starts 0,3 mm below the onset


def test_tooth_labels_name_the_middle_tooth_and_two_named_teeth(wear: ModuleType) -> None:
    from gearcore.measurement.inventory import MeasurementFile

    class Teeth:
        def __init__(self, n: int) -> None:
            self.teeth = [None] * n

    one = MeasurementFile.model_construct(path="x", me="97351", part="wheel", kind="contour", tooth=18)
    assert wear._tooth_labels(Teeth(3), one) == {0: "Nachbar +x", 1: "Zahn 18", 2: "Nachbar −x"}
    two = MeasurementFile.model_construct(
        path="x", me="97340", part="wheel", kind="contour", tooth=36, second_tooth=37
    )
    assert wear._tooth_labels(Teeth(2), two) == {0: "Zahn 36", 1: "Zahn 37"}
