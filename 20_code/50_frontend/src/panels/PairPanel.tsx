"use client";

// FE rolling-model panel (M6): both gears of the current stage in one dark viewport —
// exactly the combined .inp assembly — with co-moving DOF triads (locked 1–5 gray, free
// rotation green/amber), a roll slider (kinematic coupling), and the deck download with
// the mixed-pairing rigid-shell rule.

import { useState } from "react";
import { meshApi, type FilletSpec, type Mesh3DResponse } from "@/lib/api";
import { useStage } from "@/lib/stage";
import { useWorkbench } from "@/lib/store";
import { PairViewport } from "@/components/PairViewport";
import { AttrRow, Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { FilletEditor, ManufacturabilityNote } from "@/panels/ToothFormPanel";
import { useFmt, useT } from "@/lib/i18n";

export function PairPanel() {
  const t = useT();
  const fm = useFmt();
  const { stage, label } = useStage();
  const wb = useWorkbench();
  const [gear1, setGear1] = useState<Mesh3DResponse | null>(null);
  const [gear2, setGear2] = useState<Mesh3DResponse | null>(null);
  const [roll, setRoll] = useState(0);
  const [layers, setLayers] = useState(6);
  const [refineRoot, setRefineRoot] = useState(1);
  const [refineFlank, setRefineFlank] = useState(1);
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

  const generate = () =>
    guard("pair", async () => {
      const base = { stage, refine_root: refineRoot, refine_flank: refineFlank };
      const [g1, g2] = await Promise.all([
        meshApi.mesh3d({ ...base, gear: 1, fillet: filletGear1 }, layers),
        meshApi.mesh3d({ ...base, gear: 2, fillet: filletGear2 }, layers),
      ]);
      setGear1(g1);
      setGear2(g2);
    });

  const downloadDeck = () =>
    guard("deck", async () => {
      if (typeof m2 !== "number" || !Number.isFinite(m2)) {
        throw new Error(t("pf.noTorque"));
      }
      const req = {
        stage,
        torque_gear2_nmm: m2,
        face_layers: layers,
        n_roll_positions: rollPositions,
        rotation_sense: wb.get("fem.rotation_sense") as "cw" | "ccw",
        roll_pitches: wb.fem.roll_pitches,
        refine_root: refineRoot,
        refine_flank: refineFlank,
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
      };
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
          <table className="attr-table">
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

        {gear1 && gear2 && (
          <>
            <div className="grid grid-cols-2 gap-2">
              <Stat label={`${t("pair.gear1")} · ${t("mesh.hexes")}`} value={fm.int(gear1.n_hexes)} />
              <Stat label={`${t("pair.gear2")} · ${t("mesh.hexes")}`} value={fm.int(gear2.n_hexes)} />
            </div>
            <Section title={t("pair.roll")}>
              <div className="p-3">
                <input
                  type="range"
                  min={-15}
                  max={15}
                  step={0.2}
                  value={roll}
                  onChange={(e) => setRoll(Number(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-[11px] text-zinc-500">
                  <span>−15°</span>
                  <span className="wb-num">φ₂ = {roll.toFixed(1)}°</span>
                  <span>+15°</span>
                </div>
              </div>
            </Section>
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
        <PairViewport
          gear1={gear1}
          gear2={gear2}
          centerDistance={centerDistance}
          teethGear1={stage.teeth_pinion}
          teethGear2={stage.teeth_wheel}
          drivenGear={2}
          rollDeg={roll}
          offsetGear1Z={offsetGear1}
          offsetGear2Z={offsetGear2}
        />
      </div>
    </div>
  );
}
