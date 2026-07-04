"""
@module: 20_antigravity_scripts.extract_fva_labels
@context: One-shot extraction — the installed FVA Workbench 10.1.1 ships its UI declaratively
          (product model XML + DE/EN message catalogs + combo lists). We mine those as a
          NAMING/WORDING REFERENCE for our replica.
@role: Emit ``00_development_documentation/fva_label_reference.json`` with, per component of
       interest, every attribute's pmid, symbol, unit, default, precision, DE/EN label and
       dropdown options. IMPORTANT (user decision 2026-07-04): this is a *Vorlage* only —
       the binding attribute/dependency model is OUR OWN pydantic schema in
       ``40_backend/app/services/uimodel`` (FVA itself has known defects, e.g. the
       tool-generated root fillet and swapped Ritzel/Rad labels in places; the norm and our
       validated geometry win, ADR-011). Read-only against the installation.

Run from ``20_code/``:  python 20_antigravity_scripts/extract_fva_labels.py
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

FVA = Path(r"C:\Program Files\FVA-Workbench-10.1.1-x64\plugins")
_PM = FVA / "de.fva.workbench.core.productmodel_6.0.0"
PRODUCT_MODEL = _PM / "doc" / "pm" / "produktmodell_SI.xml"
COMBOS = _PM / "doc" / "combo" / "pm_combo.xml"
MSG_DE = _PM / "nl" / "pm_messages_de.properties"
MSG_EN = _PM / "nl" / "pm_messages.properties"

_DOCS = Path(__file__).resolve().parents[1] / "00_development_documentation"
OUT = _DOCS / "fva_label_reference.json"

#: components we replicate (model-tree node types; discovered from the filter layouts)
COMPONENTS = {
    "cylindrical_mesh",  # Stirnradstufe
    "cylindrical_gear",  # Stirnrad (Stahlritzel / Kunststoffrad)
    "gear_unit",  # Getriebeeinheit
    "gear_correction",  # Flankenmodifikation
    "wheel_body_cylindrical_gear",  # Radkörper Stirnrad
    "force",  # Belastung
    "lubricant",  # Schmierstoff
    "material",  # Werkstoff
}


_UNICODE_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")


def load_properties(path: Path) -> dict[str, str]:
    """Java .properties → dict; decode \\uXXXX plus the escaped separators (\\: \\= \\#)."""
    out: dict[str, str] = {}
    with path.open("r", encoding="latin-1") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.lstrip().startswith(("#", "!")) or "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = _UNICODE_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), value)
            for esc, plain in (("\\:", ":"), ("\\=", "="), ("\\#", "#"), ("\\n", "\n")):
                value = value.replace(esc, plain)
            out[key.strip()] = value
    return out


def parse_combos(path: Path) -> dict[str, list[dict[str, str]]]:
    """pm_combo.xml → {comboId: [{itemId, value}]} (labels resolved later)."""
    root = ET.parse(path).getroot()
    combos: dict[str, list[dict[str, str]]] = {}
    for combo in root.iter():
        if not combo.tag.lower().endswith("combo"):
            continue
        cid = combo.get("id")
        if cid is None:
            continue
        items = []
        for item in combo:
            iid = item.get("id")
            if iid is not None:
                items.append({"itemId": iid, "value": item.get("value", "")})
        if items:
            combos[cid] = items
    return combos


def main() -> None:
    de = load_properties(MSG_DE)
    en = load_properties(MSG_EN)
    combos = parse_combos(COMBOS)

    def label(dictionary_id: str | None) -> dict[str, str | None]:
        if not dictionary_id:
            return {"de": None, "en": None}
        return {"de": de.get(dictionary_id), "en": en.get(dictionary_id)}

    def combo_options(value_list_id: str) -> list[dict[str, str | None]]:
        opts = []
        for item in combos.get(value_list_id, []):
            key = f"combo_{value_list_id}_{item['itemId']}"
            opts.append({"value": item["value"], "de": de.get(key), "en": en.get(key)})
        return opts

    tree = ET.parse(PRODUCT_MODEL)

    def attr_entry(attr: ET.Element) -> dict:
        fmt = attr.find("format")
        entry = {
            "attrNr": attr.get("attrNr"),
            "valueType": attr.get("valueType"),
            "symbol": attr.findtext("symbol"),
            "category": attr.findtext("categoryId"),
            "categoryLabel": label(attr.findtext("categoryId")),
            "label": label(attr.findtext("dictionaryId")),
            "unit": attr.findtext("attributeValue/defaultUnit"),
            "default": attr.findtext("attributeValue/value"),
            "precision": fmt.get("precision") if fmt is not None else None,
        }
        vlist = attr.findtext("valueListId")
        if vlist:
            entry["options"] = combo_options(vlist)
        return entry

    # collect ALL components first: own attributes + superComp inheritance chains
    own: dict[str, dict[str, dict]] = {}
    supers: dict[str, list[str]] = {}
    for comp in tree.getroot().iter("component"):
        pmid = comp.get("pmid") or comp.get("id") or ""
        if not pmid:
            continue
        own[pmid] = {
            a.get("pmid"): attr_entry(a) for a in comp.iter("attribute") if a.get("pmid")
        }
        supers[pmid] = [s.get("pmid", "") for s in comp.iter("superComp") if s.get("pmid")]

    def resolved(pmid: str, seen: frozenset[str] = frozenset()) -> dict[str, dict]:
        if pmid in seen or pmid not in own:
            return {}
        merged: dict[str, dict] = {}
        for sup in supers.get(pmid, []):
            merged.update(resolved(sup, seen | {pmid}))
        merged.update(own[pmid])  # own attributes override inherited ones
        return merged

    result: dict[str, dict] = {}
    for pmid in sorted(COMPONENTS & set(own)):
        # keep only attributes with a user-facing label — internals never appear in the UI
        attrs = {k: v for k, v in resolved(pmid).items() if v["label"]["de"] or v["label"]["en"]}
        result[pmid] = {
            "superComps": supers.get(pmid, []),
            "count": len(attrs),
            "attributes": attrs,
        }

    found = {k: v["count"] for k, v in result.items()}
    missing = COMPONENTS - set(result)
    print("components found:", found)
    if missing:
        print("NOT FOUND:", sorted(missing))
        hints = [p for p in own if re.search("load|belast|force", p, re.I)]
        print("  candidates containing load/belast/force:", hints[:20])
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} kB)")


if __name__ == "__main__":
    main()
