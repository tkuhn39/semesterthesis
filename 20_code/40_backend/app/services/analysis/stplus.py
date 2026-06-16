"""
@module: app.services.analysis.stplus
@context: Domain layer — STplus analysis.
@role: Native (cross-platform) STplus runner. Currently covers the gear-stage
       geometry STplus computes (validated against STplus output); capacity
       (DIN 3990 / VDI 2736) follows. The full original STplus output remains
       available via the exe runner (Windows). See ADR-010.
"""

from app.io.ste import SteGearStage
from app.services.analysis.base import AnalysisKind, AnalysisResult, RunnerKind
from app.services.geometry import GearStage


def run_stplus_geometry(stage: SteGearStage) -> AnalysisResult:
    """Run the native STplus geometry analysis for a gear stage."""
    gear = GearStage.from_ste(stage)
    d1, d2 = gear.reference_diameter_mm
    db1, db2 = gear.base_diameter_mm
    dw1, dw2 = gear.working_pitch_diameter_mm
    values = {
        "normal_module_mm": f"{gear.normal_module_mm:g}",
        "teeth_pinion": str(gear.teeth[0]),
        "teeth_wheel": str(gear.teeth[1]),
        "reference_diameter_pinion_mm": f"{d1:.4f}",
        "reference_diameter_wheel_mm": f"{d2:.4f}",
        "base_diameter_pinion_mm": f"{db1:.4f}",
        "base_diameter_wheel_mm": f"{db2:.4f}",
        "working_pressure_angle_deg": f"{gear.working_pressure_angle_deg:.4f}",
        "working_center_distance_mm": f"{gear.working_center_distance_mm:.4f}",
        "working_pitch_diameter_pinion_mm": f"{dw1:.4f}",
        "working_pitch_diameter_wheel_mm": f"{dw2:.4f}",
    }
    return AnalysisResult(
        kind=AnalysisKind.STPLUS,
        runner=RunnerKind.NATIVE,
        title="STplus geometry (native)",
        values=values,
    )
