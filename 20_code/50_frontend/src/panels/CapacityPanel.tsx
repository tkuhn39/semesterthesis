"use client";

// Load-capacity editor (port into the workbench + the previously dropped fields:
// ISO 1328 accuracy grade drives f_pb/f_fα, and the VDI 2736 static peak-load check).

import { useEffect, useState } from "react";
import { api, type CapacityRequest, type CapacityResponse, type GearCapacity } from "@/lib/api";
import { AttrRow, Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { useStage } from "@/lib/stage";
import { useT } from "@/lib/i18n";

// Operating conditions only — the GEOMETRY always comes from THE shared stage
// (single source of truth); this panel never carries its own copy of it.
const DEFAULTS: CapacityRequest = {
  pinion_torque_nm: 7.85,
  pinion_speed_min1: 1000,
  application_factor: 1.0,
  compute_dynamics: true,
  dynamic_factor: 1.0,
  face_load_factor: 1.0,
  base_pitch_deviation_um: 6.0,
  profile_form_deviation_um: 5.0,
  lubricant_viscosity_40_mm2s: 100,
  flank_roughness_rz_um: 5.0,
  root_roughness_rz_um: 20.0,
  flank_life_factor: 1.0,
  root_life_factor: 1.0,
  steel_modulus_mpa: 210000,
  steel_poisson: 0.3,
  steel_sigma_hlim_mpa: 1500,
  steel_sigma_flim_mpa: 430,
  power_w: 1848.7,
  ambient_temperature_c: 80,
  duty_cycle: 1.0,
  housing_surface_m2: 0.01,
  friction_coefficient: 0.04,
  wear_coefficient_e6: 1.0,
  load_cycles: 1.324e7,
  root_minimum_safety: 2.0,
  flank_minimum_safety: 1.4,
  plastic_modulus_mpa: 4156,
  plastic_poisson: 0.34,
  plastic_sigma_hlim_mpa: 60,
  plastic_sigma_flim_mpa: 35,
  accuracy_grade: 8,
  static_overload_factor: 2.0,
  static_minimum_safety: 1.5,
  plastic_yield_strength_mpa: 65,
};

export function CapacityPanel() {
  const t = useT();
  const { stage } = useStage();
  const [req, setReq] = useState<CapacityRequest>(DEFAULTS);
  const [res, setRes] = useState<CapacityResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async (r: CapacityRequest) => {
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.capacity({ ...r, stage }));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    // recompute when the shared stage changes (a geometry edit in any tab lands here too)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void run(req);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage]);

  const set = (k: keyof CapacityRequest) => (v: number) => setReq({ ...req, [k]: v });

  return (
    <div className="grid grid-cols-[380px_1fr] gap-3 items-start">
      <div className="flex flex-col gap-3">
        <Section title={t("cap.operating")}>
          <table className="attr-table">
            <tbody>
              <AttrRow label="Ritzelmoment" symbol="T₁" unit="N·m">
                <td><Num value={req.pinion_torque_nm} onChange={set("pinion_torque_nm")} /></td>
              </AttrRow>
              <AttrRow label="Drehzahl" symbol="n₁" unit="min⁻¹">
                <td><Num value={req.pinion_speed_min1} onChange={set("pinion_speed_min1")} /></td>
              </AttrRow>
              <AttrRow label="Anwendungsfaktor" symbol="K_A" unit="–">
                <td><Num value={req.application_factor} onChange={set("application_factor")} /></td>
              </AttrRow>
              <AttrRow label="Lastspiele" symbol="N_L" unit="–">
                <td><Num value={req.load_cycles} onChange={set("load_cycles")} /></td>
              </AttrRow>
              <AttrRow label="Umgebungstemperatur" symbol="ϑ_U" unit="°C">
                <td><Num value={req.ambient_temperature_c} onChange={set("ambient_temperature_c")} /></td>
              </AttrRow>
            </tbody>
          </table>
        </Section>
        <Section title={t("cap.quality")} defaultOpen={false}>
          <table className="attr-table">
            <tbody>
              <AttrRow label="ISO-1328-Qualität (setzt f_pb/f_fα)" symbol="Q" unit="–">
                <td>
                  <Num
                    value={req.accuracy_grade ?? 8}
                    onChange={(v) => setReq({ ...req, accuracy_grade: Math.round(v) })}
                    step={1}
                  />
                </td>
              </AttrRow>
              <AttrRow label="Eingriffsteilungsabweichung" symbol="f_pb" unit="µm">
                <td><Num value={req.base_pitch_deviation_um} onChange={set("base_pitch_deviation_um")} /></td>
              </AttrRow>
              <AttrRow label="Profil-Formabweichung" symbol="f_fα" unit="µm">
                <td><Num value={req.profile_form_deviation_um} onChange={set("profile_form_deviation_um")} /></td>
              </AttrRow>
            </tbody>
          </table>
        </Section>
        <Section title={t("cap.static")} defaultOpen={false}>
          <table className="attr-table">
            <tbody>
              <AttrRow label="Statischer Überlastfaktor" symbol="K_A,stat" unit="–">
                <td>
                  <Num
                    value={req.static_overload_factor ?? 0}
                    onChange={(v) => setReq({ ...req, static_overload_factor: v || null })}
                  />
                </td>
              </AttrRow>
              <AttrRow label="Streckgrenze Kunststoff" symbol="σ_S" unit="N/mm²">
                <td>
                  <Num
                    value={req.plastic_yield_strength_mpa ?? 0}
                    onChange={(v) => setReq({ ...req, plastic_yield_strength_mpa: v || null })}
                  />
                </td>
              </AttrRow>
              <AttrRow label="Mindestsicherheit statisch" symbol="S_Smin" unit="–">
                <td>
                  <Num
                    value={req.static_minimum_safety ?? 1.5}
                    onChange={(v) => setReq({ ...req, static_minimum_safety: v })}
                  />
                </td>
              </AttrRow>
            </tbody>
          </table>
        </Section>
        <Section title={t("cap.materials")} defaultOpen={false}>
          <table className="attr-table">
            <tbody>
              <AttrRow label="Kunststoff" symbol="σ_Flim" unit="N/mm²">
                <td><Num value={req.plastic_sigma_flim_mpa} onChange={set("plastic_sigma_flim_mpa")} /></td>
              </AttrRow>
              <AttrRow label="Kunststoff" symbol="σ_Hlim" unit="N/mm²">
                <td><Num value={req.plastic_sigma_hlim_mpa} onChange={set("plastic_sigma_hlim_mpa")} /></td>
              </AttrRow>
              <AttrRow label="Stahl" symbol="σ_Flim" unit="N/mm²">
                <td><Num value={req.steel_sigma_flim_mpa} onChange={set("steel_sigma_flim_mpa")} /></td>
              </AttrRow>
            </tbody>
          </table>
        </Section>
        <Btn onClick={() => void run(req)} busy={busy}>
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
