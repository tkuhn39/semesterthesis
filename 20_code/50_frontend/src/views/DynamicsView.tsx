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

const REGIME_DE: Record<string, string> = {
  "sub-critical": "unterkritisch",
  "main resonance": "Hauptresonanz",
  "super-critical": "überkritisch",
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
        Nativer ISO-6336-1-Dynamikfaktor K_v (Verfahren B) sowie Stirn- und Breitenfaktor. Das
        Resonanzverhältnis N = n₁/n_E1 ordnet die Drehzahl der Hauptresonanz zu — der weiche
        Kunststoff-Eingriff senkt c_γα und verschiebt N.
      </p>
      <div className="split">
        <Card>
          <CardHead title="Betrieb & Qualität" sub="kst-E-Referenz, editierbar" />
          <div className="card-pad">
            <div className="input-row">
              <NumberField label="Ritzeldrehzahl n₁" value={req.pinion_speed_min1} onChange={set("pinion_speed_min1")} hint="min⁻¹" />
              <NumberField label="Ritzelmoment T₁" value={req.pinion_torque_nm} onChange={set("pinion_torque_nm")} hint="N·m" />
            </div>
            <NumberField label="Anwendungsfaktor K_A" value={req.application_factor} onChange={set("application_factor")} />
            <div className="eyebrow" style={{ margin: "8px 0 10px" }}>Verzahnungsqualität (ISO 1328)</div>
            <div className="input-row">
              <NumberField label="Eingriffsteilungs-Abw. f_pb" value={req.base_pitch_deviation_um} onChange={set("base_pitch_deviation_um")} hint="µm" />
              <NumberField label="Profilform-Abw. f_fα" value={req.profile_form_deviation_um} onChange={set("profile_form_deviation_um")} hint="µm" />
            </div>
            <Button onClick={() => run(req)} busy={busy}>
              Dynamik berechnen
            </Button>
          </div>
        </Card>

        <div className="stack" style={{ gap: 12 }}>
          {err && <div className="note bad">⚠ {err}</div>}
          {res && (
            <>
              <div className="grid cols-3">
                <Card><Stat label="Dynamikfaktor K_v" value={fmt(res.dynamic_factor, 3)} /></Card>
                <Card><Stat label="Stirnfaktor K_Hα" value={fmt(res.transverse_factor_flank, 3)} /></Card>
                <Card><Stat label="Breitenfaktor K_Hβ" value={fmt(res.face_load_factor_flank, 3)} /></Card>
              </div>
              <Card>
                <CardHead title="Resonanz-Diagnostik"
                  right={<Badge variant={regimeVariant} dot>{REGIME_DE[res.regime] ?? res.regime}</Badge>} />
                <div className="card-pad">
                  <div className="grid cols-2" style={{ gap: 10 }}>
                    <Stat label="Eingriffssteifigkeit c_γα" value={fmt(res.mesh_stiffness, 3)} unit="N/(mm·µm)" />
                    <Stat label="Reduzierte Masse m_red" value={fmt(res.reduced_mass, 5)} unit="kg/mm" />
                    <Stat label="Resonanzdrehzahl n_E1" value={fmt(res.resonance_speed_min1, 0)} unit="min⁻¹" />
                    <Stat label="Resonanzverhältnis N" value={fmt(res.resonance_ratio, 3)} />
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
    <div style={{ marginTop: 14 }}>
      <div style={{ position: "relative", height: 7, borderRadius: 999, overflow: "hidden", background: "linear-gradient(90deg,var(--good-bg) 0% 53%,var(--bad-bg) 53% 72%,var(--warn-bg) 72% 100%)" }}>
        <div style={{ position: "absolute", left: `calc(${pos}% - 6px)`, top: -3, width: 12, height: 12, borderRadius: 999, background: "var(--tum-blue)", border: "2px solid #fff", boxShadow: "var(--shadow-sm)" }} />
      </div>
      <div className="row between muted" style={{ fontSize: 10.5, marginTop: 4 }}>
        <span>unterkritisch</span>
        <span>Resonanz (N≈1)</span>
        <span>überkritisch</span>
      </div>
    </div>
  );
}
