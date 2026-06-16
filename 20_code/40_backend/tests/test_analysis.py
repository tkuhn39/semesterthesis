"""
@module: tests.test_analysis
@context: Domain-layer tests — independent analyses.
@role: The native (cross-platform) STplus geometry analysis produces an
       AnalysisResult whose values match STplus output.
"""

from app.io.ste import SteGearStage
from app.services.analysis.base import AnalysisKind, RunnerKind
from app.services.analysis.stplus import run_stplus_geometry

KST_E = SteGearStage(
    normal_module_mm=1.0,
    teeth=(51, 52),
    pressure_angle_deg=(20.0, 20.0),
    helix_angle_deg=(0.0, 0.0),
    face_width_mm=(17.0, 15.0),
    profile_shift=(0.2034, 0.3143),
    center_distance_mm=52.0,
)


def test_stplus_geometry_analysis_native() -> None:
    """Native STplus geometry runs cross-platform and matches STplus values."""
    result = run_stplus_geometry(KST_E)
    assert result.kind == AnalysisKind.STPLUS
    assert result.runner == RunnerKind.NATIVE
    assert result.values["teeth_pinion"] == "51"
    assert result.values["working_center_distance_mm"] == "52.0000"
    assert result.values["working_pitch_diameter_pinion_mm"] == "51.4951"
    assert result.values["reference_diameter_wheel_mm"] == "52.0000"
