"""The material card of a CONVERSE orientation file (``.cof``), all rows.

``gearcore.fe.deck.read_material_card`` keeps the isotropic row the FE steps need; this reader
keeps the whole card for the material side of the design check: every row of ``*ELASTIC,
TYPE=ENGINEERING CONSTANTS, DEPENDENCIES=2`` (nine constants, temperature, the field
variables a_11 and a_22 of the orientation state), the ``*PLASTIC`` reference curve per
temperature (true stress over logarithmic plastic strain, as Abaqus takes it) and every row of
``*POTENTIAL, TYPE=HILL, DEPENDENCIES=2`` (the six yield stress ratios R_11, R_22, R_33, R_12,
R_13, R_23, temperature, a_11, a_22).

How Matscape (PART Engineering) encodes the fibre orientation (read from the user's cards of
2026-10-11): the ``*PLASTIC`` curve is the stress-strain curve of the tensile bar in flow
direction converted to true stress (the QS card at 23 °C ends at 122,86 MPa true, which is
115,51 MPa engineering at 6,36 %, the end of the measured 0° curve), and the orientation state
scales it through the Hill ratios: R_11 = 1,56 for the fully aligned state a_11 = 1, 0,65 for the
isotropic state a_11 = a_22 = 1/3 (QS, 23 °C), 1 for the state of the bar itself (the effective
orientation of the model properties, a_1 = 0,70, a_2 = 0,24). The stiffness follows the same
lattice of states. The curve of a state is therefore the reference curve with the true stress
multiplied by R_11 of that state, the plastic strain divided by R_11 (the equivalent plastic
strain of the Hill potential is defined through the plastic work) and the elastic strain from
E_1 of that state;
``state_curve`` converts it back to engineering stress and strain for the nomogram.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from gearcore.errors import InputRangeError, ParseError
from gearcore.fe.deck import _blocks, _joined_rows
from gearcore.io.matscape import StressStrainCurve

ISOTROPIC_STATE = (1.0 / 3.0, 1.0 / 3.0)
ALIGNED_STATE = (1.0, 0.0)


@dataclass(frozen=True)
class ElasticRow:
    temperature_c: float
    a11: float
    a22: float
    E1_mpa: float
    E2_mpa: float
    E3_mpa: float
    nu12: float
    nu13: float
    nu23: float
    G12_mpa: float
    G13_mpa: float
    G23_mpa: float


@dataclass(frozen=True)
class HillRow:
    temperature_c: float
    a11: float
    a22: float
    R11: float
    R22: float
    R33: float
    R12: float
    R13: float
    R23: float


@dataclass(frozen=True)
class ConverseCard:
    """The material card as the file gives it."""

    name: str
    elastic: tuple[ElasticRow, ...]
    plastic: tuple[tuple[float, float, float], ...]
    """(true stress in MPa, logarithmic plastic strain, temperature in degC)."""
    hill: tuple[HillRow, ...]
    density: tuple[tuple[float, float], ...]

    @property
    def temperatures_c(self) -> tuple[float, ...]:
        return tuple(sorted({row.temperature_c for row in self.elastic}))

    def states(self, temperature_c: float) -> tuple[tuple[float, float], ...]:
        """The lattice of orientation states (a_11, a_22) the card tabulates."""
        return tuple(
            sorted(
                {
                    (row.a11, row.a22)
                    for row in self.elastic
                    if abs(row.temperature_c - temperature_c) < 1.0e-6
                }
            )
        )

    def elastic_at(self, temperature_c: float, a11: float, a22: float) -> ElasticRow:
        """The elastic row of the lattice state nearest to (a_11, a_22) at the temperature."""
        rows = [row for row in self.elastic if abs(row.temperature_c - temperature_c) < 1.0e-6]
        if not rows:
            raise InputRangeError(
                f"{self.name}: no elastic row at {temperature_c} degC; temperatures {self.temperatures_c}"
            )
        return min(rows, key=lambda row: math.hypot(row.a11 - a11, row.a22 - a22))

    def hill_at(self, temperature_c: float, a11: float, a22: float) -> HillRow:
        rows = [row for row in self.hill if abs(row.temperature_c - temperature_c) < 1.0e-6]
        if not rows:
            raise InputRangeError(f"{self.name}: no Hill row at {temperature_c} degC")
        return min(rows, key=lambda row: math.hypot(row.a11 - a11, row.a22 - a22))

    def plastic_at(self, temperature_c: float) -> tuple[np.ndarray, np.ndarray]:
        """(true stress, logarithmic plastic strain) of the reference curve at the temperature."""
        rows = [(s, e) for s, e, t in self.plastic if abs(t - temperature_c) < 1.0e-6]
        if not rows:
            raise InputRangeError(f"{self.name}: no plastic row at {temperature_c} degC")
        stress = np.array([s for s, _ in rows], dtype=np.float64)
        strain = np.array([e for _, e in rows], dtype=np.float64)
        if np.any(np.diff(strain) < 0.0):
            raise ParseError(f"{self.name}: plastic strain not increasing at {temperature_c} degC")
        return stress, strain

    def state_curve(self, temperature_c: float, a11: float, a22: float) -> StressStrainCurve:
        """Engineering stress-strain curve of an orientation state: the reference curve in true
        quantities with the stress multiplied by R_11 of the nearest lattice state and the plastic
        strain divided by R_11 (Abaqus defines the equivalent plastic strain of the Hill potential
        through the plastic work, so uniaxial loading along axis 1 reaches σ_11 = R_11 σ⁰ at
        ε_11^pl = ε̄^pl / R_11; review of 2026-10-11), the elastic strain from E_1 of that state,
        converted from true to engineering (ε = e^ε_t − 1, σ = σ_t e^(−ε_t)). The first point is
        the origin, then the plastic rows."""
        stress_true, strain_plastic = self.plastic_at(temperature_c)
        ratio = self.hill_at(temperature_c, a11, a22).R11
        modulus = self.elastic_at(temperature_c, a11, a22).E1_mpa
        scaled = ratio * stress_true
        strain_true = strain_plastic / ratio + scaled / modulus
        strain_eng = np.expm1(strain_true) * 100.0
        stress_eng = scaled * np.exp(-strain_true)
        strains = [0.0] + [float(v) for v in strain_eng]
        stresses = [0.0] + [float(v) for v in stress_eng]
        return StressStrainCurve(strain_percent=tuple(strains), stress_mpa=tuple(stresses))

    def reference_curve(self, temperature_c: float, modulus_mpa: float) -> StressStrainCurve:
        """Engineering curve of the reference (the bar in flow direction) with a given modulus:
        the reference state is not a lattice point, so the measured modulus of the bar is
        supplied (the initial slope of the Matscape 0° curve)."""
        stress_true, strain_plastic = self.plastic_at(temperature_c)
        strain_true = strain_plastic + stress_true / modulus_mpa
        strains = [0.0] + [float(v) for v in np.expm1(strain_true) * 100.0]
        stresses = [0.0] + [float(v) for v in stress_true * np.exp(-strain_true)]
        return StressStrainCurve(strain_percent=tuple(strains), stress_mpa=tuple(stresses))


def read_converse_card(text: str) -> ConverseCard:
    """Every row of the ``*MATERIAL`` block of a CONVERSE orientation file."""
    name: str | None = None
    elastic: list[ElasticRow] = []
    plastic: list[tuple[float, float, float]] = []
    hill: list[HillRow] = []
    density: list[tuple[float, float]] = []
    for keyword, line, data in _blocks(text):
        if keyword == "MATERIAL":
            if name is not None:
                raise ParseError("orientation file: more than one *MATERIAL")
            name = line.split("NAME=")[1].split(",")[0].strip()
        elif keyword == "ELASTIC":
            if "ENGINEERING CONSTANTS" not in line.upper() or "DEPENDENCIES=2" not in line.upper():
                raise ParseError(f"orientation file: unexpected elastic definition {line!r}")
            for row in _joined_rows(data, 12):
                elastic.append(
                    ElasticRow(
                        temperature_c=row[9],
                        a11=row[10],
                        a22=row[11],
                        E1_mpa=row[0],
                        E2_mpa=row[1],
                        E3_mpa=row[2],
                        nu12=row[3],
                        nu13=row[4],
                        nu23=row[5],
                        G12_mpa=row[6],
                        G13_mpa=row[7],
                        G23_mpa=row[8],
                    )
                )
        elif keyword == "PLASTIC":
            if "DEPENDENCIES" in line.upper():
                raise ParseError("orientation file: *PLASTIC with field dependencies is not read")
            plastic = [(row[0], row[1], row[2]) for row in _joined_rows(data, 3)]
        elif keyword == "POTENTIAL":
            if "HILL" not in line.upper():
                raise ParseError(f"orientation file: unexpected potential {line!r}")
            for row in _joined_rows(data, 9):
                hill.append(
                    HillRow(
                        temperature_c=row[6],
                        a11=row[7],
                        a22=row[8],
                        R11=row[0],
                        R22=row[1],
                        R33=row[2],
                        R12=row[3],
                        R13=row[4],
                        R23=row[5],
                    )
                )
        elif keyword == "DENSITY":
            density = [(row[0], row[1]) for row in _joined_rows(data, 2)]
    if name is None or not elastic or not plastic or not hill:
        raise ParseError(
            "orientation file: material block incomplete (name, elastic, plastic, Hill)"
        )
    return ConverseCard(
        name=name,
        elastic=tuple(elastic),
        plastic=tuple(plastic),
        hill=tuple(hill),
        density=tuple(density),
    )
