// Typed client for the gear-analysis backend (FastAPI). The base URL comes from
// the shared 20_code/.env (VITE_API_BASE_URL); empty means same-origin.

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

// ---- Types (mirror the pydantic response models) ----
export interface ExampleGear {
  role: string;
  material: string;
  kind: string;
  teeth: number;
  profile_shift: number;
  reference_diameter_mm: number;
  tip_diameter_mm: number;
  face_width_mm: number;
}
export interface ExampleResponse {
  name: string;
  description: string;
  normal_module_mm: number;
  normal_pressure_angle_deg: number;
  helix_angle_deg: number;
  center_distance_mm: number;
  working_pressure_angle_deg: number;
  transverse_contact_ratio: number;
  overlap_ratio: number;
  total_contact_ratio: number;
  gears: ExampleGear[];
  notes: string[];
}

export interface GeometryRequest {
  normal_module_mm: number;
  teeth_pinion: number;
  teeth_wheel: number;
  profile_shift_pinion: number;
  profile_shift_wheel: number;
  normal_pressure_angle_deg: number;
  helix_angle_deg: number;
  face_width_mm: number;
}
export interface GeometryResponse {
  reference_diameter_mm: [number, number];
  base_diameter_mm: [number, number];
  tip_diameter_mm: [number, number];
  working_pressure_angle_deg: number;
  working_center_distance_mm: number;
  transverse_contact_ratio: number;
  overlap_ratio: number;
  total_contact_ratio: number;
  valid: boolean;
  notes: string[];
}

export interface GearCapacity {
  label: string;
  material: string;
  method: string;
  flank_stress_mpa: number;
  flank_permissible_mpa: number | null;
  flank_safety: number | null;
  root_stress_mpa: number;
  root_permissible_mpa: number | null;
  root_safety: number | null;
  form_factor: number;
  stress_correction: number;
  tooth_temperature_c: number | null;
  wear_um: number | null;
  allowable_wear_um: number | null;
  deformation_mm: number | null;
}
export interface CapacityFactors {
  application_factor: number;
  dynamic_factor: number;
  transverse_factor: number;
  face_load_factor: number;
  elasticity_factor: number;
  zone_factor: number;
}
export interface CapacityResponse {
  factors: CapacityFactors;
  pinion: GearCapacity;
  wheel: GearCapacity;
}
export interface CapacityRequest {
  pinion_torque_nm: number;
  pinion_speed_min1: number;
  application_factor: number;
  compute_dynamics: boolean;
  dynamic_factor: number;
  face_load_factor: number;
  base_pitch_deviation_um: number;
  profile_form_deviation_um: number;
  lubricant_viscosity_40_mm2s: number;
  flank_roughness_rz_um: number;
  root_roughness_rz_um: number;
  flank_life_factor: number;
  root_life_factor: number;
  steel_modulus_mpa: number;
  steel_poisson: number;
  steel_sigma_hlim_mpa: number;
  steel_sigma_flim_mpa: number;
  power_w: number;
  ambient_temperature_c: number;
  duty_cycle: number;
  housing_surface_m2: number;
  friction_coefficient: number;
  wear_coefficient_e6: number;
  load_cycles: number;
  root_minimum_safety: number;
  flank_minimum_safety: number;
  plastic_modulus_mpa: number;
  plastic_poisson: number;
  plastic_sigma_hlim_mpa: number;
  plastic_sigma_flim_mpa: number;
}

export interface DynamicsRequest {
  pinion_speed_min1: number;
  pinion_torque_nm: number;
  application_factor: number;
  base_pitch_deviation_um: number;
  profile_form_deviation_um: number;
}
export interface DynamicsResponse {
  dynamic_factor: number;
  transverse_factor_flank: number;
  transverse_factor_root: number;
  face_load_factor_flank: number;
  mesh_stiffness: number;
  reduced_mass: number;
  resonance_speed_min1: number;
  resonance_ratio: number;
  regime: string;
}

export interface VarSpec {
  vary: boolean;
  value: number;
  min: number;
  max: number;
  steps: number;
}
export interface VariationRequest {
  m_n: VarSpec;
  z1: VarSpec;
  z2: VarSpec;
  x1: VarSpec;
  x2: VarSpec;
  beta_deg: VarSpec;
  b: VarSpec;
  normal_pressure_angle_deg: number;
  tool_addendum_factor: number;
  tool_tip_radius_factor: number;
  torque_nm: number;
  steel_density_kg_m3: number;
  plastic_density_kg_m3: number;
  steel_sigma_hlim_mpa: number;
  steel_sigma_flim_mpa: number;
  plastic_sigma_hlim_mpa: number;
  plastic_sigma_flim_mpa: number;
  root_minimum_safety: number;
  flank_minimum_safety: number;
  method: "grid" | "sobol" | "lhs";
  sample_count: number;
}
export interface VariationPoint {
  m_n: number;
  z1: number;
  z2: number;
  x1: number;
  x2: number;
  beta_deg: number;
  b: number;
  center_distance_mm: number;
  transverse_contact_ratio: number;
  overlap_ratio: number;
  total_contact_ratio: number;
  root_safety_pinion: number | null;
  root_safety_wheel: number | null;
  flank_safety_pinion: number | null;
  flank_safety_wheel: number | null;
  weight_g: number;
  pareto: boolean;
}
export interface VariationResponse {
  count: number;
  valid: number;
  pareto: number;
  eval_ms: number;
  varied: string[];
  points: VariationPoint[];
  warnings: string[];
}

export const api = {
  health: () => get<{ status: string; version: string }>("/api/health"),
  example: () => get<ExampleResponse>("/api/example/kst-e"),
  geometry: (req: GeometryRequest) => post<GeometryResponse>("/api/geometry", req),
  capacity: (req: CapacityRequest) => post<CapacityResponse>("/api/capacity", req),
  dynamics: (req: DynamicsRequest) => post<DynamicsResponse>("/api/dynamics", req),
  variation: (req: VariationRequest) => post<VariationResponse>("/api/variation", req),
};
