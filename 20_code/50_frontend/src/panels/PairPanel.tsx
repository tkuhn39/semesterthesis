"use client";

// FE rolling-model panel (M6): both gears of the current stage in one dark viewport —
// exactly the combined .inp assembly, served by /api/mesh/pair (backend SSOT: closing
// rotation, edge start, rigid shells, fillets, tip relief) — with co-moving DOF triads
// (locked 1–5 gray, free rotation green/amber), a slider over the REAL Wälzstellungen of
// the deck schedule, and the deck download (series ZIP or single INP).

import { useState } from "react";
import { meshApi, type FilletSpec, type PairAssemblyResponse } from "@/lib/api";
import { useStage } from "@/lib/stage";
import { useWorkbench } from "@/lib/store";
import { PairViewport } from "@/components/PairViewport";
import { AttrRow, Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { FilletEditor, ManufacturabilityNote } from "@/panels/ToothFormPanel";
import { useFmt, useT } from "@/lib/i18n";

interface Refine {
  root: number;
  flank: number;
  thickness: number;
}
interface Effective {
  root: number;
  flank: number;
  thickness: number;
}

const toMeshRefine = (r: Refine) => ({
  refine_root: r.root,
  refine_flank: r.flank,
  refine_thickness: r.thickness,
});

export function PairPanel() {
  const t = useT();
  const fm = useFmt();
  const { stage, label } = useStage();
  const wb = useWorkbench();
  const [pair, setPair] = useState<PairAssemblyResponse | null>(null);
  const [position, setPosition] = useState(0); // Wälzstellung k (continuous 0 … n−1)
  const [layers, setLayers] = useState(6);
  // FVA mesh-fineness dialog PER GEAR (user point 7): root = Zahnfuß, flank = Zahnhöhe,
  // thickness = Zahndicke (factors on the reference topology); Zahnbreite = layers, shared
  const [refine1, setRefine1] = useState<Refine>({ root: 1, flank: 1, thickness: 1 });
  const [refine2, setRefine2] = useState<Refine>({ root: 1, flank: 1, thickness: 1 });
  const [eff, setEff] = useState<Record<1 | 2, Effective | null>>({ 1: null, 2: null });
  // root-fillet strategy PER GEAR, chosen BEFORE generating the pair (user point 6,
  // 2026-07-06) — drives the preview mesh AND the deck identically
  const [filletGear1, setFilletGear1] = useState<FilletSpec>({ kind: "standard" });
  const [filletGear2, setFilletGear2] = useState<FilletSpec>({ kind: "standard" });
  const [rollPositions, setRollPositions] = useState(30);
  const [steelShell, setSteelShell] = useState(true);
  const [offsetGear1, setOffsetGear1] = useState(0);
  const [offsetGear2, setOffsetGear2] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  // SSOT (user point 7a): the deck torque M₂ comes from the Leistungsfluss — never a
  // panel-local value (the full PairPanel→store migration follows in phase F)
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

  // ONE payload for preview assembly AND deck download (SSOT — the viewport shows exactly
  // what the .inp contains); the torque is added only for the download
  const deckPayload = () => ({
    stage,
    face_layers: layers,
    n_roll_positions: rollPositions,
    rotation_sense: wb.get("fem.rotation_sense") as "cw" | "ccw",
    roll_pitches: wb.fem.roll_pitches,
    refine_root: refine1.root,
    refine_flank: refine1.flank,
    refine_thickness: refine1.thickness,
    refine_root_gear2: refine2.root,
    refine_flank_gear2: refine2.flank,
    refine_thickness_gear2: refine2.thickness,
    axial_offset_gear1_mm: offsetGear1,
    axial_offset_gear2_mm: offsetGear2,
    steel_shell: steelShell,
    rigid_shell_gear1: wb.fem.rigid_shell_gear1,
    rigid_shell_gear2: wb.fem.rigid_shell_gear2,
    fillet_gear1: filletGear1,
    fillet_gear2: filletGear2,
    align_contact: wb.fem.align_contact,
    fasten_bore: wb.fem.fasten_bore,
    fasten_cuts: wb.fem.fasten_cuts,
    fasten_top: wb.fem.fasten_top,
    fasten_bottom: wb.fem.fasten_bottom,
  });

  const generate = () =>
    guard("pair", async () => {
      // assembly + the effective per-tooth element counts of both 2D sections in parallel
      const [res, p1, p2] = await Promise.all([
        meshApi.pair(deckPayload()),
        meshApi.preview({ stage, gear: 1, ...toMeshRefine(refine1), fillet: filletGear1 }),
        meshApi.preview({ stage, gear: 2, ...toMeshRefine(refine2), fillet: filletGear2 }),
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
      const setR = gear === 1 ? setRefine1 : setRefine2;
      setR((r) => ({
        ...r,
        root: root.converged_level ?? r.root,
        flank: flank.converged_level ?? r.flank,
      }));
    });

  const downloadDeck = () =>
    guard("deck", async () => {
      if (typeof m2 !== "number" || !Number.isFinite(m2)) {
        throw new Error(t("pf.noTorque"));
      }
      const req = { ...deckPayload(), torque_gear2_nmm: m2 };
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

  return (
    <div className="grid grid-cols-[340px_1fr] gap-3 items-start h-full">
      <div className="flex flex-col gap-3 overflow-y-auto pr-1" style={{ maxHeight: "100%" }}>
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
                    const refine = gear === 1 ? refine1 : refine2;
                    const setRefine = gear === 1 ? setRefine1 : setRefine2;
                    const effective = eff[gear];
                    return (
                      <td key={gear}>
                        <span className="inline-flex items-center gap-1.5">
                          <select
                            value={refine[key]}
                            onChange={(e) =>
                              setRefine({ ...refine, [key]: Number(e.target.value) })
                            }
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
                  <Num value={layers} onChange={setLayers} step={1} />
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
                  <Num value={offsetGear1} onChange={setOffsetGear1} step={0.5} />
                </td>
              </AttrRow>
              <AttrRow label={`${t("pair.axialOffset")} · ${t("pair.gear2")}`} symbol="Δz₂" unit="mm">
                <td>
                  <Num value={offsetGear2} onChange={setOffsetGear2} step={0.5} />
                </td>
              </AttrRow>
            </tbody>
          </table>
          <div className="px-2.5 pb-2 text-[11px] text-zinc-500">{t("pair.axialNote")}</div>
        </Section>

        <Section title={`${t("mesh.fillet")} · ${t("pair.gear1")}`} defaultOpen={false}>
          <FilletEditor value={filletGear1} onChange={setFilletGear1} />
          <div className="px-2.5 pb-2">
            <ManufacturabilityNote kind={filletGear1.kind} />
          </div>
        </Section>
        <Section title={`${t("mesh.fillet")} · ${t("pair.gear2")}`} defaultOpen={false}>
          <FilletEditor value={filletGear2} onChange={setFilletGear2} />
          <div className="px-2.5 pb-2">
            <ManufacturabilityNote kind={filletGear2.kind} />
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
                <div className="flex justify-between text-[11px] text-zinc-500">
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
        <PairViewport pair={pair} position={position} />
      </div>
    </div>
  );
}
