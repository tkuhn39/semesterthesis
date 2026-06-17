"""
@package: app.services.variation
@context: Domain layer — the plastic-capable Stufenvariation (macro-geometry sweep).
@role: A vectorized kernel (``kernel``) plus the sweep orchestration (``sweep``):
       grid / Sobol / LHS sampling, early pruning, per-gear material dispatch
       (steel → ISO 6336, plastic → VDI 2736) and a Pareto front of the good
       macro-geometries. Beats the FVA-Workbench Stufenvariation on capability (it
       supports plastic gears) and speed (a numpy batch instead of a per-variant
       loop). Standards & strategy: ADR-013.
"""

from app.services.variation.sweep import (
    VariationResult,
    VariationSpec,
    Varied,
    build_grid,
    build_sample,
    evaluate,
    pareto_front,
)

__all__ = [
    "VariationResult",
    "VariationSpec",
    "Varied",
    "build_grid",
    "build_sample",
    "evaluate",
    "pareto_front",
]
