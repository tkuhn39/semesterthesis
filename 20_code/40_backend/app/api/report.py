"""
@module: app.api.report
@context: FastAPI backend — the interactive HTML system report endpoint.
@role: ``POST /api/report`` receives the frontend's INPUT state (stage + capacity
       request + powerflow block + optional variation results) and composes the
       report SERVER-SIDE from the same functions the live tabs use (geometry,
       capacity with per-gear norm dispatch, ISO 1328 tolerances, native dynamics,
       tooth profile + line of action) — guaranteed consistency, the frontend never
       ships computed values. The renderer lives in ``app.services.report``.
"""

from __future__ import annotations

import math

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app import __version__
from app.api.analysis import (
    CapacityRequest,
    DynamicsRequest,
    GearCapacity,
    GeometryReportRequest,
    MaterialParams,
    ToleranceRequest,
    ToothGear,
    ToothProfileResponse,
    VariationPoint,
    VariationRequest,
    _report_allowances,
    capacity,
    dynamics,
    geometry,
    tolerances,
    tooth_profile,
)
from app.api.stage_params import StageParams
from app.services.geometry.report import compute_geometry_report

router = APIRouter(prefix="/api", tags=["report"])


class ReportPowerflow(BaseModel):
    """The Leistungsfluss inputs (shaft-1/2 convention; ONE torque, see store)."""

    speed_shaft1_min1: float = 2250.0
    torque_nm: float | None = 8.0
    torque_shaft: int = Field(default=2, ge=1, le=2)
    load1_type: str = "abtrieb"
    load2_type: str = "antrieb"
    operating_hours: float = 100000.0


class ReportVariation(BaseModel):
    """The persisted Stufenvariation results (points from the last run, varUi)."""

    request: VariationRequest
    points: list[VariationPoint]
    count: int
    valid: int
    pareto: int
    warnings: list[str] = Field(default_factory=list)


class ReportRequest(BaseModel):
    label: str = "kst-E"
    locale: str = Field(default="de", pattern="^(de|en)$")
    capacity: CapacityRequest = Field(default_factory=CapacityRequest)
    powerflow: ReportPowerflow = Field(default_factory=lambda: ReportPowerflow())
    accuracy_grade: int = 8
    variation: ReportVariation | None = None
    # geometry context (active fillets, allowance band, series) for the SSOT block —
    # audit COV-01: the report used to rebuild with None everywhere, collapsing the
    # E_sns/E_sni band and dropping the selected fillet from the geometry section
    geometry: GeometryReportRequest | None = None


def _de(locale: str, de: str, en: str) -> str:
    return de if locale == "de" else en


def _gear_outline_points(g: ToothGear) -> str:
    """Full-gear polygon points (same walk as the frontend gearOutline)."""
    right = g.half_flank
    tooth = [(-x, y) for x, y in right] + [(x, y) for x, y in reversed(right)]
    pitch = 2.0 * math.pi / g.teeth
    pts: list[str] = []
    for k in range(g.teeth):
        c, s = math.cos(k * pitch), math.sin(k * pitch)
        for x, y in tooth:
            pts.append(f"{c * x - s * y:.3f},{-(s * x + c * y):.3f}")
    return " ".join(pts)


def _mesh_svg(profile: ToothProfileResponse, locale: str) -> tuple[str, str, str]:
    """The Zahneingriff SVG (zoom on T1…T2 like the app) + its animation script."""
    loa = profile.line_of_action
    a = profile.center_distance_mm
    g1, g2 = profile.pinion, profile.wheel
    p1 = 360.0 / g1.teeth
    if loa is not None:
        cx = (loa.t1[0] + loa.t2[0]) / 2.0
        cy = -(loa.t1[1] + loa.t2[1]) / 2.0
        half_w = max(abs(loa.t2[0] - loa.t1[0]) / 2.0 * 1.35 + 0.8, 1.7 * loa.path_of_contact_mm)
        half_h = max(abs(loa.t2[1] - loa.t1[1]) / 2.0 * 1.2 + 1.8, 1.7 * loa.path_of_contact_mm)
    else:
        cx, cy = a / 2.0, 0.0
        half_w = half_h = a
    view = f"{cx - half_w:.2f} {cy - half_h:.2f} {2 * half_w:.2f} {2 * half_h:.2f}"

    overlay = ""
    footer = ""
    if loa is not None:
        pts = {
            k: (getattr(loa, k)[0], -getattr(loa, k)[1])
            for k in ("t1", "t2", "a", "b", "c", "d", "e")
        }
        rb1, rb2 = loa.base_radius_mm
        rw1, rw2 = loa.working_pitch_radius_mm
        circles = "".join(
            f'<circle cx="{cxx}" cy="0" r="{r:.4f}" fill="none" stroke="#2b4254" '
            f'stroke-width="0.05" stroke-dasharray="0.6 0.45"/>'
            for cxx, r in ((0, rb1), (a, rb2), (0, rw1), (a, rw2))
        )
        cxp, cyp = pts["c"]
        cross = (
            f'<line x1="{cxp - 1000}" y1="{cyp}" x2="{cxp + 1000}" y2="{cyp}" '
            'stroke="#9ca3af" stroke-width="0.035"/>'
            f'<line x1="{cxp}" y1="{cyp - 1000}" x2="{cxp}" y2="{cyp + 1000}" '
            'stroke="#9ca3af" stroke-width="0.035"/>'
        )
        t1, t2, pa, pe = pts["t1"], pts["t2"], pts["a"], pts["e"]
        lines = (
            f'<line x1="{t1[0]}" y1="{t1[1]}" x2="{t2[0]}" y2="{t2[1]}" '
            'stroke="#111827" stroke-width="0.06"/>'
            f'<line x1="{pa[0]}" y1="{pa[1]}" x2="{pe[0]}" y2="{pe[1]}" '
            'stroke="#e37222" stroke-width="0.14"/>'
        )
        down = {"t1", "t2", "b", "e"}
        labels = []
        for key, (px, py) in pts.items():
            ly = py + (1.3 if key in down else -1.3)
            ty = ly + (0.72 if key in down else -0.22)
            name = key.upper()
            labels.append(
                f'<circle cx="{px}" cy="{py}" r="0.16" fill="#111827"/>'
                f'<line x1="{px}" y1="{py}" x2="{px}" y2="{ly}" '
                'stroke="#6b7280" stroke-width="0.035"/>'
                f'<text x="{px}" y="{ty}" font-size="0.85" text-anchor="middle" fill="#111827" '
                f'style="paint-order:stroke;stroke:white;stroke-width:0.18">{name}</text>'
            )
        overlay = circles + cross + lines + "".join(labels)
        eps = loa.path_of_contact_mm / loa.transverse_base_pitch_mm
        footer = (
            f"α_wt = {loa.working_pressure_angle_deg:.3f}° · g_α = {loa.path_of_contact_mm:.3f} mm "
            f"· ε_α = {eps:.3f} · "
            + _de(
                locale,
                "φ₂ = −φ₁·z₁/z₂ (kinematisch gekoppelt)",
                "φ₂ = −φ₁·z₁/z₂ (kinematically coupled)",
            )
        )

    svg = (
        f'<svg id="mesh-svg" viewBox="{view}" style="width:100%;height:430px;display:block" '
        f'preserveAspectRatio="xMidYMid meet">'
        f'<g id="rg1" transform="rotate({90 + p1 / 2.0:.4f} 0 0)">'
        f'<polygon points="{_gear_outline_points(g1)}" '
        'fill="#cfe3f4" stroke="#3070b3" stroke-width="0.1"/></g>'
        f'<g id="rg2" transform="translate({a} 0) rotate(-90 0 0)">'
        f'<polygon points="{_gear_outline_points(g2)}" '
        'fill="#e8eef4" stroke="#64748b" stroke-width="0.1"/></g>'
        f"{overlay}</svg>"
    )
    script = f"""
(function() {{
  var z1 = {g1.teeth}, z2 = {g2.teeth}, a = {a}, base1 = {90 + p1 / 2.0:.4f};
  var phi = 0, running = true, last = 0;
  var g1 = document.getElementById('rg1'), g2 = document.getElementById('rg2');
  var btn = document.getElementById('anim-toggle');
  var labels = {{play: {_de(locale, '"Abspielen"', '"Play"')},
    pause: {_de(locale, '"Pause"', '"Pause"')}}};
  function tick(ts) {{
    if (running) {{
      if (last) phi += 8 * (ts - last) / 1000;
      g1.setAttribute('transform', 'rotate(' + (base1 + phi) + ' 0 0)');
      g2.setAttribute('transform',
        'translate(' + a + ' 0) rotate(' + (-90 - phi * z1 / z2) + ' 0 0)');
    }}
    last = ts;
    requestAnimationFrame(tick);
  }}
  if (btn) btn.onclick = function() {{ running = !running;
    btn.textContent = running ? labels.pause : labels.play; }};
  requestAnimationFrame(tick);
}})();
"""
    return svg, script, footer


def _norm_rows(g: GearCapacity, locale: str) -> list[tuple[str, str, str, str]]:
    """One gear's capacity rows under ITS norm — no placeholder rows, ever."""

    def n(v: float | None, digits: int = 2) -> str:
        from app.services.report.builder import fmt

        return fmt(v, digits, locale)

    rows: list[tuple[str, str, str, str]] = [
        (
            _de(locale, "Zahnfußspannung", "Tooth root stress"),
            "σ_F",
            n(g.root_stress_mpa, 1),
            "N/mm²",
        ),
        (
            _de(locale, "Zulässige Fußspannung", "Permissible root stress"),
            "σ_FP",
            n(g.root_permissible_mpa, 1),
            "N/mm²",
        ),
        (_de(locale, "Fußsicherheit", "Root safety"), "S_F", n(g.root_safety), "–"),
        (
            _de(locale, "Flankenpressung", "Contact stress"),
            "σ_H",
            n(g.flank_stress_mpa, 1),
            "N/mm²",
        ),
        (
            _de(locale, "Zulässige Pressung", "Permissible contact stress"),
            "σ_HP",
            n(g.flank_permissible_mpa, 1),
            "N/mm²",
        ),
        (_de(locale, "Flankensicherheit", "Flank safety"), "S_H", n(g.flank_safety), "–"),
        # VDI branch reports the TIP-LOAD factors — label them Y_Fa/Y_Sa (audit MAT-13)
        (
            _de(locale, "Formfaktor", "Form factor"),
            "Y_Fa" if g.method.startswith("VDI") else "Y_F",
            n(g.form_factor, 3),
            "–",
        ),
        (
            _de(locale, "Spannungskorrekturfaktor", "Stress correction factor"),
            "Y_Sa" if g.method.startswith("VDI") else "Y_S",
            n(g.stress_correction, 3),
            "–",
        ),
    ]
    # ISO 6336-2/-3 strength sub-factors (steel branch; the folded products σ_HP/σ_FP
    # stay above — user requirement 2026-08-18: print the full factor chain)
    if g.lubricant_factor is not None:
        rows.append(
            (
                _de(
                    locale, "Schmierstoff-/Geschw.-/Rauheitsfaktor", "Lubricant/velocity/roughness"
                ),
                "Z_L · Z_v · Z_R",
                f"{n(g.lubricant_factor, 3)} · {n(g.velocity_factor, 3)} · "
                f"{n(g.roughness_factor, 3)}",
                "–",
            )
        )
    if g.work_hardening_factor is not None:
        rows.append(
            (
                _de(locale, "Werkstoffpaarungs-/Größenfaktor", "Work-hardening/size factor"),
                "Z_W · Z_X",
                f"{n(g.work_hardening_factor, 3)} · {n(g.size_factor_flank, 3)}",
                "–",
            )
        )
    if g.life_factor_flank is not None:
        rows.append(
            (
                _de(locale, "Lebensdauerfaktor Flanke", "Flank life factor"),
                "Z_NT",
                n(g.life_factor_flank, 3),
                "–",
            )
        )
    if g.notch_sensitivity_factor is not None:
        rows.append(
            (
                _de(
                    locale,
                    "Rel. Stützziffer / Oberflächenfaktor",
                    "Rel. notch sensitivity / surface",
                ),
                "Y_δrelT · Y_RrelT",
                f"{n(g.notch_sensitivity_factor, 3)} · {n(g.surface_factor, 3)}",
                "–",
            )
        )
    if g.size_factor_root is not None:
        rows.append(
            (
                _de(locale, "Größenfaktor Fuß", "Root size factor"),
                "Y_X",
                n(g.size_factor_root, 3),
                "–",
            )
        )
    if g.life_factor_root is not None:
        rows.append(
            (
                _de(locale, "Zahnfuß-Zeitfaktor", "Root life factor"),
                "Y_NT",
                n(g.life_factor_root, 3),
                "–",
            )
        )
    # plastic-only quantities exist only where VDI 2736 computed them
    if g.tooth_temperature_c is not None:
        rows.append(
            (
                _de(locale, "Zahntemperatur", "Tooth temperature"),
                "ϑ_Z",
                n(g.tooth_temperature_c, 1),
                "°C",
            )
        )
    if g.wear_um is not None:
        rows.append((_de(locale, "Verschleiß", "Wear"), "W_m", n(g.wear_um, 1), "µm"))
    if g.allowable_wear_um is not None:
        rows.append(
            (
                _de(locale, "Zulässiger Verschleiß", "Allowable wear"),
                "W_zul",
                n(g.allowable_wear_um, 1),
                "µm",
            )
        )
    if g.deformation_mm is not None:
        rows.append(
            (_de(locale, "Zahnverformung", "Tooth deflection"), "λ", n(g.deformation_mm, 4), "mm")
        )
    if g.peak_stress_mpa is not None:
        rows.append(
            (
                _de(locale, "Statische Spitzenlast", "Static peak load"),
                "σ_F,P",
                n(g.peak_stress_mpa, 1),
                "N/mm²",
            )
        )
    if g.peak_safety is not None:
        rows.append(
            (_de(locale, "Statische Sicherheit", "Static safety"), "S_stat", n(g.peak_safety), "–")
        )
    return rows


def _variation_pc_svg(points: list[VariationPoint], root_min: float) -> str:
    """Static parallel-coordinates SVG (grey lines, Pareto in colour)."""
    if not points:
        return ""
    dims: list[tuple[str, str]] = [
        ("z1", "z₁"),
        ("x1", "x₁"),
        ("center_distance_mm", "a"),
        ("total_contact_ratio", "ε_γ"),
        ("root_safety_wheel", "S_F"),
        ("weight_g", "Gew."),
    ]
    w, h, pad_x, pad_t, pad_b = 760, 230, 22, 16, 26
    cols = []
    for key, _label in dims:
        vals = [getattr(p, key) for p in points if getattr(p, key) is not None]
        lo, hi = (min(vals), max(vals)) if vals else (0.0, 1.0)
        cols.append((lo, hi if hi != lo else lo + 1.0))
    ax = lambda j: pad_x + j * (w - 2 * pad_x) / (len(dims) - 1)  # noqa: E731
    parts = [f'<svg viewBox="0 0 {w} {h}" style="width:100%;display:block;background:#fff">']
    for j, (_key, label) in enumerate(dims):
        parts.append(
            f'<line x1="{ax(j):.1f}" y1="{pad_t}" x2="{ax(j):.1f}" '
            f'y2="{h - pad_b}" stroke="#d4d4d8"/>'
            f'<text x="{ax(j):.1f}" y="{h - pad_b + 14}" font-size="9.5" '
            f'text-anchor="middle" fill="#6b7280">{label}</text>'
        )
    for p in points:
        seg = []
        for j, (key, _label) in enumerate(dims):
            v = getattr(p, key)
            lo, hi = cols[j]
            y = pad_t + (1 - ((v if v is not None else lo) - lo) / (hi - lo)) * (h - pad_t - pad_b)
            seg.append(f"{'M' if j == 0 else 'L'}{ax(j):.1f},{y:.1f}")
        good = p.root_safety_wheel is not None and p.root_safety_wheel >= root_min
        color = "#9fba36" if (p.pareto and good) else ("#2563eb" if p.pareto else "#d4d4d8")
        width_px = 1.4 if p.pareto else 0.6
        opacity = 0.9 if p.pareto else 0.4
        parts.append(
            f'<path d="{" ".join(seg)}" fill="none" stroke="{color}" '
            f'stroke-width="{width_px}" stroke-opacity="{opacity}"/>'
        )
    parts.append("</svg>")
    return "".join(parts)


@router.post("/report", response_class=HTMLResponse)
def report(req: ReportRequest) -> HTMLResponse:
    """Compose + render the interactive HTML system report (self-contained)."""
    from app.services.report import ReportData, build_report_html
    from app.services.report.builder import fmt

    loc = req.locale
    stage_params = req.capacity.stage
    stage = stage_params.stage()
    geo = geometry(stage_params)
    cap = capacity(req.capacity)
    profile = tooth_profile(stage_params)

    # kinematics from the ONE powerflow torque (same chain as the store DERIVED paths)
    z1, z2 = stage.teeth
    n1 = req.powerflow.speed_shaft1_min1
    n2 = -n1 * z1 / z2
    t_raw = req.powerflow.torque_nm
    t1: float | None = None
    t2: float | None = None
    power_kw: float | None = None
    if t_raw is not None:
        if req.powerflow.torque_shaft == 1:
            t1, t2 = t_raw, t_raw * z2 / z1
        else:
            t2, t1 = t_raw, t_raw * z1 / z2
        power_kw = abs(2.0 * math.pi * n1 / 60.0 * t1) / 1000.0

    # same materials + accuracy inputs as the capacity section (GAP-01: the K-factors of
    # the dynamics block must match the ones the capacity chain used)
    cap_req = req.capacity
    dyn = dynamics(
        DynamicsRequest(
            stage=stage_params,
            pinion_speed_min1=cap_req.pinion_speed_min1,
            pinion_torque_nm=cap_req.pinion_torque_nm,
            application_factor=cap_req.application_factor,
            accuracy_grade=cap_req.accuracy_grade,
            base_pitch_deviation_um=cap_req.base_pitch_deviation_um,
            profile_form_deviation_um=cap_req.profile_form_deviation_um,
            helix_slope_deviation_um=cap_req.helix_slope_deviation_um,
            mesh_misalignment_um=cap_req.mesh_misalignment_um,
            **{f: getattr(cap_req, f) for f in MaterialParams.model_fields},
        )
    )

    # ISO 1328 tolerances per gear (each gear its own reference diameter/width)
    widths = stage.face_width_mm or (20.0, 20.0)
    tols = [
        tolerances(
            ToleranceRequest(
                accuracy_grade=req.accuracy_grade,
                normal_module_mm=stage.normal_module_mm,
                teeth=stage.teeth[i],
                reference_diameter_mm=stage.reference_diameter_mm[i],
                face_width_mm=widths[i],
                helix_angle_deg=stage.helix_angle_deg,
            )
        )
        for i in range(2)
    ]

    def n(v: float | None, digits: int = 3) -> str:
        return fmt(v, digits, loc)

    d = _de  # brevity

    stage_rows: list[tuple[str, str, str | None, str | None, str | None]] = [
        (d(loc, "Normalmodul", "Normal module"), "m_n", n(stage.normal_module_mm, 3), None, "mm"),
        (
            d(loc, "Normaleingriffswinkel", "Normal pressure angle"),
            "α_n",
            n(stage.normal_pressure_angle_deg, 3),
            None,
            "°",
        ),
        (d(loc, "Schrägungswinkel", "Helix angle"), "β", n(stage.helix_angle_deg, 3), None, "°"),
        (d(loc, "Zähnezahl", "Number of teeth"), "z", str(stage.teeth[0]), str(stage.teeth[1]), ""),
        (
            d(loc, "Profilverschiebungsfaktor", "Profile shift coefficient"),
            "x",
            n(stage.profile_shift[0], 4),
            n(stage.profile_shift[1], 4),
            "",
        ),
        (d(loc, "Zahnbreite", "Face width"), "b", n(widths[0], 1), n(widths[1], 1), "mm"),
        (
            d(loc, "Teilkreisdurchmesser", "Reference diameter"),
            "d",
            n(geo.reference_diameter_mm[0]),
            n(geo.reference_diameter_mm[1]),
            "mm",
        ),
        (
            d(loc, "Grundkreisdurchmesser", "Base diameter"),
            "d_b",
            n(geo.base_diameter_mm[0]),
            n(geo.base_diameter_mm[1]),
            "mm",
        ),
        (
            d(loc, "Kopfkreisdurchmesser", "Tip diameter"),
            "d_a",
            n(geo.tip_diameter_mm[0]),
            n(geo.tip_diameter_mm[1]),
            "mm",
        ),
        (
            d(loc, "Betriebsachsabstand", "Working centre distance"),
            "a_w",
            n(geo.working_center_distance_mm),
            None,
            "mm",
        ),
        (
            d(loc, "Betriebseingriffswinkel", "Working pressure angle"),
            "α_wt",
            n(geo.working_pressure_angle_deg),
            None,
            "°",
        ),
        (
            d(loc, "Profilüberdeckung", "Transverse contact ratio"),
            "ε_α",
            n(geo.transverse_contact_ratio, 4),
            None,
            "",
        ),
        (d(loc, "Sprungüberdeckung", "Overlap ratio"), "ε_β", n(geo.overlap_ratio, 4), None, ""),
        (
            d(loc, "Gesamtüberdeckung", "Total contact ratio"),
            "ε_γ",
            n(geo.total_contact_ratio, 4),
            None,
            "",
        ),
    ]
    # --- full SSOT geometry block (DIN ISO 21771 / DIN 21773 / DIN 3967) ---
    # the client's geometry context (fillets, allowance band, series) with THE one stage
    # forced on top — never a second stage source (audit COV-01)
    default_grq = GeometryReportRequest(
        stage=StageParams(),
        fillet_gear1=None,
        fillet_gear2=None,
        ball_diameter_gear1_mm=None,
        ball_diameter_gear2_mm=None,
        center_distance_allowance_mm=None,
        span_allowance_upper_um=None,
        span_allowance_lower_um=None,
        allowance_series_gear1=None,
        allowance_series_gear2=None,
        tolerance_series_gear1=None,
        tolerance_series_gear2=None,
    )
    grq = (req.geometry or default_grq).model_copy(
        update={"stage": req.capacity.stage or StageParams()}
    )
    up_al, low_al = _report_allowances(grq, stage)
    rep = compute_geometry_report(
        stage,
        span_allowance_upper_mm=up_al,
        span_allowance_lower_mm=low_al,
        center_distance_allowance_mm=grq.center_distance_allowance_mm,
    )
    g1, g2, pr = rep.gear1, rep.gear2, rep.pair
    stage_rows += [
        (d(loc, "Stirnteilung", "Transverse pitch"), "p_t", n(pr.transverse_pitch_mm), None, "mm"),
        (
            d(loc, "Eingriffsteilung", "Base pitch"),
            "p_et",
            n(pr.transverse_base_pitch_mm),
            None,
            "mm",
        ),
        (
            d(loc, "Eingriffsstrecke", "Path of contact"),
            "g_α",
            n(pr.path_of_contact_mm),
            None,
            "mm",
        ),
        (
            d(loc, "Gemeinsame Zahnhöhe", "Common tooth height"),
            "h_gem",
            n(pr.common_tooth_height_mm),
            None,
            "mm",
        ),
        (
            d(loc, "Wälzkreisdurchmesser", "Working pitch diameter"),
            "d_w",
            n(g1.working_pitch_diameter_mm),
            n(g2.working_pitch_diameter_mm),
            "mm",
        ),
        (
            d(loc, "Kopf-Formkreisdurchmesser", "Tip form diameter"),
            "d_Fa",
            n(g1.tip_form_diameter_mm),
            n(g2.tip_form_diameter_mm),
            "mm",
        ),
        (
            d(loc, "Kopfkantenbruch (radial)", "Tip edge break (radial)"),
            "h_K",
            n(g1.tip_chamfer_radial_mm),
            n(g2.tip_chamfer_radial_mm),
            "mm",
        ),
        (
            d(loc, "Nutzkreisdurchmesser am Kopf", "Usable tip diameter"),
            "d_Na",
            n(g1.usable_tip_diameter_mm),
            n(g2.usable_tip_diameter_mm),
            "mm",
        ),
        (
            d(loc, "Nutzkreisdurchmesser am Fuß", "Usable root diameter"),
            "d_Nf",
            n(g1.usable_root_diameter_mm),
            n(g2.usable_root_diameter_mm),
            "mm",
        ),
        (
            d(loc, "Fuß-Formkreisdurchmesser", "Root form diameter"),
            "d_Ff",
            n(g1.root_form_diameter_mm),
            n(g2.root_form_diameter_mm),
            "mm",
        ),
        (
            d(loc, "Formübermaß", "Form reserve"),
            "c_n",
            n(g1.form_reserve_mm),
            n(g2.form_reserve_mm),
            "mm",
        ),
        (
            d(loc, "Fußkreisdurchmesser", "Root diameter"),
            "d_f",
            n(g1.root_diameter_mm),
            n(g2.root_diameter_mm),
            "mm",
        ),
        (
            d(loc, "Zahnhöhe", "Tooth height"),
            "h",
            n(g1.tooth_height_mm),
            n(g2.tooth_height_mm),
            "mm",
        ),
        (
            d(loc, "Kopfspiel (Istwert)", "Tip clearance (actual)"),
            "c",
            n(g1.tip_clearance_mm),
            n(g2.tip_clearance_mm),
            "mm",
        ),
        (
            d(loc, "Gleitfaktor am Zahnkopf", "Sliding factor at tip"),
            "K_ga",
            n(g1.sliding_factor_tip),
            n(g2.sliding_factor_tip),
            "",
        ),
        (
            d(loc, "Spez. Gleiten (Kopf/Fuß)", "Specific sliding (tip/root)"),
            "ζ_a / ζ_f",
            f"{n(g1.specific_sliding_tip)} / {n(g1.specific_sliding_root)}",
            f"{n(g2.specific_sliding_tip)} / {n(g2.specific_sliding_root)}",
            "",
        ),
        (
            d(loc, "Zahndicke (Normalschnitt)", "Tooth thickness (normal)"),
            "s_n",
            n(g1.tooth_thickness_normal_mm),
            n(g2.tooth_thickness_normal_mm),
            "mm",
        ),
        (
            d(loc, "Zahnlückenweite", "Space width"),
            "e_n",
            n(g1.space_width_normal_mm),
            n(g2.space_width_normal_mm),
            "mm",
        ),
        (
            d(loc, "Erz.-Profilverschiebungsfaktor", "Generation profile shift"),
            "x_E",
            n(g1.generation_profile_shift, 4),
            n(g2.generation_profile_shift, 4),
            "",
        ),
        (
            d(loc, "Zahndickensehne (d_a − 2·m_n)", "Chordal thickness (d_a − 2·m_n)"),
            "s̄_cn",
            n(g1.chordal_thickness_mm),
            n(g2.chordal_thickness_mm),
            "mm",
        ),
        (
            d(loc, "Höhe über der Sehne", "Height over chord"),
            "h̄_c",
            n(g1.chordal_height_mm),
            n(g2.chordal_height_mm),
            "mm",
        ),
        (
            d(loc, "Zahnweite (Messzähnezahl)", "Span measurement (tooth count)"),
            "W_k (k)",
            f"{n(g1.span_measurement_mm)} ({g1.span_teeth})",
            f"{n(g2.span_measurement_mm)} ({g2.span_teeth})",
            "mm",
        ),
        (
            d(loc, "Diam. Zweikugelmaß", "Diametral two-ball measure"),
            "M_dK",
            n(g1.two_ball_measure_mm),
            n(g2.two_ball_measure_mm),
            "mm",
        ),
        (
            d(loc, "Messtückdurchmesser", "Measuring element diameter"),
            "D_M",
            n(g1.ball_diameter_mm),
            n(g2.ball_diameter_mm),
            "mm",
        ),
    ]
    if g1.thickness_allowance_upper_mm is not None:
        stage_rows += [
            (
                d(loc, "Zahndickenabmaße (ob./unt.)", "Thickness allowances (up/low)"),
                "E_sns/E_sni",
                f"{n(g1.thickness_allowance_upper_mm)} / {n(g1.thickness_allowance_lower_mm)}",
                f"{n(g2.thickness_allowance_upper_mm)} / {n(g2.thickness_allowance_lower_mm)}",
                "mm",
            ),
        ]
    if pr.backlash_normal_mm is not None:
        stage_rows += [
            (
                d(loc, "Verdreh-/Normalflankenspiel", "Circumferential/normal backlash"),
                "j_t / j_n",
                f"{n(pr.backlash_circumferential_mm)} / {n(pr.backlash_normal_mm)}",
                None,
                "mm",
            ),
        ]

    tol_rows = [
        (
            d(loc, "Einzelteilungsabweichung", "Single pitch deviation"),
            "f_ptT",
            n(tols[0].tolerances.single_pitch, 1),
            n(tols[1].tolerances.single_pitch, 1),
            "µm",
        ),
        (
            d(loc, "Gesamtteilungsabweichung", "Total cumulative pitch deviation"),
            "F_pT",
            n(tols[0].tolerances.total_pitch, 1),
            n(tols[1].tolerances.total_pitch, 1),
            "µm",
        ),
        (
            d(loc, "Profil-Formabweichung", "Profile form deviation"),
            "f_fαT",
            n(tols[0].tolerances.profile_form, 1),
            n(tols[1].tolerances.profile_form, 1),
            "µm",
        ),
        (
            d(loc, "Profil-Gesamtabweichung", "Total profile deviation"),
            "F_αT",
            n(tols[0].tolerances.profile_total, 1),
            n(tols[1].tolerances.profile_total, 1),
            "µm",
        ),
        (
            d(loc, "Flankenlinien-Gesamtabweichung", "Total helix deviation"),
            "F_βT",
            n(tols[0].tolerances.helix_total, 1),
            n(tols[1].tolerances.helix_total, 1),
            "µm",
        ),
    ]

    f = cap.factors
    factor_rows = [
        (d(loc, "Anwendungsfaktor", "Application factor"), "K_A", n(f.application_factor)),
        (d(loc, "Dynamikfaktor", "Dynamic factor"), "K_v", n(f.dynamic_factor)),
        (d(loc, "Stirnfaktor", "Transverse factor"), "K_Hα", n(f.transverse_factor)),
        (d(loc, "Breitenfaktor", "Face load factor"), "K_Hβ", n(f.face_load_factor)),
        (d(loc, "Elastizitätsfaktor", "Elasticity factor"), "Z_E", n(f.elasticity_factor, 1)),
        (d(loc, "Zonenfaktor", "Zone factor"), "Z_H", n(f.zone_factor)),
    ]

    dynamics_rows = [
        (
            d(loc, "Eingriffssteifigkeit", "Mesh stiffness"),
            "c_γα",
            n(dyn.mesh_stiffness, 2),
            "N/(mm·µm)",
        ),
        (
            d(loc, "Resonanzdrehzahl", "Resonance speed"),
            "n_E1",
            n(dyn.resonance_speed_min1, 0),
            "1/min",
        ),
        (d(loc, "Bezugsdrehzahl", "Reference speed ratio"), "N", n(dyn.resonance_ratio), "–"),
        (d(loc, "Bereich", "Regime"), "", dyn.regime, ""),
    ]

    gear_heads = (
        f"{d(loc, 'Rad', 'Gear')} 1 ({cap.pinion.material})",
        f"{d(loc, 'Rad', 'Gear')} 2 ({cap.wheel.material})",
    )
    gear_sections = [
        (gear_heads[0], cap.pinion.material, cap.pinion.method, _norm_rows(cap.pinion, loc)),
        (gear_heads[1], cap.wheel.material, cap.wheel.method, _norm_rows(cap.wheel, loc)),
    ]

    mesh_svg, mesh_script, loa_footer = _mesh_svg(profile, loc)

    variation_summary = variation_head = variation_rows = variation_warnings = pc_svg = None
    if req.variation is not None and req.variation.points:
        v = req.variation
        variation_summary = [
            (d(loc, "Varianten", "Variants"), str(v.count)),
            (d(loc, "Erfolgreich", "Successful"), str(v.valid)),
            ("Pareto", str(v.pareto)),
        ]
        variation_head = ["z₁", "z₂", "x₁", "x₂", "m_n", "b", "b₂", "a", "ε_γ", "S_F", "g"]
        top = sorted(
            v.points,
            key=lambda p: -(p.root_safety_wheel if p.root_safety_wheel is not None else -1e9),
        )[:20]
        variation_rows = [
            [
                n(p.z1, 0),
                n(p.z2, 0),
                n(p.x1, 3),
                n(p.x2, 3),
                n(p.m_n, 2),
                n(p.b, 1),
                n(p.b2, 1),
                n(p.center_distance_mm, 2),
                n(p.total_contact_ratio, 3),
                n(p.root_safety_wheel, 2),
                n(p.weight_g, 0),
            ]
            for p in top
        ]
        variation_warnings = v.warnings
        pc_svg = _variation_pc_svg(v.points, v.request.root_minimum_safety)

    data = ReportData(
        label=req.label,
        locale=loc,
        version=__version__,
        speed_shaft1_min1=n1,
        speed_shaft2_min1=n2,
        torque_shaft1_nm=t1,
        torque_shaft2_nm=t2,
        load1_type=req.powerflow.load1_type,
        load2_type=req.powerflow.load2_type,
        power_kw=power_kw,
        operating_hours=req.powerflow.operating_hours,
        stage_rows=stage_rows,
        geometry_notes=geo.notes,
        tolerance_rows=tol_rows,
        accuracy_grade=req.accuracy_grade,
        factor_rows=factor_rows,
        dynamics_rows=dynamics_rows,
        gear_sections=gear_sections,
        same_method=cap.pinion.method == cap.wheel.method,
        mesh_svg=mesh_svg,
        mesh_script=mesh_script,
        loa_footer=loa_footer,
        variation_summary=variation_summary,
        variation_head=variation_head,
        variation_rows=variation_rows,
        variation_warnings=variation_warnings,
        variation_pc_svg=pc_svg,
    )
    html_text = build_report_html(data)
    filename = f"{req.label.replace(' ', '_')}_report.html"
    return HTMLResponse(
        content=html_text,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
