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

from app.services.model.gmsh_mesher import mesh_tooth_pitch
from app.services.model.tooth_mesh import Mesh2D, tooth_sector_2d

__all__ = ["Mesh2D", "mesh_tooth_pitch", "tooth_sector_2d"]
