"""
@module: app.services.model.abaqus_writer
@context: Domain layer — FE rolling model, the Abaqus `.inp` generator (replaces the
          Workbench export, WoBe-892 §3.3.1). Turns the structured mesh + tagged
          surfaces into a keyword deck.
@role: Build the deck text for a meshed gear: a `*PART` (nodes, C3D8 elements, the
       Fesselung node set, the per-tooth flank `*SURFACE`s, a `*SOLID SECTION`) inside
       an `*ASSEMBLY` with a master node and a `*RIGID BODY` tying the bore + cut faces
       to it, the `*MATERIAL`, and one quasi-static `*STEP`. Pure text (no file I/O — the
       caller persists via `app.storage`); the steel pinion as a rigid shell and the
       flank contact pairs + rolling amplitude sequence plug in next. Every quantity is
       a parameter (material, kinematics, master node) — nothing hardcoded.
"""

from dataclasses import dataclass

from app.services.model.gmsh_mesher import Mesh3D
from app.services.model.mesh_sets import SectorSurfaces


@dataclass(frozen=True)
class ElasticMaterial:
    """An isotropic linear-elastic material (the plastic wheel's first-order model)."""

    name: str
    youngs_modulus_mpa: float
    poisson_ratio: float
    density_t_per_mm3: float | None = None


def _wrap(ids: list[int], per_line: int = 16) -> str:
    """One id per column, ``per_line`` columns per row (Abaqus set-line limit)."""
    rows = [ids[i : i + per_line] for i in range(0, len(ids), per_line)]
    return "\n".join(", ".join(str(v) for v in row) for row in rows)


def _node_block(mesh: Mesh3D) -> str:
    lines = [f"{i + 1}, {x:.6f}, {y:.6f}, {z:.6f}" for i, (x, y, z) in enumerate(mesh.nodes)]
    return "*NODE\n" + "\n".join(lines)


def _element_block(mesh: Mesh3D, elset: str) -> str:
    lines = [
        f"{e + 1}, " + ", ".join(str(n + 1) for n in hexa) for e, hexa in enumerate(mesh.hexes)
    ]
    return f"*ELEMENT, TYPE=C3D8, ELSET={elset}\n" + "\n".join(lines)


def _surface_blocks(surfaces: SectorSurfaces) -> str:
    blocks: list[str] = []
    for name, entries in surfaces.faces.items():
        rows = "\n".join(f"{hex_index + 1}, {face}" for hex_index, face in entries)
        blocks.append(f"*SURFACE, NAME={name}, TYPE=ELEMENT\n{rows}")
    return "\n".join(blocks)


def _fesselung_nodes(surfaces: SectorSurfaces) -> list[int]:
    """The bore + radial-cut nodes (1-based) tied to the master node (the Fesselung)."""
    ids: set[int] = set()
    for key in ("BORE", "CUT"):
        if key in surfaces.node_sets:
            ids.update(int(n) + 1 for n in surfaces.node_sets[key])
    return sorted(ids)


def build_gear_deck(
    mesh: Mesh3D,
    surfaces: SectorSurfaces,
    *,
    material: ElasticMaterial,
    rotation_rad: float,
    master_node_id: int = 9_000_001,
    axis_z_mm: float = 0.0,
    part_name: str = "WHEEL",
    instance_name: str = "WHEEL-1",
    elset: str = "ALL_ELEMENTS",
    heading: str = "FE rolling model (generated)",
) -> str:
    """Build a complete quasi-static `.inp` for one meshed gear, fastened at bore + cut.

    The master node carries the gear's rigid-body rotation; DOF 1–5 are fixed and DOF 6
    is driven to ``rotation_rad``. This is the structural skeleton — the mating gear and
    the flank contact that turn rotation into root load are added in the next step.
    """
    fesselung = _wrap(_fesselung_nodes(surfaces))
    density = ""
    if material.density_t_per_mm3 is not None:
        density = f"\n*DENSITY\n{material.density_t_per_mm3:.6e},"
    elastic = f"{material.youngs_modulus_mpa:.6g}, {material.poisson_ratio:.6g}"

    return "\n".join(
        part
        for part in (
            f"*HEADING\n{heading}",
            "**",
            f"*PART, NAME={part_name}",
            _node_block(mesh),
            _element_block(mesh, elset),
            f"*NSET, NSET=FESSELUNG\n{fesselung}",
            _surface_blocks(surfaces),
            f"*SOLID SECTION, ELSET={elset}, MATERIAL={material.name}\n1.,",
            "*END PART",
            "**",
            "*ASSEMBLY, NAME=Assembly",
            f"*INSTANCE, NAME={instance_name}, PART={part_name}\n*END INSTANCE",
            f"*NODE, NSET=MASTER\n{master_node_id}, 0., 0., {axis_z_mm:.6f}",
            f"*RIGID BODY, REF NODE={master_node_id}, TIE NSET={instance_name}.FESSELUNG",
            "*END ASSEMBLY",
            "**",
            f"*MATERIAL, NAME={material.name}\n*ELASTIC\n{elastic}{density}",
            "**",
            "*STEP, NLGEOM=YES",
            "*STATIC\n0.1, 1.0",
            f"*BOUNDARY\nMASTER, 1, 5\n*BOUNDARY\nMASTER, 6, 6, {rotation_rad:.8g}",
            "*OUTPUT, FIELD, VARIABLE=PRESELECT",
            "*END STEP",
        )
        if part
    )
