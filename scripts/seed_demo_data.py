"""Generate the complete deterministic local demonstration."""

from __future__ import annotations

import json

from renewableops.pipeline import run_demo_pipeline

if __name__ == "__main__":
    print(json.dumps(run_demo_pipeline(days=90), indent=2, default=str))
