import { useEffect, useState, type JSX } from "react";
import { api, type CapacityRequest, type CapacityResponse, type GearCapacity } from "../lib/api";
import { fmt } from "../lib/format";
import {
  Badge,
  Button,
  Card,
  CardHead,
  NumberField,
  PairRow,
  SafetyBadge,
  Section,
  SelectField,
} from "../components/ui";

const DEFAULTS: CapacityRequest = {
  pinion_torque_nm: 7.85,
  pinion_speed_min1: 1000,
  application_factor: 1.0,
  compute_dynamics: true,
  dynamic_factor: 1.0,
  face_load_factor: 1.0,
  base_pitch_deviation_um: 6.0,
  profile_form_deviation_um: 5.0,
  lubricant_viscosity_40_mm2s: 100,
  flank_roughness_rz_um: 5.0,
  root_roughness_rz_um: 20.0,
  flank_life_factor: 1.0,
  root_life_factor: 1.0,
  steel_modulus_mpa: 210000,
  steel_poisson: 0.3,
  steel_sigma_hlim_mpa: 1500,
  steel_sigma_flim_mpa: 430,
  power_w: 1848.7,
  ambient_temperature_c: 80,
  duty_cycle: 1.0,
  housing_surface_m2: 0.01,
  friction_coefficient: 0.04,
  wear_coefficient_e6: 1.0,
  load_cycles: 1.324e7,
  root_minimum_safety: 2.0,
  flank_minimum_safety: 1.4,
  plastic_modulus_mpa: 4156,
  plastic_poisson: 0.34,
  plastic_sigma_hlim_mpa: 60,
  plastic_sigma_flim_mpa: 35,
};

export function CapacityView(): JSX.Element {
  const [r, setR] = useState<CapacityRequest>(DEFAULTS);
  const [res, setRes] = useState<CapacityResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async (req: CapacityRequest) => {
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.capacity(req));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    void run(DEFAULTS);
  }, []);
  const set = (k: keyof CapacityRequest) => (v: number) => setR({ ...r, [k]: v });

  return (
    <>
      <p className="page-intro">
        Aufteilung je Rad über den gemeinsamen Eingriff: Stahlritzel nach{" "}
        <strong>ISO 6336:2019</strong>, Kunststoffrad nach <strong>VDI 2736:2014</strong>. Geometrie
        = die geladene kst-E-Referenz; Betriebs-, Werkstoff-, Qualitäts- und Faktor-Eingaben sind
        editierbar.
      </p>
      <div className="split">
        <div className="stack" style={{ gap: 0 }}>
          <Card>
            <CardHead title="Eingaben" sub="kst-E-Referenz — alle Betriebswerte editierbar" />
            <div className="card-pad">
              <Section title="Last & Anwendung">
                <div className="input-row">
                  <NumberField label="Ritzelmoment T₁" value={r.pinion_torque_nm} onChange={set("pinion_torque_nm")} hint="N·m" />
                  <NumberField label="Ritzeldrehzahl n₁" value={r.pinion_speed_min1} onChange={set("pinion_speed_min1")} hint="min⁻¹" />
                </div>
                <NumberField label="Anwendungsfaktor K_A" value={r.application_factor} onChange={set("application_factor")} hint="DIN 3990" />
                <SelectField
                  label="Dynamikfaktor K_v"
                  value={r.compute_dynamics ? "auto" : "manual"}
                  options={[
                    { value: "auto", label: "Nativ (ISO 6336-1, Verf. B)" },
                    { value: "manual", label: "Manuell vorgeben" },
                  ]}
                  onChange={(v) => setR({ ...r, compute_dynamics: v === "auto" })}
                />
                {!r.compute_dynamics && (
                  <NumberField label="K_v (manuell)" value={r.dynamic_factor} onChange={set("dynamic_factor")} />
                )}
                <NumberField label="Breitenfaktor K_Hβ" value={r.face_load_factor} onChange={set("face_load_factor")} hint="aus RIKOR; 1,0 ideal" />
              </Section>

              <Section title="Verzahnungsqualität (ISO 1328)" defaultOpen={false}>
                <div className="input-row">
                  <NumberField label="Eingriffsteilungs-Abw. f_pb" value={r.base_pitch_deviation_um} onChange={set("base_pitch_deviation_um")} hint="µm" />
                  <NumberField label="Profilform-Abw. f_fα" value={r.profile_form_deviation_um} onChange={set("profile_form_deviation_um")} hint="µm" />
                </div>
              </Section>

              <Section title="ISO 6336 — Bedingungen" defaultOpen={false}>
                <div className="input-row">
                  <NumberField label="Schmierstoff ν₄₀" value={r.lubricant_viscosity_40_mm2s} onChange={set("lubricant_viscosity_40_mm2s")} hint="mm²/s" />
                  <NumberField label="Flankenrauheit R_zH" value={r.flank_roughness_rz_um} onChange={set("flank_roughness_rz_um")} hint="µm" />
                </div>
                <div className="input-row">
                  <NumberField label="Fußrauheit R_zF" value={r.root_roughness_rz_um} onChange={set("root_roughness_rz_um")} hint="µm" />
                  <NumberField label="Flanken-Lebensd. Z_NT" value={r.flank_life_factor} onChange={set("flank_life_factor")} />
                </div>
                <NumberField label="Fuß-Lebensd. Y_NT" value={r.root_life_factor} onChange={set("root_life_factor")} />
              </Section>

              <Section title="Werkstoff (Stahl / Kunststoff)" defaultOpen={false}>
                <div className="pair-head">
                  <span>Größe</span>
                  <span>Stahl</span>
                  <span>Kunststoff</span>
                </div>
                <PairRow label={<>E <code>N/mm²</code></>} pinion={r.steel_modulus_mpa} wheel={r.plastic_modulus_mpa}
                  onPinion={set("steel_modulus_mpa")} onWheel={set("plastic_modulus_mpa")} />
                <PairRow label={<>ν</>} pinion={r.steel_poisson} wheel={r.plastic_poisson}
                  onPinion={set("steel_poisson")} onWheel={set("plastic_poisson")} />
                <PairRow label={<>σ_Hlim <code>N/mm²</code></>} pinion={r.steel_sigma_hlim_mpa} wheel={r.plastic_sigma_hlim_mpa}
                  onPinion={set("steel_sigma_hlim_mpa")} onWheel={set("plastic_sigma_hlim_mpa")} />
                <PairRow label={<>σ_Flim <code>N/mm²</code></>} pinion={r.steel_sigma_flim_mpa} wheel={r.plastic_sigma_flim_mpa}
                  onPinion={set("steel_sigma_flim_mpa")} onWheel={set("plastic_sigma_flim_mpa")} />
              </Section>

              <Section title="VDI 2736 — Thermik · Verschleiß · Sicherheit" defaultOpen={false}>
                <div className="input-row">
                  <NumberField label="Wälzleistung P" value={r.power_w} onChange={set("power_w")} hint="W" />
                  <NumberField label="Umgebung ϑ₀" value={r.ambient_temperature_c} onChange={set("ambient_temperature_c")} hint="°C" />
                </div>
                <div className="input-row">
                  <NumberField label="Einschaltdauer ED" value={r.duty_cycle} onChange={set("duty_cycle")} />
                  <NumberField label="Gehäusefläche A_G" value={r.housing_surface_m2} onChange={set("housing_surface_m2")} hint="m²" />
                </div>
                <div className="input-row">
                  <NumberField label="Reibung μ" value={r.friction_coefficient} onChange={set("friction_coefficient")} />
                  <NumberField label="Verschleiß k_W ·10⁻⁶" value={r.wear_coefficient_e6} onChange={set("wear_coefficient_e6")} hint="mm³/(N·m)" />
                </div>
                <NumberField label="Lastwechsel N_L" value={r.load_cycles} onChange={set("load_cycles")} />
                <div className="input-row">
                  <NumberField label="S_Fmin (Fuß)" value={r.root_minimum_safety} onChange={set("root_minimum_safety")} />
                  <NumberField label="S_Hmin (Flanke)" value={r.flank_minimum_safety} onChange={set("flank_minimum_safety")} />
                </div>
              </Section>

              <Button onClick={() => run(r)} busy={busy}>
                Tragfähigkeit berechnen
              </Button>
            </div>
          </Card>
        </div>

        <div className="stack" style={{ gap: 12 }}>
          {err && <div className="note bad">⚠ {err}</div>}
          {res && (
            <>
              <Card>
                <CardHead title="Last- & Geometriefaktoren" />
                <div className="card-pad grid cols-3" style={{ gap: 8 }}>
                  <Fac label="K_A" v={res.factors.application_factor} />
                  <Fac label="K_v" v={res.factors.dynamic_factor} />
                  <Fac label="K_Hα" v={res.factors.transverse_factor} />
                  <Fac label="K_Hβ" v={res.factors.face_load_factor} />
                  <Fac label="Z_E" v={res.factors.elasticity_factor} />
                  <Fac label="Z_H" v={res.factors.zone_factor} />
                </div>
              </Card>
              <div className="grid cols-2">
                <GearCard gear={res.pinion} rootMin={r.root_minimum_safety} flankMin={r.flank_minimum_safety} />
                <GearCard gear={res.wheel} rootMin={r.root_minimum_safety} flankMin={r.flank_minimum_safety} />
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

function Fac(props: { label: string; v: number }): JSX.Element {
  return (
    <div className="kv" style={{ borderBottom: "none", padding: "3px 0" }}>
      <span className="k">{props.label}</span>
      <span className="v num">{fmt(props.v, 3)}</span>
    </div>
  );
}

function GearCard(props: { gear: GearCapacity; rootMin: number; flankMin: number }): JSX.Element {
  const g = props.gear;
  const plastic = g.tooth_temperature_c != null;
  return (
    <Card>
      <CardHead title={g.label} sub={g.material} right={<Badge variant={plastic ? "plastic" : "steel"}>{g.method}</Badge>} />
      <div className="card-pad stack" style={{ gap: 0 }}>
        <Line label="σ_H (ist / zul)" value={`${fmt(g.flank_stress_mpa, 1)} / ${fmt(g.flank_permissible_mpa, 1)}`} unit="N/mm²" badge={<SafetyBadge value={g.flank_safety} minimum={props.flankMin} />} />
        <Line label="σ_F (ist / zul)" value={`${fmt(g.root_stress_mpa, 1)} / ${fmt(g.root_permissible_mpa, 1)}`} unit="N/mm²" badge={<SafetyBadge value={g.root_safety} minimum={props.rootMin} />} />
        <Line label={plastic ? "Y_Fa · Y_Sa" : "Y_F · Y_S"} value={`${fmt(g.form_factor, 3)} · ${fmt(g.stress_correction, 3)}`} />
        {plastic && (
          <>
            <Line label="Zahntemperatur ϑ" value={fmt(g.tooth_temperature_c, 1)} unit="°C" />
            <Line label="Verschleiß W_m (ist / zul)" value={`${fmt(g.wear_um, 1)} / ${fmt(g.allowable_wear_um, 0)}`} unit="µm"
              badge={<Badge variant={(g.wear_um ?? 0) <= (g.allowable_wear_um ?? Infinity) ? "good" : "bad"} dot>Verschleiß</Badge>} />
            <Line label="Verformung λ" value={fmt(g.deformation_mm, 4)} unit="mm" />
          </>
        )}
      </div>
    </Card>
  );
}

function Line(props: { label: string; value: string; unit?: string; badge?: JSX.Element }): JSX.Element {
  return (
    <div className="kv">
      <span className="k">{props.label}</span>
      <span className="v">
        <span className="num">
          {props.value}
          {props.unit && <span className="muted"> {props.unit}</span>}
        </span>
        {props.badge}
      </span>
    </div>
  );
}
