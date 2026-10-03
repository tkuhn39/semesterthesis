"""Reference values of the generation equations with 45-digit decimal arithmetic.

Independent of gearcore and of libm: the formulas are typed from DIN ISO 21771:2014-08 (§4.6,
§4.7, §7.4 to §7.7 with Anhang NB) and DIN 3960:1987-03 Anhang A.3.1, the trigonometric
functions are Taylor series and Newton iterations on ``decimal.Decimal`` (``math`` only supplies
start values). The output is the table ``REFERENCE`` of ``tests/test_generation.py``:

    python scripts/decimal_reference_generation.py
"""

from __future__ import annotations

import math
from decimal import Decimal, getcontext

getcontext().prec = 45
D = Decimal


def pi() -> Decimal:
    getcontext().prec += 4
    lasts, t, s, n, na, d, da = D(0), D(3), D(3), 1, 0, 0, 24
    while s != lasts:
        lasts = s
        n, na = n + na, na + 8
        d, da = d + da, da + 32
        t = (t * n) / d
        s += t
    getcontext().prec -= 4
    return +s


def sin(x: Decimal) -> Decimal:
    getcontext().prec += 4
    i, lasts, s, fact, num, sign = 1, D(0), x, 1, x, 1
    while s != lasts:
        lasts = s
        i += 2
        fact *= i * (i - 1)
        num *= x * x
        sign *= -1
        s += num / fact * sign
    getcontext().prec -= 4
    return +s


def cos(x: Decimal) -> Decimal:
    getcontext().prec += 4
    i, lasts, s, fact, num, sign = 0, D(0), D(1), 1, D(1), 1
    while s != lasts:
        lasts = s
        i += 2
        fact *= i * (i - 1)
        num *= x * x
        sign *= -1
        s += num / fact * sign
    getcontext().prec -= 4
    return +s


def tan(x: Decimal) -> Decimal:
    return sin(x) / cos(x)


def atan(x: Decimal) -> Decimal:
    y = D(repr(math.atan(float(x))))
    for _ in range(40):
        t = tan(y)
        y = y - (t - x) / (1 + t * t)
    return +y


def acos(x: Decimal) -> Decimal:
    y = D(repr(math.acos(float(x))))
    for _ in range(40):
        y = y + (cos(y) - x) / sin(y)
    return +y


def inv(a: Decimal) -> Decimal:
    return tan(a) - a


PI = pi()


def rad(degrees: str) -> Decimal:
    return D(degrees) * PI / 180


def case(
    name: str,
    z: int,
    m_n: str,
    alpha_n_deg: str,
    beta_deg: str,
    x: str,
    d_a: str,
    h_aP0_factor: str,
    rho_factor: str,
    *,
    E_sns_um: str = "0",
    E_sni_um: str = "0",
    h_FfP0_factor: str | None = None,
    alpha_kP_deg: str | None = None,
) -> dict[str, Decimal]:
    """The generation quantities of one gear (no undercut, no protuberance, q = 0)."""
    zz, module, shift, tip = D(z), D(m_n), D(x), D(d_a)
    alpha_n, beta = rad(alpha_n_deg), rad(beta_deg)
    h_aP0, rho = D(h_aP0_factor) * module, D(rho_factor) * module
    alpha_t = atan(tan(alpha_n) / cos(beta))
    d = zz * module / cos(beta)
    d_b = d * cos(alpha_t)
    x_Es = shift + D(E_sns_um) / 1000 / (2 * module * tan(alpha_n))  # (123)
    x_Ei = shift + D(E_sni_um) / 1000 / (2 * module * tan(alpha_n))  # (124)
    x_E = x_Es
    h_FaP0 = h_aP0 - rho * (1 - sin(alpha_n))  # bracket of (128) NB
    d_fE = d + 2 * x_E * module - 2 * h_aP0  # (125)
    d_fEi = d + 2 * x_Ei * module - 2 * h_aP0
    x_Emin = h_FaP0 / module - zz * sin(alpha_t) ** 2 / (2 * cos(beta))  # (135)
    roll = d * sin(alpha_t) - 2 * (h_FaP0 - x_E * module) / sin(alpha_t)
    if roll < 0:
        raise ValueError(f"{name}: undercut, Eq. (128) does not apply")
    d_Ff = (roll * roll + d_b * d_b).sqrt()  # (128) NB
    # (129)/(130) as printed, with sin(alpha_t) in the bracket
    xi = tan(alpha_t) - 4 * ((h_aP0 - rho * (1 - sin(alpha_t))) / module - x_E) * cos(beta) / (
        zz * sin(2 * alpha_t)
    )
    d_Ff_printed = d_b / cos(atan(xi))
    psi = (PI + 4 * x_E * tan(alpha_n)) / (2 * zz)  # (41) with x_E
    psi_b = psi + inv(alpha_t)  # (42)
    alpha_at = acos(d_b / tip)  # (12)
    s_at = tip * (psi_b - inv(alpha_at))  # (38) with (40)
    beta_a = atan(tan(beta) * tip / d)  # (8)
    s_an = s_at * cos(beta_a)  # (48)
    values = {
        "x_Es": x_Es,
        "x_Ei": x_Ei,
        "h_FaP0": h_FaP0,
        "d_fE": d_fE,
        "d_fEi": d_fEi,
        "x_Emin": x_Emin,
        "d_Ff": d_Ff,
        "d_Ff_printed_130": d_Ff_printed,
        "s_at": s_at,
        "s_an": s_an,
        "h": (tip - d_fE) / 2,  # (35)
        "h_a": (tip - d) / 2,  # (36)
        "h_f": (d - d_fE) / 2,  # (37)
    }
    if alpha_kP_deg is not None and h_FfP0_factor is not None:
        # DIN 3960 Anhang A.3.1: edge break involute
        h_FfP0 = D(h_FfP0_factor) * module
        alpha_tK = atan(tan(rad(alpha_kP_deg)) / cos(beta))
        d_bK = d * cos(alpha_tK)
        m_t = module / cos(beta)
        s_tK = (
            m_t * PI / 2
            + 2 * h_FfP0 * (tan(alpha_tK) - tan(alpha_t))
            + 2 * x_E * module * tan(alpha_tK)
        )  # (A.3.03)
        psi_bK = s_tK / d + inv(alpha_tK)

        def gap(diameter: Decimal) -> Decimal:
            return psi_bK - psi_b - inv(acos(d_bK / diameter)) + inv(acos(d_b / diameter))

        low, high = d_b, tip
        if gap(high) < 0:
            for _ in range(200):  # bisection for (A.3.06)
                mid = (low + high) / 2
                if gap(mid) > 0:
                    low = mid
                else:
                    high = mid
            d_Fa = (low + high) / 2
        else:
            d_Fa = tip
        values["d_Fa"] = d_Fa
        values["h_K"] = (tip - d_Fa) / 2
        values["s_aK"] = tip * (psi_bK - inv(acos(d_bK / tip)))  # (A.3.05)
    return values


CASES: dict[str, dict[str, Decimal]] = {
    # spur, ISO/TR 6336-30 example 1 pinion tool (h_fP = 1,4 m_n, rho_fP = 0,39 m_n) on z = 17
    # as a spur gear with x = 0,3 (free of undercut), x_E from allowances
    "S": case("S", 17, "8", "20", "0", "0.3", "158", "1.4", "0.39", E_sns_um="-80", E_sni_um="-130"),
    # helical, ISO/TR 6336-30 example 1 pinion (beta = 15,8, x_E1 = 0,117 79 printed on p. 45)
    "H": case("H", 17, "8", "20", "15.8", "0.11779", "159.66", "1.4", "0.39"),
    # spur with an edge break flank of the tool (kst-C wheel: z = 36, m_n = 3, x = 0,2211 as x_E,
    # h_aP0* = 1,25, rho* = 0,33, h_FfP0* = 0,6973, alpha_kP = 45)
    "K": case("K", 36, "3", "20", "0", "0.22105", "114.69", "1.25", "0.33", h_FfP0_factor="0.6973", alpha_kP_deg="45"),
    # helical with an edge break flank (constructed): z = 25, m_n = 5, beta = 20, x_E = 0,2184
    "L": case("L", 25, "5", "20", "20", "0.2184", "145.522", "1.25", "0.3", h_FfP0_factor="0.8", alpha_kP_deg="45"),
}  # fmt: skip


def main() -> None:
    print("REFERENCE: dict[str, dict[str, float]] = {")
    for name, values in CASES.items():
        print(f'    "{name}": {{')
        for key, value in values.items():
            print(f'        "{key}": {float(value)!r},')
        print("    },")
    print("}")


if __name__ == "__main__":
    main()
