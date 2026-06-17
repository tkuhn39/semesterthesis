// Reusable presentational components + a tiny async hook. Styling via index.css.
import { useCallback, useEffect, useState, type JSX, type ReactNode } from "react";
import { fmt, safetyVerdict, type Verdict } from "../lib/format";

export function Card(props: { children: ReactNode; className?: string }): JSX.Element {
  return <div className={`card ${props.className ?? ""}`}>{props.children}</div>;
}

export function CardHead(props: { title: string; sub?: string; right?: ReactNode }): JSX.Element {
  return (
    <div className="card-head">
      <div>
        <div className="card-title">{props.title}</div>
        {props.sub && <div className="card-sub">{props.sub}</div>}
      </div>
      {props.right}
    </div>
  );
}

export function Field(props: {
  label: string;
  hint?: ReactNode;
  children: ReactNode;
}): JSX.Element {
  return (
    <label className="field">
      <span className="field-label">{props.label}</span>
      {props.children}
      {props.hint && <span className="field-hint">{props.hint}</span>}
    </label>
  );
}

export function NumberField(props: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  hint?: ReactNode;
  step?: number;
  min?: number;
  max?: number;
}): JSX.Element {
  return (
    <Field label={props.label} hint={props.hint}>
      <input
        className="input"
        type="number"
        value={Number.isFinite(props.value) ? props.value : ""}
        step={props.step ?? "any"}
        min={props.min}
        max={props.max}
        onChange={(e) => props.onChange(Number(e.target.value))}
      />
    </Field>
  );
}

export function Button(props: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "ghost";
  disabled?: boolean;
  busy?: boolean;
}): JSX.Element {
  return (
    <button
      className={`btn btn-${props.variant ?? "primary"}`}
      onClick={props.onClick}
      disabled={props.disabled || props.busy}
    >
      {props.busy && <span className="spinner" />}
      {props.children}
    </button>
  );
}

export function Stat(props: {
  label: string;
  value: ReactNode;
  unit?: string;
  foot?: ReactNode;
}): JSX.Element {
  return (
    <div className="stat">
      <div className="stat-label">{props.label}</div>
      <div className="stat-value">
        {props.value}
        {props.unit && <span className="unit">{props.unit}</span>}
      </div>
      {props.foot && <div className="stat-foot">{props.foot}</div>}
    </div>
  );
}

export function Badge(props: { children: ReactNode; variant?: string; dot?: boolean }): JSX.Element {
  return (
    <span className={`badge badge-${props.variant ?? "neutral"}`}>
      {props.dot && <span className="dot" />}
      {props.children}
    </span>
  );
}

const VERDICT_BADGE: Record<Verdict, string> = {
  good: "good",
  warn: "warn",
  bad: "bad",
  neutral: "neutral",
};

/** A safety factor rendered as a colored pill (S = value, classified vs minimum). */
export function SafetyBadge(props: { value: number | null; minimum?: number }): JSX.Element {
  const v = safetyVerdict(props.value, props.minimum);
  return (
    <Badge variant={VERDICT_BADGE[v]} dot>
      S = {fmt(props.value, 2)}
    </Badge>
  );
}

export function Section(props: {
  title: string;
  defaultOpen?: boolean;
  children: ReactNode;
}): JSX.Element {
  const [open, setOpen] = useState(props.defaultOpen ?? true);
  return (
    <div className="section">
      <button className={`section-head ${open ? "open" : ""}`} onClick={() => setOpen(!open)}>
        <span className="chev">▸</span>
        {props.title}
      </button>
      {open && <div className="section-body">{props.children}</div>}
    </div>
  );
}

export function SelectField<T extends string>(props: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  hint?: ReactNode;
}): JSX.Element {
  return (
    <Field label={props.label} hint={props.hint}>
      <select className="input" value={props.value} onChange={(e) => props.onChange(e.target.value as T)}>
        {props.options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </Field>
  );
}

/** A label + two compact numeric boxes (the Workbench per-gear pinion/wheel pattern). */
export function PairRow(props: {
  label: ReactNode;
  pinion: number;
  wheel: number;
  onPinion: (v: number) => void;
  onWheel: (v: number) => void;
  step?: number;
}): JSX.Element {
  return (
    <div className="pair">
      <span className="pl">{props.label}</span>
      <input
        type="number"
        value={Number.isFinite(props.pinion) ? props.pinion : ""}
        step={props.step ?? "any"}
        onChange={(e) => props.onPinion(Number(e.target.value))}
      />
      <input
        type="number"
        value={Number.isFinite(props.wheel) ? props.wheel : ""}
        step={props.step ?? "any"}
        onChange={(e) => props.onWheel(Number(e.target.value))}
      />
    </div>
  );
}

export function Tabs<T extends string>(props: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}): JSX.Element {
  return (
    <div className="tabs">
      {props.options.map((o) => (
        <button
          key={o.value}
          className={`tab ${o.value === props.value ? "active" : ""}`}
          onClick={() => props.onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Minimal data-fetch hook: runs `fn` on mount and exposes {data, error, loading, reload}. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []): {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
} {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const run = useCallback(() => {
    setLoading(true);
    setError(null);
    fn()
      .then((d) => setData(d))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(run, [run]);
  return { data, error, loading, reload: run };
}
