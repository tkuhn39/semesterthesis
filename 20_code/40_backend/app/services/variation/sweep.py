"""
@module: app.services.variation.sweep
@context: Domain layer — the orchestration of the plastic-capable Stufenvariation
       on top of the vectorized kernel (ADR-013).
@role: Turn a parameter space (a cartesian **grid** or a quasi-random **Sobol/LHS**
       sample) into a batch, evaluate it through ``kernel`` with **per-gear material
       dispatch** (steel → ISO 6336 limits, plastic → VDI 2736 limits) over the shared
       mesh, **prune** invalid variants early, and return the safety factors plus a
       **Pareto** front of the good macro-geometries. Missing non-essential data
       degrades to a *warning*, never a block (graceful, ADR-013).

The heavy lifting (geometry, tip-load form factors, stresses) is vectorized in
``kernel`` and validated against the scalar models; this layer only assembles the
inputs, dispatches the permissible stresses and selects the non-dominated set.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from scipy.stats import qmc

from app.services.materials import Material
from app.services.variation import kernel

Array = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


@dataclass(frozen=True)
class Varied:
    """A swept parameter — explicit ``values`` (grid) or ``bounds`` (Sobol/LHS)."""

    values: tuple[float, ...] | None = None
    bounds: tuple[float, float] | None = None

    def grid_values(self) -> np.ndarray:
        if self.values is None:
            raise ValueError("a grid sweep needs explicit `values` for every parameter")
        return np.asarray(self.values, dtype=float)


@dataclass
class VariationSpec:
    """The parameter space and the fixed design context of a Stufenvariation.

    Swept parameters live in ``varied`` (keyed by ``m_n``, ``z1``, ``z2``, ``x1``,
    ``x2``, ``beta_deg``, ``b``); everything not varied takes its ``fixed`` value.
    """

    materials: tuple[Material, Material]
    torque_nm: float  # pinion torque T_1
    varied: dict[str, Varied] = field(default_factory=dict)
    fixed: dict[str, float] = field(default_factory=dict)
    normal_pressure_angle_deg: float = 20.0
    addendum_factor: float = 1.0  # h_aP*
    tool_addendum_factor: float = 1.25  # h_aP0*
    tool_tip_radius_factor: float = 0.38  # ρ_aP0*
    application_factor: float = 1.0  # K_A
    dynamic_factor: float = 1.0  # K_v (scalar for the sweep; native kernel later)
    face_load_factor: float = 1.0  # K_Hβ / K_Fβ
    transverse_factor: float = 1.0  # K_Hα / K_Fα
    root_minimum_safety: float = 1.4
    flank_minimum_safety: float = 1.0

    def _value(self, name: str, grid: dict[str, Array]) -> Array:
        if name in grid:
            return grid[name]
        if name in self.fixed:
            return np.asarray(self.fixed[name], dtype=float)
        raise KeyError(f"parameter '{name}' is neither varied nor fixed")


@dataclass(frozen=True)
class VariationResult:
    """The flattened batch result of a Stufenvariation."""

    parameters: dict[str, Array]  # the (broadcast) input arrays per variant
    transverse_contact_ratio: Array
    overlap_ratio: Array
    total_contact_ratio: Array
    flank_stress_mpa: Array  # σ_H (shared mesh)
    root_stress_mpa: tuple[Array, Array]  # σ_F per gear
    flank_safety: tuple[Array, Array]  # S_H per gear (NaN where the limit is missing)
    root_safety: tuple[Array, Array]  # S_F per gear
    valid: BoolArray  # boolean pruning mask
    warnings: tuple[str, ...]


def build_grid(spec: VariationSpec) -> dict[str, Array]:
    """Full cartesian product of the swept ``values`` (flattened to 1-D arrays)."""
    names = list(spec.varied)
    axes = [spec.varied[n].grid_values() for n in names]
    if not names:
        return {}
    mesh = np.meshgrid(*axes, indexing="ij")
    return {n: m.reshape(-1) for n, m in zip(names, mesh, strict=True)}


def build_sample(
    spec: VariationSpec, count: int, *, method: str = "sobol", seed: int = 0
) -> dict[str, Array]:
    """Quasi-random sample of the swept ``bounds`` via Sobol or Latin-Hypercube."""
    names = [n for n, v in spec.varied.items() if v.bounds is not None]
    if not names:
        raise ValueError("sampling needs `bounds` on the swept parameters")
    dim = len(names)
    engine: qmc.QMCEngine
    if method == "sobol":
        engine = qmc.Sobol(d=dim, scramble=True, seed=seed)
    elif method in {"lhs", "latin"}:
        engine = qmc.LatinHypercube(d=dim, seed=seed)
    else:
        raise ValueError(f"unknown sampling method '{method}' (use 'sobol' or 'lhs')")
    unit = engine.random(count)
    lows = np.array([spec.varied[n].bounds[0] for n in names])  # type: ignore[index]
    highs = np.array([spec.varied[n].bounds[1] for n in names])  # type: ignore[index]
    scaled = qmc.scale(unit, lows, highs)
    return {n: scaled[:, i] for i, n in enumerate(names)}


def _a(value: float) -> Array:
    """Wrap a scalar design constant as a 0-d float64 array (broadcasts; type-clean)."""
    return np.asarray(value, dtype=np.float64)


def evaluate(spec: VariationSpec, grid: dict[str, Array]) -> VariationResult:
    """Evaluate a batch (grid or sample) through the kernel with material dispatch."""
    warnings: list[str] = []
    alpha_n = _a(np.radians(spec.normal_pressure_angle_deg))

    def p(name: str) -> Array:
        return spec._value(name, grid)

    m_n = p("m_n")
    z1, z2 = p("z1"), p("z2")
    x1, x2 = p("x1"), p("x2")
    beta = (
        _a(np.radians(spec.fixed["beta_deg"]))
        if "beta_deg" in spec.fixed
        else (np.radians(p("beta_deg")) if "beta_deg" in grid else _a(0.0))
    )
    b = p("b")

    geometry = kernel.mesh_geometry(
        normal_module_mm=m_n,
        teeth_pinion=z1,
        teeth_wheel=z2,
        profile_shift_pinion=x1,
        profile_shift_wheel=x2,
        normal_pressure_angle=alpha_n,
        helix_angle=beta,
        face_width_mm=b,
        addendum_factor=_a(spec.addendum_factor),
    )
    base_helix = np.arcsin(np.sin(beta) * np.cos(alpha_n))
    teeth = (z1, z2)
    shifts = (x1, x2)
    roots: tuple[kernel.ToothRootFormFactors, kernel.ToothRootFormFactors] = tuple(  # type: ignore[assignment]
        kernel.tip_form_factors(
            normal_module_mm=m_n,
            teeth=teeth[i],
            normal_pressure_angle=alpha_n,
            helix_angle=beta,
            generation_profile_shift=shifts[i],  # x_E ≈ x for the sweep (allowance = 0)
            tool_addendum_factor=_a(spec.tool_addendum_factor),
            tool_tip_radius_factor=_a(spec.tool_tip_radius_factor),
            tip_diameter_mm=geometry.tip_diameter[i],
        )
        for i in range(2)
    )

    u = z2 / z1
    f_t = 2000.0 * spec.torque_nm / geometry.reference_diameter[0]
    k_h = _a(
        spec.application_factor
        * spec.dynamic_factor
        * spec.face_load_factor
        * spec.transverse_factor
    )
    z_e = kernel.elasticity_factor(
        _a(spec.materials[0].elastic_modulus_mpa),
        _a(spec.materials[0].poisson_ratio),
        _a(spec.materials[1].elastic_modulus_mpa),
        _a(spec.materials[1].poisson_ratio),
    )
    z_h = kernel.zone_factor(
        geometry.transverse_pressure_angle, geometry.working_pressure_angle, base_helix
    )
    z_eps = kernel.flank_contact_ratio_factor(
        geometry.transverse_contact_ratio, geometry.overlap_ratio
    )
    z_beta = 1.0 / np.sqrt(np.cos(beta))
    sigma_h = kernel.flank_stress(
        elasticity=z_e,
        zone=z_h,
        contact_ratio_factor=z_eps,
        helix_factor=z_beta,
        tangential_force_n=f_t,
        pinion_reference_diameter_mm=geometry.reference_diameter[0],
        face_width_mm=b,
        gear_ratio=u,
        load_factor_kh=k_h,
    )

    y_beta = 1.0 - geometry.overlap_ratio * np.radians(spec.normal_pressure_angle_deg) / 120.0
    sigma_f: list[Array] = []
    s_f: list[Array] = []
    s_h: list[Array] = []
    for i in range(2):
        stress = kernel.root_stress(
            tangential_force_n=f_t,
            face_width_mm=b,
            normal_module_mm=m_n,
            form_factor_tip=roots[i].form_factor_tip,
            stress_correction_tip=roots[i].stress_correction_tip,
            transverse_contact_ratio=geometry.transverse_contact_ratio,
            helix_factor=np.clip(y_beta, 0.75, 1.0),
            load_factor_kf=k_h,
        )
        sigma_f.append(stress)
        sigma_fp = _permissible_root(spec.materials[i], spec.root_minimum_safety, warnings, i)
        sigma_hp = _permissible_flank(spec.materials[i], spec.flank_minimum_safety, warnings, i)
        s_f.append(sigma_fp / stress if sigma_fp is not None else np.full_like(stress, np.nan))
        s_h.append(sigma_hp / sigma_h if sigma_hp is not None else np.full_like(sigma_h, np.nan))

    valid = kernel.validity_mask(geometry, roots)
    broadcast = {
        n: np.broadcast_to(p(n), geometry.total_contact_ratio.shape).copy()
        for n in ("m_n", "z1", "z2", "x1", "x2", "b")
    }
    return VariationResult(
        parameters=broadcast,
        transverse_contact_ratio=geometry.transverse_contact_ratio,
        overlap_ratio=geometry.overlap_ratio,
        total_contact_ratio=geometry.total_contact_ratio,
        flank_stress_mpa=sigma_h,
        root_stress_mpa=(sigma_f[0], sigma_f[1]),
        flank_safety=(s_h[0], s_h[1]),
        root_safety=(s_f[0], s_f[1]),
        valid=valid,
        warnings=tuple(dict.fromkeys(warnings)),  # de-duplicated, order-preserving
    )


def _permissible_root(
    material: Material, minimum_safety: float, warnings: list[str], index: int
) -> Array | None:
    limit = material.sigma_flim_mpa
    if limit is None:
        warnings.append(f"gear {index + 1}: no sigma_Flim - root safety skipped")
        return None
    # sigma_Flim is already the gear root limit (DIN 3990 / VDI 2736).
    return _a(limit / minimum_safety)


def _permissible_flank(
    material: Material, minimum_safety: float, warnings: list[str], index: int
) -> Array | None:
    limit = material.sigma_hlim_mpa
    if limit is None:
        warnings.append(f"gear {index + 1}: no sigma_Hlim - flank safety skipped")
        return None
    return _a(limit / minimum_safety)


def pareto_front(objectives: list[Array], *, maximize: list[bool]) -> BoolArray:
    """Boolean mask of the Pareto-non-dominated variants over several objectives.

    Each objective is an array over the variants; ``maximize[k]`` says whether larger
    is better for objective ``k``. O(n²) pairwise — fine for the pruned candidate set.
    """
    signed = np.stack(
        [obj if grow else -obj for obj, grow in zip(objectives, maximize, strict=True)], axis=1
    )
    finite = np.all(np.isfinite(signed), axis=1)
    count = signed.shape[0]
    nondominated = finite.copy()
    for i in range(count):
        if not nondominated[i]:
            continue
        dominates = (
            np.all(signed >= signed[i], axis=1) & np.any(signed > signed[i], axis=1) & finite
        )
        if np.any(dominates):
            nondominated[i] = False
    return nondominated
