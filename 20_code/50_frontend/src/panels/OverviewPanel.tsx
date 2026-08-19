"use client";

// Overview of THE ACTIVE stage (audit GAP-07: this panel used to show the static kst-E
// example forever, contradicting the tree after any edit). Geometry comes from
// /api/geometry on the shared stage; materials/labels from the one materials store.

import { useEffect, useMemo, useState } from "react";
import { api, type GeometryResponse } from "@/lib/api";
import { ErrNote, Section, Stat } from "@/components/ui";
import { useFmt, useT } from "@/lib/i18n";
import { useWorkbench } from "@/lib/store";

export function OverviewPanel(props: { onNavigate: (key: string) => void }) {
  const t = useT();
  const fm = useFmt();
  const wb = useWorkbench();
  const stage = wb.stage;
  const [geo, setGeo] = useState<GeometryResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const stageKey = useMemo(() => JSON.stringify(stage), [stage]);

  useEffect(() => {
    api
      .geometry(stage)
      .then((g) => {
        setGeo(g);
        setErr(null);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stageKey]);

  if (err) return <ErrNote>{err}</ErrNote>;
  if (!geo) return <div className="text-zinc-400 text-[12.5px]">{t("ov.loading")}</div>;

  const m = wb.materials;
  const kindLabel = (k: "steel" | "plastic") =>
    k === "steel" ? t("mat.steel") : t("mat.plastic");
  const gears = [
    {
      role: `${t("common.pinion")} (${kindLabel(m.gear1_kind)})`,
      material: m.gear1_name,
      teeth: stage.teeth_pinion,
      x: stage.profile_shift_pinion,
      d: geo.reference_diameter_mm[0],
      da: geo.tip_diameter_mm[0],
      b: stage.face_width_pinion_mm,
    },
    {
      role: `${t("common.wheel")} (${kindLabel(m.gear2_kind)})`,
      material: m.gear2_name,
      teeth: stage.teeth_wheel,
      x: stage.profile_shift_wheel,
      d: geo.reference_diameter_mm[1],
      da: geo.tip_diameter_mm[1],
      b: stage.face_width_wheel_mm,
    },
  ];

  return (
    <div className="flex flex-col gap-3 max-w-[980px]">
      <div className="grid grid-cols-4 gap-2">
        <Stat
          label={`${t("attr.a")} a_w`}
          value={fm.num(geo.working_center_distance_mm, 2)}
          unit="mm"
        />
        <Stat label={`${t("attr.mn")} m_n`} value={fm.num(stage.normal_module_mm, 2)} unit="mm" />
        <Stat label={`${t("attr.epsAlpha")} ε_α`} value={fm.num(geo.transverse_contact_ratio, 3)} />
        <Stat label={`${t("attr.epsGamma")} ε_γ`} value={fm.num(geo.total_contact_ratio, 3)} />
        {/* angles (audit COV-16: they were absent from the overview) */}
        <Stat label="α_n" value={fm.num(stage.normal_pressure_angle_deg, 2)} unit="°" />
        <Stat label="β" value={fm.num(stage.helix_angle_deg, 2)} unit="°" />
        <Stat label="α_wt" value={fm.num(geo.working_pressure_angle_deg, 3)} unit="°" />
        <Stat label={`${t("attr.epsBeta")} ε_β`} value={fm.num(geo.overlap_ratio, 3)} />
      </div>
      <Section
        title={
          stage.use_example
            ? `${wb.label} — ${t("ov.exampleNote")}`
            : `${wb.label} — ${t("ov.freeNote")}`
        }
      >
        <table className="attr-table">
          <thead>
            <tr>
              <th>{t("ov.role")}</th>
              <th>{t("ov.material")}</th>
              <th>z</th>
              <th>x</th>
              <th>d [mm]</th>
              <th>d_a [mm]</th>
              <th>b [mm]</th>
            </tr>
          </thead>
          <tbody>
            {gears.map((g, i) => (
              <tr key={i}>
                <td>{g.role}</td>
                <td>{g.material}</td>
                <td className="wb-num">{g.teeth}</td>
                <td className="wb-num">{fm.num(g.x, 4)}</td>
                <td className="wb-num">{fm.num(g.d, 3)}</td>
                <td className="wb-num">{fm.num(g.da, 3)}</td>
                <td className="wb-num">{fm.num(g.b, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>
      <div className="grid grid-cols-3 gap-2">
        {[
          ["wheel.mesh", t("ov.card.mesh"), t("ov.card.meshSub")],
          ["wheel.toothform", t("ov.card.toothform"), t("ov.card.toothformSub")],
          ["variation", t("tree.variation"), t("ov.card.variationSub")],
        ].map(([key, title, sub]) => (
          <button
            key={key}
            type="button"
            onClick={() => props.onNavigate(key)}
            className="text-left border border-zinc-200 rounded-lg bg-white px-3 py-2 hover:border-zinc-400 transition-colors"
          >
            <div className="font-medium text-[12.5px]">{title}</div>
            <div className="text-[11.5px] text-zinc-500">{sub}</div>
          </button>
        ))}
      </div>
      {geo.notes.map((n, i) => (
        <div key={i} className="text-[12px] text-zinc-500">
          · {n}
        </div>
      ))}
    </div>
  );
}
