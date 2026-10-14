"""S-Life Plastics against the own check after Stommel et al. on the named nodes (E4).

Reads the fixture built from the S-Life reports (``data/fatigue/slife/<name>.yaml``,
``scripts/slife_reports.py``), the stress file and the node tables of the Stommel run of the
same position, and writes ``stommel/vergleich_slife.md`` beside the node tables: per load case
the principal stresses of every node (S-Life's unaveraged element value against the averaged
nodal value of the extraction), the static check (equivalent stress, h, strains, utilisation)
and the cyclic check (amplitude, fatigue strength, cap, utilisation) of both programs with
their ratios. Cyclic details are shown where the report's table was readable.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from gearcore.data import data_path
from gearcore.fe.stress import read_stress_file
from gearcore.plot_style import german_number

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FOLDER = REPO_ROOT / "80_output" / "fe" / "kst_e" / "frozen_mesh_20layers_bore33_gerechnet"
STEP_OF = {"8 Nm": "LOAD_8NM", "12 Nm": "LOAD_12NM", "16 Nm": "LOAD_16NM"}


def _node_table(path: Path) -> dict[int, dict[str, str]]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {int(row["node"]): row for row in csv.DictReader(handle)}


def _f(value: Any, digits: int = 2) -> str:
    if value is None or value == "":
        return "–"
    number = float(value)
    if not np.isfinite(number):
        return "∞"
    return german_number(number, digits)


def _principal(components: list[float]) -> np.ndarray:
    sx, sy, sz, txy, txz, tyz = components
    t = np.array([[sx, txy, txz], [txy, sy, tyz], [txz, tyz, sz]])
    return np.asarray(np.linalg.eigvalsh(t)[::-1])


def _cell(row: dict[str, str] | None, key: str, digits: int = 2) -> str:
    return _f(row[key], digits) if row else "–"


def compare(fixture: Path, folder: Path, job: str) -> list[str]:
    data = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    nodes = {int(k): v for k, v in data["nodes"].items()}
    stress = read_stress_file(folder / f"{job}_stress.npz")
    index = {label: int(i) for label, i in zip(nodes, stress.index_of(list(nodes)), strict=True)}
    p = data["provenance"]
    lines = [
        f"# S-Life Plastics gegen den eigenen Nachweis: {job} (Stellung C), W1",
        "",
        f"S-Life {p['program']}: {p['settings']['r_load']}, {p['settings']['overloading']}, "
        f"{p['settings']['type']}, N = {p['settings']['cycle_number']}, Spannungen "
        f"{p['settings']['stresses']}, kritische Ebene {p['settings']['critical_plane']}; K = "
        f"{_f(p['K_RT_mpa'])} MPa, A_S,min {_f(p['A_S_min'])}, A_S,max {_f(p['A_S_max'])}, f_τ "
        f"{_f(p['f_tau'])}. Eigener Nachweis: gemittelte Elementknotenwerte des Tensors, Route "
        "principal, Überlastfall F2, Lastgeschichte unbelastet + Stellung C, σ_stat(h) der "
        "maßgebenden Stellung als statische Kappe. S-Life druckt den Tensor im globalen System, "
        "die Extraktion im Teilesystem des Rades (um die Instanzdrehung zurückgedreht); verglichen "
        "werden die Hauptspannungen, die davon unabhängig sind. Bei 12 Nm liegt keine Knotentabelle "
        "des eigenen Nachweises vor, dort werden nur die Spannungen verglichen.",
        "",
    ]
    for case, step in STEP_OF.items():
        table = _node_table(folder / "stommel" / f"knoten_{step}.csv")
        tensor = stress.stress(step)
        lines += [
            f"## {case} ({step})",
            "",
            "### Hauptspannungen in MPa",
            "",
            "| Knoten | S-Life Element | S-Life σ1 / σ2 / σ3 (unaveraged) | "
            "eigen σ1 / σ2 / σ3 (gemittelt) | Verhältnis der größten |",
            "|---|---|---|---|---|",
        ]
        for label, info in nodes.items():
            lc = info["load_cases"].get(case)
            own = _principal(list(tensor[index[label]]))
            own_text = f"{_f(own[0])} / {_f(own[1])} / {_f(own[2])}"
            if lc is None:
                lines.append(f"| {label} | – | – | {own_text} | – |")
                continue
            sl = lc["principal_mpa"]
            k = 0 if abs(own[0]) >= abs(own[2]) else 2
            lines.append(
                f"| {label} | {lc['element']} | {_f(sl[0])} / {_f(sl[1])} / {_f(sl[2])} | "
                f"{own_text} | {_f(sl[k] / own[k], 3)} |"
            )
        lines += [
            "",
            "### Statischer Nachweis",
            "",
            "| Knoten | S-Life σ_eq | eigen σ_V | eigen h | S-Life ε_eq / ε_zul in % | "
            "eigen ε_zul in % | S-Life a_SK | eigen a_stat | Verhältnis |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for label, info in nodes.items():
            lc = info["load_cases"].get(case)
            row = table.get(label)
            if lc is None and row is None:
                continue
            a_sl = lc["a_stat"] if lc else None
            a_own = float(row["a_stat"]) if row else None
            ratio = a_sl / a_own if a_sl is not None and a_own else None
            lines.append(
                f"| {label} | {_f(lc['sigma_eq_mpa']) if lc else '–'} | {_cell(row, 'sigma_V_mpa')} | "
                f"{_cell(row, 'h', 3)} | "
                f"{_f(lc['epsilon_eq_percent']) if lc else '–'} / "
                f"{_f(lc['epsilon_allow_percent']) if lc else '–'} | "
                f"{_cell(row, 'epsilon_zul_percent')} | {_f(a_sl, 3)} | {_f(a_own, 3)} | {_f(ratio, 3)} |"
            )
        lines += [
            "",
            "### Zyklischer Nachweis",
            "",
            "| Knoten | S-Life σ_a (maßgebende Komponente) | eigen σ_a,1 | S-Life σ_WK | eigen σ_W | "
            "S-Life Kappe σ_stat,min − σ_m | S-Life σ_BK angewandt | eigen σ_B,1 | S-Life a_BK | "
            "eigen a_B,V | Verhältnis |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for label, info in nodes.items():
            lc = info["load_cases"].get(case)
            row = table.get(label)
            if lc is None and row is None:
                continue
            sa = wk = cap = applied = a_sl = None
            if lc:
                cyc = lc["cyclic"]
                a_sl = cyc["a_BK"]
                wk = cyc["sigma_WK_first_mpa"]
                if cyc["table_complete"]:
                    k = int(np.argmax(cyc["a_BK_components"]))
                    sa = cyc["sigma_a_mpa"][k]
                    applied = cyc["sigma_BK_applied_mpa"][k]
                    cap = cyc["sigma_BK_cap_mpa"][k] if cyc["sigma_BK_cap_mpa"] else None
            a_own = float(row["a_B_V"]) if row else None
            ratio = a_sl / a_own if a_sl is not None and a_own and np.isfinite(a_own) else None
            lines.append(
                f"| {label} | {_f(sa)} | {_cell(row, 'sigma_a_1_mpa')} | {_f(wk)} | "
                f"{_cell(row, 'sigma_W_mpa')} | {_f(cap)} | {_f(applied)} | "
                f"{_cell(row, 'sigma_B_1_mpa')} | {_f(a_sl, 2)} | {_f(a_own, 3)} | {_f(ratio, 2)} |"
            )
        lines.append("")
    lines += ["## Anmerkungen der Transkription", ""] + [f"- {n}" for n in p.get("notes", [])]
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default="pos_C_W1_QS")
    parser.add_argument("--folder", type=Path, default=DEFAULT_FOLDER)
    parser.add_argument("--job", default="pos_001")
    args = parser.parse_args(argv)
    fixture = data_path("fatigue", "slife", f"{args.fixture}.yaml")
    lines = compare(fixture, args.folder, args.job)
    target = args.folder / "stommel" / "vergleich_slife.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"-> {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
