import json
from pathlib import Path

import numpy as np
import pytest

from gearcore.errors import ParseError
from gearcore.io.stplus_contour import parse_contour


def test_stplus_export_grammar_semicolon_and_scientific() -> None:
    pts = parse_contour(
        "-5.549498E+00 ;  2.993630E+01\n-5.483297E+00 ;  2.995002E+01\n5.0D0 ; 6.0\n"
    )
    assert pts.shape == (3, 2)
    assert pts[0, 0] == pytest.approx(-5.549498)
    assert pts[2, 0] == 5.0


@pytest.mark.parametrize(
    "text",
    ["1.0\n2.0\n3.0\n", "a b\nc d\ne f\n", "1 2\n3 4\n", "1.0 2.0\n3.0 4.0 extra\n5.0 6.0\n"],
)
def test_bad_layout_is_a_parse_error(text: str) -> None:
    with pytest.raises(ParseError):
        parse_contour(text)


def test_packaged_contours_are_finite(case_dir: Path) -> None:
    meta = json.loads((case_dir / "meta.json").read_text(encoding="utf-8"))
    files = {c["file"] for c in meta["contours"]}
    for name in ("contour_wz1.json", "contour_wz2.json"):
        path = case_dir / name
        assert path.is_file() == (name in files), f"{case_dir.name}: {name} presence vs meta"
        if not path.is_file():
            continue
        pts = np.asarray(json.loads(path.read_text(encoding="utf-8"))["points"], dtype=float)
        assert pts.ndim == 2 and pts.shape[1] == 2 and pts.shape[0] > 10
        assert np.isfinite(pts).all()
