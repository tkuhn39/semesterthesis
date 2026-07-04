"""
@module: app.services.uimodel.schema
@context: Domain layer — pydantic models of OUR editor schema (attributes, tabs, rules).
@role: Typed building blocks the component definitions are written in. Design points:

       * **Binding**: every editable attribute names a dot-path into the frontend store
         (``stage.normal_module_mm``, ``operating.pinion_torque_nm``, ``fem.fasten_bore``,
         ``calc.vdi_2736_2014`` …); computed attributes name the response path they read
         (``geometry.working_center_distance_mm``). The store shape is the SSOT contract
         between backend schema and frontend renderer.
       * **Per-gear columns**: FVA renders one value column per gear (Stahlritzel [8] /
         Kunststoffrad [9]) — ``per_gear=True`` attributes carry a binding pair.
       * **Visibility**: tabs may name the Berechnungsauswahl method that switches them on
         (``visible_if_method``), replicating the FVA behaviour where e.g. the
         "Dynamisches Abwälzen (FEM)" tab only exists while FVA 892 is selected.
       * **Dependency rules** are declarative and norm-referenced — the frontend evaluates
         them to lock/compute fields; the glossary lists them (user decision: every
         relation documented, parameter → formula → affects …).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AttrKind = Literal["float", "int", "bool", "enum", "text", "action", "path"]


class AttrOption(BaseModel):
    """One dropdown option (value stored, labels shown)."""

    value: str
    label_de: str
    label_en: str


class AttributeDef(BaseModel):
    """One editor attribute — also the glossary (Legende) entry for that parameter."""

    id: str
    label_de: str
    label_en: str
    symbol: str | None = None  # Formelzeichen (the FVA "Fz" column)
    unit: str | None = None  # display unit: mm, °, µm, N/mm², kW, 1/min, …
    kind: AttrKind = "float"
    precision: int | None = None
    options: list[AttrOption] | None = None
    per_gear: bool = False  # one value column per gear (slot order, ADR-021)
    computed: bool = False  # grey/locked — produced by the backend, never typed
    # store binding (dot-path); per_gear attributes carry [gear1, gear2] bindings
    binding: str | None = None
    bindings: tuple[str, str] | None = None
    norm_ref: str | None = None  # e.g. "DIN 21771", "ISO 6336-1:2019 §6", "VDI 2736-2"
    info_de: str | None = None  # short glossary/help text (Legende)
    info_en: str | None = None
    step: float | None = None
    min: float | None = None
    max: float | None = None


class RowRef(BaseModel):
    """A row in a section — an attribute reference plus row-local behaviour."""

    attr: str
    # row only rendered when this store path is truthy (dropdown-dependent fields)
    visible_if: str | None = None
    # row locked (grey) when this store path is truthy
    locked_if: str | None = None


class SectionDef(BaseModel):
    """A collapsible section ("Hauptgeometrie", "Fesselung", …) of an editor tab."""

    id: str
    title_de: str
    title_en: str
    rows: list[RowRef] = Field(default_factory=list)
    info_de: str | None = None  # yellow info banner text (FVA style)
    info_en: str | None = None
    visible_if: str | None = None


class TabDef(BaseModel):
    """One editor tab of a model-tree component ("Geometrie", "Toleranzen", …)."""

    id: str
    title_de: str
    title_en: str
    sections: list[SectionDef] = Field(default_factory=list)
    # only rendered while this Berechnungsauswahl method is selected (calc.<id> truthy);
    # None = always visible. State is preserved while hidden (user decision 2026-07-04).
    visible_if_method: str | None = None


class ComponentDef(BaseModel):
    """A model-tree node type with its editor tabs (Getriebeeinheit, Stirnradstufe, …)."""

    id: str
    label_de: str
    label_en: str
    tabs: list[TabDef] = Field(default_factory=list)


class DependencyRule(BaseModel):
    """A norm-based coupling: fixing/choosing one thing locks or derives others.

    ``when`` and ``targets`` are store paths; the frontend applies ``effect`` to every
    target while ``when`` is truthy (or equals ``when_value``). Each rule is listed in
    the glossary with its norm reference (user decision: the whole system stays a
    consistent norm-active system — no orphaned couplings).
    """

    id: str
    when: str
    when_value: str | bool | float | None = None
    effect: Literal["lock", "hide", "show", "compute"]
    targets: list[str]
    description_de: str
    description_en: str
    norm_ref: str | None = None


class CalcMethod(BaseModel):
    """One row of the Berechnungsauswahl checkbox matrix."""

    id: str  # store path suffix: calc.<id>
    label_de: str
    label_en: str
    group_de: str
    group_en: str
    implemented: bool = False  # unimplemented methods render greyed out (user decision)
    always_on: bool = False  # ISO 6336 + VDI 2736: the Stufenvariation needs them complete
    default_on: bool = False
    # editor tabs this method switches on (component id, tab id)
    enables_tabs: list[tuple[str, str]] = Field(default_factory=list)


class UiSchema(BaseModel):
    """The complete editor schema served to the frontend (`/api/ui-schema`)."""

    version: str
    components: list[ComponentDef]
    attributes: dict[str, AttributeDef]  # id → definition (shared across components)
    rules: list[DependencyRule]
    methods: list[CalcMethod]
