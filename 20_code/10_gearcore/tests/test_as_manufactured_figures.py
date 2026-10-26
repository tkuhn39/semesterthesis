"""The figures of the gears as manufactured (``scripts/as_manufactured_figures.py``)."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

from gearcore import contour as ct

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "as_manufactured_figures.py"


def _load():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("as_manufactured_figures", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_flank_deviation_shows_relief_slope_and_thickness() -> None:
    script = _load()
    nominal, measured = script._generations("kst_e", "beide")
    # pinion: the linear relief of 23,6 µm from d 51,946 to the tip on top of the thinner span
    pinion_nominal = ct.tooth_contour(nominal, "pinion", points=2000)
    pinion_measured = ct.tooth_contour(
        measured.generation, "pinion", points=2000, modification=measured.modification("pinion")
    )
    d, f = script.flank_deviation(
        pinion_nominal, pinion_measured, script.base_radius_mm(nominal, pinion_nominal)
    )
    below_relief = f[d < 51.9]
    assert np.ptp(below_relief) < 1.0  # constant below the relief start (the span alone)
    assert -12.0 < float(below_relief.mean()) < -3.0  # half the span difference per flank
    assert -40.0 < float(f[-1]) < -25.0  # the relief at the tip on top of it
    # wheel: the profile slope, plus material at the tip, zero near the measuring circle
    wheel_nominal = ct.tooth_contour(nominal, "wheel", points=2000)
    wheel_measured = ct.tooth_contour(
        measured.generation, "wheel", points=2000, modification=measured.modification("wheel")
    )
    d, f = script.flank_deviation(
        wheel_nominal, wheel_measured, script.base_radius_mm(nominal, wheel_nominal)
    )
    assert float(f[-1]) > float(f[0]) + 8.0
    assert abs(float(np.interp(51.728, d, f))) < 2.0


def test_contour_deviation_agrees_with_the_involute_and_shows_the_root() -> None:
    script = _load()
    nominal, measured = script._generations("kst_e", "beide")
    for role in ("pinion", "wheel"):
        nominal_contour = ct.tooth_contour(nominal, role, points=2000)
        measured_contour = ct.tooth_contour(
            measured.generation, role, points=2000, modification=measured.modification(role)
        )
        d, f = script.contour_deviation(nominal_contour, measured_contour)
        assert np.all(np.diff(d) >= 0.0)
        # on the involute the nearest-point distance is the base-circle arc of the turn
        d_inv, f_inv = script.flank_deviation(
            nominal_contour, measured_contour, script.base_radius_mm(nominal, nominal_contour)
        )
        inside = (d > d_inv[0] + 0.1) & (d < d_inv[-1] - 0.1)
        assert inside.any()
        assert np.abs(np.interp(d[inside], d_inv, f_inv) - f[inside]).max() < 0.5
        # at the root circle the deviation is the change of the root radius (deeper = minus)
        root_shift_um = 500.0 * (
            measured_contour.generated_root_diameter_mm - nominal_contour.generated_root_diameter_mm
        )
        assert root_shift_um < -5.0
        assert abs(float(f[0]) - root_shift_um) < 3.0


def test_figures_are_written(tmp_path: Path) -> None:
    script = _load()
    written = script.run(tmp_path)
    stems = {p.stem for p in written}
    assert stems == {"kontur_ritzel", "kontur_rad", "kontur_zaehne", "netz_kopfkappe"}
    assert all(p.exists() and p.stat().st_size > 0 for p in written)
    assert len(written) == 12  # four figures as svg, pdf and png (kontur_zaehne since 2026-10-25)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
