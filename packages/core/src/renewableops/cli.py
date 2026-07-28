"""Command-line interface for reproducible portfolio workflows."""

from __future__ import annotations

import argparse
import json

from .pipeline import run_demo_pipeline
from .sources import fetch_aemet, fetch_pvgis, fetch_redata


def _ingest() -> dict[str, object]:
    results: dict[str, object] = {}
    for name, fetcher in (
        ("ree_redata", fetch_redata),
        ("pvgis", fetch_pvgis),
        ("aemet", fetch_aemet),
    ):
        try:
            payload = fetcher()
            results[name] = {
                "status": "success",
                "checksum": payload.checksum_sha256,
                "extracted_at": payload.extracted_at,
            }
        except Exception as error:  # noqa: BLE001 - CLI reports bounded source failures
            results[name] = {
                "status": "fallback",
                "reason": str(error),
                "data_used": "versioned demo fixture / synthetic reference",
            }
    return results


def main() -> None:
    parser = argparse.ArgumentParser(prog="renewableops")
    parser.add_argument(
        "command",
        choices=["run-demo", "seed", "transform", "train", "publish", "ingest"],
    )
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args()
    result = _ingest() if args.command == "ingest" else run_demo_pipeline(days=args.days)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
