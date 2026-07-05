"use client";

// Tragfähigkeits-ERGEBNISSE (ISO 6336 / VDI 2736). The request derives ENTIRELY from THE
// workbench store — geometry (stage), load case (Leistungsfluss: T₁/n₁/P/N_L all grey-
// derived), operating conditions (Tragfähigkeit/VDI-2736/Schmierstoff tabs), tolerances
// (DIN 3962 grade) and the material selection (norm dispatch per gear). No panel-local
// input copies (single source of truth) — the inputs live in their FVA tabs.

import { useEffect, useMemo, useState } from "react";
import { api, type CapacityRequest, type CapacityResponse, type GearCapacity } from "@/lib/api";
import { AttrRow, Btn, ErrNote, Section, Stat } from "@/components/ui";
import { useWorkbench } from "@/lib/store";
import { useT } from "@/lib/i18n";

type Wb = ReturnType<typeof useWorkbench>;

function buildRequest(wb: Wb): CapacityRequest {
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
    face_load_factor: op.face_load_factor,
    accuracy_grade: op.accuracy_grade,
    base_pitch_deviation_um: op.base_pitch_deviation_um,
    profile_form_deviation_um: op.profile_form_deviation_um,
    lubricant_viscosity_40_mm2s: op.lubricant_viscosity_40_mm2s,
    flank_roughness_rz_um: op.flank_roughness_rz_um,
    root_roughness_rz_um: op.root_roughness_rz_um,
    flank_life_factor: op.flank_life_factor,
    root_life_factor: op.root_life_factor,
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

export function CapacityPanel() {
  const t = useT();
  const wb = useWorkbench();
  const [res, setRes] = useState<CapacityResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const req = useMemo(() => buildRequest(wb), [wb]);
  const reqKey = useMemo(() => JSON.stringify(req), [req]);

  const run = async () => {
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.capacity(req));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    // recompute whenever ANY input tab changes something relevant (SSOT: stage, load
    // case, operating conditions, materials — all flow through the one request)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reqKey]);

  return (
    <div className="grid grid-cols-[360px_1fr] gap-3 items-start">
      <div className="flex flex-col gap-3">
        <Section title="Lastfall (aus Leistungsfluss)">
          <table className="attr-table">
            <tbody>
              <AttrRow label="Ritzelmoment" symbol="T₁" unit="N·m">
                <td className="wb-num text-zinc-500">{req.pinion_torque_nm.toFixed(4)}</td>
              </AttrRow>
              <AttrRow label="Drehzahl" symbol="n₁" unit="min⁻¹">
                <td className="wb-num text-zinc-500">{req.pinion_speed_min1.toFixed(1)}</td>
              </AttrRow>
              <AttrRow label="Leistung" symbol="P" unit="W">
                <td className="wb-num text-zinc-500">{req.power_w?.toFixed(1)}</td>
              </AttrRow>
              <AttrRow label="Lastspiele (Rad)" symbol="N_L" unit="–">
                <td className="wb-num text-zinc-500">{req.load_cycles.toExponential(3)}</td>
              </AttrRow>
              <AttrRow label="Umgebungstemperatur" symbol="ϑ_0" unit="°C">
                <td className="wb-num text-zinc-500">{req.ambient_temperature_c?.toFixed(1)}</td>
              </AttrRow>
            </tbody>
          </table>
          <div className="px-3 py-1.5 text-[11.5px] text-zinc-500 border-t border-zinc-100">
            Alle Eingaben liegen in ihren FVA-Reitern (Leistungsfluss, Tragfähigkeit,
            VDI 2736, Werkstoff, Schmierstoff, Toleranzen) — hier nur der wirksame Lastfall.
          </div>
        </Section>
        <Btn onClick={() => void run()} busy={busy}>
          {t("common.run")}
        </Btn>
        {err && <ErrNote>{err}</ErrNote>}
      </div>

      {res && (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-3 gap-2">
            <Stat label="K_v" value={res.factors.dynamic_factor.toFixed(3)} />
            <Stat label="K_Hα" value={res.factors.transverse_factor.toFixed(3)} />
            <Stat label="K_Hβ" value={res.factors.face_load_factor.toFixed(3)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <GearCard title={t("common.pinion")} g={res.pinion} minRoot={req.root_minimum_safety} minFlank={req.flank_minimum_safety} />
            <GearCard title={t("common.wheel")} g={res.wheel} minRoot={req.root_minimum_safety} minFlank={req.flank_minimum_safety} />
          </div>
        </div>
      )}
    </div>
  );
}

function GearCard(props: { title: string; g: GearCapacity; minRoot: number; minFlank: number }) {
  const { g } = props;
  const tone = (v: number | null, min: number) =>
    v == null ? undefined : v >= min ? ("good" as const) : ("bad" as const);
  return (
    <Section title={`${props.title} — ${g.material} (${g.method})`}>
      <table className="attr-table">
        <tbody>
          <AttrRow label="Zahnfußspannung" symbol="σ_F" unit="N/mm²">
            <td className="wb-num">{g.root_stress_mpa.toFixed(1)}</td>
          </AttrRow>
          <AttrRow label="Fußsicherheit" symbol="S_F" unit="–">
            <td className={`wb-num ${tone(g.root_safety, props.minRoot) === "bad" ? "text-red-600" : "text-emerald-600"}`}>
              {g.root_safety?.toFixed(2) ?? "–"}
            </td>
          </AttrRow>
          <AttrRow label="Flankenpressung" symbol="σ_H" unit="N/mm²">
            <td className="wb-num">{g.flank_stress_mpa.toFixed(1)}</td>
          </AttrRow>
          <AttrRow label="Flankensicherheit" symbol="S_H" unit="–">
            <td className={`wb-num ${tone(g.flank_safety, props.minFlank) === "bad" ? "text-red-600" : "text-emerald-600"}`}>
              {g.flank_safety?.toFixed(2) ?? "–"}
            </td>
          </AttrRow>
          {g.peak_stress_mpa != null && (
            <AttrRow label="Statische Spitzenlast" symbol="σ_F,P" unit="N/mm²">
              <td className="wb-num">{g.peak_stress_mpa.toFixed(1)}</td>
            </AttrRow>
          )}
          {g.peak_safety != null && (
            <AttrRow label="Statische Sicherheit" symbol="S_stat" unit="–">
              <td className="wb-num">{g.peak_safety.toFixed(2)}</td>
            </AttrRow>
          )}
          {g.tooth_temperature_c != null && (
            <AttrRow label="Zahntemperatur" symbol="ϑ_Z" unit="°C">
              <td className="wb-num">{g.tooth_temperature_c.toFixed(1)}</td>
            </AttrRow>
          )}
          {g.wear_um != null && (
            <AttrRow label="Verschleiß" symbol="W_m" unit="µm">
              <td className="wb-num">{g.wear_um.toFixed(1)}</td>
            </AttrRow>
          )}
        </tbody>
      </table>
    </Section>
  );
}
