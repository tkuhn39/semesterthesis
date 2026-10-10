"""House style of the figures: layers against the LaTeX sources, fonts and the Greek-capable
symbol face, palette, black-and-white cycle, labels, captions, sizes, decimal comma and the
SVG/PNG output."""

import re
import warnings
from collections.abc import Iterator
from pathlib import Path

import pytest

from gearcore import plot_style
from gearcore.errors import InputRangeError

FZGDEF = plot_style.REPO_ROOT / "10_report" / "FZGdef.sty"
TUM_PRESENTATION = (
    plot_style.DEFAULT_FONT_FOLDER
    / "TUM_Latex"
    / "TUM_LaTex-Vorlagenpaket_gesamt"
    / "200805_TUM_LaTex-Vorlagenpaket"
    / "Ressourcen"
    / "Praesentation"
    / "Anfang.tex"
)
DEFINECOLOR = re.compile(r"\\definecolor\{(\w+)\}\{RGB\}\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}")


@pytest.fixture(autouse=True)
def _own_rcparams() -> Iterator[None]:
    """``apply`` writes the global rcParams; every test gets them back afterwards."""
    import matplotlib

    with matplotlib.rc_context():
        yield


def latex_colours(path: Path) -> dict[str, tuple[int, int, int]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        m.group(1): (int(m.group(2)), int(m.group(3)), int(m.group(4)))
        for m in DEFINECOLOR.finditer(text)
    }


def test_fzg_layer_overrides_tum_and_the_series_continue_with_the_extended_palette() -> None:
    style = plot_style.merged()
    assert style["colours"]["fzgblau"] == (0, 101, 189) == style["colours"]["tum_blau"]
    assert style["colours"]["tum_grau_20"] == (204, 204, 204) and "tumgrau" in style["colours"]
    assert style["palette"][0] == (0, 51, 89) and len(style["palette"]) == 8
    assert len(style["extended_palette"]) == 10
    series = style["series"]
    assert series[:8] == tuple(style["palette"]) and len(series) == len(set(series))
    assert (0, 119, 138) in series and len(series) >= 14
    assert plot_style.merged((plot_style.TUM,))["colours"].get("fzgblau") is None
    custom = plot_style.merged((plot_style.TUM, {"colours": {"tum_blau": (1, 2, 3)}}))
    assert custom["colours"]["tum_blau"] == (1, 2, 3)
    assert custom["series"] == tuple(plot_style.TUM["extended_palette"])


def test_fzg_values_are_the_ones_of_the_latex_template() -> None:
    defined = latex_colours(FZGDEF)
    for name, rgb in plot_style.FZG["colours"].items():
        assert defined[name] == rgb, name
    for index, rgb in enumerate(plot_style.FZG["palette"], start=1):
        assert defined[f"tumdiag{index}"] == rgb, index
    assert plot_style.TEXT_WIDTH_MM == 161.0  # FZGdasa.cls \textwidth


def test_tum_presentation_colours_match_the_tum_template() -> None:
    if not TUM_PRESENTATION.is_file():
        pytest.skip(f"TUM LaTeX template not available at {TUM_PRESENTATION}")
    defined = latex_colours(TUM_PRESENTATION)
    colours = plot_style.TUM["colours"]
    for tex_name, name in (
        ("TUMBlau", "tum_blau"),
        ("TUMBlauDunkel", "tum_blau_dunkel"),
        ("TUMBlauHell", "tum_blau_hell"),
        ("TUMBlauMittel", "tum_blau_mittel"),
        ("TUMElfenbein", "tum_elfenbein"),
        ("TUMGruen", "tum_gruen"),
        ("TUMOrange", "tum_orange"),
    ):
        assert defined[tex_name] == colours[name], tex_name


def test_apply_without_the_tum_files_falls_back_and_warns(tmp_path: Path) -> None:
    import matplotlib

    with pytest.warns(UserWarning, match="falling back"):
        sheet = plot_style.apply(font_folder_override=tmp_path)  # no font files: fallback
    assert sheet.font_family == matplotlib.rcParams["font.sans-serif"][0]
    assert "falling back" in sheet.font_note
    assert sheet.registered_fonts == ()
    families = matplotlib.rcParams["font.sans-serif"]
    fallback = list(plot_style.TUM["font_fallback"])
    assert (
        families and [f for f in fallback if f in families] == families
    )  # findable ones, in order
    assert "DejaVu Sans" in families  # bundled with matplotlib
    assert matplotlib.rcParams["font.family"] == matplotlib.rcParams["font.sans-serif"]
    assert matplotlib.rcParams["mathtext.fontset"] == "custom"
    assert matplotlib.rcParams["mathtext.rm"] == sheet.math_family
    assert matplotlib.rcParams["mathtext.it"] == f"{sheet.math_family}:italic"
    cycle = list(matplotlib.rcParams["axes.prop_cycle"])
    assert len(cycle) == 8 and cycle[0]["color"] == "#003359"
    assert len({str(entry["linestyle"]) for entry in cycle}) == 8
    assert len({entry["marker"] for entry in cycle}) == 8
    assert matplotlib.rcParams["lines.linewidth"] == 1.2
    assert matplotlib.rcParams["axes.linewidth"] == 0.6
    assert matplotlib.rcParams["grid.linewidth"] == 0.3
    assert matplotlib.rcParams["grid.color"] == "#cccccc"
    assert matplotlib.rcParams["axes.spines.top"] is False
    assert matplotlib.rcParams["svg.fonttype"] == "none"
    assert matplotlib.rcParams["savefig.format"] == "svg"
    assert matplotlib.rcParams["legend.shadow"] is False
    assert sheet.colour("fzgblau") == "#0065bd" and sheet.colour("diag3") == "#e37222"
    assert sheet.colour("grad1") == "#003359" and sheet.colour("tum_orange") == "#e37222"
    with pytest.raises(InputRangeError):
        sheet.colour("diag99")
    with pytest.raises(InputRangeError):
        sheet.colour("pink")


def test_tum_fonts_are_registered_once_and_symbols_get_a_greek_face() -> None:
    from matplotlib import font_manager

    folder = plot_style.font_folder()
    if not (folder / "TUMNeueHelvetica-Regular.ttf").is_file():
        pytest.skip(f"TUM Neue Helvetica not available at {folder}")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        sheet = plot_style.apply()
        count = len(font_manager.fontManager.ttflist)
        again = plot_style.apply()
    assert len(font_manager.fontManager.ttflist) == count  # the second call registers nothing
    assert sheet.registered_fonts and "Helvetica" in sheet.font_family
    assert sheet.font_note.startswith("TUM Neue Helvetica from")
    assert not plot_style.font_covers(folder / "TUMNeueHelvetica-Regular.ttf")
    assert sheet.math_family != sheet.font_family and "no Greek glyphs" in sheet.font_note
    assert again.math_family == sheet.math_family
    if plot_style.tex_gyre_heros_files():
        assert sheet.math_family == "TeX Gyre Heros"  # the Helvetica clone of the thesis template


def test_figure_sizes_follow_the_text_width() -> None:
    width, height = plot_style.figure_size("full")
    assert abs(width - 161.0 / 25.4) < 1.0e-9 and abs(height / width - 0.62) < 1.0e-9
    assert plot_style.figure_size("half")[0] == pytest.approx(78.0 / 25.4)
    assert plot_style.figure_size(100.0, aspect=1.0) == pytest.approx((100.0 / 25.4, 100.0 / 25.4))
    with pytest.raises(InputRangeError):
        plot_style.figure_size("huge")
    with pytest.raises(InputRangeError):
        plot_style.figure_size(5.0)
    with pytest.raises(InputRangeError):
        plot_style.figure_size("full", aspect=10.0)


def test_symbol_label_sets_subscripts_upright() -> None:
    assert plot_style.symbol_label("F_p", "µm") == r"$F_{\mathrm{p}}$ in µm"
    assert plot_style.symbol_label("f_H_alpha", "µm") == r"$f_{\mathrm{H}\alpha}$ in µm"
    assert plot_style.symbol_label("d_a") == r"$d_{\mathrm{a}}$"
    assert (
        plot_style.symbol_label("R_a", "µm", words="Rauheit") == r"Rauheit $R_{\mathrm{a}}$ in µm"
    )


def test_caption_after_the_citation_guideline() -> None:
    assert plot_style.caption("Zahnkontur") == "Zahnkontur"
    assert plot_style.caption("Zahnkontur", source="Rei23") == "Zahnkontur [Rei23]"
    assert (
        plot_style.caption("Zahnkontur", source="Rei23", relation="nach")
        == "Zahnkontur nach [Rei23]"
    )
    assert (
        plot_style.caption("Zahnkontur", source="Rei23", relation="in Anlehnung an", page="12")
        == "Zahnkontur in Anlehnung an [Rei23, S. 12]"
    )
    assert (
        plot_style.caption("Zahnkontur", source="Rei23", page="12") == "Zahnkontur [Rei23, S. 12]"
    )
    with pytest.raises(InputRangeError):
        plot_style.caption("Zahnkontur", relation="nach")


def test_german_number_and_plain_decimal() -> None:
    assert plot_style.german_number(1234.5, 1) == "1234,5"
    assert plot_style.german_number(0.0, 2) == "0,00"
    assert plot_style.german_number(-2.0, 0) == "-2"
    assert plot_style.german_number(-0.004, 2) == "0,00"
    assert plot_style.german_number(-0.5, 1) == "-0,5"
    assert plot_style.plain_decimal(1.5) == "1,5" and plot_style.plain_decimal(-2.5) == "-2,5"
    assert plot_style.plain_decimal(3.0) == "3" and plot_style.plain_decimal(-0.0) == "0"
    assert plot_style.plain_decimal(1.0e-5) == "0,00001"
    assert plot_style.plain_decimal(1234567.5) == "1234567,5"
    assert plot_style.plain_decimal(12345.678) == "12345,678"
    assert plot_style.plain_decimal(0.1 + 0.2) == "0,3"


def test_a_figure_renders_as_svg_with_text_greek_and_png(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # the TUM folder may be absent here
        plot_style.apply()
    figure, axes = plt.subplots(figsize=plot_style.figure_size("half"))
    axes.plot([0.0, 1.5, 3.0], [0.0, 1.0, 0.5], label=plot_style.symbol_label("F_p", "µm"))
    axes.set_xlabel(plot_style.symbol_label("d_a", "mm"))
    axes.set_ylabel(plot_style.symbol_label("f_H_alpha", "µm"))
    axes.set_title("σ₁ als Text")  # plain Greek and subscript: taken from the next family
    plot_style.decimal_comma(axes, which="x")
    axes.legend()
    written = plot_style.save(figure, tmp_path / "bild")
    plt.close(figure)
    assert [p.suffix for p in written] == [".svg", ".png"]
    svg = written[0].read_text(encoding="utf-8")
    assert "<text" in svg and "1,5" in svg  # text kept as text, decimal comma on the axis
    assert "α" in svg and "µ" in svg  # Greek and micro as characters, not glyph codes
    assert "cmmi10" not in svg and "®" not in svg  # no Computer Modern fallback
    assert written[1].stat().st_size > 1000


def test_legend_outside_reserves_room_and_overlaps_are_detected(tmp_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        plot_style.apply()
    x = [0.0, 1.0, 2.0, 3.0, 4.0]
    # a legend inside the axes on top of the data is found
    figure, axes = plt.subplots(figsize=plot_style.figure_size("half"))
    axes.plot(x, [4.0, 4.0, 4.0, 4.0, 4.0], label="oben")
    axes.plot(x, [0.0, 0.0, 0.0, 0.0, 0.0], label="unten")
    axes.legend(loc="upper left")
    overlaps = plot_style.legend_overlaps(figure)
    assert overlaps and "oben" in overlaps[0]
    with pytest.warns(UserWarning, match="covers"):
        plot_style.save(figure, tmp_path / "ueberlappt", formats=("png",))
    assert plot_style.save(figure, tmp_path / "ohne", formats=("png",), check_overlaps=False)
    plt.close(figure)
    # the same data with the legend outside: clean, and the figure still holds both lines
    figure, axes = plot_style.new_figure("half", rows=2, sharex=True)
    axes[0].plot(x, [4.0, 4.0, 4.0, 4.0, 4.0], label="oben")
    axes[1].plot(x, [0.0, 0.0, 0.0, 0.0, 0.0], label="unten")
    legend = plot_style.legend_outside(figure, where="top")
    assert [t.get_text() for t in legend.get_texts()] == ["oben", "unten"]
    assert plot_style.legend_overlaps(figure) == []
    figure.suptitle("Titel")  # a suptitle meets a legend above the axes
    assert any("title" in line for line in plot_style.legend_overlaps(figure))
    legend.remove()
    legend = plot_style.legend_outside(figure, where="bottom")
    assert plot_style.legend_overlaps(figure) == []
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        written = plot_style.save(figure, tmp_path / "aussen")
    assert [w.suffix for w in written] == [".svg", ".png"]
    figure.canvas.draw()
    assert legend.get_window_extent().y1 < axes[1].get_window_extent().y0  # below the axes
    plt.close(figure)
    figure, axes = plot_style.new_figure("half")
    axes.plot(x, x, label="rechts")
    right = plot_style.legend_outside(figure, axes, where="right")
    figure.canvas.draw()
    assert right.get_window_extent().x0 > axes.get_window_extent().x1
    plt.close(figure)
    figure, axes = plot_style.new_figure("half")
    axes.plot(x, x, label="daneben")
    beside = plot_style.legend_beside(axes)
    figure.canvas.draw()
    assert beside.get_window_extent().x0 >= axes.get_window_extent().x1
    assert plot_style.legend_overlaps(figure) == []
    plt.close(figure)
    figure, axes = plot_style.new_figure("half")
    axes.plot(x, x)
    with pytest.raises(InputRangeError):
        plot_style.legend_outside(figure)
    with pytest.raises(InputRangeError):
        plot_style.legend_outside(figure, axes, where="bottom")
    plt.close(figure)
