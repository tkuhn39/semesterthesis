"""
@module: app.services.geometry.tooth_root
@context: Domain layer — tooth-root geometry (the thesis topic: tooth-root stress).
@role: The 30°-tangent critical root section and the bending form factors per
       DIN 3990 Teil 3 (method B; identical geometry to ISO 6336-3): the critical
       root chord s_Fn, the root fillet radius ρ_F, the load application at the
       outer point of single tooth contact (α_Fen, bending lever h_Fe), and the
       resulting tooth form factor Y_F and stress correction factor Y_S.

Built on the rack-tool generation: the root fillet is the trochoid cut by the tool
tip rounding ρ_aP0, so the **generation profile shift x_E** (not the nominal x)
drives the as-cut root — exactly as for the form circles. Validated against STplus
(kst-E): s_Fn*, ρ_F*, α_Fen, h_Fe*, Y_F, Y_S for both gears.

Validated exact against STplus (spur, kst-E) **and** the ISO 6336 helical example:
the virtual spur gear (z_n = z/(cos²β_b·cos β), eq. 15–17) drives the load point, so
s_Fn, ρ_F, α_Fen, h_Fe and Y_F match for both. (For the helical example the FVA-
Workbench reports an inconsistent Y_F = 1.181 vs the 1.541 its own h_F*/s_Fn*/α_Fen
give via eq. 9 — a tool artefact; the norm-correct value is used, ADR-011.)
"""

import math

from pydantic import BaseModel

from app.services.geometry.gear import GearStage
from app.services.geometry.generation import involute


class ToothRootGeometry(BaseModel):
    """30°-tangent root geometry and the DIN 3990 / ISO 6336-3 bending form factors.

    Lengths in mm; height/radius factors refer to the normal module. The tool
    dedendum/root-radius factors are the generating tool's addendum (h_aP0*) and tip
    rounding (ρ_aP0*), which cut the gear root.
    """

    normal_module_mm: float
    teeth: int
    normal_pressure_angle_deg: float = 20.0
    helix_angle_deg: float = 0.0
    generation_profile_shift: float  # x_E
    tool_dedendum_factor: float  # h_fP* (= tool addendum h_aP0*)
    tool_root_radius_factor: float  # ρ_fP* (= tool tip rounding ρ_aP0*)
    tool_protuberance_mm: float = 0.0  # s_pr (0 for non-protuberance tools)
    usable_tip_diameter_mm: float  # d_Na (transverse)
    transverse_contact_ratio: float  # ε_α

    @classmethod
    def from_stage(cls, stage: GearStage, index: int) -> "ToothRootGeometry":
        """Build for gear ``index`` (0 = pinion, 1 = wheel) from a built `GearStage`.

        Requires the stage to carry the per-gear generation and usable tip diameter
        (i.e. built from a `.ste` with tool profiles and KOPFKREISDM).
        """
        if stage.generation is None or stage.usable_tip_diameter_mm is None:
            raise ValueError(
                "tooth-root geometry needs the generation/tip data (tool + KOPFKREISDM)"
            )
        gen = stage.generation[index]
        return cls(
            normal_module_mm=stage.normal_module_mm,
            teeth=stage.teeth[index],
            normal_pressure_angle_deg=stage.normal_pressure_angle_deg,
            helix_angle_deg=stage.helix_angle_deg,
            generation_profile_shift=gen.generation_profile_shift,
            tool_dedendum_factor=gen.tool.addendum_factor,
            tool_root_radius_factor=gen.tool.tip_radius_factor,
            usable_tip_diameter_mm=stage.usable_tip_diameter_mm[index],
            transverse_contact_ratio=stage.transverse_contact_ratio,
        )

    @property
    def _alpha_n(self) -> float:
        return math.radians(self.normal_pressure_angle_deg)

    @property
    def _beta(self) -> float:
        return math.radians(self.helix_angle_deg)

    @property
    def _base_helix_angle(self) -> float:
        """Base helix angle β_b = asin(sin β · cos α_n) (ISO 6336-3 eq. 15)."""
        return math.asin(math.sin(self._beta) * math.cos(self._alpha_n))

    @property
    def virtual_teeth(self) -> float:
        """Virtual spur-gear tooth number z_n = z/(cos²β_b·cos β) (ISO 6336-3 eq. 16)."""
        return self.teeth / (math.cos(self._base_helix_angle) ** 2 * math.cos(self._beta))

    @property
    def _transverse_reference_diameter_mm(self) -> float:
        return self.normal_module_mm / math.cos(self._beta) * self.teeth

    @property
    def _virtual_reference_diameter_mm(self) -> float:
        return self.normal_module_mm * self.virtual_teeth  # d_n (ISO 6336-3 eq. 18)

    @property
    def _virtual_base_diameter_mm(self) -> float:
        return self._virtual_reference_diameter_mm * math.cos(self._alpha_n)  # d_bn (eq. 19)

    @property
    def _virtual_tip_diameter_mm(self) -> float:
        """Virtual tip diameter d_an = d_n + (d_Na − d) (ISO 6336-3 eq. 20)."""
        return self._virtual_reference_diameter_mm + (
            self.usable_tip_diameter_mm - self._transverse_reference_diameter_mm
        )

    @property
    def _virtual_base_pitch_mm(self) -> float:
        return math.pi * self.normal_module_mm * math.cos(self._alpha_n)  # p_en

    @property
    def _virtual_contact_ratio(self) -> float:
        return (
            self.transverse_contact_ratio / math.cos(self._base_helix_angle) ** 2
        )  # ε_αn (eq. 17)

    @property
    def _g_aux(self) -> float:
        """Auxiliary G (ISO 6336-3): G = ρ_fP* − h_fP* + x_E."""
        return (
            self.tool_root_radius_factor - self.tool_dedendum_factor + self.generation_profile_shift
        )

    @property
    def _theta(self) -> float:
        """Auxiliary angle ϑ, solved by fixed-point iteration ϑ = (2G/z_n) tan ϑ − H."""
        alpha_n = self._alpha_n
        e_aux = (
            math.pi / 4.0
            - self.tool_dedendum_factor * math.tan(alpha_n)
            + self.tool_protuberance_mm / (self.normal_module_mm * math.cos(alpha_n))
            - (1.0 - math.sin(alpha_n)) * self.tool_root_radius_factor / math.cos(alpha_n)
        )
        zn = self.virtual_teeth
        h_aux = (2.0 / zn) * (math.pi / 2.0 - e_aux) - math.pi / 3.0
        theta = math.pi / 6.0
        for _ in range(80):
            theta = (2.0 * self._g_aux / zn) * math.tan(theta) - h_aux
        return theta

    @property
    def critical_root_chord_mn(self) -> float:
        """Critical root chord at the 30° tangent, s_Fn / m_n (ISO 6336-3)."""
        zn, theta, g = self.virtual_teeth, self._theta, self._g_aux
        return zn * math.sin(math.pi / 3.0 - theta) + math.sqrt(3.0) * (
            g / math.cos(theta) - self.tool_root_radius_factor
        )

    @property
    def root_fillet_radius_mn(self) -> float:
        """Root fillet radius at the critical section, ρ_F / m_n (ISO 6336-3)."""
        zn, theta, g = self.virtual_teeth, self._theta, self._g_aux
        return self.tool_root_radius_factor + 2.0 * g**2 / (
            math.cos(theta) * (zn * math.cos(theta) ** 2 - 2.0 * g)
        )

    @property
    def notch_parameter(self) -> float:
        """Notch parameter q_s = s_Fn / (2 ρ_F)."""
        return self.critical_root_chord_mn / (2.0 * self.root_fillet_radius_mn)

    @property
    def outer_single_contact_diameter_mm(self) -> float:
        """Diameter d_en of the outer single contact point in the virtual spur gear.

        One double-contact length ``(ε_αn − 1)·p_en`` inside the virtual tip on the
        line of action — the load position for the maximum root bending moment.
        """
        base_radius = self._virtual_base_diameter_mm / 2.0
        tip_tangent = math.sqrt((self._virtual_tip_diameter_mm / 2.0) ** 2 - base_radius**2)
        single = tip_tangent - (self._virtual_contact_ratio - 1.0) * self._virtual_base_pitch_mm
        return 2.0 * math.hypot(base_radius, single)

    def _load_angle_at(self, load_diameter_mm: float) -> float:
        """Pressure angle α_e of the virtual flank at a load applied on ``load_diameter_mm``."""
        return math.acos(self._virtual_base_diameter_mm / load_diameter_mm)

    def _half_angle_to(self, load_angle: float) -> float:
        """Angle γ_e between the tooth centre line and the load point (ISO 6336-3)."""
        alpha_n = self._alpha_n
        return (
            (math.pi / 2.0 + 2.0 * self.generation_profile_shift * math.tan(alpha_n))
            / self.virtual_teeth
            + involute(alpha_n)
            - involute(load_angle)
        )

    def _bending_lever_at(self, load_diameter_mm: float) -> tuple[float, float]:
        """Return (α_Fe [rad], h_Fe / m_n) for a load applied at ``load_diameter_mm``."""
        load_angle = self._load_angle_at(load_diameter_mm)
        gamma = self._half_angle_to(load_angle)
        alpha_fe = load_angle - gamma
        zn, theta, g = self.virtual_teeth, self._theta, self._g_aux
        load_term = (math.cos(gamma) - math.sin(gamma) * math.tan(alpha_fe)) * (
            load_diameter_mm / self.normal_module_mm
        )
        root_term = zn * math.cos(math.pi / 3.0 - theta) + (
            g / math.cos(theta) - self.tool_root_radius_factor
        )
        return alpha_fe, 0.5 * (load_term - root_term)

    def _form_factor_at(self, load_diameter_mm: float) -> float:
        """Tooth form factor Y_F = 6 h_Fe cos α_Fe / (s_Fn² cos α_n) for a given load point."""
        alpha_fe, h_fe = self._bending_lever_at(load_diameter_mm)
        s_fn = self.critical_root_chord_mn
        return 6.0 * h_fe * math.cos(alpha_fe) / (s_fn**2 * math.cos(self._alpha_n))

    def _stress_correction_at(self, bending_lever_mn: float) -> float:
        """Stress correction factor Y_S (DIN 3990 / ISO 6336-3, 1 ≤ q_s < 8)."""
        lever_ratio = self.critical_root_chord_mn / bending_lever_mn
        return (1.2 + 0.13 * lever_ratio) * self.notch_parameter ** (
            1.0 / (1.21 + 2.3 / lever_ratio)
        )

    @property
    def load_application_angle_deg(self) -> float:
        """Load application angle α_Fen at the outer single contact point (ISO 6336 method B)."""
        return math.degrees(self._bending_lever_at(self.outer_single_contact_diameter_mm)[0])

    @property
    def bending_lever_mn(self) -> float:
        """Bending moment arm h_Fe / m_n (load at the outer single contact point)."""
        return self._bending_lever_at(self.outer_single_contact_diameter_mm)[1]

    @property
    def form_factor(self) -> float:
        """Tooth form factor Y_F (DIN 3990 / ISO 6336-3 method B; load at d_en)."""
        return self._form_factor_at(self.outer_single_contact_diameter_mm)

    @property
    def stress_correction_factor(self) -> float:
        """Stress correction factor Y_S (DIN 3990 / ISO 6336-3, load at d_en)."""
        return self._stress_correction_at(self.bending_lever_mn)

    @property
    def tip_load_application_angle_deg(self) -> float:
        """Load application angle α_Fan for a load at the tooth tip (VDI 2736 / method C)."""
        return math.degrees(self._bending_lever_at(self._virtual_tip_diameter_mm)[0])

    @property
    def tip_bending_lever_mn(self) -> float:
        """Bending moment arm h_Fa / m_n for a load at the tooth tip (VDI 2736)."""
        return self._bending_lever_at(self._virtual_tip_diameter_mm)[1]

    @property
    def form_factor_tip(self) -> float:
        """Tooth form factor Y_Fa for a load at the tooth tip (VDI 2736 plastic root)."""
        return self._form_factor_at(self._virtual_tip_diameter_mm)

    @property
    def stress_correction_factor_tip(self) -> float:
        """Stress correction factor Y_Sa for a load at the tooth tip (VDI 2736)."""
        return self._stress_correction_at(self.tip_bending_lever_mn)
