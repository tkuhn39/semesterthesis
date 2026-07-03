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
  type Mesh3DResponse,
} from "@/lib/api";
import { MeshViewport } from "@/components/MeshViewport";
import { FilletEditor } from "@/panels/ToothFormPanel";
import { AttrRow, Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { useT } from "@/lib/i18n";

export function MeshPanel(props: { gear: 1 | 2 }) {
  const t = useT();
  const [refineRoot, setRefineRoot] = useState(1);
  const [refineFlank, setRefineFlank] = useState(1);
  const [layers, setLayers] = useState(6);
  const [fillet, setFillet] = useState<FilletSpec>({ kind: "standard" });
  const [heatmap, setHeatmap] = useState(true);
  const [data, setData] = useState<Mesh3DResponse | null>(null);
  const [conv, setConv] = useState<Record<string, ConvergenceResponse>>({});
  const [ranking, setRanking] = useState<FilletCompareResponse | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // deck options
  const [torque, setTorque] = useState(20000);
  const [rollPositions, setRollPositions] = useState(30);
  const [steelShell, setSteelShell] = useState(true);

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
      setData(
        await meshApi.mesh3d(
          { gear: props.gear, refine_root: refineRoot, refine_flank: refineFlank, fillet },
          layers,
        ),
      );
    });

  const runConvergence = (target: "root" | "flank") =>
    guard(`conv-${target}`, async () => {
      const out = await meshApi.convergence(props.gear, target);
      setConv((c) => ({ ...c, [target]: out }));
    });

  const runRanking = () =>
    guard("rank", async () => {
      setRanking(await meshApi.filletCompare(props.gear));
    });

  const downloadDeck = () =>
    guard("deck", async () => {
      const text = await meshApi.deck({
        wheel_torque_nmm: torque,
        face_layers: layers,
        n_roll_positions: rollPositions,
        refine_root: refineRoot,
        refine_flank: refineFlank,
        steel_shell: steelShell,
        fillet_wheel: fillet,
      });
      const blob = new Blob([text], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "kst-e_implicit_generated.inp";
      a.click();
      URL.revokeObjectURL(url);
    });

  return (
    <div className="grid grid-cols-[360px_1fr] gap-3 items-start h-full">
      <div className="flex flex-col gap-3 overflow-y-auto pr-1" style={{ maxHeight: "100%" }}>
        <Section title={t("mesh.density")}>
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
                  <select value={refineRoot} onChange={(e) => setRefineRoot(Number(e.target.value))}>
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
                  <select value={refineFlank} onChange={(e) => setRefineFlank(Number(e.target.value))}>
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
            </tbody>
          </table>
        </Section>

        <Section title={t("mesh.fillet")} defaultOpen={false}>
          <FilletEditor value={fillet} onChange={setFillet} />
        </Section>

        <div className="flex gap-2">
          <Btn onClick={generate} busy={busy === "mesh"}>
            {t("mesh.generate")}
          </Btn>
          <label className="inline-flex items-center gap-1.5 text-[12px] text-zinc-600">
            <input type="checkbox" checked={heatmap} onChange={(e) => setHeatmap(e.target.checked)} />
            Jacobi-Heatmap
          </label>
        </div>
        {err && <ErrNote>{err}</ErrNote>}

        {data && (
          <div className="grid grid-cols-2 gap-2">
            <Stat label={t("mesh.hexes")} value={data.n_hexes.toLocaleString("de-DE")} />
            <Stat label={t("mesh.nodes")} value={data.n_nodes_3d.toLocaleString("de-DE")} />
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

        <Section title={t("deck.title")} defaultOpen={false}>
          <table className="attr-table">
            <tbody>
              <AttrRow label={t("deck.torque")} symbol="M₂" unit="N·mm">
                <td>
                  <Num value={torque} onChange={setTorque} />
                </td>
              </AttrRow>
              <AttrRow label={t("deck.rollPositions")} symbol="n_W" unit="–">
                <td>
                  <Num value={rollPositions} onChange={setRollPositions} step={1} />
                </td>
              </AttrRow>
            </tbody>
          </table>
          <div className="p-2 flex items-center gap-3 border-t border-zinc-100">
            <label className="inline-flex items-center gap-1.5 text-[12px] text-zinc-600">
              <input
                type="checkbox"
                checked={steelShell}
                onChange={(e) => setSteelShell(e.target.checked)}
              />
              {t("deck.steelShell")}
            </label>
            <Btn onClick={downloadDeck} busy={busy === "deck"}>
              {t("deck.download")}
            </Btn>
          </div>
        </Section>
      </div>

      <div className="h-full min-h-[560px]" style={{ background: "var(--wb-viewport)", borderRadius: 10 }}>
        <MeshViewport data={data} heatmap={heatmap} />
      </div>
    </div>
  );
}
