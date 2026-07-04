"use client";

// Stage design panel (M6): the product vision's entry paths — FZG preset, STplus .ste import,
// or fully parametric — with the tool reference profile (DIN 3972 presets), per-flank
// micro-geometry (ISO 21771 §6, carried for the load-distribution step) and ISO 1328
// tolerances. "Übernehmen" publishes the stage app-wide (mesh, contour, deck, variation).

import { useEffect, useRef, useState } from "react";
import {
  designApi,
  toleranceApi,
  type PresetsResponse,
  type StageParams,
  type ToleranceResponse,
} from "@/lib/api";
import { useStage } from "@/lib/stage";
import { AttrRow, Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { useT } from "@/lib/i18n";

export function DesignPanel() {
  const t = useT();
  const { stage, setStage, setLabel } = useStage();
  const [draft, setDraft] = useState<StageParams>(stage);
  const [presets, setPresets] = useState<PresetsResponse | null>(null);
  const [tol, setTol] = useState<ToleranceResponse | null>(null);
  const [grade, setGrade] = useState(8);
  const [notes, setNotes] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    designApi.presets().then(setPresets).catch(() => setPresets(null));
  }, []);

  useEffect(() => {
    // the draft follows external stage changes (Geometrie tab edits, Variation-Übernehmen)
    // so this panel never shows a stale copy of the single source of truth
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDraft(stage);
  }, [stage]);

  const set = (k: keyof StageParams) => (v: number) =>
    setDraft({ ...draft, use_example: false, [k]: v });

  const applyPreset = (id: string) => {
    const p = presets?.presets.find((x) => x.id === id);
    if (p) {
      setDraft(p.params);
      setNotes([]);
      setLabel(p.name);
    }
  };

  const applyTool = (id: string) => {
    const tool = presets?.tools[id];
    if (tool) {
      setDraft({
        ...draft,
        use_example: false,
        tool_addendum_factor: tool.addendum_factor,
        tool_tip_radius_factor: tool.tip_radius_factor,
      });
    }
  };

  const importSte = async (file: File) => {
    setBusy(true);
    setErr(null);
    try {
      const text = await file.text();
      const res = await designApi.importSte(text);
      setDraft(res.params);
      setNotes(res.notes);
      setLabel(file.name.replace(/\.ste$/i, ""));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const runTolerances = async () => {
    setBusy(true);
    setErr(null);
    try {
      setTol(
        await toleranceApi.tolerances({
          accuracy_grade: grade,
          normal_module_mm: draft.normal_module_mm,
          teeth: draft.teeth_wheel,
          reference_diameter_mm: draft.normal_module_mm * draft.teeth_wheel,
          face_width_mm: draft.face_width_wheel_mm,
          helix_angle_deg: draft.helix_angle_deg,
        }),
      );
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const modsActive =
    JSON.stringify(draft.modifications_pinion ?? {}) !== "{}" ||
    JSON.stringify(draft.modifications_wheel ?? {}) !== "{}";

  return (
    <div className="grid grid-cols-[420px_1fr] gap-3 items-start">
      <div className="flex flex-col gap-3">
        <Section title={t("design.source")}>
          <div className="p-2 flex items-center gap-2 flex-wrap">
            <select
              className="border border-zinc-300 rounded-md px-2 py-1 text-[12px]"
              defaultValue=""
              onChange={(e) => e.target.value && applyPreset(e.target.value)}
            >
              <option value="" disabled>
                {t("design.preset")}
              </option>
              {presets?.presets.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <Btn variant="ghost" onClick={() => fileRef.current?.click()} busy={busy}>
              {t("design.uploadSte")}
            </Btn>
            <input
              ref={fileRef}
              type="file"
              accept=".ste"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void importSte(f);
              }}
            />
            <span className="text-[11.5px] text-zinc-400">{t("design.orEdit")}</span>
          </div>
        </Section>

        <Section title={t("geo.main")}>
          <table className="attr-table">
            <thead>
              <tr>
                <th>{t("common.attribute")}</th>
                <th></th>
                <th>{t("common.pinion")}</th>
                <th>{t("common.wheel")}</th>
                <th>{t("common.unit")}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Normalmodul</td>
                <td className="wb-num text-zinc-400">m_n</td>
                <td colSpan={2}>
                  <Num value={draft.normal_module_mm} onChange={set("normal_module_mm")} />
                </td>
                <td className="text-zinc-400">mm</td>
              </tr>
              <tr>
                <td>Zähnezahl</td>
                <td className="wb-num text-zinc-400">z</td>
                <td>
                  <Num value={draft.teeth_pinion} onChange={set("teeth_pinion")} step={1} />
                </td>
                <td>
                  <Num value={draft.teeth_wheel} onChange={set("teeth_wheel")} step={1} />
                </td>
                <td></td>
              </tr>
              <tr>
                <td>Profilverschiebung</td>
                <td className="wb-num text-zinc-400">x</td>
                <td>
                  <Num value={draft.profile_shift_pinion} onChange={set("profile_shift_pinion")} />
                </td>
                <td>
                  <Num value={draft.profile_shift_wheel} onChange={set("profile_shift_wheel")} />
                </td>
                <td></td>
              </tr>
              <tr>
                <td>Zahnbreite</td>
                <td className="wb-num text-zinc-400">b</td>
                <td>
                  <Num value={draft.face_width_pinion_mm} onChange={set("face_width_pinion_mm")} />
                </td>
                <td>
                  <Num value={draft.face_width_wheel_mm} onChange={set("face_width_wheel_mm")} />
                </td>
                <td className="text-zinc-400">mm</td>
              </tr>
              <tr>
                <td>Eingriffswinkel</td>
                <td className="wb-num text-zinc-400">α_n</td>
                <td colSpan={2}>
                  <Num
                    value={draft.normal_pressure_angle_deg}
                    onChange={set("normal_pressure_angle_deg")}
                  />
                </td>
                <td className="text-zinc-400">°</td>
              </tr>
              <tr>
                <td>Schrägungswinkel</td>
                <td className="wb-num text-zinc-400">β</td>
                <td colSpan={2}>
                  <Num value={draft.helix_angle_deg} onChange={set("helix_angle_deg")} />
                </td>
                <td className="text-zinc-400">°</td>
              </tr>
            </tbody>
          </table>
        </Section>

        <Section title={t("design.tool")} defaultOpen={false}>
          <div className="p-2">
            <select
              className="border border-zinc-300 rounded-md px-2 py-1 text-[12px] w-full"
              defaultValue=""
              onChange={(e) => e.target.value && applyTool(e.target.value)}
            >
              <option value="" disabled>
                {t("design.toolPreset")}
              </option>
              {presets &&
                Object.entries(presets.tools).map(([id, tp]) => (
                  <option key={id} value={id}>
                    {tp.label}
                  </option>
                ))}
            </select>
          </div>
          <table className="attr-table">
            <tbody>
              <AttrRow label="Kopfhöhenfaktor" symbol="h_aP0*" unit="·m_n">
                <td>
                  <Num value={draft.tool_addendum_factor} onChange={set("tool_addendum_factor")} />
                </td>
              </AttrRow>
              <AttrRow label="Kopfrundung" symbol="ρ_aP0*" unit="·m_n">
                <td>
                  <Num
                    value={draft.tool_tip_radius_factor}
                    onChange={set("tool_tip_radius_factor")}
                  />
                </td>
              </AttrRow>
            </tbody>
          </table>
        </Section>

        <Section title={t("design.micro")} defaultOpen={false}>
          <MicroEditor
            value={draft}
            onChange={(d) => setDraft({ ...d, use_example: false })}
          />
          <div className="px-3 pb-2 text-[11px] text-zinc-400">
            {t("design.microNote")}
          </div>
        </Section>

        <div className="flex items-center gap-2">
          <Btn
            onClick={() => {
              setStage(draft);
              if (!draft.use_example) setLabel("frei");
            }}
          >
            {t("design.apply")}
          </Btn>
          {modsActive && (
            <span className="text-[11px] text-amber-600">{t("design.microActive")}</span>
          )}
        </div>
        {err && <ErrNote>{err}</ErrNote>}
        {notes.map((n, i) => (
          <div
            key={i}
            className="text-[12px] text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-1.5"
          >
            ⚠ {n}
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-3">
        <div className="grid grid-cols-3 gap-2">
          <Stat
            label="Achsabstand-Vorgabe"
            value={draft.center_distance_mm ? draft.center_distance_mm.toFixed(2) : "frei"}
            unit={draft.center_distance_mm ? "mm" : undefined}
          />
          <Stat label="Übersetzung u" value={(draft.teeth_wheel / draft.teeth_pinion).toFixed(3)} />
          <Stat
            label="Quelle"
            value={draft.use_example ? "kst-E" : "parametrisch"}
          />
        </div>

        <Section title={t("design.tolerances")}>
          <div className="p-2 flex items-center gap-2">
            <span className="text-[12px] text-zinc-600">{t("design.grade")}</span>
            <Num value={grade} onChange={(v) => setGrade(Math.round(v))} step={1} width={64} />
            <Btn variant="ghost" onClick={() => void runTolerances()} busy={busy}>
              ISO 1328-1
            </Btn>
          </div>
          {tol && (
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
                <AttrRow label="Einzelteilungsabweichung" symbol="f_ptT" unit="µm">
                  <td className="wb-num">{tol.tolerances.single_pitch.toFixed(1)}</td>
                </AttrRow>
                <AttrRow label="Gesamtteilungsabweichung" symbol="F_pT" unit="µm">
                  <td className="wb-num">{tol.tolerances.total_pitch.toFixed(1)}</td>
                </AttrRow>
                <AttrRow label="Profil-Formabweichung" symbol="f_fαT" unit="µm">
                  <td className="wb-num">{tol.tolerances.profile_form.toFixed(1)}</td>
                </AttrRow>
                <AttrRow label="Profil-Gesamtabweichung" symbol="F_αT" unit="µm">
                  <td className="wb-num">{tol.tolerances.profile_total.toFixed(1)}</td>
                </AttrRow>
                <AttrRow label="Flankenlinien-Gesamtabweichung" symbol="F_βT" unit="µm">
                  <td className="wb-num">{tol.tolerances.helix_total.toFixed(1)}</td>
                </AttrRow>
                <AttrRow label="Eingriffsteilungsabweichung" symbol="f_pb" unit="µm">
                  <td className="wb-num">{tol.base_pitch_deviation_um.toFixed(1)}</td>
                </AttrRow>
              </tbody>
            </table>
          )}
          {tol?.warnings.map((w, i) => (
            <div key={i} className="px-3 py-1 text-[11.5px] text-amber-600">
              ⚠ {w}
            </div>
          ))}
        </Section>
      </div>
    </div>
  );
}

function MicroEditor(props: { value: StageParams; onChange: (s: StageParams) => void }) {
  const t = useT();
  const gears: ("modifications_pinion" | "modifications_wheel")[] = [
    "modifications_pinion",
    "modifications_wheel",
  ];
  const fields: { key: "tip_relief_um" | "helix_crowning_um" | "end_relief_um"; label: string; symbol: string }[] = [
    { key: "tip_relief_um", label: "Kopfrücknahme", symbol: "C_αa" },
    { key: "helix_crowning_um", label: "Breitenballigkeit", symbol: "C_β" },
    { key: "end_relief_um", label: "Endrücknahme", symbol: "C_βe" },
  ];
  return (
    <table className="attr-table">
      <thead>
        <tr>
          <th>{t("common.attribute")}</th>
          <th></th>
          <th>links</th>
          <th>rechts</th>
          <th>{t("common.unit")}</th>
        </tr>
      </thead>
      <tbody>
        {gears.map((g) =>
          fields.map((f) => {
            const mods = props.value[g] ?? {};
            return (
              <tr key={`${g}-${f.key}`}>
                <td>
                  {g === "modifications_pinion" ? t("common.pinion") : t("common.wheel")} · {f.label}
                </td>
                <td className="wb-num text-zinc-400">{f.symbol}</td>
                {(["left", "right"] as const).map((side) => (
                  <td key={side}>
                    <Num
                      width={70}
                      value={mods[side]?.[f.key] ?? 0}
                      onChange={(v) =>
                        props.onChange({
                          ...props.value,
                          [g]: { ...mods, [side]: { ...(mods[side] ?? {}), [f.key]: v } },
                        })
                      }
                    />
                  </td>
                ))}
                <td className="text-zinc-400">µm</td>
              </tr>
            );
          }),
        )}
      </tbody>
    </table>
  );
}
