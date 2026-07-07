"use client";

// THE workbench store (single source of truth, user decision 2026-07-04): one context
// holds the shared stage, the Berechnungsauswahl method selection (drives tab visibility),
// the FEM/Dyn-Abwälzen options, operating data and the small UI-mode fields the dependency
// rules act on. Schema-rendered tabs read/write values by their backend-declared binding
// path ("stage.normal_module_mm", "calc.fva_892_transient_fem", "fem.fasten_bore", …), so
// backend schema and frontend state can never drift apart silently.

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import {
  KST_E_STAGE,
  type FilletSpec,
  type StageParams,
  type VariationPoint,
  type VariationRequest,
  type VariationResponse,
} from "@/lib/api";

export interface FemState {
  contour_source_gear1: string;
  contour_source_gear2: string;
  mods_source_gear1: string;
  mods_source_gear2: string;
  roll_position_mode: string;
  roll_pitches: number;
  n_roll_positions: number;
  run_solver: boolean;
  meshing_accuracy: string;
  modeled_teeth: number;
  free_segments: number;
  angle_limit_deg: number;
  jacobi_quality: number;
  fasten_bore: boolean;
  fasten_cuts: boolean;
  fasten_top: boolean;
  fasten_bottom: boolean;
  align_contact: boolean;
  deck_mode: "series" | "single"; // Positions-Serie (default) vs. quasi-static single deck
  result_in_model: boolean;
  auto_smoothing: boolean;
  expert_stirak: boolean;
  odb_path: string | null; // set after a solver run (roadmap steps 4/5)
  result_path: string | null;
  face_layers: number;
  // FVA mesh-fineness factors PER GEAR (root = Zahnfuß, flank = Zahnhöhe, thickness =
  // Zahndicke; Zahnbreite = face_layers, shared) — the plain fields are gear 1
  refine_root: number;
  refine_flank: number;
  refine_thickness: number;
  refine_root_gear2: number;
  refine_flank_gear2: number;
  refine_thickness_gear2: number;
  axial_offset_gear1_mm: number;
  axial_offset_gear2_mm: number;
  // root-fillet strategy per gear (drives preview mesh AND deck identically)
  fillet_gear1: FilletSpec;
  fillet_gear2: FilletSpec;
  steel_shell: boolean;
  // ideally stiff Außenhülle per gear (R3D4 lateral surface, open axial end faces);
  // the contact slave (plastic side) must stay deformable
  rigid_shell_gear1: boolean;
  rigid_shell_gear2: boolean;
}

// Werkstoffwahl per input slot (ADR-021) — THE dispatch source: steel → ISO 6336,
// plastic → VDI 2736, deck material card, rigid-shell/slave roles all derive from it.
export interface MaterialsState {
  gear1_kind: "steel" | "plastic";
  gear2_kind: "steel" | "plastic";
  gear1_name: string;
  gear2_name: string;
  steel_modulus_mpa: number;
  steel_poisson: number;
  steel_sigma_hlim_mpa: number;
  steel_sigma_flim_mpa: number;
  steel_density_kg_dm3: number;
  plastic_modulus_mpa: number;
  plastic_poisson: number;
  plastic_sigma_hlim_mpa: number;
  plastic_sigma_flim_mpa: number;
  plastic_density_kg_dm3: number;
  plastic_yield_strength_mpa: number;
  plastic_allowable_temperature_c: number;
}

// Operating conditions of the capacity methods (ISO 6336 + VDI 2736) — shared by the
// Tragfähigkeit panel and the VDI-2736/Schmierstoff schema tabs (never duplicated).
// Torque/speed/power/load cycles DERIVE from the Leistungsfluss + Betriebsdauer.
export interface OperatingState {
  application_factor: number; // K_A
  compute_dynamics: boolean;
  dynamic_factor: number; // K_v override
  face_load_factor: number; // K_Hβ
  accuracy_grade: number | null; // ISO 1328 / DIN 3962 grade (from the Toleranzen tab)
  base_pitch_deviation_um: number;
  profile_form_deviation_um: number;
  lubricant_viscosity_40_mm2s: number; // ν_40
  lubricant_viscosity_100_mm2s: number; // ν_100 (display; Schmierstoff tab)
  lubricant_density_15c_kg_dm3: number; // ρ bei 15 °C (display)
  flank_roughness_rz_um: number; // R_zH
  root_roughness_rz_um: number; // R_zF
  flank_roughness_ra_um: number; // R_aH (display, FVA row)
  root_roughness_ra_um: number; // R_aF (display)
  tip_relief_ca_um: number; // C_a Kopfrücknahme (Tragfähigkeit tab)
  flank_life_factor: number; // Z_NT
  root_life_factor: number; // Y_NT
  duty_cycle: number; // ED
  housing_surface_m2: number; // A_G
  housing_type: string; // Bauart des Getriebegehäuses
  lubrication_kind: string; // Schmierungsart (VDI 2736)
  friction_coefficient: number; // μ
  friction_mode: string; // nach VDI 2736:2014 / Nutzereingabe
  heat_transfer_mode: string; // k_ϑ nach VDI 2736 Tabelle 3
  tooth_loss_mode: string; // H_v nach Wimmer
  wear_coefficient_e6: number; // k_W ×1e-6 mm³/(N·m)
  allowable_wear_mode: string; // W_zul = 0.1·m_n
  root_minimum_safety: number; // S_Fmin
  flank_minimum_safety: number; // S_Hmin
  static_overload_factor: number | null; // K_A,stat
  static_minimum_safety: number; // S_Smin
  static_mode: string; // "Keine statische Berechnung" | Nutzereingabe
  ambient_mode: string; // ϑ_0 entspricht Öltemperatur
  deformation_condition: string; // Umgebungsbedingung (Verformung): Trocken
  // Tragfähigkeit tab (FVA rows)
  web_mode_gear1: string; // Bezogene Stegbreite b_s/b
  web_mode_gear2: string;
  rim_mode_gear1: string; // Relative Kranzdicke s_R/m_n
  rim_mode_gear2: string;
  roughness_auto: boolean;
  mesh_stiffness_mode: string; // c_γ nach ISO 6336
}

// Lastverteilung (FEM, FVA 377) tab options — solver pending, meshing/Fesselung functional
export interface LoaddistState {
  position_mode: string;
  n_positions: number;
  stress_eval: string;
  save_influence: boolean;
  auto_overroll: boolean;
  meshing_accuracy: string;
}

// Flankenmodifikation [34] (pinion; FVA editor tabs Allgemein/Flankenlinie/Stirnprofil/
// Weitere Formen/Matrix). The subset our micro-geometry model carries (ISO 21771 §6)
// merges into the effective stage: C_Hβ→helix_slope, C_β→helix_crowning, C_βI/II→
// end_relief, C_Hα→(slope, carried), C_α→profile_crowning, C_αa→tip_relief,
// C_αf→root_relief. Forms/lengths are carried for parity (mechanics pending).
export interface CorrectionState {
  length_mode: string; // Längenangaben der Modifikationen
  width_mode: string; // Breitenangaben
  flank_mode: string; // beide Flanken gleich
  non_additive: boolean;
  scope_mode: string; // Ganzes Eingriffsfeld
  // Flankenlinie
  helix_slope_on: boolean; // Winkelmodifikation C_Hβ
  helix_slope_form: string;
  helix_slope_um: number;
  helix_crown_on: boolean; // Balligkeit C_β
  helix_crown_form: string;
  helix_crown_um: number;
  end_relief_left_on: boolean; // Endrücknahme links C_βI
  end_relief_left_form: string;
  end_relief_left_um: number;
  end_relief_left_len_mm: number;
  end_relief_right_on: boolean; // C_βII
  end_relief_right_form: string;
  end_relief_right_um: number;
  end_relief_right_len_mm: number;
  // Stirnprofil
  profile_slope_on: boolean; // C_Hα
  profile_slope_um: number;
  profile_crown_on: boolean; // C_α
  profile_crown_form: string;
  profile_crown_um: number;
  tip_relief_on: boolean; // C_αa
  tip_relief_form: string;
  tip_relief_um: number;
  tip_relief_dca_mm: number; // Beginn der Kopfrücknahme (Durchmesser)
  root_relief_on: boolean; // C_αf
  root_relief_form: string;
  root_relief_um: number;
  // Weitere Formen (carried)
  tri_tip_on: boolean;
  tri_tip_um: number;
  tri_root_on: boolean;
  tri_root_um: number;
  twist_on: boolean; // Verschränkung S_α
  twist_um: number;
  waviness_on: boolean; // periodische Flankenwelligkeit
  waviness_um: number;
  waviness_length_mm: number;
}

const CORRECTION_DEFAULTS: CorrectionState = {
  length_mode: "diameter_mm",
  width_mode: "mm",
  flank_mode: "both_equal",
  non_additive: false,
  scope_mode: "full_field",
  helix_slope_on: false,
  helix_slope_form: "start_width",
  helix_slope_um: 0,
  helix_crown_on: false,
  helix_crown_form: "symmetric_arc",
  helix_crown_um: 0,
  end_relief_left_on: false,
  end_relief_left_form: "linear",
  end_relief_left_um: 0,
  end_relief_left_len_mm: 0,
  end_relief_right_on: false,
  end_relief_right_form: "linear",
  end_relief_right_um: 0,
  end_relief_right_len_mm: 0,
  profile_slope_on: false,
  profile_slope_um: 0,
  profile_crown_on: false,
  profile_crown_form: "symmetric_arc",
  profile_crown_um: 0,
  tip_relief_on: true, // kst-E: Kopfrücknahme C_a = 8 µm aktiv (Tragfähigkeit sheet)
  tip_relief_form: "linear",
  tip_relief_um: 8.0,
  tip_relief_dca_mm: 51.946,
  root_relief_on: false,
  root_relief_form: "linear",
  root_relief_um: 0,
  tri_tip_on: false,
  tri_tip_um: 0,
  tri_root_on: false,
  tri_root_um: 0,
  twist_on: false,
  twist_um: 0,
  waviness_on: false,
  waviness_um: 0,
  waviness_length_mm: 0,
};

// Radkörper Stirnrad [40] (wheel body of the plastic wheel)
export interface WheelBodyState {
  design_mode: string; // ohne Radkörper (Referenz) | elast. aus CAD
  angular_position_deg: number; // Winkellagenmodifikation
  cad_name: string;
  cut_diameter_mode: string;
  cut_diameter_mm: number;
  stiffness_mode: string; // Anbindesteifigkeit
}

const WHEEL_BODY_DEFAULTS: WheelBodyState = {
  design_mode: "none_reference",
  angular_position_deg: 0.0,
  cad_name: "kst-E_cut_dyn-Ab.stp",
  cut_diameter_mode: "user",
  cut_diameter_mm: 48.0,
  stiffness_mode: "ideal_stiff",
};

// Stufenvariation flow state — PERSISTED in the store (user decision: go back to the
// filter/result steps without recomputing; results survive tab switches).
export interface VariationFilter {
  min: number | null;
  max: number | null;
}
export interface VariationUiState {
  step: 1 | 2 | 3 | 4;
  res: VariationResponse | null;
  req: VariationRequest | null; // the exact sweep settings of `res` (report reuse)
  rows: VariationPoint[]; // sorted working set of the result steps
  compare: number[];
  filters: Record<string, VariationFilter>;
  fillet_kind: "standard" | "trochoid" | "elliptic" | "bezier" | "bionic"; // Fußform
}

const VARIATION_UI_DEFAULTS: VariationUiState = {
  step: 1,
  res: null,
  req: null,
  rows: [],
  compare: [],
  filters: {},
  fillet_kind: "standard",
};

// reference-parity defaults (measured deck: bore + cut planes, 30 roll positions, 2 pitches)
const FEM_DEFAULTS: FemState = {
  contour_source_gear1: "generated",
  contour_source_gear2: "generated",
  mods_source_gear1: "given",
  mods_source_gear2: "given",
  roll_position_mode: "linear_count",
  roll_pitches: 2,
  n_roll_positions: 30,
  run_solver: false,
  meshing_accuracy: "converged_root",
  modeled_teeth: 4,
  free_segments: 1,
  angle_limit_deg: 65.0,
  jacobi_quality: 0.35,
  fasten_bore: true,
  fasten_cuts: true,
  fasten_top: false,
  fasten_bottom: false,
  align_contact: true,
  deck_mode: "series",
  result_in_model: false,
  auto_smoothing: true,
  expert_stirak: false,
  odb_path: null,
  result_path: null,
  face_layers: 6,
  refine_root: 1,
  refine_flank: 1,
  refine_thickness: 1,
  refine_root_gear2: 1,
  refine_flank_gear2: 1,
  refine_thickness_gear2: 1,
  axial_offset_gear1_mm: 0,
  axial_offset_gear2_mm: 0,
  fillet_gear1: { kind: "standard" },
  fillet_gear2: { kind: "standard" },
  steel_shell: false,
  rigid_shell_gear1: false,
  rigid_shell_gear2: false,
};

// kst-E defaults (materials catalog names; property values = the FVA Werkstoff sheet)
const MATERIALS_DEFAULTS: MaterialsState = {
  gear1_kind: "steel",
  gear2_kind: "plastic",
  gear1_name: "20MnCr5",
  gear2_name: "Stanyl_TW200F6_cond_80",
  steel_modulus_mpa: 210000,
  steel_poisson: 0.3,
  steel_sigma_hlim_mpa: 1500,
  steel_sigma_flim_mpa: 430,
  steel_density_kg_dm3: 7.85,
  plastic_modulus_mpa: 4156,
  plastic_poisson: 0.34,
  plastic_sigma_hlim_mpa: 60,
  plastic_sigma_flim_mpa: 35,
  plastic_density_kg_dm3: 1.41,
  plastic_yield_strength_mpa: 65,
  plastic_allowable_temperature_c: 100,
};

// kst-E operating defaults (FVA screenshots: Tragfähigkeit/VDI 2736/Schmierstoff tabs)
const OPERATING_DEFAULTS: OperatingState = {
  application_factor: 1.0,
  compute_dynamics: true,
  dynamic_factor: 1.0,
  face_load_factor: 1.0,
  accuracy_grade: 7, // DIN 3962 Qualität 7 (Toleranzen screenshot)
  base_pitch_deviation_um: 6.0,
  profile_form_deviation_um: 5.0,
  lubricant_viscosity_40_mm2s: 100.0,
  lubricant_viscosity_100_mm2s: 11.0,
  lubricant_density_15c_kg_dm3: 0.88,
  flank_roughness_rz_um: 5.0,
  root_roughness_rz_um: 20.0,
  flank_roughness_ra_um: 0.8,
  root_roughness_ra_um: 3.3,
  tip_relief_ca_um: 8.0,
  flank_life_factor: 1.0,
  root_life_factor: 1.0,
  duty_cycle: 1.0,
  housing_surface_m2: 0.01,
  housing_type: "closed",
  lubrication_kind: "oil_circulation",
  friction_coefficient: 0.04,
  friction_mode: "vdi_2736_2014",
  heat_transfer_mode: "vdi_2736_table3",
  tooth_loss_mode: "wimmer",
  wear_coefficient_e6: 1.0,
  allowable_wear_mode: "0.1_mn",
  root_minimum_safety: 2.0,
  flank_minimum_safety: 1.4,
  static_overload_factor: null, // FVA default: "Keine statische Berechnung"
  static_minimum_safety: 1.5,
  static_mode: "none",
  ambient_mode: "equals_oil",
  deformation_condition: "dry",
  web_mode_gear1: "solid",
  web_mode_gear2: "solid",
  rim_mode_gear1: "solid",
  rim_mode_gear2: "solid",
  roughness_auto: true,
  mesh_stiffness_mode: "iso6336",
};

const LOADDIST_DEFAULTS: LoaddistState = {
  position_mode: "linear_count",
  n_positions: 7,
  stress_eval: "tangential",
  save_influence: false,
  auto_overroll: false,
  meshing_accuracy: "medium",
};

export interface GeometryUiState {
  center_distance_mode: "a_and_x" | "from_x";
  profile_shift_mode: string;
  profile_generation_gear1: string;
  profile_generation_gear2: string;
}

export interface OperatingUiState {
  lubricant: string;
  ambient_temperature_c: number;
  operating_hours: number;
  oil_temperature_c: number;
  gravity_enabled: boolean;
  gravity_u: number;
  gravity_v: number;
  gravity_w: number;
  gravity_m_s2: number;
  centrifugal_enabled: boolean;
}

// Leistungsfluss (Getriebeeinheit): THE load-case source — the transient-FEM deck torque
// derives from the one torque input here (SSOT chain: Leistungsfluss → Dyn. Abwälzen).
// The torque may be entered on EITHER shaft (user decision): torque_shaft says which
// field holds the raw input; the other side is derived via z₁/z₂ and rendered locked.
// torque_nm === null means both fields are empty/editable (cleared state). The store
// always computes from the ENTERED value — never from a rounded derived display value —
// so the kst-E parity chain stays exact: Welle 2 input M₂ = 8.0 N·m → deck AMP level
// 8000·51/52 = 7846.2 N·mm.
export interface PowerflowState {
  n_configurations: number;
  active_configuration: string;
  load1_switchable: boolean;
  load2_switchable: boolean;
  speed_shaft1_min1: number;
  direction_shaft1: "cw" | "ccw";
  load1_type: "antrieb" | "abtrieb";
  load2_type: "antrieb" | "abtrieb";
  torque_nm: number | null; // raw torque input at torque_shaft (null = both empty)
  torque_shaft: 1 | 2; // which shaft the input belongs to (kst-E: 2)
  u_load1_mm: number;
  u_load2_mm: number;
}

/** Canonical torque at gear 2 (M₂, the deck/reference quantity) from the one input. */
function torqueM2(s: WorkbenchState): number | undefined {
  const t = s.powerflow.torque_nm;
  if (t == null || !Number.isFinite(t)) return undefined;
  return s.powerflow.torque_shaft === 2
    ? t
    : (t * s.stage.teeth_wheel) / s.stage.teeth_pinion;
}

/** Torque at gear 1 (pinion). Raw input when entered on shaft 1 (no float round-trip);
 * otherwise M₂ scaled by z₁/z₂ (loss-free balance). */
function torqueT1(s: WorkbenchState): number | undefined {
  const t = s.powerflow.torque_nm;
  if (t == null || !Number.isFinite(t)) return undefined;
  return s.powerflow.torque_shaft === 1
    ? t
    : (t * s.stage.teeth_pinion) / s.stage.teeth_wheel;
}

// Kräfte und Momente (per load; FVA defaults 0.0 — carried, no system solver yet)
export type ForcesState = Record<string, number>;

// Steuerparameter (FVA Gesamtsystem control values; carried for parity — rows that only
// steer the FVA solver are marked inactive in the schema info texts)
export interface ControlState {
  log_io: boolean;
  nominal_torques: boolean;
  load_dependent_center_distance: boolean;
  backlash_mode: string;
  linear_solver: string;
  convergence_tolerance: string;
  max_iterations: number;
  bearing_method: string;
  width_load_points: number;
  width_correction_proposal: boolean;
  loads_as_point_forces: boolean;
  idler_tiltable: boolean;
  deviation_multiplier: number;
  n_mesh_positions: string;
  n_fourier: number;
  transmission_error_norm_um: number;
  pre_post_engagement: boolean;
  dynamic_stiffness: boolean;
  flank_mod_criterion: string;
  min_contact_line_pct: number;
}

export interface ShaftUiState {
  u_coordinate_gear1_mm: number;
  u_coordinate_gear2_mm: number;
  rotation_negative_u_deg: number;
}

// Model instances: the [n] numbers on the tree nodes are per-instance IDs the model
// assigns on insertion (FVA behaviour) — data, never hardcoded label strings. The default
// model mirrors the kst-E example project (IDs as in the reference screenshots); a model
// editor can renumber/extend this later.
export interface ModelInstance {
  id: number;
  type: string;
  name_de: string;
  name_en: string;
}
export type ModelInstances = Record<string, ModelInstance>;
const MODEL_DEFAULTS: ModelInstances = {
  gear_unit: { id: 1, type: "gear_unit", name_de: "Getriebeeinheit", name_en: "Gear unit" },
  housing: { id: 2, type: "housing", name_de: "Gehäuse", name_en: "Housing" },
  stage: { id: 3, type: "cylindrical_mesh", name_de: "Stirnradstufe", name_en: "Cylindrical gear stage" },
  shaft1: { id: 4, type: "shaft", name_de: "Welle", name_en: "Shaft" },
  shaft2: { id: 6, type: "shaft", name_de: "Welle", name_en: "Shaft" },
  pinion: { id: 8, type: "cylindrical_gear", name_de: "Stahlritzel", name_en: "Steel pinion" },
  wheel: { id: 9, type: "cylindrical_gear", name_de: "Kunststoffrad", name_en: "Plastic wheel" },
  load1: { id: 16, type: "force", name_de: "Belastung", name_en: "Load" },
  load2: { id: 17, type: "force", name_de: "Belastung", name_en: "Load" },
  correction: { id: 34, type: "gear_correction", name_de: "Flankenmodifikation", name_en: "Flank modification" },
  wheel_body: { id: 40, type: "wheel_body_cylindrical_gear", name_de: "Radkörper Stirnrad", name_en: "Wheel body" },
};

/** "Getriebeeinheit [1]" — instance label in the FVA notation, from data. */
export function instanceLabel(inst: ModelInstance, locale: string): string {
  return `${locale === "de" ? inst.name_de : inst.name_en} [${inst.id}]`;
}

// Toleranzen tab (DIN 3967 Zahnweitenabmaße + Achsabstandsabmaße + DIN 3962 Qualität).
// Writing A_We/A_Wi ALSO updates the stage's mean tooth-width allowance (drives x_E and
// the deck backlash — the closing rotation) via the write-through rule in set().
export interface TolerancesState {
  awe1_um: number; // oberes Zahnweitenabmaß A_We Rad 1
  awi1_um: number; // unteres A_Wi Rad 1
  awe2_um: number;
  awi2_um: number;
  aw_factor_mode: string; // Zahnweitenabmaßfaktor (0.94)
  aw_selection: string; // "Mit mittlerem Zahnweitenabmaß"
  a_upper_um: number; // oberes Achsabstandsabmaß A_Ae
  a_lower_um: number; // unteres A_Ai
  quality_standard: string; // DIN 3962 (1978)
  grade1: number;
  grade2: number;
  custom_diameter1: boolean; // Anzeige benutzerdefinierter Durchmesser im Zahnplot
  custom_diameter2: boolean;
}

const TOLERANCES_DEFAULTS: TolerancesState = {
  awe1_um: -278.0,
  awi1_um: -278.0,
  awe2_um: -207.0,
  awi2_um: -207.0,
  aw_factor_mode: "0.94",
  aw_selection: "mean",
  a_upper_um: 15.0,
  a_lower_um: -15.0,
  quality_standard: "din_3962_1978",
  grade1: 7,
  grade2: 7,
  custom_diameter1: false,
  custom_diameter2: false,
};

interface WorkbenchState {
  stage: StageParams;
  calc: Record<string, boolean>; // Berechnungsauswahl (method id → selected)
  fem: FemState;
  geometryUi: GeometryUiState;
  operatingUi: OperatingUiState;
  operating: OperatingState;
  materials: MaterialsState;
  tol: TolerancesState;
  loaddist: LoaddistState;
  correction: CorrectionState;
  wheelBody: WheelBodyState;
  varUi: VariationUiState;
  powerflow: PowerflowState;
  forces: ForcesState;
  control: ControlState;
  shaft: ShaftUiState;
  model: ModelInstances; // tree instances with their [n] IDs (data, not hardcoded)
  label: string;
}

// Derived (computed) paths — the norm-active couplings the schema rows read as grey
// values. Each one is documented in the glossary via its uimodel dependency rule.
const DERIVED: Record<string, (s: WorkbenchState) => unknown> = {
  // kinematic chain n₂ = −n₁·z₁/z₂ (external mesh reverses the direction)
  "powerflow.speed_shaft2_min1": (s) =>
    -(s.powerflow.speed_shaft1_min1 * s.stage.teeth_pinion) / s.stage.teeth_wheel,
  // torque balance (user decision): ONE torque, entered on shaft 1 OR shaft 2 — the
  // entered side echoes the raw value, the other side shows the z₁/z₂-converted value
  // and locks; clearing the entered field resets both (torque_nm = null)
  "powerflow.torque_shaft1_nm": (s) => torqueT1(s),
  "powerflow.torque_shaft2_nm": (s) => torqueM2(s),
  "powerflow.torque_shaft1_locked": (s) =>
    s.powerflow.torque_nm != null && s.powerflow.torque_shaft !== 1,
  "powerflow.torque_shaft2_locked": (s) =>
    s.powerflow.torque_nm != null && s.powerflow.torque_shaft !== 2,
  "powerflow.power_load1_kw": (s) => {
    const t1 = torqueT1(s);
    if (t1 == null) return undefined;
    return Math.abs(((2 * Math.PI * s.powerflow.speed_shaft1_min1) / 60) * t1) / 1000;
  },
  "powerflow.power_load2_kw": (s) => {
    const m2 = torqueM2(s);
    if (m2 == null) return undefined;
    return (
      Math.abs(
        ((2 * Math.PI * (s.powerflow.speed_shaft1_min1 * s.stage.teeth_pinion)) /
          s.stage.teeth_wheel /
          60) *
          m2,
      ) / 1000
    );
  },
  // SSOT chain: the transient-FEM deck torque M₂ [N·mm] IS the Leistungsfluss torque
  // (FVA behaviour — the Abwälz tab has no own torque input)
  "fem.torque_gear2_nmm": (s) => {
    const m2 = torqueM2(s);
    return m2 == null ? undefined : m2 * 1000;
  },
  // deck material cards + norm dispatch follow the Werkstoff selection (per slot)
  "fem.gear1_material": (s) => s.materials.gear1_kind,
  "fem.gear2_material": (s) => s.materials.gear2_kind,
  // the deck's roll/torque signs follow the Leistungsfluss Drehrichtung (user point 7b)
  "fem.rotation_sense": (s) => s.powerflow.direction_shaft1,
  // capacity load case = the Leistungsfluss (T₁ at the pinion, n₁ at shaft [4])
  "operating.pinion_torque_nm": (s) => torqueT1(s),
  "operating.pinion_speed_min1": (s) => s.powerflow.speed_shaft1_min1,
  // N_L = 60·|n₂|·L_H (load cycles of the wheel over the Betriebsdauer)
  "operating.load_cycles": (s) =>
    60.0 *
    Math.abs((s.powerflow.speed_shaft1_min1 * s.stage.teeth_pinion) / s.stage.teeth_wheel) *
    s.operatingUi.operating_hours,
  // VDI 2736 power = the transmitted power from the Leistungsfluss [W]
  "operating.power_w": (s) => {
    const t1 = torqueT1(s);
    if (t1 == null) return undefined;
    return Math.abs(((2 * Math.PI * s.powerflow.speed_shaft1_min1) / 60) * t1);
  },
  // VDI 2736 ambient ϑ₀ "entspricht Öltemperatur" (FVA default mode)
  "operating.ambient_temperature_c": (s) =>
    s.operating.ambient_mode === "equals_oil" ? s.operatingUi.oil_temperature_c : 20.0,
  // dropdown-dependent row visibility (µ value only when "Nutzereingabe" is selected)
  "operating.friction_is_user": (s) => s.operating.friction_mode === "value",
  // Radkörper: the FEM tie-in section exists only for the CAD variant
  "wheelBody.design_is_cad": (s) => s.wheelBody.design_mode === "elastic_cad",
};

/** The EFFECTIVE stage every API call receives: the raw stage merged with the values
 * other tabs own — the Toleranzen tab's mean tooth-width allowance A_We (drives x_E and
 * the deck backlash / contact-closing rotation) and the Flankenmodifikation amounts that
 * map onto the ISO 21771 §6 micro-geometry model. One stage, no divergent copies. */
function effectiveStage(s: WorkbenchState): StageParams {
  const c = s.correction;
  const flank = {
    tip_relief_um: c.tip_relief_on ? c.tip_relief_um : 0,
    // d_Ca "Beginn der Kopfrücknahme" — null lets the backend default to d_Na − m_n
    tip_relief_start_diameter_mm:
      c.tip_relief_on && c.tip_relief_dca_mm > 0 ? c.tip_relief_dca_mm : null,
    root_relief_um: c.root_relief_on ? c.root_relief_um : 0,
    profile_crowning_um: c.profile_crown_on ? c.profile_crown_um : 0,
    helix_crowning_um: c.helix_crown_on ? c.helix_crown_um : 0,
    end_relief_um: c.end_relief_left_on || c.end_relief_right_on
      ? Math.max(c.end_relief_left_um, c.end_relief_right_um)
      : 0,
    helix_slope_um: c.helix_slope_on ? c.helix_slope_um : 0,
  };
  return {
    ...s.stage,
    // Achsabstand-Modus (DIN 21771): "aus den Profilverschiebungen berechnen" sends
    // a = null so the backend derives it from inv α_wt(Σx) — the a field locks/greys
    center_distance_mm:
      s.geometryUi.center_distance_mode === "from_x" ? null : s.stage.center_distance_mm,
    tooth_width_allowance_pinion_mm: (s.tol.awe1_um + s.tol.awi1_um) / 2 / 1000,
    tooth_width_allowance_wheel_mm: (s.tol.awe2_um + s.tol.awi2_um) / 2 / 1000,
    // Flankenmodifikation [34] sits at the pinion (kst-E tree); "beide Flanken gleich"
    modifications_pinion: { left: flank, right: flank },
  };
}

interface WorkbenchStore extends WorkbenchState {
  setStage: (s: StageParams) => void;
  setLabel: (l: string) => void;
  setCalc: (id: string, on: boolean) => void;
  setFem: (patch: Partial<FemState>) => void;
  // generic binding access for schema-rendered rows (path = "<namespace>.<field>")
  get: (path: string) => unknown;
  set: (path: string, value: unknown) => void;
}

const DEFAULT_STATE: WorkbenchState = {
  stage: KST_E_STAGE,
  calc: {
    iso_6336_2019: true,
    vdi_2736_2014: true,
    fva_892_transient_fem: true,
  },
  fem: FEM_DEFAULTS,
  geometryUi: {
    center_distance_mode: "a_and_x",
    profile_shift_mode: "nominal",
    profile_generation_gear1: "by_tool",
    profile_generation_gear2: "by_tool",
  },
  operatingUi: {
    lubricant: "iso_vg_100",
    ambient_temperature_c: 20.0,
    operating_hours: 100000.0,
    oil_temperature_c: 80.0,
    gravity_enabled: true,
    gravity_u: 0.0,
    gravity_v: 1.0,
    gravity_w: 0.0,
    gravity_m_s2: 9.81,
    centrifugal_enabled: true,
  },
  operating: OPERATING_DEFAULTS,
  materials: MATERIALS_DEFAULTS,
  tol: TOLERANCES_DEFAULTS,
  loaddist: LOADDIST_DEFAULTS,
  correction: CORRECTION_DEFAULTS,
  wheelBody: WHEEL_BODY_DEFAULTS,
  varUi: VARIATION_UI_DEFAULTS,
  powerflow: {
    n_configurations: 1,
    active_configuration: "1",
    load1_switchable: true,
    load2_switchable: true,
    speed_shaft1_min1: 2250.0,
    direction_shaft1: "cw",
    load1_type: "abtrieb",
    load2_type: "antrieb",
    torque_nm: 8.0,
    torque_shaft: 2,
    u_load1_mm: 0.0,
    u_load2_mm: 0.0,
  },
  forces: {},
  control: {
    log_io: false,
    nominal_torques: false,
    load_dependent_center_distance: false,
    backlash_mode: "ignore",
    linear_solver: "native",
    convergence_tolerance: "default",
    max_iterations: 50,
    bearing_method: "fva_909",
    width_load_points: 18,
    width_correction_proposal: true,
    loads_as_point_forces: false,
    idler_tiltable: false,
    deviation_multiplier: 1.0,
    n_mesh_positions: "24",
    n_fourier: 4,
    transmission_error_norm_um: 10.0,
    pre_post_engagement: false,
    dynamic_stiffness: false,
    flank_mod_criterion: "linear_pressure",
    min_contact_line_pct: 0.0,
  },
  shaft: { u_coordinate_gear1_mm: 23.5, u_coordinate_gear2_mm: 24.5, rotation_negative_u_deg: 0 },
  model: MODEL_DEFAULTS,
  label: "kst-E",
};

const WbCtx = createContext<WorkbenchStore | null>(null);

export function WorkbenchProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<WorkbenchState>(DEFAULT_STATE);

  const store = useMemo<WorkbenchStore>(() => {
    const namespaces = [
      "stage",
      "calc",
      "fem",
      "geometryUi",
      "operatingUi",
      "operating",
      "materials",
      "tol",
      "loaddist",
      "correction",
      "wheelBody",
      "varUi",
      "powerflow",
      "forces",
      "control",
      "shaft",
    ] as const;
    const get = (path: string): unknown => {
      const derived = DERIVED[path];
      if (derived) return derived(state);
      const [ns, field] = splitPath(path);
      if (!namespaces.includes(ns as (typeof namespaces)[number])) return undefined;
      return (state[ns as keyof WorkbenchState] as Record<string, unknown>)[field];
    };
    const set = (path: string, value: unknown) => {
      const [ns, field] = splitPath(path);
      setState((prev) => {
        const bucket = prev[ns as keyof WorkbenchState] as Record<string, unknown>;
        // powerflow couplings (one setState patch — no nested set() calls):
        if (ns === "powerflow") {
          // Antrieb/Abtrieb are mutually exclusive — flipping one flips the other
          if (field === "load1_type" || field === "load2_type") {
            const other = field === "load1_type" ? "load2_type" : "load1_type";
            const inverse = value === "antrieb" ? "abtrieb" : "antrieb";
            return {
              ...prev,
              powerflow: { ...prev.powerflow, [field]: value, [other]: inverse },
            };
          }
          // ONE torque, entered on either shaft: writing a virtual shaft field stores
          // the raw value + which shaft it belongs to; an emptied field OR the value 0
          // resets both (user report 2026-07-06: 0 must free the other side again)
          if (field === "torque_shaft1_nm" || field === "torque_shaft2_nm") {
            const shaft = field === "torque_shaft1_nm" ? 1 : 2;
            const num =
              typeof value === "number" && Number.isFinite(value) && value !== 0 ? value : null;
            return {
              ...prev,
              powerflow: {
                ...prev.powerflow,
                torque_nm: num,
                torque_shaft: num == null ? prev.powerflow.torque_shaft : (shaft as 1 | 2),
              },
            };
          }
        }
        const next = { ...bucket, [field]: value };
        // editing a stage value leaves the kst-E example mode (free parameters from then on)
        if (ns === "stage" && field !== "use_example") next.use_example = false;
        return { ...prev, [ns]: next };
      });
    };
    return {
      ...state,
      // every consumer sees the EFFECTIVE stage (raw stage + tab-owned merges like the
      // Toleranzen allowances) — API calls therefore always carry the coupled values
      stage: effectiveStage(state),
      setStage: (s) => setState((p) => ({ ...p, stage: s })),
      setLabel: (l) => setState((p) => ({ ...p, label: l })),
      setCalc: (id, on) => setState((p) => ({ ...p, calc: { ...p.calc, [id]: on } })),
      setFem: (patch) => setState((p) => ({ ...p, fem: { ...p.fem, ...patch } })),
      get,
      set,
    };
  }, [state]);

  return <WbCtx.Provider value={store}>{children}</WbCtx.Provider>;
}

function splitPath(path: string): [string, string] {
  const i = path.indexOf(".");
  return i < 0 ? [path, ""] : [path.slice(0, i), path.slice(i + 1)];
}

export function useWorkbench(): WorkbenchStore {
  const ctx = useContext(WbCtx);
  if (!ctx) throw new Error("useWorkbench outside WorkbenchProvider");
  return ctx;
}
