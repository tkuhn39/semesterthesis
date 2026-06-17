import type { JSX } from "react";
import { api, type ExampleResponse } from "../lib/api";
import { fmt } from "../lib/format";
import { Badge, Card, CardHead, Stat, useAsync } from "../components/ui";

export function OverviewView(props: { onNavigate: (key: string) => void }): JSX.Element {
  const { data, error, loading } = useAsync<ExampleResponse>(() => api.example());

  if (loading) return <Loading />;
  if (error || !data) return <ErrorNote message={error ?? "keine Daten"} />;

  return (
    <>
      <p className="page-intro">
        Die Analyse ist mit der validierten <strong>{data.name}</strong>-Referenz vorgeladen —{" "}
        {data.description} Passe die Betriebsparameter in jeder Ansicht an; das Stahlrad rechnet nach
        ISO 6336:2019, das Kunststoffrad nach VDI 2736:2014.
      </p>

      <div className="grid cols-4">
        <Card><Stat label="Gesamtüberdeckung ε_γ" value={fmt(data.total_contact_ratio, 3)} /></Card>
        <Card><Stat label="Betriebseingriffswinkel α_wt" value={fmt(data.working_pressure_angle_deg, 2)} unit="°" /></Card>
        <Card><Stat label="Achsabstand a" value={fmt(data.center_distance_mm, 2)} unit="mm" /></Card>
        <Card><Stat label="Normalmodul m_n" value={fmt(data.normal_module_mm, 2)} unit="mm" /></Card>
      </div>

      <div className="grid mt">
        <Card>
          <CardHead title="Verzahnungspaar" sub="Erzeugte Geometrie der geladenen Referenz" />
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Rad</th>
                  <th>Werkstoff</th>
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
            <div className="card-pad" style={{ paddingTop: 12 }}>
              {data.notes.map((n, i) => (
                <div className="note" key={i} style={{ marginBottom: 6 }}>
                  <span>⚠</span>
                  <span>{n}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="eyebrow mt" style={{ marginBottom: 8 }}>
        Methoden
      </div>
      <div className="grid cols-2">
        {METHODS.map((m) => (
          <button
            key={m.key}
            className="card card-pad"
            onClick={() => props.onNavigate(m.key)}
            style={{ textAlign: "left", cursor: "pointer", border: "1px solid var(--border)" }}
          >
            <div className="card-title" style={{ fontSize: 14 }}>
              {m.title}
            </div>
            <div className="muted" style={{ fontSize: 12.5, marginTop: 3 }}>
              {m.text}
            </div>
            <div className="eyebrow" style={{ marginTop: 9 }}>
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
    title: "Geometrie",
    text: "Evolventen-Makrogeometrie: Durchmesser, Betriebseingriffswinkel und Überdeckungen — der vektorisierte native Kernel (ISO 21771).",
    tag: "Geometrie öffnen",
  },
  {
    key: "capacity",
    title: "Tragfähigkeit",
    text: "Stahlritzel nach ISO 6336:2019, Kunststoffrad nach VDI 2736:2014 — Spannungen, Sicherheiten, Zahntemperatur, Verschleiß, Verformung.",
    tag: "Tragfähigkeit öffnen",
  },
  {
    key: "dynamics",
    title: "Dynamikfaktoren",
    text: "Native K_v (Verf. B), K_Hα und K_Hβ mit Eingriffssteifigkeit, reduzierter Masse und Resonanzverhältnis (ISO 6336-1).",
    tag: "Dynamik öffnen",
  },
  {
    key: "variation",
    title: "Stufenvariation",
    text: "Kunststofftaugliche Makrogeometrie-Variation mit Frühausschluss, Sobol/LHS-Sampling und Pareto-Front — Hunderttausende Varianten pro Sekunde.",
    tag: "Variation öffnen",
  },
];

export function Loading(): JSX.Element {
  return (
    <div className="row" style={{ color: "var(--text-muted)", padding: 20 }}>
      <span className="spinner" /> Lädt…
    </div>
  );
}
export function ErrorNote(props: { message: string }): JSX.Element {
  return (
    <div className="note bad">
      <span>⚠</span>
      <span>Backend-Fehler — läuft die API unter der konfigurierten URL? {props.message}</span>
    </div>
  );
}
