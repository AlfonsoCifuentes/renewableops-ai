"""Verify the generated two-year, five-minute SCADA scale profile."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "data" / "scale" / "scada_5min_2y"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    manifest_path = PROFILE / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    )
    files = manifest.get("files", {})
    measured_rows = 0
    checksums_valid = bool(files)
    for filename, expected in files.items():
        path = PROFILE / filename
        if not path.exists():
            checksums_valid = False
            continue
        measured_rows += pq.ParquetFile(path).metadata.num_rows
        checksums_valid &= expected == f"sha256:{_sha256(path)}"
    passed = bool(
        manifest.get("profile") == "scada_5min_two_year"
        and manifest.get("days") == 730
        and manifest.get("frequency") == "5min"
        and manifest.get("assets") == 12
        and manifest.get("scenario_count") == 20
        and len(files) == 12
        and measured_rows == manifest.get("rows")
        and measured_rows >= 2_500_000
        and checksums_valid
    )
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if passed else "failed",
        "scope": "ignored local scale profile; reproducible with `make scale-data`",
        "profile_manifest": "data/scale/scada_5min_2y/manifest.json",
        "rows": measured_rows,
        "assets": manifest.get("assets"),
        "days": manifest.get("days"),
        "frequency": manifest.get("frequency"),
        "scenario_count": manifest.get("scenario_count"),
        "files": len(files),
        "checksums_valid": checksums_valid,
    }
    output = ROOT / "artifacts" / "verification" / "scada-scale.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
