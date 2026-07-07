"use client";

// FE-mesh editor (M4): FVA density parameters + fillet strategy → 3D hull in the dark
// viewport (quality heatmap toggle), native convergence quick check, fillet ranking, and
// the implicit rolling deck (.inp) download with the mixed-pairing rigid-shell rule.

import { useState } from "react";
import {
  meshApi,
  type ConvergenceResponse,
  type FilletCompareResponse,
  type FilletSpec,
  type FilletSweepResponse,
  type Mesh3DResponse,
  type MeshPreviewResponse,
} from "@/lib/api";
import { useStage } from "@/lib/stage";
import { MeshViewport } from "@/components/MeshViewport";
import { Mesh2DView } from "@/components/Mesh2DView";
import { SplitPair } from "@/components/SplitPane";
import { FilletEditor, ManufacturabilityNote } from "@/panels/ToothFormPanel";
import { AttrRow, Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { useFmt, useT } from "@/lib/i18n";

const DENSITY_PRESETS: { id: string; root: number; flank: number }[] = [
  { id: "reference", root: 1, flank: 1 },
  { id: "convRoot", root: 2, flank: 1 },
  { id: "convFlank", root: 1, flank: 2 },
  { id: "fine", root: 2, flank: 2 },
];

export function MeshPanel(props: { gear: 1 | 2 }) {
  const t = useT();
  const fm = useFmt();
  const { stage } = useStage();
  const [refineRoot, setRefineRoot] = useState(1);
  const [refineFlank, setRefineFlank] = useState(1);
  const [refineThickness, setRefineThickness] = useState(1);
  const [layers, setLayers] = useState(6);
  const [fillet, setFillet] = useState<FilletSpec>({ kind: "standard" });
  const [heatmap, setHeatmap] = useState(true);
  const [view, setView] = useState<"3d" | "2d">("3d");
  const [data, setData] = useState<Mesh3DResponse | null>(null);
  const [preview, setPreview] = useState<MeshPreviewResponse | null>(null);
  const [conv, setConv] = useState<Record<string, ConvergenceResponse>>({});
  const [ranking, setRanking] = useState<FilletCompareResponse | null>(null);
  const [sweep, setSweep] = useState<FilletSweepResponse | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);


  const guard = async (name: string, fn: () => Promise<void>) => {
    setBusy(name);
    setErr(null);
    try {
      await fn();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  const generate = () =>
    guard("mesh", async () => {
      const req = {
        stage,
        gear: props.gear,
        refine_root: refineRoot,
        refine_flank: refineFlank,
        refine_thickness: refineThickness,
        fillet,
      };
      // 3D hull for the viewport + the 2D section (FVA FEM-Vernetzer style) in one go
      const [d3, d2] = await Promise.all([meshApi.mesh3d(req, layers), meshApi.preview(req)]);
      setData(d3);
      setPreview(d2);
    });

  const runConvergence = (target: "root" | "flank") =>
    guard(`conv-${target}`, async () => {
      const out = await meshApi.convergence(stage, props.gear, target);
      setConv((c) => ({ ...c, [target]: out }));
    });

  const runRanking = () =>
    guard("rank", async () => {
      setRanking(await meshApi.filletCompare(stage, props.gear));
    });

  const leftPane = (
    <>
        <Section title={t("mesh.density")}>
          <div className="p-2 border-b border-zinc-100">
            <select
              className="border border-zinc-300 rounded-md px-2 py-1 text-[12px] w-full"
              value={
                DENSITY_PRESETS.find((d) => d.root === refineRoot && d.flank === refineFlank)?.id ??
                "custom"
              }
              onChange={(e) => {
                const d = DENSITY_PRESETS.find((x) => x.id === e.target.value);
                if (d) {
                  setRefineRoot(d.root);
                  setRefineFlank(d.flank);
                }
              }}
            >
              {DENSITY_PRESETS.map((d) => (
                <option key={d.id} value={d.id}>
                  {t(`mesh.preset.${d.id}`)}
                </option>
              ))}
              <option value="custom" disabled>
                {t("mesh.preset.custom")}
              </option>
            </select>
          </div>
          <table className="attr-table">
            <thead>
              <tr>
                <th>{t("common.attribute")}</th>
                <th></th>
                <th>{t("common.value")}</th>
                <th>{t("common.unit")}</th>
              </tr>
            </thead>
            <tbody>
              <AttrRow label={t("mesh.densityRoot")} symbol="f_Fuß" unit="×">
                <td>
                  <select
                    className="sel-narrow"
                    value={refineRoot}
                    onChange={(e) => setRefineRoot(Number(e.target.value))}
                  >
                    {[1, 2, 3].map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                </td>
              </AttrRow>
              <AttrRow label={t("mesh.densityFlank")} symbol="f_Flanke" unit="×">
                <td>
                  <select
                    className="sel-narrow"
                    value={refineFlank}
                    onChange={(e) => setRefineFlank(Number(e.target.value))}
                  >
                    {[1, 2, 3].map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                </td>
              </AttrRow>
              <AttrRow label={t("mesh.densityThickness")} symbol="f_Dicke" unit="×">
                <td>
                  <select
                    className="sel-narrow"
                    value={refineThickness}
                    onChange={(e) => setRefineThickness(Number(e.target.value))}
                  >
                    {[1, 2, 3].map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                </td>
              </AttrRow>
              <AttrRow label={t("mesh.layers")} symbol="n_breite" unit="–">
                <td>
                  <Num value={layers} onChange={setLayers} step={1} />
                </td>
              </AttrRow>
              {preview && (
                <AttrRow label={t("mesh.effective")} symbol="" unit="">
                  <td className="wb-num text-[11.5px] text-zinc-500">
                    {t("mesh.elemsRoot")}: {preview.elements_root} ·{" "}
                    {t("mesh.elemsHeight")}: {preview.elements_flank} ·{" "}
                    {t("mesh.elemsThickness")}: {preview.elements_thickness}
                  </td>
                </AttrRow>
              )}
            </tbody>
          </table>
        </Section>

        <Section title={t("mesh.fillet")} defaultOpen={false}>
          <FilletEditor value={fillet} onChange={setFillet} />
          <div className="p-2">
            <ManufacturabilityNote kind={fillet.kind} />
          </div>
        </Section>

        <div className="flex gap-2 items-center">
          <Btn onClick={generate} busy={busy === "mesh"}>
            {t("mesh.generate")}
          </Btn>
          <label className="inline-flex items-center gap-1.5 text-[12px] text-zinc-600">
            <input type="checkbox" checked={heatmap} onChange={(e) => setHeatmap(e.target.checked)} />
            Jacobi-Heatmap
          </label>
          <select
            className="border border-zinc-300 rounded-md px-1.5 py-0.5 text-[12px] ml-auto"
            value={view}
            onChange={(e) => setView(e.target.value as "3d" | "2d")}
          >
            <option value="3d">3D-Ansicht</option>
            <option value="2d">2D-Schnitt</option>
          </select>
        </div>
        {err && <ErrNote>{err}</ErrNote>}

        {data && (
          <div className="grid grid-cols-2 gap-2">
            <Stat label={t("mesh.hexes")} value={fm.int(data.n_hexes)} />
            <Stat label={t("mesh.nodes")} value={fm.int(data.n_nodes_3d)} />
            <Stat
              label={t("mesh.minJ")}
              value={data.min_scaled_jacobian.toFixed(3)}
              tone={data.min_scaled_jacobian >= 0.35 ? "good" : "bad"}
            />
            <Stat
              label={t("mesh.below")}
              value={String(data.cells_below_035)}
              tone={data.cells_below_035 === 0 ? "good" : "bad"}
            />
          </div>
        )}

        <Section title={t("mesh.convergence")} defaultOpen={false}>
          <div className="p-2 flex gap-2">
            <Btn variant="ghost" onClick={() => runConvergence("root")} busy={busy === "conv-root"}>
              {t("mesh.convergence.root")}
            </Btn>
            <Btn variant="ghost" onClick={() => runConvergence("flank")} busy={busy === "conv-flank"}>
              {t("mesh.convergence.flank")}
            </Btn>
          </div>
          {(["root", "flank"] as const).map((k) =>
            conv[k] ? (
              <div key={k} className="px-3 pb-2 text-[12px] text-zinc-700">
                <span className="font-medium">{t(`mesh.convergence.${k}`)}:</span>{" "}
                σ = {conv[k].sigma_mpa.map((s) => s.toFixed(1)).join(" → ")} MPa ·{" "}
                {t("mesh.convergence.level")}{" "}
                <span className="wb-num font-semibold">{conv[k].converged_level ?? "–"}</span>
              </div>
            ) : null,
          )}
        </Section>

        <Section title={t("mesh.filletCompare")} defaultOpen={false}>
          <div className="p-2">
            <Btn variant="ghost" onClick={runRanking} busy={busy === "rank"}>
              {t("mesh.filletCompare.run")}
            </Btn>
          </div>
          {ranking && (
            <table className="attr-table">
              <thead>
                <tr>
                  <th>Strategie</th>
                  <th>σ_max</th>
                  <th>Δ</th>
                  <th>{t("mesh.clearance")}</th>
                </tr>
              </thead>
              <tbody>
                {ranking.names.map((n, i) => (
                  <tr key={n}>
                    <td>{t(`mesh.fillet.${n}`)}</td>
                    <td className="wb-num">{ranking.sigma_mpa[i].toFixed(1)} MPa</td>
                    <td className="wb-num" style={{ color: ranking.delta_percent[i] < 0 ? "#059669" : undefined }}>
                      {ranking.delta_percent[i] > 0 ? "+" : ""}
                      {ranking.delta_percent[i].toFixed(1)} %
                    </td>
                    <td className="wb-num">{ranking.clearance_mm[i].toFixed(2)} mm</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Section>

        <Section title={t("mesh.sweep")} defaultOpen={false}>
          <div className="p-2 flex items-center gap-2">
            {(["elliptic", "bezier", "bionic"] as const).map((k) => (
              <Btn
                key={k}
                variant="ghost"
                busy={busy === `sweep-${k}`}
                onClick={() =>
                  guard(`sweep-${k}`, async () =>
                    setSweep(await meshApi.filletSweep(stage, props.gear, k)),
                  )
                }
              >
                {t(`mesh.fillet.${k}`)}
              </Btn>
            ))}
          </div>
          {sweep && (
            <div className="px-3 pb-2">
              <table className="attr-table">
                <thead>
                  <tr>
                    <th>{sweep.parameter}</th>
                    <th>σ_max</th>
                    <th>{t("mesh.clearance")}</th>
                    <th>OK</th>
                  </tr>
                </thead>
                <tbody>
                  {sweep.values.map((v, i) => (
                    <tr key={i} style={{ fontWeight: v === sweep.best_value ? 600 : 400 }}>
                      <td className="wb-num">{v}</td>
                      <td className="wb-num">
                        {sweep.sigma_mpa[i] > 0 ? `${sweep.sigma_mpa[i].toFixed(1)} MPa` : "–"}
                      </td>
                      <td className="wb-num">
                        {sweep.clearance_mm[i] > -90 ? `${sweep.clearance_mm[i].toFixed(2)} mm` : "–"}
                      </td>
                      <td>{sweep.feasible[i] ? "✓" : "✗"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="text-[11.5px] text-zinc-600 pt-1.5">
                {t("mesh.sweep.best")}: <span className="wb-num font-semibold">{sweep.best_value ?? "–"}</span>
                {" · "}σ {sweep.best_sigma_mpa?.toFixed(1) ?? "–"} MPa (Standard{" "}
                {sweep.standard_sigma_mpa.toFixed(1)} MPa)
              </div>
            </div>
          )}
        </Section>
    </>
  );

  return (
    <SplitPair
      initial={380}
      min={340}
      left={leftPane}
      right={
        <div className="h-full min-h-[560px]" style={{ background: "var(--wb-viewport)", borderRadius: 10 }}>
          {view === "2d" && preview ? (
            <Mesh2DView data={preview} heatmap={heatmap} height={620} />
          ) : (
            <MeshViewport data={data} heatmap={heatmap} />
          )}
        </div>
      }
    />
  );
}
