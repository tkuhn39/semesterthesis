"use client";

// The workbench shell (plan v2 D2): FVA-Workbench layout language, modernised — model tree
// left, tabbed editor centre (condensed attribute tables), messages strip bottom, language
// switch + backend status in the header. Panels own their result areas (quick-view style).

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "@/lib/api";
import { LocaleProvider, useLocale, useT } from "@/lib/i18n";
import { StageProvider, useStage } from "@/lib/stage";
import { GeometryPanel } from "@/panels/GeometryPanel";
import { MeshPanel } from "@/panels/MeshPanel";
import { ToothFormPanel } from "@/panels/ToothFormPanel";
import { VariationPanel } from "@/panels/VariationPanel";
import { OverviewPanel } from "@/panels/OverviewPanel";
import { DesignPanel } from "@/panels/DesignPanel";
import { CapacityPanel } from "@/panels/CapacityPanel";
import { DynamicsPanel } from "@/panels/DynamicsPanel";
import { PairPanel } from "@/panels/PairPanel";
import { GlossaryPanel } from "@/panels/GlossaryPanel";

type NodeKey =
  | "overview"
  | "design"
  | "geometry"
  | "capacity"
  | "dynamics"
  | "variation"
  | "pinion.toothform"
  | "pinion.mesh"
  | "wheel.toothform"
  | "wheel.mesh"
  | "deck"
  | "glossary";

interface TreeNode {
  key?: NodeKey;
  labelKey: string;
  children?: TreeNode[];
  badge?: string;
}

const TREE: TreeNode = {
  labelKey: "tree.model",
  children: [
    {
      labelKey: "tree.stage",
      children: [
        { key: "overview", labelKey: "tree.overview" },
        { key: "design", labelKey: "tree.design" },
        { key: "geometry", labelKey: "tree.geometry" },
        { key: "capacity", labelKey: "tree.capacity" },
        { key: "dynamics", labelKey: "tree.dynamics" },
        { key: "variation", labelKey: "tree.variation" },
        {
          labelKey: "tree.pinion",
          badge: "Stahl",
          children: [
            { key: "pinion.toothform", labelKey: "tree.toothform" },
            { key: "pinion.mesh", labelKey: "tree.mesh" },
          ],
        },
        {
          labelKey: "tree.wheel",
          badge: "PA",
          children: [
            { key: "wheel.toothform", labelKey: "tree.toothform" },
            { key: "wheel.mesh", labelKey: "tree.mesh" },
          ],
        },
        {
          labelKey: "tree.calcs",
          children: [{ key: "deck", labelKey: "tree.pair" }],
        },
      ],
    },
    { key: "glossary", labelKey: "tree.glossary" },
  ],
};

function TreeItem(props: {
  node: TreeNode;
  depth: number;
  active: NodeKey;
  onSelect: (k: NodeKey) => void;
}) {
  const t = useT();
  const [open, setOpen] = useState(true);
  const { node } = props;
  const isLeaf = !node.children?.length;
  const selected = node.key === props.active;
  return (
    <div>
      <button
        type="button"
        onClick={() => (isLeaf && node.key ? props.onSelect(node.key) : setOpen(!open))}
        className={`w-full flex items-center gap-1.5 text-left rounded-md px-2 py-[3px] text-[12.5px] transition-colors ${
          selected ? "bg-blue-600 text-white" : "text-zinc-700 hover:bg-zinc-200/70"
        }`}
        style={{ paddingLeft: 8 + props.depth * 14 }}
      >
        {!isLeaf && (
          <span className={`text-[9px] transition-transform ${open ? "rotate-90" : ""} ${selected ? "text-white" : "text-zinc-400"}`}>
            ▶
          </span>
        )}
        {isLeaf && <span className={`w-1.5 h-1.5 rounded-full ${selected ? "bg-white" : "bg-zinc-300"}`} />}
        <span className="truncate">{t(node.labelKey)}</span>
        {node.badge && (
          <span className={`ml-auto text-[10px] px-1.5 rounded-full ${selected ? "bg-white/20" : "bg-zinc-200 text-zinc-500"}`}>
            {node.badge}
          </span>
        )}
      </button>
      {open &&
        node.children?.map((c, i) => (
          <TreeItem key={i} node={c} depth={props.depth + 1} active={props.active} onSelect={props.onSelect} />
        ))}
    </div>
  );
}

function Shell() {
  const t = useT();
  const { locale, setLocale } = useLocale();
  const { label: stageLabel } = useStage();
  const [active, setActive] = useState<NodeKey>("overview");
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

  const titles: Record<NodeKey, string> = useMemo(
    () => ({
      overview: t("tree.overview"),
      design: `${t("tree.design")} · Presets / STE / parametrisch`,
      geometry: `${t("tree.geometry")} · ISO 21771`,
      capacity: `${t("tree.capacity")} · ISO 6336 / VDI 2736`,
      dynamics: `${t("tree.dynamics")} · ISO 6336-1`,
      variation: `${t("tree.variation")}`,
      "pinion.toothform": `${t("tree.pinion")} — ${t("tree.toothform")}`,
      "pinion.mesh": `${t("tree.pinion")} — ${t("tree.mesh")} · ADR-019`,
      "wheel.toothform": `${t("tree.wheel")} — ${t("tree.toothform")}`,
      "wheel.mesh": `${t("tree.wheel")} — ${t("tree.mesh")} · ADR-019`,
      deck: t("tree.pair"),
      glossary: t("tree.glossary"),
    }),
    [t],
  );

  const panel: ReactNode = (() => {
    switch (active) {
      case "overview":
        return <OverviewPanel onNavigate={(k) => setActive(k as NodeKey)} />;
      case "design":
        return <DesignPanel />;
      case "geometry":
        return <GeometryPanel />;
      case "capacity":
        return <CapacityPanel />;
      case "dynamics":
        return <DynamicsPanel />;
      case "variation":
        return <VariationPanel />;
      case "pinion.toothform":
        return <ToothFormPanel gear={1} />;
      case "wheel.toothform":
        return <ToothFormPanel gear={2} />;
      case "pinion.mesh":
        return <MeshPanel gear={1} />;
      case "wheel.mesh":
        return <MeshPanel gear={2} />;
      case "deck":
        return <PairPanel />;
      case "glossary":
        return <GlossaryPanel />;
    }
  })();

  return (
    <div className="h-screen flex flex-col">
      {/* header */}
      <header className="flex items-center gap-3 px-4 h-11 border-b border-zinc-200 bg-white shrink-0">
        <div className="w-5 h-5 rounded-md bg-zinc-900 text-white grid place-items-center text-[10px] font-bold">
          Z
        </div>
        <div className="font-semibold text-[13.5px]">{t("app.title")}</div>
        <div className="text-zinc-400 text-[12px]">{t("app.subtitle")}</div>
        <div className="ml-auto flex items-center gap-3">
          <span className="text-[11.5px] text-zinc-500">
            {online == null ? "…" : online ? `Backend v${version}` : t("msg.backendOffline")}
            <span
              className={`inline-block w-1.5 h-1.5 rounded-full ml-1.5 ${
                online ? "bg-emerald-500" : "bg-red-500"
              }`}
            />
          </span>
          <select
            value={locale}
            onChange={(e) => setLocale(e.target.value as "de" | "en")}
            className="border border-zinc-300 rounded-md px-1.5 py-0.5 text-[11.5px] bg-white"
          >
            <option value="de">DE</option>
            <option value="en">EN</option>
          </select>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        {/* model tree */}
        <aside className="w-[250px] shrink-0 border-r border-zinc-200 bg-zinc-50 overflow-y-auto p-2">
          <div className="text-[10.5px] uppercase tracking-wider text-zinc-400 px-2 pb-1">
            Modellbaum
          </div>
          <TreeItem node={TREE} depth={0} active={active} onSelect={setActive} />
        </aside>

        {/* editor */}
        <main className="flex-1 min-w-0 flex flex-col">
          <div className="h-9 flex items-center px-4 border-b border-zinc-200 bg-white shrink-0">
            <span className="text-[12.5px] font-medium text-zinc-800">{titles[active]}</span>
            <span className="ml-auto text-[11px] text-zinc-400">Stufe: {stageLabel}</span>
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto p-3 bg-zinc-100/70">{panel}</div>
        </main>
      </div>

      {/* messages strip */}
      <footer className="h-7 shrink-0 border-t border-zinc-200 bg-white flex items-center px-4 gap-2">
        <span className="text-[10.5px] uppercase tracking-wider text-zinc-400">{t("msg.title")}</span>
        <span className="text-[11.5px] text-zinc-500">{t("msg.ready")}</span>
      </footer>
    </div>
  );
}

export function Workbench() {
  return (
    <LocaleProvider>
      <StageProvider>
        <Shell />
      </StageProvider>
    </LocaleProvider>
  );
}
