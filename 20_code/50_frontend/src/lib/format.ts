// Number formatting and safety-factor classification (shared by the views).

export function fmt(value: number | null | undefined, digits = 2): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export type Verdict = "good" | "warn" | "bad" | "neutral";

/** Classify a safety factor against its minimum (good ≥ min, warn ≥ 1, else bad). */
export function safetyVerdict(safety: number | null | undefined, minimum = 1.0): Verdict {
  if (safety == null || !Number.isFinite(safety)) return "neutral";
  if (safety >= minimum) return "good";
  if (safety >= 1.0) return "warn";
  return "bad";
}
