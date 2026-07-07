"use client";

// Lightweight resizable split panes (user request 2026-07-06: "Fenster verschieben können,
// aber ein Block drin, dass man nicht mehr verkleinern kann"): a draggable vertical divider
// adjusts the pane width, CLAMPED to a minimum so the content is never squeezed into
// clipping — combined with the Section/QuickView overflow-x-auto rule ("nie abschneiden,
// schlimmstenfalls scrollen").

import { useRef, useState, type ReactNode } from "react";

export function clampWidth(w: number, min: number, max: number): number {
  return Math.min(Math.max(w, min), max);
}

/** Draggable vertical divider: calls onDrag with the pointer dx while the primary button
 *  is held (pointer capture keeps the drag alive outside the strip). */
export function Resizer(props: { onDrag: (dx: number) => void }) {
  const last = useRef(0);
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      className="w-1.5 shrink-0 cursor-col-resize rounded bg-transparent hover:bg-blue-200/70 active:bg-blue-300/70 transition-colors"
      onPointerDown={(e) => {
        e.preventDefault();
        last.current = e.clientX;
        (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
      }}
      onPointerMove={(e) => {
        if ((e.buttons & 1) === 0) return;
        props.onDrag(e.clientX - last.current);
        last.current = e.clientX;
      }}
    />
  );
}

/** Two-column resizable split: left pane with a MIN-WIDTH LOCK (divider clamps), right
 *  pane takes the remaining space. Used by the viewport panels (controls | 3D view). */
export function SplitPair(props: {
  left: ReactNode;
  right: ReactNode;
  initial?: number;
  min?: number;
  max?: number;
}) {
  const min = props.min ?? 320;
  const max = props.max ?? 760;
  const [w, setW] = useState(props.initial ?? 360);
  return (
    <div className="flex items-stretch h-full min-h-0 gap-1">
      <div
        className="shrink-0 overflow-y-auto flex flex-col gap-3 pr-1"
        style={{ width: w, minWidth: min, maxHeight: "100%" }}
      >
        {props.left}
      </div>
      <Resizer onDrag={(dx) => setW((v) => clampWidth(v + dx, min, max))} />
      <div className="flex-1 min-w-0 min-h-0 h-full">{props.right}</div>
    </div>
  );
}
