"use client";

// Overview: the preloaded kst-E pair at a glance + jump-off points into the tree panels.

import { useEffect, useState } from "react";
import { api, type ExampleResponse } from "@/lib/api";
import { ErrNote, Section, Stat } from "@/components/ui";

export function OverviewPanel(props: { onNavigate: (key: string) => void }) {
  const [ex, setEx] = useState<ExampleResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .example()
      .then(setEx)
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, []);

  if (err) return <ErrNote>{err}</ErrNote>;
  if (!ex) return <div className="text-zinc-400 text-[12.5px]">Lade kst-E …</div>;

  return (
    <div className="flex flex-col gap-3 max-w-[980px]">
      <div className="grid grid-cols-4 gap-2">
        <Stat label="Achsabstand a" value={ex.center_distance_mm.toFixed(1)} unit="mm" />
        <Stat label="Normalmodul m_n" value={ex.normal_module_mm.toFixed(2)} unit="mm" />
        <Stat label="Profilüberdeckung ε_α" value={ex.transverse_contact_ratio.toFixed(3)} />
        <Stat label="Gesamtüberdeckung ε_γ" value={ex.total_contact_ratio.toFixed(3)} />
      </div>
      <Section title={`${ex.name} — ${ex.description}`}>
        <table className="attr-table">
          <thead>
            <tr>
              <th>Rolle</th>
              <th>Werkstoff</th>
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
                <td className="wb-num">{g.profile_shift.toFixed(4)}</td>
                <td className="wb-num">{g.reference_diameter_mm.toFixed(3)}</td>
                <td className="wb-num">{g.tip_diameter_mm.toFixed(3)}</td>
                <td className="wb-num">{g.face_width_mm.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>
      <div className="grid grid-cols-3 gap-2">
        {[
          ["wheel.mesh", "FE-Mesh (Kunststoffrad)", "Referenz-Topologie, Feinheit, Fußkurven, 3D"],
          ["wheel.toothform", "Zahnform", "Echte erzeugte Kontur inkl. optimierter Fußkurven"],
          ["variation", "Stufenvariation", "Sweep + Pareto + Varianten-Vergleich"],
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
