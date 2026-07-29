"""Command-line interface for reproducible portfolio workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .approvals import approve_model
from .config import PROJECT_ROOT
from .ingestion import ingest_official_sources
from .model_evidence import write_model_verification
from .pipeline import refresh_public_snapshot, run_demo_pipeline
from .synthetic import write_scada_profile


def _ingest() -> dict[str, object]:
    return ingest_official_sources()


def main() -> None:
    parser = argparse.ArgumentParser(prog="renewableops")
    parser.add_argument(
        "command",
        choices=[
            "run-demo",
            "seed",
            "transform",
            "train",
            "publish",
            "ingest",
            "generate-scale",
            "approve-model",
            "verify-models",
        ],
    )
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--frequency", default="5min")
    parser.add_argument("--output", default="data/scale/scada_5min_2y")
    parser.add_argument("--technology", choices=["solar", "wind"])
    parser.add_argument("--model")
    parser.add_argument("--approver")
    parser.add_argument("--reason")
    args = parser.parse_args()
    if args.command == "ingest":
        result = _ingest()
    elif args.command == "generate-scale":
        output = (PROJECT_ROOT / Path(args.output)).resolve()
        try:
            output.relative_to(PROJECT_ROOT)
        except ValueError as error:
            raise SystemExit("--output must stay inside the project workspace") from error
        result = write_scada_profile(
            output,
            days=args.days,
            frequency=args.frequency,
        )
    elif args.command == "verify-models":
        result = write_model_verification()
    elif args.command == "approve-model":
        required = {
            "--technology": args.technology,
            "--model": args.model,
            "--approver": args.approver,
            "--reason": args.reason,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            parser.error(f"approve-model requires {', '.join(missing)}")
        decision = approve_model(
            technology=str(args.technology),
            model=str(args.model),
            approver=str(args.approver),
            rationale=str(args.reason),
        )
        snapshot = refresh_public_snapshot()
        result = {"approval": decision, "snapshot": snapshot}
    elif args.command == "publish":
        result = refresh_public_snapshot()
    else:
        result = run_demo_pipeline(days=args.days)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
