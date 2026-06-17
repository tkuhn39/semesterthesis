import { useEffect, useState, type JSX } from "react";
import { api, type GeometryRequest, type GeometryResponse } from "../lib/api";
import { fmt } from "../lib/format";
import { Badge, Button, Card, CardHead, NumberField, Stat } from "../components/ui";

const DEFAULTS: GeometryRequest = {
  normal_module_mm: 1.0,
  teeth_pinion: 51,
  teeth_wheel: 52,
  profile_shift_pinion: 0.2034,
  profile_shift_wheel: 0.3143,
  normal_pressure_angle_deg: 20,
  helix_angle_deg: 0,
  face_width_mm: 17,
};

export function GeometryView(): JSX.Element {
  const [req, setReq] = useState<GeometryRequest>(DEFAULTS);
  const [res, setRes] = useState<GeometryResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async (r: GeometryRequest) => {
    setBusy(true);
    setErr(null);
    try {
      setRes(await api.geometry(r));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    void run(DEFAULTS);
  }, []);

  const set = (k: keyof GeometryRequest) => (v: number) => setReq({ ...req, [k]: v });

  return (
    <>
      <p className="page-intro">
        Native involute macro-geometry (ISO 21771) via the vectorized kernel. Tip diameters use the
        running addendum (no chamfer) — for the exact as-cut kst-E geometry see the Overview.
      </p>
      <div className="split">
        <Card>
          <CardHead title="Parameters" sub="Edit and recompute" />
          <div className="card-pad">
            <div className="input-row">
              <NumberField label="Normal module m_n" value={req.normal_module_mm} onChange={set("normal_module_mm")}
                hint={<>mm · STplus <code>MODUL</code></>} />
              <NumberField label="Pressure angle α_n" value={req.normal_pressure_angle_deg}
                onChange={set("normal_pressure_angle_deg")} hint={<>° · <code>EINGRIFFSWINKEL</code></>} />
            </div>
            <div className="input-row">
              <NumberField label="Teeth z₁ (pinion)" value={req.teeth_pinion} onChange={set("teeth_pinion")}
                step={1} hint={<>STplus <code>ZAEHNEZAHL</code></>} />
              <NumberField label="Teeth z₂ (wheel)" value={req.teeth_wheel} onChange={set("teeth_wheel")} step={1} />
            </div>
            <div className="input-row">
              <NumberField label="Profile shift x₁" value={req.profile_shift_pinion}
                onChange={set("profile_shift_pinion")} hint={<>STplus <code>PROFILVERSCHIEBUNG</code></>} />
              <NumberField label="Profile shift x₂" value={req.profile_shift_wheel}
                onChange={set("profile_shift_wheel")} />
            </div>
            <div className="input-row">
              <NumberField label="Helix angle β" value={req.helix_angle_deg} onChange={set("helix_angle_deg")}
                hint="° · 0 = spur" />
              <NumberField label="Face width b" value={req.face_width_mm} onChange={set("face_width_mm")} hint="mm" />
            </div>
            <Button onClick={() => run(req)} busy={busy}>
              Recompute geometry
            </Button>
          </div>
        </Card>

        <div className="stack" style={{ gap: 18 }}>
          {err && <div className="note">⚠ {err}</div>}
          {res && (
            <>
              <div className="grid cols-3">
                <Card>
                  <Stat label="Transverse ε_α" value={fmt(res.transverse_contact_ratio, 3)}
                    foot={res.valid ? <Badge variant="good" dot>continuous</Badge> : <Badge variant="bad" dot>ε_γ &lt; 1</Badge>} />
                </Card>
                <Card>
                  <Stat label="Overlap ε_β" value={fmt(res.overlap_ratio, 3)} />
                </Card>
                <Card>
                  <Stat label="Total ε_γ" value={fmt(res.total_contact_ratio, 3)} />
                </Card>
              </div>
              <Card>
                <CardHead title="Diameters & mesh" right={<span className="muted num">α_wt {fmt(res.working_pressure_angle_deg, 3)}°</span>} />
                <div className="table-wrap">
                  <table className="tbl">
                    <thead>
                      <tr><th>Quantity</th><th>Pinion</th><th>Wheel</th><th>Unit</th></tr>
                    </thead>
                    <tbody>
                      <Row name="Reference diameter d" a={res.reference_diameter_mm[0]} b={res.reference_diameter_mm[1]} />
                      <Row name="Base diameter d_b" a={res.base_diameter_mm[0]} b={res.base_diameter_mm[1]} />
                      <Row name="Tip diameter d_a" a={res.tip_diameter_mm[0]} b={res.tip_diameter_mm[1]} />
                      <tr>
                        <td className="txt">Working centre distance a_w</td>
                        <td colSpan={2}>{fmt(res.working_center_distance_mm, 3)}</td>
                        <td className="txt muted">mm</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </Card>
              {res.notes.map((n, i) => (
                <div className="note" key={i}>⚠ {n}</div>
              ))}
            </>
          )}
        </div>
      </div>
    </>
  );
}

function Row(props: { name: string; a: number; b: number }): JSX.Element {
  return (
    <tr>
      <td className="txt">{props.name}</td>
      <td>{fmt(props.a, 3)}</td>
      <td>{fmt(props.b, 3)}</td>
      <td className="txt muted">mm</td>
    </tr>
  );
}
