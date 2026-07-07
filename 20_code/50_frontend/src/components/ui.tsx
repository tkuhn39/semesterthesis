"use client";

// Condensed workbench UI primitives (FVA-editor look, modernised with Geist).

import { useState, type ReactNode } from "react";

export function Section(props: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
  right?: ReactNode;
}) {
  const [open, setOpen] = useState(props.defaultOpen ?? true);
  return (
    <div className="border border-zinc-200 rounded-lg bg-white overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-1.5 text-left bg-zinc-50 hover:bg-zinc-100 border-b border-zinc-200"
      >
        <span className={`text-zinc-400 text-[10px] transition-transform ${open ? "rotate-90" : ""}`}>
          ▶
        </span>
        <span className="font-medium text-[12.5px] text-zinc-700">{props.title}</span>
        <span className="ml-auto">{props.right}</span>
      </button>
      {/* NEVER clip values/units (user report): content wider than the pane scrolls
          horizontally instead of being cut off by the rounded-corner clip above */}
      {open && <div className="overflow-x-auto">{props.children}</div>}
    </div>
  );
}

export function Btn(props: {
  children: ReactNode;
  onClick?: () => void;
  busy?: boolean;
  variant?: "primary" | "ghost";
  disabled?: boolean;
}) {
  const base =
    props.variant === "ghost"
      ? "border border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-50"
      : "bg-zinc-900 text-white hover:bg-zinc-700";
  return (
    <button
      type="button"
      disabled={props.busy || props.disabled}
      onClick={props.onClick}
      className={`${base} rounded-md px-3 py-1.5 text-[12.5px] font-medium disabled:opacity-50 transition-colors`}
    >
      {props.busy ? "…" : props.children}
    </button>
  );
}

export function Num(props: {
  value: number;
  onChange: (v: number) => void;
  step?: number | "any";
  disabled?: boolean;
  width?: number;
}) {
  return (
    <input
      type="number"
      disabled={props.disabled}
      value={Number.isFinite(props.value) ? props.value : ""}
      step={props.step ?? "any"}
      style={props.width ? { maxWidth: props.width } : undefined}
      onChange={(e) => props.onChange(Number(e.target.value))}
    />
  );
}

export function AttrRow(props: {
  label: string;
  symbol?: string;
  unit?: string;
  children: ReactNode; // value cell(s)
}) {
  return (
    <tr>
      <td className="text-zinc-700">{props.label}</td>
      <td className="wb-num text-zinc-400">{props.symbol ?? ""}</td>
      {props.children}
      <td className="text-zinc-400">{props.unit ?? ""}</td>
    </tr>
  );
}

export function Stat(props: { label: string; value: string; unit?: string; tone?: "good" | "bad" | "neutral" }) {
  const tone =
    props.tone === "good"
      ? "text-emerald-600"
      : props.tone === "bad"
        ? "text-red-600"
        : "text-zinc-900";
  return (
    <div className="border border-zinc-200 rounded-lg bg-white px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-zinc-500">{props.label}</div>
      <div className={`wb-num text-[16px] ${tone}`}>
        {props.value}
        {props.unit && <span className="text-[11px] text-zinc-400 ml-1">{props.unit}</span>}
      </div>
    </div>
  );
}

export function ErrNote(props: { children: ReactNode }) {
  return (
    <div className="border border-red-200 bg-red-50 text-red-700 rounded-md px-3 py-2 text-[12.5px]">
      ⚠ {props.children}
    </div>
  );
}
