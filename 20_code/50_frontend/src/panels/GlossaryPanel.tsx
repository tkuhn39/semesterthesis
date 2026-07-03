"use client";

// Parameter legend (user request 2026-07-04): a dedicated, FILTERABLE tab explaining every
// symbol — full name, an understandable description of what it does and which parameters it
// interacts with (formulas live in the norms), plus the norms it appears in. Filters: free
// text, category chips and a norm dropdown; related symbols are clickable cross-links.

import { useMemo, useState } from "react";
import {
  CATEGORY_LABELS,
  GLOSSARY,
  type GlossaryCategory,
  type GlossaryEntry,
} from "@/lib/glossary";
import { useLocale, useT } from "@/lib/i18n";

export function GlossaryPanel() {
  const t = useT();
  const { locale } = useLocale();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<GlossaryCategory | "all">("all");
  const [norm, setNorm] = useState<string>("all");

  const norms = useMemo(() => {
    const set = new Set<string>();
    GLOSSARY.forEach((e) => e.norms.forEach((n) => set.add(n)));
    return [...set].sort((a, b) => a.localeCompare(b, "de"));
  }, []);

  const matches = (e: GlossaryEntry): boolean => {
    if (category !== "all" && e.category !== category) return false;
    if (norm !== "all" && !e.norms.includes(norm)) return false;
    const q = query.trim().toLowerCase();
    if (!q) return true;
    const hay = [
      e.symbol,
      e.name.de,
      e.name.en,
      e.description.de,
      e.description.en,
      e.norms.join(" "),
      e.related.join(" "),
    ]
      .join(" ")
      .toLowerCase();
    return q.split(/\s+/).every((term) => hay.includes(term));
  };

  const q = query.trim().toLowerCase();
  const rows = GLOSSARY.filter(matches).sort((a, b) => {
    if (!q) return 0;
    // an exact symbol hit (e.g. after clicking a cross-link) surfaces first
    return (a.symbol.toLowerCase() === q ? 0 : 1) - (b.symbol.toLowerCase() === q ? 0 : 1);
  });

  return (
    <div className="flex flex-col gap-3 max-w-[1100px]">
      {/* filter bar */}
      <div className="flex flex-wrap items-center gap-2 bg-white border border-zinc-200 rounded-lg p-2.5">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("glossary.search")}
          className="border border-zinc-300 rounded-md px-2.5 py-1 text-[12.5px] w-[260px] bg-white"
        />
        <select
          value={norm}
          onChange={(e) => setNorm(e.target.value)}
          className="border border-zinc-300 rounded-md px-1.5 py-1 text-[12px] bg-white"
        >
          <option value="all">{t("glossary.allNorms")}</option>
          {norms.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        <span className="ml-auto text-[11.5px] text-zinc-400">
          {rows.length}/{GLOSSARY.length} {t("glossary.entries")}
        </span>
      </div>

      {/* category chips */}
      <div className="flex flex-wrap gap-1.5">
        <CategoryChip
          active={category === "all"}
          label={t("glossary.all")}
          onClick={() => setCategory("all")}
        />
        {(Object.keys(CATEGORY_LABELS) as GlossaryCategory[]).map((c) => (
          <CategoryChip
            key={c}
            active={category === c}
            label={CATEGORY_LABELS[c][locale]}
            onClick={() => setCategory(category === c ? "all" : c)}
          />
        ))}
      </div>

      {/* entries */}
      <div className="bg-white border border-zinc-200 rounded-lg overflow-hidden">
        {rows.length === 0 && (
          <div className="p-4 text-[12.5px] text-zinc-400">{t("glossary.noMatch")}</div>
        )}
        {rows.map((e, i) => (
          <div
            key={e.symbol}
            className={`grid grid-cols-[150px_1fr] gap-3 px-3 py-2.5 ${
              i > 0 ? "border-t border-zinc-100" : ""
            }`}
          >
            <div>
              <div className="wb-num font-semibold text-[13px] text-zinc-900">{e.symbol}</div>
              <div className="text-[11px] text-zinc-500 leading-snug">{e.name[locale]}</div>
              <div className="text-[10.5px] text-zinc-400 mt-0.5">
                {e.unit !== "–" && e.unit !== "—" ? `[${e.unit}]` : ""}
              </div>
            </div>
            <div className="min-w-0">
              <p className="text-[12.5px] text-zinc-700 leading-relaxed m-0">
                {e.description[locale]}
              </p>
              <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                <span className="text-[10.5px] uppercase tracking-wide text-zinc-400">
                  {CATEGORY_LABELS[e.category][locale]}
                </span>
                {e.norms.map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setNorm(norm === n ? "all" : n)}
                    className={`text-[10.5px] px-1.5 py-[1px] rounded-full border transition-colors ${
                      norm === n
                        ? "bg-blue-600 border-blue-600 text-white"
                        : "bg-zinc-50 border-zinc-200 text-zinc-500 hover:border-zinc-400"
                    }`}
                    title={t("glossary.filterNorm")}
                  >
                    {n}
                  </button>
                ))}
                {e.related.length > 0 && (
                  <span className="text-[10.5px] text-zinc-400 ml-1">{t("glossary.seeAlso")}:</span>
                )}
                {e.related.map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => {
                      setQuery(r);
                      setCategory("all");
                      setNorm("all");
                    }}
                    className="wb-num text-[11px] text-blue-700 hover:underline"
                    title={t("glossary.jump")}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CategoryChip(props: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      className={`text-[11.5px] px-2.5 py-[3px] rounded-full border transition-colors ${
        props.active
          ? "bg-zinc-900 border-zinc-900 text-white"
          : "bg-white border-zinc-300 text-zinc-600 hover:border-zinc-500"
      }`}
    >
      {props.label}
    </button>
  );
}
