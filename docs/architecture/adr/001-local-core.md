# ADR-001: núcleo Pandas/NumPy con capa PySpark

- Status: accepted
- Date: 2026-07-28

## Context

La demo debe arrancar en un portátil y explicar con precisión dónde aparece la
escala empresarial.

## Decision

Pandas/NumPy ejecutan el flujo local canónico. PySpark implementa reglas
equivalentes y Databricks materializa Delta/Lakeflow/Unity Catalog.

## Consequences

El bucle local es rápido y gratuito. La reconciliación evita dos verdades de
negocio. No se presenta Spark como necesario para 25.920 filas.

## Validation

`tests/integration/test_pandas_spark_reconciliation.py`.
