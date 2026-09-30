"""Export the JSON schemas of the public contracts (with symbol/unit/source metadata).

    python scripts/export_schemas.py [--out 20_code/00_development_documentation/schemas]

The schemas are the contract the later API, UI and AI layers read; they are regenerated, never
edited by hand.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import BaseModel

from gearcore.models.inputs import GearInput, PairInput, SpanMeasurement, ToolProfile
from gearcore.models.materials import MaterialRecord
from gearcore.models.profiles import BasicRackProfile
from gearcore.models.results import BasicGearGeometry, PairGeometry
from gearcore.parity import ParityRow

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = REPO_ROOT / "20_code" / "00_development_documentation" / "schemas"

MODELS: list[type[BaseModel]] = [
    ToolProfile,
    SpanMeasurement,
    GearInput,
    PairInput,
    MaterialRecord,
    BasicRackProfile,
    BasicGearGeometry,
    PairGeometry,
    ParityRow,
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for model in MODELS:
        path = args.out / f"{model.__name__}.schema.json"
        path.write_text(
            json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(path)


if __name__ == "__main__":
    main()
