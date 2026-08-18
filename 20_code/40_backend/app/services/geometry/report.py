"""
@module: app.services.geometry.report
@context: Domain layer — the ONE full geometry report (backend SSOT for the frontend).
@role: Compute EVERY macro-geometry, tooth-thickness, inspection and backlash quantity of
       the stage in one place, on CURRENT norms only (ADR-011): DIN ISO 21771:2014 (incl.
       the national Annex NB corrections), DIN 21773:2014 (inspection dimensions §5–§14),
       DIN 3967:1978 (tooth-thickness allowances, still valid) and DIN 3964:1980 (centre
       distance allowances, still valid). The legacy STplus output (kst-E .sta Blatt 6–8,
       DIN 3960:1987 — withdrawn) is the numeric cross-check in the tests, never the basis.

       Fillet-aware: the selected root-fillet strategy shifts the EFFECTIVE root values
       (deepest contour radius; Frühe's root diameter is a RESULT of its fit) — reported
       next to the nominal tool values so tabs/report can mark norm- vs contour-based.

Spur-plane scope: the inspection block (§5–§14) is implemented for spur gears (β = 0, the
project scope); helical extensions carry β_b terms per the cited clauses when needed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.io.ste import Pair
from app.services.geometry.gear import GearStage, line_of_action_points
from app.services.geometry.generation import involute
from app.services.geometry.tooth_form import ToothProfile

__all__ = ["GearReport", "PairReport", "GeometryReport", "compute_geometry_report"]


def _inv_inverse(inv_value: float) -> float:
    """Angle α (rad) with inv(α) = tan α − α = inv_value (Newton, e.g. DIN 21773 Eq. 30)."""
    alpha = 0.5
    for _ in range(60):
        f = math.tan(alpha) - alpha - inv_value
        df = math.tan(alpha) ** 2
        step = f / max(df, 1e-12)
        alpha -= step
        if abs(step) < 1e-14:
            break
    return alpha


@dataclass(frozen=True)
class GearReport:
    """Per-gear values (all lengths mm, angles deg; *None* = not computable from inputs)."""

    teeth: int
    profile_shift: float
    generation_profile_shift: float  # x_E (ISO 21771 §7.4, from the allowance chain)
    reference_diameter_mm: float
    base_diameter_mm: float
    tip_diameter_mm: float
    tip_form_diameter_mm: float
    tip_chamfer_radial_mm: float  # h_K
    usable_tip_diameter_mm: float  # d_Na
    usable_root_diameter_mm: float | None  # d_Nf (ISO 21771 §5.4.1, needs the mating gear)
    root_form_diameter_mm: float  # d_Ff (ISO 21771 §7.6, NB-corrected closed form)
    root_diameter_mm: float  # d_f (tool value)
    effective_root_diameter_mm: float | None  # min contour radius ·2 with the chosen fillet
    form_reserve_mm: float | None  # c_n = (d_Nf − d_Ff)/2
    working_pitch_diameter_mm: float
    tooth_height_mm: float  # h = (d_a − d_f)/2
    addendum_mm: float  # h_a = (d_a − d)/2
    addendum_factor_actual: float  # h_aP* (Istwert) = h_a/m_n − x
    tip_clearance_mm: float | None  # c (Istwert, vs the MATING root circle)
    tip_path_of_contact_mm: float | None  # g_a (Kopfeingriffsstrecke, own tip → C)
    tooth_thickness_transverse_mm: float  # s_t (nominal, x-based)
    tooth_thickness_normal_mm: float  # s_n
    space_width_normal_mm: float  # e_n = p_n − s_n
    tip_tooth_thickness_mm: float | None  # s_a at d_Na (as cut, x_E-based)
    rest_tip_thickness_mm: float | None  # after the edge break (generation)
    chordal_thickness_mm: float  # s̄_cn at d_y = d_a − 2 m_n (DIN 21773 §5)
    chordal_height_mm: float  # h̄_c over the chord to d_a (DIN 21773 Eq. 5)
    span_teeth: int | None  # measuring tooth count k (auto per DIN 21773 §7.2)
    span_teeth_min: int | None
    span_teeth_max: int | None
    span_measurement_mm: float | None  # W_k nominal (DIN 21773 Eq. 14)
    span_contact_diameter_mm: float | None  # d_M (DIN 21773 Eq. 17)
    ball_diameter_mm: float | None  # D_M used
    two_ball_measure_mm: float | None  # M_dK (DIN 21773 Eq. 35/36)
    two_roller_measure_mm: float | None  # M_dR (Eq. 37; spur: = M_dK)
    ball_contact_diameter_mm: float | None  # d_M of ball contact (Eq. 33/34)
    thickness_allowance_upper_mm: float | None  # E_sns (from A_We / DIN 3967)
    thickness_allowance_lower_mm: float | None  # E_sni
    span_allowance_upper_mm: float | None  # E_Ws = E_sn·cos α_n (DIN 21773 Eq. 54)
    span_allowance_lower_mm: float | None
    ball_allowance_factor: float | None  # E*_MdK (DIN 21773 §14.6)
    ball_allowance_upper_mm: float | None
    ball_allowance_lower_mm: float | None
    sliding_factor_tip: float | None  # K_ga (ISO 21771 Eq. 113)
    specific_sliding_tip: float | None  # ζ_a (ISO 21771 §5.6.3, at own tip)
    specific_sliding_root: float | None  # ζ_f (at own root = mating tip point)
    undercut_min_shift: float | None  # x_E,min (ISO 21771 §7.7)
    has_undercut: bool | None
    # tool reference profile (as used for generation)
    tool_module_mm: float
    tool_pressure_angle_deg: float
    tool_addendum_factor: float
    tool_tip_radius_factor: float
    tool_dedendum_factor: float | None


@dataclass(frozen=True)
class PairReport:
    """Pair-level values."""

    normal_module_mm: float
    transverse_module_mm: float
    normal_pressure_angle_deg: float
    transverse_pressure_angle_deg: float
    working_pressure_angle_deg: float
    helix_angle_deg: float
    base_helix_angle_deg: float
    gear_ratio: float  # z2/z1
    center_distance_mm: float
    reference_center_distance_mm: float
    profile_shift_sum: float
    transverse_pitch_mm: float  # p_t
    normal_pitch_mm: float  # p_n
    transverse_base_pitch_mm: float  # p_et
    normal_base_pitch_mm: float  # p_en
    path_of_contact_mm: float  # g_α
    transverse_contact_ratio: float
    overlap_ratio: float
    total_contact_ratio: float
    common_face_width_mm: float | None
    common_tooth_height_mm: float | None  # h_w (gemeinsame Zahnhöhe)
    common_height_factor: float | None  # h_* = h_w/m_n
    backlash_circumferential_mm: float | None  # j_t at the working circle (ISO 21771 §5.5.2)
    backlash_normal_mm: float | None  # j_bn (Eingriffsflankenspiel)
    backlash_delta_upper_mm: tuple[float, float] | None  # (Δj_t, Δj_n) for +A_a
    backlash_delta_lower_mm: tuple[float, float] | None  # (Δj_t, Δj_n) for −A_a
    center_distance_allowance_mm: float | None  # A_a (DIN 3964, symmetric js field)


@dataclass(frozen=True)
class GeometryReport:
    gear1: GearReport
    gear2: GearReport
    pair: PairReport
    notes: list[str]


def _auto_span_teeth(
    z: int,
    x: float,
    mn: float,
    alpha_n: float,
    alpha_t: float,
    d_b: float,
    d_ff: float,
    d_fa: float,
) -> tuple[int | None, int | None, int | None]:
    """k_min/k_max per DIN 21773 Eqs. (12)/(13) + auto k with contact nearest the V-circle."""
    p_bn = math.pi * mn * math.cos(alpha_n)
    s_bn = mn * math.cos(alpha_n) * (math.pi / 2.0 + z * involute(alpha_t)) + 2.0 * x * mn * (
        math.sin(alpha_n)
    )
    if d_ff <= d_b or d_fa <= d_b:
        return None, None, None
    k_min = math.floor((math.sqrt(d_ff**2 - d_b**2) - s_bn) / p_bn + 1.5)
    k_max = math.floor((math.sqrt(d_fa**2 - d_b**2) - s_bn) / p_bn + 0.5)
    if k_max < k_min:
        return None, k_min, k_max
    # auto k per the classic rule (DIN 21773 Eq. 9/11 approximation): contact near the
    # V-circle, k = INT(z·α_v/π + 0.5) with α_v the profile angle at d_v = d + 2x·m_n
    d_v = z * mn + 2.0 * x * mn  # V-circle (spur)
    alpha_v = math.acos(min(1.0, d_b / d_v))
    k = int(z * alpha_v / math.pi + 0.5)
    return min(max(k, k_min, 1), k_max), k_min, k_max


def _ball_measure(
    z: int, x: float, mn: float, alpha_n: float, alpha_t: float, d_b: float, d_m_ball: float
) -> tuple[float, float]:
    """(M_dK, ball contact diameter) per DIN 21773 §8/§10 (spur external).

    inv α_Kt = D_M/d_b − π/(2z) + 2x·tan α_n/z + inv α_t (Eq. 30 with the gap half-angle
    of the x-shifted tooth; verified against kst-E M_dK 53.846/55.064).
    """
    inv_akt = (
        d_m_ball / d_b - math.pi / (2.0 * z) + 2.0 * x * math.tan(alpha_n) / z + involute(alpha_t)
    )
    alpha_kt = _inv_inverse(inv_akt)
    d_k = d_b / math.cos(alpha_kt)  # Eq. (31)
    # even z: Eq. (35); odd z: the two gaps are half a pitch out of line, Eq. (36)
    m_dk = d_k + d_m_ball if z % 2 == 0 else d_k * math.cos(math.pi / (2.0 * z)) + d_m_ball
    tan_amt = math.tan(alpha_kt) - d_m_ball / d_b  # Eq. (34), β_b = 0
    d_contact = d_b / math.cos(math.atan(tan_amt))  # Eq. (33)
    return m_dk, d_contact


def compute_geometry_report(
    stage: GearStage,
    *,
    ball_diameter_mm: Pair[float] | None = None,
    span_allowance_upper_mm: Pair[float] | None = None,
    span_allowance_lower_mm: Pair[float] | None = None,
    center_distance_allowance_mm: float | None = None,
    fillet_contour_min_radius_mm: Pair[float] | None = None,
) -> GeometryReport:
    """The SSOT geometry report for one stage.

    ``ball_diameter_mm``: measuring ball/roller D_M per gear (default 1.75·m_n).
    ``span_allowance_upper/lower_mm``: A_We/A_Wi per gear (kst-E input route; DIN 3967
    series values convert the same way, E_sn = A_W/cos α_n per DIN 21773 §14.4).
    ``center_distance_allowance_mm``: symmetric A_a (DIN 3964 js field, e.g. 0.015).
    ``fillet_contour_min_radius_mm``: deepest contour radius per gear with the selected
    root-fillet strategy (from the contour pipeline) — reported as the effective root.
    """
    # Guard (audit NRM-01): several report blocks (spans, chordal thicknesses, ball
    # measurements, contact circles) are implemented for spur gears only — a helical
    # stage would get plausible-looking WRONG numbers, so refuse instead.
    if abs(stage.helix_angle_deg) > 1e-9:
        raise ValueError(
            "geometry report supports spur gears only for now "
            f"(helix angle β = {stage.helix_angle_deg:g}°)"
        )
    notes = stage.check_validity()
    mn = stage.normal_module_mm
    alpha_n = math.radians(stage.normal_pressure_angle_deg)
    alpha_t = math.radians(stage.transverse_pressure_angle_deg)
    alpha_wt = math.radians(stage.working_pressure_angle_deg)
    a_w = stage.working_center_distance_mm
    if stage.generation is None or stage.usable_tip_diameter_mm is None:
        raise ValueError("geometry report needs the generation data (tool profiles + tips)")
    profiles = (ToothProfile.from_stage(stage, 0), ToothProfile.from_stage(stage, 1))
    loa = line_of_action_points(stage)
    if loa is None:
        raise ValueError("geometry report needs the line of action (usable tip diameters)")
    balls = ball_diameter_mm or Pair(1.75 * mn, 1.75 * mn)

    # line-of-action geometry: curvature radii ρ = distance from T_i along the pressure line
    def _dist(p: tuple[float, float], q: tuple[float, float]) -> float:
        return math.hypot(p[0] - q[0], p[1] - q[1])

    u = stage.teeth[1] / stage.teeth[0]
    # A = start (near gear-1 root / gear-2 tip), E = end (gear-1 tip / gear-2 root)
    rho_a1, rho_a2 = _dist(loa.t1, loa.a), _dist(loa.t2, loa.a)
    rho_e1, rho_e2 = _dist(loa.t1, loa.e), _dist(loa.t2, loa.e)
    g_f1 = _dist(loa.a, loa.c)  # gear-1 root side of C = gear-2 tip side
    g_a1 = _dist(loa.c, loa.e)  # gear-1 tip side
    d_w = stage.working_pitch_diameter_mm

    gears: list[GearReport] = []
    for i in (0, 1):
        gen = stage.generation[i]
        prof = profiles[i]
        z = stage.teeth[i]
        x = stage.profile_shift[i]
        d = stage.reference_diameter_mm[i]
        d_b = stage.base_diameter_mm[i]
        d_a = gen.tip_diameter_mm
        d_na = stage.usable_tip_diameter_mm[i]
        d_f = prof.root_diameter_mm
        # d_Nf from the mating contact point (ISO 21771 §5.4.1): the LOWEST contact on
        # gear i is at A (i=0) / E (i=1)
        rho_low = rho_a1 if i == 0 else rho_e2
        d_nf = 2.0 * math.hypot(d_b / 2.0, rho_low)
        c_n = (d_nf - prof.d_Ff) / 2.0
        # nominal tooth thickness (x-based)
        s_t = mn * (math.pi / 2.0 + 2.0 * x * math.tan(alpha_n))  # spur: m_t = m_n
        s_n = s_t
        e_n = math.pi * mn - s_n
        # chordal at d_y = d_a − 2 m_n (DIN 21773 §5, spur: ψ_y = s_yn/d_y)
        d_y = d_a - 2.0 * mn
        alpha_y = math.acos(min(1.0, d_b / d_y))
        s_y = d_y * (s_t / d + involute(alpha_t) - involute(alpha_y))
        psi_y = s_y / d_y
        s_c = d_y * math.sin(psi_y)  # Eq. (3) spur
        h_c = (d_a - d_y * math.cos(psi_y)) / 2.0  # Eq. (5) spur
        # tip thickness (as cut, x_E) at d_Na
        theta_na = prof.half_thickness_angle(d_na / 2.0)
        s_a = d_na * theta_na
        # allowances: A_W (span) is the primary input (kst-E); E_sn = A_W / cos α_n (§14.4)
        allow_up = span_allowance_upper_mm[i] if span_allowance_upper_mm is not None else None
        allow_low = span_allowance_lower_mm[i] if span_allowance_lower_mm is not None else None
        e_sns = allow_up / math.cos(alpha_n) if allow_up is not None else None
        e_sni = allow_low / math.cos(alpha_n) if allow_low is not None else None
        allow_mean = (
            0.5 * (allow_up + allow_low) if allow_up is not None and allow_low is not None else 0.0
        )
        # span
        k, k_min, k_max = _auto_span_teeth(z, x, mn, alpha_n, alpha_t, d_b, prof.d_Ff, d_na)
        w_k = None
        d_m_span = None
        if k is not None:
            w_k = mn * math.cos(alpha_n) * (math.pi * (k - 0.5) + z * involute(alpha_t)) + (
                2.0 * x * mn * math.sin(alpha_n)
            )
            # contact circle of the ACTUAL measurement (mean allowance), like the reference
            d_m_span = math.sqrt(d_b**2 + (w_k + allow_mean) ** 2)
        # balls / rollers (spur: M_dR = M_dK); allowances as EXACT measure differences at
        # the allowance-equivalent shift x + E_sn/(2 m_n tan α_n) — DIN 21773 §14.1 route
        m_dk, _ = _ball_measure(z, x, mn, alpha_n, alpha_t, d_b, balls[i])

        def _x_of(e_sn: float, x_nom: float = x) -> float:
            return x_nom + e_sn / (2.0 * mn * math.tan(alpha_n))

        ball_up = ball_low = e_factor_ball = None
        if e_sns is not None and e_sni is not None:
            m_up, _ = _ball_measure(z, _x_of(e_sns), mn, alpha_n, alpha_t, d_b, balls[i])
            m_low, _ = _ball_measure(z, _x_of(e_sni), mn, alpha_n, alpha_t, d_b, balls[i])
            ball_up, ball_low = m_up - m_dk, m_low - m_dk
            if abs(e_sns) > 1e-12:
                e_factor_ball = abs(ball_up / e_sns)
        # contact circle at the mean allowance (matches the reference output)
        e_mean = allow_mean / math.cos(alpha_n)
        _, d_contact_ball = _ball_measure(z, _x_of(e_mean), mn, alpha_n, alpha_t, d_b, balls[i])
        # sliding (ISO 21771 §5.6): own tip = E for gear 1 / A for gear 2; the pitch-line
        # velocity v_t = ω1·d_w1/2 is common, so K_g normalizes on d_w1 for BOTH gears
        if i == 0:
            g_own_tip = g_a1
            zeta_a = 1.0 - rho_e2 / (u * rho_e1)  # Eq. (114) at E
            zeta_f = 1.0 - rho_a2 / (u * rho_a1)  # Eq. (114) at A (negative)
        else:
            g_own_tip = g_f1
            zeta_a = 1.0 - u * rho_a1 / rho_a2  # Eq. (115) at A
            zeta_f = 1.0 - u * rho_e1 / rho_e2  # Eq. (115) at E (negative)
        k_ga = 2.0 * g_own_tip / d_w[0] * (1.0 + 1.0 / u)  # Eq. (112)/(113)
        mate_prof = profiles[1 - i]
        tip_clearance = a_w - d_a / 2.0 - mate_prof.root_diameter_mm / 2.0
        gears.append(
            GearReport(
                teeth=z,
                profile_shift=x,
                generation_profile_shift=gen.generation_profile_shift,
                reference_diameter_mm=d,
                base_diameter_mm=d_b,
                tip_diameter_mm=d_a,
                tip_form_diameter_mm=gen.tip_form_diameter_mm,
                tip_chamfer_radial_mm=gen.tip_chamfer_radial_mm,
                usable_tip_diameter_mm=d_na,
                usable_root_diameter_mm=d_nf,
                root_form_diameter_mm=prof.d_Ff,
                root_diameter_mm=d_f,
                effective_root_diameter_mm=(
                    2.0 * fillet_contour_min_radius_mm[i]
                    if fillet_contour_min_radius_mm is not None
                    else None
                ),
                form_reserve_mm=c_n,
                working_pitch_diameter_mm=d_w[i],
                tooth_height_mm=(d_a - d_f) / 2.0,
                addendum_mm=(d_a - d) / 2.0,
                addendum_factor_actual=(d_a - d) / (2.0 * mn) - x,
                tip_clearance_mm=tip_clearance,
                tip_path_of_contact_mm=g_own_tip,
                tooth_thickness_transverse_mm=s_t,
                tooth_thickness_normal_mm=s_n,
                space_width_normal_mm=e_n,
                tip_tooth_thickness_mm=s_a,
                rest_tip_thickness_mm=gen.rest_tip_thickness_mm,
                chordal_thickness_mm=s_c,
                chordal_height_mm=h_c,
                span_teeth=k,
                span_teeth_min=k_min,
                span_teeth_max=k_max,
                span_measurement_mm=w_k,
                span_contact_diameter_mm=d_m_span,
                ball_diameter_mm=balls[i],
                two_ball_measure_mm=m_dk,
                two_roller_measure_mm=m_dk,  # spur (DIN 21773 §11)
                ball_contact_diameter_mm=d_contact_ball,
                thickness_allowance_upper_mm=e_sns,
                thickness_allowance_lower_mm=e_sni,
                span_allowance_upper_mm=allow_up,
                span_allowance_lower_mm=allow_low,
                ball_allowance_factor=e_factor_ball,
                ball_allowance_upper_mm=ball_up,
                ball_allowance_lower_mm=ball_low,
                sliding_factor_tip=k_ga,
                specific_sliding_tip=zeta_a,
                specific_sliding_root=zeta_f,
                undercut_min_shift=prof.undercut_min_generation_shift,
                has_undercut=prof.has_undercut,
                tool_module_mm=mn,
                tool_pressure_angle_deg=stage.normal_pressure_angle_deg,
                tool_addendum_factor=gen.tool.addendum_factor,
                tool_tip_radius_factor=gen.tool.tip_radius_factor,
                tool_dedendum_factor=getattr(gen.tool, "dedendum_factor", None),
            )
        )

    # pair values
    face = stage.face_width_mm
    b_gem = min(face[0], face[1]) if face is not None else None
    # common tooth height (working depth) from the USABLE tips: h_w = (d_Na1 + d_Na2)/2 − a_w
    h_w = (stage.usable_tip_diameter_mm[0] + stage.usable_tip_diameter_mm[1]) / 2.0 - a_w
    # backlash from the tooth-thickness allowances of BOTH gears (ISO 21771 §5.5, verified
    # against kst-E: j_bn = −(E_sn1 + E_sn2)·cos α_n, j_t = j_bn/cos α_wt at the working circle)
    e1u = gears[0].thickness_allowance_upper_mm
    e2u = gears[1].thickness_allowance_upper_mm
    j_bn = None
    j_t = None
    if e1u is not None and e2u is not None:
        j_bn = -(e1u + e2u) * math.cos(alpha_n)
        j_t = j_bn / math.cos(alpha_wt)
    delta_up = delta_low = None
    if center_distance_allowance_mm is not None:
        d_jt = 2.0 * center_distance_allowance_mm * math.tan(alpha_wt)
        delta_up = (d_jt, d_jt * math.cos(alpha_wt))
        delta_low = (-d_jt, -d_jt * math.cos(alpha_wt))
    pair = PairReport(
        normal_module_mm=mn,
        transverse_module_mm=stage.transverse_module_mm,
        normal_pressure_angle_deg=stage.normal_pressure_angle_deg,
        transverse_pressure_angle_deg=stage.transverse_pressure_angle_deg,
        working_pressure_angle_deg=stage.working_pressure_angle_deg,
        helix_angle_deg=stage.helix_angle_deg,
        base_helix_angle_deg=0.0
        if abs(stage.helix_angle_deg) < 1e-12
        else math.degrees(
            math.atan(math.tan(math.radians(stage.helix_angle_deg)) * math.cos(alpha_t))
        ),
        gear_ratio=u,
        center_distance_mm=a_w,
        reference_center_distance_mm=stage.reference_center_distance_mm,
        profile_shift_sum=stage.profile_shift[0] + stage.profile_shift[1],
        transverse_pitch_mm=math.pi * stage.transverse_module_mm,
        normal_pitch_mm=math.pi * mn,
        transverse_base_pitch_mm=stage.transverse_base_pitch_mm,
        normal_base_pitch_mm=math.pi * mn * math.cos(alpha_n),
        path_of_contact_mm=stage.path_of_contact_mm,
        transverse_contact_ratio=stage.transverse_contact_ratio,
        overlap_ratio=stage.overlap_ratio,
        total_contact_ratio=stage.total_contact_ratio,
        common_face_width_mm=b_gem,
        common_tooth_height_mm=h_w,
        common_height_factor=h_w / mn,
        backlash_circumferential_mm=j_t,
        backlash_normal_mm=j_bn,
        backlash_delta_upper_mm=delta_up,
        backlash_delta_lower_mm=delta_low,
        center_distance_allowance_mm=center_distance_allowance_mm,
    )
    return GeometryReport(gear1=gears[0], gear2=gears[1], pair=pair, notes=notes)
