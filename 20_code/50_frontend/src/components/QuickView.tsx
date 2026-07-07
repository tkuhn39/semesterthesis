"use client";

// Ergebnis-Schnellansicht (FVA right-hand panel): the ISO 21771 Hauptgeometrie and
// Durchmesser tables of the ACTIVE stage — recomputed from /api/geometry whenever the
// shared stage changes (screenshot Stirnradstufe_Geometrie.png, right column).

import { useEffect, useState } from "react";
import { api, type GeometryResponse } from "@/lib/api";
import { instanceLabel, useWorkbench } from "@/lib/store";
import { useFmt, useLocale, useT } from "@/lib/i18n";

function Row(props: { label: string; fz?: string; v1?: string; v2?: string; unit?: string }) {
  return (
    <tr>
      <td>{props.label}</td>
      <td className="wb-num text-zinc-400">{props.fz ?? ""}</td>
      <td className="wb-num text-right">{props.v1 ?? ""}</td>
      <td className="wb-num text-right">{props.v2 ?? ""}</td>
      <td className="text-zinc-400">{props.unit ?? ""}</td>
    </tr>
  );
}

export function QuickView() {
  const wb = useWorkbench();
  const { locale } = useLocale();
  const t = useT();
  const fm = useFmt();
  const [geo, setGeo] = useState<GeometryResponse | null>(null);
  const stage = wb.stage;

  useEffect(() => {
    let alive = true;
    api
      .geometry(stage)
      .then((g) => alive && setGeo(g))
      .catch(() => alive && setGeo(null));
    return () => {
      alive = false;
    };
  }, [stage]);

  const z1 = stage.teeth_pinion;
  const z2 = stage.teeth_wheel;
  const u = z2 / z1;
  const a = geo?.working_center_distance_mm;
  // working pitch diameters d_w,i = 2a·z_i/(z1+z2) (DIN 21771)
  const dw1 = a != null ? (2 * a * z1) / (z1 + z2) : null;
  const dw2 = a != null ? (2 * a * z2) / (z1 + z2) : null;
  const b_common = Math.min(stage.face_width_pinion_mm, stage.face_width_wheel_mm);
  const f = (v: number | null | undefined, d = 3) => fm.num(v, d);
  const g1 = instanceLabel(wb.model.pinion, locale);
  const g2 = instanceLabel(wb.model.wheel, locale);

  return (
    <div className="flex flex-col gap-3">
      <div className="border border-zinc-200 rounded-lg overflow-x-auto bg-white">
        <div className="px-3 py-1.5 text-[12px] font-semibold text-white bg-sky-900">
          {t("quick.mainTitle")}
        </div>
        <table className="attr-table">
          <thead>
            <tr>
              <th></th>
              <th>Fz</th>
              <th className="!text-right">{g1}</th>
              <th className="!text-right">{g2}</th>
              <th>{t("common.unitShort")}</th>
            </tr>
          </thead>
          <tbody>
            <Row label={t("attr.alphaN")} fz="α_n" v1={f(stage.normal_pressure_angle_deg, 5)} unit="°" />
            <Row label={t("attr.mn")} fz="m_n" v1={f(stage.normal_module_mm, 5)} v2={f(stage.normal_module_mm, 5)} unit="mm" />
            <Row label={t("attr.beta")} fz="β" v1={f(stage.helix_angle_deg, 5)} v2={f(stage.helix_angle_deg, 5)} unit="°" />
            <Row label={t("attr.z")} fz="z" v1={String(z1)} v2={String(z2)} />
            <Row label={t("attr.u")} fz="u" v1={f(u)} />
            <Row label={t("attr.a")} fz="a" v1={f(a)} unit="mm" />
            <Row label={t("attr.x")} fz="x" v1={f(stage.profile_shift_pinion, 4)} v2={f(stage.profile_shift_wheel, 4)} />
            <Row label={t("attr.b")} fz="b" v1={f(stage.face_width_pinion_mm)} v2={f(stage.face_width_wheel_mm)} unit="mm" />
            <Row label={t("attr.bGem")} fz="b_gem" v1={f(b_common)} unit="mm" />
            <Row label={t("attr.epsAlpha")} fz="ε_α" v1={f(geo?.transverse_contact_ratio)} />
            <Row label={t("attr.epsBeta")} fz="ε_β" v1={f(geo?.overlap_ratio)} />
            <Row label={t("attr.epsGamma")} fz="ε_γ" v1={f(geo?.total_contact_ratio)} />
          </tbody>
        </table>
      </div>
      <div className="border border-zinc-200 rounded-lg overflow-x-auto bg-white">
        <div className="px-3 py-1.5 text-[12px] font-semibold text-white bg-sky-900">
          {t("quick.diaTitle")}
        </div>
        <table className="attr-table">
          <thead>
            <tr>
              <th></th>
              <th>Fz</th>
              <th className="!text-right">{g1}</th>
              <th className="!text-right">{g2}</th>
              <th>{t("common.unitShort")}</th>
            </tr>
          </thead>
          <tbody>
            <Row label={t("attr.d")} fz="d" v1={f(geo?.reference_diameter_mm[0])} v2={f(geo?.reference_diameter_mm[1])} unit="mm" />
            <Row label={t("attr.dw")} fz="d_w" v1={f(dw1)} v2={f(dw2)} unit="mm" />
            <Row label={t("attr.db")} fz="d_b" v1={f(geo?.base_diameter_mm[0])} v2={f(geo?.base_diameter_mm[1])} unit="mm" />
            <Row label={t("attr.da")} fz="d_a" v1={f(geo?.tip_diameter_mm[0])} v2={f(geo?.tip_diameter_mm[1])} unit="mm" />
            <Row label={t("attr.alphaWt")} fz="α_wt" v1={f(geo?.working_pressure_angle_deg)} unit="°" />
          </tbody>
        </table>
      </div>
    </div>
  );
}
