"""
@module: app.services.model.gmsh_mesher
@context: Domain layer — FE rolling model, the gmsh-backed tooth/rim mesher.
@role: Mesh the gear tooth pitch (tooth + root fillet + rim) from the native STplus
       tooth profile with gmsh — the robust path the hand-rolled structured fan could
       not deliver (the trochoid fillet folds). Builds the exact STplus outline, sizes
       the mesh per the FVA-377 parameters (fine at the fillet), recombines to quads,
       and returns node/quad arrays (later: extrude → C3D8 hex, write Abaqus `.inp`).
       Sits behind the `Mesher` interface so a native STIRAK port can replace it later
       at the same seam. Spur gears (β = 0); transverse plane, tooth centred on +y.
"""

import math

import gmsh
import numpy as np
from numpy.typing import NDArray

from app.services.geometry.tooth_form import ToothProfile
from app.services.model.tooth_mesh import Mesh2D

Array = NDArray[np.float64]


def _profile_outline(profile: ToothProfile, samples: int) -> tuple[Array, float, float]:
    """Right-half tooth surface (tip → fillet bottom d_f) + the fillet-bottom angle."""
    pts = profile.right_flank_profile(fillet_points=samples, flank_points=samples)
    surface = np.array([[p[0], p[1]] for p in pts])[::-1]  # tip → d_f (root)
    df = surface[-1]
    a_df = math.atan2(df[0], df[1])
    return surface, a_df, profile.root_diameter_mm / 2.0


def mesh_tooth_pitch(
    profile: ToothProfile,
    *,
    height_elements: int = 20,
    root_elements: int = 40,
    thickness_elements: int = 5,
    rim_depth_mm: float | None = None,
    boundary_samples: int = 60,
) -> Mesh2D:
    """Quad mesh of one tooth pitch (tooth + half-gaps + rim) via gmsh.

    Element sizes follow the FVA-377 counts: the fillet curve carries ``root_elements``
    (the fine root), the flank ``height_elements``, the tooth ``thickness_elements``;
    the rim is coarser. ``rim_depth_mm`` is the rim below the root circle (default 2·m_n).
    """
    surface, a_df, r_root = _profile_outline(profile, boundary_samples)
    pitch_half = math.pi / profile.z
    rim_inner = r_root - (rim_depth_mm if rim_depth_mm is not None else 2.0 * profile.mn)

    # element sizes from the FVA counts
    flank_len = float(np.sum(np.linalg.norm(np.diff(surface, axis=0), axis=1)))
    s_flank = flank_len / max(height_elements, 1)
    s_fillet = (a_df * r_root) / max(root_elements, 1) + 1e-3  # fillet arc / count
    s_root = max(s_flank, s_fillet)

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    try:
        gmsh.model.add("tooth_pitch")
        geo = gmsh.model.geo

        def pt(x: float, y: float, size: float) -> int:
            return geo.addPoint(float(x), float(y), 0.0, size)

        # right-half surface points (tip → d_f), sized: fine on the fillet (r ≤ d_Ff)
        d_ff = profile.d_Ff / 2.0
        right_tags = []
        for x, y in surface:
            r = math.hypot(x, y)
            right_tags.append(pt(x, y, s_fillet if r <= d_ff + 1e-9 else s_flank))
        # mirror the surface (left half), tip shared
        left_tags = []
        for x, y in surface[::-1]:  # d_f → tip
            r = math.hypot(x, y)
            left_tags.append(pt(-x, y, s_fillet if r <= d_ff + 1e-9 else s_flank))

        # root-floor points (right d_f → +gap centre) and (−gap centre → left d_f)
        rf_r = pt(r_root * math.sin(pitch_half), r_root * math.cos(pitch_half), s_root)
        rf_l = pt(-r_root * math.sin(pitch_half), r_root * math.cos(pitch_half), s_root)
        # rim / cut corners
        b_r = pt(rim_inner * math.sin(pitch_half), rim_inner * math.cos(pitch_half), s_flank * 2)
        b_l = pt(-rim_inner * math.sin(pitch_half), rim_inner * math.cos(pitch_half), s_flank * 2)

        loop_pts = (
            [b_l, rf_l] + left_tags + right_tags[1:] + [rf_r, b_r]
        )  # bore-left → up → over tooth → down → bore-right
        lines = [geo.addLine(loop_pts[i], loop_pts[i + 1]) for i in range(len(loop_pts) - 1)]
        # close with the bore arc (b_r → b_l about the gear centre)
        centre = pt(0.0, 0.0, s_flank)
        lines.append(geo.addCircleArc(b_r, centre, b_l))

        loop = geo.addCurveLoop(lines)
        geo.addPlaneSurface([loop])
        geo.synchronize()

        gmsh.option.setNumber("Mesh.RecombineAll", 1)
        gmsh.option.setNumber("Mesh.Algorithm", 8)  # Frontal-Delaunay for quads
        gmsh.option.setNumber("Mesh.RecombinationAlgorithm", 1)
        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", s_flank * 2.0)
        gmsh.model.mesh.generate(2)

        node_tags, coords, _ = gmsh.model.mesh.getNodes()
        coords = np.array(coords).reshape(-1, 3)[:, :2]
        tag_index = {int(t): i for i, t in enumerate(node_tags)}
        quad_type = 3  # 4-node quad
        _, elem_node_tags = gmsh.model.mesh.getElementsByType(quad_type)
        quads = np.array([tag_index[int(t)] for t in elem_node_tags]).reshape(-1, 4)
        return Mesh2D(coords, quads)
    finally:
        gmsh.finalize()
