"use client";

// FE rolling-model panel (M6): both gears of the current stage in one dark viewport —
// exactly the combined .inp assembly — with co-moving DOF triads (locked 1–5 gray, free
// rotation green/amber), a roll slider (kinematic coupling), and the deck download with
// the mixed-pairing rigid-shell rule.

import { useState } from "react";
import { meshApi, type FilletSpec, type Mesh3DResponse } from "@/lib/api";
import { useStage } from "@/lib/stage";
import { PairViewport } from "@/components/PairViewport";
import { AttrRow, Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { useT } from "@/lib/i18n";

export function PairPanel() {
  const t = useT();
  const { stage, label } = useStage();
  const [wheel, setWheel] = useState<Mesh3DResponse | null>(null);
  const [pinion, setPinion] = useState<Mesh3DResponse | null>(null);
  const [roll, setRoll] = useState(0);
  const [layers, setLayers] = useState(6);
  const [refineRoot, setRefineRoot] = useState(1);
  const [refineFlank, setRefineFlank] = useState(1);
  const [filletWheel, setFilletWheel] = useState<FilletSpec>({ kind: "standard" });
  const [torque, setTorque] = useState(20000);
  const [rollPositions, setRollPositions] = useState(30);
  const [steelShell, setSteelShell] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

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
      const [w, p] = await Promise.all([
        meshApi.mesh3d({ ...base, gear: 2, fillet: filletWheel }, layers),
        meshApi.mesh3d({ ...base, gear: 1, fillet: { kind: "standard" } }, layers),
      ]);
      setWheel(w);
      setPinion(p);
    });

  const downloadDeck = () =>
    guard("deck", async () => {
      const text = await meshApi.deck({
        stage,
        wheel_torque_nmm: torque,
        face_layers: layers,
        n_roll_positions: rollPositions,
        refine_root: refineRoot,
        refine_flank: refineFlank,
        steel_shell: steelShell,
        fillet_wheel: filletWheel,
      });
      const blob = new Blob([text], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "implicit_rolling_generated.inp";
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

        <Btn onClick={generate} busy={busy === "pair"}>
          {t("pair.generate")}
        </Btn>
        {err && <ErrNote>{err}</ErrNote>}

        {wheel && pinion && (
          <>
            <div className="grid grid-cols-2 gap-2">
              <Stat label={`${t("common.wheel")} · ${t("mesh.hexes")}`} value={wheel.n_hexes.toLocaleString("de-DE")} />
              <Stat label={`${t("common.pinion")} · ${t("mesh.hexes")}`} value={pinion.n_hexes.toLocaleString("de-DE")} />
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
                  <span className="wb-num">φ₁ = {roll.toFixed(1)}°</span>
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
                  <Num value={torque} onChange={setTorque} />
                </td>
              </AttrRow>
              <AttrRow label={t("deck.rollPositions")} symbol="n_W" unit="–">
                <td>
                  <Num value={rollPositions} onChange={setRollPositions} step={1} />
                </td>
              </AttrRow>
              <AttrRow label={t("mesh.fillet")} symbol="" unit="">
                <td>
                  <select
                    value={filletWheel.kind}
                    onChange={(e) => setFilletWheel({ kind: e.target.value as FilletSpec["kind"] })}
                  >
                    {["standard", "trochoid", "elliptic", "bezier", "bionic"].map((k) => (
                      <option key={k} value={k}>
                        {t(`mesh.fillet.${k}`)}
                      </option>
                    ))}
                  </select>
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
          wheel={wheel}
          pinion={pinion}
          centerDistance={centerDistance}
          teethWheel={stage.teeth_wheel}
          teethPinion={stage.teeth_pinion}
          rollDeg={roll}
        />
      </div>
    </div>
  );
}
