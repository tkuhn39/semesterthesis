"""Property tests of the measurement parsers and the inventory rules."""

import datetime as dt

from hypothesis import given
from hypothesis import strategies as st

from gearcore.io.hommel import parse_roughness_table
from gearcore.io.p40 import parse_mew
from gearcore.measurement.inventory import ROUND_GAP_DAYS, classify, rounds_by_date

_labels = st.text(
    alphabet="abcfFHKpruVkmoBlinechst ßäöü/",
    min_size=1,
    max_size=12,
).filter(lambda s: s.strip() and ":" not in s)
_values = st.one_of(
    st.floats(min_value=-1.0e6, max_value=1.0e6, allow_nan=False, allow_infinity=False),
    st.sampled_from([-9999.0, 8999.0]),
)


@given(
    st.lists(
        st.tuples(st.integers(10000, 99999), _labels, _values),
        min_size=1,
        max_size=40,
        unique_by=lambda t: t[0],
    ),
    st.integers(1, 999),
)
def test_value_files_round_trip(rows: list[tuple[int, str, float]], code: int) -> None:
    lines = [
        "HEADER KS.MW.FILE",
        "TYPE  STI ! Gear Value-data",
        "",
        f"  {code} :Datum....: 01.01.26",
    ]
    for number, label, value in rows:
        lines.append(f"{number} : {label} : {value!r}")
    mew = parse_mew("\r\n".join(lines) + "\r\n")
    assert mew.header.text(code) == "01.01.26"
    assert len(mew.values) == len(rows)
    for (number, label, value), parsed in zip(rows, mew.values, strict=True):
        assert parsed.code == number and parsed.label == " ".join(label.split())
        if value in (-9999.0, 8999.0):
            assert parsed.value is None and parsed.placeholder is not None
        else:
            assert parsed.value == value and parsed.placeholder is None


@given(
    st.lists(st.floats(-100.0, 100.0, allow_nan=False), min_size=1, max_size=6),
    st.integers(0, 5),
    st.booleans(),
)
def test_roughness_exports_round_trip(values: list[float], decimals: int, remark: bool) -> None:
    names = ["Merkmalsbeschreibung"] + [f"Messung-1.P{i}" for i in range(len(values))]
    names += ["Datenfeld(MeE-Nr.:)"] + (["Datenfeld(Bemerkung:)"] if remark else [])
    names += ["Datenfeld(Flanke/Seite:)"]
    printed = [f"{v:.{decimals}f}".replace(".", ",") for v in values]
    lines = [
        "title",
        "\t".join(names),
        "\t".join(["Einheit"] + ["µm"] * len(values)),
        "\t".join(["Nachkommastellen"] + [str(decimals)] * len(values)),
        "",
        "\t".join(["01.01.2026/00:00:00", *printed, "12345", *(["neu ä"] if remark else []), "li"]),
    ]
    table = parse_roughness_table(b"\xff\xfe" + "\n".join(lines).encode("utf-16-le"))
    record = table.records[0]
    assert record.me == "12345" and record.flank == "li"
    assert record.remark == ("neu ä" if remark else None)
    for i, text in enumerate(printed):
        assert record.value(f"Messung-1.P{i}") == float(text.replace(",", "."))
    assert all(d == decimals for _, d in table.decimals[: len(values)])


@given(st.lists(st.dates(dt.date(2024, 1, 1), dt.date(2027, 12, 31)), min_size=1, max_size=30))
def test_rounds_are_monotone_and_gap_bounded(dates: list[dt.date]) -> None:
    rounds = rounds_by_date([d.isoformat() for d in dates])
    ordered = sorted(rounds)
    assert [rounds[d] for d in ordered] == sorted(rounds[d] for d in ordered)
    assert rounds[ordered[0]] == 1
    for before, after in zip(ordered, ordered[1:], strict=False):
        gap = (dt.date.fromisoformat(after) - dt.date.fromisoformat(before)).days
        assert (rounds[after] == rounds[before]) == (gap <= ROUND_GAP_DAYS)


@given(
    st.integers(10000, 99999),
    st.sampled_from(["", "-neu", "_neu", "-neu1", "-neu2"]),
    st.sampled_from(["mew", "mka"]),
)
def test_gina_names_classify_to_their_me_and_variant(me: int, variant: str, kind: str) -> None:
    folder = "messwerte" if kind == "mew" else "messkurven"
    file = classify(f"GINA/Kunststoffrad/Rr_F4028-Kunst_52Z_neu_{folder}/{me}{variant}.{kind}")
    assert file is not None and file.me == str(me) and file.kind == kind
    assert file.variant == (variant or None) and file.part == "wheel"
