"""
@module: tests.test_materials
@context: Domain-layer tests — gear materials.
@role: Materials load from a `.ste`, classify steel vs plastic by modulus, and
       carry the DIN 3990 endurance limits; missing optional fields stay None.
"""

from pathlib import Path

import pytest

from app.io.ste import load_ste
from app.services.materials import Material, MaterialKind, NonlinearCurve, material_from_ste

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)


def test_material_classifies_and_loads_limits() -> None:
    """A steel and a plastic material build directly with their limits."""
    steel = Material(
        name="16MnCr5",
        kind=MaterialKind.STEEL,
        elastic_modulus_mpa=210000.0,
        poisson_ratio=0.3,
        sigma_hlim_mpa=1460.0,
        sigma_fe_mpa=860.0,
    )
    assert steel.is_plastic is False
    plastic = Material(
        name="PA66",
        kind=MaterialKind.PLASTIC,
        elastic_modulus_mpa=2300.0,
        poisson_ratio=0.5,
        sigma_flim_mpa=35.0,
    )
    assert plastic.is_plastic is True
    assert plastic.wear_coefficient_mm3_per_nm is None  # optional, stays None


@pytest.mark.skipif(not _REF_STE.exists(), reason="STplus reference .ste not present")
def test_materials_from_ste_reference() -> None:
    """Both kst-E materials load from the `.ste`, classified by modulus."""
    ste = load_ste(_REF_STE)
    steel = material_from_ste(ste, "16MnCr5")
    plastic = material_from_ste(ste, "WST_PA66")
    assert steel.kind is MaterialKind.STEEL
    assert steel.name == "16MnCr5"
    assert steel.elastic_modulus_mpa == pytest.approx(210000.0)
    assert steel.poisson_ratio == pytest.approx(0.3)
    assert steel.sigma_hlim_mpa == pytest.approx(1460.0)
    assert steel.sigma_fe_mpa == pytest.approx(860.0)
    assert plastic.kind is MaterialKind.PLASTIC
    assert plastic.name == "PA66"
    assert plastic.elastic_modulus_mpa == pytest.approx(2300.0)
    assert plastic.poisson_ratio == pytest.approx(0.5)
    assert plastic.sigma_flim_mpa == pytest.approx(35.0)


def test_nonlinear_curve_interpolates_and_clamps() -> None:
    """A measured stress-strain curve interpolates linearly and clamps at the ends."""
    curve = NonlinearCurve(
        quantity="stress_strain",
        x_label="strain",
        y_label="stress_mpa",
        points=[(0.0, 0.0), (0.01, 30.0), (0.05, 50.0)],
    )
    assert curve.value_at(0.005) == pytest.approx(15.0)  # midpoint, first segment
    assert curve.value_at(0.03) == pytest.approx(40.0)  # midpoint, second segment
    assert curve.value_at(-1.0) == pytest.approx(0.0)  # clamped low
    assert curve.value_at(9.0) == pytest.approx(50.0)  # clamped high


def test_nonlinear_curve_rejects_unsorted() -> None:
    """x values must be strictly ascending."""
    with pytest.raises(ValueError, match="ascending"):
        NonlinearCurve(quantity="x", x_label="a", y_label="b", points=[(1.0, 0.0), (0.5, 1.0)])


def test_material_holds_nonlinear_curves() -> None:
    """A material can carry and look up nonlinear curves by quantity."""
    mat = Material(
        name="PA66",
        kind=MaterialKind.PLASTIC,
        elastic_modulus_mpa=2300.0,
        poisson_ratio=0.4,
        nonlinear_curves=[
            NonlinearCurve(
                quantity="stress_strain",
                x_label="strain",
                y_label="stress_mpa",
                points=[(0.0, 0.0), (0.02, 40.0)],
            )
        ],
    )
    assert mat.curve("stress_strain") is not None
    assert mat.curve("missing") is None


def test_catalog_is_single_source_across_ui_and_frontend_mirror() -> None:
    """Audit F2/P2: the catalog exists in three places (backend CATALOG, Werkstoff-tab
    mat_name options, frontend name→kind mirror) — this guard fails on drift until a
    served catalog replaces the copies entirely."""
    from pathlib import Path

    from app.services.materials import CATALOG, DEFAULT_BY_KIND, MaterialKind
    from app.services.uimodel.components import ATTRIBUTES

    # every kind has a default and every default exists
    assert set(DEFAULT_BY_KIND) == set(MaterialKind)
    assert all(name in CATALOG for name in DEFAULT_BY_KIND.values())

    # Werkstoff-tab name options == catalog names
    mat_name = next(a for a in ATTRIBUTES if a.id == "mat_name")
    assert mat_name.options is not None
    assert {o.value for o in mat_name.options} == set(CATALOG)

    # frontend mirror (store.tsx CATALOG_MATERIAL_KIND) carries every catalog name
    # with the right kind — parsed textually (no TS test runner in the gates)
    store = (
        Path(__file__).resolve().parents[2] / "50_frontend" / "src" / "lib" / "store.tsx"
    ).read_text(encoding="utf-8")
    for name, mat in CATALOG.items():
        needle_quoted = f'"{name}": "{mat.kind.value}"'
        needle_bare = f'{name}: "{mat.kind.value}"'
        assert needle_quoted in store or needle_bare in store, (
            f"frontend CATALOG_MATERIAL_KIND misses {name} -> {mat.kind.value}"
        )
