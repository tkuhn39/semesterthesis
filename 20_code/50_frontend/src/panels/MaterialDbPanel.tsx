"use client";

// Werkstoffdatenbank (user requirement 2026-08-19): a definable material LIBRARY next
// to the built-in catalog. Records are persisted by the backend (app.storage); picking
// one for a gear loads its properties into the session-local Werkstoff fields — edits
// there are never written back. Built-ins are immutable references.

import { useState } from "react";
import { api, type CatalogMaterial, type UserMaterialIn } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useWorkbench } from "@/lib/store";
import { Btn, ErrNote, Num, Section } from "@/components/ui";

const EMPTY_DRAFT: UserMaterialIn = {
  name: "",
  kind: "plastic",
  elastic_modulus_mpa: 3000,
  poisson_ratio: 0.35,
  density_kg_dm3: 1.2,
  sigma_hlim_mpa: 40,
  sigma_flim_mpa: 25,
  yield_strength_mpa: 50,
  allowable_temperature_c: 100,
};

export function MaterialDbPanel({ onLibraryChange }: { onLibraryChange?: () => void }) {
  const t = useT();
  const wb = useWorkbench();
  const [draft, setDraft] = useState<UserMaterialIn>(EMPTY_DRAFT);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const refresh = async () => {
    await wb.refreshMaterialCatalog();
    onLibraryChange?.(); // the schema's mat_name options follow the library
  };

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setErr(null);
    try {
      await action();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const save = () =>
    run(async () => {
      await api.saveMaterial({ ...draft, name: draft.name.trim() });
      await refresh();
    });

  const remove = (entry: CatalogMaterial) =>
    run(async () => {
      await api.deleteMaterial(entry.name);
      await refresh(); // catalog first — the kind re-set below resolves against it
      // a gear pointing at the deleted record snaps back to its kind's default (the
      // kind coupling replaces a name the catalog no longer knows)
      for (const field of ["gear1_name", "gear2_name"] as const) {
        if (wb.materials[field] === entry.name) {
          wb.set(`materials.${field === "gear1_name" ? "gear1_kind" : "gear2_kind"}`, entry.kind);
        }
      }
    });

  const loadDraft = (entry: CatalogMaterial) =>
    setDraft({
      name: entry.builtin ? `${entry.name} Kopie` : entry.name,
      kind: entry.kind,
      elastic_modulus_mpa: entry.elastic_modulus_mpa,
      poisson_ratio: entry.poisson_ratio,
      density_kg_dm3: entry.density_kg_dm3,
      sigma_hlim_mpa: entry.sigma_hlim_mpa,
      sigma_flim_mpa: entry.sigma_flim_mpa,
      yield_strength_mpa: entry.yield_strength_mpa,
      allowable_temperature_c: entry.allowable_temperature_c,
    });

  // seed the form from the session's CURRENT working values of the draft kind — the
  // path from "tuned a material in the fields" to "keep it as a library record"
  const fromFields = () => {
    const m = wb.materials;
    setDraft((d) =>
      d.kind === "steel"
        ? {
            ...d,
            elastic_modulus_mpa: m.steel_modulus_mpa,
            poisson_ratio: m.steel_poisson,
            density_kg_dm3: m.steel_density_kg_dm3,
            sigma_hlim_mpa: m.steel_sigma_hlim_mpa,
            sigma_flim_mpa: m.steel_sigma_flim_mpa,
          }
        : {
            ...d,
            elastic_modulus_mpa: m.plastic_modulus_mpa,
            poisson_ratio: m.plastic_poisson,
            density_kg_dm3: m.plastic_density_kg_dm3,
            sigma_hlim_mpa: m.plastic_sigma_hlim_mpa,
            sigma_flim_mpa: m.plastic_sigma_flim_mpa,
            yield_strength_mpa: m.plastic_yield_strength_mpa,
            allowable_temperature_c: m.plastic_allowable_temperature_c,
          },
    );
  };

  const num = (key: keyof UserMaterialIn, label: string, step?: number) => (
    <label className="flex flex-col gap-0.5 text-[11.5px] text-zinc-600">
      {label}
      <Num
        value={(draft[key] as number | null) ?? 0}
        step={step}
        onChange={(v) => setDraft((d) => ({ ...d, [key]: v }))}
      />
    </label>
  );

  return (
    <Section title={t("matdb.title")} defaultOpen={false}>
      <table className="attr-table">
        <thead>
          <tr>
            <th>{t("matdb.name")}</th>
            <th>{t("matdb.kind")}</th>
            <th className="wb-num">E [N/mm²]</th>
            <th className="wb-num">σ_Hlim</th>
            <th className="wb-num">σ_Flim</th>
            <th className="wb-num">ρ [kg/dm³]</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {wb.materialCatalog.map((m) => (
            <tr key={m.name}>
              <td>
                {m.name}
                <span className="ml-1.5 text-[10px] text-zinc-400">
                  {m.builtin ? t("matdb.builtin") : t("matdb.user")}
                </span>
              </td>
              <td>{t(m.kind === "steel" ? "mat.steel" : "mat.plastic")}</td>
              <td className="wb-num">{m.elastic_modulus_mpa}</td>
              <td className="wb-num">{m.sigma_hlim_mpa ?? "–"}</td>
              <td className="wb-num">{m.sigma_flim_mpa ?? "–"}</td>
              <td className="wb-num">{m.density_kg_dm3 ?? "–"}</td>
              <td>
                <div className="flex gap-1 justify-end">
                  <Btn variant="ghost" onClick={() => wb.set("materials.gear1_name", m.name)}>
                    → {t("common.gear")} 1
                  </Btn>
                  <Btn variant="ghost" onClick={() => wb.set("materials.gear2_name", m.name)}>
                    → {t("common.gear")} 2
                  </Btn>
                  <Btn variant="ghost" onClick={() => loadDraft(m)}>
                    {t("matdb.edit")}
                  </Btn>
                  {!m.builtin && (
                    <Btn variant="ghost" busy={busy} onClick={() => void remove(m)}>
                      {t("matdb.delete")}
                    </Btn>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="p-2 border-t border-zinc-100 flex flex-col gap-2">
        <div className="font-medium text-[12px] text-zinc-700">{t("matdb.new")}</div>
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-0.5 text-[11.5px] text-zinc-600">
            {t("matdb.name")}
            <input
              type="text"
              value={draft.name}
              onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
            />
          </label>
          <label className="flex flex-col gap-0.5 text-[11.5px] text-zinc-600">
            {t("matdb.kind")}
            <select
              value={draft.kind}
              onChange={(e) =>
                setDraft((d) => ({ ...d, kind: e.target.value as "steel" | "plastic" }))
              }
            >
              <option value="steel">{t("mat.steel")}</option>
              <option value="plastic">{t("mat.plastic")}</option>
            </select>
          </label>
          {num("elastic_modulus_mpa", "E [N/mm²]")}
          {num("poisson_ratio", "ν", 0.01)}
          {num("density_kg_dm3", "ρ [kg/dm³]", 0.01)}
          {num("sigma_hlim_mpa", "σ_Hlim [N/mm²]")}
          {num("sigma_flim_mpa", "σ_Flim [N/mm²]")}
          {draft.kind === "plastic" && num("yield_strength_mpa", "R_p0.2 [MPa]")}
          {draft.kind === "plastic" && num("allowable_temperature_c", "ϑ_zul [°C]")}
        </div>
        <div className="flex items-center gap-2">
          <Btn onClick={() => void save()} busy={busy} disabled={draft.name.trim() === ""}>
            {t("matdb.save")}
          </Btn>
          <Btn variant="ghost" onClick={fromFields}>
            {t("matdb.fromFields")}
          </Btn>
        </div>
        <div className="text-[11.5px] text-zinc-500">{t("matdb.note")}</div>
        {err && <ErrNote>{err}</ErrNote>}
      </div>
    </Section>
  );
}
