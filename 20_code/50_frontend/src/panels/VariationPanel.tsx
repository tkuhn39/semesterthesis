"use client";

// Stufenvariation editor (port + M5 overlay): plastic-capable macro-geometry sweep with
// Pareto front; up to 4 selected variants overlay their REAL as-cut wheel tooth contours
// (root_fillet-capable /api/mesh/contour) — the clean visual comparison the FVA lacks.

import { useEffect, useState } from "react";
import {
  api,
  contourApi,
  type ContourResponse,
  type StageParams,
  type VariationPoint,
  type VariationRequest,
  type VariationResponse,
  type VarSpec,
} from "@/lib/api";
import { ParallelCoordinates, type PCDim } from "@/components/ParallelCoordinates";
import { ContourPlot, OVERLAY_COLORS } from "@/components/ContourPlot";
import { AttrRow, Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { useStage } from "@/lib/stage";
import { useT } from "@/lib/i18n";

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

// Row set = the FVA Stufenvariation dialog (Stufenvariation_Ansicht-1*.png), same order.
// kind "spec" rows are sweepable; kind "fixed" rows carry a value the sweep kernel cannot
// vary (yet) — value editable, Vary checkbox disabled with an honest tooltip.
type Row =
  | { kind: "spec"; key: ParamKey; label: string; symbol: string; unit: string }
  | { kind: "fixed"; key: FixedKey; label: string; symbol: string; unit: string };
const ROWS: Row[] = [
  { kind: "spec", key: "m_n", label: "Normalmodul Rad 1", symbol: "m_n", unit: "mm" },
  { kind: "spec", key: "alpha_n", label: "Normaleingriffswinkel Rad 1", symbol: "α_n", unit: "°" },
  { kind: "spec", key: "beta_deg", label: "Schrägungswinkel Rad 1", symbol: "β", unit: "°" },
  { kind: "spec", key: "z1", label: "Zähnezahl Rad 1", symbol: "z", unit: "" },
  { kind: "spec", key: "z2", label: "Zähnezahl Rad 2", symbol: "z", unit: "" },
  { kind: "spec", key: "x1", label: "Nennprofilverschiebungsfaktor Rad 1", symbol: "x", unit: "" },
  { kind: "spec", key: "x2", label: "Nennprofilverschiebungsfaktor Rad 2", symbol: "x", unit: "" },
  { kind: "spec", key: "b", label: "Zahnbreite Rad 1", symbol: "b", unit: "mm" },
  { kind: "fixed", key: "b2_mm", label: "Zahnbreite Rad 2", symbol: "b", unit: "mm" },
  { kind: "fixed", key: "h_ap1", label: "Kopfhöhenfaktor (Bezugsprofil) Rad 1", symbol: "h_aP*", unit: "" },
  { kind: "fixed", key: "h_ap2", label: "Kopfhöhenfaktor (Bezugsprofil) Rad 2", symbol: "h_aP*", unit: "" },
  { kind: "fixed", key: "h_fp1", label: "Fußhöhenfaktor (Bezugsprofil) Rad 1", symbol: "h_fP*", unit: "" },
  { kind: "fixed", key: "h_fp2", label: "Fußhöhenfaktor (Bezugsprofil) Rad 2", symbol: "h_fP*", unit: "" },
  { kind: "fixed", key: "rho_fp1", label: "Fußausrundungsfaktor (Bezugsprofil) Rad 1", symbol: "ρ_fP*", unit: "" },
  { kind: "fixed", key: "rho_fp2", label: "Fußausrundungsfaktor (Bezugsprofil) Rad 2", symbol: "ρ_fP*", unit: "" },
  { kind: "fixed", key: "q1_mm", label: "Bearbeitungszugabe Rad 1", symbol: "q", unit: "mm" },
  { kind: "fixed", key: "q2_mm", label: "Bearbeitungszugabe Rad 2", symbol: "q", unit: "mm" },
  { kind: "fixed", key: "pr_p1_mm", label: "Protuberanzbetrag Rad 1", symbol: "pr_P", unit: "mm" },
  { kind: "fixed", key: "pr_p2_mm", label: "Protuberanzbetrag Rad 2", symbol: "pr_P", unit: "mm" },
  { kind: "fixed", key: "alpha_pr_p1_deg", label: "Protuberanzwinkel Rad 1", symbol: "α_prP", unit: "°" },
  { kind: "fixed", key: "alpha_pr_p2_deg", label: "Protuberanzwinkel Rad 2", symbol: "α_prP", unit: "°" },
];
const FIXED_HINT =
  "Variation dieses Parameters wird vom Sweep-Kernel noch nicht unterstützt — Wert wirkt als Festwert (Rad-1-Wert führt).";

const PC_DIMS: PCDim[] = [
  { key: "z1", label: "z₁" },
  { key: "x1", label: "x₁" },
  { key: "center_distance_mm", label: "a" },
  { key: "total_contact_ratio", label: "ε_γ" },
  { key: "root_safety_wheel", label: "S_F" },
  { key: "flank_safety_wheel", label: "S_H" },
  { key: "weight_g", label: "Gew." },
];

// The variation BASELINE is the currently active stage (single source of truth) —
// never a hardcoded second gear pair. Ranges open a sensible window around it.
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
    h_fp1: s.tool_addendum_factor, // gear h_fP* == tool h_aP0*
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

interface OverlayEntry {
  label: string;
  data: ContourResponse;
}

export function VariationPanel() {
  const t = useT();
  const { stage } = useStage();
  const [r, setR] = useState<VariationRequest>(() => defaultsFromStage(stage));
  const [res, setRes] = useState<VariationResponse | null>(null);
  const [rows, setRows] = useState<VariationPoint[]>([]);
  const [compare, setCompare] = useState<number[]>([]);
  const [overlays, setOverlays] = useState<OverlayEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    // the baseline follows the shared stage — a geometry edit elsewhere re-seeds the matrix
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setR(defaultsFromStage(stage));
     
  }, [stage]);

  const run = async () => {
    setBusy(true);
    setErr(null);
    setCompare([]);
    setOverlays([]);
    try {
      const out = await api.variation(r);
      setRes(out);
      setRows(
        [...out.points]
          .sort((a, b) => (b.root_safety_wheel ?? -1) - (a.root_safety_wheel ?? -1))
          .slice(0, 120),
      );
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const toggleCompare = async (i: number) => {
    const next = compare.includes(i)
      ? compare.filter((k) => k !== i)
      : [...compare, i].slice(-4); // keep max 4
    setCompare(next);
    const entries: OverlayEntry[] = [];
    for (const k of next) {
      const p = rows[k];
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
        });
        entries.push({ label: `z=${p.z1}/${p.z2} · x₂=${p.x2.toFixed(2)} · m=${p.m_n}`, data: c });
      } catch {
        // invalid variant contour — skip silently, the table still shows it
      }
    }
    setOverlays(entries);
  };

  const setSpec = (key: ParamKey, patch: Partial<VarSpec>) =>
    setR({ ...r, [key]: { ...r[key], ...patch } });
  const set = (k: keyof VariationRequest) => (v: number) => setR({ ...r, [k]: v });
  const setFlag = (k: keyof VariationRequest) => (v: boolean) => setR({ ...r, [k]: v });

  // "Es werden N Varianten berechnet." (FVA footer) — grid: product of the varied steps
  const variantCount = (() => {
    if (r.method !== "grid") return r.sample_count;
    let n = 1;
    for (const row of ROWS) {
      if (row.kind !== "spec") continue;
      const locked =
        r.fix_center_distance && (row.key === "z1" || row.key === "z2" || row.key === "x2");
      const s = r[row.key];
      if (s.vary && !locked && s.steps > 1) n *= s.steps;
    }
    return n;
  })();

  return (
    // FVA wizard layout: the attribute matrix spans the top (separate Wert AND Minimum
    // columns like the dialog — self-review finding), results render below after a run
    <div className="flex flex-col gap-3 items-start max-w-[1100px]">
      <div className="flex flex-col gap-3 w-full">
        <Section title="Stufenvariation — Attribute">
          {/* FVA dialog top checkboxes (Stufenvariation_Ansicht-1.png) */}
          <div className="p-2 flex flex-col gap-1 border-b border-zinc-100 text-[12px] text-zinc-600">
            <label className="inline-flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={r.fix_center_distance}
                onChange={(e) => setFlag("fix_center_distance")(e.target.checked)}
              />
              Achsabstand fixieren
              {r.fix_center_distance && (
                <Num width={84} value={r.center_distance_mm} onChange={set("center_distance_mm")} />
              )}
            </label>
            <label className="inline-flex items-center gap-1.5" title={FIXED_HINT}>
              <input
                type="checkbox"
                checked={r.allow_tip_shortening}
                onChange={(e) => setFlag("allow_tip_shortening")(e.target.checked)}
              />
              Automatische Kopfkürzung zulassen
            </label>
            <label className="inline-flex items-center gap-1.5" title={FIXED_HINT}>
              <input
                type="checkbox"
                checked={r.full_root_round}
                onChange={(e) => setFlag("full_root_round")(e.target.checked)}
              />
              Vollausrundung
            </label>
            <label className="inline-flex items-center gap-1.5" title={FIXED_HINT}>
              <input
                type="checkbox"
                checked={r.dedendum_with_clearance}
                onChange={(e) => setFlag("dedendum_with_clearance")(e.target.checked)}
              />
              Fußhöhen mit Kopfspiel berechnen
            </label>
          </div>
          <table className="attr-table">
            <thead>
              <tr>
                <th>Attribut</th>
                <th>Fz</th>
                <th></th>
                <th>Wert</th>
                <th>Minimum</th>
                <th>Maximum</th>
                <th>Schrittweite</th>
                <th>Einh.</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => {
                if (row.kind === "fixed") {
                  return (
                    <tr key={row.key} title={FIXED_HINT}>
                      <td>{row.label}</td>
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
                const locked =
                  r.fix_center_distance &&
                  (row.key === "z1" || row.key === "z2" || row.key === "x2");
                return (
                  <tr key={row.key} style={{ opacity: locked ? 0.5 : 1 }}>
                    <td>{row.label}</td>
                    <td className="wb-num text-zinc-400">{row.symbol}</td>
                    <td style={{ textAlign: "center" }}>
                      <input
                        type="checkbox"
                        disabled={locked}
                        checked={s.vary && !locked}
                        onChange={(e) => setSpec(row.key, { vary: e.target.checked })}
                      />
                    </td>
                    <td>
                      <Num width={74} value={s.value} onChange={(v) => setSpec(row.key, { value: v })} />
                    </td>
                    <td>
                      <Num width={74} disabled={!s.vary || locked} value={s.min} onChange={(v) => setSpec(row.key, { min: v })} />
                    </td>
                    <td>
                      <Num width={74} disabled={!s.vary || locked} value={s.max} onChange={(v) => setSpec(row.key, { max: v })} />
                    </td>
                    <td>
                      <Num width={60} disabled={!s.vary || locked} value={s.steps} step={1} onChange={(v) => setSpec(row.key, { steps: v })} />
                    </td>
                    <td className="text-zinc-400">{row.unit}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="p-2 flex items-center gap-3 border-t border-zinc-100 text-[12px] text-zinc-600">
            <span>Es werden {variantCount.toLocaleString("de-DE")} Varianten berechnet.</span>
            <select
              className="ml-auto border border-zinc-300 rounded-md px-2 py-1 text-[12px]"
              value={r.method}
              onChange={(e) => setR({ ...r, method: e.target.value as VariationRequest["method"] })}
            >
              <option value="grid">Gitter</option>
              <option value="sobol">Sobol</option>
              <option value="lhs">LHS</option>
            </select>
          </div>
        </Section>

        {/* our extension beyond the FVA dialog (user product vision): material matrix per
            gear + safety targets — the norm dispatch follows the material in the sweep */}
        <Section title="Werkstoff & Sicherheiten (Erweiterung)" defaultOpen={false}>
          <div className="p-2 flex items-center gap-2 text-[12px] text-zinc-600">
            <span>{t("variation.matrix")}</span>
            {(["pinion_material", "wheel_material"] as const).map((k) => (
              <select
                key={k}
                className="border border-zinc-300 rounded-md px-1.5 py-0.5 text-[12px]"
                value={(r as unknown as Record<string, string>)[k] ?? (k === "pinion_material" ? "steel" : "plastic")}
                onChange={(e) => setR({ ...r, [k]: e.target.value } as VariationRequest)}
              >
                <option value="steel">{k === "pinion_material" ? "Ritzel: Stahl" : "Rad: Stahl"}</option>
                <option value="plastic">{k === "pinion_material" ? "Ritzel: Kunststoff" : "Rad: Kunststoff"}</option>
              </select>
            ))}
          </div>
          <table className="attr-table">
            <tbody>
              <AttrRow label="Moment" symbol="T₁" unit="N·m">
                <td><Num value={r.torque_nm} onChange={set("torque_nm")} /></td>
              </AttrRow>
              <AttrRow label="Kunststoff" symbol="σ_Flim" unit="N/mm²">
                <td><Num value={r.plastic_sigma_flim_mpa} onChange={set("plastic_sigma_flim_mpa")} /></td>
              </AttrRow>
              <AttrRow label="Kunststoff" symbol="σ_Hlim" unit="N/mm²">
                <td><Num value={r.plastic_sigma_hlim_mpa} onChange={set("plastic_sigma_hlim_mpa")} /></td>
              </AttrRow>
              <AttrRow label="Mindestsicherheit" symbol="S_Fmin" unit="–">
                <td><Num value={r.root_minimum_safety} onChange={set("root_minimum_safety")} /></td>
              </AttrRow>
            </tbody>
          </table>
        </Section>

        <Btn onClick={() => void run()} busy={busy}>
          Stufenvariation starten
        </Btn>
        {err && <ErrNote>{err}</ErrNote>}
        {res && (
          <div className="grid grid-cols-2 gap-2">
            <Stat label="Varianten" value={res.count.toLocaleString("de-DE")} />
            <Stat label="Pareto" value={res.pareto.toLocaleString("de-DE")} />
          </div>
        )}
      </div>

      <div className="flex flex-col gap-3">
        {res && rows.length > 0 && (
          <>
            <Section title="Parallelkoordinaten" right={<span className="text-[11px] text-zinc-400">Linie wählen = vergleichen</span>}>
              <div className="p-2">
                <ParallelCoordinates
                  points={rows}
                  dims={PC_DIMS}
                  selected={compare[compare.length - 1] ?? null}
                  onSelect={(i) => void toggleCompare(i)}
                  rootMin={r.root_minimum_safety}
                />
              </div>
            </Section>
            <Section
              title={t("variation.overlay")}
              right={<span className="text-[11px] text-zinc-400">max. 4 Varianten · echte erzeugte Kontur (Rad)</span>}
            >
              <div className="p-3">
                {overlays.length > 0 ? (
                  <ContourPlot contours={overlays} teethEachSide={1} height={330} />
                ) : (
                  <div className="text-zinc-400 text-[12px]">
                    Varianten in der Tabelle ankreuzen (bis zu 4) — die echten Zahnkonturen werden überlagert.
                  </div>
                )}
              </div>
            </Section>
            <Section title="Varianten (nach S_F Rad)">
              <div className="max-h-[300px] overflow-y-auto">
                <table className="attr-table">
                  <thead>
                    <tr>
                      <th>Vgl.</th>
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
                    </tr>
                  </thead>
                  <tbody>
                    {rows.slice(0, 60).map((p, i) => {
                      const ci = compare.indexOf(i);
                      return (
                        <tr key={i}>
                          <td style={{ textAlign: "center" }}>
                            <input type="checkbox" checked={ci >= 0} onChange={() => void toggleCompare(i)} />
                            {ci >= 0 && (
                              <span
                                className="inline-block w-2 h-2 rounded-full ml-1"
                                style={{ background: OVERLAY_COLORS[ci % OVERLAY_COLORS.length] }}
                              />
                            )}
                          </td>
                          <td>{p.pareto ? "★" : ""}</td>
                          <td className="wb-num">{p.z1}</td>
                          <td className="wb-num">{p.z2}</td>
                          <td className="wb-num">{p.x1.toFixed(3)}</td>
                          <td className="wb-num">{p.x2.toFixed(3)}</td>
                          <td className="wb-num">{p.m_n.toFixed(2)}</td>
                          <td className="wb-num">{p.center_distance_mm.toFixed(1)}</td>
                          <td className="wb-num">{p.total_contact_ratio.toFixed(3)}</td>
                          <td
                            className="wb-num"
                            style={{
                              color:
                                (p.root_safety_wheel ?? 0) >= r.root_minimum_safety
                                  ? "#059669"
                                  : "#dc2626",
                            }}
                          >
                            {p.root_safety_wheel?.toFixed(2) ?? "–"}
                          </td>
                          <td className="wb-num">{p.weight_g?.toFixed(0) ?? "–"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Section>
          </>
        )}
        {!res && !err && (
          <div className="border border-dashed border-zinc-300 rounded-lg p-6 text-zinc-400 text-[12.5px]">
            Variationsraum festlegen und starten — Parallelkoordinaten, Tabelle und der
            Varianten-Vergleich mit echten Zahnkonturen erscheinen hier.
          </div>
        )}
      </div>
    </div>
  );
}
