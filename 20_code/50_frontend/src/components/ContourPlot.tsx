"use client";

// SVG plot of real as-cut tooth contours (M5). Assembles a full tooth (right boundary +
// mirrored left + tip arc) plus optional neighbour teeth from one ContourResponse, and
// overlays several variants (colour-coded) for the Stufenvariation comparison — the clean
// geometry view the FVA Workbench lacks.

import type { ContourResponse } from "@/lib/api";

export const OVERLAY_COLORS = ["#18181b", "#2563eb", "#dc2626", "#059669"];

type Pt = [number, number];

function toothOutline(c: ContourResponse, teethEachSide: number): Pt[][] {
  // right boundary arrives root-side → tip (incl. chamfer to d_a); the tooth is symmetric
  // about +y, so the left flank is the mirror. One open polyline per tooth:
  // left root → left tip → tip arc → right tip → right root.
  const right: Pt[] = [];
  for (let i = 0; i < c.boundary_xy.length; i += 2) {
    right.push([c.boundary_xy[i], c.boundary_xy[i + 1]]);
  }
  const leftRootToTip: Pt[] = right.map(([x, y]) => [-x, y] as Pt);
  const rightTip = right[right.length - 1];
  const leftTip = leftRootToTip[leftRootToTip.length - 1];
  const tipR = Math.hypot(rightTip[0], rightTip[1]);
  const aL = Math.atan2(leftTip[0], leftTip[1]);
  const aR = Math.atan2(rightTip[0], rightTip[1]);
  const tip: Pt[] = [];
  for (let k = 1; k < 16; k++) {
    const a = aL + ((aR - aL) * k) / 16;
    tip.push([tipR * Math.sin(a), tipR * Math.cos(a)]);
  }
  const one: Pt[] = [...leftRootToTip, ...tip, ...right.slice().reverse()];
  const outline: Pt[][] = [];
  const pitch = (c.pitch_deg * Math.PI) / 180;
  for (let t = -teethEachSide; t <= teethEachSide; t++) {
    const ang = t * pitch;
    const cs = Math.cos(ang);
    const sn = Math.sin(ang);
    outline.push(one.map(([x, y]) => [x * cs + y * sn, -x * sn + y * cs] as Pt));
  }
  return outline;
}

export function ContourPlot(props: {
  contours: { data: ContourResponse; label: string }[];
  teethEachSide?: number;
  height?: number;
}) {
  const teethEachSide = props.teethEachSide ?? 1;
  const height = props.height ?? 340;
  if (props.contours.length === 0) return null;

  const all: Pt[] = [];
  const polys = props.contours.map((c) => toothOutline(c.data, teethEachSide));
  polys.forEach((teeth) => teeth.forEach((t) => t.forEach((p) => all.push(p))));
  const xs = all.map((p) => p[0]);
  const ys = all.map((p) => p[1]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const pad = 0.05 * Math.max(maxX - minX, maxY - minY);
  const vb = `${minX - pad} ${-(maxY + pad)} ${maxX - minX + 2 * pad} ${maxY - minY + 2 * pad}`;

  return (
    <div>
      <svg viewBox={vb} style={{ width: "100%", height }} preserveAspectRatio="xMidYMid meet">
        {polys.map((teeth, ci) =>
          teeth.map((tooth, ti) => (
            <polyline
              key={`${ci}-${ti}`}
              points={tooth.map(([x, y]) => `${x},${-y}`).join(" ")}
              fill="none"
              stroke={OVERLAY_COLORS[ci % OVERLAY_COLORS.length]}
              strokeWidth={(maxX - minX) / 420}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          )),
        )}
      </svg>
      {props.contours.length > 1 && (
        <div className="flex flex-wrap gap-3 mt-1">
          {props.contours.map((c, i) => (
            <span key={i} className="inline-flex items-center gap-1.5 text-[11.5px] text-zinc-600">
              <span
                className="inline-block w-3 h-[3px] rounded"
                style={{ background: OVERLAY_COLORS[i % OVERLAY_COLORS.length] }}
              />
              {c.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
