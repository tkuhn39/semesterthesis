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
