"""The node-wise check: the history of every node over the mesh cycle and the two utilisations.

A node of the wheel sees, while the wheel turns once, the unloaded state, the compression from
the neighbouring tooth that carries the load before, its own loading as the tooth passes
through the mesh, and the compression from the tooth after. The FE series computes static
positions along the path of contact (one job each); the history of a node is the set of those
states plus the unloaded state, so that the stress ratio of the cycle is right. The
``HistoryAccumulator`` ingests the states one position at a time (the stress files are read
one after another, nothing is stacked) and keeps the running extremes every route needs.

Static check (section 6.2): per state the pressure-corrected equivalent stress σ_V (Eq. (6.16),
(6.17)), the degree of multiaxiality h (Eq. (6.3)), the permissible strain ε_zul(h) of the load
case (Eq. (6.4) with the bounds of the material class) and ε_V(σ_V) on the service isotherm;
a_stat = ε_V / (ε_zul / S) (Eq. (6.15)); the node keeps its largest a_stat and the state that
gave it (the governing state, whose h, σ_stat and principal directions also serve the cyclic
check). A σ_V the isotherm never reaches gives an infinite a_stat.

Cyclic check (section 6.3): the amplitude and mean of the cycle by one of four routes, the mean
stress factor K_M of the overload case (Eq. (6.21)), the fatigue life factor K_B of the required
cycles (Eq. (6.22)), the component fatigue strength σ_B = K_B K_M σ_W (Eq. (6.18)) capped by the
static component strength (Eq. (6.23)), the single utilisations (Eq. (6.26)) and their
combination (Eq. (6.24), (6.25)):

* ``principal`` (default; the component-wise check of section 6.3.5 with the principal
  directions as the components, p. 368 "komponentenweise, pro Spannungskomponente"): the
  directions are those of the governing state of a node and stay fixed over the cycle; every
  state is projected onto them (n_i^T S n_i), so a component keeps its sign when the stress
  reverses between tension and compression. This needs a second pass over the states
  (``project_state``) after the governing state is known. Sorting the principal values per
  state instead would split one reversing component into two half amplitudes (review of
  2026-10-11, ADR-118);
* ``signed_mises`` (Eq. (6.10)): one scalar history, σ_V,Mises sgn(I_1); amplitude and mean
  of it; a_B,V = σ*_a / σ_B (q plays no part, both hypotheses coincide for one component);
* ``mmk`` and ``mmk_modified`` (Eq. (6.9) with (6.11) or (6.12)): the amplitude is the von
  Mises stress of the component amplitudes, the mean the von Mises stress of the component means
  with the sign of I_1 at the state farthest from zero, or with the ratio of the extreme principal
  stresses; the components are those of the part frame, which the stress files carry, so these
  routes refuse a file whose instance rotation is unknown.

The predicted life of a node is the number of cycles at which a_B,V reaches 1 on the synthetic
Wöhler line (K_B of Eq. (6.22) with the cap of Eq. (6.23)); below 10^4 cycles the method does
not apply (p. 372), beyond N_G it extrapolates (p. 328: a further drop is to be expected).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt

from gearcore.errors import InputRangeError
from gearcore.fatigue import materials as mt
from gearcore.fatigue import stommel as st
from gearcore.fe import stress as sf

Array = npt.NDArray[np.float64]
AmplitudeRoute = Literal["principal", "signed_mises", "mmk", "mmk_modified"]
ROUTES: tuple[AmplitudeRoute, ...] = ("principal", "signed_mises", "mmk", "mmk_modified")
COMPONENT_ROUTES: tuple[AmplitudeRoute, ...] = ("mmk", "mmk_modified")
"""Routes that work with the components of the part frame and need the instance rotation."""
LIFE_GRID = np.logspace(3.0, 10.0, 71)
"""Cycles at which the utilisation is evaluated to read the predicted life (10 per decade)."""


@dataclass(frozen=True)
class CheckSettings:
    """What the user decides for a check (ADR-118)."""

    load_case: mt.LoadCase = "einmalig"
    """Row of Bild 6.18 for the static check: the first application of the load."""
    overload_case: int = 2
    """F1 to F4 of Eq. (6.21); the Bachelor thesis chose F2 (R constant)."""
    amplitude_route: AmplitudeRoute = "principal"
    required_cycles: float = st.LIMIT_NUMBER_OF_CYCLES
    """N̄ of Eq. (6.22); N_G gives K_B = 1, the check against the limit stress amplitude."""
    safety: float = 1.0
    compressive_strength_factor: float = st.COMPRESSIVE_STRENGTH_FACTOR
    include_unloaded_state: bool = True
    """Add the state σ = 0 to every history (the wheel turns out of the mesh)."""

    def __post_init__(self) -> None:
        if self.overload_case not in (1, 2, 3, 4):
            raise InputRangeError(f"overload case must be 1 to 4, got {self.overload_case!r}")
        if self.amplitude_route not in ROUTES:
            raise InputRangeError(
                f"amplitude route must be one of {ROUTES}, got {self.amplitude_route!r}"
            )
        if not self.required_cycles > 0.0 or not self.safety > 0.0:
            raise InputRangeError("required cycles and safety must be positive")


class HistoryAccumulator:
    """Running extremes of every node over the states of one series and load step.

    First pass: ``add_state`` for every state (the static check, the extremes of the principal
    values, components and signed von Mises stress, the governing state with its principal
    directions). Second pass, needed by the ``principal`` route only: ``start_second_pass`` and
    then ``project_state`` for the same states in any order (the normal stresses along the
    fixed directions)."""

    def __init__(self, material: mt.StommelMaterial, settings: CheckSettings, n_nodes: int) -> None:
        if n_nodes <= 0:
            raise InputRangeError("a history needs at least one node")
        self.material = material
        self.settings = settings
        self.n = n_nodes
        self.states = 0
        self.projected_states = 0
        shape3 = (n_nodes, 3)
        self.principal_max = np.full(shape3, -np.inf)
        self.principal_min = np.full(shape3, np.inf)
        self.component_max = np.full((n_nodes, 6), -np.inf)
        self.component_min = np.full((n_nodes, 6), np.inf)
        self.signed_max = np.full(n_nodes, -np.inf)
        self.signed_min = np.full(n_nodes, np.inf)
        self.signed_abs_max = np.zeros(n_nodes)
        self.I_1_at_abs_max = np.zeros(n_nodes)
        self.a_stat = np.full(n_nodes, -np.inf)
        self.sigma_V_at_max = np.zeros(n_nodes)
        self.h_at_max = np.zeros(n_nodes)
        self.epsilon_zul_at_max = np.zeros(n_nodes)
        self.sigma_stat_at_max = np.zeros(n_nodes)
        self.state_of_max = np.full(n_nodes, -1, dtype=np.int64)
        self.directions = np.broadcast_to(np.eye(3), (n_nodes, 3, 3)).copy()
        """(n, 3, 3): column i is the direction of the i-th principal stress (σ_1 ≥ σ_2 ≥ σ_3)
        at the governing state; the identity for a node without a loaded state."""
        self.projected_max = np.full(shape3, -np.inf)
        self.projected_min = np.full(shape3, np.inf)
        self._strain_limits = mt.strain_limits_percent(material, settings.load_case)
        self._unloaded = np.zeros((n_nodes, 6))
        if settings.include_unloaded_state:
            self.add_state(self._unloaded, label=-1)

    def _state(self, components: npt.ArrayLike) -> Array:
        s = np.asarray(components, dtype=np.float64)
        if s.shape != (self.n, 6):
            raise InputRangeError(f"state of shape {s.shape}, expected {(self.n, 6)}")
        if not np.all(np.isfinite(s)):
            raise InputRangeError("a state holds non-finite stresses")
        return s

    def add_state(self, components: npt.ArrayLike, *, label: int) -> None:
        """First pass: ingest one state, (n, 6) components in the part frame; ``label`` names
        the state (the index of the position, −1 for the unloaded state)."""
        s = self._state(components)
        values, vectors = np.linalg.eigh(st.tensors_from_components(s))  # ascending
        s1, s2, s3 = values[:, 2], values[:, 1], values[:, 0]
        principal = np.stack([s1, s2, s3], axis=1)
        np.maximum(self.principal_max, principal, out=self.principal_max)
        np.minimum(self.principal_min, principal, out=self.principal_min)
        np.maximum(self.component_max, s, out=self.component_max)
        np.minimum(self.component_min, s, out=self.component_min)
        mises = st.mises_stress(s1, s2, s3)
        trace = st.first_stress_invariant(s1, s2, s3)
        signed = st.signed_mises_stress(mises, trace)
        np.maximum(self.signed_max, signed, out=self.signed_max)
        np.minimum(self.signed_min, signed, out=self.signed_min)
        farther = np.abs(signed) > self.signed_abs_max
        self.signed_abs_max[farther] = np.abs(signed[farther])
        self.I_1_at_abs_max[farther] = trace[farther]
        # static check of this state
        settings = self.settings
        h = st.multiaxiality_degree(s1, s2, s3)
        sigma_V = st.equivalent_stress_static(
            s1, s2, s3, self.material.q, settings.compressive_strength_factor
        )
        lower, upper = self._strain_limits
        epsilon_zul = st.permissible_strain(h, lower, upper)
        epsilon_V = mt.equivalent_strain_percent(self.material.service_curve, sigma_V)
        a_stat = st.static_utilisation(epsilon_V, epsilon_zul, settings.safety)
        worse = a_stat > self.a_stat
        self.a_stat[worse] = a_stat[worse]
        self.sigma_V_at_max[worse] = sigma_V[worse]
        self.h_at_max[worse] = h[worse]
        self.epsilon_zul_at_max[worse] = epsilon_zul[worse]
        self.sigma_stat_at_max[worse] = mt.stress_on_isotherm(
            self.material.service_curve, epsilon_zul[worse]
        )
        self.state_of_max[worse] = label
        self.directions[worse] = vectors[worse][:, :, ::-1]  # columns σ_1, σ_2, σ_3
        self.states += 1

    def start_second_pass(self) -> None:
        """Project the unloaded state, when the history includes it, before the positions."""
        if self.settings.include_unloaded_state:
            self.project_state(self._unloaded)

    def project_state(self, components: npt.ArrayLike) -> None:
        """Second pass: the normal stresses n_i^T S n_i of one state along the fixed principal
        directions of the governing state; call it for every position of the first pass."""
        s = self._state(components)
        projected = np.einsum(
            "nki,nkl,nli->ni", self.directions, st.tensors_from_components(s), self.directions
        )
        np.maximum(self.projected_max, projected, out=self.projected_max)
        np.minimum(self.projected_min, projected, out=self.projected_min)
        self.projected_states += 1

    @property
    def projection_complete(self) -> bool:
        return self.states > 0 and self.projected_states == self.states


def accumulate(
    material: mt.StommelMaterial, settings: CheckSettings, states: Sequence[npt.ArrayLike]
) -> HistoryAccumulator:
    """Both passes over states held in memory (tests, small folders)."""
    if not states:
        raise InputRangeError("no state")
    first = np.asarray(states[0], dtype=np.float64)
    history = HistoryAccumulator(material, settings, first.shape[0])
    for label, state in enumerate(states):
        history.add_state(state, label=label)
    history.start_second_pass()
    for state in states:
        history.project_state(state)
    return history


@dataclass(frozen=True)
class CyclicQuantities:
    """Amplitude, mean and the chain to the utilisation of one route; arrays (n,) or (n, 3)."""

    route: AmplitudeRoute
    sigma_a: Array
    sigma_m: Array
    K_M: Array
    sigma_B_uncapped: Array
    sigma_B_max: Array
    sigma_B: Array
    a_sigma: Array
    a_B_Mises: Array
    a_B_NH: Array
    a_B_V: Array


@dataclass(frozen=True)
class CheckResult:
    """The check of every node of one series and load step."""

    node_labels: npt.NDArray[np.int32]
    settings: CheckSettings
    material: str
    states: int
    a_stat: Array
    sigma_V_max: Array
    h_at_max: Array
    epsilon_zul: Array
    sigma_stat: Array
    state_of_max: npt.NDArray[np.int64]
    q: float
    sigma_W: Array
    sigma_Y_service: float
    M: Array
    k: Array
    K_B: Array
    """Per node (k depends on h)."""
    cyclic: CyclicQuantities
    N_predicted: Array
    """Cycles at which a_B,V reaches 1 on the synthetic line; inf when it stays below 1 up to
    the end of the grid, 0 when it exceeds 1 already at its start."""
    life_flags: tuple[str, ...]
    a_B_V_at_N_G: Array
    extras: Mapping[str, object] = field(default_factory=dict)

    @property
    def critical_static(self) -> int:
        return int(np.argmax(self.a_stat))

    @property
    def critical_cyclic(self) -> int:
        return int(np.argmax(self.cyclic.a_B_V))


def _mean_stress_factor(
    settings: CheckSettings,
    M: Array,
    sigma_a: Array,
    sigma_m: Array,
    sigma_max: Array,
    sigma_min: Array,
    sigma_W: Array,
) -> Array:
    case = settings.overload_case
    if case == 1:
        return st.mean_stress_factor_case_1(M, sigma_m, sigma_W)
    if case == 2:
        return st.mean_stress_factor_case_2(M, sigma_m, sigma_a)
    if case == 3:
        return st.mean_stress_factor_case_3(M, sigma_min, sigma_W)
    return st.mean_stress_factor_case_4(M, sigma_max, sigma_W)


def _strength_chain(
    K_B: Array, K_M: Array, sigma_W: Array, sigma_stat: Array, sigma_m: Array
) -> tuple[Array, Array, Array]:
    """σ_B uncapped, its cap and the capped value. A non-positive K_M (the Haigh diagram gives
    no amplitude at that mean stress, tension side) leaves no strength; an infinite K_M (the ray
    of constant R never meets the continued line, compression side) leaves the cap alone."""
    positive = np.maximum(K_M, 0.0)
    uncapped = np.asarray(K_B * positive * sigma_W, dtype=np.float64)
    cap = st.max_component_fatigue_strength(sigma_stat, sigma_m)
    return uncapped, cap, st.capped_component_fatigue_strength(uncapped, cap)


def _mises_of_components(components: Array) -> Array:
    s1, s2, s3 = st.principal_stresses(components)
    return st.mises_stress(s1, s2, s3)


def _amplitude_and_mean(
    history: HistoryAccumulator, route: AmplitudeRoute
) -> tuple[Array, Array, Array, Array]:
    """(σ_a, σ_m, σ_max, σ_min) of the route; (n, 3) for ``principal``, (n,) otherwise."""
    if route == "principal":
        if not history.projection_complete:
            raise InputRangeError(
                "the principal route needs the second pass over every state (project_state)"
            )
        upper, lower = history.projected_max, history.projected_min
        return st.stress_amplitude(upper, lower), st.mean_stress(upper, lower), upper, lower
    if route == "signed_mises":
        s_max, s_min = history.signed_max, history.signed_min
        return (
            st.signed_mises_amplitude(s_max, s_min),
            st.signed_mises_mean(s_max, s_min),
            s_max,
            s_min,
        )
    amplitude_components = st.stress_amplitude(history.component_max, history.component_min)
    mean_components = st.mean_stress(history.component_max, history.component_min)
    sigma_a = _mises_of_components(amplitude_components)
    mises_mean = _mises_of_components(mean_components)
    if route == "mmk":
        sigma_m = st.manson_mcknight_mean(mises_mean, history.I_1_at_abs_max)
    else:
        sigma_m = st.modified_manson_mcknight_mean(
            mises_mean, history.principal_max[:, 0], history.principal_min[:, 2]
        )
    return sigma_a, sigma_m, sigma_m + sigma_a, sigma_m - sigma_a


def _utilisation(
    route: AmplitudeRoute, sigma_a: Array, sigma_B: Array, q: float
) -> tuple[Array, Array, Array, Array]:
    """The single utilisations and their combination; a node with an infinite single
    utilisation (no strength left) gets an infinite a_B,V without entering Eq. (6.25)."""
    a_sigma = st.single_utilisation(sigma_a, sigma_B)
    if route != "principal":
        return a_sigma, a_sigma, a_sigma, a_sigma
    finite = np.all(np.isfinite(a_sigma), axis=1)
    a_mises = np.full(a_sigma.shape[0], np.inf)
    a_nh = np.full(a_sigma.shape[0], np.inf)
    a_v = np.full(a_sigma.shape[0], np.inf)
    if np.any(finite):
        rows = a_sigma[finite]
        a_mises[finite] = st.cyclic_utilisation_mises(rows[:, 0], rows[:, 1], rows[:, 2])
        a_nh[finite] = st.cyclic_utilisation_normal_stress(rows[:, 0], rows[:, 1], rows[:, 2])
        a_v[finite] = st.cyclic_utilisation(a_nh[finite], a_mises[finite], q)
    return a_sigma, a_mises, a_nh, a_v


def cyclic_quantities(
    history: HistoryAccumulator,
    sigma_W: Array,
    M: Array,
    K_B: npt.ArrayLike,
    route: AmplitudeRoute | None = None,
) -> CyclicQuantities:
    """The chain from the history to a_B,V for one route at the fatigue life factor K_B."""
    settings = history.settings
    chosen: AmplitudeRoute = settings.amplitude_route if route is None else route
    sigma_a, sigma_m, sigma_max, sigma_min = _amplitude_and_mean(history, chosen)
    per_component = sigma_a.ndim == 2

    def expand(value: npt.ArrayLike) -> Array:
        array = np.asarray(value, dtype=np.float64)
        return array[:, None] if per_component and array.ndim == 1 else array

    K_M = _mean_stress_factor(
        settings, expand(M), sigma_a, sigma_m, sigma_max, sigma_min, expand(sigma_W)
    )
    uncapped, cap, sigma_B = _strength_chain(
        expand(K_B), K_M, expand(sigma_W), expand(history.sigma_stat_at_max), sigma_m
    )
    a_sigma, a_mises, a_nh, a_V = _utilisation(chosen, sigma_a, sigma_B, history.material.q)
    return CyclicQuantities(
        route=chosen,
        sigma_a=sigma_a,
        sigma_m=sigma_m,
        K_M=K_M,
        sigma_B_uncapped=uncapped,
        sigma_B_max=cap,
        sigma_B=sigma_B,
        a_sigma=a_sigma,
        a_B_Mises=a_mises,
        a_B_NH=a_nh,
        a_B_V=a_V,
    )


def predicted_cycles(
    history: HistoryAccumulator,
    sigma_W: Array,
    M: Array,
    k: Array,
    route: AmplitudeRoute | None = None,
) -> tuple[Array, tuple[str, ...]]:
    """The cycles at which a_B,V of every node reaches 1 on the synthetic Wöhler line, read off
    the grid ``LIFE_GRID`` with the cap of Eq. (6.23) applied at every grid point (the cap makes
    the utilisation independent of N where it binds), interpolated in lg N. Flags per node:
    ``ok`` (between 10^4 and N_G), ``below_1e4`` (the method does not apply), ``beyond_N_G``
    (extrapolated), ``none`` (a_B,V stays below 1 up to 10^10, N = inf), ``immediate`` (above 1
    already at 10^3, N = 0)."""
    n = history.n
    values = np.empty((LIFE_GRID.size, n))
    for i, cycles in enumerate(LIFE_GRID):
        K_B = st.fatigue_life_factor(st.LIMIT_NUMBER_OF_CYCLES, cycles, k)
        values[i] = cyclic_quantities(history, sigma_W, M, K_B, route).a_B_V
    log_grid = np.log10(LIFE_GRID)
    predicted = np.full(n, np.inf)
    flags = ["none"] * n
    for j in range(n):
        column = values[:, j]
        above = column > 1.0
        if above[0]:
            predicted[j] = 0.0
            flags[j] = "immediate"
            continue
        if not np.any(above):
            continue
        i = int(np.argmax(above))  # first grid point above one
        y0, y1 = column[i - 1], column[i]
        x0, x1 = log_grid[i - 1], log_grid[i]
        log_n = x0 + (x1 - x0) * (1.0 - y0) / (y1 - y0) if np.isfinite(y1) and y1 > y0 else x0
        predicted[j] = 10.0**log_n
        if predicted[j] < st.LOWEST_NUMBER_OF_CYCLES:
            flags[j] = "below_1e4"
        elif predicted[j] > st.LIMIT_NUMBER_OF_CYCLES:
            flags[j] = "beyond_N_G"
        else:
            flags[j] = "ok"
    return predicted, tuple(flags)


def check(history: HistoryAccumulator, node_labels: npt.ArrayLike) -> CheckResult:
    """The static and cyclic check of every node after the history is complete."""
    if history.states == 0:
        raise InputRangeError("the history holds no state")
    labels = np.asarray(node_labels, dtype=np.int32)
    if labels.shape != (history.n,):
        raise InputRangeError(f"{labels.size} labels for {history.n} nodes")
    material = history.material
    settings = history.settings
    h = history.h_at_max
    sigma_W = mt.component_alternating_strength_mpa(material, h)
    sigma_Y = material.sigma_Y_service_mpa
    M = st.mean_stress_sensitivity(sigma_W, sigma_Y)
    k = mt.slope_exponent(material, h)
    K_B = st.fatigue_life_factor(st.LIMIT_NUMBER_OF_CYCLES, settings.required_cycles, k)
    cyclic = cyclic_quantities(history, sigma_W, M, K_B)
    at_limit = cyclic_quantities(history, sigma_W, M, np.ones_like(k))
    predicted, flags = predicted_cycles(history, sigma_W, M, k)
    return CheckResult(
        node_labels=labels,
        settings=settings,
        material=material.name,
        states=history.states,
        a_stat=history.a_stat.copy(),
        sigma_V_max=history.sigma_V_at_max.copy(),
        h_at_max=h.copy(),
        epsilon_zul=history.epsilon_zul_at_max.copy(),
        sigma_stat=history.sigma_stat_at_max.copy(),
        state_of_max=history.state_of_max.copy(),
        q=material.q,
        sigma_W=sigma_W,
        sigma_Y_service=sigma_Y,
        M=M,
        k=k,
        K_B=np.asarray(K_B, dtype=np.float64),
        cyclic=cyclic,
        N_predicted=predicted,
        life_flags=flags,
        a_B_V_at_N_G=at_limit.a_B_V,
    )


@dataclass(frozen=True)
class FolderCheck:
    """The check of a series and load step of a folder with what went into it."""

    result: CheckResult
    step: str
    series: str | None
    positions_used: tuple[str, ...]
    positions_skipped: tuple[tuple[str, str], ...]
    """(job, reason) of the positions left out: no stress file, step not computed, broke off."""
    stress_file: sf.StressFile
    """The first stress file (node table, coordinates and sets of the wheel)."""


def _usable_files(
    positions: Sequence[sf.PositionStress], step: str, route: AmplitudeRoute
) -> tuple[list[tuple[sf.PositionStress, sf.StressFile]], list[tuple[str, str]]]:
    usable: list[tuple[sf.PositionStress, sf.StressFile]] = []
    skipped: list[tuple[str, str]] = []
    first: sf.StressFile | None = None
    for position in positions:
        job = position.point.job
        if position.path is None:
            skipped.append((job, "no stress file"))
            continue
        file = sf.read_stress_file(position.path)
        if step not in file.step_names:
            skipped.append((job, f"step {step} not computed"))
            continue
        if not file.is_complete(step):
            skipped.append((job, f"step {step} broke off"))
            continue
        if route in COMPONENT_ROUTES and not file.wheel_turn_known:
            raise InputRangeError(
                f"{position.path.name}: the instance rotation is unknown; the route {route} works "
                "with the components of the part frame and needs it"
            )
        if first is None:
            first = file
        elif file.n_nodes != first.n_nodes or not np.array_equal(
            file.node_labels, first.node_labels
        ):
            raise InputRangeError(
                f"{position.path.name}: node table differs from {first.path.name}"
            )
        usable.append((position, file))
    return usable, skipped


def check_folder(
    folder: Path,
    manifest: Mapping[str, object],
    material: mt.StommelMaterial,
    settings: CheckSettings,
    *,
    step: str,
    series: str | None = None,
    progress: Callable[[str], None] | None = None,
) -> FolderCheck:
    """Assemble the history of every wheel node from the stress files of one series and load
    step of a folder and run the check. Positions whose step broke off or that have no stress
    file are skipped and listed. The ``principal`` route reads the files a second time for the
    projection onto the fixed directions."""
    positions = sf.positions_with_stress(manifest, folder, series)
    if not positions:
        raise InputRangeError(f"{folder}: no positions of series {series!r}")
    usable, skipped = _usable_files(positions, step, settings.amplitude_route)
    if not usable:
        raise InputRangeError(
            f"{folder}: no complete position of step {step!r} in series {series!r}"
        )
    first = usable[0][1]
    history = HistoryAccumulator(material, settings, first.n_nodes)
    for position, file in usable:
        history.add_state(file.stress(step), label=position.point.index)
        if progress is not None:
            progress(f"{position.point.job}: state {history.states} ingested")
    if settings.amplitude_route == "principal":
        history.start_second_pass()
        for position, stress_file in usable:
            file = sf.read_stress_file(stress_file.path)  # read again, nothing is stacked
            history.project_state(file.stress(step))
            if progress is not None:
                progress(f"{position.point.job}: projected onto the fixed directions")
    result = check(history, first.node_labels)
    return FolderCheck(
        result=result,
        step=step,
        series=series,
        positions_used=tuple(position.point.job for position, _ in usable),
        positions_skipped=tuple(skipped),
        stress_file=first,
    )
