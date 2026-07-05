"use client";

// 2D sector-mesh view (the previously unrendered /api/mesh/preview): every quad as an
// SVG polygon coloured by its scaled Jacobian (same gates as the 3D heatmap — ≥0.7 grey,
// amber towards 0.35, red below), thin element edges. This is the FVA "FEM-Vernetzer"
// style cross-section view of the transplant mesh (ADR-019).

import { useMemo } from "react";
import type { MeshPreviewResponse } from "@/lib/api";
import { useFmt, useT } from "@/lib/i18n";

function qualityColor(q: number, heatmap: boolean): string {
  if (!heatmap) return "#d4d4d8";
  if (q >= 0.7) return "#d4d4d8"; // zinc-300 — comfortably good
  if (q >= 0.35) {
    // 0.7 → 0.35: grey → amber
    const t = (0.7 - q) / 0.35;
    const mix = (a: number, b: number) => Math.round(a + (b - a) * t);
    return `rgb(${mix(212, 245)}, ${mix(212, 158)}, ${mix(216, 11)})`;
  }
  return "#dc2626"; // red — below the 0.35 gate
}

export function Mesh2DView(props: {
  data: MeshPreviewResponse;
  heatmap?: boolean;
  height?: number;
}) {
  const { data } = props;
  const t = useT();
  const fm = useFmt();
  const heatmap = props.heatmap ?? true;
  const height = props.height ?? 560;

  const { polys, viewBox } = useMemo(() => {
    const xs = data.nodes_xy;
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (let i = 0; i < xs.length; i += 2) {
      if (xs[i] < minX) minX = xs[i];
      if (xs[i] > maxX) maxX = xs[i];
      if (xs[i + 1] < minY) minY = xs[i + 1];
      if (xs[i + 1] > maxY) maxY = xs[i + 1];
    }
    const pad = 0.03 * Math.max(maxX - minX, maxY - minY);
    // SVG y grows downwards — mirror by emitting -y and shifting the viewBox
    const vb = `${(minX - pad).toFixed(3)} ${(-maxY - pad).toFixed(3)} ${(maxX - minX + 2 * pad).toFixed(3)} ${(maxY - minY + 2 * pad).toFixed(3)}`;
    const out: { points: string; fill: string }[] = [];
    for (let q = 0; q < data.n_quads; q++) {
      const pts: string[] = [];
      for (let k = 0; k < 4; k++) {
        const n = data.quads[q * 4 + k];
        pts.push(`${xs[n * 2].toFixed(3)},${(-xs[n * 2 + 1]).toFixed(3)}`);
      }
      out.push({ points: pts.join(" "), fill: qualityColor(data.quality[q], heatmap) });
    }
    return { polys: out, viewBox: vb };
  }, [data, heatmap]);

  return (
    <div className="w-full" style={{ background: "var(--wb-viewport)", borderRadius: 10 }}>
      <svg viewBox={viewBox} style={{ width: "100%", height }} preserveAspectRatio="xMidYMid meet">
        {polys.map((p, i) => (
          <polygon key={i} points={p.points} fill={p.fill} stroke="#3f3f46" strokeWidth={0.006} />
        ))}
      </svg>
      <div className="flex items-center gap-3 px-3 py-1.5 text-[11px] text-zinc-400">
        <span>
          {fm.int(data.n_quads)} {t("mesh2d.quads")} · {fm.int(data.n_nodes)} {t("mesh.nodes")}
        </span>
        <span>
          min J ={" "}
          <span className={data.min_scaled_jacobian >= 0.35 ? "text-emerald-400" : "text-red-400"}>
            {fm.num(data.min_scaled_jacobian, 3)}
          </span>
        </span>
        <span className="ml-auto flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm" style={{ background: "#d4d4d8" }} /> ≥ 0.7
          <span className="inline-block w-3 h-3 rounded-sm" style={{ background: "#f59e0b" }} /> 0.35–0.7
          <span className="inline-block w-3 h-3 rounded-sm" style={{ background: "#dc2626" }} /> &lt; 0.35
        </span>
      </div>
    </div>
  );
}
