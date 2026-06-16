"""
@module: app.io.rexs
@context: I/O layer — REXS gear-model exchange files (XML).
@role: Read REXS models (as written e.g. by RIKOR) into typed pydantic objects.
       A REXS file is `<model>` → `<components>` → `<component id/name/type>` →
       `<attribute id/unit>`; an attribute is either scalar text, an `<array>` of
       `<c>` cells, or a `<matrix>` of `<r>`/`<c>`. Cell values are kept as raw
       strings (so booleans/ints/strings survive); numeric access is opt-in.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from pydantic import BaseModel, Field


def _tag(element: ET.Element) -> str:
    """Local tag name, namespace stripped."""
    return element.tag.rsplit("}", 1)[-1]


def _cell(element: ET.Element) -> str:
    return (element.text or "").strip()


class RexsAttribute(BaseModel):
    """A REXS `<attribute>`: scalar text, an array, or a matrix (raw strings)."""

    id: str
    unit: str | None = None
    text: str | None = None
    array: list[str] | None = None
    matrix: list[list[str]] | None = None

    def as_float(self) -> float:
        """Scalar value as float."""
        if self.text is None:
            raise ValueError(f"attribute {self.id!r} is not a scalar")
        return float(self.text)

    def as_floats(self) -> list[float]:
        """Array value as floats."""
        if self.array is None:
            raise ValueError(f"attribute {self.id!r} is not an array")
        return [float(cell) for cell in self.array]

    def as_float_matrix(self) -> list[list[float]]:
        """Matrix value as floats."""
        if self.matrix is None:
            raise ValueError(f"attribute {self.id!r} is not a matrix")
        return [[float(cell) for cell in row] for row in self.matrix]


class RexsComponent(BaseModel):
    """A REXS `<component>` with its attributes (order and duplicates preserved)."""

    id: int
    name: str | None = None
    type: str
    attributes: list[RexsAttribute] = Field(default_factory=list)

    def attr(self, attr_id: str) -> RexsAttribute | None:
        """First attribute with ``attr_id``, else None (ids may repeat)."""
        for attribute in self.attributes:
            if attribute.id == attr_id:
                return attribute
        return None


class RexsModel(BaseModel):
    """A parsed REXS `<model>` and its components."""

    application_id: str | None = None
    application_version: str | None = None
    version: str | None = None
    components: list[RexsComponent] = Field(default_factory=list)

    def components_of_type(self, type_: str) -> list[RexsComponent]:
        """All components of the given REXS ``type``."""
        return [c for c in self.components if c.type == type_]

    def component(
        self, *, id_: int | None = None, type_: str | None = None
    ) -> RexsComponent | None:
        """First component matching ``id_`` and/or ``type_``, else None."""
        for component in self.components:
            if id_ is not None and component.id != id_:
                continue
            if type_ is not None and component.type != type_:
                continue
            return component
        return None


def _parse_attribute(element: ET.Element) -> RexsAttribute:
    array_el = next((c for c in element if _tag(c) == "array"), None)
    matrix_el = next((c for c in element if _tag(c) == "matrix"), None)
    array: list[str] | None = None
    matrix: list[list[str]] | None = None
    text: str | None = None
    if matrix_el is not None:
        matrix = [
            [_cell(c) for c in row if _tag(c) == "c"] for row in matrix_el if _tag(row) == "r"
        ]
    elif array_el is not None:
        array = [_cell(c) for c in array_el if _tag(c) == "c"]
    else:
        text = (element.text or "").strip() or None
    return RexsAttribute(
        id=element.get("id", ""), unit=element.get("unit"), text=text, array=array, matrix=matrix
    )


def _from_root(root: ET.Element) -> RexsModel:
    components: list[RexsComponent] = []
    components_el = next((c for c in root if _tag(c) == "components"), None)
    if components_el is not None:
        for comp in components_el:
            comp_id = comp.get("id")
            if _tag(comp) != "component" or comp_id is None:
                continue
            attributes = [_parse_attribute(a) for a in comp if _tag(a) == "attribute"]
            components.append(
                RexsComponent(
                    id=int(comp_id),
                    name=comp.get("name"),
                    type=comp.get("type", ""),
                    attributes=attributes,
                )
            )
    return RexsModel(
        application_id=root.get("applicationId"),
        application_version=root.get("applicationVersion"),
        version=root.get("version"),
        components=components,
    )


def parse_rexs(text: str) -> RexsModel:
    """Parse REXS XML text into a :class:`RexsModel`."""
    return _from_root(ET.fromstring(text.encode("utf-8")))


def load_rexs(path: Path) -> RexsModel:
    """Load and parse a `.rexs` file (encoding from its XML declaration)."""
    return _from_root(ET.fromstring(path.read_bytes()))
