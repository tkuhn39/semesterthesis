"""
@module: app.services.geometry
@context: Domain layer — spur/helical gear geometry.
@role: Compute the involute gear-stage geometry (reference/base/working-pitch
       diameters, transverse and working pressure angle, center distance) from
       the defining parameters. Validated against STplus output.
"""

from app.services.geometry.gear import GearStage

__all__ = ["GearStage"]
