"use client";

// Tragfähigkeits-ERGEBNISSE (ISO 6336 / VDI 2736). The request derives ENTIRELY from THE
// workbench store — geometry (stage), load case (Leistungsfluss: T₁/n₁/P/N_L all grey-
// derived), operating conditions (Tragfähigkeit/VDI-2736/Schmierstoff tabs), tolerances
// (DIN 3962 grade) and the material selection (norm dispatch per gear). No panel-local
// input copies (single source of truth) — the inputs live in their FVA tabs.

import { useEffect, useMemo, useState } from "react";
import { api, type CapacityResponse, type GearCapacity } from "@/lib/api";
import { AttrRow, Btn, ErrNote, Section, Stat } from "@/components/ui";
import { buildCapacityRequest } from "@/lib/capacityRequest";
import { useWorkbench } from "@/lib/store";
import { useFmt, useT } from "@/lib/i18n";

export function CapacityPanel() {
  const t = useT();
  const fm = useFmt();
  const wb = useWorkbench();
  const [res, setRes] = useState<CapacityResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const req = useMemo(() => buildCapacityRequest(wb), [wb]);
  const reqKey = useMemo(() => JSON.stringify(req), [req]);

  const run = async () => {
    // powerflow torque cleared (reset state) — nothing to compute yet
    if (req.pinion_torque_nm == null || !Number.isFinite(req.pinion_torque_nm)) {
      setRes(null);
      setErr(t("pf.noTorque"));
      return;
    }
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
        <Section title={t("cap.loadcase")}>
          <table className="attr-table">
            <tbody>
              <AttrRow label={t("cap.pinionTorque")} symbol="T₁" unit="N·m">
                <td className="wb-num text-zinc-500">{fm.num(req.pinion_torque_nm, 4)}</td>
              </AttrRow>
              <AttrRow label={t("cap.speed")} symbol="n₁" unit="min⁻¹">
                <td className="wb-num text-zinc-500">{fm.num(req.pinion_speed_min1, 1)}</td>
              </AttrRow>
              <AttrRow label={t("cap.power")} symbol="P" unit="W">
                <td className="wb-num text-zinc-500">{fm.num(req.power_w, 1)}</td>
              </AttrRow>
              <AttrRow label={t("cap.cycles")} symbol="N_L" unit="–">
                <td className="wb-num text-zinc-500">{req.load_cycles.toExponential(3)}</td>
              </AttrRow>
              <AttrRow label={t("cap.ambient")} symbol="ϑ_0" unit="°C">
                <td className="wb-num text-zinc-500">{fm.num(req.ambient_temperature_c, 1)}</td>
              </AttrRow>
            </tbody>
          </table>
          <div className="px-3 py-1.5 text-[11.5px] text-zinc-500 border-t border-zinc-100">
            {t("cap.inputsNote")}
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
            <Stat label="K_v" value={fm.num(res.factors.dynamic_factor, 3)} />
            <Stat label="K_Hα" value={fm.num(res.factors.transverse_factor, 3)} />
            <Stat label="K_Hβ" value={fm.num(res.factors.face_load_factor, 3)} />
          </div>
          <Section title={t("cap.factorsTitle")} defaultOpen={false}>
            <table className="attr-table">
              <tbody>
                <AttrRow label={t("cap.kFa")} symbol="K_Fα" unit="–">
                  <td className="wb-num">{fm.num(res.factors.transverse_factor_root, 3)}</td>
                </AttrRow>
                <AttrRow label={t("cap.kFb")} symbol="K_Fβ" unit="–">
                  <td className="wb-num">{fm.num(res.factors.face_load_factor_root, 3)}</td>
                </AttrRow>
                <AttrRow label={t("cap.zE")} symbol="Z_E" unit="√(N/mm²)">
                  <td className="wb-num">{fm.num(res.factors.elasticity_factor, 2)}</td>
                </AttrRow>
                <AttrRow label={t("cap.zH")} symbol="Z_H" unit="–">
                  <td className="wb-num">{fm.num(res.factors.zone_factor, 3)}</td>
                </AttrRow>
                <AttrRow label={t("cap.zEps")} symbol="Z_ε" unit="–">
                  <td className="wb-num">{fm.num(res.factors.contact_ratio_factor, 3)}</td>
                </AttrRow>
                <AttrRow label={t("cap.zB")} symbol="Z_B / Z_D" unit="–">
                  <td className="wb-num">
                    {fm.num(res.factors.single_contact_b, 3)} / {fm.num(res.factors.single_contact_d, 3)}
                  </td>
                </AttrRow>
                <AttrRow label={t("cap.ft")} symbol="F_t" unit="N">
                  <td className="wb-num">{fm.num(res.factors.tangential_force_n, 1)}</td>
                </AttrRow>
                <AttrRow label={t("cap.vt")} symbol="v" unit="m/s">
                  <td className="wb-num">{fm.num(res.factors.pitch_velocity_ms, 3)}</td>
                </AttrRow>
                <AttrRow label={t("cap.lineLoad")} symbol="w_t" unit="N/mm">
                  <td className="wb-num">{fm.num(res.factors.line_load_n_mm, 2)}</td>
                </AttrRow>
                <AttrRow label={t("cap.zn")} symbol="z_n" unit="–">
                  <td className="wb-num">
                    {fm.num(res.factors.virtual_teeth[0], 1)} / {fm.num(res.factors.virtual_teeth[1], 1)}
                  </td>
                </AttrRow>
              </tbody>
            </table>
          </Section>
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
  const t = useT();
  const fm = useFmt();
  const tone = (v: number | null, min: number) =>
    v == null ? undefined : v >= min ? ("good" as const) : ("bad" as const);
  return (
    <Section title={`${props.title} — ${g.material} (${g.method})`}>
      <table className="attr-table">
        <tbody>
          <AttrRow label={t("cap.sigmaF")} symbol="σ_F" unit="N/mm²">
            <td className="wb-num">{fm.num(g.root_stress_mpa, 1)}</td>
          </AttrRow>
          <AttrRow label={t("cap.sF")} symbol="S_F" unit="–">
            <td className={`wb-num ${tone(g.root_safety, props.minRoot) === "bad" ? "text-red-600" : "text-emerald-600"}`}>
              {fm.num(g.root_safety, 2)}
            </td>
          </AttrRow>
          <AttrRow label={t("cap.sigmaH")} symbol="σ_H" unit="N/mm²">
            <td className="wb-num">{fm.num(g.flank_stress_mpa, 1)}</td>
          </AttrRow>
          <AttrRow label={t("cap.sH")} symbol="S_H" unit="–">
            <td className={`wb-num ${tone(g.flank_safety, props.minFlank) === "bad" ? "text-red-600" : "text-emerald-600"}`}>
              {fm.num(g.flank_safety, 2)}
            </td>
          </AttrRow>
          {g.nominal_root_stress_mpa != null && (
            <AttrRow label={t("cap.sigmaF0")} symbol="σ_F0" unit="N/mm²">
              <td className="wb-num">{fm.num(g.nominal_root_stress_mpa, 1)}</td>
            </AttrRow>
          )}
          {g.root_permissible_mpa != null && (
            <AttrRow label={t("cap.sigmaFP")} symbol="σ_FP" unit="N/mm²">
              <td className="wb-num">{fm.num(g.root_permissible_mpa, 1)}</td>
            </AttrRow>
          )}
          {g.nominal_flank_stress_mpa != null && (
            <AttrRow label={t("cap.sigmaH0")} symbol="σ_H0" unit="N/mm²">
              <td className="wb-num">{fm.num(g.nominal_flank_stress_mpa, 1)}</td>
            </AttrRow>
          )}
          {g.flank_permissible_mpa != null && (
            <AttrRow label={t("cap.sigmaHP")} symbol="σ_HP" unit="N/mm²">
              <td className="wb-num">{fm.num(g.flank_permissible_mpa, 1)}</td>
            </AttrRow>
          )}
          <AttrRow label={t("cap.yF")} symbol="Y_F" unit="–">
            <td className="wb-num">{fm.num(g.form_factor, 3)}</td>
          </AttrRow>
          <AttrRow label={t("cap.yS")} symbol="Y_S" unit="–">
            <td className="wb-num">{fm.num(g.stress_correction, 3)}</td>
          </AttrRow>
          {g.root_chord_mn != null && (
            <AttrRow label={t("cap.sFn")} symbol="s_Fn*" unit="·m_n">
              <td className="wb-num">{fm.num(g.root_chord_mn, 3)}</td>
            </AttrRow>
          )}
          {g.fillet_radius_mn != null && (
            <AttrRow label={t("cap.rhoF")} symbol="ρ_F*" unit="·m_n">
              <td className="wb-num">{fm.num(g.fillet_radius_mn, 3)}</td>
            </AttrRow>
          )}
          {g.notch_parameter != null && (
            <AttrRow label={t("cap.qs")} symbol="q_s" unit="–">
              <td className="wb-num">{fm.num(g.notch_parameter, 2)}</td>
            </AttrRow>
          )}
          {g.bending_lever_mn != null && (
            <AttrRow label={t("cap.hFe")} symbol="h_Fe*" unit="·m_n">
              <td className="wb-num">{fm.num(g.bending_lever_mn, 3)}</td>
            </AttrRow>
          )}
          {g.load_angle_deg != null && (
            <AttrRow label={t("cap.alphaFen")} symbol="α_Fen" unit="°">
              <td className="wb-num">{fm.num(g.load_angle_deg, 2)}</td>
            </AttrRow>
          )}
          {g.loss_factor != null && (
            <AttrRow label={t("cap.hv")} symbol="H_V" unit="–">
              <td className="wb-num">{fm.num(g.loss_factor, 4)}</td>
            </AttrRow>
          )}
          {g.flank_temperature_c != null && (
            <AttrRow label={t("cap.flankTemp")} symbol="ϑ_Fla" unit="°C">
              <td className="wb-num">{fm.num(g.flank_temperature_c, 1)}</td>
            </AttrRow>
          )}
          {g.peak_stress_mpa != null && (
            <AttrRow label={t("cap.staticPeak")} symbol="σ_F,P" unit="N/mm²">
              <td className="wb-num">{fm.num(g.peak_stress_mpa, 1)}</td>
            </AttrRow>
          )}
          {g.peak_safety != null && (
            <AttrRow label={t("cap.staticSafety")} symbol="S_stat" unit="–">
              <td className="wb-num">{fm.num(g.peak_safety, 2)}</td>
            </AttrRow>
          )}
          {g.tooth_temperature_c != null && (
            <AttrRow label={t("cap.toothTemp")} symbol="ϑ_Z" unit="°C">
              <td className="wb-num">{fm.num(g.tooth_temperature_c, 1)}</td>
            </AttrRow>
          )}
          {g.wear_um != null && (
            <AttrRow label={t("cap.wear")} symbol="W_m" unit="µm">
              <td className="wb-num">{fm.num(g.wear_um, 1)}</td>
            </AttrRow>
          )}
        </tbody>
      </table>
    </Section>
  );
}
