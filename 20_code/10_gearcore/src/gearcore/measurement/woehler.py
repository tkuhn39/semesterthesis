"""Wöhler lines of the running tests (L2): the test points of one material and campaign from the
rig workbook (``test_rig``), two lines fitted in the finite-life range, the pooled scatter after
DIN 50100 (Perlenschnurverfahren), the lines for 10 % and 1 % failure probability, the estimate
of VDI 2736 Blatt 4 per load level, and the Gauss and Weibull nets on the normalised cycles as
the control of the distribution. Everything is written as sections 2.6 and 3.8 of the thesis
describe it:

- semi-logarithmic line (Hasl Gl. (51), S. 110, the representation of VDI 2736 Blatt 2):
  lg N_50% = a_c − b_c · T_2, least squares with lg N as the dependent variable;
- double-logarithmic line (DIN 50100 Gl. (30), S. 55, Basquin): lg N = lg C − k · lg L_a;
- pooled scatter (DIN 50100 Gl. (36), (38), (39), S. 56 to 57): the results shifted parallel to
  the line onto one fictitious horizon, which equals the residuals in lg N; two degrees of
  freedom lost; corrected by (n − 1,74)/(n − 2); bounded below by 0,10 (Hasl S. 118);
- N_PA = 10^(lg N_50% + u · s) (DIN 50100 Gl. (67), S. 63) with u = −1,282 for 10 % (Tabelle 11)
  and u = −2,33 for 1 % (Hasl S. 9, outside the range the norm covers);
- VDI 2736 Blatt 4 Gl. (10) to (15), S. 9 to 10: per level L_i,50 %, s_i, the normalised mean
  s̄ over the levels with repetitions, L_i,10 % = (1 − 1,28 s̄) L_i,50 %;
- nets: cycles normalised on the line of their level (Hasl S. 109 to 110), ranked, P_A after
  Rossow (MA-0296 Gl. (16), S. 34) and j/(n + 1) (Illenberger Gl. (19), S. 19); Gauss net
  lg x over u, Weibull net ln(−ln(1 − P)) over ln x;
- runouts: marked, never in the regression; the rule of DIN 50100 10.2.1 (S. 54) admits only
  results above the highest level with a runout. Both fits (rule and all failures) are given.

The failure criterion per point is carried along (total failure, failure noise, estimated
count) so that the figures can mark it; the Wöhler line is a line to breakage (ADR-118
amendment of 2026-10-18 evening).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from statistics import NormalDist
from typing import Literal

from gearcore.errors import InputRangeError
from gearcore.measurement.test_rig import TestRun
from gearcore.models.common import FrozenModel
from gearcore.trace import eq

DIN = "DIN50100:2022"
VDI4 = "VDI2736-4:2016"
"""Registry keys of the two sources with a verifiable identifier; Hasl 2018, Illenberger 2022
and MA-0296 are registered without one and therefore cited in docstrings only."""

QUANTILES: dict[int, float] = {1: -2.33, 10: -1.282, 50: 0.0, 90: 1.282}
"""u of the standard normal distribution per failure probability in %: DIN 50100 Tabelle 11
(S. 63) for 10, 50 and 90 %; 1 % as Hasl uses it (S. 9)."""
SCATTER_FLOOR = 0.10
"""Lower bound of s_lgN for the lines of small failure probability (Hasl S. 118)."""
VDI_FACTOR_10 = 1.28
"""VDI 2736 Blatt 4 Gl. (14)."""
EXCLUDED_FLAGS = ("planned_only", "no_cycles", "dry_room_temperature", "oil_45C")
"""Runs that give no point: planned rows, rows without a count, dry runs, oil far below 80 °C."""

EQ_EXEMPT = (
    "points_from_runs", "runout_rule", "normalised_cycles", "net_fit", "evaluate", "campaign",
    "semilog_fit", "rossow", "rank_estimate",
    "LineFit", "TestPoint", "LevelEstimate", "VdiEstimate", "NetFit", "WoehlerResult",
)


class TestPoint(FrozenModel):
    run_id: str
    material: str
    campaign: str
    """``KV3 2026`` or ``KV4 2023``."""
    wheel: str | None
    level_Nm: int
    load_Nm: float
    """Wheel torque of the workbook (column Q)."""
    cycles: int
    criterion: str
    estimated: bool = False
    runout: bool = False
    stepped: bool = False
    """A stepped run is shown as a marker and never enters the regression."""

    @property
    def lg_cycles(self) -> float:
        return math.log10(self.cycles)


class LineFit(FrozenModel):
    kind: Literal["semilog", "loglog"]
    intercept: float
    """a_c (semilog) or lg C (loglog)."""
    slope: float
    """b_c (semilog: lg N = a_c − b_c · L) or k (loglog: lg N = lg C − k · lg L)."""
    n: int
    s_lgN: float
    s_lgN_corr: float
    s_used: float
    """max(s_lgN_corr, SCATTER_FLOOR)."""
    load_min: float
    load_max: float
    """Range of the levels the fit covers; the line is drawn only in between (DIN 50100 S. 16)."""

    def lg_cycles_50(self, load: float) -> float:
        if load <= 0.0:
            raise InputRangeError(f"load must be positive, got {load}")
        if self.kind == "semilog":
            return self.intercept - self.slope * load
        return self.intercept - self.slope * math.log10(load)

    def cycles(self, load: float, probability_percent: int = 50) -> float:
        """N_PA for the failure probability in % (DIN 50100 Gl. (67))."""
        return cycles_at(self, load, probability_percent)


class LevelEstimate(FrozenModel):
    level_Nm: int
    load_Nm: float
    n: int
    cycles_measured: tuple[int, ...]
    N_50: float
    N_10: float
    N_1: float


class VdiEstimate(FrozenModel):
    level_Nm: int
    n_i: int
    L_i_50: float
    s_i: float | None
    """Standard deviation of the level; None for a single result."""
    N_i_50: float
    L_i_10: float | None
    """None where no level carries a repetition (s̄ undefined)."""
    N_i_10: float | None


class NetFit(FrozenModel):
    kind: Literal["gauss", "weibull"]
    estimator: Literal["rossow", "rank"]
    n: int
    slope: float
    """Of the transformed cycles over the transformed probability (Gauss: σ; Weibull: 1/k)."""
    intercept: float
    """Gauss: μ = lg of the normalised cycles at 50 %; Weibull: ln η."""
    r_squared: float
    parameter: float
    """Gauss: s_lgN of the normalised cycles; Weibull: the shape parameter k."""
    scale: float
    """Gauss: 10^μ (the normalised cycles at 50 %); Weibull: η (at 63,2 %)."""
    factor_10: float
    """N_10 % / N_50 % of the fitted distribution."""
    factor_1: float


class WoehlerResult(FrozenModel):
    material: str
    campaign: str
    points: tuple[TestPoint, ...]
    admitted: tuple[TestPoint, ...]
    """Points in the regression (no runouts, no stepped runs, the runout rule applied)."""
    semilog: LineFit
    loglog: LineFit
    levels: tuple[LevelEstimate, ...]
    vdi: tuple[VdiEstimate, ...]
    vdi_s_bar: float | None
    nets: tuple[NetFit, ...]
    all_failures: LineFit | None
    """The semi-logarithmic fit on every failure, where the runout rule removed points."""


def campaign(run: TestRun) -> str:
    year = (run.date or "")[:4] or "?"
    return f"{run.rig} {year}"


def points_from_runs(
    runs: Sequence[TestRun], *, material: str, rig: str | None = None
) -> list[TestPoint]:
    """Test points of a material (and rig) from the runs of the workbook; runs without a level or
    count, planned rows, dry runs and the first runs with oil far below 80 °C give no point."""
    points: list[TestPoint] = []
    for run in runs:
        if (run.material or "").strip().upper() != material.upper():
            continue
        if rig is not None and run.rig.upper() != rig.upper():
            continue
        if any(flag in run.flags for flag in EXCLUDED_FLAGS):
            continue
        if run.level_Nm is None or run.cycles is None or run.wheel_torque_Nm is None:
            continue
        points.append(TestPoint(
            run_id=run.run_id,
            material=material,
            campaign=campaign(run),
            wheel=run.wheel_me,
            level_Nm=run.level_Nm,
            load_Nm=run.wheel_torque_Nm,
            cycles=run.cycles,
            criterion=run.criterion,
            estimated="estimated_cycles" in run.flags,
            runout="Durchläufer" in run.criterion,
            stepped="stepped" in run.flags,
        ))
    return points


def _least_squares(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float]:
    """(intercept, slope) of y = intercept + slope · x."""
    n = len(xs)
    if n < 2:
        raise InputRangeError("a line needs at least two points")
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    sxx = sum((x - x_mean) ** 2 for x in xs)
    if sxx == 0.0:
        raise InputRangeError("a line needs at least two different loads")
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True)) / sxx
    return y_mean - slope * x_mean, slope


@eq(DIN, "(36)", section="10.2.2", page=56, note="shift onto a fictitious horizon = residual in lg N")
@eq(DIN, "(38)", section="10.2.2", page=56, note="two degrees of freedom lost")
@eq(DIN, "(39)", section="10.2.2", page=57,
    note="correction (n − 1,74)/(n − 2); the lower bound 0,10 follows Hasl 2018 S. 118")
def pooled_scatter(
    kind: Literal["semilog", "loglog"], intercept: float, slope: float,
    points: Sequence[TestPoint], *, scatter_floor: float = SCATTER_FLOOR,
) -> tuple[float, float, float]:
    """(s_lgN, s_lgN_corr, s_used) of the results around the line."""
    n = len(points)
    if n < 3:
        raise InputRangeError("the pooled scatter needs at least three results")
    residuals = []
    for p in points:
        x = p.load_Nm if kind == "semilog" else math.log10(p.load_Nm)
        residuals.append(p.lg_cycles - (intercept - slope * x))
    s = math.sqrt(sum(r * r for r in residuals) / (n - 2))
    s_corr = s * (n - 1.74) / (n - 2)
    return s, s_corr, max(s_corr, scatter_floor)


def semilog_fit(points: Sequence[TestPoint], *, scatter_floor: float = SCATTER_FLOOR) -> LineFit:
    """The semi-logarithmic line lg N_50% = a_c − b_c · L (Hasl 2018 Gl. (51), S. 110, with the
    wheel torque as L; the representation of VDI 2736 Blatt 2), lg N as the dependent
    variable. No ``@eq``: the dissertation carries no identifier the registry can verify."""
    a, m = _least_squares([p.load_Nm for p in points], [p.lg_cycles for p in points])
    s, s_corr, s_used = pooled_scatter("semilog", a, -m, points, scatter_floor=scatter_floor)
    loads = [p.load_Nm for p in points]
    return LineFit(kind="semilog", intercept=a, slope=-m, n=len(points), s_lgN=s,
                   s_lgN_corr=s_corr, s_used=s_used, load_min=min(loads), load_max=max(loads))


@eq(DIN, "(30)", section="10.2.2", page=55, note="Basquin: lg N = lg C − k · lg L_a")
def loglog_fit(points: Sequence[TestPoint], *, scatter_floor: float = SCATTER_FLOOR) -> LineFit:
    """The double-logarithmic line (slope k for the comparison with Stommel Tabelle 6.3)."""
    a, m = _least_squares([math.log10(p.load_Nm) for p in points], [p.lg_cycles for p in points])
    s, s_corr, s_used = pooled_scatter("loglog", a, -m, points, scatter_floor=scatter_floor)
    loads = [p.load_Nm for p in points]
    return LineFit(kind="loglog", intercept=a, slope=-m, n=len(points), s_lgN=s,
                   s_lgN_corr=s_corr, s_used=s_used, load_min=min(loads), load_max=max(loads))


@eq(DIN, "(67)", section="10.5", page=63,
    note="N_PA = 10^(lg N_50% + u · s_lgN,korr); Tabelle 11 for u; u = 2,33 for 1 % as Hasl 2018 Gl. (10) S. 9")
def cycles_at(fit: LineFit, load: float, probability_percent: int = 50) -> float:
    if probability_percent not in QUANTILES:
        raise InputRangeError(f"no quantile for {probability_percent} %; known: {sorted(QUANTILES)}")
    return math.pow(10.0, fit.lg_cycles_50(load) + QUANTILES[probability_percent] * fit.s_used)


@eq(VDI4, "(10)", section="4", page=9, note="L_ij = lg N_ij")
@eq(VDI4, "(11)", section="4", page=9, note="L_i,50% = mean over the n_i repetitions")
@eq(VDI4, "(12)", section="4", page=9, note="s_i with n_i − 1")
@eq(VDI4, "(13)", section="4", page=10, note="s̄ = mean of s_i / L_i,50% over the n_p pairs")
@eq(VDI4, "(14)", section="4", page=10, note="L_i,10% = (1 − 1,28 s̄) L_i,50%")
@eq(VDI4, "(15)", section="4", page=10, note="N_i,10% = 10^L_i,10%")
def vdi2736_levels(points: Sequence[TestPoint]) -> tuple[tuple[VdiEstimate, ...], float | None]:
    """The estimate of VDI 2736 Blatt 4 per level; s̄ over the levels with at least two results
    (None, and no 10 % values, where no level has a repetition)."""
    by_level: dict[int, list[TestPoint]] = {}
    for p in points:
        by_level.setdefault(p.level_Nm, []).append(p)
    means: dict[int, float] = {}
    deviations: dict[int, float | None] = {}
    for level, group in by_level.items():
        values = [p.lg_cycles for p in group]
        mean = sum(values) / len(values)
        means[level] = mean
        if len(values) >= 2:
            deviations[level] = math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))
        else:
            deviations[level] = None
    ratios = [s / means[level] for level, s in deviations.items() if s is not None]
    s_bar = sum(ratios) / len(ratios) if ratios else None
    out: list[VdiEstimate] = []
    for level in sorted(by_level):
        mean = means[level]
        l10 = (1.0 - VDI_FACTOR_10 * s_bar) * mean if s_bar is not None else None
        out.append(VdiEstimate(
            level_Nm=level, n_i=len(by_level[level]), L_i_50=mean, s_i=deviations[level],
            N_i_50=math.pow(10.0, mean), L_i_10=l10,
            N_i_10=math.pow(10.0, l10) if l10 is not None else None,
        ))
    return tuple(out), s_bar


def rossow(j: int, n: int) -> float:
    """P_A = (3j − 1)/(3n + 1) after Rossow, as MA-0296 Gl. (16) (S. 34) gives it; DIN 50100
    10.1 (S. 53) calls its results comparable with the corrected standard deviation."""
    if not 1 <= j <= n:
        raise InputRangeError(f"rank {j} outside 1..{n}")
    return (3.0 * j - 1.0) / (3.0 * n + 1.0)


def rank_estimate(j: int, n: int) -> float:
    """P_A = j/(n + 1), the rank estimate Illenberger 2022 uses (Gl. (19), S. 19)."""
    if not 1 <= j <= n:
        raise InputRangeError(f"rank {j} outside 1..{n}")
    return j / (n + 1.0)


def runout_rule(points: Sequence[TestPoint]) -> list[TestPoint]:
    """Points admitted to the regression after DIN 50100 10.2.1 (S. 54): no runouts, no
    stepped runs, and no failures at or below the highest level with a runout."""
    runout_levels = [p.load_Nm for p in points if p.runout]
    bound = max(runout_levels) if runout_levels else -math.inf
    return [p for p in points if not p.runout and not p.stepped and p.load_Nm > bound]


def normalised_cycles(fit: LineFit, points: Sequence[TestPoint]) -> list[tuple[TestPoint, float]]:
    """(point, N / N_50%(load)) sorted ascending (Hasl S. 109 to 110)."""
    pairs = [(p, p.cycles / fit.cycles(p.load_Nm)) for p in points]
    return sorted(pairs, key=lambda pair: pair[1])


def net_fit(
    values: Sequence[float], kind: Literal["gauss", "weibull"],
    estimator: Literal["rossow", "rank"] = "rossow",
) -> NetFit:
    """Straight line in the probability net over the sorted normalised cycles; in both nets the
    transformed cycles are the dependent variable (as lg N is in the regression of the norm):
    Gauss lg x = μ + σ · u, Weibull ln x = ln η + (1/k) · ln(−ln(1 − P))."""
    n = len(values)
    if n < 3:
        raise InputRangeError("a net needs at least three results")
    ordered = sorted(values)
    probabilities = [rossow(j, n) if estimator == "rossow" else rank_estimate(j, n)
                     for j in range(1, n + 1)]
    if kind == "gauss":
        xs = [NormalDist().inv_cdf(p) for p in probabilities]   # u
        ys = [math.log10(v) for v in ordered]                    # lg x
        intercept, slope = _least_squares(xs, ys)
        parameter, scale = slope, math.pow(10.0, intercept)
        factor_10 = math.pow(10.0, QUANTILES[10] * slope)
        factor_1 = math.pow(10.0, QUANTILES[1] * slope)
    else:
        xs = [math.log(-math.log(1.0 - p)) for p in probabilities]
        ys = [math.log(v) for v in ordered]                      # ln x
        intercept, slope = _least_squares(xs, ys)                # ln x = ln η + (1/k) · xs
        if slope <= 0.0:
            raise InputRangeError("the Weibull net gives no positive shape parameter")
        parameter = 1.0 / slope
        scale = math.exp(intercept)
        factor_10 = math.pow(math.log(1.0 / 0.9) / math.log(2.0), slope)
        factor_1 = math.pow(math.log(1.0 / 0.99) / math.log(2.0), slope)
    y_mean = sum(ys) / n
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys, strict=True))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else 1.0
    return NetFit(kind=kind, estimator=estimator, n=n, slope=slope, intercept=intercept,
                  r_squared=r2, parameter=parameter, scale=scale, factor_10=factor_10,
                  factor_1=factor_1)


def evaluate(points: Sequence[TestPoint], *, scatter_floor: float = SCATTER_FLOOR) -> WoehlerResult:
    """Both lines, the pooled scatter, the level estimates after DIN 50100 and VDI 2736 Blatt 4
    and the four nets for one material and campaign."""
    if not points:
        raise InputRangeError("no test points")
    materials = {p.material for p in points}
    campaigns = {p.campaign for p in points}
    if len(materials) != 1 or len(campaigns) != 1:
        raise InputRangeError(f"one material and campaign per evaluation, got {materials} {campaigns}")
    admitted = runout_rule(points)
    if len({p.level_Nm for p in admitted}) < 2 or len(admitted) < 3:
        raise InputRangeError("the regression needs at least three failures on two levels")
    semilog = semilog_fit(admitted, scatter_floor=scatter_floor)
    loglog = loglog_fit(admitted, scatter_floor=scatter_floor)
    failures = [p for p in points if not p.runout and not p.stepped]
    all_failures = semilog_fit(failures, scatter_floor=scatter_floor) if len(failures) > len(admitted) else None
    levels: list[LevelEstimate] = []
    for level in sorted({p.level_Nm for p in admitted}):
        group = [p for p in admitted if p.level_Nm == level]
        load = sum(p.load_Nm for p in group) / len(group)
        levels.append(LevelEstimate(
            level_Nm=level, load_Nm=load, n=len(group),
            cycles_measured=tuple(sorted(p.cycles for p in group)),
            N_50=semilog.cycles(load, 50), N_10=semilog.cycles(load, 10), N_1=semilog.cycles(load, 1),
        ))
    vdi, s_bar = vdi2736_levels(admitted)
    normalised = [value for _, value in normalised_cycles(semilog, admitted)]
    nets = tuple(
        net_fit(normalised, kind, estimator)
        for kind in ("gauss", "weibull") for estimator in ("rossow", "rank")
    )
    return WoehlerResult(
        material=points[0].material, campaign=points[0].campaign, points=tuple(points),
        admitted=tuple(admitted), semilog=semilog, loglog=loglog, levels=tuple(levels),
        vdi=vdi, vdi_s_bar=s_bar, nets=nets, all_failures=all_failures,
    )


__all__ = [
    "EXCLUDED_FLAGS",
    "QUANTILES",
    "SCATTER_FLOOR",
    "LevelEstimate",
    "LineFit",
    "NetFit",
    "TestPoint",
    "VdiEstimate",
    "WoehlerResult",
    "campaign",
    "cycles_at",
    "evaluate",
    "loglog_fit",
    "net_fit",
    "normalised_cycles",
    "points_from_runs",
    "pooled_scatter",
    "rank_estimate",
    "rossow",
    "runout_rule",
    "semilog_fit",
    "vdi2736_levels",
]
