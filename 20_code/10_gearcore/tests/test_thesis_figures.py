"""The drawings of the thesis (T5): the 30° tangent construction against the STplus result
list of the kst-E wheel, the body outline of the drawing, the rounded corner."""

import importlib.util
import math
import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

from gearcore import contour as ct
from gearcore.errors import InputRangeError
from gearcore.fe import body as bd

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


@pytest.fixture(scope="module")
def figures() -> ModuleType:
    spec = importlib.util.spec_from_file_location("thesis_figures", SCRIPTS / "thesis_figures.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_thirty_degree_tangent_matches_stplus(figures: ModuleType) -> None:
    # STplus 11.0F result list of the case kst-E, wheel: s_Fn 2,197 mm, rho_F / m_n 0,38
    generation = figures.kst_e()
    contour = ct.tooth_contour(generation, "wheel", points=400)
    tangent = figures.tangent_point(contour)
    assert tangent.chord_mm == pytest.approx(2.197, abs=0.002)
    assert tangent.curvature_radius_mm / generation.inputs.normal_module_mm == pytest.approx(
        0.38, abs=0.01
    )
    root_form = generation.gears.wheel.root_form_diameter_mm
    root = generation.gears.wheel.generated_root_diameter_mm
    assert root < tangent.diameter_mm < root_form  # the point lies on the fillet
    with pytest.raises(InputRangeError):
        figures.tangent_point(contour, angle_deg=95.0)


def test_body_outline_follows_the_drawing(figures: ModuleType) -> None:
    body = bd.body_section("kst_e", "wheel")
    outline = figures.body_outline(body)
    assert np.allclose(outline[0], outline[-1])  # closed
    assert outline[:, 0].min() == pytest.approx(body.bore_radius_mm)
    assert outline[:, 0].max() == pytest.approx(body.tip_radius_mm)
    assert outline[:, 1].max() == pytest.approx(0.5 * body.face_width_mm)
    # the pocket floor lies at the web, the walls lean inwards with the depth
    floor = outline[np.isclose(outline[:, 1], body.bottom_z_mm)]
    assert floor[:, 0].min() > body.hub_wall_radius_mm
    assert floor[:, 0].max() < body.rim_wall_radius_mm


def test_rounded_corner_is_tangent_to_both_legs(figures: ModuleType) -> None:
    corner = np.array([0.0, 0.0])
    arc = figures._rounded_corner(np.array([-5.0, 0.0]), corner, np.array([0.0, 5.0]), 1.0, n=9)
    assert np.allclose(arc[0], [-1.0, 0.0])
    assert np.allclose(arc[-1], [0.0, 1.0])
    centre = np.array([-1.0, 1.0])
    assert np.allclose(np.hypot(*(arc - centre).T), 1.0)
    assert math.isclose(float(np.hypot(*(arc[4] - centre))), 1.0)
