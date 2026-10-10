"""Tables and labels of the measurement reports: Markdown and CSV text in German with a decimal
comma, symbols and units from the quantity registry. No file is written here."""

import csv
import io
from collections.abc import Sequence

from gearcore.errors import InputRangeError
from gearcore.quantities import quantity

GREEK_LETTERS = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "epsilon": "ε",
    "eta": "η",
    "xi": "ξ",
    "psi": "ψ",
    "rho": "ρ",
    "zeta": "ζ",
    "Sigma": "Σ",
}
"""Plain-text Greek letters for Markdown (``quantities.GREEK`` holds the LaTeX forms)."""


def german_number(value: float, digits: int) -> str:
    """``1234.5`` with one digit → ``'1234,5'`` (decimal comma, no thousands separator)."""
    text = f"{value:.{digits}f}"
    if text.lstrip("-").strip("0.") == "":
        text = text.lstrip("-")  # a value that prints as zero loses its sign
    return text.replace(".", ",")


def plain_symbol(symbol: str) -> str:
    """A registry symbol as plain text with Greek letters: ``f_H_alpha`` → ``f_Hα``, ``F_p`` →
    ``F_p`` (subscripts after the first underscore are joined)."""
    if not symbol:
        raise InputRangeError("empty symbol")
    base, _, subscript = symbol.partition("_")
    base = GREEK_LETTERS.get(base, base)
    parts = [GREEK_LETTERS.get(part, part) for part in subscript.split("_") if part]
    return base + ("_" + "".join(parts) if parts else "")


def quantity_label(name: str, *, unit: bool = True) -> str:
    """``'F_α in µm'`` for a registry name (designation of the norm in the hover of the table)."""
    entry = quantity(name)
    symbol = plain_symbol(entry.symbol) if entry.symbol else name
    return f"{symbol} in {entry.unit}" if unit and entry.unit != "-" else symbol


def markdown_table(columns: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    """Lines of a Markdown table (every row must have as many cells as there are columns)."""
    for row in rows:
        if len(row) != len(columns):
            raise InputRangeError(f"row with {len(row)} cells for {len(columns)} columns: {row!r}")
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def csv_text(columns: Sequence[str], rows: Sequence[Sequence[str]], *, delimiter: str = ";") -> str:
    """CSV text with a semicolon (German Excel) and LF line ends."""
    for row in rows:
        if len(row) != len(columns):
            raise InputRangeError(f"row with {len(row)} cells for {len(columns)} columns: {row!r}")
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return buffer.getvalue()


__all__ = [
    "GREEK_LETTERS",
    "csv_text",
    "german_number",
    "markdown_table",
    "plain_symbol",
    "quantity_label",
]
