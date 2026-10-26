"""The appendix tables of the thesis (``scripts/thesis_appendix_tables.py``): the script runs on
the data files of the chain and the generated files carry the rows the data promise."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def tables() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "thesis_appendix_tables", SCRIPTS / "thesis_appendix_tables.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _needs_outputs(tables: ModuleType) -> None:
    for path in (tables.CONVERGENCE, tables.CONVERGENCE_INCOMPATIBLE, tables.COMPARISON):
        if not path.exists():
            pytest.skip(f"output of the chain not found: {path}")


@pytest.fixture(scope="module")
def generated(tables: ModuleType, tmp_path_factory: pytest.TempPathFactory) -> Path:
    _needs_outputs(tables)
    out = tmp_path_factory.mktemp("generiert")
    assert tables.main(["--out", str(out)]) == 0
    return out


def test_formatting_follows_the_writing_rules(tables: ModuleType) -> None:
    assert tables.num(-15.378, 2) == "$-15{,}38$"
    assert tables.num(-0.0004, 2) == "$0{,}00$"
    assert tables.count(55193) == "55\\,193"
    assert tables.sym("tip_diameter") == "$d_{\\mathrm{a}}$"
    assert tables.formula_tex("h_w = (d_Fa1 + d_Fa2) / 2 - a_w") == (
        "$h_{\\mathrm{w}} = (d_{\\mathrm{Fa1}} + d_{\\mathrm{Fa2}}) / 2 - a_{\\mathrm{w}}$"
    )


def test_every_table_is_written(tables: ModuleType, generated: Path) -> None:
    names = [name for name, _builder in tables.TABLES]
    assert len(names) == 16
    for name in names:
        text = (generated / f"{name}.tex").read_text(encoding="utf-8")
        assert text.startswith(tables.HEADER)
        assert "\\begin{table}[htbp]" in text and "\\end{table}" in text
        assert tables.body_rows(text) > 0
        # the writing rules: no dash, no semicolon outside the LaTeX line ends
        body = text.replace("\\\\", "")
        assert "–" not in body and "—" not in body and ";" not in body


def test_norm_mapping_keeps_the_designations(generated: Path) -> None:
    text = (generated / "anhang_b_normzuordnung.tex").read_text(encoding="utf-8")
    assert "DIN 3960:1987-03 (zurückgezogen) & DIN ISO 21771:2014-08 (ISO 21771:2007)" in text
    assert "DIN 21773:2014-08" in text
    assert "(vorgesehen)" in text
    assert "Etappe" not in text


def test_deviations_carry_both_equations_and_the_example(generated: Path) -> None:
    text = (generated / "anhang_b_normabweichungen.tex").read_text(encoding="utf-8")
    assert "$h_{\\mathrm{w}} = (d_{\\mathrm{a1}} + d_{\\mathrm{a2}}) / 2 - a_{\\mathrm{w}}$" in text
    assert (
        "$h_{\\mathrm{w}} = (d_{\\mathrm{Fa1}} + d_{\\mathrm{Fa2}}) / 2 - a_{\\mathrm{w}}$" in text
    )
    assert "kst-B: Norm $3{,}205$\\,mm, Kette $2{,}918$\\,mm, STplus $2{,}918$\\,mm" in text
    assert "Kette $2{,}3087$, STplus $2{,}287$" in text
    assert "Gl. (48) bis (53)" in text


def test_geometry_of_kst_e_matches_the_stplus_case(generated: Path) -> None:
    text = (generated / "anhang_b_geometrie_kste.tex").read_text(encoding="utf-8")
    assert "$z$ &  & 51 & 52 \\\\" in text
    assert "$d_{\\mathrm{a}}$ & mm & $52{,}8940$ & $54{,}0220$" in text
    assert "$x_{\\mathrm{E}}$ &  & $-0{,}2030$ & $0{,}0117$" in text
    assert "$W_{\\mathrm{k}}$ (Nennmaß) & mm & $17{,}0901$ & $17{,}1800$" in text
    assert "$k$ &  & 6 & 6" in text
    pair = (generated / "anhang_b_radpaar_kste.tex").read_text(encoding="utf-8")
    assert "$a_{\\mathrm{w}}$ & mm & $52{,}0000$" in pair
    assert "$\\varepsilon_{\\alpha}$ &  & $1{,}1538$" in pair
    assert "$\\alpha_{\\mathrm{wt}}$ & ° & $21{,}463$" in pair


def test_material_cards_and_classes(generated: Path) -> None:
    cards = (generated / "anhang_d_kennwerte_karten.tex").read_text(encoding="utf-8")
    assert "$E$ & MPa & $4110{,}21$ & $2282{,}08$ & $5057{,}26$ & $2542{,}51$" in cards
    assert "$\\nu$ &  & $0{,}3032$ & $0{,}2997$" in cards
    assert "$115{,}51$ & $88{,}98$ & $176{,}40$ & $108{,}43$ & $245{,}73$ & $129{,}84$" in cards
    hill = (generated / "anhang_d_hill_zustaende.tex").read_text(encoding="utf-8")
    assert "$1{,}000$ & $0{,}000$ & $1{,}3846$ & $0{,}5489$" in hill
    assert "$0{,}333$ & $0{,}333$ & $0{,}6835$" in hill
    strength = (generated / "anhang_d_klassen_festigkeit.tex").read_text(encoding="utf-8")
    assert "teilkristallin (verstärkt) & semi-duktil & $0{,}65$ & $0{,}26$ & $0{,}25$" in strength
    assert "\\cite[Tabelle 6.1, S.~323]{Sto18}" in strength
    reduction = (generated / "anhang_d_klassen_abminderung.tex").read_text(encoding="utf-8")
    assert (
        "teilkristallin (unverstärkt) & $0{,}80$ bis $1{,}00$ & $0{,}60$ bis $0{,}80$" in reduction
    )


def test_convergence_tables_reproduce_the_study(tables: ModuleType, generated: Path) -> None:
    ladder = (generated / "anhang_e_netzleiter_cpe4.tex").read_text(encoding="utf-8")
    assert "gleichmäßig & 4 & 55\\,193 & 53\\,760 & 80 & 320 & 40 & $140{,}89$" in ladder
    assert "Stellung D & 1 & 3\\,719" in ladder
    rows = tables.read_ladder(tables.CONVERGENCE)
    fit = tables.richardson_of(tables.series_rows(rows, "gleichmäßig"), "root_sigma1_max_mpa")
    assert fit.order == pytest.approx(0.84, abs=0.005)  # convergence.md: p = 0,84, 148,216 MPa
    assert fit.limit == pytest.approx(148.216, abs=0.001)
    extrapolation = (generated / "anhang_e_extrapolation_cpe4.tex").read_text(encoding="utf-8")
    assert "$0{,}85$ & $148{,}14$ & $-15{,}34$ / $-8{,}78$ / $-6{,}23$ / $-4{,}88$" in extrapolation
    assert "$4{,}25$ & $203{,}47$" in extrapolation
    assert "keine monotone Konvergenz" in extrapolation
    incompatible = (generated / "anhang_e_extrapolation_cpe4i.tex").read_text(encoding="utf-8")
    assert "$4{,}62$ & $148{,}68$" in incompatible


def test_element_type_tables(generated: Path) -> None:
    plane = (generated / "anhang_e_elementtypen.tex").read_text(encoding="utf-8")
    assert (
        "Ausgangsnetz & CPE4R & 3\\,719 & $205{,}999$ & $203{,}801$ & $114{,}85$ & $125{,}42$"
        in plane
    )
    limits = (generated / "anhang_e_elementtypen_grenzwerte.tex").read_text(encoding="utf-8")
    assert (
        "CPE4R & $114{,}85$ / $127{,}94$ / $133{,}57$ / $136{,}69$ & $0{,}71$ & $150{,}47$"
        in limits
    )
    assert (
        "CPE4I & $141{,}60$ / $147{,}61$ / $148{,}50$ / $148{,}62$ & $4{,}63$ & $148{,}66$"
        in limits
    )
    solid = (generated / "anhang_e_volumen_schichten.tex").read_text(encoding="utf-8")
    assert "80 & C3D8I & 301\\,239 & $204{,}950$" in solid
    test = (generated / "anhang_e_elementtest.tex").read_text(encoding="utf-8")
    assert "C3D8I & ja & durchgelaufen & 4 / 6 & 29 Warnungen" in test
    assert "C3D8 & ja & durchgelaufen & 4 / 6 & 0 & $3$\\,s" in test
