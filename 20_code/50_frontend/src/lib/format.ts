// Number formatting and safety-factor classification (shared by the views).
//
// ONE locale-aware formatter for every user-visible number (FVA shows comma decimals in
// the German UI): components bind it via useFmt() from lib/i18n so a locale switch
// re-renders them. SVG/path coordinates keep plain toFixed — they are machine syntax,
// never localized.

import type { Locale } from "./i18n";

const TAGS: Record<Locale, string> = { de: "de-DE", en: "en-US" };

export function fmtNum(
  value: number | null | undefined,
  digits = 2,
  locale: Locale = "de",
): string {
  if (value == null || !Number.isFinite(value)) return "–";
  return value.toLocaleString(TAGS[locale], {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/** Integer with thousands grouping (counts, node/cell numbers). */
export function fmtInt(value: number | null | undefined, locale: Locale = "de"): string {
  if (value == null || !Number.isFinite(value)) return "–";
  return Math.round(value).toLocaleString(TAGS[locale]);
}

export type Verdict = "good" | "warn" | "bad" | "neutral";

/** Classify a safety factor against its minimum (good ≥ min, warn ≥ 1, else bad). */
export function safetyVerdict(safety: number | null | undefined, minimum = 1.0): Verdict {
  if (safety == null || !Number.isFinite(safety)) return "neutral";
  if (safety >= minimum) return "good";
  if (safety >= 1.0) return "warn";
  return "bad";
}
