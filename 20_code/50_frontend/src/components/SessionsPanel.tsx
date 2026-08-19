"use client";

// Sitzungen in der Seitenleiste (user requirement 2026-08-19): save the FULL input
// state as a named, server-persisted session (optionally with the rendered HTML
// report stored alongside), list and recall it later — plus export/import as a
// plain JSON file. Reports stay regenerable from the state; a stored report opens
// without recomputation.

import { useEffect, useRef, useState } from "react";
import { api, type SessionMeta } from "@/lib/api";
import { useT, useLocale } from "@/lib/i18n";
import { collectReportRequest } from "@/lib/report";
import { SESSION_SCHEMA_VERSION, useWorkbench } from "@/lib/store";

export function SessionsPanel() {
  const t = useT();
  const { locale } = useLocale();
  const wb = useWorkbench();
  const [sessions, setSessions] = useState<SessionMeta[]>([]);
  const [name, setName] = useState("");
  const [withReport, setWithReport] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const refresh = async () => setSessions(await api.sessions());
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh().catch(() => undefined); // offline: the list simply stays empty
  }, []);

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setErr(null);
    try {
      await action();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const save = () =>
    run(async () => {
      const res = await api.saveSession({
        name: (name.trim() || wb.label).slice(0, 80),
        schema_version: SESSION_SCHEMA_VERSION,
        state: wb.exportState(),
        report: withReport ? collectReportRequest(wb, locale) : null,
      });
      if (res.report_error) setErr(res.report_error);
      await refresh();
    });

  const load = (meta: SessionMeta) =>
    run(async () => {
      const record = await api.loadSession(meta.name);
      wb.hydrate(record.state);
      wb.setLabel(typeof record.state.label === "string" ? record.state.label : meta.name);
      setName(meta.name);
      wb.setMessages([`${t("sess.loaded")}: ${meta.name}`]);
    });

  const remove = (meta: SessionMeta) =>
    run(async () => {
      await api.deleteSession(meta.name);
      await refresh();
    });

  const exportFile = () => {
    const doc = {
      schema_version: SESSION_SCHEMA_VERSION,
      saved_at: new Date().toISOString(),
      state: wb.exportState(),
    };
    const blob = new Blob([JSON.stringify(doc, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(wb.label || "session").replace(/\s+/g, "_")}_session.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const importFile = (file: File) =>
    run(async () => {
      const doc = JSON.parse(await file.text()) as Record<string, unknown>;
      // accept both the file wrapper ({schema_version, state}) and a bare state
      wb.hydrate(typeof doc.state === "object" && doc.state !== null ? doc.state : doc);
      wb.setMessages([`${t("sess.loaded")}: ${file.name}`]);
    });

  const fmtDate = (iso: string) => {
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleString(locale === "de" ? "de-DE" : "en-GB");
  };

  return (
    <div className="mt-3 border-t border-zinc-200 pt-2">
      <div className="text-[10.5px] uppercase tracking-wider text-zinc-400 px-2 pb-1">
        {t("sess.title")}
      </div>
      <div className="px-2 flex flex-col gap-1.5">
        <div className="flex gap-1">
          <input
            type="text"
            className="flex-1 min-w-0 text-[11.5px]"
            placeholder={`${t("sess.name")} (${wb.label})`}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => void save()}
            className="border border-zinc-300 rounded-md px-2 py-0.5 text-[11.5px] bg-white hover:bg-zinc-50 disabled:opacity-50"
          >
            {busy ? "…" : t("sess.save")}
          </button>
        </div>
        <label className="flex items-center gap-1.5 text-[11.5px] text-zinc-600">
          <input
            type="checkbox"
            checked={withReport}
            onChange={(e) => setWithReport(e.target.checked)}
          />
          {t("sess.withReport")}
        </label>
        {sessions.length === 0 && (
          <div className="text-[11.5px] text-zinc-400">{t("sess.none")}</div>
        )}
        {sessions.map((s) => (
          <div key={s.name} className="border border-zinc-200 rounded-md bg-white px-2 py-1">
            <div className="text-[11.5px] font-medium text-zinc-700 break-all">{s.name}</div>
            <div className="text-[10.5px] text-zinc-400">{fmtDate(s.saved_at)}</div>
            <div className="flex gap-2 pt-0.5 text-[11px]">
              <button
                type="button"
                className="text-blue-700 hover:underline disabled:opacity-50"
                disabled={busy}
                onClick={() => void load(s)}
              >
                {t("sess.load")}
              </button>
              {s.has_report && (
                <a
                  className="text-blue-700 hover:underline"
                  href={api.sessionReportUrl(s.name)}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t("sess.report")}
                </a>
              )}
              <button
                type="button"
                className="ml-auto text-zinc-400 hover:text-red-600 disabled:opacity-50"
                disabled={busy}
                onClick={() => void remove(s)}
              >
                ✕
              </button>
            </div>
          </div>
        ))}
        <div className="flex gap-2 text-[11px] pt-0.5">
          <button type="button" className="text-zinc-500 hover:underline" onClick={exportFile}>
            {t("sess.export")}
          </button>
          <button
            type="button"
            className="text-zinc-500 hover:underline"
            onClick={() => fileRef.current?.click()}
          >
            {t("sess.import")}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void importFile(file);
              e.target.value = "";
            }}
          />
        </div>
        {err && <div className="text-[11px] text-red-600 break-all">{err}</div>}
      </div>
    </div>
  );
}
