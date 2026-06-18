"""
@module: app.io.rie
@context: I/O layer — RIKOR (FVA 30) load-distribution input files (`.rie`).
@role: Parse the RIKOR `.rie` keyword-block input (shafts, bearings, gear stage,
       corrections, config) into a typed pydantic model, so the native
       load-distribution service (`app.services.loaddist`) reads the *same* inputs
       as the original RIKOR. The `.rie` is the same `$ Section` / `KEY = value`
       family as STplus `.ste`, but a single physical line may carry several
       `KEY = value` pairs (e.g. ``UK = 0 DA = 108 TUAKA = -5975``) and the same
       key repeats across rows (one row per shaft station). Hence a dedicated
       line tokenizer that preserves row grouping, on top of which the typed
       `RikorInput` is assembled. (A REXS-compatible writer lives elsewhere.)
"""

from pathlib import Path

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
# Generic block parse (row-grouped, repeats preserved)                        #
# --------------------------------------------------------------------------- #


class RieRow(BaseModel):
    """One physical line as ordered ``KEY = value(s)`` items (keys unique per row)."""

    items: list[tuple[str, list[str]]] = Field(default_factory=list)

    def get(self, key: str) -> list[str] | None:
        for k, v in self.items:
            if k == key:
                return v
        return None

    def has(self, *keys: str) -> bool:
        present = {k for k, _ in self.items}
        return all(k in present for k in keys)


class RieSection(BaseModel):
    """A ``$ Name`` block with its rows, order preserved (repeated blocks allowed)."""

    name: str
    rows: list[RieRow] = Field(default_factory=list)

    def rows_with(self, key: str) -> list[RieRow]:
        return [r for r in self.rows if r.get(key) is not None]

    def values(self, key: str) -> list[str] | None:
        """Values of the first row that carries ``key``, else None."""
        for row in self.rows:
            found = row.get(key)
            if found is not None:
                return found
        return None

    def scalar(self, key: str) -> str | None:
        """First value of the first row carrying ``key``, else None."""
        vals = self.values(key)
        return vals[0] if vals else None


class RieFile(BaseModel):
    """A parsed `.rie` file as an ordered list of sections."""

    sections: list[RieSection] = Field(default_factory=list)

    def named(self, name: str) -> list[RieSection]:
        """All sections whose name matches ``name`` (case-insensitive)."""
        key = name.casefold()
        return [s for s in self.sections if s.name.casefold() == key]

    def first_named(self, name: str) -> RieSection | None:
        found = self.named(name)
        return found[0] if found else None


def _tokenize(line: str) -> RieRow | None:
    """Tokenize one content line into ordered ``KEY = value(s)`` items.

    Inline comments (``#`` … end of line) are stripped; ``=`` is normalized to a
    standalone token so ``KA=1.5`` and ``KA = 1.5`` parse alike. Values of a key
    run until the next ``KEY =`` token or the end of the line.
    """
    line = line.split("#", 1)[0]
    tokens = line.replace("=", " = ").split()
    if not tokens:
        return None
    items: list[tuple[str, list[str]]] = []
    i = 0
    n = len(tokens)
    while i < n:
        if i + 1 < n and tokens[i + 1] == "=":
            key = tokens[i]
            j = i + 2
            values: list[str] = []
            while j < n and not (j + 1 < n and tokens[j + 1] == "="):
                values.append(tokens[j])
                j += 1
            items.append((key, values))
            i = j
        else:
            i += 1  # stray token without an '=' (rare); skip
    return RieRow(items=items) if items else None


def parse_rie(text: str) -> RieFile:
    """Parse RIKOR `.rie` text into a :class:`RieFile` (sections of rows)."""
    sections: list[RieSection] = []
    current: RieSection | None = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("$"):
            current = RieSection(name=stripped[1:].strip())
            sections.append(current)
            continue
        row = _tokenize(stripped)
        if row is None:
            continue
        if current is None:  # content before any header → anonymous section
            current = RieSection(name="")
            sections.append(current)
        current.rows.append(row)
    return RieFile(sections=sections)


def load_rie(path: Path) -> RieFile:
    """Load and parse a `.rie` file (latin-1 tolerant, like the lab's exports)."""
    return parse_rie(path.read_text(encoding="latin-1"))


# --------------------------------------------------------------------------- #
# Typed RIKOR input model                                                     #
# --------------------------------------------------------------------------- #


def _f(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _i(value: str | None) -> int | None:
    f = _f(value)
    return int(round(f)) if f is not None else None


def _flag(value: str | None) -> bool:
    f = _f(value)
    return f is not None and f != 0.0


class ShaftStation(BaseModel):
    """One cross-section of a stepped shaft: axial position and diameters."""

    position_mm: float  # UK
    outer_diameter_mm: float  # DA
    inner_diameter_mm: float = 0.0  # DI (0 = solid)
    applied_torque_nm: float | None = None  # TUAKA / TUA (drive/resisting torque)


class Shaft(BaseModel):
    """A gear shaft as a stepped beam (stations) with its speed and loads."""

    index: int  # IW
    stations: list[ShaftStation] = Field(default_factory=list)
    speed_min1: float | None = None  # DREHZAHL
    text: str | None = None  # TEXT
    self_weight: bool = False  # EIGENGEWICHT
    origin_offset_mm: float | None = None  # U_0

    @property
    def applied_torque_nm(self) -> float | None:
        for s in self.stations:
            if s.applied_torque_nm is not None:
                return s.applied_torque_nm
        return None


class Bearing(BaseModel):
    """An elastic shaft support (radial/axial stiffness, optional fixed in axial)."""

    shaft_index: int  # IW_I
    mate_index: int | None = None  # IW_A (-1 = housing)
    position_mm: float | None = None  # UK_I
    radial_stiffness_n_per_um: float | None = None  # CS
    tilt_stiffness: float | None = None  # CD
    axial_stiffness_n_per_um: float | None = None  # CAX
    fixed_axial: bool = False  # FESTLAGER


class StageData(BaseModel):
    """The meshing stage that couples two shafts (face-width discretization)."""

    shaft_indices: list[int] = Field(default_factory=list)  # IW
    gear_indices: list[int] = Field(default_factory=list)  # IR
    axis_angle_deg: float = 0.0  # ACHSWIN
    face_steps: int | None = None  # ANZBRTSTP
    f_halpha_min_um: float | None = None  # ABW_FHALPHAMIN
    f_halpha_max_um: float | None = None  # ABW_FHALPHAMAX
    f_hbeta_min_um: float | None = None  # ABW_FHBETAMIN
    f_hbeta_max_um: float | None = None  # ABW_FHBETAMAX


class Gear(BaseModel):
    """One gear of the stage (sits on a shaft at an axial position)."""

    shaft_index: int  # IW
    gear_index: int | None = None  # IR
    normal_module_mm: float | None = None  # MN
    teeth: int | None = None  # Z
    profile_shift: float = 0.0  # X
    helix_angle_deg: float = 0.0  # BETA
    face_width_mm: float | None = None  # B
    tip_diameter_mm: float | None = None  # DNA
    axial_position_mm: float | None = None  # UKA (left face)
    addendum_factor: float | None = None  # HA0
    sigma_flim_mpa: float | None = None  # SIGMAFG
    material: str | None = None  # ZAHNRADWERKSTOFF


class Correction(BaseModel):
    """A flank-line / profile modification on a gear (helix crowning etc.)."""

    shaft_index: int  # IW
    gear_index: int | None = None  # IR
    crowning_um: float | None = None  # CHB_BET
    crowning_additive: bool = False  # CHB_ADD


class RikorConfig(BaseModel):
    """Global run configuration (language, application factor, lubricant)."""

    language: str | None = None  # SPRACHE
    application_factor: float = 1.0  # KA
    lubricant: str | None = None  # SCHMIERSTOFF
    contact_positions: int | None = None  # S_ANZEINGR


class RikorInput(BaseModel):
    """A complete, typed RIKOR `.rie` model (shafts, bearings, stage, gears)."""

    config: RikorConfig = Field(default_factory=RikorConfig)
    shafts: list[Shaft] = Field(default_factory=list)
    bearings: list[Bearing] = Field(default_factory=list)
    stage: StageData | None = None
    gears: list[Gear] = Field(default_factory=list)
    corrections: list[Correction] = Field(default_factory=list)

    def gear_on(self, shaft_index: int) -> Gear | None:
        return next((g for g in self.gears if g.shaft_index == shaft_index), None)

    def bearings_on(self, shaft_index: int) -> list[Bearing]:
        return [b for b in self.bearings if b.shaft_index == shaft_index]

    @classmethod
    def from_rie(cls, rie: RieFile) -> "RikorInput":
        """Assemble the typed model from a parsed :class:`RieFile`."""
        config = _config_from(rie)
        shafts = [_shaft_from(s) for s in rie.named("Welle")]
        bearings = [_bearing_from(s) for s in rie.named("LAGER")]
        gears = [_gear_from(s) for s in rie.named("Zahnrad")]
        corrections = [_correction_from(s) for s in rie.named("Korrektur")]
        stage_section = rie.first_named("Stufendaten")
        stage = _stage_from(stage_section) if stage_section else None
        return cls(
            config=config,
            shafts=shafts,
            bearings=bearings,
            stage=stage,
            gears=gears,
            corrections=corrections,
        )

    @classmethod
    def load(cls, path: Path) -> "RikorInput":
        return cls.from_rie(load_rie(path))


def _config_from(rie: RieFile) -> RikorConfig:
    konfig = rie.first_named("Konfig")
    getriebe = rie.first_named("GETRIEBE")
    ka = _f(getriebe.scalar("KA")) if getriebe else None
    return RikorConfig(
        language=konfig.scalar("SPRACHE") if konfig else None,
        application_factor=ka if ka is not None else 1.0,
        lubricant=getriebe.scalar("SCHMIERSTOFF") if getriebe else None,
        contact_positions=_i(konfig.scalar("S_ANZEINGR")) if konfig else None,
    )


def _shaft_from(section: RieSection) -> Shaft:
    stations = [
        ShaftStation(
            position_mm=_f(row.get("UK")[0]) or 0.0,  # type: ignore[index]
            outer_diameter_mm=_f((row.get("DA") or ["0"])[0]) or 0.0,
            inner_diameter_mm=_f((row.get("DI") or ["0"])[0]) or 0.0,
            applied_torque_nm=_f((row.get("TUAKA") or row.get("TUA") or [""])[0]),
        )
        for row in section.rows_with("UK")
        if row.has("DA")
    ]
    text_vals = section.values("TEXT")
    return Shaft(
        index=_i(section.scalar("IW")) or 0,
        stations=stations,
        speed_min1=_f(section.scalar("DREHZAHL")),
        text=" ".join(text_vals) if text_vals else None,
        self_weight=_flag(section.scalar("EIGENGEWICHT")),
        origin_offset_mm=_f(section.scalar("U_0")),
    )


def _bearing_from(section: RieSection) -> Bearing:
    return Bearing(
        shaft_index=_i(section.scalar("IW_I")) or 0,
        mate_index=_i(section.scalar("IW_A")),
        position_mm=_f(section.scalar("UK_I")),
        radial_stiffness_n_per_um=_f(section.scalar("CS")),
        tilt_stiffness=_f(section.scalar("CD")),
        axial_stiffness_n_per_um=_f(section.scalar("CAX")),
        fixed_axial=_flag(section.scalar("FESTLAGER")),
    )


def _gear_from(section: RieSection) -> Gear:
    return Gear(
        shaft_index=_i(section.scalar("IW")) or 0,
        gear_index=_i(section.scalar("IR")),
        normal_module_mm=_f(section.scalar("MN")),
        teeth=_i(section.scalar("Z")),
        profile_shift=_f(section.scalar("X")) or 0.0,
        helix_angle_deg=_f(section.scalar("BETA")) or 0.0,
        face_width_mm=_f(section.scalar("B")),
        tip_diameter_mm=_f(section.scalar("DNA")),
        axial_position_mm=_f(section.scalar("UKA")),
        addendum_factor=_f(section.scalar("HA0")),
        sigma_flim_mpa=_f(section.scalar("SIGMAFG")),
        material=section.scalar("ZAHNRADWERKSTOFF"),
    )


def _correction_from(section: RieSection) -> Correction:
    return Correction(
        shaft_index=_i(section.scalar("IW")) or 0,
        gear_index=_i(section.scalar("IR")),
        crowning_um=_f(section.scalar("CHB_BET")),
        crowning_additive=_flag(section.scalar("CHB_ADD")),
    )


def _stage_from(section: RieSection) -> StageData:
    iw = section.values("IW") or []
    ir = section.values("IR") or []
    return StageData(
        shaft_indices=[v for v in (_i(x) for x in iw) if v is not None],
        gear_indices=[v for v in (_i(x) for x in ir) if v is not None],
        axis_angle_deg=_f(section.scalar("ACHSWIN")) or 0.0,
        face_steps=_i(section.scalar("ANZBRTSTP")),
        f_halpha_min_um=_f(section.scalar("ABW_FHALPHAMIN")),
        f_halpha_max_um=_f(section.scalar("ABW_FHALPHAMAX")),
        f_hbeta_min_um=_f(section.scalar("ABW_FHBETAMIN")),
        f_hbeta_max_um=_f(section.scalar("ABW_FHBETAMAX")),
    )
