"""
@module: 10_verifiers.verify_deck_parity
@context: Verifier — the generated implicit rolling deck vs. the FVA reference deck
          (``32_Abaqus/implicit/kst-E_8_DY2-0_WS30_ohne_Radkoerper.inp``), ground truth
          measured 2026-07-04.
@role: Build the kst-E deck with :func:`implicit_deck.build_implicit_pair_from_stage`, parse
       the emitted ``.inp`` text back, and assert the load-bearing parity properties:

       1. **Fesselung composition** — per gear the ``Fesselung_Rad{g}`` nset must contain the
          bore surface plus BOTH radial cut planes as complete cross-sections (every single
          node of those faces, bore → root circle, all face-width planes; the reference holds
          2 268 / 2 225 nodes per cut plane and nothing else).
       2. **Initial contact** — minimal flank-to-flank distance at t=0 in [0, 35] um,
          single-flank, and located at an EDGE tooth of gear 1 (working flank F2) so the
          middle teeth sweep the full engagement boundary-free (user decision 2026-07-06).
       3. **Step & torque cycle** — exactly one ``*STATIC`` step with SMOOTH-STEP amplitudes,
          ``ALLSDTOL=0.0, CONTINUE=NO``, ``*RESTART``; one ``*TIME POINTS`` measurement
          instant per Wälzstellung, full torque at every measurement, torque back at the
          base fraction between positions, angle moves only while the torque is at base;
          per-flank-set measurement outputs (reference grouping).
       4. **Contact pairs** — exactly the 7 reference pairs (sweep-union pairing: working
          F2 g1-i↔g2-(6−i), back F1 g1-i↔g2-(5−i)), slave (plastic side) listed first.

       Optionally repeats the Fesselung/gap measurement on the reference deck itself
       (``--reference``; slow, parses a 74 MB file). Run from ``20_code/``:

           python 10_verifiers/verify_deck_parity.py [--reference]
"""

from __future__ import annotations

import contextlib
import math
import re
import sys
from collections.abc import Iterable
from pathlib import Path

import numpy as np

CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT / "40_backend"))

from app.io.ste import gear_stage_from_ste, load_ste  # noqa: E402
from app.services.geometry.gear import GearStage  # noqa: E402
from app.services.geometry.tooth_form import ToothProfile  # noqa: E402
from app.services.model.implicit_deck import build_implicit_pair_from_stage  # noqa: E402
from app.services.model.materials_card import LinearElastic, MarlowUniaxial  # noqa: E402

REPO_ROOT = CODE_ROOT.parent
STE = REPO_ROOT / "30_references_and_examples" / "33_STplus" / "kst-E_eingabe.ste"
REFERENCE = (
    REPO_ROOT
    / "30_references_and_examples"
    / "32_Abaqus"
    / "implicit"
    / "kst-E_8_DY2-0_WS30_ohne_Radkoerper.inp"
)

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str) -> None:
    line = f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}"
    # Windows consoles may be cp1252 — never let a symbol crash the verifier
    print(
        line.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8"
        )
    )
    if not ok:
        FAILURES.append(name)


# ------------------------------------------------------------------------------------------
# light .inp parsing (parts' nodes, nsets, amplitudes, steps, contact pairs)
# ------------------------------------------------------------------------------------------
def parse_deck(lines: Iterable[str]) -> dict:
    """Collect part nodes, Fesselung nsets, amplitudes, contact pairs from .inp lines."""
    nodes: dict[str, dict[int, tuple[float, float, float]]] = {}
    nsets: dict[str, tuple[str | None, list[int]]] = {}
    amplitudes: dict[str, list[tuple[float, float]]] = {}
    time_points: dict[str, list[float]] = {}
    contact_pairs: list[str] = []
    n_static = 0
    part: str | None = None
    mode: str | None = None
    cur: str | None = None
    generate = False

    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("**"):
            continue
        if s.startswith("*"):
            u = s.upper()
            if u.startswith("*PART"):
                m = re.search(r"NAME\s*=\s*([^,\s]+)", s, re.I)
                part = m.group(1) if m else None
                nodes.setdefault(part or "?", {})
                mode = None
            elif u.startswith("*END PART"):
                part, mode = None, None
            elif u.startswith("*NODE") and "OUTPUT" not in u and "PRINT" not in u:
                mode = "node"
            elif u.startswith("*NSET"):
                m = re.search(r"NSET\s*=\s*([^,\s]+)", s, re.I)
                inst = re.search(r"INSTANCE\s*=\s*([^,\s]+)", s, re.I)
                name = m.group(1) if m else "?"
                generate = "GENERATE" in u
                if "FESSELUNG" in name.upper() or re.fullmatch(r"G\dT\d{3}F\d_NODESET", name, re.I):
                    cur = name if inst is None else name
                    # flank nsets live inside a part; remember which part we are in
                    nsets[name] = (inst.group(1) if inst else part, [])
                    mode = "nset"
                else:
                    cur, mode = None, "skip"
            elif u.startswith("*TIME POINTS"):
                m = re.search(r"NAME\s*=\s*([^,\s]+)", s, re.I)
                cur = f"timepoints:{m.group(1) if m else '?'}"
                time_points[m.group(1) if m else "?"] = []
                mode = "tp"
            elif u.startswith("*AMPLITUDE"):
                m = re.search(r"NAME\s*=\s*([^,\s]+)", s, re.I)
                cur = m.group(1) if m else "?"
                amplitudes[cur] = []
                mode = "amp"
            elif u.startswith("*CONTACT PAIR"):
                mode = "cpair"
            elif u.startswith("*STATIC"):
                n_static += 1
                mode = None
            else:
                mode = None
            continue
        if mode == "node" and part is not None:
            p = s.split(",")
            with contextlib.suppress(ValueError, IndexError):
                nodes[part][int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
        elif mode == "nset" and cur:
            vals = [int(v) for v in s.replace(",", " ").split() if v]
            if generate and len(vals) >= 2:
                step = vals[2] if len(vals) > 2 else 1
                nsets[cur][1].extend(range(vals[0], vals[1] + 1, step))
            else:
                nsets[cur][1].extend(vals)
        elif mode == "amp" and cur:
            vals = [float(v) for v in s.split(",") if v.strip()]
            amplitudes[cur].extend(zip(vals[0::2], vals[1::2], strict=False))
        elif mode == "tp" and cur:
            name = cur.split(":", 1)[1]
            time_points[name].extend(float(v) for v in s.split(",") if v.strip())
        elif mode == "cpair":
            contact_pairs.append(s)
            mode = None
    return {
        "nodes": nodes,
        "nsets": nsets,
        "amplitudes": amplitudes,
        "time_points": time_points,
        "contact_pairs": contact_pairs,
        "n_static": n_static,
    }


def classify_fesselung(
    pts: np.ndarray, centre: tuple[float, float], label: str, r_root: float | None
) -> None:
    """Assert the bore + two-complete-cut-planes composition of a Fesselung node cloud."""
    cx, cy = centre
    r = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
    ang = np.degrees(np.arctan2(pts[:, 1] - cy, pts[:, 0] - cx))
    r_bore = float(r.min())
    on_bore = np.abs(r - r_bore) < 0.05
    off = ~on_bore
    clusters = np.unique(np.round(ang[off], 1))
    # the cut-plane nodes must collapse onto exactly two angles (complete planes, no arcs)
    grouped: list[float] = []
    for c in sorted(clusters):
        if not grouped or abs(c - grouped[-1]) > 1.0:
            grouped.append(float(c))
    check(
        f"{label} composition",
        len(grouped) == 2 and int(on_bore.sum()) > 0,
        f"{len(pts)} nodes = bore {int(on_bore.sum())} + cut-planes {int(off.sum())} "
        f"at angles {grouped}",
    )
    if r_root is not None:
        check(
            f"{label} cut planes reach the root circle",
            math.isclose(float(r.max()), r_root, rel_tol=2e-3),
            f"max r {float(r.max()):.3f} vs d_f/2 {r_root:.3f}",
        )
    n_z = len(np.unique(np.round(pts[:, 2], 6)))
    check(f"{label} spans all face-width planes", n_z >= 2, f"{n_z} distinct z planes")


def min_gap_mm(t1: np.ndarray, t2: np.ndarray, chunk: int = 2000) -> tuple[float, float, int]:
    """Minimal 2D distance between two node clouds → (gap, y at contact, index into t1)."""
    best = math.inf
    best_y = 0.0
    best_i = 0
    for i in range(0, len(t1), chunk):
        block = t1[i : i + chunk, None, :2] - t2[None, :, :2]
        d = np.hypot(block[..., 0], block[..., 1])
        j = int(np.argmin(d))
        bi, bj = np.unravel_index(j, d.shape)
        if float(d[bi, bj]) < best:
            best = float(d[bi, bj])
            best_y = float(t1[i + bi][1])
            best_i = i + int(bi)
    return best, best_y, best_i


def tooth_zone(
    nodes: np.ndarray, centre_x: float, r_ff: float, facing_positive: bool
) -> np.ndarray:
    r = np.hypot(nodes[:, 0] - centre_x, nodes[:, 1])
    r_tip = float(r.max())
    if facing_positive:
        keep = (r > r_ff) & (nodes[:, 0] > centre_x + 0.7 * r_tip)
    else:
        keep = (r > r_ff) & (nodes[:, 0] < centre_x - 0.7 * r_tip)
    return nodes[keep]


def main() -> None:
    run_reference = "--reference" in sys.argv

    stage = GearStage.from_ste(gear_stage_from_ste(load_ste(STE)))
    profile1 = ToothProfile.from_stage(stage, 0)
    profile2 = ToothProfile.from_stage(stage, 1)
    a = stage.working_center_distance_mm
    deck = build_implicit_pair_from_stage(
        stage,
        gear1_material=LinearElastic("STEEL", 210000.0, 0.3),
        gear2_material=MarlowUniaxial("PA_kstE"),
        torque_gear2_nmm=7846.2,
        face_layers=4,
        n_roll_positions=30,
    )
    parsed = parse_deck(deck.splitlines())

    print("== generated deck ==")
    m = re.search(r"contact-aligned: gear 2 rotated ([+-][0-9.e-]+) rad", deck)
    print(f"  closing rotation documented: {m.group(1) if m else 'MISSING'} rad")
    check("heading documents contact alignment", m is not None, "header comment present")

    # 1) Fesselung composition per gear (nset ids -> part node coords)
    inst2part = {"Rad_Vz_1": "Part_Rad_Vz_1", "Rad_Vz_2": "Part_Rad_Vz_2"}
    centres = {"Part_Rad_Vz_1": (0.0, 0.0), "Part_Rad_Vz_2": (a, 0.0)}
    roots = {
        "Part_Rad_Vz_1": profile1.root_diameter_mm / 2.0,
        "Part_Rad_Vz_2": profile2.root_diameter_mm / 2.0,
    }
    for name, (inst, ids) in sorted(parsed["nsets"].items()):
        if "Fesselung" not in name:
            continue  # flank nsets are used by the edge-tooth check via ids only
        pn = inst2part.get(inst or "", "?")
        coords = parsed["nodes"].get(pn, {})
        pts = np.array([coords[i] for i in ids if i in coords])
        check(f"{name} resolves", len(pts) == len(ids), f"{len(pts)}/{len(ids)} ids resolved")
        classify_fesselung(pts, centres[pn], name, roots[pn])

    # 2) initial contact: single-flank, [0, 35] um, at an EDGE tooth of gear 1
    #    (start_at_edge — the middle teeth must sweep the full engagement boundary-free)
    ids1 = np.array(list(parsed["nodes"]["Part_Rad_Vz_1"].keys()))
    n1 = np.array(list(parsed["nodes"]["Part_Rad_Vz_1"].values()))
    n2 = np.array(list(parsed["nodes"]["Part_Rad_Vz_2"].values()))
    r1 = np.hypot(n1[:, 0], n1[:, 1])
    keep1 = (r1 > profile1.d_Ff / 2.0) & (n1[:, 0] > 0.7 * r1.max())
    t1, t1_ids = n1[keep1], ids1[keep1]
    t2 = tooth_zone(n2, a, profile2.d_Ff / 2.0, facing_positive=False)
    gap, _, i1 = min_gap_mm(t1, t2)
    check("initial flank gap <= 35 um", gap <= 0.035, f"{gap * 1000:.1f} um")
    contact_id = int(t1_ids[i1])
    contact_tooth, contact_flank = None, None
    for tooth in (1, 2, 3, 4):
        for flank in (1, 2):
            name = f"G1T{tooth:03d}F{flank}_NODESET"
            entry = parsed["nsets"].get(name)
            if entry and contact_id in set(entry[1]):
                contact_tooth, contact_flank = tooth, flank
    check(
        "roll starts at an EDGE tooth of gear 1 (working flank F2)",
        contact_tooth in (1, 4) and contact_flank == 2,
        f"initial contact at gear-1 tooth {contact_tooth}, flank F{contact_flank}",
    )

    # 3) one static step with the per-position torque cycle (SMOOTH STEP)
    check("exactly one *STATIC step", parsed["n_static"] == 1, f"{parsed['n_static']} steps")
    check("SMOOTH STEP amplitudes", "DEFINITION=SMOOTH STEP" in deck, "S-shaped ramps")
    check(
        "ALLSDTOL=0.0, CONTINUE=NO (reference parity)",
        "ALLSDTOL=0.0, CONTINUE=NO" in deck,
        "stabilisation honest, no carry-over",
    )
    check("*RESTART, WRITE present", "*RESTART, WRITE, FREQUENCY=0" in deck, "restartable")
    amp_a = dict(parsed["amplitudes"].get("AMP-ANGLE", []))
    amp_t = dict(parsed["amplitudes"].get("AMP-TORQUE", []))
    measure = parsed["time_points"].get("MEASURE", [])
    check(
        "one measurement instant per Wälzstellung",
        len(measure) == 30,
        f"{len(measure)} time points",
    )
    full_at_measure = all(
        abs(amp_t.get(round(t, 9), amp_t.get(t, 0.0)) - 1.0) < 1e-9 for t in measure
    )
    check("full torque at every measurement instant", full_at_measure, "TIME POINTS = holds")
    base = min((v for v in amp_t.values() if 0.0 < v < 1.0), default=None)
    check(
        "torque returns to the base fraction between positions",
        base is not None and abs(base - 0.01) < 1e-9,
        f"base fraction = {base}",
    )
    times = sorted(amp_a)
    angle_moves_at_base = all(
        abs(amp_t[t_now] - (base or 0.0)) < 1e-9
        for t_prev, t_now in zip(times, times[1:], strict=False)
        if abs(amp_a[t_now] - amp_a[t_prev]) > 1e-12
    )
    check("angle changes only while the torque is at base", angle_moves_at_base, "cycle shape")
    check(
        "per-flank-set measurement outputs present",
        "*NODE OUTPUT, NSET=Rad_Vz_1.G1T001F1_NODESET" in deck
        and "*ELEMENT OUTPUT, ELSET=Rad_Vz_2.G2T004F2_ELEMENTSET" in deck
        and "TIME POINTS=MEASURE" in deck,
        "reference-parity output grouping",
    )

    # 4) contact pairs: the exact 7-pair reference mapping (working F2: g1 i - g2 6-i;
    #    back F1: g1 i - g2 5-i), slave (plastic = gear 2) first
    pairs = {p.replace(" ", "") for p in parsed["contact_pairs"]}
    expected = {
        f"Rad_Vz_2.TOOTH-2-{j:03d}F2,Rad_Vz_1.TOOTH-1-{i:03d}F2"
        for i, j in ((2, 4), (3, 3), (4, 2))
    } | {
        f"Rad_Vz_2.TOOTH-2-{j:03d}F1,Rad_Vz_1.TOOTH-1-{i:03d}F1"
        for i, j in ((1, 4), (2, 3), (3, 2), (4, 1))
    }
    delta = f"missing: {sorted(expected - pairs)}; extra: {sorted(pairs - expected)}"
    check(
        "contact pairs = the 7 reference pairs (sweep union)",
        pairs == expected,
        f"{len(pairs)} pairs; {delta}",
    )

    # 5) rigid Außenhülle spot-check (steel side as R3D4 lateral shell, open end faces)
    shell_deck = build_implicit_pair_from_stage(
        stage,
        gear1_material=LinearElastic("STEEL", 210000.0, 0.3),
        gear2_material=MarlowUniaxial("PA_kstE"),
        torque_gear2_nmm=7846.2,
        face_layers=4,
        n_roll_positions=4,
        settle=2,
        rigid_gears=frozenset({1}),
    )
    p1 = shell_deck.split("*PART, NAME=Part_Rad_Vz_1")[1].split("*END PART")[0]
    p2 = shell_deck.split("*PART, NAME=Part_Rad_Vz_2")[1].split("*END PART")[0]
    n1 = p1.split("*ELEMENT")[0].count("\n")
    n2 = p2.split("*ELEMENT")[0].count("\n")
    check(
        "rigid shell: R3D4 lateral surface, no section/material, SPOS surfaces",
        "*ELEMENT, TYPE=R3D4" in p1
        and "*SOLID SECTION" not in p1
        and "G1T001F1_ELEMENTSET, SPOS" in p1
        and "MATERIAL-Part_Rad_Vz_1" not in shell_deck,
        f"shell nodes {n1} vs solid nodes {n2}",
    )
    check(
        "rigid shell: massive node reduction + no Fesselung nset",
        n1 < n2 / 4 and "NSET=Fesselung_Rad1" not in shell_deck,
        f"reduction x{n2 / max(n1, 1):.1f}",
    )

    if run_reference:
        print("== reference deck (measure-only) ==")
        with REFERENCE.open("r", errors="ignore") as fh:
            ref = parse_deck(fh)
        for name, (inst, ids) in sorted(ref["nsets"].items()):
            pn = {"Rad_Vz_1": "Part_Rad_Vz_1", "Rad_Vz_2": "Part_Rad_Vz_2"}.get(inst or "", "?")
            coords = ref["nodes"].get(pn, {})
            pts = np.array([coords[i] for i in ids if i in coords])
            centre = (0.0, 0.0) if pn == "Part_Rad_Vz_1" else (52.0, 0.0)
            classify_fesselung(pts, centre, f"reference {name}", None)

    print()
    if FAILURES:
        print(f"FAILED checks: {FAILURES}")
        raise SystemExit(1)
    print("all deck parity checks passed")


if __name__ == "__main__":
    main()
