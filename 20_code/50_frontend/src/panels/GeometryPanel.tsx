"use client";

// Stage geometry editor. Edits write into THE shared stage (single source of truth,
// user decision 2026-07-04) — every other tab (capacity, tolerances, tooth form, mesh,
// deck) derives from the same StageParams, so nothing can diverge. Results are the
// canonical GearStage values from /api/geometry (DIN ISO 21771).

import { useEffect, useState } from "react";
import {
  api,
  type Din3967AllowanceSeries,
  type GearReport,
  type GeometryReportResponse,
  type GeometryResponse,
  type PairReport,
  type StageParams,
} from "@/lib/api";
import { AttrRow, Btn, ErrNote, Num, Section, Stat } from "@/components/ui";
import { MeshEngagement } from "@/components/MeshEngagement";
import { useStage } from "@/lib/stage";
import { useWorkbench } from "@/lib/store";
import { useFmt, useT } from "@/lib/i18n";

// data-driven result rows: per-gear (Ritzel/Rad columns) and pair (colspan) values
type GearRow = { k: keyof GearReport; sym: string; unit?: string; d?: number };
type PairRow = { k: keyof PairReport; sym: string; unit?: string; d?: number };

const SEC_PITCHES: PairRow[] = [
  // pair quantities the .sta reference prints (audit COV-04: computed but invisible)
  { k: "transverse_module_mm", sym: "m_t", unit: "mm" },
  { k: "transverse_pressure_angle_deg", sym: "α_t", unit: "°" },
  { k: "base_helix_angle_deg", sym: "β_b", unit: "°" },
  { k: "gear_ratio", sym: "u" },
  { k: "reference_center_distance_mm", sym: "a_d", unit: "mm" },
  { k: "profile_shift_sum", sym: "Σx", d: 4 },
  { k: "common_face_width_mm", sym: "b_gem", unit: "mm" },
  { k: "transverse_pitch_mm", sym: "p_t", unit: "mm" },
  { k: "normal_pitch_mm", sym: "p_n", unit: "mm" },
  { k: "transverse_base_pitch_mm", sym: "p_et", unit: "mm" },
  { k: "normal_base_pitch_mm", sym: "p_en", unit: "mm" },
  { k: "path_of_contact_mm", sym: "g_α", unit: "mm" },
  { k: "common_tooth_height_mm", sym: "h_gem", unit: "mm" },
  { k: "common_height_factor", sym: "h_*" },
];
const SEC_DIAMETERS: GearRow[] = [
  { k: "working_pitch_diameter_mm", sym: "d_w", unit: "mm" },
  { k: "reference_diameter_mm", sym: "d", unit: "mm" },
  { k: "base_diameter_mm", sym: "d_b", unit: "mm" },
  { k: "tip_diameter_mm", sym: "d_a", unit: "mm" },
  { k: "tip_form_diameter_mm", sym: "d_Fa", unit: "mm" },
  { k: "tip_chamfer_radial_mm", sym: "h_K", unit: "mm" },
  { k: "usable_tip_diameter_mm", sym: "d_Na", unit: "mm" },
  { k: "usable_root_diameter_mm", sym: "d_Nf", unit: "mm" },
  { k: "root_form_diameter_mm", sym: "d_Ff", unit: "mm" },
  { k: "form_reserve_mm", sym: "c_n", unit: "mm" },
  { k: "root_diameter_mm", sym: "d_f", unit: "mm" },
  { k: "effective_root_diameter_mm", sym: "d_f,eff", unit: "mm" },
];
const SEC_HEIGHTS: GearRow[] = [
  { k: "tooth_height_mm", sym: "h", unit: "mm" },
  { k: "addendum_mm", sym: "h_a", unit: "mm" },
  { k: "addendum_factor_actual", sym: "h_aP*" },
  { k: "tip_clearance_mm", sym: "c", unit: "mm" },
  { k: "tip_path_of_contact_mm", sym: "g_αa", unit: "mm" },
  { k: "sliding_factor_tip", sym: "K_ga" },
  { k: "specific_sliding_tip", sym: "ζ_a" },
  { k: "specific_sliding_root", sym: "ζ_f" },
];
const SEC_THICKNESS: GearRow[] = [
  { k: "tooth_thickness_transverse_mm", sym: "s_t", unit: "mm" },
  { k: "tooth_thickness_normal_mm", sym: "s_n", unit: "mm" },
  { k: "space_width_normal_mm", sym: "e_n", unit: "mm" },
  { k: "tip_tooth_thickness_mm", sym: "s_a", unit: "mm" },
  { k: "rest_tip_thickness_mm", sym: "s_aK", unit: "mm" },
  { k: "thickness_allowance_upper_mm", sym: "E_sns", unit: "mm" },
  { k: "thickness_allowance_lower_mm", sym: "E_sni", unit: "mm" },
  { k: "generation_profile_shift", sym: "x_E", d: 4 },
  { k: "undercut_min_shift", sym: "x_E,min", d: 4 },
  // boolean verdict next to the limit (audit COV-03; fmtCell renders ✓/✗)
  { k: "has_undercut", sym: "Unterschnitt" },
];
const SEC_INSPECTION: GearRow[] = [
  { k: "chordal_thickness_mm", sym: "s̄_cn", unit: "mm" },
  { k: "chordal_height_mm", sym: "h̄_c", unit: "mm" },
  { k: "span_teeth", sym: "k", d: 0 },
  // valid k-range (DIN 21773 eq. 12/13 — audit COV-03: computed but invisible)
  { k: "span_teeth_min", sym: "k_min", d: 0 },
  { k: "span_teeth_max", sym: "k_max", d: 0 },
  { k: "span_measurement_mm", sym: "W_k", unit: "mm" },
  { k: "span_allowance_upper_mm", sym: "A_We", unit: "mm" },
  { k: "span_allowance_lower_mm", sym: "A_Wi", unit: "mm" },
  { k: "span_contact_diameter_mm", sym: "d_M(W)", unit: "mm" },
  { k: "ball_diameter_mm", sym: "D_M", unit: "mm" },
  { k: "two_ball_measure_mm", sym: "M_dK", unit: "mm" },
  { k: "two_roller_measure_mm", sym: "M_dR", unit: "mm" },
  { k: "ball_allowance_upper_mm", sym: "E_Mds", unit: "mm" },
  { k: "ball_allowance_lower_mm", sym: "E_Mdi", unit: "mm" },
  { k: "ball_allowance_factor", sym: "E_Md/E_sn" },
  { k: "ball_contact_diameter_mm", sym: "d_M(K)", unit: "mm" },
];
const SEC_TOOL: GearRow[] = [
  { k: "tool_module_mm", sym: "m_n0", unit: "mm" },
  { k: "tool_pressure_angle_deg", sym: "α_n0", unit: "°" },
  { k: "tool_addendum_factor", sym: "h_aP0*" },
  // per-gear tool dedendum (audit COV-03: kst-E's 1.1/1.25 difference was half-hidden)
  { k: "tool_dedendum_factor", sym: "h_fP0*" },
  { k: "tool_tip_radius_factor", sym: "ρ_aP0*" },
];

function ReportSection(props: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const t = useT();
  return (
    <Section title={props.title} defaultOpen={props.defaultOpen}>
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
        <tbody>{props.children}</tbody>
      </table>
    </Section>
  );
}

function fmtCell(
  fm: ReturnType<typeof useFmt>,
  v: number | boolean | null | undefined,
  digits: number,
): string {
  if (v == null) return "–";
  if (typeof v === "boolean") return v ? "✓" : "–";
  return digits === 0 ? fm.int(v) : fm.num(v, digits);
}

function GearRows(props: { rows: GearRow[]; g1: GearReport; g2: GearReport }) {
  const t = useT();
  const fm = useFmt();
  return (
    <>
      {props.rows.map((r) => {
        const v1 = props.g1[r.k];
        const v2 = props.g2[r.k];
        if (v1 == null && v2 == null) return null;
        return (
          <AttrRow key={r.k} label={t(`gr.${r.k}`)} symbol={r.sym} unit={r.unit ?? "–"}>
            <td className="wb-num">{fmtCell(fm, v1, r.d ?? 3)}</td>
            <td className="wb-num">{fmtCell(fm, v2, r.d ?? 3)}</td>
          </AttrRow>
        );
      })}
    </>
  );
}

function PairRows(props: { rows: PairRow[]; p: PairReport }) {
  const t = useT();
  const fm = useFmt();
  return (
    <>
      {props.rows.map((r) => {
        const v = props.p[r.k];
        if (v == null || Array.isArray(v)) return null;
        return (
          <AttrRow key={r.k} label={t(`gr.${r.k}`)} symbol={r.sym} unit={r.unit ?? "–"}>
            <td className="wb-num" colSpan={2}>
              {fmtCell(fm, v as number, r.d ?? 3)}
            </td>
          </AttrRow>
        );
      })}
    </>
  );
}

const DIN3967_ALLOWANCE_SERIES = ["a", "ab", "b", "bc", "c", "cd", "d", "e", "f", "g", "h"] as const;
const DIN3967_TOLERANCE_SERIES = [21, 22, 23, 24, 25, 26, 27, 28, 29, 30] as const;

// DIN 3967 series picker: resolves a designation (e.g. "27cd") via the backend tables and
// fills the SSOT span-allowance inputs (tol.awe/awi in µm) — the whole chain (x_E, deck,
// report, backlash) then follows from the ONE store source. Direct input stays possible.
function Din3967Section() {
  const t = useT();
  const { stage } = useStage();
  const wb = useWorkbench();
  const [series, setSeries] = useState<{ a1: string; t1: number; a2: string; t2: number }>({
    a1: "",
    t1: 0,
    a2: "",
    t2: 0,
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const complete = series.a1 !== "" && series.t1 > 0 && series.a2 !== "" && series.t2 > 0;

  const apply = async () => {
    setBusy(true);
    setErr(null);
    try {
      const rep = await api.geometryReport({
        stage,
        allowance_series_gear1: series.a1 as Din3967AllowanceSeries,
        tolerance_series_gear1: series.t1,
        allowance_series_gear2: series.a2 as Din3967AllowanceSeries,
        tolerance_series_gear2: series.t2,
      });
      wb.set("tol.awe1_um", Math.round((rep.gear1.span_allowance_upper_mm ?? 0) * 1e4) / 10);
      wb.set("tol.awi1_um", Math.round((rep.gear1.span_allowance_lower_mm ?? 0) * 1e4) / 10);
      wb.set("tol.awe2_um", Math.round((rep.gear2.span_allowance_upper_mm ?? 0) * 1e4) / 10);
      wb.set("tol.awi2_um", Math.round((rep.gear2.span_allowance_lower_mm ?? 0) * 1e4) / 10);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const seriesSelect = (gear: 1 | 2) => {
    const aKey = gear === 1 ? "a1" : "a2";
    const tKey = gear === 1 ? "t1" : "t2";
    return (
      <tr>
        <td>{`${t("common.gear")} ${gear}`}</td>
        <td className="wb-num text-zinc-400">{gear === 1 ? "R1" : "R2"}</td>
        <td>
          <select
            value={series[aKey as "a1"]}
            onChange={(e) => setSeries({ ...series, [aKey]: e.target.value })}
          >
            <option value="">{t("geo.din3967.none")}</option>
            {DIN3967_ALLOWANCE_SERIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </td>
        <td>
          <select
            value={series[tKey as "t1"]}
            onChange={(e) => setSeries({ ...series, [tKey]: Number(e.target.value) })}
          >
            <option value={0}>{t("geo.din3967.none")}</option>
            {DIN3967_TOLERANCE_SERIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </td>
        <td className="wb-num text-zinc-400">
          {series[aKey as "a1"] && series[tKey as "t1"] > 0
            ? `${series[tKey as "t1"]}${series[aKey as "a1"]}`
            : "–"}
        </td>
      </tr>
    );
  };

  return (
    <Section title={t("geo.din3967")} defaultOpen={false}>
      <table className="attr-table">
        <thead>
          <tr>
            <th>{t("common.attribute")}</th>
            <th></th>
            <th>{t("geo.din3967.series")}</th>
            <th>{t("geo.din3967.tolerance")}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {seriesSelect(1)}
          {seriesSelect(2)}
        </tbody>
      </table>
      <div className="p-2 flex items-center gap-2 border-t border-zinc-100">
        <Btn onClick={() => void apply()} busy={busy} disabled={!complete}>
          {t("geo.din3967.apply")}
        </Btn>
      </div>
      <div className="text-[11.5px] text-zinc-500 px-2 pb-2">{t("geo.din3967.note")}</div>
      {err && <ErrNote>{err}</ErrNote>}
    </Section>
  );
}

export function GeometryPanel() {
  const t = useT();
  const fm = useFmt();
  const { stage, setStage } = useStage();
  const wb = useWorkbench();
  const aMode = wb.geometryUi.center_distance_mode;
  const [res, setRes] = useState<GeometryResponse | null>(null);
  const [rep, setRep] = useState<GeometryReportResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async (s: StageParams) => {
    setBusy(true);
    setErr(null);
    try {
      // the quick summary and the FULL SSOT report (fillet-aware via the shared store)
      const [geo, full] = await Promise.all([
        api.geometry(s),
        api.geometryReport({
          stage: s,
          fillet_gear1: wb.fem.fillet_gear1,
          fillet_gear2: wb.fem.fillet_gear2,
          // full allowance BAND per gear (audit COV-01: without these the backend fell
          // back to the stage's mean, so E_sns/E_sni always showed the same number)
          span_allowance_upper_um: [wb.tol.awe1_um, wb.tol.awe2_um],
          span_allowance_lower_um: [wb.tol.awi1_um, wb.tol.awi2_um],
          center_distance_allowance_mm: (wb.tol.a_upper_um - wb.tol.a_lower_um) / 2 / 1000,
        }),
      ]);
      setRes(geo);
      setRep(full);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    // recompute whenever the shared stage changes (edits here or in any other tab)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void run(stage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage, wb.fem.fillet_gear1, wb.fem.fillet_gear2]);

  // editing a geometry value leaves the kst-E example mode (free parameters from then on)
  const set = (k: keyof StageParams) => (v: number) =>
    setStage({ ...stage, use_example: false, [k]: v });

  return (
    <div className="grid grid-cols-[460px_1fr] gap-3 items-start">
      <div className="flex flex-col gap-3">
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
                <td>{t("attr.mn")}</td>
                <td className="wb-num text-zinc-400">m_n</td>
                <td colSpan={2}><Num value={stage.normal_module_mm} onChange={set("normal_module_mm")} /></td>
                <td className="text-zinc-400">mm</td>
              </tr>
              <tr>
                <td>{t("attr.alpha")}</td>
                <td className="wb-num text-zinc-400">α_n</td>
                <td colSpan={2}><Num value={stage.normal_pressure_angle_deg} onChange={set("normal_pressure_angle_deg")} /></td>
                <td className="text-zinc-400">°</td>
              </tr>
              <tr>
                <td>{t("attr.z")}</td>
                <td className="wb-num text-zinc-400">z</td>
                <td><Num value={stage.teeth_pinion} onChange={set("teeth_pinion")} step={1} /></td>
                <td><Num value={stage.teeth_wheel} onChange={set("teeth_wheel")} step={1} /></td>
                <td></td>
              </tr>
              <tr>
                <td>{t("attr.xShort")}</td>
                <td className="wb-num text-zinc-400">x</td>
                <td><Num value={stage.profile_shift_pinion} onChange={set("profile_shift_pinion")} /></td>
                <td><Num value={stage.profile_shift_wheel} onChange={set("profile_shift_wheel")} /></td>
                <td></td>
              </tr>
              <tr>
                <td>{t("attr.beta")}</td>
                <td className="wb-num text-zinc-400">β</td>
                <td colSpan={2}><Num value={stage.helix_angle_deg} onChange={set("helix_angle_deg")} /></td>
                <td className="text-zinc-400">°</td>
              </tr>
              <tr>
                <td>{t("attr.b")}</td>
                <td className="wb-num text-zinc-400">b</td>
                <td><Num value={stage.face_width_pinion_mm} onChange={set("face_width_pinion_mm")} /></td>
                <td><Num value={stage.face_width_wheel_mm} onChange={set("face_width_wheel_mm")} /></td>
                <td className="text-zinc-400">mm</td>
              </tr>
              <tr>
                <td>{t("geo.aMode")}</td>
                <td></td>
                <td colSpan={2}>
                  <select
                    value={aMode}
                    onChange={(e) => wb.set("geometryUi.center_distance_mode", e.target.value)}
                  >
                    <option value="a_and_x">{t("geo.aModeAX")}</option>
                    <option value="from_x">{t("geo.aModeFromX")}</option>
                  </select>
                </td>
                <td></td>
              </tr>
              <tr title={t("geo.aModeNote")}>
                <td>{t("attr.a")}</td>
                <td className="wb-num text-zinc-400">a</td>
                <td colSpan={2}>
                  {aMode === "from_x" ? (
                    <input type="number" disabled value={res?.working_center_distance_mm ?? ""} />
                  ) : (
                    <Num
                      value={stage.center_distance_mm ?? res?.working_center_distance_mm ?? 0}
                      onChange={set("center_distance_mm")}
                    />
                  )}
                </td>
                <td className="text-zinc-400">mm</td>
              </tr>
            </tbody>
          </table>
          <div className="p-2 border-t border-zinc-100">
            <Btn onClick={() => void run(stage)} busy={busy}>
              {t("common.run")}
            </Btn>
          </div>
        </Section>
        <Din3967Section />
        {err && <ErrNote>{err}</ErrNote>}
      </div>

      {res && (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-3 gap-2">
            <Stat label={`${t("attr.epsAlpha")} ε_α`} value={fm.num(res.transverse_contact_ratio, 3)} tone={res.valid ? "good" : "bad"} />
            <Stat label={`${t("attr.epsBeta")} ε_β`} value={fm.num(res.overlap_ratio, 3)} />
            <Stat label={`${t("attr.epsGamma")} ε_γ`} value={fm.num(res.total_contact_ratio, 3)} />
          </div>
          {rep ? (
            <>
              <ReportSection title={t("gr.sec.pitches")}>
                <AttrRow label={t("attr.aw")} symbol="a_w" unit="mm">
                  <td className="wb-num" colSpan={2}>{fm.num(rep.pair.center_distance_mm, 3)}</td>
                </AttrRow>
                <AttrRow label={t("attr.alphaWt")} symbol="α_wt" unit="°">
                  <td className="wb-num" colSpan={2}>{fm.num(rep.pair.working_pressure_angle_deg, 3)}</td>
                </AttrRow>
                <PairRows rows={SEC_PITCHES} p={rep.pair} />
              </ReportSection>
              <ReportSection title={t("gr.sec.diameters")}>
                <GearRows rows={SEC_DIAMETERS} g1={rep.gear1} g2={rep.gear2} />
              </ReportSection>
              <ReportSection title={t("gr.sec.heights")}>
                <GearRows rows={SEC_HEIGHTS} g1={rep.gear1} g2={rep.gear2} />
              </ReportSection>
              <ReportSection title={t("gr.sec.thickness")}>
                <GearRows rows={SEC_THICKNESS} g1={rep.gear1} g2={rep.gear2} />
              </ReportSection>
              <ReportSection title={t("gr.sec.inspection")}>
                <GearRows rows={SEC_INSPECTION} g1={rep.gear1} g2={rep.gear2} />
              </ReportSection>
              <ReportSection title={t("gr.sec.backlash")}>
                <AttrRow label={t("gr.backlash_circumferential_mm")} symbol="j_t" unit="mm">
                  <td className="wb-num" colSpan={2}>{fm.num(rep.pair.backlash_circumferential_mm, 3)}</td>
                </AttrRow>
                <AttrRow label={t("gr.backlash_normal_mm")} symbol="j_n" unit="mm">
                  <td className="wb-num" colSpan={2}>{fm.num(rep.pair.backlash_normal_mm, 3)}</td>
                </AttrRow>
                <AttrRow label={t("gr.backlash_delta")} symbol="Δj_t/Δj_n" unit="mm">
                  <td className="wb-num" colSpan={2}>
                    {rep.pair.backlash_delta_upper_mm
                      ? `±${fm.num(rep.pair.backlash_delta_upper_mm[0], 3)} / ±${fm.num(rep.pair.backlash_delta_upper_mm[1], 3)}`
                      : "–"}
                  </td>
                </AttrRow>
              </ReportSection>
              <ReportSection title={t("gr.sec.tool")} defaultOpen={false}>
                <GearRows rows={SEC_TOOL} g1={rep.gear1} g2={rep.gear2} />
              </ReportSection>
            </>
          ) : (
            <Section title={t("geo.diameters")}>
              <table className="attr-table">
                <tbody>
                  <AttrRow label={t("attr.dCircle")} symbol="d" unit="mm">
                    <td className="wb-num">{fm.num(res.reference_diameter_mm[0], 3)}</td>
                    <td className="wb-num">{fm.num(res.reference_diameter_mm[1], 3)}</td>
                  </AttrRow>
                </tbody>
              </table>
            </Section>
          )}
          {res.notes.map((n, i) => (
            <div key={i} className="text-[12px] text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-1.5">
              ⚠ {n}
            </div>
          ))}
          <MeshEngagement height={340} />
        </div>
      )}
    </div>
  );
}
