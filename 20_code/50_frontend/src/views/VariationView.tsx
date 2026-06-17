import { useState, type JSX } from "react";
import {
  api,
  type ToothProfileResponse,
  type VariationPoint,
  type VariationRequest,
  type VariationResponse,
  type VarSpec,
} from "../lib/api";
import { fmt, safetyVerdict } from "../lib/format";
import { Badge, Button, Card, CardHead, NumberField, Section, Tabs } from "../components/ui";
import { ParallelCoordinates, type PCDim } from "../components/ParallelCoordinates";
import { ToothMeshPlot } from "../components/ToothMeshPlot";

type ParamKey = "m_n" | "z1" | "z2" | "x1" | "x2" | "beta_deg" | "b";
const PARAMS: { key: ParamKey; label: string; unit: string }[] = [
  { key: "m_n", label: "Modul m_n", unit: "mm" },
  { key: "z1", label: "Zähnezahl z₁", unit: "" },
  { key: "z2", label: "Zähnezahl z₂", unit: "" },
  { key: "x1", label: "Profilv. x₁", unit: "" },
  { key: "x2", label: "Profilv. x₂", unit: "" },
  { key: "beta_deg", label: "Schrägung β", unit: "°" },
  { key: "b", label: "Breite b", unit: "mm" },
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

const DEFAULTS: VariationRequest = {
  m_n: { vary: false, value: 2.0, min: 1.0, max: 4.0, steps: 4 },
  z1: { vary: true, value: 24, min: 16, max: 34, steps: 19 },
  z2: { vary: false, value: 60, min: 40, max: 80, steps: 5 },
  x1: { vary: true, value: 0.0, min: -0.3, max: 0.6, steps: 10 },
  x2: { vary: false, value: 0.0, min: -0.3, max: 0.6, steps: 5 },
  beta_deg: { vary: false, value: 0.0, min: 0.0, max: 25.0, steps: 4 },
  b: { vary: false, value: 20.0, min: 10.0, max: 40.0, steps: 4 },
  fix_center_distance: false,
  center_distance_mm: 86.0,
  normal_pressure_angle_deg: 20,
  tool_addendum_factor: 1.25,
  tool_tip_radius_factor: 0.38,
  torque_nm: 15,
  steel_density_kg_m3: 7800,
  plastic_density_kg_m3: 1400,
  steel_sigma_hlim_mpa: 1500,
  steel_sigma_flim_mpa: 430,
  plastic_sigma_hlim_mpa: 60,
  plastic_sigma_flim_mpa: 35,
  root_minimum_safety: 2.0,
  flank_minimum_safety: 1.0,
  method: "grid",
  sample_count: 256,
};

export function VariationView(): JSX.Element {
  const [r, setR] = useState<VariationRequest>(DEFAULTS);
  const [res, setRes] = useState<VariationResponse | null>(null);
  const [rows, setRows] = useState<VariationPoint[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [tooth, setTooth] = useState<ToothProfileResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async () => {
    setBusy(true);
    setErr(null);
    setSelected(null);
    setTooth(null);
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

  const select = async (i: number) => {
    setSelected(i);
    const p = rows[i];
    try {
      setTooth(
        await api.toothProfile({
          normal_module_mm: p.m_n,
          teeth_pinion: p.z1,
          teeth_wheel: p.z2,
          profile_shift_pinion: p.x1,
          profile_shift_wheel: p.x2,
          normal_pressure_angle_deg: r.normal_pressure_angle_deg,
          helix_angle_deg: p.beta_deg,
        }),
      );
    } catch {
      setTooth(null);
    }
  };

  const setSpec = (key: ParamKey, patch: Partial<VarSpec>) =>
    setR({ ...r, [key]: { ...r[key], ...patch } });
  const set = (k: keyof VariationRequest) => (v: number) => setR({ ...r, [k]: v });
  const perSec = res && res.eval_ms > 0 ? (res.count / res.eval_ms) * 1000 : 0;
  const sel = selected != null ? rows[selected] : null;

  return (
    <>
      <p className="page-intro">
        Kunststofftaugliche Makrogeometrie-Variation (Stahlritzel + Kunststoffrad) — vektorisierter
        Kernel mit Frühausschluss, Sobol/LHS-Sampling und Pareto-Front. Eine Variante anklicken zeigt
        rechts den echten Zahneingriff.
      </p>
      <div className="split">
        <div className="stack" style={{ gap: 0 }}>
          <Card>
            <CardHead title="Variations-Matrix" sub="Variieren (Min/Max/Schritte) oder fest" />
            <div className="card-pad">
              <label className="row" style={{ gap: 7, marginBottom: 8, cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={r.fix_center_distance}
                  onChange={(e) => setR({ ...r, fix_center_distance: e.target.checked })}
                />
                <span className="field-label">Achsabstand fixieren</span>
                {r.fix_center_distance && (
                  <input
                    className="input"
                    type="number"
                    style={{ width: 84, padding: "3px 6px", marginLeft: "auto", textAlign: "right" }}
                    value={r.center_distance_mm}
                    step="any"
                    onChange={(e) => set("center_distance_mm")(Number(e.target.value))}
                  />
                )}
              </label>
              <div className="table-wrap">
                <table className="tbl tbl-compact">
                  <thead>
                    <tr>
                      <th>Parameter</th>
                      <th>Var.</th>
                      <th>Wert / Min</th>
                      <th>Max</th>
                      <th>Schr.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {PARAMS.map((pp) => {
                      const s = r[pp.key];
                      const locked =
                        r.fix_center_distance && (pp.key === "z1" || pp.key === "z2" || pp.key === "x2");
                      const derived = r.fix_center_distance && pp.key === "x2";
                      return (
                        <tr key={pp.key} style={{ opacity: locked ? 0.5 : 1 }}>
                          <td className="txt">
                            {pp.label} <span className="muted">{pp.unit}</span>
                            {derived && <span className="muted"> (aus a)</span>}
                          </td>
                          <td style={{ textAlign: "center" }}>
                            <input
                              type="checkbox"
                              disabled={locked}
                              checked={s.vary && !locked}
                              onChange={(e) => setSpec(pp.key, { vary: e.target.checked })}
                            />
                          </td>
                          <td>
                            <MiniInput
                              disabled={derived}
                              value={s.vary && !locked ? s.min : s.value}
                              onChange={(v) => setSpec(pp.key, s.vary && !locked ? { min: v } : { value: v })}
                            />
                          </td>
                          <td>
                            <MiniInput disabled={!s.vary || locked} value={s.max} onChange={(v) => setSpec(pp.key, { max: v })} />
                          </td>
                          <td>
                            <MiniInput disabled={!s.vary || locked} value={s.steps} step={1} onChange={(v) => setSpec(pp.key, { steps: v })} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="field mt-s">
                <span className="field-label">Sampling</span>
                <Tabs
                  value={r.method}
                  onChange={(m) => setR({ ...r, method: m })}
                  options={[
                    { value: "grid", label: "Gitter" },
                    { value: "sobol", label: "Sobol" },
                    { value: "lhs", label: "LHS" },
                  ]}
                />
              </div>
              {r.method !== "grid" && (
                <NumberField label="Stichprobenzahl" value={r.sample_count} onChange={set("sample_count")} step={1} />
              )}

              <Section title="Festes Umfeld" defaultOpen={false}>
                <div className="input-row">
                  <NumberField label="Eingriffswinkel α_n" value={r.normal_pressure_angle_deg} onChange={set("normal_pressure_angle_deg")} hint="°" />
                  <NumberField label="Moment T₁" value={r.torque_nm} onChange={set("torque_nm")} hint="N·m" />
                </div>
                <div className="input-row">
                  <NumberField label="Werkzeug h_aP0*" value={r.tool_addendum_factor} onChange={set("tool_addendum_factor")} />
                  <NumberField label="Werkzeug ρ_aP0*" value={r.tool_tip_radius_factor} onChange={set("tool_tip_radius_factor")} />
                </div>
              </Section>
              <Section title="Werkstoff & Sicherheiten" defaultOpen={false}>
                <div className="input-row">
                  <NumberField label="Stahl σ_Hlim" value={r.steel_sigma_hlim_mpa} onChange={set("steel_sigma_hlim_mpa")} hint="N/mm²" />
                  <NumberField label="Stahl σ_Flim" value={r.steel_sigma_flim_mpa} onChange={set("steel_sigma_flim_mpa")} hint="N/mm²" />
                </div>
                <div className="input-row">
                  <NumberField label="Kunststoff σ_Hlim" value={r.plastic_sigma_hlim_mpa} onChange={set("plastic_sigma_hlim_mpa")} hint="N/mm²" />
                  <NumberField label="Kunststoff σ_Flim" value={r.plastic_sigma_flim_mpa} onChange={set("plastic_sigma_flim_mpa")} hint="N/mm²" />
                </div>
                <div className="input-row">
                  <NumberField label="S_Fmin" value={r.root_minimum_safety} onChange={set("root_minimum_safety")} />
                  <NumberField label="S_Hmin" value={r.flank_minimum_safety} onChange={set("flank_minimum_safety")} />
                </div>
              </Section>

              <Button onClick={run} busy={busy}>
                Stufenvariation starten
              </Button>
            </div>
          </Card>
        </div>

        <div className="stack" style={{ gap: 12 }}>
          {err && <div className="note bad">⚠ {err}</div>}
          {res ? (
            <>
              <div className="grid cols-4">
                <Card><Stat label="Varianten" value={res.count.toLocaleString("de-DE")} /></Card>
                <Card><Stat label="Gültig (gefiltert)" value={res.valid.toLocaleString("de-DE")} /></Card>
                <Card><Stat label="Pareto-optimal" value={res.pareto.toLocaleString("de-DE")} /></Card>
                <Card>
                  <Stat label="Auswertung" value={fmt(res.eval_ms, 1)} unit="ms"
                    foot={perSec > 0 ? `${Math.round(perSec).toLocaleString("de-DE")} Var./s` : undefined} />
                </Card>
              </div>
              {res.warnings.map((w, i) => <div className="note" key={i}>⚠ {w}</div>)}

              <div className="grid" style={{ gridTemplateColumns: "1fr 312px", gap: 12, alignItems: "start" }}>
                <Card>
                  <CardHead title="Parallelkoordinaten" sub="alle gültigen Varianten · Linie/Zeile wählen" />
                  <div className="card-pad" style={{ paddingTop: 10 }}>
                    {rows.length > 0 && (
                      <ParallelCoordinates points={rows} dims={PC_DIMS} selected={selected} onSelect={select} rootMin={r.root_minimum_safety} />
                    )}
                  </div>
                </Card>
                <Card>
                  <CardHead title="Zahneingriff" sub={sel ? `z=${fmt(sel.z1, 0)}/${fmt(sel.z2, 0)}` : "Variante wählen"} />
                  <div className="card-pad" style={{ paddingTop: 10 }}>
                    {tooth ? (
                      <>
                        <ToothMeshPlot data={tooth} />
                        {sel && (
                          <div className="mt-s" style={{ fontSize: 11.5 }}>
                            <div className="kv"><span className="k">a</span><span className="v num">{fmt(sel.center_distance_mm, 2)} mm</span></div>
                            <div className="kv"><span className="k">x₁ / x₂</span><span className="v num">{fmt(sel.x1, 3)} / {fmt(sel.x2, 3)}</span></div>
                            <div className="kv"><span className="k">ε_γ</span><span className="v num">{fmt(sel.total_contact_ratio, 3)}</span></div>
                            <div className="kv"><span className="k">S_F / S_H Rad</span><span className="v num">{fmt(sel.root_safety_wheel, 2)} / {fmt(sel.flank_safety_wheel, 2)}</span></div>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="muted" style={{ fontSize: 12 }}>Eine Variante in der Tabelle oder im Plot wählen.</div>
                    )}
                  </div>
                </Card>
              </div>

              <Card>
                <CardHead title="Varianten" sub="nach Kunststoff-Fußsicherheit · ★ = Pareto · Zeile wählen" />
                <div className="table-wrap">
                  <table className="tbl tbl-compact">
                    <thead>
                      <tr>
                        <th></th><th>z₁</th><th>z₂</th><th>x₁</th><th>x₂</th><th>m_n</th><th>a</th>
                        <th>ε_γ</th><th>S_F Rad</th><th>S_H Rad</th><th>Gew.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.slice(0, 60).map((p, i) => (
                        <tr key={i} className={i === selected ? "row-hi" : ""} style={{ cursor: "pointer" }} onClick={() => select(i)}>
                          <td>{p.pareto ? "★" : ""}</td>
                          <td>{fmt(p.z1, 0)}</td>
                          <td>{fmt(p.z2, 0)}</td>
                          <td>{fmt(p.x1, 3)}</td>
                          <td>{fmt(p.x2, 3)}</td>
                          <td>{fmt(p.m_n, 2)}</td>
                          <td>{fmt(p.center_distance_mm, 1)}</td>
                          <td>{fmt(p.total_contact_ratio, 3)}</td>
                          <td><SBadge value={p.root_safety_wheel} min={r.root_minimum_safety} /></td>
                          <td><SBadge value={p.flank_safety_wheel} min={r.flank_minimum_safety} /></td>
                          <td>{fmt(p.weight_g, 0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </>
          ) : (
            !err && (
              <Card>
                <div className="card-pad muted">
                  Variationsraum festlegen und starten, um Tabelle, Parallelkoordinaten und Zahneingriff zu sehen.
                </div>
              </Card>
            )
          )}
        </div>
      </div>
    </>
  );
}

function MiniInput(props: { value: number; onChange: (v: number) => void; step?: number; disabled?: boolean }): JSX.Element {
  return (
    <input
      type="number"
      className="input"
      style={{ padding: "3px 6px", textAlign: "right", opacity: props.disabled ? 0.4 : 1 }}
      disabled={props.disabled}
      value={Number.isFinite(props.value) ? props.value : ""}
      step={props.step ?? "any"}
      onChange={(e) => props.onChange(Number(e.target.value))}
    />
  );
}

function SBadge(props: { value: number | null; min: number }): JSX.Element {
  return (
    <Badge variant={safetyVerdict(props.value, props.min)} dot>
      {fmt(props.value, 2)}
    </Badge>
  );
}

function Stat(props: { label: string; value: string; unit?: string; foot?: string }): JSX.Element {
  return (
    <div className="stat">
      <div className="stat-label">{props.label}</div>
      <div className="stat-value">
        {props.value}
        {props.unit && <span className="unit">{props.unit}</span>}
      </div>
      {props.foot && <div className="stat-foot">{props.foot}</div>}
    </div>
  );
}
