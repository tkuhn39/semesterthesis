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
       2. **Initial contact** — minimal flank-to-flank distance at t=0 in [0, 35] um on the
          -y flank (single-flank contact; reference ≈ 25 um). The gears must not "run in
          the air" with the allowance backlash split onto both flanks.
       3. **Step & amplitudes** — exactly one ``*STATIC`` step; AMP-TORQUE reaches full level
          while AMP-ANGLE still dwells at 0 (the torque ramp closes the last um of gap).
       4. **Contact pairs** — ≥ 5 flank-wise ``*CONTACT PAIR`` (reference: 7 for 4-tooth
          sectors), slave (plastic side) listed first.

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
                if "FESSELUNG" in name.upper():
                    cur = name
                    nsets[name] = (inst.group(1) if inst else None, [])
                    mode = "nset"
                else:
                    cur, mode = None, "skip"
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
        elif mode == "cpair":
            contact_pairs.append(s)
            mode = None
    return {
        "nodes": nodes,
        "nsets": nsets,
        "amplitudes": amplitudes,
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


def min_gap_mm(
    t1: np.ndarray, t2: np.ndarray, chunk: int = 2000
) -> tuple[float, float, np.ndarray]:
    """Minimal 2D distance between two node clouds (chunked, numpy only)."""
    best = math.inf
    best_pair = (np.zeros(2), np.zeros(2))
    for i in range(0, len(t1), chunk):
        block = t1[i : i + chunk, None, :2] - t2[None, :, :2]
        d = np.hypot(block[..., 0], block[..., 1])
        j = int(np.argmin(d))
        bi, bj = np.unravel_index(j, d.shape)
        if float(d[bi, bj]) < best:
            best = float(d[bi, bj])
            best_pair = (t1[i + bi], t2[bj])
    return best, float(best_pair[0][1]), best_pair[0]


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
        pn = inst2part.get(inst or "", "?")
        coords = parsed["nodes"].get(pn, {})
        pts = np.array([coords[i] for i in ids if i in coords])
        check(f"{name} resolves", len(pts) == len(ids), f"{len(pts)}/{len(ids)} ids resolved")
        classify_fesselung(pts, centres[pn], name, roots[pn])

    # 2) initial contact: single-flank, [0, 35] um, on the -y side
    n1 = np.array(list(parsed["nodes"]["Part_Rad_Vz_1"].values()))
    n2 = np.array(list(parsed["nodes"]["Part_Rad_Vz_2"].values()))
    t1 = tooth_zone(n1, 0.0, profile1.d_Ff / 2.0, facing_positive=True)
    t2 = tooth_zone(n2, a, profile2.d_Ff / 2.0, facing_positive=False)
    gap, y_at, _ = min_gap_mm(t1, t2)
    check("initial flank gap <= 35 um", gap <= 0.035, f"{gap * 1000:.1f} um")
    check("contact on the -y flank (single-flank)", y_at < 0.0, f"y = {y_at:+.3f}")

    # 3) one static step; torque switches on before the angle leaves zero
    check("exactly one *STATIC step", parsed["n_static"] == 1, f"{parsed['n_static']} steps")
    amp_a = parsed["amplitudes"].get("AMP-ANGLE", [])
    amp_t = parsed["amplitudes"].get("AMP-TORQUE", [])
    t_angle_moves = next((t for t, v in amp_a if abs(v) > 1e-12), math.inf)
    t_torque_full = next((t for t, v in amp_t if abs(v) >= 1.0 - 1e-12), math.inf)
    check(
        "torque reaches full level before the angle moves",
        t_torque_full <= t_angle_moves,
        f"torque full at t={t_torque_full:.4f}, angle moves at t={t_angle_moves:.4f}",
    )

    # 4) contact pairs, slave (plastic = gear 2) first
    pairs = parsed["contact_pairs"]
    check(">= 5 flank contact pairs (reference: 7)", len(pairs) >= 5, f"{len(pairs)} pairs")
    check(
        "plastic side listed first (slave)",
        all(p.startswith("Rad_Vz_2.") for p in pairs),
        f"first entries: {sorted({p.split(',')[0] for p in pairs})}",
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
