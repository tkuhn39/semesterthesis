import type { JSX } from "react";
import type { ToothGear, ToothProfileResponse } from "../lib/api";

/** Real involute tooth mesh of the selected pair, both gears at the centre distance. */
export function ToothMeshPlot(props: { data: ToothProfileResponse }): JSX.Element {
  const { pinion, wheel, center_distance_mm: a } = props.data;
  const rMax = Math.max(pinion.tip_radius_mm, wheel.tip_radius_mm);
  const minX = -pinion.tip_radius_mm;
  const maxX = a + wheel.tip_radius_mm;
  const m = 6;
  const wPx = 300;
  const scale = (wPx - 2 * m) / (maxX - minX);
  const hPx = 2 * rMax * scale + 2 * m;
  const tx = (X: number) => m + (X - minX) * scale;
  const ty = (Y: number) => m + (rMax - Y) * scale;

  const gearPath = (g: ToothGear, phase: number): string => {
    const flank = g.half_flank;
    const mirror = flank.map(([x, y]) => [-x, y] as [number, number]).reverse();
    const tooth = [...flank, ...mirror]; // right root→tip, left tip→root
    const parts: string[] = [];
    for (let k = 0; k < g.teeth; k++) {
      const th = (k * 2 * Math.PI) / g.teeth + phase;
      const c = Math.cos(th);
      const s = Math.sin(th);
      const pts = tooth.map(([x, y]) => {
        const rx = x * c - y * s + g.center_x_mm;
        const ry = x * s + y * c;
        return `${tx(rx).toFixed(1)},${ty(ry).toFixed(1)}`;
      });
      parts.push(`M${pts.join("L")}Z`);
    }
    return parts.join(" ");
  };

  return (
    <svg viewBox={`0 0 ${wPx} ${hPx}`} width="100%" style={{ display: "block" }}>
      {/* root discs */}
      <circle cx={tx(0)} cy={ty(0)} r={pinion.root_radius_mm * scale} fill="#eceff2" stroke="var(--tum-grey-400)" strokeWidth={0.8} />
      <circle cx={tx(a)} cy={ty(0)} r={wheel.root_radius_mm * scale} fill="var(--tum-blue-50)" stroke="var(--tum-blue-200)" strokeWidth={0.8} />
      {/* reference circles (dashed) */}
      <circle cx={tx(0)} cy={ty(0)} r={pinion.reference_radius_mm * scale} fill="none" stroke="var(--tum-grey-400)" strokeWidth={0.5} strokeDasharray="3 3" />
      <circle cx={tx(a)} cy={ty(0)} r={wheel.reference_radius_mm * scale} fill="none" stroke="var(--tum-blue-300)" strokeWidth={0.5} strokeDasharray="3 3" />
      {/* teeth */}
      <path d={gearPath(pinion, 0)} fill="#d6dbe0" stroke="var(--tum-grey-500)" strokeWidth={0.7} />
      <path d={gearPath(wheel, Math.PI / wheel.teeth)} fill="var(--tum-blue-100)" stroke="var(--tum-blue-700)" strokeWidth={0.7} />
      {/* centres */}
      <circle cx={tx(0)} cy={ty(0)} r={1.6} fill="var(--tum-grey-500)" />
      <circle cx={tx(a)} cy={ty(0)} r={1.6} fill="var(--tum-blue-700)" />
    </svg>
  );
}
