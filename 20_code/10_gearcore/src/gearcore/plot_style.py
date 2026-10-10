"""House style of every figure the scripts draw: FZG guideline first, TUM corporate design where
the FZG says nothing (standing rule of the user, 2026-10-10).

Two layers, applied in order. ``TUM`` holds the corporate design as the user quoted it from the
TUM style guide on 2026-10-10 (primary colours blue, black, white; secondary blues; greys as 80,
50 and 20 % black; accent colours; the extended palette for diagrams and infographics; the
typeface TUM Neue Helvetica, Arial as the system alternative; line widths doubling from 0,3 pt;
no 3D effects or shadows; gradations of one colour before many colours; a graphic is a reduced
display of data, Tufte's data-ink ratio). ``FZG`` overrides it with what the FZG template of the
thesis defines (``FZGdef.sty``, the chair's original in
``30_references_and_examples/94_BASAMA_LaTeX`` and the user's copy in ``10_report`` agree:
``fzgblau``, ``tumblau``, ``tumgrau`` and the diagram palette ``tumdiag1`` to ``tumdiag8``;
``FZGdasa.cls``: captions small with a bold label, text width 161 mm). The FZG guidelines in
``10_report`` add rules for captions and formulas: a figure from a source names it in square
brackets, "nach [..]" when slightly changed, "in Anlehnung an [..]" when substantially changed,
with the page where useful (FZG-Zitierrichtlinie §2.12); symbols italic, subscripts and units
upright, every symbol in the nomenclature at the beginning (Formeln in wissenschaftlichen
Arbeiten, DIN 1338).

Decisions of the user (2026-10-10): series colours = the FZG palette first, the TUM extended
palette when more are needed; every series also gets its own line style and marker so the figure
reads in black-and-white print; the thesis figures are SVG with text kept as text (the typeface is
referenced, not outlined, so it can be exchanged later without redrawing) plus a PNG preview; the
thesis uses TUM Neue Helvetica (the template's ``phv`` is LaTeX's Helvetica clone).

Symbols are mathtext, and mathtext needs a face with Greek glyphs (f_Hα, ε_α, ρ): the TUM Neue
Helvetica files carry none, so ``apply`` renders mathtext in the first fallback face that does
and says so in ``font_note``; the SVG then holds the Greek letters as characters, not as glyph
codes of a Computer Modern face. The first fallback is TeX Gyre Heros, the Helvetica clone the
thesis template sets its text in (``phv``), taken from the TeX Live installation through
``kpsewhich`` (user's wish of 2026-10-10: closer to the TUM typeface than Arial); then Arial,
Helvetica, DejaVu Sans (bundled with matplotlib).

matplotlib is a development dependency, so it is imported inside the functions; the module
itself imports nothing of it. The TUM Neue Helvetica files live in
``30_references_and_examples/99_TUM_Corporate_Design`` (gitignored, licensed); where they are
absent the style falls back to Arial or Helvetica, warns, and says so in ``StyleSheet.font_note``.
``font.family`` names the families explicitly, so that a glyph the TUM face lacks (a Greek
letter or a subscript digit in plain text) is taken from the next family instead of a box.
The TUM values without a file in the repository (greys, extended palette, font sizes, the 0,3 pt
rule) are the user's quotation of the style guide; the FZG values and the TUM presentation colours
are read from the LaTeX files and pinned by the tests.
"""

import os
import shutil
import subprocess
import warnings
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from gearcore.errors import InputRangeError
from gearcore.quantities import latex

REPO_ROOT = Path(__file__).resolve().parents[4]
"""The repository (``src/gearcore/plot_style.py`` lies four levels below it)."""
FONT_FOLDER_ENV = "GEARCORE_TUM_FONTS"
DEFAULT_FONT_FOLDER = REPO_ROOT / "30_references_and_examples" / "99_TUM_Corporate_Design"
TEXT_WIDTH_MM = 161.0
"""``\\textwidth`` of the thesis template (``FZGdasa.cls``)."""
MM_PER_INCH = 25.4
GREEK_PROBE = "αβεμρσ"
"""Characters a mathtext face must have (Greek subscripts and symbols of the registry)."""

Rgb = tuple[int, int, int]
LineStyle = str | tuple[float, tuple[float, ...]]
Relation = Literal["nach", "in Anlehnung an"]

TUM: dict[str, Any] = {
    "font_files": (
        "TUMNeueHelvetica-Regular.ttf",
        "TUMNeueHelvetica-Bold.ttf",
        "TUMNeueHelvetica-Italic.ttf",
        "TUMNeueHelvetica-BoldItalic.ttf",
    ),
    "font_fallback": ("TeX Gyre Heros", "Arial", "Helvetica", "DejaVu Sans"),
    "tex_gyre_files": (
        "texgyreheros-regular.otf",
        "texgyreheros-bold.otf",
        "texgyreheros-italic.otf",
        "texgyreheros-bolditalic.otf",
    ),
    "colours": {
        # primary
        "tum_blau": (0, 101, 189),
        "tum_schwarz": (0, 0, 0),
        "tum_weiss": (255, 255, 255),
        # secondary
        "tum_blau_dunkel": (0, 82, 147),
        "tum_blau_dunkler": (0, 51, 89),
        "tum_grau_80": (51, 51, 51),
        "tum_grau_50": (128, 128, 128),
        "tum_grau_20": (204, 204, 204),
        # accents (orange and green never together to tell series apart: red-green deficiency)
        "tum_elfenbein": (218, 215, 203),
        "tum_orange": (227, 114, 34),
        "tum_gruen": (162, 173, 0),
        "tum_blau_hell": (152, 198, 234),
        "tum_blau_mittel": (100, 160, 200),
    },
    # ordered gradation of the brand colour for series of one kind (the TUM diagram examples)
    "gradation": ((0, 51, 89), (0, 82, 147), (0, 101, 189), (100, 160, 200), (152, 198, 234)),
    # extended palette for diagrams and infographics only, never in the layout
    "extended_palette": (
        (105, 8, 90),
        (15, 27, 95),
        (0, 119, 138),
        (0, 124, 48),
        (103, 154, 29),
        (255, 220, 0),
        (249, 186, 0),
        (214, 76, 19),
        (196, 7, 27),
        (156, 13, 22),
    ),
    "line_widths_pt": (0.3, 0.6, 1.2),
    "font_size": 9.0,
    "title_size": 10.0,
    "legend_size": 8.0,
    "dpi": 160,
    "png_dpi": 300,
}
"""TUM corporate design as quoted by the user (2026-10-10) and the TUM LaTeX template
(``99_TUM_Corporate_Design/TUM_Latex``, ``Ressourcen/Praesentation/Anfang.tex``: TUMBlau,
TUMBlauDunkel, TUMBlauHell, TUMBlauMittel, TUMElfenbein, TUMGruen, TUMOrange)."""

FZG: dict[str, Any] = {
    "colours": {
        "fzgblau": (0, 101, 189),
        "tumblau": (0, 101, 189),
        "tumgrau": (218, 215, 203),
    },
    # the diagram palette of the FZG template (FZGdef.sty tumdiag1 to tumdiag8), used first
    "palette": (
        (0, 51, 89),
        (100, 160, 200),
        (227, 114, 34),
        (162, 173, 0),
        (156, 13, 22),
        (105, 8, 90),
        (103, 154, 29),
        (249, 186, 0),
    ),
    # captions of the LaTeX template (FZGdasa.cls: captionsetup font=small, labelfont=bf,
    # format=hang); used by the thesis output, not by matplotlib
    "caption": {"font": "small", "label": "bold", "format": "hang"},
    "text_width_mm": TEXT_WIDTH_MM,
}
"""What the FZG template defines itself (``10_report/FZGdef.sty`` lines 133 to 146,
``FZGdasa.cls``); everything it does not define comes from ``TUM``."""

LINE_STYLES: tuple[LineStyle, ...] = (
    "-",
    "--",
    ":",
    "-.",
    (0.0, (10.0, 3.0)),  # long dashes
    (0.0, (5.0, 1.5, 1.0, 1.5, 1.0, 1.5)),  # dash, dot, dot
    (0.0, (1.0, 3.0)),  # sparse dots
    (0.0, (10.0, 3.0, 2.0, 3.0)),  # long dash, dot
)
MARKERS: tuple[str, ...] = ("o", "s", "^", "D", "v", "P", "X", "*")
"""Eight distinct line styles and markers cycled with the colours, so every series differs in
black-and-white print even where two palette colours share a grey value (tumdiag1 and 5, 3 and 7)."""


@dataclass(frozen=True)
class StyleSheet:
    """The resolved style after ``apply``."""

    font_family: str
    """The family matplotlib uses first (``'TUM Neue Helvetica'`` or the fallback)."""
    font_note: str
    """Where the typeface came from, or why the fallback is in use; which face draws the symbols."""
    math_family: str
    """The face of the mathtext symbols: ``font_family`` where it has Greek glyphs, else the first
    fallback that has them."""
    colours: Mapping[str, Rgb]
    palette: tuple[Rgb, ...]
    """Series colours in order: the FZG palette, then the TUM extended palette."""
    gradation: tuple[Rgb, ...]
    registered_fonts: tuple[str, ...] = field(default_factory=tuple)

    def colour(self, name: str) -> str:
        """Hex colour of a named colour (``'fzgblau'``, ``'tum_orange'``), of ``'diagN'`` (N-th
        series colour) or of ``'gradN'`` (N-th step of the blue gradation)."""
        for prefix, table in (("diag", self.palette), ("grad", self.gradation)):
            if name.startswith(prefix) and name[len(prefix) :].isdigit():
                index = int(name[len(prefix) :])
                if not 1 <= index <= len(table):
                    raise InputRangeError(f"{name!r}: the table has {len(table)} colours")
                return hex_colour(table[index - 1])
        if name not in self.colours:
            raise InputRangeError(f"unknown colour {name!r}; known: {sorted(self.colours)}")
        return hex_colour(self.colours[name])


def hex_colour(rgb: Rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def merged(layers: Sequence[Mapping[str, Any]] = (TUM, FZG)) -> dict[str, Any]:
    """The layers merged in order, later layers overriding (colour maps merge by key). The
    series palette is the ``palette`` of the layers, continued by the ``extended_palette``
    without repeating a colour."""
    out: dict[str, Any] = {}
    for layer in layers:
        for key, value in layer.items():
            if key == "colours":
                colours = dict(out.get("colours", {}))
                colours.update(value)
                out["colours"] = colours
            else:
                out[key] = value
    series: list[Rgb] = [tuple(c) for c in out.get("palette", ())]
    for colour in out.get("extended_palette", ()):
        if tuple(colour) not in series:
            series.append(tuple(colour))
    out["series"] = tuple(series)
    return out


def font_folder() -> Path:
    return Path(os.environ.get(FONT_FOLDER_ENV, DEFAULT_FONT_FOLDER))


def tex_gyre_heros_files() -> tuple[Path, ...]:
    """The TeX Gyre Heros OpenType files of a TeX Live installation (``kpsewhich``), or none."""
    kpsewhich = shutil.which("kpsewhich")
    if kpsewhich is None:
        return ()
    found: list[Path] = []
    for file_name in merged()["tex_gyre_files"]:
        try:
            result = subprocess.run(
                [kpsewhich, file_name], capture_output=True, text=True, timeout=30.0, check=False
            )
        except (OSError, subprocess.SubprocessError):
            return ()
        path = Path(result.stdout.strip())
        if result.returncode == 0 and path.is_file():
            found.append(path)
    return tuple(found)


def _register(paths: Iterable[Path]) -> tuple[str, ...]:
    from matplotlib import font_manager

    known = {Path(entry.fname).resolve() for entry in font_manager.fontManager.ttflist}
    names: list[str] = []
    for path in paths:
        if path.resolve() not in known:
            font_manager.fontManager.addfont(str(path))
        names.append(font_manager.FontProperties(fname=str(path)).get_name())
    return tuple(dict.fromkeys(names))


def register_fonts(folder: Path | None = None) -> tuple[str, ...]:
    """Register the TUM Neue Helvetica files with matplotlib (once per file); returns the family
    names found. The TeX Gyre Heros files of TeX Live are registered as well, so that the
    symbol face is available, but they are not among the names returned."""
    base = font_folder() if folder is None else Path(folder)
    paths = [base / file_name for file_name in merged()["font_files"]]
    _register(tex_gyre_heros_files())
    return _register(path for path in paths if path.is_file())


def font_covers(path: Path, characters: str = GREEK_PROBE) -> bool:
    """Whether the font file has a glyph for every character."""
    from matplotlib.ft2font import FT2Font

    font = FT2Font(str(path))
    return all(font.get_char_index(ord(c)) != 0 for c in characters)


def _findable(family: str) -> bool:
    """Whether matplotlib finds a face of the family (a family it cannot find in the explicit
    ``font.family`` list makes it log a warning at every draw)."""
    from matplotlib import font_manager

    try:
        font_manager.findfont(font_manager.FontProperties(family=family), fallback_to_default=False)
    except ValueError:
        return False
    return True


def math_family(candidates: Sequence[str]) -> str:
    """The first family matplotlib finds whose regular face covers ``GREEK_PROBE``; DejaVu Sans
    (bundled with matplotlib) where none does."""
    from matplotlib import font_manager

    for name in candidates:
        try:
            path = font_manager.findfont(
                font_manager.FontProperties(family=name), fallback_to_default=False
            )
        except ValueError:
            continue
        if font_covers(Path(path)):
            return name
    return "DejaVu Sans"


def apply(*, font_folder_override: Path | None = None) -> StyleSheet:
    """Set matplotlib's rcParams to the house style and return what was resolved; warns where
    the TUM typeface is missing."""
    import matplotlib
    from cycler import cycler

    style = merged()
    registered = register_fonts(font_folder_override)
    fallback = tuple(style["font_fallback"])
    folder = font_folder_override or font_folder()
    fallback = tuple(name for name in fallback if _findable(name))
    if registered:
        family = registered[0]
        note = f"TUM Neue Helvetica from {folder}"
        families = (family, *fallback)
    else:
        family = fallback[0]
        note = f"TUM Neue Helvetica not found in {folder}; falling back to {', '.join(fallback)}"
        families = fallback
        warnings.warn(note, stacklevel=2)
    symbols = math_family(families)
    if symbols != family:
        note += f"; symbols (mathtext) in {symbols}: {family} has no Greek glyphs"
    series = tuple(style["series"])
    count = len(LINE_STYLES)
    thin, medium, thick = style["line_widths_pt"]
    colours = style["colours"]
    matplotlib.rcParams.update(
        {
            # the explicit list, not the alias: matplotlib takes a missing glyph (Greek,
            # subscript digits) from the next family only when the families are named here
            "font.family": list(families),
            "font.sans-serif": list(families),
            "font.size": style["font_size"],
            "axes.titlesize": style["title_size"],
            "axes.labelsize": style["font_size"],
            "xtick.labelsize": style["font_size"] - 1.0,
            "ytick.labelsize": style["font_size"] - 1.0,
            "legend.fontsize": style["legend_size"],
            "legend.frameon": False,
            "legend.handlelength": 2.8,
            "figure.dpi": style["dpi"],
            "savefig.dpi": style["png_dpi"],
            "savefig.format": "svg",
            "svg.fonttype": "none",  # text stays text: the typeface can be exchanged later
            # series: colour, line style and marker cycle together (readable in black and white)
            "axes.prop_cycle": (
                cycler(color=[hex_colour(c) for c in series[:count]])
                + cycler(linestyle=list(LINE_STYLES))
                + cycler(marker=list(MARKERS))
            ),
            "lines.linewidth": thick,
            "lines.markersize": 3.5,
            "lines.markeredgewidth": medium,
            "patch.linewidth": medium,
            "axes.linewidth": medium,
            "xtick.major.width": medium,
            "ytick.major.width": medium,
            "xtick.minor.width": thin,
            "ytick.minor.width": thin,
            # Tufte: no frame on top and right, a light grid of the lightest grey
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": hex_colour(colours["tum_grau_20"]),
            "grid.linewidth": thin,
            "axes.edgecolor": hex_colour(colours["tum_schwarz"]),
            "axes.labelcolor": hex_colour(colours["tum_schwarz"]),
            "text.color": hex_colour(colours["tum_schwarz"]),
            "legend.shadow": False,
            "legend.fancybox": False,
            # symbols in italics, subscripts and units upright: mathtext in a face with Greek
            "mathtext.fontset": "custom",
            "mathtext.rm": symbols,
            "mathtext.it": f"{symbols}:italic",
            "mathtext.bf": f"{symbols}:bold",
            "mathtext.default": "it",
            "axes.formatter.use_locale": False,
        }
    )
    return StyleSheet(
        font_family=family,
        font_note=note,
        math_family=symbols,
        colours=dict(colours),
        palette=series,
        gradation=tuple(tuple(c) for c in style["gradation"]),
        registered_fonts=registered,
    )


def figure_size(width: float | str = "full", aspect: float = 0.62) -> tuple[float, float]:
    """Figure size in inches for the thesis: ``'full'`` = the text width (161 mm), ``'half'``
    = one of two side by side (78 mm, 5 mm between), ``'third'`` = one of three (50 mm), or a
    width in mm; ``aspect`` = height / width."""
    if isinstance(width, str):
        widths = {"full": TEXT_WIDTH_MM, "half": 78.0, "third": 50.0}
        if width not in widths:
            raise InputRangeError(f"figure width {width!r}; known: {sorted(widths)} or mm")
        width_mm = widths[width]
    else:
        width_mm = float(width)
        if not 10.0 <= width_mm <= 400.0:
            raise InputRangeError(f"figure width {width!r} mm lies outside 10 to 400 mm")
    if not 0.1 <= aspect <= 3.0:
        raise InputRangeError(f"aspect {aspect!r} lies outside 0,1 to 3")
    return width_mm / MM_PER_INCH, width_mm * aspect / MM_PER_INCH


def german_number(value: float, digits: int) -> str:
    """``1234.5`` with one digit → ``'1234,5'`` (decimal comma, no thousands separator); a value
    that prints as zero loses its sign (``-0.004`` with two digits → ``'0,00'``)."""
    text = f"{value:.{digits}f}"
    if text.lstrip("-").strip("0.") == "":
        text = text.lstrip("-")
    return text.replace(".", ",")


def plain_decimal(value: float) -> str:
    """Positional decimal text without exponent and without trailing zeros, up to twelve
    decimals (tick values): ``1e-05`` → ``'0,00001'``, ``1234567.5`` → ``'1234567,5'``,
    ``0.1 + 0.2`` → ``'0,3'``, ``-0.0`` → ``'0'``."""
    text = f"{value:.12f}".rstrip("0").rstrip(".")
    if text in ("", "-", "-0"):
        return "0"
    return text.replace(".", ",")


def decimal_comma(axes: Any, *, digits: int | None = None, which: str = "both") -> None:
    """Tick labels of ``axes`` with a decimal comma; ``digits`` fixes the decimals, else the
    ticks decide (integers without a comma, no exponent notation)."""
    from matplotlib.ticker import FuncFormatter

    def label(value: float, _position: float) -> str:
        if digits is not None:
            return german_number(value, digits)
        return plain_decimal(value)

    formatter = FuncFormatter(label)
    if which in ("x", "both"):
        axes.xaxis.set_major_formatter(formatter)
    if which in ("y", "both"):
        axes.yaxis.set_major_formatter(formatter)


def new_figure(
    width: float | str = "full",
    aspect: float = 0.62,
    *,
    rows: int = 1,
    cols: int = 1,
    sharex: bool = False,
    sharey: bool = False,
) -> tuple[Any, Any]:
    """A figure of the thesis size with the constrained layout engine, so that legends placed
    outside the axes (``legend_outside``) and titles get their own room instead of covering
    data; returns ``(figure, axes)`` as ``pyplot.subplots`` does."""
    import matplotlib.pyplot as plt

    return plt.subplots(
        rows,
        cols,
        figsize=figure_size(width, aspect),
        sharex=sharex,
        sharey=sharey,
        layout="constrained",
    )


def legend_outside(
    figure: Any,
    source: Any = None,
    *,
    where: str = "top",
    ncol: int | None = None,
    **kwargs: Any,
) -> Any:
    """A figure legend outside the axes: ``where`` ``'bottom'`` (centred below the axes, the
    place for a figure with a suptitle), ``'top'`` (centred above; it collides with a suptitle,
    which ``legend_overlaps`` reports) or ``'right'`` (one column beside the axes). The handles
    come from ``source`` (an axes) or from every axes of the figure. Needs the constrained
    layout of ``new_figure``: the engine reserves the room, so the legend never covers data."""
    if where not in ("bottom", "top", "right"):
        raise InputRangeError(f"where must be 'bottom', 'top' or 'right', got {where!r}")
    axes_list = [source] if source is not None else list(figure.axes)
    handles: list[Any] = []
    labels: list[str] = []
    for axes in axes_list:
        for handle, label in zip(*axes.get_legend_handles_labels(), strict=True):
            if label not in labels:
                handles.append(handle)
                labels.append(label)
    if not handles:
        raise InputRangeError("no labelled artist for the legend")
    if where in ("bottom", "top"):
        columns = ncol if ncol is not None else min(len(labels), 4)
        location = "outside lower center" if where == "bottom" else "outside upper center"
        return figure.legend(handles, labels, loc=location, ncol=columns, **kwargs)
    return figure.legend(handles, labels, loc="outside center right", ncol=ncol or 1, **kwargs)


def legend_beside(axes: Any, **kwargs: Any) -> Any:
    """The legend of one axes to the right of it, outside the data; with the constrained layout
    of ``new_figure`` the axes shrinks to make room. For figures with several axes whose series
    differ (``legend_outside`` would merge them)."""
    return axes.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0, **kwargs)


def legend_overlaps(figure: Any) -> list[str]:
    """Legends of the figure that cover plotted data or text: for every legend (of an axes or
    of the figure) the lines, scatter points and patches of every axes whose display-space
    points fall inside the legend box, and the titles of the figure and of the axes whose box
    meets it. Returns one line of text per overlap (empty when clean)."""
    import numpy as np

    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    legends = list(figure.legends)
    legends += [axes.get_legend() for axes in figure.axes if axes.get_legend() is not None]
    found: list[str] = []
    titles = [text for text in figure.texts if text.get_text()]
    titles += [axes.title for axes in figure.axes if axes.get_title()]
    for legend in legends:
        box = legend.get_window_extent(renderer)
        for title in titles:
            if title.get_window_extent(renderer).overlaps(box):
                found.append(f"{_describe(legend)} meets the title {title.get_text()!r}")
        for axes in figure.axes:
            clip = axes.get_window_extent(renderer)
            artists = list(axes.lines) + list(axes.collections) + list(axes.patches)
            for artist in artists:
                if hasattr(artist, "get_xydata"):
                    points = np.asarray(artist.get_xydata(), dtype=float)
                elif hasattr(artist, "get_offsets"):
                    points = np.asarray(artist.get_offsets(), dtype=float)
                else:
                    corners = artist.get_window_extent(renderer)
                    points = np.array(
                        [[corners.x0, corners.y0], [corners.x1, corners.y1]], dtype=float
                    )
                    inside = (
                        corners.overlaps(box)
                        and corners.width > 0.0
                        and corners.height > 0.0
                        and corners.width * corners.height < 0.9 * clip.width * clip.height
                    )
                    if inside:
                        found.append(f"{_describe(legend)} covers a patch of axes {_title(axes)}")
                    continue
                if points.size == 0:
                    continue
                if hasattr(artist, "get_xydata"):
                    points = axes.transData.transform(points[np.isfinite(points).all(axis=1)])
                elif getattr(artist, "get_offset_transform", None) is not None:
                    points = artist.get_offset_transform().transform(points)
                hits = (
                    (points[:, 0] >= box.x0)
                    & (points[:, 0] <= box.x1)
                    & (points[:, 1] >= box.y0)
                    & (points[:, 1] <= box.y1)
                    & (points[:, 0] >= clip.x0)
                    & (points[:, 0] <= clip.x1)
                    & (points[:, 1] >= clip.y0)
                    & (points[:, 1] <= clip.y1)
                )
                if hits.any():
                    label = artist.get_label() if hasattr(artist, "get_label") else "?"
                    found.append(
                        f"{_describe(legend)} covers {int(hits.sum())} points of {label!r} "
                        f"in axes {_title(axes)}"
                    )
    return found


def _describe(legend: Any) -> str:
    texts = [t.get_text() for t in legend.get_texts()]
    return "legend (" + ", ".join(texts[:3]) + (", …" if len(texts) > 3 else "") + ")"


def _title(axes: Any) -> str:
    return repr(axes.get_title() or axes.get_ylabel() or "?")


def save(
    figure: Any,
    stem: Path,
    formats: Iterable[str] = ("svg", "png"),
    *,
    check_overlaps: bool = True,
) -> list[Path]:
    """Write the figure as ``<stem>.svg`` (text as text) and ``<stem>.png`` (preview, 300 dpi);
    returns the paths written, with the axis labels of all axes aligned on one line. Warns
    (``UserWarning``) when a legend covers plotted data, so the tests, which turn warnings into
    errors, refuse such a figure."""
    if check_overlaps:
        overlaps = legend_overlaps(figure)
        if overlaps:
            warnings.warn(f"{Path(stem).name}: " + "; ".join(overlaps), stacklevel=2)
    figure.align_labels()  # axis labels of stacked or side-by-side axes on one line (user, 2026-10-10)
    written: list[Path] = []
    for extension in formats:
        path = Path(stem).with_suffix(f".{extension}")
        path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(path, format=extension)
        written.append(path)
    return written


def symbol_label(symbol: str, unit: str | None = None, *, words: str | None = None) -> str:
    """Axis or legend label with the symbol in italics and its subscripts upright (the registry
    notation ``F_p``, ``f_H_alpha`` gives mathtext through ``gearcore.quantities.latex``), the unit
    upright after "in": ``symbol_label('F_p', 'µm')`` → ``'$F_{\\mathrm{p}}$ in µm'``."""
    label = f"${latex(symbol)}$"
    if words:
        label = f"{words} {label}"
    return f"{label} in {unit}" if unit else label


def caption(
    text: str,
    *,
    source: str | None = None,
    relation: Relation | None = None,
    page: str | None = None,
) -> str:
    """Figure caption after the FZG citation guideline §2.12: a figure from a source carries the
    source in square brackets at the end, ``relation`` "nach" when the figure was slightly
    changed, "in Anlehnung an" when substantially changed; ``page`` adds ", S. <page>"."""
    if source is None:
        if relation is not None or page is not None:
            raise InputRangeError("a relation or a page needs a source")
        return text
    reference = f"[{source}, S. {page}]" if page else f"[{source}]"
    return f"{text} {relation} {reference}" if relation else f"{text} {reference}"


__all__ = [
    "DEFAULT_FONT_FOLDER",
    "FONT_FOLDER_ENV",
    "FZG",
    "GREEK_PROBE",
    "LINE_STYLES",
    "MARKERS",
    "TEXT_WIDTH_MM",
    "TUM",
    "StyleSheet",
    "apply",
    "caption",
    "decimal_comma",
    "figure_size",
    "font_covers",
    "font_folder",
    "german_number",
    "hex_colour",
    "legend_beside",
    "legend_outside",
    "legend_overlaps",
    "math_family",
    "merged",
    "new_figure",
    "plain_decimal",
    "register_fonts",
    "save",
    "symbol_label",
    "tex_gyre_heros_files",
]
