"""
@module: tests.test_rexs
@context: I/O tests.
@role: Parse synthetic and real RIKOR REXS files (scalar / array / matrix
       attributes) and verify reference parity across all shipped examples.
"""

from pathlib import Path

import pytest

from app.io.rexs import load_rexs, parse_rexs

_REXS = """<?xml version="1.0" encoding="UTF-8"?>
<model applicationId="TEST" applicationVersion="0.1" version="1.2">
<components>
  <component id="1" name="Unit" type="gear_unit">
    <attribute id="g" unit="m / s^2">9.81</attribute>
    <attribute id="vec" unit="mm"><array><c>1.0</c><c>0.0</c><c>0.0</c></array></attribute>
    <attribute id="mat" unit="none">
      <matrix><r><c>1</c><c>2</c></r><r><c>3</c><c>4</c></r></matrix>
    </attribute>
    <attribute id="flag" unit="none">true</attribute>
  </component>
  <component id="3" type="cylindrical_stage">
    <attribute id="common_face_width" unit="mm">10.0</attribute>
  </component>
</components>
</model>
"""


def test_parse_scalar_array_matrix() -> None:
    """Scalar, array and matrix attributes are read and typed on demand."""
    model = parse_rexs(_REXS)
    assert model.application_id == "TEST"
    assert model.version == "1.2"

    unit = model.component(type_="gear_unit")
    assert unit is not None

    g = unit.attr("g")
    assert g is not None and g.as_float() == 9.81
    vec = unit.attr("vec")
    assert vec is not None and vec.as_floats() == [1.0, 0.0, 0.0]
    mat = unit.attr("mat")
    assert mat is not None and mat.as_float_matrix() == [[1.0, 2.0], [3.0, 4.0]]
    flag = unit.attr("flag")
    assert flag is not None and flag.text == "true"


def test_wrong_accessor_raises() -> None:
    """Using the scalar accessor on an array attribute raises."""
    unit = parse_rexs(_REXS).component(type_="gear_unit")
    assert unit is not None
    vec = unit.attr("vec")
    assert vec is not None
    with pytest.raises(ValueError):
        vec.as_float()


# All shipped RIKOR reference outputs — varied (1 stage up to 6 stages).
_REXS_DIR = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "35_Rikor"
    / "RIKOR_exec"
    / "work"
    / "Beispiele"
)
_REXS_FILES = sorted(_REXS_DIR.rglob("*.rexs")) if _REXS_DIR.exists() else []
_REXS_PARAMS: list[Path | None] = [*_REXS_FILES] if _REXS_FILES else [None]


@pytest.mark.parametrize("path", _REXS_PARAMS, ids=lambda p: p.parent.parent.name if p else "none")
def test_reference_parity_all_rexs(path: Path | None) -> None:
    """Every RIKOR reference parses and exposes stages with positive face width."""
    if path is None:
        pytest.skip("RIKOR references not present")
    model = load_rexs(path)
    assert model.application_id == "RIKOR M"
    assert model.components
    stages = model.components_of_type("cylindrical_stage")
    assert stages
    for stage in stages:
        cfw = stage.attr("common_face_width")
        assert cfw is not None and cfw.as_float() > 0


def test_known_stage_values() -> None:
    """Spot-check the single-stage reference (RIKOR M 1.2)."""
    path = _REXS_DIR / "001_eine_stufe" / "3_Referenz" / "rikor_ausgabe_ref.rexs"
    if not path.exists():
        pytest.skip("reference not present")
    model = load_rexs(path)
    stage = model.component(type_="cylindrical_stage")
    unit = model.component(type_="gear_unit")
    assert stage is not None and unit is not None

    cfw = stage.attr("common_face_width")
    ratio = stage.attr("gear_ratio")
    grav = unit.attr("gravitational_acceleration")
    assert cfw is not None and cfw.as_float() == 127.0
    assert ratio is not None and ratio.as_float() == 4.21428585
    assert grav is not None and grav.as_float() == 9.81
