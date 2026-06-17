import { useState, type JSX } from "react";
import { api, type VariationRequest, type VariationResponse, type VarSpec } from "../lib/api";
import { fmt, safetyVerdict } from "../lib/format";
import { Badge, Button, Card, CardHead, NumberField, Section, Tabs } from "../components/ui";

type ParamKey = "m_n" | "z1" | "z2" | "x1" | "x2" | "beta_deg" | "b";
const PARAMS: { key: ParamKey; label: string; unit: string; int?: boolean }[] = [
  { key: "m_n", label: "Modul m_n", unit: "mm" },
  { key: "z1", label: "Zähnezahl z₁", unit: "—", int: true },
  { key: "z2", label: "Zähnezahl z₂", unit: "—", int: true },
  { key: "x1", label: "Profilv. x₁", unit: "—" },
  { key: "x2", label: "Profilv. x₂", unit: "—" },
  { key: "beta_deg", label: "Schrägung β", unit: "°" },
  { key: "b", label: "Breite b", unit: "mm" },
];

const DEFAULTS: VariationRequest = {
  m_n: { vary: false, value: 2.0, min: 1.0, max: 4.0, steps: 4 },
  z1: { vary: true, value: 24, min: 16, max: 34, steps: 19 },
  z2: { vary: false, value: 60, min: 40, max: 80, steps: 5 },
  x1: { vary: true, value: 0.0, min: -0.3, max: 0.6, steps: 10 },
  x2: { vary: false, value: 0.0, min: -0.3, max: 0.6, steps: 5 },
  beta_deg: { vary: false, value: 0.0, min: 0.0, max: 25.0, steps: 4 },
  b: { vary: false, value: 20.0, min: 10.0, max: 40.0, steps: 4 },
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
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async () => {
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.variation(r));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  const setSpec = (key: ParamKey, patch: Partial<VarSpec>) =>
    setR({ ...r, [key]: { ...r[key], ...patch } });
  const set = (k: keyof VariationRequest) => (v: number) => setR({ ...r, [k]: v });

  const perSec = res && res.eval_ms > 0 ? (res.count / res.eval_ms) * 1000 : 0;
  const rows = res
    ? [...res.points]
        .sort((a, b) => (b.root_safety_wheel ?? -1) - (a.root_safety_wheel ?? -1))
        .slice(0, 60)
    : [];

  return (
    <>
      <p className="page-intro">
        Kunststofftaugliche Makrogeometrie-Variation (Stahlritzel + Kunststoffrad) — der
        vektorisierte Kernel mit Frühausschluss, Sobol/LHS-Sampling und Pareto-Front. Genau das, was
        die FVA-Workbench-Stufenvariation mit einem Kunststoffrad nicht kann.
      </p>
      <div className="split">
        <div className="stack" style={{ gap: 0 }}>
          <Card>
            <CardHead title="Variations-Matrix" sub="Pro Parameter: variieren (Min/Max/Schritte) oder fest" />
            <div className="card-pad">
              <div className="table-wrap">
                <table className="tbl tbl-compact">
                  <thead>
                    <tr>
                      <th>Parameter</th>
                      <th>Var.</th>
                      <th>Wert / Min</th>
                      <th>Max</th>
                      <th>Schritte</th>
                    </tr>
                  </thead>
                  <tbody>
                    {PARAMS.map((p) => {
                      const s = r[p.key];
                      return (
                        <tr key={p.key}>
                          <td className="txt">
                            {p.label} <span className="muted">{p.unit !== "—" ? p.unit : ""}</span>
                          </td>
                          <td style={{ textAlign: "center" }}>
                            <input
                              type="checkbox"
                              checked={s.vary}
                              onChange={(e) => setSpec(p.key, { vary: e.target.checked })}
                            />
                          </td>
                          <td>
                            <MiniInput
                              value={s.vary ? s.min : s.value}
                              onChange={(v) => setSpec(p.key, s.vary ? { min: v } : { value: v })}
                            />
                          </td>
                          <td>
                            <MiniInput disabled={!s.vary} value={s.max} onChange={(v) => setSpec(p.key, { max: v })} />
                          </td>
                          <td>
                            <MiniInput disabled={!s.vary} value={s.steps} step={1} onChange={(v) => setSpec(p.key, { steps: v })} />
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
                    foot={perSec > 0 ? `${Math.round(perSec).toLocaleString("de-DE")} Varianten/s` : undefined} />
                </Card>
              </div>
              {res.warnings.map((w, i) => <div className="note" key={i}>⚠ {w}</div>)}
              <Card>
                <CardHead title="Top-Varianten" sub="nach Kunststoff-Fußsicherheit · ★ = Pareto-optimal (max S_F, S_H, ε_γ)" />
                <div className="table-wrap">
                  <table className="tbl tbl-compact">
                    <thead>
                      <tr>
                        <th></th>
                        <th>z₁</th>
                        <th>z₂</th>
                        <th>x₁</th>
                        <th>m_n</th>
                        <th>a</th>
                        <th>ε_γ</th>
                        <th>S_F Rad</th>
                        <th>S_H Rad</th>
                        <th>Gew.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((p, i) => (
                        <tr key={i} className={p.pareto ? "row-hi" : ""}>
                          <td>{p.pareto ? "★" : ""}</td>
                          <td>{fmt(p.z1, 0)}</td>
                          <td>{fmt(p.z2, 0)}</td>
                          <td>{fmt(p.x1, 3)}</td>
                          <td>{fmt(p.m_n, 2)}</td>
                          <td>{fmt(p.center_distance_mm, 1)}</td>
                          <td>{fmt(p.total_contact_ratio, 3)}</td>
                          <td><SBadge value={p.root_safety_wheel} min={r.root_minimum_safety} /></td>
                          <td><SBadge value={p.flank_safety_wheel} min={r.flank_minimum_safety} /></td>
                          <td>{fmt(p.weight_g, 0)} g</td>
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
                  Variationsraum festlegen und Stufenvariation starten, um die Pareto-Front zu sehen.
                </div>
              </Card>
            )
          )}
        </div>
      </div>
    </>
  );
}

function MiniInput(props: {
  value: number;
  onChange: (v: number) => void;
  step?: number;
  disabled?: boolean;
}): JSX.Element {
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

// local Stat (de-DE) to avoid importing the shared one twice
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
