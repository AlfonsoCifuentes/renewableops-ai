# ADR-002: promoción de modelos mediante aliases y aprobación

- Status: accepted
- Date: 2026-07-28

## Context

Una métrica agregada no basta para sustituir un modelo operativo.

## Decision

Cada entrenamiento produce Champion/Challenger, evidencia temporal, dataset
hash y gates. Databricks asigna `Challenger`; `Champion` solo cambia con una
decisión explícita. `Rollback` conserva la versión anterior.

## Consequences

La promoción es más lenta, pero reversible y auditable. La demo local marca su
Champion como aprobado solo para demostración.
