"""
@module: tests.test_tolerances
@context: Domain-layer tests — gear-accuracy tolerances (ISO 1328-1:2018).
@role: The flank deviations, the (√2)^(A−5) grade step and the §5.2.3 rounding match
       the standard's equations (5–12) for a hand-verifiable gear; the dynamics
       deviation helper and the §1 validity ranges behave.
"""

import math

import pytest

from app.services.geometry.tolerances import (
    dynamics_deviations,
    flank_tolerances,
    grade_factor,
    round_tolerance,
    validity_warnings,
)


def test_rounding_rule() -> None:
    """ISO 1328-1 §5.2.3: >10 µm → 1, 5…10 µm → 0.5, <5 µm → 0.1."""
    assert round_tolerance(19.1) == 19.0
    assert round_tolerance(7.762) == 8.0
    assert round_tolerance(6.7125) == 6.5
    assert round_tolerance(4.83) == 4.8
    assert round_tolerance(2.04) == 2.0


def test_grade_step_sqrt2() -> None:
    """Each grade scales the unrounded class-5 value by √2 (§5.2.2)."""
    assert grade_factor(5) == pytest.approx(1.0)
    assert grade_factor(6) == pytest.approx(math.sqrt(2.0))
    assert grade_factor(4) == pytest.approx(1.0 / math.sqrt(2.0))


def test_flank_tolerances_grade5_reference() -> None:
    """Grade 5, m_n=2, d=100, b=20 — every deviation hand-computed from eq. 5–12."""
    t = flank_tolerances(
        accuracy_grade=5, normal_module_mm=2.0, reference_diameter_mm=100.0, face_width_mm=20.0
    )
    assert t.single_pitch == 6.0  # f_ptT (0.1+0.8+5)=5.9 → 6.0
    assert t.total_pitch == 19.0  # F_pT (0.2+5.5+1.4+12)=19.1 → 19
    assert t.profile_slope == 4.8  # f_HαT 4.8
    assert t.profile_form == 6.0  # f_fαT 6.1 → 6.0
    assert t.profile_total == 8.0  # F_αT √(4.8²+6.1²)=7.76 → 8.0 (unrounded components)
    assert t.helix_slope == 6.0  # f_HβT 6.065 → 6.0
    assert t.helix_form == 6.5  # f_fβT 6.713 → 6.5
    assert t.helix_total == 9.0  # F_βT √(6.065²+6.713²)=9.05 → 9.0


def test_grade6_is_grade5_times_sqrt2() -> None:
    """Grade 6 single pitch = grade-5 unrounded (5.9) × √2 = 8.34 → 8.5."""
    t6 = flank_tolerances(
        accuracy_grade=6, normal_module_mm=2.0, reference_diameter_mm=100.0, face_width_mm=20.0
    )
    assert t6.single_pitch == pytest.approx(round(5.9 * math.sqrt(2.0) * 2) / 2)
    assert t6.single_pitch == 8.5


def test_dynamics_deviations_from_grade() -> None:
    """The dynamics helper returns (f_pb=f_ptT, f_fα=f_fαT)."""
    f_pb, f_fa = dynamics_deviations(
        accuracy_grade=6, normal_module_mm=2.0, reference_diameter_mm=100.0
    )
    full = flank_tolerances(
        accuracy_grade=6, normal_module_mm=2.0, reference_diameter_mm=100.0, face_width_mm=10.0
    )
    assert f_pb == full.single_pitch
    assert f_fa == full.profile_form


def test_validity_ranges() -> None:
    """Out-of-range inputs warn (ISO 1328-1 §1); a normal gear is clean."""
    assert (
        validity_warnings(
            accuracy_grade=6,
            teeth=24,
            reference_diameter_mm=48.0,
            normal_module_mm=2.0,
            face_width_mm=20.0,
        )
        == []
    )
    warns = validity_warnings(
        accuracy_grade=13,
        teeth=3,
        reference_diameter_mm=2.0,
        normal_module_mm=0.2,
        face_width_mm=2.0,
    )
    assert len(warns) >= 4
