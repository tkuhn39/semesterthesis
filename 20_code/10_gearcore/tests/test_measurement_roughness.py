"""Roughness measurements from the Hommel exports: typed values of the fixture, the cross-check of
the instrument's means, duplicate exports, trace spread and the statistics over parts."""

import pytest

from gearcore.data import measurement_fixture
from gearcore.errors import InputRangeError, ParseError
from gearcore.io.hommel import load_roughness_table, parse_roughness_table
from gearcore.measurement import roughness as rg


@pytest.fixture(scope="module")
def wheel_left() -> rg.RoughnessMeasurement:
    table = load_roughness_table(measurement_fixture("roughness_F4092_97340_li.utf16.txt"))
    (measurement,) = rg.roughness_measurements(table)
    return measurement


def test_fixture_values(wheel_left: rg.RoughnessMeasurement) -> None:
    m = wheel_left
    assert (m.me, m.flank, m.measured_on, m.measured_at) == (
        "97340",
        "links",
        "2026-05-31",
        "15:58:14",
    )
    assert m.remark == "neu" and m.program.startswith("1.2mm-0.25mm-TKU300_3Mp")
    assert m.R_a_traces_um == (0.649, 1.043, 1.373) and m.R_a_um == 1.022
    assert m.R_z_traces_um == (5.002, 7.624, 9.644) and m.R_z_um == 7.423
    assert m.R_max_um == 10.92 and m.value("Messung-2.Rvk") == 5.144
    assert sum(m.R_a_traces_um) / 3 == pytest.approx(m.R_a_um, abs=rg.mean_tolerance_um(3))
    assert rg.mean_tolerance_um(2) == pytest.approx(0.0055, abs=1.0e-6)
    assert len(m.raw) == 48 and m.key == ("97340", "links", "2026-05-31", "15:58:14")
    assert rg.trace_spread(m) == pytest.approx(1.373 - 0.649)
    assert rg.trace_spread(m, "Rz") == pytest.approx(9.644 - 5.002)
    assert rg.trace_spread(m, "Rmax") == pytest.approx(13.362 - 6.856)
    with pytest.raises(InputRangeError):
        m.value("Messung-4.Ra")


def test_twin_export_is_dropped_and_a_disagreeing_one_refused(
    wheel_left: rg.RoughnessMeasurement,
) -> None:
    twin_table = load_roughness_table(measurement_fixture("roughness_F4092_97340_neu_li.utf16.txt"))
    (twin,) = rg.roughness_measurements(twin_table)
    assert twin.remark is None and twin.raw == wheel_left.raw
    kept, dropped = rg.dedupe([wheel_left, twin])
    assert kept == (wheel_left,) and dropped == (twin,)
    changed = twin.model_copy(update={"raw": twin.raw[:-1] + (("Xq-Ra", 1.023),)})
    with pytest.raises(ParseError, match="different numbers"):
        rg.dedupe([wheel_left, changed])
    other = twin.model_copy(update={"me": "97341"})
    kept, dropped = rg.dedupe([wheel_left, other])
    assert len(kept) == 2 and dropped == ()


def test_a_wrong_instrument_mean_is_refused() -> None:
    data = measurement_fixture("roughness_F4092_97340_li.utf16.txt").read_bytes()
    text = data.decode("utf-16")
    assert text.count("1,022") == 1
    broken = text.replace("1,022", "1,030").encode("utf-16")
    with pytest.raises(ParseError, match="Xq-Ra"):
        rg.roughness_measurements(parse_roughness_table(broken))
    sideways = text.replace("\tli\t", "\tlx\t").replace("\tli\r", "\tlx\r")
    if sideways != text:
        with pytest.raises(ParseError, match="flank code"):
            rg.roughness_measurements(parse_roughness_table(sideways.encode("utf-16")))


def test_statistics_over_parts(wheel_left: rg.RoughnessMeasurement) -> None:
    second = wheel_left.model_copy(update={"me": "97341", "R_a_um": 1.422, "R_z_um": 9.423})
    right = wheel_left.model_copy(update={"flank": "rechts", "R_a_um": 0.8})
    rows = rg.statistics([wheel_left, second, right])
    by_key = {(r.parameter, r.flank): r for r in rows}
    ra = by_key[("Ra", "links")]
    assert ra.quantity == "arithmetic_mean_roughness" and ra.count == 2
    assert ra.mean_um == pytest.approx(1.222) and ra.standard_deviation_um == pytest.approx(
        0.4 / 2**0.5
    )
    assert (ra.me_of_minimum, ra.me_of_maximum) == ("97340", "97341")
    assert ra.mean_trace_spread_um == pytest.approx(1.373 - 0.649)
    assert by_key[("Rz", "links")].maximum_um == 9.423
    assert (
        by_key[("Ra", "rechts")].count == 1
        and by_key[("Ra", "rechts")].standard_deviation_um == 0.0
    )
    assert ("Rz", "rechts") in by_key and len(rows) == 4
    with pytest.raises(InputRangeError):
        rg.statistics([])
