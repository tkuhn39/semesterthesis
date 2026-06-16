"""
@module: app.services.ingest
@context: Domain layer — import gear definitions from existing tool files.
@role: Let users pick an STplus `.ste` and a RIKOR `.rexs` instead of re-typing
       everything; pull the gear values from both and flag inconsistencies if the
       two files do not describe the same gearing (wrong file pair). The check is
       order-independent (which file lists pinion/wheel first does not matter).
"""

from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from app.io.rexs import RexsGearStage, gear_stage_from_rexs, load_rexs
from app.io.ste import SteGearStage, gear_stage_from_ste, load_ste


class Discrepancy(BaseModel):
    """One mismatching quantity between the STplus and RIKOR gear definition."""

    field: str
    ste: str
    rexs: str
    note: str


def _close_multiset(a: Sequence[float], b: Sequence[float], tol: float) -> bool:
    """Whether two value sets match within ``tol``, ignoring order."""
    sa, sb = sorted(a), sorted(b)
    return len(sa) == len(sb) and all(abs(x - y) <= tol for x, y in zip(sa, sb, strict=True))


def compare_gear_stages(
    ste: SteGearStage,
    rexs: RexsGearStage,
    *,
    length_tol_mm: float = 0.05,
    angle_tol_deg: float = 0.05,
) -> list[Discrepancy]:
    """Return the discrepancies between an STplus and a RIKOR gear stage.

    An empty list means the two files describe the same gearing. Comparison is
    order-independent and uses tooth count, module, face widths and helix-angle
    magnitudes — enough to catch an accidentally mismatched file pair.
    """
    issues: list[Discrepancy] = []

    if sorted(ste.teeth) != sorted(rexs.teeth):
        issues.append(
            Discrepancy(
                field="teeth",
                ste=str(tuple(ste.teeth)),
                rexs=str(tuple(rexs.teeth)),
                note="different tooth counts",
            )
        )
    if abs(ste.normal_module_mm - rexs.normal_module_mm) > 1e-3:
        issues.append(
            Discrepancy(
                field="normal_module_mm",
                ste=str(ste.normal_module_mm),
                rexs=str(rexs.normal_module_mm),
                note="different normal module",
            )
        )
    if not _close_multiset(ste.face_width_mm, rexs.face_width_mm, length_tol_mm):
        issues.append(
            Discrepancy(
                field="face_width_mm",
                ste=str(ste.face_width_mm),
                rexs=str(rexs.face_width_mm),
                note="different face widths",
            )
        )
    ste_helix = [abs(h) for h in ste.helix_angle_deg]
    rexs_helix = [abs(h) for h in rexs.helix_angle_deg]
    if not _close_multiset(ste_helix, rexs_helix, angle_tol_deg):
        issues.append(
            Discrepancy(
                field="helix_angle_deg",
                ste=str(ste.helix_angle_deg),
                rexs=str(rexs.helix_angle_deg),
                note="different helix angle (magnitude)",
            )
        )
    return issues


def load_and_compare(
    ste_path: Path, rexs_path: Path
) -> tuple[SteGearStage, RexsGearStage, list[Discrepancy]]:
    """Load both tool files and cross-check them; returns the two stages and the
    discrepancies (empty if they describe the same gearing)."""
    ste = gear_stage_from_ste(load_ste(ste_path))
    rexs = gear_stage_from_rexs(load_rexs(rexs_path))
    return ste, rexs, compare_gear_stages(ste, rexs)
