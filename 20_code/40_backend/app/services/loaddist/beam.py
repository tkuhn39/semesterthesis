"""
@module: app.services.loaddist.beam
@context: Domain layer — RIKOR (FVA 30) load distribution, step R2 helper.
@role: A small Euler–Bernoulli beam finite-element solver for a stepped shaft on
       elastic supports. Two DOF per node (transverse deflection v, rotation θ);
       Hermitian beam elements; point/moment/distributed loads as consistent nodal
       forces; bearings as translational springs to ground. Used by `shaft.py` to
       get the shaft bending line (one plane = the gear line of action). Kept
       generic and analytically testable (simply-supported reference cases).
"""

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]


class BeamModel:
    """A 1-D Euler–Bernoulli beam on a node grid, assembled and solved in one plane.

    Nodes are given by their axial coordinates (ascending). Each element spans two
    neighbouring nodes and carries a bending stiffness EI. Supports (springs),
    point loads/moments and distributed loads are applied, then `solve()` returns
    the nodal deflection and rotation.
    """

    def __init__(self, node_positions: Array, ei: Array, shear_ga: Array | None = None) -> None:
        """``node_positions`` (n,), ``ei`` (n-1,) bending stiffness per element.

        ``shear_ga`` (n-1,), the shear rigidity G·A_s per element, switches the
        elements to Timoshenko (shear-flexible) beams; omit for Euler–Bernoulli.
        """
        self.x = np.asarray(node_positions, dtype=float)
        self.ei = np.asarray(ei, dtype=float)
        self.ga = None if shear_ga is None else np.asarray(shear_ga, dtype=float)
        self.n = self.x.size
        self.ndof = 2 * self.n
        self.k = np.zeros((self.ndof, self.ndof))
        self.f = np.zeros(self.ndof)
        self._assemble_stiffness()

    def _assemble_stiffness(self) -> None:
        for e in range(self.n - 1):
            length = self.x[e + 1] - self.x[e]
            ei = self.ei[e]
            phi = 0.0 if self.ga is None else 12.0 * ei / (self.ga[e] * length**2)
            ke = _element_stiffness(length, ei, phi)
            dofs = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
            for a in range(4):
                for b in range(4):
                    self.k[dofs[a], dofs[b]] += ke[a, b]

    def _node_at(self, position: float) -> int:
        return int(np.argmin(np.abs(self.x - position)))

    def add_support(self, position: float, stiffness: float) -> None:
        """Add a translational spring (N/mm) to ground at the deflection DOF."""
        node = self._node_at(position)
        self.k[2 * node, 2 * node] += stiffness

    def add_point_load(self, position: float, force: float) -> None:
        self.f[2 * self._node_at(position)] += force

    def add_point_moment(self, position: float, moment: float) -> None:
        self.f[2 * self._node_at(position) + 1] += moment

    def add_distributed_load(self, start: float, end: float, total_force: float) -> None:
        """Spread ``total_force`` as a uniform line load over [start, end] (consistent loads)."""
        lo, hi = sorted((start, end))
        span = hi - lo
        if span <= 0.0:
            self.add_point_load(lo, total_force)
            return
        q = total_force / span
        for e in range(self.n - 1):
            a, b = self.x[e], self.x[e + 1]
            seg_lo, seg_hi = max(a, lo), min(b, hi)
            if seg_hi <= seg_lo:
                continue
            length = b - a
            # consistent nodal load of a uniform q acting on the sub-span of the element
            self.f[2 * e : 2 * e + 4] += _consistent_uniform(length, q, seg_lo - a, seg_hi - a)

    def solve(self) -> tuple[Array, Array]:
        """Solve K·u = f; return (deflection v at nodes, rotation θ at nodes)."""
        u: Array = np.linalg.solve(self.k, self.f).astype(np.float64)
        return u[0::2], u[1::2]

    def deflection_at(self, positions: Array) -> Array:
        """Deflection v interpolated at arbitrary positions (cubic Hermite per element)."""
        v, theta = self.solve()
        out = np.empty(np.asarray(positions).shape, dtype=float)
        for i, p in enumerate(np.atleast_1d(positions)):
            e = min(max(int(np.searchsorted(self.x, p) - 1), 0), self.n - 2)
            length = self.x[e + 1] - self.x[e]
            xi = (p - self.x[e]) / length
            out.flat[i] = _hermite(xi, length) @ np.array([v[e], theta[e], v[e + 1], theta[e + 1]])
        return out


def _element_stiffness(length: float, ei: float, phi: float = 0.0) -> Array:
    """Beam element stiffness; ``phi`` = 12EI/(G·A_s·L²) adds Timoshenko shear (0 = Euler)."""
    le = length
    return (ei / (le**3 * (1.0 + phi))) * np.array(
        [
            [12.0, 6.0 * le, -12.0, 6.0 * le],
            [6.0 * le, (4.0 + phi) * le**2, -6.0 * le, (2.0 - phi) * le**2],
            [-12.0, -6.0 * le, 12.0, -6.0 * le],
            [6.0 * le, (2.0 - phi) * le**2, -6.0 * le, (4.0 + phi) * le**2],
        ]
    )


def _consistent_uniform(length: float, q: float, a: float, b: float) -> Array:
    """Consistent nodal forces of a uniform load q on [a, b] within an element of length ``length``.

    Integrates q·N(x) over [a, b] with the cubic Hermite shape functions N. For a
    full element (a=0, b=length) this reduces to [qL/2, qL²/12, qL/2, −qL²/12].
    """
    le = length

    def shapes(x: float) -> Array:
        xi = x / le
        return np.array(
            [
                1 - 3 * xi**2 + 2 * xi**3,
                le * (xi - 2 * xi**2 + xi**3),
                3 * xi**2 - 2 * xi**3,
                le * (-(xi**2) + xi**3),
            ]
        )

    # 3-point Gauss on [a, b]
    mid, half = 0.5 * (a + b), 0.5 * (b - a)
    nodes = (-np.sqrt(3 / 5), 0.0, np.sqrt(3 / 5))
    weights = (5 / 9, 8 / 9, 5 / 9)
    acc = np.zeros(4)
    for xg, wg in zip(nodes, weights, strict=True):
        acc += wg * half * q * shapes(mid + half * xg)
    return acc


def _hermite(xi: float, length: float) -> Array:
    return np.array(
        [
            1 - 3 * xi**2 + 2 * xi**3,
            length * (xi - 2 * xi**2 + xi**3),
            3 * xi**2 - 2 * xi**3,
            length * (-(xi**2) + xi**3),
        ]
    )
