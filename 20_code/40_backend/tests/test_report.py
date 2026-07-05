"""
@module: tests.test_report
@context: API tests — the interactive HTML system report (POST /api/report).
@role: The report is self-contained (no external requests), carries the animated
       Zahneingriff with the labelled line of action, and — better than FVA —
       lists each gear ONLY under its own norm: the mixed kst-E pair gets two
       separate single-column sections (ISO 6336 steel pinion, VDI 2736 plastic
       wheel) without "−" placeholder rows; a steel/steel pair gets one shared
       two-column ISO table.
"""

import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _report(payload: dict) -> str:
    res = client.post("/api/report", json=payload)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert "attachment" in res.headers.get("content-disposition", "")
    return res.text


def test_mixed_pair_each_gear_only_under_its_norm() -> None:
    html = _report({"label": "kst-E", "locale": "de"})
    # two separate norm sections, one per gear
    assert 'id="sec-gear1"' in html and 'id="sec-gear2"' in html
    assert 'id="sec-norm"' not in html
    g1 = html.index('id="sec-gear1"')
    g2 = html.index('id="sec-gear2"')
    sec1, sec2 = html[g1:g2], html[g2:]
    assert "ISO 6336" in sec1 and "VDI 2736" not in sec1[: sec1.find("</section>")]
    assert "VDI 2736" in sec2
    # plastic-only rows live ONLY in the VDI section — never as placeholder rows in
    # the ISO section (the FVA report lists them there with "−" values)
    sec1_table = sec1[: sec1.find("</section>")]
    for plastic_row in ("Zahntemperatur", "Verschleiß", "Zahnverformung"):
        assert plastic_row in sec2
        assert plastic_row not in sec1_table


def test_steel_steel_pair_shares_one_iso_table() -> None:
    html = _report(
        {
            "label": "steel-steel",
            "locale": "de",
            "capacity": {"pinion_material": "steel", "wheel_material": "steel"},
        }
    )
    assert 'id="sec-norm"' in html
    assert 'id="sec-gear1"' not in html
    assert html.count("VDI 2736") == 0


def test_report_is_self_contained_with_mesh_plot() -> None:
    html = _report({"label": "kst-E", "locale": "de"})
    # animated mesh plot with the labelled line of action
    assert "<svg" in html and 'id="mesh-svg"' in html
    for label in (">T1<", ">T2<", ">A<", ">B<", ">C<", ">D<", ">E<"):
        assert label in html
    assert "requestAnimationFrame" in html
    # kst-E line-of-action characteristics in the footer (α_wt ≈ 21.46°)
    assert "21.46" in html
    # no external references (self-contained: file works offline)
    assert not re.search(r'(?:src|href)\s*=\s*"https?://', html)
    # powerflow parity: shaft-1 torque 7.8462 derived from 8 N·m at shaft 2
    assert "7,8462" in html


def test_variation_section_from_persisted_results() -> None:
    # run a tiny sweep through the real endpoint, then feed its points to the report
    sweep = client.post(
        "/api/variation",
        json={
            "z1": {"vary": True, "value": 24, "min": 20, "max": 26, "steps": 4},
            "x1": {"vary": False, "value": 0.0, "min": -0.3, "max": 0.6},
        },
    ).json()
    html = _report(
        {
            "label": "kst-E",
            "locale": "de",
            "variation": {
                "request": {},
                "points": sweep["points"],
                "count": sweep["count"],
                "valid": sweep["valid"],
                "pareto": sweep["pareto"],
                "warnings": sweep["warnings"],
            },
        }
    )
    assert 'id="sec-variation"' in html
    assert "Stufenvariation" in html
    # the static parallel-coordinates SVG is embedded
    assert html.count("<svg") >= 2


def test_english_locale() -> None:
    html = _report({"label": "kst-E", "locale": "en"})
    assert "System report" in html
    assert "Cylindrical gear stage" in html
    assert "Tooth engagement" in html
