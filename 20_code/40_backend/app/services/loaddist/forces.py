"""
@module: app.services.loaddist.forces
@context: Domain layer — RIKOR (FVA 30) load distribution, step R1: nominal mesh
          forces and the mesh line stiffness.
@role: Resolve the nominal gear-mesh forces (tangential/normal/axial at the base
       circle, mean line load) and the ISO 6336-1 mesh stiffness c_γ for a RIKOR
       input, building the meshing `GearStage` from the two `.rie` gears via the
       native generation (`GearStage.from_parameters`). These feed the shaft
       deflection (R2) and the load-distribution solver (R3). The stiffness chain
       (c′_th, C_B, c′, c_γα/c_γβ) is reused from `capacity.iso6336_dynamics` — one
       mesh-stiffness implementation for both the dynamic factor and RIKOR.

Validated against RIKOR standard test 001 (single helical stage): F_bt 167555.8 N,
F_bt/b 1319.34 N/mm, F_bn 170316.0 N, F_bx 30538.0 N, c′_th 18.4, C_B 0.87,
c_γ 16.7 N/(µm·mm).
"""

import math

from pydantic import BaseModel

from app.io.rie import Gear, RikorInput
from app.io.ste import Pair
from app.services.capacity.iso6336_dynamics import (
    basic_rack_factor,
    mesh_stiffness_alpha,
    mesh_stiffness_beta,
    single_stiffness,
    theoretical_single_stiffness,
)
from app.services.geometry.gear import GearStage, ToolReferenceProfile

_DEFAULT_PRESSURE_ANGLE_DEG = 20.0  # RIKOR default α_n when not given in the .rie
_DEFAULT_TOOL_TIP_RADIUS = 0.38  # ρ_aP0*/m_n; irrelevant to forces/stiffness (tip given)


class MeshForces(BaseModel):
    """Nominal mesh forces at the base circle (design load = K_A · nominal)."""

    design_torque_nm: float  # T = K_A · T_nom (drive gear)
    tangential_force_n: float  # F_bt
    normal_force_n: float  # F_bn
    axial_force_n: float  # F_bx
    line_load_n_per_mm: float  # F_bt/b (mean over the common face width)
    common_face_width_mm: float


class MeshStiffness(BaseModel):
    """ISO 6336-1 mesh stiffness chain (the line stiffness for the load sharing)."""

    theoretical_single: float  # c′_th  (RIKOR c_sth)
    basic_rack_factor: float  # C_B
    single: float  # c′
    mesh_alpha: float  # c_γα  (RIKOR c_γ)  [N/(mm·µm)]
    mesh_beta: float  # c_γβ


class RikorMesh(BaseModel):
    """The meshing pair resolved from a RIKOR input: geometry, forces, stiffness."""

    stage: GearStage
    design_torque_nm: float
    normal_pressure_angle_deg: float
    dedendum_factors: Pair[float]  # h_fP*/m_n per gear (drive, driven)
    forces: MeshForces
    stiffness: MeshStiffness


def _drive_then_driven(ri: RikorInput) -> tuple[Gear, Gear]:
    """Order the two gears (drive = the shaft carrying the input torque, else fewer teeth)."""
    if len(ri.gears) != 2:
        raise ValueError(f"expected a single stage (2 gears), got {len(ri.gears)}")
    torque_shafts = {s.index for s in ri.shafts if s.applied_torque_nm is not None}
    a, b = ri.gears
    if a.shaft_index in torque_shafts and b.shaft_index not in torque_shafts:
        return a, b
    if b.shaft_index in torque_shafts and a.shaft_index not in torque_shafts:
        return b, a
    # fall back to tooth count (pinion = fewer teeth)
    return (a, b) if (a.teeth or 0) <= (b.teeth or 0) else (b, a)


def _require(value: float | None, name: str, gear: Gear) -> float:
    if value is None:
        raise ValueError(f"gear on shaft {gear.shaft_index} lacks {name}")
    return value


def build_stage(ri: RikorInput) -> tuple[GearStage, Pair[float], float]:
    """Build the meshing `GearStage` from the two RIKOR gears (drive first).

    Returns the stage, the per-gear dedendum factors h_fP* (= the tool addendum
    HA0, drive then driven), and the normal pressure angle used.
    """
    drive, driven = _drive_then_driven(ri)
    module = _require(drive.normal_module_mm, "normal module", drive)
    z = Pair(
        int(_require(drive.teeth, "teeth", drive)), int(_require(driven.teeth, "teeth", driven))
    )
    alpha_n = _DEFAULT_PRESSURE_ANGLE_DEG
    helix = abs(drive.helix_angle_deg)
    ha = Pair(drive.addendum_factor or 1.0, driven.addendum_factor or 1.0)
    tools = Pair(
        ToolReferenceProfile(
            addendum_factor=ha[0],
            tip_radius_factor=_DEFAULT_TOOL_TIP_RADIUS,
            normal_pressure_angle_deg=alpha_n,
        ),
        ToolReferenceProfile(
            addendum_factor=ha[1],
            tip_radius_factor=_DEFAULT_TOOL_TIP_RADIUS,
            normal_pressure_angle_deg=alpha_n,
        ),
    )
    tips = (
        Pair(drive.tip_diameter_mm, driven.tip_diameter_mm)
        if drive.tip_diameter_mm is not None and driven.tip_diameter_mm is not None
        else None
    )
    stage = GearStage.from_parameters(
        normal_module_mm=module,
        teeth=z,
        profile_shift=Pair(drive.profile_shift, driven.profile_shift),
        face_width_mm=Pair(
            _require(drive.face_width_mm, "face width", drive),
            _require(driven.face_width_mm, "face width", driven),
        ),
        tool=tools,
        normal_pressure_angle_deg=alpha_n,
        helix_angle_deg=helix,
        tip_diameter_mm=tips,
    )
    return stage, ha, alpha_n


def mesh_forces(stage: GearStage, *, design_torque_nm: float) -> MeshForces:
    """Nominal forces at the base circle from the drive-gear design torque (eq. base-circle).

    F_bt = 2000·T/d_b1; F_bx = F_bt·tan β_b; F_bn = F_bt/cos β_b; line load over the
    common (smaller) face width.
    """
    d_b1 = stage.base_diameter_mm[0]
    beta = math.radians(stage.helix_angle_deg)
    alpha_n = math.radians(stage.normal_pressure_angle_deg)
    beta_b = math.asin(math.sin(beta) * math.cos(alpha_n))
    f_bt = 2000.0 * design_torque_nm / d_b1
    width = stage.face_width_mm or Pair(0.0, 0.0)
    common = min(w for w in width if w > 0.0)
    return MeshForces(
        design_torque_nm=design_torque_nm,
        tangential_force_n=f_bt,
        normal_force_n=f_bt / math.cos(beta_b),
        axial_force_n=f_bt * math.tan(beta_b),
        line_load_n_per_mm=f_bt / common,
        common_face_width_mm=common,
    )


def mesh_stiffness(
    stage: GearStage, *, dedendum_factors: Pair[float], normal_pressure_angle_deg: float
) -> MeshStiffness:
    """ISO 6336-1 mesh line stiffness c_γ (reusing the dynamics stiffness chain)."""
    beta = math.radians(stage.helix_angle_deg)
    alpha_n = math.radians(normal_pressure_angle_deg)
    beta_b = math.asin(math.sin(beta) * math.cos(alpha_n))
    cos_b = math.cos(beta_b)
    virtual_teeth = Pair(
        stage.teeth[0] / (cos_b**2 * math.cos(beta)),
        stage.teeth[1] / (cos_b**2 * math.cos(beta)),
    )
    c_th = theoretical_single_stiffness(virtual_teeth, stage.profile_shift)
    c_b = basic_rack_factor(dedendum_factors, normal_pressure_angle_deg)
    c_prime = single_stiffness(c_th, c_b, stage.helix_angle_deg)
    c_ga = mesh_stiffness_alpha(c_prime, stage.transverse_contact_ratio)
    return MeshStiffness(
        theoretical_single=c_th,
        basic_rack_factor=c_b,
        single=c_prime,
        mesh_alpha=c_ga,
        mesh_beta=mesh_stiffness_beta(c_ga),
    )


def evaluate_mesh(ri: RikorInput) -> RikorMesh:
    """Resolve geometry, design torque, nominal forces and mesh stiffness for a stage."""
    stage, dedendum, alpha_n = build_stage(ri)
    drive, _ = _drive_then_driven(ri)
    drive_shaft = next((s for s in ri.shafts if s.index == drive.shaft_index), None)
    nominal_torque = (
        abs(drive_shaft.applied_torque_nm) if drive_shaft and drive_shaft.applied_torque_nm else 0.0
    )
    design_torque = nominal_torque * ri.config.application_factor
    return RikorMesh(
        stage=stage,
        design_torque_nm=design_torque,
        normal_pressure_angle_deg=alpha_n,
        dedendum_factors=dedendum,
        forces=mesh_forces(stage, design_torque_nm=design_torque),
        stiffness=mesh_stiffness(
            stage, dedendum_factors=dedendum, normal_pressure_angle_deg=alpha_n
        ),
    )
