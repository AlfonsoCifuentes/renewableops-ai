# Model Card — Wind Forecast

## Identity

- Artifact: `wind_forecast_champion.joblib`
- Version: 1.0.0
- Owner: ML Engineering

## Task

Probabilistic hourly generation forecast for fictitious wind assets.

## Data / features

Synthetic power curve, wind speed, temperature, cloud, availability, causal
lags and rolling features. The split is blocked; no random temporal shuffle.

## Algorithms / metrics

Persistence, Ridge, ExtraTrees and HistGradientBoosting. MAE, RMSE, nMAE, bias,
skill and P10–P90 coverage are versioned with the artifact.

## Limitations

No wake, curtailment, NWP ensemble or turbine-specific power-curve calibration
from a real park. Extreme winds and icing are underrepresented.

## Monitoring / rollback

Track error by asset and wind regime. Hold promotion when extreme-wind evidence
is insufficient. Aliases preserve Champion, Challenger and Rollback.
