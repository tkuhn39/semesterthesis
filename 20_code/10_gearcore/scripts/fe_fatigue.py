"""Design check of the FE positions after Stommel, Stojek, Korte (2018), chapter 6 (track E).

    uv run --all-extras python scripts/fe_fatigue.py stommel --folder DIR [--step LOAD_16NM ...]
        [--series W1] [--material pa46_gf30_qs] [--load-case einmalig] [--case 2]
        [--route principal] [--cycles 1e7] [--safety 1] [--top 12] [--out DIR] [--no-plots]
        [--equivalent mises|hill --cof FILE]
    uv run --all-extras python scripts/fe_fatigue.py curves [--material NAME ...]
        [--load-case einmalig] [--out DIR]

``stommel`` assembles, for every node of the wheel, the history over the mesh cycle from the
stress files ``pos_*_stress.npz`` of one series and load step of a folder (the unloaded state
plus every complete position), runs the static and the cyclic check (``gearcore.fatigue.check``)
and writes below ``<folder>/stommel`` (or ``--out``): ``bericht_<step>.md`` (settings, the
material side of the nomogram, the positions used and skipped, the critical nodes of both checks
with their chain of values, the nodes above one, the largest utilisations per fillet),
``knoten_<step>.csv`` (every node with its coordinates in the part frame, its zone, h, σ_V,
a_stat, σ_a, σ_m, K_M, σ_B, a_B,V, N_pred and flag) and the figures ``karte_<step>_<fillet>``
(a_B,V over the fillet surface of the critical fillet, face width over the arc) and
``verlauf_<step>`` (a_stat and a_B,V over the position of the critical nodes).

``curves`` draws the method figures of the material cards (all four by default: the linear
card and the rates QS, DY1, DY2 of Stanyl TW200F6) "in Anlehnung an [Sto18]" in the house
style, lines only and with the same axis limits per figure family (the maximum over all cards):
the stress-strain curves of every direction (``spannung_dehnung_<card>``), the nomogram with K,
the reduction factors and A_W transferred to the service isotherm (``nomogramm_<card>``), the
Haigh diagram as Matscape draws it at both temperatures (``haigh_<card>_<T>C``), the synthetic
Wöhler line with a linear amplitude axis and markers at the decades
(``woehler_synthetisch_<card>``), the orientation states of the CONVERSE card beside the measured
directions (``orientierungszustaende_<card>``, the own extension E7) and the comparison of the
reference curves of all cards; ``bildunterschriften.md`` carries the captions with the relation
to the source and the limits used.

Everything that computes lives in ``gearcore.fatigue``; this script reads the folder, calls the
package, draws (``gearcore.plot_style``) and writes files (gitignored output).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from gearcore.errors import InputRangeError
from gearcore.fatigue import anisotropy as an
from gearcore.fatigue import check as ck
from gearcore.fatigue import materials as mt
from gearcore.fatigue import stommel as st
from gearcore.fe import stress as sf
from gearcore.io.matscape import StressStrainCurve
from gearcore.plot_style import (
    DEGREE_COLOURMAP,
    caption,
    decimal_comma,
    figure_size,
    german_number,
    legend_outside,
    new_figure,
)
from gearcore.plot_style import apply as apply_plot_style
from gearcore.plot_style import save as save_figure

REPO = Path(__file__).resolve().parents[3]
Array = npt.NDArray[np.float64]
DEFAULT_MATERIAL = "pa46_gf30_qs"
HILL_DEFAULT_CLASS = "semi_crystalline_unreinforced"
"""Reduction factors under the Hill extension (user 2026-10-11): the anisotropy is in the
ratios of the card, so the lump-sum factors of the reinforced class are not applied again."""
SOURCE_LABEL = "Sto18"
SHEET = apply_plot_style()


# --- helpers --------------------------------------------------------------------------------------


def _g(value: float, digits: int = 3) -> str:
    if math.isinf(value):
        return "∞"
    return german_number(value, digits)


def _manifest(folder: Path) -> dict[str, Any]:
    path = folder / "manifest.json"
    if not path.is_file():
        raise InputRangeError(f"{folder}: no manifest.json")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise InputRangeError(f"{path}: not a manifest")
    return loaded


def _load_steps(manifest: dict[str, Any]) -> list[str]:
    names = manifest.get("step_names")
    if not isinstance(names, list):
        return []
    return [str(n) for n in names if str(n).startswith("LOAD_")]


def _zones(file: sf.StressFile) -> list[str]:
    """Zone of every node from the node sets: fillet set, flank, head or rim."""
    zone = ["rim"] * file.n_nodes
    index = file.index_of(file.node_labels)
    lookup = {int(label): int(i) for label, i in zip(file.node_labels, index, strict=True)}
    for name, labels in file.sets.items():
        if name.startswith("WHEEL_T") and "_SURF_" in name and name.endswith("_NODES"):
            tag = (
                "flank"
                if "FLANK" in name
                else name.split("_SURF_")[1].removesuffix("_NODES").lower()
            )
            for label in labels:
                zone[lookup[int(label)]] = f"{name.split('_')[1]} {tag}"
    for name, labels in file.sets.items():
        if name.startswith("WHEEL_HEAD_T"):
            for label in labels:
                zone[lookup[int(label)]] = name.split("_")[2] + " head"
    for name, labels in file.sets.items():
        if name.startswith("WHEEL_ROOT_T") and name.endswith("_SURF_NODES"):
            parts = name.split("_")
            for label in labels:
                zone[lookup[int(label)]] = f"fillet {parts[2]}_{parts[3]}"
    return zone


def _fillet_of(zone: str) -> str | None:
    return zone.removeprefix("fillet ") if zone.startswith("fillet ") else None


MATERIAL_STEP_TEXT = {
    "W1": "W1 linear-elastisch, isotrop",
    "W2": "W2 elastisch-plastisch, isotrop",
    "W3": "W3 linear-elastisch, anisotrop",
    "W4": "W4 elastisch-plastisch, anisotrop",
}
RATE_TEXT = {"QS": "quasistatisch", "DY1": "Dehnrate 3 s$^{-1}$", "DY2": "Dehnrate 60 s$^{-1}$"}
STEP_TEXT = {"LOAD_8NM": "8 Nm", "LOAD_12NM": "12 Nm", "LOAD_16NM": "16 Nm"}


def _zone_text(zone: str) -> str:
    """The zone of a node in the words of the figures: ``'fillet T3_T4'`` -> ``'Fußrundung
    T3/T4'``, ``'T3 head'`` -> ``'Zahnkopf T3'``, ``'rim'`` (the remainder label of ``_zones``:
    every node outside the fillet, head and surface sets, FE-22) -> ``'ohne Satz'``."""
    if zone.startswith("fillet "):
        return "Fußrundung " + zone.removeprefix("fillet ").replace("_", "/")
    if zone.endswith(" head"):
        return "Zahnkopf " + zone.removesuffix(" head")
    if zone == "rim":
        return "ohne Satz (Flanke oder Körper)"
    if zone == "TEETH nodes":
        return "Zahnoberfläche"
    return zone


def _series_title(series: str | None, step: str) -> str:
    """``'W2_QS', 'LOAD_8NM'`` -> ``'W2 elastisch-plastisch, isotrop, quasistatisch, 8 Nm'``."""
    parts: list[str] = []
    if series:
        material, _, rate = series.partition("_")
        parts.append(MATERIAL_STEP_TEXT.get(material, material))
        if rate:
            parts.append(RATE_TEXT.get(rate, rate))
    parts.append(STEP_TEXT.get(step, step))
    return ", ".join(parts)


def _row(
    result: ck.CheckResult, file: sf.StressFile, zones: Sequence[str], i: int
) -> dict[str, Any]:
    x, y, z = (float(v) for v in file.coordinates[i])
    cyc = result.cyclic
    per_component = cyc.sigma_a.ndim == 2
    row: dict[str, Any] = {
        "node": int(result.node_labels[i]),
        "x_mm": x,
        "y_mm": y,
        "z_mm": z,
        "r_mm": math.hypot(x, y),
        "zone": zones[i],
        "h": float(result.h_at_max[i]),
        "sigma_V_mpa": float(result.sigma_V_max[i]),
        "epsilon_zul_percent": float(result.epsilon_zul[i]),
        "sigma_stat_mpa": float(result.sigma_stat[i]),
        "a_stat": float(result.a_stat[i]),
        "state_of_max": int(result.state_of_max[i]),
        "sigma_W_mpa": float(result.sigma_W[i]),
        "k": float(result.k[i]),
        "a_B_V": float(cyc.a_B_V[i]),
        "a_B_V_at_N_G": float(result.a_B_V_at_N_G[i]),
        "N_predicted": float(result.N_predicted[i]),
        "life_flag": result.life_flags[i],
    }
    if per_component:
        for j in range(3):
            row[f"sigma_a_{j + 1}_mpa"] = float(cyc.sigma_a[i, j])
            row[f"sigma_m_{j + 1}_mpa"] = float(cyc.sigma_m[i, j])
            row[f"K_M_{j + 1}"] = float(cyc.K_M[i, j])
            row[f"sigma_B_{j + 1}_mpa"] = float(cyc.sigma_B[i, j])
            row[f"a_sigma_{j + 1}"] = float(cyc.a_sigma[i, j])
        row["a_B_Mises"] = float(cyc.a_B_Mises[i])
        row["a_B_NH"] = float(cyc.a_B_NH[i])
    else:
        row["sigma_a_mpa"] = float(cyc.sigma_a[i])
        row["sigma_m_mpa"] = float(cyc.sigma_m[i])
        row["K_M"] = float(cyc.K_M[i])
        row["sigma_B_mpa"] = float(cyc.sigma_B[i])
    return row


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _material_section(material: mt.StommelMaterial, settings: ck.CheckSettings) -> list[str]:
    lower, upper = mt.strain_limits_percent(material, settings.load_case)
    a_range = material.reduction_class.a_range(settings.load_case)
    sigma_w = float(mt.component_alternating_strength_mpa(material, 1.0 / 3.0))
    sigma_stat_lo = float(mt.static_component_strength_mpa(material, settings.load_case, math.inf))
    sigma_stat_hi = float(mt.static_component_strength_mpa(material, settings.load_case, 1.0 / 3.0))
    sensitivity = sigma_w / material.sigma_Y_service_mpa
    k_uni = float(mt.slope_exponent(material, 1.0 / 3.0))
    k_hyd = float(mt.slope_exponent(material, math.inf))
    cls = material.reduction_class
    hyp = material.failure_hypothesis_class
    return [
        "## Werkstoffseite des Nomogramms",
        "",
        f"- Werkstoff: {material.designation}; Kurven {material.room_temperature.file} "
        f"({material.room_temperature.source}, {material.room_temperature.direction_deg}°, "
        f"{_g(material.room_temperature.temperature_c, 0)} °C) und {material.service.file} "
        f"({material.service.source}, {material.service.direction_deg}°, "
        f"{_g(material.temperature_c, 0)} °C); Zustand {material.service.state or 'Referenz 0°'}",
        f"- Klasse der Abminderungsfaktoren: {cls.designation} ({cls.behaviour}); Versagenshypothese: "
        f"{hyp.designation}, f_τ {_g(hyp.f_tau, 2)}, q {_g(material.q, 2)} (Tabelle 6.1)",
        f"- K = σ_Y(23 °C) = {_g(material.K_mpa, 1)} MPa bei {_g(material.K_strain_percent, 2)} %; "
        f"σ_Y({_g(material.temperature_c, 0)} °C) = {_g(material.sigma_Y_service_mpa, 1)} MPa",
        f"- Lastfall {settings.load_case}: A {_g(a_range.minimum, 2)} bis {_g(a_range.maximum, 2)} (Bild 6.18), "
        f"ε_min {_g(lower, 2)} %, ε_max {_g(upper, 2)} % (Raumtemperaturkurve); "
        f"σ_stat({_g(material.temperature_c, 0)} °C) {_g(sigma_stat_lo, 1)} bis {_g(sigma_stat_hi, 1)} MPa",
        f"- A_W {_g(cls.cyclic_reduction_factor.minimum, 2)} bis {_g(cls.cyclic_reduction_factor.maximum, 2)} "
        f"(Bild 6.26{', fest' if not cls.cyclic_factor_scaled_by_multiaxiality else ''}); "
        f"σ_W({_g(material.temperature_c, 0)} °C) = {_g(sigma_w, 1)} MPa; M = {_g(sensitivity, 3)}",
        f"- Neigungsexponent k = {_g(k_uni, 2)} (h = 1/3) bis {_g(k_hyd, 2)} (h → ∞); Tabelle 6.3: "
        f"{_g(cls.slope_exponent.minimum, 2)} bis {_g(cls.slope_exponent.maximum, 2)}",
        f"- N_G = {st.LIMIT_NUMBER_OF_CYCLES:.0e}, geforderte Lastspielzahl {settings.required_cycles:.3g}, "
        f"Überlastungsfall F{settings.overload_case}, Amplitudenroute {settings.amplitude_route}, "
        f"S = {_g(settings.safety, 1)}",
        (
            "- Vergleichsspannung: Hill-Vergleichsspannung im Faserkoordinatensystem mit den "
            "R_ij der CONVERSE-Karte je Knoten (Erweiterung E7); Amplitude und Mittelwert aus "
            "der vorzeichenbehafteten Hill-Spannung"
            if settings.amplitude_route == "signed_hill"
            else "- Vergleichsspannung: von Mises mit q nach Gl. (6.2) und (6.16), wie veröffentlicht"
        ),
        "",
    ]


def _node_lines(row: dict[str, Any]) -> list[str]:
    lines = [
        f"- Knoten {row['node']} ({row['zone']}), Teilsystem x {_g(row['x_mm'])} y {_g(row['y_mm'])} "
        f"z {_g(row['z_mm'])} mm, r {_g(row['r_mm'])} mm",
        f"- statisch: σ_V {_g(row['sigma_V_mpa'], 1)} MPa, h {_g(row['h'])}, "
        f"ε_zul {_g(row['epsilon_zul_percent'], 2)} %, σ_stat {_g(row['sigma_stat_mpa'], 1)} MPa, "
        f"a_stat {_g(row['a_stat'])}, maßgebende Stellung {row['state_of_max']}",
    ]
    if "sigma_a_1_mpa" in row:
        for j in (1, 2, 3):
            lines.append(
                f"- Hauptrichtung {j}: σ_a {_g(row[f'sigma_a_{j}_mpa'], 1)} MPa, "
                f"σ_m {_g(row[f'sigma_m_{j}_mpa'], 1)} MPa, "
                f"K_M {_g(row[f'K_M_{j}'])}, σ_B {_g(row[f'sigma_B_{j}_mpa'], 1)} MPa, a_σ {_g(row[f'a_sigma_{j}'])}"
            )
        lines.append(f"- a_B,Mises {_g(row['a_B_Mises'])}, a_B,NH {_g(row['a_B_NH'])}")
    else:
        lines.append(
            f"- σ_a {_g(row['sigma_a_mpa'], 1)} MPa, σ_m {_g(row['sigma_m_mpa'], 1)} MPa, K_M {_g(row['K_M'])}, "
            f"σ_B {_g(row['sigma_B_mpa'], 1)} MPa"
        )
    lines.append(
        f"- σ_W {_g(row['sigma_W_mpa'], 1)} MPa, k {_g(row['k'], 2)}, **a_B,V {_g(row['a_B_V'])}** "
        f"(bei N_G {_g(row['a_B_V_at_N_G'])}), vorhergesagte Lastspielzahl "
        f"{row['N_predicted']:.3g} ({row['life_flag']})"
    )
    return lines


def _table(rows: list[dict[str, Any]], columns: list[tuple[str, str, int]]) -> list[str]:
    head = "| " + " | ".join(title for _, title, _ in columns) + " |"
    sep = "|" + "|".join("---" for _ in columns) + "|"
    out = [head, sep]
    for row in rows:
        cells = []
        for key, _, digits in columns:
            value = row[key]
            if isinstance(value, float):
                cells.append(f"{value:.3g}" if key == "N_predicted" else _g(value, digits))
            else:
                cells.append(str(value))
        out.append("| " + " | ".join(cells) + " |")
    return out


# --- figures ----------------------------------------------------------------------------------------


def _fillet_map(
    result: ck.CheckResult,
    file: sf.StressFile,
    zones: Sequence[str],
    fillet: str,
    stem: Path,
    step: str,
) -> list[Path]:
    """a_B,V over the fillet surface: arc position (angle about the wheel axis in the part
    frame) over the face width."""
    index = [i for i, zone in enumerate(zones) if zone == f"fillet {fillet}"]
    if not index:
        return []
    coordinates = file.coordinates[index].astype(float)
    angle = np.degrees(np.arctan2(coordinates[:, 1], coordinates[:, 0]))
    values = result.cyclic.a_B_V[index]
    figure, axes = new_figure("full", 0.45)
    scatter = axes.scatter(
        angle, coordinates[:, 2], c=values, s=9, cmap=DEGREE_COLOURMAP, marker="s", linewidths=0
    )
    bar = figure.colorbar(scatter, ax=axes, pad=0.02)
    bar.set_label("$a_{\\mathrm{B,V}}$")
    axes.set_xlabel("Winkel um die Radachse in °")
    axes.set_ylabel("$z$ in mm")
    decimal_comma(axes)
    return save_figure(figure, stem)


def _position_curves(
    folder: Path,
    manifest: dict[str, Any],
    material: mt.StommelMaterial,
    settings: ck.CheckSettings,
    step: str,
    series: str | None,
    nodes: Sequence[int],
    stem: Path,
    roles: Mapping[int, str] | None = None,
) -> list[Path]:
    """σ_V and the signed von Mises stress of the given nodes over the positions; ``roles``
    names what each node is in the legend (its check, zone and place), the named points A to
    E of the path stand as vertical lines."""
    positions = [
        p for p in sf.positions_with_stress(manifest, folder, series) if p.path is not None
    ]
    if not positions or not nodes:
        return []
    named = sorted(
        {(p.point.from_a_mm, p.point.label) for p in positions if p.point.label},
        key=lambda item: item[0],
    )
    first = sf.read_stress_file(positions[0].path)  # type: ignore[arg-type]
    rows = first.index_of(nodes)
    from_a: list[float] = []
    sigma_v: list[np.ndarray] = []
    signed: list[np.ndarray] = []
    for position in positions:
        file = sf.read_stress_file(position.path)  # type: ignore[arg-type]
        if step not in file.step_names or not file.is_complete(step):
            continue
        s = file.stress(step)[rows]
        s1, s2, s3 = st.principal_stresses(s)
        sigma_v.append(
            st.equivalent_stress_static(
                s1, s2, s3, material.q, settings.compressive_strength_factor
            )
        )
        signed.append(
            st.signed_mises_stress(
                st.mises_stress(s1, s2, s3), st.first_stress_invariant(s1, s2, s3)
            )
        )
        from_a.append(position.point.from_a_mm)
    if not from_a:
        return []
    figure, (top, bottom) = new_figure("full", 0.8, rows=2, sharex=True)
    sv = np.array(sigma_v)
    sg = np.array(signed)
    for j, node in enumerate(nodes):
        label = f"Knoten {node}" + (f": {roles[node]}" if roles and node in roles else "")
        top.plot(from_a, sv[:, j], label=label)
        bottom.plot(from_a, sg[:, j], label=label)
    for ax in (top, bottom):
        for x, _label in named:
            ax.axvline(x, color=SHEET.colour("tum_grau_50"), linewidth=0.6)
    for x, label in named:
        top.text(x, top.get_ylim()[1], label, ha="center", va="bottom")
    top.set_ylabel("$\\sigma_{\\mathrm{V}}$ in MPa")
    bottom.set_ylabel("$\\sigma_{\\mathrm{V,Mises}}\\,\\mathrm{sgn}\\,I_1$ in MPa")
    bottom.set_xlabel("Wälzweg ab A in mm")
    legend_outside(figure, top, where="bottom", ncol=1)
    decimal_comma(top)
    decimal_comma(bottom)
    return save_figure(figure, stem)


# --- the method figures (``curves``) ----------------------------------------------------------------

ALL_MATERIALS: tuple[str, ...] = (
    "pa46_gf30_linear",
    "pa46_gf30_qs",
    "pa46_gf30_dy1",
    "pa46_gf30_dy2",
)
CARD_NAMES: dict[str, str] = {
    "pa46_gf30_linear": "linear-elastisch",
    "pa46_gf30_qs": "QS",
    "pa46_gf30_dy1": "DY1",
    "pa46_gf30_dy2": "DY2",
}
CARD_LABELS: dict[str, str] = {
    "pa46_gf30_linear": "linear",
    "pa46_gf30_qs": "qs",
    "pa46_gf30_dy1": "dy1",
    "pa46_gf30_dy2": "dy2",
}
ROOT_STATE: tuple[float, float] = (0.64, 0.083)
"""Mean orientation state (a_11, a_22) of the root fillet elements of the CONVERSE mapping
(``wheel_mesh.con5`` read on 2026-10-11: whole wheel 0,593 / 0,083, root fillets about
0,64 / 0,083): the state whose Hill ratio the own extension (E7) would apply at the root."""
STATES: tuple[tuple[str, mt.OrientationState], ...] = (
    ("isotrop (1/3; 1/3)", "isotropic"),
    ("Zahnfuß-Mapping (0,64; 0,083)", ROOT_STATE),
    ("ausgerichtet (1; 0)", "aligned"),
)
# Black-and-white rule (user, 2026-10-11, second round): uniform line width; the temperature is
# told by its colour and by its family of line styles (23 °C the solid family, 80 °C the dotted
# family), the direction, state or multiaxiality by the member of the family, so no two curves
# of one panel share a style.
LineStyle = str | tuple[float, tuple[float, ...]]
TEMPERATURE_COLOURS: dict[float, str] = {23.0: "diag1", 80.0: "diag2"}
STYLE_FAMILIES: dict[float, tuple[LineStyle, ...]] = {
    23.0: ("-", (0, (6, 2)), "-."),
    80.0: ((0, (3, 1.5)), (0, (1, 1.5)), (0, (6, 1.5, 1, 1.5, 1, 1.5))),
}
DIRECTION_INDEX: dict[int, int] = {0: 0, 45: 1, 90: 2}
MEASURED_STYLES: tuple[LineStyle, ...] = STYLE_FAMILIES[23.0]
STATE_STYLES: tuple[LineStyle, ...] = STYLE_FAMILIES[80.0]
CARD_STYLES: tuple[LineStyle, ...] = ("-", (0, (6, 2)), "-.", (0, (1, 1.5)))
CONSTRUCTION_STYLES: tuple[LineStyle, ...] = ((0, (5, 2)), "-.", (0, (1, 1.5)))
CLASS_ORDER: tuple[str, ...] = (
    "semi_crystalline_reinforced",
    "amorphous_reinforced",
    "semi_crystalline_unreinforced",
    "amorphous_unreinforced",
)
LOAD_CASE_COLOURS: dict[str, str] = {
    "einmalig": "diag1",
    "mehrmalig": "diag2",
    "langzeitig": "diag3",
    "wechselnd": "diag4",
}
LOAD_CASE_HATCHES: dict[str, str] = {
    "einmalig": "",
    "mehrmalig": "///",
    "langzeitig": "...",
    "wechselnd": "xxx",
}
LOAD_CASE_NAMES: dict[str, str] = {
    "einmalig": "einmalig",
    "mehrmalig": "mehrmalig",
    "langzeitig": "langzeitig",
    "wechselnd": "wechselnd ($N$ ≤ 10$^7$)",
}
CLASS_SHORT: dict[str, str] = {
    "semi_crystalline_reinforced": "teilkristallin\nverstärkt",
    "amorphous_reinforced": "amorph\nverstärkt",
    "semi_crystalline_unreinforced": "teilkristallin\nunverstärkt",
    "amorphous_unreinforced": "amorph\nunverstärkt",
}
DECADES = np.logspace(4.0, 7.0, 4)
GREY = "0.45"
REFERENCE_NOTE = (
    "Referenzkurve der Zugprobe in Fließrichtung (0°), wie Matscape sie für die Karte verwendet "
    "(identisch mit der *PLASTIC-Kurve der CONVERSE-Karte)"
)
BOX = {"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": GREY, "linewidth": 0.5}


@dataclass(frozen=True)
class FigureLimits:
    """Shared axis limits of a family of comparable figures (user rule of 2026-10-11: comparable
    diagrams get the same scaling, the maximum over all of them)."""

    strain_percent: float
    stress_mpa: float
    state_strain_percent: float
    state_stress_mpa: float
    haigh_mean_min_mpa: float
    haigh_mean_max_mpa: float
    haigh_amplitude_max_mpa: float
    woehler_amplitude_max_mpa: float


def _save(figure: Any, stem: Path) -> None:
    """Write the figure and close it (the script draws more than twenty figures)."""
    import matplotlib.pyplot as plt

    save_figure(figure, stem)
    plt.close(figure)


def _style(colour: str, linestyle: LineStyle, **kwargs: Any) -> dict[str, Any]:
    """Line arguments: a palette colour, a line style and no marker (the house style cycles
    markers with the colours; the method figures are drawn with lines only, user 2026-10-11)."""
    return {"color": SHEET.colour(colour), "linestyle": linestyle, "marker": "none", **kwargs}


def _tstyle(temperature_c: float, member: int, **kwargs: Any) -> dict[str, Any]:
    """Line arguments of a temperature: its colour and the ``member``-th style of its family."""
    return _style(
        TEMPERATURE_COLOURS[temperature_c], STYLE_FAMILIES[temperature_c][member], **kwargs
    )


def _sigma(sub: str) -> str:
    return f"$\\sigma_{{\\mathrm{{{sub}}}}}$"


def _boxed(
    axes: Any,
    x: float,
    y: float,
    text: str,
    colour: str = "black",
    *,
    offset_points: tuple[float, float] = (0.0, 0.0),
    ha: str = "center",
    va: str = "center",
) -> None:
    """A label in a white box with the glyphs centred in the box: matplotlib reserves the
    descender of the font in every text box, so a label without descenders sits high; the box is
    drawn by an invisible copy of the text and the visible text is shifted down by a tenth of
    the font size (user, 2026-10-11)."""
    from matplotlib.font_manager import FontProperties

    size_pt = FontProperties(size="small").get_size_in_points()
    common = {"ha": ha, "va": va, "fontsize": "small", "textcoords": "offset points"}
    dx, dy = offset_points
    axes.annotate(text, (x, y), xytext=(dx, dy), color="none", bbox=BOX, **common)
    axes.annotate(text, (x, y), xytext=(dx, dy - 0.1 * size_pt), color=colour, **common)


def _at_temperature(material: mt.StommelMaterial, temperature_c: float) -> mt.StommelMaterial:
    """The material with the isotherm of ``temperature_c`` as its service curve: at room
    temperature the nomogram reads its values off the reference curve itself."""
    if temperature_c == material.temperature_c:
        return material
    if temperature_c != material.room_temperature.temperature_c:
        raise InputRangeError(f"{material.name}: no isotherm at {temperature_c} degC")
    return material.model_copy(
        update={"service": material.room_temperature, "service_curve": material.room_curve}
    )


def _haigh_values(
    material: mt.StommelMaterial, temperature_c: float, load_case: mt.LoadCase
) -> tuple[float, float, float]:
    """(σ_W, σ_Y, σ_stat) of the Haigh construction at a temperature, h = 1/3: what Matscape
    prints as σ_WK, σ_B,S and σ_SK (at room temperature A_W K, K and A_max K; at the service
    temperature the strains of those transferred to the isotherm)."""
    at = _at_temperature(material, temperature_c)
    return (
        float(mt.component_alternating_strength_mpa(at, 1.0 / 3.0)),
        at.sigma_Y_service_mpa,
        float(mt.static_component_strength_mpa(at, load_case, 1.0 / 3.0)),
    )


def _state_materials(material: mt.StommelMaterial) -> list[tuple[str, mt.StommelMaterial]]:
    """The orientation states of the CONVERSE card of the material (empty without a card)."""
    if not material.cof:
        return []
    return [(label, mt.material_for_state(material, state)) for label, state in STATES]


def _all_curves(material: mt.StommelMaterial) -> list[StressStrainCurve]:
    return [material.room_curve, material.service_curve, *(c for _, c in material.other_curves)]


def _limits(
    materials: Sequence[mt.StommelMaterial],
    states: dict[str, list[tuple[str, mt.StommelMaterial]]],
    load_case: mt.LoadCase,
) -> FigureLimits:
    """The limits of every figure family over all materials drawn."""
    strain = max(max(c.strain_percent) for m in materials for c in _all_curves(m))
    stress = max(max(c.stress_mpa) for m in materials for c in _all_curves(m))
    state_curves = [
        c
        for m in materials
        for _, s in states.get(m.name, [])
        for c in (s.room_curve, s.service_curve)
    ]
    state_strain = max([strain, *(max(c.strain_percent) for c in state_curves)])
    state_stress = max([stress, *(max(c.stress_mpa) for c in state_curves)])
    mean_min = mean_max = amplitude = woehler = 0.0
    for m in materials:
        for temperature in (m.room_temperature.temperature_c, m.temperature_c):
            sigma_w, sigma_y, sigma_stat = _haigh_values(m, temperature, load_case)
            mean_min = max(mean_min, sigma_stat)
            mean_max = max(mean_max, sigma_y)
            amplitude = max(amplitude, sigma_stat, sigma_w * (1.0 + sigma_stat / sigma_y))
            woehler = max(woehler, sigma_stat)
    return FigureLimits(
        strain_percent=math.ceil(strain),
        stress_mpa=10.0 * math.ceil(stress / 10.0),
        state_strain_percent=math.ceil(state_strain),
        state_stress_mpa=10.0 * math.ceil(state_stress / 10.0),
        haigh_mean_min_mpa=-10.0 * math.ceil(1.05 * mean_min / 10.0),
        haigh_mean_max_mpa=10.0 * math.ceil(1.05 * mean_max / 10.0),
        haigh_amplitude_max_mpa=10.0 * math.ceil(1.1 * amplitude / 10.0),
        woehler_amplitude_max_mpa=10.0 * math.ceil(1.05 * woehler / 10.0),
    )


def _figure_stress_strain(material: mt.StommelMaterial, limits: FigureLimits, out: Path) -> str:
    """The engineering stress-strain curves of the card at both temperatures, every direction;
    plotted direction by direction so that the legend shows 23 °C in its upper row and 80 °C in
    its lower row (user, 2026-10-11)."""
    figure, axes = new_figure("full", 0.6)
    temperatures = (material.room_temperature.temperature_c, material.temperature_c)
    by_direction: dict[int, list[tuple[float, StressStrainCurve]]] = {}
    for temperature in temperatures:
        for reference, curve in material.curves_at(temperature):
            by_direction.setdefault(reference.direction_deg, []).append((temperature, curve))
    with_direction = len(by_direction) > 1 or bool(material.other_curves)
    for direction in sorted(by_direction):
        for temperature, curve in by_direction[direction]:
            label = f"{_g(temperature, 0)} °C" + (f", {direction}°" if with_direction else "")
            axes.plot(
                curve.strain_percent,
                curve.stress_mpa,
                label=label,
                **_tstyle(temperature, DIRECTION_INDEX[direction]),
            )
    axes.set_xlabel("Dehnung $\\varepsilon$ in %")
    axes.set_ylabel("Spannung $\\sigma$ in MPa")
    axes.set_xlim(0.0, limits.strain_percent)
    axes.set_ylim(0.0, limits.stress_mpa)
    legend_outside(figure, axes, ncol=len(by_direction))
    decimal_comma(axes)
    stem = f"spannung_dehnung_{CARD_LABELS[material.name]}"
    _save(figure, out / stem)
    which = (
        "je Prüfrichtung zur Fließrichtung ("
        + ", ".join(f"{d}°" for d in sorted(by_direction))
        + ")"
        if with_direction
        else "(linear bis 1 % Dehnung)"
    )
    return f"`{stem}`: " + caption(
        f"Spannungs-Dehnungs-Kurven (technische Spannung) von {material.designation} bei "
        f"{_g(temperatures[0], 0)} und {_g(temperatures[1], 0)} °C {which}; Werte der "
        f"Matscape-Karte aus den METG-Zugversuchen"
    )


def _head(axes: Any, start: tuple[float, float], end: tuple[float, float]) -> None:
    """A filled arrow head at ``end`` pointing from ``start``: a very short solid arrow, so the
    head is complete whatever the line style of the shaft."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    axes.annotate(
        "",
        xy=end,
        xytext=(end[0] - 1.0e-3 * dx, end[1] - 1.0e-3 * dy),
        arrowprops={
            "arrowstyle": "-|>",
            "color": GREY,
            "linewidth": 0.9,
            "shrinkA": 0.0,
            "shrinkB": 0.0,
            "mutation_scale": 9,
        },
    )


def _arrow(
    axes: Any, start: tuple[float, float], end: tuple[float, float], style: LineStyle
) -> None:
    """A construction arrow: the shaft in the given line style, the head filled."""
    axes.plot(
        [start[0], end[0]],
        [start[1], end[1]],
        color=GREY,
        linestyle=style,
        linewidth=0.9,
        marker="none",
    )
    _head(axes, start, end)


def _reduction_panel(
    axes: Any, material: mt.StommelMaterial, load_case: mt.LoadCase, k_value: float
) -> tuple[dict[str, tuple[float, float]], list[tuple[Any, str]]]:
    """The left panel of the nomogram (Bild 6.17 / 6.21, "Bereiche der A-Faktoren"): one column
    per material class with the ranges of the reduction factor per load case as bars on the
    shared stress axis (A K); the load case is told by its hatch in every class and by its colour
    in the class of the gear (first column), the names go to the legend (user, 2026-10-11).
    Returns the bar corners the constructions start from and the legend entries."""
    from matplotlib.patches import Patch

    classes = mt.material_classes()
    chosen = material.reduction_class.name
    starts: dict[str, tuple[float, float]] = {}
    legend: list[tuple[Any, str]] = []
    for column, name in enumerate(CLASS_ORDER, start=1):
        cls = classes[name]
        own = name == chosen
        for case in mt.LOAD_CASES:
            bounds = cls.a_range(case)
            colour = SHEET.colour(LOAD_CASE_COLOURS[case]) if own else GREY
            alpha = 0.85 if own else 0.3
            hatch = LOAD_CASE_HATCHES[case]
            low, high = bounds.minimum * k_value, bounds.maximum * k_value
            if high > low:
                height, bottom = high - low, low
            else:
                # a single value (A_min = A_max): a thin bar of the common width with the hatch
                height, bottom = 0.03 * k_value, low - 0.015 * k_value
            # the transparent face and the hatch as two artists: in one artist the SVG backend
            # paints the hatch tile's background with the opaque face colour, so that the hatch
            # vanished in the SVG and in every PDF made from it (2026-10-17)
            axes.bar(
                column, height, bottom=bottom, width=0.6, facecolor=colour, alpha=alpha, linewidth=0
            )
            axes.bar(
                column,
                height,
                bottom=bottom,
                width=0.6,
                facecolor="none",
                edgecolor=colour,
                hatch=hatch,
                linewidth=0,
            )
            if own:
                starts[case] = (column + 0.3, high)
                starts[case + "_min"] = (column + 0.3, low)
                span = (
                    f"$A$ = {_g(bounds.minimum, 2)} bis {_g(bounds.maximum, 2)}"
                    if high > low
                    else f"$A$ = {_g(bounds.maximum, 2)}"
                )
                handle = (
                    Patch(facecolor=colour, alpha=alpha, linewidth=0),
                    Patch(facecolor="none", edgecolor=colour, hatch=hatch, linewidth=0),
                )
                legend.append(
                    (
                        handle,
                        f"{LOAD_CASE_NAMES[case]}, {material.reduction_class.designation}: {span}",
                    )
                )
        axes.text(
            column,
            1.02,
            CLASS_SHORT[name],
            transform=axes.get_xaxis_transform(),
            ha="center",
            va="bottom",
            fontsize="x-small",
            rotation=90,
            multialignment="left",
            color=SHEET.colour("diag1") if own else GREY,
        )
    legend.append(
        (
            Patch(facecolor=GREY, edgecolor=GREY, alpha=0.3, linewidth=0),
            "andere Werkstoffklassen, Lastart am Muster erkennbar (Bild 6.18)",
        )
    )
    axes.set_xlim(0.2, len(CLASS_ORDER) + 0.8)
    axes.set_xticks([])
    axes.tick_params(labelleft=False, left=False)
    axes.grid(False)
    import matplotlib as mpl

    for a in (0.2, 0.4, 0.6, 0.8):
        axes.axhline(
            a * k_value,
            color=mpl.rcParams["grid.color"],
            linewidth=mpl.rcParams["grid.linewidth"],
            alpha=mpl.rcParams["grid.alpha"],
            zorder=0,
        )
    axes.set_axisbelow(True)
    for spine in ("top", "right"):
        axes.spines[spine].set_visible(False)
    factor_axis = axes.secondary_yaxis(
        "left", functions=(lambda s: s / k_value, lambda a: a * k_value)
    )
    factor_axis.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    factor_axis.set_yticklabels(["0,0", "0,2", "0,4", "0,6", "0,8", "1,0"])
    factor_axis.set_ylabel("Abminderungsfaktor $A$")
    return starts, legend


def _figure_nomogram(
    material: mt.StommelMaterial, load_case: mt.LoadCase, limits: FigureLimits, out: Path
) -> str:
    """Bild 6.17 / 6.21 (and Bild 3.26, p. 194) for the card: the ranges of the reduction factors
    per class and load case on the left, the reference curve at 23 °C and the isotherm of the
    service temperature on the right; A_max of the load case goes from its bar to the reference
    curve, the permissible strain is taken as temperature-independent and goes down to the
    isotherm, from there the permissible stress goes on to the stress axis at the right
    of the panel (a Z, user 2026-10-11; section 6.2.2.1);
    A_min and A_W likewise. Every value in the legend."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import ConnectionPatch

    room, service = material.room_curve, material.service_curve
    k_value = material.K_mpa
    a_range = material.reduction_class.a_range(load_case)
    a_w = material.reduction_class.cyclic_reduction_factor.maximum
    t_room_c = material.room_temperature.temperature_c
    t_hot_c = material.temperature_c
    t_room, t_hot = _g(t_room_c, 0), _g(t_hot_c, 0)
    figure, (left, right) = plt.subplots(
        1,
        2,
        figsize=figure_size("full", 0.8),
        sharey=True,
        layout="constrained",
        gridspec_kw={"width_ratios": [1.0, 2.4]},
    )
    starts, case_legend = _reduction_panel(left, material, load_case, k_value)
    # own scaling per card: the A axis hangs on K, a shared stress limit would squash it
    x_max = float(math.ceil(max(room.strain_percent[-1], service.strain_percent[-1])))
    y_max = 10.0 * math.ceil(0.11 * k_value)
    right.plot(
        room.strain_percent,
        room.stress_mpa,
        label=f"{t_room} °C, Referenzkurve 0° (Fließrichtung)",
        **_tstyle(t_room_c, 0),
    )
    right.plot(
        service.strain_percent,
        service.stress_mpa,
        label=f"{t_hot} °C, Isotherme der Betriebstemperatur",
        **_tstyle(t_hot_c, 0),
    )
    for axes in (left, right):
        axes.axhline(k_value, color=GREY, linestyle="-", linewidth=0.8, marker="none")
    right.plot(
        [],
        [],
        color=GREY,
        linestyle="-",
        linewidth=0.8,
        marker="none",
        label=(
            f"$A$ = 1,0 entspricht $K$ = {_sigma('Y')}({t_room} °C) = {_g(k_value, 1)} MPa "
            f"bei {_g(material.K_strain_percent, 2)} % (Matscape: {_sigma('B,S')})"
        ),
    )
    constructions: tuple[tuple[float, tuple[float, float], LineStyle, str, str, str], ...] = (
        (
            a_range.maximum,
            starts[load_case],
            CONSTRUCTION_STYLES[0],
            f"$A_{{\\mathrm{{max}}}}$ = {_g(a_range.maximum, 2)}",
            "stat",
            "zul,max",
        ),
        (
            a_range.minimum,
            starts[load_case + "_min"],
            CONSTRUCTION_STYLES[1],
            f"$A_{{\\mathrm{{min}}}}$ = {_g(a_range.minimum, 2)}",
            "stat",
            "zul,min",
        ),
        (
            a_w,
            starts["wechselnd"],
            CONSTRUCTION_STYLES[2],
            f"$A_{{\\mathrm{{W}}}}$ = {_g(a_w, 2)}",
            "W",
            "W",
        ),
    )
    for factor, start, style, name, sub, strain_name in constructions:
        level = factor * k_value
        strain = mt.strain_limit_percent(room, factor, k_value)
        sigma_t = float(mt.stress_on_isotherm(service, strain))
        figure.add_artist(
            ConnectionPatch(
                xyA=start,
                coordsA=left.transData,
                xyB=(strain, level),
                coordsB=right.transData,
                arrowstyle="-",
                linestyle=style,
                color=GREY,
                linewidth=0.9,
                shrinkA=0.0,
                shrinkB=0.0,
            )
        )
        _head(right, (0.0, level), (strain, level))
        _arrow(right, (strain, level), (strain, sigma_t), style)
        _arrow(right, (strain, sigma_t), (x_max, sigma_t), style)
        right.plot(
            [strain, strain],
            [0.0, sigma_t],
            color=GREY,
            linestyle=(0, (1, 2)),
            linewidth=0.6,
            marker="none",
        )
        right.plot(
            [x_max],
            [sigma_t],
            marker="o",
            markersize=4,
            color=SHEET.colour(TEMPERATURE_COLOURS[t_hot_c]),
            linestyle="none",
            clip_on=False,
        )
        right.plot(
            [],
            [],
            color=GREY,
            linestyle=style,
            linewidth=0.9,
            marker="none",
            label=(
                f"{name}: {_g(level, 1)} MPa, "
                f"$\\varepsilon_{{\\mathrm{{{strain_name}}}}}$ = {_g(strain, 2)} %, "
                f"{_sigma(sub)}({t_hot} °C) = {_g(sigma_t, 1)} MPa"
            ),
        )
    from matplotlib.legend_handler import HandlerTuple

    handles, labels = right.get_legend_handles_labels()
    for handle, label in case_legend:
        handles.append(handle)
        labels.append(label)
    right.set_xlabel("Dehnung $\\varepsilon$ in %")
    right.set_ylabel("Spannung $\\sigma$ in MPa")
    right.yaxis.tick_right()
    right.yaxis.set_label_position("right")
    right.tick_params(labelright=True, labelleft=False)
    right.spines["left"].set_visible(False)
    right.spines["right"].set_visible(True)
    right.set_xlim(0.0, x_max)
    right.set_ylim(0.0, y_max)
    figure.legend(
        handles,
        labels,
        loc="outside lower center",
        ncol=1,
        # a bar's face and hatch are two patches drawn on top of each other in one entry
        handler_map={tuple: HandlerTuple(ndivide=1, pad=0.0)},
    )
    decimal_comma(right)
    stem = f"nomogramm_{CARD_LABELS[material.name]}"
    _save(figure, out / stem)
    return f"`{stem}`: " + caption(
        f"Nomogramm zur Ermittlung der Bemessungsgrenzen für {material.designation}: links die "
        f"Bereiche der Abminderungsfaktoren je Werkstoffklasse und Lastart (Lastart durch das "
        f"Flächenmuster, in der Klasse des Zahnrads zusätzlich durch die Farbe), rechts die "
        f"{REFERENCE_NOTE} bei {t_room} °C und die Isotherme bei {t_hot} °C; der obere Wert A_max "
        f"der Lastart {load_case} führt waagerecht zur Referenzkurve, die zulässige Dehnung gilt "
        f"als temperaturunabhängig und wird senkrecht auf die Isotherme übertragen, von dort "
        f"weiter waagerecht zur Spannungsachse rechts (σ_stat bei {t_hot} °C); A_min und A_W "
        f"entsprechend",
        source=SOURCE_LABEL,
        relation="in Anlehnung an",
        page="194, 345, 349",
    )


def _value_axis(
    axes: Any,
    which: str,
    offset: float,
    ticks: list[tuple[float, str, str]],
    label: str,
) -> None:
    """A second axis below (``'x'``) or left of (``'y'``) the main one that carries only the
    characteristic values of the Haigh diagram, two lines per tick (value, symbol), as the
    Matscape original prints them under its axes; the axis label moves to this axis so nothing
    overlaps."""
    secondary = axes.secondary_xaxis(offset) if which == "x" else axes.secondary_yaxis(offset)
    positions = [position for position, _, _ in ticks]
    texts = [f"{_g(position, 1)}\n{symbol}" for position, symbol, _ in ticks]
    if which == "x":
        secondary.set_xticks(positions)
        secondary.set_xticklabels(texts)
        secondary.set_xlabel(label)
        labels = secondary.get_xticklabels()
        secondary.spines["bottom"].set_visible(False)
    else:
        secondary.set_yticks(positions)
        secondary.set_yticklabels(texts)
        secondary.set_ylabel(label)
        labels = secondary.get_yticklabels()
        secondary.spines["left"].set_visible(False)
    for text, (_, _, colour) in zip(labels, ticks, strict=True):
        text.set_color(colour)
        text.set_fontsize("small")
    secondary.tick_params(length=4, width=0.8, colors=GREY, labelcolor="black")


def _figure_haigh(
    material: mt.StommelMaterial,
    temperature_c: float,
    load_case: mt.LoadCase,
    limits: FigureLimits,
    out: Path,
) -> str:
    """The Haigh diagram as Matscape draws it (Strength Limits SSK, N = 10^7, A_WL = 1): the
    static limit triangle, the Goodman line from −σ_stat to σ_Y, the allowed region below both,
    the stress ratios R = −∞, −1, 0 as rays, M at the Goodman line and the characteristic values
    on value axes below and beside the main axes; lines only, every value in the legend too."""
    sigma_w, sigma_y, sigma_stat = _haigh_values(material, temperature_c, load_case)
    x_min, x_max = limits.haigh_mean_min_mpa, limits.haigh_mean_max_mpa
    y_max = limits.haigh_amplitude_max_mpa
    figure, axes = new_figure("full", 0.32 + 0.85 * y_max / (x_max - x_min))
    static_colour = SHEET.colour("diag1")
    goodman_colour = SHEET.colour("diag2")
    mean = np.linspace(-sigma_stat, sigma_y, 800)
    goodman = sigma_w * (1.0 - mean / sigma_y)
    static = np.clip(sigma_stat - np.abs(mean), 0.0, None)
    axes.fill_between(
        mean,
        0.0,
        np.minimum(goodman, static),
        color=static_colour,
        alpha=0.2,
        linewidth=0.0,
        label="zulässiger Bereich ($N$ = 10$^7$, $A_{\\mathrm{WL}}$ = 1)",
    )
    axes.plot(
        [-sigma_stat, 0.0, sigma_stat],
        [0.0, sigma_stat, 0.0],
        label=f"statische Grenze {_sigma('stat')} = {_g(sigma_stat, 1)} MPa",
        **_style("diag1", "-"),
    )
    left_end = sigma_w * (1.0 + sigma_stat / sigma_y)
    sensitivity = sigma_w / sigma_y
    axes.plot(
        [-sigma_stat, sigma_y],
        [left_end, 0.0],
        label=(
            f"Goodman-Gerade: {_sigma('W')} = {_g(sigma_w, 1)} MPa, "
            f"{_sigma('Y')} = {_g(sigma_y, 1)} MPa, $M$ = {_g(sensitivity, 3)}"
        ),
        **_style("diag2", (0, (6, 2))),
    )
    _boxed(
        axes,
        -sigma_stat,
        left_end,
        f"$M$ = {_g(sensitivity, 3)}",
        goodman_colour,
        offset_points=(-6.0, 6.0),
        ha="right",
        va="bottom",
    )
    rays = ((-1.0, "$R = -\\infty$"), (0.0, "$R = -1$"), (1.0, "$R = 0$"))
    for index, (slope, text) in enumerate(rays):
        axes.plot(
            [0.0, slope * y_max],
            [0.0, y_max],
            color=GREY,
            linestyle=(0, (1, 1.5)),
            linewidth=0.8,
            marker="none",
            label="Spannungsverhältnis $R$ = −∞, −1, 0" if index == 0 else None,
        )
        _boxed(axes, 0.88 * slope * y_max, 0.88 * y_max, text)
    axes.set_xlim(x_min, x_max)
    axes.set_ylim(0.0, y_max)
    axes.set_aspect("equal")
    _value_axis(
        axes,
        "x",
        -0.17,
        [
            (-sigma_stat, f"−{_sigma('stat')}", static_colour),
            (sigma_stat, _sigma("stat"), static_colour),
            (sigma_y, _sigma("Y"), goodman_colour),
        ],
        f"Mittelspannung {_sigma('m')} in MPa",
    )
    _value_axis(
        axes,
        "y",
        -0.09,
        [(sigma_w, _sigma("W"), goodman_colour), (sigma_stat, _sigma("stat"), static_colour)],
        f"Spannungsamplitude {_sigma('a')} in MPa",
    )
    legend_outside(figure, axes, where="bottom", ncol=1)
    decimal_comma(axes)
    stem = f"haigh_{CARD_LABELS[material.name]}_{_g(temperature_c, 0)}C"
    _save(figure, out / stem)
    return f"`{stem}`: " + caption(
        f"Haigh-Diagramm für {material.designation} bei {_g(temperature_c, 0)} °C aus der "
        f"{REFERENCE_NOTE}: statische Grenze σ_stat (A_max des Lastfalls {load_case}; Matscape "
        f"σ_SK), Goodman-Gerade von σ_W (A_W, N_G = 10^7; Matscape σ_WK) bis σ_Y (Matscape "
        f"σ_B,S) mit der Mittelspannungsempfindlichkeit M, zulässiger Bereich unterhalb beider "
        f"Grenzen, Kennwerte an den Achsen, Aufbau wie das Festigkeitsdiagramm von Matscape",
        source=SOURCE_LABEL,
        relation="in Anlehnung an",
        page="365",
    )


def _figure_woehler(material: mt.StommelMaterial, limits: FigureLimits, out: Path) -> str:
    """Bild 6.31: the synthetic Wöhler line (R = −1) of the card at both temperatures for the
    uniaxial state h = 1/3 (A_max) and the hydrostatic bound h → ∞ (A_min), amplitude linear
    over lg N, drawn only where the method is valid (10^4 to N_G = 10^7, no extrapolation to
    either side, user 2026-10-11), markers at the decades; always with the single-load factors
    A_S of Eq. (6.22), whatever load case the other figures use (review of 2026-10-11)."""
    figure, axes = new_figure("full", 0.6)
    cycles = np.logspace(4.0, 7.0, 200)
    variants: tuple[tuple[float, int, str, str], ...] = (
        (1.0 / 3.0, 0, "o", "$h$ = 1/3 (einachsig, $A_{\\mathrm{max}}$)"),
        (math.inf, 1, "s", "$h \\to \\infty$ (hydrostatisch, $A_{\\mathrm{min}}$)"),
    )
    for temperature in TEMPERATURE_COLOURS:
        at = _at_temperature(material, temperature)
        colour = SHEET.colour(TEMPERATURE_COLOURS[temperature])
        for h_value, member, marker, h_label in variants:
            k = float(mt.slope_exponent(at, h_value))
            sigma_s = float(mt.static_component_strength_mpa(at, "einmalig", h_value))
            sigma_w = float(mt.component_alternating_strength_mpa(at, h_value))
            line = np.minimum(sigma_w * (st.LIMIT_NUMBER_OF_CYCLES / cycles) ** (1.0 / k), sigma_s)
            axes.plot(
                cycles,
                line,
                label=(
                    f"{_g(temperature, 0)} °C, {h_label}: {_sigma('stat')} = {_g(sigma_s, 1)} MPa, "
                    f"{_sigma('W')} = {_g(sigma_w, 1)} MPa, $k$ = {_g(k, 2)}"
                ),
                **_tstyle(temperature, member),
            )
            at_decades = np.minimum(
                sigma_w * (st.LIMIT_NUMBER_OF_CYCLES / DECADES) ** (1.0 / k), sigma_s
            )
            axes.plot(
                DECADES,
                at_decades,
                linestyle="none",
                marker=marker,
                color=colour,
                markerfacecolor="white",
            )
    for index, bound in enumerate((st.LOWEST_NUMBER_OF_CYCLES, st.LIMIT_NUMBER_OF_CYCLES)):
        axes.axvline(
            bound,
            color=GREY,
            linestyle=(0, (1, 2)),
            linewidth=1.0,
            marker="none",
            label=(
                "Gültigkeitsbereich des Verfahrens $N$ = 10$^4$ bis $N_{\\mathrm{G}}$ = 10$^7$"
                if index == 0
                else None
            ),
        )
    axes.set_xscale("log")
    axes.set_xlim(1.0e3, 1.0e8)
    axes.set_ylim(0.0, limits.woehler_amplitude_max_mpa)
    axes.set_xlabel("Lastspielzahl $N$")
    axes.set_ylabel(f"Spannungsamplitude {_sigma('a')} in MPa ($R$ = −1)")
    legend_outside(figure, axes, where="bottom", ncol=1)
    decimal_comma(axes, which="y")
    stem = f"woehler_synthetisch_{CARD_LABELS[material.name]}"
    _save(figure, out / stem)
    return f"`{stem}`: " + caption(
        f"Synthetische Wöhlerlinien (R = −1) für {material.designation} bei "
        f"{_g(material.room_temperature.temperature_c, 0)} und {_g(material.temperature_c, 0)} °C "
        f"aus der {REFERENCE_NOTE}, gezeichnet im Gültigkeitsbereich des Verfahrens zwischen 10^4 "
        f"und N_G = 10^7: Gerade von σ_stat (Lastfall einmalig) bei N = 1 bis σ_W bei N_G, "
        f"Neigung k nach Formel (6.22) mit den Werten der jeweiligen Temperatur; h = 1/3 ist der "
        f"einachsige Zugzustand (A_max), h → ∞ der hydrostatische Grenzfall (A_min)",
        source=SOURCE_LABEL,
        relation="in Anlehnung an",
        page="370 bis 371",
    )


def _figure_orientation_states(
    material: mt.StommelMaterial,
    states: list[tuple[str, mt.StommelMaterial]],
    limits: FigureLimits,
    out: Path,
) -> str:
    """The measured directions (dark, solid family) beside the curves of the orientation states
    of the CONVERSE card (light, dotted family; the reference curve in true quantities with the
    stress times and the plastic strain divided by R_11 of the state, the elastic strain from E_1
    of the state): what the own extension would use at the root (E7)."""
    figure, (left, right) = new_figure("full", 0.5, cols=2, sharey=True)
    panels = ((left, material.room_temperature.temperature_c), (right, material.temperature_c))
    for axes, temperature in panels:
        for reference, curve in material.curves_at(temperature):
            axes.plot(
                curve.strain_percent,
                curve.stress_mpa,
                label=f"gemessen, {reference.direction_deg}° zur Fließrichtung",
                **_style("diag1", MEASURED_STYLES[DIRECTION_INDEX[reference.direction_deg]]),
            )
        for (label, state_material), style in zip(states, STATE_STYLES, strict=True):
            curve = (
                state_material.room_curve
                if temperature == material.room_temperature.temperature_c
                else state_material.service_curve
            )
            axes.plot(
                curve.strain_percent,
                curve.stress_mpa,
                label=f"CONVERSE-Karte, Zustand {label}",
                **_style("diag2", style),
            )
        axes.set_title(f"{_g(temperature, 0)} °C")
        axes.set_xlabel("Dehnung $\\varepsilon$ in %")
        axes.set_xlim(0.0, limits.state_strain_percent)
        axes.set_ylim(0.0, limits.state_stress_mpa)
        decimal_comma(axes)
    left.set_ylabel("Spannung $\\sigma$ in MPa")
    legend_outside(figure, left, where="bottom", ncol=2)
    stem = f"orientierungszustaende_{CARD_LABELS[material.name]}"
    _save(figure, out / stem)
    return f"`{stem}`: " + caption(
        f"Gemessene Richtungen und Orientierungszustände der CONVERSE-Karte für "
        f"{material.designation} (a_11; a_22): Referenzkurve 0° in wahren Größen mit dem "
        f"Hill-Verhältnis R_11 des Zustands skaliert (Spannung mal R_11, plastische Dehnung durch "
        f"R_11), elastischer Anteil mit E_1 des Zustands; Zustand des Zahnfußes aus "
        f"dem Mapping; Erweiterung E7, nicht Teil des veröffentlichten Verfahrens"
    )


def _figure_card_comparison(
    materials: Sequence[mt.StommelMaterial], limits: FigureLimits, out: Path
) -> str:
    """The reference curves of every card at both temperatures in one figure: colour by
    temperature, line style by card; legend with 23 °C in the upper row."""
    figure, axes = new_figure("full", 0.6)
    for material, style in zip(materials, CARD_STYLES, strict=False):
        card = CARD_NAMES[material.name]
        for temperature, curve in (
            (material.room_temperature.temperature_c, material.room_curve),
            (material.temperature_c, material.service_curve),
        ):
            axes.plot(
                curve.strain_percent,
                curve.stress_mpa,
                label=f"{card}, {_g(temperature, 0)} °C",
                **_style(TEMPERATURE_COLOURS[temperature], style),
            )
    axes.set_xlabel("Dehnung $\\varepsilon$ in %")
    axes.set_ylabel("Spannung $\\sigma$ in MPa")
    axes.set_xlim(0.0, limits.strain_percent)
    axes.set_ylim(0.0, limits.stress_mpa)
    legend_outside(figure, axes, ncol=len(materials))
    decimal_comma(axes)
    stem = "spannung_dehnung_vergleich_karten"
    _save(figure, out / stem)
    return f"`{stem}`: " + caption(
        "Referenzkurven (0°, Fließrichtung) der Matscape-Karten linear-elastisch, QS, DY1 und DY2 "
        "von Stanyl TW200F6 (PA46-GF30, konditioniert) bei 23 und 80 °C; die Dehnrate hebt "
        "Steifigkeit und Festigkeit, die Temperatur senkt sie"
    )


def _method_figures(
    materials: Sequence[mt.StommelMaterial], load_case: mt.LoadCase, out: Path
) -> list[str]:
    """Every method figure of the material cards with shared axis limits per figure family."""
    states = {m.name: _state_materials(m) for m in materials}
    limits = _limits(materials, states, load_case)
    lines = [
        "# Bildunterschriften der Methodenbilder (Stommel et al., Matscape-Karten)",
        "",
        "Gleiche Achsenskalierung je Bildfamilie (Maximum über alle Karten): Spannungs-Dehnungs-"
        f"Diagramme 0 bis {_g(limits.strain_percent, 0)} % und 0 bis "
        f"{_g(limits.stress_mpa, 0)} MPa; Nomogramme je Karte skaliert, weil die A-Achse an K "
        f"hängt (A = 1,0 bei K); Orientierungszustände 0 bis "
        f"{_g(limits.state_strain_percent, 0)} % und 0 bis {_g(limits.state_stress_mpa, 0)} MPa; "
        f"Haigh-Diagramme σ_m {_g(limits.haigh_mean_min_mpa, 0)} bis "
        f"{_g(limits.haigh_mean_max_mpa, 0)} MPa, σ_a 0 bis {_g(limits.haigh_amplitude_max_mpa, 0)} MPa; "
        f"Wöhlerlinien σ_a 0 bis {_g(limits.woehler_amplitude_max_mpa, 0)} MPa. "
        "Schwarz-Weiß-Regel: einheitliche Strichstärke; Temperatur durch Farbe und Linienfamilie "
        "(23 °C durchgezogen, lang gestrichelt, strichpunktiert; 80 °C kurz gestrichelt, "
        "gepunktet, strich-punkt-punkt), Richtung, Zustand oder Mehrachsigkeit durch das "
        "Familienmitglied.",
        "",
    ]
    for material in materials:
        lines.append(f"- {_figure_stress_strain(material, limits, out)}")
        lines.append(f"- {_figure_nomogram(material, load_case, limits, out)}")
        for temperature in (material.room_temperature.temperature_c, material.temperature_c):
            lines.append(f"- {_figure_haigh(material, temperature, load_case, limits, out)}")
        lines.append(f"- {_figure_woehler(material, limits, out)}")
        if states[material.name]:
            lines.append(
                f"- {_figure_orientation_states(material, states[material.name], limits, out)}"
            )
    if len(materials) > 1:
        lines.append(f"- {_figure_card_comparison(materials, limits, out)}")
    return lines


# --- commands ---------------------------------------------------------------------------------------


def _nodal_anisotropy(
    folder: Path,
    manifest: dict[str, Any],
    cof: Path,
    material: mt.StommelMaterial,
    series: str | None,
) -> an.NodalAnisotropy:
    """Frames, states and Hill ratios of every node of the folder's wheel from the CONVERSE
    orientation file and the mesh file named in the manifest, in the node order of the stress
    files."""
    from gearcore.fe.deck import (
        read_distribution,
        read_element_connectivity,
        read_field_variables,
        read_node_labels,
        verify_orientation_file,
    )
    from gearcore.io.converse_card import read_converse_card

    positions = sf.positions_with_stress(manifest, folder, series)
    with_file = [p for p in positions if p.path is not None]
    if not with_file:
        raise InputRangeError(f"{folder}: no stress file of series {series!r}")
    first = sf.read_stress_file(with_file[0].path)  # type: ignore[arg-type]
    mesh_entry = manifest.get("wheel_mesh", {})
    mesh_file = folder / str(mesh_entry.get("file", "wheel_mesh.inp"))
    if not mesh_file.is_file():
        raise InputRangeError(f"mesh file not found: {mesh_file}")
    if not cof.is_file():
        raise InputRangeError(f"orientation file not found: {cof}")
    print(f"reading the mesh {mesh_file.name} and the orientation file {cof.name} ...")
    mesh_text = mesh_file.read_text(encoding="utf-8", errors="replace")
    elements = read_element_connectivity(mesh_text)
    text = cof.read_text(encoding="utf-8", errors="replace")
    # the guard: the file must be the mapping of THIS mesh (labels of elements and nodes),
    # and, where the folder holds its own orientation piece, the mapping the decks were
    # built with (row by row; a mapping on the same numbering at other node positions has
    # the same labels and other vectors)
    reference = _orientation_reference(folder, manifest, series)
    fit = verify_orientation_file(
        text,
        element_labels=elements,
        node_labels=read_node_labels(mesh_text),
        reference_text=reference.piece_text,
        name=cof.name,
        reference_name=reference.piece_name,
    )
    if fit.reference is not None:
        print(
            f"  {cof.name} fits the mesh ({fit.elements} elements, {fit.nodes} nodes) and equals "
            f"the folder's {fit.reference} row by row"
        )
    else:
        print(
            f"  {cof.name} fits the mesh by its labels ({fit.elements} elements, {fit.nodes} "
            "nodes); the folder holds no orientation piece of this series, so a mapping on the "
            "same numbering at other node positions could not be told apart"
            + (
                f" (the decks were built with {reference.recorded_file})"
                if reference.recorded_file
                else ""
            )
        )
    orientation = read_distribution(text)
    fields = read_field_variables(text)
    card = read_converse_card(text)
    # the rate: the orientation rows are the same for every rate of one mesh, only the
    # material tables differ, so the card's name is checked against the card the decks of
    # this series were built with
    if reference.recorded_card is not None and card.name != reference.recorded_card:
        raise InputRangeError(
            f"{cof.name} holds the card {card.name}, but the decks of series {series!r} were "
            f"built with {reference.recorded_card}: the orientation file of another strain rate?"
        )
    if reference.recorded_card is not None:
        print(f"  card {card.name} as recorded for series {series}")
    else:
        print(f"  card {card.name}; the manifest records no card for series {series}, not checked")
    if fit.reference is not None:
        print(
            "  note: the row-by-row check tells a file swapped since the generation apart, not a "
            "file that was wrong at the generation already (the piece was cut from that file)"
        )
    built = an.build_nodal_anisotropy(
        first.node_labels, elements, orientation, fields, card, material.temperature_c
    )
    print(f"  {built.n} nodes, card {built.card} at {_g(built.temperature_c, 0)} °C")
    return built


@dataclass(frozen=True)
class OrientationReference:
    """What the folder records about the orientation file of one series: the folder's own
    orientation piece (``wheel_orientation_<rate>_part.inp``, cut from the file the decks were
    built with), the name of that file and the name of its material card."""

    piece_name: str | None
    piece_text: str | None
    recorded_file: str | None
    recorded_card: str | None


def _orientation_reference(
    folder: Path, manifest: dict[str, Any], series: str | None
) -> OrientationReference:
    """The folder's reference for the orientation-file guard of ``series``; Nones where the
    folder has none (a folder of the isotropic steps only, or written before the rates were
    a variant axis, which records the card under ``material_card``)."""
    rate = series.split("_")[1] if series and series.count("_") >= 1 else None
    rates = manifest.get("rates")
    entry: dict[str, Any] | None = None
    if isinstance(rates, dict):
        if rate is not None and isinstance(rates.get(rate), dict):
            entry = rates[rate]
        elif rate is None and len(rates) == 1:
            entry = next(iter(rates.values()))
    files: list[str] = []
    if entry is not None and isinstance(entry.get("orientation_files"), list):
        files = [str(f) for f in entry["orientation_files"]]
    elif isinstance(manifest.get("orientation_files"), list):
        files = [str(f) for f in manifest["orientation_files"]]
    recorded_file = Path(str(entry["file"])).name if entry and entry.get("file") else None
    recorded_card = str(entry["name"]) if entry and entry.get("name") else None
    if recorded_card is None:
        card = manifest.get("material_card")
        if isinstance(card, dict) and card.get("name"):
            recorded_card = str(card["name"])
    for name in files:
        if name.endswith("_part.inp") and (folder / name).is_file():
            text = (folder / name).read_text(encoding="utf-8", errors="replace")
            return OrientationReference(name, text, recorded_file, recorded_card)
    return OrientationReference(None, None, recorded_file, recorded_card)


def _anisotropy_rows(built: an.NodalAnisotropy) -> list[dict[str, Any]]:
    """Per node: the orientation state, the six ratios and the frame quality (the gap of the
    first orientation tensor; below 0,1 the first axis is weakly defined)."""
    gap = built.frame_gap if built.frame_gap is not None else np.full(built.n, np.nan)
    rows: list[dict[str, Any]] = []
    for i in range(built.n):
        row: dict[str, Any] = {
            "node": int(built.node_labels[i]),
            "a11": float(built.states[i, 0]),
            "a22": float(built.states[i, 1]),
            "elements": int(built.element_count[i]),
            "frame_gap": float(gap[i]),
        }
        for j, name in enumerate(an.RATIO_NAMES):
            row[name] = float(built.ratios[i, j])
        rows.append(row)
    return rows


def _frame_quality_lines(built: an.NodalAnisotropy | None, node: int) -> list[str]:
    """The frame quality of one node for the report (nothing without anisotropy)."""
    if built is None or built.frame_gap is None:
        return []
    hits = np.where(built.node_labels == node)[0]
    if hits.size == 0:
        return []
    i = int(hits[0])
    gap = float(built.frame_gap[i])
    verdict = "schwach bestimmt" if gap < 0.1 else "gut bestimmt"
    return [
        f"- Faserrahmen: a_11 {_g(float(built.states[i, 0]), 3)}, a_22 "
        f"{_g(float(built.states[i, 1]), 3)}, R_11 {_g(float(built.ratios[i, 0]), 3)}, "
        f"Eigenwertabstand {_g(gap, 3)} ({verdict}), {int(built.element_count[i])} Elemente"
    ]


def _anisotropy_lines(built: an.NodalAnisotropy, cof: Path) -> list[str]:
    ratios = built.ratios
    states = built.states
    lines = [
        "# Anisotropie je Knoten (Erweiterung E7)",
        "",
        f"- Orientierungsdatei: {cof}; Karte {built.card} bei {_g(built.temperature_c, 0)} °C",
        f"- Knoten: {built.n}; Elemente je Knoten {int(built.element_count.min())} bis "
        f"{int(built.element_count.max())}",
        f"- Orientierungszustand a_11: Mittel {_g(float(states[:, 0].mean()), 3)}, "
        f"min {_g(float(states[:, 0].min()), 3)}, max {_g(float(states[:, 0].max()), 3)}; "
        f"a_22: Mittel {_g(float(states[:, 1].mean()), 3)}",
        "- Hill-Verhältnisse (Mittel über die Knoten): "
        + ", ".join(
            f"{name} {_g(float(ratios[:, i].mean()), 3)}" for i, name in enumerate(an.RATIO_NAMES)
        ),
        f"- R_11: min {_g(float(ratios[:, 0].min()), 3)}, max {_g(float(ratios[:, 0].max()), 3)}",
    ]
    if built.frame_gap is not None:
        gap = built.frame_gap
        weak = int(np.sum(gap < 0.1))
        lines.append(
            f"- Rahmenqualität: Eigenwertabstand (λ_3 − λ_2)/λ_3 des ersten Orientierungstensors "
            f"Mittel {_g(float(gap.mean()), 3)}, min {_g(float(gap.min()), 3)}; Knoten unter 0,1: "
            f"{weak} (dort ist die erste Achse schwach bestimmt, die Elemente widersprechen sich)"
        )
    return lines


def run_stommel(args: argparse.Namespace) -> None:
    folder: Path = args.folder.resolve()
    manifest = _manifest(folder)
    figure_captions: list[str] = []
    material = mt.load_material(args.material)
    reduction_class = args.reduction_class
    if args.equivalent == "hill" and reduction_class is None:
        reduction_class = HILL_DEFAULT_CLASS
        print(
            f"Hill equivalent: reduction factors of the class {reduction_class} (the anisotropy is "
            "not counted twice; override with --reduction-class)"
        )
    if reduction_class is not None:
        material = mt.with_reduction_class(material, reduction_class)
    route: ck.AmplitudeRoute = "signed_hill" if args.equivalent == "hill" else "principal"
    if args.route:
        route = args.route
    settings = ck.CheckSettings(
        load_case=args.load_case,
        overload_case=args.case,
        amplitude_route=route,
        required_cycles=args.cycles,
        safety=args.safety,
        equivalent=args.equivalent,
    )
    steps = args.step or _load_steps(manifest)
    if not steps:
        raise InputRangeError("no load step given and the manifest names none")
    series = args.series
    if series is None:
        from gearcore.fe.evaluation import series_names

        names = series_names(manifest)
        series = names[0] if names else None
    default_out = folder / ("stommel_hill" if args.equivalent == "hill" else "stommel")
    out: Path = (args.out or default_out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    anisotropy: an.NodalAnisotropy | None = None
    if args.equivalent == "hill":
        if args.cof is None:
            raise InputRangeError("the Hill equivalent needs --cof (the CONVERSE orientation file)")
        anisotropy = _nodal_anisotropy(folder, manifest, args.cof.resolve(), material, series)
        (out / "anisotropie.md").write_text(
            "\n".join(_anisotropy_lines(anisotropy, args.cof)) + "\n", encoding="utf-8"
        )
        _write_csv(out / "anisotropie_knoten.csv", _anisotropy_rows(anisotropy))
    for step in steps:
        print(f"{step}: assembling the history of series {series} ...")
        folder_check = ck.check_folder(
            folder,
            manifest,
            material,
            settings,
            step=step,
            series=series,
            progress=lambda m: print("  " + m),
            anisotropy=anisotropy,
        )
        result = folder_check.result
        file = folder_check.stress_file
        zones = _zones(file)
        rows = [_row(result, file, zones, i) for i in range(file.n_nodes)]
        _write_csv(out / f"knoten_{step}.csv", rows)
        by_cyclic = sorted(rows, key=lambda r: -r["a_B_V"])
        by_static = sorted(rows, key=lambda r: -r["a_stat"])
        critical = by_cyclic[0]
        lines = [
            f"# Bemessung nach Stommel et al. (2018), Kapitel 6: {folder.name}, {step}, Serie {series}",
            "",
            f"Stellungen verwendet: {len(folder_check.positions_used)} (plus der unbelastete Zustand); "
            f"übersprungen: {len(folder_check.positions_skipped)}",
            "",
        ]
        if folder_check.positions_skipped:
            lines += (
                ["Übersprungen:", ""]
                + [f"- {job}: {why}" for job, why in folder_check.positions_skipped]
                + [""]
            )
        lines += _material_section(material, settings)
        above_cyclic = sum(1 for r in rows if r["a_B_V"] > 1.0)
        above_static = sum(1 for r in rows if r["a_stat"] > 1.0)
        lines += [
            "## Ergebnis",
            "",
            f"- Knoten: {len(rows)}; a_B,V > 1: {above_cyclic}; a_stat > 1: {above_static}",
            f"- größte zyklische Auslastung a_B,V = {_g(critical['a_B_V'])} an Knoten "
            f"{critical['node']} ({critical['zone']}), "
            f"vorhergesagte Lastspielzahl {critical['N_predicted']:.3g} ({critical['life_flag']})",
            f"- größte statische Auslastung a_stat = {_g(by_static[0]['a_stat'])} an Knoten "
            f"{by_static[0]['node']} ({by_static[0]['zone']})",
            "",
            "## Kritischer Knoten der zyklischen Bemessung",
            "",
            *_node_lines(critical),
            *_frame_quality_lines(anisotropy, int(critical["node"])),
            "",
            "## Kritischer Knoten der statischen Bemessung",
            "",
            *_node_lines(by_static[0]),
            *_frame_quality_lines(anisotropy, int(by_static[0]["node"])),
            "",
            f"## Die {args.top} höchsten zyklischen Auslastungen",
            "",
            *_table(
                by_cyclic[: args.top],
                [
                    ("node", "Knoten", 0),
                    ("zone", "Zone", 0),
                    ("r_mm", "r in mm", 3),
                    ("z_mm", "z in mm", 2),
                    ("h", "h", 3),
                    ("sigma_V_mpa", "σ_V in MPa", 1),
                    ("a_stat", "a_stat", 3),
                    ("a_B_V", "a_B,V", 3),
                    ("N_predicted", "N_pred", 3),
                    ("life_flag", "Bereich", 0),
                ],
            ),
            "",
            "## Größte zyklische Auslastung je Zone",
            "",
        ]
        per_zone: dict[str, dict[str, Any]] = {}
        for row in rows:
            zone = row["zone"]
            if zone not in per_zone or row["a_B_V"] > per_zone[zone]["a_B_V"]:
                per_zone[zone] = row
        lines += _table(
            sorted(per_zone.values(), key=lambda r: -r["a_B_V"]),
            [
                ("zone", "Zone", 0),
                ("node", "Knoten", 0),
                ("a_stat", "a_stat", 3),
                ("a_B_V", "a_B,V", 3),
                ("N_predicted", "N_pred", 3),
            ],
        )
        lines.append("")
        (out / f"bericht_{step}.md").write_text("\n".join(lines), encoding="utf-8")
        print(
            f"{step}: a_B,V max {critical['a_B_V']:.3f} at node {critical['node']} ({critical['zone']}), "
            f"N_pred {critical['N_predicted']:.3g}; a_stat max {by_static[0]['a_stat']:.3f}"
        )
        if not args.no_plots:
            fillet = _fillet_of(critical["zone"])
            if fillet is not None:
                _fillet_map(result, file, zones, fillet, out / f"karte_{step}_{fillet}", step)
                figure_captions.append(
                    f"- `karte_{step}_{fillet}`: zyklische Auslastung a_B,V über der Fußrundung "
                    f"{fillet.replace('_', '/')} (Winkel um die Radachse über der Zahnbreite), "
                    f"{_series_title(series, step)}."
                )
            figure_captions.append(
                f"- `verlauf_{step}`: Vergleichsspannung σ_V und vorzeichenbehaftete von-Mises-"
                "Spannung der beiden kritischen Knoten (größte zyklische und größte statische "
                f"Auslastung) über dem Wälzweg, {_series_title(series, step)}; senkrechte Linien "
                "an den Normpunkten A bis E."
            )
            nodes = [critical["node"], by_static[0]["node"]]
            # legend text per node: its role(s) on the first line, its place on the second
            whats: dict[int, list[str]] = {}
            places: dict[int, str] = {}
            for row, what in (
                (critical, "größte zyklische Auslastung $a_{\\mathrm{B,V}}$"),
                (by_static[0], "größte statische Auslastung $a_{\\mathrm{stat}}$"),
            ):
                node = int(row["node"])
                whats.setdefault(node, []).append(what)
                places[node] = (
                    f"{_zone_text(str(row['zone']))}, r {_g(row['r_mm'], 2)} mm, "
                    f"z {_g(row['z_mm'], 2)} mm"
                )
            roles = {
                node: " und ".join(what_list) + f"\n({places[node]})"
                for node, what_list in whats.items()
            }
            _position_curves(
                folder,
                manifest,
                material,
                settings,
                step,
                series,
                sorted(set(nodes)),
                out / f"verlauf_{step}",
                roles,
            )
    if figure_captions:
        (out / "bildunterschriften.md").write_text(
            "\n".join(["# Bildunterschriften", "", *figure_captions, ""]), encoding="utf-8"
        )
    print(f"written to {out}")


def run_curves(args: argparse.Namespace) -> None:
    names: list[str] = list(args.material) if args.material else list(ALL_MATERIALS)
    unknown = [name for name in names if name not in CARD_LABELS]
    if unknown:
        raise InputRangeError(f"no card label for {unknown}; known: {sorted(CARD_LABELS)}")
    materials = [mt.load_material(name) for name in names]
    out: Path = (args.out or REPO / "80_output" / "fe" / "stommel_methode_V2").resolve()
    out.mkdir(parents=True, exist_ok=True)
    lines = _method_figures(materials, args.load_case, out)
    (out / "bildunterschriften.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"written to {out}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("stommel", help="check every wheel node of a folder after Stommel et al.")
    s.add_argument(
        "--folder",
        type=Path,
        required=True,
        help="FE output folder with manifest.json and pos_*_stress.npz",
    )
    s.add_argument(
        "--step",
        action="append",
        help="load step name (default: every LOAD_* step of the manifest)",
    )
    s.add_argument(
        "--series",
        help="material step, rate and variant (default: the first series of the manifest)",
    )
    s.add_argument(
        "--material",
        default=DEFAULT_MATERIAL,
        help="material of data/fatigue/stommel_materials.yaml",
    )
    s.add_argument(
        "--load-case",
        default="einmalig",
        choices=mt.LOAD_CASES,
        help="row of Bild 6.18 for the static check",
    )
    s.add_argument(
        "--case", type=int, default=2, choices=(1, 2, 3, 4), help="overload case F1 to F4"
    )
    s.add_argument(
        "--equivalent",
        default="mises",
        choices=ck.EQUIVALENTS,
        help="equivalent stress of the static check: the book's von Mises or the Hill stress (E7)",
    )
    s.add_argument(
        "--reduction-class",
        default=None,
        choices=sorted(mt.material_classes()),
        help="class of the reduction factors (Bild 6.18); default: the material's class, under the "
        "Hill equivalent the ductile unreinforced class",
    )
    s.add_argument(
        "--cof",
        type=Path,
        default=None,
        help="CONVERSE orientation file of the wheel mesh (element orientations, field variables, card)",
    )
    s.add_argument(
        "--route", default=None, choices=ck.ROUTES, help="amplitude and mean of the cycle"
    )
    s.add_argument(
        "--cycles", type=float, default=st.LIMIT_NUMBER_OF_CYCLES, help="required number of cycles"
    )
    s.add_argument("--safety", type=float, default=1.0)
    s.add_argument("--top", type=int, default=12)
    s.add_argument("--out", type=Path)
    s.add_argument("--no-plots", action="store_true")
    s.set_defaults(func=run_stommel)
    c = sub.add_parser(
        "curves", help="the method figures of the material cards in Anlehnung an [Sto18]"
    )
    c.add_argument(
        "--material",
        nargs="*",
        default=None,
        help=f"cards to draw (default: all of {', '.join(ALL_MATERIALS)})",
    )
    c.add_argument("--load-case", default="einmalig", choices=mt.LOAD_CASES)
    c.add_argument("--out", type=Path)
    c.set_defaults(func=run_curves)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
