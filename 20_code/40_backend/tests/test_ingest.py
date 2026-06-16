"""
@module: tests.test_ingest
@context: Domain-layer tests — import & cross-check of STplus/RIKOR files.
@role: Verify the consistency check is order-independent, passes for a matching
       pair, flags a mismatched pair, and works end-to-end on real (deliberately
       mismatched) reference files.
"""

from pathlib import Path

import pytest

from app.io.rexs import RexsGearStage
from app.io.ste import SteGearStage
from app.services.ingest import compare_gear_stages, load_and_compare

# A matching kst-E pair (STplus and RIKOR describing the same gearing).
_STE = SteGearStage(
    normal_module_mm=1.0,
    teeth=(51, 52),
    pressure_angle_deg=(20.0, 20.0),
    helix_angle_deg=(0.0, 0.0),
    face_width_mm=(17.0, 15.0),
    profile_shift=(0.2034, 0.3143),
)
_REXS = RexsGearStage(
    teeth=(51, 52),
    normal_module_mm=1.0,
    helix_angle_deg=(0.0, 0.0),
    face_width_mm=(17.0, 15.0),
)


def test_consistent_pair_has_no_discrepancies() -> None:
    assert compare_gear_stages(_STE, _REXS) == []


def test_comparison_is_order_independent() -> None:
    """It does not matter which file lists pinion/wheel first."""
    swapped = _REXS.model_copy(update={"teeth": (52, 51), "face_width_mm": (15.0, 17.0)})
    assert compare_gear_stages(_STE, swapped) == []


def test_mismatched_pair_is_flagged() -> None:
    """A wrong file pair is flagged per field."""
    other = _REXS.model_copy(
        update={"teeth": (14, 59), "normal_module_mm": 8.0, "face_width_mm": (137.0, 127.0)}
    )
    fields = {issue.field for issue in compare_gear_stages(_STE, other)}
    assert {"teeth", "normal_module_mm", "face_width_mm"} <= fields


_ROOT = Path(__file__).resolve().parents[3] / "30_references_and_examples"
_STE_FILE = _ROOT / "33_STplus" / "kst-E_eingabe.ste"
_REXS_FILE = (
    _ROOT
    / "35_Rikor"
    / "RIKOR_exec"
    / "work"
    / "Beispiele"
    / "001_eine_stufe"
    / "3_Referenz"
    / "rikor_ausgabe_ref.rexs"
)


@pytest.mark.skipif(
    not (_STE_FILE.exists() and _REXS_FILE.exists()), reason="references not present"
)
def test_load_and_compare_flags_mismatched_real_files() -> None:
    """Picking a .ste and a .rexs of different gearings is flagged end-to-end."""
    _, _, issues = load_and_compare(_STE_FILE, _REXS_FILE)
    assert issues
    assert any(issue.field == "teeth" for issue in issues)
