"""Refinement of the sector mesh, the plane strain solver and the load case of the convergence
study (``gearcore.fe.refine``, ``plane_solver``, ``convergence``)."""

import math
from collections import Counter

import numpy as np
import pytest

from gearcore import contour as ct
from gearcore import data
from gearcore.errors import GeometryInfeasibleError, InputRangeError
from gearcore.fe import convergence as cv
from gearcore.fe import placement as pl
from gearcore.fe import plane_solver as ps
from gearcore.fe import refine as rf
from gearcore.fe import sector_mesh as sm
from gearcore.fe import solid as so
from gearcore.generation import compute_generation
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.results import GenerationResult

E_MPA, NU = 2282.0, 0.30


def _generation(case: str) -> GenerationResult:
    return compute_generation(pair_input_from_ste(load_ste(data.stplus_input_path(case))).pair)


_KST_E = _generation("kst_e")


@pytest.fixture(scope="module")
def kst_e() -> GenerationResult:
    return _KST_E


@pytest.fixture(scope="module")
def outline(kst_e: GenerationResult) -> np.ndarray:
    return ct.tooth_contour(kst_e, "wheel", points=2000).as_array()


@pytest.fixture(scope="module")
def base(kst_e: GenerationResult) -> sm.SectorMesh:
    return sm.sector_mesh(kst_e, "wheel", teeth=3, rim_rings=12)


def _edge_counts(quads: np.ndarray) -> Counter[tuple[int, int]]:
    counts: Counter[tuple[int, int]] = Counter()
    for quad in quads.tolist():
        for k in range(4):
            a, b = quad[k], quad[(k + 1) % 4]
            counts[(min(a, b), max(a, b))] += 1
    return counts


def _turned(points: np.ndarray, angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.column_stack(
        (c * points[:, 0] - s * points[:, 1], s * points[:, 0] + c * points[:, 1])
    )


# --- refinement ----------------------------------------------------------------------------------


def test_refinement_factors_are_validated() -> None:
    assert rf.Refinement().is_identity
    assert rf.Refinement(root=2, uniform=3).label() == "r2_u3"
    assert rf.Refinement().label() == "base"
    with pytest.raises(InputRangeError):
        rf.Refinement(height=0)
    with pytest.raises(InputRangeError):
        rf.Refinement(thickness=1.5)  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        rf.Refinement(root=True)


def test_identity_refinement_returns_the_same_mesh(
    base: sm.SectorMesh, outline: np.ndarray
) -> None:
    assert rf.refined(base, outline, rf.Refinement()) is base


def test_uniform_refinement_is_conformal_with_the_expected_counts(
    base: sm.SectorMesh, outline: np.ndarray
) -> None:
    fine = rf.refined(base, outline, rf.Refinement(uniform=2))
    edges = _edge_counts(base.quads)
    assert len(fine.quads) == 4 * len(base.quads)
    # every edge gets one node, every quad one interior node
    assert len(fine.points_mm) == len(base.points_mm) + len(edges) + len(base.quads)
    fine_edges = _edge_counts(fine.quads)
    assert max(fine_edges.values()) == 2
    boundary = sum(1 for count in fine_edges.values() if count == 1)
    # the boundary edge count doubles: surface path, bore and both cut planes
    assert boundary == 2 * sum(1 for count in edges.values() if count == 1)
    assert set(fine.quads.ravel().tolist()) == set(range(len(fine.points_mm)))
    assert (fine.height_factor, fine.root_factor, fine.thickness_factor, fine.uniform_factor) == (
        1,
        1,
        1,
        2,
    )
    assert len(fine.surface_path) == 2 * len(base.surface_path) - 1
    assert float(sm.scaled_jacobians(fine.points_mm, fine.quads).min()) >= sm.MIN_CORNER_SINE


def test_new_surface_nodes_lie_on_the_contour(base: sm.SectorMesh, outline: np.ndarray) -> None:
    fine = rf.refined(base, outline, rf.Refinement(uniform=2))
    kind = np.array(fine.node_kind)
    new = np.arange(len(base.points_mm), len(fine.points_mm))
    surface = new[kind[new] == "surface"]
    assert len(surface) == len(base.surface_path) - 1
    radius = np.hypot(fine.points_mm[surface, 0], fine.points_mm[surface, 1])
    # every new surface node lies on the outline of its tooth or on the root circle
    full = rf._with_root_arcs(outline, base)
    for node in surface:
        p = fine.points_mm[node]
        best = math.inf
        for tooth in range(1, base.teeth + 1):
            angle = (tooth - 0.5 * (base.teeth + 1)) * base.pitch_angle_rad
            foot = rf._nearest_on_polyline(p[None, :], _turned(full, angle))[0]
            best = min(best, float(np.hypot(*(foot - p))))
        best = min(best, abs(float(np.hypot(*p)) - base.root_radius_mm))
        assert best < 1.0e-9, f"node {node} at radius {np.hypot(*p):.6f} is {best:.2e} mm off"
    assert radius.max() <= base.tip_radius_mm + 1.0e-9
    bore = new[kind[new] == "bore"]
    assert len(bore) > 0
    assert np.allclose(np.hypot(*fine.points_mm[bore].T), base.bore_radius_mm, atol=1.0e-9)


@pytest.mark.parametrize(
    ("refinement", "expected"),
    [
        (rf.Refinement(height=2), (40, 80, 10)),
        (rf.Refinement(root=3), (20, 240, 10)),
        (rf.Refinement(thickness=2), (20, 80, 20)),
        (rf.Refinement(uniform=2), (40, 160, 20)),
        (rf.Refinement(root=2, uniform=2), (40, 320, 20)),
    ],
)
def test_factors_multiply_the_effective_counts(
    base: sm.SectorMesh,
    outline: np.ndarray,
    refinement: rf.Refinement,
    expected: tuple[int, int, int],
) -> None:
    before = rf.effective_counts(base)
    assert (before.over_tooth_height, before.at_tooth_root, before.over_tooth_thickness) == (
        20,
        80,
        10,
    )
    fine = rf.refined(base, outline, refinement)
    after = rf.effective_counts(fine)
    assert (after.over_tooth_height, after.at_tooth_root, after.over_tooth_thickness) == expected
    assert after.rim_rings == 12 * refinement.uniform


def test_directional_refinement_leaves_the_other_bands_alone(
    base: sm.SectorMesh, outline: np.ndarray
) -> None:
    fine = rf.refined(base, outline, rf.Refinement(height=2))
    # only the head grid rows are split: the quads of the root layers and the rim are unchanged
    assert int((fine.quad_head == 1).sum()) == 2 * int((base.quad_head == 1).sum())
    assert int((fine.quad_zone == 0).sum()) == int((base.quad_zone == 0).sum())
    assert int((fine.quad_tooth == 0).sum()) == int((base.quad_tooth == 0).sum())


def test_refined_teeth_stay_congruent(base: sm.SectorMesh, outline: np.ndarray) -> None:
    fine = rf.refined(base, outline, rf.Refinement(uniform=2, root=2))
    centres = []
    for tooth in (1, 2):
        nodes = np.unique(fine.quads[fine.quad_tooth == tooth])
        angle = -(tooth - 0.5 * (fine.teeth + 1)) * fine.pitch_angle_rad
        centres.append(np.sort(_turned(fine.points_mm[nodes], angle), axis=0))
    assert centres[0].shape == centres[1].shape
    assert np.allclose(centres[0], centres[1], atol=1.0e-9)


def test_refined_mesh_extrudes_with_its_sets(base: sm.SectorMesh, outline: np.ndarray) -> None:
    fine = rf.refined(base, outline, rf.Refinement(thickness=2))
    solid = so.extrude(fine, face_width_mm=15.0, layers=2)
    sets = so.gear_sets(solid, "WHEEL")
    assert len(sets.surfaces["WHEEL_T2_RIGHT_SURF_FLANK"]) == 2 * 18
    assert float(so.hex_corner_volumes(solid).min()) > 0.0


def test_middle_tooth() -> None:
    assert [rf.middle_tooth(n) for n in (1, 2, 3, 4, 5)] == [1, 1, 2, 2, 3]
    with pytest.raises(InputRangeError):
        rf.middle_tooth(0)


def test_refinement_rejects_wrong_inputs(base: sm.SectorMesh, outline: np.ndarray) -> None:
    with pytest.raises(InputRangeError):
        rf.refined(base, outline, "u2")  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        rf.refined(base, outline[:, :1], rf.Refinement(uniform=2))
    with pytest.raises(InputRangeError):
        rf.refined(base.points_mm, outline, rf.Refinement(uniform=2))  # type: ignore[arg-type]


# --- plane solver --------------------------------------------------------------------------------


def _patch() -> tuple[np.ndarray, np.ndarray]:
    """An irregular quad mesh of the unit square (the patch test)."""
    points = np.array(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [1.0, 1.0],
            [0.0, 1.0],
            [0.3, 0.2],
            [0.7, 0.35],
            [0.65, 0.8],
            [0.25, 0.7],
        ]
    )
    quads = np.array([[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7], [4, 5, 6, 7]])
    return points, quads


@pytest.mark.parametrize("formulation", ps.FORMULATIONS)
def test_patch_test_reproduces_a_linear_displacement_field(formulation: str) -> None:
    points, quads = _patch()
    d = ps.plane_strain_matrix(E_MPA, NU)
    exact = np.column_stack((1.0e-3 * points[:, 0] + 2.0e-4 * points[:, 1], 5.0e-4 * points[:, 1]))
    k = ps.stiffness(points, quads, d, formulation)
    reaction = (k @ exact.ravel()).reshape(-1, 2)
    fixed = np.zeros(len(points), dtype=bool)
    fixed[:4] = True  # the corners carry the exact displacements through the loads
    # solve with the interior free and the boundary nodes loaded by the reactions
    loads = reaction.copy()
    free = ~fixed
    k_ff = k[np.repeat(free, 2)][:, np.repeat(free, 2)].toarray()
    k_fc = k[np.repeat(free, 2)][:, np.repeat(fixed, 2)].toarray()
    u_free = np.linalg.solve(k_ff, loads[free].ravel() - k_fc @ exact[fixed].ravel())
    assert np.allclose(u_free, exact[free].ravel(), atol=1.0e-12)
    gauss = ps.gauss_stresses(points, quads, exact, d, formulation)
    strain = np.array([1.0e-3, 5.0e-4, 2.0e-4])
    assert np.allclose(gauss, d @ strain, rtol=1.0e-10)
    nodal = ps.nodal_stresses(points, quads, gauss)
    assert np.allclose(nodal, d @ strain, rtol=1.0e-10)


def _cantilever(nx: int, ny: int, length: float, height: float) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = np.meshgrid(np.linspace(0, length, nx + 1), np.linspace(0, height, ny + 1))
    points = np.column_stack((xs.ravel(), ys.ravel()))
    quads = np.array(
        [
            [
                j * (nx + 1) + i,
                j * (nx + 1) + i + 1,
                (j + 1) * (nx + 1) + i + 1,
                (j + 1) * (nx + 1) + i,
            ]
            for j in range(ny)
            for i in range(nx)
        ]
    )
    return points, quads


def test_incompatible_modes_bend_a_coarse_cantilever_better() -> None:
    """One element over the height: the selectively reduced element locks in shear, the
    incompatible modes represent the linear bending strain and come close to beam theory."""
    length, height = 20.0, 2.0
    points, quads = _cantilever(10, 1, length, height)
    fixed = points[:, 0] == 0.0
    loads = np.zeros_like(points)
    tip = np.flatnonzero(points[:, 0] == length)
    loads[tip, 1] = -10.0 / len(tip)
    beam = 10.0 * length**3 / (3.0 * (E_MPA / (1.0 - NU**2)) * height**3 / 12.0)
    d = ps.plane_strain_matrix(E_MPA, NU)
    deflections = {}
    for formulation in ps.FORMULATIONS:
        solution = ps.solve(
            points, quads, d_matrix=d, fixed=fixed, loads_n_per_mm=loads, formulation=formulation
        )
        assert solution.formulation == formulation
        deflections[formulation] = -solution.displacements_mm[tip, 1].mean()
    # one row of selectively reduced elements misses the bending state (the modified normal
    # strains carry only the deviatoric part: 43 % too soft here), the incompatible modes
    # represent it
    assert abs(deflections["selectively_reduced"] - beam) > 0.2 * beam
    assert deflections["incompatible_modes"] == pytest.approx(beam, rel=0.1)
    with pytest.raises(InputRangeError):
        ps.solve(points, quads, d_matrix=d, fixed=fixed, loads_n_per_mm=loads, formulation="CPE4")


def test_cantilever_matches_beam_theory_within_a_few_percent() -> None:
    length, height, nx, ny = 20.0, 2.0, 40, 8
    xs, ys = np.meshgrid(np.linspace(0, length, nx + 1), np.linspace(0, height, ny + 1))
    points = np.column_stack((xs.ravel(), ys.ravel()))
    quads = np.array(
        [
            [
                j * (nx + 1) + i,
                j * (nx + 1) + i + 1,
                (j + 1) * (nx + 1) + i + 1,
                (j + 1) * (nx + 1) + i,
            ]
            for j in range(ny)
            for i in range(nx)
        ]
    )
    fixed = points[:, 0] == 0.0
    loads = np.zeros_like(points)
    tip = np.flatnonzero(points[:, 0] == length)
    force = 10.0
    loads[tip, 1] = -force / len(tip)
    solution = ps.solve(
        points, quads, d_matrix=ps.plane_strain_matrix(E_MPA, NU), fixed=fixed, loads_n_per_mm=loads
    )
    e_plane = E_MPA / (1.0 - NU**2)
    inertia = height**3 / 12.0
    beam = force * length**3 / (3.0 * e_plane * inertia)
    deflection = -solution.displacements_mm[tip, 1].mean()
    assert deflection == pytest.approx(beam, rel=0.05)
    assert solution.strain_energy_nmm == pytest.approx(0.5 * force * deflection, rel=0.05)
    # bending stress on the top edge a quarter length from the wall (the clamped wall itself
    # concentrates the stress), from the averaged nodal values. With the volumetric strain
    # taken at the centroid the surface value of a first-order element lies below the exact
    # one by the order of one element size (here 9 % with 8 elements over the height); the
    # convergence study measures exactly this, so the check only brackets it.
    sigma_xx = solution.nodal_stress_mpa[:, 0]
    x = 0.25 * length
    top = np.flatnonzero((points[:, 0] == x) & (points[:, 1] == height))
    exact = force * (length - x) * (height / 2.0) / inertia
    assert 0.85 * exact < sigma_xx[top].item() < exact


def test_principal_and_von_mises() -> None:
    sigma1, sigma2 = ps.principal_stresses(np.array([[3.0, 1.0, 0.0], [0.0, 0.0, 2.0]]))
    assert np.allclose(sigma1, [3.0, 2.0]) and np.allclose(sigma2, [1.0, -2.0])
    uniaxial = ps.von_mises_plane_strain(np.array([[100.0, 0.0, 0.0]]), 0.0)
    assert uniaxial.item() == pytest.approx(100.0)
    shear = ps.von_mises_plane_strain(np.array([[0.0, 0.0, 10.0]]), 0.3)
    assert shear.item() == pytest.approx(math.sqrt(3.0) * 10.0)


def test_solver_rejects_wrong_inputs() -> None:
    points, quads = _patch()
    d = ps.plane_strain_matrix(E_MPA, NU)
    with pytest.raises(InputRangeError):
        ps.plane_strain_matrix(E_MPA, 0.5)
    with pytest.raises(InputRangeError):
        ps.solve(
            points,
            quads,
            d_matrix=d,
            fixed=np.zeros(8, dtype=bool),
            loads_n_per_mm=np.zeros((8, 2)),
        )
    with pytest.raises(InputRangeError):
        ps.solve(
            points, quads, d_matrix=d, fixed=np.ones(7, dtype=bool), loads_n_per_mm=np.zeros((8, 2))
        )
    with pytest.raises(GeometryInfeasibleError):
        ps.stiffness(points, quads[:, ::-1], d)  # clockwise quads


# --- load case and evaluation ------------------------------------------------------------------


@pytest.fixture(scope="module")
def load(kst_e: GenerationResult, base: sm.SectorMesh) -> cv.LoadCase:
    return cv.wheel_load_case(
        kst_e,
        base,
        torque_wheel_nmm=16000.0,
        youngs_modulus_mpa=E_MPA,
        poisson_ratio=NU,
        face_width_mm=15.0,
    )


def test_load_case_at_point_b(
    kst_e: GenerationResult, base: sm.SectorMesh, load: cv.LoadCase
) -> None:
    geometry = kst_e.pair_geometry
    r_b2 = 0.5 * 52 * 1.0 * math.cos(math.radians(20.0))
    assert load.force_per_mm == pytest.approx(16000.0 / r_b2 / 15.0)
    assert load.loaded_tooth == 2 and load.loaded_side == -1  # the right flanks work
    # the contact point lies on the flank of the middle tooth at the radius of point B:
    # rho_B2 = rho_E2 + p_bt, so r_B = sqrt(r_b2^2 + rho_B2^2)
    rho_e1 = pl.path_of_contact_limits(kst_e)[1]
    t1_t2 = kst_e.pair_geometry.centre_distance_mm * math.sin(
        math.radians(geometry.transverse_working_pressure_angle_deg)
    )
    rho_b2 = t1_t2 - (rho_e1 - geometry.transverse_base_pitch_mm)
    assert load.contact_radius_mm == pytest.approx(math.hypot(r_b2, rho_b2))
    assert base.root_form_radius_mm < load.contact_radius_mm < base.tip_form_radius_mm
    assert math.hypot(*load.contact_point_mm) == pytest.approx(load.contact_radius_mm)
    assert not load.cut_at_tip_form_circle
    # the loads add up to the force along the line of action, pointing into the gear
    resultant = np.asarray(load.resultant_n_per_mm)
    assert np.hypot(*resultant) == pytest.approx(load.force_per_mm)
    assert float(np.dot(resultant, load.contact_point_mm)) < 0.0
    assert np.allclose(load.loads_n_per_mm.sum(axis=0), resultant)
    # only flank nodes of the loaded half carry load, within the Hertz patch
    radius = np.hypot(*base.points_mm[load.loaded_nodes].T)
    assert np.all(radius > base.root_form_radius_mm) and np.all(radius < base.tip_radius_mm)
    assert load.half_width_mm == pytest.approx(0.3218, abs=5.0e-4)
    assert load.max_pressure_mpa == pytest.approx(
        2.0 * load.force_per_mm / (math.pi * load.half_width_mm)
    )


def test_a_wider_patch_keeps_the_force(
    kst_e: GenerationResult, base: sm.SectorMesh, load: cv.LoadCase
) -> None:
    wide = cv.wheel_load_case(
        kst_e,
        base,
        torque_wheel_nmm=16000.0,
        youngs_modulus_mpa=E_MPA,
        poisson_ratio=NU,
        face_width_mm=15.0,
        half_width_scale=3.0,
    )
    assert wide.half_width_mm == pytest.approx(3.0 * load.half_width_mm)
    assert wide.cut_at_tip_form_circle
    assert np.hypot(*wide.resultant_n_per_mm) == pytest.approx(load.force_per_mm)
    assert len(wide.loaded_nodes) > len(load.loaded_nodes)


def test_load_case_rejects_wrong_inputs(kst_e: GenerationResult, base: sm.SectorMesh) -> None:
    with pytest.raises(InputRangeError):
        cv.wheel_load_case(
            kst_e,
            base,
            torque_wheel_nmm=0.0,
            youngs_modulus_mpa=E_MPA,
            poisson_ratio=NU,
            face_width_mm=15.0,
        )
    with pytest.raises(InputRangeError):
        cv.wheel_load_case(
            kst_e,
            base,
            torque_wheel_nmm=1.0,
            youngs_modulus_mpa=E_MPA,
            poisson_ratio=NU,
            face_width_mm=15.0,
            rho_1_mm=0.0,
        )
    pinion = sm.sector_mesh(kst_e, "pinion", teeth=1, rim_rings=12)
    with pytest.raises(InputRangeError):
        cv.wheel_load_case(
            kst_e,
            pinion,
            torque_wheel_nmm=1.0,
            youngs_modulus_mpa=E_MPA,
            poisson_ratio=NU,
            face_width_mm=15.0,
        )


def test_evaluation_of_the_base_mesh(base: sm.SectorMesh, load: cv.LoadCase) -> None:
    fixed = cv.fixed_nodes(base)
    kind = np.array(base.node_kind)
    assert int(fixed.sum()) == int(((kind == "bore") | (kind == "cut")).sum())
    solution = ps.solve(
        base.points_mm,
        base.quads,
        d_matrix=ps.plane_strain_matrix(E_MPA, NU),
        fixed=fixed,
        loads_n_per_mm=load.loads_n_per_mm,
    )
    result = cv.evaluate(base, solution, load, NU)
    assert result.nodes == len(base.points_mm) and result.elements == len(base.quads)
    # the tensile maximum lies in the fillet of the loaded side, below the root form circle
    assert base.root_radius_mm < result.root_radius_mm < base.root_form_radius_mm
    assert result.root_angle_deg < 0.0  # the right (clockwise) side
    assert result.root_sigma1_max_mpa > 0.0
    assert result.root_sigma1_max_mpa == pytest.approx(result.fillet_sigma1_mpa.max())
    assert result.fillet_arc_mm[0] == 0.0 and np.all(np.diff(result.fillet_arc_mm) > 0.0)
    # the fillet chain starts at the root form point
    first = result.fillet_nodes[0]
    assert math.hypot(*base.points_mm[first]) == pytest.approx(base.root_form_radius_mm, abs=1.0e-6)
    # tip nodes lie on the tip circle of the middle tooth; the corner on the loaded side
    for node in (result.tip_centre_node, result.tip_corner_node):
        assert math.hypot(*base.points_mm[node]) == pytest.approx(base.tip_radius_mm, abs=1.0e-6)
    assert base.points_mm[result.tip_centre_node, 0] == pytest.approx(0.0, abs=1.0e-9)
    assert base.points_mm[result.tip_corner_node, 0] > 0.0
    assert 0.1 < result.tip_centre_magnitude_mm < 0.5
    assert result.strain_energy_nmm == pytest.approx(
        0.5 * float(np.sum(solution.displacements_mm * load.loads_n_per_mm))
    )
    # the displacement of the tip follows the load: towards the axis and the loaded side
    assert result.tip_centre_displacement_mm[1] < 0.0
    assert result.tip_centre_displacement_mm[0] < 0.0


def test_richardson_fit_recovers_a_known_order_from_noisy_levels() -> None:
    h = (1.0, 0.75, 0.5, 0.375, 0.3, 0.25)
    values = tuple(150.0 - 9.0 * x**1.5 + 1.0e-4 * (-1) ** k for k, x in enumerate(h))
    result = cv.richardson_fit(h, values)
    assert result.order == pytest.approx(1.5, abs=0.02)
    assert result.limit == pytest.approx(150.0, abs=0.01)
    assert result.relative_error is not None and result.relative_error[0] == pytest.approx(
        -0.06, abs=1e-4
    )
    with pytest.raises(InputRangeError):
        cv.richardson_fit((1.0, 0.5, 0.25), (1.0, 1.1, 1.05))


def test_richardson_recovers_a_known_order() -> None:
    h = (1.0, 0.5, 1.0 / 3.0, 0.25)
    values = tuple(10.0 - 0.8 * x**2 for x in h)
    result = cv.richardson(h, values)
    assert result.order == pytest.approx(2.0, abs=1.0e-6)
    assert result.limit == pytest.approx(10.0, abs=1.0e-8)
    assert result.relative_error is not None
    assert result.relative_error[0] == pytest.approx(-0.08, abs=1.0e-8)
    assert len(result.successive_change) == 3
    flat = cv.richardson((1.0, 0.5, 0.25), (1.0, 1.1, 1.05))
    assert flat.order is None and flat.limit is None
    with pytest.raises(InputRangeError):
        cv.richardson((1.0, 1.0), (1.0, 2.0))
    with pytest.raises(InputRangeError):
        cv.richardson((1.0,), (1.0,))
