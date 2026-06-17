import { useState, type JSX } from "react";
import { api, type VariationRequest, type VariationResponse } from "../lib/api";
import { fmt, safetyVerdict } from "../lib/format";
import { Badge, Button, Card, CardHead, NumberField, Stat, Tabs } from "../components/ui";

const DEFAULTS: VariationRequest = {
  normal_module_mm: 2.0,
  teeth_wheel: 60,
  profile_shift_wheel: 0.0,
  torque_nm: 15.0,
  teeth_pinion_min: 16,
  teeth_pinion_max: 34,
  teeth_pinion_steps: 19,
  profile_shift_pinion_min: -0.3,
  profile_shift_pinion_max: 0.6,
  profile_shift_pinion_steps: 10,
  face_width_mm: 20,
  method: "grid",
  sample_count: 256,
};

export function VariationView(): JSX.Element {
  const [req, setReq] = useState<VariationRequest>(DEFAULTS);
  const [res, setRes] = useState<VariationResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async () => {
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.variation(req));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  const set = (k: keyof VariationRequest) => (v: number) => setReq({ ...req, [k]: v });

  const perSec = res && res.eval_ms > 0 ? (res.count / res.eval_ms) * 1000 : 0;
  const rows = res
    ? [...res.points].sort((a, b) => (b.root_safety_plastic ?? -1) - (a.root_safety_plastic ?? -1)).slice(0, 40)
    : [];

  return (
    <>
      <p className="page-intro">
        Plastic-capable macro-geometry sweep (steel pinion + plastic wheel) — the vectorized kernel
        with early pruning, Sobol/LHS sampling and a Pareto front. This is what the FVA-Workbench
        Stufenvariation cannot do with a plastic gear.
      </p>
      <div className="split">
        <Card>
          <CardHead title="Design space" sub="Fixed wheel + swept pinion" />
          <div className="card-pad">
            <div className="input-row">
              <NumberField label="Module m_n" value={req.normal_module_mm} onChange={set("normal_module_mm")} hint="mm" />
              <NumberField label="Wheel z₂" value={req.teeth_wheel} onChange={set("teeth_wheel")} step={1} />
            </div>
            <div className="input-row">
              <NumberField label="Wheel x₂" value={req.profile_shift_wheel} onChange={set("profile_shift_wheel")} />
              <NumberField label="Torque T₁" value={req.torque_nm} onChange={set("torque_nm")} hint="N·m" />
            </div>
            <NumberField label="Face width b" value={req.face_width_mm} onChange={set("face_width_mm")} hint="mm" />

            <div className="eyebrow" style={{ margin: "10px 0 12px" }}>Swept: pinion teeth z₁</div>
            <div className="input-row">
              <NumberField label="min" value={req.teeth_pinion_min} onChange={set("teeth_pinion_min")} step={1} />
              <NumberField label="max" value={req.teeth_pinion_max} onChange={set("teeth_pinion_max")} step={1} />
            </div>
            <NumberField label="steps" value={req.teeth_pinion_steps} onChange={set("teeth_pinion_steps")} step={1} />

            <div className="eyebrow" style={{ margin: "10px 0 12px" }}>Swept: pinion shift x₁</div>
            <div className="input-row">
              <NumberField label="min" value={req.profile_shift_pinion_min} onChange={set("profile_shift_pinion_min")} />
              <NumberField label="max" value={req.profile_shift_pinion_max} onChange={set("profile_shift_pinion_max")} />
            </div>
            <NumberField label="steps" value={req.profile_shift_pinion_steps} onChange={set("profile_shift_pinion_steps")} step={1} />

            <div className="field">
              <span className="field-label">Sampling</span>
              <Tabs
                value={req.method}
                onChange={(m) => setReq({ ...req, method: m })}
                options={[
                  { value: "grid", label: "Grid" },
                  { value: "sobol", label: "Sobol" },
                  { value: "lhs", label: "LHS" },
                ]}
              />
            </div>
            {req.method !== "grid" && (
              <NumberField label="Sample count" value={req.sample_count} onChange={set("sample_count")} step={1} />
            )}
            <Button onClick={run} busy={busy}>
              Run Stufenvariation
            </Button>
          </div>
        </Card>

        <div className="stack" style={{ gap: 18 }}>
          {err && <div className="note">⚠ {err}</div>}
          {res && (
            <>
              <div className="grid cols-4">
                <Card><Stat label="Variants" value={res.count.toLocaleString()} /></Card>
                <Card><Stat label="Valid (pruned)" value={res.valid.toLocaleString()} /></Card>
                <Card><Stat label="Pareto-optimal" value={res.pareto.toLocaleString()} /></Card>
                <Card><Stat label="Evaluation" value={fmt(res.eval_ms, 1)} unit="ms"
                  foot={perSec > 0 ? `${Math.round(perSec).toLocaleString()} variants/s` : undefined} /></Card>
              </div>
              {res.warnings.map((w, i) => <div className="note" key={i}>⚠ {w}</div>)}
              <Card>
                <CardHead title="Top variants" sub="By plastic root safety · ★ = Pareto-optimal (max S_F, S_H, ε_γ)" />
                <div className="table-wrap">
                  <table className="tbl">
                    <thead>
                      <tr><th></th><th>z₁</th><th>x₁</th><th>ε_γ</th><th>S_F (plastic)</th><th>S_H (plastic)</th></tr>
                    </thead>
                    <tbody>
                      {rows.map((p, i) => (
                        <tr key={i} className={p.pareto ? "row-hi" : ""}>
                          <td>{p.pareto ? "★" : ""}</td>
                          <td>{fmt(p.teeth_pinion, 0)}</td>
                          <td>{fmt(p.profile_shift_pinion, 3)}</td>
                          <td>{fmt(p.total_contact_ratio, 3)}</td>
                          <td><Badge variant={badge(p.root_safety_plastic, 2.0)} dot>{fmt(p.root_safety_plastic, 2)}</Badge></td>
                          <td><Badge variant={badge(p.flank_safety_plastic, 1.0)} dot>{fmt(p.flank_safety_plastic, 2)}</Badge></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </>
          )}
          {!res && !err && (
            <Card>
              <div className="card-pad muted">Set the design space and run the sweep to see the Pareto front.</div>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}

function badge(value: number | null, min: number): string {
  return safetyVerdict(value, min);
}
