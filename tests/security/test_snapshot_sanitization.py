from __future__ import annotations

import math

import pytest
from renewableops.snapshots import SnapshotValidationError, _validate_public_document


def test_public_snapshot_rejects_secret_fields_and_local_paths() -> None:
    with pytest.raises(SnapshotValidationError, match="forbidden field"):
        _validate_public_document("unsafe.json", {"api_key": "not-even-a-real-secret"})
    with pytest.raises(SnapshotValidationError, match="local path"):
        _validate_public_document(
            "unsafe.json",
            {"resource": r"C:\Users\operator\private\artifact.json"},
        )


def test_public_snapshot_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValueError):
        _validate_public_document("unsafe.json", {"metric": math.nan})


def test_public_snapshot_accepts_bounded_public_evidence() -> None:
    encoded = _validate_public_document(
        "safe.json",
        {
            "source": "Eurostat",
            "checksum": "a" * 64,
            "is_synthetic": False,
        },
    )
    assert b"Eurostat" in encoded
