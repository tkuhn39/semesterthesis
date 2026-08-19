"""
@module: app.services.material_store
@context: Domain layer — the USER material library (persisted, user-definable).
@role: CRUD for user-defined :class:`Material` records next to the built-in
       ``CATALOG`` (app.services.materials). The user asked for "eine verwendbare
       Datenbank an Materialien": define materials once, pick one per gear, and
       tune the copied properties in the session WITHOUT writing back — so the
       library holds the reference values, the Werkstoff tab holds the working
       copy. Selecting a material stays a frontend concern (the store loads the
       served properties into its editable fields); the capacity chain keeps
       receiving explicit property values (ADR-026 kind dispatch untouched).

Persistence: one JSON object per material under ``materials/user/<slug>.json``
via app.storage (project_rules §17 — the app.database backend is a documented
extension point still at "none", while storage is implemented for local AND
S3-compatible backends). Per-material objects keep concurrent nodes safe
(§18): saves of different materials never race, same-name saves are
last-write-wins. Built-in catalog names are immutable — a user material can
neither shadow nor delete them.
"""

from __future__ import annotations

import logging
import re

from app.services.materials import CATALOG, Material
from app.storage import get_storage

logger = logging.getLogger(__name__)

__all__ = [
    "all_materials",
    "delete_user_material",
    "list_user_materials",
    "save_user_material",
]

_PREFIX = "materials/user/"
_SLUG_STRIP = re.compile(r"[^A-Za-z0-9._-]+")


def _slug(name: str) -> str:
    """Storage-safe file stem for a material name (the true name lives in the JSON)."""
    slug = _SLUG_STRIP.sub("_", name.strip()).strip("._")
    if not slug:
        raise ValueError(f"material name {name!r} has no storable characters")
    return slug


def _key(name: str) -> str:
    return f"{_PREFIX}{_slug(name)}.json"


def list_user_materials() -> list[Material]:
    """All user-defined materials, sorted by name. Unreadable objects are skipped
    with a warning (a broken record must not take the whole catalog down)."""
    storage = get_storage()
    materials: list[Material] = []
    for key in storage.list_keys(_PREFIX):
        if not key.endswith(".json"):
            continue
        try:
            materials.append(Material.model_validate_json(storage.load_bytes(key)))
        except (KeyError, ValueError) as exc:  # pydantic ValidationError is a ValueError
            logger.warning("skipping unreadable user material %r: %s", key, exc)
    return sorted(materials, key=lambda m: m.name.lower())


def save_user_material(material: Material) -> Material:
    """Create or update a user material (upsert by name).

    Built-in catalog names are immutable references — rejected with ValueError.
    A name whose storage slug collides with a DIFFERENT existing user material is
    rejected too (two names must never share one object).
    """
    if material.name in CATALOG:
        raise ValueError(
            f"material {material.name!r} is a built-in catalog entry and cannot be overwritten"
        )
    storage = get_storage()
    key = _key(material.name)
    if storage.exists(key):
        existing = Material.model_validate_json(storage.load_bytes(key))
        if existing.name != material.name:
            raise ValueError(
                f"material name {material.name!r} collides with existing entry "
                f"{existing.name!r} (same storage slug)"
            )
    payload = material.model_copy(update={"source": "user"})
    storage.save_bytes(key, payload.model_dump_json().encode("utf-8"))
    return payload


def delete_user_material(name: str) -> bool:
    """Remove a user material; ``False`` if it does not exist.

    Built-in names raise ValueError (they are not deletable records).
    """
    if name in CATALOG:
        raise ValueError(f"material {name!r} is a built-in catalog entry and cannot be deleted")
    storage = get_storage()
    key = _key(name)
    if not storage.exists(key):
        return False
    storage.delete(key)
    return True


def all_materials() -> dict[str, Material]:
    """Built-in catalog first, then the user library (insertion-ordered).

    A user record whose name equals a built-in (legacy data written before the
    save guard) is ignored — the built-in always wins.
    """
    merged: dict[str, Material] = dict(CATALOG)
    for mat in list_user_materials():
        if mat.name in merged:
            logger.warning("user material %r shadows a built-in entry - ignored", mat.name)
            continue
        merged[mat.name] = mat
    return merged
