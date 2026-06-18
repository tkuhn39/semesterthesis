"""
@module: app.services.geometry.tolerances
@context: Domain layer — gear-accuracy tolerances (the current inspection standard).
@role: Turn an **accuracy grade** A (ISO 1328-1:2018, classes 1…11) into the flank
       deviations the rest of the toolchain needs — single/total pitch (f_ptT, F_pT),
       profile slope/form/total (f_HαT, f_fαT, F_αT) and helix slope/form/total
       (f_HβT, f_fβT, F_βT). These feed the native dynamics (f_pb ≈ f_ptT, f_fα =
       f_fαT) and the manufacturing part of the face load factor (F_βT), so a user
       can specify the **quality grade** instead of raw µm deviations.

Formulas read visually from DIN ISO 1328-1:2018 §5.2.4 (eq. 5–12); the grade step is
(√2)^(A−5) referred to the unrounded grade-5 value (§5.2.2), and the totals F_αT/F_βT
use the **unrounded** slope/form components (eq. 9/12) before rounding. Rounding per
§5.2.3: >10 µm → 1 µm, 5…10 µm → 0.5 µm, <5 µm → 0.1 µm. The DIN 21773 span W_k lives
in ``geometry.gear``. All deviations in µm; m_n, d, b in mm. See memory
[[iso1328-din21773-tolerances]].
"""

import math

from pydantic import BaseModel

_SQRT2 = math.sqrt(2.0)

# ISO 1328-1 §1 application ranges (outside → extrapolation needs agreement, §5.2.1).
_GRADE_RANGE = (1, 11)
_TEETH_RANGE = (5, 1000)
_DIAMETER_RANGE_MM = (5.0, 15000.0)
_MODULE_RANGE_MM = (0.5, 70.0)
_WIDTH_RANGE_MM = (4.0, 1200.0)
_MAX_HELIX_DEG = 45.0


def grade_factor(accuracy_grade: int) -> float:
    """ISO 1328-1 §5.2.2 grade step: (√2)^(A−5), from the unrounded class-5 value."""
    return _SQRT2 ** (accuracy_grade - 5)


def round_tolerance(value: float) -> float:
    """ISO 1328-1 §5.2.3 rounding: >10 µm → 1 µm, 5…10 µm → 0.5 µm, <5 µm → 0.1 µm."""
    if value > 10.0:
        return float(round(value))
    if value >= 5.0:
        return round(value * 2.0) / 2.0
    return round(value * 10.0) / 10.0


class FlankTolerances(BaseModel):
    """ISO 1328-1:2018 single-flank deviations for one gear (µm)."""

    accuracy_grade: int
    single_pitch: float  # f_ptT  (5)
    total_pitch: float  # F_pT   (6)
    profile_slope: float  # f_HαT  (7)
    profile_form: float  # f_fαT  (8)
    profile_total: float  # F_αT   (9)
    helix_slope: float  # f_HβT  (10)
    helix_form: float  # f_fβT  (11)
    helix_total: float  # F_βT   (12)


def flank_tolerances(
    *,
    accuracy_grade: int,
    normal_module_mm: float,
    reference_diameter_mm: float,
    face_width_mm: float,
) -> FlankTolerances:
    """Flank deviations from the accuracy grade (ISO 1328-1:2018, eq. 5–12)."""
    g = grade_factor(accuracy_grade)
    mn, d, b = normal_module_mm, reference_diameter_mm, face_width_mm
    f_pt = (0.001 * d + 0.4 * mn + 5.0) * g
    f_p = (0.002 * d + 0.55 * math.sqrt(d) + 0.7 * mn + 12.0) * g
    f_halpha = (0.4 * mn + 4.0) * g
    f_falpha = (0.55 * mn + 5.0) * g
    f_hbeta = (0.05 * math.sqrt(d) + 0.35 * math.sqrt(b) + 4.0) * g
    f_fbeta = (0.07 * math.sqrt(d) + 0.45 * math.sqrt(b) + 4.0) * g
    # totals from the UNROUNDED slope/form components (eq. 9, 12)
    f_alpha = math.hypot(f_halpha, f_falpha)
    f_beta = math.hypot(f_hbeta, f_fbeta)
    return FlankTolerances(
        accuracy_grade=accuracy_grade,
        single_pitch=round_tolerance(f_pt),
        total_pitch=round_tolerance(f_p),
        profile_slope=round_tolerance(f_halpha),
        profile_form=round_tolerance(f_falpha),
        profile_total=round_tolerance(f_alpha),
        helix_slope=round_tolerance(f_hbeta),
        helix_form=round_tolerance(f_fbeta),
        helix_total=round_tolerance(f_beta),
    )


def dynamics_deviations(
    *, accuracy_grade: int, normal_module_mm: float, reference_diameter_mm: float
) -> tuple[float, float]:
    """(f_pb, f_fα) in µm for the ISO 6336-1 dynamics from the accuracy grade.

    f_pb (base pitch deviation) is taken as the single pitch deviation f_ptT and
    f_fα as the profile form deviation f_fαT (face width not needed for these two).
    """
    t = flank_tolerances(
        accuracy_grade=accuracy_grade,
        normal_module_mm=normal_module_mm,
        reference_diameter_mm=reference_diameter_mm,
        face_width_mm=10.0,  # unused by f_ptT / f_fαT
    )
    return t.single_pitch, t.profile_form


def validity_warnings(
    *,
    accuracy_grade: int,
    teeth: int,
    reference_diameter_mm: float,
    normal_module_mm: float,
    face_width_mm: float,
    helix_angle_deg: float = 0.0,
) -> list[str]:
    """ISO 1328-1 §1 application ranges — outside these the tolerances are extrapolated."""
    out: list[str] = []
    if not _GRADE_RANGE[0] <= accuracy_grade <= _GRADE_RANGE[1]:
        out.append("Toleranzklasse außerhalb 1…11 (ISO 1328-1 §5.2.1).")
    if not _TEETH_RANGE[0] <= teeth <= _TEETH_RANGE[1]:
        out.append("Zähnezahl außerhalb 5…1000.")
    if not _DIAMETER_RANGE_MM[0] <= reference_diameter_mm <= _DIAMETER_RANGE_MM[1]:
        out.append("Teilkreisdurchmesser außerhalb 5…15000 mm.")
    if not _MODULE_RANGE_MM[0] <= normal_module_mm <= _MODULE_RANGE_MM[1]:
        out.append("Normalmodul außerhalb 0,5…70 mm.")
    if not _WIDTH_RANGE_MM[0] <= face_width_mm <= _WIDTH_RANGE_MM[1]:
        out.append("Zahnbreite außerhalb 4…1200 mm.")
    if abs(helix_angle_deg) > _MAX_HELIX_DEG:
        out.append("Schrägungswinkel > 45°.")
    return out
