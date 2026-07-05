"use client";

// Stage geometry editor. Edits write into THE shared stage (single source of truth,
// user decision 2026-07-04) — every other tab (capacity, tolerances, tooth form, mesh,
// deck) derives from the same StageParams, so nothing can diverge. Results are the
// canonical GearStage values from /api/geometry (DIN ISO 21771).

import { useEffect, useState } from "react";
import { api, type GeometryResponse, type StageParams } from "@/lib/api";
import { AttrRow, Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { MeshEngagement } from "@/components/MeshEngagement";
import { useStage } from "@/lib/stage";
import { useWorkbench } from "@/lib/store";
import { useT } from "@/lib/i18n";

export function GeometryPanel() {
  const t = useT();
  const { stage, setStage } = useStage();
  const wb = useWorkbench();
  const aMode = wb.geometryUi.center_distance_mode;
  const [res, setRes] = useState<GeometryResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async (s: StageParams) => {
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.geometry(s));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    // recompute whenever the shared stage changes (edits here or in any other tab)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void run(stage);
     
  }, [stage]);

  // editing a geometry value leaves the kst-E example mode (free parameters from then on)
  const set = (k: keyof StageParams) => (v: number) =>
    setStage({ ...stage, use_example: false, [k]: v });

  return (
    <div className="grid grid-cols-[460px_1fr] gap-3 items-start">
      <div className="flex flex-col gap-3">
        <Section title={t("geo.main")}>
          <table className="attr-table">
            <thead>
              <tr>
                <th>{t("common.attribute")}</th>
                <th></th>
                <th>{t("common.pinion")}</th>
                <th>{t("common.wheel")}</th>
                <th>{t("common.unit")}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Normalmodul</td>
                <td className="wb-num text-zinc-400">m_n</td>
                <td colSpan={2}><Num value={stage.normal_module_mm} onChange={set("normal_module_mm")} /></td>
                <td className="text-zinc-400">mm</td>
              </tr>
              <tr>
                <td>Eingriffswinkel</td>
                <td className="wb-num text-zinc-400">α_n</td>
                <td colSpan={2}><Num value={stage.normal_pressure_angle_deg} onChange={set("normal_pressure_angle_deg")} /></td>
                <td className="text-zinc-400">°</td>
              </tr>
              <tr>
                <td>Zähnezahl</td>
                <td className="wb-num text-zinc-400">z</td>
                <td><Num value={stage.teeth_pinion} onChange={set("teeth_pinion")} step={1} /></td>
                <td><Num value={stage.teeth_wheel} onChange={set("teeth_wheel")} step={1} /></td>
                <td></td>
              </tr>
              <tr>
                <td>Profilverschiebung</td>
                <td className="wb-num text-zinc-400">x</td>
                <td><Num value={stage.profile_shift_pinion} onChange={set("profile_shift_pinion")} /></td>
                <td><Num value={stage.profile_shift_wheel} onChange={set("profile_shift_wheel")} /></td>
                <td></td>
              </tr>
              <tr>
                <td>Schrägungswinkel</td>
                <td className="wb-num text-zinc-400">β</td>
                <td colSpan={2}><Num value={stage.helix_angle_deg} onChange={set("helix_angle_deg")} /></td>
                <td className="text-zinc-400">°</td>
              </tr>
              <tr>
                <td>Zahnbreite</td>
                <td className="wb-num text-zinc-400">b</td>
                <td><Num value={stage.face_width_pinion_mm} onChange={set("face_width_pinion_mm")} /></td>
                <td><Num value={stage.face_width_wheel_mm} onChange={set("face_width_wheel_mm")} /></td>
                <td className="text-zinc-400">mm</td>
              </tr>
              <tr>
                <td>Achsabstand definieren</td>
                <td></td>
                <td colSpan={2}>
                  <select
                    value={aMode}
                    onChange={(e) => wb.set("geometryUi.center_distance_mode", e.target.value)}
                  >
                    <option value="a_and_x">Achsabstand und Profilverschiebung definieren</option>
                    <option value="from_x">Aus den Profilverschiebungen berechnen</option>
                  </select>
                </td>
                <td></td>
              </tr>
              <tr title="DIN 21771: inv α_wt = inv α_t + 2·Σx·tan α_n/Σz — bei 'aus x berechnen' ist a Ergebnis und gesperrt">
                <td>Achsabstand</td>
                <td className="wb-num text-zinc-400">a</td>
                <td colSpan={2}>
                  {aMode === "from_x" ? (
                    <input type="number" disabled value={res?.working_center_distance_mm ?? ""} />
                  ) : (
                    <Num
                      value={stage.center_distance_mm ?? res?.working_center_distance_mm ?? 0}
                      onChange={set("center_distance_mm")}
                    />
                  )}
                </td>
                <td className="text-zinc-400">mm</td>
              </tr>
            </tbody>
          </table>
          <div className="p-2 border-t border-zinc-100">
            <Btn onClick={() => void run(stage)} busy={busy}>
              {t("common.run")}
            </Btn>
          </div>
        </Section>
        {err && <ErrNote>{err}</ErrNote>}
      </div>

      {res && (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-3 gap-2">
            <Stat label="Profilüberdeckung ε_α" value={res.transverse_contact_ratio.toFixed(3)} tone={res.valid ? "good" : "bad"} />
            <Stat label="Sprungüberdeckung ε_β" value={res.overlap_ratio.toFixed(3)} />
            <Stat label="Gesamtüberdeckung ε_γ" value={res.total_contact_ratio.toFixed(3)} />
          </div>
          <Section title={t("geo.diameters")}>
            <table className="attr-table">
              <thead>
                <tr>
                  <th>{t("common.attribute")}</th>
                  <th></th>
                  <th>{t("common.pinion")}</th>
                  <th>{t("common.wheel")}</th>
                  <th>{t("common.unit")}</th>
                </tr>
              </thead>
              <tbody>
                <AttrRow label="Teilkreis" symbol="d" unit="mm">
                  <td className="wb-num">{res.reference_diameter_mm[0].toFixed(3)}</td>
                  <td className="wb-num">{res.reference_diameter_mm[1].toFixed(3)}</td>
                </AttrRow>
                <AttrRow label="Grundkreis" symbol="d_b" unit="mm">
                  <td className="wb-num">{res.base_diameter_mm[0].toFixed(3)}</td>
                  <td className="wb-num">{res.base_diameter_mm[1].toFixed(3)}</td>
                </AttrRow>
                <AttrRow label="Kopfkreis" symbol="d_a" unit="mm">
                  <td className="wb-num">{res.tip_diameter_mm[0].toFixed(3)}</td>
                  <td className="wb-num">{res.tip_diameter_mm[1].toFixed(3)}</td>
                </AttrRow>
                <AttrRow label="Betriebsachsabstand" symbol="a_w" unit="mm">
                  <td className="wb-num" colSpan={2}>{res.working_center_distance_mm.toFixed(3)}</td>
                </AttrRow>
                <AttrRow label="Betriebseingriffswinkel" symbol="α_wt" unit="°">
                  <td className="wb-num" colSpan={2}>{res.working_pressure_angle_deg.toFixed(3)}</td>
                </AttrRow>
              </tbody>
            </table>
          </Section>
          {res.notes.map((n, i) => (
            <div key={i} className="text-[12px] text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-1.5">
              ⚠ {n}
            </div>
          ))}
          <MeshEngagement height={340} />
        </div>
      )}
    </div>
  );
}
