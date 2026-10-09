import json
import math
from typing import Any

import pytest
from pydantic import ValidationError

from gearcore.models.common import FrozenModel, Pair
from gearcore.models.inputs import (
    DimensionKind,
    GearInput,
    GearKind,
    MaterialKind,
    MaterialRef,
    PairInput,
    SpanMeasurement,
    ToolProfile,
)
from gearcore.models.materials import (
    GearStrength,
    MaterialRecord,
    PolymerData,
    Provenance,
    SteelData,
)
from gearcore.models.profiles import BasicRackProfile
from gearcore.models.results import BasicGearGeometry

UNIT_SUFFIXES = {
    "_mm": "mm",
    "_deg": "deg",
    "_um": "µm",
    "_MPa": "MPa",
    "_C": "degC",
    "_kg_m3": "kg/m3",
}


def tool(**overrides: Any) -> ToolProfile:
    base: dict[str, Any] = {
        "addendum_factor": 1.25,
        "tip_radius_factor": 0.25,
        "protuberance_mm": 0.0,
        "machining_allowance_mm": 0.0,
    }
    base.update(overrides)
    return ToolProfile(**base)


def gear(**overrides: Any) -> GearInput:
    base: dict[str, Any] = {
        "number_of_teeth": 24,
        "profile_shift_coefficient": 0.1,
        "face_width_mm": 14.0,
        "tip_chamfer_radial_mm": 0.0,
        "tool": tool(),
    }
    base.update(overrides)
    return GearInput(**base)


def pair(**overrides: Any) -> PairInput:
    base: dict[str, Any] = {
        "normal_module_mm": 4.5,
        "normal_pressure_angle_deg": 20.0,
        "helix_angle_deg": 0.0,
        "centre_distance_mm": 91.5,
        "gears": Pair(
            pinion=gear(number_of_teeth=16),
            wheel=gear(number_of_teeth=24, profile_shift_coefficient=None),
        ),
    }
    base.update(overrides)
    return PairInput(**base)


def test_frozen_forbids_mutation_extra_and_nan() -> None:
    p = pair()
    with pytest.raises(ValidationError):
        p.normal_module_mm = 3.0  # type: ignore[misc]
    with pytest.raises(ValidationError):
        PairInput(**p.model_dump(), bogus=1)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        pair(normal_module_mm=math.nan)
    with pytest.raises(ValidationError):
        pair(normal_module_mm=math.inf)


def test_json_round_trip_and_hash() -> None:
    p = pair()
    dumped = p.model_dump_json()
    assert PairInput.model_validate_json(dumped) == p
    assert json.loads(dumped)["gears"]["pinion"]["number_of_teeth"] == 16
    assert hash(p) == hash(PairInput.model_validate_json(dumped))


def test_pair_container_keeps_roles() -> None:
    p = Pair[float](pinion=1.0, wheel=2.0)
    assert p.as_tuple() == (1.0, 2.0)
    assert Pair.same(3) == Pair[int](pinion=3, wheel=3)
    assert Pair[float].model_validate({"pinion": 1, "wheel": 2}).wheel == 2.0


def test_schema_carries_symbol_unit_source() -> None:
    schema = PairInput.model_json_schema()
    field = schema["properties"]["normal_module_mm"]
    assert field["symbol"] == "m_n" and field["unit"] == "mm"


@pytest.mark.parametrize(
    "model",
    [
        ToolProfile,
        GearInput,
        PairInput,
        SpanMeasurement,
        SteelData,
        PolymerData,
        GearStrength,
        BasicGearGeometry,
        BasicRackProfile,
    ],
)
def test_units_match_field_names(model: type[FrozenModel]) -> None:
    for name, info in model.model_fields.items():
        extra = info.json_schema_extra
        if not isinstance(extra, dict) or "unit" not in extra:
            continue
        for suffix, unit in UNIT_SUFFIXES.items():
            if name.endswith(suffix):
                assert extra["unit"] == unit, (
                    f"{model.__name__}.{name}: unit {extra['unit']!r} != {unit!r}"
                )


def test_profile_shift_must_be_determinable() -> None:
    with pytest.raises(ValidationError, match="profile shift undetermined"):
        pair(centre_distance_mm=None)
    with pytest.raises(ValidationError, match="one gear needs its nominal x"):
        pair(
            gears=Pair(
                pinion=gear(profile_shift_coefficient=None),
                wheel=gear(profile_shift_coefficient=None),
            )
        )
    ok = pair(
        centre_distance_mm=None,
        gears=Pair(
            pinion=gear(
                profile_shift_coefficient=None,
                span=SpanMeasurement(
                    kind=DimensionKind.UPPER_LIMIT,
                    span_measurement_mm=27.827,
                    number_of_teeth_spanned=5,
                ),
            ),
            wheel=gear(profile_shift_coefficient=0.2),
        ),
    )
    assert ok.gears.pinion.span is not None


def test_only_two_of_centre_distance_and_profile_shifts_may_be_given() -> None:
    """User decision 2026-09-30 (ADR-107): a_w, x_1 and x_2 together are an input error."""
    both: Pair[GearInput] = Pair(pinion=gear(number_of_teeth=16), wheel=gear(number_of_teeth=24))
    with pytest.raises(ValidationError, match="only two of the three may be given"):
        pair(gears=both)
    assert pair(gears=both, centre_distance_mm=None).centre_distance_mm is None
    one = pair()  # a_w and x_1
    assert one.gears.wheel.profile_shift_coefficient is None
    other = pair(
        gears=Pair(
            pinion=gear(number_of_teeth=16, profile_shift_coefficient=None),
            wheel=gear(number_of_teeth=24),
        )
    )  # a_w and x_2
    assert other.gears.pinion.profile_shift_coefficient is None


def test_tool_module_must_generate_the_basic_rack() -> None:
    with pytest.raises(ValidationError, match="cannot generate this basic rack"):
        pair(
            gears=Pair(
                pinion=gear(tool=tool(normal_module_mm=5.0)),
                wheel=gear(profile_shift_coefficient=None),
            )
        )
    # m_n0 cos alpha_n0 = m_n cos alpha_n holds for the STplus-allowed combination
    m_n0 = 4.5 * math.cos(math.radians(20)) / math.cos(math.radians(17.5))
    ok = pair(
        gears=Pair(
            pinion=gear(tool=tool(normal_module_mm=m_n0, profile_angle_deg=17.5)),
            wheel=gear(profile_shift_coefficient=None),
        )
    )
    assert ok.gears.pinion.tool.profile_angle_deg == 17.5


def test_input_ranges_reject_out_of_scope_values() -> None:
    with pytest.raises(ValidationError):
        gear(number_of_teeth=4)
    with pytest.raises(ValidationError):
        gear(profile_shift_coefficient=2.5)
    with pytest.raises(ValidationError):
        pair(helix_angle_deg=50.0)
    with pytest.raises(ValidationError):
        tool(tip_radius_factor=0.7)
    with pytest.raises(ValidationError, match="upper allowance"):
        gear(span_allowance_um=(-300.0, -200.0))


def test_gear_kind_internal_is_representable() -> None:
    g = gear(kind=GearKind.INTERNAL)
    assert g.kind is GearKind.INTERNAL


def test_material_record_layers_follow_kind() -> None:
    prov = Provenance(source="test")
    steel = SteelData(youngs_modulus_MPa=210000, poisson_ratio=0.3, provenance=prov)
    polymer = PolymerData(tensile_modulus_dry_MPa=10000, provenance=prov)
    MaterialRecord(kind=MaterialKind.STEEL, name="16MnCr5", steel=steel)
    MaterialRecord(kind=MaterialKind.PLASTIC, name="PA46-GF30", polymer=polymer)
    with pytest.raises(ValidationError, match="steel record must not carry a polymer"):
        MaterialRecord(kind=MaterialKind.STEEL, name="x", polymer=polymer)
    with pytest.raises(ValidationError, match="plastic record must not carry a steel"):
        MaterialRecord(kind=MaterialKind.PLASTIC, name="x", steel=steel)
    assert MaterialRef(kind=MaterialKind.PLASTIC, name="WST_PA66").kind is MaterialKind.PLASTIC
