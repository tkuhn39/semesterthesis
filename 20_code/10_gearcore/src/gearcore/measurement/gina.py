"""Typed evaluation of the Klingelnberg P40 gear measurement (GINA): what the value file says
about one measured gear, the per-tooth tables of the curve file, and statistics over parts.

The five-digit result codes of a ``.mew`` file decompose for the flank deviations as
``G MM S T``: the group ``G`` (1 lead, 2 profile), the measurand ``MM`` (01 slope, 04 total,
07 form; 02/03, 05/06, 08/09 the same at a second position, the lead at the inner and outer
diameter ``f``/``k``, the profile at the lower and upper face-width position ``u``/``o``; 16 the
measured tip relief ``fKo`` of the pinion), the statistic ``S`` (1/2 per tooth left/right,
3/4 mean, 5/6 variation, 7/8 maximum, 9/0 minimum) and the tooth slot ``T`` (1 to 5 in the
order of the measured teeth). Every decoded code is cross-checked against the label the file
prints (``fHb links 12``, ``Fb m links``, ``V ffa rechts``, ``fHa links max``); a mismatch is a
``ParseError``, so a changed export cannot be misread silently. Sizes (``Fuß``, ``Kopf``, ``WK``,
``MdK``) and the pitch and runout values (``fp max``, ``fu max``, ``Fp``, ``Fpz/8``, ``Fr``,
``Rp``, ``Rs``) are taken by their labels.

Quantities of DIN ISO 1328-1:2018 are named by their registry name (``profile_slope_deviation``
= f_Hα …); the P40's ``Rp``, ``Rs`` and ``Fpz/8`` and the tolerances of ``Fr``, ``Rs`` and
``Fpz/8`` have no entry and stay raw: the program's ``Fpz/8`` is the pitch span of Anhang D.4
taken over all z sectors (``sliding_pitch_span_deviation``, checked on 136 of 136 flanks), which
is neither the norm's F_pk (Anhang D.2, max minus min inside a sector: ``sector_pitch_deviation``)
nor its F_pSk (Anhang D.4, z/k consecutive sectors: ``pitch_span_deviation``); both are computed
from the per-tooth tables of the curve file (``sector_values``). The tolerances in the header are
settings of the measuring program ("Toleranz laut Messprotokoll"), never a grade of a norm. The
per-tooth tip diameter lines of the value file repeat the root values (known trap, MEAS-07) and
are ignored; per-tooth tip and root diameters come from the curve file.

Signs and references: the module requires the header settings every file of the user carries
(code 178 ``LVORZ 1: DIN``, code 165 reference of f_Hβ ``1``, code 179 ``BZGFL 1: Z`` = f_Hβ
referred to the face width b, not to L_β as the norm defines it, code 180 ``BZGPR 0: M1-M2`` =
f_Hα referred to the evaluation range), else ``NotSupportedError``; a negative ``fKo`` is material
removed at the tip (pinion 95911: −23 µm). The curves of the ``.mka`` carry the probe's raw sign:
``din_sign`` gives the factor that turns them into the sign of the printed values (regression of
the printed f_Hα and f_Hβ against the curves of all 68 files, 2026-10-10: profile left flank −1,
right flank +1, lead −1 on both flanks; the pinion relief then reads −23 µm on both flanks). The
profile curves are evenly spaced in roll length, not in diameter (the printed f_Hα is reproduced
to 0,04 µm with the roll-length spacing, to 1 µm with a diameter spacing).
"""

import math
import re
from collections.abc import Sequence
from typing import Literal

from gearcore import involute as iv
from gearcore.errors import InputRangeError, NotSupportedError, ParseError
from gearcore.io.p40 import Flank, MewFile, MkaCurve, MkaFile, P40Header
from gearcore.models.common import FrozenModel
from gearcore.quantities import quantity
from gearcore.trace import eq

SOURCE = "DINISO1328-1:2018"
_TIME = re.compile(r"\d{2}:\d{2}:\d{2}")
EQ_EXEMPT = (
    "decode_code",
    "expected_labels",
    "measured_teeth",
    "gina_result",
    "tooth_tables",
    "window_statistics",
    "curve_abscissa",
    "tip_relief_length",
    "scatter_table",
    "repeatability",
    "latest_per_part",
    "sliding_pitch_span_deviation",
    "sector_values",
    "din_sign",
    "curve_values_din",
)
"""Decoding, assembly, statistics and the program's own rules: no equation of a norm
(``sector_pitches``, ``sector_pitch_deviation`` and ``pitch_span_deviation`` have one)."""

Part = Literal["wheel", "pinion"]
Statistic = Literal["tooth", "mean", "variation", "max", "min"]
Position = Literal["f", "k", "u", "o"]

FLANK_MEASURANDS: dict[tuple[int, int], tuple[str, Position | None]] = {
    (1, 1): ("helix_slope_deviation", None),
    (1, 2): ("helix_slope_deviation", "f"),
    (1, 3): ("helix_slope_deviation", "k"),
    (1, 4): ("total_helix_deviation", None),
    (1, 5): ("total_helix_deviation", "f"),
    (1, 6): ("total_helix_deviation", "k"),
    (1, 7): ("helix_form_deviation", None),
    (1, 8): ("helix_form_deviation", "f"),
    (1, 9): ("helix_form_deviation", "k"),
    (2, 1): ("profile_slope_deviation", None),
    (2, 2): ("profile_slope_deviation", "u"),
    (2, 3): ("profile_slope_deviation", "o"),
    (2, 4): ("total_profile_deviation", None),
    (2, 5): ("total_profile_deviation", "u"),
    (2, 6): ("total_profile_deviation", "o"),
    (2, 7): ("profile_form_deviation", None),
    (2, 8): ("profile_form_deviation", "u"),
    (2, 9): ("profile_form_deviation", "o"),
    (2, 16): ("tip_relief", None),
}
"""(group, measurand digits) of the flank deviation codes → registry name and position."""
STATISTICS: dict[int, tuple[Statistic, Flank]] = {
    1: ("tooth", "links"),
    2: ("tooth", "rechts"),
    3: ("mean", "links"),
    4: ("mean", "rechts"),
    5: ("variation", "links"),
    6: ("variation", "rechts"),
    7: ("max", "links"),
    8: ("max", "rechts"),
    9: ("min", "links"),
    0: ("min", "rechts"),
}
SHORT_LABEL: dict[str, str] = {
    "helix_slope_deviation": "fHb",
    "total_helix_deviation": "Fb",
    "helix_form_deviation": "ffb",
    "profile_slope_deviation": "fHa",
    "total_profile_deviation": "Fa",
    "profile_form_deviation": "ffa",
    "tip_relief": "fKo",
}
"""How the P40 labels each flank measurand."""
PITCH_LABELS: dict[str, tuple[str | None, str]] = {
    "fp max": ("single_pitch_deviation", "per flank"),
    "fu max": ("adjacent_pitch_difference", "per flank"),
    "Fp": ("total_cumulative_pitch_deviation", "per flank"),
    "Fpz/8": (None, "per flank"),
    "Fr": ("runout", "single"),
    "Rp": (None, "per flank"),
    "Rs": (None, "single"),
}
"""Pitch and runout labels → registry name (None = no norm entry, kept raw) and layout;
``Fpz/8`` is the sliding pitch span of the program (module docstring), not F_pk."""
SIZE_LABELS: dict[str, tuple[str | None, tuple[str, str, str]]] = {
    "Kopf": ("tip_diameter", ("Kopf m", "Kopf min", "Kopf max")),
    "Fuß": (None, ("Fuß m", "Fuß min", "Fuß max")),
    "WK": ("span_measurement", ("WK", "WKmin", "WKmax")),
    "MdK": ("diametral_two_ball_dimension", ("MdK", "MdKmin", "MdKmax")),
}
"""Size labels → registry name and the labels of mean, minimum and maximum. The measured root
diameter has no entry of its own (the registry's ``generated_root_diameter`` is the generation's)."""
TOLERANCE_CODES: dict[int, tuple[str | None, str, Flank | None]] = {
    82: ("profile_slope_tolerance", "fHa", "links"),
    83: ("profile_slope_tolerance", "fHa", "rechts"),
    89: ("helix_slope_tolerance", "fHb", "links"),
    90: ("helix_slope_tolerance", "fHb", "rechts"),
    210: ("single_pitch_tolerance", "fp", "links"),
    211: ("single_pitch_tolerance", "fp", "rechts"),
    212: ("adjacent_pitch_difference_tolerance", "fu", "links"),
    213: ("adjacent_pitch_difference_tolerance", "fu", "rechts"),
    214: ("total_cumulative_pitch_tolerance", "Fp", "links"),
    215: ("total_cumulative_pitch_tolerance", "Fp", "rechts"),
    216: (None, "Fpz/8", "links"),
    217: (None, "Fpz/8", "rechts"),
    218: (None, "Fr", None),
    219: (None, "Rs", None),
}
"""Header codes of the tolerances the measuring program checked against."""
REQUIRED_SIGN_SETTINGS: dict[int, tuple[str, tuple[str, ...]]] = {
    178: ("LVORZ", ("1", "DIN")),
    165: ("R_FHB", ("1",)),
    179: ("BZGFL", ("1", "Z")),
    180: ("BZGPR", ("0", "M1-M2")),
}
"""Header settings the evaluation is written for: code → the key token of the line and the
fields that must follow it (178 ``LVORZ: 1: DIN`` = sign of the lead deviations after DIN, 165
``R_FHB: 1`` = reference of f_Hβ after DIN, 179 ``BZGFL: 1: Z`` = f_Hβ referred to the face width
b, 180 ``BZGPR: 0: M1-M2`` = f_Hα referred to the evaluation range M1 to M2)."""
CONVENTION_CODES = (161, 165, 178, 179, 180, 181, 182)
"""Header lines carried verbatim in ``GinaResult.sign_conventions``."""
TOOTH_SLOTS = 5


class MewKey(FrozenModel):
    """A decoded flank deviation code."""

    code: int
    group: int
    quantity: str
    position: Position | None
    statistic: Statistic
    flank: Flank
    slot: int


def decode_code(code: int) -> MewKey:
    """The meaning of a flank deviation code; ``InputRangeError`` for a code outside the flank
    deviation groups (sizes and pitch values are taken by their labels)."""
    if not isinstance(code, int) or not 10000 <= code <= 99999:
        raise InputRangeError(f"a result code has five digits, got {code!r}")
    group, rest = divmod(code, 10000)
    measurand, rest = divmod(rest, 100)
    statistic_digit, slot = divmod(rest, 10)
    key = (group, measurand)
    if key not in FLANK_MEASURANDS:
        raise InputRangeError(
            f"code {code}: no flank deviation (group {group}, measurand {measurand})"
        )
    name, position = FLANK_MEASURANDS[key]
    statistic, flank = STATISTICS[statistic_digit]
    if statistic == "tooth" and not 1 <= slot <= TOOTH_SLOTS:
        raise InputRangeError(f"code {code}: tooth slot {slot} outside 1 to {TOOTH_SLOTS}")
    if statistic != "tooth" and slot != 0:
        raise InputRangeError(f"code {code}: statistic {statistic} carries no tooth slot")
    return MewKey(
        code=code,
        group=group,
        quantity=name,
        position=position,
        statistic=statistic,
        flank=flank,
        slot=slot,
    )


def expected_labels(key: MewKey, tooth: int | None) -> tuple[str, ...]:
    """The label forms the P40 prints for a decoded code (several, because the mean of a slope is
    ``fHbm`` while the mean of a total is ``Fb m``)."""
    short = SHORT_LABEL[key.quantity]
    flank = key.flank
    if key.statistic == "tooth":
        if tooth is None:
            raise InputRangeError("a per-tooth code needs the tooth number of its slot")
        if key.position is None:
            return (f"{short} {flank} {tooth}",)
        return (f"{short} {flank} {key.position} {tooth}{key.position}",)
    if key.statistic == "mean":
        return (f"{short}m {flank}", f"{short} m {flank}")
    if key.statistic == "variation":
        return (f"{short} Var {flank}", f"V {short} {flank}")
    return (f"{short} {flank} {key.statistic}",)


def measured_teeth(mew: MewFile) -> tuple[int, ...]:
    """The tooth numbers measured, in the order of the slots (from the per-tooth labels)."""
    teeth: dict[int, int] = {}
    for value in mew.values:
        try:
            key = decode_code(value.code)
        except InputRangeError:
            continue
        if key.statistic != "tooth" or key.position is not None:
            continue
        number = int(value.label.split()[-1])
        if teeth.setdefault(key.slot, number) != number:
            raise ParseError(f"slot {key.slot} names teeth {teeth[key.slot]} and {number}")
    if not teeth:
        raise ParseError("no per-tooth flank deviation in the file")
    ordered = [teeth[slot] for slot in sorted(teeth)]
    if sorted(teeth) != list(range(1, len(teeth) + 1)):
        raise ParseError(f"tooth slots are not 1..n: {sorted(teeth)}")
    return tuple(ordered)


class ToothValue(FrozenModel):
    tooth: int
    value_um: float


class ToothSize(FrozenModel):
    tooth: int
    value_mm: float


class PositionValue(FrozenModel):
    """A deviation measured at a second position (lead at ``f``/``k``, profile at ``u``/``o``)."""

    flank: Flank
    position: Position
    tooth: int
    value_um: float


class FlankStatistics(FrozenModel):
    flank: Flank
    per_tooth: tuple[ToothValue, ...]
    mean_um: float | None
    variation_um: float | None
    max_um: float | None
    min_um: float | None


class DeviationSet(FrozenModel):
    """One flank measurand of one gear: both flanks with their per-tooth values and statistics."""

    quantity: str
    """Registry name (``profile_slope_deviation`` …); the symbol comes from the registry."""
    symbol: str
    left: FlankStatistics
    right: FlankStatistics
    at_positions: tuple[PositionValue, ...] = ()

    def flank(self, flank: Flank) -> FlankStatistics:
        return self.left if flank == "links" else self.right


class PitchValue(FrozenModel):
    """A pitch or runout value of the value file (per flank or single)."""

    label: str
    quantity: str | None
    symbol: str | None
    left_um: float | None
    right_um: float | None
    value_um: float | None


class SizeValue(FrozenModel):
    label: str
    quantity: str | None
    symbol: str | None
    mean_mm: float
    min_mm: float | None
    max_mm: float | None
    per_tooth_mm: tuple[ToothSize, ...] = ()


class ToleranceValue(FrozenModel):
    """A tolerance the measuring program checked against ("Toleranz laut Messprotokoll")."""

    label: str
    quantity: str | None
    left_um: float
    right_um: float | None
    grade: int | None


class TipReliefMeasured(FrozenModel):
    """The tip relief the P40 measured on the pinion (``fKo``, negative = material removed)."""

    deviations: DeviationSet
    start_diameter_mm: float
    end_diameter_mm: float
    tip_relief_length_mm: float


class GinaResult(FrozenModel):
    me: str
    variant: str | None
    part: Part
    measured_on: str
    measured_at: str
    """Time of the measurement (header code 3, ``HH:MM:SS``); orders same-day files."""
    number_of_teeth: int
    measured_teeth: tuple[int, ...]
    sign_conventions: tuple[tuple[int, str], ...]
    profile_evaluation_length_mm: float
    helix_evaluation_length_mm: float
    evaluation_diameters_mm: tuple[float, float]
    """Start and end of the profile evaluation (header codes 42, 43)."""
    deviations: tuple[DeviationSet, ...]
    pitch: tuple[PitchValue, ...]
    sizes: tuple[SizeValue, ...]
    tolerances: tuple[ToleranceValue, ...]
    grade: int | None
    """Tolerance grade the measuring program was set to (7 wheel, 6 pinion), norm unnamed."""
    tip_relief: TipReliefMeasured | None
    unmapped: tuple[int, ...]
    """Result codes the evaluation does not use (per-tooth tip lines of MEAS-07 among them)."""

    def deviation(self, name: str) -> DeviationSet:
        for entry in self.deviations:
            if entry.quantity == name:
                return entry
        raise InputRangeError(f"no deviation {name!r} in the result of {self.me}")

    def pitch_value(self, label: str) -> PitchValue:
        for entry in self.pitch:
            if entry.label == label:
                return entry
        raise InputRangeError(f"no pitch value {label!r} in the result of {self.me}")

    def size(self, label: str) -> SizeValue:
        for entry in self.sizes:
            if entry.label == label:
                return entry
        raise InputRangeError(f"no size {label!r} in the result of {self.me}")


def _symbol(name: str | None) -> str | None:
    return None if name is None else quantity(name).symbol


def _check_signs(mew: MewFile) -> tuple[tuple[int, str], ...]:
    """The sign and reference settings of the header (codes 161, 165, 178, 181, 182) as printed;
    ``NotSupportedError`` where a setting differs from the one the evaluation is written for."""
    conventions = tuple((code, mew.header.text(code)) for code in CONVENTION_CODES)
    for code, (token, expected) in REQUIRED_SIGN_SETTINGS.items():
        fields = mew.header.require(code).fields
        if token not in fields:
            raise ParseError(f"header code {code} has no field {token!r}: {fields}")
        at = fields.index(token) + 1
        if tuple(fields[at : at + len(expected)]) != expected:
            raise NotSupportedError(
                f"header code {code} is {mew.header.text(code)!r}; the evaluation is written for "
                f"the setting {token}: {' : '.join(expected)!r} of the user's files"
            )
    return conventions


def _flank_statistics(
    flank: Flank, values: dict[tuple[Statistic, int], float], teeth: Sequence[int]
) -> FlankStatistics:
    per_tooth = tuple(
        ToothValue(tooth=teeth[slot - 1], value_um=values[("tooth", slot)])
        for slot in range(1, len(teeth) + 1)
        if ("tooth", slot) in values
    )
    return FlankStatistics(
        flank=flank,
        per_tooth=per_tooth,
        mean_um=values.get(("mean", 0)),
        variation_um=values.get(("variation", 0)),
        max_um=values.get(("max", 0)),
        min_um=values.get(("min", 0)),
    )


def _number(mew: MewFile, label: str) -> float | None:
    """The value of the single result line with this label; ``None`` if absent or a placeholder."""
    found = [value for value in mew.values if value.label == label]
    if not found:
        return None
    if len(found) > 1:
        raise ParseError(f"label {label!r} appears {len(found)} times")
    return found[0].value


def tip_relief_length(start_diameter_mm: float, end_diameter_mm: float, d_b_mm: float) -> float:
    """Roll length of the tip relief zone: ρ(end) − ρ(start) with the radius of curvature of the
    involute (``involute.radius_of_curvature``, ISO 21771 Eq. (17))."""
    if not end_diameter_mm > start_diameter_mm:
        raise InputRangeError(
            f"the relief zone must run outwards: {start_diameter_mm!r} to {end_diameter_mm!r}"
        )
    return iv.radius_of_curvature(end_diameter_mm, d_b_mm) - iv.radius_of_curvature(
        start_diameter_mm, d_b_mm
    )


def gina_result(mew: MewFile, *, part: Part) -> GinaResult:
    """The typed result of a value file; every flank deviation code cross-checked against its
    label, sizes and pitch values by their labels, unmatched codes listed in ``unmapped``."""
    if part not in ("wheel", "pinion"):
        raise InputRangeError(f"part must be 'wheel' or 'pinion', got {part!r}")
    header = mew.header
    conventions = _check_signs(mew)
    teeth = measured_teeth(mew)
    z = int(header.number(22))
    used: set[int] = set()
    # ---- flank deviations by code, checked against the labels
    collected: dict[str, dict[Flank, dict[tuple[Statistic, int], float]]] = {}
    positions: dict[str, list[PositionValue]] = {}
    for value in mew.values:
        try:
            key = decode_code(value.code)
        except InputRangeError:
            continue
        if key.statistic == "tooth" and key.slot > len(teeth):
            raise ParseError(
                f"code {value.code}: slot {key.slot}, only {len(teeth)} teeth measured"
            )
        tooth = teeth[key.slot - 1] if key.statistic == "tooth" else None
        forms = expected_labels(key, tooth)
        if value.label not in forms:
            raise ParseError(
                f"code {value.code} is labelled {value.label!r}, expected one of {forms}"
            )
        used.add(value.code)
        if value.value is None:
            continue
        if key.position is not None:
            assert tooth is not None
            positions.setdefault(key.quantity, []).append(
                PositionValue(
                    flank=key.flank, position=key.position, tooth=tooth, value_um=value.value
                )
            )
            continue
        collected.setdefault(key.quantity, {}).setdefault(key.flank, {})[
            (key.statistic, key.slot)
        ] = value.value
    deviations: list[DeviationSet] = []
    relief_set: DeviationSet | None = None
    for name in SHORT_LABEL:
        if name not in collected:
            continue
        flanks = collected[name]
        entry = DeviationSet(
            quantity=name,
            symbol=quantity(name).symbol or name,
            left=_flank_statistics("links", flanks.get("links", {}), teeth),
            right=_flank_statistics("rechts", flanks.get("rechts", {}), teeth),
            at_positions=tuple(positions.get(name, ())),
        )
        if name == "tip_relief":
            relief_set = entry
        else:
            deviations.append(entry)
    # ---- pitch and runout by label
    pitch: list[PitchValue] = []
    for label, (pitch_name, layout) in PITCH_LABELS.items():
        if layout == "per flank":
            left = _number(mew, f"{label} links")
            right = _number(mew, f"{label} rechts")
            if left is None and right is None:
                continue
            pitch.append(
                PitchValue(
                    label=label,
                    quantity=pitch_name,
                    symbol=_symbol(pitch_name),
                    left_um=left,
                    right_um=right,
                    value_um=None,
                )
            )
        else:
            single = _number(mew, label)
            if single is None:
                continue
            pitch.append(
                PitchValue(
                    label=label,
                    quantity=pitch_name,
                    symbol=_symbol(pitch_name),
                    left_um=None,
                    right_um=None,
                    value_um=single,
                )
            )
    for value in mew.values:
        if value.label.rsplit(" ", 1)[0] in PITCH_LABELS or value.label in PITCH_LABELS:
            used.add(value.code)
    # ---- sizes by label (per-tooth root values; the per-tooth tip lines are the trap MEAS-07)
    sizes: list[SizeValue] = []
    for label, (size_name, (mean_label, min_label, max_label)) in SIZE_LABELS.items():
        mean = _number(mew, mean_label)
        if mean is None:
            continue
        per_tooth: list[ToothSize] = []
        if label == "Fuß":
            for tooth in teeth:
                root = _number(mew, f"Fuß {tooth}")
                if root is not None:
                    per_tooth.append(ToothSize(tooth=tooth, value_mm=root))
        sizes.append(
            SizeValue(
                label=label,
                quantity=size_name,
                symbol=_symbol(size_name),
                mean_mm=mean,
                min_mm=_number(mew, min_label),
                max_mm=_number(mew, max_label),
                per_tooth_mm=tuple(per_tooth),
            )
        )
        for value in mew.values:
            if value.label in (mean_label, min_label, max_label) or value.label.startswith(
                f"{label} "
            ):
                used.add(value.code)
            if value.label.startswith("V " + label):
                used.add(value.code)
    # ---- tolerances of the measuring program
    tolerances: list[ToleranceValue] = []
    grade: int | None = None
    pairs: dict[str, dict[Flank | None, tuple[float, int | None]]] = {}
    for code, (_, label, flank) in TOLERANCE_CODES.items():
        line = header.get(code)
        if line is None:
            continue
        numbers = line.numbers()
        if code in (82, 83, 89, 90):
            limit, this_grade = abs(numbers[0]), None
            if len(numbers) > 1 and abs(numbers[1]) != limit:
                raise ParseError(f"header code {code}: asymmetric tolerance {numbers[:2]}")
        else:
            limit, this_grade = numbers[0], int(numbers[1]) if len(numbers) > 1 else None
            if this_grade is not None:
                grade = this_grade if grade is None else grade
                if this_grade != grade:
                    raise ParseError(f"tolerance grades differ: {grade} and {this_grade}")
        pairs.setdefault(label, {})[flank] = (limit, this_grade)
    for label, by_flank in pairs.items():
        tolerance_name = next(n for n, lab, _ in TOLERANCE_CODES.values() if lab == label)
        if None in by_flank:
            limit, this_grade = by_flank[None]
            tolerances.append(
                ToleranceValue(
                    label=label,
                    quantity=tolerance_name,
                    left_um=limit,
                    right_um=None,
                    grade=this_grade,
                )
            )
        else:
            left, this_grade = by_flank["links"]
            right = by_flank.get("rechts", (left, this_grade))[0]
            tolerances.append(
                ToleranceValue(
                    label=label,
                    quantity=tolerance_name,
                    left_um=left,
                    right_um=right,
                    grade=this_grade,
                )
            )
    # ---- tip relief (pinion)
    relief: TipReliefMeasured | None = None
    if relief_set is not None:
        if header.get(431) is None or header.get(432) is None:
            raise ParseError("fKo values without the relief zone (header codes 431, 432)")
        start = header.number(431)
        end = header.number(432)
        relief = TipReliefMeasured(
            deviations=relief_set,
            start_diameter_mm=start,
            end_diameter_mm=end,
            tip_relief_length_mm=tip_relief_length(start, end, _base_diameter(header)),
        )
    unmapped = tuple(sorted(value.code for value in mew.values if value.code not in used))
    return GinaResult(
        me=header.text(7).split("-")[0].split("_")[0],
        variant=_variant(header.text(7)),
        part=part,
        measured_on=_iso_date(header.text(2)),
        measured_at=_time_of_day(header.text(3)),
        number_of_teeth=z,
        measured_teeth=teeth,
        sign_conventions=conventions,
        profile_evaluation_length_mm=header.number(45),
        helix_evaluation_length_mm=header.number(63) - header.number(62),
        evaluation_diameters_mm=(header.number(42), header.number(43)),
        deviations=tuple(deviations),
        pitch=tuple(pitch),
        sizes=tuple(sizes),
        tolerances=tuple(tolerances),
        grade=grade,
        tip_relief=relief,
        unmapped=unmapped,
    )


def _variant(me_field: str) -> str | None:
    for separator in ("-", "_"):
        if separator in me_field:
            return separator + me_field.split(separator, 1)[1]
    return None


def _iso_date(text: str) -> str:
    day, month, year = text.strip().split(".")
    return f"20{year}-{month}-{day}"


def _time_of_day(text: str) -> str:
    """The first ``HH:MM:SS`` of a header line (code 3 prints the time of the measurement)."""
    match = _TIME.search(text)
    if match is None:
        raise ParseError(f"no time of day in header code 3: {text!r}")
    return match.group(0)


def _base_diameter(header: P40Header) -> float:
    """Base diameter of the gear data in the header (codes 21 to 24, ISO 21771 Eq. (7))."""
    return iv.base_diameter(
        int(header.number(22)),
        header.number(21),
        math.radians(header.number(24)),
        math.radians(header.number(23)),
    )


# ---- per-tooth tables of the curve file ---------------------------------------------------------


class ToothTable(FrozenModel):
    """``individual_single_pitch_deviation`` f_pi, ``individual_cumulative_pitch_deviation`` F_pi
    and ``individual_radial_measurement`` r_i of every tooth of one flank (µm)."""

    me: str
    flank: Flank
    teeth: tuple[int, ...]
    f_pi_um: tuple[float, ...]
    F_pi_um: tuple[float, ...]
    r_i_um: tuple[float, ...]


def tooth_tables(mka: MkaFile) -> tuple[ToothTable, ToothTable]:
    """Both per-tooth tables (left, right) of a curve file."""
    me = mka.header.text(7).split("-")[0].split("_")[0]
    out: list[ToothTable] = []
    flanks: tuple[Flank, ...] = ("links", "rechts")
    for flank in flanks:
        table = mka.pitch_table(flank)
        out.append(
            ToothTable(
                me=me,
                flank=flank,
                teeth=tuple(row[0] for row in table.rows),
                f_pi_um=tuple(row[1] for row in table.rows),
                F_pi_um=tuple(row[2] for row in table.rows),
                r_i_um=tuple(row[3] for row in table.rows),
            )
        )
    return out[0], out[1]


def _nearest_whole(numerator: int, denominator: int) -> int:
    """``numerator / denominator`` to the nearest whole number (halves up), in integers."""
    n = 0
    while 2 * denominator * (n + 1) <= 2 * numerator + denominator:
        n += 1
    return n


def _check_table(F_pi_um: Sequence[float], k: int) -> list[float]:
    values = [float(v) for v in F_pi_um]
    z = len(values)
    if z < 3:
        raise InputRangeError(f"a gear has at least 3 teeth, got {z}")
    if not isinstance(k, int) or not 2 <= k <= z - 1:
        raise InputRangeError(f"k must lie in 2 to {z - 1} (Anhang D: k >= 2), got {k!r}")
    return values


@eq(SOURCE, "(D.1)", section="Anhang D.2", page=48, note="k = z/8 to the nearest whole number")
def sector_pitches(z: int) -> int:
    """Number of pitches of the sector of F_pz/8: k ≈ z/8 to the nearest whole number
    (52 teeth: 7; 51 teeth: 6), at least 2; F_pz/8 applies to 12 teeth or more."""
    if not isinstance(z, int) or z < 12:
        raise InputRangeError(f"F_pz/8 applies to gears with 12 or more teeth, got {z!r}")
    return max(2, _nearest_whole(z, 8))


@eq(
    SOURCE,
    "D.2",
    section="Anhang D.2 and D.4",
    page=48,
    note=(
        "F_pk: largest algebraic difference (max minus min) of the F_pi inside any of the z "
        "sectors of k pitches (k + 1 adjacent teeth)"
    ),
)
def sector_pitch_deviation(F_pi_um: Sequence[float], k: int) -> float:
    """F_pk of Anhang D.2: for every one of the z sectors of ``k`` pitches (k + 1 adjacent teeth,
    continuing past the last tooth) the largest minus the smallest F_pi inside it; F_pk is the
    largest of these (Anhang D.3). Not what the P40 prints as ``Fpz/8``: see
    ``sliding_pitch_span_deviation``."""
    values = _check_table(F_pi_um, k)
    z = len(values)
    spans = []
    for first in range(z):
        sector = [values[(first + i) % z] for i in range(k + 1)]
        spans.append(max(sector) - min(sector))
    return max(spans)


@eq(
    SOURCE,
    "D.4",
    section="Anhang D.4",
    page=49,
    note=(
        "F_pSk: algebraic difference between the first and the last F_pi of a sector of k "
        "pitches, over z/k (nearest whole number) consecutive sectors from tooth 1"
    ),
)
def pitch_span_deviation(F_pi_um: Sequence[float], k: int) -> float:
    """F_pSk of Anhang D.4 (magnitude): the sectors are z/k consecutive windows of ``k`` pitches
    starting at the first tooth, and only the first and the last value of each window enter.
    The norm sets no tolerance for F_pSk."""
    values = _check_table(F_pi_um, k)
    z = len(values)
    windows = _nearest_whole(z, k)
    if windows < 1:
        raise InputRangeError(f"no window of {k} pitches on {z} teeth")
    return max(abs(values[(w * k + k) % z] - values[w * k]) for w in range(windows))


def sliding_pitch_span_deviation(F_pi_um: Sequence[float], k: int) -> float:
    """What the P40 prints as ``Fpz/8`` (checked against all 68 files of the user, 136 of 136
    flanks, 2026-10-10): the pitch span of Anhang D.4 (first minus last F_pi of a sector of
    ``k`` pitches, magnitude) taken over all z sectors instead of z/k consecutive ones. It is
    neither F_pk nor F_pSk of the norm, so it stays a value of the measuring program."""
    values = _check_table(F_pi_um, k)
    z = len(values)
    return max(abs(values[(first + k) % z] - values[first]) for first in range(z))


class SectorValues(FrozenModel):
    """The three sector quantities of one flank from the per-tooth table (µm)."""

    me: str
    flank: Flank
    k: int
    sliding_span_um: float
    """The program's ``Fpz/8``."""
    F_pk_um: float
    """Anhang D.2."""
    F_pSk_um: float
    """Anhang D.4."""


def sector_values(table: ToothTable) -> SectorValues:
    """Program value, F_pk and F_pSk of a per-tooth table with k = ``sector_pitches(z)``."""
    k = sector_pitches(len(table.teeth))
    return SectorValues(
        me=table.me,
        flank=table.flank,
        k=k,
        sliding_span_um=sliding_pitch_span_deviation(table.F_pi_um, k),
        F_pk_um=sector_pitch_deviation(table.F_pi_um, k),
        F_pSk_um=pitch_span_deviation(table.F_pi_um, k),
    )


class WindowStatistics(FrozenModel):
    """Tooth-individual pitch and radial values inside a window of teeth against the rest."""

    me: str
    flank: Flank
    first_tooth: int
    last_tooth: int
    mean_abs_f_pi_inside_um: float
    mean_abs_f_pi_outside_um: float
    mean_r_i_inside_um: float
    mean_r_i_outside_um: float
    spread_F_pi_inside_um: float
    """Largest minus smallest F_pi within the window: the sector pitch deviation of this one
    sector (Anhang D.2) when the window spans k pitches."""
    spread_rank: int
    """1 = the window has the largest spread of all windows of its length on the gear."""
    tooth_of_max_abs_f_pi: int
    """Over the whole gear, not only the window."""
    tooth_of_max_abs_F_pi: int
    """Over the whole gear, not only the window."""


def window_statistics(table: ToothTable, first_tooth: int, last_tooth: int) -> WindowStatistics:
    """Statistics of the window ``first_tooth`` to ``last_tooth`` (inclusive, continuing past the last tooth)."""
    z = len(table.teeth)
    if not (1 <= first_tooth <= z and 1 <= last_tooth <= z):
        raise InputRangeError(f"window {first_tooth} to {last_tooth} outside 1 to {z}")
    index = {tooth: i for i, tooth in enumerate(table.teeth)}
    length = (last_tooth - first_tooth) % z + 1
    inside = [((first_tooth - 1 + i) % z) + 1 for i in range(length)]
    inside_set = set(inside)
    outside = [t for t in table.teeth if t not in inside_set]

    def mean(values: Sequence[float]) -> float:
        return sum(values) / len(values) if values else math.nan

    f_pi = table.f_pi_um
    F_pi = table.F_pi_um
    r_i = table.r_i_um
    f_in = [abs(f_pi[index[t]]) for t in inside]
    f_out = [abs(f_pi[index[t]]) for t in outside]
    r_in = [r_i[index[t]] for t in inside]
    r_out = [r_i[index[t]] for t in outside]
    spans = []
    for start in range(z):
        window = [F_pi[(start + i) % z] for i in range(length)]
        spans.append(max(window) - min(window))
    own = spans[first_tooth - 1]
    rank = 1 + sum(1 for s in spans if s > own)
    return WindowStatistics(
        me=table.me,
        flank=table.flank,
        first_tooth=first_tooth,
        last_tooth=last_tooth,
        mean_abs_f_pi_inside_um=mean(f_in),
        mean_abs_f_pi_outside_um=mean(f_out),
        mean_r_i_inside_um=mean(r_in),
        mean_r_i_outside_um=mean(r_out),
        spread_F_pi_inside_um=own,
        spread_rank=rank,
        tooth_of_max_abs_f_pi=max(table.teeth, key=lambda t: abs(f_pi[index[t]])),
        tooth_of_max_abs_F_pi=max(table.teeth, key=lambda t: abs(F_pi[index[t]])),
    )


def _is_profile(curve: MkaCurve) -> bool:
    if curve.block == "Profil" or (curve.block == "Verschränkung" and curve.axis == "z"):
        return True
    if curve.block == "Flankenlinie" or (curve.block == "Verschränkung" and curve.axis == "x"):
        return False
    raise InputRangeError(f"no abscissa or sign rule for the block {curve.block!r}")


def curve_abscissa(mka: MkaFile, curve: MkaCurve) -> tuple[float, ...]:
    """Where the values of a curve lie. A profile runs from the start of the measuring range
    (header code 41) to its end (code 44), evenly spaced in roll length (the probe rolls on the
    base circle: the printed f_Hα is reproduced from the curve to 0,04 µm with this spacing and
    to 1 µm with an even spacing in diameter), returned as the diameter d = sqrt(4 ρ² + d_b²);
    a lead runs over the face width from the lower end (61) to the upper end (64), evenly."""
    header = mka.header
    if _is_profile(curve):
        start, end = header.number(41), header.number(44)
    else:
        start, end = header.number(61), header.number(64)
    if curve.count < 2 or not end > start:
        raise ParseError(f"curve {curve.block} of tooth {curve.tooth}: range {start} to {end}")
    if not _is_profile(curve):
        step = (end - start) / (curve.count - 1)
        return tuple(start + i * step for i in range(curve.count))
    d_b = _base_diameter(header)
    rho_start = iv.radius_of_curvature(start, d_b)
    rho_end = iv.radius_of_curvature(end, d_b)
    step = (rho_end - rho_start) / (curve.count - 1)
    return tuple(
        math.sqrt((2.0 * (rho_start + i * step)) ** 2 + d_b**2) for i in range(curve.count)
    )


def din_sign(curve: MkaCurve) -> float:
    """Factor that turns the raw values of a curve into the sign convention of the printed
    values (DIN, header codes 165/178): profile left flank −1, right flank +1, lead −1 on both
    flanks. Found by regressing the printed f_Hα and f_Hβ of every tooth against its curve over
    all 68 files of the user (2026-10-10, residuals ≤ 0,05 µm); with it the measured tip relief of
    the pinions reads −23 µm on both flanks and the tip rounding of the wheels is negative."""
    if _is_profile(curve):
        return -1.0 if curve.flank == "links" else 1.0
    return -1.0


def curve_values_din(curve: MkaCurve) -> tuple[float | None, ...]:
    """The values of a curve with the sign of the printed values (``din_sign``)."""
    factor = din_sign(curve)
    return tuple(None if v is None else factor * v for v in curve.values)


# ---- statistics over parts -----------------------------------------------------------------------


class ScatterRow(FrozenModel):
    """Spread of one quantity (per flank) over a set of parts."""

    quantity: str | None
    symbol: str | None
    label: str
    flank: str
    """``links``, ``rechts`` or ``''`` for a single value."""
    unit: str
    count: int
    mean: float
    standard_deviation: float
    minimum: float
    maximum: float
    me_of_minimum: str
    me_of_maximum: str


def _rows_of(result: GinaResult) -> list[tuple[str | None, str | None, str, str, str, float]]:
    """(quantity, symbol, label, flank, unit, value) of every mean/single value of a result."""
    rows: list[tuple[str | None, str | None, str, str, str, float]] = []
    flanks: tuple[Flank, ...] = ("links", "rechts")
    for entry in result.deviations:
        for flank in flanks:
            stats = entry.flank(flank)
            if stats.mean_um is not None:
                rows.append(
                    (
                        entry.quantity,
                        entry.symbol,
                        SHORT_LABEL[entry.quantity],
                        flank,
                        "µm",
                        stats.mean_um,
                    )
                )
    for value in result.pitch:
        if value.value_um is not None:
            rows.append((value.quantity, value.symbol, value.label, "", "µm", value.value_um))
        for flank, number in (("links", value.left_um), ("rechts", value.right_um)):
            if number is not None:
                rows.append((value.quantity, value.symbol, value.label, flank, "µm", number))
    for size in result.sizes:
        rows.append((size.quantity, size.symbol, size.label, "", "mm", size.mean_mm))
    if result.tip_relief is not None:
        for flank in flanks:
            stats = result.tip_relief.deviations.flank(flank)
            if stats.mean_um is not None:
                rows.append(
                    (
                        "tip_relief",
                        result.tip_relief.deviations.symbol,
                        "fKo",
                        flank,
                        "µm",
                        stats.mean_um,
                    )
                )
    return rows


def scatter_table(results: Sequence[GinaResult]) -> tuple[ScatterRow, ...]:
    """Mean, standard deviation (n − 1), minimum and maximum of every mean or single value over
    the results given (one result per part: choose the latest measurement before calling)."""
    if not results:
        raise InputRangeError("no results")
    groups: dict[
        tuple[str, str], list[tuple[str | None, str | None, str, str, str, float, str]]
    ] = {}
    for result in results:
        for name, symbol, label, flank, unit, value in _rows_of(result):
            groups.setdefault((label, flank), []).append(
                (name, symbol, label, flank, unit, value, result.me)
            )
    rows: list[ScatterRow] = []
    for (label, flank), entries in groups.items():
        values = [e[5] for e in entries]
        n = len(values)
        mean = sum(values) / n
        sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1)) if n > 1 else 0.0
        low = min(entries, key=lambda e: e[5])
        high = max(entries, key=lambda e: e[5])
        rows.append(
            ScatterRow(
                quantity=entries[0][0],
                symbol=entries[0][1],
                label=label,
                flank=flank,
                unit=entries[0][4],
                count=n,
                mean=mean,
                standard_deviation=sd,
                minimum=low[5],
                maximum=high[5],
                me_of_minimum=low[6],
                me_of_maximum=high[6],
            )
        )
    return tuple(rows)


class RepeatRow(FrozenModel):
    """The spread of one value over repeated measurements of the same part."""

    me: str
    label: str
    flank: str
    unit: str
    count: int
    values: tuple[float, ...]
    spread: float
    """Largest minus smallest value."""


def repeatability(results: Sequence[GinaResult]) -> tuple[RepeatRow, ...]:
    """Spread of every value over the results of parts measured more than once."""
    by_me: dict[str, list[GinaResult]] = {}
    for result in results:
        by_me.setdefault(result.me, []).append(result)
    rows: list[RepeatRow] = []
    for me, own in sorted(by_me.items()):
        if len(own) < 2:
            continue
        values: dict[tuple[str, str, str], list[float]] = {}
        for result in own:
            for _, _, label, flank, unit, value in _rows_of(result):
                values.setdefault((label, flank, unit), []).append(value)
        for (label, flank, unit), numbers in values.items():
            if len(numbers) < 2:
                continue
            rows.append(
                RepeatRow(
                    me=me,
                    label=label,
                    flank=flank,
                    unit=unit,
                    count=len(numbers),
                    values=tuple(numbers),
                    spread=max(numbers) - min(numbers),
                )
            )
    return tuple(rows)


def latest_per_part(results: Sequence[GinaResult]) -> tuple[GinaResult, ...]:
    """One result per ME: the latest date and time of day, among equal ones the last variant in
    sorted order."""
    chosen: dict[str, GinaResult] = {}
    for result in results:
        current = chosen.get(result.me)
        key = (result.measured_on, result.measured_at, result.variant or "")
        if current is None or key > (
            current.measured_on,
            current.measured_at,
            current.variant or "",
        ):
            chosen[result.me] = result
    return tuple(chosen[me] for me in sorted(chosen))


__all__ = [
    "EQ_EXEMPT",
    "FLANK_MEASURANDS",
    "PITCH_LABELS",
    "SHORT_LABEL",
    "SIZE_LABELS",
    "STATISTICS",
    "TOLERANCE_CODES",
    "DeviationSet",
    "FlankStatistics",
    "GinaResult",
    "MewKey",
    "PitchValue",
    "PositionValue",
    "RepeatRow",
    "ScatterRow",
    "SectorValues",
    "SizeValue",
    "TipReliefMeasured",
    "ToleranceValue",
    "ToothSize",
    "ToothTable",
    "ToothValue",
    "WindowStatistics",
    "curve_abscissa",
    "curve_values_din",
    "decode_code",
    "din_sign",
    "expected_labels",
    "gina_result",
    "latest_per_part",
    "measured_teeth",
    "pitch_span_deviation",
    "repeatability",
    "scatter_table",
    "sector_pitch_deviation",
    "sector_pitches",
    "sector_values",
    "sliding_pitch_span_deviation",
    "tip_relief_length",
    "tooth_tables",
    "window_statistics",
]
