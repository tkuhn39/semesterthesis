"""
@module: app.services.model.materials_card
@context: Domain layer — FE rolling model, the Abaqus ``*MATERIAL`` cards.
@role: Turn a material definition into the keyword card the reference deck uses — a linear
       ``*ELASTIC`` card (the steel gear) or the isotropic-nonlinear ``*Hyperelastic, marlow``
       driven by a measured ``*Uniaxial Test Data`` curve (the plastic gear, WoBe-892 "simple"
       material mode). The measured curve is a parameter; the project gear's kst-E PA curve is
       embedded as a regression reference. The ``cof``-mapped anisotropic mode plugs in here later.
"""

from dataclasses import dataclass

# kst-E plastic (PA) uniaxial test data from the reference deck: (nominal stress [MPa], strain [-]).
# Embedded for validation — the production path feeds curves from app.services.materials.
KST_E_PA_MARLOW_CURVE: tuple[tuple[float, float], ...] = (
    (0.00, 0.000), (4.27, 0.001), (22.81, 0.006), (28.00, 0.008), (32.91, 0.009),
    (37.41, 0.011), (41.69, 0.012), (45.64, 0.014), (49.35, 0.016), (52.84, 0.017),
    (56.10, 0.019), (59.16, 0.020), (62.01, 0.022), (64.64, 0.024), (67.09, 0.025),
    (69.34, 0.027), (71.39, 0.028), (73.24, 0.030), (74.92, 0.032), (76.34, 0.033),
    (77.78, 0.035), (79.00, 0.036), (80.10, 0.038), (81.07, 0.040), (81.96, 0.041),
    (82.75, 0.043), (83.48, 0.044), (84.15, 0.046), (84.75, 0.048), (85.30, 0.049),
    (85.80, 0.051), (86.26, 0.052), (86.68, 0.054), (87.04, 0.056), (87.38, 0.057),
    (87.69, 0.059), (87.97, 0.060), (88.23, 0.062), (88.44, 0.064), (88.64, 0.065),
    (88.81, 0.067), (88.94, 0.068), (88.98, 0.070),
)


@dataclass(frozen=True)
class LinearElastic:
    """An isotropic linear-elastic material — the steel gear (deformable, not rigid)."""

    name: str
    youngs_modulus_mpa: float
    poisson_ratio: float
    density_t_per_mm3: float | None = None


@dataclass(frozen=True)
class MarlowUniaxial:
    """Isotropic-nonlinear hyperelastic (Marlow) from a measured uniaxial curve — the plastic."""

    name: str
    curve: tuple[tuple[float, float], ...] = KST_E_PA_MARLOW_CURVE  # (stress [MPa], strain [-])
    poisson_ratio: float = 0.30
    smooth: int = 3
    density_t_per_mm3: float | None = None


Material = LinearElastic | MarlowUniaxial


def _density_card(density_t_per_mm3: float | None) -> str:
    return f"\n*DENSITY\n{density_t_per_mm3:.6e}," if density_t_per_mm3 is not None else ""


def material_card(material: Material) -> str:
    """Build the ``*MATERIAL`` keyword card for either material mode."""
    if isinstance(material, LinearElastic):
        body = f"*ELASTIC\n{material.youngs_modulus_mpa:.6g}, {material.poisson_ratio:.6g}"
    else:
        rows = "\n".join(f"{s:.6g}, {e:.6g}" for s, e in material.curve)
        body = (
            f"*HYPERELASTIC, MARLOW, POISSON={material.poisson_ratio:.6g}\n"
            f"*UNIAXIAL TEST DATA, SMOOTH={material.smooth}\n{rows}"
        )
    return f"*MATERIAL, NAME={material.name}\n{body}{_density_card(material.density_t_per_mm3)}"
