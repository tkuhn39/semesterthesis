import { useEffect, useState, type JSX } from "react";
import { api, type CapacityRequest, type CapacityResponse, type GearCapacity } from "../lib/api";
import { fmt } from "../lib/format";
import { Badge, Button, Card, CardHead, NumberField, SafetyBadge } from "../components/ui";

const DEFAULTS: CapacityRequest = {
  pinion_torque_nm: 7.85,
  application_factor: 1.0,
  power_w: 1848.7,
  ambient_temperature_c: 80,
  friction_coefficient: 0.04,
  load_cycles: 1.324e7,
};

export function CapacityView(): JSX.Element {
  const [req, setReq] = useState<CapacityRequest>(DEFAULTS);
  const [res, setRes] = useState<CapacityResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async (r: CapacityRequest) => {
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.capacity(r));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    void run(DEFAULTS);
  }, []);
  const set = (k: keyof CapacityRequest) => (v: number) => setReq({ ...req, [k]: v });

  return (
    <>
      <p className="page-intro">
        Per-gear material dispatch over the shared mesh: the steel pinion on ISO 6336:2019, the
        plastic wheel on VDI 2736:2014. Safeties compare against S_min (root 1.4 steel / 2.0 plastic,
        flank 1.0).
      </p>
      <div className="split">
        <Card>
          <CardHead title="Operating point" sub="kst-E reference, editable" />
          <div className="card-pad">
            <div className="input-row">
              <NumberField label="Pinion torque T₁" value={req.pinion_torque_nm} onChange={set("pinion_torque_nm")}
                hint="N·m" />
              <NumberField label="Application factor K_A" value={req.application_factor}
                onChange={set("application_factor")} hint="DIN 3990" />
            </div>
            <div className="eyebrow" style={{ margin: "8px 0 12px" }}>VDI 2736 — plastic / thermal</div>
            <div className="input-row">
              <NumberField label="Rolling power P" value={req.power_w} onChange={set("power_w")} hint="W" />
              <NumberField label="Ambient ϑ₀" value={req.ambient_temperature_c}
                onChange={set("ambient_temperature_c")} hint="°C" />
            </div>
            <div className="input-row">
              <NumberField label="Friction μ" value={req.friction_coefficient} onChange={set("friction_coefficient")}
                hint="VDI 2736 Tab. 1" />
              <NumberField label="Load cycles N_L" value={req.load_cycles} onChange={set("load_cycles")} hint="—" />
            </div>
            <Button onClick={() => run(req)} busy={busy}>
              Evaluate capacity
            </Button>
          </div>
        </Card>

        <div className="grid cols-2">
          {err && <div className="note">⚠ {err}</div>}
          {res && (
            <>
              <GearCard gear={res.pinion} rootMin={1.4} />
              <GearCard gear={res.wheel} rootMin={2.0} />
            </>
          )}
        </div>
      </div>
    </>
  );
}

function GearCard(props: { gear: GearCapacity; rootMin: number }): JSX.Element {
  const g = props.gear;
  const plastic = g.tooth_temperature_c != null;
  return (
    <Card>
      <CardHead
        title={g.label}
        sub={g.material}
        right={<Badge variant={plastic ? "plastic" : "steel"}>{g.method}</Badge>}
      />
      <div className="card-pad stack" style={{ gap: 0 }}>
        <Line label="Flank stress σ_H" value={`${fmt(g.flank_stress_mpa, 2)} N/mm²`} badge={<SafetyBadge value={g.flank_safety} minimum={1.0} />} />
        <Line label="Root stress σ_F" value={`${fmt(g.root_stress_mpa, 2)} N/mm²`} badge={<SafetyBadge value={g.root_safety} minimum={props.rootMin} />} />
        <Line label={plastic ? "Form factor Y_Fa" : "Form factor Y_F"} value={fmt(g.form_factor, 3)} />
        <Line label={plastic ? "Stress correction Y_Sa" : "Stress correction Y_S"} value={fmt(g.stress_correction, 3)} />
        {plastic && (
          <>
            <div className="eyebrow" style={{ margin: "14px 0 6px" }}>Thermal · wear · deformation</div>
            <Line label="Tooth temperature ϑ" value={`${fmt(g.tooth_temperature_c, 2)} °C`} />
            <Line label="Linear wear W_m"
              value={`${fmt(g.wear_um, 2)} µm`}
              badge={<Badge variant={(g.wear_um ?? 0) <= (g.allowable_wear_um ?? Infinity) ? "good" : "bad"} dot>
                ≤ {fmt(g.allowable_wear_um, 0)} µm
              </Badge>} />
            <Line label="Tooth deformation λ" value={`${fmt(g.deformation_mm, 4)} mm`} />
          </>
        )}
      </div>
    </Card>
  );
}

function Line(props: { label: string; value: string; badge?: JSX.Element }): JSX.Element {
  return (
    <div className="row between" style={{ padding: "9px 0", borderBottom: "1px solid var(--border)" }}>
      <span className="muted" style={{ fontSize: 13.5 }}>{props.label}</span>
      <span className="row" style={{ gap: 10 }}>
        <span className="num">{props.value}</span>
        {props.badge}
      </span>
    </div>
  );
}
