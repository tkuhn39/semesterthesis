"use client";

// Zahneingriff-Animation (Vorbild: FVA Gesamtsystemreport "updateMeshGearAnimation"):
// both gears' REAL as-cut tooth outlines (/api/tooth-profile — same geometry as the FE
// contour) rendered as SVG and rotated kinematically coupled (φ₂ = −φ₁·z₁/z₂), with
// play/pause and speed. Initial position = deck convention: gear 1 gap on the line of
// centres, gear 2 tooth meshing into it.

import { useEffect, useRef, useState } from "react";
import { api, type ToothGear, type ToothProfileResponse } from "@/lib/api";
import { useT } from "@/lib/i18n";
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

export function MeshEngagement(props: { height?: number }) {
  const wb = useWorkbench();
  const t = useT();
  const stage = wb.stage;
  const [data, setData] = useState<ToothProfileResponse | null>(null);
  const [running, setRunning] = useState(true);
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
    const tick = (t: number) => {
      if (last.current) setPhi((p) => p + (speed * (t - last.current)) / 1000);
      last.current = t;
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
  const p1 = 360 / g1.teeth;
  // deck convention (rig view): gear 1 gap on the line of centres, gear 2 tooth meshing
  // into it (tooth data is centred on +y; SVG y is mirrored, so CCW becomes CW)
  const rot1 = 90 + p1 / 2 + phi;
  const rot2 = -90 - (phi * g1.teeth) / g2.teeth;
  // viewport: the meshing zone with both pitch circles in view
  const r1 = g1.tip_radius_mm;
  const r2 = g2.tip_radius_mm;
  const minX = -r1 * 1.02;
  const width = a + r2 * 1.02 - minX;
  const minY = -Math.max(r1, r2) * 1.02;
  const height = 2 * Math.max(r1, r2) * 1.02;

  return (
    <div className="border border-zinc-200 rounded-lg overflow-hidden bg-white">
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-zinc-100">
        <span className="text-[12px] font-semibold text-sky-800">{t("eng.title")}</span>
        <button
          type="button"
          className="ml-auto px-2 py-0.5 border border-zinc-300 rounded-md text-[11.5px] bg-white hover:bg-zinc-50"
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
        viewBox={`${minX.toFixed(1)} ${minY.toFixed(1)} ${width.toFixed(1)} ${height.toFixed(1)}`}
        style={{ width: "100%", height: props.height ?? 320, background: "#f8fafc" }}
        preserveAspectRatio="xMidYMid meet"
      >
        {/* pitch circles (construction geometry) */}
        <circle cx={0} cy={0} r={(2 * a * g1.teeth) / (g1.teeth + g2.teeth) / 2} fill="none" stroke="#cbd5e1" strokeWidth={0.15} strokeDasharray="1 1" />
        <circle cx={a} cy={0} r={(2 * a * g2.teeth) / (g1.teeth + g2.teeth) / 2} fill="none" stroke="#cbd5e1" strokeWidth={0.15} strokeDasharray="1 1" />
        <g transform={`rotate(${rot1.toFixed(4)} 0 0)`}>
          <polygon points={gearOutline(g1)} fill="#cfe3f4" stroke="#3070b3" strokeWidth={0.12} />
        </g>
        <g transform={`translate(${a} 0) rotate(${rot2.toFixed(4)} 0 0)`}>
          <polygon points={gearOutline(g2)} fill="#e8eef4" stroke="#64748b" strokeWidth={0.12} />
        </g>
        {/* rotation axes */}
        <circle cx={0} cy={0} r={0.8} fill="#3070b3" />
        <circle cx={a} cy={0} r={0.8} fill="#64748b" />
      </svg>
      <div className="px-3 py-1 text-[11px] text-zinc-500">
        φ₁ = {(phi % 360).toFixed(1)}° · φ₂ = −φ₁·z₁/z₂ {t("eng.footer")}
      </div>
    </div>
  );
}
