"""Flank tolerances of DIN ISO 1328-1:2018-03 (ISO 1328-1:2013) for one accuracy class: the
equations (5) to (12) of 5.3, the step factor 2^((A − 5)/2) of 5.2.2, the rounding rules of 5.2.3
and the informative runout tolerance of Anhang E.4 (Gl. (E.1)) and adjacent pitch difference
tolerance of Anhang G.2 (Gl. (G.2)).

Used to place the measured gears against the quality the drawing demands (Q10 after DIN ISO
1328-1 for the plastic wheel), because the measuring program (Klingelnberg GINA) checks against
the tables of the withdrawn DIN 3962 Teil 1 and Teil 2 (grade 7 wheels, grade 6 pinions; the
values of its headers are those of DIN 3962, checked 2026-10-25 on the norm) and the two systems
are stepped differently. The norm's validity ranges (5 ≤ z ≤ 1000, 5 mm ≤ d ≤ 15 000 mm,
0,5 mm ≤ m_n ≤ 70 mm, 4 mm ≤ b ≤ 1200 mm, classes 1 to 11; 5.2.1 and Abschnitt 1) are enforced,
the class 12 of ISO 1328-1 is not part of the equations.
"""

import math
from dataclasses import dataclass

from gearcore.errors import InputRangeError
from gearcore.trace import eq

SOURCE = "DINISO1328-1:2018"

CLASSES = range(1, 12)
"""Flank tolerance classes the equations hold for (Abschnitt 1 and 5.2.1, p. 35)."""


@eq(SOURCE, "5.2.2", section="5.2.2 Stufungsfaktor", page=36, note="2^((A − 5)/2) on class 5")
def step_factor(accuracy_class: int) -> float:
    """Factor of the class ``A`` against class 5: √2 per class (5.2.2)."""
    if accuracy_class not in CLASSES:
        raise InputRangeError(f"flank tolerance class {accuracy_class} is not 1 to 11 (5.2.1)")
    return math.pow(2.0, 0.5 * (accuracy_class - 5))


@eq(
    SOURCE,
    "5.2.3",
    section="5.2.3 Rundungsregeln",
    page=36,
    note="> 10 µm whole µm, 5 to 10 µm to 0,5 µm, < 5 µm to 0,1 µm",
)
def rounded(value_um: float) -> float:
    """A tolerance rounded as 5.2.3 prescribes (half away from zero, the values are positive)."""
    if value_um > 10.0:
        return float(math.floor(value_um + 0.5))
    if value_um >= 5.0:
        return math.floor(value_um * 2.0 + 0.5) / 2.0
    return math.floor(value_um * 10.0 + 0.5) / 10.0


def _check_ranges(d_mm: float, m_n_mm: float, b_mm: float | None) -> None:
    if not 5.0 <= d_mm <= 15000.0:
        raise InputRangeError(f"reference diameter {d_mm} mm outside 5 to 15 000 mm (Abschnitt 1)")
    if not 0.5 <= m_n_mm <= 70.0:
        raise InputRangeError(f"normal module {m_n_mm} mm outside 0,5 to 70 mm (Abschnitt 1)")
    if b_mm is not None and not 4.0 <= b_mm <= 1200.0:
        raise InputRangeError(f"face width {b_mm} mm outside 4 to 1200 mm (Abschnitt 1)")


@eq(SOURCE, "(5)", section="5.3.1", page=36)
def single_pitch_tolerance(d_mm: float, m_n_mm: float, accuracy_class: int) -> float:
    """f_pT = (0,001 d + 0,4 m_n + 5) · 2^((A − 5)/2), unrounded, in µm."""
    _check_ranges(d_mm, m_n_mm, None)
    return (0.001 * d_mm + 0.4 * m_n_mm + 5.0) * step_factor(accuracy_class)


@eq(SOURCE, "(6)", section="5.3.2", page=36)
def total_cumulative_pitch_tolerance(d_mm: float, m_n_mm: float, accuracy_class: int) -> float:
    """F_pT = (0,002 d + 0,55 √d + 0,7 m_n + 12) · 2^((A − 5)/2), unrounded, in µm."""
    _check_ranges(d_mm, m_n_mm, None)
    return (0.002 * d_mm + 0.55 * math.sqrt(d_mm) + 0.7 * m_n_mm + 12.0) * step_factor(
        accuracy_class
    )


@eq(SOURCE, "(7)", section="5.3.3.1", page=37, note="applied as ± value")
def profile_slope_tolerance(d_mm: float, m_n_mm: float, accuracy_class: int) -> float:
    """f_HαT = (0,4 √m_n + 0,001 d + 4) · 2^((A − 5)/2), unrounded, in µm."""
    _check_ranges(d_mm, m_n_mm, None)
    return (0.4 * math.sqrt(m_n_mm) + 0.001 * d_mm + 4.0) * step_factor(accuracy_class)


@eq(SOURCE, "(8)", section="5.3.3.2", page=37)
def profile_form_tolerance(d_mm: float, m_n_mm: float, accuracy_class: int) -> float:
    """f_fαT = (0,55 √m_n + 5) · 2^((A − 5)/2), unrounded, in µm."""
    _check_ranges(d_mm, m_n_mm, None)
    return (0.55 * math.sqrt(m_n_mm) + 5.0) * step_factor(accuracy_class)


@eq(SOURCE, "(9)", section="5.3.3.3", page=37, note="from the unrounded slope and form tolerances")
def total_profile_tolerance(d_mm: float, m_n_mm: float, accuracy_class: int) -> float:
    """F_αT = √(f_HαT² + f_fαT²), unrounded, in µm."""
    return math.hypot(
        profile_slope_tolerance(d_mm, m_n_mm, accuracy_class),
        profile_form_tolerance(d_mm, m_n_mm, accuracy_class),
    )


@eq(SOURCE, "(10)", section="5.3.4.1", page=37, note="applied as ± value")
def helix_slope_tolerance(d_mm: float, b_mm: float, accuracy_class: int) -> float:
    """f_HβT = (0,05 √d + 0,35 √b + 4) · 2^((A − 5)/2), unrounded, in µm."""
    _check_ranges(d_mm, 1.0, b_mm)
    return (0.05 * math.sqrt(d_mm) + 0.35 * math.sqrt(b_mm) + 4.0) * step_factor(accuracy_class)


@eq(SOURCE, "(11)", section="5.3.4.2", page=37)
def helix_form_tolerance(d_mm: float, b_mm: float, accuracy_class: int) -> float:
    """f_fβT = (0,07 √d + 0,45 √b + 4) · 2^((A − 5)/2), unrounded, in µm."""
    _check_ranges(d_mm, 1.0, b_mm)
    return (0.07 * math.sqrt(d_mm) + 0.45 * math.sqrt(b_mm) + 4.0) * step_factor(accuracy_class)


@eq(SOURCE, "(12)", section="5.3.4.3", page=37, note="from the unrounded slope and form tolerances")
def total_helix_tolerance(d_mm: float, b_mm: float, accuracy_class: int) -> float:
    """F_βT = √(f_HβT² + f_fβT²), unrounded, in µm."""
    return math.hypot(
        helix_slope_tolerance(d_mm, b_mm, accuracy_class),
        helix_form_tolerance(d_mm, b_mm, accuracy_class),
    )


@eq(SOURCE, "(E.1)", section="Anhang E.4 (informativ)", page=53, note="F_rT = 0,9 F_pT")
def runout_tolerance(d_mm: float, m_n_mm: float, accuracy_class: int) -> float:
    """F_rT = 0,9 · F_pT (Anhang E, informative), unrounded, in µm."""
    return 0.9 * total_cumulative_pitch_tolerance(d_mm, m_n_mm, accuracy_class)


@eq(SOURCE, "(G.2)", section="Anhang G.2 (informativ)", page=60, note="f_uT = √2 f_pT")
def adjacent_pitch_difference_tolerance(d_mm: float, m_n_mm: float, accuracy_class: int) -> float:
    """f_uT = √2 · f_pT (Anhang G, informative), unrounded, in µm."""
    return math.sqrt(2.0) * single_pitch_tolerance(d_mm, m_n_mm, accuracy_class)


@dataclass(frozen=True)
class FlankTolerances:
    """The rounded tolerances of one gear and class in µm (registry names as attributes)."""

    accuracy_class: int
    single_pitch_tolerance: float
    total_cumulative_pitch_tolerance: float
    profile_slope_tolerance: float
    profile_form_tolerance: float
    total_profile_tolerance: float
    helix_slope_tolerance: float
    helix_form_tolerance: float
    total_helix_tolerance: float
    runout_tolerance: float
    adjacent_pitch_difference_tolerance: float

    def value(self, name: str) -> float:
        out = getattr(self, name, None)
        if not isinstance(out, float):
            raise InputRangeError(f"no tolerance {name!r}")
        return out


def flank_tolerances(
    d_mm: float, m_n_mm: float, b_mm: float, accuracy_class: int
) -> FlankTolerances:
    """All tolerances of the class, rounded after 5.2.3 (the totals from the unrounded parts)."""
    args = (d_mm, m_n_mm, accuracy_class)
    return FlankTolerances(
        accuracy_class=accuracy_class,
        single_pitch_tolerance=rounded(single_pitch_tolerance(*args)),
        total_cumulative_pitch_tolerance=rounded(total_cumulative_pitch_tolerance(*args)),
        profile_slope_tolerance=rounded(profile_slope_tolerance(*args)),
        profile_form_tolerance=rounded(profile_form_tolerance(*args)),
        total_profile_tolerance=rounded(total_profile_tolerance(*args)),
        helix_slope_tolerance=rounded(helix_slope_tolerance(d_mm, b_mm, accuracy_class)),
        helix_form_tolerance=rounded(helix_form_tolerance(d_mm, b_mm, accuracy_class)),
        total_helix_tolerance=rounded(total_helix_tolerance(d_mm, b_mm, accuracy_class)),
        runout_tolerance=rounded(runout_tolerance(*args)),
        adjacent_pitch_difference_tolerance=rounded(adjacent_pitch_difference_tolerance(*args)),
    )


__all__ = [
    "CLASSES",
    "FlankTolerances",
    "adjacent_pitch_difference_tolerance",
    "flank_tolerances",
    "helix_form_tolerance",
    "helix_slope_tolerance",
    "profile_form_tolerance",
    "profile_slope_tolerance",
    "rounded",
    "runout_tolerance",
    "single_pitch_tolerance",
    "step_factor",
    "total_cumulative_pitch_tolerance",
    "total_helix_tolerance",
    "total_profile_tolerance",
]
