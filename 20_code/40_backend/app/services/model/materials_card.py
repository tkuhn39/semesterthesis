"""
@module: app.services.model.materials_card
@context: Domain layer — FE rolling model, the Abaqus ``*MATERIAL`` cards.
@role: Turn a material definition into the keyword card the reference deck uses — a linear
       ``*ELASTIC`` card (the steel gear) or the isotropic-nonlinear ``*Hyperelastic, marlow``
       driven by a measured ``*Uniaxial Test Data`` curve (the plastic gear, WoBe-892 "simple"
       material mode). Material PROPERTIES come from the single catalog in
       ``app.services.materials`` (user decision 2026-07-04: no divergent copies between the
       analytical methods and the FE deck) — ``card_from_catalog`` converts a catalog entry
       into the deck card. The ``cof``-mapped anisotropic mode plugs in here later.
"""

from dataclasses import dataclass

from app.services.materials import Material as CatalogMaterial
from app.services.materials import catalog_material

# kst-E plastic uniaxial test data in the deck-card order (stress [MPa], strain [-]) —
# derived from the SINGLE copy in app.services.materials (catalog "Stanyl_TW200F6_cond_80").
_kst_e_curve = catalog_material("Stanyl_TW200F6_cond_80").curve("stress_strain")
assert _kst_e_curve is not None  # the catalog entry always carries the measured curve
KST_E_PA_MARLOW_CURVE: tuple[tuple[float, float], ...] = tuple(
    (stress, strain) for strain, stress in _kst_e_curve.points
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


def card_from_catalog(mat: CatalogMaterial) -> Material:
    """Convert a catalog material (app.services.materials) into its deck card.

    Steel → linear ``*ELASTIC``; plastic → ``*HYPERELASTIC, MARLOW`` from the material's
    measured stress–strain curve (falls back to the kst-E curve when none is attached).
    Density converts kg/m³ → t/mm³ (Abaqus consistent units).
    """
    density = mat.density_kg_m3 * 1e-12 if mat.density_kg_m3 is not None else None
    if not mat.is_plastic:
        return LinearElastic(
            name=mat.name,
            youngs_modulus_mpa=mat.elastic_modulus_mpa,
            poisson_ratio=mat.poisson_ratio,
            density_t_per_mm3=density,
        )
    curve = mat.curve("stress_strain")
    points = (
        tuple((stress, strain) for strain, stress in curve.points)
        if curve is not None
        else KST_E_PA_MARLOW_CURVE
    )
    return MarlowUniaxial(
        name=mat.name,
        curve=points,
        poisson_ratio=mat.fe_poisson_ratio or mat.poisson_ratio,
        density_t_per_mm3=density,
    )


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
