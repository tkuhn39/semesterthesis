# Adversarial gate — protocol for every increment

Every increment (module + tests + notebook section) ends with this gate before the next one starts.

## Reviewer
A separate agent (Explore/Plan type) with the explicit guard sentence:
*"Do not modify ANY file by any means, including shell redirection, heredocs, sed -i, touch, mkdir or git;
if you believe a fix is needed, describe it in the report only."* Temporary files only in the agent's
scratchpad. After the report: `git status` must show no unexpected change (incident 2026-08-18).

## Inputs handed to the reviewer
- The increment's diff (or file list), public signatures, fixtures and the relevant norm pages
  (page numbers; the reviewer reads the PDF via Poppler).
- The invariants and error types the implementer claims.

## Mandate, in this order
1. **Boundary sweeps** on every input field: min, max, ±ε around limits, sign flips, β = 0 / 1e-9 / ±45°,
   z = 5, x = ±2, a = a_min·(1 ± 1e-9), m_n = 0.05, k = k_min − 1 / k_max + 1.
2. **Invariant hunting** beyond the shipped property tests (symmetry ±β, continuity β → 0, x → 0,
   equality of alternative formulas, monotonicity).
3. **Independent recomputation** of at least three fixture values by hand from the norm page — not from
   the code.
4. **Code smells:** `max(x, 1e-12)`-style clamping, `abs()` before `sqrt`, `try/except` around math,
   silent `None`, unbracketed iteration, duplicated helpers (a second `inv_inverse` anywhere = P0),
   missing or bare `@eq` references, equation numbers without source key.
5. **Quantity registry:** every quantity the increment introduces has an entry in
   `data/quantities.yaml`; symbol, designation and location are compared with the rendered page;
   worked-example fixtures are complete and carry the labels of the norm. Tabulated values and
   defaults of the increment are listed in `norm_map.md` and compared with the current norm.
6. **Contract checks:** JSON round trip, schema export, typed error classes for every failure path.

## Output
Table `ID | severity P0–P3 | repro (≤ 5 lines) | expected (norm reference) | actual`.
- P0: wrong number or crash on a valid input; duplicated formula; missing source.
- P1: wrong behaviour at the boundary, missing guard, misleading warning, unverified citation.
- P2: unclear naming, doc gap, tolerance too loose.
- P3: cosmetic.

## Exit criterion
P0 = 0. Every P1 fixed or entered in `known_limits.md` with a reason and owner. Every finding becomes a
regression test `tests/test_adv_<increment>_<id>.py` written by the implementer, not the reviewer.
Budget: 30–45 min reviewer time per increment. The gate result is summarised in the roadmap entry of the
increment and reported to the user before the next increment starts.
