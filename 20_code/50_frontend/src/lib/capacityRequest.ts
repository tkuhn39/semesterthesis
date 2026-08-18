// THE capacity request assembled from the workbench store (single source of truth):
// geometry (stage), load case (Leistungsfluss derived values), operating conditions,
// tolerances grade and the material selection (norm dispatch per gear). Shared by the
// CapacityPanel and the report collector — never duplicated per panel.

import type { CapacityRequest } from "@/lib/api";
import type { useWorkbench } from "@/lib/store";

export type Wb = ReturnType<typeof useWorkbench>;

export function buildCapacityRequest(wb: Wb): CapacityRequest {
  const op = wb.operating;
  const m = wb.materials;
  return {
    stage: wb.stage,
    pinion_material: m.gear1_kind,
    wheel_material: m.gear2_kind,
    pinion_torque_nm: wb.get("operating.pinion_torque_nm") as number,
    pinion_speed_min1: wb.get("operating.pinion_speed_min1") as number,
    application_factor: op.application_factor,
    compute_dynamics: op.compute_dynamics,
    dynamic_factor: op.dynamic_factor,
    // K_Hβ: the untouched default 1.0 means "compute natively" (ISO 6336-1 Method C);
    // any user-entered value stays an explicit override
    face_load_factor: op.face_load_factor === 1.0 ? null : op.face_load_factor,
    accuracy_grade: op.accuracy_grade,
    base_pitch_deviation_um: op.base_pitch_deviation_um,
    profile_form_deviation_um: op.profile_form_deviation_um,
    helix_slope_deviation_um: op.helix_slope_deviation_um,
    mesh_misalignment_um: op.mesh_misalignment_um,
    lubricant_viscosity_40_mm2s: op.lubricant_viscosity_40_mm2s,
    flank_roughness_rz_um: op.flank_roughness_rz_um,
    root_roughness_rz_um: op.root_roughness_rz_um,
    flank_life_factor: op.flank_life_factor,
    root_life_factor: op.root_life_factor,
    pinion_material_group: m.gear1_root_group,
    wheel_material_group: m.gear2_root_group,
    softer_gear_hardness_hb: m.softer_gear_hardness_hb,
    steel_modulus_mpa: m.steel_modulus_mpa,
    steel_poisson: m.steel_poisson,
    steel_sigma_hlim_mpa: m.steel_sigma_hlim_mpa,
    steel_sigma_flim_mpa: m.steel_sigma_flim_mpa,
    power_w: wb.get("operating.power_w") as number,
    ambient_temperature_c: wb.get("operating.ambient_temperature_c") as number,
    duty_cycle: op.duty_cycle,
    housing_surface_m2: op.housing_surface_m2,
    friction_coefficient: op.friction_coefficient,
    wear_coefficient_e6: op.wear_coefficient_e6,
    load_cycles: wb.get("operating.load_cycles") as number,
    root_minimum_safety: op.root_minimum_safety,
    flank_minimum_safety: op.flank_minimum_safety,
    plastic_modulus_mpa: m.plastic_modulus_mpa,
    plastic_poisson: m.plastic_poisson,
    plastic_sigma_hlim_mpa: m.plastic_sigma_hlim_mpa,
    plastic_sigma_flim_mpa: m.plastic_sigma_flim_mpa,
    static_overload_factor:
      op.static_mode === "value" ? (op.static_overload_factor ?? 2.0) : null,
    static_minimum_safety: op.static_minimum_safety,
    plastic_yield_strength_mpa: m.plastic_yield_strength_mpa,
  };
}
