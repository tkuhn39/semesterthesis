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

// /api/geometry consumes THE shared StageParams (single source of truth) — no
// separate request type with its own copies of the gear parameters anymore.
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
  nominal_flank_stress_mpa?: number | null; // σ_H0 (ISO branch)
  nominal_root_stress_mpa?: number | null; // σ_F0
  // ISO 6336-2/-3 strength sub-factors (σ_HP/σ_FP chains, explicit)
  lubricant_factor?: number | null; // Z_L
  velocity_factor?: number | null; // Z_v
  roughness_factor?: number | null; // Z_R
  work_hardening_factor?: number | null; // Z_W
  size_factor_flank?: number | null; // Z_X
  life_factor_flank?: number | null; // Z_NT
  notch_sensitivity_factor?: number | null; // Y_δrelT
  surface_factor?: number | null; // Y_RrelT
  size_factor_root?: number | null; // Y_X
  life_factor_root?: number | null; // Y_NT
  root_chord_mn?: number | null; // s_Fn* (30°-tangent)
  fillet_radius_mn?: number | null; // ρ_F*
  notch_parameter?: number | null; // q_s
  bending_lever_mn?: number | null; // h_Fe*
  load_angle_deg?: number | null; // α_Fen
  flank_temperature_c?: number | null; // ϑ_Fla (VDI branch)
  loss_factor?: number | null; // H_V
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
  transverse_factor_root: number;
  face_load_factor: number;
  face_load_factor_root: number;
  elasticity_factor: number;
  zone_factor: number;
  contact_ratio_factor: number;
  single_contact_b: number;
  single_contact_d: number;
  tangential_force_n: number;
  pitch_velocity_ms: number;
  line_load_n_mm: number;
  virtual_teeth: number[];
}
export interface CapacityResponse {
  factors: CapacityFactors;
  pinion: GearCapacity;
  wheel: GearCapacity;
}
// ISO 6336-3 material group (ρ′, Y_RrelT, Y_X curves) per gear — audit NRM-07
export type RootMaterialGroup =
  | "case_hardened"
  | "through_hardened"
  | "normalized"
  | "nitrided"
  | "cast_iron";

export interface CapacityRequest {
  // THE shared stage (single source of truth) + per-slot material kind — the norm
  // dispatch follows the MATERIAL (steel → ISO 6336, plastic → VDI 2736), never the role.
  stage?: StageParams;
  pinion_material?: "steel" | "plastic";
  wheel_material?: "steel" | "plastic";
  pinion_torque_nm: number;
  pinion_speed_min1: number;
  application_factor: number;
  compute_dynamics: boolean;
  dynamic_factor: number;
  face_load_factor: number | null; // null = native ISO 6336-1 Method C K_Hβ/K_Fβ
  base_pitch_deviation_um: number;
  profile_form_deviation_um: number;
  helix_slope_deviation_um?: number | null; // f_Hβ — used when no accuracy grade (V-02)
  mesh_misalignment_um?: number | null; // F_βx override; null → native estimate
  lubricant_viscosity_40_mm2s: number;
  flank_roughness_rz_um: number;
  root_roughness_rz_um: number;
  flank_life_factor: number;
  root_life_factor: number;
  pinion_material_group?: RootMaterialGroup; // ISO 6336-3 group (NRM-07)
  wheel_material_group?: RootMaterialGroup;
  softer_gear_hardness_hb?: number | null; // HB of the softer mating gear (Z_W)
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
  stage?: StageParams; // THE shared stage
  pinion_material?: "steel" | "plastic";
  wheel_material?: "steel" | "plastic";
  pinion_speed_min1: number;
  pinion_torque_nm: number;
  application_factor: number;
  // same accuracy + material inputs as /api/capacity (GAP-01: the tabs must agree)
  accuracy_grade?: number | null;
  base_pitch_deviation_um: number;
  profile_form_deviation_um: number;
  helix_slope_deviation_um?: number | null;
  mesh_misalignment_um?: number | null;
  steel_modulus_mpa?: number;
  steel_poisson?: number;
  steel_sigma_hlim_mpa?: number;
  steel_sigma_flim_mpa?: number;
  plastic_modulus_mpa?: number;
  plastic_poisson?: number;
  plastic_sigma_hlim_mpa?: number;
  plastic_sigma_flim_mpa?: number;
  plastic_yield_strength_mpa?: number | null;
}
export interface DynamicsResponse {
  dynamic_factor: number;
  transverse_factor_flank: number;
  transverse_factor_root: number;
  face_load_factor_flank: number;
  face_load_factor_root: number;
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
  // FVA Stufenvariation row set (screenshots Stufenvariation_Ansicht-1*.png)
  m_n: VarSpec;
  alpha_n: VarSpec; // Normaleingriffswinkel Rad 1 (sweepable)
  z1: VarSpec;
  z2: VarSpec;
  x1: VarSpec;
  x2: VarSpec;
  beta_deg: VarSpec;
  b: VarSpec; // Zahnbreite Rad 1
  // per-gear reference-profile rows — real sweep parameters (v0.7)
  b2: VarSpec; // Zahnbreite Rad 2
  h_ap1: VarSpec; // Kopfhöhenfaktor (Bezugsprofil)
  h_ap2: VarSpec;
  h_fp1: VarSpec; // Fußhöhenfaktor (Bezugsprofil)
  h_fp2: VarSpec;
  rho_fp1: VarSpec; // Fußausrundungsfaktor (Bezugsprofil)
  rho_fp2: VarSpec;
  q1_mm: number; // Bearbeitungszugabe (not in the kernel — carried, warns)
  q2_mm: number;
  pr_p1_mm: number; // Protuberanzbetrag
  pr_p2_mm: number;
  alpha_pr_p1_deg: number; // Protuberanzwinkel
  alpha_pr_p2_deg: number;
  allow_tip_shortening: boolean; // Automatische Kopfkürzung zulassen
  full_root_round: boolean; // Vollausrundung
  dedendum_with_clearance: boolean; // Fußhöhen mit Kopfspiel berechnen
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
  b2: number;
  h_ap1: number;
  h_ap2: number;
  h_fp1: number;
  h_fp2: number;
  rho_fp1: number;
  rho_fp2: number;
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

// /api/tooth-profile consumes THE shared StageParams and returns the real as-cut flanks.
export interface ToothGear {
  teeth: number;
  center_x_mm: number;
  reference_radius_mm: number;
  base_radius_mm: number;
  tip_radius_mm: number;
  root_radius_mm: number;
  half_flank: [number, number][];
}
// line of action in the tooth-profile frame (gear 1 at origin, gear 2 at (a, 0));
// verified against the FVA Gesamtsystemreport reference plot (kst-E)
export interface LineOfAction {
  t1: [number, number];
  t2: [number, number];
  a: [number, number];
  b: [number, number];
  c: [number, number];
  d: [number, number];
  e: [number, number];
  working_pressure_angle_deg: number;
  path_of_contact_mm: number;
  transverse_base_pitch_mm: number;
  working_pitch_radius_mm: [number, number];
  base_radius_mm: [number, number];
}
export interface ToothProfileResponse {
  center_distance_mm: number;
  pinion: ToothGear;
  wheel: ToothGear;
  line_of_action: LineOfAction | null;
}

export const api = {
  health: () => get<{ status: string; version: string }>("/api/health"),
  example: () => get<ExampleResponse>("/api/example/kst-e"),
  geometry: (stage: StageParams) => post<GeometryResponse>("/api/geometry", stage),
  geometryReport: (req: GeometryReportRequest) =>
    post<GeometryReportResponse>("/api/geometry/report", req),
  capacity: (req: CapacityRequest) => post<CapacityResponse>("/api/capacity", req),
  dynamics: (req: DynamicsRequest) => post<DynamicsResponse>("/api/dynamics", req),
  variation: (req: VariationRequest) => post<VariationResponse>("/api/variation", req),
  toothProfile: (stage: StageParams) => post<ToothProfileResponse>("/api/tooth-profile", stage),
};

// ---- Stage definition (design.py — kst-E example or free parameters, M6) ----
export interface FlankModification {
  tip_relief_um?: number;
  tip_relief_start_diameter_mm?: number | null; // d_Ca (null → backend default d_Na − m_n)
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
  // gear-1 tool (and gear-2 default); *_gear2 overrides the wheel tool when set
  // (kst-E: h_aP0* 1.1/1.25, Kantenbrechwinkel 45° only on the wheel tool)
  tool_addendum_factor: number;
  tool_tip_radius_factor: number;
  tool_dedendum_factor?: number | null;
  tool_root_form_height_factor?: number | null;
  tool_edge_break_angle_deg?: number | null;
  tool_addendum_factor_gear2?: number | null;
  tool_tip_radius_factor_gear2?: number | null;
  tool_dedendum_factor_gear2?: number | null;
  tool_root_form_height_factor_gear2?: number | null;
  tool_edge_break_angle_deg_gear2?: number | null;
  gear_addendum_factor?: number;
  tip_diameter_pinion_mm?: number | null;
  tip_diameter_wheel_mm?: number | null;
  // mean tooth-width allowance A_We (Toleranzen; drives x_E and the deck backlash)
  tooth_width_allowance_pinion_mm?: number;
  tooth_width_allowance_wheel_mm?: number;
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
  // per-gear tools from the kst-E .ste ground truth (WKZ_Profil_B_Ritzel / _Rad):
  // pinion h_aP0*=1.1 ρ*=0.2; wheel h_aP0*=1.25 ρ*=0.2 h_FfP0*=0.8456 + 45° edge break
  tool_addendum_factor: 1.1,
  tool_tip_radius_factor: 0.2,
  tool_dedendum_factor: 1.0,
  tool_addendum_factor_gear2: 1.25,
  tool_tip_radius_factor_gear2: 0.2,
  tool_dedendum_factor_gear2: 1.0,
  tool_root_form_height_factor_gear2: 0.8456,
  tool_edge_break_angle_deg_gear2: 45.0,
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

// ---- Full geometry report (backend SSOT: DIN ISO 21771 / DIN 21773 / 3967 / 3964) ----
export interface GearReport {
  teeth: number;
  profile_shift: number;
  generation_profile_shift: number;
  reference_diameter_mm: number;
  base_diameter_mm: number;
  tip_diameter_mm: number;
  tip_form_diameter_mm: number;
  tip_chamfer_radial_mm: number;
  usable_tip_diameter_mm: number;
  usable_root_diameter_mm: number | null;
  root_form_diameter_mm: number;
  root_diameter_mm: number;
  effective_root_diameter_mm: number | null;
  form_reserve_mm: number | null;
  working_pitch_diameter_mm: number;
  tooth_height_mm: number;
  addendum_mm: number;
  addendum_factor_actual: number;
  tip_clearance_mm: number | null;
  tip_path_of_contact_mm: number | null;
  tooth_thickness_transverse_mm: number;
  tooth_thickness_normal_mm: number;
  space_width_normal_mm: number;
  tip_tooth_thickness_mm: number | null;
  rest_tip_thickness_mm: number | null;
  chordal_thickness_mm: number;
  chordal_height_mm: number;
  span_teeth: number | null;
  span_teeth_min: number | null;
  span_teeth_max: number | null;
  span_measurement_mm: number | null;
  span_contact_diameter_mm: number | null;
  ball_diameter_mm: number | null;
  two_ball_measure_mm: number | null;
  two_roller_measure_mm: number | null;
  ball_contact_diameter_mm: number | null;
  thickness_allowance_upper_mm: number | null;
  thickness_allowance_lower_mm: number | null;
  span_allowance_upper_mm: number | null;
  span_allowance_lower_mm: number | null;
  ball_allowance_factor: number | null;
  ball_allowance_upper_mm: number | null;
  ball_allowance_lower_mm: number | null;
  sliding_factor_tip: number | null;
  specific_sliding_tip: number | null;
  specific_sliding_root: number | null;
  undercut_min_shift: number | null;
  has_undercut: boolean | null;
  tool_module_mm: number;
  tool_pressure_angle_deg: number;
  tool_addendum_factor: number;
  tool_tip_radius_factor: number;
  tool_dedendum_factor: number | null;
}
export interface PairReport {
  normal_module_mm: number;
  transverse_module_mm: number;
  normal_pressure_angle_deg: number;
  transverse_pressure_angle_deg: number;
  working_pressure_angle_deg: number;
  helix_angle_deg: number;
  base_helix_angle_deg: number;
  gear_ratio: number;
  center_distance_mm: number;
  reference_center_distance_mm: number;
  profile_shift_sum: number;
  transverse_pitch_mm: number;
  normal_pitch_mm: number;
  transverse_base_pitch_mm: number;
  normal_base_pitch_mm: number;
  path_of_contact_mm: number;
  transverse_contact_ratio: number;
  overlap_ratio: number;
  total_contact_ratio: number;
  common_face_width_mm: number | null;
  common_tooth_height_mm: number | null;
  common_height_factor: number | null;
  backlash_circumferential_mm: number | null;
  backlash_normal_mm: number | null;
  backlash_delta_upper_mm: [number, number] | null;
  backlash_delta_lower_mm: [number, number] | null;
  center_distance_allowance_mm: number | null;
}
export interface GeometryReportResponse {
  gear1: GearReport;
  gear2: GearReport;
  pair: PairReport;
  notes: string[];
}
export type Din3967AllowanceSeries =
  | "a"
  | "ab"
  | "b"
  | "bc"
  | "c"
  | "cd"
  | "d"
  | "e"
  | "f"
  | "g"
  | "h";
export interface GeometryReportRequest {
  stage: StageParams;
  fillet_gear1?: FilletSpec | null;
  fillet_gear2?: FilletSpec | null;
  ball_diameter_gear1_mm?: number | null;
  ball_diameter_gear2_mm?: number | null;
  center_distance_allowance_mm?: number | null;
  span_allowance_upper_um?: [number, number] | null;
  span_allowance_lower_um?: [number, number] | null;
  // DIN 3967 designation per gear (drawing "27cd" = tolerance 27 + allowance cd)
  allowance_series_gear1?: Din3967AllowanceSeries | null;
  allowance_series_gear2?: Din3967AllowanceSeries | null;
  tolerance_series_gear1?: number | null;
  tolerance_series_gear2?: number | null;
}

// ---- Mesh (FE sector, ADR-019 transplant mesher) ----
export type FilletApproach = "kassem" | "fruehe" | "landi" | "roth" | "dong" | "voith" | "cao";
export interface FilletSpec {
  kind: "standard" | "trochoid" | "elliptic" | "bezier" | "bionic";
  approach?: FilletApproach; // literature method within the kind; backend defaults per family
  e_f?: number;
  tilt_deg?: number; // fruehe: tilt γ of the ellipse major axis (study optimum 30°)
  aspect?: number; // fruehe: axis ratio a/b (study optimum 3.0)
  ra_f?: number; // landi: D1 offset above d_Ff in ·m_n (paper default: limit contact diam.)
  d2_frac?: number; // landi: D2 position on d_f as fraction of the angle to the gap centre
  be?: number;
  dv0?: number; // dong: P0 depth below the hob tip (·h_kW)
  dv1?: number; // dong: P4 along the tip land (1 = gap centreline)
  dv2?: number; // dong: tangent lengths at P0/P4 (·m_n)
  dv3?: number; // dong: P2 x-interpolation P0→P4
  dv4?: number; // dong: P2 y-interpolation P0→P4
  gamma_deg?: number | null;
  b_f?: number;
  cao_step?: number; // cao: growth scale (·0.025·m_n per iteration)
  cao_iterations?: number; // cao: FE↔growth budget
  cao_tol?: number; // cao: surface-stress uniformity target
  junction_offset_mm?: number; // interference fallback: nudge the d_Ff junction inward
}
/** Literature approaches per fillet family (order = backend default first). */
export const FILLET_APPROACHES: Record<string, FilletApproach[]> = {
  elliptic: ["kassem", "fruehe", "landi"],
  bezier: ["roth", "dong"],
  bionic: ["voith", "cao"],
};
/** Approaches accepted by the backend but not implemented yet (rendered disabled). */
export const FILLET_APPROACHES_PENDING: ReadonlySet<FilletApproach> = new Set();
export function defaultApproach(kind: FilletSpec["kind"]): FilletApproach | undefined {
  return FILLET_APPROACHES[kind]?.[0];
}
export interface MeshRequest {
  stage: StageParams;
  gear: 1 | 2;
  refine_root: number;
  refine_flank: number;
  refine_thickness?: number; // Elemente über Zahndicke (FVA mesh-fineness dialog)
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
  // effective per-tooth element counts (FVA dialog "effektive Werte")
  elements_root: number;
  elements_flank: number;
  elements_thickness: number;
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
  approach: string;
  parameter: string;
  values: number[];
  sigma_mpa: number[];
  clearance_mm: number[];
  feasible: boolean[];
  best_value: number | null;
  best_sigma_mpa: number | null;
  standard_sigma_mpa: number;
}
// Slot semantics (ADR-021, amended): gear 1 = the stage's FIRST gear (origin/left in the
// assembly — Kleingetriebeprüfstand top view), gear 2 = the second (centre distance/right);
// per-gear fields follow the input chain, never re-ordered by role or tooth count.
// torque_gear2_nmm is the resisting torque expressed at gear 2 (M₂); the axial offsets
// displace each gear along its rotation axis from the default mid-plane alignment (both
// gears extrude symmetric about z = 0).
export interface DeckRequest {
  stage: StageParams;
  torque_gear2_nmm: number;
  face_layers: number;
  n_roll_positions: number;
  // fineness factors: plain fields = both gears, *_gear2 overrides gear 2 (FVA dialog)
  refine_root: number;
  refine_flank: number;
  refine_thickness?: number;
  refine_root_gear2?: number | null;
  refine_flank_gear2?: number | null;
  refine_thickness_gear2?: number | null;
  gear1_material?: "steel" | "plastic";
  gear2_material?: "steel" | "plastic";
  axial_offset_gear1_mm?: number;
  axial_offset_gear2_mm?: number;
  steel_shell: boolean;
  fillet_gear1?: FilletSpec;
  fillet_gear2?: FilletSpec;
  // reference parity: rotate gear 2 into single-flank contact (torque closes the last µm)
  align_contact?: boolean;
  // FVA "Fesselung" checkboxes (Dynamisches Abwälzen (FEM)); defaults = reference
  fasten_bore?: boolean;
  fasten_cuts?: boolean;
  fasten_top?: boolean;
  fasten_bottom?: boolean;
  // ideally stiff Außenhülle per gear (R3D4 lateral surface, open end faces)
  rigid_shell_gear1?: boolean;
  rigid_shell_gear2?: boolean;
  // per-position torque cycle + roll setup (user decisions 2026-07-06)
  roll_pitches?: number;
  ramp_up?: number;
  hold?: number;
  ramp_down?: number;
  move?: number;
  settle?: number;
  base_torque_fraction?: number;
  start_at_edge?: boolean;
  rotation_sense?: "cw" | "ccw";
}
// THE deck assembly for the pair viewport (SSOT): vertices in absolute assembly
// coordinates at the closed, centered configuration; the viewer animates position k by
// rotating each gear about its own center by start_angle_rad + k · step_angle_rad.
export interface PairGearOut {
  gear: number;
  teeth: number;
  center: [number, number];
  z_mid_mm: number;
  face_width_mm: number;
  rigid_shell: boolean;
  n_elements: number;
  vertices: number[];
  faces: number[];
  start_angle_rad: number;
  step_angle_rad: number;
}
export interface PairAssemblyResponse {
  center_distance_mm: number;
  closing_rad: number;
  driven_gear: number;
  n_positions: number;
  roll_angle_rad: number;
  contact_pairs: string[];
  gear1: PairGearOut;
  gear2: PairGearOut;
}
export interface ContourRequest {
  stage: StageParams;
  gear: 1 | 2;
  fillet?: FilletSpec;
  points?: number;
}
export interface FilletCaoResponse {
  gear: number;
  iterations_run: number;
  converged: boolean;
  sigma_history_mpa: number[];
  uniformity_history: number[];
  boundary_xy: number[];
  effective_root_diameter_mm: number;
  clearance_mm: number;
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
  fillet_approach: string | null;
  effective_root_diameter_mm: number; // 2·min|boundary| — Frühe digs below d_f by design
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
  filletSweep: (
    stage: StageParams,
    gear: 1 | 2,
    kind: "elliptic" | "bezier" | "bionic",
    approach?: FilletApproach,
    parameter?: string,
  ) =>
    post<FilletSweepResponse>("/api/mesh/fillet-sweep", {
      stage,
      gear,
      kind,
      approach,
      parameter,
      points: 6,
    }),
  filletCao: (stage: StageParams, gear: 1 | 2, spec: FilletSpec) =>
    post<FilletCaoResponse>("/api/mesh/fillet-cao", {
      stage,
      gear,
      cao_step: spec.cao_step ?? 1.0,
      cao_iterations: spec.cao_iterations ?? 12,
      cao_tol: spec.cao_tol ?? 0.02,
    }),
  // preview assembly: same request shape as the deck, torque not needed (geometry only)
  pair: (req: Omit<DeckRequest, "torque_gear2_nmm">) =>
    post<PairAssemblyResponse>("/api/mesh/pair", req),
  deck: (req: DeckRequest) => postText("/api/mesh/deck", req),
  deckSeries: async (req: DeckRequest): Promise<Blob> => {
    const res = await fetch(`${BASE}/api/mesh/deck-series`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
    return res.blob();
  },
};
export const contourApi = {
  contour: (req: ContourRequest) => post<ContourResponse>("/api/mesh/contour", req),
};

// ---- FEM results (phase G): Abaqus dump upload → path-of-contact viewer data ----
// the per-node array fields of a flank frame that the viewer can plot (axis 3 / color)
export type FemField = "s_mises" | "s_maxp" | "s_minp" | "e_mises" | "e_maxp" | "cpress" | "u";
export interface FlankFrameData {
  xi: number[]; // path-of-contact coordinate relative to C [mm] (gear-signed)
  z: number[]; // axial coordinate over the face width [mm]
  s_mises: number[];
  s_maxp: number[];
  s_minp: number[];
  e_mises: number[];
  e_maxp: number[];
  cpress: number[];
  u: number[];
  max_mises: number;
  max_cpress: number;
  n_z: number; // grid hint: n_z · n_xi == nodes → structured surface
  n_xi: number;
}
export interface FemFrame {
  index: number;
  phi_driven_rad: number | null;
  flanks: Record<string, FlankFrameData>;
}
export interface LineOfActionMarkers {
  a: number;
  b: number;
  c: number;
  d: number;
  e: number;
  xi_min: number; // extended range d_Nf…d_Na (pre-/post-engagement)
  xi_max: number;
  transverse_base_pitch_mm: number;
}
export interface FemResultsResponse {
  mode: string;
  n_frames: number;
  flank_tags: string[];
  markers: LineOfActionMarkers;
  frames: FemFrame[];
}
export const femApi = {
  results: (stage: StageParams, results: unknown) =>
    post<FemResultsResponse>("/api/fem/results", { stage, results }),
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
