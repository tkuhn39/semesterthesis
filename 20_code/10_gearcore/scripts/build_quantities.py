"""Render the quantity registry as a table for the documentation.

    python scripts/build_quantities.py            # writes 00_development_documentation/quantities.md
    python scripts/build_quantities.py --check    # exit 1 if the file is stale

The registry ``src/gearcore/data/quantities.yaml`` is the single source of truth for program names,
symbols and designations (project rule 3b, ADR-108); the table is generated, never edited by hand.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from gearcore.quantities import quantities, render_markdown

REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET = REPO_ROOT / "20_code" / "00_development_documentation" / "quantities.md"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = render_markdown()
    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.is_file() else ""
        raise SystemExit(0 if current == text else 1)
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    registry = quantities()
    pending = sum(entry.status == "pending" for entry in registry.values())
    print(f"{len(registry)} quantities, {pending} pending -> {TARGET}")


if __name__ == "__main__":
    main()
