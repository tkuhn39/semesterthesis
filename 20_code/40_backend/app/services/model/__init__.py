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

from app.services.model.abaqus_writer import (
    ElasticMaterial,
    RollingSetup,
    build_gear_deck,
    build_rolling_deck,
)
from app.services.model.implicit_deck import (
    GearPart,
    RollKinematics,
    build_gear_part,
    build_implicit_pair_deck,
    build_implicit_pair_from_stage,
)
from app.services.model.mapped_mesher import (
    mesh_pitch_mapped_2d,
    mesh_pitch_mapped_3d,
    mesh_sector_mapped_2d,
    mesh_sector_mapped_3d,
)
from app.services.model.materials_card import (
    LinearElastic,
    MarlowUniaxial,
    Material,
    material_card,
)
from app.services.model.mesh3d import Mesh3D, extrude_to_hex
from app.services.model.mesh_sets import (
    GearReferenceSets,
    SectorSurfaces,
    tag_gear_reference,
    tag_sector_surfaces,
)
from app.services.model.tooth_mesh import Mesh2D, tooth_sector_2d

__all__ = [
    "ElasticMaterial",
    "GearPart",
    "GearReferenceSets",
    "LinearElastic",
    "MarlowUniaxial",
    "Material",
    "Mesh2D",
    "Mesh3D",
    "RollKinematics",
    "RollingSetup",
    "SectorSurfaces",
    "build_gear_deck",
    "build_gear_part",
    "build_implicit_pair_deck",
    "build_implicit_pair_from_stage",
    "build_rolling_deck",
    "extrude_to_hex",
    "material_card",
    "mesh_pitch_mapped_2d",
    "mesh_pitch_mapped_3d",
    "mesh_sector_mapped_2d",
    "mesh_sector_mapped_3d",
    "tag_gear_reference",
    "tag_sector_surfaces",
    "tooth_sector_2d",
]
