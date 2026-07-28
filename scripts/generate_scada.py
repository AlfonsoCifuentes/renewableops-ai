"""Regenerate only the synthetic SCADA sample."""

from __future__ import annotations

from renewableops.config import LAKEHOUSE_DIR, ensure_directories
from renewableops.synthetic import generate_scada

if __name__ == "__main__":
    ensure_directories()
    frame = generate_scada(days=90)
    target = LAKEHOUSE_DIR / "bronze" / "synthetic_scada.parquet"
    frame.to_parquet(target, index=False, compression="zstd")
    print(f"{len(frame)} rows written to {target}")
