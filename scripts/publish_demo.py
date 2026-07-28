"""Regenerate and validate the sanitized public snapshot."""

from __future__ import annotations

import json

from renewableops.pipeline import run_demo_pipeline

if __name__ == "__main__":
    result = run_demo_pipeline(days=90)
    print(json.dumps({"published": result["snapshot_manifest"]}, indent=2))
