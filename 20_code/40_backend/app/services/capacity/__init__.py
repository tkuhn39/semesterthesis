"""
@package: app.services.capacity
@context: Domain layer — analytical tooth load capacity.
@role: Steel gears per **DIN 3990** and plastic gears per **VDI 2736**, sharing the
       geometry (``app.services.geometry``) and materials (``app.services.materials``).
       The stresses are exact vs the reference tools; load/dynamic/life factors are
       typed inputs (graceful defaults), to be computed or supplied per case.
"""

from app.services.capacity.iso6336 import (
    Iso6336Conditions,
    Iso6336GearResult,
    Iso6336LoadCase,
    elasticity_factor,
    evaluate_iso6336,
    native_dynamic_factors,
    single_contact_factors,
    zone_factor,
)
from app.services.capacity.iso6336_dynamics import (
    DynamicConditions,
    DynamicFactors,
    RunningInGroup,
    compute_dynamic_factors,
)
from app.services.capacity.iso6336_root_strength import RootMaterialGroup

__all__ = [
    "DynamicConditions",
    "DynamicFactors",
    "Iso6336GearResult",
    "Iso6336LoadCase",
    "Iso6336Conditions",
    "RootMaterialGroup",
    "RunningInGroup",
    "compute_dynamic_factors",
    "elasticity_factor",
    "evaluate_iso6336",
    "native_dynamic_factors",
    "single_contact_factors",
    "zone_factor",
]
