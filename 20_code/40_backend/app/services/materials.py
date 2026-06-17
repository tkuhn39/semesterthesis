"""
@module: app.services.materials
@context: Domain layer — gear materials for the capacity methods.
@role: A typed material model shared by the steel (DIN 3990) and plastic
       (VDI 2736) tooth-capacity methods. Steel carries the DIN 3990 endurance
       limits; plastic additionally carries the VDI 2736 specifics (allowable
       temperature, wear coefficient, and — where available — the temperature-
       and cycle-dependent strength curves).

Design rule (from the project): missing *non-essential* fields must never block a
calculation — a capacity sub-result that needs an absent field is reported as a
warning and skipped, the rest still runs. So most fields are optional; the
consuming method decides what it strictly needs.
"""

from enum import StrEnum

from pydantic import BaseModel

from app.io.ste import SteFile, SteSection


class MaterialKind(StrEnum):
    """Whether a gear body is metal (DIN 3990) or polymer (VDI 2736)."""

    STEEL = "steel"
    PLASTIC = "plastic"


class StrengthPoint(BaseModel):
    """One point of a temperature/cycle-dependent strength curve (VDI 2736 plastics)."""

    temperature_c: float
    cycles: float
    stress_mpa: float


class Material(BaseModel):
    """Elastic and strength data for one gear material.

    Lengths/stresses in N/mm² (= MPa). Endurance limits are optional so a partly
    specified material (e.g. plastic without a wear coefficient) still loads and
    only blocks the sub-results that truly need the missing value.
    """

    name: str
    kind: MaterialKind
    elastic_modulus_mpa: float
    poisson_ratio: float

    # Endurance limits — DIN 3990 for steel; VDI 2736 baseline for plastic.
    sigma_hlim_mpa: float | None = None  # flank endurance limit
    sigma_flim_mpa: float | None = None  # root (bending) endurance limit
    sigma_fe_mpa: float | None = None  # basic root strength (DIN 3990 sigma_FE)
    reference_cycles_flank: float | None = None
    reference_cycles_root: float | None = None

    # VDI 2736 plastic specifics (optional → graceful when absent).
    allowable_temperature_c: float | None = None
    wear_coefficient_mm3_per_nm: float | None = None  # k_W
    # Optional measured strength curves (sigma_Flim/N/T, sigma_Hlim/N/T).
    root_strength_curve: list[StrengthPoint] | None = None
    flank_strength_curve: list[StrengthPoint] | None = None

    @property
    def is_plastic(self) -> bool:
        return self.kind is MaterialKind.PLASTIC


def _section_float(section: SteSection, key: str) -> float | None:
    entry = section.get(key)
    if entry is None:
        return None
    for token in entry.values:
        try:
            return float(token)
        except ValueError:
            continue
    return None


# Heuristic: STplus plastic materials carry the reduced DIN-3990 limits and a low
# modulus. The kind is decided from the modulus (steel ~ 200 GPa, polymer < 20 GPa).
_PLASTIC_MODULUS_CEILING_MPA = 20_000.0


def material_from_ste(ste: SteFile, name: str) -> Material:
    """Build a :class:`Material` from the ``$ name`` material section of a `.ste`.

    Raises ``KeyError`` if the section or the elastic data is missing (those are
    essential); all strength limits are optional.
    """
    section = ste.section(name)
    if section is None:
        raise KeyError(f"material section not found: {name}")
    modulus = _section_float(section, "ELASTIZITAETSMODUL")
    poisson = _section_float(section, "QUERKONTRAKTIONSZAHL")
    if modulus is None or poisson is None:
        raise KeyError(f"material {name!r} lacks elastic data (modulus/poisson)")
    label = section.get("WERKSTOFFBEZEICHNUNG")
    kind = MaterialKind.PLASTIC if modulus < _PLASTIC_MODULUS_CEILING_MPA else MaterialKind.STEEL
    return Material(
        name=label.values[0] if label and label.values else name,
        kind=kind,
        elastic_modulus_mpa=modulus,
        poisson_ratio=poisson,
        sigma_hlim_mpa=_section_float(section, "DIN3990/87_SIGMA_HLIM"),
        sigma_flim_mpa=_section_float(section, "DIN3990/87_SIGMA_FLIM"),
        sigma_fe_mpa=_section_float(section, "DIN3990/87_SIGMA_FE"),
        reference_cycles_flank=_section_float(section, "DIN3990/87_NL_REF_H"),
        reference_cycles_root=_section_float(section, "DIN3990/87_NL_REF_F"),
    )
