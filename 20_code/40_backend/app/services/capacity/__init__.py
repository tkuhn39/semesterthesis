"""
@package: app.services.capacity
@context: Domain layer — analytical tooth load capacity.
@role: Steel gears per **DIN 3990** and plastic gears per **VDI 2736**, sharing the
       geometry (``app.services.geometry``) and materials (``app.services.materials``).
       The stresses are exact vs the reference tools; load/dynamic/life factors are
       typed inputs (graceful defaults), to be computed or supplied per case.
"""

from app.services.capacity.din3990 import (
    Din3990GearResult,
    Din3990LoadCase,
    Iso6336Conditions,
    elasticity_factor,
    evaluate_din3990,
    single_contact_factors,
    zone_factor,
)
from app.services.capacity.iso6336_root_strength import RootMaterialGroup

__all__ = [
    "Din3990GearResult",
    "Din3990LoadCase",
    "Iso6336Conditions",
    "RootMaterialGroup",
    "elasticity_factor",
    "evaluate_din3990",
    "single_contact_factors",
    "zone_factor",
]
