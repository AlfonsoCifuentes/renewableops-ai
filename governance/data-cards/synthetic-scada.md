# Data Card — Synthetic SCADA

## Identity

- Dataset: `synthetic_scada_bronze`
- Version: manifest timestamp
- Owner: Data Engineering
- Classification: public synthetic

## Content and collection

Hourly telemetry for 12 fictitious solar, wind and battery assets across 90
days. NumPy creates autocorrelated weather, heteroscedastic noise, availability
and labelled soiling/yaw/frozen-sensor scenarios.

## Transformations

Bronze is immutable Parquet. Silver normalizes UTC, deduplicates, checks
physical ranges and interpolates only short numeric gaps. Gold evaluates
forecasts.

## Quality

Reproducible seed, unique asset/timestamp key, synthetic flag, bounds,
freshness, schema/content hash and row counts. Quarantined rows never silently
enter Gold.

## Bias and limitations

Not representative of every Spanish technology, OEM, topology or fault rate.
No personal data. Retention is repository demo history; regenerate at will.
