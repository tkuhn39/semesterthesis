"""
@module: app.io.ste
@context: I/O layer — STplus (FVA 241) spur-gear input files.
@role: Parse STplus `.ste` files into a typed model and extract the gear-stage
       geometry. STplus stores `$ Section` blocks of `KEY = value(s)` lines
       (whitespace-separated tokens, often pinion/wheel pairs); `#` starts a
       comment. Values are kept as raw tokens so non-numeric entries
       (materials, tools) survive; typed extraction is opt-in.
"""

from pathlib import Path

from pydantic import BaseModel, Field

# (pinion, wheel) — STplus lists gear 1 then gear 2 on a line.
Pair = tuple[float, float]


class SteEntry(BaseModel):
    """A single `KEY = value(s)` line; values are raw whitespace-split tokens."""

    key: str
    values: list[str]


class SteSection(BaseModel):
    """A `$ Name` block with its entries, order preserved."""

    name: str
    entries: list[SteEntry] = Field(default_factory=list)

    def get(self, key: str) -> SteEntry | None:
        """Return the first entry with ``key`` in this section, else None."""
        for entry in self.entries:
            if entry.key == key:
                return entry
        return None


class SteFile(BaseModel):
    """A parsed STplus `.ste` file as an ordered list of sections."""

    sections: list[SteSection] = Field(default_factory=list)

    def section(self, name: str) -> SteSection | None:
        """Return the first section named ``name``, else None."""
        for section in self.sections:
            if section.name == name:
                return section
        return None

    def find(self, key: str) -> SteEntry | None:
        """Return the first entry with ``key`` across all sections, else None."""
        for section in self.sections:
            entry = section.get(key)
            if entry is not None:
                return entry
        return None


def parse_ste(text: str) -> SteFile:
    """Parse STplus `.ste` text into a :class:`SteFile`."""
    sections: list[SteSection] = []
    current: SteSection | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("$"):
            current = SteSection(name=line[1:].strip())
            sections.append(current)
            continue
        if "=" not in line:
            continue
        key, _, rhs = line.partition("=")
        if current is None:
            current = SteSection(name="")
            sections.append(current)
        current.entries.append(SteEntry(key=key.strip(), values=rhs.split()))
    return SteFile(sections=sections)


def load_ste(path: Path) -> SteFile:
    """Load and parse a `.ste` file (Latin-1, as written by STplus)."""
    return parse_ste(path.read_text(encoding="latin-1"))


class SteGearStage(BaseModel):
    """Spur-gear stage geometry extracted from a `.ste`, as (pinion, wheel)."""

    normal_module_mm: float
    teeth: tuple[int, int]
    center_distance_mm: float
    pressure_angle_deg: Pair
    helix_angle_deg: Pair
    face_width_mm: Pair
    profile_shift: Pair
    tip_diameter_mm: Pair


def _floats(ste: SteFile, key: str) -> list[float]:
    entry = ste.find(key)
    if entry is None:
        raise KeyError(f"STplus key not found: {key}")
    return [float(token) for token in entry.values]


def _pair(ste: SteFile, key: str) -> Pair:
    values = _floats(ste, key)
    return (values[0], values[0] if len(values) == 1 else values[1])


def gear_stage_from_ste(ste: SteFile) -> SteGearStage:
    """Extract the spur-gear stage geometry from a parsed `.ste`."""
    teeth = _floats(ste, "ZAEHNEZAHL")
    return SteGearStage(
        normal_module_mm=_floats(ste, "NORMALMODUL")[0],
        teeth=(int(teeth[0]), int(teeth[1])),
        center_distance_mm=_floats(ste, "ACHSABSTAND")[0],
        pressure_angle_deg=_pair(ste, "EINGRIFFSWINKEL"),
        helix_angle_deg=_pair(ste, "SCHRAEGUNGSWINKEL"),
        face_width_mm=_pair(ste, "ZAHNBREITE"),
        profile_shift=_pair(ste, "PROFILVERSCHIEBUNG_N"),
        tip_diameter_mm=_pair(ste, "KOPFKREISDM"),
    )
