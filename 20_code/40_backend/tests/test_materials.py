"""
@module: tests.test_materials
@context: Domain-layer tests — gear materials.
@role: Materials load from a `.ste`, classify steel vs plastic by modulus, and
       carry the DIN 3990 endurance limits; missing optional fields stay None.
"""

from pathlib import Path

import pytest

from app.io.ste import load_ste
from app.services.materials import Material, MaterialKind, material_from_ste

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
