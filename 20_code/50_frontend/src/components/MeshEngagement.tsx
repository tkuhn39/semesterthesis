"use client";

// Zahneingriff (Vorbild: FVA Gesamtsystemreport "Zahneingriff"-Plot): ZOOM on the
// meshing zone (user decision — no full-disc overview), with the exact line of action
// drawn as a static overlay: tangent line T1–T2 on both base circles, the active path
// A–E highlighted, single-contact points B/D, pitch point C with a grey crosshair,
// dashed base + working pitch circles — all from /api/tooth-profile.line_of_action
// (verified against the FVA reference coordinates). The gears' REAL as-cut outlines
// rotate kinematically coupled (φ₂ = −φ₁·z₁/z₂) behind the static overlay.

import { useEffect, useRef, useState } from "react";
import { api, type LineOfAction, type ToothGear, type ToothProfileResponse } from "@/lib/api";
import { useFmt, useT } from "@/lib/i18n";
import { useWorkbench } from "@/lib/store";

function gearOutline(g: ToothGear): string {
  // one tooth, walked gap-centre → left flank up → tip → right flank down → gap-centre,
  // so consecutive teeth join at the root lands (half_flank runs root land → tip)
  const right = g.half_flank;
  const tooth: [number, number][] = [
    ...right.map(([x, y]) => [-x, y] as [number, number]),
    ...right.slice().reverse(),
  ];
  const pitch = (2 * Math.PI) / g.teeth;
  const pts: string[] = [];
  for (let k = 0; k < g.teeth; k++) {
    const c = Math.cos(k * pitch);
    const s = Math.sin(k * pitch);
    for (const [x, y] of tooth) {
      pts.push(`${(c * x - s * y).toFixed(3)},${(-(s * x + c * y)).toFixed(3)}`);
    }
  }
  return pts.join(" ");
}

// label offsets like the FVA annotations (ay = ±90): below the line for T1/T2/B/E,
// above for A/C/D — in SVG plot coordinates (y flipped) "below" is +y
const LABEL_DOWN = new Set(["T1", "T2", "B", "E"]);

function LineOfActionOverlay({
  loa,
  a,
  rootRadii,
}: {
  loa: LineOfAction;
  a: number;
  rootRadii?: [number, number]; // r_f per gear (audit COV-14: served but never drawn)
}) {
  // plot coordinates: y flipped (like the gear outlines)
  const P = (p: [number, number]): [number, number] => [p[0], -p[1]];
  const [t1, t2, pa, pb, pc, pd, pe] = [loa.t1, loa.t2, loa.a, loa.b, loa.c, loa.d, loa.e].map(P);
  const points: [string, [number, number]][] = [
    ["T1", t1],
    ["T2", t2],
    ["A", pa],
    ["B", pb],
    ["C", pc],
    ["D", pd],
    ["E", pe],
  ];
  const [rw1, rw2] = loa.working_pitch_radius_mm;
  const [rb1, rb2] = loa.base_radius_mm;
  const dash = "0.6 0.45";
  const navy = "#2b4254"; // FVA construction-geometry colour
  return (
    <g>
      {/* base + working pitch circles (dashed construction geometry, FVA style) */}
      <circle cx={0} cy={0} r={rb1} fill="none" stroke={navy} strokeWidth={0.05} strokeDasharray={dash} />
      <circle cx={a} cy={0} r={rb2} fill="none" stroke={navy} strokeWidth={0.05} strokeDasharray={dash} />
      <circle cx={0} cy={0} r={rw1} fill="none" stroke={navy} strokeWidth={0.05} strokeDasharray={dash} />
      <circle cx={a} cy={0} r={rw2} fill="none" stroke={navy} strokeWidth={0.05} strokeDasharray={dash} />
      {/* root circles (audit COV-14 — visually useful next to the tip engagement) */}
      {rootRadii && (
        <>
          <circle cx={0} cy={0} r={rootRadii[0]} fill="none" stroke={navy} strokeWidth={0.04} strokeDasharray="0.3 0.3" />
          <circle cx={a} cy={0} r={rootRadii[1]} fill="none" stroke={navy} strokeWidth={0.04} strokeDasharray="0.3 0.3" />
        </>
      )}
      {/* grey crosshair through the pitch point C */}
      <line x1={pc[0] - 1000} y1={pc[1]} x2={pc[0] + 1000} y2={pc[1]} stroke="#9ca3af" strokeWidth={0.035} />
      <line x1={pc[0]} y1={pc[1] - 1000} x2={pc[0]} y2={pc[1] + 1000} stroke="#9ca3af" strokeWidth={0.035} />
      {/* line of action T1–T2, active path A–E on top */}
      <line x1={t1[0]} y1={t1[1]} x2={t2[0]} y2={t2[1]} stroke="#111827" strokeWidth={0.06} />
      <line x1={pa[0]} y1={pa[1]} x2={pe[0]} y2={pe[1]} stroke="#e37222" strokeWidth={0.14} />
      {/* labelled points with a short vertical leader (FVA annotation pattern) */}
      {points.map(([name, [x, y]]) => {
        const down = LABEL_DOWN.has(name);
        const ly = y + (down ? 1.3 : -1.3);
        return (
          <g key={name}>
            <circle cx={x} cy={y} r={0.16} fill="#111827" />
            <line x1={x} y1={y} x2={x} y2={ly} stroke="#6b7280" strokeWidth={0.035} />
            <text
              x={x}
              y={ly + (down ? 0.72 : -0.22)}
              fontSize={0.85}
              textAnchor="middle"
              fill="#111827"
              style={{ paintOrder: "stroke", stroke: "white", strokeWidth: 0.18 }}
            >
              {name}
            </text>
          </g>
        );
      })}
    </g>
  );
}

export function MeshEngagement(props: { height?: number; epsAlpha?: number | null }) {
  const wb = useWorkbench();
  const t = useT();
  const fm = useFmt();
  const stage = wb.stage;
  const [data, setData] = useState<ToothProfileResponse | null>(null);
  const [running, setRunning] = useState(true);
  const [zoomed, setZoomed] = useState(true);
  const [speed, setSpeed] = useState(8); // deg/s at gear 1
  const [phi, setPhi] = useState(0);
  const raf = useRef<number>(0);
  const last = useRef<number>(0);

  useEffect(() => {
    let alive = true;
    api
      .toothProfile(stage)
      .then((d) => alive && setData(d))
      .catch(() => alive && setData(null));
    return () => {
      alive = false;
    };
  }, [stage]);

  useEffect(() => {
    if (!running) return;
    const tick = (ts: number) => {
      if (last.current) setPhi((p) => p + (speed * (ts - last.current)) / 1000);
      last.current = ts;
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf.current);
      last.current = 0;
    };
  }, [running, speed]);

  if (!data) {
    return <div className="text-[12px] text-zinc-400 p-3">{t("eng.loading")}</div>;
  }
  const g1 = data.pinion;
  const g2 = data.wheel;
  const a = data.center_distance_mm;
  const loa = data.line_of_action;
  const p1 = 360 / g1.teeth;
  // deck convention (rig view): gear 1 gap on the line of centres, gear 2 tooth meshing
  // into it (tooth data is centred on +y; SVG y is mirrored, so CCW becomes CW)
  const rot1 = 90 + p1 / 2 + phi;
  const rot2 = -90 - (phi * g1.teeth) / g2.teeth;
  // viewport: zoom window centred on the pitch point (FVA: ~3.2·g_α tall), or the
  // full pair as a fallback/toggle
  const r1 = g1.tip_radius_mm;
  const r2 = g2.tip_radius_mm;
  let minX: number;
  let minY: number;
  let width: number;
  let height: number;
  if (zoomed && loa) {
    // window: the FULL tangent span T1–T2 stays visible (incl. labels), centred
    // between the tangent points — the user requirement "T1 über A–E bis T2 sichtbar"
    const cx = (loa.t1[0] + loa.t2[0]) / 2;
    const cy = -(loa.t1[1] + loa.t2[1]) / 2;
    const halfW = Math.max(
      (Math.abs(loa.t2[0] - loa.t1[0]) / 2) * 1.35 + 0.8,
      1.7 * loa.path_of_contact_mm,
    );
    const halfH = Math.max(
      (Math.abs(loa.t2[1] - loa.t1[1]) / 2) * 1.2 + 1.8,
      1.7 * loa.path_of_contact_mm,
    );
    minX = cx - halfW;
    minY = cy - halfH;
    width = 2 * halfW;
    height = 2 * halfH;
  } else {
    minX = -r1 * 1.02;
    width = a + r2 * 1.02 - minX;
    minY = -Math.max(r1, r2) * 1.02;
    height = 2 * Math.max(r1, r2) * 1.02;
  }
  // SSOT ε_α from the embedding panel's GeometryResponse when provided (audit STR-08:
  // the local g_α/p_et recomputation could diverge from the served contact ratio)
  const epsAlpha =
    props.epsAlpha ?? (loa ? loa.path_of_contact_mm / loa.transverse_base_pitch_mm : null);

  return (
    <div className="border border-zinc-200 rounded-lg overflow-hidden bg-white">
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-zinc-100">
        <span className="text-[12px] font-semibold text-sky-800">{t("eng.title")}</span>
        <button
          type="button"
          className="ml-auto px-2 py-0.5 border border-zinc-300 rounded-md text-[11.5px] bg-white hover:bg-zinc-50"
          onClick={() => setZoomed((z) => !z)}
        >
          {zoomed ? t("eng.full") : t("eng.zoom")}
        </button>
        <button
          type="button"
          className="px-2 py-0.5 border border-zinc-300 rounded-md text-[11.5px] bg-white hover:bg-zinc-50"
          onClick={() => setRunning((r) => !r)}
        >
          {running ? t("eng.pause") : t("eng.play")}
        </button>
        <input
          type="range"
          min={1}
          max={40}
          value={speed}
          onChange={(e) => setSpeed(Number(e.target.value))}
          title={t("eng.speed")}
        />
      </div>
      <svg
        viewBox={`${minX.toFixed(2)} ${minY.toFixed(2)} ${width.toFixed(2)} ${height.toFixed(2)}`}
        style={{ width: "100%", height: props.height ?? 400, background: "#f8fafc" }}
        preserveAspectRatio="xMidYMid meet"
      >
        <g transform={`rotate(${rot1.toFixed(4)} 0 0)`}>
          <polygon points={gearOutline(g1)} fill="#cfe3f4" stroke="#3070b3" strokeWidth={0.1} />
        </g>
        <g transform={`translate(${a} 0) rotate(${rot2.toFixed(4)} 0 0)`}>
          <polygon points={gearOutline(g2)} fill="#e8eef4" stroke="#64748b" strokeWidth={0.1} />
        </g>
        {/* static overlay: line of action with T1/A/B/C/D/E (never rotates) */}
        {loa && (
          <LineOfActionOverlay
            loa={loa}
            a={a}
            rootRadii={[g1.root_radius_mm, g2.root_radius_mm]}
          />
        )}
        {!zoomed && (
          <>
            <circle cx={0} cy={0} r={0.8} fill="#3070b3" />
            <circle cx={a} cy={0} r={0.8} fill="#64748b" />
          </>
        )}
      </svg>
      <div className="px-3 py-1 text-[11px] text-zinc-500 flex flex-wrap gap-x-3">
        <span>
          φ₁ = {(phi % 360).toFixed(1)}° · φ₂ = −φ₁·z₁/z₂ {t("eng.footer")}
        </span>
        {loa && (
          <span className="wb-num">
            α_wt = {fm.num(loa.working_pressure_angle_deg, 3)}° · g_α ={" "}
            {fm.num(loa.path_of_contact_mm, 3)} mm · ε_α = {fm.num(epsAlpha, 3)}
          </span>
        )}
      </div>
    </div>
  );
}
