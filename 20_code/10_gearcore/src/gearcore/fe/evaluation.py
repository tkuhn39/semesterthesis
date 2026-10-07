"""Evaluation of the extracted position results over the path of contact.

``scripts/fe_odb_extract.py`` (run by the Python of Abaqus after every job) writes one
``<job>_fields.json`` per position: the reference points, the closed contact nodes of the wheel
flank, the nodal averaged stresses of every root fillet surface and the head displacements.
This module reads those files, condenses one position into its maxima per tooth half and
fillet (``step_summary``), lines the positions of a folder up along the path of contact
(``path_points``, ``curve``), forms the nested sub-grids of a position grid (``grid_subset``)
and compares the location and the value of every maximum between the sub-grids
(``resolution_rows``): the resolution study of the mesh positions, which answers how many
positions per base pitch the batch needs so that the deformation does not shift the maxima by
a grid step (user, 2026-10-07). The location of a maximum is refined by the vertex of the
parabola through the largest point and its two neighbours, so that it does not snap to the
grid.
"""

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from gearcore.errors import InputRangeError, ParseError

EQ_EXEMPT = (
    "read_fields",
    "step_summary",
    "path_points",
    "curve",
    "grid_subset",
    "extremum",
    "resolution_rows",
    "format_summary",
    "format_resolution",
)
"""Reading of files and bookkeeping of maxima: no equation of a norm."""

FORMAT_VERSION = 1


@dataclass(frozen=True)
class ContactNode:
    n: int
    x: float
    y: float
    z: float
    r: float
    p: float
    f: float | None
    tooth: str
    side: str
    zone: str


@dataclass(frozen=True)
class FilletNode:
    n: int
    x: float
    y: float
    z: float
    r: float
    s1: float
    s3: float
    mises: float


@dataclass(frozen=True)
class FilletLayer:
    z: float
    s1: float
    n_s1: int
    r_s1: float
    s3: float
    n_s3: int
    r_s3: float


@dataclass(frozen=True)
class Fillet:
    name: str
    mid_width: tuple[FilletNode, ...]
    layers: tuple[FilletLayer, ...]
    nodes: tuple[FilletNode, ...] = ()
    """Every node of the fillet surface (width x arc), when the extraction stored them."""


@dataclass(frozen=True)
class Head:
    tooth: str
    u: float
    n: int
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class StepFields:
    name: str
    time: float
    wheel: Mapping[str, tuple[float, ...]]
    pinion: Mapping[str, tuple[float, ...]]
    history: Mapping[str, Mapping[str, float]]
    contact: tuple[ContactNode, ...]
    fillets: Mapping[str, Fillet]
    heads: Mapping[str, Head]


@dataclass(frozen=True)
class PositionFields:
    job: str
    wheel_axis: tuple[float, float]
    z_levels: tuple[float, ...]
    z_mid: float
    steps: tuple[StepFields, ...]


@dataclass(frozen=True)
class ToothContact:
    """Contact of one tooth half: closed nodes, the largest pressure with its node, and the
    normal force summed over the nodes (None when CFORCE was not in the output request)."""

    tooth: str
    side: str
    nodes: int
    p_max: float
    at: ContactNode
    force: float | None


@dataclass(frozen=True)
class FilletExtreme:
    name: str
    s1_max: float
    s1_layer: FilletLayer
    s3_min: float
    s3_layer: FilletLayer


@dataclass(frozen=True)
class StepSummary:
    name: str
    pinion_rotation_rad: float | None
    wheel_moment_nmm: float | None
    teeth: tuple[ToothContact, ...]
    p_max: float
    p_max_at: ContactNode | None
    fillets: tuple[FilletExtreme, ...]
    s1_max: float
    s1_max_fillet: FilletExtreme | None
    s3_min: float
    s3_min_fillet: FilletExtreme | None
    u_head_max: float
    u_head_tooth: str


def _float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ParseError(f"{name}: expected a number, got {value!r}")
    return float(value)


def _node(item: Mapping[str, object]) -> ContactNode:
    force = item.get("f")
    return ContactNode(
        n=int(_float(item["n"], "n")),
        x=_float(item["x"], "x"),
        y=_float(item["y"], "y"),
        z=_float(item["z"], "z"),
        r=_float(item["r"], "r"),
        p=_float(item["p"], "p"),
        f=None if force is None else _float(force, "f"),
        tooth=str(item.get("tooth", "")),
        side=str(item.get("side", "")),
        zone=str(item.get("zone", "")),
    )


def _fillet_node(m: Mapping[str, object]) -> FilletNode:
    return FilletNode(
        n=int(_float(m["n"], "n")),
        x=_float(m["x"], "x"),
        y=_float(m["y"], "y"),
        z=_float(m["z"], "z"),
        r=_float(m["r"], "r"),
        s1=_float(m["s1"], "s1"),
        s3=_float(m["s3"], "s3"),
        mises=_float(m["mises"], "mises"),
    )


def _fillet(name: str, item: Mapping[str, object]) -> Fillet:
    mid = item.get("mid_width", [])
    layers = item.get("layers", [])
    nodes = item.get("nodes", [])
    if not isinstance(mid, list) or not isinstance(layers, list) or not isinstance(nodes, list):
        raise ParseError(f"fillet {name}: mid_width, layers and nodes must be lists")
    return Fillet(
        name=name,
        mid_width=tuple(_fillet_node(m) for m in mid),
        nodes=tuple(_fillet_node(m) for m in nodes),
        layers=tuple(
            FilletLayer(
                z=_float(ly["z"], "z"),
                s1=_float(ly["s1"], "s1"),
                n_s1=int(_float(ly["n_s1"], "n_s1")),
                r_s1=_float(ly["r_s1"], "r_s1"),
                s3=_float(ly["s3"], "s3"),
                n_s3=int(_float(ly["n_s3"], "n_s3")),
                r_s3=_float(ly["r_s3"], "r_s3"),
            )
            for ly in layers
        ),
    )


def _vectors(item: object) -> dict[str, tuple[float, ...]]:
    if not isinstance(item, dict):
        return {}
    return {str(k): tuple(_float(c, k) for c in v) for k, v in item.items() if isinstance(v, list)}


def read_fields(path: Path) -> PositionFields:
    """The extracted results of one position (``<job>_fields.json``)."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ParseError(f"{path}: {error}") from error
    if not isinstance(document, dict) or document.get("format") != FORMAT_VERSION:
        raise ParseError(f"{path}: not a fields file of format {FORMAT_VERSION}")
    steps = []
    for raw in document.get("steps", []):
        reference = raw.get("reference_points", {})
        history = {
            str(k): {str(n): _float(x, n) for n, x in v.items()}
            for k, v in raw.get("history", {}).items()
            if isinstance(v, dict)
        }
        steps.append(
            StepFields(
                name=str(raw["name"]),
                time=_float(raw.get("time", 0.0), "time"),
                wheel=_vectors(reference.get("wheel")),
                pinion=_vectors(reference.get("pinion")),
                history=history,
                contact=tuple(_node(c) for c in raw.get("contact", [])),
                fillets={str(k): _fillet(str(k), v) for k, v in raw.get("fillets", {}).items()},
                heads={
                    str(k): Head(
                        tooth=str(k),
                        u=_float(v["u"], "u"),
                        n=int(_float(v["n"], "n")),
                        x=_float(v["x"], "x"),
                        y=_float(v["y"], "y"),
                        z=_float(v["z"], "z"),
                    )
                    for k, v in raw.get("heads", {}).items()
                },
            )
        )
    axis = document.get("wheel_axis", [0.0, 0.0])
    return PositionFields(
        job=path.name.removesuffix("_fields.json"),
        wheel_axis=(_float(axis[0], "axis"), _float(axis[1], "axis")),
        z_levels=tuple(_float(z, "z") for z in document.get("z_levels", [])),
        z_mid=_float(document.get("z_mid", 0.0), "z_mid"),
        steps=tuple(steps),
    )


def _rotation(step: StepFields) -> float | None:
    ur = step.pinion.get("UR")
    if ur is not None and len(ur) == 3:
        return ur[2]
    return step.history.get("pinion", {}).get("UR3")


def _moment(step: StepFields) -> float | None:
    rm = step.wheel.get("RM")
    if rm is not None and len(rm) == 3:
        return rm[2]
    return step.history.get("wheel", {}).get("RM3")


def step_summary(step: StepFields) -> StepSummary:
    """The maxima of one step: per tooth half the largest contact pressure and the normal
    force, per fillet the largest tensile and the most compressive principal stress with their
    layer, the largest head displacement; plus rotation of the pinion and moment at the wheel."""
    teeth: list[ToothContact] = []
    by_half: dict[tuple[str, str], list[ContactNode]] = {}
    for node in step.contact:
        by_half.setdefault((node.tooth, node.side), []).append(node)
    for (tooth, side), nodes in sorted(by_half.items()):
        forces = [n.f for n in nodes]
        force = None if any(f is None for f in forces) else sum(f for f in forces if f is not None)
        best = max(nodes, key=lambda n: n.p)
        teeth.append(ToothContact(tooth, side, len(nodes), best.p, best, force))
    p_at = max(step.contact, key=lambda n: n.p, default=None)
    extremes: list[FilletExtreme] = []
    for name, fillet in sorted(step.fillets.items()):
        if not fillet.layers:
            continue
        top = max(fillet.layers, key=lambda ly: ly.s1)
        bottom = min(fillet.layers, key=lambda ly: ly.s3)
        extremes.append(FilletExtreme(name, top.s1, top, bottom.s3, bottom))
    s1_fillet = max(extremes, key=lambda f: f.s1_max, default=None)
    s3_fillet = min(extremes, key=lambda f: f.s3_min, default=None)
    head = max(step.heads.values(), key=lambda h: h.u, default=None)
    return StepSummary(
        name=step.name,
        pinion_rotation_rad=_rotation(step),
        wheel_moment_nmm=_moment(step),
        teeth=tuple(teeth),
        p_max=p_at.p if p_at else 0.0,
        p_max_at=p_at,
        fillets=tuple(extremes),
        s1_max=s1_fillet.s1_max if s1_fillet else 0.0,
        s1_max_fillet=s1_fillet,
        s3_min=s3_fillet.s3_min if s3_fillet else 0.0,
        s3_min_fillet=s3_fillet,
        u_head_max=head.u if head else 0.0,
        u_head_tooth=head.tooth if head else "",
    )


@dataclass(frozen=True)
class PathPoint:
    """One mesh position of a folder with the summaries of its steps (empty when the
    position has no extracted fields yet)."""

    index: int
    label: str
    from_a_mm: float
    rho_1_mm: float
    job: str
    summaries: Mapping[str, StepSummary]


def path_points(manifest: Mapping[str, object], folder: Path) -> tuple[PathPoint, ...]:
    """The positions of a folder along the path of contact with their extracted results."""
    positions = manifest.get("positions")
    if not isinstance(positions, list):
        raise ParseError("manifest without positions")
    points = []
    for entry in positions:
        job = Path(str(entry["file"])).stem
        fields_file = folder / f"{job}_fields.json"
        summaries: dict[str, StepSummary] = {}
        if fields_file.exists():
            fields = read_fields(fields_file)
            summaries = {step.name: step_summary(step) for step in fields.steps}
        points.append(
            PathPoint(
                index=int(_float(entry["index"], "index")),
                label=str(entry.get("point") or ""),
                from_a_mm=_float(entry["from_A_mm"], "from_A_mm"),
                rho_1_mm=_float(entry["rho_1_mm"], "rho_1_mm"),
                job=job,
                summaries=summaries,
            )
        )
    points.sort(key=lambda p: p.from_a_mm)
    return tuple(points)


QUANTITIES = (
    "pinion_rotation_rad",
    "p_max",
    "s1_max",
    "s3_min",
    "u_head_max",
)
"""Quantities of a step summary that ``curve`` lines up over the path of contact; a tooth
half's force or pressure is addressed as ``force:T3_RIGHT`` / ``p:T3_RIGHT``."""


def _quantity(summary: StepSummary, quantity: str) -> float | None:
    if quantity in QUANTITIES:
        value = getattr(summary, quantity)
        return None if value is None else float(value)
    kind, _, half = quantity.partition(":")
    for tooth in summary.teeth:
        if f"{tooth.tooth}_{tooth.side}" == half:
            if kind == "force":
                return tooth.force
            if kind == "p":
                return tooth.p_max
            raise InputRangeError(f"unknown quantity kind {kind!r}")
    if kind in ("force", "p") and half:
        return 0.0
    raise InputRangeError(f"unknown quantity {quantity!r}")


def curve(
    points: Sequence[PathPoint], step_name: str, quantity: str
) -> tuple[tuple[float, float], ...]:
    """(from_A, value) over the positions that have the step; rotations and moments are
    taken by magnitude, so that every curve has a maximum to locate."""
    out = []
    for point in points:
        summary = point.summaries.get(step_name)
        if summary is None:
            continue
        value = _quantity(summary, quantity)
        if value is None:
            continue
        if quantity in ("pinion_rotation_rad", "s3_min"):
            value = abs(value)
        out.append((point.from_a_mm, value))
    return tuple(out)


def grid_subset(
    points: Sequence[PathPoint],
    steps_per_pitch: int,
    base_pitch_mm: float,
    margin_pitches: float,
    factor: int,
) -> tuple[PathPoint, ...]:
    """Every ``factor``-th point of the grid (the grid starts ``margin_pitches`` before A with
    the step ``base_pitch_mm / steps_per_pitch``); the named points A to E are always kept."""
    if factor < 1 or steps_per_pitch < 1 or base_pitch_mm <= 0.0:
        raise InputRangeError("factor and steps per pitch must be positive, the pitch too")
    step = base_pitch_mm / steps_per_pitch
    kept = []
    for point in points:
        # grid index of the point, divided by the factor: kept when the remainder is a whole
        # number of factors (no rounding of a result, only a tolerance test on the remainder)
        index_float = (point.from_a_mm + margin_pitches * base_pitch_mm) / step
        remainder = math.fmod(index_float, float(factor))
        on_subgrid = min(abs(remainder), abs(abs(remainder) - factor)) < 1.0e-6
        if point.label or on_subgrid:
            kept.append(point)
    return tuple(kept)


def extremum(values: Sequence[tuple[float, float]]) -> tuple[float, float] | None:
    """Location and value of the largest point of a curve: the location refined by the vertex
    of the parabola through it and its two neighbours when both exist and the parabola is
    concave, the value the measured maximum itself (a parabola through a cusp would
    overshoot); None for an empty curve."""
    if not values:
        return None
    ordered = sorted(values)
    k = max(range(len(ordered)), key=lambda i: ordered[i][1])
    x0, y0 = ordered[k]
    if 0 < k < len(ordered) - 1:
        (xl, yl), (xr, yr) = ordered[k - 1], ordered[k + 1]
        denominator = (xl - x0) * (xl - xr) * (x0 - xr)
        if denominator != 0.0:
            a = (xr * (y0 - yl) + x0 * (yl - yr) + xl * (yr - y0)) / denominator
            b = (xr * xr * (yl - y0) + x0 * x0 * (yr - yl) + xl * xl * (y0 - yr)) / denominator
            if a < 0.0:
                xv = -b / (2.0 * a)
                if min(xl, xr) <= xv <= max(xl, xr):
                    return xv, y0
    return x0, y0


@dataclass(frozen=True)
class ResolutionRow:
    steps_per_pitch: int
    positions: int
    quantity: str
    location_mm: float
    value: float
    shift_mm: float
    change: float
    """Change of the value against the finest grid, as a fraction."""


def resolution_rows(
    points: Sequence[PathPoint],
    step_name: str,
    quantities: Iterable[str],
    steps_per_pitch: int,
    base_pitch_mm: float,
    margin_pitches: float,
    factors: Sequence[int] = (1, 2, 3, 4, 5, 6),
) -> tuple[ResolutionRow, ...]:
    """For every sub-grid (steps per pitch divided by the factor) and quantity: location and
    value of the maximum and their shift and change against the finest grid."""
    rows: list[ResolutionRow] = []
    finest: dict[str, tuple[float, float]] = {}
    for factor in factors:
        if factor < 1 or steps_per_pitch % factor != 0:
            raise InputRangeError(f"{steps_per_pitch} steps per pitch do not divide by {factor}")
        sub_steps = next(s for s in range(1, steps_per_pitch + 1) if s * factor == steps_per_pitch)
        subset = grid_subset(points, steps_per_pitch, base_pitch_mm, margin_pitches, factor)
        for quantity in quantities:
            peak = extremum(curve(subset, step_name, quantity))
            if peak is None or (quantity not in finest and peak[1] == 0.0):
                continue  # no curve, or a quantity without data (all zero) on the finest grid
            reference = finest.setdefault(quantity, peak)
            change = (peak[1] / reference[1] - 1.0) if reference[1] != 0.0 else 0.0
            rows.append(
                ResolutionRow(
                    steps_per_pitch=sub_steps,
                    positions=len(subset),
                    quantity=quantity,
                    location_mm=peak[0],
                    value=peak[1],
                    shift_mm=peak[0] - reference[0],
                    change=change,
                )
            )
    return tuple(rows)


def format_summary(summary: StepSummary) -> list[str]:
    """Lines of one step summary for the report."""
    lines = []
    for tooth in summary.teeth:
        at = tooth.at
        force = f", normal force {tooth.force:.1f} N" if tooth.force is not None else ""
        lines.append(
            f"    {tooth.tooth} {tooth.side}: {tooth.nodes} closed nodes, CPRESS max "
            f"{tooth.p_max:.2f} MPa at r {at.r:.3f} mm, z {at.z:+.3f} mm ({at.zone.lower()}){force}"
        )
    for fillet in summary.fillets:
        lines.append(
            f"    fillet {fillet.name}: s1 max {fillet.s1_max:.2f} MPa (z {fillet.s1_layer.z:+.3f}, "
            f"r {fillet.s1_layer.r_s1:.3f}), s3 min {fillet.s3_min:.2f} MPa "
            f"(z {fillet.s3_layer.z:+.3f}, r {fillet.s3_layer.r_s3:.3f})"
        )
    lines.append(
        f"    largest head displacement {summary.u_head_max * 1000:.1f} um ({summary.u_head_tooth})"
    )
    return lines


def _format_number(value: float) -> str:
    return f"{value:.4e}" if abs(value) < 1.0e-2 or abs(value) >= 1.0e4 else f"{value:.3f}"


def format_resolution(rows: Sequence[ResolutionRow]) -> list[str]:
    """Markdown table of the resolution study."""
    lines = [
        "| steps per pitch | positions | quantity | location from A in mm | value "
        "| shift vs finest in mm | change vs finest |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.steps_per_pitch} | {row.positions} | {row.quantity} | {row.location_mm:.3f} | "
            f"{_format_number(row.value)} | {row.shift_mm:+.3f} | {row.change * 100:+.2f} % |"
        )
    return lines


__all__ = [
    "ContactNode",
    "Fillet",
    "FilletExtreme",
    "FilletLayer",
    "FilletNode",
    "Head",
    "PathPoint",
    "PositionFields",
    "QUANTITIES",
    "ResolutionRow",
    "StepFields",
    "StepSummary",
    "ToothContact",
    "curve",
    "extremum",
    "format_resolution",
    "format_summary",
    "grid_subset",
    "path_points",
    "read_fields",
    "resolution_rows",
    "step_summary",
]
