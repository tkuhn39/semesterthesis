"""The thesis builders (T2, T3, T5): the symbol rendering and the scan of the nomenclature
generator, the Citavi parser and the key rules of the bibliography generator, the listing
rules of the figure build."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from gearcore.errors import InputRangeError

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def nomenclature() -> ModuleType:
    return _load("build_nomenclature")


@pytest.fixture(scope="module")
def bibliography() -> ModuleType:
    return _load("build_bibliography")


@pytest.fixture(scope="module")
def figures() -> ModuleType:
    return _load("build_thesis_figures")


@pytest.mark.parametrize(
    ("symbol", "latex"),
    [
        ("z", "z"),
        ("m_n", "m_{\\mathrm{n}}"),
        ("alpha_n", "\\alpha_{\\mathrm{n}}"),
        ("rho_aP0", "\\rho_{\\mathrm{aP0}}"),
        ("sigma_V_Mises", "\\sigma_{\\mathrm{V,Mises}}"),
        ("a_B_V", "a_{\\mathrm{B,V}}"),
        ("f_H_alpha", "f_{\\mathrm{H}\\alpha}"),
        ("E_W*", "E_{\\mathrm{W}}^{*}"),
        ("sigma'_W", "\\sigma'_{\\mathrm{W}}"),
        ("epsilon_alpha", "\\varepsilon_{\\alpha}"),
        ("phi", "\\varphi"),
        ("a/b", "a/b"),
        ("s_ns/s_ni", "s_{\\mathrm{ns}}/s_{\\mathrm{ni}}"),
        ("Sigma x", "\\Sigma x"),
        ("inv", "\\mathrm{inv}"),
    ],
)
def test_symbol_to_latex(nomenclature: ModuleType, symbol: str, latex: str) -> None:
    assert nomenclature.symbol_to_latex(symbol) == latex


def test_symbol_to_latex_refuses_empty(nomenclature: ModuleType) -> None:
    with pytest.raises(InputRangeError):
        nomenclature.symbol_to_latex(" ")


def test_scan_reports_symbols_without_a_row(nomenclature: ModuleType, tmp_path: Path) -> None:
    tex = tmp_path / "kap.tex"
    tex.write_text(
        "Die Spannung $\\sigma_{\\mathrm{F}}$ folgt aus $m_{\\mathrm{n}}$ und $z$; % $x$ im Kommentar\n"
        "\\begin{equation} a_{\\mathrm{B,V}} = \\frac{\\sigma_{\\mathrm{a}}}{K_{\\mathrm{B}}} \\end{equation}\n"
        "Einheit $\\mathrm{mm}$ zählt nicht.\n",
        encoding="utf-8",
    )
    rows = [
        nomenclature.Row("m_n", "m_{\\mathrm{n}}", "mm", "Normalmodul", ""),
        nomenclature.Row("a_B_V", "a_{\\mathrm{B,V}}", "-", "Auslastung", ""),
        nomenclature.Row("sigma_a", "\\sigma_{\\mathrm{a}}", "MPa", "Amplitude", ""),
    ]
    missing = nomenclature.scan([tex], nomenclature.known_symbols(rows))
    assert set(missing) == {"sigma_F", "z", "K_B"}
    assert missing["z"] == ["kap.tex"]


def test_unit_and_designation_rendering(nomenclature: ModuleType) -> None:
    assert nomenclature._unit("deg") == "\\textdegree "
    assert nomenclature._unit("-") == "--"
    assert nomenclature._tex("Grenzlastspielzahl = 10^7") == "Grenzlastspielzahl = $10^{7}$"
    assert nomenclature._tex("R_11 & 5 %") == "R\\_11 \\& 5 \\%"


def test_bib_parser_and_key_rules(bibliography: ModuleType) -> None:
    text = (
        "% Citavi\n\n"
        "@book{Sto18,\n author = {Stommel, M. and Stojek, M. and Korte, W.},\n year = {2018},\n"
        " title = {FEM zur Berechnung von {Kunststoff-} und Elastomerbauteilen},\n price = {EUR 1}\n}\n\n"
        '@misc{DIN14,\n year = {2014},\n title = {Pr{\\"u}fma{\\ss}e},\n number = {DIN 21773},\n author = {DIN}\n}\n\n'
        "@misc{CWF24,\n title = {Seite},\n url = {https://example.org},\n urldate = {2024-04-01}\n}\n\n"
        '@phdthesis{Frü12,\n author = {Fr{\\"u}he, T.},\n year = {2012},\n title = {Diss},\n school = {TUM}\n}\n'
    )
    entries = bibliography.parse_bib(text)
    assert [e.key for e in entries] == ["Sto18", "DIN14", "CWF24", "Frü12"]
    book = bibliography.classify(entries[0])
    assert book.kind == "book" and "price" not in book.fields
    assert book.fields["title"] == "FEM zur Berechnung von {Kunststoff-} und Elastomerbauteilen"
    norm = bibliography.classify(entries[1])
    assert norm.kind == "manual" and norm.fields["keywords"] == "norm"
    assert norm.fields["author"] == "DIN"  # the label [DIN14] comes from the author
    stray = bibliography.classify(
        bibliography.Entry("Lin10", "book", {"title": "x", "doi": "41464"})
    )
    assert "doi" not in stray.fields
    kept = bibliography.classify(
        bibliography.Entry("Has16", "article", {"title": "x", "doi": "10.1007/s10010-016-0207-8"})
    )
    assert kept.fields["doi"].startswith("10.")
    web = bibliography.classify(entries[2])
    assert web.kind == "online" and "keywords" not in web.fields
    assert bibliography.ascii_key("Frü12") == "Frue12"
    assert bibliography.ascii_key("Öch16") == "Oech16"
    assert bibliography.ascii_key("İmr09") == "Imr09"
    with pytest.raises(InputRangeError):
        bibliography.parse_bib(text + "\n@book{Sto18,\n title = {x}\n}\n")


def test_bib_check_and_take(bibliography: ModuleType, tmp_path: Path) -> None:
    chapters = tmp_path / "Kapitel"
    chapters.mkdir()
    (chapters / "kap.tex").write_text(
        "nach \\cite{Sto18} und \\cite[S. 5]{Frue12, Fehlt} % \\cite{Nie03}\n", encoding="utf-8"
    )
    assert bibliography.cited_keys([chapters / "kap.tex"]) == {"Sto18", "Frue12", "Fehlt"}
    litbib = tmp_path / "litbib.bib"
    litbib.write_text(
        "@book{Sto18,\n author = {Stommel, M.},\n title = {FEM},\n year = {2018}\n}\n"
        "@thesis{Frue12,\n author = {Frühe, T.},\n title = {Diss},\n year = {2012}\n}\n"
        "@manual{DIN3972,\n author = {DIN},\n title = {Bezugsprofile},\n year = {1952},\n"
        " keywords = {norm}\n}\n"
        "@book{Unbenutzt,\n title = {x}\n}\n",
        encoding="utf-8",
    )
    missing, unused, problems = bibliography.check(litbib, chapters)
    assert missing == ["Fehlt"]
    assert unused == ["DIN3972", "Unbenutzt"]
    assert "Norm ohne Bezeichnung mit Nummer im title" in problems["DIN3972"]
    assert "Norm ohne date mit Monat (JJJJ-MM)" in problems["DIN3972"]
    assert "ohne year oder date" in problems["Unbenutzt"]
    assert "ohne author oder editor" in problems["Unbenutzt"]
    assert "Sto18" not in problems and "Frue12" not in problems
    citavi = tmp_path / "citavi.bib"
    citavi.write_text(
        '@misc{DIN14,\n year = {2014},\n title = {Pr{\\"u}fma{\\ss}e},\n number = {DIN 21773},\n'
        " author = {DIN}\n}\n@phdthesis{Für13,\n author = {F.},\n year = {2013},\n title = {D}\n}\n",
        encoding="utf-8",
    )
    taken = bibliography.take(["Für13", "DIN14"], citavi, litbib)
    assert [e.key for e in taken] == ["Fuer13", "DIN14"]
    assert taken[1].kind == "manual" and taken[1].fields["keywords"] == "norm"
    text = litbib.read_text(encoding="utf-8")
    assert "@phdthesis{Fuer13," in text and "Titelseite noch zu prüfen" in text
    with pytest.raises(InputRangeError, match="already"):
        bibliography.take(["DIN14"], citavi, litbib)
    with pytest.raises(InputRangeError, match="not in the Citavi export"):
        bibliography.take(["Nix99"], citavi, litbib)


def test_figure_listing_rules(figures: ModuleType, tmp_path: Path) -> None:
    listing = tmp_path / "bilder.yaml"
    listing.write_text(
        "bilder:\n  - name: a\n    kapitel: 3\n    quelle: nicht/da.svg\n", encoding="utf-8"
    )
    with pytest.raises(InputRangeError, match="does not exist"):
        figures.read_listing(listing)
    listing.write_text("bilder: 5\n", encoding="utf-8")
    with pytest.raises(InputRangeError, match="list 'bilder'"):
        figures.read_listing(listing)
    # an existing png source may only be copied as png
    source = (
        figures.OUTPUT / "fe" / "kst_e" / "frozen_mesh_20layers_bore33_pocket" / "mesh_tooth.png"
    )
    if not source.is_file():
        pytest.skip("the output folder of the frozen pocket mesh is not on this machine")
    listing.write_text(
        "bilder:\n  - name: netz\n    kapitel: 3\n"
        "    quelle: fe/kst_e/frozen_mesh_20layers_bore33_pocket/mesh_tooth.png\n    format: pdf\n",
        encoding="utf-8",
    )
    with pytest.raises(InputRangeError, match="copied as png"):
        figures.read_listing(listing)
