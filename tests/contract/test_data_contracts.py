from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def test_contract_files_are_valid_json_schema() -> None:
    schemas = sorted((ROOT / "data/contracts").glob("*.schema.json"))
    assert len(schemas) >= 4
    for path in schemas:
        schema = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)


def test_generation_sample_matches_required_fields() -> None:
    schema = json.loads(
        (ROOT / "data/contracts/generation.schema.json").read_text(encoding="utf-8")
    )
    frame = pd.read_parquet(ROOT / "data/lakehouse/silver/generation.parquet")
    assert set(schema["required"]) <= set(frame.columns)
