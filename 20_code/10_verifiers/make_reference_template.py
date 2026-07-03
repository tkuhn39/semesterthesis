"""
@module: 10_verifiers.make_reference_template
@context: Verifier — reference-mesh ground-truth mining (ADR-019).
@role: Regenerate the committed sector templates in ``40_backend/app/services/model/data/`` from
       the reference deck and print the pinned topology metrics for both gear parts. Run from
       ``20_code/`` with the project conda env:

           python 10_verifiers/make_reference_template.py
"""

from __future__ import annotations

import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT / "40_backend"))

from app.services.model.reference_slice import (  # noqa: E402
    REFERENCE_DECK,
    extract_template,
    measure,
    mid_slice,
    parse_part,
)

REPO_ROOT = CODE_ROOT.parent
DATA_DIR = CODE_ROOT / "40_backend" / "app" / "services" / "model" / "data"


def main() -> None:
    # Only the wheel (Part_Rad_Vz_1, the plastic thesis-critical side) is mined: it is a clean
    # uniform z-sweep. The steel pinion part is NOT (1979 z-levels, hexes spanning 4 levels,
    # bowtie-prone slice) and the generator applies the wheel-derived FVA/STIRAK pattern to any
    # gear anyway; in mixed pairings the steel side becomes a rigid shell (ADR-019).
    deck = REPO_ROOT / REFERENCE_DECK
    DATA_DIR.mkdir(exist_ok=True)
    for part in ("Part_Rad_Vz_1",):
        nodes, elems = parse_part(deck, part)
        quads, coords = mid_slice(nodes, elems)
        metrics = measure(quads, coords)
        print(f"\n=== {part}: {len(nodes)} nodes, {len(elems)} hexes ===")
        print(f"slice: {metrics.n_quads} quads, {metrics.n_nodes} nodes")
        print(f"interior valence: {metrics.interior_valence}")
        print(f"boundary valence: {metrics.boundary_valence}")
        print(f"irregular interior nodes ({len(metrics.irregular)}):")
        for nid, valence, r, theta_deg in metrics.irregular:
            print(f"  node {nid}: v={valence} r={r:.3f} theta={theta_deg:.2f} deg")
        print(f"rim grid: {metrics.rim_rings} rings x {metrics.rim_cols} cols")
        print(
            f"min scaled Jacobian {metrics.min_scaled_jacobian:.3f}, "
            f"cells<0.35: {metrics.cells_below_035}"
        )
        template = extract_template(quads, coords, part)
        slug = part.lower().replace("part_", "")
        out = DATA_DIR / f"reference_sector_{slug}.json"
        template.to_json(out)
        print(f"template: {out} ({out.stat().st_size / 1024:.0f} KiB)")
        print(f"meta: {template.meta}")
        print(f"surface nodes on contour: {len(template.surface_order)}")


if __name__ == "__main__":
    main()
