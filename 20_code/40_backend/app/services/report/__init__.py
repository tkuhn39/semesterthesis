"""
@module: app.services.report
@context: Domain layer — the interactive HTML system report (Gesamtsystemreport).
@role: Re-export the builder; see :mod:`app.services.report.builder`.
"""

from app.services.report.builder import ReportData, build_report_html

__all__ = ["ReportData", "build_report_html"]
