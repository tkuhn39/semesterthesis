// THE deck payload (single source of truth, phase F): every consumer — the Dyn-Abwälzen
// tab action, the pair-view assembly preview and the deck/series download — builds its
// request through this ONE function, so identical settings yield byte-identical decks.
// Torque M₂ and Drehrichtung come from the Leistungsfluss, the materials from the
// Werkstoff tab (both via derived store paths); everything else lives in fem.*.

import type { DeckRequest, StageParams } from "@/lib/api";
import type { FemState, MaterialsState } from "@/lib/store";

export interface DeckSource {
  stage: StageParams;
  fem: FemState;
  materials: MaterialsState;
  get: (path: string) => unknown;
}

export function deckPayload(wb: DeckSource): Omit<DeckRequest, "torque_gear2_nmm"> {
  return {
    stage: wb.stage,
    face_layers: wb.fem.face_layers,
    n_roll_positions: wb.fem.n_roll_positions,
    roll_pitches: wb.fem.roll_pitches,
    start_at_edge: true,
    rotation_sense: wb.get("fem.rotation_sense") as "cw" | "ccw",
    refine_root: wb.fem.refine_root,
    refine_flank: wb.fem.refine_flank,
    refine_thickness: wb.fem.refine_thickness,
    refine_root_gear2: wb.fem.refine_root_gear2,
    refine_flank_gear2: wb.fem.refine_flank_gear2,
    refine_thickness_gear2: wb.fem.refine_thickness_gear2,
    gear1_material: wb.get("fem.gear1_material") as "steel" | "plastic",
    gear2_material: wb.get("fem.gear2_material") as "steel" | "plastic",
    // deck material cards follow the EDITED Werkstoff-tab values (audit F4 — FE and
    // analytics must never compute with different materials)
    steel_modulus_mpa: wb.materials.steel_modulus_mpa,
    steel_poisson: wb.materials.steel_poisson,
    steel_density_kg_dm3: wb.materials.steel_density_kg_dm3,
    plastic_poisson: wb.materials.plastic_poisson,
    plastic_density_kg_dm3: wb.materials.plastic_density_kg_dm3,
    axial_offset_gear1_mm: wb.fem.axial_offset_gear1_mm,
    axial_offset_gear2_mm: wb.fem.axial_offset_gear2_mm,
    steel_shell: wb.fem.steel_shell,
    rigid_shell_gear1: wb.fem.rigid_shell_gear1,
    rigid_shell_gear2: wb.fem.rigid_shell_gear2,
    fillet_gear1: wb.fem.fillet_gear1,
    fillet_gear2: wb.fem.fillet_gear2,
    align_contact: wb.fem.align_contact,
    fasten_bore: wb.fem.fasten_bore,
    fasten_cuts: wb.fem.fasten_cuts,
    fasten_top: wb.fem.fasten_top,
    fasten_bottom: wb.fem.fasten_bottom,
  };
}
