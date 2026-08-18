"""
@module: app.services.geometry.din3967
@context: Domain layer — DIN 3967:1978-08 tooth-thickness allowances (still valid).
@role: The complete Tables 1 (upper tooth-thickness allowances E_sns, series a…h) and
       2 (tooth-thickness tolerances T_sn, series 21…30) of DIN 3967, keyed by the
       reference-diameter range. A drawing designation like "27cd" (tolerance series 27 +
       allowance series cd) resolves to (E_sns, E_sni = E_sns − T_sn) in µm — the input
       alternative to directly specified span allowances (DIN 21773 §14.4 converts:
       A_W = E_sn·cos α_n). Transcribed 2026-08-18 from the norm PDF and pinned against
       the norm's own example (§3.1: designation 27cd at d = 100 mm → E_sns = −70 µm,
       E_sni = −170 µm).

Symbols: DIN 3967 wrote the allowances as A_sne/A_sni; DIN 21773 renamed them E_sns/E_sni
(international harmonization) — this module uses the current E names.
"""

from __future__ import annotations

__all__ = [
    "ALLOWANCE_SERIES",
    "TOLERANCE_SERIES",
    "allowances_um",
    "tolerance_um",
    "upper_allowance_um",
]

#: reference-diameter range upper bounds (mm): row i covers bounds[i-1] < d ≤ bounds[i]
_DIA_UPPER_BOUNDS_MM = (
    10.0,
    50.0,
    125.0,
    280.0,
    560.0,
    1000.0,
    1600.0,
    2500.0,
    4000.0,
    6300.0,
    10000.0,
)

ALLOWANCE_SERIES: tuple[str, ...] = ("a", "ab", "b", "bc", "c", "cd", "d", "e", "f", "g", "h")
TOLERANCE_SERIES: tuple[int, ...] = (21, 22, 23, 24, 25, 26, 27, 28, 29, 30)

#: Table 1 — upper tooth-thickness allowances E_sns in µm (rows = diameter ranges,
#: columns = ALLOWANCE_SERIES)
_TABLE1_UPPER_UM: tuple[tuple[int, ...], ...] = (
    (-100, -85, -70, -58, -48, -40, -33, -22, -10, -5, 0),  # d ≤ 10
    (-135, -110, -95, -75, -65, -54, -44, -30, -14, -7, 0),  # 10 < d ≤ 50
    (-180, -150, -125, -105, -85, -70, -60, -40, -19, -9, 0),  # 50 < d ≤ 125
    (-250, -200, -170, -140, -115, -95, -80, -56, -26, -12, 0),  # 125 < d ≤ 280
    (-330, -280, -230, -190, -155, -130, -110, -75, -35, -17, 0),  # 280 < d ≤ 560
    (-450, -370, -310, -260, -210, -175, -145, -100, -48, -22, 0),  # 560 < d ≤ 1000
    (-600, -500, -420, -340, -290, -240, -200, -135, -64, -30, 0),  # 1000 < d ≤ 1600
    (-820, -680, -560, -460, -390, -320, -270, -180, -85, -41, 0),  # 1600 < d ≤ 2500
    (-1100, -920, -760, -620, -520, -430, -360, -250, -115, -56, 0),  # 2500 < d ≤ 4000
    (-1500, -1250, -1020, -840, -700, -580, -480, -330, -155, -75, 0),  # 4000 < d ≤ 6300
    (-2000, -1650, -1350, -1150, -940, -780, -640, -450, -210, -100, 0),  # 6300 < d ≤ 10000
)

#: Table 2 — tooth-thickness tolerances T_sn in µm (rows = diameter ranges,
#: columns = TOLERANCE_SERIES)
_TABLE2_TOLERANCE_UM: tuple[tuple[int, ...], ...] = (
    (3, 5, 8, 12, 20, 30, 50, 80, 130, 200),  # d ≤ 10
    (5, 8, 12, 20, 30, 50, 80, 130, 200, 300),  # 10 < d ≤ 50
    (6, 10, 16, 25, 40, 60, 100, 160, 250, 400),  # 50 < d ≤ 125
    (8, 12, 20, 30, 50, 80, 130, 200, 300, 500),  # 125 < d ≤ 280
    (10, 16, 25, 40, 60, 100, 160, 250, 400, 600),  # 280 < d ≤ 560
    (12, 20, 30, 50, 80, 130, 200, 300, 500, 800),  # 560 < d ≤ 1000
    (16, 25, 40, 60, 100, 160, 250, 400, 600, 1000),  # 1000 < d ≤ 1600
    (20, 30, 50, 80, 130, 200, 300, 500, 800, 1300),  # 1600 < d ≤ 2500
    (25, 40, 60, 100, 160, 250, 400, 600, 1000, 1600),  # 2500 < d ≤ 4000
    (30, 50, 80, 130, 200, 300, 500, 800, 1300, 2000),  # 4000 < d ≤ 6300
    (40, 60, 100, 160, 250, 400, 600, 1000, 1600, 2400),  # 6300 < d ≤ 10000
)


def _row_index(reference_diameter_mm: float) -> int:
    d = abs(reference_diameter_mm)
    for i, upper in enumerate(_DIA_UPPER_BOUNDS_MM):
        if d <= upper:
            return i
    raise ValueError(f"DIN 3967: reference diameter {d:.1f} mm exceeds the table range (10 m)")


def upper_allowance_um(reference_diameter_mm: float, series: str) -> float:
    """Upper tooth-thickness allowance E_sns in µm (DIN 3967 Table 1; always ≤ 0)."""
    if series not in ALLOWANCE_SERIES:
        raise ValueError(f"DIN 3967: unknown allowance series '{series}' (a…h)")
    return float(
        _TABLE1_UPPER_UM[_row_index(reference_diameter_mm)][ALLOWANCE_SERIES.index(series)]
    )


def tolerance_um(reference_diameter_mm: float, series: int) -> float:
    """Tooth-thickness tolerance T_sn in µm (DIN 3967 Table 2; always > 0)."""
    if series not in TOLERANCE_SERIES:
        raise ValueError(f"DIN 3967: unknown tolerance series {series} (21…30)")
    return float(
        _TABLE2_TOLERANCE_UM[_row_index(reference_diameter_mm)][TOLERANCE_SERIES.index(series)]
    )


def allowances_um(
    reference_diameter_mm: float, allowance_series: str, tolerance_series: int
) -> tuple[float, float]:
    """(E_sns, E_sni) in µm for a DIN 3967 designation, e.g. ("cd", 27) = drawing "27cd".

    E_sni = E_sns − T_sn (DIN 21773 Eq. 45).
    """
    e_sns = upper_allowance_um(reference_diameter_mm, allowance_series)
    return e_sns, e_sns - tolerance_um(reference_diameter_mm, tolerance_series)
