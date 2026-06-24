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

from app.services.model.mesh3d import Mesh3D
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


def _surface_block(name: str, entries: list[tuple[int, str]]) -> str:
    rows = "\n".join(f"{hex_index + 1}, {face}" for hex_index, face in entries)
    return f"*SURFACE, NAME={name}, TYPE=ELEMENT\n{rows}"


def _surface_blocks(surfaces: SectorSurfaces) -> str:
    blocks = [_surface_block(name, entries) for name, entries in surfaces.faces.items()]
    flank_faces = [
        fe for name, ents in surfaces.faces.items() if name.startswith("FLANK") for fe in ents
    ]
    if flank_faces:  # one combined contact surface (all tooth flanks that can touch)
        blocks.append(_surface_block("FLANKS", flank_faces))
    return "\n".join(blocks)


def _fesselung_nodes(surfaces: SectorSurfaces) -> list[int]:
    """The bore + radial-cut nodes (1-based) tied to the master node (the Fesselung)."""
    ids: set[int] = set()
    for key in ("BORE", "CUT"):
        if key in surfaces.node_sets:
            ids.update(int(n) + 1 for n in surfaces.node_sets[key])
    return sorted(ids)


def _part_block(
    part_name: str, mesh: Mesh3D, surfaces: SectorSurfaces, material: ElasticMaterial, elset: str
) -> str:
    """A `*PART`: nodes, C3D8 elements, the Fesselung set, the surfaces, a solid section."""
    return "\n".join(
        (
            f"*PART, NAME={part_name}",
            _node_block(mesh),
            _element_block(mesh, elset),
            f"*NSET, NSET=FESSELUNG\n{_wrap(_fesselung_nodes(surfaces))}",
            _surface_blocks(surfaces),
            f"*SOLID SECTION, ELSET={elset}, MATERIAL={material.name}\n1.,",
            "*END PART",
        )
    )


def _material_block(material: ElasticMaterial) -> str:
    density = ""
    if material.density_t_per_mm3 is not None:
        density = f"\n*DENSITY\n{material.density_t_per_mm3:.6e},"
    elastic = f"{material.youngs_modulus_mpa:.6g}, {material.poisson_ratio:.6g}"
    return f"*MATERIAL, NAME={material.name}\n*ELASTIC\n{elastic}{density}"


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
    the flank contact that turn rotation into root load are added by ``build_rolling_deck``.
    """
    return "\n".join(
        (
            f"*HEADING\n{heading}",
            "**",
            _part_block(part_name, mesh, surfaces, material, elset),
            "**",
            "*ASSEMBLY, NAME=Assembly",
            f"*INSTANCE, NAME={instance_name}, PART={part_name}\n*END INSTANCE",
            f"*NODE, NSET=MASTER\n{master_node_id}, 0., 0., {axis_z_mm:.6f}",
            f"*RIGID BODY, REF NODE={master_node_id}, TIE NSET={instance_name}.FESSELUNG",
            "*END ASSEMBLY",
            "**",
            _material_block(material),
            "**",
            "*STEP, NLGEOM=YES",
            "*STATIC\n0.1, 1.0",
            f"*BOUNDARY\nMASTER, 1, 5\n*BOUNDARY\nMASTER, 6, 6, {rotation_rad:.8g}",
            "*OUTPUT, FIELD, VARIABLE=PRESELECT",
            "*END STEP",
        )
    )


@dataclass(frozen=True)
class RollingSetup:
    """The mating kinematics + load for the rolling model — every value a parameter."""

    center_distance_mm: float
    wheel_torque_nmm: float  # resisting moment on the plastic wheel (DOF6)
    roll_span_rad: float  # pinion rotation swept while meshing (~2 transverse pitches)
    n_roll_positions: int = 30  # Wälzstellungen — output frames over the roll (adjustable)
    pinion_phase_deg: float = 180.0  # pinion mounting angle about its axis (tunable to mesh)
    penetration_mm: float = 0.0  # initial flank overlap to seed contact (~1 % pitch)
    wheel_axis_z_mm: float = 0.0
    pinion_axis_z_mm: float = 0.0
    stabilize: float = 2.0e-4


def build_rolling_deck(
    *,
    wheel_mesh: Mesh3D,
    wheel_surfaces: SectorSurfaces,
    wheel_material: ElasticMaterial,
    pinion_mesh: Mesh3D,
    pinion_surfaces: SectorSurfaces,
    pinion_material: ElasticMaterial,
    setup: RollingSetup,
    heading: str = "FE rolling model - plastic wheel + rigid steel pinion (generated)",
) -> str:
    """Build the full WoBe-892 rolling deck: meshed plastic wheel + rigid steel pinion.

    The wheel is fastened at its bore/cut to its master node and carries the resisting
    torque on DOF6; the pinion is made rigid (`*RIGID BODY` over its elements) and driven
    through ``setup.roll_span_rad``. Step 1 engages contact and ramps the torque; step 2
    rolls the pinion in ``setup.n_roll_positions`` equal increments (the Wälzstellungen),
    one output frame each — so the position count is a parameter, not baked in.
    """
    wheel_master, pinion_master = 9_000_001, 9_000_002
    a = setup.center_distance_mm - setup.penetration_mm
    pz = setup.pinion_axis_z_mm
    dt = 1.0 / setup.n_roll_positions
    pinion = _part_block("PINION", pinion_mesh, pinion_surfaces, pinion_material, "PINION_EL")
    wheel = _part_block("WHEEL", wheel_mesh, wheel_surfaces, wheel_material, "WHEEL_EL")

    assembly = "\n".join(
        (
            "*ASSEMBLY, NAME=Assembly",
            "*INSTANCE, NAME=WHEEL-1, PART=WHEEL\n*END INSTANCE",
            f"*INSTANCE, NAME=PINION-1, PART=PINION\n0., {a:.6f}, 0.\n"
            f"0., 0., 0., 0., 0., 1., {setup.pinion_phase_deg:.6f}\n*END INSTANCE",
            f"*NODE, NSET=WHEEL_MASTER\n{wheel_master}, 0., 0., {setup.wheel_axis_z_mm:.6f}",
            f"*NODE, NSET=PINION_MASTER\n{pinion_master}, 0., {a:.6f}, {pz:.6f}",
            f"*RIGID BODY, REF NODE={wheel_master}, TIE NSET=WHEEL-1.FESSELUNG",
            f"*RIGID BODY, REF NODE={pinion_master}, ELSET=PINION-1.PINION_EL",
            "*SURFACE INTERACTION, NAME=FLANK_CONTACT",
            "*FRICTION\n0.,",
            "*CONTACT PAIR, INTERACTION=FLANK_CONTACT, TYPE=SURFACE TO SURFACE",
            "WHEEL-1.FLANKS, PINION-1.FLANKS",
            "*END ASSEMBLY",
        )
    )
    amplitudes = "\n".join(
        ("*AMPLITUDE, NAME=AMP_TORQUE\n0., 0., 1., 1.", "*AMPLITUDE, NAME=AMP_HOLD\n0., 1., 1., 1.")
    )
    engage = "\n".join(
        (
            f"*STEP, NLGEOM=YES, NAME=Engage\n*STATIC, STABILIZE={setup.stabilize:.3g}\n0.05, 1.0",
            "*BOUNDARY\nWHEEL_MASTER, 1, 5\nPINION_MASTER, 1, 6",
            f"*CLOAD, AMPLITUDE=AMP_TORQUE\nWHEEL_MASTER, 6, {setup.wheel_torque_nmm:.8g}",
            "*OUTPUT, FIELD, VARIABLE=PRESELECT",
            "*END STEP",
        )
    )
    roll = "\n".join(
        (
            f"*STEP, NLGEOM=YES, NAME=Roll, INC=100000\n*STATIC, DIRECT\n{dt:.8g}, 1.0",
            "*BOUNDARY\nWHEEL_MASTER, 1, 5",
            f"*BOUNDARY\nPINION_MASTER, 1, 5\nPINION_MASTER, 6, 6, {-setup.roll_span_rad:.8g}",
            f"*CLOAD, AMPLITUDE=AMP_HOLD\nWHEEL_MASTER, 6, {setup.wheel_torque_nmm:.8g}",
            "*OUTPUT, FIELD, FREQUENCY=1, VARIABLE=PRESELECT",
            "*END STEP",
        )
    )
    return "\n".join(
        (
            f"*HEADING\n{heading}",
            "**",
            wheel,
            "**",
            pinion,
            "**",
            assembly,
            "**",
            _material_block(wheel_material),
            _material_block(pinion_material),
            "**",
            amplitudes,
            "**",
            engage,
            "**",
            roll,
        )
    )
