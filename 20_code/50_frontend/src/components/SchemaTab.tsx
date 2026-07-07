"use client";

// Renders one backend-defined editor tab (app/services/uimodel → /api/ui-schema) in the
// FVA attribute-table style: Attribut | Fz | value column(s) | Einheit. Values bind to
// THE workbench store via the schema's dot-paths; computed attributes render grey/locked;
// enum → dropdown, bool → checkbox, action → button. This is the pattern every replica
// tab uses — adding a tab is backend schema work, not new frontend code.

import { useState } from "react";
import type { AttributeDef, RowRef, SectionDef, TabDef, UiSchema } from "@/lib/uischema";
import { useWorkbench } from "@/lib/store";
import { useLocale, useT } from "@/lib/i18n";
import { meshApi } from "@/lib/api";
import { deckPayload } from "@/lib/deck";

function pick(loc: string, de?: string | null, en?: string | null): string {
  return (loc === "de" ? de ?? en : en ?? de) ?? "";
}

/** Action buttons referenced by schema bindings (kind == "action"); a returned string is
 * shown next to the button as the result message. */
function useActions(): Record<string, { label: string; run: () => Promise<string | void> }> {
  const wb = useWorkbench();
  const t = useT();
  return {
    "fem.download_deck": {
      label:
        wb.fem.deck_mode === "series"
          ? "rolling_position_series.zip"
          : "implicit_rolling_generated.inp",
      run: async () => {
        const m2 = wb.get("fem.torque_gear2_nmm");
        if (typeof m2 !== "number" || !Number.isFinite(m2)) {
          throw new Error(t("pf.noTorque"));
        }
        // THE shared payload builder (phase F): identical settings ⇒ byte-identical decks
        // from this tab and the pair view; torque M₂ from the Leistungsfluss on top
        const req = { ...deckPayload(wb), torque_gear2_nmm: m2 };
        const series = wb.fem.deck_mode === "series";
        const blob = series
          ? await meshApi.deckSeries(req)
          : new Blob([await meshApi.deck(req)], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = series ? "rolling_position_series.zip" : "implicit_rolling_generated.inp";
        a.click();
        URL.revokeObjectURL(url);
      },
    },
    "loaddist.run_meshing": {
      label: t("loaddist.runMeshing"),
      run: async () => {
        // quick native meshing check (full 2D rendering lands with the mesh viewport)
        const level = { coarse: 1, medium: 1, fine: 2 }[wb.loaddist.meshing_accuracy] ?? 1;
        const g1 = await meshApi.preview({
          stage: wb.stage,
          gear: 1,
          refine_root: level,
          refine_flank: level,
          fillet: { kind: "standard" },
        });
        const g2 = await meshApi.preview({
          stage: wb.stage,
          gear: 2,
          refine_root: level,
          refine_flank: level,
          fillet: { kind: "standard" },
        });
        return (
          `✓ ${t("common.gear")} 1: ${g1.n_quads} Quads (min J = ${g1.min_scaled_jacobian.toFixed(2)}), ` +
          `${t("common.gear")} 2: ${g2.n_quads} Quads (min J = ${g2.min_scaled_jacobian.toFixed(2)})`
        );
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
  if (attr.kind === "text" || attr.kind === "path") {
    return (
      <input
        type="text"
        value={String(value ?? "")}
        disabled={disabled}
        onChange={(e) => wb.set(binding, e.target.value)}
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
  const isEmpty = value == null;
  const num = typeof value === "number" ? value : Number(value ?? 0);
  const shown = isEmpty
    ? ""
    : attr.precision != null && Number.isFinite(num)
      ? num.toFixed(attr.precision)
      : String(num);
  return (
    <input
      type="number"
      defaultValue={shown}
      key={`${binding}:${shown}:${disabled}`}
      disabled={disabled}
      step={attr.step ?? (attr.kind === "int" ? 1 : undefined)}
      onBlur={(e) => {
        // nullable fields: emptying writes null (reset semantics — e.g. the one
        // powerflow torque, where clearing frees both shaft fields again)
        if (e.target.value === "" && attr.nullable) {
          if (!isEmpty) wb.set(binding, null);
          return;
        }
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
  const [info, setInfo] = useState<string | null>(null);
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
          setInfo(null);
          action
            .run()
            .then((msg) => setInfo(typeof msg === "string" ? msg : null))
            .catch((e) => setErr(e instanceof Error ? e.message : String(e)))
            .finally(() => setBusy(false));
        }}
      >
        {busy ? "…" : action.label}
      </button>
      {err && <span className="text-red-600 text-[11px] ml-2">{err}</span>}
      {info && <span className="text-emerald-700 text-[11px] ml-2">{info}</span>}
    </td>
  );
}

function Row({ schema, row }: { schema: UiSchema; row: RowRef }) {
  const { locale } = useLocale();
  const wb = useWorkbench();
  const attr = schema.attributes[row.attr];
  if (!attr) return null;
  // row-level dynamic lock (dependency rules: DIN 21771 a-mode, torque single input …)
  const rowLocked = row.locked_if ? Boolean(wb.get(row.locked_if)) : false;
  const colLocked = (i: 0 | 1) =>
    rowLocked || (attr.locked_ifs ? Boolean(wb.get(attr.locked_ifs[i])) : false);
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
          <ValueCell attr={attr} binding={attr.bindings[0]} locked={colLocked(0)} />
        </td>
        <td>
          <ValueCell attr={attr} binding={attr.bindings[1]} locked={colLocked(1)} />
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
        {attr.binding ? (
          <ValueCell attr={attr} binding={attr.binding} locked={rowLocked} />
        ) : null}
      </td>
      {unit}
    </tr>
  );
}

function SectionBlock({
  schema,
  section,
  pairHeaders,
}: {
  schema: UiSchema;
  section: SectionDef;
  pairHeaders?: [string, string];
}) {
  const { locale } = useLocale();
  const wb = useWorkbench();
  if (section.visible_if && !wb.get(section.visible_if)) return null;
  const hasPair = section.rows.some((r) => schema.attributes[r.attr]?.per_gear);
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
            <th>{pick(locale, "Attribut", "Attribute")}</th>
            <th>Fz</th>
            {hasPair && pairHeaders ? (
              <>
                <th>{pairHeaders[0]}</th>
                <th>{pairHeaders[1]}</th>
              </>
            ) : (
              <th colSpan={2}></th>
            )}
            <th>{pick(locale, "Einheit", "Unit")}</th>
          </tr>
        </thead>
        <tbody>
          {section.rows.map((r) => {
            if (r.visible_if && !wb.get(r.visible_if)) return null;
            return <Row key={r.attr} schema={schema} row={r} />;
          })}
        </tbody>
      </table>
    </div>
  );
}

export function SchemaTab({
  schema,
  tab,
  pairHeaders,
}: {
  schema: UiSchema;
  tab: TabDef;
  pairHeaders?: [string, string];
}) {
  return (
    <div className="flex flex-col gap-3 max-w-[860px]">
      {tab.sections.map((s) => (
        <SectionBlock key={s.id} schema={schema} section={s} pairHeaders={pairHeaders} />
      ))}
    </div>
  );
}
