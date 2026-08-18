"use client";

// Tooth-form editor (M5): the real as-cut contour of one gear with the root-fillet strategy
// selectable — standard tool fillet vs elliptic / Bézier / bionic, with live mating-tip
// clearance from the backend interference check.

import { useCallback, useEffect, useState } from "react";
import {
  contourApi,
  defaultApproach,
  FILLET_APPROACHES,
  FILLET_APPROACHES_PENDING,
  meshApi,
  type ContourResponse,
  type FilletCaoResponse,
  type FilletSpec,
} from "@/lib/api";
import { ContourPlot } from "@/components/ContourPlot";
import { AttrRow, Btn, ErrNote, Section, Stat } from "@/components/ui";
import { useFmt, useT } from "@/lib/i18n";
import { useStage } from "@/lib/stage";
import { useWorkbench } from "@/lib/store";

export function FilletEditor(props: { value: FilletSpec; onChange: (f: FilletSpec) => void }) {
  const t = useT();
  const f = props.value;
  const approach = f.approach ?? defaultApproach(f.kind);
  const set = (patch: Partial<FilletSpec>) => props.onChange({ ...f, ...patch });
  const setKind = (kind: FilletSpec["kind"]) =>
    // kind change resets the approach (and stale approach params) to the family default
    props.onChange({ kind, approach: defaultApproach(kind) });
  return (
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
        <AttrRow label={t("mesh.fillet")} symbol="">
          <td>
            <select value={f.kind} onChange={(e) => setKind(e.target.value as FilletSpec["kind"])}>
              <option value="standard">{t("mesh.fillet.standard")}</option>
              <option value="trochoid">{t("mesh.fillet.trochoid")}</option>
              <option value="elliptic">{t("mesh.fillet.elliptic")}</option>
              <option value="bezier">{t("mesh.fillet.bezier")}</option>
              <option value="bionic">{t("mesh.fillet.bionic")}</option>
            </select>
          </td>
        </AttrRow>
        {FILLET_APPROACHES[f.kind] && (
          <AttrRow label={t("mesh.fillet.approach")} symbol="">
            <td>
              <select
                value={approach}
                onChange={(e) => set({ approach: e.target.value as FilletSpec["approach"] })}
              >
                {FILLET_APPROACHES[f.kind].map((a) => (
                  <option key={a} value={a} disabled={FILLET_APPROACHES_PENDING.has(a)}>
                    {t(`mesh.fillet.${f.kind}-${a}`)}
                    {FILLET_APPROACHES_PENDING.has(a) ? ` ${t("mesh.fillet.pending")}` : ""}
                  </option>
                ))}
              </select>
            </td>
          </AttrRow>
        )}
        {f.kind === "elliptic" && approach === "kassem" && (
          <AttrRow label={t("tf.ef")} symbol="e_f" unit="·m_n">
            <td>
              <input
                type="number"
                step={0.05}
                min={-0.5}
                max={0.2}
                value={f.e_f ?? 0}
                onChange={(e) => set({ e_f: Number(e.target.value) })}
              />
            </td>
          </AttrRow>
        )}
        {f.kind === "elliptic" && approach === "landi" && (
          <>
            <AttrRow label={t("tf.raf")} symbol="Δr_D1" unit="·m_n">
              <td>
                <input
                  type="number"
                  step={0.1}
                  min={0}
                  max={1.5}
                  value={f.ra_f ?? 0}
                  onChange={(e) => set({ ra_f: Number(e.target.value) })}
                />
              </td>
            </AttrRow>
            <AttrRow label={t("tf.d2frac")} symbol="φ_D2/φ_L" unit="–">
              <td>
                <input
                  type="number"
                  step={0.05}
                  min={0.5}
                  max={1}
                  value={f.d2_frac ?? 1}
                  onChange={(e) => set({ d2_frac: Number(e.target.value) })}
                />
              </td>
            </AttrRow>
          </>
        )}
        {f.kind === "elliptic" && approach === "fruehe" && (
          <>
            <AttrRow label={t("tf.tilt")} symbol="γ" unit="°">
              <td>
                <input
                  type="number"
                  step={1}
                  min={5}
                  max={45}
                  value={f.tilt_deg ?? 30}
                  onChange={(e) => set({ tilt_deg: Number(e.target.value) })}
                />
              </td>
            </AttrRow>
            <AttrRow label={t("tf.aspect")} symbol="a/b" unit="–">
              <td>
                <input
                  type="number"
                  step={0.25}
                  min={1}
                  max={6}
                  value={f.aspect ?? 3}
                  onChange={(e) => set({ aspect: Number(e.target.value) })}
                />
              </td>
            </AttrRow>
          </>
        )}
        {f.kind === "bezier" && approach === "roth" && (
          <AttrRow label={t("tf.be")} symbol="Be" unit="–">
            <td>
              <input
                type="number"
                step={0.01}
                min={0.3}
                max={0.95}
                value={f.be ?? 0.57}
                onChange={(e) => set({ be: Number(e.target.value) })}
              />
            </td>
          </AttrRow>
        )}
        {f.kind === "bezier" &&
          approach === "dong" &&
          (
            [
              ["dv0", "v₀", 0.05, 0.9, 0.35],
              ["dv1", "v₁", 0.05, 1.0, 1.0],
              ["dv2", "v₂", 0.02, 0.6, 0.15],
              ["dv3", "v₃", 0, 1, 0.499],
              ["dv4", "v₄", 0, 1.2, 0.991],
            ] as const
          ).map(([key, sym, min, max, dflt]) => (
            <AttrRow key={key} label={t(`tf.${key}`)} symbol={sym} unit="–">
              <td>
                <input
                  type="number"
                  step={0.01}
                  min={min}
                  max={max}
                  value={f[key] ?? dflt}
                  onChange={(e) => set({ [key]: Number(e.target.value) })}
                />
              </td>
            </AttrRow>
          ))}
        {f.kind === "bionic" && (
          <>
            <AttrRow label={t("tf.gamma")} symbol="γ_b" unit="°">
              <td>
                <input
                  type="number"
                  step={1}
                  min={6}
                  max={64}
                  value={f.gamma_deg ?? ("" as unknown as number)}
                  placeholder="auto"
                  onChange={(e) =>
                    set({ gamma_deg: e.target.value === "" ? null : Number(e.target.value) })
                  }
                />
              </td>
            </AttrRow>
            <AttrRow label={t("tf.bf")} symbol="b_f" unit="–">
              <td>
                <input
                  type="number"
                  step={0.05}
                  min={0.1}
                  max={0.6}
                  value={f.b_f ?? 0.35}
                  onChange={(e) => set({ b_f: Number(e.target.value) })}
                />
              </td>
            </AttrRow>
          </>
        )}
        {f.kind === "bionic" &&
          approach === "cao" &&
          (
            [
              ["cao_step", "s", 0.1, 3, 0.05, 1.0],
              ["cao_iterations", "n_it", 1, 30, 1, 12],
              ["cao_tol", "tol", 0.001, 0.2, 0.005, 0.02],
            ] as const
          ).map(([key, sym, min, max, step, dflt]) => (
            <AttrRow key={key} label={t(`tf.${key}`)} symbol={sym} unit="–">
              <td>
                <input
                  type="number"
                  step={step}
                  min={min}
                  max={max}
                  value={f[key] ?? dflt}
                  onChange={(e) => set({ [key]: Number(e.target.value) })}
                />
              </td>
            </AttrRow>
          ))}
        {(f.kind === "elliptic" || f.kind === "bezier" || f.kind === "bionic") &&
          approach !== "cao" &&
          approach !== "landi" &&
          approach !== "dong" && (
            <AttrRow label={t("tf.junctionOffset")} symbol="Δr_j" unit="mm">
              <td>
                <input
                  type="number"
                  step={0.01}
                  min={0}
                  max={0.2}
                  value={f.junction_offset_mm ?? 0}
                  onChange={(e) => set({ junction_offset_mm: Number(e.target.value) })}
                />
              </td>
            </AttrRow>
          )}
      </tbody>
    </table>
  );
}

export function ManufacturabilityNote(props: { kind: FilletSpec["kind"]; approach?: string }) {
  const t = useT();
  if (props.kind === "standard" || props.kind === "trochoid") return null;
  if (props.kind === "bezier" && props.approach === "dong") {
    // Dong optimizes the HOB tip — the only optimized fillet that stays hob-manufacturable
    return (
      <div className="text-[11.5px] text-sky-700 bg-sky-50 border border-sky-200 rounded-md px-2.5 py-1.5">
        {t("mesh.fillet.manufacturingDong")}
      </div>
    );
  }
  return (
    <div className="text-[11.5px] text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-2.5 py-1.5">
      {t("mesh.fillet.manufacturing")}
    </div>
  );
}

export function ToothFormPanel(props: { gear: 1 | 2 }) {
  const t = useT();
  const fm = useFmt();
  const { stage } = useStage();
  const wb = useWorkbench();
  // THE fillet spec lives in fem.fillet_gear{n} (audit STR-03/FEM-02: a panel-local
  // useState meant the Zahnform choice never reached deck, pair view or geometry report)
  const fillet = props.gear === 1 ? wb.fem.fillet_gear1 : wb.fem.fillet_gear2;
  const setFillet = (f: FilletSpec) =>
    wb.setFem(props.gear === 1 ? { fillet_gear1: f } : { fillet_gear2: f });
  const [standard, setStandard] = useState<ContourResponse | null>(null);
  const [current, setCurrent] = useState<ContourResponse | null>(null);
  const [cao, setCao] = useState<FilletCaoResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(
    async (f: FilletSpec, freshStandard = false) => {
      setBusy(true);
      setErr(null);
      try {
        const cur = await contourApi.contour({ stage, gear: props.gear, fillet: f });
        setCurrent(cur);
        if (f.kind !== "standard" && (freshStandard || !standard)) {
          setStandard(
            await contourApi.contour({ stage, gear: props.gear, fillet: { kind: "standard" } }),
          );
        }
        if (f.kind === "bionic" && (f.approach ?? defaultApproach(f.kind)) === "cao") {
          // convergence history; the growth run itself is cached server-side per profile
          setCao(await meshApi.filletCao(stage, props.gear, f));
        } else {
          setCao(null);
        }
      } catch (e) {
        setErr(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [props.gear, standard, stage],
  );

  useEffect(() => {
    // gear switch / stage edit: INVALIDATE every cached contour before refetching —
    // the old standard overlay belonged to the previous gear/geometry (audit FIL-01)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setStandard(null);
    setCurrent(null);
    setCao(null);
    void load(fillet, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.gear, stage]);

  const contours = [];
  if (current) {
    if (fillet.kind !== "standard" && standard) {
      contours.push({ data: standard, label: t("mesh.fillet.standard") });
    }
    const key = current.fillet_approach
      ? `mesh.fillet.${fillet.kind}-${current.fillet_approach}`
      : `mesh.fillet.${fillet.kind}`;
    contours.push({ data: current, label: t(key) });
  }
  // the fillet digs below d_f for some approaches (Frühe by design) — surface it
  const effRoot = current ? current.effective_root_diameter_mm : null;
  const rootDeviates =
    current != null && effRoot != null && Math.abs(effRoot - current.root_diameter_mm) > 5e-3;

  return (
    <div className="grid grid-cols-[340px_1fr] gap-3 items-start">
      <div className="flex flex-col gap-3">
        <Section title={t("mesh.fillet")}>
          <FilletEditor value={fillet} onChange={setFillet} />
          <div className="p-2 border-t border-zinc-100">
            <Btn onClick={() => void load(fillet)} busy={busy}>
              {t("common.run")}
            </Btn>
          </div>
        </Section>
        <ManufacturabilityNote kind={fillet.kind} approach={fillet.approach} />
        {err && <ErrNote>{err}</ErrNote>}
        {current && (
          <Section title={t("toothform.title")}>
            <table className="attr-table">
              <tbody>
                <AttrRow label={t("attr.df")} symbol="d_f" unit="mm">
                  <td className="wb-num">{fm.num(current.root_diameter_mm, 3)}</td>
                </AttrRow>
                {rootDeviates && (
                  <AttrRow label={t("tf.dfEff")} symbol="d_f,eff" unit="mm">
                    <td className="wb-num">{fm.num(effRoot, 3)}</td>
                  </AttrRow>
                )}
                <AttrRow label={t("attr.dFf")} symbol="d_Ff" unit="mm">
                  <td className="wb-num">{fm.num(current.root_form_diameter_mm, 3)}</td>
                </AttrRow>
                <AttrRow label={t("tf.dNa")} symbol="d_Na" unit="mm">
                  <td className="wb-num">{fm.num(current.usable_tip_diameter_mm, 3)}</td>
                </AttrRow>
                <AttrRow label={t("attr.daCircle")} symbol="d_a" unit="mm">
                  <td className="wb-num">{fm.num(current.tip_diameter_mm, 3)}</td>
                </AttrRow>
              </tbody>
            </table>
          </Section>
        )}
        {current?.clearance_mm != null && (
          <Stat
            label={t("mesh.clearance")}
            value={fm.num(current.clearance_mm, 3)}
            unit="mm"
            tone={current.clearance_mm > 0.05 ? "good" : "bad"}
          />
        )}
        {cao && (
          <Section title={t("toothform.caoTitle")}>
            <table className="attr-table">
              <thead>
                <tr>
                  <th>It.</th>
                  <th>σ_max [MPa]</th>
                  <th>{t("toothform.caoUniformity")}</th>
                </tr>
              </thead>
              <tbody>
                {cao.sigma_history_mpa.map((s, i) => (
                  <tr key={i}>
                    <td className="wb-num">{i + 1}</td>
                    <td className="wb-num">{fm.num(s, 1)}</td>
                    <td className="wb-num">{fm.num(cao.uniformity_history[i], 3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="text-[11.5px] text-zinc-600 px-2 py-1.5">
              {cao.converged ? t("toothform.caoConverged") : t("toothform.caoBudget")}
            </div>
          </Section>
        )}
      </div>
      <div className="border border-zinc-200 rounded-lg bg-white p-3">
        <ContourPlot contours={contours} teethEachSide={1} height={430} showRootCircles />
      </div>
    </div>
  );
}
