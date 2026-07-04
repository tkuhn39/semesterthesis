"use client";

// Berechnungsauswahl (screenshot Getriebeeinheit_Berechnungsauswahl.png): the method
// checkbox matrix. Selected methods reveal their editor tabs (schema.enables_tabs);
// unimplemented methods render greyed out (user decision); ISO 6336 + VDI 2736 stay
// always-on — the Stufenvariation needs both complete for the analytic safeties.

import type { UiSchema } from "@/lib/uischema";
import { useWorkbench } from "@/lib/store";
import { useLocale } from "@/lib/i18n";

export function CalcSelectionPanel({ schema }: { schema: UiSchema }) {
  const { locale } = useLocale();
  const pick = (de: string, en: string) => (locale === "de" ? de : en);

  const groups: { title: string; ids: string[] }[] = [];
  for (const m of schema.methods) {
    const title = pick(m.group_de, m.group_en);
    const g = groups.find((x) => x.title === title);
    if (g) g.ids.push(m.id);
    else groups.push({ title, ids: [m.id] });
  }

  return (
    <div className="max-w-[860px] flex flex-col gap-3">
      <div className="px-3 py-2 text-[12px] text-sky-900 bg-sky-50 border border-sky-100 rounded-lg">
        ⓘ{" "}
        {pick(
          "Im Rahmen der Gesamtsystemberechnung werden immer die Geometrie und die analytischen " +
            "Tragfähigkeiten (ISO 6336, VDI 2736) berechnet — die Stufenvariation benötigt beide " +
            "vollständig. Zusätzlich können die folgenden Berechnungen aktiviert werden; " +
            "ausgegraute Verfahren sind (noch) nicht implementiert.",
          "The system run always computes the geometry and the analytic capacities (ISO 6336, " +
            "VDI 2736) — the Stufenvariation needs both. Additional methods can be enabled; " +
            "greyed-out methods are not implemented (yet).",
        )}
      </div>
      <div className="border border-zinc-200 rounded-lg overflow-hidden bg-white">
        <table className="attr-table">
          <thead>
            <tr>
              <th>Attribut</th>
              <th style={{ width: 120 }}>Getriebeeinheit [1]</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <GroupRows key={g.title} schema={schema} title={g.title} ids={g.ids} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function GroupRows({ schema, title, ids }: { schema: UiSchema; title: string; ids: string[] }) {
  const wb = useWorkbench();
  const { locale } = useLocale();
  return (
    <>
      <tr>
        <td colSpan={2} className="!bg-zinc-50 font-semibold text-sky-800">
          {title}
        </td>
      </tr>
      {ids.map((id) => {
        const m = schema.methods.find((x) => x.id === id)!;
        const label = locale === "de" ? m.label_de : m.label_en;
        const checked = m.always_on || Boolean(wb.calc[m.id]);
        const disabled = !m.implemented || m.always_on;
        return (
          <tr key={id} style={{ opacity: m.implemented ? 1 : 0.45 }}>
            <td title={m.implemented ? undefined : locale === "de" ? "nicht implementiert" : "not implemented"}>
              {label}
            </td>
            <td style={{ textAlign: "center" }}>
              <input
                type="checkbox"
                checked={checked}
                disabled={disabled}
                onChange={(e) => wb.setCalc(m.id, e.target.checked)}
              />
            </td>
          </tr>
        );
      })}
    </>
  );
}
