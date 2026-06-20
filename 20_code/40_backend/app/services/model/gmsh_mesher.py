"""
@module: app.services.model.gmsh_mesher
@context: Domain layer — FE rolling model, the gmsh-backed tooth/rim mesher.
@role: Mesh the gear tooth pitch (tooth + root fillet + rim) from the native STplus
       tooth profile with gmsh — the robust path the hand-rolled structured fan could
       not deliver (the trochoid fillet folds). Builds the exact STplus outline, sizes
       the mesh per the FVA-377 parameters (fine at the fillet), recombines to quads,
       and extrudes over the face width to **C3D8 hexahedra**. Returns node/element
       arrays for the assembly (`model.assembly`) → Abaqus `.inp`. Sits behind the
       `Mesher` seam so a native STIRAK port can replace it later at the same spot.
       Spur gears (β = 0); transverse plane, tooth centred on +y, extruded along +z.
"""

import math

import gmsh
import numpy as np
from numpy.typing import NDArray

from app.services.geometry.tooth_form import ToothProfile
from app.services.model.tooth_mesh import Mesh2D

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]


class Mesh3D:
    """A 3-D mesh: ``nodes`` (N, 3) and 8-node ``hexes`` (M, 8) node indices."""

    def __init__(self, nodes: Array, hexes: IntArray, *, quality: Array | None = None) -> None:
        self.nodes = np.asarray(nodes, dtype=float)
        self.hexes = np.asarray(hexes, dtype=int)
        self.quality = quality  # gmsh scaled-Jacobian per hex (the FVA "Jacobi-Güte")

    @property
    def n_nodes(self) -> int:
        return int(self.nodes.shape[0])

    @property
    def n_hexes(self) -> int:
        return int(self.hexes.shape[0])


def _build_pitch_surface(
    profile: ToothProfile,
    *,
    height_elements: int,
    root_elements: int,
    rim_depth_mm: float | None,
    boundary_samples: int,
) -> tuple[int, float]:
    """Build the one-pitch tooth+rim plane surface in the active gmsh model.

    Returns the surface tag and the flank element size (the mesh-size reference).
    """
    pts = profile.right_flank_profile(fillet_points=boundary_samples, flank_points=boundary_samples)
    surface = np.array([[p[0], p[1]] for p in pts])[::-1]  # tip → d_f (root)
    a_df = math.atan2(surface[-1][0], surface[-1][1])
    r_root = profile.root_diameter_mm / 2.0
    d_ff = profile.d_Ff / 2.0
    pitch_half = math.pi / profile.z
    rim_inner = r_root - (rim_depth_mm if rim_depth_mm is not None else 2.0 * profile.mn)

    flank_len = float(np.sum(np.linalg.norm(np.diff(surface, axis=0), axis=1)))
    s_flank = flank_len / max(height_elements, 1)
    s_fillet = (a_df * r_root) / max(root_elements, 1) + 1e-3
    s_root = max(s_flank, s_fillet)

    geo = gmsh.model.geo

    def pt(x: float, y: float, size: float) -> int:
        return geo.addPoint(float(x), float(y), 0.0, size)

    right = [pt(x, y, s_fillet if math.hypot(x, y) <= d_ff + 1e-9 else s_flank) for x, y in surface]
    left = [
        pt(-x, y, s_fillet if math.hypot(x, y) <= d_ff + 1e-9 else s_flank)
        for x, y in surface[::-1]
    ]
    rf_r = pt(r_root * math.sin(pitch_half), r_root * math.cos(pitch_half), s_root)
    rf_l = pt(-r_root * math.sin(pitch_half), r_root * math.cos(pitch_half), s_root)
    b_r = pt(rim_inner * math.sin(pitch_half), rim_inner * math.cos(pitch_half), s_flank * 2)
    b_l = pt(-rim_inner * math.sin(pitch_half), rim_inner * math.cos(pitch_half), s_flank * 2)
    centre = pt(0.0, 0.0, s_flank)

    loop_pts = [b_l, rf_l] + left + right[1:] + [rf_r, b_r]
    lines = [geo.addLine(loop_pts[i], loop_pts[i + 1]) for i in range(len(loop_pts) - 1)]
    lines.append(geo.addCircleArc(b_r, centre, b_l))  # bore arc closes the loop
    surf = geo.addPlaneSurface([geo.addCurveLoop(lines)])
    geo.synchronize()
    return surf, s_flank


def _rotate(points: Array, angle: float) -> Array:
    c, s = math.cos(angle), math.sin(angle)
    return points @ np.array([[c, s], [-s, c]])


def _tooth_outline(profile: ToothProfile, boundary_samples: int) -> tuple[Array, Array]:
    """One tooth outline (left fillet bottom → tip → right fillet bottom) + per-point on-fillet flag."""
    pts = profile.right_flank_profile(fillet_points=boundary_samples, flank_points=boundary_samples)
    right = np.array([[p[0], p[1]] for p in pts])  # d_f → d_Na (root → tip)
    left = right * np.array([-1.0, 1.0])  # mirror, d_f → tip
    outline = np.vstack([left, right[::-1][1:]])  # left d_f→tip, then tip→d_f right
    radii = np.hypot(outline[:, 0], outline[:, 1])
    on_fillet = radii <= profile.d_Ff / 2.0 + 1e-9
    return outline, on_fillet


def _sector_boundary(
    profile: ToothProfile, n_teeth: int, n_segments: int
) -> tuple[Array, Array, float]:
    """Outer boundary of the gear sector (n_teeth teeth + n_segments rim-only pitches each side).

    Returns the ordered boundary points, an on-fillet flag per point (for sizing), and
    the sector half-angle.
    """
    pitch = 2.0 * math.pi / profile.z
    total = n_teeth + 2 * n_segments
    half_sector = total * pitch / 2.0
    r_root = profile.root_diameter_mm / 2.0
    outline, on_fillet = _tooth_outline(profile, 40)
    a_df = math.atan2(outline[0, 0], outline[0, 1])  # left fillet-bottom angle (negative)

    pts: list[Array] = []
    flags: list[bool] = []

    def root_arc(a0: float, a1: float, n: int = 6) -> None:
        for a in np.linspace(a0, a1, n)[1:]:
            pts.append(np.array([r_root * math.sin(a), r_root * math.cos(a)]))
            flags.append(False)

    pts.append(np.array([r_root * math.sin(-half_sector), r_root * math.cos(-half_sector)]))
    flags.append(False)
    for p in range(total):
        centre = (p - (total - 1) / 2.0) * pitch
        is_tooth = n_segments <= p < n_segments + n_teeth
        if is_tooth:
            root_arc(math.atan2(pts[-1][0], pts[-1][1]), centre + a_df)
            # skip outline[0]: it coincides with the root-arc end (avoids a zero-length edge)
            for (x, y), f in zip(_rotate(outline, centre)[1:], on_fillet[1:], strict=True):
                pts.append(np.array([x, y]))
                flags.append(bool(f))
        # else: a tooth-free pitch — the root floor continues (added by the next arc)
    root_arc(math.atan2(pts[-1][0], pts[-1][1]), half_sector)
    return np.array(pts), np.array(flags), half_sector


def _quad_recombine_options(s_flank: float) -> None:
    gmsh.option.setNumber("Mesh.RecombineAll", 1)
    gmsh.option.setNumber("Mesh.Algorithm", 8)  # Frontal-Delaunay for quads
    gmsh.option.setNumber("Mesh.RecombinationAlgorithm", 1)
    gmsh.option.setNumber("Mesh.SubdivisionAlgorithm", 1)  # force all-quad (→ all-hex on extrude)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", s_flank * 2.0)


def mesh_tooth_pitch(
    profile: ToothProfile,
    *,
    height_elements: int = 20,
    root_elements: int = 40,
    thickness_elements: int = 5,
    rim_depth_mm: float | None = None,
    boundary_samples: int = 60,
) -> Mesh2D:
    """Quad mesh of one tooth pitch (tooth + half-gaps + rim) via gmsh (2-D section)."""
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    try:
        gmsh.model.add("tooth_pitch")
        _, s_flank = _build_pitch_surface(
            profile,
            height_elements=height_elements,
            root_elements=root_elements,
            rim_depth_mm=rim_depth_mm,
            boundary_samples=boundary_samples,
        )
        _quad_recombine_options(s_flank)
        gmsh.model.mesh.generate(2)
        return _extract_2d()
    finally:
        gmsh.finalize()


def mesh_tooth_pitch_3d(
    profile: ToothProfile,
    *,
    face_width_mm: float,
    face_layers: int,
    height_elements: int = 20,
    root_elements: int = 40,
    thickness_elements: int = 5,
    rim_depth_mm: float | None = None,
    boundary_samples: int = 60,
) -> Mesh3D:
    """C3D8 hex mesh of one tooth pitch, extruded ``face_layers`` over the face width."""
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    try:
        gmsh.model.add("tooth_pitch_3d")
        surf, s_flank = _build_pitch_surface(
            profile,
            height_elements=height_elements,
            root_elements=root_elements,
            rim_depth_mm=rim_depth_mm,
            boundary_samples=boundary_samples,
        )
        _quad_recombine_options(s_flank)
        gmsh.model.mesh.generate(2)
        section, quality = _extract_2d_quality()
    finally:
        gmsh.finalize()
    return extrude_to_hex(section, quality, width=face_width_mm, layers=face_layers)


def mesh_sector_3d(
    profile: ToothProfile,
    *,
    n_teeth: int,
    n_segments: int,
    face_width_mm: float,
    face_layers: int,
    height_elements: int = 20,
    root_elements: int = 40,
    thickness_elements: int = 5,
    rim_depth_mm: float | None = None,
) -> Mesh3D:
    """C3D8 hex mesh of a gear sector: ``n_teeth`` teeth + ``n_segments`` rim-only pitches each side.

    The sector (gear-body) angle = (n_teeth + 2·n_segments)·360°/z. Extruded
    ``face_layers`` over the face width.

    WIP: the multi-tooth outer boundary self-intersects on the trochoid fillet fold
    (gmsh 1-D mesh intersections) — being fixed; the single-pitch ``mesh_tooth_pitch_3d``
    is the working meshing primitive meanwhile.
    """
    boundary, flags, half_sector = _sector_boundary(profile, n_teeth, n_segments)
    r_root = profile.root_diameter_mm / 2.0
    rim_inner = r_root - (rim_depth_mm if rim_depth_mm is not None else 2.0 * profile.mn)
    flank_len = float(
        np.sum(np.linalg.norm(np.diff(_tooth_outline(profile, 40)[0], axis=0), axis=1))
    )
    s_flank = 0.5 * flank_len / max(height_elements, 1)
    s_fillet = (abs(math.atan2(boundary[0, 0], boundary[0, 1])) * r_root) / max(root_elements, 1)
    s_fillet = max(s_fillet, 1e-3)

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    try:
        gmsh.model.add("sector")
        geo = gmsh.model.geo
        tags = [
            geo.addPoint(float(x), float(y), 0.0, s_fillet if f else s_flank)
            for (x, y), f in zip(boundary, flags, strict=True)
        ]
        b_l = geo.addPoint(
            rim_inner * math.sin(-half_sector), rim_inner * math.cos(-half_sector), 0, s_flank * 2
        )
        b_r = geo.addPoint(
            rim_inner * math.sin(half_sector), rim_inner * math.cos(half_sector), 0, s_flank * 2
        )
        centre = geo.addPoint(0.0, 0.0, 0.0, s_flank)
        loop_pts = [b_l] + tags + [b_r]
        lines = [geo.addLine(loop_pts[i], loop_pts[i + 1]) for i in range(len(loop_pts) - 1)]
        lines.append(geo.addCircleArc(b_r, centre, b_l))
        surf = geo.addPlaneSurface([geo.addCurveLoop(lines)])
        geo.synchronize()
        _quad_recombine_options(s_flank)
        gmsh.model.mesh.generate(2)
        section, quality = _extract_2d_quality()
    finally:
        gmsh.finalize()
    return extrude_to_hex(section, quality, width=face_width_mm, layers=face_layers)


def extrude_to_hex(section: Mesh2D, quad_quality: Array, *, width: float, layers: int) -> Mesh3D:
    """Extrude a 2-D quad section into C3D8 hexahedra (``layers`` over the face ``width``).

    Done natively (replicate the section nodes per z-layer; one hex per quad × layer) so
    it is robust to gmsh's surface-extrusion quirks on complex sector boundaries. The hex
    Jacobi-Güte equals the section quad's (orthogonal extrusion), tiled over the layers.
    """
    n = section.n_nodes
    z = np.linspace(0.0, width, layers + 1)
    nodes = np.empty(((layers + 1) * n, 3))
    for k in range(layers + 1):
        nodes[k * n : (k + 1) * n, :2] = section.nodes
        nodes[k * n : (k + 1) * n, 2] = z[k]
    q = section.quads
    hexes = np.empty((layers * q.shape[0], 8), dtype=int)
    for k in range(layers):
        block = slice(k * q.shape[0], (k + 1) * q.shape[0])
        hexes[block, :4] = q + k * n
        hexes[block, 4:] = q + (k + 1) * n
    quality = np.tile(quad_quality, layers)
    return Mesh3D(nodes, hexes, quality=quality)


def _extract_2d() -> Mesh2D:
    node_tags, coords, _ = gmsh.model.mesh.getNodes()
    pts = np.array(coords).reshape(-1, 3)[:, :2]
    index = {int(t): i for i, t in enumerate(node_tags)}
    _, conn = gmsh.model.mesh.getElementsByType(3)  # 4-node quad
    quads = np.array([index[int(t)] for t in conn]).reshape(-1, 4)
    return Mesh2D(pts, quads)


def _extract_2d_quality() -> tuple[Mesh2D, Array]:
    node_tags, coords, _ = gmsh.model.mesh.getNodes()
    pts = np.array(coords).reshape(-1, 3)[:, :2]
    index = {int(t): i for i, t in enumerate(node_tags)}
    elem_tags, conn = gmsh.model.mesh.getElementsByType(3)  # 4-node quad
    quads = np.array([index[int(t)] for t in conn]).reshape(-1, 4)
    quality = np.array(gmsh.model.mesh.getElementQualities(elem_tags, "minSJ"))  # = Jacobi-Güte
    return Mesh2D(pts, quads), quality
