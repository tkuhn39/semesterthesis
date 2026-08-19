"""
@module: app.api.ui_schema
@context: API layer — serves OUR editor schema (FVA-replica tabs, attributes, rules).
@role: One GET endpoint the frontend renders its editor from. The schema is pure data
       (pydantic, see app.services.uimodel) — labels DE/EN, symbols, units, dropdowns,
       store bindings, Berechnungsauswahl methods (tab visibility) and the norm-referenced
       dependency rules that double as glossary entries.

The schema is static EXCEPT the Werkstoff name options: the user material library
(app.services.material_store) grows at runtime, so ``mat_name`` options are refreshed
per request from built-ins + user records (the static definition stays the built-in
seed — the drift-guard test in tests/test_materials.py pins that seed).
"""

from fastapi import APIRouter

from app.services.material_store import all_materials
from app.services.uimodel import AttrOption, UiSchema, build_ui_schema

router = APIRouter(prefix="/api", tags=["ui-schema"])

_SCHEMA = build_ui_schema()  # static data — built once at import


def _with_material_options(schema: UiSchema) -> UiSchema:
    """The schema with ``mat_name`` options set to the CURRENT material names."""
    options = [AttrOption(value=name, label_de=name, label_en=name) for name in all_materials()]
    base = schema.attributes["mat_name"]
    if base.options is not None and [o.value for o in base.options] == [o.value for o in options]:
        return schema  # no user materials beyond the seed — serve the cached object
    attributes = dict(schema.attributes)
    attributes["mat_name"] = base.model_copy(update={"options": options})
    return schema.model_copy(update={"attributes": attributes})


@router.get("/ui-schema", response_model=UiSchema)
def ui_schema() -> UiSchema:
    """The editor schema (components → tabs → sections → attribute rows + rules)."""
    return _with_material_options(_SCHEMA)
