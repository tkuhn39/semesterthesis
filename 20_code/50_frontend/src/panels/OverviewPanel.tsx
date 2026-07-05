"use client";

// Overview: the preloaded kst-E pair at a glance + jump-off points into the tree panels.

import { useEffect, useState } from "react";
import { api, type ExampleResponse } from "@/lib/api";
import { ErrNote, Section, Stat } from "@/components/ui";
import { useFmt, useT } from "@/lib/i18n";

export function OverviewPanel(props: { onNavigate: (key: string) => void }) {
  const t = useT();
  const fm = useFmt();
  const [ex, setEx] = useState<ExampleResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .example()
      .then(setEx)
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, []);

  if (err) return <ErrNote>{err}</ErrNote>;
  if (!ex) return <div className="text-zinc-400 text-[12.5px]">{t("ov.loading")}</div>;

  return (
    <div className="flex flex-col gap-3 max-w-[980px]">
      <div className="grid grid-cols-4 gap-2">
        <Stat label={`${t("attr.a")} a`} value={fm.num(ex.center_distance_mm, 1)} unit="mm" />
        <Stat label={`${t("attr.mn")} m_n`} value={fm.num(ex.normal_module_mm, 2)} unit="mm" />
        <Stat label={`${t("attr.epsAlpha")} ε_α`} value={fm.num(ex.transverse_contact_ratio, 3)} />
        <Stat label={`${t("attr.epsGamma")} ε_γ`} value={fm.num(ex.total_contact_ratio, 3)} />
      </div>
      <Section title={`${ex.name} — ${ex.description}`}>
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
            {ex.gears.map((g, i) => (
              <tr key={i}>
                <td>{g.role}</td>
                <td>{g.material}</td>
                <td className="wb-num">{g.teeth}</td>
                <td className="wb-num">{fm.num(g.profile_shift, 4)}</td>
                <td className="wb-num">{fm.num(g.reference_diameter_mm, 3)}</td>
                <td className="wb-num">{fm.num(g.tip_diameter_mm, 3)}</td>
                <td className="wb-num">{fm.num(g.face_width_mm, 1)}</td>
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
      {ex.notes.map((n, i) => (
        <div key={i} className="text-[12px] text-zinc-500">
          · {n}
        </div>
      ))}
    </div>
  );
}
