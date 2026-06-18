"""
@module: app.services.loaddist
@context: Domain layer — native RIKOR (FVA 30) load distribution.
@role: Reimplement the RIKOR face-/profile load distribution from the documented
       FVA 30 method (not by fitting RIKOR's I/O): nominal mesh forces and stiffness
       (R1), the shaft–bearing deflection → mesh misalignment (R2), and the load
       distribution w(b) → K_Hβ/K_Fβ + the flank-line correction (R3). The mesh
       misalignment F_βx feeds the existing ISO 6336-1 K_Hβ (Method C), closing the
       last fed quantity of the analytical capacity. Reads the RIKOR `.rie` input
       (`app.io.rie`) and validates against the bundled standard tests.
"""

from app.services.loaddist.compliance import local_mesh_compliance, shaft_compliance
from app.services.loaddist.distribution import (
    LoadDistribution,
    evaluate_load_distribution,
    solve_contact,
)
from app.services.loaddist.forces import (
    MeshForces,
    MeshStiffness,
    RikorMesh,
    build_stage,
    evaluate_mesh,
    mesh_forces,
    mesh_stiffness,
)
from app.services.loaddist.shaft import GapResult, mesh_gap

__all__ = [
    "GapResult",
    "LoadDistribution",
    "MeshForces",
    "MeshStiffness",
    "RikorMesh",
    "build_stage",
    "evaluate_load_distribution",
    "evaluate_mesh",
    "local_mesh_compliance",
    "mesh_forces",
    "mesh_gap",
    "mesh_stiffness",
    "shaft_compliance",
    "solve_contact",
]
