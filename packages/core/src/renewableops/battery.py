"""Bounded battery dispatch heuristic for transparent what-if analysis."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DispatchStep:
    horizon_hour: int
    price_eur_mwh: float
    charge_mw: float
    discharge_mw: float
    state_of_charge_mwh: float
    cashflow_eur: float


def optimize_dispatch(
    prices_eur_mwh: list[float],
    *,
    capacity_mwh: float,
    max_power_mw: float,
    initial_soc_fraction: float = 0.5,
    reserve_fraction: float = 0.1,
    roundtrip_efficiency: float = 0.90,
) -> tuple[list[DispatchStep], float]:
    """Produce an explainable charge/discharge plan with hard physical bounds.

    This demonstrator uses robust price quantiles rather than claiming to be a
    market-grade optimizer. It forbids simultaneous charge/discharge and
    accounts for symmetric conversion losses.
    """

    if not prices_eur_mwh or len(prices_eur_mwh) > 168:
        raise ValueError("prices must contain between 1 and 168 hourly values")
    if capacity_mwh <= 0 or max_power_mw <= 0:
        raise ValueError("capacity and power must be positive")
    if not 0 <= reserve_fraction < initial_soc_fraction <= 1:
        raise ValueError("SOC fractions are inconsistent")
    if not 0 < roundtrip_efficiency <= 1:
        raise ValueError("roundtrip_efficiency must be in (0, 1]")

    prices = np.asarray(prices_eur_mwh, dtype=float)
    if not np.isfinite(prices).all():
        raise ValueError("prices must be finite")
    charge_threshold, discharge_threshold = np.quantile(prices, [0.30, 0.70])
    one_way_efficiency = float(np.sqrt(roundtrip_efficiency))
    minimum_soc = capacity_mwh * reserve_fraction
    soc = capacity_mwh * initial_soc_fraction
    steps: list[DispatchStep] = []

    for horizon, price in enumerate(prices, start=1):
        charge = 0.0
        discharge = 0.0
        if price <= charge_threshold:
            charge = min(max_power_mw, (capacity_mwh - soc) / one_way_efficiency)
            soc += charge * one_way_efficiency
        elif price >= discharge_threshold:
            discharge = min(max_power_mw, (soc - minimum_soc) * one_way_efficiency)
            soc -= discharge / one_way_efficiency
        cashflow = discharge * price - charge * price
        steps.append(
            DispatchStep(
                horizon_hour=horizon,
                price_eur_mwh=round(float(price), 4),
                charge_mw=round(float(charge), 4),
                discharge_mw=round(float(discharge), 4),
                state_of_charge_mwh=round(float(soc), 4),
                cashflow_eur=round(float(cashflow), 2),
            )
        )
    return steps, round(sum(item.cashflow_eur for item in steps), 2)
