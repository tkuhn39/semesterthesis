"""
@package: app.services.uimodel
@context: Domain layer — OUR editor schema (the FVA-Workbench replica's single source for
          attribute definitions, tab layouts and dependency rules).
@role: The FVA installation's declarative UI (produktmodell_SI.xml + messages) is mined as a
       WORDING reference (`00_development_documentation/fva_label_reference.json`), but the
       binding model is defined HERE in pydantic — norm-correct and slot-consistent (user
       decision 2026-07-04: FVA itself has defects — tool-generated root fillet, swapped
       Ritzel/Rad labels — so the norm and our validated geometry win, ADR-011). The frontend
       renders its editor tabs from `/api/ui-schema`; every attribute carries DE/EN labels,
       symbol, unit, norm reference and its store binding, and doubles as the glossary
       (Legende) entry.
"""

from app.services.uimodel.components import build_ui_schema
from app.services.uimodel.schema import (
    AttributeDef,
    AttrOption,
    ComponentDef,
    DependencyRule,
    RowRef,
    SectionDef,
    TabDef,
    UiSchema,
)

__all__ = [
    "AttrOption",
    "AttributeDef",
    "ComponentDef",
    "DependencyRule",
    "RowRef",
    "SectionDef",
    "TabDef",
    "UiSchema",
    "build_ui_schema",
]
