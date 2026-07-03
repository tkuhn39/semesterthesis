import type { JSX } from "react";
import type { VariationPoint } from "../lib/api";
import { safetyVerdict } from "../lib/format";

export interface PCDim {
  key: keyof VariationPoint;
  label: string;
}

const COLOR: Record<string, string> = {
  good: "#9fba36",
  warn: "#f7811e",
  bad: "#ea7237",
  neutral: "#9abce4",
};

/** Parallel-coordinates plot of all variants; colour by plastic root safety; click to select. */
export function ParallelCoordinates(props: {
  points: VariationPoint[];
  dims: PCDim[];
  selected: number | null;
  onSelect: (i: number) => void;
  rootMin: number;
}): JSX.Element {
  const W = 760;
  const H = 230;
  const padX = 18;
  const padTop = 16;
  const padBot = 26;
  const dims = props.dims;
  const axisX = (j: number) => padX + (j * (W - 2 * padX)) / Math.max(1, dims.length - 1);

  // min/max per dimension
  const ranges = dims.map((d) => {
    const vals = props.points
      .map((p) => p[d.key] as number)
      .filter((v) => Number.isFinite(v));
    const lo = Math.min(...vals);
    const hi = Math.max(...vals);
    return { lo, hi: hi === lo ? lo + 1 : hi };
  });
  const y = (j: number, v: number) => {
    const { lo, hi } = ranges[j];
    return padTop + (1 - (v - lo) / (hi - lo)) * (H - padTop - padBot);
  };
  const path = (p: VariationPoint) =>
    dims
      .map((d, j) => `${j === 0 ? "M" : "L"}${axisX(j).toFixed(1)},${y(j, p[d.key] as number).toFixed(1)}`)
      .join(" ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: "block" }}>
      {dims.map((d, j) => (
        <g key={d.key as string}>
          <line x1={axisX(j)} y1={padTop} x2={axisX(j)} y2={H - padBot} stroke="var(--border-strong)" strokeWidth={1} />
          <text x={axisX(j)} y={H - padBot + 14} fontSize={9.5} textAnchor="middle" fill="var(--text-muted)">
            {d.label}
          </text>
          <text x={axisX(j)} y={padTop - 5} fontSize={8.5} textAnchor="middle" fill="var(--text-muted)">
            {fmtAxis(ranges[j].hi)}
          </text>
        </g>
      ))}
      {props.points.map((p, i) => {
        const sel = i === props.selected;
        if (sel) return null; // draw selected on top
        const c = COLOR[safetyVerdict(p.root_safety_wheel, props.rootMin)];
        return (
          <path
            key={i}
            d={path(p)}
            fill="none"
            stroke={c}
            strokeWidth={p.pareto ? 1.4 : 0.7}
            strokeOpacity={p.pareto ? 0.9 : 0.42}
            style={{ cursor: "pointer" }}
            onClick={() => props.onSelect(i)}
          />
        );
      })}
      {props.selected != null && props.points[props.selected] && (
        <path d={path(props.points[props.selected])} fill="none" stroke="var(--tum-blue)" strokeWidth={2.4} />
      )}
    </svg>
  );
}

function fmtAxis(v: number): string {
  return Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(2);
}
