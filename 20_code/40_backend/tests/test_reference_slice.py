"""
@module: tests.test_reference_slice
@context: Domain-layer tests — reference-mesh ground-truth mining (ADR-019).
@role: Pin the measured topology of the ANSA/FVA reference wheel slice (the target the block
       mesher must reproduce) and guard the committed sector template against going stale.
"""

from pathlib import Path

import pytest

from app.services.model.reference_slice import (
    REFERENCE_DECK,
    SectorTemplate,
    extract_template,
    load_reference_template,
    measure,
    mid_slice,
    parse_part,
)

_DECK = Path(__file__).resolve().parents[3] / REFERENCE_DECK

pytestmark = pytest.mark.skipif(not _DECK.exists(), reason="reference deck not present")


@pytest.fixture(scope="module")
def wheel_slice() -> tuple[list, dict]:
    nodes, elems = parse_part(_DECK, "Part_Rad_Vz_1")
    assert len(nodes) == 269_649
    assert len(elems) == 241_920
    return mid_slice(nodes, elems)


def test_wheel_slice_topology_pinned(wheel_slice: tuple[list, dict]) -> None:
    """The measured ground truth: fully conformal, one fan node per gap, 26x25 rim grid."""
    quads, coords = wheel_slice
    metrics = measure(quads, coords)
    assert metrics.n_quads == 3024
    assert metrics.n_nodes == 3329
    # All interior nodes valence 4 except exactly one fan-convergence node per tooth gap:
    # valence 6 under the three mid-sector gaps, valence 5 at the two sector-edge gaps.
    assert metrics.interior_valence == {4: 2716, 5: 2, 6: 3}
    assert [v for _, v, _, _ in metrics.irregular] == [5, 6, 6, 6, 5]
    assert all(abs(r - 23.379) < 1e-2 for _, _, r, _ in metrics.irregular)
    # Fan nodes sit on the rim-top ring one pitch apart (z=52 -> 6.923 deg).
    gaps = [t for _, _, _, t in metrics.irregular]
    steps = [b - a for a, b in zip(gaps, gaps[1:], strict=False)]
    assert all(abs(s - 360.0 / 52.0) < 0.01 for s in steps)
    # Structured polar rim grid and the reference's own quality level.
    assert metrics.rim_rings == 26
    assert metrics.rim_cols == 25
    assert metrics.min_scaled_jacobian == pytest.approx(0.243, abs=5e-3)
    assert metrics.cells_below_035 == 24


def test_committed_template_matches_fresh_extraction(wheel_slice: tuple, tmp_path: Path) -> None:
    """The committed JSON template is regenerable from the deck (no silent drift)."""
    quads, coords = wheel_slice
    fresh = extract_template(quads, coords, "Part_Rad_Vz_1")
    committed = load_reference_template("Part_Rad_Vz_1")
    assert committed.meta == fresh.meta
    assert committed.quads.shape == fresh.quads.shape
    assert committed.nodes.shape == fresh.nodes.shape
    assert committed.kind == fresh.kind
    assert committed.surface_order == fresh.surface_order
    # Round-trip through JSON is stable.
    fresh.to_json(tmp_path / "t.json")
    again = SectorTemplate.from_json(tmp_path / "t.json")
    assert again.meta == fresh.meta


def test_template_internal_consistency() -> None:
    """The committed template is self-consistent (loadable without the reference deck)."""
    template = load_reference_template("Part_Rad_Vz_1")
    n = len(template.nodes)
    assert template.quads.min() >= 0
    assert template.quads.max() < n
    assert len(template.kind) == n
    assert set(template.kind) <= {"interior", "surface", "bore", "cut"}
    assert len(template.surface_order) == 527
    assert all(template.kind[i] == "surface" for i in template.surface_order)
    assert template.meta["n_quads"] == 3024
