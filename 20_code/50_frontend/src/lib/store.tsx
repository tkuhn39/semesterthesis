"use client";

// THE workbench store (single source of truth, user decision 2026-07-04): one context
// holds the shared stage, the Berechnungsauswahl method selection (drives tab visibility),
// the FEM/Dyn-Abwälzen options, operating data and the small UI-mode fields the dependency
// rules act on. Schema-rendered tabs read/write values by their backend-declared binding
// path ("stage.normal_module_mm", "calc.fva_892_transient_fem", "fem.fasten_bore", …), so
// backend schema and frontend state can never drift apart silently.

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { KST_E_STAGE, type StageParams } from "@/lib/api";

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
  result_in_model: boolean;
  auto_smoothing: boolean;
  expert_stirak: boolean;
  odb_path: string | null; // set after a solver run (roadmap steps 4/5)
  result_path: string | null;
  face_layers: number;
  refine_root: number;
  refine_flank: number;
  gear1_material: "steel" | "plastic";
  gear2_material: "steel" | "plastic";
  steel_shell: boolean;
}

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
  result_in_model: false,
  auto_smoothing: true,
  expert_stirak: false,
  odb_path: null,
  result_path: null,
  face_layers: 6,
  refine_root: 1,
  refine_flank: 1,
  gear1_material: "steel",
  gear2_material: "plastic",
  steel_shell: false,
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
// derives from the Antrieb load here (SSOT chain: Leistungsfluss → Dyn. Abwälzen).
// kst-E reference: Welle [4] 2250 min⁻¹ (Abtrieb), Welle [6] Antrieb with M₂ = 8.0 N·m
// (the deck converts to the torque gear: 8000·51/52 = 7846.2 N·mm — reference AMP level).
export interface PowerflowState {
  n_configurations: number;
  active_configuration: string;
  load1_switchable: boolean;
  load2_switchable: boolean;
  speed_shaft1_min1: number;
  direction_shaft1: "cw" | "ccw";
  load1_type: "antrieb" | "abtrieb";
  load2_type: "antrieb" | "abtrieb";
  torque_antrieb_nm: number; // T_sc of the Antrieb load (M₂ for load 2 = kst-E)
  u_load1_mm: number;
  u_load2_mm: number;
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

interface WorkbenchState {
  stage: StageParams;
  calc: Record<string, boolean>; // Berechnungsauswahl (method id → selected)
  fem: FemState;
  geometryUi: GeometryUiState;
  operatingUi: OperatingUiState;
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
  // torque balance: the Abtrieb load carries T·z-ratio of the Antrieb torque (loss-free)
  "powerflow.torque_abtrieb_nm": (s) =>
    (s.powerflow.torque_antrieb_nm * s.stage.teeth_pinion) / s.stage.teeth_wheel,
  "powerflow.power_load1_kw": (s) =>
    Math.abs(
      ((2 * Math.PI * s.powerflow.speed_shaft1_min1) / 60) *
        ((s.powerflow.torque_antrieb_nm * s.stage.teeth_pinion) / s.stage.teeth_wheel),
    ) / 1000,
  "powerflow.power_load2_kw": (s) =>
    Math.abs(
      ((2 * Math.PI * (s.powerflow.speed_shaft1_min1 * s.stage.teeth_pinion)) /
        s.stage.teeth_wheel /
        60) *
        s.powerflow.torque_antrieb_nm,
    ) / 1000,
  // SSOT chain: the transient-FEM deck torque M₂ [N·mm] IS the Leistungsfluss Antrieb
  // torque (FVA behaviour — the Abwälz tab has no own torque input)
  "fem.torque_gear2_nmm": (s) => s.powerflow.torque_antrieb_nm * 1000,
};

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
  powerflow: {
    n_configurations: 1,
    active_configuration: "1",
    load1_switchable: true,
    load2_switchable: true,
    speed_shaft1_min1: 2250.0,
    direction_shaft1: "cw",
    load1_type: "abtrieb",
    load2_type: "antrieb",
    torque_antrieb_nm: 8.0,
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
        const next = { ...bucket, [field]: value };
        // editing a stage value leaves the kst-E example mode (free parameters from then on)
        if (ns === "stage" && field !== "use_example") next.use_example = false;
        return { ...prev, [ns]: next };
      });
    };
    return {
      ...state,
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
