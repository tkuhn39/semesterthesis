"""
@module: app.services.model.mesh3d
@context: Domain layer — FE rolling model, the 3-D mesh data type + face-width extrusion.
@role: Hold the C3D8 hex-mesh container (`Mesh3D`) and the native quad→hex extrusion
       (`extrude_to_hex`) shared by the structured (transfinite) mapped mesher. Pure numpy,
       no gmsh — the native sweep is robust to gmsh's surface-extrusion quirks on complex
       sector boundaries, and keeps the mesh data type free of the mesher's dependencies.
"""

import numpy as np
from numpy.typing import NDArray

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
