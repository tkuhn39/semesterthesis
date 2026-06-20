"""
@module: app.services.model
@context: Domain layer — the FE rolling-model generator (replaces STIRAK).
@role: Build the quasi-static Abaqus rolling-contact model from the native STplus
       tooth geometry: the structured tooth FE mesh (`tooth_mesh`), the assembly
       (master nodes, rigid bodies, ties, flank contact pairs) and the rolling step
       (angle/torque amplitudes) per the FVA 892 method (WoBe 892 §3.3.1), written
       through `app.io.inp`. Owning the mesh is the lever for the FE convergence and
       run-time problems (element type, root refinement, sector vs full model).
"""

from app.services.model.gmsh_mesher import Mesh3D, mesh_tooth_pitch, mesh_tooth_pitch_3d
from app.services.model.mapped_mesher import mesh_pitch_mapped_2d, mesh_pitch_mapped_3d
from app.services.model.tooth_mesh import Mesh2D, tooth_sector_2d

__all__ = [
    "Mesh2D",
    "Mesh3D",
    "mesh_pitch_mapped_2d",
    "mesh_pitch_mapped_3d",
    "mesh_tooth_pitch",
    "mesh_tooth_pitch_3d",
    "tooth_sector_2d",
]
