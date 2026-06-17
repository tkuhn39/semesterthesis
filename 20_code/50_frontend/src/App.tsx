import { useEffect, useState, type JSX } from "react";
import { Layout, type NavItem } from "./components/Layout";
import { Badge } from "./components/ui";
import { IconActivity, IconGauge, IconGear, IconGrid, IconOverview } from "./components/icons";
import { api } from "./lib/api";
import { OverviewView } from "./views/OverviewView";
import { GeometryView } from "./views/GeometryView";
import { CapacityView } from "./views/CapacityView";
import { DynamicsView } from "./views/DynamicsView";
import { VariationView } from "./views/VariationView";

const NAV: (NavItem & { title: string; eyebrow: string })[] = [
  { key: "overview", label: "Übersicht", icon: <IconOverview />, title: "Übersicht", eyebrow: "Geladenes Beispiel" },
  { key: "geometry", label: "Geometrie", icon: <IconGear />, title: "Makrogeometrie", eyebrow: "ISO 21771" },
  { key: "capacity", label: "Tragfähigkeit", icon: <IconGauge />, title: "Tragfähigkeit", eyebrow: "ISO 6336 · VDI 2736" },
  { key: "dynamics", label: "Dynamikfaktoren", icon: <IconActivity />, title: "Dynamikfaktoren", eyebrow: "ISO 6336-1" },
  { key: "variation", label: "Stufenvariation", icon: <IconGrid />, title: "Stufenvariation", eyebrow: "Makrogeometrie-Variation" },
];

export default function App(): JSX.Element {
  const [active, setActive] = useState("overview");
  const [version, setVersion] = useState<string | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .health()
      .then((h) => {
        setVersion(h.version);
        setOnline(true);
      })
      .catch(() => setOnline(false));
  }, []);

  const current = NAV.find((n) => n.key === active) ?? NAV[0];

  return (
    <Layout
      items={NAV}
      active={active}
      onSelect={setActive}
      title={current.title}
      eyebrow={current.eyebrow}
      topRight={<Badge variant="neutral" dot>Beispiel: kst-E</Badge>}
      footer={
        <div className="stack" style={{ gap: 4 }}>
          <span>
            {online == null ? "…" : online ? `Backend verbunden · v${version}` : "Backend offline"}
          </span>
          <span style={{ opacity: 0.7 }}>Kunststoff-Zahnfuß-Tool</span>
        </div>
      }
    >
      {active === "overview" && <OverviewView onNavigate={setActive} />}
      {active === "geometry" && <GeometryView />}
      {active === "capacity" && <CapacityView />}
      {active === "dynamics" && <DynamicsView />}
      {active === "variation" && <VariationView />}
    </Layout>
  );
}
