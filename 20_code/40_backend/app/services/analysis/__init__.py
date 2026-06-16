"""
@module: app.services.analysis
@context: Domain layer — the three independent analyses.
@role: STplus, RIKOR and quasi-static rolling, each runnable on its own with a
       pluggable runner (exe | native | remote). See ADR-010 and README.md.
"""

from app.services.analysis.base import AnalysisKind, AnalysisResult, RunnerKind

__all__ = ["AnalysisKind", "AnalysisResult", "RunnerKind"]
