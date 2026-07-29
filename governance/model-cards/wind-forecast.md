# Model Card — Wind Forecast

## Identity

- Artifact: `wind_forecast_champion.joblib`
- Version: 1.0.0
- Owner: ML Engineering

## Task

Probabilistic hourly generation forecast for fictitious wind assets.

## Data / features

Synthetic power curve, wind speed, temperature, cloud, availability, causal
lags 1/24/168 h and rolling features. Selection uses three temporal folds with
a 24 h gap and the last 14 days remain untouched until final evaluation.

## Algorithms / metrics

Five persistence/physical baselines and Ridge, ElasticNet, RandomForest,
ExtraTrees and HistGradientBoosting. Separate trained quantile models produce
P10/P50/P90. MAE, RMSE, nMAE, bias, skill, pinball, coverage and error by
horizon are versioned with the artifact.

## Limitations

No wake, curtailment, NWP ensemble or turbine-specific power-curve calibration
from a real park. Extreme winds and icing are underrepresented.

## Monitoring / rollback

Track error by asset and wind regime. Hold promotion when extreme-wind evidence
is insufficient. Aliases preserve Champion, Challenger and Rollback.
