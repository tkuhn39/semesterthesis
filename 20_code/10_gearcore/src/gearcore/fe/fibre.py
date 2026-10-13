"""Fibre orientation of the moulding simulation on the mapped FE mesh (ADR-119).

CONVERSE writes the orientation of every element of the wheel mesh as a local frame
(``*DISTRIBUTION, LOCATION=ELEMENT``: the main fibre direction e_1 and a direction in the 1-2
plane) and the orientation state of every node as the field variables a_11 and a_22, the two
largest eigenvalues of the second-order orientation tensor. From the two the orientation tensor
of an element is

    A = a_11 e_1 e_1ᵀ + a_22 e_2 e_2ᵀ + a_33 e_3 e_3ᵀ,  a_33 = 1 − a_11 − a_22,

the nodal states averaged over the element. The tensor of a zone of the tooth is the volume-
weighted mean of its element tensors, which is what a CT analysis reports for a zone (the mean
over all fibres of the zone): FVA 856 I evaluates the eigenvalues λ_1 ≤ λ_2 ≤ λ_3 of the zone
tensor, the anisotropy index AI = 1 − λ_min / λ_max (Eq. (1), p. 17) and the preferred direction
of the zone in the front (transverse) plane (Bild 17 and Bild 18, p. 19). This module gives the
same quantities for the mapped simulation so that both can stand side by side.

The zones follow the report's names: surface zones along the fibre flow (valley T, root fillet
F, lower flank FU, upper flank FO, tip S), the inner zones M (inside the tooth) and U (below
the root circle), and the transition zones Ü between them (lower, middle, upper), with the
prefix L or R for the left or right side. Left and right are the halves of the mesh (``LEFT``
is the counter-clockwise half seen from +z, as the mesh header says). The surface band is a
depth below the tooth outline in the transverse plane, the transition band the next depth, the
rest is the core; the depths are parameters, the report does not print its zone widths.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from gearcore.errors import InputRangeError
from gearcore.trace import eq

Array = npt.NDArray[np.float64]
SOURCE = "FVA856-I:2022"
EQ_EXEMPT = (
    "orientation_tensor",
    "hexahedron_volumes",
    "zone_tensor",
    "eigen_sorted",
    "in_plane_angle",
    "zone_name",
    "third_of_width",
    "evaluate_zone",
    "ZoneResult",
)
"""Tensor algebra and bookkeeping; the anisotropy index carries the equation of the report."""

FVA856_ZONES: dict[str, tuple[float, float, float, float]] = {
    "LFO": (0.15, 0.23, 0.62, 0.76),
    "LFU": (0.12, 0.18, 0.70, 0.83),
    "LF": (0.10, 0.19, 0.71, 0.86),
    "LT": (0.17, 0.25, 0.58, 0.71),
    "LÜO": (0.20, 0.29, 0.50, 0.60),
    "LÜM": (0.18, 0.22, 0.60, 0.70),
    "LÜU": (0.16, 0.17, 0.67, 0.76),
    "S": (0.23, 0.26, 0.51, 0.55),
    "M": (0.28, 0.29, 0.43, 0.35),
    "U": (0.16, 0.30, 0.54, 0.70),
}
"""(λ_1, λ_2, λ_3, AI) of the zones of the CT-scanned tooth, FVA 856 I, Bild 17, p. 19,
transcribed from the rendered page; the right zones are not printed there ("nahezu gleich zu
denen der linken Zonen")."""

FVA856_ANGLES_DEG: dict[str, float] = {
    "S": -89.1,
    "LFO": -18.5,
    "RFO": 20.9,
    "LFU": -12.8,
    "RFU": 12.1,
    "LF": -27.5,
    "RF": 28.5,
    "LT": -81.6,
    "RT": 84.4,
    "M": -85.3,
    "LÜ": -32.5,
    "RÜ": 32.6,
}
"""Preferred fibre direction of the zone map handed to the FE of the report, FVA 856 I,
Bild 18, p. 19, as printed (read from a 220 dpi rendering: the left zones negative, the right
ones positive): 0° along the tooth axis, 90° across the tooth with the arrow of the figure
pointing to the left; the three transition zones of a side are merged there."""

ZONE_ORDER: tuple[str, ...] = (
    "LT",
    "LF",
    "LFU",
    "LFO",
    "S",
    "RFO",
    "RFU",
    "RF",
    "RT",
    "LÜU",
    "LÜM",
    "LÜO",
    "RÜO",
    "RÜM",
    "RÜU",
    "M",
    "U",
)
"""Surface zones from the left valley over the tip to the right valley, then the transition
zones and the two inner zones, as Bild 17 lists them."""

_GAUSS = (-1.0 / math.sqrt(3.0), 1.0 / math.sqrt(3.0))
_NATURAL = np.array(
    [
        [-1.0, -1.0, -1.0],
        [1.0, -1.0, -1.0],
        [1.0, 1.0, -1.0],
        [-1.0, 1.0, -1.0],
        [-1.0, -1.0, 1.0],
        [1.0, -1.0, 1.0],
        [1.0, 1.0, 1.0],
        [-1.0, 1.0, 1.0],
    ]
)
"""Natural coordinates of the eight corners in the Abaqus C3D8 order."""


def orientation_tensor(frame: Array, a11: float, a22: float) -> Array:
    """The orientation tensor (3, 3) of one element from its fibre frame (columns e_1, e_2,
    e_3, orthonormal) and the two largest eigenvalues a_11 ≥ a_22 of the orientation state;
    the third eigenvalue is 1 − a_11 − a_22. Refuses eigenvalues outside [0, 1], a sum above
    one or an order a_22 > a_11 (beyond 1e-6)."""
    f = np.asarray(frame, dtype=np.float64)
    if f.shape != (3, 3):
        raise InputRangeError("the fibre frame must be a 3 x 3 matrix")
    if not np.allclose(f.T @ f, np.eye(3), atol=1.0e-6):
        raise InputRangeError("the fibre frame is not orthonormal")
    for name, value in (("a_11", a11), ("a_22", a22)):
        if not math.isfinite(value) or value < -1.0e-6 or value > 1.0 + 1.0e-6:
            raise InputRangeError(f"{name} = {value!r} lies outside [0, 1]")
    if a11 + a22 > 1.0 + 1.0e-6:
        raise InputRangeError(f"a_11 + a_22 = {a11 + a22!r} exceeds one")
    if a22 > a11 + 1.0e-6:
        raise InputRangeError(f"a_22 = {a22!r} exceeds a_11 = {a11!r}: the state is not ordered")
    a33 = max(1.0 - a11 - a22, 0.0)
    values = (a11, a22, a33)
    tensor = np.zeros((3, 3))
    for k, value in enumerate(values):
        tensor += value * np.outer(f[:, k], f[:, k])
    return tensor


def hexahedron_volumes(corners: Array) -> Array:
    """Volumes (n,) of trilinear hexahedra from their corners (n, 8, 3) in the Abaqus C3D8
    order, by 2 x 2 x 2 Gauss integration of the Jacobian determinant, which is exact for the
    trilinear map. A negative volume (inverted node order) is refused."""
    c = np.asarray(corners, dtype=np.float64)
    if c.ndim != 3 or c.shape[1:] != (8, 3):
        raise InputRangeError("corners must have the shape (n, 8, 3)")
    volumes = np.zeros(c.shape[0])
    for xi in _GAUSS:
        for eta in _GAUSS:
            for zeta in _GAUSS:
                # derivatives of the eight trilinear shape functions at the Gauss point
                d_xi = (
                    0.125
                    * _NATURAL[:, 0]
                    * (1.0 + _NATURAL[:, 1] * eta)
                    * (1.0 + _NATURAL[:, 2] * zeta)
                )
                d_eta = (
                    0.125
                    * _NATURAL[:, 1]
                    * (1.0 + _NATURAL[:, 0] * xi)
                    * (1.0 + _NATURAL[:, 2] * zeta)
                )
                d_zeta = (
                    0.125
                    * _NATURAL[:, 2]
                    * (1.0 + _NATURAL[:, 0] * xi)
                    * (1.0 + _NATURAL[:, 1] * eta)
                )
                jacobian = np.stack(
                    [
                        np.einsum("k,nkj->nj", d_xi, c),
                        np.einsum("k,nkj->nj", d_eta, c),
                        np.einsum("k,nkj->nj", d_zeta, c),
                    ],
                    axis=1,
                )
                volumes += np.linalg.det(jacobian)
    if np.any(volumes <= 0.0):
        raise InputRangeError("an element has no positive volume (inverted node order)")
    return volumes


def zone_tensor(tensors: Array, weights: Array) -> Array:
    """Weighted mean (3, 3) of element tensors (n, 3, 3) with positive weights (n,), the
    volumes of the elements."""
    t = np.asarray(tensors, dtype=np.float64)
    w = np.asarray(weights, dtype=np.float64)
    if t.ndim != 3 or t.shape[1:] != (3, 3) or w.shape != (t.shape[0],) or t.shape[0] == 0:
        raise InputRangeError("tensors (n, 3, 3) and weights (n,) must match and be non-empty")
    if np.any(w <= 0.0):
        raise InputRangeError("every weight must be positive")
    return np.asarray(np.einsum("n,nij->ij", w, t) / w.sum(), dtype=np.float64)


def eigen_sorted(tensor: Array) -> tuple[Array, Array]:
    """Eigenvalues ascending (3,) and the eigenvectors as columns (3, 3) of a symmetric
    tensor; the last column belongs to the largest eigenvalue."""
    t = np.asarray(tensor, dtype=np.float64)
    if t.shape != (3, 3) or not np.allclose(t, t.T, atol=1.0e-9):
        raise InputRangeError("the tensor must be symmetric 3 x 3")
    values, vectors = np.linalg.eigh(t)
    return np.asarray(values, dtype=np.float64), np.asarray(vectors, dtype=np.float64)


@eq(SOURCE, "(1)", section="6.2.1.2", page=17, note="AI = 1 − λ_min / λ_max of the zone tensor")
def anisotropy_index(eigenvalues: npt.ArrayLike) -> float:
    """Anisotropy index of a zone, 0 for the isotropic tensor (all eigenvalues 1/3), 1 for one
    eigenvalue of one."""
    values = np.asarray(eigenvalues, dtype=np.float64)
    if values.shape != (3,) or not np.all(np.isfinite(values)):
        raise InputRangeError("three finite eigenvalues are needed")
    largest = float(values.max())
    if largest <= 0.0:
        raise InputRangeError("the largest eigenvalue must be positive")
    return 1.0 - float(values.min()) / largest


def in_plane_angle(direction: Array, radial: Array, across: Array) -> tuple[float, float]:
    """(angle in degrees, in-plane share) of a sign-free direction in the plane of the unit
    vectors ``radial`` (the tooth axis, 0°) and ``across`` (90°, the direction the report's
    arrow points to): the angle lies in (−90, 90], the share is the length of the projection
    into the plane of a unit direction (1 for a fibre lying in the plane)."""
    d = np.asarray(direction, dtype=np.float64)
    r_axis = np.asarray(radial, dtype=np.float64)
    t_axis = np.asarray(across, dtype=np.float64)
    length = float(np.linalg.norm(d))
    if not length > 0.0:
        raise InputRangeError("the direction has no length")
    for name, axis in (("radial", r_axis), ("across", t_axis)):
        if not math.isclose(float(np.linalg.norm(axis)), 1.0, abs_tol=1.0e-9):
            raise InputRangeError(f"the {name} axis must be a unit vector")
    if abs(float(r_axis @ t_axis)) > 1.0e-9:
        raise InputRangeError("the two axes must be orthogonal")
    r = float(d @ r_axis) / length
    t = float(d @ t_axis) / length
    if abs(r) < 1.0e-12:
        r = 0.0  # exactly across the tooth: +90°, never −90° by rounding noise
    if r < 0.0 or (r == 0.0 and t < 0.0):
        r, t = -r, -t
    angle = math.degrees(math.atan2(t, r))
    if angle <= -90.0:
        angle += 180.0
    return angle, math.hypot(r, t)


def zone_name(
    *,
    side: str,
    kind: str,
    depth_mm: float,
    skin_mm: float,
    height_fraction: float,
) -> str:
    """The zone of an element from the side of the nearest surface (``'L'`` or ``'R'``), the
    kind of that surface (``'tip'``, ``'flank'``, ``'root'`` for the fillet, ``'valley'`` for
    the root land), its depth below the outline, the surface band depth ``skin_mm`` (the
    transition band is as deep again) and its radial position in the tooth as a fraction of
    the tooth height from the root circle (negative below it)."""
    if side not in ("L", "R"):
        raise InputRangeError(f"side must be 'L' or 'R', got {side!r}")
    if kind not in ("tip", "flank", "root", "valley"):
        raise InputRangeError(f"kind {kind!r} is not tip, flank, root or valley")
    if not skin_mm > 0.0 or not math.isfinite(depth_mm) or depth_mm < 0.0:
        raise InputRangeError("the skin depth must be positive and the depth finite and ≥ 0")
    if depth_mm <= skin_mm:
        if kind == "tip":
            return "S"
        if kind == "valley":
            return f"{side}T"
        if kind == "root":
            return f"{side}F"
        return f"{side}FU" if height_fraction < 0.5 else f"{side}FO"
    if depth_mm <= 2.0 * skin_mm:
        if kind == "valley":
            return "U"
        if kind == "tip":
            return "M"
        if kind == "root":
            return f"{side}ÜU"
        return f"{side}ÜM" if height_fraction < 0.5 else f"{side}ÜO"
    return "M" if height_fraction >= 0.0 else "U"


def third_of_width(z_mm: float, half_width_mm: float) -> str:
    """``'z-'``, ``'mid'`` or ``'z+'``: the third of the face width (−b/2 … b/2) a position
    falls into."""
    if not half_width_mm > 0.0:
        raise InputRangeError("the half width must be positive")
    if abs(z_mm) > half_width_mm * (1.0 + 1.0e-9):
        raise InputRangeError(f"z = {z_mm!r} lies outside the face width")
    limit = half_width_mm / 3.0
    if z_mm < -limit:
        return "z-"
    if z_mm > limit:
        return "z+"
    return "mid"


@dataclass(frozen=True)
class ZoneResult:
    """The orientation tensor of a zone reduced to what the report prints."""

    name: str
    elements: int
    volume_mm3: float
    eigenvalues: tuple[float, float, float]
    anisotropy_index: float
    angle_deg: float
    in_plane: float
    a11_mean: float
    diagonal: tuple[float, float, float]
    """The diagonal of the zone tensor in the tooth frame: along the tooth axis (radial),
    across the tooth and along the wheel axis (the face width); 1/3 each for isotropy."""
    tilt_deg: float
    """Angle of the main axis out of the transverse plane, in (−90, 90]: positive when the
    axis, pointed outward along the tooth (or, across the tooth, to the left), rises towards
    +z; 0 for a fibre in the plane, ±90 for a fibre along the wheel axis."""


def evaluate_zone(
    name: str,
    tensors: Array,
    volumes: Array,
    a11: Sequence[float],
    radial: Array,
    across: Array,
) -> ZoneResult:
    """Zone tensor, its eigenvalues, the anisotropy index and the preferred direction in the
    transverse plane of the elements of one zone."""
    tensor = zone_tensor(tensors, volumes)
    values, vectors = eigen_sorted(tensor)
    angle, share = in_plane_angle(vectors[:, 2], radial, across)
    states = np.asarray(a11, dtype=np.float64)
    if states.shape != (len(volumes),):
        raise InputRangeError("one a_11 per element is needed")
    r_axis = np.asarray(radial, dtype=np.float64)
    t_axis = np.asarray(across, dtype=np.float64)
    z_axis = np.cross(r_axis, t_axis)
    diagonal = tuple(float(axis @ tensor @ axis) for axis in (r_axis, t_axis, z_axis))
    main = vectors[:, 2]
    r_part, t_part = float(main @ r_axis), float(main @ t_axis)
    if r_part < 0.0 or (abs(r_part) < 1.0e-12 and t_part < 0.0):
        main = -main
    tilt = math.degrees(math.atan2(float(main @ z_axis), math.hypot(r_part, t_part)))
    if tilt <= -90.0:
        tilt += 180.0
    return ZoneResult(
        name=name,
        elements=int(len(volumes)),
        volume_mm3=float(np.sum(volumes)),
        eigenvalues=(float(values[0]), float(values[1]), float(values[2])),
        anisotropy_index=anisotropy_index(values),
        angle_deg=angle,
        in_plane=share,
        a11_mean=float(np.average(states, weights=np.asarray(volumes, dtype=np.float64))),
        diagonal=(diagonal[0], diagonal[1], diagonal[2]),
        tilt_deg=tilt,
    )
