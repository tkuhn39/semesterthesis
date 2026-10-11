"""Anisotropic strength for the check after Stommel et al.: the own extension E7 (ADR-118).

The published method (chapter 6 of Stommel, Stojek, Korte 2018) prescribes an isotropic linear
elastic model and the reference curve of the tensile bar in flow direction (p. 344); the
strength of the short-fibre material across the fibres enters only through the reduction
factors of the class. This module replaces the von Mises stress of the equivalent stress
(Eq. (6.2), (6.16)) by the Hill equivalent stress of the quadratic Hill potential as Abaqus
defines it for the ``*POTENTIAL, TYPE=HILL`` card that CONVERSE writes (Hill Anisotropic
Yield/Creep, Abaqus 2025 documentation): with the six yield stress ratios R_11, R_22, R_33,
R_12, R_13, R_23 of the orientation state,

    σ_Hill² = F (σ_22 − σ_33)² + G (σ_33 − σ_11)² + H (σ_11 − σ_22)² + 2 L σ_23² + 2 M σ_13² + 2 N σ_12²

    F = ½ (1/R_22² + 1/R_33² − 1/R_11²), G = ½ (1/R_33² + 1/R_11² − 1/R_22²),
    H = ½ (1/R_11² + 1/R_22² − 1/R_33²), L = 3/(2 R_23²), M = 3/(2 R_13²), N = 3/(2 R_12²),

the stress components taken in the local frame of the fibre orientation. With all ratios one
the expression is the von Mises stress. Uniaxial stress along axis 1 gives |σ_11| / R_11, pure
shear σ_12 gives √3 |σ_12| / R_12: the ratios scale the yield surface relative to the reference
curve, which is exactly how the card relates the orientation states to the 0° bar, so the
strength side of the check (K, σ_stat, σ_W of the reference curve) stays as it is and the
anisotropy enters through the equivalent stress alone. With q = 0 of the ductile hypothesis the
static equivalent stress is σ_Hill itself; with q > 0 the normal stress hypothesis keeps its
share as in Eq. (6.2).

What the component supplies per node (``NodalAnisotropy``): the fibre frame, averaged from the
element orientations of the CONVERSE distribution (``*DISTRIBUTION, LOCATION=ELEMENT``: the
local 1-direction and a direction in the 1-2 plane per element), and the orientation state
(a_11, a_22) of the field variables (``*INITIAL CONDITIONS, TYPE=FIELD``), from which the Hill
row of the nearest lattice state of the card is taken (``ConverseCard.hill_at``). The frames
are averaged without a sign (a fibre direction is a line, not an arrow): the orientation tensor
e_1 e_1ᵀ of the attached elements is averaged and its dominant eigenvector taken, the second
axis likewise within the plane orthogonal to the first, the third by the cross product.

The degree of multiaxiality h (Eq. (6.3)) and the sign of the cyclic history (Eq. (6.10)) stay
frame-free invariants; the cyclic route ``signed_hill`` applies the sign of I_1 to σ_Hill as the
signed von Mises route does to σ_Mises. The principal route with direction-dependent strengths
is not built (extension point).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from gearcore.errors import InputRangeError
from gearcore.fatigue import stommel as st
from gearcore.fe.stress import COMPONENTS
from gearcore.io.converse_card import ConverseCard
from gearcore.trace import eq

SOURCE = "Abaqus2025:Hill"
Array = npt.NDArray[np.float64]
Vector = tuple[float, float, float]
RATIO_NAMES = ("R11", "R22", "R33", "R12", "R13", "R23")
EQ_EXEMPT = (
    "element_frame",
    "pressure_corrected_components",
    "interpolated_hill_ratios",
    "nodal_frames",
    "nodal_states",
    "nearest_hill_ratios",
    "to_local_frame",
    "build_nodal_anisotropy",
)


def _ratios(R: npt.ArrayLike) -> Array:
    ratios = np.asarray(R, dtype=np.float64)
    if ratios.ndim == 1:
        ratios = ratios[np.newaxis, :]
    if ratios.ndim != 2 or ratios.shape[1] != 6:
        raise InputRangeError(f"Hill ratios must have shape (n, 6), got {ratios.shape}")
    if not np.all(np.isfinite(ratios)) or np.any(ratios <= 0.0):
        raise InputRangeError("every Hill ratio must be positive and finite")
    return ratios


@eq(SOURCE, "Hill potential", section="Yield and Creep Stress Ratios")
def hill_constants(R: npt.ArrayLike) -> Array:
    """(n, 6) constants F, G, H, L, M, N of the quadratic Hill potential from the six yield
    stress ratios R_11, R_22, R_33, R_12, R_13, R_23 (in that order, as the card gives them)."""
    ratios = _ratios(R)
    inv = 1.0 / ratios**2
    r11, r22, r33, r12, r13, r23 = (inv[:, i] for i in range(6))
    F = 0.5 * (r22 + r33 - r11)
    G = 0.5 * (r33 + r11 - r22)
    H = 0.5 * (r11 + r22 - r33)
    L = 1.5 * r23
    M = 1.5 * r13
    N = 1.5 * r12
    return np.stack([F, G, H, L, M, N], axis=1)


@eq(SOURCE, "Hill potential", section="Yield and Creep Stress Ratios")
def hill_equivalent_stress(components_local: npt.ArrayLike, R: npt.ArrayLike) -> Array:
    """σ_Hill of (n, 6) stress components in the local frame of the anisotropy, in the order of
    ``gearcore.fe.stress.COMPONENTS`` (S11, S22, S33, S12, S13, S23), with the (n, 6) ratios of
    every node; the von Mises stress when every ratio is one. The constants F, G, H may be
    negative for strongly anisotropic states; the potential is then not positive definite and a
    negative radicand is refused."""
    s = np.asarray(components_local, dtype=np.float64)
    if s.ndim == 1:
        s = s[np.newaxis, :]
    if s.ndim != 2 or s.shape[1] != 6:
        raise InputRangeError(f"stress components must have shape (n, 6), got {s.shape}")
    constants = hill_constants(R)
    if constants.shape[0] not in (1, s.shape[0]):
        raise InputRangeError(f"{constants.shape[0]} ratio rows for {s.shape[0]} stress rows")
    F, G, H, L, M, N = (constants[:, i] for i in range(6))
    s11, s22, s33, s12, s13, s23 = (s[:, i] for i in range(6))
    radicand = (
        F * (s22 - s33) ** 2
        + G * (s33 - s11) ** 2
        + H * (s11 - s22) ** 2
        + 2.0 * L * s23**2
        + 2.0 * M * s13**2
        + 2.0 * N * s12**2
    )
    if np.any(radicand < -1.0e-9 * np.max(np.abs(s), initial=1.0) ** 2):
        raise InputRangeError("the Hill potential is not positive definite for these ratios")
    return np.asarray(np.sqrt(np.maximum(radicand, 0.0)), dtype=np.float64)


@eq("Stommel2018", "(6.16)", section="6.2.4", page=357, note="von Mises replaced by Hill, E7")
def equivalent_stress_static_hill(
    sigma_1: npt.ArrayLike,
    sigma_2: npt.ArrayLike,
    sigma_3: npt.ArrayLike,
    sigma_Hill: npt.ArrayLike,
    q: npt.ArrayLike,
    f_sigma: npt.ArrayLike = st.COMPRESSIVE_STRENGTH_FACTOR,
) -> Array:
    """Equivalent stress of the static check with the Hill stress in place of the von Mises
    stress: σ_V = q σ̄_V,NH + (1 − q) σ_Hill, the normal stress hypothesis with the
    pressure-corrected principal stresses as in Eq. (6.17); the Hill stress passed in is the one
    of the pressure-corrected tensor (``pressure_corrected_components``: the corrected principal
    values put back on their directions), so that unit ratios reproduce the published branch
    exactly (review of 2026-10-11)."""
    s1 = st.pressure_corrected_principal_stress(sigma_1, f_sigma)
    s2 = st.pressure_corrected_principal_stress(sigma_2, f_sigma)
    s3 = st.pressure_corrected_principal_stress(sigma_3, f_sigma)
    hill = np.asarray(sigma_Hill, dtype=np.float64)
    if np.any(hill < 0.0):
        raise InputRangeError("the Hill stress is not negative")
    return st.equivalent_stress(st.normal_stress_hypothesis_stress(s1, s2, s3), hill, q)


def pressure_corrected_components(
    components: npt.ArrayLike, f_sigma: npt.ArrayLike = st.COMPRESSIVE_STRENGTH_FACTOR
) -> Array:
    """(n, 6) components of the tensor whose principal values are the pressure-corrected ones
    of Eq. (6.17) (compressive values divided by f_σ) on the original principal directions:
    the static Hill check corrects the compression as the published static check does."""
    s = np.asarray(components, dtype=np.float64)
    if s.ndim != 2 or s.shape[1] != 6:
        raise InputRangeError(f"stress components must have shape (n, 6), got {s.shape}")
    values, vectors = np.linalg.eigh(st.tensors_from_components(s))
    corrected = st.pressure_corrected_principal_stress(values, f_sigma)
    tensors = np.einsum("nik,nk,njk->nij", vectors, corrected, vectors)
    return st.components_from_tensors(tensors)


# --- the fibre frame and the orientation state per node ----------------------------------------------


def to_local_frame(components: npt.ArrayLike, frames: npt.ArrayLike) -> Array:
    """Stress components (n, 6) of the part frame expressed in the local frames (n, 3, 3) whose
    columns are the local axes in the part frame: S_loc = Qᵀ S Q, back to components."""
    s = np.asarray(components, dtype=np.float64)
    q = np.asarray(frames, dtype=np.float64)
    if s.ndim != 2 or s.shape[1] != 6:
        raise InputRangeError(f"stress components must have shape (n, 6), got {s.shape}")
    if q.shape != (s.shape[0], 3, 3):
        raise InputRangeError(f"frames must have shape {(s.shape[0], 3, 3)}, got {q.shape}")
    tensors = st.tensors_from_components(s)
    local = np.einsum("nki,nkl,nlj->nij", q, tensors, q)
    return st.components_from_tensors(local)


def element_frame(a: Vector, b: Vector) -> Array:
    """Orthonormal frame (3, 3) of one element from the local 1-direction ``a`` and a direction
    ``b`` in the 1-2 plane, as ``*ORIENTATION, DEFINITION=COORDINATES`` takes them: column 0 is
    a normalised, column 1 the part of b orthogonal to it, column 2 their cross product."""
    e1 = np.asarray(a, dtype=np.float64)
    norm = float(np.linalg.norm(e1))
    if not norm > 0.0:
        raise InputRangeError("the local 1-direction has no length")
    e1 = e1 / norm
    raw = np.asarray(b, dtype=np.float64)
    e2 = raw - float(e1 @ raw) * e1
    norm2 = float(np.linalg.norm(e2))
    if not norm2 > 1.0e-9:
        raise InputRangeError("the second direction is parallel to the first")
    e2 = e2 / norm2
    return np.stack([e1, e2, np.cross(e1, e2)], axis=1)


def _dominant(tensor: Array) -> Array:
    """Dominant eigenvector of symmetric (n, 3, 3) tensors, (n, 3)."""
    values, vectors = np.linalg.eigh(tensor)
    return np.asarray(vectors[:, :, -1], dtype=np.float64)


def nodal_frames(
    node_labels: npt.ArrayLike,
    connectivity: Mapping[int, Sequence[int]],
    orientation: Mapping[int, tuple[Vector, Vector]],
) -> tuple[Array, npt.NDArray[np.int64], Array]:
    """Fibre frame (n, 3, 3) of every node from the orientations of the attached elements and
    the number of elements that contributed (n,): the orientation tensors e_1 e_1ᵀ and
    e_2 e_2ᵀ of the elements are averaged per node (sign-free), the first axis is the dominant
    eigenvector of the first, the second the dominant eigenvector of the second projected
    orthogonal to the first, the third the cross product. A node without an oriented element
    keeps the identity and a count of zero. Elements of the connectivity without an
    orientation are refused. The third value is the quality of the first axis per node,
    (λ_3 − λ_2) / λ_3 of the averaged first orientation tensor: near zero the attached elements
    disagree and the axis is weakly defined (review of 2026-10-11)."""
    labels = np.asarray(node_labels, dtype=np.int64)
    if labels.ndim != 1 or labels.size == 0:
        raise InputRangeError("node labels must be a non-empty vector")
    index = {int(label): i for i, label in enumerate(labels)}
    if len(index) != labels.size:
        raise InputRangeError("node labels are not unique")
    n = labels.size
    first = np.zeros((n, 3, 3))
    second = np.zeros((n, 3, 3))
    count = np.zeros(n, dtype=np.int64)
    missing = [label for label in connectivity if label not in orientation]
    if missing:
        raise InputRangeError(
            f"{len(missing)} elements without an orientation (first: {missing[:5]})"
        )
    for element, nodes in connectivity.items():
        frame = element_frame(*orientation[element])
        t1 = np.outer(frame[:, 0], frame[:, 0])
        t2 = np.outer(frame[:, 1], frame[:, 1])
        rows = [index[int(node)] for node in nodes if int(node) in index]
        for row in rows:
            first[row] += t1
            second[row] += t2
            count[row] += 1
    frames = np.broadcast_to(np.eye(3), (n, 3, 3)).copy()
    gap = np.zeros(n)
    has = count > 0
    if np.any(has):
        eigenvalues = np.linalg.eigvalsh(first[has])
        largest = np.maximum(eigenvalues[:, -1], 1.0e-12)
        gap[has] = (eigenvalues[:, -1] - eigenvalues[:, -2]) / largest
        e1 = _dominant(first[has])
        projector = np.eye(3)[np.newaxis] - np.einsum("ni,nj->nij", e1, e1)
        t2p = np.einsum("nij,njk,nkl->nil", projector, second[has], projector)
        e2 = _dominant(t2p)
        e2 -= np.einsum("ni,ni->n", e2, e1)[:, np.newaxis] * e1
        e2 /= np.linalg.norm(e2, axis=1)[:, np.newaxis]
        e3 = np.cross(e1, e2)
        frames[has] = np.stack([e1, e2, e3], axis=2)
    return frames, count, gap


def nodal_states(node_labels: npt.ArrayLike, fields: Mapping[int, tuple[float, float]]) -> Array:
    """(n, 2) orientation state (a_11, a_22) of every node from the field variables of the
    orientation file; every node must have one."""
    labels = np.asarray(node_labels, dtype=np.int64)
    out = np.empty((labels.size, 2))
    missing = 0
    for i, label in enumerate(labels):
        pair = fields.get(int(label))
        if pair is None:
            missing += 1
            continue
        out[i] = pair
    if missing:
        raise InputRangeError(f"{missing} nodes without field variables (a_11, a_22)")
    if np.any(out < 0.0) or np.any(out[:, 0] + out[:, 1] > 1.0 + 1.0e-6):
        raise InputRangeError("a field variable pair is not an orientation state")
    return out


def nearest_hill_ratios(card: ConverseCard, temperature_c: float, states: npt.ArrayLike) -> Array:
    """(n, 6) Hill ratios of the lattice state of the card nearest to every (a_11, a_22)."""
    rows = [row for row in card.hill if abs(row.temperature_c - temperature_c) < 1.0e-6]
    if not rows:
        raise InputRangeError(f"{card.name}: no Hill row at {temperature_c} degC")
    lattice = np.array([[row.a11, row.a22] for row in rows])
    ratios = np.array([[row.R11, row.R22, row.R33, row.R12, row.R13, row.R23] for row in rows])
    points = np.asarray(states, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2:
        raise InputRangeError(f"states must have shape (n, 2), got {points.shape}")
    distance = ((points[:, np.newaxis, :] - lattice[np.newaxis, :, :]) ** 2).sum(axis=2)
    nearest = np.argmin(distance, axis=1)
    return np.asarray(ratios[nearest], dtype=np.float64)


def interpolated_hill_ratios(
    card: ConverseCard, temperature_c: float, states: npt.ArrayLike
) -> Array:
    """(n, 6) Hill ratios interpolated linearly over the (a_11, a_22) lattice of the card, as
    Abaqus interpolates a table over its field variables; outside the convex hull of the
    lattice, or with fewer than three lattice states, the nearest state is taken (the lattice
    is coarse in a_22, nearest-state snapping made the ratios jump by up to 10 % between
    neighbouring nodes, review of 2026-10-11)."""
    from scipy.interpolate import LinearNDInterpolator

    rows = [row for row in card.hill if abs(row.temperature_c - temperature_c) < 1.0e-6]
    points = np.asarray(states, dtype=np.float64)
    nearest = nearest_hill_ratios(card, temperature_c, points)
    if len(rows) < 3:
        return nearest
    lattice = np.array([[row.a11, row.a22] for row in rows])
    ratios = np.array([[row.R11, row.R22, row.R33, row.R12, row.R13, row.R23] for row in rows])
    try:
        interpolator = LinearNDInterpolator(lattice, ratios)
    except Exception:  # noqa: BLE001 - a collinear lattice has no triangulation
        return nearest
    values = np.asarray(interpolator(points), dtype=np.float64)
    outside = np.any(np.isnan(values), axis=1)
    values[outside] = nearest[outside]
    return values


@dataclass(frozen=True)
class NodalAnisotropy:
    """What the Hill check needs per node of a stress file, in the order of its node table."""

    node_labels: npt.NDArray[np.int64]
    frames: Array
    """(n, 3, 3): columns = local axes 1, 2, 3 in the part frame."""
    element_count: npt.NDArray[np.int64]
    states: Array
    """(n, 2): a_11, a_22."""
    ratios: Array
    """(n, 6): R_11, R_22, R_33, R_12, R_13, R_23 interpolated over the lattice of the card."""
    temperature_c: float
    card: str
    frame_gap: Array | None = None
    """(n,): (λ_3 − λ_2) / λ_3 of the first orientation tensor, the quality of the first axis."""

    @property
    def n(self) -> int:
        return int(self.node_labels.size)


def build_nodal_anisotropy(
    node_labels: npt.ArrayLike,
    connectivity: Mapping[int, Sequence[int]],
    orientation: Mapping[int, tuple[Vector, Vector]],
    fields: Mapping[int, tuple[float, float]],
    card: ConverseCard,
    temperature_c: float,
) -> NodalAnisotropy:
    """Frames, states and ratios of every node of a stress file's node table."""
    labels = np.asarray(node_labels, dtype=np.int64)
    frames, count, gap = nodal_frames(labels, connectivity, orientation)
    if not np.all(count > 0):
        raise InputRangeError(f"{int(np.sum(count == 0))} nodes without an oriented element")
    states = nodal_states(labels, fields)
    ratios = interpolated_hill_ratios(card, temperature_c, states)
    return NodalAnisotropy(
        node_labels=labels,
        frames=frames,
        element_count=count,
        states=states,
        ratios=ratios,
        temperature_c=temperature_c,
        card=card.name,
        frame_gap=gap,
    )


__all__ = [
    "COMPONENTS",
    "NodalAnisotropy",
    "RATIO_NAMES",
    "build_nodal_anisotropy",
    "element_frame",
    "equivalent_stress_static_hill",
    "hill_constants",
    "hill_equivalent_stress",
    "interpolated_hill_ratios",
    "nearest_hill_ratios",
    "nodal_frames",
    "nodal_states",
    "pressure_corrected_components",
    "to_local_frame",
]
