"use client";

// Tooth-form editor (M5): the real as-cut contour of one gear with the root-fillet strategy
// selectable — standard tool fillet vs elliptic / Bézier / bionic, with live mating-tip
// clearance from the backend interference check.

import { useCallback, useEffect, useState } from "react";
import { contourApi, type ContourResponse, type FilletSpec } from "@/lib/api";
import { ContourPlot } from "@/components/ContourPlot";
import { AttrRow, Btn, ErrNote, Section, Stat } from "@/components/ui";
import { useFmt, useT } from "@/lib/i18n";
import { useStage } from "@/lib/stage";

export function FilletEditor(props: { value: FilletSpec; onChange: (f: FilletSpec) => void }) {
  const t = useT();
  const f = props.value;
  const set = (patch: Partial<FilletSpec>) => props.onChange({ ...f, ...patch });
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
            <select value={f.kind} onChange={(e) => set({ kind: e.target.value as FilletSpec["kind"] })}>
              <option value="standard">{t("mesh.fillet.standard")}</option>
              <option value="trochoid">{t("mesh.fillet.trochoid")}</option>
              <option value="elliptic">{t("mesh.fillet.elliptic")}</option>
              <option value="bezier">{t("mesh.fillet.bezier")}</option>
              <option value="bionic">{t("mesh.fillet.bionic")}</option>
            </select>
          </td>
        </AttrRow>
        {f.kind === "elliptic" && (
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
        {f.kind === "bezier" && (
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
      </tbody>
    </table>
  );
}

export function ManufacturabilityNote(props: { kind: FilletSpec["kind"] }) {
  const t = useT();
  if (props.kind === "standard" || props.kind === "trochoid") return null;
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
  const [fillet, setFillet] = useState<FilletSpec>({ kind: "standard" });
  const [standard, setStandard] = useState<ContourResponse | null>(null);
  const [current, setCurrent] = useState<ContourResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(
    async (f: FilletSpec) => {
      setBusy(true);
      setErr(null);
      try {
        const cur = await contourApi.contour({ stage, gear: props.gear, fillet: f });
        setCurrent(cur);
        if (f.kind !== "standard" && !standard) {
          setStandard(
            await contourApi.contour({ stage, gear: props.gear, fillet: { kind: "standard" } }),
          );
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
    // initial contour fetch on mount / gear switch; async, so state updates land post-render
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(fillet);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.gear, stage]);

  const contours = [];
  if (current) {
    if (fillet.kind !== "standard" && standard) {
      contours.push({ data: standard, label: t("mesh.fillet.standard") });
    }
    contours.push({ data: current, label: t(`mesh.fillet.${fillet.kind}`) });
  }

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
        <ManufacturabilityNote kind={fillet.kind} />
        {err && <ErrNote>{err}</ErrNote>}
        {current && (
          <Section title={t("toothform.title")}>
            <table className="attr-table">
              <tbody>
                <AttrRow label={t("attr.df")} symbol="d_f" unit="mm">
                  <td className="wb-num">{fm.num(current.root_diameter_mm, 3)}</td>
                </AttrRow>
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
      </div>
      <div className="border border-zinc-200 rounded-lg bg-white p-3">
        <ContourPlot contours={contours} teethEachSide={1} height={430} />
      </div>
    </div>
  );
}
