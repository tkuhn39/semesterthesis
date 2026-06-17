import { useEffect, useState, type JSX } from "react";
import { api, type DynamicsRequest, type DynamicsResponse } from "../lib/api";
import { fmt } from "../lib/format";
import { Badge, Button, Card, CardHead, NumberField, Stat } from "../components/ui";

const DEFAULTS: DynamicsRequest = {
  pinion_speed_min1: 1000,
  pinion_torque_nm: 7.85,
  application_factor: 1.0,
  base_pitch_deviation_um: 6.0,
  profile_form_deviation_um: 5.0,
};

export function DynamicsView(): JSX.Element {
  const [req, setReq] = useState<DynamicsRequest>(DEFAULTS);
  const [res, setRes] = useState<DynamicsResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async (r: DynamicsRequest) => {
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.dynamics(r));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    void run(DEFAULTS);
  }, []);
  const set = (k: keyof DynamicsRequest) => (v: number) => setReq({ ...req, [k]: v });

  const regimeVariant =
    res?.regime === "sub-critical" ? "good" : res?.regime === "main resonance" ? "bad" : "warn";

  return (
    <>
      <p className="page-intro">
        Native ISO 6336-1 internal dynamic factor K_v (Method B) plus the transverse and face load
        factors. The resonance ratio N = n₁/n_E1 places the running speed against the gear-pair main
        resonance — the soft plastic mesh lowers c_γα and shifts N.
      </p>
      <div className="split">
        <Card>
          <CardHead title="Operating & accuracy" sub="kst-E reference, editable" />
          <div className="card-pad">
            <div className="input-row">
              <NumberField label="Pinion speed n₁" value={req.pinion_speed_min1} onChange={set("pinion_speed_min1")}
                hint="min⁻¹" />
              <NumberField label="Pinion torque T₁" value={req.pinion_torque_nm} onChange={set("pinion_torque_nm")}
                hint="N·m" />
            </div>
            <NumberField label="Application factor K_A" value={req.application_factor} onChange={set("application_factor")} />
            <div className="eyebrow" style={{ margin: "8px 0 12px" }}>Gear accuracy (ISO 1328)</div>
            <div className="input-row">
              <NumberField label="Base pitch dev. f_pb" value={req.base_pitch_deviation_um}
                onChange={set("base_pitch_deviation_um")} hint="µm" />
              <NumberField label="Profile form dev. f_fα" value={req.profile_form_deviation_um}
                onChange={set("profile_form_deviation_um")} hint="µm" />
            </div>
            <Button onClick={() => run(req)} busy={busy}>
              Compute dynamics
            </Button>
          </div>
        </Card>

        <div className="stack" style={{ gap: 18 }}>
          {err && <div className="note">⚠ {err}</div>}
          {res && (
            <>
              <div className="grid cols-3">
                <Card><Stat label="Dynamic factor K_v" value={fmt(res.dynamic_factor, 3)} /></Card>
                <Card><Stat label="Transverse K_Hα" value={fmt(res.transverse_factor_flank, 3)} /></Card>
                <Card><Stat label="Face load K_Hβ" value={fmt(res.face_load_factor_flank, 3)} /></Card>
              </div>
              <Card>
                <CardHead title="Resonance diagnostics"
                  right={<Badge variant={regimeVariant} dot>{res.regime}</Badge>} />
                <div className="card-pad">
                  <div className="grid cols-2" style={{ gap: 14 }}>
                    <Stat label="Mesh stiffness c_γα" value={fmt(res.mesh_stiffness, 3)} unit="N/(mm·µm)" />
                    <Stat label="Reduced mass m_red" value={fmt(res.reduced_mass, 5)} unit="kg/mm" />
                    <Stat label="Resonance speed n_E1" value={fmt(res.resonance_speed_min1, 0)} unit="min⁻¹" />
                    <Stat label="Resonance ratio N" value={fmt(res.resonance_ratio, 3)} />
                  </div>
                  <ResonanceBar n={res.resonance_ratio} />
                </div>
              </Card>
            </>
          )}
        </div>
      </div>
    </>
  );
}

function ResonanceBar(props: { n: number }): JSX.Element {
  const pos = Math.max(0, Math.min(1, props.n / 1.6)) * 100;
  return (
    <div style={{ marginTop: 18 }}>
      <div style={{ position: "relative", height: 8, borderRadius: 999, overflow: "hidden", background: "linear-gradient(90deg,var(--good-bg) 0% 53%,var(--bad-bg) 53% 72%,var(--warn-bg) 72% 100%)" }}>
        <div style={{ position: "absolute", left: `calc(${pos}% - 7px)`, top: -3, width: 14, height: 14, borderRadius: 999, background: "var(--tum-blue)", border: "2px solid #fff", boxShadow: "var(--shadow-sm)" }} />
      </div>
      <div className="row between muted" style={{ fontSize: 11, marginTop: 5 }}>
        <span>sub-critical</span>
        <span>resonance (N≈1)</span>
        <span>super-critical</span>
      </div>
    </div>
  );
}
