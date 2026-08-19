"use client";

// FEM results panel (phase G, user goal 2026-07-06): upload the fem_results.json produced
// by the bundled abaqus_fem_postprocessing.py, then explore it as a 3-D plot per contact
// flank pair — axis 1 = path-of-contact coordinate ξ (relative to C, range beyond A/E down
// to d_Nf…d_Na), axis 2 = face width, axis 3 = selectable σ/ε/CPRESS/u — with a position
// slider over the Wälzstellungen and the frame maximum flagged. The r→ξ unwrapping + the
// A…E markers come from the backend (GearStage SSOT); this panel only renders.

import { useMemo, useState } from "react";
import { femApi, type FemField, type FemResultsResponse } from "@/lib/api";
import { useStage } from "@/lib/stage";
import { FemResultsViewport } from "@/components/FemResultsViewport";
import { SplitPair } from "@/components/SplitPane";
import { AttrRow, ErrNote, Section, Stat } from "@/components/ui";
import { useFmt, useT } from "@/lib/i18n";
import { useWorkbench } from "@/lib/store";

const FIELDS: { id: FemField; unit: string }[] = [
  { id: "s_mises", unit: "MPa" },
  { id: "s_maxp", unit: "MPa" },
  { id: "s_minp", unit: "MPa" },
  { id: "e_mises", unit: "–" },
  { id: "e_maxp", unit: "–" },
  { id: "cpress", unit: "MPa" },
  { id: "u", unit: "mm" },
];

export function FemResultsPanel() {
  const t = useT();
  const fm = useFmt();
  const { stage } = useStage();
  const wb = useWorkbench();
  const [res, setRes] = useState<FemResultsResponse | null>(null);
  const [tag, setTag] = useState<string | null>(null);
  const [field, setField] = useState<FemField>("s_mises");
  const [pos, setPos] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const upload = async (file: File) => {
    setBusy(true);
    setErr(null);
    try {
      const parsed = JSON.parse(await file.text());
      // pass the ACTIVE fillets — the extended-range markers follow their junction
      // radii (audit FEM-04), same specs the deck was built with
      const out = await femApi.results(stage, parsed, {
        fillet_gear1: wb.fem.fillet_gear1,
        fillet_gear2: wb.fem.fillet_gear2,
      });
      setRes(out);
      setTag(out.flank_tags[0] ?? null);
      setPos(0);
      setFileName(file.name);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const frame = res?.frames[Math.min(pos, (res?.frames.length ?? 1) - 1)] ?? null;
  const flank = frame && tag ? frame.flanks[tag] : null;
  const frameMax = flank ? Math.max(...flank[field]) : 0; // this position's peak of the field

  // stable color/height scale: the field maximum over ALL frames of the selected tag
  const vMax = useMemo(() => {
    if (!res || !tag) return 0;
    let m = 0;
    for (const fr of res.frames) {
      const fl = fr.flanks[tag];
      if (!fl) continue;
      for (const v of fl[field]) if (v > m) m = v;
    }
    return m;
  }, [res, tag, field]);

  const leftPane = (
    <>
      <Section title={t("fem.upload")}>
        <div className="p-3 flex flex-col gap-2">
          <p className="text-[11.5px] text-zinc-500 leading-relaxed">{t("fem.uploadHint")}</p>
          <label className="inline-flex items-center gap-2 text-[12px]">
            <span className="border border-zinc-300 rounded-md px-2.5 py-1 bg-white hover:bg-zinc-50 cursor-pointer">
              {busy ? "…" : t("fem.chooseFile")}
              <input
                type="file"
                accept=".json,application/json"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void upload(f);
                }}
              />
            </span>
            {fileName && <span className="text-zinc-500 wb-num">{fileName}</span>}
          </label>
          {err && <ErrNote>{err}</ErrNote>}
        </div>
        {/* provenance (audit GAP-06): the dump is unwrapped with the CURRENT stage —
            say so, and surface the dump's solver mode instead of hiding it */}
        {res && (
          <div className="px-3 py-1.5 text-[11.5px] text-zinc-500 border-t border-zinc-100">
            {t("fem.provenance").replace("{mode}", res.mode)}
          </div>
        )}
      </Section>

      {res && (
        <>
          <div className="grid grid-cols-2 gap-2">
            <Stat label={t("fem.frames")} value={fm.int(res.n_frames)} />
            <Stat label={t("fem.flanks")} value={fm.int(res.flank_tags.length)} />
          </div>

          <Section title={t("fem.selection")}>
            <table className="attr-table">
              <tbody>
                <AttrRow label={t("fem.flankSet")} symbol="" unit="">
                  <td>
                    <select value={tag ?? ""} onChange={(e) => setTag(e.target.value)}>
                      {res.flank_tags.map((tg) => (
                        <option key={tg} value={tg}>
                          {tg}
                        </option>
                      ))}
                    </select>
                  </td>
                </AttrRow>
                <AttrRow label={t("fem.field")} symbol="" unit="">
                  <td>
                    <select value={field} onChange={(e) => setField(e.target.value as FemField)}>
                      {FIELDS.map((f) => (
                        <option key={f.id} value={f.id}>
                          {t(`fem.field.${f.id}`)}
                        </option>
                      ))}
                    </select>
                  </td>
                </AttrRow>
                <AttrRow label={t("fem.maxField")} symbol="max" unit={FIELDS.find((f) => f.id === field)?.unit}>
                  <td className="wb-num text-right" title={t("fem.maxFieldHint")}>
                    {fm.num(vMax, 3)}
                  </td>
                </AttrRow>
              </tbody>
            </table>
          </Section>

          <Section title={t("fem.position")}>
            <div className="p-3">
              <div className="flex flex-wrap justify-between gap-x-2 pb-1.5 text-[11px] text-zinc-500">
                <span>1</span>
                <span className="wb-num">
                  {t("pair.position")} {pos + 1}/{res.n_frames}
                  {frame?.phi_driven_rad != null
                    ? ` · φ = ${((frame.phi_driven_rad * 180) / Math.PI).toFixed(2)}°`
                    : ""}
                  {flank ? ` · max = ${fm.num(frameMax, 1)}` : ""}
                </span>
                <span>{res.n_frames}</span>
              </div>
              <input
                type="range"
                min={0}
                max={Math.max(res.n_frames - 1, 0)}
                step={1}
                value={pos}
                onChange={(e) => setPos(Number(e.target.value))}
                className="w-full"
                disabled={res.n_frames < 2}
              />
            </div>
          </Section>

          <div className="text-[11.5px] text-zinc-500 leading-relaxed border border-zinc-200 rounded-lg bg-white p-2.5">
            <div className="font-medium text-zinc-700 mb-1">{t("fem.legend")}</div>
            <div>{t("fem.axisXi")}</div>
            <div>{t("fem.axisZ")}</div>
            <div>{t("fem.axisField")}</div>
            <div>
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-green-500 mr-1.5" />
              C · A/B/D/E {t("fem.markers")}
            </div>
            <div>
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500 mr-1.5" />
              {t("fem.maxMarker")}
            </div>
          </div>
        </>
      )}
    </>
  );

  return (
    <SplitPair
      initial={400}
      min={360}
      left={leftPane}
      right={
        <div className="h-full min-h-[560px]" style={{ background: "var(--wb-viewport)", borderRadius: 10 }}>
          <FemResultsViewport frame={frame} tag={tag} field={field} markers={res?.markers ?? null} vMax={vMax} />
        </div>
      }
    />
  );
}
