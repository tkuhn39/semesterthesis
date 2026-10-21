"""The gears as manufactured (``gearcore.manufactured``, ``data/fe/as_manufactured.yaml``):
the measured numbers reach the generation exactly, the untouched gear stays, and the numbers of
the file are the medians of the measured parts (checked against the raw files when present)."""

from pathlib import Path
from statistics import median
from typing import Any

import pytest

from gearcore import contour as ct
from gearcore import data
from gearcore import manufactured as mf
from gearcore.errors import GeometryInfeasibleError, InputRangeError, NotSupportedError
from gearcore.fe import placement as pl
from gearcore.generation import compute_generation
from gearcore.inspection import compute_inspection
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.inputs import PairInput

REPO_ROOT = Path(__file__).resolve().parents[3]
MEASUREMENTS = REPO_ROOT / "70_input" / "71_Messungen"


@pytest.fixture(scope="module")
def kst_e() -> PairInput:
    return pair_input_from_ste(load_ste(data.stplus_input_path("kst_e"))).pair


def test_the_file_is_well_formed() -> None:
    document = data.load_as_manufactured()
    assert mf.variant_labels("kst_e") == ["stahl", "kunststoff", "beide"]
    variant = mf.load_variant("kst_e", "beide")
    assert variant.pinion is not None and variant.wheel is not None
    assert variant.set_names == {"pinion": "pinion_measured", "wheel": "wheel_measured"}
    assert variant.pinion.tip_relief_um == 23.6 and variant.wheel.tip_edge_radius_mm == 0.21
    assert variant.wheel.profile_slope_um == 10.25
    assert document["cases"]["kst_e"]["gears"]["pinion_measured"]["sources"]
    steel = mf.load_variant("kst_e", "stahl")
    assert steel.wheel is None and steel.pinion == variant.pinion
    with pytest.raises(InputRangeError):
        mf.load_variant("kst_e", "alles")
    with pytest.raises(InputRangeError):
        mf.variant_labels("kst_z")


def test_the_measured_numbers_reach_the_generation(kst_e: PairInput) -> None:
    base = compute_generation(kst_e)
    both = mf.apply(kst_e, mf.load_variant("kst_e", "beide"))
    generation = both.generation
    inspection = compute_inspection(generation)
    pinion, wheel = both.changes["pinion"], both.changes["wheel"]
    # spans, tip and root circles are the measured medians
    assert inspection.gears.pinion.span_measurement_mm is not None
    assert inspection.gears.pinion.span_measurement_mm.upper == pytest.approx(16.797, abs=1e-9)
    assert inspection.gears.wheel.span_measurement_mm is not None
    assert inspection.gears.wheel.span_measurement_mm.upper == pytest.approx(16.972, abs=1e-9)
    assert generation.gears.pinion.tip_diameter_mm == 52.879
    assert generation.gears.wheel.tip_diameter_mm == 54.0515
    assert generation.gears.pinion.generated_root_diameter_mm == pytest.approx(48.321, abs=1e-9)
    assert generation.gears.wheel.generated_root_diameter_mm == pytest.approx(49.5055, abs=1e-9)
    # the nominal x of the case stays, the allowance carries the measured thickness
    assert (
        generation.gears.pinion.profile_shift_coefficient
        == base.gears.pinion.profile_shift_coefficient
    )
    assert generation.gears.wheel.profile_shift_coefficient == pytest.approx(
        base.gears.wheel.profile_shift_coefficient
    )
    assert pinion.span_allowance_um == pytest.approx(-293.1, abs=0.1)
    assert wheel.span_allowance_um == pytest.approx(-208.0, abs=0.1)
    assert pinion.span_generated_mm == pytest.approx(16.797, abs=1e-9)
    # the fillet keeps the tool tip radius, the addendum reaches the measured root
    assert generation.gears.pinion.tool_tip_radius_mm == base.gears.pinion.tool_tip_radius_mm
    # h_aP0 = (d + 2 x_E m_n - d_fE) / 2 with the x_E of the measured thickness
    assert pinion.addendum_factor == pytest.approx(1.1144, abs=5e-4)
    assert wheel.addendum_factor == pytest.approx(1.2575, abs=5e-4)
    assert generation.gears.pinion.generating_profile_shift_coefficient == pytest.approx(
        -0.2251, abs=5e-4
    )
    # the wheel's tool would top the measured tip circle: its dedendum was raised
    assert wheel.dedendum_factor is not None and wheel.dedendum_factor > 1.0
    assert pinion.dedendum_factor is None
    assert not [w for w in generation.warnings if w.code == "tip_circle_cut_by_tool"]
    # the arc replaces the edge break: the tip form diameter of the generation is the arc's
    assert generation.gears.wheel.tool_edge_break_angle_deg is None
    assert wheel.modification is not None and wheel.modification.tip_edge_radius_mm == 0.21
    rounded = ct.tooth_contour(generation, "wheel", modification=wheel.modification)
    assert generation.gears.wheel.tip_form_diameter_mm == pytest.approx(
        rounded.tip_form_diameter_mm, abs=1e-9
    )
    assert wheel.tip_chamfer_radial_mm is not None and 0.1 < wheel.tip_chamfer_radial_mm < 0.2
    assert (
        wheel.residual_tip_thickness_mm is not None and 0.4 < wheel.residual_tip_thickness_mm < 0.6
    )
    # the slope pivots on the measuring circle of the measured span
    assert wheel.modification.profile_slope_pivot_diameter_mm == pytest.approx(51.7275, abs=1e-3)
    assert wheel.modification.profile_slope_um == 10.25
    assert pinion.modification is not None and pinion.modification.tip_relief_um == 23.6
    assert pinion.modification.tip_edge_radius_mm == 0.0
    # A moves outwards with the larger wheel tip, E inwards with the smaller pinion tip
    rho_a0, rho_e0 = pl.path_of_contact_limits(base)
    rho_a1, rho_e1 = pl.path_of_contact_limits(generation)
    assert rho_a1 < rho_a0 and rho_e1 < rho_e0
    assert 1.1 < generation.pair_geometry.transverse_contact_ratio < 1.2
    # the manifest form of the changes is plain data
    as_dict = wheel.as_dict()
    assert as_dict["modification"]["tip_edge_radius_mm"] == 0.21 and as_dict["notes"]


def test_each_single_variant_leaves_the_other_gear_untouched(kst_e: PairInput) -> None:
    base = compute_generation(kst_e)
    steel = mf.apply(kst_e, mf.load_variant("kst_e", "stahl"))
    plastic = mf.apply(kst_e, mf.load_variant("kst_e", "kunststoff"))
    assert steel.generation.gears.wheel == base.gears.wheel
    assert steel.modification("wheel") is None and steel.modification("pinion") is not None
    assert plastic.generation.gears.pinion == base.gears.pinion
    assert plastic.modification("pinion") is None and plastic.modification("wheel") is not None
    # the untouched wheel of the steel variant gives the base contour
    assert ct.tooth_contour(steel.generation, "wheel") == ct.tooth_contour(base, "wheel")
    with pytest.raises(InputRangeError):
        mf.apply("kst_e", mf.load_variant("kst_e", "stahl"))  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        mf.apply(kst_e, "stahl")  # type: ignore[arg-type]


def test_a_target_the_generation_cannot_meet_is_refused(kst_e: PairInput) -> None:
    variant = mf.load_variant("kst_e", "stahl")
    assert variant.pinion is not None
    deep = variant.pinion.model_copy(update={"root_diameter_mm": 30.0})
    with pytest.raises((GeometryInfeasibleError, InputRangeError)):
        mf.apply(kst_e, variant.model_copy(update={"pinion": deep}))
    helical = kst_e.model_copy(update={"helix_angle_deg": 10.0})
    with pytest.raises(NotSupportedError):
        mf.apply(helical, variant)


def _flank_values(results: list[Any], name: str) -> list[float]:
    values: list[float] = []
    for result in results:
        entry = result.deviation(name)
        for stats in (entry.left, entry.right):
            if stats.mean_um is not None:
                values.append(stats.mean_um)
    return values


@pytest.mark.skipif(not MEASUREMENTS.is_dir(), reason="raw measurements not on this machine")
def test_the_numbers_of_the_file_are_the_medians_of_the_measured_parts() -> None:
    from gearcore.io.p40 import load_mew
    from gearcore.measurement import gina
    from gearcore.measurement.inventory import scan_folder

    inventory = scan_folder(MEASUREMENTS)
    groups = data.load_measurement_parts()["parts"]
    document = data.load_as_manufactured()["cases"]["kst_e"]["gears"]

    def latest(part_kind: str, group: str) -> list[Any]:
        members = set(groups[part_kind]["groups"][group])
        results = []
        for part in inventory.parts:
            if part.part != part_kind or part.me not in members:
                continue
            for file in sorted(part.of_kind("mew"), key=lambda f: (f.measured_on or "", f.path)):
                results.append(
                    gina.gina_result(load_mew(Path(inventory.root) / file.path), part=part_kind)
                )
        return list(gina.latest_per_part(results))

    pinions = latest("pinion", "rig_series")
    wheels = latest("wheel", "core")
    assert len(pinions) == 7 and len(wheels) == 10
    spec = document["pinion_measured"]
    assert median(r.size("WK").mean_mm for r in pinions) == pytest.approx(
        spec["span_measurement_mm"], abs=1e-9
    )
    assert median(r.size("Kopf").mean_mm for r in pinions) == pytest.approx(
        spec["tip_diameter_mm"], abs=1e-9
    )
    assert median(r.size("Fuß").mean_mm for r in pinions) == pytest.approx(
        spec["root_diameter_mm"], abs=1e-9
    )
    relief = []
    for result in pinions:
        assert result.tip_relief is not None
        for stats in (result.tip_relief.deviations.left, result.tip_relief.deviations.right):
            assert stats.mean_um is not None
            relief.append(stats.mean_um)
        assert result.tip_relief.start_diameter_mm == spec["tip_relief_start_diameter_mm"]
        assert result.evaluation_diameters_mm[0] == spec["profile_control_diameter_mm"]
    assert -median(relief) == pytest.approx(spec["tip_relief_um"], abs=1e-9)
    spec = document["wheel_measured"]
    assert median(r.size("WK").mean_mm for r in wheels) == pytest.approx(
        spec["span_measurement_mm"], abs=1e-9
    )
    assert median(r.size("Kopf").mean_mm for r in wheels) == pytest.approx(
        spec["tip_diameter_mm"], abs=1e-9
    )
    assert median(r.size("Fuß").mean_mm for r in wheels) == pytest.approx(
        spec["root_diameter_mm"], abs=1e-9
    )
    assert median(_flank_values(wheels, "profile_slope_deviation")) == pytest.approx(
        spec["profile_slope_um"], abs=1e-9
    )
    assert all(r.evaluation_diameters_mm[0] == spec["profile_control_diameter_mm"] for r in wheels)
