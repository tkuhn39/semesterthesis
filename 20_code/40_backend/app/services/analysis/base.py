"""
@module: app.services.analysis.base
@context: Domain layer — independent analyses (STplus / RIKOR / rolling).
@role: Shared types for the three first-class, independently runnable analyses.
       Each analysis's compute is a pluggable runner (exe | native | remote); a
       run yields display-ready values and produced artifacts (storage keys) that
       can be exported to a folder or fed into a downstream analysis (ADR-010).
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class AnalysisKind(StrEnum):
    """The three independently runnable analyses."""

    STPLUS = "stplus"
    RIKOR = "rikor"
    ROLLING = "rolling"


class RunnerKind(StrEnum):
    """How an analysis is computed."""

    EXE = "exe"  # subprocess of the original Windows program (full output, Windows-only)
    NATIVE = "native"  # Python reimplementation (cross-platform)
    REMOTE = "remote"  # run on a remote (Windows) host


class AnalysisResult(BaseModel):
    """Outcome of an analysis run.

    ``values`` are rendered strings (UI/export friendly). ``artifacts`` are
    storage keys (see :mod:`app.storage`) of files the run produced, which the
    user can export to a chosen folder or feed into a downstream analysis.
    """

    kind: AnalysisKind
    runner: RunnerKind
    title: str
    values: dict[str, str] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)
