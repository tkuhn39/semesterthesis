"""
@module: app.services.report.builder
@context: Domain layer — the interactive HTML system report.
@role: Render ONE self-contained HTML document (no external requests, printable) from
       the computed responses, modelled on the FVA Gesamtsystemreport: sidebar
       navigation (Getriebeeinheit → Stirnradstufe → per-gear norm sections →
       Stufenvariation), attribute tables with per-gear columns and colspan pairing
       rows, and the animated Zahneingriff plot with the exact line of action
       (same construction as the frontend MeshEngagement, vanilla-JS rAF rotation).

       Deliberately BETTER than FVA in one point (user decision): each gear appears
       ONLY under its own norm — a mixed steel/plastic pair gets two separate
       single-column sections (ISO 6336 for the steel gear, VDI 2736 for the plastic
       gear) instead of one table with "−" placeholder rows.

       Plain string templating on purpose — one template, no jinja2 dependency
       (project rule: every dependency syncs conda env + yaml + requirements.txt).
"""

from __future__ import annotations

import datetime as _dt
import html
import math

from pydantic import BaseModel

Locale = str  # "de" | "en"


class ReportData(BaseModel):
    """Everything the template needs — assembled server-side by ``app.api.report``."""

    label: str
    locale: Locale
    version: str
    # Getriebeeinheit / Leistungsfluss (shaft-1/2 convention, ADR-021)
    speed_shaft1_min1: float
    speed_shaft2_min1: float
    torque_shaft1_nm: float | None
    torque_shaft2_nm: float | None
    load1_type: str  # "antrieb" | "abtrieb"
    load2_type: str
    power_kw: float | None
    operating_hours: float
    # Stirnradstufe
    stage_rows: list[tuple[str, str, str | None, str | None, str | None]]
    # (label_key resolved, symbol, v1, v2 | None for colspan, unit)
    geometry_notes: list[str]
    tolerance_rows: list[tuple[str, str, str, str, str]]
    accuracy_grade: int
    factor_rows: list[tuple[str, str, str]]  # (label, symbol, value) — pairing scalars
    dynamics_rows: list[tuple[str, str, str, str]]  # (label, symbol, value, unit)
    # per-gear norm sections: (gear label, material, method, rows[(label, sym, val, unit)])
    gear_sections: list[tuple[str, str, str, list[tuple[str, str, str, str]]]]
    same_method: bool  # both gears share the norm → one two-column table
    # Zahneingriff plot data
    mesh_svg: str
    mesh_script: str
    loa_footer: str
    # Stufenvariation (optional)
    variation_summary: list[tuple[str, str]] | None = None
    variation_head: list[str] | None = None
    variation_rows: list[list[str]] | None = None
    variation_warnings: list[str] | None = None
    variation_pc_svg: str | None = None


# --------------------------------------------------------------------------- #
# small helpers                                                                #
# --------------------------------------------------------------------------- #
def fmt(value: float | None, digits: int, locale: Locale) -> str:
    """Locale-aware number for the report body (de: comma decimals, like the FVA UI)."""
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "–"
    text = f"{value:,.{digits}f}"  # en grouping: 1,234.567
    if locale == "de":
        # swap grouping/decimal via a sentinel ("@" cannot occur in a formatted number)
        text = text.replace(",", "@").replace(".", ",").replace("@", ".")
    return text


def _e(text: str) -> str:
    return html.escape(text, quote=True)


def _tr(cells: list[str], *, head: bool = False) -> str:
    tag = "th" if head else "td"
    return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"


def _attr_table(head: list[str], rows: list[str]) -> str:
    return (
        '<table class="attr">'
        + ("<thead>" + _tr([_e(h) for h in head], head=True) + "</thead>" if head else "")
        + "<tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _section(sec_id: str, title: str, body: str) -> str:
    return f'<section id="{sec_id}"><h2>{_e(title)}</h2>{body}</section>'


_T = {
    "title": ("Gesamtsystemreport", "System report"),
    "unit": ("Getriebeeinheit", "Gear unit"),
    "powerflow": ("Leistungsfluss", "Power flow"),
    "stage": ("Stirnradstufe", "Cylindrical gear stage"),
    "geometry": ("Geometrie (ISO 21771)", "Geometry (ISO 21771)"),
    "mesh": ("Zahneingriff", "Tooth engagement"),
    "tol": ("Toleranzen (ISO 1328-1)", "Tolerances (ISO 1328-1)"),
    "factors": ("K-Faktoren und Paarungsgrößen", "K factors and pairing values"),
    "dynamics": ("Dynamik und Resonanz (ISO 6336-1)", "Dynamics and resonance (ISO 6336-1)"),
    "variation": ("Stufenvariation", "Stage variation"),
    "attribute": ("Attribut", "Attribute"),
    "unit_col": ("Einheit", "Unit"),
    "shaft1": ("Welle 1", "Shaft 1"),
    "shaft2": ("Welle 2", "Shaft 2"),
    "type": ("Typ", "Type"),
    "antrieb": ("Antrieb", "Input"),
    "abtrieb": ("Abtrieb", "Output"),
    "speed": ("Drehzahl", "Speed"),
    "torque": ("Drehmoment", "Torque"),
    "power": ("Leistung", "Power"),
    "hours": ("Betriebsdauer", "Operating time"),
    "grade": ("Verzahnungsqualität (ISO 1328-1)", "Accuracy grade (ISO 1328-1)"),
    "play": ("Abspielen", "Play"),
    "pause": ("Pause", "Pause"),
    "notes": ("Hinweise", "Notes"),
    "created": ("Erstellt", "Created"),
    "warnings": ("Warnungen", "Warnings"),
    "print": ("Drucken", "Print"),
    "norm_note": (
        "Jedes Rad erscheint nur unter seiner Norm (Werkstoff-Dispatch: Stahl → ISO 6336, "
        "Kunststoff → VDI 2736) — keine Platzhalterzeilen wie im FVA-Report.",
        "Each gear appears only under its own norm (material dispatch: steel → ISO 6336, "
        "plastic → VDI 2736) — no placeholder rows like the FVA report.",
    ),
}


def _t(key: str, locale: Locale) -> str:
    de, en = _T[key]
    return de if locale == "de" else en


# --------------------------------------------------------------------------- #
# the template                                                                 #
# --------------------------------------------------------------------------- #
_CSS = """
:root{--navy:#2b4254;--line:#d4d4d8;--muted:#6b7280;}
*{box-sizing:border-box;margin:0;padding:0}
body{font:13px/1.45 "Segoe UI",system-ui,sans-serif;color:#18181b;display:flex}
nav{position:fixed;left:0;top:0;bottom:0;width:230px;background:#f4f4f5;
 border-right:1px solid var(--line);padding:14px;overflow-y:auto}
nav h1{font-size:14px;color:var(--navy);margin-bottom:2px}
nav .meta{font-size:11px;color:var(--muted);margin-bottom:12px}
nav a{display:block;padding:3px 6px;border-radius:5px;color:#18181b;
 text-decoration:none;font-size:12.5px}
nav a:hover{background:#e4e4e7}
nav a.sub{padding-left:18px;color:#3f3f46;font-size:12px}
nav button{margin-top:12px;width:100%;padding:5px;border:1px solid var(--line);
 border-radius:6px;background:#fff;cursor:pointer;font-size:12px}
main{margin-left:230px;padding:22px 30px;max-width:960px}
section{margin-bottom:30px}
h2{font-size:16px;color:var(--navy);border-bottom:2px solid var(--navy);
 padding-bottom:3px;margin-bottom:10px}
h3{font-size:13.5px;color:var(--navy);margin:14px 0 6px}
table.attr{border-collapse:collapse;width:100%;margin:6px 0 12px}
table.attr th{background:#eef2f6;color:var(--navy);text-align:left;font-size:11.5px;
 text-transform:uppercase;letter-spacing:.03em}
table.attr th,table.attr td{border:1px solid var(--line);padding:3.5px 8px}
table.attr td.num{font-variant-numeric:tabular-nums;text-align:right}
/* single PAIR values span both gear columns - centre them so they read as pair
   values, not as gear-2 values (audit V-08) */
table.attr td.num[colspan]{text-align:center}
table.attr td.sym{color:var(--muted);font-family:ui-monospace,monospace;font-size:12px}
table.attr td.unit{color:var(--muted)}
.note{background:#fefce8;border:1px solid #fde68a;border-radius:6px;
 padding:6px 10px;font-size:12px;margin:6px 0}
.info{background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;
 padding:6px 10px;font-size:12px;margin:6px 0}
.plot{border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#f8fafc}
.plot .bar{display:flex;gap:8px;align-items:center;padding:6px 10px;
 border-bottom:1px solid var(--line);background:#fff}
.plot .bar button{padding:3px 10px;border:1px solid var(--line);border-radius:6px;
 background:#fff;cursor:pointer;font-size:12px}
.plot .foot{padding:5px 10px;font-size:11.5px;color:var(--muted);background:#fff;
 border-top:1px solid var(--line)}
@media print{nav{display:none}main{margin:0;max-width:none}
 .plot .bar button{display:none}section{break-inside:avoid}}
"""


def build_report_html(d: ReportData) -> str:
    """Render the complete, self-contained report document."""
    loc = d.locale

    def t(key: str) -> str:
        return _t(key, loc)

    # ---- Getriebeeinheit -------------------------------------------------- #
    def _pf_row(label: str, sym: str, v1: str, v2: str | None, unit: str) -> str:
        if v2 is None:  # pairing value spanning both shaft columns
            return (
                f"<tr><td>{_e(label)}</td><td class='sym'>{_e(sym)}</td>"
                f"<td class='num' colspan='2'>{v1}</td><td class='unit'>{_e(unit)}</td></tr>"
            )
        return (
            f"<tr><td>{_e(label)}</td><td class='sym'>{_e(sym)}</td>"
            f"<td class='num'>{v1}</td><td class='num'>{v2}</td>"
            f"<td class='unit'>{_e(unit)}</td></tr>"
        )

    pf_rows = [
        _pf_row(t("type"), "", _e(t(d.load1_type)), _e(t(d.load2_type)), ""),
        _pf_row(
            t("speed"),
            "n",
            fmt(d.speed_shaft1_min1, 2, loc),
            fmt(d.speed_shaft2_min1, 2, loc),
            "1/min",
        ),
        _pf_row(
            t("torque"),
            "T",
            fmt(d.torque_shaft1_nm, 4, loc),
            fmt(d.torque_shaft2_nm, 4, loc),
            "N·m",
        ),
        _pf_row(t("power"), "P", fmt(d.power_kw, 4, loc), None, "kW"),
        _pf_row(t("hours"), "L_h", fmt(d.operating_hours, 0, loc), None, "h"),
    ]
    unit_html = _attr_table(
        [t("attribute"), "Fz", t("shaft1"), t("shaft2"), t("unit_col")], pf_rows
    )

    # ---- Stirnradstufe: Geometrie ----------------------------------------- #
    geo_rows = []
    for label, sym, v1, v2, unit in d.stage_rows:
        if v2 is None:  # pairing value spanning both gear columns
            geo_rows.append(
                f"<tr><td>{_e(label)}</td><td class='sym'>{_e(sym)}</td>"
                f"<td class='num' colspan='2'>{v1}</td><td class='unit'>{_e(unit or '')}</td></tr>"
            )
        else:
            geo_rows.append(
                f"<tr><td>{_e(label)}</td><td class='sym'>{_e(sym)}</td>"
                f"<td class='num'>{v1}</td><td class='num'>{v2}</td>"
                f"<td class='unit'>{_e(unit or '')}</td></tr>"
            )
    gear1_head = d.gear_sections[0][0]
    gear2_head = d.gear_sections[-1][0]
    geometry_html = _attr_table(
        [t("attribute"), "Fz", gear1_head, gear2_head, t("unit_col")], geo_rows
    )
    notes_html = "".join(f'<div class="note">⚠ {_e(n)}</div>' for n in d.geometry_notes)

    # ---- Zahneingriff ------------------------------------------------------ #
    mesh_html = (
        '<div class="plot"><div class="bar">'
        f"<strong>{_e(t('mesh'))}</strong>"
        f'<button id="anim-toggle" style="margin-left:auto">{_e(t("pause"))}</button>'
        f"</div>{d.mesh_svg}"
        f'<div class="foot">{_e(d.loa_footer)}</div></div>'
    )

    # ---- Toleranzen -------------------------------------------------------- #
    tol_rows = [
        _tr([_e(label), _e(sym), v1, v2, _e(unit)]) for label, sym, v1, v2, unit in d.tolerance_rows
    ]
    tol_html = f'<div class="info">{_e(t("grade"))}: Q{d.accuracy_grade}</div>' + _attr_table(
        [t("attribute"), "Fz", gear1_head, gear2_head, t("unit_col")], tol_rows
    )

    # ---- Faktoren + Dynamik ------------------------------------------------ #
    fac_html = _attr_table(
        [t("attribute"), "Fz", ""],
        [_tr([_e(label), _e(sym), val]) for label, sym, val in d.factor_rows],
    )
    dyn_html = _attr_table(
        [t("attribute"), "Fz", "", t("unit_col")],
        [_tr([_e(label), _e(sym), val, _e(unit)]) for label, sym, val, unit in d.dynamics_rows],
    )

    # ---- per-gear norm sections -------------------------------------------- #
    gear_secs: list[str] = []
    nav_gears: list[str] = []
    if d.same_method:
        head, _mat, method, _rows = d.gear_sections[0]
        rows_by_label: dict[str, list[str]] = {}
        units: dict[str, tuple[str, str]] = {}
        order: list[str] = []
        for gi, (_h, _m, _me, rows) in enumerate(d.gear_sections):
            for label, sym, val, unit in rows:
                if label not in rows_by_label:
                    rows_by_label[label] = ["–", "–"]
                    units[label] = (sym, unit)
                    order.append(label)
                rows_by_label[label][gi] = val
        body_rows = [
            _tr([_e(label), _e(units[label][0]), *rows_by_label[label], _e(units[label][1])])
            for label in order
        ]
        title = f"{method} — {gear1_head} / {gear2_head}"
        gear_secs.append(
            _section(
                "sec-norm",
                title,
                _attr_table(
                    [t("attribute"), "Fz", gear1_head, gear2_head, t("unit_col")], body_rows
                ),
            )
        )
        nav_gears.append(f'<a class="sub" href="#sec-norm">{_e(method)}</a>')
    else:
        gear_secs.append(f'<div class="info">ⓘ {_e(t("norm_note"))}</div>')
        for i, (head, mat, method, rows) in enumerate(d.gear_sections, start=1):
            body_rows = [_tr([_e(label), _e(sym), val, _e(unit)]) for label, sym, val, unit in rows]
            title = f"{head} — {mat} ({method})"
            gear_secs.append(
                _section(
                    f"sec-gear{i}",
                    title,
                    _attr_table([t("attribute"), "Fz", "", t("unit_col")], body_rows),
                )
            )
            nav_gears.append(f'<a class="sub" href="#sec-gear{i}">{_e(head)}</a>')

    # ---- Stufenvariation ---------------------------------------------------- #
    var_html = ""
    nav_var = ""
    if d.variation_rows is not None and d.variation_head is not None:
        summary = "".join(
            f"<tr><td>{_e(k)}</td><td class='num'>{v}</td></tr>"
            for k, v in (d.variation_summary or [])
        )
        warn = "".join(f'<div class="note">⚠ {_e(w)}</div>' for w in (d.variation_warnings or []))
        table = _attr_table(
            d.variation_head,
            [
                "<tr>" + "".join(f"<td class='num'>{c}</td>" for c in row) + "</tr>"
                for row in d.variation_rows
            ],
        )
        pc = d.variation_pc_svg or ""
        var_html = _section(
            "sec-variation",
            t("variation"),
            f"<table class='attr'><tbody>{summary}</tbody></table>{warn}{pc}<h3>Top</h3>{table}",
        )
        nav_var = f'<a href="#sec-variation">{_e(t("variation"))}</a>'

    created = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    doc = f"""<!DOCTYPE html>
<html lang="{loc}">
<head>
<meta charset="utf-8">
<title>{_e(d.label)} — {_e(t("title"))}</title>
<style>{_CSS}</style>
</head>
<body>
<nav>
  <h1>{_e(d.label)}</h1>
  <div class="meta">{_e(t("title"))} · v{_e(d.version)}<br>{_e(t("created"))}: {created}</div>
  <a href="#sec-unit">{_e(t("unit"))}</a>
  <a href="#sec-stage">{_e(t("stage"))}</a>
  <a class="sub" href="#sec-geometry">{_e(t("geometry"))}</a>
  <a class="sub" href="#sec-mesh">{_e(t("mesh"))}</a>
  <a class="sub" href="#sec-tol">{_e(t("tol"))}</a>
  <a class="sub" href="#sec-dyn">{_e(t("dynamics"))}</a>
  {"".join(nav_gears)}
  {nav_var}
  <button onclick="window.print()">{_e(t("print"))}</button>
</nav>
<main>
  {_section("sec-unit", t("unit") + " — " + t("powerflow"), unit_html)}
  <section id="sec-stage"><h2>{_e(t("stage"))}</h2>
    <section id="sec-geometry"><h3>{_e(t("geometry"))}</h3>{geometry_html}{notes_html}</section>
    <section id="sec-mesh"><h3>{_e(t("mesh"))}</h3>{mesh_html}</section>
    <section id="sec-tol"><h3>{_e(t("tol"))}</h3>{tol_html}</section>
    <section id="sec-fac"><h3>{_e(t("factors"))}</h3>{fac_html}</section>
    <section id="sec-dyn"><h3>{_e(t("dynamics"))}</h3>{dyn_html}</section>
  </section>
  {"".join(gear_secs)}
  {var_html}
</main>
<script>{d.mesh_script}</script>
</body>
</html>"""
    return doc
