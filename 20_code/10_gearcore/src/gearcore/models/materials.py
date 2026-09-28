"""Material record contract (stage 1: contract + ``.ste`` import; contents in stage 2).

Two separated data layers per record, chosen by ``kind`` (rule 9: steel and plastic never mix):

* ``steel`` — ISO 6336-5 style data (material group, quality, hardness, E, ν) or the DIN 3990
  values STplus files carry;
* ``polymer`` — ISO 10350 single-point datasheet values (CAMPUS datasheets: modulus dry/conditioned,
  yield/break stress, density, melting/glass temperatures, HDT, CLTE, moisture);
* ``strength`` — gear-specific strength values, whose source differs by kind (ISO 6336-5 for steel,
  VDI 2736-2 tables or measurements for plastics).

Every layer carries a ``Provenance``; a value without a source is not accepted.
"""

from typing import Self

from pydantic import model_validator

from gearcore.models.common import F, FrozenModel
from gearcore.models.inputs import MaterialKind


class Provenance(FrozenModel):
    """Where a set of values comes from."""

    source: str = F(
        "-", "-", "source key (sources.yaml) or file name, e.g. 'STplus:kst-E_eingabe.ste'"
    )
    location: str | None = F("-", "-", "table / page / block within the source", default=None)
    retrieved: str | None = F("-", "-", "ISO date of retrieval or transcription", default=None)
    note: str | None = None


class SteelData(FrozenModel):
    youngs_modulus_MPa: float = F("E", "MPa", "ELASTIZITAETSMODUL", gt=0.0)
    poisson_ratio: float = F("nu", "-", "QUERKONTRAKTIONSZAHL", gt=0.0, lt=0.5)
    density_kg_m3: float | None = F("rho", "kg/m3", "DICHTE_RADKRANZMATERIAL", default=None, gt=0.0)
    heat_treatment: str | None = F("-", "-", "WAERMEBEHANDLUNG", default=None)
    surface_hardness_HV: float | None = F(
        "HV_surface", "HV", "OBERFLAECHENHAERTE", default=None, ge=0.0
    )
    core_hardness_HV: float | None = F("HV_core", "HV", "KERNHAERTE_ZAHN", default=None, ge=0.0)
    yield_strength_MPa: float | None = F(
        "R_p0.2", "MPa", "STRECKGRENZE_SIGMA02", default=None, gt=0.0
    )
    tensile_strength_MPa: float | None = F("R_m", "MPa", "BRUCHGRENZE", default=None, gt=0.0)
    provenance: Provenance


class PolymerData(FrozenModel):
    """ISO 10350 single-point values as printed on CAMPUS datasheets (dry / conditioned)."""

    tensile_modulus_dry_MPa: float | None = F(
        "E_t,dry", "MPa", "Zug-Modul trocken (ISO 527)", default=None, gt=0.0
    )
    tensile_modulus_cond_MPa: float | None = F(
        "E_t,cond", "MPa", "Zug-Modul konditioniert (ISO 527)", default=None, gt=0.0
    )
    poisson_ratio: float | None = F("nu", "-", "", default=None, gt=0.0, le=0.5)
    yield_stress_dry_MPa: float | None = F(
        "sigma_y,dry", "MPa", "Streckspannung trocken", default=None, gt=0.0
    )
    break_stress_dry_MPa: float | None = F(
        "sigma_b,dry", "MPa", "Bruchspannung trocken", default=None, gt=0.0
    )
    density_kg_m3: float | None = F("rho", "kg/m3", "Dichte (ISO 1183)", default=None, gt=0.0)
    melting_temperature_C: float | None = F(
        "T_m", "degC", "Schmelztemperatur (ISO 11357)", default=None
    )
    glass_transition_C: float | None = F(
        "T_g", "degC", "Glasuebergangstemperatur (ISO 11357)", default=None
    )
    hdt_1_8MPa_C: float | None = F(
        "HDT_A", "degC", "Formbestaendigkeitstemperatur 1,80 MPa (ISO 75)", default=None
    )
    clte_parallel_1e6_per_K: float | None = F(
        "alpha_L", "1e-6/K", "Laengenausdehnungskoeffizient laengs", default=None
    )
    moisture_absorption_pct: float | None = F(
        "-", "%", "Feuchtigkeitsaufnahme (ISO 62)", default=None, ge=0.0
    )
    filler: str | None = F("-", "-", "e.g. 'GF30'", default=None)
    provenance: Provenance


class GearStrength(FrozenModel):
    """Gear-specific strength values. Steel: ISO 6336-5 / DIN 3990-5. Plastic: VDI 2736-2 tables."""

    sigma_Hlim_MPa: float | None = F(
        "sigma_Hlim", "MPa", "allowable contact stress number", default=None, gt=0.0
    )
    sigma_FE_MPa: float | None = F(
        "sigma_FE", "MPa", "allowable bending stress number (notched, steel)", default=None, gt=0.0
    )
    sigma_Flim_MPa: float | None = F(
        "sigma_Flim", "MPa", "nominal bending stress number", default=None, gt=0.0
    )
    n_ref_H: float | None = F(
        "N_L,ref,H", "-", "reference cycles (DIN3990/87_NL_REF_H)", default=None, gt=0.0
    )
    n_ref_F: float | None = F(
        "N_L,ref,F", "-", "reference cycles (DIN3990/87_NL_REF_F)", default=None, gt=0.0
    )
    provenance: Provenance


class MaterialRecord(FrozenModel):
    kind: MaterialKind
    name: str = F("-", "-", "record name", min_length=1)
    steel: SteelData | None = None
    polymer: PolymerData | None = None
    strength: GearStrength | None = None

    @model_validator(mode="after")
    def _layers_match_kind(self) -> Self:
        if self.kind is MaterialKind.STEEL and self.polymer is not None:
            raise ValueError(
                f"{self.name}: a steel record must not carry a polymer datasheet layer"
            )
        if self.kind is MaterialKind.PLASTIC and self.steel is not None:
            raise ValueError(f"{self.name}: a plastic record must not carry a steel data layer")
        return self
