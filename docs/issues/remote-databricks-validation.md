# Gate externo — ejecución Databricks Free Edition

- Estado: abierto; requiere acción del propietario.
- Alcance afectado: criterios 25, 26 y 28, y evidencia remota de Unity Catalog.
- Última comprobación: 2026-07-29.

## Bloqueo

No existe en este entorno un `DATABRICKS_HOST` ni una sesión OAuth autorizada.
Crear una cuenta, aceptar términos o usar capacidad de un workspace son acciones
personales que no se pueden suplantar ni resolver con credenciales ficticias.

## Impacto

El bundle, Lakeflow pipeline, Jobs, entrenamiento/registro MLflow, catálogo,
volume, grants y dashboard AI/BI están terminados y validan estructuralmente,
pero no se puede afirmar que sus runs remotos hayan finalizado ni mostrar IDs,
lineage o una URL publicada del workspace.

## Evidencia

- Databricks CLI 1.9.0 ejecutó `bundle validate --strict` contra un stub local
  acotado: `Validation OK!`.
- `databricks/resources/` contiene pipeline y tres Jobs con dependencias.
- `databricks/src/renewableops_operations.lvdash.json` contiene el dashboard.
- `databricks/sql/` contiene catálogo, schemas, Volume, grants y metric views.
- `artifacts/verification/platform-validation.json` conserva el resultado.

## Alternativa disponible

La demo completa funciona sin cloud con Pandas, PySpark 4.2, Parquet,
MLflow/SQLite, registry local, FastAPI y snapshots estáticos. Así se puede
evaluar la lógica sin coste y sin ocultar la diferencia con una ejecución
Databricks real.

## Próximo paso

El propietario ejecuta:

```text
databricks auth login --host <workspace-url> --profile renewableops-free
make databricks-bootstrap
make databricks-upload-demo
make databricks-validate
make databricks-deploy
make databricks-run
make databricks-export-snapshot
```

Después se añaden los IDs de pipeline/Job/modelo/dashboard y capturas saneadas a
esta página, se comprueba lineage y se cambian los criterios 25, 26 y 28 a
«sí». Los schedules permanecen pausados y no existe autopromoción.
