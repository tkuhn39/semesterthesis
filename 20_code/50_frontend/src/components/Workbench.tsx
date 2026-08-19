"use client";

// FVA-Workbench-style shell (user decision 2026-07-04, screenshots are the spec):
// model tree on the left (Getriebeeinheit → Stirnradstufe → Wellen → Räder …), a TAB BAR
// per selected node in the editor (Geometrie · Tragfähigkeit · … · Dynamisches Abwälzen
// (FEM)), messages strip at the bottom. Tab visibility follows the Berechnungsauswahl
// (schema.methods → enables_tabs); hidden tabs keep their state. Schema-driven tabs render
// via <SchemaTab/>; the richer bespoke views (viewports, plots) stay as custom panels —
// they are the "Extras" the user chose to keep.

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "@/lib/api";
import { fetchUiSchema, type TabDef, type UiSchema } from "@/lib/uischema";
import { LocaleProvider, useLocale, useT } from "@/lib/i18n";
import { StageProvider, useStage } from "@/lib/stage";
import { instanceLabel, useWorkbench, type ModelInstances } from "@/lib/store";
import { downloadReport } from "@/lib/report";
import { SchemaTab } from "@/components/SchemaTab";
import { QuickView } from "@/components/QuickView";
import { SessionsPanel } from "@/components/SessionsPanel";
import { clampWidth, Resizer } from "@/components/SplitPane";
import { CalcSelectionPanel } from "@/panels/CalcSelectionPanel";
import { OverviewPanel } from "@/panels/OverviewPanel";
import { DesignPanel } from "@/panels/DesignPanel";
import { GeometryPanel } from "@/panels/GeometryPanel";
import { CapacityPanel } from "@/panels/CapacityPanel";
import { DynamicsPanel } from "@/panels/DynamicsPanel";
import { VariationPanel } from "@/panels/VariationPanel";
import { ToothFormPanel } from "@/panels/ToothFormPanel";
import { MeshPanel } from "@/panels/MeshPanel";
import { PairPanel } from "@/panels/PairPanel";
import { FemResultsPanel } from "@/panels/FemResultsPanel";
import { GlossaryPanel } from "@/panels/GlossaryPanel";
import { MaterialDbPanel } from "@/panels/MaterialDbPanel";

type NodeId =
  | "overview"
  | "unit"
  | "stage"
  | "pinion"
  | "correction"
  | "correction2"
  | "wheel"
  | "wheel_body"
  | "variation"
  | "glossary";

interface TreeNode {
  id?: NodeId;
  label: string;
  labelEn?: string;
  children?: TreeNode[];
  badge?: string;
}

// The [n] numbers are per-instance model IDs (data from the store, FVA behaviour) —
// the tree is built from the instance table, never from hardcoded label strings. The
// material badges follow the Werkstoff selection (norm-dispatch source), not the role.
function buildTree(
  model: ModelInstances,
  locale: string,
  badges: { gear1: string; gear2: string },
): TreeNode {
  const lab = (key: string) => instanceLabel(model[key], locale);
  return {
    label: "Modell",
    labelEn: "Model",
    children: [
      {
        id: "unit",
        label: lab("gear_unit"),
        children: [
          {
            id: "stage",
            label: lab("stage"),
            children: [
              {
                label: lab("shaft1"),
                children: [
                  {
                    id: "pinion",
                    label: lab("pinion"),
                    badge: badges.gear1,
                    children: [{ id: "correction", label: lab("correction") }],
                  },
                ],
              },
              {
                label: lab("shaft2"),
                children: [
                  {
                    id: "wheel",
                    label: lab("wheel"),
                    badge: badges.gear2,
                    children: [
                      { id: "correction2", label: lab("correction2") },
                      { id: "wheel_body", label: lab("wheel_body") },
                    ],
                  },
                ],
              },
              { id: "variation", label: "Stufenvariation", labelEn: "Stage variation" },
            ],
          },
        ],
      },
      { id: "overview", label: "Übersicht", labelEn: "Overview" },
      { id: "glossary", label: "Legende & Parameter", labelEn: "Glossary & parameters" },
    ],
  };
}

interface TabSpec {
  id: string;
  title: string;
  render: () => ReactNode;
  visibleIfMethod?: string | null;
}

function schemaTab(
  schema: UiSchema,
  componentId: string,
  tabId: string,
  locale: string,
  pairHeaders?: [string, string],
): TabSpec | null {
  const comp = schema.components.find((c) => c.id === componentId);
  const tab: TabDef | undefined = comp?.tabs.find((t) => t.id === tabId);
  if (!tab) return null;
  return {
    id: tabId,
    title: locale === "de" ? tab.title_de : tab.title_en,
    visibleIfMethod: tab.visible_if_method,
    render: () => <SchemaTab schema={schema} tab={tab} pairHeaders={pairHeaders} />,
  };
}

function TreeItem(props: {
  node: TreeNode;
  depth: number;
  active: NodeId;
  onSelect: (k: NodeId) => void;
}) {
  const { locale } = useLocale();
  const [open, setOpen] = useState(true);
  const { node } = props;
  const hasChildren = Boolean(node.children?.length);
  const selected = node.id === props.active;
  const label = locale === "de" ? node.label : node.labelEn ?? node.label;
  return (
    <div>
      <button
        type="button"
        onClick={() => {
          if (node.id) props.onSelect(node.id);
          if (hasChildren && !node.id) setOpen(!open);
        }}
        className={`w-full flex items-center gap-1.5 text-left rounded-md px-2 py-[3px] text-[12.5px] transition-colors ${
          selected ? "bg-blue-600 text-white" : "text-zinc-700 hover:bg-zinc-200/70"
        }`}
        style={{ paddingLeft: 8 + props.depth * 14 }}
      >
        {hasChildren && (
          <span
            role="presentation"
            onClick={(e) => {
              e.stopPropagation();
              setOpen(!open);
            }}
            className={`text-[9px] transition-transform ${open ? "rotate-90" : ""} ${selected ? "text-white" : "text-zinc-400"}`}
          >
            ▶
          </span>
        )}
        {!hasChildren && <span className={`w-1.5 h-1.5 rounded-full ${selected ? "bg-white" : "bg-zinc-300"}`} />}
        <span className="truncate">{label}</span>
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
  const wb = useWorkbench();
  const [schema, setSchema] = useState<UiSchema | null>(null);
  const [active, setActive] = useState<NodeId>("stage");
  const [tabByNode, setTabByNode] = useState<Record<string, string>>({});
  const [version, setVersion] = useState<string | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);
  const [reportBusy, setReportBusy] = useState(false);
  const [reportErr, setReportErr] = useState<string | null>(null);
  // resizable shell columns (user request): drag the dividers, widths clamp at the
  // content minimum so tree/quick-view content never gets squeezed into clipping
  const [treeW, setTreeW] = useState(250);
  const [quickW, setQuickW] = useState(470);

  useEffect(() => {
    api
      .health()
      .then((h) => {
        setVersion(h.version);
        setOnline(true);
      })
      .catch(() => setOnline(false));
    fetchUiSchema()
      .then(setSchema)
      .catch(() => setSchema(null));
  }, []);

  // node → editor tabs (FVA layout; schema tabs + bespoke panels as the kept extras)
  const nodeTabs: Record<NodeId, TabSpec[]> = useMemo(() => {
    const s = schema;
    const maybe = (spec: TabSpec | null) => (spec ? [spec] : []);
    // per-gear column headers from the model-instance table (never hardcoded)
    const gearHeads: [string, string] = [
      instanceLabel(wb.model.pinion, locale),
      instanceLabel(wb.model.wheel, locale),
    ];
    // load columns use the shaft-1/2 convention (user decision: instance IDs stay in
    // the store/tree for later multi-stage systems, but a single stage reads clearer
    // as "Welle 1 / Welle 2" — 1 = left gear, 2 = right gear per ADR-021)
    const loadHeads: [string, string] =
      locale === "de" ? ["Welle 1", "Welle 2"] : ["Shaft 1", "Shaft 2"];
    return {
      overview: [{ id: "overview", title: locale === "de" ? "Übersicht" : "Overview", render: () => (
        <OverviewPanel
          onNavigate={(key) => {
            // route the card's target (audit STR-14: every card used to land on the
            // stage node) — "node.tab" selects node AND tab, a bare key the node
            const [node, tab] = key.split(".");
            setActive(node as NodeId);
            if (tab) setTabByNode((m) => ({ ...m, [node]: tab }));
          }}
        />
      ) }],
      unit: [
        ...(s
          ? [
              {
                id: "calc_selection",
                title: locale === "de" ? "Berechnungsauswahl" : "Calculation selection",
                render: () => <CalcSelectionPanel schema={s} />,
              } satisfies TabSpec,
            ]
          : []),
        // FVA tab order: Leistungsfluss · Kräfte und Momente · Betriebsdaten · Steuerparameter
        ...(s ? maybe(schemaTab(s, "gear_unit", "powerflow", locale, loadHeads)) : []),
        ...(s ? maybe(schemaTab(s, "gear_unit", "forces", locale, loadHeads)) : []),
        ...(s ? maybe(schemaTab(s, "gear_unit", "operating_data", locale)) : []),
        ...(s ? maybe(schemaTab(s, "gear_unit", "control", locale)) : []),
      ],
      stage: [
        // FVA tab order: Geometrie · Toleranzen · Tragfähigkeit · VDI 2736 · Werkstoff ·
        // Schmierstoff · Lastverteilung (FEM) · Dyn. Abwälzen (FEM) — then our extras
        { id: "geometry", title: locale === "de" ? "Geometrie" : "Geometry", render: () => <GeometryPanel /> },
        ...(s ? maybe(schemaTab(s, "cylindrical_mesh", "tolerances", locale, gearHeads)) : []),
        ...(s
          ? [
              {
                id: "capacity",
                title: locale === "de" ? "Tragfähigkeit" : "Load capacity",
                render: () => {
                  const tab = s.components
                    .find((c) => c.id === "cylindrical_mesh")
                    ?.tabs.find((x) => x.id === "capacity_inputs");
                  return (
                    <div className="flex flex-col gap-3">
                      {tab && <SchemaTab schema={s} tab={tab} pairHeaders={gearHeads} />}
                      <CapacityPanel />
                    </div>
                  );
                },
              } satisfies TabSpec,
            ]
          : [{ id: "capacity", title: locale === "de" ? "Tragfähigkeit" : "Load capacity", render: () => <CapacityPanel /> }]),
        ...(s ? maybe(schemaTab(s, "cylindrical_mesh", "vdi2736", locale, gearHeads)) : []),
        // Werkstoff = schema fields + the material LIBRARY below (user requirement
        // 2026-08-19); saving/deleting a record reloads the schema so the mat_name
        // dropdown follows the library
        ...(() => {
          const matTab = s?.components
            .find((c) => c.id === "cylindrical_mesh")
            ?.tabs.find((x) => x.id === "material");
          if (!s || !matTab) return [];
          return [
            {
              id: "material",
              title: locale === "de" ? matTab.title_de : matTab.title_en,
              visibleIfMethod: matTab.visible_if_method,
              render: () => (
                <div className="flex flex-col gap-3">
                  <SchemaTab schema={s} tab={matTab} pairHeaders={gearHeads} />
                  <MaterialDbPanel
                    onLibraryChange={() =>
                      void fetchUiSchema()
                        .then(setSchema)
                        .catch(() => undefined)
                    }
                  />
                </div>
              ),
            } satisfies TabSpec,
          ];
        })(),
        ...(s ? maybe(schemaTab(s, "cylindrical_mesh", "lubricant", locale, gearHeads)) : []),
        ...(s ? maybe(schemaTab(s, "cylindrical_mesh", "loaddist_fem", locale, gearHeads)) : []),
        ...(s ? maybe(schemaTab(s, "cylindrical_mesh", "transient_fem", locale, gearHeads)) : []),
        { id: "design", title: locale === "de" ? "Auslegung" : "Design", render: () => <DesignPanel /> },
        { id: "dynamics", title: locale === "de" ? "Dynamikfaktoren" : "Dynamic factors", render: () => <DynamicsPanel /> },
        { id: "pair", title: locale === "de" ? "FE-Abwälzmodell (Ansicht)" : "FE rolling model (view)", render: () => <PairPanel /> },
        { id: "fem_results", title: locale === "de" ? "Ergebnisse (3D)" : "Results (3D)", visibleIfMethod: "fva_892_transient_fem", render: () => <FemResultsPanel /> },
      ],
      pinion: [
        { id: "toothform", title: locale === "de" ? "Zahnform" : "Tooth form", render: () => <ToothFormPanel gear={1} /> },
        { id: "mesh", title: "FE-Mesh", render: () => <MeshPanel gear={1} /> },
      ],
      correction: s
        ? (s.components.find((c) => c.id === "gear_correction")?.tabs ?? []).map((tab) => ({
            id: tab.id,
            title: locale === "de" ? tab.title_de : tab.title_en,
            visibleIfMethod: tab.visible_if_method,
            render: () => <SchemaTab schema={s} tab={tab} />,
          }))
        : [],
      // wheel-side Flankenmodifikation [41]: the SAME gear_correction schema rendered
      // against the correction2 store namespace — each gear edits its micro-geometry
      // independently in the full editor (user requirement 2026-08-18)
      correction2: s
        ? (s.components.find((c) => c.id === "gear_correction")?.tabs ?? []).map((tab) => ({
            id: tab.id,
            title: locale === "de" ? tab.title_de : tab.title_en,
            visibleIfMethod: tab.visible_if_method,
            render: () => (
              <SchemaTab
                schema={s}
                tab={tab}
                remapNamespace={{ from: "correction", to: "correction2" }}
              />
            ),
          }))
        : [],
      wheel: [
        { id: "toothform", title: locale === "de" ? "Zahnform" : "Tooth form", render: () => <ToothFormPanel gear={2} /> },
        { id: "mesh", title: "FE-Mesh", render: () => <MeshPanel gear={2} /> },
      ],
      wheel_body: s ? maybe(schemaTab(s, "wheel_body_cylindrical_gear", "wheel_body", locale)) : [],
      variation: [
        { id: "variation", title: locale === "de" ? "Stufenvariation" : "Stage variation", render: () => <VariationPanel /> },
      ],
      glossary: [
        { id: "glossary", title: locale === "de" ? "Legende & Parameter" : "Glossary & parameters", render: () => <GlossaryPanel /> },
      ],
    };
  }, [schema, locale, wb.model]);

  // Berechnungsauswahl drives tab visibility (state preserved while hidden)
  const visibleTabs = (nodeTabs[active] ?? []).filter(
    (tab) => !tab.visibleIfMethod || wb.calc[tab.visibleIfMethod],
  );
  const activeTabId = tabByNode[active] ?? visibleTabs[0]?.id;
  const activeTab = visibleTabs.find((x) => x.id === activeTabId) ?? visibleTabs[0];

  // material badges follow the Werkstoff selection (steel → "Stahl"/"Steel", plastic → "PA")
  const g1k = wb.materials.gear1_kind;
  const g2k = wb.materials.gear2_kind;
  const tree = useMemo(
    () =>
      buildTree(wb.model, locale, {
        gear1: g1k === "steel" ? (locale === "de" ? "Stahl" : "Steel") : "PA",
        gear2: g2k === "steel" ? (locale === "de" ? "Stahl" : "Steel") : "PA",
      }),
    [wb.model, locale, g1k, g2k],
  );
  const nodeTitle: Record<NodeId, string> = {
    overview: locale === "de" ? "Übersicht" : "Overview",
    unit: instanceLabel(wb.model.gear_unit, locale),
    stage: instanceLabel(wb.model.stage, locale),
    pinion: instanceLabel(wb.model.pinion, locale),
    correction: instanceLabel(wb.model.correction, locale),
    correction2: instanceLabel(wb.model.correction2, locale),
    wheel: instanceLabel(wb.model.wheel, locale),
    wheel_body: instanceLabel(wb.model.wheel_body, locale),
    variation: locale === "de" ? "Stufenvariation" : "Stage variation",
    glossary: locale === "de" ? "Legende & Parameter" : "Glossary & parameters",
  };

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
          <button
            type="button"
            className="border border-zinc-300 rounded-md px-2 py-0.5 text-[11.5px] bg-white hover:bg-zinc-50 disabled:opacity-50"
            disabled={reportBusy}
            title={t("report.hint")}
            onClick={() => {
              setReportBusy(true);
              setReportErr(null);
              downloadReport(wb, locale)
                .catch((e) => setReportErr(e instanceof Error ? e.message : String(e)))
                .finally(() => setReportBusy(false));
            }}
          >
            {reportBusy ? "…" : t("report.button")}
          </button>
          {reportErr && <span className="text-[11px] text-red-600">{reportErr}</span>}
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
        {/* model tree (resizable, min-width lock) */}
        <aside
          className="shrink-0 border-r border-zinc-200 bg-zinc-50 overflow-y-auto overflow-x-auto p-2"
          style={{ width: treeW, minWidth: 190 }}
        >
          <div className="text-[10.5px] uppercase tracking-wider text-zinc-400 px-2 pb-1">
            {locale === "de" ? "Modellbaum" : "Model tree"}
          </div>
          <TreeItem node={tree} depth={0} active={active} onSelect={setActive} />
          {/* saved sessions live in the sidebar (user requirement 2026-08-19) */}
          <SessionsPanel />
        </aside>
        <Resizer onDrag={(dx) => setTreeW((w) => clampWidth(w + dx, 190, 480))} />

        {/* editor: node title + FVA tab bar + panel */}
        <main className="flex-1 min-w-0 flex flex-col">
          <div className="flex items-center px-3 border-b border-zinc-200 bg-white shrink-0 gap-1 h-9 overflow-x-auto">
            {visibleTabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setTabByNode({ ...tabByNode, [active]: tab.id })}
                className={`px-2.5 h-7 rounded-t-md text-[12px] whitespace-nowrap border-b-2 ${
                  activeTab?.id === tab.id
                    ? "border-blue-600 text-blue-700 font-medium bg-blue-50/50"
                    : "border-transparent text-zinc-600 hover:text-zinc-900"
                }`}
              >
                {tab.title}
              </button>
            ))}
          </div>
          <div className="h-8 flex items-center px-4 border-b border-zinc-100 bg-white shrink-0">
            <span className="text-[13px] font-semibold text-sky-900">{nodeTitle[active]}</span>
            {/* active-geometry badge: outside the scrollable tab strip so it never clips */}
            <span className="ml-auto text-[11px] text-zinc-400 whitespace-nowrap">
              {t("pair.stageLabel")}: {stageLabel}
            </span>
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto p-3 bg-zinc-100/70">
            {activeTab?.render() ?? null}
          </div>
        </main>

        {/* Ergebnis-Schnellansicht (FVA right panel) — ISO 21771 tables of the ONE stage;
            resizable with a min-width lock, tables scroll instead of clipping */}
        {["unit", "stage", "pinion", "wheel", "correction", "correction2", "wheel_body"].includes(active) && (
          <>
            <div className="hidden xl:flex self-stretch">
              {/* min 390: at 330 the wheel column clipped at 1720 px (audit V-05) */}
              <Resizer onDrag={(dx) => setQuickW((w) => clampWidth(w - dx, 390, 640))} />
            </div>
            <aside
              className="shrink-0 border-l border-zinc-200 bg-zinc-50 overflow-y-auto p-2 hidden xl:block"
              style={{ width: quickW, minWidth: 390 }}
            >
              <div className="text-[10.5px] uppercase tracking-wider text-zinc-400 px-2 pb-1">
                {locale === "de" ? "Ergebnis-Schnellansicht" : "Result quick view"}
              </div>
              <QuickView />
            </aside>
          </>
        )}
      </div>

      {/* messages strip */}
      <footer className="h-7 shrink-0 border-t border-zinc-200 bg-white flex items-center px-4 gap-2 overflow-hidden">
        <span className="text-[10.5px] uppercase tracking-wider text-zinc-400">{t("msg.title")}</span>
        {/* live messages (audit GAP-12: the strip was static decoration) — panels push
            geometry notes / request errors via wb.setMessages */}
        {wb.messages.length === 0 ? (
          <span className="text-[11.5px] text-zinc-500">{t("msg.ready")}</span>
        ) : (
          <span className="text-[11.5px] text-amber-700 truncate" title={wb.messages.join(" · ")}>
            ⚠ {wb.messages.join(" · ")}
          </span>
        )}
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
