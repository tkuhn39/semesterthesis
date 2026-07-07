"use client";

// FE rolling-model panel (M6): both gears of the current stage in one dark viewport —
// exactly the combined .inp assembly, served by /api/mesh/pair (backend SSOT: closing
// rotation, edge start, rigid shells, fillets, tip relief) — with co-moving DOF triads
// (locked 1–5 gray, free rotation green/amber), a slider over the REAL Wälzstellungen of
// the deck schedule, and the deck download (series ZIP or single INP).

import { useState } from "react";
import { meshApi, type PairAssemblyResponse } from "@/lib/api";
import { useStage } from "@/lib/stage";
import { useWorkbench } from "@/lib/store";
import { deckPayload } from "@/lib/deck";
import { PairViewport } from "@/components/PairViewport";
import { SplitPair } from "@/components/SplitPane";
import { AttrRow, Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { FilletEditor, ManufacturabilityNote } from "@/panels/ToothFormPanel";
import { useFmt, useT } from "@/lib/i18n";

interface Effective {
  root: number;
  flank: number;
  thickness: number;
}

export function PairPanel() {
  const t = useT();
  const fm = useFmt();
  const { stage, label } = useStage();
  const wb = useWorkbench();
  const [pair, setPair] = useState<PairAssemblyResponse | null>(null);
  const [position, setPosition] = useState(0); // Wälzstellung k (continuous 0 … n−1)
  const [eff, setEff] = useState<Record<1 | 2, Effective | null>>({ 1: null, 2: null });
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  // FULL store SSOT (phase F): every deck setting lives in fem.* — this panel and the
  // Dyn-Abwälzen tab edit the SAME values, and both build their request through
  // deckPayload(); torque M₂ comes from the Leistungsfluss (user point 7a)
  const fem = wb.fem;
  const m2 = wb.get("fem.torque_gear2_nmm");

  const centerDistance = stage.center_distance_mm ?? (stage.normal_module_mm * (stage.teeth_pinion + stage.teeth_wheel)) / 2;

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

  const refineOf = (gear: 1 | 2) =>
    gear === 1
      ? {
          refine_root: fem.refine_root,
          refine_flank: fem.refine_flank,
          refine_thickness: fem.refine_thickness,
        }
      : {
          refine_root: fem.refine_root_gear2,
          refine_flank: fem.refine_flank_gear2,
          refine_thickness: fem.refine_thickness_gear2,
        };

  const generate = () =>
    guard("pair", async () => {
      // assembly + the effective per-tooth element counts of both 2D sections in parallel
      const [res, p1, p2] = await Promise.all([
        meshApi.pair(deckPayload(wb)),
        meshApi.preview({ stage, gear: 1, ...refineOf(1), fillet: fem.fillet_gear1 }),
        meshApi.preview({ stage, gear: 2, ...refineOf(2), fillet: fem.fillet_gear2 }),
      ]);
      setPair(res);
      setPosition(0); // start of the roll = the deck's edge-tooth start position
      setEff({
        1: { root: p1.elements_root, flank: p1.elements_flank, thickness: p1.elements_thickness },
        2: { root: p2.elements_root, flank: p2.elements_flank, thickness: p2.elements_thickness },
      });
    });

  // 2D quick convergence per gear (user point 7): preseed root/flank factors with the
  // converged level of the native plane-FE check
  const preseed = (gear: 1 | 2) =>
    guard(`conv${gear}`, async () => {
      const [root, flank] = await Promise.all([
        meshApi.convergence(stage, gear, "root"),
        meshApi.convergence(stage, gear, "flank"),
      ]);
      const patch: Record<string, number> = {};
      if (root.converged_level != null) {
        patch[gear === 1 ? "refine_root" : "refine_root_gear2"] = root.converged_level;
      }
      if (flank.converged_level != null) {
        patch[gear === 1 ? "refine_flank" : "refine_flank_gear2"] = flank.converged_level;
      }
      wb.setFem(patch);
    });

  const downloadDeck = () =>
    guard("deck", async () => {
      if (typeof m2 !== "number" || !Number.isFinite(m2)) {
        throw new Error(t("pf.noTorque"));
      }
      const req = { ...deckPayload(wb), torque_gear2_nmm: m2 };
      const series = wb.fem.deck_mode === "series";
      const blob = series
        ? await meshApi.deckSeries(req)
        : new Blob([await meshApi.deck(req)], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = series ? "rolling_position_series.zip" : "implicit_rolling_generated.inp";
      a.click();
      URL.revokeObjectURL(url);
    });

  const leftPane = (
    <>
        <div className="text-[12px] text-zinc-500">
          {t("pair.stageLabel")}: <span className="font-medium text-zinc-800">{label}</span> · a ={" "}
          <span className="wb-num">{centerDistance.toFixed(2)} mm</span>
        </div>

        <Section title={t("mesh.density")}>
          {/* FVA mesh-fineness dialog per gear: factor dropdowns + effective per-tooth
              counts (after generating); Zahnbreite (layers) is shared like the deck */}
          <table className="attr-table">
            <thead>
              <tr>
                <th>{t("common.attribute")}</th>
                <th></th>
                <th>{t("pair.gear1")}</th>
                <th>{t("pair.gear2")}</th>
              </tr>
            </thead>
            <tbody>
              {(
                [
                  ["root", t("mesh.elemsRoot"), "f_Fuß"],
                  ["flank", t("mesh.elemsHeight"), "f_Höhe"],
                  ["thickness", t("mesh.elemsThickness"), "f_Dicke"],
                ] as const
              ).map(([key, label, symbol]) => (
                <AttrRow key={key} label={label} symbol={symbol} unit="">
                  {([1, 2] as const).map((gear) => {
                    const field = (gear === 1 ? `refine_${key}` : `refine_${key}_gear2`) as
                      | "refine_root"
                      | "refine_flank"
                      | "refine_thickness"
                      | "refine_root_gear2"
                      | "refine_flank_gear2"
                      | "refine_thickness_gear2";
                    const effective = eff[gear];
                    return (
                      <td key={gear}>
                        <span className="inline-flex items-center gap-1.5">
                          <select
                            className="sel-narrow"
                            value={fem[field]}
                            onChange={(e) => wb.setFem({ [field]: Number(e.target.value) })}
                          >
                            {[1, 2, 3].map((v) => (
                              <option key={v} value={v}>
                                ×{v}
                              </option>
                            ))}
                          </select>
                          {effective && (
                            <span
                              className="wb-num text-[11px] text-zinc-500 whitespace-nowrap"
                              title={t("mesh.effective")}
                            >
                              ≙ {effective[key]}
                            </span>
                          )}
                        </span>
                      </td>
                    );
                  })}
                </AttrRow>
              ))}
              <AttrRow label={t("mesh.elemsWidth")} symbol="n_breite" unit="–">
                <td colSpan={2}>
                  <Num
                    value={fem.face_layers}
                    onChange={(v) => wb.setFem({ face_layers: v })}
                    step={1}
                  />
                </td>
              </AttrRow>
            </tbody>
          </table>
          <div className="p-2 flex items-center gap-2 border-t border-zinc-100">
            {([1, 2] as const).map((gear) => (
              <Btn key={gear} onClick={() => preseed(gear)} busy={busy === `conv${gear}`}>
                {t("mesh.preseed")} · {t(`pair.gear${gear}`)}
              </Btn>
            ))}
          </div>
        </Section>

        <Section title={t("pair.axial")}>
          <table className="attr-table">
            <tbody>
              <AttrRow label={`${t("pair.axialOffset")} · ${t("pair.gear1")}`} symbol="Δz₁" unit="mm">
                <td>
                  <Num
                    value={fem.axial_offset_gear1_mm}
                    onChange={(v) => wb.setFem({ axial_offset_gear1_mm: v })}
                    step={0.5}
                  />
                </td>
              </AttrRow>
              <AttrRow label={`${t("pair.axialOffset")} · ${t("pair.gear2")}`} symbol="Δz₂" unit="mm">
                <td>
                  <Num
                    value={fem.axial_offset_gear2_mm}
                    onChange={(v) => wb.setFem({ axial_offset_gear2_mm: v })}
                    step={0.5}
                  />
                </td>
              </AttrRow>
            </tbody>
          </table>
          <div className="px-2.5 pb-2 text-[11px] text-zinc-500">{t("pair.axialNote")}</div>
        </Section>

        <Section title={`${t("mesh.fillet")} · ${t("pair.gear1")}`} defaultOpen={false}>
          <FilletEditor
            value={fem.fillet_gear1}
            onChange={(f) => wb.setFem({ fillet_gear1: f })}
          />
          <div className="px-2.5 pb-2">
            <ManufacturabilityNote kind={fem.fillet_gear1.kind} />
          </div>
        </Section>
        <Section title={`${t("mesh.fillet")} · ${t("pair.gear2")}`} defaultOpen={false}>
          <FilletEditor
            value={fem.fillet_gear2}
            onChange={(f) => wb.setFem({ fillet_gear2: f })}
          />
          <div className="px-2.5 pb-2">
            <ManufacturabilityNote kind={fem.fillet_gear2.kind} />
          </div>
        </Section>

        <Btn onClick={generate} busy={busy === "pair"}>
          {t("pair.generate")}
        </Btn>
        {err && <ErrNote>{err}</ErrNote>}

        {pair && (
          <>
            <div className="grid grid-cols-2 gap-2">
              <Stat
                label={`${t("pair.gear1")} · ${pair.gear1.rigid_shell ? "R3D4" : t("mesh.hexes")}`}
                value={fm.int(pair.gear1.n_elements)}
              />
              <Stat
                label={`${t("pair.gear2")} · ${pair.gear2.rigid_shell ? "R3D4" : t("mesh.hexes")}`}
                value={fm.int(pair.gear2.n_elements)}
              />
            </div>
            <Section title={t("pair.roll")}>
              <div className="p-3">
                {/* caption ABOVE the slider — a horizontal scrollbar of the section can
                    then never overlay it (user report: swallowed text lines) */}
                <div className="flex flex-wrap justify-between gap-x-2 pb-1.5 text-[11px] text-zinc-500">
                  <span>1</span>
                  <span className="wb-num">
                    {t("pair.position")} {Math.round(position) + 1}/{pair.n_positions}
                    {Math.abs(position - Math.round(position)) < 0.05
                      ? ` · ${t("pair.measurePoint")}`
                      : ""}{" "}
                    · φ ={" "}
                    {(
                      ((pair.gear2.start_angle_rad + position * pair.gear2.step_angle_rad) * 180) /
                      Math.PI
                    ).toFixed(2)}
                    °
                  </span>
                  <span>{pair.n_positions}</span>
                </div>
                {/* the REAL Wälzstellungen of the deck schedule (edge start → far edge) */}
                <input
                  type="range"
                  min={0}
                  max={pair.n_positions - 1}
                  step={0.1}
                  value={position}
                  onChange={(e) => setPosition(Number(e.target.value))}
                  className="w-full"
                />
              </div>
            </Section>
            <div className="text-[11.5px] text-zinc-500 leading-relaxed border border-zinc-200 rounded-lg bg-white p-2.5">
              {t("pair.mouseHint")}
            </div>
            <div className="text-[11.5px] text-zinc-500 leading-relaxed border border-zinc-200 rounded-lg bg-white p-2.5">
              <div className="font-medium text-zinc-700 mb-1">{t("pair.legend")}</div>
              <div>
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-zinc-400 mr-1.5" />
                {t("pair.legendLocked")}
              </div>
              <div>
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-green-500 mr-1.5" />
                {t("pair.legendDriven")}
              </div>
              <div>
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-amber-500 mr-1.5" />
                {t("pair.legendTorque")}
              </div>
            </div>
          </>
        )}

        <Section title={t("deck.title")} defaultOpen={false}>
          <table className="attr-table">
            <tbody>
              <AttrRow label={t("deck.torque")} symbol="M₂" unit="N·mm">
                <td>
                  {/* SSOT: from the Leistungsfluss — edit it there, never here */}
                  <input
                    type="text"
                    value={typeof m2 === "number" ? m2.toFixed(1) : "—"}
                    disabled
                    title={t("pf.torqueSource")}
                  />
                </td>
              </AttrRow>
              <AttrRow label={t("deck.rollPositions")} symbol="n_W" unit="–">
                <td>
                  <Num
                    value={fem.n_roll_positions}
                    onChange={(v) => wb.setFem({ n_roll_positions: v })}
                    step={1}
                  />
                </td>
              </AttrRow>
            </tbody>
          </table>
          <div className="p-2 flex items-center gap-3 border-t border-zinc-100">
            <label className="inline-flex items-center gap-1.5 text-[12px] text-zinc-600">
              <input
                type="checkbox"
                checked={fem.steel_shell}
                onChange={(e) => wb.setFem({ steel_shell: e.target.checked })}
              />
              {t("deck.steelShell")}
            </label>
            <Btn onClick={downloadDeck} busy={busy === "deck"}>
              {t("deck.download")}
            </Btn>
          </div>
        </Section>
    </>
  );

  return (
    <SplitPair
      initial={475}
      min={430}
      left={leftPane}
      right={
        <div className="h-full min-h-[560px]" style={{ background: "var(--wb-viewport)", borderRadius: 10 }}>
          <PairViewport pair={pair} position={position} />
        </div>
      }
    />
  );
}
