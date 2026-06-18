"""
@module: app.services.model.tooth_mesh
@context: Domain layer — FE rolling model, the structured tooth mesh (replaces STIRAK).
@role: Turn the native STplus transverse tooth profile (`geometry.tooth_form.ToothProfile`)
       into a **structured quad mesh** of one tooth column — the repeating unit of the
       gear FE mesh, later extruded over the face width to C3D8R hexahedra. v1 meshes the
       **involute flank** d_Ff → d_Na on constant-radius arcs (the flanks are the exact
       left/right boundaries), radius-graded toward the root form for a finer base. The
       **root fillet + rim** (d_f → d_Ff, carrying the 30°-tangent critical section) is a
       separate transition block (next step) — like the reference mesh it fans into the
       rim rather than the tooth column. Owning the mesh is the lever for FE convergence
       and run-time. Spur gears (β = 0); transverse plane, tooth centred on +y.
"""

import numpy as np
from numpy.typing import NDArray

from app.services.geometry.tooth_form import ToothProfile

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]


class Mesh2D:
    """A 2-D structured quad mesh: ``nodes`` (N, 2) and ``quads`` (M, 4) CCW indices."""

    def __init__(self, nodes: Array, quads: IntArray) -> None:
        self.nodes = np.asarray(nodes, dtype=float)
        self.quads = np.asarray(quads, dtype=int)

    @property
    def n_nodes(self) -> int:
        return int(self.nodes.shape[0])

    @property
    def n_quads(self) -> int:
        return int(self.quads.shape[0])

    def element_areas(self) -> Array:
        """Signed area of each quad (shoelace); all-positive ⇒ no inverted/degenerate cells."""
        p = self.nodes[self.quads]  # (M, 4, 2)
        x, y = p[..., 0], p[..., 1]
        return 0.5 * (
            x[:, 0] * y[:, 1]
            - x[:, 1] * y[:, 0]
            + x[:, 1] * y[:, 2]
            - x[:, 2] * y[:, 1]
            + x[:, 2] * y[:, 3]
            - x[:, 3] * y[:, 2]
            + x[:, 3] * y[:, 0]
            - x[:, 0] * y[:, 3]
        )

    def radii(self) -> Array:
        return np.hypot(self.nodes[:, 0], self.nodes[:, 1])

    def aspect_ratios(self) -> Array:
        """Per-quad longest/shortest edge ratio (FE shape quality; ~1 is ideal)."""
        p = self.nodes[self.quads]
        edges = np.linalg.norm(p - np.roll(p, -1, axis=1), axis=2)
        return edges.max(axis=1) / np.maximum(edges.min(axis=1), 1e-12)


def _resample_radial(points: Array, count: int, root_bias: float) -> Array:
    """Resample the root→tip boundary at ``count`` levels **by radius**, root-graded.

    Radius is monotonic root→tip, so spacing levels by radius (not the curvy fillet
    arc length) keeps the rows clean; ``root_bias`` > 1 packs more levels near the
    fillet (small radius) for the 30°-tangent section.
    """
    r = np.hypot(points[:, 0], points[:, 1])
    order = np.argsort(r)
    r, pts = r[order], points[order]
    u = np.linspace(0.0, 1.0, count)
    r_target = r[0] + (r[-1] - r[0]) * u**root_bias
    x = np.interp(r_target, r, pts[:, 0])
    y = np.interp(r_target, r, pts[:, 1])
    return np.column_stack([x, y])


def tooth_sector_2d(
    profile: ToothProfile,
    *,
    radial: int = 20,
    circumferential: int = 10,
    root_bias: float = 1.5,
    boundary_samples: int = 400,
) -> Mesh2D:
    """Structured quad mesh of one tooth column over the **involute flank** (d_Ff → d_Na).

    ``radial`` × ``circumferential`` cells on constant-radius arcs; the involute
    flanks are the exact left/right boundaries. Radius-graded toward the root form
    circle (``root_bias`` > 1) for a finer base. The **root fillet + rim** (d_f → d_Ff)
    is a separate transition block (next step) — it carries the 30°-tangent critical
    section and, like the reference mesh, fans into the rim rather than the tooth column.
    """
    raw = profile.flank_points(boundary_samples)  # involute flank, d_Ff → d_Na (root → tip)
    right_raw = np.array([[p[0], p[1]] for p in raw])
    right = _resample_radial(right_raw, radial + 1, root_bias)  # right flank, level 0…radial

    # Polar structured mesh: each radial level lies on its own constant-radius arc, from
    # the left flank (mirror) to the right flank; the flanks are the exact boundaries and
    # the interior nodes sit on the radius circle, so no cell can invert.
    radius = np.hypot(right[:, 0], right[:, 1])
    half_angle = np.arctan2(right[:, 0], right[:, 1])  # +y axis = 0, right flank > 0
    n_c = circumferential
    s = np.linspace(-1.0, 1.0, n_c + 1)  # left flank … right flank
    nodes = np.empty(((radial + 1) * (n_c + 1), 2))
    for i in range(radial + 1):
        ang = half_angle[i] * s
        nodes[i * (n_c + 1) : (i + 1) * (n_c + 1)] = np.column_stack(
            [radius[i] * np.sin(ang), radius[i] * np.cos(ang)]
        )

    def idx(i: int, j: int) -> int:
        return i * (n_c + 1) + j

    quads = np.array(
        [
            [idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)]
            for i in range(radial)
            for j in range(n_c)
        ],
        dtype=int,
    )
    mesh = Mesh2D(nodes, quads)
    if float(mesh.element_areas().mean()) < 0.0:  # keep CCW (positive) orientation
        mesh.quads = mesh.quads[:, ::-1]
    return mesh
