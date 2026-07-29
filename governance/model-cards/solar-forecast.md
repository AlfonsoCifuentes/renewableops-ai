# Model Card — Solar Forecast

## Identity

- Artifact: `solar_forecast_champion.joblib`
- Version: 1.0.0
- Owner: ML Engineering

## Task and intended use

Forecast asset generation in MW with P10/P50/P90 for demo planning. Not for
dispatch, bids, safety or autonomous control.

## Data and features

Synthetic hourly solar telemetry, causal calendar encodings, weather,
availability, lags 1/24/168 h and shifted rolling 24 h. Last 14 days are an
untouched holdout.

## Algorithm and validation

Ridge, ElasticNet, RandomForest, ExtraTrees and HistGradientBoosting are
compared. Selection uses the lowest mean MAE over three TimeSeriesSplit folds
with a 24 h gap; the test is not used for ranking. Five baselines cover 1 h,
24 h, 168 h, hour/weekday mean and physical expected power. Separate gradient
boosting quantile models estimate P10/P50/P90. Metrics and error buckets 1–48 h
live in `data/models/forecast_metrics.json` and
`data/models/solar_forecast_evidence.json`.

## Error analysis

Expected weaknesses: dawn/dusk transitions, extreme cloud changes, outage
periods and a distribution unlike a real plant. Quantile intervals are measured
but are not guaranteed to be calibrated for every operating regime.

## Security, monitoring and rollback

Joblib is loaded only from a trusted local artifact path. Monitor nMAE, bias,
coverage, latency and drift. Promotion needs approval; rollback restores the
previous Champion.
