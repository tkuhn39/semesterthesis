// Typed client for the gear-analysis backend (FastAPI). The base URL comes from
// the shared 20_code/.env (VITE_API_BASE_URL); empty means same-origin.

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

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
  peak_stress_mpa?: number | null;
  peak_safety?: number | null;
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
  accuracy_grade?: number | null;
  static_overload_factor?: number | null;
  static_minimum_safety?: number;
  plastic_yield_strength_mpa?: number | null;
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
  fix_center_distance: boolean;
  center_distance_mm: number;
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
  pinion_material?: "steel" | "plastic";
  wheel_material?: "steel" | "plastic";
  steel_modulus_mpa?: number;
  plastic_modulus_mpa?: number;
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

export interface ToothProfileRequest {
  normal_module_mm: number;
  teeth_pinion: number;
  teeth_wheel: number;
  profile_shift_pinion: number;
  profile_shift_wheel: number;
  normal_pressure_angle_deg: number;
  helix_angle_deg: number;
}
export interface ToothGear {
  teeth: number;
  center_x_mm: number;
  reference_radius_mm: number;
  base_radius_mm: number;
  tip_radius_mm: number;
  root_radius_mm: number;
  half_flank: [number, number][];
}
export interface ToothProfileResponse {
  center_distance_mm: number;
  pinion: ToothGear;
  wheel: ToothGear;
}

export const api = {
  health: () => get<{ status: string; version: string }>("/api/health"),
  example: () => get<ExampleResponse>("/api/example/kst-e"),
  geometry: (req: GeometryRequest) => post<GeometryResponse>("/api/geometry", req),
  capacity: (req: CapacityRequest) => post<CapacityResponse>("/api/capacity", req),
  dynamics: (req: DynamicsRequest) => post<DynamicsResponse>("/api/dynamics", req),
  variation: (req: VariationRequest) => post<VariationResponse>("/api/variation", req),
  toothProfile: (req: ToothProfileRequest) => post<ToothProfileResponse>("/api/tooth-profile", req),
};

// ---- Stage definition (design.py — kst-E example or free parameters, M6) ----
export interface FlankModification {
  tip_relief_um?: number;
  root_relief_um?: number;
  profile_crowning_um?: number;
  helix_crowning_um?: number;
  end_relief_um?: number;
  helix_slope_um?: number;
}
export interface GearModifications {
  left?: FlankModification;
  right?: FlankModification;
}
export interface StageParams {
  use_example: boolean;
  normal_module_mm: number;
  teeth_pinion: number;
  teeth_wheel: number;
  profile_shift_pinion: number;
  profile_shift_wheel: number;
  normal_pressure_angle_deg: number;
  helix_angle_deg: number;
  face_width_pinion_mm: number;
  face_width_wheel_mm: number;
  center_distance_mm?: number | null;
  tool_addendum_factor: number;
  tool_tip_radius_factor: number;
  tool_root_form_height_factor?: number | null;
  tool_edge_break_angle_deg?: number | null;
  modifications_pinion?: GearModifications;
  modifications_wheel?: GearModifications;
}
export const KST_E_STAGE: StageParams = {
  use_example: true,
  normal_module_mm: 1.0,
  teeth_pinion: 51,
  teeth_wheel: 52,
  profile_shift_pinion: 0.2034,
  profile_shift_wheel: 0.3143,
  normal_pressure_angle_deg: 20,
  helix_angle_deg: 0,
  face_width_pinion_mm: 17,
  face_width_wheel_mm: 15,
  center_distance_mm: 52,
  tool_addendum_factor: 1.25,
  tool_tip_radius_factor: 0.38,
};
export interface PresetInfo {
  id: string;
  name: string;
  description: string;
  params: StageParams;
}
export interface PresetsResponse {
  presets: PresetInfo[];
  tools: Record<string, { addendum_factor: number; tip_radius_factor: number; label: string }>;
}
export const designApi = {
  presets: () => get<PresetsResponse>("/api/presets"),
  importSte: (content: string) =>
    post<{ params: StageParams; notes: string[] }>("/api/import/ste", { content }),
};

// ---- Mesh (FE sector, ADR-019 transplant mesher) ----
export interface FilletSpec {
  kind: "standard" | "trochoid" | "elliptic" | "bezier" | "bionic";
  e_f?: number;
  be?: number;
  gamma_deg?: number | null;
  b_f?: number;
}
export interface MeshRequest {
  stage: StageParams;
  gear: 1 | 2;
  refine_root: number;
  refine_flank: number;
  fillet: FilletSpec;
}
export interface MeshPreviewResponse {
  gear: number;
  n_nodes: number;
  n_quads: number;
  nodes_xy: number[];
  quads: number[];
  quality: number[];
  min_scaled_jacobian: number;
  cells_below_035: number;
  kind_surface: number[];
}
export interface Mesh3DResponse {
  gear: number;
  n_nodes_3d: number;
  n_hexes: number;
  min_scaled_jacobian: number;
  cells_below_035: number;
  face_width_mm: number;
  vertices: number[];
  faces: number[];
  face_quality: number[];
}
export interface ConvergenceResponse {
  target: string;
  levels: number[];
  sigma_mpa: number[];
  relative_change: number[];
  converged_level: number | null;
  reference_sigma_mpa: number;
}
export interface FilletCompareResponse {
  gear: number;
  names: string[];
  sigma_mpa: number[];
  delta_percent: number[];
  clearance_mm: number[];
}
export interface FilletSweepResponse {
  gear: number;
  kind: string;
  parameter: string;
  values: number[];
  sigma_mpa: number[];
  clearance_mm: number[];
  feasible: boolean[];
  best_value: number | null;
  best_sigma_mpa: number | null;
  standard_sigma_mpa: number;
}
// Gear numbering follows the stage input order (ADR-021): gear 1 = pinion, gear 2 = wheel.
// wheel_torque_nmm is the resisting torque at the WHEEL (the deck applies T1 = T2·z1/z2 at
// the pinion); the axial offsets displace each gear along its rotation axis from the default
// mid-plane alignment (both gears extrude symmetric about z = 0).
export interface DeckRequest {
  stage: StageParams;
  wheel_torque_nmm: number;
  face_layers: number;
  n_roll_positions: number;
  refine_root: number;
  refine_flank: number;
  pinion_material?: "steel" | "plastic";
  wheel_material?: "steel" | "plastic";
  axial_offset_pinion_mm?: number;
  axial_offset_wheel_mm?: number;
  steel_shell: boolean;
  fillet_pinion?: FilletSpec;
  fillet_wheel: FilletSpec;
}
export interface ContourRequest {
  stage: StageParams;
  gear: 1 | 2;
  fillet?: FilletSpec;
  points?: number;
}
export interface ContourResponse {
  gear: number;
  teeth: number;
  pitch_deg: number;
  root_diameter_mm: number;
  root_form_diameter_mm: number;
  usable_tip_diameter_mm: number;
  tip_diameter_mm: number | null;
  boundary_xy: number[];
  fillet_kind: string;
  clearance_mm: number | null;
}

async function postText(path: string, body: unknown): Promise<string> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
  return res.text();
}

export const meshApi = {
  preview: (req: MeshRequest) => post<MeshPreviewResponse>("/api/mesh/preview", req),
  mesh3d: (req: MeshRequest, layers: number) =>
    post<Mesh3DResponse>(`/api/mesh/3d?layers=${layers}`, req),
  convergence: (stage: StageParams, gear: 1 | 2, target: "root" | "flank") =>
    post<ConvergenceResponse>("/api/mesh/convergence", { stage, gear, target, levels: [1, 2, 3] }),
  filletCompare: (stage: StageParams, gear: 1 | 2) =>
    post<FilletCompareResponse>("/api/mesh/fillet-compare", { stage, gear }),
  filletSweep: (stage: StageParams, gear: 1 | 2, kind: "elliptic" | "bezier" | "bionic") =>
    post<FilletSweepResponse>("/api/mesh/fillet-sweep", { stage, gear, kind, points: 6 }),
  deck: (req: DeckRequest) => postText("/api/mesh/deck", req),
};
export const contourApi = {
  contour: (req: ContourRequest) => post<ContourResponse>("/api/mesh/contour", req),
};

// ---- Tolerances (ISO 1328-1) + free evaluate ----
export interface ToleranceRequest {
  accuracy_grade: number;
  normal_module_mm: number;
  teeth: number;
  reference_diameter_mm: number;
  face_width_mm: number;
  helix_angle_deg: number;
}
export interface FlankTolerances {
  accuracy_grade: number;
  single_pitch: number;
  total_pitch: number;
  profile_slope: number;
  profile_form: number;
  profile_total: number;
  helix_slope: number;
  helix_form: number;
  helix_total: number;
}
export interface ToleranceResponse {
  tolerances: FlankTolerances;
  base_pitch_deviation_um: number;
  profile_form_deviation_um: number;
  warnings: string[];
}
export const toleranceApi = {
  tolerances: (req: ToleranceRequest) => post<ToleranceResponse>("/api/tolerances", req),
};
