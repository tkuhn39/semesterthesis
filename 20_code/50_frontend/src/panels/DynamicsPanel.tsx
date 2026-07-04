"use client";

// Dynamic factors editor (port): native ISO 6336-1 K_v/K_Hα/K_Hβ + resonance diagnostics.

import { useEffect, useState } from "react";
import { api, type DynamicsRequest, type DynamicsResponse } from "@/lib/api";
import { AttrRow, Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { useStage } from "@/lib/stage";
import { useT } from "@/lib/i18n";

// Operating conditions only — the geometry comes from THE shared stage (SSOT).
const DEFAULTS: DynamicsRequest = {
  pinion_speed_min1: 1000,
  pinion_torque_nm: 7.85,
  application_factor: 1.0,
  base_pitch_deviation_um: 6.0,
  profile_form_deviation_um: 5.0,
};

export function DynamicsPanel() {
  const t = useT();
  const { stage } = useStage();
  const [req, setReq] = useState<DynamicsRequest>(DEFAULTS);
  const [res, setRes] = useState<DynamicsResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async (r: DynamicsRequest) => {
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.dynamics({ ...r, stage }));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    // recompute when the shared stage changes (geometry edits land here too)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void run(req);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage]);

  const set = (k: keyof DynamicsRequest) => (v: number) => setReq({ ...req, [k]: v });

  return (
    <div className="grid grid-cols-[360px_1fr] gap-3 items-start">
      <div className="flex flex-col gap-3">
        <Section title={t("cap.operating")}>
          <table className="attr-table">
            <tbody>
              <AttrRow label="Drehzahl" symbol="n₁" unit="min⁻¹">
                <td><Num value={req.pinion_speed_min1} onChange={set("pinion_speed_min1")} /></td>
              </AttrRow>
              <AttrRow label="Ritzelmoment" symbol="T₁" unit="N·m">
                <td><Num value={req.pinion_torque_nm} onChange={set("pinion_torque_nm")} /></td>
              </AttrRow>
              <AttrRow label="Anwendungsfaktor" symbol="K_A" unit="–">
                <td><Num value={req.application_factor} onChange={set("application_factor")} /></td>
              </AttrRow>
              <AttrRow label="Eingriffsteilungsabweichung" symbol="f_pb" unit="µm">
                <td><Num value={req.base_pitch_deviation_um} onChange={set("base_pitch_deviation_um")} /></td>
              </AttrRow>
              <AttrRow label="Profil-Formabweichung" symbol="f_fα" unit="µm">
                <td><Num value={req.profile_form_deviation_um} onChange={set("profile_form_deviation_um")} /></td>
              </AttrRow>
            </tbody>
          </table>
          <div className="p-2 border-t border-zinc-100">
            <Btn onClick={() => void run(req)} busy={busy}>
              {t("common.run")}
            </Btn>
          </div>
        </Section>
        {err && <ErrNote>{err}</ErrNote>}
      </div>

      {res && (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-3 gap-2">
            <Stat label="Dynamikfaktor K_v" value={res.dynamic_factor.toFixed(3)} />
            <Stat label="Stirnfaktor K_Hα" value={res.transverse_factor_flank.toFixed(3)} />
            <Stat label="Breitenfaktor K_Hβ" value={res.face_load_factor_flank.toFixed(3)} />
          </div>
          <Section title="Resonanz (ISO 6336-1)">
            <table className="attr-table">
              <tbody>
                <AttrRow label="Eingriffssteifigkeit" symbol="c_γα" unit="N/(mm·µm)">
                  <td className="wb-num">{res.mesh_stiffness.toFixed(2)}</td>
                </AttrRow>
                <AttrRow label="Reduzierte Masse" symbol="m_red" unit="kg/mm">
                  <td className="wb-num">{res.reduced_mass.toExponential(3)}</td>
                </AttrRow>
                <AttrRow label="Resonanzdrehzahl" symbol="n_E1" unit="min⁻¹">
                  <td className="wb-num">{res.resonance_speed_min1.toFixed(0)}</td>
                </AttrRow>
                <AttrRow label="Bezugsdrehzahl" symbol="N" unit="–">
                  <td className="wb-num">{res.resonance_ratio.toFixed(3)}</td>
                </AttrRow>
                <AttrRow label="Bereich" symbol="" unit="">
                  <td className="wb-num">{res.regime}</td>
                </AttrRow>
              </tbody>
            </table>
          </Section>
        </div>
      )}
    </div>
  );
}
