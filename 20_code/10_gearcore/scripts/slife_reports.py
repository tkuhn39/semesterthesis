"""Transcribe the S-Life Plastics assessment reports (PDF) into the E4 fixture.

The user exports, per load case folder ``<T>-Nm`` and node, a static and a cyclic report
(``*_Plastics_SSK_Static_<node>.pdf``, ``*_Plastics_SSK_Cyclic_<node>.pdf``). The text layer of
the reports (``pdftotext -layout``, read as UTF-8) interleaves the label column and the value
column, so this script reads only lines whose label is unambiguous and checks the arithmetic
between them (amplitude / applied strength = component ratio). Every number in the fixture
comes from a report; the principal values are computed from the transcribed tensor. Output:
``data/fatigue/slife/<name>.yaml``.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from gearcore.data import data_path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPORTS = REPO_ROOT / "70_input" / "74_S-Life"
NUMBER = r"(-?\d+(?:\.\d+)?)"
FOUR = rf"{NUMBER}[ ]+{NUMBER}[ ]+{NUMBER}[ ]+{NUMBER}"


def _text(pdf: Path) -> str:
    out = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return re.sub(r"[ \t]+", " ", out.stdout)


def _one(pattern: str, text: str, what: str, name: str) -> str:
    found = re.search(pattern, text, flags=re.MULTILINE)
    if found is None:
        raise ValueError(f"{name}: {what} not found ({pattern!r})")
    return found.group(1)


def _four(pattern: str, text: str) -> list[float] | None:
    """Four numbers of a table row, or None where the text layer splits or marks the row."""
    found = re.search(pattern, text, flags=re.MULTILINE)
    if found is None:
        return None
    return [float(found.group(k)) for k in range(1, 5)]


def _tensor(text: str, name: str) -> dict[str, float]:
    rows = []
    for axis in ("x", "y", "z"):
        rows.append(
            [float(v) for v in re.findall(rf"^{axis} {NUMBER} {NUMBER} {NUMBER}$", text, re.M)[0]]
        )
    t = np.array(rows)
    if not np.allclose(t, t.T, atol=1.0e-3):
        raise ValueError(f"{name}: the printed tensor is not symmetric")
    return {
        "sx": float(t[0, 0]),
        "sy": float(t[1, 1]),
        "sz": float(t[2, 2]),
        "txy": float(t[0, 1]),
        "txz": float(t[0, 2]),
        "tyz": float(t[1, 2]),
    }


def _principal(tensor: dict[str, float]) -> list[float]:
    t = np.array(
        [
            [tensor["sx"], tensor["txy"], tensor["txz"]],
            [tensor["txy"], tensor["sy"], tensor["tyz"]],
            [tensor["txz"], tensor["tyz"], tensor["sz"]],
        ]
    )
    return [float(v) for v in np.linalg.eigvalsh(t)[::-1]]


def parse_static(pdf: Path) -> dict[str, Any]:
    name, text = pdf.name, _text(pdf)
    tensor = _tensor(text, name)
    principal = _principal(tensor)
    eps_eq = float(_one(rf"^Assessment eq,ex1 \[%\] {NUMBER}", text, "eps_eq", name))
    return {
        "load_case": _one(r"load case name (LC\d)", text, "load case", name),
        "element": int(_one(r"^element (\d+)$", text, "element", name)),
        "averaging": _one(r"^averaging (\w+)$", text, "averaging", name),
        "tensor_mpa": tensor,
        "principal_mpa": principal,
        "sigma_eq_mpa": float(
            _one(rf"control parameter eq,q,ex1 \[MPa\] {NUMBER}", text, "sigma_eq", name)
        ),
        "epsilon_eq_percent": eps_eq,
        "epsilon_allow_percent": float(
            _one(rf"S,allow,ex1 \[%\] {NUMBER}", text, "eps_allow", name)
        ),
        "sigma_allow_mpa": float(_one(rf"S,allow,ex1 \[MPa\] {NUMBER}", text, "sigma_allow", name)),
        "sigma_allow_min_mpa": float(
            _one(rf"S,allow,ex2 \[MPa\] {NUMBER}", text, "sigma_allow_min", name)
        ),
        "a_stat": float(
            _one(r"The static utilization ratio is (\d+(?:\.\d+)?)%", text, "a_stat", name)
        )
        / 100.0,
    }


def parse_cyclic(pdf: Path) -> dict[str, Any]:
    name, text = pdf.name, _text(pdf)
    amplitude = _four(rf"^\(fully reversed\) {FOUR}$", text)
    sigma_wk = _four(rf"WK \[MPa\] {FOUR}$", text)
    cap = _four(rf"AK \* KBK \(as computed\) BK \[MPa\] {FOUR}$", text)
    applied = _four(rf"component fatigue strength limit BK,max \[MPa\] {FOUR}$", text)
    ratios = _four(rf"individual stress components a,1 / BK {FOUR}$", text)
    complete = all(v is not None for v in (amplitude, applied, ratios))
    if complete:
        assert amplitude is not None and applied is not None and ratios is not None
        for a, s_applied, r in zip(amplitude, applied, ratios, strict=True):
            if s_applied > 0.0 and abs(a / s_applied - r) > 0.02 * max(r, 1.0):
                raise ValueError(
                    f"{name}: amplitude / applied strength does not give the printed ratio"
                )
    sigma_wk_scalar = float(_one(rf"WK \[MPa\] {NUMBER}", text, "sigma_WK", name))
    return {
        "load_case": _one(r"load case name (LC\d)", text, "load case", name),
        "element": int(_one(r"^element (\d+)$", text, "element", name)),
        "critical_plane_step_deg": float(
            _one(rf"^FEA stress computation {NUMBER}", text, "step angle", name)
        ),
        "components": ["x", "y", "z", "xy"],
        "sigma_a_mpa": amplitude,
        "sigma_WK_mpa": sigma_wk,
        "sigma_WK_first_mpa": sigma_wk_scalar,
        "table_complete": complete,
        "sigma_BK_cap_mpa": cap,
        "sigma_BK_applied_mpa": applied,
        "a_BK_components": ratios,
        "a_BK": float(_one(r"The cyclic utilization ratio is (\d+(?:\.\d+)?)%", text, "a_BK", name))
        / 100.0,
    }


def build(reports: Path) -> dict[str, Any]:
    nodes: dict[int, dict[str, Any]] = {}
    material: dict[str, Any] = {}
    for folder in sorted(reports.glob("*-Nm"), key=lambda f: int(f.name.split("-")[0])):
        torque = int(folder.name.split("-")[0])
        for pdf in sorted(folder.glob("*_Static_*.pdf")):
            node = int(pdf.stem.rsplit("_", 1)[1])
            static = parse_static(pdf)
            cyclic_pdf = next(folder.glob(f"*_Cyclic_{node}.pdf"))
            cyclic = parse_cyclic(cyclic_pdf)
            if cyclic["load_case"] != static["load_case"]:
                raise ValueError(f"{pdf.name}: static and cyclic report disagree on the load case")
            # each report takes the most severe element of its own check at the node
            entry = nodes.setdefault(node, {"load_cases": {}})
            entry["load_cases"][f"{torque} Nm"] = {
                "static_report": str(pdf.relative_to(REPO_ROOT)).replace("\\", "/"),
                "cyclic_report": str(cyclic_pdf.relative_to(REPO_ROOT)).replace("\\", "/"),
                **static,
                "cyclic": {k: v for k, v in cyclic.items() if k != "load_case"},
            }
            if not material:
                text = _text(pdf)
                material = {
                    "program": _one(
                        r"generated with S-Life Plastics (S-Life Plastics [\d.]+)",
                        text,
                        "version",
                        pdf.name,
                    ),
                    "material": "PA46 GF30, filler QS card (reports: 'Material PA46 GF30', 'Filler QS')",
                    "K_RT_mpa": float(
                        _one(rf"Limit type \(EoC\)1\) {NUMBER}", text, "K", pdf.name)
                    ),
                    "sigma_EoC_80C_mpa": float(_one(rf"^ {NUMBER}$", text, "EoC 80", pdf.name)),
                    "A_S_min": float(
                        _one(rf"limit scale factor AS,min {NUMBER}", text, "A_S_min", pdf.name)
                    ),
                    "A_S_max": float(
                        _one(rf"min\. influence factor AS,max {NUMBER}", text, "A_S_max", pdf.name)
                    ),
                    "f_tau": float(_one(rf"^ f {NUMBER}$", text, "f_tau", pdf.name)),
                }
    return {
        "provenance": {
            "source": "S-Life Plastics assessment reports exported by the user on 2026-10-14 (70_input/74_S-Life)",
            "result_file": "80_output/fe/kst_e/frozen_mesh_20layers_bore33_gerechnet/pos_001.odb",
            "model": "position C, W1 (linear elastic, isotropic row of the QS card at 80 °C), Abaqus 2025",
            "settings": {
                "r_load": "Purely pulsating (R = 0)",
                "overloading": "F2 Stress Ratio Constant",
                "type": "Ultimate Fatigue Limit",
                "cycle_number": 10000000,
                "stresses": "unaveraged (element-nodal value of one element at the node)",
                "critical_plane": "on, step angle 11,25 deg",
                "service_temperature_c": 80,
            },
            "transcribed_by": "scripts/slife_reports.py (pdftotext text layer, "
            "labels checked by arithmetic)",
            "notes": [
                "load cases LC1, LC2, LC3 are the increments 6 of LOAD_8NM, LOAD_12NM, "
                "LOAD_16NM (folder names of the user)",
                "node 6193 (beneath the fillet surface) has no report: S-Life evaluates surface nodes only",
                "the text layer shifts labels against values by one row in the cyclic tables; "
                "the rows were assigned by their arithmetic (amplitude / applied strength = "
                "component ratio, checked); the degree of multiaxiality h and the mean stress "
                "factor K_AK are not transcribed because their rows are split in the text layer",
                "the stress table typed by the user on 2026-10-14 (LC1 values) is superseded by the report tensors",
            ],
            **material,
        },
        "nodes": nodes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--name", default="pos_C_W1_QS")
    args = parser.parse_args(argv)
    data = build(args.reports)
    target = data_path("fatigue", "slife", f"{args.name}.yaml")
    target.write_text(
        "# Generated by scripts/slife_reports.py from the S-Life Plastics reports; do not edit.\n"
        + yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=110),
        encoding="utf-8",
    )
    cases = sum(len(n["load_cases"]) for n in data["nodes"].values())
    print(f"{len(data['nodes'])} nodes, {cases} load cases -> {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
