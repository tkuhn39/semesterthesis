import type { JSX } from "react";
import { api, type ExampleResponse } from "../lib/api";
import { fmt } from "../lib/format";
import { Badge, Card, CardHead, Stat, useAsync } from "../components/ui";

export function OverviewView(props: { onNavigate: (key: string) => void }): JSX.Element {
  const { data, error, loading } = useAsync<ExampleResponse>(() => api.example());

  if (loading) return <Loading />;
  if (error || !data) return <ErrorNote message={error ?? "no data"} />;

  return (
    <>
      <p className="page-intro">
        The analysis is preloaded with the validated <strong>{data.name}</strong> reference —{" "}
        {data.description} Edit the operating parameters in each view to recompute live; the steel
        gear runs on ISO 6336:2019, the plastic gear on VDI 2736:2014.
      </p>

      <div className="grid cols-4">
        <Card>
          <Stat label="Total contact ratio ε_γ" value={fmt(data.total_contact_ratio, 3)} />
        </Card>
        <Card>
          <Stat label="Working pressure angle α_wt" value={fmt(data.working_pressure_angle_deg, 2)} unit="°" />
        </Card>
        <Card>
          <Stat label="Centre distance a" value={fmt(data.center_distance_mm, 2)} unit="mm" />
        </Card>
        <Card>
          <Stat label="Normal module m_n" value={fmt(data.normal_module_mm, 2)} unit="mm" />
        </Card>
      </div>

      <div className="grid mt">
        <Card>
          <CardHead title="Gear pair" sub="As-cut geometry of the loaded reference" />
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Gear</th>
                  <th>Material</th>
                  <th>z</th>
                  <th>x</th>
                  <th>d</th>
                  <th>d_a</th>
                  <th>b</th>
                </tr>
              </thead>
              <tbody>
                {data.gears.map((g) => (
                  <tr key={g.role}>
                    <td className="txt">
                      <Badge variant={g.kind === "steel" ? "steel" : "plastic"}>{g.role}</Badge>
                    </td>
                    <td className="txt">{g.material}</td>
                    <td>{g.teeth}</td>
                    <td>{fmt(g.profile_shift, 4)}</td>
                    <td>{fmt(g.reference_diameter_mm, 3)}</td>
                    <td>{fmt(g.tip_diameter_mm, 3)}</td>
                    <td>{fmt(g.face_width_mm, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.notes.length > 0 && (
            <div className="card-pad" style={{ paddingTop: 14 }}>
              {data.notes.map((n, i) => (
                <div className="note" key={i} style={{ marginBottom: 8 }}>
                  <span>⚠</span>
                  <span>{n}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="eyebrow mt" style={{ marginBottom: 10 }}>
        Methods
      </div>
      <div className="grid cols-2">
        {METHODS.map((m) => (
          <button key={m.key} className="card card-pad method" onClick={() => props.onNavigate(m.key)}
            style={{ textAlign: "left", cursor: "pointer", border: "1px solid var(--border)" }}>
            <div className="card-title" style={{ fontFamily: "var(--font-serif)", fontSize: 17 }}>
              {m.title}
            </div>
            <div className="muted" style={{ fontSize: 13.5, marginTop: 4 }}>
              {m.text}
            </div>
            <div className="eyebrow" style={{ marginTop: 12 }}>
              {m.tag} →
            </div>
          </button>
        ))}
      </div>
    </>
  );
}

const METHODS = [
  {
    key: "geometry",
    title: "Geometry",
    text: "Involute macro-geometry: diameters, working pressure angle and contact ratios — the vectorized native kernel (ISO 21771).",
    tag: "Open geometry",
  },
  {
    key: "capacity",
    title: "Load capacity",
    text: "Steel pinion per ISO 6336:2019, plastic wheel per VDI 2736:2014 — stresses, safeties, tooth temperature, wear, deformation.",
    tag: "Open capacity",
  },
  {
    key: "dynamics",
    title: "Dynamic factors",
    text: "Native K_v (Method B), K_Hα and K_Hβ with the mesh stiffness, reduced mass and resonance ratio (ISO 6336-1).",
    tag: "Open dynamics",
  },
  {
    key: "variation",
    title: "Stufenvariation",
    text: "Plastic-capable macro-geometry sweep with early pruning, Sobol/LHS sampling and a Pareto front — hundreds of thousands of variants per second.",
    tag: "Open sweep",
  },
];

export function Loading(): JSX.Element {
  return (
    <div className="row" style={{ color: "var(--text-muted)", padding: 24 }}>
      <span className="spinner" /> Loading…
    </div>
  );
}
export function ErrorNote(props: { message: string }): JSX.Element {
  return (
    <div className="note" style={{ color: "var(--bad)", background: "var(--bad-bg)", borderColor: "#f3cab9" }}>
      <span>⚠</span>
      <span>Backend error — is the API running on the configured URL? {props.message}</span>
    </div>
  );
}
