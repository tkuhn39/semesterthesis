"""
@module: app.services.loaddist.shaft
@context: Domain layer — RIKOR (FVA 30) load distribution, step R2: shaft–bearing
          deflection → mesh misalignment (the gap along the face width).
@role: Build each gear shaft as a stepped Timoshenko beam (cross-sections from the
       `.rie` UK/DA stations) on elastic bearing supports, load it with the mesh
       force over the gear face, and superpose the **bending + shear** deflection
       with the **torsional wind-up** of both shafts to get the gap g(b): the
       relative flank misalignment over the face width that, for a uniform load,
       equals RIKOR's "Gesamtkorrektur". Feeds the load-distribution solver (R3)
       and the capacity's K_Hβ (Method C) via the equivalent misalignment f_βx.

Reproduces RIKOR standard test 001 in shape and magnitude (peak gap ≈ 44 µm vs the
report's 41.8 µm; vertex in the loaded face): bending dominates, torsion sets the
asymmetry, shear lifts the peak. A bit-exact match needs RIKOR's internal
torque-transfer/bearing-tilt conventions; the physics here is the documented method.
"""

import math

import numpy as np
from numpy.typing import NDArray

from app.io.rie import Gear, RikorInput, Shaft
from app.io.ste import Pair
from app.services.loaddist.beam import BeamModel
from app.services.loaddist.forces import build_stage, evaluate_mesh

Array = NDArray[np.float64]

_E_STEEL_MPA = 210000.0
_POISSON = 0.3
_G_STEEL = _E_STEEL_MPA / (2.0 * (1.0 + _POISSON))
_SHEAR_KAPPA = 6.0 * (1.0 + _POISSON) / (7.0 + 6.0 * _POISSON)  # solid circular section
_FACE_STEPS_DEFAULT = 50


class GapResult:
    """The mesh gap over the face width (R2 result), with its components."""

    def __init__(
        self,
        face_mm: Array,
        gap_um: Array,
        bending_um: Array,
        torsion_um: Array,
    ) -> None:
        self.face_mm = face_mm  # b coordinate, 0 … common face width
        self.gap_um = gap_um  # relative approach (line of action), mean-referenced
        self.bending_um = bending_um  # bending+shear part
        self.torsion_um = torsion_um  # torsional wind-up part

    @property
    def correction_um(self) -> Array:
        """Gesamtkorrektur: material to add for uniform load = max approach − approach."""
        return float(self.gap_um.max()) - self.gap_um

    @property
    def peak_correction_um(self) -> float:
        return float(self.correction_um.max())

    @property
    def equivalent_misalignment_um(self) -> float:
        """Linear equivalent misalignment f_βx = best-fit slope × face width (ISO K_Hβ input)."""
        b = self.face_mm
        slope = np.polyfit(b, self.gap_um, 1)[0]
        return abs(slope * (b[-1] - b[0]))


def _da_at(stations: list, position: float) -> float:
    """Outer diameter of the stepped shaft at an axial position (last station ≤ x)."""
    diameter = 0.0
    for s in stations:
        if s.position_mm <= position:
            diameter = s.outer_diameter_mm
    return diameter


def _di_at(stations: list, position: float) -> float:
    bore = 0.0
    for s in stations:
        if s.position_mm <= position:
            bore = s.inner_diameter_mm
    return bore


def _shaft_bending(shaft: Shaft, gear: Gear, bearings: list, force_n: float, face: Array) -> Array:
    """Timoshenko bending+shear deflection of a shaft over the gear face (line of action)."""
    stations = sorted(shaft.stations, key=lambda s: s.position_mm)
    g0 = gear.axial_position_mm or 0.0
    g1 = g0 + (gear.face_width_mm or 0.0)
    grid = sorted(
        {s.position_mm for s in stations}
        | {b.position_mm for b in bearings if b.position_mm is not None}
        | set(np.linspace(g0, g1, 61))
    )
    nodes = np.array(grid)
    ei = np.empty(nodes.size - 1)
    ga = np.empty(nodes.size - 1)
    for e in range(nodes.size - 1):
        mid = 0.5 * (nodes[e] + nodes[e + 1])
        d_o, d_i = _da_at(stations, mid), _di_at(stations, mid)
        area = math.pi / 4.0 * max(d_o**2 - d_i**2, 1.0)
        inertia = math.pi / 64.0 * max(d_o**4 - d_i**4, 1.0e3)
        ei[e] = _E_STEEL_MPA * inertia
        ga[e] = _G_STEEL * _SHEAR_KAPPA * area
    beam = BeamModel(nodes, ei, ga)
    for b in bearings:
        if b.position_mm is not None and b.radial_stiffness_n_per_um is not None:
            beam.add_support(b.position_mm, b.radial_stiffness_n_per_um)
    beam.add_distributed_load(g0, g1, force_n)
    return beam.deflection_at(g0 + face)


def _shaft_torsion(
    shaft: Shaft, gear: Gear, torque_nmm: float, base_radius_mm: float, face: Array
) -> Array:
    """Torsional flank displacement r_b·Δφ over the gear face (wind-up of the loaded teeth).

    The torque flows from the input/output station to the gear; across the engaged
    face it is reacted uniformly (uniform load), so the transmitted torque falls
    linearly from full (near the in/out side) to zero. The accumulated twist φ(b),
    mean-referenced, maps to a line-of-action displacement r_b·(φ − φ̄).
    """
    stations = sorted(shaft.stations, key=lambda s: s.position_mm)
    g0 = gear.axial_position_mm or 0.0
    g1 = g0 + (gear.face_width_mm or 0.0)
    drive_x = next((s.position_mm for s in stations if s.applied_torque_nm is not None), g0)
    near = g0 if abs(drive_x - g0) <= abs(drive_x - g1) else g1
    far = g1 if near == g0 else g0

    def transmitted(x: float) -> float:
        if (x - near) * (far - near) <= 0.0:  # between the in/out side and the gear
            return torque_nmm
        frac = min(max((x - near) / (far - near), 0.0), 1.0)
        return torque_nmm * (1.0 - frac)

    samples = np.linspace(min(drive_x, g0), g1, 400)
    rate = np.array(
        [
            transmitted(x) / (_G_STEEL * math.pi / 32.0 * max(_da_at(stations, x) ** 4, 1.0e3))
            for x in samples
        ]
    )
    twist = np.concatenate([[0.0], np.cumsum(0.5 * (rate[:-1] + rate[1:]) * np.diff(samples))])
    phi = np.interp(g0 + face, samples, twist)
    return base_radius_mm * (phi - phi.mean())


def mesh_gap(ri: RikorInput, *, face_steps: int | None = None) -> GapResult:
    """The mesh gap g(b) over the common face width from both shafts' deflection.

    g(b) = Σ shaft bending+shear deflection + Σ torsional wind-up, in the line of
    action; mean-referenced. For a uniform load this is RIKOR's Gesamtkorrektur.
    """
    mesh = evaluate_mesh(ri)
    stage = mesh.stage
    steps = face_steps or (
        ri.stage.face_steps if ri.stage and ri.stage.face_steps else _FACE_STEPS_DEFAULT
    )
    width = stage.face_width_mm or Pair(0.0, 0.0)
    common = min(w for w in width if w > 0.0)
    face = np.linspace(0.0, common, steps)

    f_bt = mesh.forces.tangential_force_n
    torque_nmm = mesh.design_torque_nm * 1000.0
    base_radius = Pair(stage.base_diameter_mm[0] / 2.0, stage.base_diameter_mm[1] / 2.0)

    bending = np.zeros(steps)
    torsion = np.zeros(steps)
    drive, _driven = _ordered_gears(ri)
    for index, gear in enumerate((drive, _driven)):
        shaft = next(s for s in ri.shafts if s.index == gear.shaft_index)
        bearings = ri.bearings_on(gear.shaft_index)
        bending += _shaft_bending(shaft, gear, bearings, f_bt, face)
        torsion += _shaft_torsion(shaft, gear, torque_nmm, base_radius[index], face)

    bending_um = 1000.0 * (bending - bending.mean())
    torsion_um = 1000.0 * torsion
    gap_um = bending_um + torsion_um
    return GapResult(face, gap_um, bending_um, torsion_um)


def _ordered_gears(ri: RikorInput) -> tuple[Gear, Gear]:
    from app.services.loaddist.forces import _drive_then_driven

    return _drive_then_driven(ri)


__all__ = ["GapResult", "mesh_gap", "build_stage"]
