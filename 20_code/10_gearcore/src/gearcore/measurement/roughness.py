"""Roughness of the tooth flanks from the Hommel-Etamic ASCII exports: one export per gear and
flank with three traces (``Messung-1`` to ``Messung-3``) of fifteen parameters each and the
instrument's means ``Xq-Ra``, ``Xq-Rz``, ``Xq-Rmax``; the printed PDFs are the protocols for
the appendix (user's decision of 2026-10-10: no roughness analysis in the house style, the raw
data only have to be used correctly).

R_a (``arithmetic_mean_roughness``) and R_z (``mean_peak_to_valley_roughness``) are the
registry quantities of ISO/TR 6336-30; every other parameter (R_max, R_q, R_sk, R_t, R_p,
R_zISO, W_t, RΔq, R_pk, R_k, R_vk, A1, A2) is passed through raw under the instrument's name,
because its defining norm is not in the repository (MEAS-05). The instrument's mean of the
three traces is cross-checked against the traces (``ParseError`` where it differs by more than
the printed decimals), the duplicate exports (``_neu_`` files, equal numbers) are dropped
(``dedupe``), and the statistics over parts follow ``gina.scatter_table``.
"""

import datetime as dt
import math
from collections.abc import Sequence
from typing import Literal

from gearcore.errors import InputRangeError, ParseError
from gearcore.io.hommel import RoughnessTable
from gearcore.io.p40 import Flank
from gearcore.models.common import FrozenModel

EQ_EXEMPT = ("mean_tolerance_um", "roughness_measurements", "dedupe", "trace_spread", "statistics")
"""Assembly and statistics: no equation of a norm."""

TRACES = ("Messung-1", "Messung-2", "Messung-3")
MEAN_COLUMNS: dict[str, str] = {"Ra": "Xq-Ra", "Rz": "Xq-Rz", "Rmax": "Xq-Rmax"}
"""Instrument parameter → the column of its mean over the three traces."""
REGISTRY_NAMES: dict[str, str] = {
    "Ra": "arithmetic_mean_roughness",
    "Rz": "mean_peak_to_valley_roughness",
}
"""Instrument parameters with a registry entry; the others stay raw."""
FLANKS: dict[str, Flank] = {"li": "links", "re": "rechts"}
TRACE_DECIMALS = 3
"""The traces are printed with three decimals; the means with the decimals of their column."""


def mean_tolerance_um(decimals: int) -> float:
    """How far the printed mean may lie from the mean of the printed traces: half a unit of its
    last digit plus half a unit of the last digit of the traces."""
    return 0.5 * 10.0 ** (-decimals) + 0.5 * 10.0 ** (-TRACE_DECIMALS) + 1.0e-9


Parameter = Literal["Ra", "Rz", "Rmax"]


class RoughnessMeasurement(FrozenModel):
    """One export: a gear flank with three traces and the instrument's means."""

    me: str
    flank: Flank
    measured_on: str
    """ISO date."""
    measured_at: str
    """``HH:MM:SS``."""
    remark: str | None
    program: str
    """Title line of the export (cut-off, traversing length, probe)."""
    R_a_traces_um: tuple[float, float, float]
    R_z_traces_um: tuple[float, float, float]
    R_a_um: float
    """Mean of the three traces as the instrument prints it (``Xq-Ra``)."""
    R_z_um: float
    R_max_um: float
    """``Xq-Rmax``, raw (no registry entry)."""
    raw: tuple[tuple[str, float], ...]
    """Every numeric column as printed, by the instrument's name."""

    def value(self, column: str) -> float:
        for name, number in self.raw:
            if name == column:
                return number
        raise InputRangeError(f"no column {column!r} in the export of {self.me} {self.flank}")

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.me, self.flank, self.measured_on, self.measured_at)


def _traces(record_value: dict[str, float], parameter: str) -> tuple[float, float, float]:
    try:
        values = tuple(record_value[f"{trace}.{parameter}"] for trace in TRACES)
    except KeyError as missing:
        raise ParseError(f"export without the column {missing.args[0]!r}") from None
    return values[0], values[1], values[2]


def _check_mean(parameter: str, traces: Sequence[float], printed: float, decimals: int) -> None:
    mean = sum(traces) / len(traces)
    if abs(mean - printed) > mean_tolerance_um(decimals):
        raise ParseError(
            f"{MEAN_COLUMNS[parameter]} {printed} is not the mean of the traces {tuple(traces)} "
            f"({mean:.4f})"
        )


def _printed_decimals(table: RoughnessTable, column: str) -> int:
    """Decimals the export prints for a column (the traces' three where the line is short)."""
    value = dict(table.decimals).get(column)
    return TRACE_DECIMALS if value is None else value


def roughness_measurements(table: RoughnessTable) -> tuple[RoughnessMeasurement, ...]:
    """Every record of an export as a typed measurement, the instrument's means cross-checked
    against the traces."""
    out: list[RoughnessMeasurement] = []
    for record in table.records:
        numbers = dict(record.numbers)
        flank_code = record.flank
        if flank_code not in FLANKS:
            raise ParseError(f"unknown flank code {flank_code!r} (expected li or re)")
        r_a = _traces(numbers, "Ra")
        r_z = _traces(numbers, "Rz")
        for parameter in MEAN_COLUMNS:
            if MEAN_COLUMNS[parameter] not in numbers:
                raise ParseError(f"export without the column {MEAN_COLUMNS[parameter]!r}")
        _check_mean("Ra", r_a, numbers["Xq-Ra"], _printed_decimals(table, "Xq-Ra"))
        _check_mean("Rz", r_z, numbers["Xq-Rz"], _printed_decimals(table, "Xq-Rz"))
        _check_mean(
            "Rmax",
            _traces(numbers, "Rmax"),
            numbers["Xq-Rmax"],
            _printed_decimals(table, "Xq-Rmax"),
        )
        try:
            stamp = dt.datetime.strptime(record.measured_at, "%d.%m.%Y/%H:%M:%S")
        except ValueError:
            raise ParseError(
                f"timestamp {record.measured_at!r} is not dd.mm.yyyy/HH:MM:SS"
            ) from None
        out.append(
            RoughnessMeasurement(
                me=record.me,
                flank=FLANKS[flank_code],
                measured_on=stamp.date().isoformat(),
                measured_at=stamp.time().isoformat(),
                remark=record.remark,
                program=table.title,
                R_a_traces_um=r_a,
                R_z_traces_um=r_z,
                R_a_um=numbers["Xq-Ra"],
                R_z_um=numbers["Xq-Rz"],
                R_max_um=numbers["Xq-Rmax"],
                raw=tuple(record.numbers),
            )
        )
    return tuple(out)


def dedupe(
    measurements: Sequence[RoughnessMeasurement],
) -> tuple[tuple[RoughnessMeasurement, ...], tuple[RoughnessMeasurement, ...]]:
    """(kept, dropped): a later measurement with the same gear, flank and timestamp and the same
    numbers is a duplicate export and is dropped; the same key with different numbers is an
    error (two exports of one measurement cannot disagree)."""
    kept: list[RoughnessMeasurement] = []
    dropped: list[RoughnessMeasurement] = []
    seen: dict[tuple[str, str, str, str], RoughnessMeasurement] = {}
    for measurement in measurements:
        first = seen.get(measurement.key)
        if first is None:
            seen[measurement.key] = measurement
            kept.append(measurement)
        elif first.raw == measurement.raw:
            dropped.append(measurement)
        else:
            raise ParseError(
                f"{measurement.me} {measurement.flank} {measurement.measured_at}: two exports of one "
                "measurement with different numbers"
            )
    return tuple(kept), tuple(dropped)


def trace_spread(measurement: RoughnessMeasurement, parameter: Parameter = "Ra") -> float:
    """Largest minus smallest value of the three traces (µm)."""
    traces = measurement.R_a_traces_um if parameter == "Ra" else measurement.R_z_traces_um
    if parameter == "Rmax":
        traces = (
            measurement.value("Messung-1.Rmax"),
            measurement.value("Messung-2.Rmax"),
            measurement.value("Messung-3.Rmax"),
        )
    return max(traces) - min(traces)


class RoughnessStatistics(FrozenModel):
    """Spread of one parameter over the parts of a group, per flank."""

    parameter: str
    quantity: str | None
    flank: Flank
    count: int
    mean_um: float
    standard_deviation_um: float
    minimum_um: float
    maximum_um: float
    me_of_minimum: str
    me_of_maximum: str
    mean_trace_spread_um: float
    """Mean over the parts of the spread of the three traces: the scatter along one flank."""


def statistics(measurements: Sequence[RoughnessMeasurement]) -> tuple[RoughnessStatistics, ...]:
    """Mean, sample standard deviation, minimum and maximum of R_a and R_z per flank over the
    measurements given (one per part and flank: ``dedupe`` first)."""
    if not measurements:
        raise InputRangeError("no measurements")
    out: list[RoughnessStatistics] = []
    for parameter in ("Ra", "Rz"):
        flanks: tuple[Flank, ...] = ("links", "rechts")
        for flank in flanks:
            rows = [m for m in measurements if m.flank == flank]
            if not rows:
                continue
            values = [m.R_a_um if parameter == "Ra" else m.R_z_um for m in rows]
            n = len(values)
            mean = sum(values) / n
            sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1)) if n > 1 else 0.0
            low = min(zip(values, rows, strict=True), key=lambda pair: pair[0])
            high = max(zip(values, rows, strict=True), key=lambda pair: pair[0])
            spreads = [trace_spread(m, parameter) for m in rows]
            out.append(
                RoughnessStatistics(
                    parameter=parameter,
                    quantity=REGISTRY_NAMES.get(parameter),
                    flank=flank,
                    count=n,
                    mean_um=mean,
                    standard_deviation_um=sd,
                    minimum_um=low[0],
                    maximum_um=high[0],
                    me_of_minimum=low[1].me,
                    me_of_maximum=high[1].me,
                    mean_trace_spread_um=sum(spreads) / n,
                )
            )
    return tuple(out)


__all__ = [
    "EQ_EXEMPT",
    "FLANKS",
    "MEAN_COLUMNS",
    "TRACE_DECIMALS",
    "REGISTRY_NAMES",
    "TRACES",
    "RoughnessMeasurement",
    "RoughnessStatistics",
    "dedupe",
    "mean_tolerance_um",
    "roughness_measurements",
    "statistics",
    "trace_spread",
]
