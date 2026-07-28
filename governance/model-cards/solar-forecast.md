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
availability, lag 24 h and shifted rolling 24 h. Last 14 days are holdout.

## Algorithm and validation

Ridge, ExtraTrees and HistGradientBoosting are compared with 24 h persistence.
Champion is lowest MAE. Metrics are recorded in
`data/models/forecast_metrics.json`; exact run evidence supersedes this card.

## Error analysis

Expected weaknesses: dawn/dusk transitions, extreme cloud changes, outage
periods and a distribution unlike a real plant. Interval residuals are
empirical and not calibrated for all regimes.

## Security, monitoring and rollback

Joblib is loaded only from a trusted local artifact path. Monitor nMAE, bias,
coverage, latency and drift. Promotion needs approval; rollback restores the
previous Champion.
