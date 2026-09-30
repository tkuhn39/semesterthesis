"""Reference values of the pair equations with 45-digit decimal arithmetic.

Independent of gearcore and of libm: the formulas are typed from DIN ISO 21771:2014-08 (§4.4,
§5.2 to §5.6), the trigonometric functions are Taylor series and Newton iterations on
``decimal.Decimal`` (``math`` only supplies start values of the iterations). The output is the
table ``REFERENCE`` of ``tests/test_pair.py``; run the script to reproduce it:

    python scripts/decimal_reference_pair.py
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


def inv_inverse(value: Decimal, start: Decimal) -> Decimal:
    a = start
    for _ in range(80):
        t = tan(a)
        a = a - (t - a - value) / (t * t)
    return +a


PI = pi()


def rad(degrees: str) -> Decimal:
    return D(degrees) * PI / 180


def case(
    name: str,
    z: tuple[int, int],
    m_n: str,
    alpha_n_deg: str,
    beta_deg: str,
    b_w: str,
    d_a: tuple[str, str],
    *,
    a_w: str | None = None,
    x: tuple[str, str] | None = None,
    d_Ff: tuple[str, str] | None = None,
) -> dict[str, Decimal]:
    """All pair quantities of one case. ``d_Ff`` applies Eq. (66) to (69) where it limits."""
    z1, z2, module, width = D(z[0]), D(z[1]), D(m_n), D(b_w)
    d_a1, d_a2 = D(d_a[0]), D(d_a[1])
    alpha_n, beta = rad(alpha_n_deg), rad(beta_deg)
    alpha_t = atan(tan(alpha_n) / cos(beta))
    if a_w is None:
        if x is None:
            raise ValueError(f"{name}: give a_w or both x")
        value = inv(alpha_t) + 2 * tan(alpha_n) * (D(x[0]) + D(x[1])) / (z1 + z2)
        alpha_wt = inv_inverse(value, alpha_t)
        distance = (z1 + z2) * module * cos(alpha_t) / (2 * cos(beta) * cos(alpha_wt))
    else:
        distance = D(a_w)
        alpha_wt = acos((z1 + z2) * module * cos(alpha_t) / (2 * distance * cos(beta)))
    sum_x = (z1 + z2) * (inv(alpha_wt) - inv(alpha_t)) / (2 * tan(alpha_n))
    d_b1 = z1 * module / cos(beta) * cos(alpha_t)
    d_b2 = z2 * module / cos(beta) * cos(alpha_t)
    t1t2 = distance * sin(alpha_wt)

    def roll(d: Decimal, d_b: Decimal) -> Decimal:
        return (d * d - d_b * d_b).sqrt()

    def mating(d_mate: Decimal, d_b_mate: Decimal, d_b: Decimal) -> Decimal:
        return ((2 * t1t2 - roll(d_mate, d_b_mate)) ** 2 + d_b * d_b).sqrt()

    d_Nf1, d_Nf2 = mating(d_a2, d_b2, d_b1), mating(d_a1, d_b1, d_b2)  # Eq. (64), (65)
    d_Na1, d_Na2 = d_a1, d_a2
    if d_Ff is not None:
        form1, form2 = D(d_Ff[0]), D(d_Ff[1])
        if form1 > d_Nf1:  # Eq. (66), (68)
            d_Nf1, d_Na2 = form1, mating(form1, d_b1, d_b2)
        if form2 > d_Nf2:  # Eq. (67), (69)
            d_Nf2, d_Na1 = form2, mating(form2, d_b2, d_b1)
    r1, r2 = roll(d_Na1, d_b1), roll(d_Na2, d_b2)
    g_a1 = (r1 - d_b1 * tan(alpha_wt)) / 2
    g_a2 = (r2 - d_b2 * tan(alpha_wt)) / 2
    p_t = PI * module / cos(beta)
    p_bt = p_t * cos(alpha_t)
    u = z2 / z1
    d_w1 = d_b1 / cos(alpha_wt)
    g_alpha = (r1 + r2) / 2 - t1t2
    return {
        "alpha_wt_deg": alpha_wt * 180 / PI,
        "a_w": distance,
        "sum_x": sum_x,
        "d_w1": d_w1,
        "d_w2": d_b2 / cos(alpha_wt),
        "p_t": p_t,
        "p_bt": p_bt,
        "T1T2": t1t2,
        "d_Nf1": d_Nf1,
        "d_Nf2": d_Nf2,
        "d_Na1": d_Na1,
        "d_Na2": d_Na2,
        "g_alpha": g_alpha,
        "g_a1": g_a1,
        "g_a2": g_a2,
        "h_w": (d_a1 + d_a2) / 2 - distance,
        "eps_alpha": g_alpha / p_bt,
        "eps_beta": width * abs(sin(beta)) / (PI * module),
        "K_ga1": 2 * g_a1 / d_w1 * (1 + 1 / u),
        "K_ga2": 2 * g_a2 / d_w1 * (1 + 1 / u),
        "zeta_f1": 1 - (r2 / 2) / (u * (t1t2 - r2 / 2)),
        "zeta_f2": 1 - u * (r1 / 2) / (t1t2 - r1 / 2),
    }


CASES: dict[str, dict[str, Decimal]] = {
    # ISO/TR 6336-30:2022 Annex A example 1
    "A": case("A", (17, 103), "8", "20", "15.8", "100", ("159.66", "872.35"), a_w="500"),
    "B": case("B", (12, 40), "2", "20", "0", "20", ("28", "83.2"), x=("0.3", "-0.1")),
    "C": case("C", (25, 40), "3", "22.5", "-30", "30", ("94.4", "144"), x=("0.3", "-0.1")),
    # B with root form circles above the start of the active profile of both gears
    "D": case(
        "D", (12, 40), "2", "20", "0", "20", ("28", "83.2"), x=("0.3", "-0.1"),
        d_Ff=("22.9", "78.4"),
    ),
    # B with a root form circle of the wheel only (Eq. (67), (69))
    "E": case(
        "E", (12, 40), "2", "20", "0", "20", ("28", "83.2"), x=("0.3", "-0.1"),
        d_Ff=("22.6", "78.4"),
    ),
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
