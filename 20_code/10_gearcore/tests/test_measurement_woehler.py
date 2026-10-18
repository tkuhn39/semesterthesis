"""Wöhler evaluation of the running tests (L2): the two lines on exact data, the pooled scatter
with the correction of DIN 50100, the quantile lines, the VDI 2736 Blatt 4 estimate on a hand
example, Rossow and rank estimates, the nets on an exact Weibull sample, the runout rule."""

import math

import pytest

from gearcore.errors import InputRangeError
from gearcore.measurement import woehler as wl


def _point(run: str, level: int, cycles: int, criterion: str = "Totalausfall",
           **kwargs: object) -> wl.TestPoint:
    return wl.TestPoint(run_id=run, material="PA46-GF30", campaign="KV3 2026", wheel=None,
                        level_Nm=level, load_Nm=float(level), cycles=cycles,
                        criterion=criterion, **kwargs)  # type: ignore[arg-type]


def _exact_semilog(a: float, b: float) -> list[wl.TestPoint]:
    points = []
    for i, level in enumerate((8, 8, 12, 12, 16, 16)):
        points.append(_point(f"r{i}", level, round(10.0 ** (a - b * level))))
    return points


def test_semilog_fit_recovers_the_line_and_floors_the_scatter() -> None:
    points = _exact_semilog(9.0, 0.25)
    fit = wl.semilog_fit(points)
    assert fit.intercept == pytest.approx(9.0, abs=1e-6) and fit.slope == pytest.approx(0.25, abs=1e-7)
    assert fit.s_lgN == pytest.approx(0.0, abs=1e-6) and fit.s_used == wl.SCATTER_FLOOR
    assert fit.lg_cycles_50(12.0) == pytest.approx(6.0, abs=1e-6)
    assert fit.cycles(12.0, 10) == pytest.approx(10.0 ** (6.0 - 1.282 * 0.10), rel=1e-6)
    assert fit.cycles(12.0, 1) == pytest.approx(10.0 ** (6.0 - 2.33 * 0.10), rel=1e-6)
    assert (fit.load_min, fit.load_max) == (8.0, 16.0)
    with pytest.raises(InputRangeError):
        fit.cycles(12.0, 5)


def test_loglog_fit_recovers_basquin() -> None:
    points = [_point(f"r{i}", level, round(10.0 ** (10.0 - 4.0 * math.log10(level))))
              for i, level in enumerate((8, 12, 16, 8, 12, 16))]
    fit = wl.loglog_fit(points)
    assert fit.intercept == pytest.approx(10.0, abs=1e-5) and fit.slope == pytest.approx(4.0, abs=1e-5)


def test_pooled_scatter_correction() -> None:
    # residuals ±0,2 around an exact line, n = 6: s = sqrt(6 · 0,04 / 4) = 0,2449
    base = _exact_semilog(9.0, 0.25)
    points = [p.model_copy(update={"cycles": round(p.cycles * 10.0 ** (0.2 if i % 2 else -0.2))})
              for i, p in enumerate(base)]
    s, s_corr, s_used = wl.pooled_scatter("semilog", 9.0, 0.25, points)
    assert s == pytest.approx(math.sqrt(6 * 0.04 / 4), rel=1e-4)
    assert s_corr == pytest.approx(s * (6 - 1.74) / 4, rel=1e-9) and s_used == s_corr
    with pytest.raises(InputRangeError):
        wl.pooled_scatter("semilog", 9.0, 0.25, points[:2])


def test_vdi2736_levels_hand_example() -> None:
    points = [_point("a", 12, 1_000_000), _point("b", 12, 10_000_000),
              _point("c", 16, 100_000), _point("d", 16, 1_000_000), _point("e", 8, 30_000_000)]
    estimates, s_bar = wl.vdi2736_levels(points)
    by_level = {e.level_Nm: e for e in estimates}
    assert by_level[12].L_i_50 == pytest.approx(6.5) and by_level[12].s_i == pytest.approx(math.sqrt(0.5))
    assert by_level[16].L_i_50 == pytest.approx(5.5) and by_level[8].s_i is None
    expected_s_bar = (math.sqrt(0.5) / 6.5 + math.sqrt(0.5) / 5.5) / 2
    assert s_bar == pytest.approx(expected_s_bar)
    assert by_level[12].L_i_10 == pytest.approx((1 - 1.28 * expected_s_bar) * 6.5)
    assert by_level[12].N_i_10 == pytest.approx(10 ** ((1 - 1.28 * expected_s_bar) * 6.5))
    single, s_none = wl.vdi2736_levels([points[0], points[2]])
    assert s_none is None and single[0].N_i_10 is None and single[0].L_i_10 is None


def test_rossow_and_rank() -> None:
    assert wl.rossow(1, 9) == pytest.approx(2 / 28) and wl.rossow(9, 9) == pytest.approx(26 / 28)
    assert wl.rank_estimate(5, 9) == pytest.approx(0.5)
    with pytest.raises(InputRangeError):
        wl.rossow(0, 9)


def test_nets_on_exact_samples() -> None:
    n = 12
    shape, scale = 3.0, 1.1
    probabilities = [wl.rossow(j, n) for j in range(1, n + 1)]
    weibull_sample = [scale * (-math.log(1 - p)) ** (1 / shape) for p in probabilities]
    fit = wl.net_fit(weibull_sample, "weibull", "rossow")
    assert fit.parameter == pytest.approx(shape, rel=1e-6) and fit.scale == pytest.approx(scale, rel=1e-6)
    assert fit.r_squared == pytest.approx(1.0, abs=1e-9)
    assert fit.factor_10 == pytest.approx((math.log(1 / 0.9) / math.log(2)) ** (1 / shape))
    from statistics import NormalDist

    gauss_sample = [10 ** (0.05 + 0.15 * NormalDist().inv_cdf(p)) for p in probabilities]
    gfit = wl.net_fit(gauss_sample, "gauss", "rossow")
    assert gfit.parameter == pytest.approx(0.15, rel=1e-6) and gfit.scale == pytest.approx(10 ** 0.05)
    assert gfit.factor_10 == pytest.approx(10 ** (-1.282 * 0.15))
    with pytest.raises(InputRangeError):
        wl.net_fit([1.0, 2.0], "gauss")


def test_runout_rule_and_evaluate() -> None:
    # results scattered ±0,1 decades around the line (exactly aligned results make the nets
    # degenerate, every normalised count being 1)
    base = _exact_semilog(9.0, 0.25)
    points = [p.model_copy(update={"cycles": round(p.cycles * 10.0 ** (0.1 if i % 2 else -0.1))})
              for i, p in enumerate(base)]
    runout = _point("ro", 8, 50_000_000, runout=True, criterion="Durchläufer")
    stepped = _point("st", 12, 2_000_000, stepped=True)
    admitted = wl.runout_rule(points + [runout, stepped])
    assert {p.run_id for p in admitted} == {"r2", "r3", "r4", "r5"}
    result = wl.evaluate(points + [runout, stepped])
    assert len(result.admitted) == 4 and result.all_failures is not None
    assert result.all_failures.n == 6 and result.semilog.n == 4
    assert [lvl.level_Nm for lvl in result.levels] == [12, 16]
    assert result.levels[0].N_50 == pytest.approx(result.semilog.cycles(12.0), rel=1e-9)
    assert result.levels[0].N_10 < result.levels[0].N_50 < result.levels[1].N_50 * 10
    assert len(result.nets) == 4 and result.vdi_s_bar is not None
    assert all(f.parameter > 0.0 for f in result.nets)
    with pytest.raises(InputRangeError):
        wl.evaluate(points[:2])
    other = _point("x", 8, 1000).model_copy(update={"material": "POM"})
    with pytest.raises(InputRangeError):
        wl.evaluate(points + [other])
