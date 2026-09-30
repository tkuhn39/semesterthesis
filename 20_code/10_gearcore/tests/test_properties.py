"""Property-based tests (rule 17): contracts round-trip, ranges reject, parsers are stable."""

from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from gearcore.io.ste import parse_ste
from gearcore.models.common import Pair
from gearcore.models.inputs import GearInput, PairInput, ToolProfile

finite = st.floats(allow_nan=False, allow_infinity=False)

tools = st.builds(
    ToolProfile,
    addendum_factor=st.floats(0.8, 2.5),
    tip_radius_factor=st.floats(0.0, 0.6),
    profile_angle_deg=st.none(),
    normal_module_mm=st.none(),
    dedendum_factor=st.none() | st.floats(0.8, 2.5),
    edge_break_angle_deg=st.none() | st.floats(1.0, 89.0),
    protuberance_mm=st.floats(0.0, 1.0),
    machining_allowance_mm=st.floats(0.0, 1.0),
)
gears = st.builds(
    GearInput,
    number_of_teeth=st.integers(5, 1000),
    profile_shift_coefficient=st.floats(-2.0, 2.0),
    face_width_mm=st.floats(0.1, 2000.0),
    tip_diameter_mm=st.none() | st.floats(1.0, 5000.0),
    tip_chamfer_radial_mm=st.floats(0.0, 2.0),
    tool=tools,
)


def _pinion_is_smaller(pair: Pair[GearInput]) -> bool:
    return pair.pinion.number_of_teeth <= pair.wheel.number_of_teeth


gears_without_shift = st.builds(
    GearInput,
    number_of_teeth=st.integers(5, 1000),
    profile_shift_coefficient=st.none(),
    face_width_mm=st.floats(0.1, 2000.0),
    tip_diameter_mm=st.none() | st.floats(1.0, 5000.0),
    tip_chamfer_radial_mm=st.floats(0.0, 2.0),
    tool=tools,
)
# only two of a_w, x_1, x_2 are given (ADR-107)
pairs = st.one_of(
    st.builds(
        PairInput,
        normal_module_mm=st.floats(0.05, 100.0),
        normal_pressure_angle_deg=st.floats(10.0, 30.0),
        helix_angle_deg=st.floats(-45.0, 45.0),
        centre_distance_mm=st.none(),
        gears=st.builds(Pair[GearInput], pinion=gears, wheel=gears).filter(_pinion_is_smaller),
    ),
    st.builds(
        PairInput,
        normal_module_mm=st.floats(0.05, 100.0),
        normal_pressure_angle_deg=st.floats(10.0, 30.0),
        helix_angle_deg=st.floats(-45.0, 45.0),
        centre_distance_mm=st.floats(1.0, 5000.0),
        gears=st.one_of(
            st.builds(Pair[GearInput], pinion=gears, wheel=gears_without_shift).filter(
                _pinion_is_smaller
            ),
            st.builds(Pair[GearInput], pinion=gears_without_shift, wheel=gears).filter(
                _pinion_is_smaller
            ),
        ),
    ),
)


@given(pairs)
def test_pair_input_round_trips_through_json_and_hashes(pair: PairInput) -> None:
    restored = PairInput.model_validate_json(pair.model_dump_json())
    assert restored == pair
    assert hash(restored) == hash(pair)
    assert restored.model_dump() == pair.model_dump()


@given(st.integers(-10_000, 10_000))
def test_teeth_outside_range_are_rejected(z: int) -> None:
    tool = ToolProfile(
        addendum_factor=1.25,
        tip_radius_factor=0.25,
        protuberance_mm=0.0,
        machining_allowance_mm=0.0,
    )
    if 5 <= z <= 1000:
        assert (
            GearInput(
                number_of_teeth=z,
                profile_shift_coefficient=0.0,
                face_width_mm=1.0,
                tip_chamfer_radial_mm=0.0,
                tool=tool,
            ).number_of_teeth
            == z
        )
    else:
        try:
            GearInput(
                number_of_teeth=z,
                profile_shift_coefficient=0.0,
                face_width_mm=1.0,
                tip_chamfer_radial_mm=0.0,
                tool=tool,
            )
        except ValidationError:
            return
        raise AssertionError(f"number_of_teeth={z} accepted outside [5, 1000]")


@given(finite)
def test_helix_angle_outside_range_is_rejected(beta: float) -> None:
    tool = ToolProfile(
        addendum_factor=1.25,
        tip_radius_factor=0.25,
        protuberance_mm=0.0,
        machining_allowance_mm=0.0,
    )
    gear = GearInput(
        number_of_teeth=20,
        profile_shift_coefficient=0.0,
        face_width_mm=1.0,
        tip_chamfer_radial_mm=0.0,
        tool=tool,
    )
    inside = -45.0 <= beta <= 45.0
    try:
        PairInput(
            normal_module_mm=1.0,
            normal_pressure_angle_deg=20.0,
            helix_angle_deg=beta,
            gears=Pair(pinion=gear, wheel=gear),
        )
    except ValidationError:
        assert not inside, f"beta={beta} rejected inside the range"
        return
    assert inside, f"beta={beta} accepted outside [-45, 45]"


keys = st.from_regex(r"[A-Z][A-Z0-9_]{0,22}", fullmatch=True)
numbers = st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False).map(lambda v: f"{v:.6g}")
values = st.lists(numbers | st.just("%"), min_size=1, max_size=3)


@given(st.lists(st.tuples(keys, values), min_size=1, max_size=8, unique_by=lambda kv: kv[0]))
def test_parse_ste_preserves_keys_and_tokens(entries: list[tuple[str, list[str]]]) -> None:
    body = "\n".join(f"{key} = {' '.join(vals)}" for key, vals in entries)
    ste = parse_ste(f"$ Anfang\n$ Block\n{body}\n$ Ende\n")
    section = ste.section("Block")
    assert section is not None
    assert [(e.key, list(e.values)) for e in section.entries] == [(k, v) for k, v in entries]
    for entry in section.entries:
        for index, token in enumerate(entry.values):
            number = entry.number(index)
            assert (number is None) == (token == "%")
