"""
@module: app.api.ui_schema
@context: API layer — serves OUR editor schema (FVA-replica tabs, attributes, rules).
@role: One GET endpoint the frontend renders its editor from. The schema is pure data
       (pydantic, see app.services.uimodel) — labels DE/EN, symbols, units, dropdowns,
       store bindings, Berechnungsauswahl methods (tab visibility) and the norm-referenced
       dependency rules that double as glossary entries.
"""

from fastapi import APIRouter

from app.services.uimodel import UiSchema, build_ui_schema

router = APIRouter(prefix="/api", tags=["ui-schema"])

_SCHEMA = build_ui_schema()  # static data — built once at import


@router.get("/ui-schema", response_model=UiSchema)
def ui_schema() -> UiSchema:
    """The editor schema (components → tabs → sections → attribute rows + rules)."""
    return _SCHEMA
