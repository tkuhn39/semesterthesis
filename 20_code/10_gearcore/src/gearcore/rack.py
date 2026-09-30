"""Basic rack profiles, tool reference profiles and the module series.

Sources (current notation throughout, project rule 3a):

* DIN 867:1986-02 — basic rack of cylindrical gears, Eq. (1)–(9).
* ISO 53:1998 — standard basic rack (Table 2), types A–D (Table A.1), Eq. (1)–(3).
* ISO 54:1996 — modules, Table 1.
* DIN 3972:1952-02 — reference profiles of gear cutting tools I–IV. The norm prints its own
  symbols (``h_kw``, ``r_1``, ``r_2``, ``p``, ``alpha_0``); they are mapped to the current symbols
  ``h_aP0``, ``rho_aP0``, ``q``, ``alpha_P0``, see ``data/quantities.yaml``. The tool tip rounding
  is tabulated in the norm (column "r_2 ≈ 0,2 m"), it is not computed from 0.2·m.

Tool tip rounding radius ``rho_aP0``: symbol of DIN ISO 21771:2014-08 Eq. (128) (normative
Anhang NB) and Eq. (130), of DIN 867:1986-02 (§2, §4.4, §4.5) and of ISO/TR 6336-30:2022. ISO
6336-3:2019 and VDI 2736 Blatt 2 write ``rho_a0``; Bild 35 of DIN ISO 21771 letters ``r_aP0``.
"""

import math
from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Literal

from gearcore._safe import EPS, finite_input, finite_result, positive_input, safe_div
from gearcore.errors import GeometryInfeasibleError, InputRangeError
from gearcore.models.common import InputWarning
from gearcore.models.inputs import ToolKind, ToolProfile
from gearcore.models.profiles import BasicRackProfile
from gearcore.trace import eq

EQ_EXEMPT = ("validate_basic_rack",)

TABLE_MATCH_RELATIVE = 1e-9
"""Relative tolerance for matching a module to a tabulated one (float noise such as 0.07 * 100)."""

DIN867_USUAL_CLEARANCE: tuple[float, float] = (0.1, 0.4)
"""DIN 867:1986-02 §4.4: the bottom clearance is "im allgemeinen" 0,1·m to 0,4·m."""

Iso53Type = Literal["A", "B", "C", "D"]
Din3972Profile = Literal["I", "II", "III", "IV"]

_ISO53_TYPES: Mapping[str, tuple[float, float, float]] = MappingProxyType(
    {
        # ISO 53 type -> (h_fP*, c_P*, rho_fP*) as printed in ISO 53:1998 Table A.1; alpha_P = 20°, h_aP* = 1
        "A": (1.25, 0.25, 0.38),
        "B": (1.25, 0.25, 0.3),
        "C": (1.25, 0.25, 0.25),
        "D": (1.4, 0.4, 0.39),
    }
)

NORM_PRINTED_FILLETS: Mapping[tuple[float, float], str] = MappingProxyType(
    {
        # (c_P*, rho_fP*) printed with two decimals although the pair exceeds the geometric bound
        (0.25, 0.38): "ISO 53:1998 Table A.1 type A, DIN 867:1986-02 §4.5 (bound 0.37995)",
        (0.3, 0.45): "DIN 867:1986-02 table p. 3 (bound 0.44592)",
    }
)

ISO54_SERIES_I: tuple[float, ...] = (
    1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0, 25.0, 32.0, 40.0, 50.0,
)  # fmt: skip
ISO54_SERIES_II: tuple[float, ...] = (
    1.125, 1.375, 1.75, 2.25, 2.75, 3.5, 4.5, 5.5, 6.5, 7.0, 9.0, 11.0, 14.0, 18.0, 22.0, 28.0, 36.0,
    45.0,
)  # fmt: skip
ISO54_AVOID: tuple[float, ...] = (6.5,)

DIN3972_TIP_ROUNDING_MM: Mapping[float, float] = MappingProxyType(
    {
        # module m : r_2 in mm (DIN 3972:1952-02, table p. 1, column "r_2 ≈ 0,2 m"); r_1 = r_2
        1.0: 0.08, 1.25: 0.12, 1.5: 0.20, 1.75: 0.25, 2.0: 0.30, 2.25: 0.40, 2.5: 0.50, 2.75: 0.50,
        3.0: 0.60, 3.25: 0.60, 3.5: 0.70, 3.75: 0.75, 4.0: 0.80, 4.5: 0.90, 5.0: 1.00, 5.5: 1.10,
        6.0: 1.20, 6.5: 1.30, 7.0: 1.40, 8.0: 1.60, 9.0: 1.80, 10.0: 2.00, 11.0: 2.20, 12.0: 2.40,
        13.0: 2.60, 14.0: 2.80, 15.0: 3.00, 16.0: 3.20,
    }
)  # fmt: skip
DIN3972_PROFILE_III_MAX_MODULE = 8.0
"""From module 9 the norm uses profile I, II or IV instead of III (table note)."""


def _angle(alpha_rad: float) -> float:
    alpha = finite_input(alpha_rad, "profile angle alpha_P")
    if not 0.0 < alpha < math.pi / 2.0 - EPS:
        raise InputRangeError(f"profile angle must lie in (0, 90 deg), got {math.degrees(alpha)!r}")
    return alpha


def _tabulated(module_mm: float, table: Iterable[float]) -> float | None:
    """The tabulated module equal to ``module_mm`` within ``TABLE_MATCH_RELATIVE``, else None."""
    for entry in table:
        if math.isclose(module_mm, entry, rel_tol=TABLE_MATCH_RELATIVE, abs_tol=0.0):
            return entry
    return None


@eq("DIN867:1986", "(2)", section="4.1", page=1)
@eq("ISO53:1998", "5.2", section="5.2", page=2)
def rack_pitch(module_mm: float) -> float:
    """Pitch of the basic rack: p = pi m."""
    return finite_result(math.pi * positive_input(module_mm, "module m"), "pitch p")


@eq("DIN867:1986", "(7)", section="4.5", page=2)
@eq("DIN867:1986", "(8)", section="4.5", page=2)
@eq("ISO53:1998", "(2)", section="5.9", page=4)
@eq(
    "ISO53:1998",
    "(3)",
    section="5.9",
    page=4,
    note="ISO 53 states (3) for 0,295 m < c_P <= 0,396 m; DIN 867 (8) has no upper limit",
)
def max_fillet_radius_factor(
    *, bottom_clearance_factor: float, dedendum_factor: float, profile_angle_rad: float
) -> float:
    """Largest fillet radius factor of a basic rack (per module).

    Two geometric bounds apply and the smaller governs:

    * the fillet must start at or below the common tooth depth:
      rho_fP <= c_P / (1 - sin alpha_P)                       [DIN 867 (7), ISO 53 (2)]
    * the fillets of both flanks must not overlap in the space:
      rho_fP <= (pi m / 4 - h_fP tan alpha_P) / tan((90° - alpha_P) / 2)   [ISO 53 (3)]
      which equals DIN 867 (8) for h_fP = m + c_P.
    """
    alpha = _angle(profile_angle_rad)
    clearance = finite_input(bottom_clearance_factor, "clearance factor c_P*")
    if clearance < 0.0:
        raise InputRangeError(
            f"clearance factor c_P* must be >= 0, got {bottom_clearance_factor!r}"
        )
    dedendum = positive_input(dedendum_factor, "dedendum factor h_fP*")
    by_clearance = safe_div(clearance, 1.0 - math.sin(alpha), what="c_P / (1 - sin alpha_P)")
    half_space = math.pi / 4.0 - finite_result(dedendum * math.tan(alpha), "h_fP tan alpha_P")
    if half_space <= 0.0:
        raise GeometryInfeasibleError(
            f"basic rack: flanks intersect above the root line (h_fP* = {dedendum!r}, "
            f"alpha_P = {math.degrees(alpha)!r} deg)"
        )
    by_space = half_space / math.tan((math.pi / 2.0 - alpha) / 2.0)
    return finite_result(min(by_clearance, by_space), "rho_fP* max")


@eq("DIN867:1986", "(9)", section="4.6", page=3)
def root_form_height_factor(
    *, dedendum_factor: float, fillet_radius_factor: float, profile_angle_rad: float
) -> float:
    """Straight part of the dedendum: h_FfP = h_fP - rho_fP (1 - sin alpha_P) (per module)."""
    alpha = _angle(profile_angle_rad)
    dedendum = positive_input(dedendum_factor, "dedendum factor h_fP*")
    fillet = finite_input(fillet_radius_factor, "fillet radius factor rho_fP*")
    if fillet < 0.0:
        raise InputRangeError(f"fillet radius factor rho_fP* must be >= 0, got {fillet!r}")
    height = finite_result(dedendum - fillet * (1.0 - math.sin(alpha)), "h_FfP*")
    if height <= 0.0:
        raise GeometryInfeasibleError(
            f"basic rack: the fillet (rho_fP* = {fillet!r}) reaches the datum line "
            f"(h_FfP* = {height!r} <= 0)"
        )
    return height


def _printed_by_a_norm(rack: BasicRackProfile) -> str | None:
    if rack.profile_angle_deg != 20.0 or rack.addendum_factor != 1.0:
        return None
    for (clearance, fillet), where in NORM_PRINTED_FILLETS.items():
        if math.isclose(
            rack.bottom_clearance_factor, clearance, rel_tol=TABLE_MATCH_RELATIVE
        ) and math.isclose(rack.fillet_radius_factor, fillet, rel_tol=TABLE_MATCH_RELATIVE):
            return where
    return None


def validate_basic_rack(rack: BasicRackProfile) -> BasicRackProfile:
    """Raise ``GeometryInfeasibleError`` if the fillet radius exceeds the geometric bound.

    The bound is applied without slack. The only exceptions are the value pairs the norms print
    with two decimals (``NORM_PRINTED_FILLETS``): they exceed the bound by rounding.
    """
    limit = max_fillet_radius_factor(
        bottom_clearance_factor=rack.bottom_clearance_factor,
        dedendum_factor=rack.dedendum_factor,
        profile_angle_rad=math.radians(rack.profile_angle_deg),
    )
    if rack.fillet_radius_factor > limit + EPS and _printed_by_a_norm(rack) is None:
        raise GeometryInfeasibleError(
            f"{rack.name}: fillet radius factor {rack.fillet_radius_factor!r} exceeds the maximum "
            f"{limit!r} (DIN 867 Eq. (7)/(8), ISO 53 Eq. (2)/(3))"
        )
    return rack


@eq("DIN867:1986", "4.4", section="4.4", page=2)
@eq("DIN867:1986", "(7)", section="4.5", page=2)
def check_basic_rack(rack: BasicRackProfile) -> tuple[InputWarning, ...]:
    """Soft findings on a valid basic rack (never an error)."""
    findings: list[InputWarning] = []
    low, high = DIN867_USUAL_CLEARANCE
    clearance = rack.bottom_clearance_factor
    inside = (
        low <= clearance <= high or math.isclose(clearance, low) or math.isclose(clearance, high)
    )
    if not inside:
        findings.append(
            InputWarning(
                code="clearance_outside_usual_range",
                field="bottom_clearance_factor",
                message=(
                    f"bottom clearance factor {clearance!r} lies outside the range 0,1 to 0,4 that "
                    "DIN 867:1986-02 §4.4 names as usual"
                ),
            )
        )
    printed = _printed_by_a_norm(rack)
    if printed is not None:
        findings.append(
            InputWarning(
                code="fillet_radius_rounded_by_norm",
                field="fillet_radius_factor",
                message=(
                    f"fillet radius factor {rack.fillet_radius_factor!r} is the rounded value "
                    f"printed in {printed}"
                ),
            )
        )
    return tuple(findings)


@eq("ISO53:1998", "Table 2", section="5.1", page=3)
@eq("ISO53:1998", "Table A.1", section="A.1", page=5)
def iso53_basic_rack(kind: Iso53Type = "A") -> BasicRackProfile:
    """Basic rack type A–D of ISO 53 (type A is the standard basic rack of Table 2)."""
    if not isinstance(kind, str) or kind not in _ISO53_TYPES:
        raise InputRangeError(f"ISO 53 basic rack type must be one of A, B, C, D, got {kind!r}")
    dedendum, clearance, fillet = _ISO53_TYPES[kind]
    return validate_basic_rack(
        BasicRackProfile(
            name=f"ISO 53 type {kind}",
            source="ISO53:1998",
            profile_angle_deg=20.0,
            addendum_factor=1.0,
            dedendum_factor=dedendum,
            bottom_clearance_factor=clearance,
            fillet_radius_factor=fillet,
        )
    )


@eq("DIN867:1986", "(4)", section="4.3", page=2)
@eq("DIN867:1986", "(5)", section="4.3", page=2)
def din867_basic_rack(
    *, bottom_clearance_factor: float, fillet_radius_factor: float
) -> BasicRackProfile:
    """Basic rack per DIN 867: alpha_P = 20°, h_aP = 1·m, h_fP = 1·m + c_P.

    DIN 867 §4.4 names c_P = 0,1·m to 0,4·m as the usual range, not as a limit; a clearance outside
    it is accepted here and reported by ``check_basic_rack``.
    """
    clearance = positive_input(bottom_clearance_factor, "clearance factor c_P*")
    fillet = finite_input(fillet_radius_factor, "fillet radius factor rho_fP*")
    if clearance > 1.0:
        raise InputRangeError(
            f"clearance factor c_P* must be <= 1, got {bottom_clearance_factor!r}"
        )
    if not 0.0 <= fillet <= 1.0:
        raise InputRangeError(
            f"fillet radius factor rho_fP* must lie in [0, 1], got {fillet_radius_factor!r}"
        )
    return validate_basic_rack(
        BasicRackProfile(
            name=f"DIN 867 (c_P* = {clearance!r}, rho_fP* = {fillet!r})",
            source="DIN867:1986",
            profile_angle_deg=20.0,
            addendum_factor=1.0,
            dedendum_factor=1.0 + clearance,
            bottom_clearance_factor=clearance,
            fillet_radius_factor=fillet,
        )
    )


@eq("ISO21771:2014", "Bild 35", section="7.1", page=63)
@eq("DIN867:1986", "Anmerkung", section="4.5", page=2)
def tool_from_basic_rack(rack: BasicRackProfile) -> ToolProfile:
    """Tool reference profile as the counterpart of the gear basic rack.

    The tool addendum cuts the gear dedendum (h_aP0 = h_fP) and the tool tip rounding forms the
    basic rack fillet (rho_aP0 = rho_fP, DIN 867 §4.5 note). The tool dedendum is not defined by
    the basic rack (non-topping tools leave the gear tip untouched) and stays ``None``.
    """
    validate_basic_rack(rack)
    return ToolProfile(
        kind=ToolKind.RACK,
        name=f"counterpart of {rack.name}",
        profile_angle_deg=rack.profile_angle_deg,
        addendum_factor=rack.dedendum_factor,
        tip_radius_factor=rack.fillet_radius_factor,
    )


def _din3972_profile(profile: Din3972Profile) -> Din3972Profile:
    if not isinstance(profile, str) or profile not in ("I", "II", "III", "IV"):
        raise InputRangeError(
            f"DIN 3972 reference profile must be I, II, III or IV, got {profile!r}"
        )
    return profile


@eq("DIN3972:1952", "Tabelle", page=1, note="h_kw I..IV (norm symbol) = tool addendum h_aP0")
def din3972_tool_addendum_mm(profile: Din3972Profile, module_mm: float) -> float:
    """Tool addendum of DIN 3972 reference profile I–IV (norm: Kopfhöhe des Werkzeugs h_kw).

    I: 1.167·m, II: 1.25·m, III: 1.25·m + 0.25·m^(1/3), IV: 1.25·m + 0.6·m^(1/3); III and IV are
    numerical-value equations with m in mm.
    """
    kind = _din3972_profile(profile)
    module = positive_input(module_mm, "module m")
    if kind == "I":
        return finite_result(1.167 * module, "h_aP0")
    if kind == "II":
        return finite_result(1.25 * module, "h_aP0")
    if kind == "III":
        if module > DIN3972_PROFILE_III_MAX_MODULE * (1.0 + TABLE_MATCH_RELATIVE):
            raise InputRangeError(
                "DIN 3972: reference profile III is defined up to module 8; from module 9 "
                "profile I, II or IV is used"
            )
        return finite_result(1.25 * module + 0.25 * math.cbrt(module), "h_aP0")
    return finite_result(1.25 * module + 0.6 * math.cbrt(module), "h_aP0")


@eq(
    "DIN3972:1952",
    "Erläuterungen",
    page=2,
    note="p (norm symbol) = machining allowance per flank q",
)
def din3972_machining_allowance_mm(
    profile: Din3972Profile, module_mm: float, profile_angle_rad: float = math.radians(20.0)
) -> float:
    """Machining allowance per flank left by profile III/IV, normal to the flank.

    p = (h_kw − h_fr)·sin(alpha_0); the norm prints it for III (h_fr = 1.25·m):
    0.25·m^(1/3)·sin(alpha_0), and for IV: 0.6·m^(1/3)·sin(alpha_0). Profiles I and II are finishing
    profiles (h_kw = h_fr, p = 0).
    """
    alpha = _angle(profile_angle_rad)
    addendum = din3972_tool_addendum_mm(profile, module_mm)
    if profile in ("I", "II"):
        return 0.0
    return (addendum - 1.25 * float(module_mm)) * math.sin(alpha)


@eq("DIN3972:1952", "Tabelle", page=1, note="r_1 = r_2 (norm symbols) = tool tip rounding rho_aP0")
def din3972_tool(profile: Din3972Profile, module_mm: float) -> ToolProfile:
    """Tool reference profile I–IV of DIN 3972 for a tabulated module (1 … 16 mm)."""
    module = positive_input(module_mm, "module m")
    tabulated = _tabulated(module, DIN3972_TIP_ROUNDING_MM)
    if tabulated is None:
        raise InputRangeError(
            f"DIN 3972 tabulates modules {sorted(DIN3972_TIP_ROUNDING_MM)}; module {module!r} "
            "has no tabulated tip rounding, define the tool explicitly"
        )
    addendum = din3972_tool_addendum_mm(profile, tabulated)
    return ToolProfile(
        kind=ToolKind.RACK,
        name=f"DIN 3972 Bezugsprofil {profile} x {tabulated!r}",
        normal_module_mm=tabulated,
        profile_angle_deg=20.0,
        addendum_factor=addendum / tabulated,
        tip_radius_factor=DIN3972_TIP_ROUNDING_MM[tabulated] / tabulated,
        machining_allowance_mm=din3972_machining_allowance_mm(profile, tabulated),
    )


@eq("ISO54:1996", "Table 1", section="3", page=2)
def module_series(module_mm: float) -> Literal["I", "II"] | None:
    """Series of ISO 54 Table 1 the module belongs to, or ``None`` if it is not standardised."""
    module = positive_input(module_mm, "module m")
    if _tabulated(module, ISO54_SERIES_I) is not None:
        return "I"
    if _tabulated(module, ISO54_SERIES_II) is not None:
        return "II"
    return None


@eq("ISO54:1996", "Table 1", section="3", page=2)
@eq("ISO54:1996", "3", section="3", page=1, note="preference for series I; module 6,5 avoided")
def check_module(module_mm: float) -> InputWarning | None:
    """Soft finding for modules outside ISO 54 series I (never an error)."""
    module = positive_input(module_mm, "module m")
    series = module_series(module)
    if series == "I":
        return None
    if series == "II":
        avoided = _tabulated(module, ISO54_AVOID) is not None
        hint = "; ISO 54 §3: module 6,5 should be avoided" if avoided else ""
        return InputWarning(
            code="module_series_ii",
            field="normal_module_mm",
            message=f"module {module!r} belongs to ISO 54 series II (series I is preferred){hint}",
        )
    return InputWarning(
        code="module_not_in_iso54",
        field="normal_module_mm",
        message=(
            f"module {module!r} is not listed in ISO 54:1996 Table 1 "
            "(the norm covers modules 1 … 50 for general and heavy engineering)"
        ),
    )
