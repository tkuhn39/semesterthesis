"""How far the circle approximation of FVA 604 I (p. 29) lies from the STplus contour exports.

FVA 604 I approximates the transverse tip rounding of a helical tool, an ellipse with the
semi-axes rho_aP0 / cos(beta) and rho_aP0, by a circle of the constant radius rho_aP0 / cos(beta)
about the centre of the rounding. This script generates the fillet with that circle (both
semi-axes rho_aP0 / cos(beta), the centre unchanged, so the root circle moves towards the gear
centre by rho_aP0 (1 / cos(beta) - 1)) and with the ellipse, and prints the largest normal deviation of the
STplus contour export from each fillet, for the three helical own runs. The numbers quoted in
ADR-113 and norm_map.md come from here:

    python scripts/circle_approximation_fva604.py
"""

from __future__ import annotations

import dataclasses
from typing import Literal

from gearcore import contour as ct
from gearcore import trochoid as tr
from gearcore.data import has_stplus, stplus_case_dirs
from gearcore.parity import compute_generation_from_data, generation_data


def main() -> None:
    original = tr.tip_rounding

    def circle(*args: object, **kwargs: object) -> tr.TipRounding:
        rounding = original(*args, **kwargs)  # type: ignore[arg-type]
        return dataclasses.replace(
            rounding, semi_axis_eta_mm=rounding.semi_axis_xi_mm, axis_ratio=1.0
        )

    print(
        "case, gear, beta | ellipse: fillet max / rms um | FVA circle rho / cos(beta): max / rms um"
    )
    for path in stplus_case_dirs():
        case = path.name
        data = generation_data(case)
        if data.pair.helix_angle_deg == 0.0:
            continue
        result = compute_generation_from_data(data, data.values)
        for gear in (1, 2):
            if not has_stplus(case, f"contour_wz{gear}"):
                continue
            role: Literal["pinion", "wheel"] = "pinion" if gear == 1 else "wheel"
            reference = ct.stplus_contour(case, gear)
            exact = ct.compare(ct.tooth_contour(result, role), reference)
            tr.tip_rounding = circle
            try:
                approximate = ct.compare(ct.tooth_contour(result, role), reference)
            finally:
                tr.tip_rounding = original
            print(
                f"{case} {role} beta={data.pair.helix_angle_deg} | "
                f"{exact.fillet_max_um:.3f} / {exact.fillet_rms_um:.3f} | "
                f"{approximate.fillet_max_um:.1f} / {approximate.fillet_rms_um:.1f}"
            )


if __name__ == "__main__":
    main()
