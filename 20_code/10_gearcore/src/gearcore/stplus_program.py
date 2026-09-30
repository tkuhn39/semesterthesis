"""What STplus itself ships and presets: tool databases and defaults, kept with their provenance.

User decision 2026-09-30 (ADR-109): nothing STplus offered may get lost. The tool databases of the
installation are packaged verbatim (``data/stplus_program/tool_database_*.txt``), the defaults of
the program are transcribed from the manual and from probe runs (``defaults.yaml``), and every
record says which program version it comes from (``provenance.yaml``).

None of this is a norm. gearcore applies no STplus default silently: a caller asks for a record
or a default by name and gets it labelled with program and version.

Tool records. A record keeps every entry of the database as written. Its ``profile`` is the
``ToolProfile`` of the factor keys, which is what STplus computes with (probe
``tool_contradicting_record``). A record has no profile when the contract would have to guess or
bend a value: no tip rounding given (STplus presets 0,25), a factor beyond the contract bounds
(STplus reduces it to the geometric limit), a shaper or profile tool. Absolute values that
contradict the factors are reported as issues. ``WERKZEUGTYP`` is kept as written; the manual
does not explain the key.
"""

from functools import lru_cache
from types import MappingProxyType
from typing import Any, Literal

import yaml
from pydantic import Field, ValidationError

from gearcore.data import data_path
from gearcore.errors import InputRangeError, NotSupportedError, ParseError
from gearcore.io.ste import SteSection, parse_ste, tool_from_section
from gearcore.models.common import FrozenModel
from gearcore.models.inputs import ToolProfile

DIRECTORY = "stplus_program"
ABSOLUTE_VALUES: MappingProxyType[str, str] = MappingProxyType(
    {
        "KOPFHOEHE": "KOPFHOEHENFAKTOR",
        "FUSSHOEHE": "FUSSHOEHENFAKTOR",
        "FUSSFORMHOEHE": "FUSSFORMHOEHENFAKTOR",
        "KOPFABRUNDUNGSRADIUS": "KOPFABRUNDUNGSFAKTOR",
    }
)
"""Absolute tool dimension in mm -> its module factor (manual Bild 4.174, p. 185)."""

CONTRADICTION_MM = 1.0e-3
"""Absolute value and factor times module agree within the digits the database prints."""


class ProgramFile(FrozenModel):
    """One file of the installation that is packaged."""

    stored: str
    original: str
    role: str
    bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    stored_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    line_endings: str
    encoding: str
    modified: str


class ProgramProvenance(FrozenModel):
    """Program, version and release the packaged STplus data comes from."""

    program: str
    version: str
    release: str
    publisher: str
    evidence: str
    installation: str
    manual: dict[str, str]
    imported: str
    note: str
    files: tuple[ProgramFile, ...]

    @property
    def label(self) -> str:
        """``'STplus 11.1F (Freigabe 01.12.2025)'``: the label every record carries."""
        return f"{self.program} {self.version} (Freigabe {self.release})"


class StplusToolRecord(FrozenModel):
    """A tool of an STplus tool database, as written, with its provenance."""

    name: str
    database: Literal["local", "global"]
    origin: str
    """Program, version, release and file the record comes from."""
    entries: tuple[tuple[str, str], ...]
    """Every ``KEY = value`` of the record in the order of the file."""
    profile: ToolProfile | None
    """The contract of the factor keys; ``None`` where ``issues`` say why there is none."""
    issues: tuple[str, ...] = ()


class ManualPassage(FrozenModel):
    page: int = Field(ge=1)
    text: str = Field(min_length=1)


class StplusDefault(FrozenModel):
    """A default of STplus with its evidence."""

    name: str
    origin: str
    quantity: str | None
    input_key: str | None
    value: float | str | None
    unit: str
    rule: str | None
    applies_to: Literal["user interface", "batch input", "both"]
    manual: ManualPassage | None
    probe: str | None
    status: Literal["verified", "located"]
    note: str | None
    tool: dict[str, float] | None = None
    file: str | None = None
    """Packaged file of the installation that is the evidence (``input_key_register.txt``)."""


def _load_yaml(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(data_path(DIRECTORY, name).read_text(encoding="utf-8"))
    return loaded


@lru_cache(maxsize=1)
def program_provenance() -> ProgramProvenance:
    """Program version and files of the packaged STplus data."""
    return ProgramProvenance(**_load_yaml("provenance.yaml"))


def _number(section: SteSection, key: str) -> float | None:
    entry = section.get(key)
    return None if entry is None else entry.number(0)


def _contradictions(section: SteSection) -> list[str]:
    module = _number(section, "WKZ_NORMALMODUL")
    found: list[str] = []
    for absolute_key, factor_key in ABSOLUTE_VALUES.items():
        absolute, factor = _number(section, absolute_key), _number(section, factor_key)
        if absolute is None or factor is None or module is None:
            continue
        if abs(factor * module - absolute) > CONTRADICTION_MM:
            found.append(
                f"{absolute_key} = {absolute:g} mm contradicts {factor_key} = {factor:g} at "
                f"WKZ_NORMALMODUL = {module:g} ({factor * module:g} mm); STplus computes with the "
                "factor (probe tool_contradicting_record)"
            )
    return found


def _record(
    section: SteSection, database: Literal["local", "global"], origin: str
) -> StplusToolRecord:
    issues = _contradictions(section)
    profile: ToolProfile | None = None
    try:
        profile = tool_from_section(section)
    except (ParseError, NotSupportedError) as error:
        issues.append(f"no tool contract: {error}")
    except ValidationError as error:
        reasons = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
        issues.append(f"no tool contract: {reasons}")
    return StplusToolRecord(
        name=section.name,
        database=database,
        origin=origin,
        entries=tuple((entry.key, " ".join(entry.values)) for entry in section.entries),
        profile=profile,
        issues=tuple(issues),
    )


@lru_cache(maxsize=1)
def tool_database() -> MappingProxyType[str, StplusToolRecord]:
    """Every record of the packaged tool databases by name: local database first, then global.

    STplus searches its tool files in this order (``Werkzeugdatei_lokal``, ``Werkzeugdatei_global``
    of ``stplus.cfg``); a name of the local database hides the same name of the global one.
    """
    provenance = program_provenance()
    records: dict[str, StplusToolRecord] = {}
    for file in provenance.files:
        if not file.role.startswith("Werkzeugdatei"):
            continue
        database: Literal["local", "global"] = "local" if file.role.endswith("lokal") else "global"
        text = data_path(DIRECTORY, file.stored).read_text(encoding=file.encoding)
        for section in parse_ste(text, path=file.original).sections:
            if section.name.upper() in {"ANFANG", "ENDE"} or section.name in records:
                continue
            origin = f"{provenance.label}, {file.original}"
            records[section.name] = _record(section, database, origin)
    return MappingProxyType(records)


def stplus_tool(name: str) -> ToolProfile:
    """The tool contract of the database record ``name``.

    An unknown name is an ``InputRangeError``; a record that is no valid contract is a
    ``NotSupportedError`` that names the reasons (gearcore does not apply the corrections STplus
    makes silently).
    """
    records = tool_database()
    if not isinstance(name, str) or name not in records:
        raise InputRangeError(
            f"unknown tool {name!r} in the STplus tool databases; packaged: {sorted(records)}"
        )
    record = records[name]
    if record.profile is None:
        raise NotSupportedError(f"tool {name!r} ({record.origin}): " + "; ".join(record.issues))
    return record.profile


@lru_cache(maxsize=1)
def stplus_defaults() -> MappingProxyType[str, StplusDefault]:
    """The defaults of STplus by name, each labelled with program and version."""
    origin = program_provenance().label
    loaded = _load_yaml("defaults.yaml")["defaults"]
    return MappingProxyType(
        {name: StplusDefault(name=name, origin=origin, **entry) for name, entry in loaded.items()}
    )


def stplus_default(name: str) -> StplusDefault:
    """The default ``name``; an unknown name is an ``InputRangeError``."""
    defaults = stplus_defaults()
    if not isinstance(name, str) or name not in defaults:
        raise InputRangeError(f"unknown STplus default {name!r}; known: {sorted(defaults)}")
    return defaults[name]


def stplus_default_tool() -> ToolProfile:
    """The hob STplus uses when no tool is given (probe ``defaults_minimal``), as a named tool.

    Module and profile angle are those of the gear (``None`` in the contract). A caller that wants
    the old STplus behaviour asks for this tool explicitly; gearcore never falls back on it.
    """
    default = stplus_default("default_rack_tool")
    if default.tool is None:
        raise ParseError("defaults.yaml: default_rack_tool carries no tool factors")
    return ToolProfile(name=f"{default.origin} default tool", **default.tool)


REGISTER_END = "# Ende der konfigurierbaren Eingabedaten"
"""Comment line of ``bin/DEFAULT.STY`` after which program-internal control data follows."""


def input_key_register() -> tuple[tuple[str, str], ...]:
    """Every entry ``(input key, register default)`` of the configurable input data of
    ``bin/DEFAULT.STY``, in the order of the file.

    The register is an INI-like list ``[KEY]`` / ``DEFAULT=value``; six keys appear twice. The
    program-internal control data after the line ``REGISTER_END`` ("NICHT VERAENDERN") is kept in
    the packaged file and not returned. Whether the program uses the entries as defaults of the
    computation is not documented.
    """
    text = data_path(DIRECTORY, "input_key_register.txt").read_text(encoding="latin-1")
    if REGISTER_END not in text:
        raise ParseError(
            "input key register: the end mark of the configurable input data is missing"
        )
    entries: list[tuple[str, str]] = []
    key: str | None = None
    for number, raw in enumerate(text.split(REGISTER_END, 1)[0].splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]") and key is None:
            key = line[1:-1]
        elif line.startswith("DEFAULT=") and key is not None:
            entries.append((key, line.removeprefix("DEFAULT=")))
            key = None
        else:
            raise ParseError(f"input key register line {number}: cannot read {line!r}")
    if key is not None:
        raise ParseError(f"input key register: key {key} has no DEFAULT entry")
    return tuple(entries)


def probe_listing(name: str) -> str:
    """The listing of the probe run ``name`` (``probes/<name>/report.sta.txt``)."""
    base = data_path(DIRECTORY, "probes")
    known = sorted(path.name for path in base.iterdir() if path.is_dir())
    if not isinstance(name, str) or name not in known:
        raise InputRangeError(f"unknown STplus probe {name!r}; packaged: {known}")
    return (base / name / "report.sta.txt").read_text(encoding="latin-1")
