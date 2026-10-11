"""The equations of chapter 6 of Stommel, Stojek, Korte (2018), one traced function each.

Every function takes floats or arrays of equal shape (the nodes of a mesh, the states of a
history) and returns a float64 array of the broadcast shape; a scalar input gives a 0-d array,
``float(...)`` reads it. Inputs must be finite (``InputRangeError`` otherwise); nothing is
clamped. Stresses in MPa, strains in %, as the book prints them.

Conventions that the book leaves to the reader are stated at the function:

* the Hencky degree of multiaxiality of an unloaded node (σ_Mises = 0) is taken as 0, the value of
  pure shear, so that the permissible strain is the uniaxial one; the utilisation of such a node
  is 0 anyway (``multiaxiality_degree``);
* the overload cases of Eq. (6.21) are printed for the tension side of the Haigh diagram; with a
  signed mean stress the same formulas continue the Goodman line straight into the compression
  side, as Bild 6.28 and 6.29 (p. 365 to 366) draw it, and the static cap of Eq. (6.23) bounds
  the stress of the largest magnitude on both sides (``max_component_fatigue_strength``);
* case 2 (R constant) on the compression side: where the ray of constant R never meets the
  continued line (1 + M σ_m/σ_a ≤ 0) the line sets no limit, the factor is infinite and the
  static cap alone governs; a vanishing amplitude has no stress ratio, the factor is set to 1
  there by convention (its utilisation is 0 either way) (``mean_stress_factor_case_2``);
* an infinite equivalent strain (σ_V above the maximum of the isotherm) gives an infinite static
  utilisation, an infinite single utilisation (no strength left) an infinite cyclic one.

PDF page = printed page + 18 in the repository's copy; the pages below are the printed ones.
"""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt

from gearcore.errors import InputRangeError
from gearcore.trace import eq

SOURCE = "Stommel2018"
Array = npt.NDArray[np.float64]

LIMIT_NUMBER_OF_CYCLES = 1.0e7
"""N_G, the substitute of the endurance limit (section 6.1.4, p. 328; Eq. (6.22), p. 371)."""
COMPRESSIVE_STRENGTH_FACTOR = 1.3
"""f_σ for σ_i < 0: the compressive strength is taken 30 % above the tensile (Eq. (6.17), p. 357)."""
LOWEST_NUMBER_OF_CYCLES = 1.0e4
"""Below 10^4 cycles the linear elastic method does not apply (section 6.3.4, p. 372)."""
SQRT3 = math.sqrt(3.0)

EQ_EXEMPT = (
    "principal_stresses",
    "tensors_from_components",
    "components_from_tensors",
)


def _array(value: npt.ArrayLike, what: str) -> Array:
    array = np.asarray(value, dtype=np.float64)
    if not np.all(np.isfinite(array)):
        raise InputRangeError(f"{what} must be finite")
    return array


def _array_or_infinite(value: npt.ArrayLike, what: str) -> Array:
    """Like ``_array`` but an infinite value passes (the degree of multiaxiality of a
    hydrostatic state); NaN does not."""
    array = np.asarray(value, dtype=np.float64)
    if np.any(np.isnan(array)):
        raise InputRangeError(f"{what} must not be NaN")
    return array


def _positive(value: npt.ArrayLike, what: str) -> Array:
    array = _array(value, what)
    if np.any(array <= 0.0):
        raise InputRangeError(f"{what} must be positive")
    return array


# --- tensor helpers (linear algebra, no equation of the book) --------------------------------


def tensors_from_components(components: npt.ArrayLike) -> Array:
    """(..., 6) Abaqus components S11, S22, S33, S12, S13, S23 -> (..., 3, 3) symmetric tensors."""
    s = _array(components, "stress components")
    if s.shape[-1] != 6:
        raise InputRangeError(f"six stress components expected, got shape {s.shape}")
    t = np.empty(s.shape[:-1] + (3, 3), dtype=np.float64)
    t[..., 0, 0] = s[..., 0]
    t[..., 1, 1] = s[..., 1]
    t[..., 2, 2] = s[..., 2]
    t[..., 0, 1] = t[..., 1, 0] = s[..., 3]
    t[..., 0, 2] = t[..., 2, 0] = s[..., 4]
    t[..., 1, 2] = t[..., 2, 1] = s[..., 5]
    return t


def components_from_tensors(tensors: npt.ArrayLike) -> Array:
    """(..., 3, 3) symmetric tensors -> (..., 6) components in the Abaqus order."""
    t = _array(tensors, "stress tensors")
    if t.shape[-2:] != (3, 3):
        raise InputRangeError(f"3 x 3 tensors expected, got shape {t.shape}")
    return np.stack(
        [t[..., 0, 0], t[..., 1, 1], t[..., 2, 2], t[..., 0, 1], t[..., 0, 2], t[..., 1, 2]],
        axis=-1,
    )


def principal_stresses(components: npt.ArrayLike) -> tuple[Array, Array, Array]:
    """Principal stresses σ_1 ≥ σ_2 ≥ σ_3 of (..., 6) components (eigenvalues of the tensor)."""
    values = np.linalg.eigvalsh(tensors_from_components(components))  # ascending
    return values[..., 2], values[..., 1], values[..., 0]


# --- 6.1.2 utilisation ----------------------------------------------------------------------------


@eq(SOURCE, "(6.1)", section="6.1.2.2", page=313)
def utilisation(sigma_V: npt.ArrayLike, sigma_zul: npt.ArrayLike) -> Array:
    """Utilisation a = present / permissible, for stresses (a_σ), strains (a_ε) or energies alike."""
    present = _array(sigma_V, "present value")
    permissible = _positive(sigma_zul, "permissible value")
    return np.asarray(present / permissible, dtype=np.float64)


# --- 6.1.3 failure hypothesis and multiaxiality -------------------------------------------------


@eq(SOURCE, "(6.2)", section="6.1.3", page=322, note="Tabelle 6.1, p. 323: f_tau and q per class")
def control_variable(f_tau: npt.ArrayLike) -> Array:
    """Control variable q = (√3 − 1/f_τ) / (√3 − 1) from the shear strength factor f_τ (shear
    strength over tensile strength); 0 at f_τ = 1/√3 (von Mises), 1 at f_τ = 1 (normal stress
    hypothesis). Below 1/√3 the mixing rule would extrapolate, which is refused."""
    f = _positive(f_tau, "shear strength factor f_tau")
    if np.any(f < 1.0 / SQRT3 - 1.0e-3) or np.any(f > 1.0):
        raise InputRangeError("shear strength factor f_tau must lie between 1/sqrt(3) and 1")
    return np.asarray((SQRT3 - 1.0 / f) / (SQRT3 - 1.0), dtype=np.float64)


@eq(SOURCE, "(6.2)", section="6.1.3", page=322)
@eq(SOURCE, "(6.16)", section="6.2.4", page=357, note="same form with pressure-corrected inputs")
def equivalent_stress(
    sigma_V_NH: npt.ArrayLike, sigma_V_Mises: npt.ArrayLike, q: npt.ArrayLike
) -> Array:
    """Interpolated equivalent stress σ_V = q σ_V,NH + (1 − q) σ_V,Mises."""
    nh = _array(sigma_V_NH, "normal stress hypothesis stress")
    mises = _array(sigma_V_Mises, "von Mises stress")
    control = _array(q, "control variable q")
    return np.asarray(control * nh + (1.0 - control) * mises, dtype=np.float64)


@eq(SOURCE, "(6.3)", section="6.1.3", page=325)
def hydrostatic_stress(
    sigma_1: npt.ArrayLike, sigma_2: npt.ArrayLike, sigma_3: npt.ArrayLike
) -> Array:
    """Hydrostatic stress σ_H = (σ_1 + σ_2 + σ_3) / 3."""
    s1 = _array(sigma_1, "sigma_1")
    s2 = _array(sigma_2, "sigma_2")
    s3 = _array(sigma_3, "sigma_3")
    return np.asarray((s1 + s2 + s3) / 3.0, dtype=np.float64)


@eq(
    SOURCE,
    "(6.3)",
    section="6.1.3",
    page=325,
    note="the deviatoric (von Mises) stress of the denominator",
)
@eq(SOURCE, "(6.17)", section="6.2.4", page=357)
def mises_stress(sigma_1: npt.ArrayLike, sigma_2: npt.ArrayLike, sigma_3: npt.ArrayLike) -> Array:
    """Von Mises stress √(½ [(σ_1 − σ_2)² + (σ_2 − σ_3)² + (σ_3 − σ_1)²]) of three principal (or
    pressure-corrected principal) stresses."""
    s1 = _array(sigma_1, "sigma_1")
    s2 = _array(sigma_2, "sigma_2")
    s3 = _array(sigma_3, "sigma_3")
    return np.asarray(
        np.sqrt(0.5 * ((s1 - s2) ** 2 + (s2 - s3) ** 2 + (s3 - s1) ** 2)), dtype=np.float64
    )


@eq(
    SOURCE,
    "(6.3)",
    section="6.1.3",
    page=325,
    note="Tabelle 6.2: 0 pure shear, 1/3 uniaxial, 2/3 equibiaxial, inf hydrostatic",
)
def multiaxiality_degree(
    sigma_1: npt.ArrayLike, sigma_2: npt.ArrayLike, sigma_3: npt.ArrayLike
) -> Array:
    """Degree of multiaxiality after Hencky, h = σ_H / σ_Mises; a hydrostatic state
    (σ_Mises = 0, σ_H ≠ 0) gives ±infinity as Tabelle 6.2 prints, an unloaded state (both zero)
    gives 0 by convention (see the module docstring)."""
    hydro = hydrostatic_stress(sigma_1, sigma_2, sigma_3)
    mises = mises_stress(sigma_1, sigma_2, sigma_3)
    shape = np.broadcast(hydro, mises).shape
    out = np.zeros(shape, dtype=np.float64)
    loaded = mises > 0.0
    np.divide(hydro, mises, out=out, where=loaded)
    hydrostatic = (~loaded) & (np.broadcast_to(hydro, shape) != 0.0)
    out[hydrostatic] = np.sign(np.broadcast_to(hydro, shape)[hydrostatic]) * np.inf
    return out


@eq(SOURCE, "(6.4)", section="6.1.3", page=326, note="Bild 6.8 and Bild 6.19")
def permissible_strain(
    h: npt.ArrayLike, epsilon_min: npt.ArrayLike, epsilon_max: npt.ArrayLike
) -> Array:
    """Permissible strain over the degree of multiaxiality: ε_max for h ≤ 1/3, otherwise
    (1 − 1/(3h)) (ε_min − ε_max) + ε_max, which falls from ε_max towards ε_min (ε_min at
    h = infinity, the hydrostatic state)."""
    degree = _array_or_infinite(h, "degree of multiaxiality h")
    lower = _positive(epsilon_min, "minimal permissible strain")
    upper = _positive(epsilon_max, "maximal permissible strain")
    if np.any(lower > upper):
        raise InputRangeError("epsilon_min must not exceed epsilon_max")
    scaled = np.where(
        degree > 1.0 / 3.0,
        (1.0 - 1.0 / (3.0 * np.where(degree > 1.0 / 3.0, degree, 1.0))) * (lower - upper) + upper,
        upper,
    )
    return np.asarray(scaled, dtype=np.float64)


@eq(
    SOURCE,
    "(6.5)",
    section="6.1.3",
    page=327,
    note="the 'natural' degree of multiaxiality after [KUN2017-2]",
)
def natural_multiaxiality_degree(
    sigma_1: npt.ArrayLike, sigma_2: npt.ArrayLike, sigma_3: npt.ArrayLike
) -> Array:
    """h = I_1 / σ_V,NH = (σ_1 + σ_2 + σ_3) / max(|σ_1|, |σ_2|, |σ_3|); 1 uniaxial, 2 equibiaxial,
    3 hydrostatic, 0 pure shear; 0 by convention for an unloaded state."""
    s1 = _array(sigma_1, "sigma_1")
    s2 = _array(sigma_2, "sigma_2")
    s3 = _array(sigma_3, "sigma_3")
    largest = np.maximum(np.maximum(np.abs(s1), np.abs(s2)), np.abs(s3))
    out = np.zeros(np.broadcast(s1, s2, s3).shape, dtype=np.float64)
    loaded = largest > 0.0
    np.divide(s1 + s2 + s3, largest, out=out, where=loaded)
    return out


@eq(SOURCE, "(6.6)", section="6.1.3", page=327)
def permissible_strain_natural(
    h: npt.ArrayLike, epsilon_min: npt.ArrayLike, epsilon_max: npt.ArrayLike
) -> Array:
    """Permissible strain over the natural degree of multiaxiality: ε_max for h ≤ 1, otherwise
    (1 − 1/h) · 3/2 · (ε_min − ε_max) + ε_max."""
    degree = _array_or_infinite(h, "natural degree of multiaxiality h")
    lower = _positive(epsilon_min, "minimal permissible strain")
    upper = _positive(epsilon_max, "maximal permissible strain")
    if np.any(lower > upper):
        raise InputRangeError("epsilon_min must not exceed epsilon_max")
    scaled = np.where(
        degree > 1.0,
        (1.0 - 1.0 / np.where(degree > 1.0, degree, 1.0)) * 1.5 * (lower - upper) + upper,
        upper,
    )
    return np.asarray(scaled, dtype=np.float64)


# --- 6.1.4 Haigh approximation -----------------------------------------------------------------


@eq(SOURCE, "(6.7)", section="6.1.4", page=328, note="Goodman line")
def goodman_amplitude(
    sigma_W: npt.ArrayLike, sigma_m: npt.ArrayLike, sigma_B: npt.ArrayLike
) -> Array:
    """Permissible amplitude on the Goodman line, σ_a = σ_w (1 − σ_m / σ_B); the book prints the
    alternating strength σ_w (lowercase) here and σ_W from Eq. (6.18) on."""
    alternating = _positive(sigma_W, "alternating strength sigma_W")
    mean = _array(sigma_m, "mean stress sigma_m")
    static = _positive(sigma_B, "static strength sigma_B")
    return np.asarray(alternating * (1.0 - mean / static), dtype=np.float64)


@eq(SOURCE, "(6.7)", section="6.1.4", page=328, note="Gerber parabola")
def gerber_amplitude(
    sigma_W: npt.ArrayLike, sigma_m: npt.ArrayLike, sigma_B: npt.ArrayLike
) -> Array:
    """Permissible amplitude on the Gerber parabola, σ_a = σ_w (1 − (σ_m / σ_B)²)."""
    alternating = _positive(sigma_W, "alternating strength sigma_W")
    mean = _array(sigma_m, "mean stress sigma_m")
    static = _positive(sigma_B, "static strength sigma_B")
    return np.asarray(alternating * (1.0 - (mean / static) ** 2), dtype=np.float64)


# --- 6.1.5 multiaxiality under cyclic loading ---------------------------------------------------


@eq(SOURCE, "(6.8)", section="6.1.5", page=332)
@eq(
    SOURCE,
    "(6.9)",
    section="6.1.5",
    page=332,
    note="applied to the amplitudes or the means of the components",
)
def mises_stress_plane(
    sigma_x: npt.ArrayLike, sigma_y: npt.ArrayLike, tau_xy: npt.ArrayLike
) -> Array:
    """Von Mises stress of a plane stress state, √(σ_x² + σ_y² − σ_x σ_y + 3 τ_xy²); with the
    amplitudes of the components it is σ_V,Mises,a, with the means σ_V,Mises,m of Eq. (6.9)."""
    sx = _array(sigma_x, "sigma_x")
    sy = _array(sigma_y, "sigma_y")
    txy = _array(tau_xy, "tau_xy")
    return np.asarray(np.sqrt(sx**2 + sy**2 - sx * sy + 3.0 * txy**2), dtype=np.float64)


@eq(SOURCE, "(6.9)", section="6.1.5", page=332)
def stress_amplitude(sigma_max: npt.ArrayLike, sigma_min: npt.ArrayLike) -> Array:
    """Amplitude of a component over the cycle, σ_a = (σ_max − σ_min) / 2."""
    upper = _array(sigma_max, "sigma_max")
    lower = _array(sigma_min, "sigma_min")
    if np.any(lower > upper):
        raise InputRangeError("sigma_min must not exceed sigma_max")
    return np.asarray((upper - lower) / 2.0, dtype=np.float64)


@eq(SOURCE, "(6.9)", section="6.1.5", page=332)
def mean_stress(sigma_max: npt.ArrayLike, sigma_min: npt.ArrayLike) -> Array:
    """Mean of a component over the cycle, σ_m = (σ_max + σ_min) / 2."""
    upper = _array(sigma_max, "sigma_max")
    lower = _array(sigma_min, "sigma_min")
    if np.any(lower > upper):
        raise InputRangeError("sigma_min must not exceed sigma_max")
    return np.asarray((upper + lower) / 2.0, dtype=np.float64)


@eq(
    SOURCE,
    "(6.10)",
    section="6.1.5",
    page=333,
    note="I_1 = sigma_11 + sigma_22 + sigma_33 = sigma_1 + sigma_2 + sigma_3",
)
def first_stress_invariant(
    sigma_1: npt.ArrayLike, sigma_2: npt.ArrayLike, sigma_3: npt.ArrayLike
) -> Array:
    """First invariant of the stress tensor, I_1 = σ_1 + σ_2 + σ_3 (the trace)."""
    s1 = _array(sigma_1, "sigma_1")
    s2 = _array(sigma_2, "sigma_2")
    s3 = _array(sigma_3, "sigma_3")
    return np.asarray(s1 + s2 + s3, dtype=np.float64)


@eq(SOURCE, "(6.10)", section="6.1.5", page=333, note="signed von Mises stress after [PVH2012]")
def signed_mises_stress(sigma_V_Mises: npt.ArrayLike, I_1: npt.ArrayLike) -> Array:
    """Signed von Mises stress of one state, σ_V,Mises(t) sgn(I_1(t)); the sign of the first
    invariant tells tension from compression. A state with I_1 = 0 keeps the sign 0, that is a
    vanishing value (pure shear carries no sign in this convention)."""
    mises = _array(sigma_V_Mises, "von Mises stress")
    trace = _array(I_1, "first invariant I_1")
    return np.asarray(mises * np.sign(trace), dtype=np.float64)


@eq(SOURCE, "(6.10)", section="6.1.5", page=333)
def signed_mises_amplitude(sigma_max: npt.ArrayLike, sigma_min: npt.ArrayLike) -> Array:
    """Corrected amplitude σ*_V,Mises,a = [max_t(σ_V sgn I_1) − min_t(σ_V sgn I_1)] / 2 of the
    largest and smallest signed von Mises stress of the cycle."""
    return stress_amplitude(sigma_max, sigma_min)


@eq(SOURCE, "(6.10)", section="6.1.5", page=333)
def signed_mises_mean(sigma_max: npt.ArrayLike, sigma_min: npt.ArrayLike) -> Array:
    """Corrected mean σ*_V,Mises,m = [max_t(σ_V sgn I_1) + min_t(σ_V sgn I_1)] / 2."""
    return mean_stress(sigma_max, sigma_min)


@eq(SOURCE, "(6.11)", section="6.1.5", page=334, note="Manson-McKnight, classic variant")
def manson_mcknight_mean(sigma_V_Mises_m: npt.ArrayLike, I_1_d: npt.ArrayLike) -> Array:
    """Corrected mean stress σ*_V,Mises,m = σ_V,Mises,m sgn(I_1,d), with I_1,d the first invariant
    at the state of the largest distance from zero within the cycle."""
    mean = _array(sigma_V_Mises_m, "component-wise von Mises mean stress")
    trace = _array(I_1_d, "first invariant at the largest distance from zero")
    return np.asarray(mean * np.sign(trace), dtype=np.float64)


@eq(
    SOURCE,
    "(6.12)",
    section="6.1.5",
    page=335,
    note="modified Manson-McKnight after [PVH2012] [NASA2014]",
)
def modified_manson_mcknight_mean(
    sigma_V_Mises_m: npt.ArrayLike, sigma_1_max: npt.ArrayLike, sigma_3_min: npt.ArrayLike
) -> Array:
    """Corrected mean stress σ*_V,Mises,m = σ_V,Mises,m (σ_1,max + σ_3,min) / (σ_1,max − σ_3,min);
    0 by convention when the largest and the smallest principal stress of the cycle coincide."""
    mean = _array(sigma_V_Mises_m, "component-wise von Mises mean stress")
    upper = _array(sigma_1_max, "largest principal stress of the cycle")
    lower = _array(sigma_3_min, "smallest principal stress of the cycle")
    if np.any(lower > upper):
        raise InputRangeError("sigma_3_min must not exceed sigma_1_max")
    out = np.zeros(np.broadcast(mean, upper, lower).shape, dtype=np.float64)
    span = upper - lower
    np.divide(mean * (upper + lower), span, out=out, where=span > 0.0)
    return out


@eq(
    SOURCE,
    "(6.13)",
    section="6.1.5",
    page=336,
    note="normalised equivalent stress hypothesis after [HAI2002] [FKM2012]",
)
def normalised_mises_utilisation(
    a_sigma_x: npt.ArrayLike, a_sigma_y: npt.ArrayLike, a_tau: npt.ArrayLike
) -> Array:
    """Equivalent utilisation a_V,Mises = √(a_σ,x² + a_σ,y² − a_σ,x a_σ,y + a_τ²) of the single
    utilisations a_σ = σ_a / σ_B and a_τ = τ_a / τ_B (the factor 3 of the shear term is absorbed by
    the shear strength τ_B = σ_B / √3)."""
    ax = _array(a_sigma_x, "single utilisation a_sigma_x")
    ay = _array(a_sigma_y, "single utilisation a_sigma_y")
    at = _array(a_tau, "single utilisation a_tau")
    return np.asarray(np.sqrt(ax**2 + ay**2 - ax * ay + at**2), dtype=np.float64)


# --- 6.1.6 notch stress correction ---------------------------------------------------------------


@eq(SOURCE, "(6.14)", section="6.1.6", page=341, note="Neuber's rule [NEU85]")
def neuber_product(sigma_el: npt.ArrayLike, E: npt.ArrayLike) -> Array:
    """Neuber's product σ_el ε_el = σ_el² / E, which the pseudo-plastic state σ_pl ε_pl must equal."""
    elastic = _array(sigma_el, "linear elastic stress")
    modulus = _positive(E, "modulus of elasticity E")
    return np.asarray(elastic**2 / modulus, dtype=np.float64)


# --- 6.2 static check ---------------------------------------------------------------------------


@eq(SOURCE, "(6.15)", section="6.2.4", page=355)
def static_utilisation(
    epsilon_V: npt.ArrayLike, epsilon_zul: npt.ArrayLike, S: npt.ArrayLike = 1.0
) -> Array:
    """Static utilisation a_stat = ε_V / (ε_zul / S); the check holds for a_stat ≤ 1. An
    infinite ε_V (the stress-strain curve never reaches σ_V) gives an infinite utilisation."""
    present = _array_or_infinite(epsilon_V, "equivalent strain")
    if np.any(present < 0.0):
        raise InputRangeError("equivalent strain must not be negative")
    permissible = _positive(epsilon_zul, "permissible strain")
    safety = _positive(S, "safety factor S")
    return np.asarray(present / (permissible / safety), dtype=np.float64)


@eq(SOURCE, "(6.17)", section="6.2.4", page=357)
def pressure_corrected_principal_stress(
    sigma_i: npt.ArrayLike, f_sigma: npt.ArrayLike = COMPRESSIVE_STRENGTH_FACTOR
) -> Array:
    """Pressure-corrected principal stress σ̄_i = σ_i / f_σ,i with f_σ = 1 for σ_i ≥ 0 and the
    compressive strength factor (1,3) for σ_i < 0."""
    stress = _array(sigma_i, "principal stress")
    factor = _positive(f_sigma, "compressive strength factor f_sigma")
    return np.asarray(np.where(stress < 0.0, stress / factor, stress), dtype=np.float64)


@eq(SOURCE, "(6.17)", section="6.2.4", page=357)
def normal_stress_hypothesis_stress(
    sigma_1: npt.ArrayLike, sigma_2: npt.ArrayLike, sigma_3: npt.ArrayLike
) -> Array:
    """Equivalent stress of the normal stress hypothesis, MAX(|σ_1|, |σ_2|, |σ_3|), of three
    principal (or pressure-corrected principal) stresses."""
    s1 = _array(sigma_1, "sigma_1")
    s2 = _array(sigma_2, "sigma_2")
    s3 = _array(sigma_3, "sigma_3")
    return np.asarray(np.maximum(np.maximum(np.abs(s1), np.abs(s2)), np.abs(s3)), dtype=np.float64)


@eq(SOURCE, "(6.16)", section="6.2.4", page=357)
@eq(SOURCE, "(6.17)", section="6.2.4", page=357)
def equivalent_stress_static(
    sigma_1: npt.ArrayLike,
    sigma_2: npt.ArrayLike,
    sigma_3: npt.ArrayLike,
    q: npt.ArrayLike,
    f_sigma: npt.ArrayLike = COMPRESSIVE_STRENGTH_FACTOR,
) -> Array:
    """Equivalent stress of the static check: the pressure-corrected principal stresses enter
    both hypotheses, σ_V = q σ̄_V,NH + (1 − q) σ̄_V,Mises."""
    s1 = pressure_corrected_principal_stress(sigma_1, f_sigma)
    s2 = pressure_corrected_principal_stress(sigma_2, f_sigma)
    s3 = pressure_corrected_principal_stress(sigma_3, f_sigma)
    return equivalent_stress(
        normal_stress_hypothesis_stress(s1, s2, s3), mises_stress(s1, s2, s3), q
    )


# --- 6.3 fatigue check -------------------------------------------------------------------------------


@eq(SOURCE, "(6.18)", section="6.3", page=360, note="Bild 6.24")
def component_fatigue_strength(
    K_B: npt.ArrayLike, K_M: npt.ArrayLike, sigma_W: npt.ArrayLike
) -> Array:
    """Component fatigue strength (an amplitude) σ_B = K_B K_M σ_W."""
    life = _positive(K_B, "fatigue life factor K_B")
    mean = _positive(K_M, "mean stress factor K_M")
    alternating = _positive(sigma_W, "component alternating strength sigma_W")
    return np.asarray(life * mean * alternating, dtype=np.float64)


@eq(
    SOURCE,
    "(6.19)",
    section="6.3.2",
    page=363,
    note="Bild 6.26: A_W per class; fixed 0,25 / 0,17 for reinforced",
)
def component_alternating_strength(A_W: npt.ArrayLike, K: npt.ArrayLike) -> Array:
    """Component alternating strength σ_W = A_W K at N_G and R = −1 from the static
    characteristic value K and the cyclic reduction factor A_W."""
    factor = _positive(A_W, "cyclic reduction factor A_W")
    static = _positive(K, "static characteristic value K")
    return np.asarray(factor * static, dtype=np.float64)


@eq(SOURCE, "(6.20)", section="6.3.3", page=367)
def mean_stress_factor(
    corrected_alternating_strength_mpa: npt.ArrayLike, sigma_W: npt.ArrayLike
) -> Array:
    """Mean stress factor K_M = σ'_W / σ_W, corrected over uncorrected alternating strength."""
    corrected = _array(
        corrected_alternating_strength_mpa, "mean stress corrected alternating strength"
    )
    alternating = _positive(sigma_W, "component alternating strength sigma_W")
    return np.asarray(corrected / alternating, dtype=np.float64)


@eq(
    SOURCE,
    "(6.21)",
    section="6.3.3",
    page=368,
    note="M = |sigma_W / sigma_Y|, the slope of the Goodman line of Bild 6.28",
)
def mean_stress_sensitivity(sigma_W: npt.ArrayLike, sigma_Y: npt.ArrayLike) -> Array:
    """Mean stress sensitivity M = |σ_W / σ_Y|; the Goodman line of the construction runs from
    σ_W on the amplitude axis to the static yield stress σ_Y on the mean stress axis."""
    alternating = _positive(sigma_W, "component alternating strength sigma_W")
    yield_stress = _positive(sigma_Y, "static yield stress sigma_Y")
    return np.asarray(np.abs(alternating / yield_stress), dtype=np.float64)


@eq(SOURCE, "(6.21)", section="6.3.3", page=367, note="overload case F1, mean stress constant")
def mean_stress_factor_case_1(
    M: npt.ArrayLike, sigma_m: npt.ArrayLike, sigma_W: npt.ArrayLike
) -> Array:
    """K_M = 1 − M s_m with the relative mean stress s_m = σ_m / σ_W (signed: the compression
    side gives K_M > 1, the mirrored line of Bild 6.28)."""
    sensitivity = _positive(M, "mean stress sensitivity M")
    mean = _array(sigma_m, "mean stress sigma_m")
    alternating = _positive(sigma_W, "component alternating strength sigma_W")
    return np.asarray(1.0 - sensitivity * mean / alternating, dtype=np.float64)


@eq(SOURCE, "(6.21)", section="6.3.3", page=367, note="overload case F2, stress ratio constant")
def mean_stress_factor_case_2(
    M: npt.ArrayLike, sigma_m: npt.ArrayLike, sigma_a: npt.ArrayLike
) -> Array:
    """K_M = 1 / (1 + M σ_m / σ_a). On the compression side the ray of constant R may never meet
    the continued Goodman line (1 + M σ_m/σ_a ≤ 0): the line then sets no limit and the factor
    is infinite, the static cap of Eq. (6.23) governs. A component without amplitude has no
    stress ratio and keeps K_M = 1 by convention (its utilisation is 0)."""
    sensitivity = _positive(M, "mean stress sensitivity M")
    mean = _array(sigma_m, "mean stress sigma_m")
    amplitude = _array(sigma_a, "stress amplitude sigma_a")
    if np.any(amplitude < 0.0):
        raise InputRangeError("stress amplitude sigma_a must not be negative")
    ratio = np.zeros(np.broadcast(sensitivity, mean, amplitude).shape, dtype=np.float64)
    np.divide(sensitivity * mean, amplitude, out=ratio, where=amplitude > 0.0)
    denominator = 1.0 + ratio
    out = np.full(denominator.shape, np.inf, dtype=np.float64)
    np.divide(1.0, denominator, out=out, where=denominator > 0.0)
    return out


@eq(SOURCE, "(6.21)", section="6.3.3", page=367, note="overload case F3, minimum stress constant")
def mean_stress_factor_case_3(
    M: npt.ArrayLike, sigma_min: npt.ArrayLike, sigma_W: npt.ArrayLike
) -> Array:
    """K_M = (1 − M s_min) / (1 + M) with the relative minimum stress s_min = σ_min / σ_W."""
    sensitivity = _positive(M, "mean stress sensitivity M")
    lower = _array(sigma_min, "minimum stress sigma_min")
    alternating = _positive(sigma_W, "component alternating strength sigma_W")
    return np.asarray(
        (1.0 - sensitivity * lower / alternating) / (1.0 + sensitivity), dtype=np.float64
    )


@eq(SOURCE, "(6.21)", section="6.3.3", page=368, note="overload case F4, maximum stress constant")
def mean_stress_factor_case_4(
    M: npt.ArrayLike, sigma_max: npt.ArrayLike, sigma_W: npt.ArrayLike
) -> Array:
    """K_M = (1 − M s_max) / (1 − M) with the relative maximum stress s_max = σ_max / σ_W; needs
    M < 1 (the Goodman line steeper than the R = −1 axis is excluded)."""
    sensitivity = _positive(M, "mean stress sensitivity M")
    if np.any(sensitivity >= 1.0):
        raise InputRangeError("overload case F4 needs a mean stress sensitivity M below 1")
    upper = _array(sigma_max, "maximum stress sigma_max")
    alternating = _positive(sigma_W, "component alternating strength sigma_W")
    return np.asarray(
        (1.0 - sensitivity * upper / alternating) / (1.0 - sensitivity), dtype=np.float64
    )


@eq(
    SOURCE,
    "(6.22)",
    section="6.3.4",
    page=371,
    note="Bild 6.31: the synthetic Woehler line between sigma_stat at N = 1 and sigma_W at N_G",
)
def fatigue_life_factor(N_G: npt.ArrayLike, N: npt.ArrayLike, k: npt.ArrayLike) -> Array:
    """Fatigue life factor K_B = (N_G / N̄)^(1/k) for the required number of cycles N̄; 1 at N_G,
    larger for fewer cycles."""
    limit = _positive(N_G, "limit number of cycles N_G")
    required = _positive(N, "required number of cycles N")
    slope = _positive(k, "slope exponent k")
    return np.asarray((limit / required) ** (1.0 / slope), dtype=np.float64)


@eq(
    SOURCE,
    "(6.22)",
    section="6.3.4",
    page=371,
    note="Tabelle 6.3: 15,65 to 20,44 for reinforced semi-crystalline",
)
def woehler_slope_exponent(
    A_S: npt.ArrayLike, A_W: npt.ArrayLike, N_G: npt.ArrayLike = LIMIT_NUMBER_OF_CYCLES
) -> Array:
    """Slope exponent of the synthetic Wöhler line, k = lg N_G / lg(A_S / A_W), from the reduction
    factor of a single static load A_S and the cyclic one A_W."""
    static = _positive(A_S, "static reduction factor A_S")
    cyclic = _positive(A_W, "cyclic reduction factor A_W")
    if np.any(static <= cyclic):
        raise InputRangeError("A_S must exceed A_W for a falling Woehler line")
    limit = _positive(N_G, "limit number of cycles N_G")
    return np.asarray(np.log10(limit) / np.log10(static / cyclic), dtype=np.float64)


@eq(
    SOURCE,
    "(6.22)",
    section="6.3.4",
    page=371,
    note="inverse: the N at which K_B equals a given value",
)
def cycles_at_fatigue_life_factor(
    K_B: npt.ArrayLike, k: npt.ArrayLike, N_G: npt.ArrayLike = LIMIT_NUMBER_OF_CYCLES
) -> Array:
    """The number of cycles N̄ = N_G / K_B^k at which the fatigue life factor takes the value
    K_B: the inverse of Eq. (6.22), used to read the predicted life of a node off the synthetic
    Wöhler line (the utilisation at N_G equals the K_B that brings it to one)."""
    life = _positive(K_B, "fatigue life factor K_B")
    slope = _positive(k, "slope exponent k")
    limit = _positive(N_G, "limit number of cycles N_G")
    return np.asarray(limit / life**slope, dtype=np.float64)


@eq(
    SOURCE,
    "(6.23)",
    section="6.3.4",
    page=372,
    note="Bild 6.32: the Haigh diagram bounded by the static component strength",
)
def max_component_fatigue_strength(sigma_stat: npt.ArrayLike, sigma_m: npt.ArrayLike) -> Array:
    """Largest permissible component fatigue strength σ_B,max = σ_stat − |σ_m|: the stress of the
    largest magnitude in the cycle may not exceed the static component strength. The book prints
    σ_stat − σ_m for the tension side; the magnitude extends it to the compression side of
    Bild 6.28 (module docstring)."""
    static = _positive(sigma_stat, "static component strength sigma_stat")
    mean = _array(sigma_m, "mean stress sigma_m")
    return np.asarray(static - np.abs(mean), dtype=np.float64)


@eq(SOURCE, "(6.23)", section="6.3.4", page=372)
def capped_component_fatigue_strength(sigma_B: npt.ArrayLike, sigma_B_max: npt.ArrayLike) -> Array:
    """σ_B = σ_B,max where σ_B > σ_B,max, else unchanged; an infinite σ_B (no Goodman limit on
    the compression side) takes the cap; a non-positive cap means the mean stress alone
    exhausts the static strength, and 0 is returned (the utilisation is then infinite)."""
    strength = _array_or_infinite(sigma_B, "component fatigue strength sigma_B")
    cap = _array(sigma_B_max, "largest permissible component fatigue strength")
    return np.asarray(np.maximum(np.minimum(strength, cap), 0.0), dtype=np.float64)


@eq(SOURCE, "(6.24)", section="6.3.5", page=374)
def cyclic_utilisation(a_B_NH: npt.ArrayLike, a_B_Mises: npt.ArrayLike, q: npt.ArrayLike) -> Array:
    """Cyclic equivalent utilisation a_B,V = q a_B,NH + (1 − q) a_B,Mises; the check holds for
    a_B,V ≤ 1. q as in the static check but without the pressure correction."""
    nh = _array(a_B_NH, "utilisation of the normal stress hypothesis")
    mises = _array(a_B_Mises, "utilisation after von Mises")
    control = _array(q, "control variable q")
    return np.asarray(control * nh + (1.0 - control) * mises, dtype=np.float64)


@eq(SOURCE, "(6.25)", section="6.3.5", page=374)
def cyclic_utilisation_mises(
    a_sigma_1: npt.ArrayLike, a_sigma_2: npt.ArrayLike, a_sigma_3: npt.ArrayLike
) -> Array:
    """a_B,Mises = √(½ [(a_σ,1 − a_σ,2)² + (a_σ,2 − a_σ,3)² + (a_σ,3 − a_σ,1)²]) of the single
    utilisations of the three principal directions."""
    return mises_stress(a_sigma_1, a_sigma_2, a_sigma_3)


@eq(SOURCE, "(6.25)", section="6.3.5", page=374)
def cyclic_utilisation_normal_stress(
    a_sigma_1: npt.ArrayLike, a_sigma_2: npt.ArrayLike, a_sigma_3: npt.ArrayLike
) -> Array:
    """a_B,NH = MAX(|a_σ,1|, |a_σ,2|, |a_σ,3|)."""
    return normal_stress_hypothesis_stress(a_sigma_1, a_sigma_2, a_sigma_3)


@eq(SOURCE, "(6.26)", section="6.3.5", page=374)
def single_utilisation(sigma_a_i: npt.ArrayLike, sigma_B: npt.ArrayLike) -> Array:
    """Single cyclic utilisation a_σ,i = σ_a,i / σ_B: the amplitude of the component over the
    component fatigue strength (the mean stress is already inside σ_B through K_M). A vanishing
    σ_B (the static strength exhausted by the mean stress) gives an infinite utilisation."""
    amplitude = _array(sigma_a_i, "stress amplitude of the component")
    if np.any(amplitude < 0.0):
        raise InputRangeError("stress amplitude sigma_a_i must not be negative")
    strength = _array(sigma_B, "component fatigue strength sigma_B")
    if np.any(strength < 0.0):
        raise InputRangeError("component fatigue strength sigma_B must not be negative")
    out = np.full(np.broadcast(amplitude, strength).shape, np.inf, dtype=np.float64)
    positive = strength > 0.0
    np.divide(amplitude, strength, out=out, where=positive)
    out[(~positive) & (np.broadcast_to(amplitude, out.shape) == 0.0)] = 0.0
    return out
