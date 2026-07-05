"use client";

// Dynamic factors editor (port): native ISO 6336-1 K_v/K_Hα/K_Hβ + resonance diagnostics.
// The load case (T₁, n₁) comes from THE Leistungsfluss (SSOT — no panel-local copy);
// K_A and the deviations are the shared operating values (Tragfähigkeit tab owns them).

import { useEffect, useMemo, useState } from "react";
import { api, type DynamicsRequest, type DynamicsResponse } from "@/lib/api";
import { AttrRow, Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { useWorkbench } from "@/lib/store";
import { useFmt, useT } from "@/lib/i18n";

export function DynamicsPanel() {
  const t = useT();
  const fm = useFmt();
  const wb = useWorkbench();
  const stage = wb.stage;
  const [res, setRes] = useState<DynamicsResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const req: DynamicsRequest = useMemo(
    () => ({
      pinion_speed_min1: wb.get("operating.pinion_speed_min1") as number,
      pinion_torque_nm: wb.get("operating.pinion_torque_nm") as number,
      application_factor: wb.operating.application_factor,
      base_pitch_deviation_um: wb.operating.base_pitch_deviation_um,
      profile_form_deviation_um: wb.operating.profile_form_deviation_um,
    }),
    [wb],
  );
  const reqKey = useMemo(() => JSON.stringify({ ...req, stage }), [req, stage]);

  const run = async () => {
    if (req.pinion_torque_nm == null || !Number.isFinite(req.pinion_torque_nm)) {
      setRes(null);
      setErr(t("pf.noTorque"));
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.dynamics({ ...req, stage }));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    // recompute when the shared stage OR the Leistungsfluss load case changes
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reqKey]);

  // K_A and deviations are shared operating values — edits write back to the store
  const setOp = (k: string) => (v: number) => wb.set(`operating.${k}`, v);

  return (
    <div className="grid grid-cols-[360px_1fr] gap-3 items-start">
      <div className="flex flex-col gap-3">
        <Section title={t("cap.operating")}>
          <table className="attr-table">
            <tbody>
              <AttrRow label={t("cap.speed")} symbol="n₁" unit="min⁻¹">
                <td className="wb-num text-zinc-500">{fm.num(req.pinion_speed_min1, 1)}</td>
              </AttrRow>
              <AttrRow label={t("cap.pinionTorque")} symbol="T₁" unit="N·m">
                <td className="wb-num text-zinc-500">{fm.num(req.pinion_torque_nm, 4)}</td>
              </AttrRow>
              <AttrRow label={t("dyn.ka")} symbol="K_A" unit="–">
                <td><Num value={req.application_factor} onChange={setOp("application_factor")} /></td>
              </AttrRow>
              <AttrRow label={t("tol.fpb")} symbol="f_pb" unit="µm">
                <td><Num value={req.base_pitch_deviation_um} onChange={setOp("base_pitch_deviation_um")} /></td>
              </AttrRow>
              <AttrRow label={t("tol.ffa")} symbol="f_fα" unit="µm">
                <td><Num value={req.profile_form_deviation_um} onChange={setOp("profile_form_deviation_um")} /></td>
              </AttrRow>
            </tbody>
          </table>
          <div className="px-3 py-1.5 text-[11.5px] text-zinc-500 border-t border-zinc-100">
            {t("cap.inputsNote")}
          </div>
          <div className="p-2 border-t border-zinc-100">
            <Btn onClick={() => void run()} busy={busy}>
              {t("common.run")}
            </Btn>
          </div>
        </Section>
        {err && <ErrNote>{err}</ErrNote>}
      </div>

      {res && (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-3 gap-2">
            <Stat label={t("dyn.kv")} value={fm.num(res.dynamic_factor, 3)} />
            <Stat label={t("dyn.kha")} value={fm.num(res.transverse_factor_flank, 3)} />
            <Stat label={t("dyn.khb")} value={fm.num(res.face_load_factor_flank, 3)} />
          </div>
          <Section title={t("dyn.resonance")}>
            <table className="attr-table">
              <tbody>
                <AttrRow label={t("dyn.cGamma")} symbol="c_γα" unit="N/(mm·µm)">
                  <td className="wb-num">{fm.num(res.mesh_stiffness, 2)}</td>
                </AttrRow>
                <AttrRow label={t("dyn.mRed")} symbol="m_red" unit="kg/mm">
                  <td className="wb-num">{res.reduced_mass.toExponential(3)}</td>
                </AttrRow>
                <AttrRow label={t("dyn.nE1")} symbol="n_E1" unit="min⁻¹">
                  <td className="wb-num">{fm.num(res.resonance_speed_min1, 0)}</td>
                </AttrRow>
                <AttrRow label={t("dyn.refN")} symbol="N" unit="–">
                  <td className="wb-num">{fm.num(res.resonance_ratio, 3)}</td>
                </AttrRow>
                <AttrRow label={t("dyn.range")} symbol="" unit="">
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
