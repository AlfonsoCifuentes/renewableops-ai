from __future__ import annotations

import numpy as np
from renewableops.monitoring import population_stability_index


def test_psi_is_near_zero_for_identical_distributions() -> None:
    values = np.linspace(0, 1, 1_000)
    assert population_stability_index(values, values) < 1e-9


def test_psi_detects_large_distribution_change() -> None:
    reference = np.linspace(0, 1, 1_000)
    shifted = np.linspace(0.7, 1.7, 1_000)
    assert population_stability_index(reference, shifted) > 0.25
