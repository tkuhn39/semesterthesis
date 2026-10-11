"""The material side of the check after Stommel et al.: classes, curves, K-value and limits.

The book works with a nomogram (Bild 6.17, p. 345): the reduction factor A of the material
class and load case (Bild 6.18, p. 346) scales the static characteristic value K of the
room-temperature stress-strain curve, the scaled stress meets that curve at the permissible
strain, and the degree of multiaxiality h moves the permissible strain between the bounds the
A range gives (Eq. (6.4), Bild 6.19 and 6.20, p. 347 to 348). Other temperatures: the
permissible strain is taken as temperature-independent and the permissible stress is read off
the isotherm of the service temperature at that strain (section 6.2.2.1, p. 349 to 350). The
cyclic strength follows the same way with A_W (Bild 6.26, p. 362; p. 363: K and the
temperature as in the static check; A_W is fixed, not scaled by h, for short-fibre classes).

K: A = 1,0 of the nomogram corresponds to the yield stress σ_Y of the room-temperature curve
(Bild 6.17, p. 345; Bild 6.21, p. 349, "der Wert A = 1,0 des Nomogramms mit der Streckgrenze
σ_Y ... assoziiert"); for the reinforced polyamide the curve has its maximum shortly before break
and that maximum is taken as σ_Y (``static_characteristic_value: maximum`` of the data file).
σ_Y at the service temperature, the end of the Goodman line (Bild 6.28, p. 365, "bei der
gegebenen Temperatur"), is the maximum of the service isotherm.

The reference curve is the one of the tensile bar in flow direction (p. 344), the 0° curve as
Matscape uses it (``data/fatigue/matscape/*.csv``, the user's copy of the Matscape values of
2026-10-11). The orientation state of the component enters through the Hill ratios of the
CONVERSE card (``gearcore.io.converse_card``): ``material_for_state`` builds the same material
with the curves of a state (isotropic, aligned, or given a_11, a_22), the own extension of the
thesis (track E7), not the published method. Only R_11 and E_1 of the state enter the curve
there (true stress times R_11, plastic strain divided by R_11), the uniaxial strength along the
first fibre axis; the other five ratios are kept by the reader for the Hill equivalent stress of
the anisotropic check (E7, open).

The class tables are ``data/fatigue/stommel_materials.yaml``. Not implemented: the optional
shift of the strain limit with the yield strains of the isotherms (Bild 6.22, p. 350); the
permissible strain is the same at every temperature, as the main procedure prescribes.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt

from gearcore.data import data_path, load_stommel_materials
from gearcore.errors import InputRangeError, ParseError
from gearcore.fatigue import stommel as st
from gearcore.io.converse_card import ConverseCard, read_converse_card
from gearcore.io.matscape import StressStrainCurve, load_matscape_workbook
from gearcore.models.common import FrozenModel

Array = npt.NDArray[np.float64]
LoadCase = Literal["einmalig", "mehrmalig", "langzeitig", "wechselnd"]
LOAD_CASES: tuple[LoadCase, ...] = ("einmalig", "mehrmalig", "langzeitig", "wechselnd")
REPO_ROOT = Path(__file__).resolve().parents[5]
OrientationState = Literal["reference", "isotropic", "aligned"] | tuple[float, float]


class Range(FrozenModel):
    """A printed range (min, max)."""

    minimum: float
    maximum: float


class MaterialClass(FrozenModel):
    """One material class of the book with its printed factors."""

    name: str
    designation: str
    behaviour: str
    f_tau: float
    q: float
    reduction_factor: dict[str, Range]
    cyclic_reduction_factor: Range
    cyclic_factor_scaled_by_multiaxiality: bool
    slope_exponent: Range

    def a_range(self, load_case: LoadCase) -> Range:
        if load_case not in self.reduction_factor:
            raise InputRangeError(f"unknown load case {load_case!r}; known: {LOAD_CASES}")
        return self.reduction_factor[load_case]


class CurveReference(FrozenModel):
    """Where a curve comes from: ``matscape_csv`` (a file below ``data/fatigue/matscape``),
    ``xlsx`` (a METG workbook relative to the repository root) or ``cof`` (a state curve of the
    CONVERSE card; ``state`` names the orientation state)."""

    source: str = "matscape_csv"
    file: str
    temperature_c: float
    direction_deg: int = 0
    rate: str = ""
    humidity_percent: float = 50.0
    state: str = ""


class StommelMaterial(FrozenModel):
    """A material of the thesis with its classes and its two curves."""

    name: str
    designation: str
    reduction_class: MaterialClass
    failure_hypothesis_class: MaterialClass
    room_temperature: CurveReference
    service: CurveReference
    room_curve: StressStrainCurve
    service_curve: StressStrainCurve
    provenance: str
    f_tau_override: float | None = None
    """f_tau of the material's own card (Matscape), in place of the class value."""
    q_override: float | None = None
    failure_hypothesis_source: str = ""
    cof: str = ""
    """The CONVERSE card of the rate, relative to the repository root (empty: none)."""
    other_curves: tuple[tuple[CurveReference, StressStrainCurve], ...] = ()
    """Further measured curves of the card (other directions), for the figures."""

    @property
    def q(self) -> float:
        """Control variable: the material's own value when its card gives one, else that of
        the failure hypothesis class (Tabelle 6.1)."""
        return self.q_override if self.q_override is not None else self.failure_hypothesis_class.q

    @property
    def f_tau(self) -> float:
        """Shear strength factor: the material's own value or that of the class."""
        return (
            self.f_tau_override
            if self.f_tau_override is not None
            else self.failure_hypothesis_class.f_tau
        )

    @property
    def K_mpa(self) -> float:
        """Static characteristic value K: the largest stress of the room-temperature curve."""
        return static_characteristic_value(self.room_curve)[0]

    @property
    def K_strain_percent(self) -> float:
        return static_characteristic_value(self.room_curve)[1]

    @property
    def sigma_Y_service_mpa(self) -> float:
        """Yield stress at the service temperature: the largest stress of the service isotherm."""
        return static_characteristic_value(self.service_curve)[0]

    @property
    def temperature_c(self) -> float:
        return self.service.temperature_c

    def curves_at(self, temperature_c: float) -> list[tuple[CurveReference, StressStrainCurve]]:
        """Every curve of the material at a temperature, the reference first, then the other
        directions in ascending angle."""
        out: list[tuple[CurveReference, StressStrainCurve]] = []
        for reference, curve in (
            (self.room_temperature, self.room_curve),
            (self.service, self.service_curve),
        ):
            if reference.temperature_c == temperature_c:
                out.append((reference, curve))
        others = [pair for pair in self.other_curves if pair[0].temperature_c == temperature_c]
        out.extend(sorted(others, key=lambda pair: pair[0].direction_deg))
        return out


def _classes(loaded: dict[str, object]) -> dict[str, MaterialClass]:
    classes = loaded["classes"]
    if not isinstance(classes, dict):
        raise InputRangeError("stommel_materials.yaml: 'classes' is not a mapping")
    out: dict[str, MaterialClass] = {}
    for name, entry in classes.items():
        if not isinstance(entry, dict):
            raise InputRangeError(f"stommel_materials.yaml: class {name!r} is not a mapping")
        factors = entry["reduction_factor"]
        out[str(name)] = MaterialClass(
            name=str(name),
            designation=str(entry["designation"]),
            behaviour=str(entry["behaviour"]),
            f_tau=float(entry["f_tau"]),
            q=float(entry["q"]),
            reduction_factor={
                str(case): Range(minimum=float(pair[0]), maximum=float(pair[1]))
                for case, pair in factors.items()
            },
            cyclic_reduction_factor=Range(
                minimum=float(entry["cyclic_reduction_factor"][0]),
                maximum=float(entry["cyclic_reduction_factor"][1]),
            ),
            cyclic_factor_scaled_by_multiaxiality=bool(
                entry["cyclic_factor_scaled_by_multiaxiality"]
            ),
            slope_exponent=Range(
                minimum=float(entry["slope_exponent"][0]), maximum=float(entry["slope_exponent"][1])
            ),
        )
    return out


def material_classes() -> dict[str, MaterialClass]:
    """The classes of the book as the data file transcribes them."""
    return _classes(load_stommel_materials())


def material_names() -> list[str]:
    materials = load_stommel_materials()["materials"]
    return sorted(str(name) for name in materials)


def _material_entry(name: str) -> dict[str, object]:
    materials = load_stommel_materials()["materials"]
    if not isinstance(materials, dict) or name not in materials:
        raise InputRangeError(f"unknown material {name!r}; known: {material_names()}")
    entry = materials[name]
    if not isinstance(entry, dict):
        raise InputRangeError(f"stommel_materials.yaml: material {name!r} is not a mapping")
    return entry


def _curve_reference(entry: dict[str, object]) -> CurveReference:
    return CurveReference(
        source=str(entry.get("source", "matscape_csv")),
        file=str(entry["file"]),
        temperature_c=float(str(entry["temperature_c"])),
        direction_deg=int(str(entry.get("direction_deg", 0))),
        rate=str(entry.get("rate", "")),
        humidity_percent=float(str(entry.get("humidity_percent", 50.0))),
        state=str(entry.get("state", "")),
    )


def load_matscape_csv(path: Path) -> StressStrainCurve:
    """One curve of ``data/fatigue/matscape``: comment lines, a header, strain % and stress MPa."""
    if not path.is_file():
        raise InputRangeError(f"curve file not found: {path}")
    strains: list[float] = []
    stresses: list[float] = []
    for row in csv.reader(path.read_text(encoding="utf-8").splitlines()):
        if not row or row[0].startswith("#") or row[0] == "strain_percent":
            continue
        if len(row) != 2:
            raise ParseError(f"{path.name}: a row with {len(row)} fields")
        strains.append(float(row[0]))
        stresses.append(float(row[1]))
    if len(strains) < 2 or strains[0] != 0.0:
        raise ParseError(f"{path.name}: a curve starts at zero strain and has two points at least")
    if any(b <= a for a, b in zip(strains, strains[1:], strict=False)):
        raise ParseError(f"{path.name}: strain must increase strictly")
    if stresses[0] != 0.0 or any(s < 0.0 for s in stresses):
        raise ParseError(f"{path.name}: stress starts at zero and is never negative")
    return StressStrainCurve(strain_percent=tuple(strains), stress_mpa=tuple(stresses))


def _curve(reference: CurveReference, root: Path) -> StressStrainCurve:
    if reference.source == "matscape_csv":
        return load_matscape_csv(data_path("fatigue", "matscape", reference.file))
    if reference.source == "xlsx":
        path = root / reference.file
        if not path.is_file():
            raise InputRangeError(f"curve file not found: {path}")
        workbook = load_matscape_workbook(
            path, temperature_c=reference.temperature_c, humidity_percent=reference.humidity_percent
        )
        return workbook.curve(reference.direction_deg, reference.rate).curve
    raise InputRangeError(f"unknown curve source {reference.source!r} (matscape_csv, xlsx)")


def load_material(name: str, *, root: Path | None = None) -> StommelMaterial:
    """A material of the data file with its curves read from their sources."""
    loaded = load_stommel_materials()
    entry = _material_entry(name)
    classes = _classes(loaded)
    reduction = classes[str(entry["reduction_class"])]
    hypothesis = classes[str(entry["failure_hypothesis_class"])]
    if str(entry.get("static_characteristic_value", "maximum")) != "maximum":
        raise InputRangeError(
            f"{name}: only static_characteristic_value 'maximum' is implemented "
            "(the yield stress of the curve)"
        )
    card = entry.get("failure_hypothesis")
    if card is not None and not isinstance(card, dict):
        raise InputRangeError(f"{name}: failure_hypothesis must be a mapping")
    if card is not None:
        f_tau = float(str(card["f_tau"]))
        q_given = float(str(card["q"]))
        if abs(float(st.control_variable(max(f_tau, 1.0 / math.sqrt(3.0)))) - q_given) > 0.01:
            raise InputRangeError(
                f"{name}: q {q_given} does not follow from f_tau {f_tau} by Eq. (6.2)"
            )
    curves = entry["curves"]
    if not isinstance(curves, dict):
        raise InputRangeError(f"{name}: 'curves' must be a mapping")
    room = _curve_reference(curves["room_temperature"])
    service = _curve_reference(curves["service"])
    base = REPO_ROOT if root is None else root
    others: list[tuple[CurveReference, StressStrainCurve]] = []
    listed = entry.get("other_curves") or []
    if not isinstance(listed, list):
        raise InputRangeError(f"{name}: 'other_curves' must be a list")
    for other in listed:
        reference = _curve_reference(other)
        others.append((reference, _curve(reference, base)))
    return StommelMaterial(
        name=name,
        designation=str(entry["designation"]),
        reduction_class=reduction,
        failure_hypothesis_class=hypothesis,
        room_temperature=room,
        service=service,
        room_curve=_curve(room, base),
        service_curve=_curve(service, base),
        provenance=str(entry.get("provenance", "")),
        f_tau_override=(float(str(card["f_tau"])) if card else None),
        q_override=(float(str(card["q"])) if card else None),
        failure_hypothesis_source=(str(card.get("source", "")) if card else ""),
        cof=str(entry.get("cof", "")),
        other_curves=tuple(others),
    )


def model_property(name: str, temperature_c: float, key: str) -> float:
    """A model property Matscape prints for the card (``model_properties`` of the data file)."""
    properties = _material_entry(name).get("model_properties")
    if not isinstance(properties, dict) or int(temperature_c) not in properties:
        raise InputRangeError(f"{name}: no model properties at {temperature_c} degC")
    return float(properties[int(temperature_c)][key])


def validation_values(name: str, temperature_c: float) -> dict[str, float]:
    """What Matscape prints in its Haigh diagram for the card at the temperature
    (``validation_matscape`` of the data file): sigma_B_S, sigma_SK, sigma_WK in MPa and M."""
    block = _material_entry(name).get("validation_matscape")
    if not isinstance(block, dict) or int(temperature_c) not in block:
        raise InputRangeError(f"{name}: no Matscape validation values at {temperature_c} degC")
    return {str(key): float(value) for key, value in block[int(temperature_c)].items()}


def converse_card(material: StommelMaterial, *, root: Path | None = None) -> ConverseCard:
    """The CONVERSE card of the material's rate."""
    if not material.cof:
        raise InputRangeError(f"{material.name}: no CONVERSE card registered")
    path = (REPO_ROOT if root is None else root) / material.cof
    if not path.is_file():
        raise InputRangeError(f"CONVERSE card not found: {path}")
    return read_converse_card(path.read_text(encoding="utf-8", errors="replace"))


def state_of(state: OrientationState) -> tuple[float, float]:
    """(a_11, a_22) of a named or given orientation state."""
    if isinstance(state, tuple):
        a11, a22 = float(state[0]), float(state[1])
        if not (0.0 <= a22 <= a11 <= 1.0 and a11 + a22 <= 1.0):
            raise InputRangeError(f"orientation state ({a11}, {a22}) is not an eigenvalue pair")
        return a11, a22
    if state == "isotropic":
        return 1.0 / 3.0, 1.0 / 3.0
    if state == "aligned":
        return 1.0, 0.0
    raise InputRangeError(f"unknown orientation state {state!r} (isotropic, aligned or (a11, a22))")


def material_for_state(
    material: StommelMaterial, state: OrientationState, *, root: Path | None = None
) -> StommelMaterial:
    """The same material with the curves of an orientation state of its CONVERSE card (the own
    extension E7): the reference state keeps the measured curves; any other state takes the
    state curves of the card at both temperatures (R_11 and E_1 of the nearest lattice state)."""
    if state == "reference":
        return material
    a11, a22 = state_of(state)
    card = converse_card(material, root=root)
    label = f"a11={a11:.3f},a22={a22:.3f}"
    room = material.room_temperature.model_copy(
        update={"source": "cof", "file": material.cof, "state": label}
    )
    service = material.service.model_copy(
        update={"source": "cof", "file": material.cof, "state": label}
    )
    return material.model_copy(
        update={
            "name": f"{material.name}_{a11:.3f}_{a22:.3f}",
            "designation": (f"{material.designation}, Orientierungszustand ({a11:.3f}; {a22:.3f})"),
            "room_temperature": room,
            "service": service,
            "room_curve": card.state_curve(material.room_temperature.temperature_c, a11, a22),
            "service_curve": card.state_curve(material.service.temperature_c, a11, a22),
            "other_curves": (),
        }
    )


def with_reduction_class(material: StommelMaterial, class_name: str) -> StommelMaterial:
    """The same material with the reduction factors of another class of the book. The user's
    decision of 2026-10-11 for the Hill extension (E7): the low factors of the reinforced class
    carry the transverse weakness as a lump sum (book p. 346), which the ratios of the card
    express explicitly, so the anisotropy must not be counted twice; the extension takes the
    factors of the ductile unreinforced class by default."""
    classes = material_classes()
    if class_name not in classes:
        raise InputRangeError(f"unknown material class {class_name!r}; known: {sorted(classes)}")
    return material.model_copy(update={"reduction_class": classes[class_name]})


# --- the nomogram -----------------------------------------------------------------------------------


def static_characteristic_value(curve: StressStrainCurve) -> tuple[float, float]:
    """K and the strain at which the curve reaches it: the largest stress of the curve, which is
    the yield stress σ_Y (A = 1,0 of the nomogram, Bild 6.17) when the curve has a maximum."""
    return curve.maximum


def strain_limit_percent(curve: StressStrainCurve, A: float, K_mpa: float) -> float:
    """The strain at which the room-temperature curve reaches A K (Bild 6.17: the intersection
    of the reduced stress with the curve gives the permissible strain)."""
    if not 0.0 < A <= 1.0:
        raise InputRangeError(f"reduction factor A must lie in (0, 1], got {A!r}")
    return curve.strain_at(A * K_mpa)


def strain_limits_percent(material: StommelMaterial, load_case: LoadCase) -> tuple[float, float]:
    """(ε_min, ε_max): the strains of the room-temperature curve at A_min K and A_max K of the
    load case (the bounds between which Eq. (6.4) interpolates over h)."""
    bounds = material.reduction_class.a_range(load_case)
    k_value = material.K_mpa
    return (
        strain_limit_percent(material.room_curve, bounds.minimum, k_value),
        strain_limit_percent(material.room_curve, bounds.maximum, k_value),
    )


def _rising_branch(curve: StressStrainCurve) -> tuple[Array, Array]:
    """Strain and stress of the curve up to its maximum (the branch the inverse reading uses)."""
    _, peak_strain = curve.maximum
    strain = np.asarray(curve.strain_percent, dtype=np.float64)
    stress = np.asarray(curve.stress_mpa, dtype=np.float64)
    keep = strain <= peak_strain
    return strain[keep], stress[keep]


def stress_on_isotherm(curve: StressStrainCurve, strain_percent: npt.ArrayLike) -> Array:
    """Stress of the isotherm at given strains (p. 350: the permissible strain transferred
    horizontally to the isotherm of the service temperature), linear between the points; a
    strain beyond the curve is refused."""
    strains = np.asarray(strain_percent, dtype=np.float64)
    x = np.asarray(curve.strain_percent, dtype=np.float64)
    y = np.asarray(curve.stress_mpa, dtype=np.float64)
    if np.any(strains < x[0]) or np.any(strains > x[-1]):
        raise InputRangeError(f"a strain lies outside the isotherm ({x[0]:g} to {x[-1]:g} %)")
    return np.asarray(np.interp(strains, x, y), dtype=np.float64)


def equivalent_strain_percent(curve: StressStrainCurve, sigma_V_mpa: npt.ArrayLike) -> Array:
    """ε_V(σ_V) read off the rising branch of the service isotherm (Eq. (6.15): the equivalent
    strain as a function of the equivalent stress); a stress above the maximum of the curve is
    not reached by the material and gives an infinite strain (the static check then fails). A
    dip of the measured curve below its running maximum is bridged (the inverse reading needs
    a strictly increasing stress axis)."""
    stresses = np.asarray(sigma_V_mpa, dtype=np.float64)
    if np.any(stresses < 0.0):
        raise InputRangeError("an equivalent stress is not negative")
    x, y = _rising_branch(curve)
    envelope = np.maximum.accumulate(y)
    keep = np.concatenate(([True], np.diff(envelope) > 0.0))
    strain = np.interp(stresses, envelope[keep], x[keep], right=np.inf)
    return np.asarray(strain, dtype=np.float64)


def permissible_strain_percent(
    material: StommelMaterial, load_case: LoadCase, h: npt.ArrayLike
) -> Array:
    """ε_zul(h) of Eq. (6.4) between the strain limits of the load case."""
    lower, upper = strain_limits_percent(material, load_case)
    return st.permissible_strain(h, lower, upper)


def static_component_strength_mpa(
    material: StommelMaterial, load_case: LoadCase, h: npt.ArrayLike
) -> Array:
    """σ_stat(h): the stress of the service isotherm at the permissible strain ε_zul(h)
    (Bild 6.20 and section 6.2.2.1)."""
    return stress_on_isotherm(
        material.service_curve, permissible_strain_percent(material, load_case, h)
    )


def effective_reduction_factor(
    material: StommelMaterial, load_case: LoadCase, h: npt.ArrayLike
) -> Array:
    """The reduction factor the interpolation over h effectively applies on the room-temperature
    curve, A(h) = σ_RT(ε_zul(h)) / K (Bild 6.20: 47 MPa of 52 MPa is A = 0,9 for the PA66
    example); with the single-load case it is the A_S of Eq. (6.22)."""
    strain = permissible_strain_percent(material, load_case, h)
    return np.asarray(
        stress_on_isotherm(material.room_curve, strain) / material.K_mpa, dtype=np.float64
    )


def cyclic_reduction_factor(material: StommelMaterial, h: npt.ArrayLike) -> Array:
    """A_W(h): fixed for the short-fibre classes, interpolated over h like the static factor for
    the unreinforced ones (p. 363)."""
    bounds = material.reduction_class.cyclic_reduction_factor
    degree = np.asarray(h, dtype=np.float64)
    if (
        not material.reduction_class.cyclic_factor_scaled_by_multiaxiality
        or bounds.minimum == bounds.maximum
    ):
        return np.full(degree.shape, bounds.maximum, dtype=np.float64)
    k_value = material.K_mpa
    lower = strain_limit_percent(material.room_curve, bounds.minimum, k_value)
    upper = strain_limit_percent(material.room_curve, bounds.maximum, k_value)
    strain = st.permissible_strain(degree, lower, upper)
    return np.asarray(stress_on_isotherm(material.room_curve, strain) / k_value, dtype=np.float64)


def component_alternating_strength_mpa(material: StommelMaterial, h: npt.ArrayLike) -> Array:
    """σ_W at the service temperature: A_W K on the room-temperature curve gives the strain
    ε_W, the service isotherm at ε_W gives σ_W (Eq. (6.19) with the temperature treatment of
    section 6.2.2.1, as p. 363 prescribes)."""
    factor = cyclic_reduction_factor(material, h)
    k_value = material.K_mpa
    strains = np.asarray(
        [
            strain_limit_percent(material.room_curve, float(a), k_value)
            for a in np.atleast_1d(factor)
        ],
        dtype=np.float64,
    ).reshape(factor.shape)
    return stress_on_isotherm(material.service_curve, strains)


def slope_exponent(material: StommelMaterial, h: npt.ArrayLike) -> Array:
    """k(h) of the synthetic Wöhler line at the service temperature: k = lg N_G / lg(A_S / A_W)
    (Eq. (6.22)) with the reduction factors "für geänderte Temperatur ... mit der in Abschnitt
    6.2.2 dargestellten Vorgehensweise ermittelt" (p. 371), that is the effective factors at the
    service temperature, A_S = σ_stat,T(h) / σ_Y,T and A_W = σ_W,T(h) / σ_Y,T; the line then runs
    from σ_stat,T at N = 1 to σ_W,T at N_G as Bild 6.31 draws it. At room temperature this is
    the ratio of ``effective_reduction_factor`` to ``cyclic_reduction_factor``."""
    sigma_y = material.sigma_Y_service_mpa
    static = static_component_strength_mpa(material, "einmalig", h) / sigma_y
    cyclic = component_alternating_strength_mpa(material, h) / sigma_y
    return st.woehler_slope_exponent(static, cyclic)
