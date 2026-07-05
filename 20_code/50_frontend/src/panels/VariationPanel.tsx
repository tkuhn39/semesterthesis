"use client";

// Stufenvariation as the FVA-style GUIDED FLOW inside the tree tab (user decision):
//   1 Attribute  →  2 Rechnung  →  3 Filterkriterien  →  4 Ergebnisse (+ Übernehmen)
// Results/filters/selection persist in THE workbench store — going back to step 3/4
// never recomputes; Übernehmen writes the picked variant into the shared stage so every
// other tab follows (single source of truth). Extensions beyond FVA: material matrix per
// gear (norm dispatch), Fußform (root-fillet strategy for the contour comparison + deck).

import { useEffect, useState } from "react";
import {
  api,
  contourApi,
  type ContourResponse,
  type StageParams,
  type VariationPoint,
  type VariationRequest,
  type VarSpec,
} from "@/lib/api";
import { ParallelCoordinates, type PCDim } from "@/components/ParallelCoordinates";
import { ContourPlot, OVERLAY_COLORS } from "@/components/ContourPlot";
import { Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { useFmt, useT } from "@/lib/i18n";
import { useStage } from "@/lib/stage";
import { useWorkbench, type VariationFilter } from "@/lib/store";

type ParamKey = "m_n" | "alpha_n" | "beta_deg" | "z1" | "z2" | "x1" | "x2" | "b";
type FixedKey =
  | "b2_mm"
  | "h_ap1"
  | "h_ap2"
  | "h_fp1"
  | "h_fp2"
  | "rho_fp1"
  | "rho_fp2"
  | "q1_mm"
  | "q2_mm"
  | "pr_p1_mm"
  | "pr_p2_mm"
  | "alpha_pr_p1_deg"
  | "alpha_pr_p2_deg";

type Row =
  | { kind: "spec"; key: ParamKey; labelKey: string; gear: 1 | 2; symbol: string; unit: string }
  | { kind: "fixed"; key: FixedKey; labelKey: string; gear: 1 | 2; symbol: string; unit: string };
// FVA row set — labels resolve to "<attr> Rad n" via the DICT (DE = exact FVA wording)
const ROWS: Row[] = [
  { kind: "spec", key: "m_n", labelKey: "attr.mn", gear: 1, symbol: "m_n", unit: "mm" },
  { kind: "spec", key: "alpha_n", labelKey: "attr.alphaN", gear: 1, symbol: "α_n", unit: "°" },
  { kind: "spec", key: "beta_deg", labelKey: "attr.beta", gear: 1, symbol: "β", unit: "°" },
  { kind: "spec", key: "z1", labelKey: "attr.z", gear: 1, symbol: "z", unit: "" },
  { kind: "spec", key: "z2", labelKey: "attr.z", gear: 2, symbol: "z", unit: "" },
  { kind: "spec", key: "x1", labelKey: "attr.x", gear: 1, symbol: "x", unit: "" },
  { kind: "spec", key: "x2", labelKey: "attr.x", gear: 2, symbol: "x", unit: "" },
  { kind: "spec", key: "b", labelKey: "attr.b", gear: 1, symbol: "b", unit: "mm" },
  { kind: "fixed", key: "b2_mm", labelKey: "attr.b", gear: 2, symbol: "b", unit: "mm" },
  { kind: "fixed", key: "h_ap1", labelKey: "attr.haP", gear: 1, symbol: "h_aP*", unit: "" },
  { kind: "fixed", key: "h_ap2", labelKey: "attr.haP", gear: 2, symbol: "h_aP*", unit: "" },
  { kind: "fixed", key: "h_fp1", labelKey: "attr.hfP", gear: 1, symbol: "h_fP*", unit: "" },
  { kind: "fixed", key: "h_fp2", labelKey: "attr.hfP", gear: 2, symbol: "h_fP*", unit: "" },
  { kind: "fixed", key: "rho_fp1", labelKey: "attr.rhofP", gear: 1, symbol: "ρ_fP*", unit: "" },
  { kind: "fixed", key: "rho_fp2", labelKey: "attr.rhofP", gear: 2, symbol: "ρ_fP*", unit: "" },
  { kind: "fixed", key: "q1_mm", labelKey: "attr.q", gear: 1, symbol: "q", unit: "mm" },
  { kind: "fixed", key: "q2_mm", labelKey: "attr.q", gear: 2, symbol: "q", unit: "mm" },
  { kind: "fixed", key: "pr_p1_mm", labelKey: "attr.prP", gear: 1, symbol: "pr_P", unit: "mm" },
  { kind: "fixed", key: "pr_p2_mm", labelKey: "attr.prP", gear: 2, symbol: "pr_P", unit: "mm" },
  { kind: "fixed", key: "alpha_pr_p1_deg", labelKey: "attr.alphaPrP", gear: 1, symbol: "α_prP", unit: "°" },
  { kind: "fixed", key: "alpha_pr_p2_deg", labelKey: "attr.alphaPrP", gear: 2, symbol: "α_prP", unit: "°" },
];

const PC_DIMS: PCDim[] = [
  { key: "z1", label: "z₁" },
  { key: "x1", label: "x₁" },
  { key: "center_distance_mm", label: "a" },
  { key: "total_contact_ratio", label: "ε_γ" },
  { key: "root_safety_wheel", label: "S_F" },
  { key: "flank_safety_wheel", label: "S_H" },
  { key: "weight_g", label: "Gew." },
];

// step-3 result filters (FVA Ansicht-3: Ergebnis-Attribute with min/max)
const FILTERS: { key: keyof VariationPoint; labelKey: string; gear?: 1 | 2; symbol: string }[] = [
  { key: "total_contact_ratio", labelKey: "attr.epsGamma", symbol: "ε_γ" },
  { key: "flank_safety_pinion", labelKey: "attr.sh", gear: 1, symbol: "S_H" },
  { key: "flank_safety_wheel", labelKey: "attr.sh", gear: 2, symbol: "S_H" },
  { key: "root_safety_pinion", labelKey: "attr.sf", gear: 1, symbol: "S_F" },
  { key: "root_safety_wheel", labelKey: "attr.sf", gear: 2, symbol: "S_F" },
  { key: "center_distance_mm", labelKey: "attr.a", symbol: "a" },
  { key: "weight_g", labelKey: "attr.weight", symbol: "m" },
];

function defaultsFromStage(s: StageParams): VariationRequest {
  const a0 = s.center_distance_mm ?? (s.normal_module_mm * (s.teeth_pinion + s.teeth_wheel)) / 2;
  return {
    m_n: { vary: false, value: s.normal_module_mm, min: s.normal_module_mm / 2, max: s.normal_module_mm * 2, steps: 4 },
    alpha_n: { vary: false, value: s.normal_pressure_angle_deg, min: s.normal_pressure_angle_deg - 2.5, max: s.normal_pressure_angle_deg + 2.5, steps: 6 },
    beta_deg: { vary: false, value: s.helix_angle_deg, min: 0.0, max: 25.0, steps: 4 },
    z1: { vary: true, value: s.teeth_pinion, min: Math.max(8, s.teeth_pinion - 10), max: s.teeth_pinion + 10, steps: 21 },
    z2: { vary: false, value: s.teeth_wheel, min: Math.max(8, s.teeth_wheel - 10), max: s.teeth_wheel + 10, steps: 5 },
    x1: { vary: true, value: s.profile_shift_pinion, min: -1.0, max: 1.0, steps: 10 },
    x2: { vary: false, value: s.profile_shift_wheel, min: -1.0, max: 1.0, steps: 5 },
    b: { vary: false, value: s.face_width_pinion_mm, min: Math.max(5, s.face_width_pinion_mm - 10), max: s.face_width_pinion_mm + 15, steps: 4 },
    b2_mm: s.face_width_wheel_mm,
    h_ap1: 1.0,
    h_ap2: 1.0,
    h_fp1: s.tool_addendum_factor,
    h_fp2: s.tool_addendum_factor,
    rho_fp1: s.tool_tip_radius_factor,
    rho_fp2: s.tool_tip_radius_factor,
    q1_mm: 0.0,
    q2_mm: 0.0,
    pr_p1_mm: 0.0,
    pr_p2_mm: 0.0,
    alpha_pr_p1_deg: 0.0,
    alpha_pr_p2_deg: 0.0,
    allow_tip_shortening: false,
    full_root_round: false,
    dedendum_with_clearance: false,
    fix_center_distance: false,
    center_distance_mm: a0,
    normal_pressure_angle_deg: s.normal_pressure_angle_deg,
    tool_addendum_factor: s.tool_addendum_factor,
    tool_tip_radius_factor: s.tool_tip_radius_factor,
    torque_nm: 7.85,
    steel_density_kg_m3: 7850,
    plastic_density_kg_m3: 1410,
    steel_sigma_hlim_mpa: 1500,
    steel_sigma_flim_mpa: 430,
    plastic_sigma_hlim_mpa: 60,
    plastic_sigma_flim_mpa: 35,
    root_minimum_safety: 2.0,
    flank_minimum_safety: 1.0,
    method: "grid",
    sample_count: 256,
  };
}

function applyFilters(points: VariationPoint[], filters: Record<string, VariationFilter>): VariationPoint[] {
  return points.filter((p) =>
    FILTERS.every(({ key }) => {
      const f = filters[key as string];
      if (!f) return true;
      const v = p[key] as number | null;
      if (v == null) return true;
      if (f.min != null && v < f.min) return false;
      if (f.max != null && v > f.max) return false;
      return true;
    }),
  );
}

interface OverlayEntry {
  label: string;
  data: ContourResponse;
}

export function VariationPanel() {
  const { stage, setStage, setLabel } = useStage();
  const wb = useWorkbench();
  const t = useT();
  const fm = useFmt();
  const v = wb.varUi;
  const [r, setR] = useState<VariationRequest>(() => defaultsFromStage(stage));
  const [overlays, setOverlays] = useState<OverlayEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const gearLabel = (labelKey: string, gear?: 1 | 2) =>
    gear ? `${t(labelKey)} ${t("common.gear")} ${gear}` : t(labelKey);
  const fixedHint = t("var.fixedHint");

  useEffect(() => {
    // the baseline follows the shared stage — a geometry edit elsewhere re-seeds step 1
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setR(defaultsFromStage(stage));
  }, [stage]);

  const setVar = (patch: Partial<typeof v>) => {
    for (const [k, val] of Object.entries(patch)) wb.set(`varUi.${k}`, val);
  };

  const run = async () => {
    setBusy(true);
    setErr(null);
    setVar({ step: 2, compare: [] });
    setOverlays([]);
    try {
      const out = await api.variation(r);
      const rows = [...out.points].sort(
        (a, b) => (b.root_safety_wheel ?? -1) - (a.root_safety_wheel ?? -1),
      );
      setVar({ res: out, rows, step: 3 });
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setVar({ step: 1 });
    } finally {
      setBusy(false);
    }
  };

  const filtered = applyFilters(v.rows, v.filters);

  const buildOverlays = async (indices: number[], pts: VariationPoint[]) => {
    const entries: OverlayEntry[] = [];
    for (const k of indices) {
      const p = pts[k];
      if (!p) continue;
      try {
        const c = await contourApi.contour({
          stage: {
            ...stage,
            use_example: false,
            normal_module_mm: p.m_n,
            teeth_pinion: p.z1,
            teeth_wheel: p.z2,
            profile_shift_pinion: p.x1,
            profile_shift_wheel: p.x2,
            normal_pressure_angle_deg: r.normal_pressure_angle_deg,
            helix_angle_deg: p.beta_deg,
            face_width_pinion_mm: p.b ?? 20,
            face_width_wheel_mm: p.b ?? 20,
            center_distance_mm: null,
            tool_addendum_factor: r.tool_addendum_factor,
            tool_tip_radius_factor: r.tool_tip_radius_factor,
          },
          gear: 2,
          fillet: { kind: v.fillet_kind }, // Fußform (our extension)
        });
        entries.push({ label: `z=${p.z1}/${p.z2} · x₂=${p.x2.toFixed(2)} · m=${p.m_n}`, data: c });
      } catch {
        // invalid variant contour — skip silently, the table still shows it
      }
    }
    setOverlays(entries);
  };

  const toggleCompare = (i: number) => {
    const next = v.compare.includes(i) ? v.compare.filter((k) => k !== i) : [...v.compare, i].slice(-4);
    setVar({ compare: next });
    void buildOverlays(next, filtered);
  };

  useEffect(() => {
    // returning to step 4 (tab switch / back-navigation): overlays are local state and
    // gone, but the persisted compare selection is not — rebuild the contours once
    if (v.step === 4 && v.compare.length > 0 && overlays.length === 0) {
      // async fetch — setOverlays fires after the contour round-trip, not synchronously
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void buildOverlays(v.compare, filtered);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [v.step]);

  const applyVariant = (p: VariationPoint) => {
    // Übernehmen (FVA): the picked variant becomes THE stage — every tab follows (SSOT)
    setStage({
      ...stage,
      use_example: false,
      normal_module_mm: p.m_n,
      teeth_pinion: Math.round(p.z1),
      teeth_wheel: Math.round(p.z2),
      profile_shift_pinion: p.x1,
      profile_shift_wheel: p.x2,
      helix_angle_deg: p.beta_deg,
      face_width_pinion_mm: p.b,
      face_width_wheel_mm: r.b2_mm,
      center_distance_mm: null,
    });
    setLabel(`Variante z=${Math.round(p.z1)}/${Math.round(p.z2)} x₁=${p.x1.toFixed(2)}`);
  };

  const setSpec = (key: ParamKey, patch: Partial<VarSpec>) => setR({ ...r, [key]: { ...r[key], ...patch } });
  const set = (k: keyof VariationRequest) => (val: number) => setR({ ...r, [k]: val });
  const setFlag = (k: keyof VariationRequest) => (val: boolean) => setR({ ...r, [k]: val });

  const variantCount = (() => {
    if (r.method !== "grid") return r.sample_count;
    let n = 1;
    for (const row of ROWS) {
      if (row.kind !== "spec") continue;
      const locked = r.fix_center_distance && (row.key === "z1" || row.key === "z2" || row.key === "x2");
      const s = r[row.key];
      if (s.vary && !locked && s.steps > 1) n *= s.steps;
    }
    return n;
  })();

  const stepChip = (n: number, label: string) => (
    <span
      key={n}
      className={`px-2 py-0.5 rounded-full text-[11.5px] ${
        v.step === n ? "bg-blue-600 text-white" : n < v.step ? "bg-blue-100 text-blue-800" : "bg-zinc-100 text-zinc-500"
      }`}
    >
      {n}. {label}
    </span>
  );

  return (
    <div className="flex flex-col gap-3 items-start max-w-[1150px]">
      <div className="flex items-center gap-2">
        {stepChip(1, t("var.step1"))}
        <span className="text-zinc-300">→</span>
        {stepChip(2, t("var.step2"))}
        <span className="text-zinc-300">→</span>
        {stepChip(3, t("var.step3"))}
        <span className="text-zinc-300">→</span>
        {stepChip(4, t("var.step4"))}
        {v.res && v.step !== 4 && (
          <span className="text-[11.5px] text-zinc-400 ml-2">{t("var.persistNote")}</span>
        )}
      </div>
      {err && <ErrNote>{err}</ErrNote>}

      {v.step === 1 && (
        <div className="flex flex-col gap-3 w-full">
          <div className="text-[12.5px] text-zinc-600">{t("var.step1Hint")}</div>
          <Section title={t("var.attrTitle")}>
            <div className="p-2 flex flex-col gap-1 border-b border-zinc-100 text-[12px] text-zinc-600">
              <label className="inline-flex items-center gap-1.5">
                <input type="checkbox" checked={r.fix_center_distance} onChange={(e) => setFlag("fix_center_distance")(e.target.checked)} />
                {t("var.fixA")}
                {r.fix_center_distance && <Num width={84} value={r.center_distance_mm} onChange={set("center_distance_mm")} />}
              </label>
              <label className="inline-flex items-center gap-1.5" title={fixedHint}>
                <input type="checkbox" checked={r.allow_tip_shortening} onChange={(e) => setFlag("allow_tip_shortening")(e.target.checked)} />
                {t("var.tipShort")}
              </label>
              <label className="inline-flex items-center gap-1.5" title={fixedHint}>
                <input type="checkbox" checked={r.full_root_round} onChange={(e) => setFlag("full_root_round")(e.target.checked)} />
                {t("var.fullRound")}
              </label>
              <label className="inline-flex items-center gap-1.5" title={fixedHint}>
                <input type="checkbox" checked={r.dedendum_with_clearance} onChange={(e) => setFlag("dedendum_with_clearance")(e.target.checked)} />
                {t("var.dedClear")}
              </label>
            </div>
            <table className="attr-table">
              <thead>
                <tr>
                  <th>{t("common.attribute")}</th>
                  <th>Fz</th>
                  <th></th>
                  <th>{t("common.value")}</th>
                  <th>{t("common.min")}</th>
                  <th>{t("common.max")}</th>
                  <th>{t("var.stepSize")}</th>
                  <th>{t("common.unitShort")}</th>
                </tr>
              </thead>
              <tbody>
                {ROWS.map((row) => {
                  if (row.kind === "fixed") {
                    return (
                      <tr key={row.key} title={fixedHint}>
                        <td>{gearLabel(row.labelKey, row.gear)}</td>
                        <td className="wb-num text-zinc-400">{row.symbol}</td>
                        <td style={{ textAlign: "center" }}>
                          <input type="checkbox" disabled checked={false} />
                        </td>
                        <td>
                          <Num width={74} value={r[row.key]} onChange={set(row.key)} />
                        </td>
                        <td></td>
                        <td></td>
                        <td></td>
                        <td className="text-zinc-400">{row.unit}</td>
                      </tr>
                    );
                  }
                  const s = r[row.key];
                  const locked = r.fix_center_distance && (row.key === "z1" || row.key === "z2" || row.key === "x2");
                  return (
                    <tr key={row.key} style={{ opacity: locked ? 0.5 : 1 }}>
                      <td>{gearLabel(row.labelKey, row.gear)}</td>
                      <td className="wb-num text-zinc-400">{row.symbol}</td>
                      <td style={{ textAlign: "center" }}>
                        <input type="checkbox" disabled={locked} checked={s.vary && !locked} onChange={(e) => setSpec(row.key, { vary: e.target.checked })} />
                      </td>
                      <td>
                        <Num width={74} value={s.value} onChange={(val) => setSpec(row.key, { value: val })} />
                      </td>
                      <td>
                        <Num width={74} disabled={!s.vary || locked} value={s.min} onChange={(val) => setSpec(row.key, { min: val })} />
                      </td>
                      <td>
                        <Num width={74} disabled={!s.vary || locked} value={s.max} onChange={(val) => setSpec(row.key, { max: val })} />
                      </td>
                      <td>
                        <Num width={60} disabled={!s.vary || locked} value={s.steps} step={1} onChange={(val) => setSpec(row.key, { steps: val })} />
                      </td>
                      <td className="text-zinc-400">{row.unit}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Section>

          <Section title={t("var.extTitle")} defaultOpen={false}>
            <div className="p-2 flex items-center gap-2 text-[12px] text-zinc-600 flex-wrap">
              {(["pinion_material", "wheel_material"] as const).map((k) => (
                <select
                  key={k}
                  className="border border-zinc-300 rounded-md px-1.5 py-0.5 text-[12px]"
                  value={r[k] ?? (k === "pinion_material" ? "steel" : "plastic")}
                  onChange={(e) => setR({ ...r, [k]: e.target.value as "steel" | "plastic" })}
                  title={t("var.normNote")}
                >
                  <option value="steel">{`${t("common.gear")} ${k === "pinion_material" ? 1 : 2}: ${t("mat.steel")}`}</option>
                  <option value="plastic">{`${t("common.gear")} ${k === "pinion_material" ? 1 : 2}: ${t("mat.plastic")}`}</option>
                </select>
              ))}
              <label className="inline-flex items-center gap-1.5" title={t("var.fussformNote")}>
                {t("var.fussform")}:
                <select
                  className="border border-zinc-300 rounded-md px-1.5 py-0.5 text-[12px]"
                  value={v.fillet_kind}
                  onChange={(e) => setVar({ fillet_kind: e.target.value as typeof v.fillet_kind })}
                >
                  <option value="standard">{t("mesh.fillet.standard")}</option>
                  <option value="trochoid">{t("mesh.fillet.trochoid")}</option>
                  <option value="elliptic">{t("mesh.fillet.elliptic")}</option>
                  <option value="bezier">{t("mesh.fillet.bezier")}</option>
                  <option value="bionic">{t("mesh.fillet.bionic")}</option>
                </select>
              </label>
            </div>
            <table className="attr-table">
              <tbody>
                <tr>
                  <td>{t("var.torque")}</td>
                  <td className="wb-num text-zinc-400">T₁</td>
                  <td><Num value={r.torque_nm} onChange={set("torque_nm")} /></td>
                  <td className="text-zinc-400">N·m</td>
                </tr>
                <tr>
                  <td>{t("var.sfMin")}</td>
                  <td className="wb-num text-zinc-400">S_Fmin</td>
                  <td><Num value={r.root_minimum_safety} onChange={set("root_minimum_safety")} /></td>
                  <td></td>
                </tr>
              </tbody>
            </table>
          </Section>

          <div className="flex items-center gap-3 w-full">
            <span className="text-[12px] text-zinc-600">
              {t("var.countCompute").replace("{n}", fm.int(variantCount))}
            </span>
            <select
              className="border border-zinc-300 rounded-md px-2 py-1 text-[12px]"
              value={r.method}
              onChange={(e) => setR({ ...r, method: e.target.value as VariationRequest["method"] })}
            >
              <option value="grid">{t("var.method.grid")}</option>
              <option value="sobol">Sobol</option>
              <option value="lhs">LHS</option>
            </select>
            <div className="ml-auto flex gap-2">
              {v.res && (
                <Btn variant="ghost" onClick={() => setVar({ step: 3 })}>
                  {t("var.continueExisting")}
                </Btn>
              )}
              <Btn onClick={() => void run()} busy={busy}>
                {t("var.computeNext")}
              </Btn>
            </div>
          </div>
        </div>
      )}

      {v.step === 2 && (
        <Section title={t("var.step2")}>
          <div className="p-6 text-[13px] text-zinc-600 flex items-center gap-3">
            <span className="inline-block w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
            {t("var.computing").replace("{n}", fm.int(variantCount))}
          </div>
        </Section>
      )}

      {v.step === 3 && v.res && (
        <div className="flex flex-col gap-3 w-full">
          <div className="text-[12.5px] text-zinc-600">{t("var.step3Hint")}</div>
          <Section title={t("var.filterTitle")}>
            <table className="attr-table">
              <thead>
                <tr>
                  <th>{t("common.attribute")}</th>
                  <th>Fz</th>
                  <th>{t("common.min")}</th>
                  <th>{t("common.max")}</th>
                </tr>
              </thead>
              <tbody>
                {FILTERS.map((f) => {
                  const cur = v.filters[f.key as string] ?? { min: null, max: null };
                  // changing a filter re-indexes the filtered list → drop the compare
                  // selection (its indices would silently point at other variants)
                  const setF = (patch: Partial<VariationFilter>) =>
                    setVar({
                      filters: { ...v.filters, [f.key as string]: { ...cur, ...patch } },
                      compare: [],
                    });
                  return (
                    <tr key={f.key as string}>
                      <td>{gearLabel(f.labelKey, f.gear)}</td>
                      <td className="wb-num text-zinc-400">{f.symbol}</td>
                      <td>
                        <input
                          type="number"
                          value={cur.min ?? ""}
                          placeholder="–"
                          onChange={(e) => setF({ min: e.target.value === "" ? null : Number(e.target.value) })}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          value={cur.max ?? ""}
                          placeholder="–"
                          onChange={(e) => setF({ max: e.target.value === "" ? null : Number(e.target.value) })}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Section>
          <div className="text-[12px] text-zinc-600">
            {t("var.countResult")
              .replace("{n}", fm.int(v.res.count))
              .replace("{m}", fm.int(v.res.valid))
              .replace("{k}", fm.int(v.res.count - v.res.valid))}
            <br />
            <span className="font-semibold">
              {t("var.countShown").replace("{n}", fm.int(filtered.length))}
            </span>
          </div>
          {v.res.warnings.length > 0 && (
            <div className="text-[12px] text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-1.5">
              {v.res.warnings.map((w, i) => (
                <div key={i}>⚠ {w}</div>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <Btn variant="ghost" onClick={() => setVar({ step: 1 })}>
              {t("var.back")}
            </Btn>
            <Btn onClick={() => setVar({ step: 4 })}>{t("var.next")}</Btn>
          </div>
        </div>
      )}

      {v.step === 4 && v.res && (
        <div className="flex flex-col gap-3 w-full">
          <div className="text-[12.5px] text-zinc-600">{t("var.step4Hint")}</div>
          <div className="grid grid-cols-3 gap-2 max-w-[520px]">
            <Stat label={t("var.filteredStat")} value={fm.int(filtered.length)} />
            <Stat label={t("var.okStat")} value={fm.int(v.res.valid)} />
            <Stat label={t("var.paretoStat")} value={fm.int(v.res.pareto)} />
          </div>
          <Section
            title={t("var.pcTitle")}
            right={<span className="text-[11px] text-zinc-400">{t("var.pcNote")}</span>}
          >
            <div className="p-2">
              <ParallelCoordinates
                points={filtered}
                dims={PC_DIMS}
                selected={v.compare[v.compare.length - 1] ?? null}
                onSelect={toggleCompare}
                rootMin={r.root_minimum_safety}
              />
            </div>
          </Section>
          <div className="grid grid-cols-[1fr_420px] gap-3 items-start">
            <Section title={t("var.tableTitle")}>
              <div className="max-h-[340px] overflow-y-auto">
                <table className="attr-table">
                  <thead>
                    <tr>
                      <th>{t("var.compareCol")}</th>
                      <th>★</th>
                      <th>z₁</th>
                      <th>z₂</th>
                      <th>x₁</th>
                      <th>x₂</th>
                      <th>m_n</th>
                      <th>a</th>
                      <th>ε_γ</th>
                      <th>S_F Rad</th>
                      <th>Gew. [g]</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.slice(0, 80).map((p, i) => {
                      const ci = v.compare.indexOf(i);
                      return (
                        <tr key={i} style={ci >= 0 ? { background: "#eff6ff" } : undefined}>
                          <td style={{ textAlign: "center" }}>
                            <input type="checkbox" checked={ci >= 0} onChange={() => toggleCompare(i)} />
                            {ci >= 0 && (
                              <span className="inline-block w-2 h-2 rounded-full ml-1" style={{ background: OVERLAY_COLORS[ci % OVERLAY_COLORS.length] }} />
                            )}
                          </td>
                          <td>{p.pareto ? "★" : ""}</td>
                          <td className="wb-num">{p.z1}</td>
                          <td className="wb-num">{p.z2}</td>
                          <td className="wb-num">{fm.num(p.x1, 3)}</td>
                          <td className="wb-num">{fm.num(p.x2, 3)}</td>
                          <td className="wb-num">{p.m_n}</td>
                          <td className="wb-num">{fm.num(p.center_distance_mm, 2)}</td>
                          <td className="wb-num">{fm.num(p.total_contact_ratio, 3)}</td>
                          <td className="wb-num">{fm.num(p.root_safety_wheel, 2)}</td>
                          <td className="wb-num">{fm.num(p.weight_g, 0)}</td>
                          <td>
                            <button
                              type="button"
                              className="px-1.5 py-0.5 border border-zinc-300 rounded text-[11px] bg-white hover:bg-zinc-50"
                              onClick={() => applyVariant(p)}
                            >
                              {t("var.apply")}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Section>
            <Section
              title={t("var.plotTitle")}
              right={
                <span className="text-[11px] text-zinc-400">
                  max. 4 · {t("var.fussform")}: {v.fillet_kind}
                </span>
              }
            >
              <div className="p-3">
                {overlays.length > 0 ? (
                  <ContourPlot contours={overlays} teethEachSide={1} height={300} />
                ) : (
                  <div className="text-zinc-400 text-[12px]">{t("var.plotHint")}</div>
                )}
              </div>
            </Section>
          </div>
          <div className="flex gap-2">
            <Btn variant="ghost" onClick={() => setVar({ step: 3 })}>
              {t("var.back")}
            </Btn>
            <Btn variant="ghost" onClick={() => setVar({ step: 1 })}>
              {t("var.newVariation")}
            </Btn>
          </div>
        </div>
      )}
    </div>
  );
}
