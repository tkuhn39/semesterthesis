// Report collector: gathers the INPUT state from the workbench store (capacity request,
// powerflow block, persisted variation results) and downloads the server-rendered,
// self-contained HTML system report (POST /api/report — the backend recomputes
// geometry/capacity/tolerances/dynamics itself, guaranteed consistency).

import { buildCapacityRequest, type Wb } from "@/lib/capacityRequest";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export function collectReportRequest(wb: Wb, locale: string): Record<string, unknown> {
  const pf = wb.powerflow;
  const v = wb.varUi;
  return {
    label: wb.label,
    locale,
    capacity: buildCapacityRequest(wb),
    // geometry context for the report's SSOT block: active fillets + the full allowance
    // band (audit COV-01 — the report used to rebuild with None everywhere)
    geometry: {
      fillet_gear1: wb.fem.fillet_gear1,
      fillet_gear2: wb.fem.fillet_gear2,
      span_allowance_upper_um: [wb.tol.awe1_um, wb.tol.awe2_um],
      span_allowance_lower_um: [wb.tol.awi1_um, wb.tol.awi2_um],
      center_distance_allowance_mm: (wb.tol.a_upper_um - wb.tol.a_lower_um) / 2 / 1000,
    },
    powerflow: {
      speed_shaft1_min1: pf.speed_shaft1_min1,
      torque_nm: pf.torque_nm,
      torque_shaft: pf.torque_shaft,
      load1_type: pf.load1_type,
      load2_type: pf.load2_type,
      operating_hours: wb.operatingUi.operating_hours,
    },
    accuracy_grade: wb.operating.accuracy_grade ?? 8,
    // last Stufenvariation run (persisted in the store) — omitted when never run
    variation:
      v.res && v.req
        ? {
            request: v.req,
            points: v.res.points,
            count: v.res.count,
            valid: v.res.valid,
            pareto: v.res.pareto,
            warnings: v.res.warnings,
          }
        : null,
  };
}

export async function downloadReport(wb: Wb, locale: string): Promise<void> {
  const res = await fetch(`${BASE}/api/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collectReportRequest(wb, locale)),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${wb.label.replace(/\s+/g, "_")}_report.html`;
  a.click();
  URL.revokeObjectURL(url);
}
