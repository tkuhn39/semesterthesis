"""STplus ``.sta`` text reports (FVA STplus 6.0 … 11.1F).

Layout (observed on kst-A 6.0.9, kst-B 9.0F, kst-E 11.0F, own 11.1F runs): 7-space indented lines;
a page break is a line starting with ``1`` (FORTRAN carriage control) followed by three ``*`` framed
header lines; the cover page carries ``Version: 11.1F``; a calculation block starts with a title
between two dashed lines (``Geometrieberechnung nach DIN 3960 (Maerz 1987)``), subsections are
``--- Name ----`` lines, and a value line is::

    <label with dot leaders>  <symbol>   <value gear 1>   <value gear 2>   <unit>
    <label ...>               <symbol>        <pair value>                 <unit>

Symbols are recognised from an explicit registry (``SYMBOLS``); lines without a registered symbol are
kept by their label so nothing is dropped silently. Letter markers (quality ``N 7``, DIN 3967 series
``C C`` / ``cd cd``) are value tokens: a registered single-letter symbol (``z``, ``a``, ``b`` …) counts as
the symbol only when numbers follow it (gate ADV0-12). Special shapes (``A_Ae  + 0.015``, the
``j_t / j_n`` backlash pairs) are coded explicitly. The parser is grammar-only: it never interprets
numbers; the symbol → contract mapping lives in the parity tests.
"""

import re
from pathlib import Path

from gearcore.errors import ParseError
from gearcore.models.common import FrozenModel

UNITS: frozenset[str] = frozenset(
    {
        "mm",
        "Grad",
        "-",
        "um",
        "N",
        "1/min",
        "min-1",
        "N/mm2",
        "N/mm",
        "MPa",
        "kW",
        "W",
        "hp",
        "Nm",
        "g/cm3",
        "kg/m3",
        "kg/mm",
        "mm2/s",
        "mPas",
        "h",
        "Mio",
        "Mio.",
        "m/s",
        "HV",
        "HB",
        "Proz.",
        "%",
        "(N/mm2).5",
        "N2/(m2K2s)",
        "N/um/mm",
        "psi",
        "um/m",
        "1/s",
    }
)
"""Single-token units printed by STplus; ``Grad C`` is handled as a two-token unit."""

_NUMBER = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")
_MARKER = re.compile(r"^[A-Za-z]{1,2}$")
_PAGE_BREAK = re.compile(r"^1\s+\*{10,}")
_DASHED = re.compile(r"^\s*-{20,}\s*$")
_SUBSECTION = re.compile(r"^\s*---\s+(?P<name>.+?)\s+-{3,}\s*$")
_HEADER_VERSION = re.compile(r"Stirnradprogramm STplus\s+(?P<version>[\w.]+?)\.?(?=\s)")
_COVER_VERSION = re.compile(r"^\s*Version:\s+(?P<version>[\w.]+)\s*$")

SYMBOLS: frozenset[str] = frozenset(
    {
        # basic data
        "alfa_n",
        "alfa_t",
        "alfa_wt",
        "beta",
        "beta_b",
        "z",
        "z2/z1",
        "a",
        "m_n",
        "m_t",
        "x_1+x_2",
        "x",
        "x*m_n",
        # pitches / contact ratios
        "p_t",
        "p_n",
        "p_et",
        "p_en",
        "p_x",
        "g",
        "h_*",
        "eps_alfa",
        "eps_beta",
        "eps_gamma",
        # widths / diameters
        "b",
        "b_gem",
        "d_w",
        "d",
        "d_b",
        "d_a",
        "d_Fa",
        "h_K",
        "d_Na",
        "d_Nf",
        "d_Ff",
        "c_n",
        "Fs_n",
        "d_Fs-n",
        "d_f",
        # heights / sliding
        "h_aP*",
        "h",
        "h_gem",
        "h_a",
        "c",
        "c_*",
        "g_alfa-a",
        "K_ga",
        "zeta_a",
        "zeta_f",
        # allowances / thicknesses
        "s_t",
        "A_ste",
        "A_sti",
        "s_n",
        "e_n",
        "s_an",
        # inspection dimensions
        "s_n-",
        "h_a-",
        "A_sne",
        "A_sni",
        "W_k",
        "k",
        "A_We",
        "A_Wi",
        "A_W/A_Sn",
        "M_dK",
        "M_dR",
        "D_M",
        "A_Mde",
        "A_Mdi",
        "A_Md/A_sn",
        "A_Ae",
        "A_Ai",
        # tool data
        "m_n0",
        "alfa_n0",
        "h_aP0*",
        "rho_aP0*",
        "h_FfP0*",
        "h_fP0*",
        "pr_0",
        "h_pr0*",
        "alfa_pr0",
        "q",
        "x_E",
        # load capacity general (kept for later stages)
        "z_g",
        "f_pe",
        "R_z-H",
        "R_z-F",
        "b_ges",
        "b/d",
        "d_s",
        "d_I",
        "P",
        "T",
        "F_t",
        "F_tw",
        "F_tb",
        "F_ax",
        "n",
        "v",
        "z_n",
        "my_mz",
        "X_L",
        "H_v",
        "P_VzP",
        "eta_zP",
        "K*",
        "U",
        "E",
        "nue",
        "alpha_Fan",
        "alpha_Fen",
        "s_fn*",
        "h_fa*",
        "h_fe*",
        "rho_f*",
        "d_sf",
        "t_a*",
        "t_e*",
        "h_a*",
        "h_e*",
    }
)
"""Symbols printed by STplus in the geometry and general blocks (extend explicitly when needed)."""


class StaValue(FrozenModel):
    section: str
    subsection: str | None
    label: str
    symbol: str | None
    tokens: tuple[str, ...]
    """Value tokens as printed (numbers, letters such as ``N``/``C``, separators ``/``)."""
    numbers: tuple[float, ...]
    unit: str | None
    line: int

    @property
    def key(self) -> str:
        """``symbol`` when registered, else the normalised label."""
        return self.symbol if self.symbol is not None else _label_key(self.label)


class StaReport(FrozenModel):
    version: str | None
    values: tuple[StaValue, ...]
    sections: tuple[str, ...]
    path: str | None = None

    def get(self, key: str, *, section: str | None = None) -> StaValue:
        """First value with ``key`` (symbol or label key), optionally restricted to a section prefix."""
        for value in self.values:
            if value.key == key and (section is None or value.section.startswith(section)):
                return value
        raise KeyError(f"no value {key!r}" + (f" in section {section!r}" if section else ""))

    def get_all(self, key: str) -> tuple[StaValue, ...]:
        return tuple(v for v in self.values if v.key == key)

    def symbols(self) -> set[str]:
        return {v.symbol for v in self.values if v.symbol is not None}


def _label_key(label: str) -> str:
    """Label without dot leaders (`` . . .``); abbreviation dots (``Zahnabm.``) are kept."""
    cleaned = re.sub(r"(\s+\.)+\s*$", "", label)
    cleaned = re.sub(r"(\s+\.){2,}", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _is_number(token: str) -> bool:
    return bool(_NUMBER.match(token))


def parse_sta(text: str, *, path: str | None = None) -> StaReport:
    """Parse the whole report into ``StaValue`` records (grammar only)."""
    version: str | None = None
    values: list[StaValue] = []
    sections: list[str] = []
    section: str | None = None
    subsection: str | None = None
    lines = text.splitlines()
    index = 0
    n = len(lines)
    while index < n:
        raw = lines[index]
        cover = _COVER_VERSION.match(raw)
        if cover and version is None:
            version = cover.group("version")
        if _PAGE_BREAK.match(raw):
            for offset in range(1, 4):
                if index + offset < n and version is None:
                    match = _HEADER_VERSION.search(lines[index + offset])
                    if match:
                        version = match.group("version")
            index += 4
            continue
        stripped = raw.strip()
        if _DASHED.match(raw):
            if index + 2 < n and _DASHED.match(lines[index + 2]) and lines[index + 1].strip():
                section = lines[index + 1].strip()
                subsection = None
                if section not in sections:
                    sections.append(section)
                index += 3
                continue
            index += 1
            continue
        sub = _SUBSECTION.match(raw)
        if sub:
            subsection = sub.group("name")
            index += 1
            continue
        if section is None or not stripped:
            index += 1
            continue
        parsed = _parse_value_line(stripped, index + 1, section, subsection)
        if parsed is not None:
            values.append(parsed)
        index += 1
    return StaReport(version=version, values=tuple(values), sections=tuple(sections), path=path)


def _parse_value_line(
    line: str, number: int, section: str, subsection: str | None
) -> StaValue | None:
    tokens = line.split()
    if len(tokens) < 2:
        return None
    unit: str | None = None
    if len(tokens) >= 2 and tokens[-2] == "Grad" and tokens[-1] == "C":
        unit = "Grad C"
        tokens = tokens[:-2]
    elif tokens[-1] in UNITS:
        unit = tokens[-1]
        tokens = tokens[:-1]
    # collect the value tail from the right: numbers, sign tokens, separators, 1–2 letter markers
    tail: list[str] = []
    while tokens:
        token = tokens[-1]
        if _is_number(token) or token in {"+", "-", "/"} or _MARKER.match(token):
            tail.insert(0, tokens.pop())
            continue
        break
    # a registered single-letter symbol at the left end of the tail is the symbol only if numbers follow
    symbol: str | None = None
    if tail and tail[0] in SYMBOLS and any(_is_number(t) for t in tail[1:]):
        symbol = tail.pop(0)
    elif tokens and tokens[-1] in SYMBOLS and any(_is_number(t) for t in tail):
        symbol = tokens.pop()
    if not tail and unit is None:
        return None  # pure text line (e.g. "Zahnradfertigung mit Fraeser oder Hobelkamm")
    label = " ".join(tokens)
    if not label and symbol is None:
        return None
    numbers = _numbers_from_tail(tail, number)
    return StaValue(
        section=section,
        subsection=subsection,
        label=label,
        symbol=symbol,
        tokens=tuple(tail),
        numbers=numbers,
        unit=unit,
        line=number,
    )


def _numbers_from_tail(tail: list[str], number: int) -> tuple[float, ...]:
    """Numbers from the tail; a lone sign token attaches to the following number (``+ 0.015``)."""
    out: list[float] = []
    pending_sign = ""
    for token in tail:
        if token in {"+", "-"}:
            if pending_sign:
                raise ParseError(f"line {number}: two consecutive sign tokens")
            pending_sign = token
            continue
        if _is_number(token):
            out.append(float(pending_sign + token))
            pending_sign = ""
            continue
        # separators and letter markers carry no number
    if pending_sign:
        raise ParseError(f"line {number}: dangling sign token")
    return tuple(out)


def load_sta(path: Path) -> StaReport:
    return parse_sta(path.read_text(encoding="latin-1"), path=str(path))


def geometry_block(report: StaReport) -> tuple[StaValue, ...]:
    """Values of the DIN 3960 geometry block(s)."""
    return tuple(v for v in report.values if v.section.startswith("Geometrieberechnung"))
