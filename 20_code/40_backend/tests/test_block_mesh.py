"""
@module: tests.test_block_mesh
@context: Domain-layer tests — FE rolling model, block-structured (FVA/STIRAK) gear mesher.
@role: Guard the MESHING_SPEC pipeline: conformity by the shared-node registry (no tolerance
       merge), the transfinite tooth blocks (B3 fillet / B4 core), and the section-11 finish that
       lifts the B2 2:1-reduction valence-3 nodes to det(J) ≥ 0.35 on a frozen connectivity.
"""

import math

from app.io.ste import Pair
from app.services.geometry.gear import GearStage, ToolReferenceProfile
from app.services.geometry.tooth_form import ToothProfile
from app.services.model import block_mesh as bm


def _profile() -> ToothProfile:
    tool = ToolReferenceProfile(addendum_factor=1.25, tip_radius_factor=0.38)
    stage = GearStage.from_parameters(
        normal_module_mm=1.0,
        teeth=Pair(52, 51),
        profile_shift=Pair(0.31, 0.20),
        face_width_mm=Pair(15.0, 17.0),
        tool=Pair(tool, tool),
    )
    return ToothProfile.from_stage(stage, 0)


def test_registry_conformity_no_merge() -> None:
    """Two adjacent annulus blocks share their common edge through the registry exactly once."""
    reg = bm.NodeRegistry(1e-7)
    n_ang, n_rad = 7, 9
    a = bm.coons(
        bm.arc(12, 0.0, 0.2, n_ang),
        bm.arc(24, 0.0, 0.2, n_ang),
        bm.radial(0.0, 12, 24, n_rad),
        bm.radial(0.2, 12, 24, n_rad),
    )
    reg.grid_ids(a)
    before = len(reg.coords)
    b = bm.coons(
        bm.arc(12, 0.2, 0.4, n_ang),
        bm.arc(24, 0.2, 0.4, n_ang),
        bm.radial(0.2, 12, 24, n_rad),
        bm.radial(0.4, 12, 24, n_rad),
    )
    reg.grid_ids(b)
    assert len(reg.coords) - before == n_ang * n_rad - n_rad  # shared edge merged exactly once


def test_tooth_blocks_share_dff_edge_and_quality() -> None:
    """B3 fillet band + B4 core share the d_Ff edge and mesh without flipped quads."""
    p = _profile()
    n_dicke = 5
    blk = bm.tooth_blocks(p, n_flanke=3, n_fuss=3, n_dicke=n_dicke)
    reg = bm.NodeRegistry(1e-6)
    ids3 = reg.grid_ids(blk["B3"])
    before = len(reg.coords)
    ids4 = reg.grid_ids(blk["B4"])
    assert len(reg.coords) - before == (n_dicke + 1) * 3  # B4 shares its bottom row with B3 top
    quads = bm.grid_quads(ids3, reg.coords) + bm.grid_quads(ids4, reg.coords)
    assert bm.quad_min_jac_ok(reg.coords, quads) == 0


def test_b2_reduction_finish_meets_jacobi_target() -> None:
    """Section-11 finish lifts the deep 2:1 reduction template to det(J) >= 0.35, 0 inverted,
    on a frozen connectivity (same element count before/after)."""
    reg = bm.NodeRegistry(1e-6)
    ph, r_df, r_red, r_red2, bore = math.pi / 52, 24.762, 16.0, 14.0, 12.38
    top = bm.arc(r_df, -ph, ph, 9)  # 8 segments
    fine = bm.coons(
        bm.arc(r_red, -ph, ph, 9),
        top,
        bm.radial(-ph, r_red, r_df, 8),
        bm.radial(ph, r_red, r_df, 8),
    )
    qf = bm.grid_quads(reg.grid_ids(fine), reg.coords)
    red, q2 = bm.transition_band(reg, bm.arc(r_red, -ph, ph, 9), r_red2)
    rim = bm.coons(
        bm.arc(bore, -ph, ph, len(red)),
        red,
        bm.radial(-ph, bore, r_red2, 5),
        bm.radial(ph, bore, r_red2, 5),
    )
    qr = bm.grid_quads(reg.grid_ids(rim), reg.coords)
    quads = qf + q2 + qr
    before, _ = bm.min_scaled_jac(reg.coords, quads)
    finished = bm.optimize_finish(reg.coords, quads, bm.boundary_nodes(quads), iters=60)
    worst, nbad = bm.min_scaled_jac(finished, quads)
    assert before < 0.35  # raw template is below target (valence-3 nodes)
    assert worst >= 0.35 and nbad == 0  # finish meets the FVA target
    assert bm.quad_min_jac_ok(finished, quads) == 0  # no flipped elements
    assert len(finished) == len(reg.coords)  # frozen connectivity, positions only
