"""Evidence for the choices STplus makes for the inspection dimensions: k and D_M.

STplus 11.1F prints the span over a number of teeth k and the ball dimension over a measuring
ball D_M that it chooses itself where the input gives neither. The manual does not say how. The
rules were found by experiment on 2026-10-04 (switch points of k and D_M bisected over the tip
diameter and the profile shift, then checked on random gears); they live in
``gearcore.stplus_program`` (``stplus_number_of_teeth_spanned``, ``stplus_measuring_ball_diameter``).

This script reruns the evidence with the local installation and stores it in
``src/gearcore/data/stplus_program/inspection_choices.json``:

  table   every D_M the program prints while the module runs from 0,3 to 70 mm (z 30 / 61)
  gears   random gears (seeded): what the listing prints for z, m_n, alpha_n, beta, x_E, d_a,
          d_Ff, d_Fa, and the k and D_M it chose

Usage:  python scripts/stplus_inspection_choices.py [--stplus-root <dir>]

The installation is licensed and not part of the repository; the stored file is.
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import random
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import stplus_oracle as oracle

TARGET = (
    oracle.PKG_ROOT / "src" / "gearcore" / "data" / "stplus_program" / "inspection_choices.json"
)
MODULES = (0.4, 0.5, 0.8, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 14.0, 20.0)
GROUPS: tuple[dict[str, Any], ...] = (
    {
        "name": "general",
        "seed": 11,
        "pairs": 150,
        "z1": (9, 80),
        "z2": (20, 130),
        "modules": MODULES,
        "helix": (0, 0, 0, 5, 8, 10, 12, 15, 18, 20, 23, 25, 28, 30, 33, 35, 40),
    },
    {
        "name": "few teeth, small modules",
        "seed": 5,
        "pairs": 60,
        "z1": (7, 16),
        "z2": (17, 40),
        "modules": (0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7, 0.8, 1.0, 1.25, 1.5, 2.0),
        "helix": (0, 0, 0, 5, 10, 15, 20, 25, 30, 35),
    },
    {
        "name": "many teeth, large helix angles",
        "seed": 7,
        "pairs": 60,
        "z1": (60, 220),
        "z2": (60, 260),
        "modules": MODULES,
        "helix": (25, 28, 30, 33, 35, 38, 40, 43, 45),
    },
)
"""The random gears: number of pairs, ranges of the numbers of teeth, modules and helix angles."""
ROWS = {
    "x_E": r"Erz\.-Profilversch\.faktor",
    "D_M": r"Messtueckdurchmesser",
    "k": r"Messzaehnezahl  ",
    "d_a": r"Kopfkreisdurchmesser  ",
    "d_Fa": r"Kopf-Formkreisdurchmesser",
    "d_Ff": r"Fuss-Formkreisdurchmesser",
}
"""Rows of the listing that are read, by their label."""


def ste(
    z: tuple[int, int],
    m_n: float,
    x: tuple[float, float],
    beta: float,
    alpha: float,
    d_a: tuple[float | None, float | None],
    tool: tuple[float, float],
) -> str:
    """Input file of a pair generated with a rack tool (addendum factor, tip radius factor)."""
    lines = [
        "$ Anfang",
        "",
        "$ Geometriedaten",
        f"ZAHNBREITE = {15 * m_n:g} {15 * m_n:g}",
        f"NORMALMODUL = {m_n}",
        f"EINGRIFFSWINKEL = {alpha}",
        f"SCHRAEGUNGSWINKEL = {beta}",
        f"ZAEHNEZAHL = {z[0]} {z[1]}",
        f"PROFILVERSCHIEBUNG_N = {x[0]} {x[1]}",
    ]
    if d_a[0] is not None or d_a[1] is not None:
        tips = " ".join("%" if value is None else str(value) for value in d_a)
        lines.append(f"KOPFKREISDM = {tips}")
    lines.append("WERKZEUG_VORVERZ. = WKZ_1 WKZ_2")
    text = "\n".join(lines) + "\n"
    for index in (1, 2):
        text += (
            f"\n$ WKZ_{index}\nKOPFHOEHENFAKTOR = {tool[0]}\nKOPFABRUNDUNGSFAKTOR = {tool[1]}\n"
            f"WKZ_NORMALMODUL = {m_n}\nWKZ_EINGRIFFSWINKEL = {alpha}\n"
        )
    return text + "\n$ Ende\n"


def run(root: Path, scratch: Path, text: str) -> str:
    """The listing STplus writes for the input ``text``; empty where it writes none."""
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    (scratch / "eingabe.ste").write_text(
        oracle.prepare_ste(text, 0.005), encoding="latin-1", newline="\r\n"
    )
    oracle.write_cfg(scratch, root)
    for companion in oracle.COMPANIONS:
        source = root / "bin" / companion
        if source.is_file():
            shutil.copy2(source, scratch / companion)
    subprocess.run(
        [str(root / "bin" / "STplus.exe"), "--CFG", str(scratch / "stplus.cfg")],
        cwd=str(scratch),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    listing = scratch / "ausgabe.sta"
    return listing.read_text(encoding="latin-1") if listing.is_file() else ""


def numbers(listing: str, label: str) -> list[float]:
    """The numbers at the end of the first row of the listing that begins with ``label``."""
    for line in listing.splitlines():
        if re.match(rf"^\s*{label}", line) and "=" not in line:
            values: list[float] = []
            for token in reversed(line.split()):
                if re.fullmatch(r"-?\d+(\.\d+)?", token):
                    values.insert(0, float(token))
                elif values:
                    break
            if values:
                return values
    return []


def gears(
    listing: str, z: tuple[int, int], m_n: float, beta: float, alpha: float
) -> list[dict[str, float]]:
    """One record per gear of the listing; none where a row is missing."""
    rows = {key: numbers(listing, label) for key, label in ROWS.items()}
    if any(len(values) < 2 for values in rows.values()):
        return []
    return [
        {
            "z": z[index],
            "m_n": m_n,
            "alpha_n_deg": alpha,
            "beta_deg": beta,
            **{key: values[index] for key, values in rows.items()},
        }
        for index in range(2)
    ]


def table_values(root: Path, scratch: Path) -> list[float]:
    """Every D_M the program prints while the module runs from 0,3 to 70 mm."""
    seen: set[float] = set()
    m_n = 0.3
    while m_n < 70.0:
        module = round(m_n, 4)
        listing = run(
            root, scratch, ste((30, 61), module, (0.0, 0.0), 0.0, 20.0, (None, None), (1.25, 0.25))
        )
        seen.update(numbers(listing, ROWS["D_M"])[:2])
        m_n *= 1.012
    return sorted(seen - {0.0})


def random_gears(root: Path, scratch: Path, group: dict[str, Any]) -> list[dict[str, float]]:
    rng = random.Random(group["seed"])
    found: list[dict[str, float]] = []
    for _ in range(group["pairs"]):
        z = (rng.randint(*group["z1"]), rng.randint(*group["z2"]))
        m_n = rng.choice(group["modules"])
        beta = float(rng.choice(group["helix"]))
        alpha = float(rng.choice((20, 20, 20, 20, 17.5, 22.5, 25)))
        x = (round(rng.uniform(-0.3, 0.8), 3), round(rng.uniform(-0.4, 0.6), 3))
        tool = (rng.choice((1.25, 1.25, 1.2, 1.4, 1.5)), rng.choice((0.25, 0.2, 0.3, 0.38)))
        tips: list[float | None] = []
        for teeth, shift in zip(z, x, strict=True):
            if rng.random() < 0.5:
                tips.append(None)
            else:
                d = teeth * m_n / math.cos(math.radians(beta))
                tips.append(round(d + 2 * m_n * (1 + shift + rng.uniform(-0.35, 0.45)), 3))
        listing = run(root, scratch, ste(z, m_n, x, beta, alpha, (tips[0], tips[1]), tool))
        found.extend(gears(listing, z, m_n, beta, alpha))
    return found


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stplus-root", default=None)
    args = parser.parse_args(argv)
    root = Path(args.stplus_root) if args.stplus_root else oracle.DEFAULT_STPLUS_ROOT
    if not (root / "bin" / "STplus.exe").is_file():
        raise SystemExit(f"no STplus installation at {root}")
    with tempfile.TemporaryDirectory(prefix="stplus_choices_") as folder:
        scratch = Path(folder) / "run"
        table = table_values(root, scratch)
        groups = [
            {
                **{key: group[key] for key in ("name", "seed", "pairs")},
                "gears": random_gears(root, scratch, group),
            }
            for group in GROUPS
        ]
    payload = {
        "program": "STplus",
        "version": "11.1F",
        "generated": datetime.date.today().isoformat(),
        "note": (
            "Printed values of listings of STplus 11.1F, written by scripts/stplus_inspection_choices.py. "
            "table: every measuring ball diameter the program chose while the module ran from 0,3 to "
            "70 mm; gears: z, m_n, alpha_n, beta as given, x_E, d_a, d_Fa, d_Ff, k and D_M as printed."
        ),
        "table_mm": table,
        "groups": groups,
    }
    TARGET.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8", newline="\n")
    total = sum(len(group["gears"]) for group in groups)
    print(f"{len(table)} table values, {total} gears -> {TARGET}")


if __name__ == "__main__":
    main()
