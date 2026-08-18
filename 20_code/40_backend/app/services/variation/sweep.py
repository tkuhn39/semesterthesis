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
    ``x2``, ``beta_deg``, ``b``, ``alpha_n_deg``, and the per-gear rows ``b2``,
    ``h_ap1``/``h_ap2``, ``h_fp1``/``h_fp2``, ``rho_fp1``/``rho_fp2``); everything not
    varied takes its ``fixed`` value (``alpha_n_deg`` falls back to
    ``normal_pressure_angle_deg``; the per-gear rows fall back to the scalar spec
    fields below — direct ``VariationSpec`` users keep the old behaviour bit-exactly).
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

    def p(name: str) -> Array:
        return spec._value(name, grid)

    def p_opt(name: str, fallback: Array) -> Array:
        # optional per-gear rows: present in the batch/fixed set → use them, else the
        # scalar spec field (keeps direct VariationSpec construction bit-identical)
        return p(name) if name in grid or name in spec.fixed else fallback

    # α_n is sweepable (FVA Stufenvariation row "Normaleingriffswinkel Rad 1"): the whole
    # kernel is vectorized in alpha_n already — an "alpha_n_deg" grid/fixed entry wins over
    # the spec scalar.
    if "alpha_n_deg" in grid or "alpha_n_deg" in spec.fixed:
        alpha_n = np.radians(p("alpha_n_deg"))
    else:
        alpha_n = _a(np.radians(spec.normal_pressure_angle_deg))

    m_n = p("m_n")
    z1, z2 = p("z1"), p("z2")
    x1, x2 = p("x1"), p("x2")
    beta = (
        _a(np.radians(spec.fixed["beta_deg"]))
        if "beta_deg" in spec.fixed
        else (np.radians(p("beta_deg")) if "beta_deg" in grid else _a(0.0))
    )
    b = p("b")
    # per-gear rows (FVA dialog): face width, addendum, tool dedendum + tip radius —
    # the shared-mesh quantities (ε, flank) use the COMMON width min(b, b2), the root
    # stress of each gear uses its own width
    b2 = p_opt("b2", b)
    b_eff = np.minimum(b, b2)
    h_ap = (p_opt("h_ap1", _a(spec.addendum_factor)), p_opt("h_ap2", _a(spec.addendum_factor)))
    h_fp = (
        p_opt("h_fp1", _a(spec.tool_addendum_factor)),
        p_opt("h_fp2", _a(spec.tool_addendum_factor)),
    )
    rho_fp = (
        p_opt("rho_fp1", _a(spec.tool_tip_radius_factor)),
        p_opt("rho_fp2", _a(spec.tool_tip_radius_factor)),
    )

    geometry = kernel.mesh_geometry(
        normal_module_mm=m_n,
        teeth_pinion=z1,
        teeth_wheel=z2,
        profile_shift_pinion=x1,
        profile_shift_wheel=x2,
        normal_pressure_angle=alpha_n,
        helix_angle=beta,
        face_width_mm=b_eff,
        addendum_factor_pinion=h_ap[0],
        addendum_factor_wheel=h_ap[1],
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
            tool_addendum_factor=h_fp[i],
            tool_tip_radius_factor=rho_fp[i],
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
    # Z_β = √cos β (DIN 3990-2:1987 Eq. 6.01 — the VDI 2736 chain's convention, "Z_β ≤ 1";
    # fixed 2026-08-18, audit NRM-04: was the ISO 6336-2:2019 form 1/√cos β)
    z_beta = np.sqrt(np.cos(beta))
    sigma_h = kernel.flank_stress(
        elasticity=z_e,
        zone=z_h,
        contact_ratio_factor=z_eps,
        helix_factor=z_beta,
        tangential_force_n=f_t,
        pinion_reference_diameter_mm=geometry.reference_diameter[0],
        face_width_mm=b_eff,
        gear_ratio=u,
        load_factor_kh=k_h,
    )

    # Y_β = 1 − min(ε_β,1)·min(β,30°)/120° (VDI 2736-2 Eq. 12 with BOTH norm caps;
    # fixed 2026-08-18, audit NRM-04: the old line fed the *pressure angle in radians*
    # instead of the helix angle in degrees)
    y_beta = (
        1.0
        - np.minimum(geometry.overlap_ratio, 1.0)
        * np.minimum(np.abs(np.degrees(beta)), 30.0)
        / 120.0
    )
    sigma_f: list[Array] = []
    s_f: list[Array] = []
    s_h: list[Array] = []
    widths = (b, b2)
    for i in range(2):
        stress = kernel.root_stress(
            tangential_force_n=f_t,
            face_width_mm=widths[i],
            normal_module_mm=m_n,
            form_factor_tip=roots[i].form_factor_tip,
            stress_correction_tip=roots[i].stress_correction_tip,
            transverse_contact_ratio=geometry.transverse_contact_ratio,
            helix_factor=y_beta,
            load_factor_kf=k_h,
        )
        sigma_f.append(stress)
        # TRUE safeties S = σ_lim/σ (fixed 2026-08-18, audit NRM-06: the old values were
        # (σ_lim/S_min)/σ and were then compared against S_min AGAIN downstream)
        root_limit = _root_limit(spec.materials[i], warnings, i)
        flank_limit = _flank_limit(spec.materials[i], warnings, i)
        s_f.append(root_limit / stress if root_limit is not None else np.full_like(stress, np.nan))
        s_h.append(
            flank_limit / sigma_h if flank_limit is not None else np.full_like(sigma_h, np.nan)
        )

    valid = kernel.validity_mask(geometry, roots)
    # the batch shape comes from the swept arrays — geometry may stay scalar when the
    # varied parameter only enters the tooth-root side (h_fP*, ρ_fP*, b2), so every
    # output is broadcast up to the batch before returning
    batch_shape = next(iter(grid.values())).shape if grid else geometry.total_contact_ratio.shape

    def bx(a: Array) -> Array:
        return a if a.shape == batch_shape else np.broadcast_to(a, batch_shape).copy()

    extra = tuple(
        n
        for n in ("b2", "h_ap1", "h_ap2", "h_fp1", "h_fp2", "rho_fp1", "rho_fp2")
        if n in grid or n in spec.fixed
    )
    broadcast = {
        n: np.broadcast_to(p(n), batch_shape).copy()
        for n in ("m_n", "z1", "z2", "x1", "x2", "b", *extra)
    }
    return VariationResult(
        parameters=broadcast,
        transverse_contact_ratio=bx(geometry.transverse_contact_ratio),
        overlap_ratio=bx(geometry.overlap_ratio),
        total_contact_ratio=bx(geometry.total_contact_ratio),
        flank_stress_mpa=bx(sigma_h),
        root_stress_mpa=(bx(sigma_f[0]), bx(sigma_f[1])),
        flank_safety=(bx(s_h[0]), bx(s_h[1])),
        root_safety=(bx(s_f[0]), bx(s_f[1])),
        valid=np.broadcast_to(valid, batch_shape).copy(),
        warnings=tuple(dict.fromkeys(warnings)),  # de-duplicated, order-preserving
    )


def _root_limit(material: Material, warnings: list[str], index: int) -> Array | None:
    limit = material.sigma_flim_mpa
    if limit is None:
        warnings.append(f"gear {index + 1}: no sigma_Flim - root safety skipped")
        return None
    # Root strength limit = 2·σ_Flim: the σ_Flim inputs are NOMINAL-stress fatigue values,
    # so the stress correction factor doubles them in both norms — Y_St ≈ 2 for plastics
    # (VDI 2736-2 Eq. 13, σ_FG = Y_St·σ_FlimN) and Y_ST = 2 for steel (ISO 6336-3,
    # σ_FE = 2·σ_Flim). Added 2026-08-18 (adversarial verify pass on the NRM-06 fix).
    return _a(2.0 * limit)


def _flank_limit(material: Material, warnings: list[str], index: int) -> Array | None:
    limit = material.sigma_hlim_mpa
    if limit is None:
        warnings.append(f"gear {index + 1}: no sigma_Hlim - flank safety skipped")
        return None
    return _a(limit)


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
