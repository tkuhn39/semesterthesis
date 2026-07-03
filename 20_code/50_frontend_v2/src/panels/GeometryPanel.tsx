"use client";

// Stage geometry editor (port of the Vite GeometryView into the workbench attribute-table
// style): edit macro parameters, recompute via the vectorized ISO 21771 kernel.

import { useEffect, useState } from "react";
import { api, type GeometryRequest, type GeometryResponse } from "@/lib/api";
import { AttrRow, Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { useT } from "@/lib/i18n";

const DEFAULTS: GeometryRequest = {
  normal_module_mm: 1.0,
  teeth_pinion: 51,
  teeth_wheel: 52,
  profile_shift_pinion: 0.2034,
  profile_shift_wheel: 0.3143,
  normal_pressure_angle_deg: 20,
  helix_angle_deg: 0,
  face_width_mm: 17,
};

export function GeometryPanel() {
  const t = useT();
  const [req, setReq] = useState<GeometryRequest>(DEFAULTS);
  const [res, setRes] = useState<GeometryResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async (r: GeometryRequest) => {
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.geometry(r));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    // initial compute on mount; async, so state updates land post-render
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void run(DEFAULTS);
  }, []);

  const set = (k: keyof GeometryRequest) => (v: number) => setReq({ ...req, [k]: v });

  return (
    <div className="grid grid-cols-[400px_1fr] gap-3 items-start">
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
                <td colSpan={2}><Num value={req.normal_module_mm} onChange={set("normal_module_mm")} /></td>
                <td className="text-zinc-400">mm</td>
              </tr>
              <tr>
                <td>Eingriffswinkel</td>
                <td className="wb-num text-zinc-400">α_n</td>
                <td colSpan={2}><Num value={req.normal_pressure_angle_deg} onChange={set("normal_pressure_angle_deg")} /></td>
                <td className="text-zinc-400">°</td>
              </tr>
              <tr>
                <td>Zähnezahl</td>
                <td className="wb-num text-zinc-400">z</td>
                <td><Num value={req.teeth_pinion} onChange={set("teeth_pinion")} step={1} /></td>
                <td><Num value={req.teeth_wheel} onChange={set("teeth_wheel")} step={1} /></td>
                <td></td>
              </tr>
              <tr>
                <td>Profilverschiebung</td>
                <td className="wb-num text-zinc-400">x</td>
                <td><Num value={req.profile_shift_pinion} onChange={set("profile_shift_pinion")} /></td>
                <td><Num value={req.profile_shift_wheel} onChange={set("profile_shift_wheel")} /></td>
                <td></td>
              </tr>
              <tr>
                <td>Schrägungswinkel</td>
                <td className="wb-num text-zinc-400">β</td>
                <td colSpan={2}><Num value={req.helix_angle_deg} onChange={set("helix_angle_deg")} /></td>
                <td className="text-zinc-400">°</td>
              </tr>
              <tr>
                <td>Zahnbreite</td>
                <td className="wb-num text-zinc-400">b</td>
                <td colSpan={2}><Num value={req.face_width_mm} onChange={set("face_width_mm")} /></td>
                <td className="text-zinc-400">mm</td>
              </tr>
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
        </div>
      )}
    </div>
  );
}
