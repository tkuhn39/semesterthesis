"use client";

// Renders one backend-defined editor tab (app/services/uimodel → /api/ui-schema) in the
// FVA attribute-table style: Attribut | Fz | value column(s) | Einheit. Values bind to
// THE workbench store via the schema's dot-paths; computed attributes render grey/locked;
// enum → dropdown, bool → checkbox, action → button. This is the pattern every replica
// tab uses — adding a tab is backend schema work, not new frontend code.

import { useState } from "react";
import type { AttributeDef, SectionDef, TabDef, UiSchema } from "@/lib/uischema";
import { useWorkbench } from "@/lib/store";
import { useLocale } from "@/lib/i18n";
import { meshApi } from "@/lib/api";

function pick(loc: string, de?: string | null, en?: string | null): string {
  return (loc === "de" ? de ?? en : en ?? de) ?? "";
}

/** Action buttons referenced by schema bindings (kind == "action"). */
function useActions(): Record<string, { label: string; run: () => Promise<void> }> {
  const wb = useWorkbench();
  return {
    "fem.download_deck": {
      label: "implicit_rolling_generated.inp",
      run: async () => {
        const text = await meshApi.deck({
          stage: wb.stage,
          torque_gear2_nmm: wb.fem.torque_gear2_nmm,
          face_layers: wb.fem.face_layers,
          n_roll_positions: wb.fem.n_roll_positions,
          refine_root: wb.fem.refine_root,
          refine_flank: wb.fem.refine_flank,
          gear1_material: wb.fem.gear1_material,
          gear2_material: wb.fem.gear2_material,
          steel_shell: wb.fem.steel_shell,
          align_contact: wb.fem.align_contact,
          fasten_bore: wb.fem.fasten_bore,
          fasten_cuts: wb.fem.fasten_cuts,
          fasten_top: wb.fem.fasten_top,
          fasten_bottom: wb.fem.fasten_bottom,
        });
        const blob = new Blob([text], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "implicit_rolling_generated.inp";
        a.click();
        URL.revokeObjectURL(url);
      },
    },
  };
}

function ValueCell({
  attr,
  binding,
  locked,
}: {
  attr: AttributeDef;
  binding: string;
  locked: boolean;
}) {
  const wb = useWorkbench();
  const { locale } = useLocale();
  const value = wb.get(binding);
  const disabled = locked || attr.computed;

  // computed value not delivered yet — show a dash instead of a misleading 0
  if (attr.computed && (value === undefined || value === null)) {
    return <span className="text-zinc-400">–</span>;
  }
  if (attr.kind === "bool") {
    return (
      <input
        type="checkbox"
        checked={Boolean(value)}
        disabled={disabled}
        onChange={(e) => wb.set(binding, e.target.checked)}
      />
    );
  }
  if (attr.kind === "enum") {
    return (
      <select
        value={String(value ?? "")}
        disabled={disabled}
        onChange={(e) => wb.set(binding, e.target.value)}
      >
        {(attr.options ?? []).map((o) => (
          <option key={o.value} value={o.value}>
            {pick(locale, o.label_de, o.label_en)}
          </option>
        ))}
      </select>
    );
  }
  const num = typeof value === "number" ? value : Number(value ?? 0);
  const shown =
    attr.precision != null && Number.isFinite(num) ? num.toFixed(attr.precision) : String(num);
  return (
    <input
      type="number"
      defaultValue={shown}
      key={`${binding}:${shown}`}
      disabled={disabled}
      step={attr.step ?? (attr.kind === "int" ? 1 : undefined)}
      onBlur={(e) => {
        const v = attr.kind === "int" ? parseInt(e.target.value, 10) : Number(e.target.value);
        if (Number.isFinite(v) && v !== num) wb.set(binding, v);
      }}
    />
  );
}

function ActionCell({ attr }: { attr: AttributeDef }) {
  const actions = useActions();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const action = attr.binding ? actions[attr.binding] : undefined;
  if (!action) return <td className="text-zinc-400">—</td>;
  return (
    <td colSpan={2}>
      <button
        className="px-2 py-0.5 border border-zinc-300 rounded-md bg-white hover:bg-zinc-50 text-[12px] disabled:opacity-50"
        disabled={busy}
        onClick={() => {
          setBusy(true);
          setErr(null);
          action
            .run()
            .catch((e) => setErr(e instanceof Error ? e.message : String(e)))
            .finally(() => setBusy(false));
        }}
      >
        {busy ? "…" : action.label}
      </button>
      {err && <span className="text-red-600 text-[11px] ml-2">{err}</span>}
    </td>
  );
}

function Row({ schema, attrId }: { schema: UiSchema; attrId: string }) {
  const { locale } = useLocale();
  const attr = schema.attributes[attrId];
  if (!attr) return null;
  const unit = attr.unit ? <td className="text-zinc-400">{attr.unit}</td> : <td></td>;
  const label = (
    <td title={pick(locale, attr.info_de, attr.info_en) || attr.norm_ref || undefined}>
      {pick(locale, attr.label_de, attr.label_en)}
    </td>
  );
  const fz = <td className="wb-num text-zinc-400">{attr.symbol ?? ""}</td>;
  if (attr.kind === "action") {
    return (
      <tr>
        {label}
        {fz}
        <ActionCell attr={attr} />
        {unit}
      </tr>
    );
  }
  if (attr.per_gear && attr.bindings) {
    return (
      <tr>
        {label}
        {fz}
        <td>
          <ValueCell attr={attr} binding={attr.bindings[0]} locked={false} />
        </td>
        <td>
          <ValueCell attr={attr} binding={attr.bindings[1]} locked={false} />
        </td>
        {unit}
      </tr>
    );
  }
  return (
    <tr>
      {label}
      {fz}
      <td colSpan={2}>
        {attr.binding ? <ValueCell attr={attr} binding={attr.binding} locked={false} /> : null}
      </td>
      {unit}
    </tr>
  );
}

function SectionBlock({ schema, section }: { schema: UiSchema; section: SectionDef }) {
  const { locale } = useLocale();
  const wb = useWorkbench();
  if (section.visible_if && !wb.get(section.visible_if)) return null;
  return (
    <div className="border border-zinc-200 rounded-lg overflow-hidden bg-white">
      <div className="px-3 py-1.5 text-[12px] font-semibold text-sky-800 bg-sky-50 border-b border-zinc-200">
        {pick(locale, section.title_de, section.title_en)}
      </div>
      {(section.info_de || section.info_en) && (
        <div className="px-3 py-1.5 text-[12px] text-amber-800 bg-amber-50 border-b border-amber-100">
          ⓘ {pick(locale, section.info_de, section.info_en)}
        </div>
      )}
      <table className="attr-table">
        <thead>
          <tr>
            <th>Attribut</th>
            <th>Fz</th>
            <th colSpan={2}></th>
            <th>Einheit</th>
          </tr>
        </thead>
        <tbody>
          {section.rows.map((r) => {
            if (r.visible_if && !wb.get(r.visible_if)) return null;
            return <Row key={r.attr} schema={schema} attrId={r.attr} />;
          })}
        </tbody>
      </table>
    </div>
  );
}

export function SchemaTab({ schema, tab }: { schema: UiSchema; tab: TabDef }) {
  return (
    <div className="flex flex-col gap-3 max-w-[860px]">
      {tab.sections.map((s) => (
        <SectionBlock key={s.id} schema={schema} section={s} />
      ))}
    </div>
  );
}
